import Foundation
import Combine
import SQLite3

enum QuizLogEventType: String, Codable, CaseIterable {
    case quizStarted = "quiz_started"
    case quizResumed = "quiz_resumed"
    case questionAnswered = "question_answered"
    case questionSkipped = "question_skipped"
    case quizExited = "quiz_exited"
    case quizFinished = "quiz_finished"
}

enum QuizLogSyncStatus: String, Codable {
    case pending
    case syncing
    case synced
    case failed
}

struct QuizLogEvent: Identifiable, Codable, Hashable {
    let id: String
    let occurredAt: String
    let sessionID: String
    let deviceID: String
    let questionID: String?
    let courseKey: String?
    let sourcePath: String?
    let filterMode: String?
    let scope: String?
    let eventType: QuizLogEventType
    let selectedIndex: Int?
    let correctIndex: Int?
    let result: String?
    let appVersion: String
    let buildNumber: String
    let metadata: [String: String]

    private enum CodingKeys: String, CodingKey {
        case id = "event_id"
        case occurredAt = "occurred_at"
        case sessionID = "session_id"
        case deviceID = "device_id"
        case questionID = "question_id"
        case courseKey = "course_key"
        case sourcePath = "source_path"
        case filterMode = "filter_mode"
        case scope
        case eventType = "event_type"
        case selectedIndex = "selected_index"
        case correctIndex = "correct_index"
        case result
        case appVersion = "app_version"
        case buildNumber = "build_number"
        case metadata
    }
}

struct QuizLogConfiguration: Codable, Hashable {
    var serverURLString: String = ""
    var apiKey: String = ""
    var autoSyncEnabled: Bool = false
    var batchSize: Int = 50
}

struct QuizLogSnapshot: Hashable {
    var totalCount: Int = 0
    var pendingCount: Int = 0
    var syncingCount: Int = 0
    var syncedCount: Int = 0
    var failedCount: Int = 0
    var lastSyncedAt: String?
    var cloudPendingCount: Int = 0
    var cloudSyncingCount: Int = 0
    var cloudSyncedCount: Int = 0
    var cloudFailedCount: Int = 0
    var lastCloudSyncedAt: String?
    var lastError: String?

    static let empty = QuizLogSnapshot()
}

struct QuizLogSyncResult: Decodable {
    let accepted: Int?
    let deduplicated: Int?
}

private actor QuizLogStore {
    private let schemaSQL = """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
        occurred_at TEXT NOT NULL,
        session_id TEXT NOT NULL,
        device_id TEXT NOT NULL,
        question_id TEXT,
        course_key TEXT,
        source_path TEXT,
        filter_mode TEXT,
        scope TEXT,
        event_type TEXT NOT NULL,
        selected_index INTEGER,
        correct_index INTEGER,
        result TEXT,
        app_version TEXT NOT NULL,
        build_number TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        payload_json TEXT NOT NULL,
            sync_status TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            cloud_sync_status TEXT NOT NULL DEFAULT 'pending',
            cloud_retry_count INTEGER NOT NULL DEFAULT 0,
            cloud_last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            synced_at TEXT,
            received_at TEXT,
            cloud_synced_at TEXT
        );
    CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events (occurred_at);
    CREATE INDEX IF NOT EXISTS idx_events_sync_status ON events (sync_status);
    CREATE INDEX IF NOT EXISTS idx_events_course_key ON events (course_key);
    CREATE INDEX IF NOT EXISTS idx_events_session_id ON events (session_id);
    """
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()
    private let isoFormatter = ISO8601DateFormatter()
    private let dbURL: URL
    private var db: OpaquePointer?

    init() {
        let fm = FileManager.default
        let appSupport = try! fm.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        let directory = appSupport.appendingPathComponent("QuizProg", isDirectory: true)
        try! fm.createDirectory(at: directory, withIntermediateDirectories: true)
        dbURL = directory.appendingPathComponent("quiz_log.sqlite3")
        sqlite3_open_v2(
            dbURL.path,
            &db,
            SQLITE_OPEN_CREATE | SQLITE_OPEN_READWRITE | SQLITE_OPEN_FULLMUTEX,
            nil
        )
        sqlite3_exec(db, schemaSQL, nil, nil, nil)
        sqlite3_exec(db, "ALTER TABLE events ADD COLUMN cloud_sync_status TEXT NOT NULL DEFAULT 'pending';", nil, nil, nil)
        sqlite3_exec(db, "ALTER TABLE events ADD COLUMN cloud_retry_count INTEGER NOT NULL DEFAULT 0;", nil, nil, nil)
        sqlite3_exec(db, "ALTER TABLE events ADD COLUMN cloud_last_error TEXT;", nil, nil, nil)
        sqlite3_exec(db, "ALTER TABLE events ADD COLUMN cloud_synced_at TEXT;", nil, nil, nil)

        let sql = """
        UPDATE events
        SET sync_status = ?, updated_at = ?, last_error = COALESCE(last_error, 'Recovered interrupted sync')
        WHERE sync_status = ?
        """
        var statement: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK {
            defer { sqlite3_finalize(statement) }
            let failed = QuizLogSyncStatus.failed.rawValue as NSString
            let updatedAt = isoFormatter.string(from: Date()) as NSString
            let syncing = QuizLogSyncStatus.syncing.rawValue as NSString
            sqlite3_bind_text(statement, 1, failed.utf8String, -1, sqliteTransient)
            sqlite3_bind_text(statement, 2, updatedAt.utf8String, -1, sqliteTransient)
            sqlite3_bind_text(statement, 3, syncing.utf8String, -1, sqliteTransient)
            sqlite3_step(statement)
        }
    }

    deinit {
        if let db {
            sqlite3_close(db)
        }
    }

    func insert(event: QuizLogEvent) throws {
        let payloadData = try encoder.encode(event)
        let payloadJSON = String(decoding: payloadData, as: UTF8.self)
        let timestamp = isoFormatter.string(from: Date())

        let sql = """
        INSERT OR REPLACE INTO events (
            event_id, occurred_at, session_id, device_id, question_id, course_key, source_path,
            filter_mode, scope, event_type, selected_index, correct_index, result, app_version,
            build_number, metadata_json, payload_json, sync_status, retry_count, last_error,
            cloud_sync_status, cloud_retry_count, cloud_last_error, created_at, updated_at,
            synced_at, received_at, cloud_synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
        defer { sqlite3_finalize(statement) }

        let metadataJSON = String(decoding: try encoder.encode(event.metadata), as: UTF8.self)

        bindText(statement, index: 1, value: event.id)
        bindText(statement, index: 2, value: event.occurredAt)
        bindText(statement, index: 3, value: event.sessionID)
        bindText(statement, index: 4, value: event.deviceID)
        bindOptionalText(statement, index: 5, value: event.questionID)
        bindOptionalText(statement, index: 6, value: event.courseKey)
        bindOptionalText(statement, index: 7, value: event.sourcePath)
        bindOptionalText(statement, index: 8, value: event.filterMode)
        bindOptionalText(statement, index: 9, value: event.scope)
        bindText(statement, index: 10, value: event.eventType.rawValue)
        bindOptionalInt(statement, index: 11, value: event.selectedIndex)
        bindOptionalInt(statement, index: 12, value: event.correctIndex)
        bindOptionalText(statement, index: 13, value: event.result)
        bindText(statement, index: 14, value: event.appVersion)
        bindText(statement, index: 15, value: event.buildNumber)
        bindText(statement, index: 16, value: metadataJSON)
        bindText(statement, index: 17, value: payloadJSON)
        bindText(statement, index: 18, value: QuizLogSyncStatus.pending.rawValue)
        sqlite3_bind_int(statement, 19, 0)
        sqlite3_bind_null(statement, 20)
        bindText(statement, index: 21, value: QuizLogSyncStatus.pending.rawValue)
        sqlite3_bind_int(statement, 22, 0)
        sqlite3_bind_null(statement, 23)
        bindText(statement, index: 24, value: timestamp)
        bindText(statement, index: 25, value: timestamp)
        sqlite3_bind_null(statement, 26)
        sqlite3_bind_null(statement, 27)
        sqlite3_bind_null(statement, 28)

        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
    }

    func syncableEvents(limit: Int) throws -> [QuizLogEvent] {
        let sql = """
        SELECT payload_json
        FROM events
        WHERE sync_status IN (?, ?)
        ORDER BY occurred_at ASC
        LIMIT ?
        """

        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
        defer { sqlite3_finalize(statement) }

        bindText(statement, index: 1, value: QuizLogSyncStatus.pending.rawValue)
        bindText(statement, index: 2, value: QuizLogSyncStatus.failed.rawValue)
        sqlite3_bind_int(statement, 3, Int32(limit))

        var events: [QuizLogEvent] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            guard let payloadCString = sqlite3_column_text(statement, 0) else { continue }
            let payload = String(cString: payloadCString)
            let event = try decoder.decode(QuizLogEvent.self, from: Data(payload.utf8))
            events.append(event)
        }
        return events
    }

    func markSyncing(eventIDs: [String]) throws {
        try updateStatus(
            eventIDs: eventIDs,
            status: .syncing,
            lastError: nil,
            syncedAt: nil,
            receivedAt: nil,
            incrementRetryCount: false
        )
    }

    func markSynced(eventIDs: [String], receivedAt: String) throws {
        try updateStatus(
            eventIDs: eventIDs,
            status: .synced,
            lastError: nil,
            syncedAt: isoFormatter.string(from: Date()),
            receivedAt: receivedAt,
            incrementRetryCount: false
        )
    }

    func markFailed(eventIDs: [String], error: String) throws {
        try updateStatus(
            eventIDs: eventIDs,
            status: .failed,
            lastError: error,
            syncedAt: nil,
            receivedAt: nil,
            incrementRetryCount: true
        )
    }

    func snapshot() throws -> QuizLogSnapshot {
        QuizLogSnapshot(
            totalCount: try count(where: nil),
            pendingCount: try count(where: QuizLogSyncStatus.pending.rawValue),
            syncingCount: try count(where: QuizLogSyncStatus.syncing.rawValue),
            syncedCount: try count(where: QuizLogSyncStatus.synced.rawValue),
            failedCount: try count(where: QuizLogSyncStatus.failed.rawValue),
            lastSyncedAt: try scalarText("SELECT MAX(synced_at) FROM events WHERE synced_at IS NOT NULL"),
            cloudPendingCount: try count(where: QuizLogSyncStatus.pending.rawValue, field: "cloud_sync_status"),
            cloudSyncingCount: try count(where: QuizLogSyncStatus.syncing.rawValue, field: "cloud_sync_status"),
            cloudSyncedCount: try count(where: QuizLogSyncStatus.synced.rawValue, field: "cloud_sync_status"),
            cloudFailedCount: try count(where: QuizLogSyncStatus.failed.rawValue, field: "cloud_sync_status"),
            lastCloudSyncedAt: try scalarText("SELECT MAX(cloud_synced_at) FROM events WHERE cloud_synced_at IS NOT NULL"),
            lastError: try scalarText("SELECT last_error FROM events WHERE last_error IS NOT NULL ORDER BY updated_at DESC LIMIT 1")
        )
    }

    func recentEvents(limit: Int) throws -> [QuizLogEvent] {
        let sql = """
        SELECT payload_json
        FROM events
        ORDER BY occurred_at DESC
        LIMIT ?
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
        defer { sqlite3_finalize(statement) }

        sqlite3_bind_int(statement, 1, Int32(limit))

        var events: [QuizLogEvent] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            guard let payloadCString = sqlite3_column_text(statement, 0) else { continue }
            let payload = String(cString: payloadCString)
            let event = try decoder.decode(QuizLogEvent.self, from: Data(payload.utf8))
            events.append(event)
        }
        return events
    }

    func exportJSONL() throws -> URL {
        let events = try allEvents()
        let documents = try FileManager.default.url(
            for: .documentDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let filename = "quizprog-log-\(formatter.string(from: Date()).replacingOccurrences(of: ":", with: "-")).jsonl"
        let fileURL = documents.appendingPathComponent(filename)
        let lines = try events.map { event -> String in
            let data = try encoder.encode(event)
            return String(decoding: data, as: UTF8.self)
        }
        try lines.joined(separator: "\n").write(to: fileURL, atomically: true, encoding: .utf8)
        return fileURL
    }

    private func allEvents() throws -> [QuizLogEvent] {
        let sql = """
        SELECT payload_json
        FROM events
        ORDER BY occurred_at ASC
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
        defer { sqlite3_finalize(statement) }

        var events: [QuizLogEvent] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            guard let payloadCString = sqlite3_column_text(statement, 0) else { continue }
            let payload = String(cString: payloadCString)
            let event = try decoder.decode(QuizLogEvent.self, from: Data(payload.utf8))
            events.append(event)
        }
        return events
    }

    func cloudSyncableEvents(limit: Int) throws -> [QuizLogEvent] {
        let sql = """
        SELECT payload_json
        FROM events
        WHERE cloud_sync_status IN (?, ?)
        ORDER BY occurred_at ASC
        LIMIT ?
        """
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
        defer { sqlite3_finalize(statement) }

        bindText(statement, index: 1, value: QuizLogSyncStatus.pending.rawValue)
        bindText(statement, index: 2, value: QuizLogSyncStatus.failed.rawValue)
        sqlite3_bind_int(statement, 3, Int32(limit))

        var events: [QuizLogEvent] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            guard let payloadCString = sqlite3_column_text(statement, 0) else { continue }
            let payload = String(cString: payloadCString)
            let event = try decoder.decode(QuizLogEvent.self, from: Data(payload.utf8))
            events.append(event)
        }
        return events
    }

    func cloudPendingCount() throws -> Int {
        try count(where: QuizLogSyncStatus.pending.rawValue, field: "cloud_sync_status")
    }

    func markCloudSyncing(eventIDs: [String]) throws {
        try updateCloudStatus(
            eventIDs: eventIDs,
            status: .syncing,
            lastError: nil,
            syncedAt: nil,
            incrementRetryCount: false
        )
    }

    func markCloudSynced(eventIDs: [String], syncedAt: String) throws {
        try updateCloudStatus(
            eventIDs: eventIDs,
            status: .synced,
            lastError: nil,
            syncedAt: syncedAt,
            incrementRetryCount: false
        )
    }

    func markCloudFailed(eventIDs: [String], error: String) throws {
        try updateCloudStatus(
            eventIDs: eventIDs,
            status: .failed,
            lastError: error,
            syncedAt: nil,
            incrementRetryCount: true
        )
    }

    private func updateStatus(
        eventIDs: [String],
        status: QuizLogSyncStatus,
        lastError: String?,
        syncedAt: String?,
        receivedAt: String?,
        incrementRetryCount: Bool
    ) throws {
        guard !eventIDs.isEmpty else { return }
        let placeholders = Array(repeating: "?", count: eventIDs.count).joined(separator: ",")
        let sql = """
        UPDATE events
        SET sync_status = ?, last_error = ?, synced_at = ?, received_at = ?, updated_at = ?,
            retry_count = retry_count + ?
        WHERE event_id IN (\(placeholders))
        """

        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
        defer { sqlite3_finalize(statement) }

        var bindIndex: Int32 = 1
        bindText(statement, index: bindIndex, value: status.rawValue)
        bindIndex += 1
        bindOptionalText(statement, index: bindIndex, value: lastError)
        bindIndex += 1
        bindOptionalText(statement, index: bindIndex, value: syncedAt)
        bindIndex += 1
        bindOptionalText(statement, index: bindIndex, value: receivedAt)
        bindIndex += 1
        bindText(statement, index: bindIndex, value: isoFormatter.string(from: Date()))
        bindIndex += 1
        sqlite3_bind_int(statement, bindIndex, incrementRetryCount ? 1 : 0)
        bindIndex += 1

        for eventID in eventIDs {
            bindText(statement, index: bindIndex, value: eventID)
            bindIndex += 1
        }

        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
    }

    private func updateCloudStatus(
        eventIDs: [String],
        status: QuizLogSyncStatus,
        lastError: String?,
        syncedAt: String?,
        incrementRetryCount: Bool
    ) throws {
        guard !eventIDs.isEmpty else { return }
        let placeholders = Array(repeating: "?", count: eventIDs.count).joined(separator: ",")
        let sql = """
        UPDATE events
        SET cloud_sync_status = ?, cloud_last_error = ?, cloud_synced_at = ?, updated_at = ?,
            cloud_retry_count = cloud_retry_count + ?
        WHERE event_id IN (\(placeholders))
        """

        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
        defer { sqlite3_finalize(statement) }

        var bindIndex: Int32 = 1
        bindText(statement, index: bindIndex, value: status.rawValue)
        bindIndex += 1
        bindOptionalText(statement, index: bindIndex, value: lastError)
        bindIndex += 1
        bindOptionalText(statement, index: bindIndex, value: syncedAt)
        bindIndex += 1
        bindText(statement, index: bindIndex, value: isoFormatter.string(from: Date()))
        bindIndex += 1
        sqlite3_bind_int(statement, bindIndex, incrementRetryCount ? 1 : 0)
        bindIndex += 1

        for eventID in eventIDs {
            bindText(statement, index: bindIndex, value: eventID)
            bindIndex += 1
        }

        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
    }

    private func count(where status: String?, field: String = "sync_status") throws -> Int {
        let sql: String
        if status == nil {
            sql = "SELECT COUNT(*) FROM events"
        } else {
            sql = "SELECT COUNT(*) FROM events WHERE \(field) = ?"
        }
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
        defer { sqlite3_finalize(statement) }

        if let status {
            bindText(statement, index: 1, value: status)
        }

        guard sqlite3_step(statement) == SQLITE_ROW else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
        return Int(sqlite3_column_int64(statement, 0))
    }

    private func scalarText(_ sql: String) throws -> String? {
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw QuizLogStoreError.database(message: lastErrorMessage())
        }
        defer { sqlite3_finalize(statement) }

        guard sqlite3_step(statement) == SQLITE_ROW else { return nil }
        guard let cString = sqlite3_column_text(statement, 0) else { return nil }
        return String(cString: cString)
    }

    private func bindText(_ statement: OpaquePointer?, index: Int32, value: String) {
        let nsValue = value as NSString
        sqlite3_bind_text(statement, index, nsValue.utf8String, -1, sqliteTransient)
    }

    private func bindOptionalText(_ statement: OpaquePointer?, index: Int32, value: String?) {
        if let value {
            bindText(statement, index: index, value: value)
        } else {
            sqlite3_bind_null(statement, index)
        }
    }

    private func bindOptionalInt(_ statement: OpaquePointer?, index: Int32, value: Int?) {
        if let value {
            sqlite3_bind_int64(statement, index, sqlite3_int64(value))
        } else {
            sqlite3_bind_null(statement, index)
        }
    }

    private func lastErrorMessage() -> String {
        guard let error = sqlite3_errmsg(db) else {
            return "Unknown SQLite error"
        }
        return String(cString: error)
    }
}

private enum QuizLogStoreError: Error {
    case database(message: String)
}

private nonisolated(unsafe) let sqliteTransient = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

@MainActor
final class QuizLogController: ObservableObject {
    static let shared = QuizLogController()

    @Published private(set) var snapshot: QuizLogSnapshot = .empty
    @Published private(set) var recentEvents: [QuizLogEvent] = []
    @Published private(set) var lastExportURL: URL?
    @Published private(set) var isSyncInProgress = false

    @Published var serverURLString: String {
        didSet { persistConfiguration() }
    }

    @Published var apiKey: String {
        didSet { persistConfiguration() }
    }

    @Published var autoSyncEnabled: Bool {
        didSet { persistConfiguration() }
    }

    @Published var batchSize: Int {
        didSet {
            persistConfiguration()
        }
    }

    let deviceID: String

    private let configurationKey = "quizprog.log.configuration.v1"
    private let deviceIDKey = "quizprog.log.deviceID.v1"
    private let store = QuizLogStore()
    private let isoFormatter = ISO8601DateFormatter()

    private init() {
        let configuration: QuizLogConfiguration = Self.loadConfiguration(forKey: configurationKey)
            ?? QuizLogConfiguration()
        serverURLString = configuration.serverURLString
        apiKey = configuration.apiKey
        autoSyncEnabled = configuration.autoSyncEnabled
        batchSize = configuration.batchSize

        if let existing = UserDefaults.standard.string(forKey: deviceIDKey), !existing.isEmpty {
            deviceID = existing
        } else {
            let newID = UUID().uuidString
            UserDefaults.standard.set(newID, forKey: deviceIDKey)
            deviceID = newID
        }

        Task {
            await refresh()
        }
    }

    var dashboardURLString: String? {
        guard let baseURL = normalizedBaseURL() else { return nil }
        return baseURL.appendingPathComponent("dashboard").absoluteString
    }

    func handleSceneBecameActive() {
        Task {
            await refresh()
            if autoSyncEnabled {
                await syncNow()
            }
        }
    }

    func handleSceneMovedToBackground() {
        guard autoSyncEnabled else { return }
        Task {
            await syncNow()
        }
    }

    func refresh() async {
        do {
            snapshot = try await store.snapshot()
            recentEvents = try await store.recentEvents(limit: 8)
        } catch {
            snapshot.lastError = error.localizedDescription
        }
    }

    func exportEvents() async {
        do {
            lastExportURL = try await store.exportJSONL()
            await refresh()
        } catch {
            snapshot.lastError = error.localizedDescription
        }
    }

    func syncNow() async {
        guard !isSyncInProgress else { return }
        guard let endpointURL = endpointURL() else {
            snapshot.lastError = "Configure a valid sync endpoint first."
            return
        }

        isSyncInProgress = true
        defer { isSyncInProgress = false }
        var syncingEventIDs: [String] = []

        do {
            let events = try await store.syncableEvents(limit: max(1, min(batchSize, 250)))
            guard !events.isEmpty else {
                await refresh()
                return
            }

            let eventIDs = events.map(\.id)
            syncingEventIDs = eventIDs
            try await store.markSyncing(eventIDs: eventIDs)
            await refresh()

            var request = URLRequest(url: endpointURL)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            if !apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                request.setValue(apiKey.trimmingCharacters(in: .whitespacesAndNewlines), forHTTPHeaderField: "X-API-Key")
            }

            let payload = ["events": events]
            request.httpBody = try JSONEncoder().encode(payload)

            let (data, response) = try await URLSession.shared.data(for: request)
            guard
                let httpResponse = response as? HTTPURLResponse,
                200..<300 ~= httpResponse.statusCode
            else {
                let responseBody = String(data: data, encoding: .utf8) ?? "Unexpected server response"
                try await store.markFailed(eventIDs: eventIDs, error: responseBody)
                await refresh()
                return
            }

            let receivedAt = isoFormatter.string(from: Date())
            if let result = try? JSONDecoder().decode(QuizLogSyncResult.self, from: data),
               let accepted = result.accepted, accepted == 0 {
                try await store.markFailed(eventIDs: eventIDs, error: "Server accepted zero events")
            } else {
                try await store.markSynced(eventIDs: eventIDs, receivedAt: receivedAt)
            }
            await refresh()
        } catch {
            do {
                try await store.markFailed(eventIDs: syncingEventIDs, error: error.localizedDescription)
            } catch {}
            await refresh()
        }
    }

    func cloudPendingCount() async throws -> Int {
        try await store.cloudPendingCount()
    }

    func cloudSyncableEvents(limit: Int) async throws -> [QuizLogEvent] {
        try await store.cloudSyncableEvents(limit: limit)
    }

    func markCloudSyncing(eventIDs: [String]) async throws {
        try await store.markCloudSyncing(eventIDs: eventIDs)
        await refresh()
    }

    func markCloudSynced(eventIDs: [String], at timestamp: String) async throws {
        try await store.markCloudSynced(eventIDs: eventIDs, syncedAt: timestamp)
        await refresh()
    }

    func markCloudFailed(eventIDs: [String], error: String) async throws {
        try await store.markCloudFailed(eventIDs: eventIDs, error: error)
        await refresh()
    }

    func recordQuizStarted(
        sessionID: String,
        mode: QuizFilterMode,
        scope: QuizScope,
        totalQuestions: Int
    ) {
        record(
            eventType: .quizStarted,
            sessionID: sessionID,
            filterMode: mode,
            scope: scope,
            metadata: ["total_questions": String(totalQuestions)]
        )
    }

    func recordQuizResumed(
        sessionID: String,
        mode: QuizFilterMode,
        scope: QuizScope,
        currentIndex: Int,
        totalQuestions: Int
    ) {
        record(
            eventType: .quizResumed,
            sessionID: sessionID,
            filterMode: mode,
            scope: scope,
            metadata: [
                "current_index": String(currentIndex),
                "total_questions": String(totalQuestions)
            ]
        )
    }

    func recordQuestionAnswered(
        sessionID: String,
        question: QuizQuestion,
        selectedIndex: Int,
        result: QuizQuestionResult,
        mode: QuizFilterMode,
        scope: QuizScope
    ) {
        record(
            eventType: .questionAnswered,
            sessionID: sessionID,
            question: question,
            selectedIndex: selectedIndex,
            correctIndex: question.correctIndex,
            result: result,
            filterMode: mode,
            scope: scope,
            metadata: ["selected_answer": question.options[selectedIndex]]
        )
    }

    func recordQuestionSkipped(
        sessionID: String,
        question: QuizQuestion,
        mode: QuizFilterMode,
        scope: QuizScope
    ) {
        record(
            eventType: .questionSkipped,
            sessionID: sessionID,
            question: question,
            correctIndex: question.correctIndex,
            result: .skipped,
            filterMode: mode,
            scope: scope
        )
    }

    func recordQuizExited(
        sessionID: String,
        mode: QuizFilterMode,
        scope: QuizScope,
        currentIndex: Int,
        score: Int,
        totalQuestions: Int
    ) {
        record(
            eventType: .quizExited,
            sessionID: sessionID,
            filterMode: mode,
            scope: scope,
            metadata: [
                "current_index": String(currentIndex),
                "score": String(score),
                "total_questions": String(totalQuestions)
            ]
        )
    }

    func recordQuizFinished(
        sessionID: String,
        mode: QuizFilterMode,
        scope: QuizScope,
        score: Int,
        totalQuestions: Int
    ) {
        record(
            eventType: .quizFinished,
            sessionID: sessionID,
            filterMode: mode,
            scope: scope,
            metadata: [
                "score": String(score),
                "total_questions": String(totalQuestions)
            ]
        )
    }

    private func record(
        eventType: QuizLogEventType,
        sessionID: String,
        question: QuizQuestion? = nil,
        selectedIndex: Int? = nil,
        correctIndex: Int? = nil,
        result: QuizQuestionResult? = nil,
        filterMode: QuizFilterMode? = nil,
        scope: QuizScope? = nil,
        metadata: [String: String] = [:]
    ) {
        let event = QuizLogEvent(
            id: UUID().uuidString,
            occurredAt: isoFormatter.string(from: Date()),
            sessionID: sessionID,
            deviceID: deviceID,
            questionID: question?.id,
            courseKey: question?.courseKey,
            sourcePath: question?.sourcePath,
            filterMode: filterMode?.rawValue,
            scope: scope?.logDescription,
            eventType: eventType,
            selectedIndex: selectedIndex,
            correctIndex: correctIndex,
            result: result?.rawValue,
            appVersion: appVersion,
            buildNumber: buildNumber,
            metadata: metadata
        )

        Task {
            do {
                try await store.insert(event: event)
                await refresh()
                if autoSyncEnabled {
                    await syncNow()
                }
            } catch {
                snapshot.lastError = error.localizedDescription
            }
        }
    }

    private var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
    }

    private var buildNumber: String {
        Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1"
    }

    private func endpointURL() -> URL? {
        guard let baseURL = normalizedBaseURL() else { return nil }
        return baseURL.appendingPathComponent("events").appendingPathComponent("batch")
    }

    private func normalizedBaseURL() -> URL? {
        let trimmed = serverURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        return URL(string: trimmed)
    }

    private func persistConfiguration() {
        let configuration = QuizLogConfiguration(
            serverURLString: serverURLString,
            apiKey: apiKey,
            autoSyncEnabled: autoSyncEnabled,
            batchSize: max(1, min(batchSize, 250))
        )
        if let data = try? JSONEncoder().encode(configuration) {
            UserDefaults.standard.set(data, forKey: configurationKey)
        }
    }

    private static func loadConfiguration(forKey key: String) -> QuizLogConfiguration? {
        guard let data = UserDefaults.standard.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(QuizLogConfiguration.self, from: data)
    }
}

private extension QuizScope {
    var logDescription: String {
        switch self {
        case .repository:
            return "repository"
        case .file(let sourcePath):
            return "file:\(sourcePath)"
        case .tag(let tag):
            return "tag:\(tag)"
        }
    }
}
