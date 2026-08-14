import SwiftUI

@MainActor final class RelationsViewModel: ObservableObject {
    enum Phase { case loading, loaded([RelationSummary]), failed(String) }
    @Published var phase: Phase = .loading
    @Published var mutationError: String?
    @Published var workingRelationID: String?
    private let repository: SocialRepository
    init(repository: SocialRepository) { self.repository = repository }
    func load() async { phase = .loading; do { phase = .loaded(try await repository.relations()) } catch { phase = .failed(error.localizedDescription) } }
    func dissolve(_ id: String) async {
        guard workingRelationID == nil else { return }
        workingRelationID = id; defer { workingRelationID = nil }
        do { try await repository.dissolve(relationID: id); mutationError = nil; phase = .loaded(try await repository.relations()) }
        catch { mutationError = error.localizedDescription }
    }
    func recur(_ id: String) async -> String? {
        guard workingRelationID == nil else { return nil }
        workingRelationID = id
        defer { workingRelationID = nil }
        do {
            let gatheringID = try await repository.recur(relationID: id)
            mutationError = nil
            return gatheringID
        } catch {
            mutationError = error.localizedDescription
            return nil
        }
    }
}

@MainActor final class MessagesViewModel: ObservableObject {
    struct Content {
        let ongoing: [GatheringSummary]
        let relations: [RelationSummary]
        var isEmpty: Bool { ongoing.isEmpty && relations.isEmpty }
    }
    enum Phase { case loading, loaded(Content), failed(String) }
    @Published var phase: Phase = .loading
    private let social: SocialRepository
    private let gatherings: GatheringRepository

    init(social: SocialRepository, gatherings: GatheringRepository) {
        self.social = social
        self.gatherings = gatherings
    }

    func load() async {
        phase = .loading
        do {
            async let relationsTask = social.relations()
            let mine = (try? await gatherings.mine()) ?? []
            let relations = try await relationsTask
            phase = .loaded(Content(ongoing: Self.ongoing(mine), relations: relations))
        } catch { phase = .failed(error.localizedDescription) }
    }

    /// 需要我关注的局：待确认最优先，然后按开始时间由近到远。
    static func ongoing(_ items: [GatheringSummary]) -> [GatheringSummary] {
        let visible: Set<GatheringStatus> = [.pooling, .tentative, .confirmed, .previewed, .executed, .active]
        let now = Date()
        var seen = Set<String>()
        return items
            .filter { item in
                guard visible.contains(item.status) else { return false }
                // 已经结束两小时以上的不再打扰
                if let end = item.endAt, end < now.addingTimeInterval(-7200) { return false }
                return seen.insert(dedupeKey(item)).inserted
            }
            .sorted { lhs, rhs in
                if needsMyConfirmation(lhs) != needsMyConfirmation(rhs) { return needsMyConfirmation(lhs) }
                return (lhs.startAt ?? .distantFuture) < (rhs.startAt ?? .distantFuture)
            }
    }

    static func needsMyConfirmation(_ item: GatheringSummary) -> Bool {
        item.status == .tentative && item.myConfirmation != "confirmed"
    }

    /// demo 数据里同名同时段的重复局只留一张卡。
    private static func dedupeKey(_ item: GatheringSummary) -> String {
        let slot = item.startAt.map { String(Int($0.timeIntervalSince1970 / 1800)) } ?? "-"
        return "\(item.title)|\(item.status.rawValue)|\(slot)"
    }
}

/// MSG · 消息（Tab 根）：正在进行的局 + 搭子频道。视觉对齐 mobile-ios.html#/s/MSG。
struct MessagesView: View {
    @StateObject private var model: MessagesViewModel
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var environment: AppEnvironment

    init(repository: SocialRepository, gatherings: GatheringRepository) {
        _model = StateObject(wrappedValue: MessagesViewModel(social: repository, gatherings: gatherings))
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                OMHeader(title: "消息与搭子", lulu: .homeListening)
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                case let .loaded(content):
                    loaded(content)
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task {
            await model.load()
            await environment.refreshAttention()
        }
        .onAppear {
            Task { await environment.refreshAttention(force: true) }
        }
        .refreshable {
            await model.load()
            await environment.refreshAttention(force: true)
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-MSG-messages")
    }

    @ViewBuilder private func loaded(_ content: MessagesViewModel.Content) -> some View {
        let attention = environment.attentionItems
        if content.isEmpty && attention.isEmpty {
            OMCard {
                VStack(spacing: OMTheme.Spacing.s3) {
                    LuluView(clip: .homeListening, placement: .confirm)
                    OMTextRole.t3("这里还很安静")
                    OMTextRole.cap("成局后的对话会出现在下面。正在进行的局还是上面那些卡片。")
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity)
            }
            OMButton("去差一个，说一句", icon: .spark) { router.selectedTab = .create }
                .padding(.top, OMTheme.Spacing.s2)
        }
        if !attention.isEmpty {
            OMSection(title: "需要你处理")
            OMCard(tight: true) {
                ForEach(Array(attention.enumerated()), id: \.element.id) { index, item in
                    AttentionRow(
                        title: item.title,
                        badge: item.badge,
                        showsDivider: index < attention.count - 1
                    ) {
                        guard let url = URL(string: item.deepLink) else { return }
                        router.handle(url: url, isAuthenticated: environment.session.isAuthenticated)
                    }
                }
            }
            .accessibilityIdentifier("messages-attention")
        }
        if !content.ongoing.isEmpty {
            OMSection(title: "正在进行")
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: OMTheme.Spacing.s3) {
                    ForEach(content.ongoing) { item in
                        OngoingGatheringCard(item: item) { router.push(.gathering(item.id)) }
                    }
                }
                .padding(.vertical, 2)
            }
            .accessibilityIdentifier("messages-ongoing-strip")
        }
        if !content.relations.isEmpty {
            OMSection(title: "对话")
            OMCard(tight: true) {
                ForEach(content.relations) { item in
                    PartnerChannelRow(item: item) {
                        if let channel = item.channelId { router.push(.channel(channel)) }
                        else { router.push(.relations) }
                    }
                }
            }
            .accessibilityIdentifier("messages-chat-list")
            OMButton("查看全部搭子关系", kind: .ghost) { router.push(.relations) }
                .padding(.top, OMTheme.Spacing.s2)
        }
    }
}

/// 正在进行的局：状态导向的横滑卡。
private struct OngoingGatheringCard: View {
    let item: GatheringSummary
    let action: () -> Void

    private var needsMe: Bool { MessagesViewModel.needsMyConfirmation(item) }

    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: OMTheme.Spacing.s2) {
                HStack(spacing: 6) {
                    OMChip(text: statusLabel, kind: needsMe ? .gap : .soft)
                    Spacer(minLength: 0)
                }
                Text(item.title)
                    .font(OMTheme.TypeToken.callout.weight(.bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                Spacer(minLength: 0)
                if item.status == .pooling {
                    SeatDotsView(total: item.targetSize, filled: filledSeats)
                } else if let start = item.startAt {
                    HStack(spacing: 5) {
                        Image(systemName: "clock")
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundStyle(OMTheme.ColorToken.yolkBorder)
                        Text(Self.timeLabel(start))
                            .font(OMTheme.TypeToken.caption.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink.opacity(0.75))
                    }
                }
            }
            .padding(OMTheme.Spacing.s3)
            .frame(width: 172, height: 108, alignment: .topLeading)
            .background(needsMe ? OMTheme.ColorToken.yolk.opacity(0.35) : OMTheme.ColorToken.card)
            .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.medium))
            .overlay {
                RoundedRectangle(cornerRadius: OMTheme.Radius.medium)
                    .stroke(needsMe ? OMTheme.ColorToken.yolkBorder : OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
            }
        }
        .buttonStyle(OMButtonPressStyle())
    }

    private var filledSeats: Int {
        min(item.targetSize, item.memberCount ?? item.confirmedCount ?? 1)
    }

    private var statusLabel: String {
        if needsMe { return "待你确认" }
        switch item.status {
        case .pooling: return "还差 \(max(0, item.targetSize - filledSeats)) 人"
        case .tentative: return "等大家确认"
        case .confirmed, .previewed: return "已成局"
        case .executed, .active: return "进行中"
        default: return item.status.displayName
        }
    }

    private static func timeLabel(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        let calendar = Calendar.current
        if calendar.isDateInToday(date) { formatter.dateFormat = "今天 HH:mm" }
        else if calendar.isDateInTomorrow(date) { formatter.dateFormat = "明天 HH:mm" }
        else { formatter.dateFormat = "M月d日（EEE）HH:mm" }
        return formatter.string(from: date)
    }
}

/// 搭子频道行：称号 + 一起次数 + 最近动态时间。
private struct PartnerChannelRow: View {
    let item: RelationSummary
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: OMTheme.Spacing.s3) {
                OMSticker("chat-bubble.png", size: .s44)
                VStack(alignment: .leading, spacing: 3) {
                    HStack(spacing: 6) {
                        Text(item.peerDisplayName ?? item.participants.map { $0.displayName ?? "同学" }.joined(separator: " · "))
                            .font(OMTheme.TypeToken.callout.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .lineLimit(1)
                        if let title = item.partnerTitle, item.isFixedPartner {
                            OMChip(text: title, kind: .gap)
                        }
                    }
                    Text(subline)
                        .font(OMTheme.TypeToken.caption)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .lineLimit(1)
                }
                Spacer(minLength: 0)
                VStack(alignment: .trailing, spacing: 4) {
                    if let latest = item.lastMessage?.sentAt ?? item.latestExperienceAt {
                        Text(Self.relativeLabel(latest))
                            .font(OMTheme.TypeToken.caption)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                    }
                    Image(systemName: "chevron.right")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(OMTheme.ColorToken.mist)
                }
            }
            .padding(.vertical, 9)
            .contentShape(Rectangle())
        }
        .buttonStyle(OMButtonPressStyle())
    }

    private var subline: String {
        if let preview = item.lastMessage?.content, !preview.isEmpty {
            return preview
        }
        var parts: [String] = []
        if item.timesTogether > 0 { parts.append("一起 \(item.timesTogether) 次") }
        if let recent = item.experiences.first?.gatheringType { parts.append("上次\(recent)") }
        if parts.isEmpty { parts.append("打个招呼吧") }
        return parts.joined(separator: " · ")
    }

    private static func relativeLabel(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.unitsStyle = .short
        return formatter.localizedString(for: date, relativeTo: Date())
    }
}

private struct AttentionRow: View {
    let title: String
    let badge: String?
    let showsDivider: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 8) {
                Text(title)
                    .font(OMTheme.TypeToken.callout.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                    .frame(maxWidth: .infinity, alignment: .leading)
                if let badge {
                    OMGapBadge(text: badge, compact: true)
                }
                Text("›")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.sage)
            }
            .padding(.vertical, 10)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .overlay(alignment: .bottom) {
            if showsDivider {
                Rectangle().fill(OMTheme.ColorToken.line).frame(height: OMTheme.Radius.borderWidth)
            }
        }
    }
}
