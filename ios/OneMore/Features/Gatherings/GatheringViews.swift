import SwiftUI

enum CampusActionExecutionDisposition: Equatable {
    case succeeded
    case reauthenticate
    case chooseAnotherResource
    case retryLater
    case invalidParameters
    case unknownFailure

    static func resolve(status: String, errorCategory: String?) -> Self {
        guard status == "succeeded" else {
            switch errorCategory {
            case "login_expired": return .reauthenticate
            case "resource_conflict": return .chooseAnotherResource
            case "rate_limited_or_maintenance": return .retryLater
            case "invalid_parameters", "invalid_response": return .invalidParameters
            default: return .unknownFailure
            }
        }
        return .succeeded
    }

    static func recoveryScreen(actionName: String) -> String {
        if actionName.hasPrefix("room.") { return "B6" }
        if actionName.hasPrefix("gym.") { return "B5" }
        return "B2"
    }
}

@MainActor final class GatheringListViewModel: ObservableObject {
    enum Phase { case loading, loaded([GatheringSummary]), failed(String) }
    @Published var phase: Phase = .loading
    let mine: Bool; let repository: GatheringRepository
    init(mine: Bool, repository: GatheringRepository) { self.mine = mine; self.repository = repository }
    func load() async {
        if case .loaded = phase {} else { phase = .loading }
        do {
            let items = try await (mine ? repository.mine() : repository.open())
            guard !Task.isCancelled else { return }
            phase = .loaded(items)
        } catch {
            guard !error.isCancellation, !Task.isCancelled else { return }
            phase = .failed(error.localizedDescription)
        }
    }
}

/// E1 我的局 / C1 公开局。视觉对齐 mobile-ios.html#/s/E1 与 #/s/C1。
struct GatheringListView: View {
    @StateObject private var model: GatheringListViewModel
    @EnvironmentObject private var router: AppRouter
    init(mine: Bool, repository: GatheringRepository) { _model = StateObject(wrappedValue: GatheringListViewModel(mine: mine, repository: repository)) }
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                OMHeader(
                    eyebrow: model.mine ? "我发起的" : "正在招募",
                    title: model.mine ? "我的局" : "公开局",
                    lulu: .poolWaiting
                )
                .accessibilityIdentifier(model.mine ? "screen-E1-my-gatherings-header" : "screen-C1-public-gatherings-header")
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                case let .loaded(items):
                    if items.isEmpty {
                        OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
                    }
                    ForEach(items) { item in
                        gatheringCard(item)
                            .contentShape(Rectangle())
                            .onTapGesture { router.push(.gathering(item.id)) }
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .refreshable { await model.load() }
        .accessibilityIdentifier(model.mine ? "screen-E1-my-gatherings" : "screen-C1-public-gatherings")
    }

    private func gatheringCard(_ item: GatheringSummary) -> some View {
        OMCard {
            HStack {
                OMChip(text: item.gatheringType, kind: .soft)
                Spacer()
                Text(item.status.displayName)
                    .font(OMTheme.TypeToken.caption.weight(.bold))
                    .foregroundStyle(OMTheme.ColorToken.mist)
            }
            OMTextRole.t3(item.title).padding(.top, OMTheme.Spacing.s2)
            OMTextRole.foot(item.goal).padding(.top, 4)
            if item.status == .pooling, let looking = item.lookingFor, !looking.isEmpty {
                OMFlowLayout {
                    ForEach(Array(looking.prefix(3)), id: \.self) { role in
                        OMChip(text: CapabilityLabel.displayName(for: role), kind: .gap)
                    }
                }
                .padding(.top, OMTheme.Spacing.s2)
            }
            if item.status != .pooling, let memberCount = item.memberCount {
                Text("\(memberCount) 人")
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .padding(.top, OMTheme.Spacing.s2)
            }
        }
    }
}

/// E3/E5/E6/E7 · 局详情主链路。红线 17：成局后 Lulu 已退场（E7 是退场点），局内不再出现。
struct GatheringDetailView: View {
    let id: String
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    @State private var item: GatheringSummary?
    @State private var error: String?
    @State private var working = false
    @State private var calendarMessage: String?
    @State private var timeOptions: [GatheringTimeOption] = []
    @State private var rescheduleProposal: RescheduleProposal?
    @State private var campusAction: CampusAction?
    @State private var actionCapability: GatheringActionCapability?
    @State private var bookingOptions: [GatheringBookingOption] = []
    @State private var bookingOptionsLoading = false
    @State private var bookingOptionsMessage: String?
    @State private var backfill: BackfillOpportunity?
    @State private var gapShare: GapShare?
    @State private var icebreaker: IcebreakerPack?
    @State private var showsCelebration = false
    @State private var actionMessage: String?
    @State private var terminalMessage: String?
    @State private var calendarPermissionDenied = false
    @State private var notificationPermissionDenied = false
    @State private var calendarEventExists = false
    @State private var currentUserID: String?
    @State private var calendarScope = "anonymous"
    @State private var retryAction: (() async -> Void)?
    @State private var confirmsLeave = false
    @State private var showsReport = false
    @State private var reportedUserID: String?
    @State private var reportReason = ""
    @State private var reportAndBlock = true
    @State private var showsRecurrenceChoice = false
    @State private var recurrenceKeptUserIDs: Set<String> = []
    @State private var showsActionModification = false
    @State private var actionModificationReason = ""
    @State private var actionModificationResource = ""
    @State private var actionModificationDate = ""
    @State private var actionModificationStart = ""
    @State private var actionModificationEnd = ""
    @State private var actionModificationResourceKey = "room"
    @State private var backfillRefreshTask: Task<Void, Never>?
    @State private var statusRefreshTask: Task<Void, Never>?
    @State private var rescheduleRefreshTask: Task<Void, Never>?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                if let terminalMessage {
                    OMCard {
                        HStack(spacing: 10) {
                            OMSticker("door-exit.png", size: .s44)
                            VStack(alignment: .leading, spacing: 2) {
                                OMTextRole.t2("已退出这个局")
                                OMTextRole.foot(terminalMessage)
                            }
                            Spacer()
                        }
                    }
                    .accessibilityIdentifier("gathering-terminal-state")
                    if let error {
                        OMCard {
                            HStack(spacing: 10) {
                                Image(om: .warn)
                                    .font(.system(size: 17))
                                    .foregroundStyle(OMTheme.ColorToken.ink)
                                    .frame(width: 38, height: 38)
                                    .background(OMTheme.ColorToken.gapSoft)
                                    .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                                VStack(alignment: .leading, spacing: 2) {
                                    OMTextRole.t3("局已退出，日历清理待恢复")
                                    OMTextRole.cap(error)
                                }
                                Spacer()
                            }
                            if retryAction != nil {
                                OMButton("重试清理日历", kind: .ghost, small: true, fillsWidth: false) {
                                    Task { await retryAction?() }
                                }
                                .padding(.top, OMTheme.Spacing.s3)
                            }
                        }
                        .accessibilityIdentifier("gathering-error-recovery")
                    }
                    if let item {
                        OMButton("举报本局 / 拉黑曾同局成员…", kind: .ghost) {
                            let candidates = reportCandidates(item)
                            reportedUserID = candidates.count == 1 ? candidates[0].userId : nil
                            reportReason = ""
                            reportAndBlock = candidates.count == 1
                            showsReport = true
                        }
                        .accessibilityIdentifier("departed-gathering-safety-report")
                    }
                    OMButton("返回我的局", icon: .back) {
                        router.popToRoot()
                        router.selectedTab = .profile
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
                else if let item {
                    if let error {
                        OMCard {
                            HStack(spacing: 10) {
                                Image(om: .warn)
                                    .font(.system(size: 17))
                                    .foregroundStyle(OMTheme.ColorToken.ink)
                                    .frame(width: 38, height: 38)
                                    .background(OMTheme.ColorToken.gapSoft)
                                    .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                                VStack(alignment: .leading, spacing: 2) {
                                    OMTextRole.t3("操作未完成")
                                    OMTextRole.cap(error)
                                }
                                Spacer()
                            }
                            HStack(spacing: 8) {
                                if retryAction != nil {
                                    OMButton("重试上一步", kind: .ghost, small: true, fillsWidth: false) {
                                        Task { await retryAction?() }
                                    }
                                }
                                OMButton("刷新服务端状态", kind: .text, small: true, fillsWidth: false) {
                                    Task { await load() }
                                }
                            }
                            .padding(.top, OMTheme.Spacing.s3)
                        }
                        .accessibilityIdentifier("gathering-error-recovery")
                    }
                    loaded(item)
                }
                else if let error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await load() }
                        }
                    }
                }
                else {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            // Keep terminal/safety actions scrollable above the floating tab bar.
            // Without trailing scroll space, the last actionable row can remain
            // visually present but partially covered by the app chrome.
            .padding(.bottom, 120)
        }
        .background(OMPageBackground())
        .task { await load() }
        .refreshable { await load() }
        .onDisappear {
            backfillRefreshTask?.cancel(); backfillRefreshTask = nil
            statusRefreshTask?.cancel(); statusRefreshTask = nil
            rescheduleRefreshTask?.cancel(); rescheduleRefreshTask = nil
        }
        .confirmationDialog("退出这个局？", isPresented: $confirmsLeave, titleVisibility: .visible) {
            Button("确认退出", role: .destructive) { Task { await leave() } }
            Button("取消", role: .cancel) {}
        } message: { Text(leaveDialogMessage) }
        .sheet(isPresented: $showsReport) { reportSheet }
        .fullScreenCover(isPresented: $showsRecurrenceChoice) { recurrenceChoiceSheet }
        .sheet(isPresented: $showsActionModification) { actionModificationSheet }
        .fullScreenCover(isPresented: $showsCelebration) {
            if let item {
                GatheringCelebrationOverlay(
                    gathering: item,
                    onEnterIcebreaker: { showsCelebration = false },
                    onDismiss: { showsCelebration = false }
                )
            }
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-E3-gathering-detail")
    }

    @ViewBuilder private func loaded(_ item: GatheringSummary) -> some View {
        OMHeader(eyebrow: "\(item.gatheringType) · \(item.status.displayName)", title: item.title, lulu: .confirmGather)
        OMCard {
            OMTextRole.t3(item.goal)
            if let mood = item.moodNote, !mood.isEmpty {
                MoodNoteQuote(text: mood)
                    .padding(.top, OMTheme.Spacing.s2)
            }
            if let location = item.location {
                HStack(spacing: 6) {
                    Image(om: .pin).font(.system(size: 13))
                    Text(location)
                }
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.top, OMTheme.Spacing.s2)
            }
            if let start = item.startAt {
                HStack(spacing: 6) {
                    Image(om: .cal).font(.system(size: 13))
                    Text(start.formatted(date: .abbreviated, time: .shortened))
                }
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.top, 4)
            }
        }
        if let reason = item.matchReason, !reason.isEmpty {
            OMCard {
                OMTextRole.t3("为什么是你们")
                OMTextRole.foot(reason).padding(.top, OMTheme.Spacing.s2)
            }
        }
        if item.status == .pooling {
            OMCard {
                HStack {
                    OMTextRole.t3("桌上已经有谁")
                    Spacer()
                    if let count = item.memberCount {
                        Text("\(min(count, item.targetSize))/\(item.targetSize)")
                            .font(OMTheme.TypeToken.footnote.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                    }
                }
                if let count = item.memberCount {
                    OMLuluSeatStrip(filled: min(count, item.targetSize), total: item.targetSize)
                        .padding(.top, OMTheme.Spacing.s2)
                }
                if let filled = item.filledRoles, !filled.isEmpty {
                    OMFlowLayout {
                        ForEach(filled, id: \.self) { role in
                            OMChip(text: CapabilityLabel.displayName(for: role), kind: .soft)
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
                if let highlights = item.rosterHighlights, !highlights.isEmpty {
                    OMFlowLayout {
                        ForEach(highlights, id: \.self) { highlight in
                            OMChip(text: highlight, kind: .standard)
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
            }
        }
        if item.status == .pooling, let looking = item.lookingFor, !looking.isEmpty {
            OMCard {
                OMTextRole.t3("这桌还在找")
                OMFlowLayout {
                    ForEach(looking, id: \.self) { role in
                        OMChip(text: CapabilityLabel.displayName(for: role), kind: .gap)
                    }
                }
                .padding(.top, OMTheme.Spacing.s2)
            }
        }
        if let participants = item.participants {
            OMCard {
                OMTextRole.t3("参与成员")
                ForEach(participants) { person in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(person.displayName ?? "待确认同学")
                            .font(OMTheme.TypeToken.callout)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .redacted(reason: item.status == .tentative ? .placeholder : [])
                        if item.status != .tentative, !person.interestTags.isEmpty {
                            Text(person.interestTags.prefix(4).joined(separator: " · "))
                                .font(OMTheme.TypeToken.footnote)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                        }
                        if item.status != .tentative, let summary = person.tasteSummary, !summary.isEmpty {
                            Text(summary)
                                .font(OMTheme.TypeToken.caption)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                                .lineLimit(2)
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
            }
        }
        if let icebreaker {
            IcebreakerCardView(pack: icebreaker) { channelID in
                router.push(.channel(channelID))
            }
        }
        statusActions(item)
        if item.status == .pooling, item.myConfirmation != nil { shareActions(item) }
        if let channel = item.channelId {
            OMButton("进入局内消息", systemIcon: "message") { router.push(.channel(channel)) }
                .padding(.top, OMTheme.Spacing.s2)
                .accessibilityIdentifier("gathering-collaboration-space")
        }
        if [.executed, .active, .completed].contains(item.status), item.startAt != nil, item.endAt != nil {
            calendarActions(item)
        }
        safetyActions(item)
        if notificationPermissionDenied {
            OMCard {
                OMTextRole.t3("成局通知权限未开启")
                OMTextRole.foot("本次局仍可正常使用；可稍后重试，或到系统设置开启通知。")
                    .padding(.top, OMTheme.Spacing.s2)
                OMButton("打开系统设置", kind: .ghost, small: true, fillsWidth: false) {
                    environment.permissions.openSystemSettings()
                }
                .padding(.top, OMTheme.Spacing.s3)
            }
        }
        if let actionMessage {
            OMTextRole.cap(actionMessage).padding(.top, OMTheme.Spacing.s2)
        }
    }

    @ViewBuilder private func statusActions(_ item: GatheringSummary) -> some View {
        switch item.status {
        case .pooling:
            if let backfill {
                backfillActions(backfill)
            } else if item.myConfirmation == nil {
                OMButton("加入这个局", systemIcon: "person.badge.plus", loading: working) {
                    Task { await join() }
                }
                .padding(.top, OMTheme.Spacing.s2)
            } else {
                OMCard {
                    VStack(spacing: 2) {
                        LuluView(clip: .poolWaiting, placement: .empty)
                        OMTextRole.t3("噜噜正在翻今晚有空的同学……")
                        if item.targetSize > 0 {
                            SeatDotsView(total: item.targetSize, filled: 1)
                                .padding(.top, OMTheme.Spacing.s3)
                        }
                    }
                    .frame(maxWidth: .infinity)
                }
                .accessibilityIdentifier("gathering-pool-waiting")
            }
        case .tentative:
            OMCard {
                HStack(spacing: 10) {
                    OMSticker("party-popper.png", size: .s44)
                    OMTextRole.t3("人齐了，分别确认")
                    Spacer()
                }
                if let count = item.confirmedCount {
                    Text("\(count) / \(item.targetSize) 已确认")
                        .font(OMTheme.TypeToken.mono(.callout, weight: .bold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .padding(.top, OMTheme.Spacing.s2)
                }
            }
            .accessibilityIdentifier("gathering-confirmation-actions")
            OMButton("确认参加", systemIcon: "checkmark.circle", loading: working) {
                Task { await confirm(true) }
            }
            .padding(.top, OMTheme.Spacing.s2)
            OMButton("暂不参加", kind: .ghost) { Task { await confirm(false) } }
                .padding(.top, OMTheme.Spacing.s2)
            rescheduleActions(item)
        case .confirmed, .previewed:
            actionPreviewActions(item)
            rescheduleActions(item)
        case .executed, .active:
            if campusAction != nil {
                actionPreviewActions(item)
            }
            if let endAt = item.endAt, endAt <= .now {
                OMButton("确认本次已完成", systemIcon: "checkmark.seal") { Task { await complete(true) } }
                    .padding(.top, OMTheme.Spacing.s2)
                    .accessibilityIdentifier("gathering-completion-actions")
                OMButton("这次没有完成", kind: .ghost) { Task { await complete(false) } }
                    .padding(.top, OMTheme.Spacing.s2)
            } else {
                OMCard {
                    HStack(spacing: 10) {
                        OMSticker("alarm-clock.png", size: .s44)
                        VStack(alignment: .leading, spacing: 2) {
                            OMTextRole.t3(item.status == .active ? "这次局正在进行" : "预约已完成，等待开始")
                            OMTextRole.foot("服务端记录的结束时间到达后，才会开放完成确认。")
                        }
                        Spacer()
                    }
                }
                OMButton("结束后确认完成", disabledReason: "尚未到服务端结束时间") {}
                    .padding(.top, OMTheme.Spacing.s2)
            }
        case .completed:
            if let decision = item.myRecurrenceDecision {
                OMCard {
                    HStack(spacing: 10) {
                        OMSticker(decision.decision == "ended" ? "door-exit.png" : "redo-arrow.png", size: .s44)
                        VStack(alignment: .leading, spacing: 2) {
                            OMTextRole.t3(recurrenceDecisionTitle(decision))
                            OMTextRole.foot(decision.decision == "ended" ? "选择已保存" : "你的选择已保存")
                        }
                        Spacer()
                    }
                    if let cloneID = decision.cloneGatheringId {
                        OMButton("打开新的局", kind: .ghost, small: true, fillsWidth: false) {
                            router.push(.gathering(cloneID))
                        }
                        .padding(.top, OMTheme.Spacing.s3)
                    }
                }
            } else {
                HStack(spacing: 8) {
                    OMButton("再来一次", systemIcon: "arrow.clockwise", kind: .ghost, small: true) {
                        recurrenceKeptUserIDs = []
                        showsRecurrenceChoice = true
                    }
                    .accessibilityIdentifier("gathering-recurrence-actions")
                    OMButton("T3 · 周期固定局", systemIcon: "repeat", kind: .ghost, small: true) {
                        router.push(.recurringGathering(item.id))
                    }
                }
                .padding(.top, OMTheme.Spacing.s2)
            }
        default:
            EmptyView()
        }
    }

    @ViewBuilder private func backfillActions(_ opportunity: BackfillOpportunity) -> some View {
        OMCard {
            HStack(spacing: 10) {
                OMSticker("chair-empty.png", size: .s44)
                VStack(alignment: .leading, spacing: 2) {
                    OMTextRole.t3("E8 · 补位缺口")
                    if !opportunity.open {
                        OMTextRole.foot("补位窗口已结束")
                    } else if opportunity.fastLaneActive {
                        OMTextRole.foot(opportunity.viewerFastLaneEligible ? "T3 补位快速通道已开放" : "T3 补位快速通道进行中")
                        if let until = opportunity.fastLaneUntil {
                            OMTextRole.cap("普通候选可于 \(until.formatted(date: .omitted, time: .shortened)) 后确认补位。")
                        }
                    } else {
                        OMTextRole.foot("补位窗口已开放")
                    }
                }
                Spacer()
            }
        }
        .accessibilityIdentifier("gathering-backfill-actions")
        if opportunity.open && opportunity.viewerHasMatchingIntent {
            if opportunity.fastLaneActive && !opportunity.viewerFastLaneEligible {
                OMButton("等待快速通道结束", disabledReason: "T3 候选拥有前 15 分钟补位优先权") {}
                    .padding(.top, OMTheme.Spacing.s2)
            } else {
                OMButton("确认补位", systemIcon: "person.fill.checkmark", loading: working) {
                    Task { await claimBackfill() }
                }
                .padding(.top, OMTheme.Spacing.s2)
            }
        } else if opportunity.open {
            OMButton("等待匹配候选补位", disabledReason: "只有持有相符有效意图的候选可以确认") {}
                .padding(.top, OMTheme.Spacing.s2)
        }
        if opportunity.viewerIsMember, !opportunity.fallbackOptions.isEmpty {
            OMSection(title: "补位失败时")
            ForEach(opportunity.fallbackOptions) { option in
                OMCard {
                    OMTextRole.t3(option.title)
                    OMTextRole.foot(option.summary).padding(.top, OMTheme.Spacing.s2)
                    OMTextRole.cap("新方案：最低 \(option.minSize) 人 · 目标 \(option.targetSize) 人\(option.location.map { " · \($0)" } ?? "")")
                        .padding(.top, 4)
                    OMButton("采用并让成员重新确认", kind: .ghost, small: true, fillsWidth: false, loading: working) {
                        Task { await applyFallback(option) }
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
            }
        }
    }

    @ViewBuilder private func actionPreviewActions(_ item: GatheringSummary) -> some View {
        if let campusAction {
            OMCard {
                OMTextRole.t3("校园写操作预览")
                Text(campusAction.actionName)
                    .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .padding(.top, OMTheme.Spacing.s2)
                OMTextRole.cap("将提交").padding(.top, OMTheme.Spacing.s3)
                ForEach(Array(flattened(campusAction.params).enumerated()), id: \.offset) { _, row in
                    HStack(alignment: .top) {
                        Text(row.0).foregroundStyle(OMTheme.ColorToken.mist)
                        Spacer(minLength: 10)
                        Text(row.1).multilineTextAlignment(.trailing).textSelection(.enabled)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                    }
                    .font(OMTheme.TypeToken.footnote)
                    .padding(.top, 4)
                    .accessibilityElement(children: .combine)
                }
                OMTextRole.cap("服务端预览").padding(.top, OMTheme.Spacing.s3)
                ForEach(Array(flattened(campusAction.previewSnapshot).enumerated()), id: \.offset) { _, row in
                    HStack(alignment: .top) {
                        Text(row.0).foregroundStyle(OMTheme.ColorToken.mist)
                        Spacer(minLength: 10)
                        Text(row.1).multilineTextAlignment(.trailing).textSelection(.enabled)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                    }
                    .font(OMTheme.TypeToken.footnote)
                    .padding(.top, 4)
                    .accessibilityElement(children: .combine)
                }
                Text("\(campusAction.authorization.authorizedCount) / \(campusAction.authorization.requiredCount) 位成员已核对")
                    .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .padding(.top, OMTheme.Spacing.s3)
            }
            .accessibilityIdentifier(campusAction.status == "succeeded" || campusAction.status == "failed" ? "gathering-action-result" : "gathering-action-preview")
            if campusAction.status == "previewed" {
                if campusAction.authorization.actorDecision != "authorized" {
                    OMButton("核对无误，分别确认", systemIcon: "checkmark.shield", loading: working) {
                        Task { await authorize(campusAction) }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                } else if !campusAction.authorization.allAuthorized {
                    OMButton("等待其他成员确认", disabledReason: "每位当前成员都要核对同一份预览") {}
                        .padding(.top, OMTheme.Spacing.s2)
                } else if campusAction.userId == currentUserID {
                    OMButton("全员已确认，由我执行", systemIcon: "bolt.fill", loading: working) {
                        Task { await execute(campusAction) }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                } else {
                    OMButton("已完成分别确认", disabledReason: "等待本局发起人的授权代理提交") {}
                        .padding(.top, OMTheme.Spacing.s2)
                }
                OMButton("提议修改预览…", kind: .ghost) {
                    prepareActionModification(campusAction)
                    showsActionModification = true
                }
                .padding(.top, OMTheme.Spacing.s2)
                .disabled(working)
            } else {
                HStack(spacing: 8) {
                    Image(systemName: campusAction.status == "succeeded" ? "checkmark.seal.fill" : "exclamationmark.triangle.fill")
                    Text(campusAction.status == "succeeded" ? "校园写操作已完成" : "校园写操作未完成")
                }
                .font(OMTheme.TypeToken.footnote.weight(.bold))
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.top, OMTheme.Spacing.s2)
            }
        } else if let capability = actionCapability {
            if let pending = capability.pendingModification {
                OMCard {
                    HStack(spacing: 10) {
                        Image(om: .doc)
                            .font(.system(size: 17))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .frame(width: 38, height: 38)
                            .background(OMTheme.ColorToken.gapSoft)
                            .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                        OMTextRole.t3("成员匿名修改建议")
                        Spacer()
                    }
                    OMTextRole.call(pending.reason).padding(.top, OMTheme.Spacing.s2)
                    OMTextRole.cap("建议后的完整参数").padding(.top, OMTheme.Spacing.s3)
                    ForEach(Array(flattened(pending.proposedParams).enumerated()), id: \.offset) { _, row in
                        HStack(alignment: .top) {
                            Text(row.0).foregroundStyle(OMTheme.ColorToken.mist)
                            Spacer(minLength: 10)
                            Text(row.1).multilineTextAlignment(.trailing).textSelection(.enabled)
                                .foregroundStyle(OMTheme.ColorToken.ink)
                        }
                        .font(OMTheme.TypeToken.footnote)
                        .padding(.top, 4)
                    }
                }
                if capability.enabled,
                   !pending.proposedParams.isEmpty,
                   let action = capability.action {
                    OMButton("应用建议并生成新版预览", systemIcon: "checkmark.circle", loading: working) {
                        Task { await preview(item, action: action, params: pending.proposedParams) }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
            }
            if capability.enabled, capability.action != nil {
                OMButton(capability.pendingModification == nil ? "生成校园写操作预览" : "使用服务端当前参数生成", systemIcon: "doc.text.magnifyingglass", loading: working) {
                    Task { await preview(item, capability: capability) }
                }
                .padding(.top, OMTheme.Spacing.s2)
            } else {
                OMButton("当前无可执行校园操作", disabledReason: capability.disabledReason ?? "等待服务端状态") {}
                    .padding(.top, OMTheme.Spacing.s2)
                if bookingPlanNeeded(capability) {
                    OMButton("查询真实可预约场地", systemIcon: "building.2", kind: .ghost, loading: bookingOptionsLoading) {
                        Task { await loadBookingOptions() }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                    if !bookingOptions.isEmpty {
                        OMCard {
                            OMTextRole.t3("\(AppBrand.agentName) 实时可预约结果")
                            ForEach(bookingOptions) { option in
                                Button {
                                    Task { await selectBookingOption(option) }
                                } label: {
                                    HStack {
                                        VStack(alignment: .leading) {
                                            Text(option.label)
                                                .font(OMTheme.TypeToken.callout.weight(.semibold))
                                                .foregroundStyle(OMTheme.ColorToken.ink)
                                            Text(option.startAt.formatted(date: .abbreviated, time: .shortened) + " — " + option.endAt.formatted(date: .omitted, time: .shortened))
                                                .font(OMTheme.TypeToken.footnote)
                                                .foregroundStyle(OMTheme.ColorToken.mist)
                                        }
                                        Spacer()
                                        Image(systemName: "checkmark.circle").foregroundStyle(OMTheme.ColorToken.sage)
                                    }
                                    .padding(.vertical, 10)
                                    .contentShape(Rectangle())
                                }
                                .buttonStyle(.plain)
                                .disabled(working)
                                .accessibilityIdentifier("gathering-booking-option")
                            }
                        }
                        .accessibilityElement(children: .contain)
                        .accessibilityIdentifier("gathering-booking-options")
                    }
                    if let bookingOptionsMessage {
                        OMTextRole.cap(bookingOptionsMessage).padding(.top, OMTheme.Spacing.s2)
                    }
                }
            }
        } else {
            OMButton("当前无可执行校园操作", disabledReason: actionCapability?.disabledReason ?? "正在读取服务端能力") {}
                .padding(.top, OMTheme.Spacing.s2)
        }
    }

    @ViewBuilder private func rescheduleActions(_ item: GatheringSummary) -> some View {
        if let proposal = rescheduleProposal {
            OMCard {
                HStack {
                    OMTextRole.t3("匿名改约确认")
                    Spacer()
                    OMChip(text: rescheduleStatusLabel(proposal.status), kind: proposal.status == "accepted" ? .solid : .gap)
                }
                Text(proposal.startAt.formatted(date: .abbreviated, time: .shortened) + " — " + proposal.endAt.formatted(date: .omitted, time: .shortened))
                    .font(OMTheme.TypeToken.callout.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .padding(.top, OMTheme.Spacing.s2)
                OMTextRole.foot("\(proposal.acceptedCount) / \(proposal.requiredCount) 已确认")
                    .padding(.top, 4)
                if proposal.status == "open", proposal.myVote == nil {
                    HStack(spacing: 8) {
                        OMButton("同意新时间", small: true, loading: working) {
                            Task { await voteReschedule(proposal, accepted: true) }
                        }
                        OMButton("保留原时间", kind: .ghost, small: true) {
                            Task { await voteReschedule(proposal, accepted: false) }
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                } else if proposal.status == "open" {
                    OMTextRole.foot("你的选择已保存，等待其余成员。")
                        .padding(.top, OMTheme.Spacing.s2)
                } else if proposal.status == "rejected" {
                    OMTextRole.foot("提议未通过，原时间保持不变。")
                        .padding(.top, OMTheme.Spacing.s2)
                }
            }
            .accessibilityIdentifier("gathering-reschedule-actions")
        }
        if rescheduleProposal?.status != "open" {
            OMButton("查看共同可改约时段", kind: .ghost) { Task { await loadTimeOptions() } }
                .padding(.top, OMTheme.Spacing.s2)
            ForEach(timeOptions.prefix(3)) { option in
                Button {
                    Task { await reschedule(startAt: option.startAt, endAt: option.endAt) }
                } label: {
                    HStack {
                        Text(option.startAt.formatted(date: .abbreviated, time: .shortened))
                            .font(OMTheme.TypeToken.callout.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                        Spacer()
                        Text("\(option.feasibleCount) 人可行")
                            .font(OMTheme.TypeToken.footnote)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                    }
                    .padding(.vertical, 12)
                    .padding(.horizontal, OMTheme.Spacing.s4)
                    .background(OMTheme.ColorToken.card)
                    .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.medium))
                    .overlay {
                        RoundedRectangle(cornerRadius: OMTheme.Radius.medium)
                            .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .disabled(working || !option.campusReachable)
                .opacity(option.campusReachable ? 1 : 0.45)
                .padding(.top, OMTheme.Spacing.s2)
            }
        }
    }

    @ViewBuilder private func calendarActions(_ item: GatheringSummary) -> some View {
        OMButton("加入 / 更新系统日历", systemIcon: "calendar.badge.plus", kind: .ghost) {
            Task { await syncCalendar(item) }
        }
        .padding(.top, OMTheme.Spacing.s2)
        if calendarEventExists {
            OMButton("从系统日历删除", kind: .text, small: true, fillsWidth: false) {
                Task { await deleteCalendar(item) }
            }
        }
        if let calendarMessage {
            OMTextRole.cap(calendarMessage).padding(.top, OMTheme.Spacing.s2)
        }
        if calendarPermissionDenied {
            OMButton("打开日历权限设置", kind: .ghost, small: true, fillsWidth: false) {
                environment.permissions.openSystemSettings()
            }
        }
    }

    @ViewBuilder private func safetyActions(_ item: GatheringSummary) -> some View {
        if item.myConfirmation != nil {
            if ![.completed, .archived, .dissolved].contains(item.status) {
                if let capability = item.leaveCapability {
                    HStack(spacing: 6) {
                        Image(systemName: capability.trustImpact == "late_exit" ? "exclamationmark.triangle.fill" : "checkmark.shield")
                        Text(capability.message)
                    }
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(capability.trustImpact == "late_exit" ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist)
                    .padding(.top, OMTheme.Spacing.s3)
                }
                OMButton("退出这个局…", kind: .ghost) { confirmsLeave = true }
                    .padding(.top, OMTheme.Spacing.s2)
                    .disabled(item.leaveCapability?.enabled == false)
                    .accessibilityIdentifier("gathering-leave-action")
            }
            OMButton("举报本局 / 拉黑成员…", kind: .text, small: true, fillsWidth: false) {
                let candidates = reportCandidates(item)
                reportedUserID = candidates.count == 1 ? candidates[0].userId : nil
                reportReason = ""
                reportAndBlock = candidates.count == 1
                showsReport = true
            }
            .accessibilityIdentifier("gathering-safety-report")
        }
    }

    @ViewBuilder private func shareActions(_ item: GatheringSummary) -> some View {
        if let gapShare {
            OMCard {
                HStack {
                    OMTextRole.t3("缺口卡")
                    Spacer()
                    OMGapBadge(count: gapShare.missingCount ?? 1)
                }
                if let start = gapShare.startAt {
                    HStack(spacing: 6) {
                        Image(om: .cal).font(.system(size: 13))
                        Text(start.formatted(date: .abbreviated, time: .shortened))
                        if let campus = gapShare.campus { Text("· \(campus)") }
                    }
                    .font(OMTheme.TypeToken.callout)
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .padding(.top, OMTheme.Spacing.s2)
                }
                if let mood = gapShare.moodNote, !mood.isEmpty {
                    MoodNoteQuote(text: mood)
                        .padding(.top, OMTheme.Spacing.s2)
                }
                if let looking = gapShare.lookingFor, !looking.isEmpty {
                    OMFlowLayout {
                        ForEach(looking, id: \.self) { role in
                            OMChip(text: CapabilityLabel.displayName(for: role), kind: .gap)
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
                Text(gapShare.universalLink.absoluteString)
                    .font(OMTheme.TypeToken.mono(.caption))
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .textSelection(.enabled)
                    .padding(.top, OMTheme.Spacing.s2)
            }
            ShareLink(item: gapShare.universalLink, subject: Text(item.title), message: Text(shareMessage(item, gapShare: gapShare))) {
                Label("系统分享缺口卡", systemImage: "square.and.arrow.up")
                    .font(OMTheme.TypeToken.body.weight(.bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .frame(maxWidth: .infinity, minHeight: 52)
                    .background(OMTheme.ColorToken.yolk)
                    .clipShape(Capsule())
                    .overlay { Capsule().stroke(OMTheme.ColorToken.yolkBorder, lineWidth: OMTheme.Radius.borderWidth) }
            }
            .padding(.top, OMTheme.Spacing.s2)
            .accessibilityIdentifier("gathering-share-link")
        } else {
            OMButton("生成无身份缺口卡", icon: .share, kind: .ghost) { Task { await createShare() } }
                .padding(.top, OMTheme.Spacing.s2)
                .accessibilityIdentifier("gathering-create-share")
        }
    }

    private var reportSheet: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    if let item, !reportCandidates(item).isEmpty {
                        OMSection(title: "举报对象")
                        OMCard(tight: true) {
                            ForEach(reportCandidates(item)) { participant in
                                OMRow(
                                    sticker: "id-card.png",
                                    title: participant.displayName ?? "已确认成员",
                                    onTap: { reportedUserID = participant.userId }
                                ) {
                                    if reportedUserID == participant.userId {
                                        Image(om: .check)
                                            .font(.system(size: 15, weight: .bold))
                                            .foregroundStyle(OMTheme.ColorToken.ink)
                                    }
                                }
                            }
                        }
                    } else {
                        OMCard {
                            HStack(spacing: 10) {
                                OMSticker("flag.png", size: .s44)
                                OMTextRole.t3("匿名安全上报")
                                Spacer()
                            }
                        }
                    }
                    OMSection(title: "举报原因")
                    OMCard {
                        TextField("请描述需要平台复核的事实", text: $reportReason, axis: .vertical)
                            .omInputStyle(multiline: true)
                        if reportedUserID != nil {
                            HStack {
                                OMTextRole.t3("同时拉黑该成员")
                                Spacer()
                                OMSwitch(isOn: $reportAndBlock)
                            }
                            .padding(.top, OMTheme.Spacing.s3)
                        }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .accessibilityIdentifier("gathering-report-sheet")
            .navigationTitle("举报与拉黑")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("取消") { showsReport = false } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("提交") {
                        showsReport = false
                        Task { await report(userID: reportedUserID) }
                    }
                    .disabled(
                        reportReason.trimmingCharacters(in: .whitespacesAndNewlines).count < 5 ||
                        (item.map { !reportCandidates($0).isEmpty } == true && reportedUserID == nil)
                    )
                }
            }
        }
    }

    /// D · 复局满屏三选一：原班再来 / 保留部分回池 / 安静结束。
    private var recurrenceChoiceSheet: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    VStack(spacing: 4) {
                        LuluView(clip: .homeReply, placement: .empty)
                        Text("这局完成了")
                            .font(OMTheme.TypeToken.caption.weight(.semibold))
                            .tracking(2)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                        OMTextRole.t1("下一次怎么继续？")
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                    .padding(.bottom, OMTheme.Spacing.s4)
                    recurrenceOptionCard(
                        sticker: "redo-arrow.png",
                        title: "原班再来一次",
                        detail: "同一桌人、同样的类型；时间地点可以再商量。",
                        accent: true
                    ) {
                        Task { await recur(keepUserIDs: nil) }
                    }
                    if let item, !recurrenceCandidates(item).isEmpty {
                        OMCard {
                            HStack(spacing: 10) {
                                OMSticker("chair-empty.png", size: .s44)
                                OMTextRole.t3("保留部分成员，再差一个")
                                Spacer()
                            }
                            ForEach(recurrenceCandidates(item)) { participant in
                                HStack {
                                    OMTextRole.call(participant.displayName ?? "已确认成员")
                                    Spacer()
                                    OMSwitch(isOn: Binding(
                                        get: { recurrenceKeptUserIDs.contains(participant.userId) },
                                        set: { selected in
                                            if selected { recurrenceKeptUserIDs.insert(participant.userId) }
                                            else { recurrenceKeptUserIDs.remove(participant.userId) }
                                        }
                                    ))
                                }
                                .padding(.top, OMTheme.Spacing.s2)
                            }
                            OMButton("保留所选并回池补人", small: true, loading: working, disabledReason: recurrenceKeptUserIDs.isEmpty ? "先选择要保留的成员" : nil) {
                                Task { await recur(keepUserIDs: Array(recurrenceKeptUserIDs).sorted()) }
                            }
                            .padding(.top, OMTheme.Spacing.s3)
                        }
                    }
                    recurrenceOptionCard(
                        sticker: "door-exit.png",
                        title: "安静结束",
                        detail: "不再发起复局；其他成员看不到你的选择，也不会收到通知。",
                        accent: false
                    ) {
                        Task { await finishRecurrenceChoice() }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationTitle("复局选择")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("稍后决定") { showsRecurrenceChoice = false }
                }
            }
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-E10-recurrence-choice")
    }

    private func recurrenceOptionCard(
        sticker: String, title: String, detail: String, accent: Bool, action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            HStack(spacing: 12) {
                OMSticker(sticker, size: .s44)
                VStack(alignment: .leading, spacing: 3) {
                    Text(title)
                        .font(OMTheme.TypeToken.title3)
                        .foregroundStyle(OMTheme.ColorToken.ink)
                    Text(detail)
                        .font(OMTheme.TypeToken.footnote)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .multilineTextAlignment(.leading)
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(OMTheme.ColorToken.mist)
            }
            .padding(OMTheme.Spacing.s4)
            .background(accent ? OMTheme.ColorToken.gapSoft : OMTheme.ColorToken.card)
            .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.large, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: OMTheme.Radius.large, style: .continuous)
                    .stroke(accent ? OMTheme.ColorToken.yolkBorder : OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(OMButtonPressStyle())
        .disabled(working)
        .padding(.top, OMTheme.Spacing.s2)
    }

    private var actionModificationSheet: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMSection(title: "为什么需要修改")
                    OMCard {
                        TextField(
                            "例如：时间可以，但希望换成东区 401",
                            text: $actionModificationReason,
                            axis: .vertical
                        )
                        .omInputStyle(multiline: true)
                    }
                    OMSection(title: "修改后的可执行参数")
                    OMCard {
                        VStack(spacing: OMTheme.Spacing.s3) {
                            TextField(actionModificationResourceKey == "room" ? "研讨室编号" : "资源", text: $actionModificationResource)
                                .omInputStyle()
                            if !actionModificationDate.isEmpty {
                                TextField("日期 YYYY-MM-DD", text: $actionModificationDate)
                                    .omInputStyle()
                            }
                            if !actionModificationStart.isEmpty || !actionModificationEnd.isEmpty {
                                HStack(spacing: OMTheme.Spacing.s3) {
                                    if !actionModificationStart.isEmpty {
                                        TextField("开始 HH:mm", text: $actionModificationStart)
                                            .omInputStyle()
                                    }
                                    if !actionModificationEnd.isEmpty {
                                        TextField("结束 HH:mm", text: $actionModificationEnd)
                                            .omInputStyle()
                                    }
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationTitle("提议修改")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { showsActionModification = false }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("提交建议") { Task { await submitActionModification() } }
                        .disabled(
                            working || actionModificationReason
                                .trimmingCharacters(in: .whitespacesAndNewlines).count < 5
                                || !actionModificationHasChanges
                        )
                }
            }
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-E5-action-modification")
    }

    private func load() async {
        do {
            currentUserID = await environment.auth.currentUserID()
            calendarScope = await environment.auth.cacheScope()
            let previousStatus = item?.status
            let value = try await environment.gatherings.detail(id)
            item = value; error = nil
            celebrateIfJustConfirmed(from: previousStatus, to: value)
            await loadIcebreakerIfNeeded(value)
            scheduleStatusRefresh(value)
            backfill = nil
            if value.status == .pooling {
                do {
                    let opportunity = try await environment.gatherings.backfill(id)
                    if opportunity.open || (opportunity.viewerIsMember && !opportunity.fallbackOptions.isEmpty) {
                        backfill = opportunity
                        if opportunity.open { scheduleBackfillRefresh(opportunity) }
                    }
                }
                catch let APIClientError.server(status, _) where [403, 404, 409].contains(status) {}
            }
            calendarEventExists = await environment.calendarReconciler.hasEvent(gatheringID: id, scope: calendarScope)
            retryAction = nil
            if let actionID = value.actionId {
                campusAction = try await environment.actions.detail(actionID)
                actionCapability = nil
                bookingOptions = []
            } else if [.confirmed, .previewed].contains(value.status) {
                campusAction = nil
                do { actionCapability = try await environment.gatherings.actionCapability(id) }
                catch let APIClientError.server(status, _) where status == 403 {
                    actionCapability = .init(
                        enabled: false,
                        action: nil,
                        params: [:],
                        disabledReason: "等待本局发起人生成行动预览",
                        pendingModification: nil
                    )
                }
            } else {
                actionCapability = nil
                campusAction = nil
                bookingOptions = []
            }
            if [.tentative, .confirmed].contains(value.status) {
                notificationPermissionDenied = !(await environment.permissions.requestNotificationsAndRegister())
            }
            if [.tentative, .confirmed, .previewed].contains(value.status) {
                rescheduleProposal = try? await environment.gatherings.currentReschedule(id)
                scheduleRescheduleRefresh()
            } else {
                rescheduleProposal = nil
                rescheduleRefreshTask?.cancel()
                rescheduleRefreshTask = nil
            }
            switch value.status {
            case .tentative: environment.motion.trigger(.gatheringTentative)
            case .previewed: environment.motion.trigger(.previewReady)
            case .executed: environment.motion.trigger(.executeSucceeded)
            case .pooling where value.expiresAt.map({ $0 < .now }) == true: environment.motion.trigger(.poolingExpired)
            default: break
            }
        } catch { self.error = error.localizedDescription }
    }

    private func run(_ operation: @escaping () async throws -> Void) async {
        guard !working else { return }
        working = true
        error = nil
        retryAction = nil
        defer { working = false }
        do { try await operation() }
        catch {
            if let requirement = TrustRequirementContext(
                error: error,
                recoveryTarget: .gathering(id)
            ) {
                router.push(.trustRequirement(requirement))
                return
            }
            self.error = error.localizedDescription
            retryAction = { await run(operation) }
        }
    }

    private func join() async { await run { item = try await environment.gatherings.join(id) } }
    private func claimBackfill() async {
        await run {
            item = try await environment.gatherings.claimBackfill(id)
            backfill = nil
            actionMessage = "补位已确认；此前协作记录不会向你开放。"
        }
    }
    private func applyFallback(_ option: BackfillOpportunity.FallbackOption) async {
        await run {
            item = try await environment.gatherings.applyBackfillFallback(id, optionKey: option.key)
            backfill = nil
            actionMessage = "已采用“\(option.title)”；当前成员需要分别重新确认。"
        }
    }
    private func scheduleBackfillRefresh(_ opportunity: BackfillOpportunity) {
        backfillRefreshTask?.cancel()
        guard opportunity.fastLaneActive, let boundary = opportunity.fastLaneUntil else { return }
        let delay = max(0.25, boundary.timeIntervalSinceNow + 0.15)
        backfillRefreshTask = Task {
            try? await Task.sleep(for: .seconds(delay))
            guard !Task.isCancelled else { return }
            await load()
        }
    }
    private func scheduleStatusRefresh(_ gathering: GatheringSummary) {
        statusRefreshTask?.cancel()
        let boundary: Date?
        switch gathering.status {
        case .confirmed, .previewed, .executed:
            boundary = gathering.startAt
        case .active:
            boundary = gathering.endAt
        default:
            boundary = nil
        }
        guard let boundary else { return }
        let delay = max(0.5, boundary.timeIntervalSinceNow + 0.2)
        statusRefreshTask = Task {
            try? await Task.sleep(for: .seconds(delay))
            guard !Task.isCancelled else { return }
            await load()
        }
    }
    private func leave() async {
        var succeeded = false
        await run {
            let result = try await environment.gatherings.leave(id)
            succeeded = true
            if result.status == .pooling || result.status == .tentative {
                environment.motion.trigger(.backfillStarted)
                terminalMessage = "服务端已开始中性补位；不会向其他成员暴露你的退出原因。"
            } else {
                terminalMessage = "服务端已中性处理状态；不会向其他成员暴露你的退出原因。"
            }
        }
        if succeeded { await reconcileCalendarAfterLeave() }
    }
    private func confirm(_ confirmed: Bool) async {
        await run { item = try await environment.gatherings.confirm(id, confirmed: confirmed) }
        if confirmed, let value = item, value.status == .confirmed {
            celebrateIfJustConfirmed(from: .tentative, to: value)
            await load()
        }
    }

    /// A3 · 全员确认落定的那 3 秒：只在本会话第一次看到状态跃迁时全屏庆祝。
    private func celebrateIfJustConfirmed(from previous: GatheringStatus?, to value: GatheringSummary) {
        guard value.status == .confirmed,
              let previous, [.pooling, .tentative].contains(previous),
              GatheringCelebrationTracker.markCelebrated(value.id)
        else { return }
        environment.motion.trigger(.gatheringTentative)
        showsCelebration = true
    }

    private func loadIcebreakerIfNeeded(_ value: GatheringSummary) async {
        guard [.confirmed, .previewed, .executed, .active].contains(value.status),
              value.myConfirmation != nil else {
            icebreaker = nil
            return
        }
        guard icebreaker?.gatheringId != value.id else { return }
        icebreaker = try? await environment.gatherings.icebreaker(value.id)
    }
    private func complete(_ completed: Bool) async {
        await run { item = try await environment.gatherings.complete(id, completed: completed) }
        // D · 复局是主路径：完成确认后直接进入满屏三选一，而不是等用户翻到角落。
        if completed, item?.status == .completed, item?.myRecurrenceDecision == nil {
            recurrenceKeptUserIDs = []
            showsRecurrenceChoice = true
        }
    }
    private func recur(keepUserIDs: [String]?) async {
        var cloneID: String?
        await run {
            let clone = try await environment.gatherings.recur(id, keepUserIDs: keepUserIDs)
            cloneID = clone.id
            actionMessage = keepUserIDs == nil ? "原班复局已创建" : "保留成员的补人局已创建"
        }
        guard let cloneID else { return }
        showsRecurrenceChoice = false
        await load()
        router.push(.gathering(cloneID))
    }
    private func finishRecurrenceChoice() async {
        var succeeded = false
        await run {
            try await environment.gatherings.finishRecurrenceChoice(id)
            succeeded = true
        }
        guard succeeded else { return }
        showsRecurrenceChoice = false
        await load()
    }
    private func loadTimeOptions() async { await run { timeOptions = try await environment.gatherings.timeOptions(id) } }
    private func reschedule(startAt: Date, endAt: Date) async {
        await run {
            rescheduleProposal = try await environment.gatherings.reschedule(id, startAt: startAt, endAt: endAt)
            timeOptions = []
            actionMessage = "匿名改约提议已提交；全员同意前原时间保持不变。"
        }
        scheduleRescheduleRefresh()
    }

    private func voteReschedule(_ proposal: RescheduleProposal, accepted: Bool) async {
        var becameAccepted = false
        await run {
            let updated = try await environment.gatherings.voteReschedule(
                id, proposalID: proposal.id, accepted: accepted
            )
            rescheduleProposal = updated
            becameAccepted = updated.status == "accepted"
            actionMessage = accepted ? "你的匿名确认已保存。" : "已保留原时间；不会展示是谁拒绝。"
        }
        if becameAccepted { await reconcileAcceptedReschedule() }
        else { scheduleRescheduleRefresh() }
    }

    private func scheduleRescheduleRefresh() {
        rescheduleRefreshTask?.cancel()
        guard rescheduleProposal?.status == "open" else { return }
        rescheduleRefreshTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(5))
                guard !Task.isCancelled else { return }
                guard let proposal = try? await environment.gatherings.currentReschedule(id) else { return }
                rescheduleProposal = proposal
                if proposal.status != "open" {
                    if proposal.status == "accepted" { await reconcileAcceptedReschedule() }
                    return
                }
            }
        }
    }

    private func reconcileAcceptedReschedule() async {
        await load()
        guard let item, let start = item.startAt, let end = item.endAt else { return }
        let descriptor = calendarDescriptor(item, start: start, end: end)
        do {
            if try await environment.calendarReconciler.updateIfPresent(
                gatheringID: id, scope: calendarScope, descriptor: descriptor
            ) {
                calendarEventExists = true
                calendarMessage = "全员同意后已同步系统日历"
            }
        } catch {
            calendarMessage = "改约已生效，系统日历更新待重试：\(error.localizedDescription)"
            retryAction = { await retryCalendarUpdate(descriptor) }
        }
    }

    private func rescheduleStatusLabel(_ status: String) -> String {
        switch status {
        case "open": return "确认中"
        case "accepted": return "全员同意"
        case "rejected": return "未通过"
        case "expired": return "已过期"
        default: return "已失效"
        }
    }
    private func report(userID: String?) async {
        await run {
            _ = try await environment.gatherings.report(id, userID: userID, reason: reportReason, block: reportAndBlock && userID != nil)
            actionMessage = reportAndBlock && userID != nil ? "举报与拉黑已提交" : "安全举报已提交"
        }
    }

    private func createShare() async { await run { gapShare = try await environment.gatherings.createShare(id) } }

    /// 班级群里的自然传播物：「周六 14:00 珠海 羽毛球 还差 1 人」。
    private func shareMessage(_ item: GatheringSummary, gapShare: GapShare) -> String {
        var parts: [String] = []
        if let start = gapShare.startAt {
            parts.append(start.formatted(.dateTime.weekday(.wide).hour().minute()))
        }
        if let campus = gapShare.campus { parts.append(campus) }
        parts.append(item.gatheringType)
        parts.append("还差 \(gapShare.missingCount ?? 1) 人")
        if let looking = gapShare.lookingFor, !looking.isEmpty {
            let labels = looking.prefix(2).map { CapabilityLabel.displayName(for: $0) }
            parts.append("还缺\(labels.joined(separator: "、"))")
        }
        return parts.joined(separator: " ")
    }

    private func preview(_ item: GatheringSummary, capability: GatheringActionCapability) async {
        guard let action = capability.action else { return }
        await preview(item, action: action, params: capability.params)
    }

    private func bookingPlanNeeded(_ capability: GatheringActionCapability) -> Bool {
        guard !capability.enabled, let reason = capability.disabledReason else { return false }
        return reason.contains("地点") || reason.contains("场地")
    }

    private func loadBookingOptions() async {
        guard !bookingOptionsLoading else { return }
        bookingOptionsLoading = true
        bookingOptionsMessage = nil
        defer { bookingOptionsLoading = false }
        do {
            bookingOptions = try await environment.gatherings.bookingOptions(id)
            if bookingOptions.isEmpty { bookingOptionsMessage = "当前时段没有服务端确认可预约的场地。" }
        } catch {
            bookingOptionsMessage = error.localizedDescription
        }
    }

    private func selectBookingOption(_ option: GatheringBookingOption) async {
        await run {
            item = try await environment.gatherings.selectBookingPlan(
                id, optionToken: option.optionToken
            )
            bookingOptions = []
            bookingOptionsMessage = "场地已由服务端再次核验；正在读取行动能力。"
        }
        await load()
    }

    private func preview(
        _ item: GatheringSummary, action: String, params: [String: JSONValue]
    ) async {
        await run {
            campusAction = try await environment.actions.preview(action: action, params: params, gatheringID: item.id)
            environment.motion.trigger(.previewReady)
        }
    }

    private func execute(_ action: CampusAction) async {
        environment.motion.trigger(.executeStarted)
        await run {
            do {
                let result = try await environment.actions.execute(action)
                campusAction = result
                switch CampusActionExecutionDisposition.resolve(
                    status: result.status,
                    errorCategory: result.errorCategory
                ) {
                case .succeeded:
                    environment.motion.trigger(.executeSucceeded)
                    actionMessage = "执行成功；噜噜已退场。"
                    await load()
                case .reauthenticate:
                    environment.motion.trigger(.executeFailed)
                    actionMessage = "校园登录已失效，重新扫码后会回到这次局。"
                    router.recoverAfterSessionExpired(.gathering(id))
                case .chooseAnotherResource:
                    environment.motion.trigger(.executeFailed)
                    actionMessage = "原资源已被占用，请从服务端共同可行时段中重选。"
                    await load()
                    timeOptions = try await environment.gatherings.timeOptions(id)
                case .retryLater:
                    environment.motion.trigger(.executeFailed)
                    actionMessage = "校园系统限流或维护中；状态未伪装为成功，可稍后重新生成预览。"
                    await load()
                case .invalidParameters:
                    environment.motion.trigger(.executeFailed)
                    actionMessage = "预览参数已不再有效，请刷新局信息后重新生成。"
                    await load()
                case .unknownFailure:
                    environment.motion.trigger(.executeFailed)
                    actionMessage = "校园操作未完成；服务端已回滚局状态，可刷新后重试。"
                    await load()
                }
            } catch {
                environment.motion.trigger(.executeFailed)
                throw error
            }
        }
    }

    private func authorize(_ action: CampusAction) async {
        await run {
            campusAction = try await environment.actions.authorize(action, authorized: true)
            actionMessage = "你已确认同一份行动预览；等待其余成员。"
        }
    }

    private func submitActionModification() async {
        guard let action = campusAction else { return }
        let reason = actionModificationReason.trimmingCharacters(in: .whitespacesAndNewlines)
        var succeeded = false
        await run {
            var proposed: [String: JSONValue] = [:]
            if !actionModificationResource.isEmpty {
                proposed[actionModificationResourceKey] = .string(actionModificationResource)
            }
            if !actionModificationDate.isEmpty { proposed["date"] = .string(actionModificationDate) }
            if !actionModificationStart.isEmpty { proposed["start"] = .string(actionModificationStart) }
            if !actionModificationEnd.isEmpty { proposed["end"] = .string(actionModificationEnd) }
            campusAction = try await environment.actions.proposeModification(
                action, reason: reason, proposedParams: proposed
            )
            succeeded = true
        }
        guard succeeded else { return }
        showsActionModification = false
        actionMessage = "旧预览已失效；请由发起人生成新预览并让全员重新核对。"
        await load()
    }

    private func prepareActionModification(_ action: CampusAction) {
        actionModificationReason = ""
        let resourceKey = ["room", "venue", "seminar_id"].first { action.params[$0] != nil } ?? "room"
        actionModificationResourceKey = resourceKey
        actionModificationResource = stringValue(action.params[resourceKey]) ?? ""
        actionModificationDate = stringValue(action.params["date"]) ?? ""
        actionModificationStart = stringValue(action.params["start"]) ?? ""
        actionModificationEnd = stringValue(action.params["end"]) ?? ""
    }

    private var actionModificationHasChanges: Bool {
        guard let action = campusAction else { return false }
        return actionModificationResource != (stringValue(action.params[actionModificationResourceKey]) ?? "")
            || actionModificationDate != (stringValue(action.params["date"]) ?? "")
            || actionModificationStart != (stringValue(action.params["start"]) ?? "")
            || actionModificationEnd != (stringValue(action.params["end"]) ?? "")
    }

    private func stringValue(_ value: JSONValue?) -> String? {
        guard case let .string(text)? = value else { return nil }
        return text
    }

    private func flattened(_ dictionary: [String: JSONValue]) -> [(String, String)] {
        dictionary.keys.sorted().flatMap { key in flatten(dictionary[key] ?? .null, path: key) }
    }

    private func flatten(_ value: JSONValue, path: String) -> [(String, String)] {
        switch value {
        case let .string(value): return [(path, value)]
        case let .number(value): return [(path, String(value))]
        case let .bool(value): return [(path, value ? "是" : "否")]
        case .null: return [(path, "—")]
        case let .array(values):
            if values.isEmpty { return [(path, "空列表")] }
            return values.enumerated().flatMap { index, item in
                flatten(item, path: "\(path)[\(index + 1)]")
            }
        case let .object(values):
            if values.isEmpty { return [(path, "空对象")] }
            return values.keys.sorted().flatMap { key in
                flatten(values[key] ?? .null, path: "\(path).\(key)")
            }
        }
    }

    private func syncCalendar(_ item: GatheringSummary) async {
        guard let start = item.startAt, let end = item.endAt else { return }
        do {
            _ = try await environment.calendarReconciler.addOrUpdate(
                gatheringID: item.id,
                scope: calendarScope,
                descriptor: calendarDescriptor(item, start: start, end: end),
                requestAccess: !calendarEventExists
            )
            calendarPermissionDenied = false
            calendarEventExists = true
            calendarMessage = "已同步系统日历"
        } catch {
            if case CalendarReconciliationError.accessDenied = error { calendarPermissionDenied = true }
            calendarMessage = error.localizedDescription
        }
    }
    private func deleteCalendar(_ item: GatheringSummary) async {
        do {
            _ = try await environment.calendarReconciler.removeIfPresent(gatheringID: item.id, scope: calendarScope)
            calendarEventExists = false
            calendarMessage = "已从系统日历删除"
        } catch { calendarMessage = error.localizedDescription }
    }

    private func reportCandidates(_ item: GatheringSummary) -> [GatheringSummary.Participant] {
        let legal = item.reportableParticipants.isEmpty
            ? (item.participants ?? [])
            : item.reportableParticipants
        return legal.filter { $0.userId != currentUserID }
    }

    private func recurrenceCandidates(_ item: GatheringSummary) -> [GatheringSummary.Participant] {
        (item.participants ?? []).filter { $0.userId != currentUserID }
    }

    private func recurrenceDecisionTitle(_ decision: GatheringSummary.RecurrenceDecision) -> String {
        switch decision.decision {
        case "same_group": return "已选择原班复局"
        case "partial": return "已选择保留部分成员"
        case "ended": return "已安静结束"
        default: return "复局选择已保存"
        }
    }

    private var leaveDialogMessage: String {
        item?.leaveCapability?.message
            ?? "确定退出这个局？"
    }

    private func calendarDescriptor(_ item: GatheringSummary, start: Date, end: Date) -> CalendarEventDescriptor {
        .init(
            title: item.title,
            start: start,
            end: end,
            location: item.location,
            notes: "onemore://gathering/\(item.id)/space"
        )
    }

    private func reconcileCalendarAfterLeave() async {
        do {
            if try await environment.calendarReconciler.removeIfPresent(gatheringID: id, scope: calendarScope) {
                calendarEventExists = false
                calendarMessage = "退出后已删除系统日历事件"
            }
        } catch {
            self.error = "局已退出；系统日历清理失败：\(error.localizedDescription)"
            retryAction = { await retryCalendarDeletion() }
        }
    }

    private func retryCalendarDeletion() async {
        do {
            _ = try await environment.calendarReconciler.removeIfPresent(gatheringID: id, scope: calendarScope)
            calendarEventExists = false
            calendarMessage = "系统日历已清理"
            error = nil
            retryAction = nil
        } catch { self.error = error.localizedDescription }
    }

    private func retryCalendarUpdate(_ descriptor: CalendarEventDescriptor) async {
        do {
            _ = try await environment.calendarReconciler.updateIfPresent(gatheringID: id, scope: calendarScope, descriptor: descriptor)
            calendarEventExists = true
            calendarMessage = "系统日历已更新"
            error = nil
            retryAction = nil
        } catch { self.error = error.localizedDescription }
    }
}

/// E13 · 历史局安全与举报
struct DepartedSafetyHistoryView: View {
    let repository: GatheringRepository
    @State private var contexts: [DepartedSafetyContext] = []
    @State private var loading = true
    @State private var error: String?
    @State private var selected: DepartedSafetyContext?
    @State private var targetUserID: String?
    @State private var reason = ""
    @State private var alsoBlock = true
    @State private var message: String?
    @State private var submitting = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "安全与举报", title: "历史局安全与举报", lulu: .coreCare)
                if loading {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                } else if contexts.isEmpty {
                    OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
                }
                ForEach(contexts) { context in
                    OMCard {
                        HStack {
                            OMChip(text: context.gatheringType, kind: .soft)
                            Spacer()
                            Text(context.status.displayName)
                                .font(OMTheme.TypeToken.caption)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                        }
                        OMTextRole.t3(context.title).padding(.top, OMTheme.Spacing.s2)
                        OMTextRole.foot("已于 \(context.leftAt.formatted(date: .abbreviated, time: .shortened)) 退出")
                            .padding(.top, 4)
                        if !context.reportableParticipants.isEmpty {
                            OMTextRole.cap(context.reportableParticipants.map { $0.displayName ?? "已披露成员" }.joined(separator: "、"))
                                .padding(.top, OMTheme.Spacing.s2)
                        }
                        OMButton("举报本局 / 拉黑曾同局成员…", kind: .ghost, small: true, fillsWidth: false) {
                            selected = context
                            targetUserID = context.reportableParticipants.count == 1
                                ? context.reportableParticipants[0].userId : nil
                            reason = ""
                            alsoBlock = context.reportableParticipants.count == 1
                        }
                        .padding(.top, OMTheme.Spacing.s3)
                    }
                }
                if let message {
                    OMTextRole.foot(message).padding(.top, OMTheme.Spacing.s2)
                }
                if let error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await load() }
                        }
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await load() }
        .refreshable { await load() }
        .sheet(item: $selected) { context in reportSheet(context) }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-E13-departed-safety-history")
    }

    private func reportSheet(_ context: DepartedSafetyContext) -> some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    if !context.reportableParticipants.isEmpty {
                        OMSection(title: "举报对象")
                        OMCard(tight: true) {
                            ForEach(context.reportableParticipants) { participant in
                                OMRow(
                                    sticker: "id-card.png",
                                    title: participant.displayName ?? "已披露成员",
                                    onTap: { targetUserID = participant.userId }
                                ) {
                                    if targetUserID == participant.userId {
                                        Image(om: .check)
                                            .font(.system(size: 15, weight: .bold))
                                            .foregroundStyle(OMTheme.ColorToken.ink)
                                    }
                                }
                            }
                        }
                    } else {
                        OMCard {
                            HStack(spacing: 10) {
                                OMSticker("flag.png", size: .s44)
                                OMTextRole.t3("匿名安全上报")
                                Spacer()
                            }
                        }
                    }
                    OMSection(title: "举报原因")
                    OMCard {
                        TextField("描述需要平台核查的事实", text: $reason, axis: .vertical)
                            .omInputStyle(multiline: true)
                        if targetUserID != nil {
                            HStack {
                                OMTextRole.t3("同时拉黑该成员")
                                Spacer()
                                OMSwitch(isOn: $alsoBlock)
                            }
                            .padding(.top, OMTheme.Spacing.s3)
                        }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationTitle("历史局安全上报")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { selected = nil }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(submitting ? "提交中…" : "提交") {
                        Task { await submit(context) }
                    }
                    .disabled(
                        submitting
                            || reason.trimmingCharacters(in: .whitespacesAndNewlines).count < 5
                            || (!context.reportableParticipants.isEmpty && targetUserID == nil)
                    )
                }
            }
        }
    }

    private func load() async {
        loading = true
        defer { loading = false }
        do {
            contexts = try await repository.departedSafetyHistory()
            error = nil
        } catch { self.error = error.localizedDescription }
    }

    private func submit(_ context: DepartedSafetyContext) async {
        guard !submitting else { return }
        submitting = true
        defer { submitting = false }
        do {
            _ = try await repository.report(
                context.gatheringId,
                userID: targetUserID,
                reason: reason.trimmingCharacters(in: .whitespacesAndNewlines),
                block: alsoBlock && targetUserID != nil
            )
            selected = nil
            message = alsoBlock && targetUserID != nil
                ? "举报与拉黑已提交" : "安全举报已提交"
            error = nil
        } catch { self.error = error.localizedDescription }
    }
}
