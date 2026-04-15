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
    static let datasetFamily = "datasetFamily"
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
        let writeFamily = session.writeFamily
        let localSnapshot = session.cloudSharedStateSnapshot()
        var remoteSnapshots = try await fetchRemoteFamilySnapshots()

        let mergeResult = mergeSharedState(
            local: localSnapshot,
            remote: remoteSnapshots[writeFamily] ?? .empty
        )

        remoteSnapshots[writeFamily] = mergeResult.mergedSnapshot
        session.applyCloudFamilySnapshots(
            localFamilySnapshot: mergeResult.mergedSnapshot,
            remoteFamilySnapshots: remoteSnapshots
        )
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
        remote: QuizCloudSharedStateSnapshot
    ) -> (mergedSnapshot: QuizCloudSharedStateSnapshot, recordsToSave: [CKRecord]) {
        let merged = sessionLikeMerge(local: local, remote: remote)
        var recordsToSave: [CKRecord] = []

        for (questionID, localPerformance) in merged.questionPerformances {
            let remotePerformance = remote.questionPerformances[questionID]
            if remotePerformance == nil || compareTimestamps(lhs: localPerformance.updatedAt, rhs: remotePerformance?.updatedAt) != .orderedAscending {
                recordsToSave.append(
                    makeQuestionPerformanceRecord(
                        family: currentWriteFamily,
                        questionID: questionID,
                        performance: localPerformance
                    )
                )
            }
        }

        for (courseID, stats) in merged.courseStats {
            let remoteStats = remote.courseStats[courseID]
            if remoteStats == nil || compareTimestamps(lhs: stats.updatedAt, rhs: remoteStats?.updatedAt) != .orderedAscending {
                recordsToSave.append(
                    makeCourseStatsRecord(
                        family: currentWriteFamily,
                        courseID: courseID,
                        stats: stats
                    )
                )
            }
        }

        for (courseID, scoreEntry) in merged.bestScores {
            let remoteBestScore = remote.bestScores[courseID]
            if remoteBestScore == nil || compareTimestamps(lhs: scoreEntry.updatedAt, rhs: remoteBestScore?.updatedAt) != .orderedAscending {
                recordsToSave.append(
                    makeBestScoreRecord(
                        family: currentWriteFamily,
                        courseID: courseID,
                        bestScore: scoreEntry
                    )
                )
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
                        if QuizCloudSyncController.isMissingRecordTypeError(error) {
                            continuation.resume(returning: [])
                        } else {
                            continuation.resume(throwing: error)
                        }
                    }
                }
                self.container.privateCloudDatabase.add(operation)
            }

            run(cursor: nil)
        }
    }

    private func fetchRemoteFamilySnapshots() async throws -> [QuizDatasetFamily: QuizCloudSharedStateSnapshot] {
        async let remotePerformancesTask = fetchAllRecords(ofType: QuizCloudRecordType.questionPerformance)
        async let remoteCourseStatsTask = fetchAllRecords(ofType: QuizCloudRecordType.courseStats)
        async let remoteBestScoresTask = fetchAllRecords(ofType: QuizCloudRecordType.bestScore)

        let remotePerformances = try await remotePerformancesTask
        let remoteCourseStats = try await remoteCourseStatsTask
        let remoteBestScores = try await remoteBestScoresTask

        var snapshots: [QuizDatasetFamily: QuizCloudSharedStateSnapshot] = [
            .ios: .empty,
            .macos: .empty,
        ]

        for record in remotePerformances {
            guard
                let family = datasetFamily(from: record),
                let questionID = record[QuizCloudRecordKey.questionID] as? String,
                let performance = questionPerformance(from: record)
            else { continue }
            snapshots[family, default: .empty].questionPerformances[questionID] = performance
        }

        for record in remoteCourseStats {
            guard
                let family = datasetFamily(from: record),
                let courseID = record[QuizCloudRecordKey.courseID] as? String,
                let stats = courseStats(from: record)
            else { continue }
            snapshots[family, default: .empty].courseStats[courseID] = stats
        }

        for record in remoteBestScores {
            guard
                let family = datasetFamily(from: record),
                let courseID = record[QuizCloudRecordKey.courseID] as? String,
                let bestScore = bestScoreEntry(from: record)
            else { continue }
            snapshots[family, default: .empty].bestScores[courseID] = bestScore
        }

        return snapshots
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

    private func makeQuestionPerformanceRecord(family: QuizDatasetFamily, questionID: String, performance: QuizQuestionPerformance) -> CKRecord {
        let recordID = CKRecord.ID(recordName: "question-performance|\(family.rawValue)|\(questionID)")
        let record = CKRecord(recordType: QuizCloudRecordType.questionPerformance, recordID: recordID)
        record[QuizCloudRecordKey.datasetFamily] = family.rawValue as CKRecordValue
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

    private func makeCourseStatsRecord(family: QuizDatasetFamily, courseID: String, stats: QuizCourseStats) -> CKRecord {
        let recordID = CKRecord.ID(recordName: "course-stats|\(family.rawValue)|\(courseID)")
        let record = CKRecord(recordType: QuizCloudRecordType.courseStats, recordID: recordID)
        record[QuizCloudRecordKey.datasetFamily] = family.rawValue as CKRecordValue
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

    private func makeBestScoreRecord(family: QuizDatasetFamily, courseID: String, bestScore: QuizBestScoreEntry) -> CKRecord {
        let recordID = CKRecord.ID(recordName: "best-score|\(family.rawValue)|\(courseID)")
        let record = CKRecord(recordType: QuizCloudRecordType.bestScore, recordID: recordID)
        record[QuizCloudRecordKey.datasetFamily] = family.rawValue as CKRecordValue
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
        let family = QuizDatasetFamily(rawValue: event.datasetFamily) ?? currentWriteFamily
        let recordID = CKRecord.ID(recordName: "device-log|\(family.rawValue)|\(event.deviceID)|\(event.id)")
        let record = CKRecord(recordType: QuizCloudRecordType.deviceLogEvent, recordID: recordID)
        let payload = (try? JSONEncoder().encode(event)).flatMap { String(data: $0, encoding: .utf8) } ?? "{}"
        record[QuizCloudRecordKey.datasetFamily] = family.rawValue as CKRecordValue
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

    private func datasetFamily(from record: CKRecord) -> QuizDatasetFamily? {
        guard let rawValue = record[QuizCloudRecordKey.datasetFamily] as? String else { return nil }
        return QuizDatasetFamily(rawValue: rawValue)
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
        #if targetEnvironment(macCatalyst)
        return "macos"
        #elseif os(macOS)
        return "macos"
        #else
        return "ios"
        #endif
    }

    private var currentWriteFamily: QuizDatasetFamily {
        #if targetEnvironment(macCatalyst)
        return .macos
        #elseif os(macOS)
        return .macos
        #else
        return .ios
        #endif
    }

    private func sessionLikeMerge(
        local: QuizCloudSharedStateSnapshot,
        remote: QuizCloudSharedStateSnapshot
    ) -> QuizCloudSharedStateSnapshot {
        var mergedPerformances = remote.questionPerformances
        for (questionID, localPerformance) in local.questionPerformances {
            guard let remotePerformance = mergedPerformances[questionID] else {
                mergedPerformances[questionID] = localPerformance
                continue
            }
            if compareTimestamps(lhs: remotePerformance.updatedAt, rhs: localPerformance.updatedAt) != .orderedDescending {
                mergedPerformances[questionID] = localPerformance
            }
        }

        var mergedStats = remote.courseStats
        for (courseID, localStats) in local.courseStats {
            guard let remoteStats = mergedStats[courseID] else {
                mergedStats[courseID] = localStats
                continue
            }
            if compareTimestamps(lhs: remoteStats.updatedAt, rhs: localStats.updatedAt) != .orderedDescending {
                mergedStats[courseID] = localStats
            }
        }

        var mergedBestScores = remote.bestScores
        for (courseID, localBestScore) in local.bestScores {
            guard let remoteBestScore = mergedBestScores[courseID] else {
                mergedBestScores[courseID] = localBestScore
                continue
            }
            if compareTimestamps(lhs: remoteBestScore.updatedAt, rhs: localBestScore.updatedAt) != .orderedDescending {
                mergedBestScores[courseID] = localBestScore
            }
        }

        return QuizCloudSharedStateSnapshot(
            questionPerformances: mergedPerformances,
            courseStats: mergedStats,
            bestScores: mergedBestScores
        )
    }

    private nonisolated static func isMissingRecordTypeError(_ error: Error) -> Bool {
        let nsError = error as NSError
        if nsError.localizedDescription.localizedCaseInsensitiveContains("did not find record type") {
            return true
        }
        if let serverMessage = nsError.userInfo[NSLocalizedDescriptionKey] as? String,
           serverMessage.localizedCaseInsensitiveContains("did not find record type") {
            return true
        }
        return false
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
