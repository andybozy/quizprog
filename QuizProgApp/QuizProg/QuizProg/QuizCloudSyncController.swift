import Foundation
import CloudKit
import Combine

enum QuizCloudAccountState: String, Codable {
    case checking
    case available
    case noAccount
    case restricted
    case couldNotDetermine

    var title: String {
        switch self {
        case .checking: return "Checking"
        case .available: return "Available"
        case .noAccount: return "No iCloud account"
        case .restricted: return "Restricted"
        case .couldNotDetermine: return "Unavailable"
        }
    }
}

struct QuizCloudSyncConfiguration: Codable, Hashable {
    var autoSyncEnabled: Bool = false
    var sharedProgressSyncEnabled: Bool = true
    var cloudLogMirroringEnabled: Bool = false
}

struct QuizCloudSyncSnapshot: Hashable {
    var accountState: QuizCloudAccountState = .checking
    var lastSharedSyncAt: String?
    var lastLogMirrorAt: String?
    var lastError: String?
    var pendingSharedChanges: Int = 0
    var pendingLogMirroringChanges: Int = 0
    var sharedProgressSyncEnabled = true
    var cloudLogMirroringEnabled = false
    var autoSyncEnabled = false

    static let empty = QuizCloudSyncSnapshot()
}

private enum QuizCloudRecordType {
    static let questionPerformance = "QuizQuestionPerformance"
    static let courseStats = "QuizCourseStats"
    static let bestScore = "QuizBestScore"
    static let deviceLogEvent = "QuizDeviceLogEvent"
}

private enum QuizCloudRecordKey {
    static let questionID = "questionID"
    static let historyJSON = "historyJSON"
    static let ease = "ease"
    static let interval = "interval"
    static let repetition = "repetition"
    static let nextReview = "nextReview"
    static let updatedAt = "updatedAt"

    static let courseID = "courseID"
    static let plays = "plays"
    static let answered = "answered"
    static let correct = "correct"
    static let score = "score"

    static let eventID = "eventID"
    static let payloadJSON = "payloadJSON"
    static let deviceID = "deviceID"
    static let platform = "platform"
    static let occurredAt = "occurredAt"
}

@MainActor
final class QuizCloudSyncController: ObservableObject {
    static let shared = QuizCloudSyncController()

    @Published private(set) var snapshot: QuizCloudSyncSnapshot = .empty
    @Published private(set) var isSyncInProgress = false

    @Published var autoSyncEnabled: Bool {
        didSet { persistConfiguration() }
    }

    @Published var sharedProgressSyncEnabled: Bool {
        didSet { persistConfiguration() }
    }

    @Published var cloudLogMirroringEnabled: Bool {
        didSet { persistConfiguration() }
    }

    private let configurationKey = "quizprog.cloudsync.configuration.v1"
    private let lastSharedSyncKey = "quizprog.cloudsync.lastSharedSync.v1"
    private let lastLogMirrorKey = "quizprog.cloudsync.lastLogMirror.v1"
    private let container = CKContainer.default()
    private let isoFormatter = ISO8601DateFormatter()

    private init() {
        let configuration: QuizCloudSyncConfiguration = Self.loadConfiguration(forKey: configurationKey)
            ?? QuizCloudSyncConfiguration()
        autoSyncEnabled = configuration.autoSyncEnabled
        sharedProgressSyncEnabled = configuration.sharedProgressSyncEnabled
        cloudLogMirroringEnabled = configuration.cloudLogMirroringEnabled

        snapshot.autoSyncEnabled = autoSyncEnabled
        snapshot.sharedProgressSyncEnabled = sharedProgressSyncEnabled
        snapshot.cloudLogMirroringEnabled = cloudLogMirroringEnabled
        snapshot.lastSharedSyncAt = UserDefaults.standard.string(forKey: lastSharedSyncKey)
        snapshot.lastLogMirrorAt = UserDefaults.standard.string(forKey: lastLogMirrorKey)
    }

    func handleSceneBecameActive(session: QuizSession) {
        Task {
            await refreshAccountStatus()
            if autoSyncEnabled {
                await syncNow(session: session)
            } else {
                await refreshPendingCounts(session: session)
            }
        }
    }

    func handleSceneMovedToBackground(session: QuizSession) {
        guard autoSyncEnabled else { return }
        Task {
            await syncNow(session: session)
        }
    }

    func refreshAccountStatus() async {
        snapshot.accountState = .checking
        do {
            let status = try await accountStatus()
            snapshot.accountState = mapAccountStatus(status)
            if snapshot.accountState == .available {
                snapshot.lastError = nil
            }
        } catch {
            snapshot.accountState = .couldNotDetermine
            snapshot.lastError = error.localizedDescription
        }
    }

    func refreshPendingCounts(session: QuizSession) async {
        snapshot.pendingSharedChanges = countPendingSharedChanges(snapshot: session.cloudSharedStateSnapshot())
        do {
            snapshot.pendingLogMirroringChanges = try await QuizLogController.shared.cloudPendingCount()
        } catch {
            snapshot.lastError = error.localizedDescription
        }
    }

    func syncNow(session: QuizSession) async {
        guard !isSyncInProgress else { return }
        await refreshAccountStatus()
        guard snapshot.accountState == .available else { return }

        isSyncInProgress = true
        defer { isSyncInProgress = false }

        do {
            if sharedProgressSyncEnabled {
                try await syncSharedProgress(session: session)
            }
            if cloudLogMirroringEnabled {
                try await mirrorDeviceLogs()
            }
            await refreshPendingCounts(session: session)
        } catch {
            snapshot.lastError = error.localizedDescription
        }
    }

    func scheduleAutoSync(session: QuizSession) {
        guard autoSyncEnabled else { return }
        Task {
            await syncNow(session: session)
        }
    }

    private func syncSharedProgress(session: QuizSession) async throws {
        let localSnapshot = session.cloudSharedStateSnapshot()

        async let remotePerformancesTask = fetchAllRecords(ofType: QuizCloudRecordType.questionPerformance)
        async let remoteCourseStatsTask = fetchAllRecords(ofType: QuizCloudRecordType.courseStats)
        async let remoteBestScoresTask = fetchAllRecords(ofType: QuizCloudRecordType.bestScore)

        let remotePerformances = try await remotePerformancesTask
        let remoteCourseStats = try await remoteCourseStatsTask
        let remoteBestScores = try await remoteBestScoresTask

        let mergeResult = mergeSharedState(
            local: localSnapshot,
            remoteQuestionPerformances: remotePerformances,
            remoteCourseStats: remoteCourseStats,
            remoteBestScores: remoteBestScores
        )

        session.applyCloudSharedState(mergeResult.mergedSnapshot)
        if !mergeResult.recordsToSave.isEmpty {
            try await saveRecords(mergeResult.recordsToSave)
        }

        let timestamp = isoFormatter.string(from: Date())
        snapshot.lastSharedSyncAt = timestamp
        UserDefaults.standard.set(timestamp, forKey: lastSharedSyncKey)
        snapshot.lastError = nil
    }

    private func mirrorDeviceLogs() async throws {
        let events = try await QuizLogController.shared.cloudSyncableEvents(limit: 200)
        guard !events.isEmpty else { return }

        try await QuizLogController.shared.markCloudSyncing(eventIDs: events.map(\.id))
        do {
            let records = events.map(makeDeviceLogRecord(from:))
            try await saveRecords(records)
            let timestamp = isoFormatter.string(from: Date())
            try await QuizLogController.shared.markCloudSynced(eventIDs: events.map(\.id), at: timestamp)
            snapshot.lastLogMirrorAt = timestamp
            UserDefaults.standard.set(timestamp, forKey: lastLogMirrorKey)
        } catch {
            try? await QuizLogController.shared.markCloudFailed(eventIDs: events.map(\.id), error: error.localizedDescription)
            throw error
        }
    }

    private func mergeSharedState(
        local: QuizCloudSharedStateSnapshot,
        remoteQuestionPerformances: [CKRecord],
        remoteCourseStats: [CKRecord],
        remoteBestScores: [CKRecord]
    ) -> (mergedSnapshot: QuizCloudSharedStateSnapshot, recordsToSave: [CKRecord]) {
        var merged = local
        var recordsToSave: [CKRecord] = []

        let remotePerformancesByID: [String: QuizQuestionPerformance] = Dictionary(
            uniqueKeysWithValues: remoteQuestionPerformances.compactMap { record in
                guard
                    let questionID = record[QuizCloudRecordKey.questionID] as? String,
                    let performance = questionPerformance(from: record)
                else { return nil }
                return (questionID, performance)
            }
        )

        for (questionID, remotePerformance) in remotePerformancesByID {
            guard let localPerformance = merged.questionPerformances[questionID] else {
                merged.questionPerformances[questionID] = remotePerformance
                continue
            }
            if compareTimestamps(lhs: remotePerformance.updatedAt, rhs: localPerformance.updatedAt) == .orderedDescending {
                merged.questionPerformances[questionID] = remotePerformance
            }
        }

        for (questionID, localPerformance) in merged.questionPerformances {
            let remotePerformance = remotePerformancesByID[questionID]
            if remotePerformance == nil || compareTimestamps(lhs: localPerformance.updatedAt, rhs: remotePerformance?.updatedAt) != .orderedAscending {
                recordsToSave.append(makeQuestionPerformanceRecord(questionID: questionID, performance: localPerformance))
            }
        }

        let remoteStatsByID: [String: QuizCourseStats] = Dictionary(
            uniqueKeysWithValues: remoteCourseStats.compactMap { record in
                guard
                    let courseID = record[QuizCloudRecordKey.courseID] as? String,
                    let stats = courseStats(from: record)
                else { return nil }
                return (courseID, stats)
            }
        )

        for (courseID, remoteStats) in remoteStatsByID {
            guard let localStats = merged.courseStats[courseID] else {
                merged.courseStats[courseID] = remoteStats
                continue
            }
            if compareTimestamps(lhs: remoteStats.updatedAt, rhs: localStats.updatedAt) == .orderedDescending {
                merged.courseStats[courseID] = remoteStats
            }
        }

        for (courseID, stats) in merged.courseStats {
            let remoteStats = remoteStatsByID[courseID]
            if remoteStats == nil || compareTimestamps(lhs: stats.updatedAt, rhs: remoteStats?.updatedAt) != .orderedAscending {
                recordsToSave.append(makeCourseStatsRecord(courseID: courseID, stats: stats))
            }
        }

        let remoteBestScoresByID: [String: QuizBestScoreEntry] = Dictionary(
            uniqueKeysWithValues: remoteBestScores.compactMap { record in
                guard
                    let courseID = record[QuizCloudRecordKey.courseID] as? String,
                    let scoreEntry = bestScoreEntry(from: record)
                else { return nil }
                return (courseID, scoreEntry)
            }
        )

        for (courseID, remoteBestScore) in remoteBestScoresByID {
            guard let localBestScore = merged.bestScores[courseID] else {
                merged.bestScores[courseID] = remoteBestScore
                continue
            }
            if compareTimestamps(lhs: remoteBestScore.updatedAt, rhs: localBestScore.updatedAt) == .orderedDescending {
                merged.bestScores[courseID] = remoteBestScore
            }
        }

        for (courseID, scoreEntry) in merged.bestScores {
            let remoteBestScore = remoteBestScoresByID[courseID]
            if remoteBestScore == nil || compareTimestamps(lhs: scoreEntry.updatedAt, rhs: remoteBestScore?.updatedAt) != .orderedAscending {
                recordsToSave.append(makeBestScoreRecord(courseID: courseID, bestScore: scoreEntry))
            }
        }

        return (merged, recordsToSave)
    }

    private func fetchAllRecords(ofType recordType: String) async throws -> [CKRecord] {
        try await withCheckedThrowingContinuation { continuation in
            var collected: [CKRecord] = []

            func run(cursor: CKQueryOperation.Cursor?) {
                let operation: CKQueryOperation
                if let cursor {
                    operation = CKQueryOperation(cursor: cursor)
                } else {
                    let query = CKQuery(recordType: recordType, predicate: NSPredicate(value: true))
                    operation = CKQueryOperation(query: query)
                }

                operation.resultsLimit = 500
                operation.recordMatchedBlock = { _, result in
                    switch result {
                    case .success(let record):
                        collected.append(record)
                    case .failure:
                        break
                    }
                }
                operation.queryResultBlock = { result in
                    switch result {
                    case .success(let cursor):
                        if let cursor {
                            run(cursor: cursor)
                        } else {
                            continuation.resume(returning: collected)
                        }
                    case .failure(let error):
                        continuation.resume(throwing: error)
                    }
                }
                self.container.privateCloudDatabase.add(operation)
            }

            run(cursor: nil)
        }
    }

    private func saveRecords(_ records: [CKRecord]) async throws {
        guard !records.isEmpty else { return }
        try await withCheckedThrowingContinuation { continuation in
            let operation = CKModifyRecordsOperation(recordsToSave: records, recordIDsToDelete: nil)
            operation.savePolicy = .changedKeys
            operation.modifyRecordsResultBlock = { result in
                switch result {
                case .success:
                    continuation.resume()
                case .failure(let error):
                    continuation.resume(throwing: error)
                }
            }
            self.container.privateCloudDatabase.add(operation)
        }
    }

    private func makeQuestionPerformanceRecord(questionID: String, performance: QuizQuestionPerformance) -> CKRecord {
        let recordID = CKRecord.ID(recordName: "question-performance-\(questionID)")
        let record = CKRecord(recordType: QuizCloudRecordType.questionPerformance, recordID: recordID)
        record[QuizCloudRecordKey.questionID] = questionID as CKRecordValue
        record[QuizCloudRecordKey.historyJSON] = String(decoding: (try? JSONEncoder().encode(performance.history)) ?? Data("[]".utf8), as: UTF8.self) as CKRecordValue
        record[QuizCloudRecordKey.ease] = performance.ease as CKRecordValue
        record[QuizCloudRecordKey.interval] = performance.interval as CKRecordValue
        record[QuizCloudRecordKey.repetition] = performance.repetition as CKRecordValue
        if let nextReview = performance.nextReview {
            record[QuizCloudRecordKey.nextReview] = nextReview as CKRecordValue
        }
        if let updatedAt = performance.updatedAt {
            record[QuizCloudRecordKey.updatedAt] = updatedAt as CKRecordValue
        }
        return record
    }

    private func questionPerformance(from record: CKRecord) -> QuizQuestionPerformance? {
        let historyJSON = record[QuizCloudRecordKey.historyJSON] as? String ?? "[]"
        let history = (try? JSONDecoder().decode([String].self, from: Data(historyJSON.utf8))) ?? []
        return QuizQuestionPerformance(
            history: history,
            ease: record[QuizCloudRecordKey.ease] as? Double ?? 2.5,
            interval: record[QuizCloudRecordKey.interval] as? Int ?? 0,
            repetition: record[QuizCloudRecordKey.repetition] as? Int ?? 0,
            nextReview: record[QuizCloudRecordKey.nextReview] as? String,
            updatedAt: record[QuizCloudRecordKey.updatedAt] as? String
        )
    }

    private func makeCourseStatsRecord(courseID: String, stats: QuizCourseStats) -> CKRecord {
        let recordID = CKRecord.ID(recordName: "course-stats-\(courseID)")
        let record = CKRecord(recordType: QuizCloudRecordType.courseStats, recordID: recordID)
        record[QuizCloudRecordKey.courseID] = courseID as CKRecordValue
        record[QuizCloudRecordKey.plays] = stats.plays as CKRecordValue
        record[QuizCloudRecordKey.answered] = stats.answered as CKRecordValue
        record[QuizCloudRecordKey.correct] = stats.correct as CKRecordValue
        if let updatedAt = stats.updatedAt {
            record[QuizCloudRecordKey.updatedAt] = updatedAt as CKRecordValue
        }
        return record
    }

    private func courseStats(from record: CKRecord) -> QuizCourseStats? {
        QuizCourseStats(
            plays: record[QuizCloudRecordKey.plays] as? Int ?? 0,
            answered: record[QuizCloudRecordKey.answered] as? Int ?? 0,
            correct: record[QuizCloudRecordKey.correct] as? Int ?? 0,
            updatedAt: record[QuizCloudRecordKey.updatedAt] as? String
        )
    }

    private func makeBestScoreRecord(courseID: String, bestScore: QuizBestScoreEntry) -> CKRecord {
        let recordID = CKRecord.ID(recordName: "best-score-\(courseID)")
        let record = CKRecord(recordType: QuizCloudRecordType.bestScore, recordID: recordID)
        record[QuizCloudRecordKey.courseID] = courseID as CKRecordValue
        record[QuizCloudRecordKey.score] = bestScore.score as CKRecordValue
        if let updatedAt = bestScore.updatedAt {
            record[QuizCloudRecordKey.updatedAt] = updatedAt as CKRecordValue
        }
        return record
    }

    private func bestScoreEntry(from record: CKRecord) -> QuizBestScoreEntry? {
        QuizBestScoreEntry(
            score: record[QuizCloudRecordKey.score] as? Int ?? 0,
            updatedAt: record[QuizCloudRecordKey.updatedAt] as? String
        )
    }

    private func makeDeviceLogRecord(from event: QuizLogEvent) -> CKRecord {
        let recordID = CKRecord.ID(recordName: "device-log-\(event.deviceID)-\(event.id)")
        let record = CKRecord(recordType: QuizCloudRecordType.deviceLogEvent, recordID: recordID)
        let payload = (try? JSONEncoder().encode(event)).flatMap { String(data: $0, encoding: .utf8) } ?? "{}"
        record[QuizCloudRecordKey.eventID] = event.id as CKRecordValue
        record[QuizCloudRecordKey.deviceID] = event.deviceID as CKRecordValue
        record[QuizCloudRecordKey.platform] = currentPlatform as CKRecordValue
        record[QuizCloudRecordKey.occurredAt] = event.occurredAt as CKRecordValue
        record[QuizCloudRecordKey.payloadJSON] = payload as CKRecordValue
        return record
    }

    private func accountStatus() async throws -> CKAccountStatus {
        try await withCheckedThrowingContinuation { continuation in
            container.accountStatus { status, error in
                if let error {
                    continuation.resume(throwing: error)
                } else {
                    continuation.resume(returning: status)
                }
            }
        }
    }

    private func mapAccountStatus(_ status: CKAccountStatus) -> QuizCloudAccountState {
        switch status {
        case .available:
            return .available
        case .noAccount:
            return .noAccount
        case .restricted:
            return .restricted
        default:
            return .couldNotDetermine
        }
    }

    private func countPendingSharedChanges(snapshot sharedState: QuizCloudSharedStateSnapshot) -> Int {
        let lastSyncDate = parseTimestamp(self.snapshot.lastSharedSyncAt)
        let performancePending = sharedState.questionPerformances.values.filter {
            isTimestamp($0.updatedAt, newerThan: lastSyncDate)
        }.count
        let statsPending = sharedState.courseStats.values.filter {
            isTimestamp($0.updatedAt, newerThan: lastSyncDate)
        }.count
        let bestScorePending = sharedState.bestScores.values.filter {
            isTimestamp($0.updatedAt, newerThan: lastSyncDate)
        }.count
        return performancePending + statsPending + bestScorePending
    }

    private func compareTimestamps(lhs: String?, rhs: String?) -> ComparisonResult {
        let lhsDate = parseTimestamp(lhs) ?? .distantPast
        let rhsDate = parseTimestamp(rhs) ?? .distantPast
        if lhsDate == rhsDate { return .orderedSame }
        return lhsDate < rhsDate ? .orderedAscending : .orderedDescending
    }

    private func isTimestamp(_ timestamp: String?, newerThan referenceDate: Date?) -> Bool {
        guard let date = parseTimestamp(timestamp) else { return false }
        guard let referenceDate else { return true }
        return date > referenceDate
    }

    private func parseTimestamp(_ value: String?) -> Date? {
        guard let value, !value.isEmpty else { return nil }
        return isoFormatter.date(from: value)
    }

    private var currentPlatform: String {
        #if os(macOS)
        return "macos"
        #else
        return "ios"
        #endif
    }

    private func persistConfiguration() {
        let configuration = QuizCloudSyncConfiguration(
            autoSyncEnabled: autoSyncEnabled,
            sharedProgressSyncEnabled: sharedProgressSyncEnabled,
            cloudLogMirroringEnabled: cloudLogMirroringEnabled
        )
        if let data = try? JSONEncoder().encode(configuration) {
            UserDefaults.standard.set(data, forKey: configurationKey)
        }
        snapshot.autoSyncEnabled = autoSyncEnabled
        snapshot.sharedProgressSyncEnabled = sharedProgressSyncEnabled
        snapshot.cloudLogMirroringEnabled = cloudLogMirroringEnabled
    }

    private static func loadConfiguration(forKey key: String) -> QuizCloudSyncConfiguration? {
        guard let data = UserDefaults.standard.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(QuizCloudSyncConfiguration.self, from: data)
    }
}
