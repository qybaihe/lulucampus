import SwiftUI

@MainActor
final class OrganizerViewModel: ObservableObject {
    enum Phase {
        case loading
        case loaded
        case failed(String)
    }

    @Published var phase: Phase = .loading
    @Published var gatherings: [OfficialGatheringSummary] = []
    @Published var templates: [OfficialTemplate] = []
    @Published var working = false
    @Published var message: String?

    private let repository: OrganizerRepository

    init(repository: OrganizerRepository) {
        self.repository = repository
    }

    func load() async {
        phase = .loading
        do {
            async let gatheringRequest = repository.gatherings()
            async let templateRequest = repository.templates()
            gatherings = try await gatheringRequest
            templates = try await templateRequest
            phase = .loaded
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    func createGathering(_ draft: OfficialGatheringDraft) async -> Bool {
        await mutate(success: "官方局已创建") {
            _ = try await repository.createGathering(draft)
        }
    }

    func saveTemplate(id: String?, draft: OfficialTemplateDraft) async -> Bool {
        await mutate(success: id == nil ? "模板已创建" : "模板已更新") {
            if let id {
                _ = try await repository.update(id: id, draft: draft)
            } else {
                _ = try await repository.create(draft)
            }
        }
    }

    func copy(_ item: OfficialTemplate) async {
        _ = await mutate(success: "模板副本已创建") {
            _ = try await repository.copy(id: item.id, title: "\(item.title) · 副本")
        }
    }

    func deactivate(_ item: OfficialTemplate) async {
        _ = await mutate(success: "模板已停用") {
            _ = try await repository.deactivate(id: item.id)
        }
    }

    func instantiate(_ item: OfficialTemplate) async {
        _ = await mutate(success: "已从模板生成官方局") {
            _ = try await repository.instantiate(
                id: item.id,
                startAt: Date().addingTimeInterval(86_400)
            )
        }
    }

    private func mutate(
        success: String,
        operation: () async throws -> Void
    ) async -> Bool {
        guard !working else { return false }
        working = true
        message = nil
        defer { working = false }
        do {
            try await operation()
            async let gatheringRequest = repository.gatherings()
            async let templateRequest = repository.templates()
            gatherings = try await gatheringRequest
            templates = try await templateRequest
            phase = .loaded
            message = success
            return true
        } catch {
            message = error.localizedDescription
            return false
        }
    }
}

/// O1 · 校园主理人控制台（T4）
struct OrganizerView: View {
    @StateObject private var model: OrganizerViewModel
    @State private var templateEditor: TemplateEditorContext?
    @State private var showsGatheringEditor = false
    @State private var dashboard: OfficialGatheringSummary?
    @EnvironmentObject private var router: AppRouter

    private let repository: OrganizerRepository

    init(repository: OrganizerRepository) {
        self.repository = repository
        _model = StateObject(
            wrappedValue: OrganizerViewModel(repository: repository)
        )
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "主理人认证", title: "校园主理人", lulu: .homeThinking)
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(error):
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                    OMCard {
                        OMTextRole.t3("解锁条件")
                        OMTextRole.foot("达到 T4 且完成主理人认证后开放。当前不会伪造成功状态。")
                            .padding(.top, OMTheme.Spacing.s2)
                    }
                case .loaded:
                    gatheringSection
                    templateSection
                }
                if let message = model.message {
                    OMCard {
                        OMTextRole.foot(message)
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .sheet(isPresented: $showsGatheringEditor) {
            OfficialGatheringEditor { draft in
                let saved = await model.createGathering(draft)
                if saved { showsGatheringEditor = false }
                return saved
            }
        }
        .sheet(item: $dashboard) { gathering in
            OrganizerDashboardView(
                gathering: gathering,
                repository: repository
            )
        }
        .sheet(item: $templateEditor) { context in
            TemplateEditor(context: context) { id, draft in
                let saved = await model.saveTemplate(id: id, draft: draft)
                if saved { templateEditor = nil }
                return saved
            }
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-O1-organizer")
    }

    private var gatheringSection: some View {
        Group {
            OMCard {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        OMTextRole.t2("官方局 · \(model.gatherings.count)")
                    }
                    Spacer()
                    OMSticker("clipboard-whistle.png", size: .s56)
                }
            }
            OMButton("直接创建官方局", systemIcon: "plus.circle.fill", loading: model.working) {
                showsGatheringEditor = true
            }
            .accessibilityIdentifier("organizer-create-gathering")
            if model.gatherings.isEmpty {
                OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
            }
            ForEach(model.gatherings) { item in
                officialCard(item)
            }
        }
    }

    private var templateSection: some View {
        Group {
            OMSection(title: "官方局模板")
            OMButton("新建官方局模板", systemIcon: "doc.badge.plus", loading: model.working) {
                templateEditor = .new
            }
            .accessibilityElement(children: .contain).accessibilityIdentifier("screen-O4-templates")
            if model.templates.isEmpty {
                OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
            }
            ForEach(model.templates) { item in templateCard(item) }
        }
    }

    static func statusLabel(_ raw: String) -> String {
        GatheringStatus(rawValue: raw)?.displayName ?? "状态同步中"
    }

    static func identityVisibilityLabel(_ raw: String) -> String {
        switch raw {
        case "after_all_confirmed": "全员确认后才展示身份"
        case "after_full": "满员后展示身份"
        case "never": "全程不展示身份"
        default: "身份按确认进度展示"
        }
    }

    private func officialCard(_ item: OfficialGatheringSummary) -> some View {
        OMCard {
            HStack {
                OMChip(text: Self.statusLabel(item.status), kind: .solid)
                Spacer()
                Text("目标 \(item.targetSize) 人")
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.mist)
            }
            OMTextRole.t3(item.title).padding(.top, OMTheme.Spacing.s2)
            OMTextRole.call(
                item.startAt?.formatted(date: .abbreviated, time: .shortened)
                    ?? "时间待确认"
            )
            .padding(.top, 2)
            HStack(spacing: 8) {
                OMButton("报名与到场看板", kind: .ghost, small: true, fillsWidth: false) {
                    dashboard = item
                }
                .accessibilityIdentifier("organizer-dashboard-\(item.id)")
                OMButton("打开局详情", kind: .ghost, small: true, fillsWidth: false) {
                    router.push(.gathering(item.id))
                }
            }
            .padding(.top, OMTheme.Spacing.s3)
        }
    }

    private func templateCard(_ item: OfficialTemplate) -> some View {
        OMCard {
            HStack {
                OMTextRole.t3(item.title)
                Spacer()
                OMChip(text: item.active ? "启用" : "停用", kind: item.active ? .solid : .standard)
            }
            OMTextRole.foot("\(item.gatheringType) · \(item.location) · \(item.durationMinutes) 分钟")
                .padding(.top, 4)
            HStack(spacing: 8) {
                OMButton("编辑", kind: .ghost, small: true, fillsWidth: false) { templateEditor = .edit(item) }
                OMButton("复制", kind: .ghost, small: true, fillsWidth: false) { Task { await model.copy(item) } }
                if item.active {
                    OMButton("停用", kind: .text, small: true, fillsWidth: false) { Task { await model.deactivate(item) } }
                }
            }
            .padding(.top, OMTheme.Spacing.s3)
            OMButton("明天实例化", systemIcon: "calendar.badge.plus", small: true) {
                Task { await model.instantiate(item) }
            }
            .padding(.top, OMTheme.Spacing.s2)
        }
    }
}

private struct OfficialGatheringEditor: View {
    let onSave: (OfficialGatheringDraft) async -> Bool
    @Environment(\.dismiss) private var dismiss
    @State private var draft: OfficialGatheringDraft
    @State private var saving = false
    @State private var error: String?

    init(onSave: @escaping (OfficialGatheringDraft) async -> Bool) {
        self.onSave = onSave
        let start = Date().addingTimeInterval(86_400)
        _draft = State(
            initialValue: .init(
                title: "",
                goal: "",
                gatheringType: "校园活动",
                startAt: start,
                endAt: start.addingTimeInterval(7_200),
                location: "",
                campus: "东校园",
                minSize: 3,
                targetSize: 20,
                requiredRoles: [],
                quotaBatches: []
            )
        )
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMSection(title: "共同目标")
                    OMCard {
                        VStack(spacing: OMTheme.Spacing.s3) {
                            TextField("官方局名称", text: $draft.title)
                                .omInputStyle()
                            TextField("要共同完成什么", text: $draft.goal, axis: .vertical)
                                .omInputStyle(multiline: true)
                            TextField("类型", text: $draft.gatheringType)
                                .omInputStyle()
                        }
                    }

                    OMSection(title: "时间与地点")
                    OMCard {
                        DatePicker("开始", selection: $draft.startAt)
                            .tint(OMTheme.ColorToken.ink)
                        DatePicker("结束", selection: $draft.endAt)
                            .tint(OMTheme.ColorToken.ink)
                            .padding(.top, OMTheme.Spacing.s2)
                        HStack(spacing: OMTheme.Spacing.s3) {
                            TextField("地点", text: $draft.location)
                                .omInputStyle()
                            TextField("校区", text: Binding($draft.campus, replacingNilWith: ""))
                                .omInputStyle()
                        }
                        .padding(.top, OMTheme.Spacing.s3)
                    }

                    OMSection(title: "规模")
                    OMCard(tight: true) {
                        OMStepperRow(title: "最低人数", value: $draft.minSize, range: 2...500)
                        OMStepperRow(title: "目标人数", value: $draft.targetSize, range: 2...500)
                    }
                    OMCard {
                        TextField(
                            "所需角色（逗号分隔）",
                            text: Binding(
                                get: { draft.requiredRoles.joined(separator: ",") },
                                set: { draft.requiredRoles = Self.tokens($0) }
                            )
                        )
                        .omInputStyle()
                    }

                    OMSection(title: "分批名额")
                    OMCard {
                        ForEach(Array(draft.quotaBatches.indices), id: \.self) { index in
                            VStack(spacing: OMTheme.Spacing.s2) {
                                TextField("批次名称", text: $draft.quotaBatches[index].label)
                                    .omInputStyle()
                                HStack {
                                    OMStepperRow(
                                        title: "名额",
                                        value: $draft.quotaBatches[index].slots,
                                        range: 1...500
                                    )
                                    .overlay(alignment: .bottom) { EmptyView() }
                                    Spacer()
                                    OMButton("删除", kind: .text, small: true, fillsWidth: false) {
                                        draft.quotaBatches.remove(at: index)
                                    }
                                }
                            }
                            .padding(.vertical, OMTheme.Spacing.s2)
                        }
                        OMButton("添加名额批次", kind: .ghost, small: true, fillsWidth: false) {
                            draft.quotaBatches.append(.init(label: "公开名额", slots: 1))
                        }
                        .disabled(draft.quotaBatches.count >= 20)
                        .padding(.top, OMTheme.Spacing.s2)
                    }

                    if let reason = invalidReason {
                        OMNote(text: reason, sticker: "hourglass.png")
                    }
                    if let error {
                        OMCard { OMG5StateView(state: .networkError, message: error) }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationTitle("创建官方局")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(saving ? "创建中…" : "创建") {
                        Task {
                            guard !saving else { return }
                            saving = true
                            error = nil
                            if !(await onSave(draft)) { error = "创建未完成，请核对服务端提示。" }
                            saving = false
                        }
                    }
                    .disabled(saving || invalidReason != nil)
                }
            }
            .accessibilityElement(children: .contain).accessibilityIdentifier("screen-O2-create-official")
        }
    }

    private var invalidReason: String? {
        if draft.title.trimmingCharacters(in: .whitespaces).count < 2 { return "名称至少 2 个字符" }
        if draft.goal.trimmingCharacters(in: .whitespaces).count < 2 { return "共同目标至少 2 个字符" }
        if draft.location.trimmingCharacters(in: .whitespaces).isEmpty { return "请填写地点" }
        if draft.endAt <= draft.startAt { return "结束时间必须晚于开始时间" }
        if draft.startAt <= Date() { return "开始时间必须晚于当前时间" }
        if draft.minSize > draft.targetSize { return "最低人数不能超过目标人数" }
        if draft.quotaBatches.reduce(0, { $0 + $1.slots }) > draft.targetSize {
            return "分批名额合计不能超过目标人数"
        }
        if draft.quotaBatches.contains(where: { $0.label.trimmingCharacters(in: .whitespaces).isEmpty }) {
            return "批次名称不能为空"
        }
        return nil
    }

    private static func tokens(_ text: String) -> [String] {
        Array(
            Set(
                text.split(whereSeparator: { $0 == "," || $0 == "，" })
                    .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                    .filter { !$0.isEmpty }
            )
        )
        .sorted()
        .prefix(20)
        .map { String($0.prefix(64)) }
    }
}

@MainActor
private final class OrganizerDashboardViewModel: ObservableObject {
    enum Phase {
        case loading
        case loaded(OrganizerDashboard)
        case failed(String)
    }

    @Published var phase: Phase = .loading
    @Published var working = false
    @Published var message: String?

    private let gatheringID: String
    private let repository: OrganizerRepository

    init(gatheringID: String, repository: OrganizerRepository) {
        self.gatheringID = gatheringID
        self.repository = repository
    }

    func load() async {
        do {
            phase = .loaded(try await repository.dashboard(gatheringID))
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    func closeRegistration() async {
        await mutate(success: "报名已关闭，进入成员分别确认阶段") {
            _ = try await repository.closeRegistration(gatheringID)
        }
    }

    func finalize() async {
        await mutate(success: "全员确认已验证，官方局已正式成局") {
            _ = try await repository.finalize(gatheringID)
        }
    }

    func checkIn(_ participantID: String) async {
        await mutate(success: "到场事实已登记") {
            _ = try await repository.checkIn(participantID, gatheringID: gatheringID)
        }
    }

    private func mutate(
        success: String,
        operation: () async throws -> Void
    ) async {
        guard !working else { return }
        working = true
        message = nil
        defer { working = false }
        do {
            try await operation()
            phase = .loaded(try await repository.dashboard(gatheringID))
            message = success
        } catch {
            message = error.localizedDescription
        }
    }
}

/// O3 · 报名与到场看板
private struct OrganizerDashboardView: View {
    let gathering: OfficialGatheringSummary
    @StateObject private var model: OrganizerDashboardViewModel
    @Environment(\.dismiss) private var dismiss

    init(gathering: OfficialGatheringSummary, repository: OrganizerRepository) {
        self.gathering = gathering
        _model = StateObject(
            wrappedValue: OrganizerDashboardViewModel(
                gatheringID: gathering.id,
                repository: repository
            )
        )
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMHeader(eyebrow: "实时看板", title: gathering.title, lulu: .actionExecuting)
                    switch model.phase {
                    case .loading:
                        OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                    case let .failed(message):
                        OMCard {
                            OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                                Task { await model.load() }
                            }
                        }
                    case let .loaded(value):
                        dashboardContent(value)
                    }
                    if let message = model.message {
                        OMCard {
                            OMTextRole.foot(message)
                        }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("关闭") { dismiss() }
                }
            }
            .task { await model.load() }
            .refreshable { await model.load() }
            .accessibilityElement(children: .contain).accessibilityIdentifier("screen-O3-organizer-dashboard")
        }
    }

    @ViewBuilder private func dashboardContent(_ value: OrganizerDashboard) -> some View {
        OMCard {
            OMChip(text: OrganizerView.statusLabel(value.status), kind: .solid)
            HStack {
                metric("报名", value.registeredCount)
                metric("确认", value.confirmedCount)
                metric("到场", value.attendedCount)
                metric("目标", value.targetSize)
            }
            .padding(.top, OMTheme.Spacing.s3)
            Text(OrganizerView.identityVisibilityLabel(value.identityVisibility))
                .font(OMTheme.TypeToken.caption)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .padding(.top, OMTheme.Spacing.s2)
        }
        if !value.quotaBatches.isEmpty {
            OMCard {
                OMTextRole.t3("名额批次")
                ForEach(value.quotaBatches) { batch in
                    HStack { Text(batch.label); Spacer(); Text("\(batch.slots)") }
                        .font(OMTheme.TypeToken.callout)
                        .padding(.top, OMTheme.Spacing.s2)
                }
            }
        }
        lifecycleAction(value)
        OMCard {
            OMTextRole.t3("参与者与到场")
            if let participants = value.participants {
                if participants.isEmpty {
                    OMTextRole.foot("暂无参与者").padding(.top, OMTheme.Spacing.s2)
                }
                ForEach(participants) { participant in
                    HStack(alignment: .center) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(participant.displayName ?? "已确认成员")
                                .font(OMTheme.TypeToken.callout.weight(.semibold))
                            Text(participant.confirmationStatus)
                                .font(OMTheme.TypeToken.footnote)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                        }
                        Spacer()
                        if participant.attended {
                            HStack(spacing: 4) {
                                Image(systemName: "checkmark.circle.fill")
                                Text("已到场")
                            }
                            .font(OMTheme.TypeToken.footnote.weight(.bold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                        } else {
                            OMButton("登记到场", kind: .ghost, small: true, fillsWidth: false) {
                                Task { await model.checkIn(participant.userId) }
                            }
                            .disabled(model.working || !attendanceStatus(value.status))
                            .accessibilityHint(
                                attendanceStatus(value.status)
                                    ? "服务端仍会校验开始前 30 分钟至结束后 24 小时的窗口"
                                    : "正式成局后开放"
                            )
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                    OMDivider()
                }
            }
        }
    }

    @ViewBuilder private func lifecycleAction(_ value: OrganizerDashboard) -> some View {
        switch value.status {
        case "Pooling":
            OMButton("关闭报名并发起分别确认", systemIcon: "lock.fill", loading: model.working) {
                Task { await model.closeRegistration() }
            }
            .padding(.top, OMTheme.Spacing.s2)
        case "Confirmed":
            OMButton("验证全员确认并正式成局", systemIcon: "checkmark.seal.fill", loading: model.working) {
                Task { await model.finalize() }
            }
            .padding(.top, OMTheme.Spacing.s2)
        case "Tentative":
            OMButton(
                "等待所有成员分别确认",
                disabledReason: "当前 \(value.confirmedCount) / \(value.registeredCount) 位已确认"
            ) {}
            .padding(.top, OMTheme.Spacing.s2)
        default:
            OMCard {
                OMTextRole.foot("生命周期操作已完成或当前状态不接受变更。")
            }
        }
    }

    private func metric(_ label: String, _ value: Int) -> some View {
        VStack(spacing: 3) {
            Text("\(value)").font(OMTheme.TypeToken.title3.weight(.bold))
            Text(label)
                .font(OMTheme.TypeToken.caption)
                .foregroundStyle(OMTheme.ColorToken.mist)
        }
        .frame(maxWidth: .infinity)
    }

    private func attendanceStatus(_ status: String) -> Bool {
        ["Executed", "Active", "Completed"].contains(status)
    }
}

private struct TemplateEditorContext: Identifiable {
    let id: String
    let templateID: String?
    let draft: OfficialTemplateDraft

    static var new: Self {
        .init(
            id: UUID().uuidString,
            templateID: nil,
            draft: .init(
                title: "",
                goal: "",
                gatheringType: "校园活动",
                campus: "东校园",
                location: "",
                durationMinutes: 120,
                minSize: 3,
                targetSize: 20,
                requiredRoles: [],
                recurrenceRule: nil
            )
        )
    }

    static func edit(_ item: OfficialTemplate) -> Self {
        .init(
            id: item.id,
            templateID: item.id,
            draft: .init(
                title: item.title,
                goal: item.goal,
                gatheringType: item.gatheringType,
                campus: item.campus,
                location: item.location,
                durationMinutes: item.durationMinutes,
                minSize: item.minSize,
                targetSize: item.targetSize,
                requiredRoles: item.requiredRoles,
                recurrenceRule: item.recurrenceRule
            )
        )
    }
}

private struct TemplateEditor: View {
    let context: TemplateEditorContext
    let onSave: (String?, OfficialTemplateDraft) async -> Bool
    @Environment(\.dismiss) private var dismiss
    @State private var draft: OfficialTemplateDraft
    @State private var saving = false

    init(
        context: TemplateEditorContext,
        onSave: @escaping (String?, OfficialTemplateDraft) async -> Bool
    ) {
        self.context = context
        self.onSave = onSave
        _draft = State(initialValue: context.draft)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMSection(title: "模板内容")
                    OMCard {
                        VStack(spacing: OMTheme.Spacing.s3) {
                            TextField("模板名称", text: $draft.title)
                                .omInputStyle()
                            TextField("共同目标", text: $draft.goal, axis: .vertical)
                                .omInputStyle(multiline: true)
                            HStack(spacing: OMTheme.Spacing.s3) {
                                TextField("类型", text: $draft.gatheringType)
                                    .omInputStyle()
                                TextField("校区", text: Binding($draft.campus, replacingNilWith: ""))
                                    .omInputStyle()
                            }
                            TextField("地点", text: $draft.location)
                                .omInputStyle()
                        }
                    }
                    OMSection(title: "规模与时长")
                    OMCard(tight: true) {
                        OMStepperRow(title: "时长", value: $draft.durationMinutes, range: 30...1440, step: 30, unit: "分钟")
                        OMStepperRow(title: "最低人数", value: $draft.minSize, range: 2...500)
                        OMStepperRow(title: "目标人数", value: $draft.targetSize, range: 2...500)
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationTitle(context.templateID == nil ? "新建模板" : "编辑模板")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(saving ? "保存中…" : "保存") {
                        Task {
                            guard !saving else { return }
                            saving = true
                            _ = await onSave(context.templateID, draft)
                            saving = false
                        }
                    }
                    .disabled(
                        saving
                            || draft.title.count < 2
                            || draft.goal.count < 2
                            || draft.location.isEmpty
                            || draft.minSize > draft.targetSize
                    )
                }
            }
        }
    }
}

private extension Binding where Value == String {
    init(_ source: Binding<String?>, replacingNilWith fallback: String) {
        self.init(
            get: { source.wrappedValue ?? fallback },
            set: { source.wrappedValue = $0.isEmpty ? nil : $0 }
        )
    }
}
