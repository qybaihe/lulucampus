import SwiftUI

/// E15 · 搭子关系（事实列表）
struct RelationsView: View {
    @StateObject private var model: RelationsViewModel
    @State private var pendingDissolution: RelationSummary?
    @EnvironmentObject private var router: AppRouter
    init(repository: SocialRepository) {
        _model = StateObject(wrappedValue: RelationsViewModel(repository: repository))
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "共同经历事实", title: "搭子关系", lulu: .homeReply)
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                case let .loaded(relations):
                    if relations.isEmpty {
                        OMCard {
                            OMG5StateView(state: .empty, message: "完成一次真实的共同活动后，搭子关系会出现在这里。")
                            OMButton("浏览公开局", systemIcon: "person.3", small: true, fillsWidth: false) {
                                router.push(.publicGatherings)
                            }
                            .padding(.top, OMTheme.Spacing.s3)
                        }
                        .accessibilityElement(children: .contain)
                        .accessibilityIdentifier("relations-empty-state")
                    }
                    ForEach(relations) { relation in
                        OMCard {
                            HStack(alignment: .firstTextBaseline) {
                                OMTextRole.t2(relation.participants.map { $0.displayName ?? "同学" }.joined(separator: " × "))
                                Spacer()
                                if let title = relation.partnerTitle {
                                    OMChip(text: title, kind: .soft)
                                }
                            }
                            OMTextRole.foot(relationSummaryLine(relation))
                                .padding(.top, 4)
                            if let milestone = relation.milestone, let next = milestone.next, let remaining = milestone.remaining {
                                OMProgressBar(value: Double(relation.timesTogether) / Double(next))
                                    .padding(.top, OMTheme.Spacing.s2)
                                OMTextRole.cap("再同局 \(remaining) 次达成「\(milestone.nextLabel ?? "下个纪念点")」")
                                    .padding(.top, 4)
                            }
                            HStack(spacing: 8) {
                                OMButton(
                                    model.workingRelationID == relation.id ? "创建中…" : "再来一次",
                                    systemIcon: "arrow.clockwise",
                                    kind: .ghost,
                                    small: true,
                                    loading: model.workingRelationID == relation.id
                                ) {
                                    Task {
                                        if let gatheringID = await model.recur(relation.id) {
                                            router.push(.gathering(gatheringID))
                                        }
                                    }
                                }
                                .accessibilityIdentifier("relation-recur-action")
                                if let channelID = relation.channelId {
                                    OMButton("进入对话", kind: .ghost, small: true, fillsWidth: false) {
                                        router.push(.channel(channelID))
                                    }
                                    .accessibilityIdentifier("relation-open-chat")
                                } else {
                                    OMButton("进入对话", kind: .ghost, small: true, fillsWidth: false, disabledReason: "共同完成并建立会话后开放") {}
                                        .accessibilityIdentifier("relation-open-chat")
                                }
                                OMButton("共同经历", kind: .ghost, small: true, fillsWidth: false) {
                                    router.push(.relation(relation.id))
                                }
                                .accessibilityIdentifier("relation-detail-\(relation.id)")
                            }
                            .padding(.top, OMTheme.Spacing.s3)
                            OMButton(model.workingRelationID == relation.id ? "处理中…" : "解除关系…", kind: .text, small: true, fillsWidth: false) {
                                pendingDissolution = relation
                            }
                            .disabled(model.workingRelationID != nil)
                        }
                        .accessibilityElement(children: .contain)
                    }
                }
                if let error = model.mutationError {
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
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-E15-relations")
        .alert(
            "解除这段搭子关系？",
            isPresented: Binding(
                get: { pendingDissolution != nil },
                set: { if !$0 { pendingDissolution = nil } }
            )
        ) {
            Button("取消", role: .cancel) { pendingDissolution = nil }
            Button("确认解除", role: .destructive) {
                if let id = pendingDissolution?.id {
                    pendingDissolution = nil
                    Task { await model.dissolve(id) }
                }
            }
        } message: {
            Text("这是单方静默操作，对方不会收到解除通知。共同经历只保留事实记录。")
        }
    }

    /// C · 弱展示 → 强展示：「一起成过 3 局 · 最近一次是组队备赛」。
    private func relationSummaryLine(_ relation: RelationSummary) -> String {
        var parts: [String] = []
        if relation.timesTogether > 0 { parts.append("一起成过 \(relation.timesTogether) 局") }
        if relation.recurCount > 0 { parts.append("复局 \(relation.recurCount) 次") }
        if let latest = relation.timeline.first {
            parts.append("最近一次是\(latest.gatheringType)")
        } else if let experience = relation.experiences.max(by: { $0.occurredAt < $1.occurredAt }) {
            parts.append("最近一次是\(experience.gatheringType)")
        }
        return parts.isEmpty ? "共同经历只记事实" : parts.joined(separator: " · ")
    }
}

@MainActor
private final class RelationDetailViewModel: ObservableObject {
    enum Phase { case loading, loaded(RelationSummary), failed(String), dissolved }
    @Published var phase: Phase = .loading
    @Published var isWorking = false
    private let relationID: String
    private let repository: SocialRepository

    init(relationID: String, repository: SocialRepository) {
        self.relationID = relationID
        self.repository = repository
    }

    func load() async {
        phase = .loading
        do { phase = .loaded(try await repository.relation(relationID)) }
        catch { phase = .failed(error.localizedDescription) }
    }

    func dissolve() async {
        guard !isWorking else { return }
        isWorking = true
        defer { isWorking = false }
        do {
            try await repository.dissolve(relationID: relationID)
            phase = .dissolved
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    func recur() async -> String? {
        guard !isWorking else { return nil }
        isWorking = true
        defer { isWorking = false }
        do { return try await repository.recur(relationID: relationID) }
        catch { phase = .failed(error.localizedDescription); return nil }
    }
}

/// E16 · 共同经历
struct RelationDetailView: View {
    @StateObject private var model: RelationDetailViewModel
    @EnvironmentObject private var router: AppRouter
    @State private var confirmDissolution = false

    init(relationID: String, repository: SocialRepository) {
        _model = StateObject(
            wrappedValue: RelationDetailViewModel(
                relationID: relationID,
                repository: repository
            )
        )
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "事实记录", title: "共同经历", lulu: .homeIdle)
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                case .dissolved:
                    OMCard { OMG5StateView(state: .empty, message: "这段搭子关系已解除。") }
                    OMButton("返回搭子关系", systemIcon: "person.2") {
                        router.popToRoot()
                        router.push(.relations)
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                case let .loaded(relation):
                    relationContent(relation)
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-E16-relation-detail")
        .alert("解除这段搭子关系？", isPresented: $confirmDissolution) {
            Button("取消", role: .cancel) {}
            Button("确认解除", role: .destructive) { Task { await model.dissolve() } }
        } message: {
            Text("这是单方静默操作，对方不会收到通知；共同经历仅保留事实。")
        }
    }

    @ViewBuilder
    private func relationContent(_ relation: RelationSummary) -> some View {
        // 搭子档案头：称号 + 次数事实，全部来自 shared_experiences。
        OMCard {
            HStack(alignment: .firstTextBaseline) {
                OMTextRole.t2(
                    relation.participants
                        .map { $0.displayName ?? "同学" }
                        .joined(separator: " × ")
                )
                Spacer()
                if let title = relation.partnerTitle {
                    OMChip(text: title, kind: .soft)
                }
            }
            HStack(spacing: 0) {
                statBlock("\(relation.timesTogether)", "次同局")
                statBlock("\(relation.recurCount)", "次复局")
                statBlock("\(relation.timeline.count)", "条经历")
            }
            .padding(.top, OMTheme.Spacing.s3)
            if let milestone = relation.milestone {
                if let reachedLabel = milestone.reachedLabel {
                    HStack(spacing: 8) {
                        OMSticker("badge.png", size: .s44)
                        VStack(alignment: .leading, spacing: 2) {
                            OMTextRole.t3(reachedLabel)
                            if milestone.next != nil, let remaining = milestone.remaining {
                                OMTextRole.cap("再同局 \(remaining) 次达成「\(milestone.nextLabel ?? "下个纪念点")」")
                            }
                        }
                        Spacer()
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                if let next = milestone.next {
                    OMProgressBar(value: Double(relation.timesTogether) / Double(next))
                        .padding(.top, OMTheme.Spacing.s2)
                }
            }
        }
        // 下次可约：唯一由服务端算出的「你们都空着」窗口，是全页最该行动的信息。
        if let window = relation.nextWindow {
            OMCard {
                HStack(spacing: 10) {
                    OMSticker("desk-calendar.png", size: .s44)
                    VStack(alignment: .leading, spacing: 2) {
                        OMTextRole.t3("下次你们都空着")
                        OMTextRole.foot(window.startAt.formatted(.dateTime.weekday(.wide).month().day().hour().minute()) + " — " + window.endAt.formatted(date: .omitted, time: .shortened))
                    }
                    Spacer()
                }
                OMButton(model.isWorking ? "创建中…" : "就约这天，再来一局", systemIcon: "arrow.clockwise", kind: .dark, small: true, loading: model.isWorking) {
                    Task {
                        if let gatheringID = await model.recur() { router.push(.gathering(gatheringID)) }
                    }
                }
                .padding(.top, OMTheme.Spacing.s3)
            }
            .accessibilityIdentifier("relation-next-window")
        }
        if let goal = relation.activeGoal {
            OMCard {
                HStack {
                    OMTextRole.t3(goal.definition)
                    Spacer()
                    Text("\(goal.currentValue.formatted()) / \(goal.targetValue.formatted()) \(goal.unit)")
                        .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                }
                OMProgressBar(value: goal.currentValue / max(goal.targetValue, 1))
                    .padding(.top, OMTheme.Spacing.s2)
                OMTextRole.cap("目标进度只由到场与完成事实自动更新 · \(goal.periodEnd) 截止")
                    .padding(.top, 4)
            }
            .accessibilityIdentifier("relation-active-goal")
        }
        // 操作区：复局 / 会话 / 目标同为次级行动，等权 ghost 一排收拢，
        // 不用蛋黄主按钮抢「事实记录」内容的视觉权重。
        HStack(spacing: 8) {
            if relation.nextWindow == nil {
                OMButton(model.isWorking ? "创建中…" : "再来一次", systemIcon: "arrow.clockwise", kind: .ghost, small: true, loading: model.isWorking) {
                    Task {
                        if let gatheringID = await model.recur() { router.push(.gathering(gatheringID)) }
                    }
                }
                .accessibilityIdentifier("relation-detail-recur")
            }
            if let channelID = relation.channelId {
                OMButton("搭子会话", systemIcon: "message", kind: .ghost, small: true) {
                    router.push(.channel(channelID))
                }
            }
            if relation.activeGoal == nil {
                OMButton("共同目标", systemIcon: "target", kind: .ghost, small: true) {
                    router.push(.sharedGoals(relation.id))
                }
            }
        }
        .padding(.top, OMTheme.Spacing.s2)
        // 经历时间线：仅双方可见的「物证」，替代原始日志式列表。
        if !relation.timeline.isEmpty {
            OMSection(title: "经历时间线")
            ForEach(relation.timeline) { entry in
                timelineCard(entry)
            }
        } else {
            ForEach(relation.experiences) { experience in
                OMCard {
                    OMTextRole.t3(experience.gatheringType)
                    OMTextRole.cap(experience.occurredAt.formatted(date: .long, time: .omitted))
                        .padding(.top, 2)
                    OMTextRole.call(experience.outcome).padding(.top, OMTheme.Spacing.s2)
                    if !experience.commonGrounds.isEmpty {
                        OMTextRole.foot(experience.commonGrounds.joined(separator: " · "))
                            .padding(.top, OMTheme.Spacing.s2)
                    }
                }
            }
        }
        OMButton(model.isWorking ? "处理中…" : "解除关系…", kind: .text, small: true, fillsWidth: false) {
            confirmDissolution = true
        }
        .disabled(model.isWorking)
        .accessibilityIdentifier("relation-dissolve-action")
    }

    private func timelineCard(_ entry: RelationSummary.TimelineEntry) -> some View {
        OMCard {
            HStack(alignment: .firstTextBaseline) {
                Text(entry.occurredAt.formatted(.dateTime.month().day()))
                    .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                Text(timelineHeadline(entry))
                    .font(OMTheme.TypeToken.callout.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                Spacer()
                if entry.viaRecurrence {
                    OMChip(text: "复局", kind: .soft)
                }
            }
            if let title = entry.title, !title.isEmpty {
                OMTextRole.foot(title).padding(.top, 4)
            }
            if !entry.commonGrounds.isEmpty {
                OMTextRole.cap(entry.commonGrounds.joined(separator: " · "))
                    .padding(.top, 4)
            }
        }
    }

    /// 「4 月 3 日 · 珠海馆 · 羽毛球 2 小时」式的一行事实。
    private func timelineHeadline(_ entry: RelationSummary.TimelineEntry) -> String {
        var parts: [String] = []
        if let location = entry.location, !location.isEmpty { parts.append(location) }
        if let minutes = entry.durationMinutes, minutes > 0 {
            if minutes >= 60 {
                let hours = Double(minutes) / 60
                parts.append("\(entry.gatheringType) \(hours.formatted(.number.precision(.fractionLength(0...1)))) 小时")
            } else {
                parts.append("\(entry.gatheringType) \(minutes) 分钟")
            }
        } else {
            parts.append(entry.gatheringType)
        }
        return parts.joined(separator: " · ")
    }

    private func statBlock(_ value: String, _ label: String) -> some View {
        VStack(spacing: 3) {
            Text(value)
                .font(.system(size: 24, weight: .heavy, design: .monospaced))
                .foregroundStyle(OMTheme.ColorToken.ink)
            Text(label)
                .font(OMTheme.TypeToken.caption)
                .foregroundStyle(OMTheme.ColorToken.mist)
        }
        .frame(maxWidth: .infinity)
    }
}

@MainActor
private final class SharedGoalsViewModel: ObservableObject {
    @Published var goals: [SharedGoal] = []
    @Published var loading = true
    @Published var working = false
    @Published var error: String?
    let relationID: String
    private let repository: SocialRepository

    init(relationID: String, repository: SocialRepository) {
        self.relationID = relationID; self.repository = repository
    }

    func load() async {
        loading = true; defer { loading = false }
        do { goals = try await repository.goals(relationID: relationID); error = nil }
        catch { self.error = error.localizedDescription }
    }

    func create(
        definition: String, start: Date, end: Date, target: Double, unit: String
    ) async -> Bool {
        guard !working else { return false }
        working = true; defer { working = false }
        do {
            _ = try await repository.createGoal(
                relationID: relationID,
                definition: definition,
                periodStart: Self.localDate(start),
                periodEnd: Self.localDate(end),
                targetValue: target,
                unit: unit
            )
            goals = try await repository.goals(relationID: relationID)
            error = nil
            return true
        } catch { self.error = error.localizedDescription; return false }
    }

    func updateNextAction(_ goal: SharedGoal, nextAction: String) async -> Bool {
        let normalized = nextAction.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !working, !normalized.isEmpty else { return false }
        working = true; defer { working = false }
        do {
            let value = try await repository.updateGoal(goal.id, nextAction: normalized)
            if let index = goals.firstIndex(where: { $0.id == value.id }) { goals[index] = value }
            error = nil
            return true
        } catch { self.error = error.localizedDescription; return false }
    }

    private static func localDate(_ date: Date) -> String {
        CampusDayCodec.string(from: date)
    }
}

/// E11 · 共同目标（T3）
struct SharedGoalsView: View {
    @StateObject private var model: SharedGoalsViewModel
    @State private var showsCreate = false
    @State private var definition = ""
    @State private var start = Date()
    @State private var end = Date().addingTimeInterval(30 * 86_400)
    @State private var target = 4.0
    @State private var unit = "次"
    @State private var editingGoal: SharedGoal?
    @State private var nextActionDraft = ""

    init(relationID: String, repository: SocialRepository) {
        _model = StateObject(wrappedValue: SharedGoalsViewModel(relationID: relationID, repository: repository))
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "长期共同目标", title: "共同目标", lulu: .poolWaiting)
                OMButton("创建长期共同目标", systemIcon: "plus") { showsCreate = true }
                if model.loading {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                } else if model.goals.isEmpty {
                    OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
                }
                ForEach(model.goals) { goal in goalCard(goal) }
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
        .sheet(isPresented: $showsCreate) { createSheet }
        .alert(
            "编辑下一步",
            isPresented: Binding(
                get: { editingGoal != nil },
                set: { if !$0 { editingGoal = nil } }
            )
        ) {
            TextField("下一次要一起做什么", text: $nextActionDraft)
            Button("取消", role: .cancel) { editingGoal = nil }
            Button("保存") {
                guard let goal = editingGoal else { return }
                Task {
                    if await model.updateNextAction(goal, nextAction: nextActionDraft) {
                        editingGoal = nil
                    }
                }
            }
            .disabled(nextActionDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        } message: {
            Text("这只更新双方可见的下一步，不改写系统记录的事实进度。")
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-E11-shared-goals")
    }

    private func goalCard(_ goal: SharedGoal) -> some View {
        OMCard {
            HStack {
                OMTextRole.t3(goal.definition)
                Spacer()
                OMChip(text: goal.status, kind: .soft)
            }
            OMProgressBar(value: goal.currentValue / max(goal.targetValue, 1))
                .padding(.top, OMTheme.Spacing.s3)
            Text("\(goal.currentValue.formatted()) / \(goal.targetValue.formatted()) \(goal.unit)")
                .font(OMTheme.TypeToken.footnote.weight(.bold))
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.top, 4)
            HStack(spacing: 6) {
                Image(systemName: "checkmark.seal")
                Text("系统自动进度 · 到场与完成事实")
            }
            .font(OMTheme.TypeToken.caption)
            .foregroundStyle(OMTheme.ColorToken.mist)
            .padding(.top, OMTheme.Spacing.s2)
            OMTextRole.cap("\(goal.periodStart) — \(goal.periodEnd)")
                .padding(.top, 2)
            if !goal.milestones.isEmpty {
                HStack(spacing: 8) {
                    ForEach(goal.milestones) { milestone in
                        VStack(spacing: 3) {
                            Image(systemName: milestone.reached ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(milestone.reached ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
                            Text("\(Int(milestone.fraction * 100))%")
                                .font(OMTheme.TypeToken.mono(.caption))
                                .foregroundStyle(OMTheme.ColorToken.mist)
                        }
                        if milestone.id != goal.milestones.last?.id { Spacer(minLength: 0) }
                    }
                }
                .padding(.top, OMTheme.Spacing.s2)
                .accessibilityElement(children: .combine)
                .accessibilityLabel("共同目标里程碑")
            }
            if !goal.memberProgress.isEmpty {
                OMDivider()
                Text("成员事实进度")
                    .font(OMTheme.TypeToken.footnote.weight(.bold))
                    .foregroundStyle(OMTheme.ColorToken.mist)
                ForEach(goal.memberProgress) { member in
                    HStack {
                        Text(member.displayName ?? "成员")
                        Spacer()
                        Text("\(member.currentValue.formatted()) \(goal.unit)")
                            .font(OMTheme.TypeToken.mono(.footnote))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                    }
                    .font(OMTheme.TypeToken.footnote)
                    .padding(.top, 4)
                }
            }
            if let broadcast = goal.lastBroadcast {
                HStack(spacing: 6) {
                    Image(systemName: "wave.3.right")
                    Text(broadcast)
                }
                .font(OMTheme.TypeToken.footnote)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .padding(.top, OMTheme.Spacing.s2)
            }
            if let nextAction = goal.nextAction {
                VStack(alignment: .leading, spacing: 4) {
                    Text("下一步")
                        .font(OMTheme.TypeToken.caption)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                    Text(nextAction).font(OMTheme.TypeToken.callout.weight(.semibold))
                }
                .padding(.top, OMTheme.Spacing.s2)
            }
            OMButton("编辑下一步", kind: .ghost, small: true, fillsWidth: false) {
                nextActionDraft = goal.nextAction ?? ""
                editingGoal = goal
            }
            .padding(.top, OMTheme.Spacing.s3)
            .disabled(model.working || goal.status == "completed")
        }
    }

    private var createSheet: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMCard {
                        VStack(spacing: OMTheme.Spacing.s3) {
                            TextField("共同目标", text: $definition, axis: .vertical)
                                .omInputStyle(multiline: true)
                            HStack(spacing: OMTheme.Spacing.s3) {
                                TextField("目标值", value: $target, format: .number)
                                    .keyboardType(.decimalPad)
                                    .omInputStyle()
                                TextField("单位", text: $unit)
                                    .omInputStyle()
                            }
                        }
                    }
                    OMCard {
                        DatePicker("开始", selection: $start, displayedComponents: .date)
                            .environment(\.timeZone, CampusDayCodec.timeZone)
                            .tint(OMTheme.ColorToken.ink)
                        DatePicker("结束", selection: $end, displayedComponents: .date)
                            .environment(\.timeZone, CampusDayCodec.timeZone)
                            .tint(OMTheme.ColorToken.ink)
                            .padding(.top, OMTheme.Spacing.s2)
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationTitle("创建共同目标")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("取消") { showsCreate = false } }
                ToolbarItem(placement: .confirmationAction) {
                    Button(model.working ? "创建中…" : "创建") {
                        Task {
                            if await model.create(definition: definition, start: start, end: end, target: target, unit: unit) {
                                showsCreate = false; definition = ""
                            }
                        }
                    }
                    .disabled(model.working || definition.isEmpty || unit.isEmpty || target <= 0 || end <= start)
                }
            }
        }
    }
}
