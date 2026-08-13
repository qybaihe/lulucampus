import SwiftUI

@MainActor
final class IntentComposerViewModel: ObservableObject {
    enum Phase {
        case editing
        case compiling
        case clarifying(IntentCard, [IntentClarificationQuestion], Int, Int)
        case preview(IntentCard)
        case publishing(IntentCard)
        case published(IntentPublishResult)
        case failed(String)
    }
    @Published var text: String
    @Published var moodNote = ""
    @Published var clarificationAnswer = ""
    @Published var availabilityStart = Date().addingTimeInterval(86_400)
    @Published var availabilityEnd = Date().addingTimeInterval(93_600)
    @Published var phase: Phase = .editing
    @Published var goal = ""
    @Published var capabilitiesText = ""
    @Published var rolesText = ""
    @Published var campus = ""
    @Published var intensity = "balanced"
    @Published var socialMode = "after_full"
    @Published var sameGenderOnly = false
    @Published var minimumSize = 3
    @Published var targetSize = 3
    @Published var startAt = Date().addingTimeInterval(86_400)
    @Published var endAt = Date().addingTimeInterval(93_600)
    @Published var operationError: String?
    @Published var saving = false
    @Published private(set) var pendingPublishKey: String?
    @Published var recruitHints: [String] = []
    @Published var tasteFitLabel: String?
    private let repository: IntentRepository
    let competitionID: String?

    init(repository: IntentRepository, competitionID: String? = nil, preset: IntentPreset? = nil) {
        self.repository = repository
        self.competitionID = competitionID
        text = preset?.text ?? ""
    }

    func compile(round: Int = 0, answers: [String: String] = [:]) async {
        let value = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return }
        phase = .compiling; operationError = nil
        do {
            let trimmedMood = moodNote.trimmingCharacters(in: .whitespacesAndNewlines)
            let result = try await repository.compile(
                text: value,
                moodNote: trimmedMood.isEmpty ? nil : trimmedMood,
                competitionID: competitionID,
                clarificationRound: round,
                answers: answers
            )
            recruitHints = result.recruitHints ?? []
            tasteFitLabel = result.tasteFitLabel
            if result.needsClarification, round < result.maxRounds {
                clarificationAnswer = ""
                phase = .clarifying(result.card, result.questions, round, result.maxRounds)
            } else { prepare(result.card); phase = .preview(result.card) }
        } catch { phase = .failed(error.localizedDescription) }
    }

    func answer(_ questions: [IntentClarificationQuestion], round: Int) async {
        var answers: [String: String] = [:]
        for question in questions {
            if question.key == "availability" {
                answers[question.key] = "\(Self.iso.string(from: availabilityStart))|\(Self.iso.string(from: availabilityEnd))"
            } else {
                let value = clarificationAnswer.trimmingCharacters(in: .whitespacesAndNewlines)
                if !value.isEmpty { answers[question.key] = value }
            }
        }
        guard answers.count == questions.count else {
            operationError = "请完成这一轮的所有澄清项"
            return
        }
        await compile(round: min(round + 1, 2), answers: answers)
    }

    func prepare(_ card: IntentCard) {
        goal = card.goal
        moodNote = card.moodNote ?? moodNote
        capabilitiesText = card.capabilities.map(\.key).joined(separator: "、")
        rolesText = card.requiredRoles.joined(separator: "、")
        campus = card.campus ?? ""
        intensity = IntentComposerView.normalizedIntensity(card.intensity)
        socialMode = card.socialMode
        sameGenderOnly = card.sameGenderOnly ?? false
        minimumSize = card.minSize
        targetSize = card.targetSize
        if let window = card.availableWindows.first { startAt = window.startAt; endAt = window.endAt }
    }

    func restore(_ draft: IntentRecoveryDraft) async {
        guard draft.competitionID == competitionID else { return }
        text = draft.text
        goal = draft.goal
        capabilitiesText = draft.capabilitiesText
        rolesText = draft.rolesText
        campus = draft.campus
        intensity = IntentComposerView.normalizedIntensity(draft.intensity)
        socialMode = draft.socialMode
        sameGenderOnly = draft.sameGenderOnly ?? false
        minimumSize = draft.minimumSize
        targetSize = draft.targetSize
        startAt = draft.startAt
        endAt = draft.endAt
        pendingPublishKey = draft.idempotencyKey
        if let cardID = draft.cardID {
            if draft.pendingAction == "publish",
               let published = try? await repository.publication(cardID) {
                phase = .published(published)
                pendingPublishKey = nil
                operationError = "发布结果已从服务端恢复。"
                return
            }
            do {
                let card = try await repository.card(cardID)
                phase = .preview(card)
                if draft.pendingAction == "publish" {
                    operationError = "登录已恢复。请确认后重试发布；将沿用原操作标识，不会重复创建。"
                }
            } catch {
                phase = .editing
                operationError = "草稿已恢复；服务端意图卡需重新理解：\(error.localizedDescription)"
            }
        }
    }

    func recoveryDraft(pendingAction: String? = nil) -> IntentRecoveryDraft {
        let cardID: String?
        switch phase {
        case let .clarifying(card, _, _, _), let .preview(card), let .publishing(card): cardID = card.id
        default: cardID = nil
        }
        return IntentRecoveryDraft(
            text: text,
            goal: goal,
            capabilitiesText: capabilitiesText,
            rolesText: rolesText,
            campus: campus,
            intensity: intensity,
            socialMode: socialMode,
            sameGenderOnly: sameGenderOnly,
            minimumSize: minimumSize,
            targetSize: targetSize,
            startAt: startAt,
            endAt: endAt,
            cardID: cardID,
            competitionID: competitionID,
            pendingAction: pendingAction ?? (pendingPublishKey == nil ? nil : "publish"),
            idempotencyKey: pendingPublishKey
        )
    }

    func save(_ card: IntentCard) async -> IntentCard? {
        guard !saving else { return nil }
        guard minimumSize <= targetSize, endAt > startAt else {
            operationError = minimumSize > targetSize ? "最低人数不能超过目标人数" : "结束时间必须晚于开始时间"
            return nil
        }
        saving = true; defer { saving = false }
        let existing = Dictionary(uniqueKeysWithValues: card.capabilities.map { ($0.key, $0.source) })
        let capabilities = split(capabilitiesText).map {
            IntentCard.Capability(key: $0, source: existing[$0] ?? "self_reported")
        }
        let trimmedMood = moodNote.trimmingCharacters(in: .whitespacesAndNewlines)
        let patch = IntentCardPatch(
            gatheringType: card.gatheringType,
            goal: goal,
            moodNote: trimmedMood.isEmpty ? nil : trimmedMood,
            capabilities: capabilities,
            requiredRoles: split(rolesText),
            intensity: intensity,
            availableWindows: [.init(startAt: startAt, endAt: endAt, stability: 1)],
            campus: campus.isEmpty ? nil : campus,
            minSize: minimumSize,
            targetSize: targetSize,
            socialMode: socialMode,
            sameGenderOnly: sameGenderOnly,
            expiresAt: card.expiresAt
        )
        do {
            let updated = try await repository.update(card.id, patch: patch)
            prepare(updated); phase = .preview(updated); operationError = nil
            return updated
        } catch { operationError = error.localizedDescription; return nil }
    }

    @discardableResult
    func publish(_ card: IntentCard) async -> Bool {
        let recoveringAmbiguousPublish = pendingPublishKey != nil
        beginPublish()
        if recoveringAmbiguousPublish {
            do {
                return completeRecoveredPublication(try await repository.publication(card.id))
            } catch let APIClientError.server(status, _) where status == 404 {
                // The prior operation definitely has no result, so the same
                // logical operation may continue through save and publish.
            } catch {
                phase = .preview(card)
                operationError = "正在向服务端核对上次发布结果，请保持网络后重试：\(error.localizedDescription)"
                return false
            }
        }
        guard let updated = await save(card) else {
            if recoveringAmbiguousPublish,
               let recovered = try? await repository.publication(card.id) {
                return completeRecoveredPublication(recovered)
            }
            return false
        }
        phase = .publishing(updated)
        do {
            phase = .published(try await repository.publish(cardID: updated.id, idempotencyKey: pendingPublishKey!))
            operationError = nil
            pendingPublishKey = nil
            return true
        } catch {
            if isAmbiguousPublishError(error) {
                do {
                    return completeRecoveredPublication(
                        try await repository.publication(updated.id)
                    )
                } catch {
                    phase = .preview(updated)
                    operationError = "发布响应未确认，已保留同一操作标识；重试时会先核对服务端结果。"
                    return false
                }
            }
            phase = .preview(updated)
            operationError = error.localizedDescription
            pendingPublishKey = nil
            return false
        }
    }

    private func completeRecoveredPublication(_ result: IntentPublishResult) -> Bool {
        phase = .published(result)
        pendingPublishKey = nil
        operationError = "发布结果已从服务端恢复。"
        return true
    }

    private func isAmbiguousPublishError(_ error: Error) -> Bool {
        guard let apiError = error as? APIClientError else { return true }
        switch apiError {
        case .transport, .invalidResponse, .decoding, .offline:
            return true
        case let .server(status, body):
            return status >= 500 || [
                "IDEMPOTENCY_IN_PROGRESS",
                "IDEMPOTENCY_RESULT_PENDING",
                "IDEMPOTENCY_RESULT_UNKNOWN",
            ].contains(body.code)
        case .invalidConfiguration, .sessionExpired:
            return false
        }
    }

    func beginPublish() {
        if pendingPublishKey == nil { pendingPublishKey = "ios-publish-\(UUID().uuidString)" }
    }

    func withdraw(_ card: IntentCard) async {
        guard !saving else { return }; saving = true; defer { saving = false }
        do { _ = try await repository.withdraw(card.id); phase = .editing; operationError = nil }
        catch { operationError = error.localizedDescription }
    }

    private func split(_ value: String) -> [String] {
        value.components(separatedBy: CharacterSet(charactersIn: "、,，/;；\n "))
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
    }
    private static let iso: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter(); formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]; return formatter
    }()
}

/// D1–D4 · 差一个（自然语言意图 → 澄清 → 意图卡 → 发布入池）。
/// 视觉对齐 2026-08-12 Lulu 亮色稿 mobile-ios.html#/s/D1。
struct IntentComposerView: View {
    @StateObject private var model: IntentComposerViewModel
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    @FocusState private var focused: Bool
    @State private var voiceStatus: String?
    @State private var restoredRecovery = false
    @State private var fineTuning = false

    init(repository: IntentRepository, competitionID: String? = nil, preset: IntentPreset? = nil) {
        _model = StateObject(wrappedValue: IntentComposerViewModel(repository: repository, competitionID: competitionID, preset: preset))
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(
                    eyebrow: model.competitionID == nil ? "一句话发起" : "赛事组队",
                    title: "差一个，就说一句"
                )
                inputPanel
                phaseContent
                if case .editing = model.phase {
                    if model.competitionID == nil {
                        OMButton("熟练了？直接发起具体局", kind: .text, small: true) {
                            router.push(.initiateGathering)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, OMTheme.Spacing.s1)
                        .accessibilityIdentifier("intent-direct-initiate")
                    }
                    LuluView(clip: .homeIdle, placement: .empty)
                        .frame(maxWidth: .infinity)
                        .padding(.top, OMTheme.Spacing.s6)
                }
                if let error = model.operationError {
                    OMCard { OMG5StateView(state: .networkError, message: error) }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .scrollDismissesKeyboard(.interactively)
        .background(OMPageBackground())
        .onChange(of: focused) { _, value in if value { environment.motion.trigger(.intentFocused) } }
        .onChange(of: environment.speech.transcript) { _, value in if !value.isEmpty { model.text = value } }
        .onChange(of: environment.speech.errorMessage) { _, value in if let value { voiceStatus = value } }
        .onDisappear { environment.speech.stop() }
        .task {
            guard !restoredRecovery else { return }
            restoredRecovery = true
            // UI 测试要求确定性输入环境，跳过草稿恢复（否则每次启动叠加上次文本）。
            guard !ProcessInfo.processInfo.arguments.contains("-UI_TESTING") else { return }
            let scope = await environment.auth.cacheScope()
            if let draft = environment.recovery.draft(for: scope) { await model.restore(draft) }
        }
        .onReceive(model.objectWillChange) { _ in
            Task {
                await Task.yield()
                await persistRecovery()
            }
        }
        .toolbar { ToolbarItemGroup(placement: .keyboard) { Spacer(); Button("完成") { focused = false } } }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-D1-intent")
    }

    private var inputPanel: some View {
        OMCard {
            TextEditor(text: $model.text).focused($focused).scrollContentBackground(.hidden)
                .frame(minHeight: 108)
                .font(OMTheme.TypeToken.title3)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.trailing, 44)
                .accessibilityIdentifier("intent-text-input")
                .overlay(alignment: .topLeading) {
                    if model.text.isEmpty {
                        Text("例如：周六晚上珠海校区，差一个会打双打的同学")
                            .font(OMTheme.TypeToken.title3)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                            .allowsHitTesting(false)
                            .padding(.top, 8)
                            .padding(.leading, 5)
                            .padding(.trailing, 44)
                    }
                }
                .overlay(alignment: .bottomTrailing) { voiceButton }
            if let voiceStatus {
                OMTextRole.cap(voiceStatus)
                    .padding(.top, OMTheme.Spacing.s1)
            }
            if environment.permissions.denied.contains(.microphone) || environment.permissions.denied.contains(.speech) {
                OMButton("语音权限未开启，去设置", kind: .text, small: true, fillsWidth: false) {
                    environment.permissions.openSystemSettings()
                }
            }
            OMDivider()
            HStack(spacing: 8) {
                Image(systemName: "quote.opening")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.yolkBorder)
                TextField("一句话心情（可选）", text: $model.moodNote)
                    .font(OMTheme.TypeToken.callout)
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .onChange(of: model.moodNote) { _, value in
                        if value.count > 60 { model.moodNote = String(value.prefix(60)) }
                    }
                    .accessibilityIdentifier("intent-mood-note-input")
            }
        }
    }

    /// 输入框右下角的语音圆钮：录音中变停止样式。
    private var voiceButton: some View {
        Button {
            Task { await toggleVoice() }
        } label: {
            Image(systemName: environment.speech.isRecording ? "stop.fill" : "mic")
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(OMTheme.ColorToken.ink)
                .frame(width: 38, height: 38)
                .background(environment.speech.isRecording ? OMTheme.ColorToken.yolk : OMTheme.ColorToken.paper)
                .clipShape(Circle())
                .overlay {
                    Circle().stroke(
                        environment.speech.isRecording ? OMTheme.ColorToken.yolkBorder : OMTheme.ColorToken.line,
                        lineWidth: OMTheme.Radius.borderWidth
                    )
                }
        }
        .buttonStyle(OMButtonPressStyle())
        .accessibilityLabel(environment.speech.isRecording ? "停止转写" : "语音输入")
        .accessibilityIdentifier("intent-voice-button")
    }

    @ViewBuilder private var phaseContent: some View {
        switch model.phase {
        case .editing:
            OMButton("整理成意图卡", icon: .spark, disabledReason: model.text.trimmingCharacters(in: .whitespaces).isEmpty ? "先输入这次想做的事" : nil) {
                environment.motion.trigger(.intentCompileStarted)
                Task { await model.compile() }
            }
            .padding(.top, OMTheme.Spacing.s3)
            .accessibilityIdentifier("intent-compile-button")
            if !model.text.trimmingCharacters(in: .whitespaces).isEmpty {
                OMTextRole.cap("噜噜会整理成一张匿名意图卡，确认后才开始找人。")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
            }
        case .compiling:
            OMCard {
                VStack(spacing: OMTheme.Spacing.s3) {
                    LuluView(clip: .homeThinking, placement: .confirm)
                    OMG5StateView(state: .loading, message: "噜噜正在理解…")
                }
            }
            .padding(.top, OMTheme.Spacing.s3)
        case let .clarifying(_, questions, round, maxRounds):
            clarification(questions, round: round, maxRounds: maxRounds)
        case let .preview(card), let .publishing(card):
            editor(card)
        case let .published(result):
            OMCard {
                HStack(spacing: 10) {
                    OMSticker("hourglass.png", size: .s44)
                    OMTextRole.t3("已进入\(GatheringStatus(rawValue: result.status)?.displayName ?? "匿名池")")
                    Spacer()
                }
            }
            .padding(.top, OMTheme.Spacing.s3)
            OMButton("查看招募状态", systemIcon: "person.3") { router.push(.gathering(result.gatheringId)) }
                .padding(.top, OMTheme.Spacing.s2)
                .accessibilityIdentifier("intent-view-gathering")
        case let .failed(message):
            OMCard {
                OMG5StateView(state: .networkError, message: message, actionTitle: "重新编辑") {
                    model.phase = .editing
                }
            }
            .padding(.top, OMTheme.Spacing.s3)
        }
    }

    private func clarification(_ questions: [IntentClarificationQuestion], round: Int, maxRounds: Int) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            OMCard {
                HStack {
                    OMChip(text: "澄清 \(round + 1) / \(maxRounds)", kind: .gap)
                    Spacer()
                }
                ForEach(questions) { question in
                    OMTextRole.t3(question.prompt).padding(.top, OMTheme.Spacing.s3)
                    if question.key == "availability" {
                        DatePicker("开始", selection: $model.availabilityStart, in: Date()..., displayedComponents: [.date, .hourAndMinute])
                            .font(OMTheme.TypeToken.callout)
                            .tint(OMTheme.ColorToken.ink)
                            .padding(.top, OMTheme.Spacing.s2)
                        DatePicker("结束", selection: $model.availabilityEnd, in: model.availabilityStart..., displayedComponents: [.date, .hourAndMinute])
                            .font(OMTheme.TypeToken.callout)
                            .tint(OMTheme.ColorToken.ink)
                    } else {
                        TextField("例如：前端、产品", text: $model.clarificationAnswer, axis: .vertical)
                            .omInputStyle(multiline: true)
                            .padding(.top, OMTheme.Spacing.s2)
                    }
                }
            }
            .padding(.top, OMTheme.Spacing.s3)
            OMButton("继续", icon: .arrow) {
                environment.motion.trigger(.intentCompileStarted)
                Task { await model.answer(questions, round: round) }
            }
            .padding(.top, OMTheme.Spacing.s2)
            .accessibilityIdentifier("intent-clarification-continue")
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-D2-clarification")
    }

    /// D3 · 确认优先：先呈现一张已理解好的意图卡摘要；想改的人再展开微调。
    private func editor(_ card: IntentCard) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            OMSection(title: "噜噜整理好了，确认一下")
            summaryCard(card)
            fineTuneToggle
            if fineTuning {
                fineTuneEditors(card)
            }
            OMButton(
                "开始找人",
                icon: .spark,
                loading: model.saving || { if case .publishing = model.phase { true } else { false } }()
            ) {
                Task {
                    let scope = await environment.auth.cacheScope()
                    model.beginPublish()
                    environment.recovery.updateIntentDraft(model.recoveryDraft(pendingAction: "publish"), scope: scope)
                    if await model.publish(card) {
                        environment.recovery.clearIntentDraft(scope: scope)
                        environment.motion.trigger(.intentPublished)
                    }
                }
            }
            .padding(.top, OMTheme.Spacing.s3)
            .accessibilityIdentifier("intent-publish-button")
            OMTextRole.cap("发布后进入匿名池；找齐并确认前，不会透露任何人的身份。")
                .frame(maxWidth: .infinity)
                .multilineTextAlignment(.center)
                .padding(.top, OMTheme.Spacing.s2)
            OMButton("撤回这张卡", kind: .text, small: true) {
                Task { await model.withdraw(card) }
            }
            .frame(maxWidth: .infinity)
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-D3-intent-editor")
    }

    /// 意图卡摘要：像一张车票，事实一屏看完。
    private func summaryCard(_ card: IntentCard) -> some View {
        OMCard {
            HStack(spacing: 6) {
                OMChip(text: card.gatheringType, kind: .gap)
                OMChip(text: "匿名意图卡", kind: .soft)
                Spacer()
            }
            Text(model.goal.isEmpty ? card.goal : model.goal)
                .font(OMTheme.TypeToken.title3.weight(.bold))
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.top, OMTheme.Spacing.s3)
            if !model.moodNote.trimmingCharacters(in: .whitespaces).isEmpty {
                MoodNoteQuote(text: model.moodNote)
                    .padding(.top, OMTheme.Spacing.s2)
            }
            OMDivider()
            VStack(alignment: .leading, spacing: 9) {
                factRow("clock", Self.windowLabel(start: model.startAt, end: model.endAt))
                factRow("mappin.and.ellipse", model.campus.isEmpty ? "校区待定" : model.campus)
                factRow(
                    "person.2",
                    model.minimumSize == model.targetSize
                        ? "\(model.targetSize) 人 · \(Self.intensityLabel(model.intensity))"
                        : "\(model.minimumSize)–\(model.targetSize) 人 · \(Self.intensityLabel(model.intensity))"
                )
                factRow("theatermasks", model.socialMode == "after_full" ? "满员确认后互见身份" : "最低人数确认后互见身份")
                if model.sameGenderOnly {
                    factRow("checkmark.shield", "只匹配同性成员")
                }
            }
            // 能力标签是画像内部数据，不在摘要露出；只展示「还需要谁」这个找人关键信息。
            let roleChips = Self.displayTags(model.rolesText)
            if !roleChips.isEmpty {
                OMDivider()
                chipsRow(title: "还需要", items: roleChips)
            }
            if let fit = model.tasteFitLabel, !fit.isEmpty {
                OMChip(text: fit, kind: .gap).padding(.top, OMTheme.Spacing.s3)
            }
            if !model.recruitHints.isEmpty {
                OMDivider()
                OMTextRole.t3("招什么样的人")
                ForEach(model.recruitHints, id: \.self) { hint in
                    OMTextRole.foot(hint).padding(.top, 4)
                }
            }
        }
        .accessibilityIdentifier("intent-summary-card")
    }

    private var fineTuneToggle: some View {
        Button {
            withAnimation(OMTheme.Motion.medium) { fineTuning.toggle() }
        } label: {
            HStack(spacing: 6) {
                Image(systemName: "slider.horizontal.3")
                    .font(.system(size: 13, weight: .semibold))
                Text(fineTuning ? "收起调整" : "调整细节")
                    .font(OMTheme.TypeToken.callout.weight(.semibold))
                Image(systemName: "chevron.down")
                    .font(.system(size: 11, weight: .bold))
                    .rotationEffect(.degrees(fineTuning ? 180 : 0))
            }
            .foregroundStyle(OMTheme.ColorToken.mist)
            .frame(maxWidth: .infinity, minHeight: 40)
            .contentShape(Rectangle())
        }
        .buttonStyle(OMButtonPressStyle())
        .padding(.top, OMTheme.Spacing.s1)
        .accessibilityIdentifier("intent-fine-tune-toggle")
    }

    /// 展开后的微调编辑区：与摘要同源字段，保存后回写摘要。
    @ViewBuilder private func fineTuneEditors(_ card: IntentCard) -> some View {
        OMCard {
            OMTextRole.t3("内容")
            TextField("目标", text: $model.goal, axis: .vertical)
                .omInputStyle(multiline: true)
                .padding(.top, OMTheme.Spacing.s2)
            TextField("一句话心情（匿名可见，可留空）", text: $model.moodNote)
                .omInputStyle()
                .padding(.top, OMTheme.Spacing.s2)
            TextField("我的能力标签（顿号分隔）", text: $model.capabilitiesText)
                .omInputStyle()
                .padding(.top, OMTheme.Spacing.s2)
            TextField("所需角色（顿号分隔）", text: $model.rolesText)
                .omInputStyle()
                .padding(.top, OMTheme.Spacing.s2)
        }
        .accessibilityIdentifier("intent-capabilities-editor")
        OMCard {
            OMTextRole.t3("时间与校区")
            TextField("校区", text: $model.campus)
                .omInputStyle()
                .padding(.top, OMTheme.Spacing.s2)
            DatePicker("开始", selection: $model.startAt, in: Date()..., displayedComponents: [.date, .hourAndMinute])
                .font(OMTheme.TypeToken.callout)
                .tint(OMTheme.ColorToken.ink)
                .padding(.top, OMTheme.Spacing.s2)
            DatePicker("结束", selection: $model.endAt, in: model.startAt..., displayedComponents: [.date, .hourAndMinute])
                .font(OMTheme.TypeToken.callout)
                .tint(OMTheme.ColorToken.ink)
        }
        .accessibilityIdentifier("intent-availability-editor")
        OMCard {
            OMTextRole.t3("人数与投入")
            VStack(spacing: 0) {
                OMStepperRow(title: "最低人数", value: $model.minimumSize, range: 2...20)
                OMStepperRow(title: "目标人数", value: $model.targetSize, range: 2...20)
            }
            .padding(.top, OMTheme.Spacing.s2)
            OMSeg(
                items: ["light", "balanced", "focused"],
                label: { Self.intensityLabel($0) },
                selection: $model.intensity
            )
            .padding(.top, OMTheme.Spacing.s2)
        }
        .accessibilityIdentifier("intent-roles-editor")
        OMCard {
            OMTextRole.t3("身份安全")
            OMSeg(
                items: ["after_full", "after_confirmed"],
                label: { $0 == "after_full" ? "满员确认后" : "最低人数确认后" },
                selection: $model.socialMode
            )
            .padding(.top, OMTheme.Spacing.s2)
            HStack {
                OMTextRole.t3("本次只匹配同性成员")
                Spacer()
                OMSwitch(isOn: $model.sameGenderOnly)
            }
            .padding(.top, OMTheme.Spacing.s3)
        }
        .accessibilityIdentifier("intent-safety-editor")
        OMButton(model.saving ? "保存中…" : "保存调整", kind: .ghost, small: true, loading: model.saving) {
            Task {
                if await model.save(card) != nil {
                    withAnimation(OMTheme.Motion.medium) { fineTuning = false }
                }
            }
        }
        .padding(.top, OMTheme.Spacing.s2)
        .accessibilityIdentifier("intent-save-edits")
    }

    private func factRow(_ systemIcon: String, _ text: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 9) {
            Image(systemName: systemIcon)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(OMTheme.ColorToken.yolkBorder)
                .frame(width: 18)
            Text(text)
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.ink)
        }
    }

    private func chipsRow(title: String, items: [String]) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            OMTextRole.cap(title)
            FlowChips(items: items)
        }
    }

    /// 摘要卡上的标签：过滤 taste: 等内部画像标签，最多露出 6 个。
    private static func displayTags(_ value: String) -> [String] {
        let visible = splitTags(value).filter { !$0.hasPrefix("taste:") }
        if visible.count > 6 {
            return Array(visible.prefix(6)) + ["+\(visible.count - 6)"]
        }
        return visible
    }

    private static func splitTags(_ value: String) -> [String] {
        value.components(separatedBy: CharacterSet(charactersIn: "、,，/;；\n "))
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
    }

    /// 后端 intensity 枚举 → 用户可读文案；兼容历史草稿里的中文旧值。
    static func intensityLabel(_ value: String) -> String {
        switch value {
        case "light", "轻松参与": "轻松参与"
        case "balanced", "认真参与": "认真参与"
        case "focused", "高强度冲刺": "高强度冲刺"
        default: value
        }
    }

    static func normalizedIntensity(_ value: String) -> String {
        switch value {
        case "轻松参与": "light"
        case "认真参与": "balanced"
        case "高强度冲刺": "focused"
        default: value
        }
    }

    /// 「8月13日（周四）19:00–22:00」；跨天时展示两端完整时间。
    private static func windowLabel(start: Date, end: Date) -> String {
        let calendar = Calendar.current
        if calendar.isDate(start, inSameDayAs: end) {
            return "\(dayFormatter.string(from: start)) \(timeFormatter.string(from: start))–\(timeFormatter.string(from: end))"
        }
        return "\(dayFormatter.string(from: start)) \(timeFormatter.string(from: start)) – \(dayFormatter.string(from: end)) \(timeFormatter.string(from: end))"
    }

    private static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "M月d日（EEE）"
        return formatter
    }()

    private static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "HH:mm"
        return formatter
    }()

    private func toggleVoice() async {
        if environment.speech.isRecording { environment.speech.stop(); voiceStatus = "转写已停止"; return }
        guard await environment.permissions.requestVoice() else { voiceStatus = "语音权限未开启，可到系统设置恢复"; return }
        do { try environment.speech.start(seed: model.text); voiceStatus = "正在实时转写…" }
        catch { voiceStatus = error.localizedDescription }
    }

    private func persistRecovery() async {
        let scope = await environment.auth.cacheScope()
        environment.recovery.updateIntentDraft(model.recoveryDraft(), scope: scope)
    }
}
