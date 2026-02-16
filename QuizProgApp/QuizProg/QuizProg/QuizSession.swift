import Foundation
import Combine
import CryptoKit

struct QuizQuestion: Identifiable, Hashable {
    let id: String
    let category: String
    let prompt: String
    let options: [String]
    let correctIndex: Int
    let explanation: String
    let courseKey: String
    let sectionName: String
    let sourcePath: String
    let sourceFileName: String
    let tags: [String]

    init(
        id: String = UUID().uuidString,
        category: String,
        prompt: String,
        options: [String],
        correctIndex: Int,
        explanation: String,
        courseKey: String = "sample-course",
        sectionName: String = "(No subfolder)",
        sourcePath: String = "",
        sourceFileName: String = "",
        tags: [String] = []
    ) {
        self.id = id
        self.category = category
        self.prompt = prompt
        self.options = options
        self.correctIndex = correctIndex
        self.explanation = explanation
        self.courseKey = courseKey
        self.sectionName = sectionName
        self.sourcePath = sourcePath
        self.sourceFileName = sourceFileName
        self.tags = tags
    }

    static let sampleDeck: [QuizQuestion] = [
        QuizQuestion(
            id: "sample-1",
            category: "Swift",
            prompt: "What does the `@State` property wrapper do in SwiftUI?",
            options: [
                "Stores local mutable state owned by a view",
                "Creates a background thread",
                "Fetches data from a remote API",
                "Turns a struct into a class"
            ],
            correctIndex: 0,
            explanation: "`@State` is used for view-local source-of-truth values that trigger a UI refresh when changed."
        ),
        QuizQuestion(
            id: "sample-2",
            category: "Web",
            prompt: "Which HTTP status code means a resource was not found?",
            options: ["200", "301", "404", "500"],
            correctIndex: 2,
            explanation: "Status code 404 is returned when the requested resource cannot be found."
        ),
        QuizQuestion(
            id: "sample-3",
            category: "Algorithms",
            prompt: "What is the time complexity of binary search on a sorted array?",
            options: ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
            correctIndex: 1,
            explanation: "Binary search halves the search interval each step, giving logarithmic complexity."
        ),
        QuizQuestion(
            id: "sample-4",
            category: "Databases",
            prompt: "Which SQL clause is used to filter rows before grouping?",
            options: ["HAVING", "ORDER BY", "WHERE", "LIMIT"],
            correctIndex: 2,
            explanation: "`WHERE` filters individual rows before aggregation, while `HAVING` filters grouped results."
        ),
        QuizQuestion(
            id: "sample-5",
            category: "Architecture",
            prompt: "In MVC, which layer should contain UI rendering logic?",
            options: ["Model", "Controller", "View", "Router"],
            correctIndex: 2,
            explanation: "The View layer is responsible for presenting data and rendering UI."
        )
    ]
}

struct QuizCourse: Identifiable, Hashable {
    let id: String
    let title: String
    let questions: [QuizQuestion]
}

struct QuizOutcome: Identifiable {
    let id = UUID()
    let question: QuizQuestion
    let selectedIndex: Int

    var isCorrect: Bool {
        selectedIndex == question.correctIndex
    }
}

struct QuizCourseStats: Codable, Hashable {
    var plays: Int = 0
    var answered: Int = 0
    var correct: Int = 0

    var accuracyPercent: Int {
        guard answered > 0 else { return 0 }
        return Int((Double(correct) / Double(answered) * 100.0).rounded())
    }
}

enum QuizFilterMode: String, Codable, CaseIterable, Identifiable {
    case due
    case all
    case unanswered
    case wrong
    case skipped
    case wrongOrSkipped

    var id: String { rawValue }

    var title: String {
        switch self {
        case .due: return "Programmate per oggi"
        case .all: return "Tutte le domande"
        case .unanswered: return "Non risposte"
        case .wrong: return "Fallite"
        case .skipped: return "Saltate"
        case .wrongOrSkipped: return "Fallite o saltate"
        }
    }
}

enum QuizScope: Codable, Hashable {
    case repository
    case file(String)
    case tag(String)
}

struct QuizFileInfo: Identifiable, Hashable {
    let id: String
    let sourcePath: String
    let fileName: String
    let courseKey: String
    let courseTitle: String
    let sectionName: String
    let questionCount: Int
}

struct QuizScopeStats: Hashable {
    let total: Int
    let never: Int
    let skipped: Int
    let wrong: Int
    let correct: Int
    let due: Int
}

struct QuizFileSummaryItem: Identifiable, Hashable {
    let id: String
    let info: QuizFileInfo
    let stats: QuizScopeStats
}

struct QuizCourseSummaryItem: Identifiable, Hashable {
    let id: String
    let courseKey: String
    let courseTitle: String
    let totalQuestions: Int
    let stats: QuizScopeStats
}

private enum QuizBundleLoader {
    private struct QuizFile: Decodable {
        let disabled: Bool?
        let fileName: String?
        let questions: [QuizEntry]

        private enum CodingKeys: String, CodingKey {
            case disabled
            case fileName = "file_name"
            case questions
        }
    }

    private struct QuizEntry: Decodable {
        let question: String
        let answers: [QuizAnswer]
        let explanation: String?
        let tags: [String]?
    }

    private struct QuizAnswer: Decodable {
        let text: String
        let correct: Bool
    }

    static func loadCourses() -> [QuizCourse] {
        guard let rootURL = Bundle.main.resourceURL else {
            return []
        }

        let quizDataURL = rootURL.appendingPathComponent("quiz_data", isDirectory: true)
        let usesNestedLayout = FileManager.default.fileExists(atPath: quizDataURL.path)
        let sortedURLs: [URL]
        if usesNestedLayout {
            sortedURLs = jsonFilesRecursively(in: quizDataURL)
        } else {
            sortedURLs = Bundle.main.urls(forResourcesWithExtension: "json", subdirectory: nil) ?? []
        }

        guard !sortedURLs.isEmpty else { return [] }

        let orderedURLs = sortedURLs
            .sorted { $0.path < $1.path }
        var groupedQuestions: [String: [QuizQuestion]] = [:]
        var courseTitles: [String: String] = [:]

        for url in orderedURLs {
            let filename = url.lastPathComponent
            if filename.hasPrefix(".") || filename == "exam_dates.json" {
                continue
            }

            guard
                let data = try? Data(contentsOf: url),
                let file = try? JSONDecoder().decode(QuizFile.self, from: data),
                file.disabled != true
            else {
                continue
            }

            let relativePath: String
            if usesNestedLayout {
                relativePath = url.path.replacingOccurrences(of: quizDataURL.path + "/", with: "")
            } else {
                relativePath = url.lastPathComponent
            }

            let parts = relativePath.split(separator: "/").map(String.init)
            let fallbackTitle = url.deletingPathExtension().lastPathComponent
            let fileTitle = file.fileName?.trimmingCharacters(in: .whitespacesAndNewlines)
            let sourceFileName = (fileTitle?.isEmpty == false) ? fileTitle! : filename

            let rawCourseName: String
            if usesNestedLayout, let first = parts.first, parts.count > 1 {
                rawCourseName = first
            } else if let fileTitle, !fileTitle.isEmpty {
                rawCourseName = fileTitle
            } else {
                rawCourseName = fallbackTitle
            }

            let sectionName: String
            if usesNestedLayout, parts.count > 2 {
                sectionName = normalizedSectionTitle(parts[1])
            } else {
                sectionName = "(No subfolder)"
            }

            let courseTitle = normalizedCourseTitle(rawCourseName)
            let courseID = stableHash("course|\(rawCourseName)")
            courseTitles[courseID] = courseTitle

            let questions: [QuizQuestion] = file.questions.enumerated().compactMap { index, entry in
                let prompt = entry.question.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !prompt.isEmpty else { return nil }

                guard
                    entry.answers.count >= 2,
                    let correctIndex = entry.answers.firstIndex(where: { $0.correct })
                else {
                    return nil
                }

                let options = entry.answers.map {
                    $0.text.trimmingCharacters(in: .whitespacesAndNewlines)
                }
                guard options.allSatisfy({ !$0.isEmpty }) else { return nil }

                let cleanedExplanation = entry.explanation?.trimmingCharacters(in: .whitespacesAndNewlines)
                let explanation = (cleanedExplanation?.isEmpty == false)
                    ? cleanedExplanation!
                    : "No explanation provided."
                let tags = (entry.tags ?? [])
                    .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                    .filter { !$0.isEmpty }

                let fingerprint = [relativePath, String(index), prompt, options.joined(separator: "||"), String(correctIndex)]
                    .joined(separator: "|")
                let questionID = stableHash("\(courseID)|\(fingerprint)")

                return QuizQuestion(
                    id: questionID,
                    category: courseTitle,
                    prompt: prompt,
                    options: options,
                    correctIndex: correctIndex,
                    explanation: explanation,
                    courseKey: rawCourseName,
                    sectionName: sectionName,
                    sourcePath: relativePath,
                    sourceFileName: sourceFileName,
                    tags: tags
                )
            }

            if !questions.isEmpty {
                groupedQuestions[courseID, default: []].append(contentsOf: questions)
            }
        }

        return groupedQuestions
            .map { courseID, questions in
                QuizCourse(
                    id: courseID,
                    title: courseTitles[courseID] ?? "Course",
                    questions: questions
                )
            }
            .sorted { $0.title < $1.title }
    }

    private static func stableHash(_ text: String) -> String {
        let digest = SHA256.hash(data: Data(text.utf8))
        return digest.map { String(format: "%02x", $0) }.joined()
    }

    private static func prettyTitle(from rawFolderName: String) -> String {
        let withoutPrefix = rawFolderName.replacingOccurrences(
            of: #"^\d+[_\-\s]*"#,
            with: "",
            options: .regularExpression
        )
        return withoutPrefix
            .replacingOccurrences(of: "_", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func normalizedCourseTitle(_ rawName: String) -> String {
        let trimmed = rawName.trimmingCharacters(in: .whitespacesAndNewlines)
        let withoutExtension = URL(fileURLWithPath: trimmed).deletingPathExtension().lastPathComponent
        let titleSource = withoutExtension.isEmpty ? trimmed : withoutExtension
        return prettyTitle(from: titleSource)
    }

    private static func normalizedSectionTitle(_ rawName: String) -> String {
        prettyTitle(from: rawName)
    }

    static func loadExamDates() -> [String: String] {
        guard let rootURL = Bundle.main.resourceURL else { return [:] }
        let quizDataURL = rootURL.appendingPathComponent("quiz_data", isDirectory: true)
        let nestedPath = quizDataURL.appendingPathComponent("exam_dates.json")
        let fileURL: URL
        if FileManager.default.fileExists(atPath: nestedPath.path) {
            fileURL = nestedPath
        } else {
            fileURL = rootURL.appendingPathComponent("exam_dates.json")
        }

        guard
            let data = try? Data(contentsOf: fileURL),
            let value = try? JSONDecoder().decode([String: String].self, from: data)
        else {
            return [:]
        }
        return value
    }

    private static func jsonFilesRecursively(in directoryURL: URL) -> [URL] {
        guard let enumerator = FileManager.default.enumerator(
            at: directoryURL,
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        var files: [URL] = []
        for case let url as URL in enumerator {
            guard url.pathExtension.lowercased() == "json" else { continue }
            files.append(url)
        }
        return files
    }
}

private struct QuizPersistedSettings: Codable {
    let selectedCourseID: String
    let questionLimit: Int
    let shuffleQuestions: Bool
    let wrongAnswersOnly: Bool
}

private struct QuizQuestionPerformance: Codable {
    var history: [String] = []
    var ease: Double = 2.5
    var interval: Int = 0
    var repetition: Int = 0
    var nextReview: String?
}

private enum QuizQuestionResult: String {
    case correct
    case wrong
    case skipped
}

private struct QuizOutcomeSnapshot: Codable {
    let questionID: String
    let selectedIndex: Int
}

private struct QuizProgressSnapshot: Codable {
    let courseID: String
    let questionIDs: [String]
    let currentIndex: Int
    let score: Int
    let selectedIndex: Int?
    let didSubmit: Bool
    let outcomes: [QuizOutcomeSnapshot]
    let settings: QuizPersistedSettings
}

@MainActor
final class QuizSession: ObservableObject {
    private let settingsKey = "quizprog.settings.v1"
    private let bestScoresKey = "quizprog.bestScores.v1"
    private let courseStatsKey = "quizprog.courseStats.v1"
    private let wrongIDsKey = "quizprog.wrongQuestionIDs.v1"
    private let progressKey = "quizprog.progress.v1"
    private let performanceKey = "quizprog.performanceByQuestion.v1"

    private let coursesByID: [String: QuizCourse]
    private let courseIDByCourseKey: [String: String]
    private let allQuestions: [QuizQuestion]
    private let questionsByID: [String: QuizQuestion]
    private let orderedFileInfos: [QuizFileInfo]
    private let examDatesByCourseKey: [String: String]

    private var bestScoresByCourse: [String: Int]
    private var statsByCourse: [String: QuizCourseStats]
    private var wrongQuestionIDsByCourse: [String: Set<String>]
    private var performanceByQuestionID: [String: QuizQuestionPerformance]
    private var progressSnapshot: QuizProgressSnapshot?
    private var activeScope: QuizScope = .repository

    @Published private(set) var courses: [QuizCourse]
    @Published private(set) var questions: [QuizQuestion] = []
    @Published private(set) var currentIndex = 0
    @Published private(set) var score = 0
    @Published private(set) var hasStarted = false
    @Published private(set) var isFinished = false
    @Published var selectedIndex: Int?
    @Published private(set) var didSubmit = false
    @Published private(set) var outcomes: [QuizOutcome] = []
    @Published private(set) var bestScore = 0
    @Published private(set) var selectedCourseStats = QuizCourseStats()
    @Published private(set) var hasResumableSession = false
    @Published private(set) var availableQuestionCount = 0
    @Published private(set) var activeFilterMode: QuizFilterMode = .all
    @Published private(set) var activeScopeLabel = "Tutte le domande"

    @Published var selectedCourseID: String {
        didSet {
            guard oldValue != selectedCourseID else { return }
            handleSetupChange()
        }
    }

    @Published var questionLimit: Int {
        didSet {
            guard oldValue != questionLimit else { return }
            handleSetupChange()
        }
    }

    @Published var shuffleQuestions: Bool {
        didSet {
            guard oldValue != shuffleQuestions else { return }
            persistSettings()
        }
    }

    @Published var wrongAnswersOnly: Bool {
        didSet {
            guard oldValue != wrongAnswersOnly else { return }
            handleSetupChange()
        }
    }

    init(courses: [QuizCourse]? = nil) {
        let inputCourses = courses ?? QuizBundleLoader.loadCourses()
        let loadedCourses: [QuizCourse]
        if inputCourses.isEmpty {
            loadedCourses = [
                QuizCourse(id: "sample-course", title: "Sample Course", questions: QuizQuestion.sampleDeck)
            ]
        } else {
            loadedCourses = inputCourses
        }

        coursesByID = Dictionary(uniqueKeysWithValues: loadedCourses.map { ($0.id, $0) })
        courseIDByCourseKey = Dictionary(
            uniqueKeysWithValues: loadedCourses.compactMap { course in
                guard let key = course.questions.first?.courseKey else { return nil }
                return (key, course.id)
            }
        )
        allQuestions = loadedCourses.flatMap(\.questions)
        questionsByID = Dictionary(uniqueKeysWithValues: allQuestions.map { ($0.id, $0) })
        orderedFileInfos = Self.buildFileInfos(from: allQuestions)
        examDatesByCourseKey = QuizBundleLoader.loadExamDates()
        self.courses = loadedCourses

        bestScoresByCourse = Self.loadValue(forKey: bestScoresKey) ?? [:]
        statsByCourse = Self.loadValue(forKey: courseStatsKey) ?? [:]
        let wrongArrays: [String: [String]] = Self.loadValue(forKey: wrongIDsKey) ?? [:]
        wrongQuestionIDsByCourse = wrongArrays.mapValues { Set($0) }
        let loadedPerformance: [String: QuizQuestionPerformance] = Self.loadValue(forKey: performanceKey) ?? [:]
        performanceByQuestionID = loadedPerformance

        let persistedSettings: QuizPersistedSettings? = Self.loadValue(forKey: settingsKey)
        let initialCourseID: String
        if let savedCourseID = persistedSettings?.selectedCourseID, coursesByID[savedCourseID] != nil {
            initialCourseID = savedCourseID
        } else {
            initialCourseID = loadedCourses[0].id
        }

        selectedCourseID = initialCourseID
        shuffleQuestions = persistedSettings?.shuffleQuestions ?? true
        wrongAnswersOnly = false
        questionLimit = max(0, persistedSettings?.questionLimit ?? 0)
        activeFilterMode = .all
        activeScope = .repository
        activeScopeLabel = QuizFilterMode.all.title

        clampQuestionLimit()
        refreshCourseMetrics()
        prepareRound(shuffle: shuffleQuestions)
        persistSettings()

        if let snapshot: QuizProgressSnapshot = Self.loadValue(forKey: progressKey),
           canRestore(snapshot: snapshot) {
            progressSnapshot = snapshot
            hasResumableSession = true
        } else {
            progressSnapshot = nil
            hasResumableSession = false
            clearProgressSnapshot()
        }
    }

    var selectedCourseTitle: String {
        selectedCourse?.title ?? "Quiz"
    }

    var selectedCourseQuestionCount: Int {
        selectedCourse?.questions.count ?? 0
    }

    var totalQuestions: Int {
        questions.count
    }

    var plannedQuestionCount: Int {
        guard availableQuestionCount > 0 else { return 0 }
        if questionLimit == 0 {
            return availableQuestionCount
        }
        return min(max(1, questionLimit), availableQuestionCount)
    }

    var maxQuestionLimit: Int {
        max(1, availableQuestionCount)
    }

    var currentQuestion: QuizQuestion {
        questions[currentIndex]
    }

    var scorePercent: Int {
        guard totalQuestions > 0 else { return 0 }
        let percentage = Double(score) / Double(totalQuestions) * 100.0
        return Int(percentage.rounded())
    }

    var canSubmit: Bool {
        selectedIndex != nil && !didSubmit
    }

    var totalRepositoryQuestionCount: Int {
        allQuestions.count
    }

    var fileCourseKeys: [String] {
        let grouped = Dictionary(grouping: orderedFileInfos, by: \.courseKey)
        return grouped.keys.sorted {
            courseTitle(forCourseKey: $0).localizedCaseInsensitiveCompare(courseTitle(forCourseKey: $1)) == .orderedAscending
        }
    }

    var allFileInfos: [QuizFileInfo] {
        orderedFileInfos
    }

    var tagNames: [String] {
        Set(allQuestions.flatMap(\.tags))
            .sorted { $0.localizedCaseInsensitiveCompare($1) == .orderedAscending }
    }

    func courseTitle(forCourseKey key: String) -> String {
        orderedFileInfos.first(where: { $0.courseKey == key })?.courseTitle ?? key
    }

    func sectionNames(forCourseKey key: String) -> [String] {
        let names = Set(
            orderedFileInfos
                .filter { $0.courseKey == key }
                .map(\.sectionName)
        )
        return names.sorted { $0.localizedCaseInsensitiveCompare($1) == .orderedAscending }
    }

    func files(forCourseKey key: String, sectionName: String) -> [QuizFileInfo] {
        orderedFileInfos
            .filter { $0.courseKey == key && $0.sectionName == sectionName }
            .sorted { $0.fileName.localizedCaseInsensitiveCompare($1.fileName) == .orderedAscending }
    }

    func startMenuQuiz(mode: QuizFilterMode, scope: QuizScope) -> Bool {
        activeFilterMode = mode
        activeScope = scope
        activeScopeLabel = scopeLabel(for: scope)
        wrongAnswersOnly = false
        clearProgressSnapshot()
        prepareRound(shuffle: shuffleQuestions)
        guard !questions.isEmpty else { return false }
        hasStarted = true
        saveProgressSnapshot()
        return true
    }

    func fileSummaryItems() -> [QuizFileSummaryItem] {
        orderedFileInfos.map { info in
            let fileQuestions = allQuestions.filter { $0.sourcePath == info.sourcePath }
            return QuizFileSummaryItem(
                id: info.id,
                info: info,
                stats: stats(for: fileQuestions)
            )
        }
    }

    func courseSummaryItems() -> [QuizCourseSummaryItem] {
        fileCourseKeys.map { courseKey in
            let courseQuestions = allQuestions.filter { $0.courseKey == courseKey }
            return QuizCourseSummaryItem(
                id: courseKey,
                courseKey: courseKey,
                courseTitle: courseTitle(forCourseKey: courseKey),
                totalQuestions: courseQuestions.count,
                stats: stats(for: courseQuestions)
            )
        }
    }

    func repositoryStats() -> QuizScopeStats {
        stats(for: allQuestions)
    }

    func courseStats(forCourseKey key: String) -> QuizScopeStats {
        stats(for: allQuestions.filter { $0.courseKey == key })
    }

    func fileStats(forSourcePath path: String) -> QuizScopeStats {
        stats(for: allQuestions.filter { $0.sourcePath == path })
    }

    func start() {
        if hasResumableSession {
            resumeSavedSession()
        } else {
            startNewQuiz()
        }
    }

    func startNewQuiz() {
        clearProgressSnapshot()
        prepareRound(shuffle: shuffleQuestions)
        guard !questions.isEmpty else { return }
        hasStarted = true
        saveProgressSnapshot()
    }

    func resumeSavedSession() {
        guard let snapshot = progressSnapshot, canRestore(snapshot: snapshot) else {
            startNewQuiz()
            return
        }

        selectedCourseID = snapshot.settings.selectedCourseID
        wrongAnswersOnly = false
        shuffleQuestions = snapshot.settings.shuffleQuestions
        questionLimit = max(0, snapshot.settings.questionLimit)
        clampQuestionLimit()
        persistSettings()
        let restoredQuestions = snapshot.questionIDs.compactMap { questionsByID[$0] }
        guard !restoredQuestions.isEmpty else {
            startNewQuiz()
            return
        }

        questions = restoredQuestions
        currentIndex = min(max(0, snapshot.currentIndex), restoredQuestions.count - 1)
        score = min(max(0, snapshot.score), restoredQuestions.count)
        didSubmit = snapshot.didSubmit
        selectedIndex = snapshot.selectedIndex.flatMap { index in
            guard restoredQuestions[currentIndex].options.indices.contains(index) else { return nil }
            return index
        }
        outcomes = snapshot.outcomes.compactMap { item in
            guard
                let question = questionsByID[item.questionID],
                question.options.indices.contains(item.selectedIndex)
            else {
                return nil
            }
            return QuizOutcome(question: question, selectedIndex: item.selectedIndex)
        }

        hasStarted = true
        isFinished = false
        hasResumableSession = true
        refreshCourseMetrics()
        saveProgressSnapshot()
    }

    func exitAndSave() {
        guard hasStarted, !isFinished else { return }
        saveProgressSnapshot()
        hasStarted = false
    }

    func selectOption(_ index: Int) {
        guard hasStarted, !didSubmit else { return }
        selectedIndex = index
    }

    func submitCurrentAnswer() {
        guard hasStarted, !didSubmit, let selectedIndex else { return }

        didSubmit = true
        let outcome = QuizOutcome(question: currentQuestion, selectedIndex: selectedIndex)
        outcomes.append(outcome)

        if outcome.isCorrect {
            score += 1
        }

        updateWrongQuestionSet(with: outcome)
        updateQuestionPerformance(for: currentQuestion, result: outcome.isCorrect ? .correct : .wrong)
        saveProgressSnapshot()
    }

    func skipCurrentQuestion() {
        guard hasStarted, !didSubmit else { return }
        didSubmit = true
        selectedIndex = nil
        updateQuestionPerformance(for: currentQuestion, result: .skipped)
        saveProgressSnapshot()
    }

    func goToNextQuestion() {
        guard didSubmit else { return }

        if currentIndex + 1 < totalQuestions {
            currentIndex += 1
            selectedIndex = nil
            didSubmit = false
            saveProgressSnapshot()
            return
        }

        finishQuiz()
    }

    func restart() {
        clearProgressSnapshot()
        prepareRound(shuffle: shuffleQuestions)
        guard !questions.isEmpty else { return }
        hasStarted = true
        saveProgressSnapshot()
    }

    func backToHome() {
        clearProgressSnapshot()
        prepareRound(shuffle: shuffleQuestions)
        hasStarted = false
    }

    func resetWrongAnswersForSelectedCourse() {
        wrongQuestionIDsByCourse[selectedCourseID] = []
        saveWrongQuestionIDs()
        prepareRound(shuffle: shuffleQuestions)
    }

    private var selectedCourse: QuizCourse? {
        coursesByID[selectedCourseID]
    }

    private func handleSetupChange() {
        refreshCourseMetrics()
        prepareRound(shuffle: shuffleQuestions)
        persistSettings()
    }

    private func refreshCourseMetrics() {
        bestScore = bestScoresByCourse[selectedCourseID] ?? 0
        selectedCourseStats = statsByCourse[selectedCourseID] ?? QuizCourseStats()
    }

    private func scopeLabel(for scope: QuizScope) -> String {
        switch scope {
        case .repository:
            return "Tutte le domande"
        case .file(let sourcePath):
            let fileName = orderedFileInfos.first(where: { $0.sourcePath == sourcePath })?.fileName ?? sourcePath
            return "File: \(fileName)"
        case .tag(let tag):
            return "Tag: \(tag)"
        }
    }

    private func questionPool(scope: QuizScope, mode: QuizFilterMode) -> [QuizQuestion] {
        let scopedQuestions = questions(in: scope)
        guard !scopedQuestions.isEmpty else { return [] }

        switch mode {
        case .all:
            return scopedQuestions
        case .unanswered:
            return scopedQuestions.filter { performance(for: $0).history.isEmpty }
        case .wrong:
            return scopedQuestions.filter { performance(for: $0).history.last == QuizQuestionResult.wrong.rawValue }
        case .skipped:
            return scopedQuestions.filter { performance(for: $0).history.last == QuizQuestionResult.skipped.rawValue }
        case .wrongOrSkipped:
            let filtered = scopedQuestions.filter {
                guard let last = performance(for: $0).history.last else { return false }
                return last == QuizQuestionResult.wrong.rawValue || last == QuizQuestionResult.skipped.rawValue
            }
            return filtered.sorted { lhs, rhs in
                performance(for: lhs).history.filter { $0 == QuizQuestionResult.wrong.rawValue }.count
                    > performance(for: rhs).history.filter { $0 == QuizQuestionResult.wrong.rawValue }.count
            }
        case .due:
            return scopedQuestions.filter(isDue)
        }
    }

    private func questions(in scope: QuizScope) -> [QuizQuestion] {
        switch scope {
        case .repository:
            return allQuestions
        case .file(let sourcePath):
            return allQuestions.filter { $0.sourcePath == sourcePath }
        case .tag(let tag):
            return allQuestions.filter { $0.tags.contains(tag) }
        }
    }

    private func stats(for questions: [QuizQuestion]) -> QuizScopeStats {
        guard !questions.isEmpty else {
            return QuizScopeStats(total: 0, never: 0, skipped: 0, wrong: 0, correct: 0, due: 0)
        }

        var never = 0
        var skipped = 0
        var wrong = 0
        var correct = 0
        var due = 0

        for question in questions {
            let entry = performance(for: question)
            let history = entry.history
            if history.isEmpty {
                never += 1
            } else {
                switch history.last {
                case QuizQuestionResult.skipped.rawValue:
                    skipped += 1
                case QuizQuestionResult.wrong.rawValue:
                    wrong += 1
                case QuizQuestionResult.correct.rawValue:
                    correct += 1
                default:
                    break
                }
            }

            if isDue(question) {
                due += 1
            }
        }

        return QuizScopeStats(
            total: questions.count,
            never: never,
            skipped: skipped,
            wrong: wrong,
            correct: correct,
            due: due
        )
    }

    private func performance(for question: QuizQuestion) -> QuizQuestionPerformance {
        performanceByQuestionID[question.id] ?? QuizQuestionPerformance()
    }

    private func isDue(_ question: QuizQuestion) -> Bool {
        let entry = performance(for: question)
        guard
            let nextReview = entry.nextReview,
            let date = Self.isoDateFormatter.date(from: nextReview)
        else {
            return true
        }
        return Calendar.current.compare(date, to: effectiveToday(), toGranularity: .day) != .orderedDescending
    }

    private func effectiveToday() -> Date {
        let now = Date()
        let calendar = Calendar.current
        let dayStart = calendar.startOfDay(for: now)
        let cutoff = calendar.date(
            bySettingHour: 5,
            minute: 30,
            second: 0,
            of: dayStart
        ) ?? dayStart
        if now < cutoff {
            return calendar.date(byAdding: .day, value: -1, to: dayStart) ?? dayStart
        }
        return dayStart
    }

    private func updateQuestionPerformance(for question: QuizQuestion, result: QuizQuestionResult) {
        var entry = performance(for: question)
        let quality = result == .correct ? 5 : 0
        let today = effectiveToday()
        entry.history.append(result.rawValue)

        if quality >= 3 {
            entry.repetition += 1
            if entry.repetition == 1 {
                entry.interval = 1
            } else if entry.repetition == 2 {
                entry.interval = 3
            } else {
                entry.interval = max(1, Int((Double(entry.interval) * entry.ease).rounded()))
            }
        } else {
            entry.repetition = 0
            entry.interval = 1
        }

        let penalty = Double(5 - quality)
        entry.ease = max(1.3, entry.ease + (0.1 - penalty * (0.08 + penalty * 0.02)))

        if let examDateString = examDatesByCourseKey[question.courseKey],
           let examDate = Self.isoDateFormatter.date(from: examDateString) {
            let daysLeft = max(
                Calendar.current.dateComponents([.day], from: today, to: examDate).day ?? 1,
                1
            )
            entry.interval = min(entry.interval, daysLeft)
        }

        let nextReview = Calendar.current.date(byAdding: .day, value: entry.interval, to: today) ?? today
        entry.nextReview = Self.isoDateFormatter.string(from: nextReview)
        performanceByQuestionID[question.id] = entry
        savePerformanceByQuestion()
    }

    private func clampQuestionLimit() {
        if availableQuestionCount > 0 {
            if questionLimit == 0 {
                return
            }
            questionLimit = min(max(1, questionLimit), availableQuestionCount)
        } else {
            questionLimit = 0
        }
    }

    private func finishQuiz() {
        isFinished = true
        hasStarted = true

        var stats = statsByCourse[selectedCourseID] ?? QuizCourseStats()
        stats.plays += 1
        stats.answered += totalQuestions
        stats.correct += score
        statsByCourse[selectedCourseID] = stats
        saveStatsByCourse()

        let oldBest = bestScoresByCourse[selectedCourseID] ?? 0
        if score > oldBest {
            bestScoresByCourse[selectedCourseID] = score
            saveBestScores()
        }

        refreshCourseMetrics()
        clearProgressSnapshot()
    }

    private func updateWrongQuestionSet(with outcome: QuizOutcome) {
        let targetCourseID = courseIDByCourseKey[outcome.question.courseKey] ?? selectedCourseID
        var wrongIDs = wrongQuestionIDsByCourse[targetCourseID] ?? []
        if outcome.isCorrect {
            wrongIDs.remove(outcome.question.id)
        } else {
            wrongIDs.insert(outcome.question.id)
        }
        wrongQuestionIDsByCourse[targetCourseID] = wrongIDs
        saveWrongQuestionIDs()
    }

    private func prepareRound(shuffle: Bool) {
        let mode = wrongAnswersOnly ? QuizFilterMode.wrong : activeFilterMode
        let pool = questionPool(scope: activeScope, mode: mode)
        availableQuestionCount = pool.count
        clampQuestionLimit()

        var round = shuffle ? pool.shuffled() : pool
        if !round.isEmpty && questionLimit > 0 {
            round = Array(round.prefix(questionLimit))
        }

        questions = round
        currentIndex = 0
        score = 0
        isFinished = false
        selectedIndex = nil
        didSubmit = false
        outcomes = []
    }

    private func canRestore(snapshot: QuizProgressSnapshot) -> Bool {
        guard !snapshot.questionIDs.isEmpty else { return false }
        return snapshot.questionIDs.allSatisfy { questionsByID[$0] != nil }
    }

    private func saveProgressSnapshot() {
        guard hasStarted, !isFinished, !questions.isEmpty else { return }

        let snapshot = QuizProgressSnapshot(
            courseID: selectedCourseID,
            questionIDs: questions.map(\.id),
            currentIndex: currentIndex,
            score: score,
            selectedIndex: selectedIndex,
            didSubmit: didSubmit,
            outcomes: outcomes.map { QuizOutcomeSnapshot(questionID: $0.question.id, selectedIndex: $0.selectedIndex) },
            settings: QuizPersistedSettings(
                selectedCourseID: selectedCourseID,
                questionLimit: questionLimit,
                shuffleQuestions: shuffleQuestions,
                wrongAnswersOnly: wrongAnswersOnly
            )
        )

        progressSnapshot = snapshot
        hasResumableSession = true
        Self.saveValue(snapshot, forKey: progressKey)
    }

    private func clearProgressSnapshot() {
        progressSnapshot = nil
        hasResumableSession = false
        UserDefaults.standard.removeObject(forKey: progressKey)
    }

    private func saveBestScores() {
        Self.saveValue(bestScoresByCourse, forKey: bestScoresKey)
    }

    private func saveStatsByCourse() {
        Self.saveValue(statsByCourse, forKey: courseStatsKey)
    }

    private func saveWrongQuestionIDs() {
        let serializable = wrongQuestionIDsByCourse.mapValues { Array($0).sorted() }
        Self.saveValue(serializable, forKey: wrongIDsKey)
    }

    private func savePerformanceByQuestion() {
        Self.saveValue(performanceByQuestionID, forKey: performanceKey)
    }

    private func persistSettings() {
        let settings = QuizPersistedSettings(
            selectedCourseID: selectedCourseID,
            questionLimit: questionLimit,
            shuffleQuestions: shuffleQuestions,
            wrongAnswersOnly: wrongAnswersOnly
        )
        Self.saveValue(settings, forKey: settingsKey)
    }

    private static func buildFileInfos(from questions: [QuizQuestion]) -> [QuizFileInfo] {
        let grouped = Dictionary(grouping: questions, by: \.sourcePath)
        return grouped.compactMap { sourcePath, groupedQuestions in
            guard let first = groupedQuestions.first else { return nil }
            let fallbackName = sourcePath.isEmpty ? "Sample Quiz" : URL(fileURLWithPath: sourcePath).lastPathComponent
            let fileName = first.sourceFileName.isEmpty ? fallbackName : first.sourceFileName
            return QuizFileInfo(
                id: sourcePath.isEmpty ? fileName : sourcePath,
                sourcePath: sourcePath,
                fileName: fileName,
                courseKey: first.courseKey,
                courseTitle: first.category,
                sectionName: first.sectionName,
                questionCount: groupedQuestions.count
            )
        }
        .sorted { lhs, rhs in
            if lhs.courseTitle != rhs.courseTitle {
                return lhs.courseTitle.localizedCaseInsensitiveCompare(rhs.courseTitle) == .orderedAscending
            }
            if lhs.sectionName != rhs.sectionName {
                return lhs.sectionName.localizedCaseInsensitiveCompare(rhs.sectionName) == .orderedAscending
            }
            return lhs.fileName.localizedCaseInsensitiveCompare(rhs.fileName) == .orderedAscending
        }
    }

    private static let isoDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone.current
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    private static func saveValue<T: Encodable>(_ value: T, forKey key: String) {
        guard let data = try? JSONEncoder().encode(value) else { return }
        UserDefaults.standard.set(data, forKey: key)
    }

    private static func loadValue<T: Decodable>(forKey key: String) -> T? {
        guard let data = UserDefaults.standard.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(T.self, from: data)
    }
}
