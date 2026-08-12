import SwiftUI
import UIKit

@MainActor final class TasteImportViewModel: ObservableObject {
    enum Phase {
        case intro
        case starting
        case status(TasteImportStatus)
        case ready(TasteImportStatus, TasteProfileResult)
        case questions(TasteImportStatus, TasteQuestionSet)
        /// Answers submitted; waiting for rule refine + AI rewrite.
        case refining(TasteImportStatus)
        case deleted
        case failed(String)
    }

    @Published var phase: Phase = .intro
    @Published var selections: [String: String] = [:]
    @Published var submitting = false
    @Published var phone = ""
    @Published var countryCode = "86"
    @Published var verificationCode = ""
    @Published var phoneWorking = false
    @Published var phoneError: String?
    @Published var phoneStatus: TastePhoneLoginStatus?
    @Published var existingProfile: TasteProfileResult?
    /// Prefer opening the quiz once after first READY (user can skip).
    @Published var offeredQuizForImport: String?
    @Published var shareText = ""
    @Published var usingLink = true

    private let repository: TasteImportRepository
    private var polling: Task<Void, Never>?

    init(repository: TasteImportRepository) { self.repository = repository }

    func loadExisting() async {
        existingProfile = try? await repository.currentProfile()
    }

    func analyzeFromLink() async {
        let text = shareText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard text.count >= 8, !submitting, polling == nil else { return }
        usingLink = true
        submitting = true
        phase = .starting
        defer { submitting = false }
        do {
            let value = try await repository.fromLink(text, force: true)
            // Match the judge page: show the persona card first, quiz stays optional.
            offeredQuizForImport = value.id
            await applyStatus(value)
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    func start(force: Bool = false) async {
        guard polling == nil else { return }
        usingLink = false
        phase = .starting
        do {
            // Prefer QR-wait entry from docs/17; fall back to async create.
            let value: TasteImportStatus
            do {
                value = try await repository.createWithQR(force: force, waitSeconds: 10)
            } catch {
                value = try await repository.create(force: force)
            }
            await applyStatus(value)
            if !isTerminal(value.status) || value.status == "QR_EXPIRED" {
                if value.status != "QR_EXPIRED" { poll(id: value.id) }
            }
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    func poll(id: String) {
        polling?.cancel()
        polling = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                do {
                    let value = try await repository.status(id)
                    await applyStatus(value)
                    if ["READY", "FAILED", "CANCELLED"].contains(value.status) { break }
                    if value.status == "QR_EXPIRED" { break }
                    let delay = pollDelay(for: value.status)
                    try? await Task.sleep(for: .seconds(delay))
                } catch {
                    phase = .failed(error.localizedDescription)
                    break
                }
            }
            polling = nil
        }
    }

    func cancel(_ id: String) async {
        do { await applyStatus(try await repository.cancel(id)) }
        catch { phase = .failed(error.localizedDescription) }
        polling?.cancel(); polling = nil
    }

    func refreshQR(_ id: String) async {
        do {
            let value = try await repository.refreshQR(id)
            await applyStatus(value)
            poll(id: id)
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    func requestPhoneCode(_ status: TasteImportStatus) async {
        guard !phoneWorking else { return }
        let normalizedPhone = phone.filter(\.isNumber)
        let normalizedCountryCode = countryCode.filter(\.isNumber)
        guard (5...20).contains(normalizedPhone.count), (1...4).contains(normalizedCountryCode.count) else {
            phoneError = "请输入有效的国家或地区代码与手机号"
            return
        }
        phoneWorking = true
        phoneError = nil
        defer {
            phone = ""
            phoneWorking = false
        }
        do {
            phoneStatus = try await repository.requestPhoneCode(
                status.id, phone: normalizedPhone, countryCode: normalizedCountryCode
            )
            await applyStatus(try await repository.status(status.id))
            if polling == nil { poll(id: status.id) }
        } catch {
            phoneError = error.localizedDescription
        }
    }

    func refreshPhoneStatus(_ status: TasteImportStatus) async {
        guard !phoneWorking else { return }
        do { phoneStatus = try await repository.phoneStatus(status.id) }
        catch { phoneError = error.localizedDescription }
    }

    func submitPhoneCode(_ status: TasteImportStatus) async {
        guard !phoneWorking else { return }
        let normalizedCode = verificationCode.filter(\.isNumber)
        guard (4...8).contains(normalizedCode.count) else {
            phoneError = "请输入 4–8 位短信验证码"
            return
        }
        phoneWorking = true
        phoneError = nil
        defer {
            verificationCode = ""
            phoneWorking = false
        }
        do {
            phoneStatus = try await repository.submitPhoneCode(status.id, code: normalizedCode)
            _ = try await repository.verifyLogin(status.id, waitSeconds: 2)
            let current = try await repository.status(status.id)
            await applyStatus(current)
            if !isTerminal(current.status), polling == nil {
                poll(id: status.id)
            }
        } catch {
            phoneError = error.localizedDescription
        }
    }

    func openOptionalQuestions(from status: TasteImportStatus) async {
        guard !submitting else { return }
        submitting = true
        defer { submitting = false }
        do {
            // Prefer embedded JSON on status; otherwise fetch GET .../questions.
            let questions = try await loadQuestionPackage(for: status)
            selections = [:]
            phase = .questions(status, questions)
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    func submit(_ status: TasteImportStatus, questions: TasteQuestionSet) async {
        guard !submitting else { return }
        let minCount = questions.minimumSelections
        let answers = questions.questions.compactMap { question in
            selections[question.id].map { TasteQuizAnswer(questionId: question.id, optionId: $0) }
        }
        guard answers.count >= minCount else { return }
        submitting = true
        phase = .refining(status)
        defer { submitting = false }
        do {
            // POST answers JSON → backend rule refine + AI re-narrate.
            let result = try await repository.submitAnswers(status.id, answers: answers)
            existingProfile = result
            let refreshed = try await repository.status(status.id)
            if let serverResult = refreshed.result {
                phase = .ready(refreshed, serverResult)
            } else {
                phase = .ready(refreshed, result)
            }
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    private func loadQuestionPackage(for status: TasteImportStatus) async throws -> TasteQuestionSet {
        if let embedded = status.questions, !embedded.questions.isEmpty {
            return embedded
        }
        return try await repository.questions(status.id)
    }

    func deleteProfile() async {
        guard !submitting else { return }
        submitting = true
        defer { submitting = false }
        do {
            _ = try await repository.deleteProfile()
            existingProfile = nil
            phase = .deleted
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    deinit { polling?.cancel() }

    private func applyStatus(_ value: TasteImportStatus) async {
        if value.status == "READY" {
            let result: TasteProfileResult?
            if let embedded = value.result {
                result = embedded
            } else {
                result = try? await repository.currentProfile()
            }
            if let result {
                existingProfile = result
                // First time READY + not calibrated → auto-load quiz JSON for refinement.
                if !result.calibrated,
                   value.questionCount > 0,
                   offeredQuizForImport != value.id {
                    offeredQuizForImport = value.id
                    if let quiz = try? await loadQuestionPackage(for: value), !quiz.questions.isEmpty {
                        selections = [:]
                        phase = .questions(value, quiz)
                        return
                    }
                }
                phase = .ready(value, result)
                return
            }
        }
        // Legacy in-flight tasks only.
        if value.status == "NEEDS_CONFIRMATION" {
            do {
                let questions = try await loadQuestionPackage(for: value)
                selections = [:]
                phase = .questions(value, questions)
                return
            } catch {
                // Fall through to status view if questions are unavailable.
            }
        }
        phase = .status(value)
    }

    private func isTerminal(_ status: String) -> Bool {
        ["READY", "FAILED", "CANCELLED", "QR_EXPIRED"].contains(status)
    }

    private func pollDelay(for status: String) -> Double {
        switch status {
        case "COLLECTING", "ANALYZING", "RESOLVING_PROFILE", "AUTHENTICATED":
            return 2
        case "WAITING_SCAN", "PREPARING_QR", "QR_SCANNED", "PHONE_REQUIRED", "WAITING_SMS_CODE":
            return 2
        default:
            return 2
        }
    }
}

/// 抖音兴趣画像导入（可选）
/// 主链路：粘贴主页链接 → 喜欢+收藏 HTTP 采集 → READY 画像可用 → 可选细化题
/// 扫码导入仍作为次要入口保留。
struct TasteImportView: View {
    @StateObject private var model: TasteImportViewModel
    init(repository: TasteImportRepository) {
        _model = StateObject(wrappedValue: TasteImportViewModel(repository: repository))
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(title: "导入兴趣画像")
                    .accessibilityElement(children: .contain)
                    .accessibilityIdentifier("screen-taste-import-header")

                switch model.phase {
                case .intro:
                    introContent
                case .starting:
                    OMCard {
                        OMG5StateView(
                            state: .loading,
                            message: model.usingLink ? "噜噜正在看你的喜欢和收藏…" : "正在创建导入会话…"
                        )
                    }
                case .refining:
                    OMCard {
                        OMG5StateView(
                            state: .loading,
                            message: "已收到你的回答，AI 正在精修兴趣画像…"
                        )
                    }
                    .accessibilityIdentifier("taste-quiz-refining")
                case .deleted:
                    deletedContent
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            model.phase = .intro
                        }
                    }
                case let .questions(status, questions):
                    questionsContent(status, questions)
                case let .ready(status, result):
                    readyContent(status, result)
                case let .status(status):
                    statusContent(status)
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.loadExisting() }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-taste-import")
    }

    @ViewBuilder private var introContent: some View {
        if let existing = model.existingProfile {
            tasteResultCard(existing, title: "当前兴趣画像")
            OMButton("重新粘贴链接导入", kind: .ghost) {
                model.existingProfile = nil
                model.shareText = ""
                model.phase = .intro
            }
            .padding(.top, OMTheme.Spacing.s2)
            OMButton("删除抖音兴趣画像", systemIcon: "trash", kind: .dark, loading: model.submitting) {
                Task { await model.deleteProfile() }
            }
            .padding(.top, OMTheme.Spacing.s2)
        } else {
            OMCard {
                OMTextRole.t3("粘贴主页分享链接")
                OMTextRole.foot("噜噜会一起看你最近的喜欢和收藏。把「喜欢」和收藏里的「视频」设为公开后再贴。")
                    .padding(.top, OMTheme.Spacing.s2)
                VStack(alignment: .leading, spacing: 6) {
                    Text("1. 打开抖音，点底部「我」")
                    Text("2. 点自己的抖音号，进入抖音码页面")
                    Text("3. 点右上角分享箭头，再选「复制链接」")
                    Text("4. 打开「设置 → 隐私与政策 → 收藏」，把里面的「视频」设为公开")
                    Text("5. 把主页「喜欢」也设为公开，然后粘贴到下面")
                }
                .font(OMTheme.TypeToken.footnote)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .padding(.top, OMTheme.Spacing.s3)
            }
            TextEditor(text: $model.shareText)
                .omInputStyle(multiline: true)
                .frame(minHeight: 96)
                .padding(.top, OMTheme.Spacing.s3)
                .accessibilityIdentifier("taste-share-input")
            OMButton(
                "让噜噜看看",
                systemIcon: "sparkles",
                loading: model.submitting,
                disabledReason: model.shareText.trimmingCharacters(in: .whitespacesAndNewlines).count < 8
                    ? "先粘贴主页分享链接"
                    : nil
            ) {
                Task { await model.analyzeFromLink() }
            }
            .padding(.top, OMTheme.Spacing.s3)
            OMButton("改用扫码导入", systemIcon: "qrcode", kind: .ghost) {
                Task { await model.start() }
            }
            .padding(.top, OMTheme.Spacing.s2)
        }
    }

    @ViewBuilder private var deletedContent: some View {
        OMCard {
            HStack(spacing: 10) {
                OMSticker("sparkle-wand.png", size: .s44)
                OMTextRole.t3("抖音兴趣画像已删除")
                Spacer()
            }
        }
        OMButton("重新导入") { model.phase = .intro }
    }

    @ViewBuilder private func questionsContent(_ status: TasteImportStatus, _ questions: TasteQuestionSet) -> some View {
        let minCount = questions.minimumSelections
        OMCard {
            OMTextRole.t2(questions.optional == true ? "答几题，让画像更准" : "确认你的兴趣")
            OMTextRole.foot(
                questions.intro
                    ?? "服务端下发 \(questions.questions.count) 道单选题 JSON；答完后 AI 会按你的选择再精修画像。"
            )
            .padding(.top, OMTheme.Spacing.s2)
            if let provisional = status.result ?? model.existingProfile, !provisional.summary.isEmpty {
                OMTextRole.cap("当前草稿：\(provisional.summary)")
                    .padding(.top, OMTheme.Spacing.s2)
                    .lineLimit(3)
            }
            OMTextRole.cap("已选 \(model.selections.count) / 需至少 \(minCount) 题 · schema \(questions.schemaVersion ?? "taste-quiz-v1")")
                .padding(.top, OMTheme.Spacing.s2)
        }
        .accessibilityIdentifier("taste-quiz-package")
        ForEach(questions.questions) { question in
            OMCard {
                OMTextRole.t3(question.prompt)
                ForEach(question.options) { option in
                    let selected = model.selections[question.id] == option.id
                    Button {
                        model.selections[question.id] = option.id
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: selected ? "largecircle.fill.circle" : "circle")
                                .foregroundStyle(selected ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
                            Text(option.label)
                                .foregroundStyle(OMTheme.ColorToken.ink)
                            Spacer()
                        }
                        .font(OMTheme.TypeToken.callout)
                        .padding(.vertical, 6)
                    }
                    .buttonStyle(.plain)
                    .padding(.top, OMTheme.Spacing.s2)
                    .accessibilityIdentifier("taste-quiz-option-\(option.id)")
                }
            }
            .accessibilityIdentifier("taste-quiz-question-\(question.id)")
        }
        OMButton(
            "提交并让 AI 精修",
            systemIcon: "sparkles",
            loading: model.submitting,
            disabledReason: model.selections.count < minCount ? "至少完成 \(minCount) 道单选题" : nil
        ) {
            Task { await model.submit(status, questions: questions) }
        }
        .accessibilityIdentifier("taste-quiz-submit")
        OMButton("跳过，先用当前画像", kind: .ghost) {
            if let result = status.result ?? model.existingProfile {
                model.phase = .ready(status, result)
            } else {
                model.phase = .status(status)
            }
        }
        .padding(.top, OMTheme.Spacing.s2)
        OMButton("取消本次导入", kind: .text, small: true, fillsWidth: false) {
            Task { await model.cancel(status.id) }
        }
    }

    @ViewBuilder private func readyContent(_ status: TasteImportStatus, _ result: TasteProfileResult) -> some View {
        tasteResultCard(result, title: result.calibrated ? "兴趣画像 · 已细化" : "兴趣画像已就绪")
        if !result.calibrated {
            OMButton("可选 · 答细化题", kind: .ghost, loading: model.submitting) {
                Task { await model.openOptionalQuestions(from: status) }
            }
            .padding(.top, OMTheme.Spacing.s2)
        }
        OMButton("删除抖音兴趣画像", systemIcon: "trash", kind: .dark, loading: model.submitting) {
            Task { await model.deleteProfile() }
        }
        .padding(.top, OMTheme.Spacing.s2)
        OMButton("重新导入", kind: .text, small: true, fillsWidth: false) {
            model.shareText = ""
            model.phase = .intro
        }
    }

    @ViewBuilder private func statusContent(_ status: TasteImportStatus) -> some View {
        OMCard {
            OMTextRole.t3(statusLine(status))
            if let image = image(status.qrImageDataUrl) {
                image.resizable().interpolation(.none).scaledToFit()
                    .padding(OMTheme.Spacing.s3)
                    .frame(maxWidth: .infinity)
                    .background(OMTheme.ColorToken.card, in: RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                    .overlay {
                        RoundedRectangle(cornerRadius: OMTheme.Radius.small)
                            .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                    }
                    .padding(.top, OMTheme.Spacing.s3)
            }
            if let message = progressMessage(status) {
                OMTextRole.foot(message).padding(.top, OMTheme.Spacing.s2)
            }
            if let collection = status.collection {
                OMTextRole.cap("已采集 \(collection.itemsCollected) 条公开兴趣信号 · \(collection.apiPages) 页")
                    .padding(.top, OMTheme.Spacing.s2)
            }
            if let err = status.error?["message"], !err.isEmpty {
                OMTextRole.foot(err).padding(.top, OMTheme.Spacing.s2)
            }
        }
        if status.status == "PHONE_REQUIRED" || status.status == "QR_SCANNED" {
            phoneEntry(status)
        }
        if status.status == "WAITING_SMS_CODE" {
            verificationEntry(status)
        }
        if status.status == "QR_EXPIRED" {
            OMButton("刷新二维码", systemIcon: "arrow.clockwise") {
                Task { await model.refreshQR(status.id) }
            }
        }
        if !["READY", "FAILED", "CANCELLED", "QR_EXPIRED"].contains(status.status) {
            OMButton("取消本次导入", kind: .text, small: true, fillsWidth: false) {
                Task { await model.cancel(status.id) }
            }
        }
        if status.status == "FAILED" || status.status == "CANCELLED" {
            OMButton("重新开始") { Task { await model.start(force: true) } }
        }
    }

    @ViewBuilder private func tasteResultCard(_ result: TasteProfileResult, title: String) -> some View {
        OMCard {
            VStack(alignment: .leading, spacing: 0) {
                HStack(alignment: .top, spacing: OMTheme.Spacing.s3) {
                    VStack(alignment: .leading, spacing: 0) {
                        OMTextRole.cap(title)
                        Text(result.primaryTag.label)
                            .font(OMTheme.TypeToken.title1)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .padding(.top, OMTheme.Spacing.s2)
                        if !result.secondaryTags.isEmpty {
                            OMFlowLayout {
                                ForEach(result.secondaryTags) { tag in
                                    personaChip(tag.label)
                                }
                            }
                            .padding(.top, OMTheme.Spacing.s3)
                        }
                    }
                    Spacer(minLength: 0)
                    LuluView(clip: .homeIdle, placement: .header)
                        .accessibilityHidden(true)
                }
                if !result.summary.isEmpty {
                    Text(result.summary)
                        .font(OMTheme.TypeToken.callout)
                        .foregroundStyle(OMTheme.ColorToken.ink60)
                        .lineSpacing(3)
                        .padding(.top, OMTheme.Spacing.s3)
                }
                if let persona = result.persona, !persona.isEmpty {
                    Text("“\(persona)”")
                        .font(OMTheme.TypeToken.footnote)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .lineSpacing(2)
                        .padding(.top, OMTheme.Spacing.s2)
                }
                if !result.interestFacets.isEmpty {
                    OMTextRole.t3("子兴趣").padding(.top, OMTheme.Spacing.s4)
                    OMFlowLayout {
                        ForEach(result.interestFacets) { facet in
                            personaChip(facet.label)
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
                if !result.interestDomains.isEmpty {
                    OMTextRole.t3("兴趣领域").padding(.top, OMTheme.Spacing.s4)
                    OMFlowLayout {
                        ForEach(result.interestDomains) { domain in
                            personaChip(domain.label)
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
                if !result.matchingHints.isEmpty {
                    OMTextRole.t3("成局提示").padding(.top, OMTheme.Spacing.s4)
                    ForEach(result.matchingHints, id: \.self) { hint in
                        OMTextRole.cap("· \(hint)").padding(.top, 2)
                    }
                }
            }
        }
        .accessibilityIdentifier("taste-profile-result")
    }

    private func personaChip(_ label: String) -> some View {
        Text(label)
            .font(OMTheme.TypeToken.footnote.weight(.semibold))
            .foregroundStyle(OMTheme.ColorToken.ink)
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(OMTheme.ColorToken.yolk14)
            .clipShape(Capsule())
            .overlay {
                Capsule().stroke(OMTheme.ColorToken.yolkBorder, lineWidth: OMTheme.Radius.borderWidth)
            }
    }

    @ViewBuilder private func phoneEntry(_ status: TasteImportStatus) -> some View {
        OMCard {
            OMTextRole.t3("完成抖音手机号验证")
            HStack(spacing: 10) {
                TextField("区号", text: $model.countryCode)
                    .keyboardType(.numberPad)
                    .textContentType(.telephoneNumber)
                    .frame(width: 72)
                    .omInputStyle()
                    .accessibilityLabel("国家或地区代码")
                TextField("手机号", text: $model.phone)
                    .keyboardType(.phonePad)
                    .textContentType(.telephoneNumber)
                    .privacySensitive()
                    .omInputStyle()
                    .accessibilityIdentifier("taste-phone-input")
            }
            .padding(.top, OMTheme.Spacing.s3)
            if let error = model.phoneError {
                OMTextRole.foot(error).padding(.top, OMTheme.Spacing.s2)
            }
            OMButton(
                "发送短信验证码", systemIcon: "message.badge",
                loading: model.phoneWorking,
                disabledReason: model.phone.filter(\.isNumber).count < 5 ? "请输入手机号" : nil
            ) { Task { await model.requestPhoneCode(status) } }
            .padding(.top, OMTheme.Spacing.s3)
            .accessibilityIdentifier("taste-send-phone-code")
        }
    }

    @ViewBuilder private func verificationEntry(_ status: TasteImportStatus) -> some View {
        OMCard {
            OMTextRole.t3("输入短信验证码")
            if let masked = model.phoneStatus?.phoneMasked ?? status.progress.phoneMasked {
                OMTextRole.foot("验证码已发送至 \(masked)").padding(.top, OMTheme.Spacing.s2)
            } else {
                OMTextRole.foot("验证码已发送；仅展示服务端返回的脱敏号码。")
                    .padding(.top, OMTheme.Spacing.s2)
            }
            SecureField("4–8 位验证码", text: $model.verificationCode)
                .keyboardType(.numberPad)
                .textContentType(.oneTimeCode)
                .privacySensitive()
                .omInputStyle()
                .padding(.top, OMTheme.Spacing.s3)
                .accessibilityIdentifier("taste-phone-code-input")
            if let error = model.phoneError {
                OMTextRole.foot(error).padding(.top, OMTheme.Spacing.s2)
            }
            OMButton(
                "验证并继续导入", systemIcon: "checkmark.shield",
                loading: model.phoneWorking,
                disabledReason: model.verificationCode.filter(\.isNumber).count < 4 ? "请输入短信验证码" : nil
            ) { Task { await model.submitPhoneCode(status) } }
            .padding(.top, OMTheme.Spacing.s3)
            .accessibilityIdentifier("taste-submit-phone-code")
            OMButton("检查验证码状态", kind: .ghost, small: true, fillsWidth: false) {
                Task { await model.refreshPhoneStatus(status) }
            }
            .padding(.top, OMTheme.Spacing.s2)
            .disabled(model.phoneWorking)
        }
    }

    private func image(_ dataURL: String?) -> Image? {
        guard let dataURL,
              let comma = dataURL.firstIndex(of: ","),
              let data = Data(base64Encoded: String(dataURL[dataURL.index(after: comma)...])),
              let ui = UIImage(data: data)
        else { return nil }
        return Image(uiImage: ui)
    }

    private func progressMessage(_ value: TasteImportStatus) -> String? {
        let message = value.progress.message.trimmingCharacters(in: .whitespacesAndNewlines)
        return message.isEmpty ? nil : message
    }

    private func statusLine(_ value: TasteImportStatus) -> String {
        switch value.status {
        case "PREPARING_QR": return "正在准备二维码"
        case "WAITING_SCAN": return "请用抖音扫码，App 会继续轮询"
        case "QR_SCANNED": return "扫码成功，可能需要手机号验证"
        case "PHONE_REQUIRED": return "抖音要求补充手机号验证"
        case "WAITING_SMS_CODE": return "短信验证码已发送，验证后将自动继续"
        case "AUTHENTICATED": return "已登录，正在识别账号"
        case "RESOLVING_PROFILE": return "正在识别抖音账号"
        case "COLLECTING": return "正在采集公开「喜欢」内容"
        case "ANALYZING": return "正在生成兴趣画像（含 AI 文案）"
        case "NEEDS_CONFIRMATION": return "可选兴趣细化（遗留任务）"
        case "READY": return "兴趣画像已生成"
        case "QR_EXPIRED": return "二维码已过期，请主动刷新"
        case "FAILED": return "本次导入失败，可重试"
        case "CANCELLED": return "本次导入已取消"
        default: return "状态由服务端同步"
        }
    }
}
