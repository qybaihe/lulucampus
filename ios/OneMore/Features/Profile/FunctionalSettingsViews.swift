import SwiftUI

@MainActor
private final class GrantManagementViewModel: ObservableObject {
    @Published var facts: IdentityFacts?
    @Published var loading = true
    @Published var workingScope: String?
    @Published var error: String?
    private let repository: IdentityRepository

    init(repository: IdentityRepository) { self.repository = repository }

    func load() async {
        loading = true
        defer { loading = false }
        do { facts = try await repository.facts(); error = nil }
        catch { self.error = error.localizedDescription }
    }

    func set(_ scope: String, granted: Bool) async {
        guard workingScope == nil else { return }
        workingScope = scope
        defer { workingScope = nil }
        do {
            _ = try await repository.setGrant(scope: scope, granted: granted)
            facts = try await repository.facts()
            error = nil
        } catch { self.error = error.localizedDescription }
    }
}

/// M4 · 授权管理
struct GrantManagementView: View {
    @StateObject private var model: GrantManagementViewModel
    @State private var pendingRevocation: AuthorizationGrantView?

    init(repository: IdentityRepository) {
        _model = StateObject(wrappedValue: GrantManagementViewModel(repository: repository))
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "分项授权", title: "授权管理", lulu: .coreCare)
                if model.loading {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                } else if let facts = model.facts {
                    ForEach(facts.grants) { grant in
                        OMCard {
                            HStack(alignment: .top) {
                                VStack(alignment: .leading, spacing: 3) {
                                    OMTextRole.t3(label(grant.scope))
                                    OMTextRole.foot(impact(grant.scope))
                                }
                                Spacer()
                                OMChip(text: grant.granted ? "已授权" : "未授权", kind: grant.granted ? .solid : .standard)
                            }
                            if grant.granted {
                                OMButton("撤回并清除派生数据…", kind: .ghost, small: true, fillsWidth: false) {
                                    pendingRevocation = grant
                                }
                                .padding(.top, OMTheme.Spacing.s3)
                                .disabled(model.workingScope != nil)
                            } else {
                                OMButton(model.workingScope == grant.scope ? "授权中…" : "重新授权", small: true, fillsWidth: false, loading: model.workingScope == grant.scope) {
                                    Task { await model.set(grant.scope, granted: true) }
                                }
                                .padding(.top, OMTheme.Spacing.s3)
                                .disabled(model.workingScope != nil)
                            }
                        }
                    }
                    OMSection(title: "子系统状态")
                    if facts.sessionHealth.isEmpty {
                        OMCard { OMTextRole.foot("暂无已建立的子系统会话") }
                    }
                    ForEach(facts.sessionHealth) { item in
                        OMCard {
                            HStack {
                                Image(systemName: item.healthy ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                                    .foregroundStyle(item.healthy ? OMTheme.ColorToken.ink : OMTheme.ColorToken.ink)
                                Text(item.subsystem)
                                    .font(OMTheme.TypeToken.callout.weight(.semibold))
                                Spacer()
                                Text(item.healthy ? "正常" : "需重新认证")
                                    .font(OMTheme.TypeToken.footnote)
                                    .foregroundStyle(OMTheme.ColorToken.mist)
                            }
                            if let checked = item.lastCheckedAt {
                                OMTextRole.cap("检查于 \(checked.formatted(date: .abbreviated, time: .shortened))")
                                    .padding(.top, 4)
                            }
                        }
                    }
                }
                if let error = model.error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .confirmationDialog(
            "撤回 \(label(pendingRevocation?.scope ?? "")) 授权？",
            isPresented: Binding(
                get: { pendingRevocation != nil },
                set: { if !$0 { pendingRevocation = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("撤回并清除", role: .destructive) {
                if let scope = pendingRevocation?.scope {
                    pendingRevocation = nil
                    Task { await model.set(scope, granted: false) }
                }
            }
            Button("取消", role: .cancel) { pendingRevocation = nil }
        } message: {
            Text(impact(pendingRevocation?.scope ?? "") + " 已缓存的派生数据会同步清除。")
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-M4-grants")
    }

    private func label(_ scope: String) -> String {
        ["timetable": "课表", "curriculum": "课程目录", "enrollment": "选课事实", "agent_booking": "校园预约代理"][scope] ?? scope
    }

    private func impact(_ scope: String) -> String {
        switch scope {
        case "timetable": "用于自己的课表、空档与通勤可行性；撤回会清除时间窗并退出相关匿名池。"
        case "curriculum": "用于课程名称与能力标签解释；撤回会清除课程派生画像。"
        case "enrollment": "用于本人选课事实和同课匹配；撤回会清除核验标签。"
        case "agent_booking": "仅在你和局内成员分别核对预览后执行校园预约。"
        default: "此授权只用于对应校园子系统。"
        }
    }
}

@MainActor
private final class MatchingPreferencesViewModel: ObservableObject {
    @Published var value: MatchingPreferences?
    @Published var loading = true
    @Published var saving = false
    @Published var error: String?
    private let repository: IdentityRepository
    init(repository: IdentityRepository) { self.repository = repository }
    func load() async {
        loading = true; defer { loading = false }
        do { value = try await repository.matchingPreferences(); error = nil }
        catch { self.error = error.localizedDescription }
    }
    func save() async {
        guard let value, !saving else { return }
        saving = true; defer { saving = false }
        do { self.value = try await repository.updateMatchingPreferences(value); error = nil }
        catch { self.error = error.localizedDescription }
    }
}

/// M6 · 匹配偏好
struct MatchingPreferencesView: View {
    @StateObject private var model: MatchingPreferencesViewModel
    init(repository: IdentityRepository) {
        _model = StateObject(wrappedValue: MatchingPreferencesViewModel(repository: repository))
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "只影响推荐", title: "匹配偏好", lulu: .homeThinking)
                if model.value != nil {
                    OMSection(title: "互动节奏")
                    OMCard {
                        OMSeg(
                            items: ["quiet", "balanced", "talkative"],
                            label: { ["quiet": "安静做事", "balanced": "自然平衡", "talkative": "愿意多交流"][$0] ?? $0 },
                            selection: binding(\.interactionStyle)
                        )
                    }
                    OMSection(title: "运动自述")
                    OMCard {
                        OMSeg(
                            items: ["beginner", "casual", "intermediate", "advanced"],
                            label: { ["beginner": "刚入门", "casual": "休闲", "intermediate": "稳定练习", "advanced": "高阶训练"][$0] ?? $0 },
                            selection: binding(\.sportLevel)
                        )
                    }
                    OMSection(title: "学习强度")
                    OMCard {
                        OMSeg(
                            items: ["light", "balanced", "focused"],
                            label: { ["light": "轻量", "balanced": "平衡", "focused": "专注"][$0] ?? $0 },
                            selection: binding(\.studyIntensity)
                        )
                    }
                    if let error = model.error {
                        OMCard { OMG5StateView(state: .networkError, message: error) }
                    }
                    OMButton(model.saving ? "保存中…" : "保存匹配偏好", icon: .spark, loading: model.saving) {
                        Task { await model.save() }
                    }
                    .padding(.top, OMTheme.Spacing.s4)
                } else if model.loading {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                } else if let error = model.error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-M6-matching-preferences")
    }
    private func binding<Value>(_ path: WritableKeyPath<MatchingPreferences, Value>) -> Binding<Value> {
        Binding {
            guard let value = model.value else { preconditionFailure("preferences not loaded") }
            return value[keyPath: path]
        } set: { model.value?[keyPath: path] = $0 }
    }
}

@MainActor
private final class BlockListViewModel: ObservableObject {
    @Published var rows: [BlockedUser] = []
    @Published var loading = true
    @Published var workingID: String?
    @Published var error: String?
    private let repository: IdentityRepository
    init(repository: IdentityRepository) { self.repository = repository }
    func load() async {
        loading = true; defer { loading = false }
        do { rows = try await repository.blocks(); error = nil }
        catch { self.error = error.localizedDescription }
    }
    func unblock(_ id: String) async {
        guard workingID == nil else { return }
        workingID = id; defer { workingID = nil }
        do { try await repository.unblock(id); rows.removeAll { $0.id == id }; error = nil }
        catch { self.error = error.localizedDescription }
    }
}

/// M8 · 黑名单
struct BlockListView: View {
    @StateObject private var model: BlockListViewModel
    @State private var pendingID: String?
    init(repository: IdentityRepository) {
        _model = StateObject(wrappedValue: BlockListViewModel(repository: repository))
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "安全", title: "黑名单", lulu: .coreCare)
                if model.loading {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                } else if model.rows.isEmpty {
                    OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
                }
                ForEach(model.rows) { row in
                    OMCard {
                        OMTextRole.t3("已拉黑成员")
                        Text("记录 ···\(row.blockedUserId.suffix(6))")
                            .font(OMTheme.TypeToken.mono(.footnote))
                            .foregroundStyle(OMTheme.ColorToken.mist)
                            .padding(.top, 4)
                        OMTextRole.cap(row.createdAt.formatted(date: .abbreviated, time: .shortened))
                            .padding(.top, 2)
                        OMButton(model.workingID == row.id ? "处理中…" : "解除拉黑…", kind: .ghost, small: true, fillsWidth: false) {
                            pendingID = row.id
                        }
                        .padding(.top, OMTheme.Spacing.s3)
                        .disabled(model.workingID != nil)
                    }
                }
                if let error = model.error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .confirmationDialog("解除拉黑？", isPresented: Binding(get: { pendingID != nil }, set: { if !$0 { pendingID = nil } })) {
            Button("确认解除", role: .destructive) {
                if let id = pendingID { pendingID = nil; Task { await model.unblock(id) } }
            }
            Button("取消", role: .cancel) { pendingID = nil }
        } message: { Text("解除是单方静默操作，对方不会收到通知。") }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-M8-block-list")
    }
}

@MainActor
private final class InitiateGatheringViewModel: ObservableObject {
    @Published var draft = InitiateGatheringDraft(
        title: "", goal: "", gatheringType: "自习", campus: "珠海校区", location: nil
    )
    @Published var scheduled = false
    @Published var startAt = Date().addingTimeInterval(86_400)
    @Published var endAt = Date().addingTimeInterval(86_400 + 5_400)
    @Published var working = false
    @Published var error: String?
    private let repository: GatheringRepository
    init(repository: GatheringRepository) { self.repository = repository }
    func submit() async -> GatheringSummary? {
        guard !working else { return nil }
        working = true; defer { working = false }
        var value = draft
        value.startAt = scheduled ? startAt : nil
        value.endAt = scheduled ? endAt : nil
        do { let item = try await repository.initiate(value); error = nil; return item }
        catch { self.error = error.localizedDescription; return nil }
    }
}

/// E2 · 直接发起具体局（T2）
struct InitiateGatheringView: View {
    @StateObject private var model: InitiateGatheringViewModel
    @EnvironmentObject private var router: AppRouter
    init(repository: GatheringRepository) {
        _model = StateObject(wrappedValue: InitiateGatheringViewModel(repository: repository))
    }
    private var formInvalid: Bool {
        model.draft.title.count < 2 || model.draft.goal.count < 2
            || model.draft.targetSize < model.draft.minSize
            || (model.scheduled && model.endAt <= model.startAt)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "自行发起", title: "直接发起局", lulu: .confirmGather)

                OMSection(title: "局信息")
                OMCard {
                    VStack(spacing: OMTheme.Spacing.s3) {
                        TextField("局标题", text: $model.draft.title)
                            .omInputStyle()
                        TextField("要一起完成什么", text: $model.draft.goal, axis: .vertical)
                            .omInputStyle(multiline: true)
                        HStack(spacing: OMTheme.Spacing.s3) {
                            TextField("类型", text: $model.draft.gatheringType)
                                .omInputStyle()
                            TextField("校区", text: optionalBinding(\.campus))
                                .omInputStyle()
                        }
                        TextField("地点（可稍后确定）", text: optionalBinding(\.location))
                            .omInputStyle()
                    }
                }

                OMSection(title: "人数与范围")
                OMCard(tight: true) {
                    OMStepperRow(title: "最低人数", value: $model.draft.minSize, range: 2...20)
                    OMStepperRow(title: "目标人数", value: $model.draft.targetSize, range: max(model.draft.minSize, 2)...20)
                    OMRow(sticker: "teaching-building.png", title: "跨院系匹配", toggle: $model.draft.crossCollege)
                }

                OMSection(title: "固定时段")
                OMCard {
                    HStack {
                        OMTextRole.t3("现在确定时间")
                        Spacer()
                        OMSwitch(isOn: $model.scheduled)
                    }
                    if model.scheduled {
                        DatePicker("开始", selection: $model.startAt)
                            .tint(OMTheme.ColorToken.ink)
                            .padding(.top, OMTheme.Spacing.s3)
                        DatePicker("结束", selection: $model.endAt)
                            .tint(OMTheme.ColorToken.ink)
                    }
                }

                if let error = model.error {
                    OMCard { OMG5StateView(state: .networkError, message: error) }
                }
                OMButton(
                    model.working ? "创建中…" : "创建并进入匿名池",
                    icon: .plus, loading: model.working,
                    disabledReason: formInvalid ? "先补全标题与目标，并确认人数与时间" : nil
                ) {
                    Task {
                        if let item = await model.submit() { router.push(.gathering(item.id)) }
                    }
                }
                .padding(.top, OMTheme.Spacing.s4)
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-E2-self-initiate")
    }

    private func optionalBinding(
        _ path: WritableKeyPath<InitiateGatheringDraft, String?>
    ) -> Binding<String> {
        Binding(
            get: { model.draft[keyPath: path] ?? "" },
            set: { model.draft[keyPath: path] = $0.isEmpty ? nil : $0 }
        )
    }
}

@MainActor
private final class RecurringGatheringViewModel: ObservableObject {
    @Published var firstStart = Date().addingTimeInterval(7 * 86_400)
    @Published var occurrences = 4
    @Published var intervalWeeks = 1
    @Published var durationMinutes = 90
    @Published var working = false
    @Published var result: [GatheringSummary] = []
    @Published var error: String?
    let gatheringID: String
    private let repository: GatheringRepository
    init(gatheringID: String, repository: GatheringRepository) {
        self.gatheringID = gatheringID; self.repository = repository
    }
    func create() async {
        guard !working else { return }
        working = true; defer { working = false }
        do {
            result = try await repository.createRecurring(
                gatheringID, firstStartAt: firstStart, occurrences: occurrences,
                intervalWeeks: intervalWeeks, durationMinutes: durationMinutes
            )
            error = nil
        } catch { self.error = error.localizedDescription }
    }
}

/// E10 · 周期性固定局（T3）
struct RecurringGatheringView: View {
    @StateObject private var model: RecurringGatheringViewModel
    @EnvironmentObject private var router: AppRouter
    init(gatheringID: String, repository: GatheringRepository) {
        _model = StateObject(wrappedValue: RecurringGatheringViewModel(gatheringID: gatheringID, repository: repository))
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "周期性固定局", title: "固定周期", lulu: .poolWaiting)

                OMCard {
                    DatePicker("首期开始", selection: $model.firstStart)
                        .tint(OMTheme.ColorToken.ink)
                }
                OMCard(tight: true) {
                    OMStepperRow(title: "期数", value: $model.occurrences, range: 2...12, unit: "期")
                    OMStepperRow(title: "间隔", value: $model.intervalWeeks, range: 1...4, unit: "周")
                    OMStepperRow(title: "每期时长", value: $model.durationMinutes, range: 30...1440, step: 30, unit: "分钟")
                }

                if let error = model.error {
                    OMCard { OMG5StateView(state: .networkError, message: error) }
                }
                OMButton(
                    model.working ? "创建中…" : "创建固定周期",
                    icon: .cal, loading: model.working,
                    disabledReason: model.firstStart <= .now ? "首期开始时间需在未来" : nil
                ) { Task { await model.create() } }
                .padding(.top, OMTheme.Spacing.s4)

                if !model.result.isEmpty {
                    OMSection(title: "已创建 \(model.result.count) 期")
                    OMCard(tight: true) {
                        ForEach(model.result) { item in
                            OMRow(
                                sticker: "desk-calendar.png",
                                title: item.startAt?.formatted(date: .abbreviated, time: .shortened) ?? item.title,
                                onTap: { router.push(.gathering(item.id)) }
                            )
                        }
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-E10-recurring")
    }
}
