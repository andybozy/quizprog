import SwiftUI

private struct QuizTheme {
    let colorScheme: ColorScheme

    var accent: Color {
        colorScheme == .dark
            ? Color(red: 0.30, green: 0.72, blue: 1.00)
            : Color(red: 0.05, green: 0.38, blue: 0.92)
    }

    var success: Color {
        colorScheme == .dark
            ? Color(red: 0.44, green: 0.90, blue: 0.58)
            : Color(red: 0.09, green: 0.58, blue: 0.27)
    }

    var danger: Color {
        colorScheme == .dark
            ? Color(red: 1.00, green: 0.56, blue: 0.56)
            : Color(red: 0.80, green: 0.22, blue: 0.22)
    }

    var backgroundGradient: LinearGradient {
        if colorScheme == .dark {
            return LinearGradient(
                colors: [
                    Color(red: 0.07, green: 0.09, blue: 0.13),
                    Color(red: 0.05, green: 0.08, blue: 0.12)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
        }
        return LinearGradient(
            colors: [
                Color(red: 0.97, green: 0.99, blue: 1.0),
                Color(red: 0.92, green: 0.96, blue: 1.0)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    var cardBackground: Color {
        colorScheme == .dark
            ? Color(red: 0.12, green: 0.14, blue: 0.19).opacity(0.94)
            : .white.opacity(0.96)
    }

    var cardBorder: Color {
        colorScheme == .dark
            ? .white.opacity(0.16)
            : .black.opacity(0.08)
    }

    var secondaryText: Color {
        colorScheme == .dark
            ? .white.opacity(0.78)
            : .black.opacity(0.62)
    }

    var optionDefaultBackground: Color {
        colorScheme == .dark
            ? Color(red: 0.10, green: 0.12, blue: 0.17).opacity(0.96)
            : .white.opacity(0.96)
    }

    var optionDefaultBorder: Color {
        colorScheme == .dark
            ? .white.opacity(0.20)
            : .gray.opacity(0.24)
    }

    var disabledButtonBackground: Color {
        colorScheme == .dark
            ? .white.opacity(0.22)
            : .gray.opacity(0.50)
    }

    var correctFill: Color {
        success.opacity(colorScheme == .dark ? 0.28 : 0.15)
    }

    var wrongFill: Color {
        danger.opacity(colorScheme == .dark ? 0.28 : 0.14)
    }
}

private extension View {
    func quizCard(_ theme: QuizTheme, cornerRadius: CGFloat = 14) -> some View {
        self
            .background(theme.cardBackground)
            .overlay {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(theme.cardBorder, lineWidth: 1)
            }
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
    }
}

struct ContentView: View {
    @StateObject private var session = QuizSession()
    @Environment(\.colorScheme) private var colorScheme

    private var theme: QuizTheme {
        QuizTheme(colorScheme: colorScheme)
    }

    var body: some View {
        NavigationStack {
            ZStack {
                theme.backgroundGradient
                    .ignoresSafeArea()

                Group {
                    if !session.hasStarted {
                        StartScreen(session: session, theme: theme)
                    } else if session.isFinished {
                        ResultsScreen(session: session, theme: theme)
                    } else {
                        QuizScreen(session: session, theme: theme)
                    }
                }
                .padding(20)
            }
            .navigationTitle("QuizProg")
            .navigationBarTitleDisplayMode(.inline)
        }
        .tint(theme.accent)
    }
}

private struct StartScreen: View {
    @ObservedObject var session: QuizSession
    let theme: QuizTheme
    @State private var showingFileMenu = false
    @State private var showingTagMenu = false
    @State private var showingSummaryMenu = false
    @State private var showingStatsMenu = false
    @State private var menuErrorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("QuizProg Legacy Menu")
                    .font(.system(size: 32, weight: .bold, design: .rounded))
                    .foregroundStyle(.primary)

                Text("Replica struttura CLI: filtri, navigazione per file/tag, riepiloghi e statistiche.")
                    .font(.body.weight(.medium))
                    .foregroundStyle(theme.secondaryText)

                if session.hasResumableSession {
                    Button {
                        session.resumeSavedSession()
                    } label: {
                        Text("Riprendi quiz salvato")
                            .font(.headline.weight(.semibold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(theme.accent)
                            .foregroundStyle(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    }
                }

                VStack(alignment: .leading, spacing: 14) {
                    Text("Menu Principale")
                        .font(.subheadline.weight(.semibold))

                    LegacyMenuButton(
                        index: "1",
                        title: "Programmate per oggi",
                        subtitle: "Filtro due su tutto il repository",
                        theme: theme
                    ) {
                        startQuiz(mode: .due, scope: .repository)
                    }

                    LegacyMenuButton(
                        index: "2",
                        title: "Tutte le domande",
                        subtitle: "Nessun filtro",
                        theme: theme
                    ) {
                        startQuiz(mode: .all, scope: .repository)
                    }

                    LegacyMenuButton(
                        index: "3",
                        title: "Non risposte",
                        subtitle: "Solo domande mai tentate",
                        theme: theme
                    ) {
                        startQuiz(mode: .unanswered, scope: .repository)
                    }

                    LegacyMenuButton(
                        index: "4",
                        title: "Fallite",
                        subtitle: "Ultimo tentativo errato",
                        theme: theme
                    ) {
                        startQuiz(mode: .wrong, scope: .repository)
                    }

                    LegacyMenuButton(
                        index: "5",
                        title: "Fallite o saltate",
                        subtitle: "Ultimo tentativo wrong/skipped",
                        theme: theme
                    ) {
                        startQuiz(mode: .wrongOrSkipped, scope: .repository)
                    }

                    LegacyMenuButton(
                        index: "5b",
                        title: "Saltate",
                        subtitle: "Ultimo tentativo skipped",
                        theme: theme
                    ) {
                        startQuiz(mode: .skipped, scope: .repository)
                    }

                    LegacyMenuButton(
                        index: "6",
                        title: "Per file",
                        subtitle: "Corso -> sezione -> file -> filtro",
                        theme: theme
                    ) {
                        showingFileMenu = true
                    }

                    LegacyMenuButton(
                        index: "7",
                        title: "Per tag",
                        subtitle: "Come CLI: usa il filtro 'Programmate per oggi'",
                        theme: theme
                    ) {
                        showingTagMenu = true
                    }

                    LegacyMenuButton(
                        index: "8",
                        title: "Riepilogo file",
                        subtitle: "Statistiche aggregate per file e corso",
                        theme: theme
                    ) {
                        showingSummaryMenu = true
                    }

                    LegacyMenuButton(
                        index: "9",
                        title: "Statistiche",
                        subtitle: "Repository, corso o file",
                        theme: theme
                    ) {
                        showingStatsMenu = true
                    }
                }
                .padding(16)
                .quizCard(theme)

                HStack(spacing: 12) {
                    StatPill(label: "Domande repo", value: "\(session.totalRepositoryQuestionCount)", theme: theme)
                    StatPill(label: "Tag", value: "\(session.tagNames.count)", theme: theme)
                    StatPill(label: "File", value: "\(session.allFileInfos.count)", theme: theme)
                }
            }
            .padding(.vertical, 6)
        }
        .scrollIndicators(.hidden)
        .sheet(isPresented: $showingFileMenu) {
            FileQuizMenuSheet(session: session, theme: theme)
        }
        .sheet(isPresented: $showingTagMenu) {
            TagQuizMenuSheet(session: session, theme: theme)
        }
        .sheet(isPresented: $showingSummaryMenu) {
            FileSummarySheet(session: session, theme: theme)
        }
        .sheet(isPresented: $showingStatsMenu) {
            StatsMenuSheet(session: session, theme: theme)
        }
        .alert("Filtro senza domande", isPresented: menuErrorBinding) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(menuErrorMessage ?? "Nessuna domanda disponibile per questa selezione.")
        }
    }

    private var menuErrorBinding: Binding<Bool> {
        Binding(
            get: { menuErrorMessage != nil },
            set: { visible in
                if !visible {
                    menuErrorMessage = nil
                }
            }
        )
    }

    private func startQuiz(mode: QuizFilterMode, scope: QuizScope) {
        if !session.startMenuQuiz(mode: mode, scope: scope) {
            menuErrorMessage = "Nessuna domanda disponibile in '\(mode.title)'."
        }
    }
}

private struct LegacyMenuButton: View {
    let index: String
    let title: String
    let subtitle: String
    let theme: QuizTheme
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(alignment: .top, spacing: 12) {
                Text("\(index)")
                    .font(.headline.weight(.bold))
                    .frame(width: 28, height: 28)
                    .background(theme.accent.opacity(theme.colorScheme == .dark ? 0.34 : 0.15))
                    .foregroundStyle(theme.accent)
                    .clipShape(Circle())

                VStack(alignment: .leading, spacing: 3) {
                    Text(title)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                    Text(subtitle)
                        .font(.caption.weight(.medium))
                        .foregroundStyle(theme.secondaryText)
                }

                Spacer()
            }
            .padding(.vertical, 6)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}

private struct FileQuizMenuSheet: View {
    @ObservedObject var session: QuizSession
    let theme: QuizTheme
    @Environment(\.dismiss) private var dismiss

    @State private var selectedCourseKey: String = ""
    @State private var selectedSectionName: String = ""
    @State private var selectedFilePath: String = ""
    @State private var localErrorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if session.fileCourseKeys.isEmpty {
                    Text("Nessun file quiz disponibile.")
                        .font(.headline.weight(.semibold))
                        .foregroundStyle(theme.secondaryText)
                        .padding()
                } else {
                    Form {
                        Section("Corso") {
                            Picker("Corso", selection: $selectedCourseKey) {
                                ForEach(session.fileCourseKeys, id: \.self) { key in
                                    Text(session.courseTitle(forCourseKey: key)).tag(key)
                                }
                            }
                        }

                        Section("Sezione") {
                            Picker("Sezione", selection: $selectedSectionName) {
                                ForEach(currentSections, id: \.self) { section in
                                    Text(section).tag(section)
                                }
                            }
                        }

                        Section("File") {
                            Picker("File", selection: $selectedFilePath) {
                                ForEach(currentFiles) { file in
                                    Text(file.fileName).tag(file.sourcePath)
                                }
                            }
                        }

                        Section("Filtro (come CLI opzione 6)") {
                            filterButton(title: "1) Tutte", mode: .all)
                            filterButton(title: "2) Non risposte", mode: .unanswered)
                            filterButton(title: "3) Fallite", mode: .wrong)
                            filterButton(title: "4) Fallite o saltate", mode: .wrongOrSkipped)
                            filterButton(title: "5) Saltate", mode: .skipped)
                            filterButton(title: "6) Programmate per oggi", mode: .due)
                        }
                    }
                }
            }
            .navigationTitle("6) Per file")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Chiudi") { dismiss() }
                }
            }
        }
        .onAppear {
            syncSelections()
        }
        .onChange(of: selectedCourseKey) { _, _ in
            syncSectionAndFile()
        }
        .onChange(of: selectedSectionName) { _, _ in
            syncFileSelection()
        }
        .alert("Filtro senza domande", isPresented: localErrorBinding) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(localErrorMessage ?? "Nessuna domanda disponibile in questa selezione.")
        }
    }

    private var currentSections: [String] {
        guard !selectedCourseKey.isEmpty else { return [] }
        return session.sectionNames(forCourseKey: selectedCourseKey)
    }

    private var currentFiles: [QuizFileInfo] {
        guard !selectedCourseKey.isEmpty, !selectedSectionName.isEmpty else { return [] }
        return session.files(forCourseKey: selectedCourseKey, sectionName: selectedSectionName)
    }

    private var localErrorBinding: Binding<Bool> {
        Binding(
            get: { localErrorMessage != nil },
            set: { visible in
                if !visible {
                    localErrorMessage = nil
                }
            }
        )
    }

    private func filterButton(title: String, mode: QuizFilterMode) -> some View {
        Button(title) {
            startFileQuiz(mode: mode)
        }
    }

    private func syncSelections() {
        if selectedCourseKey.isEmpty {
            selectedCourseKey = session.fileCourseKeys.first ?? ""
        }
        syncSectionAndFile()
    }

    private func syncSectionAndFile() {
        let sections = currentSections
        if !sections.contains(selectedSectionName) {
            selectedSectionName = sections.first ?? ""
        }
        syncFileSelection()
    }

    private func syncFileSelection() {
        let files = currentFiles
        if !files.contains(where: { $0.sourcePath == selectedFilePath }) {
            selectedFilePath = files.first?.sourcePath ?? ""
        }
    }

    private func startFileQuiz(mode: QuizFilterMode) {
        guard !selectedFilePath.isEmpty else { return }
        let didStart = session.startMenuQuiz(mode: mode, scope: .file(selectedFilePath))
        if didStart {
            dismiss()
        } else {
            localErrorMessage = "Il file selezionato non ha domande per '\(mode.title)'."
        }
    }
}

private struct TagQuizMenuSheet: View {
    @ObservedObject var session: QuizSession
    let theme: QuizTheme
    @Environment(\.dismiss) private var dismiss
    @State private var localErrorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if session.tagNames.isEmpty {
                    VStack(spacing: 10) {
                        Text("Nessun tag presente nei quiz.")
                            .font(.headline.weight(.semibold))
                        Text("La struttura è pronta: basta aggiungere `tags` nei JSON.")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(theme.secondaryText)
                    }
                    .padding()
                } else {
                    List {
                        ForEach(session.tagNames, id: \.self) { tag in
                            Button(tag) {
                                let didStart = session.startMenuQuiz(mode: .due, scope: .tag(tag))
                                if didStart {
                                    dismiss()
                                } else {
                                    localErrorMessage = "Nessuna domanda per il tag '\(tag)' nel filtro Programmate per oggi."
                                }
                            }
                            .font(.headline)
                        }
                    }
                    .listStyle(.insetGrouped)
                }
            }
            .navigationTitle("7) Per tag")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Chiudi") { dismiss() }
                }
            }
        }
        .alert("Filtro senza domande", isPresented: localErrorBinding) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(localErrorMessage ?? "Nessuna domanda disponibile.")
        }
    }

    private var localErrorBinding: Binding<Bool> {
        Binding(
            get: { localErrorMessage != nil },
            set: { visible in
                if !visible {
                    localErrorMessage = nil
                }
            }
        )
    }
}

private struct FileSummarySheet: View {
    @ObservedObject var session: QuizSession
    let theme: QuizTheme
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section("File") {
                    ForEach(session.fileSummaryItems()) { item in
                        NavigationLink {
                            ScopeStatsDetailView(
                                title: item.info.fileName,
                                subtitle: item.info.courseTitle,
                                stats: item.stats,
                                theme: theme
                            )
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.info.fileName)
                                    .font(.subheadline.weight(.semibold))
                                Text("tot \(item.stats.total) • no-int \(item.stats.never) • skip \(item.stats.skipped) • wrong \(item.stats.wrong) • correct \(item.stats.correct) • due \(item.stats.due)")
                                    .font(.caption.weight(.medium))
                                    .foregroundStyle(theme.secondaryText)
                            }
                        }
                    }
                }

                Section("Corsi") {
                    ForEach(session.courseSummaryItems()) { item in
                        NavigationLink {
                            ScopeStatsDetailView(
                                title: item.courseTitle,
                                subtitle: "Corso",
                                stats: item.stats,
                                theme: theme
                            )
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.courseTitle)
                                    .font(.subheadline.weight(.semibold))
                                Text("tot \(item.stats.total) • no-int \(item.stats.never) • skip \(item.stats.skipped) • wrong \(item.stats.wrong) • correct \(item.stats.correct) • due \(item.stats.due)")
                                    .font(.caption.weight(.medium))
                                    .foregroundStyle(theme.secondaryText)
                            }
                        }
                    }
                }
            }
            .listStyle(.insetGrouped)
            .navigationTitle("8) Riepilogo file")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Chiudi") { dismiss() }
                }
            }
        }
    }
}

private struct StatsMenuSheet: View {
    @ObservedObject var session: QuizSession
    let theme: QuizTheme
    @Environment(\.dismiss) private var dismiss

    @State private var selectedScope: StatsScope = .repository
    @State private var selectedCourseKey: String = ""
    @State private var selectedFilePath: String = ""

    private enum StatsScope: String, CaseIterable, Identifiable {
        case repository
        case course
        case file

        var id: String { rawValue }

        var title: String {
            switch self {
            case .repository: return "Repository"
            case .course: return "Corso"
            case .file: return "File"
            }
        }
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Ambito") {
                    Picker("Ambito", selection: $selectedScope) {
                        ForEach(StatsScope.allCases) { scope in
                            Text(scope.title).tag(scope)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                if selectedScope == .course {
                    Section("Corso") {
                        Picker("Corso", selection: $selectedCourseKey) {
                            ForEach(session.fileCourseKeys, id: \.self) { key in
                                Text(session.courseTitle(forCourseKey: key)).tag(key)
                            }
                        }
                    }
                }

                if selectedScope == .file {
                    Section("File") {
                        Picker("File", selection: $selectedFilePath) {
                            ForEach(session.allFileInfos) { info in
                                Text("\(info.fileName) (\(info.courseTitle))").tag(info.sourcePath)
                            }
                        }
                    }
                }

                Section("Statistiche") {
                    StatsGrid(stats: currentStats, theme: theme)
                }
            }
            .navigationTitle("9) Statistiche")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Chiudi") { dismiss() }
                }
            }
        }
        .onAppear {
            if selectedCourseKey.isEmpty {
                selectedCourseKey = session.fileCourseKeys.first ?? ""
            }
            if selectedFilePath.isEmpty {
                selectedFilePath = session.allFileInfos.first?.sourcePath ?? ""
            }
        }
    }

    private var currentStats: QuizScopeStats {
        switch selectedScope {
        case .repository:
            return session.repositoryStats()
        case .course:
            return session.courseStats(forCourseKey: selectedCourseKey)
        case .file:
            return session.fileStats(forSourcePath: selectedFilePath)
        }
    }
}

private struct ScopeStatsDetailView: View {
    let title: String
    let subtitle: String
    let stats: QuizScopeStats
    let theme: QuizTheme

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(title)
                    .font(.title2.weight(.bold))
                Text(subtitle)
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(theme.secondaryText)
                StatsGrid(stats: stats, theme: theme)
            }
            .padding()
        }
        .navigationTitle("Dettaglio")
    }
}

private struct StatsGrid: View {
    let stats: QuizScopeStats
    let theme: QuizTheme

    var body: some View {
        VStack(spacing: 10) {
            HStack(spacing: 10) {
                StatPill(label: "Totale", value: "\(stats.total)", theme: theme)
                StatPill(label: "No-int", value: "\(stats.never)", theme: theme)
                StatPill(label: "Due", value: "\(stats.due)", theme: theme)
            }
            HStack(spacing: 10) {
                StatPill(label: "Skip", value: "\(stats.skipped)", theme: theme)
                StatPill(label: "Wrong", value: "\(stats.wrong)", theme: theme)
                StatPill(label: "Correct", value: "\(stats.correct)", theme: theme)
            }
        }
    }
}

private struct QuizScreen: View {
    @ObservedObject var session: QuizSession
    let theme: QuizTheme

    var question: QuizQuestion {
        session.currentQuestion
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Question \(session.currentIndex + 1) of \(session.totalQuestions)")
                            .font(.subheadline.weight(.semibold))
                        Spacer()
                        Text("Score \(session.score)")
                            .font(.subheadline.weight(.semibold))
                    }

                    HStack {
                        Text(session.activeScopeLabel)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(theme.secondaryText)
                        Spacer()
                        Button("Exit & Save") {
                            session.exitAndSave()
                        }
                        .font(.caption.weight(.semibold))
                    }

                    let completed = session.currentIndex + (session.didSubmit ? 1 : 0)
                    ProgressView(value: Double(completed), total: Double(session.totalQuestions))
                        .tint(theme.accent)

                    Text("Filtro: \(session.activeFilterMode.title)")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(theme.secondaryText)
                }

                VStack(alignment: .leading, spacing: 12) {
                    Text(question.category.uppercased())
                        .font(.caption.weight(.bold))
                        .foregroundStyle(theme.accent)

                    Text(question.prompt)
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(.primary)
                }
                .padding(16)
                .quizCard(theme, cornerRadius: 16)

                VStack(spacing: 10) {
                    ForEach(question.options.indices, id: \.self) { index in
                        Button {
                            session.selectOption(index)
                        } label: {
                            HStack(spacing: 10) {
                                Text(question.options[index])
                                    .font(.body.weight(.medium))
                                    .multilineTextAlignment(.leading)
                                    .frame(maxWidth: .infinity, alignment: .leading)

                                if session.didSubmit {
                                    if index == question.correctIndex {
                                        Image(systemName: "checkmark.circle.fill")
                                            .foregroundStyle(theme.success)
                                    } else if index == session.selectedIndex {
                                        Image(systemName: "xmark.circle.fill")
                                            .foregroundStyle(theme.danger)
                                    }
                                }
                            }
                            .padding(14)
                            .background(optionBackground(for: index))
                            .overlay {
                                RoundedRectangle(cornerRadius: 14, style: .continuous)
                                    .stroke(optionBorder(for: index), lineWidth: 1)
                            }
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                        }
                        .buttonStyle(.plain)
                        .disabled(session.didSubmit)
                    }
                }

                if session.didSubmit {
                    FeedbackCard(question: question, selectedIndex: session.selectedIndex, theme: theme)
                }

                Button {
                    if session.didSubmit {
                        session.goToNextQuestion()
                    } else {
                        session.submitCurrentAnswer()
                    }
                } label: {
                    Text(session.didSubmit ? nextButtonTitle : "Submit Answer")
                        .font(.headline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(session.canSubmit || session.didSubmit ? theme.accent : theme.disabledButtonBackground)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                }
                .disabled(!session.canSubmit && !session.didSubmit)

                if !session.didSubmit {
                    Button("Salta Domanda") {
                        session.skipCurrentQuestion()
                    }
                    .font(.subheadline.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .foregroundStyle(theme.secondaryText)
                }
            }
            .padding(.vertical, 6)
        }
        .scrollIndicators(.hidden)
    }

    var nextButtonTitle: String {
        session.currentIndex + 1 < session.totalQuestions ? "Next Question" : "See Results"
    }

    func optionBackground(for index: Int) -> Color {
        if !session.didSubmit {
            return session.selectedIndex == index
                ? theme.accent.opacity(theme.colorScheme == .dark ? 0.28 : 0.15)
                : theme.optionDefaultBackground
        }

        if index == question.correctIndex {
            return theme.correctFill
        }

        if index == session.selectedIndex {
            return theme.wrongFill
        }

        return theme.optionDefaultBackground
    }

    func optionBorder(for index: Int) -> Color {
        if !session.didSubmit {
            return session.selectedIndex == index ? theme.accent : theme.optionDefaultBorder
        }

        if index == question.correctIndex {
            return theme.success
        }

        if index == session.selectedIndex {
            return theme.danger
        }

        return theme.optionDefaultBorder
    }
}

private struct FeedbackCard: View {
    let question: QuizQuestion
    let selectedIndex: Int?
    let theme: QuizTheme

    var body: some View {
        let didGetItRight = selectedIndex == question.correctIndex
        let wasSkipped = selectedIndex == nil

        VStack(alignment: .leading, spacing: 8) {
            Text(wasSkipped ? "Saltata" : (didGetItRight ? "Correct" : "Not quite"))
                .font(.headline.weight(.semibold))
                .foregroundStyle(didGetItRight ? theme.success : theme.danger)

            if !didGetItRight {
                Text("Correct answer: \(question.options[question.correctIndex])")
                    .font(.subheadline.weight(.medium))
            }

            Text(question.explanation)
                .font(.subheadline)
                .foregroundStyle(theme.secondaryText)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .quizCard(theme)
    }
}

private struct ResultsScreen: View {
    @ObservedObject var session: QuizSession
    let theme: QuizTheme

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Quiz Complete")
                    .font(.system(size: 32, weight: .bold, design: .rounded))

                VStack(alignment: .leading, spacing: 8) {
                    Text("\(session.score)/\(session.totalQuestions) correct")
                        .font(.title2.weight(.bold))

                    Text("\(session.scorePercent)% score")
                        .font(.headline.weight(.semibold))
                        .foregroundStyle(theme.secondaryText)

                    Text(resultMessage)
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(theme.secondaryText)
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .quizCard(theme, cornerRadius: 16)

                Text("Review")
                    .font(.headline.weight(.semibold))

                VStack(spacing: 10) {
                    ForEach(session.outcomes) { outcome in
                        ReviewRow(outcome: outcome, theme: theme)
                    }
                }

                Button {
                    session.restart()
                } label: {
                    Text("Play Again")
                        .font(.headline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(theme.accent)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                }

                Button {
                    session.backToHome()
                } label: {
                    Text("Back to Home")
                        .font(.headline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(theme.cardBackground)
                        .foregroundStyle(theme.accent)
                        .overlay {
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .stroke(theme.cardBorder, lineWidth: 1)
                        }
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                }
            }
            .padding(.vertical, 6)
        }
        .scrollIndicators(.hidden)
    }

    var resultMessage: String {
        switch session.scorePercent {
        case 90...:
            return "Excellent accuracy."
        case 75...:
            return "Strong work. A little more and you are near-perfect."
        case 50...:
            return "Solid start. Keep drilling weak spots."
        default:
            return "Keep practicing. Consistency will raise your score."
        }
    }
}

private struct ReviewRow: View {
    let outcome: QuizOutcome
    let theme: QuizTheme

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: outcome.isCorrect ? "checkmark.circle.fill" : "xmark.circle.fill")
                    .foregroundStyle(outcome.isCorrect ? theme.success : theme.danger)
                Text(outcome.question.prompt)
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(2)
            }

            Text("Your answer: \(outcome.question.options[outcome.selectedIndex])")
                .font(.footnote.weight(.medium))
                .foregroundStyle(theme.secondaryText)

            if !outcome.isCorrect {
                Text("Correct: \(outcome.question.options[outcome.question.correctIndex])")
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(theme.success)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .quizCard(theme, cornerRadius: 12)
    }
}

private struct StatPill: View {
    let label: String
    let value: String
    let theme: QuizTheme

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(label)
                .font(.caption.weight(.semibold))
                .foregroundStyle(theme.secondaryText)
            Text(value)
                .font(.headline.weight(.bold))
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .quizCard(theme, cornerRadius: 12)
    }
}

#Preview {
    ContentView()
}
