import SwiftUI

/// 活动 Tab：比赛 + 组局 双分段。比赛段复用 B12 内容；组局段展示公开局
/// （类型 / 地点 / 规模 / 缺口），点击进入详情加入。红线：招募未满员不显示报名人数，
/// 只显示目标规模与服务端已披露的确认进度。
struct ActivityDiscoveryView: View {
    enum Segment: String, CaseIterable {
        case competitions = "比赛"
        case gatherings = "组局"
        case events = "校园活动"
    }

    @StateObject private var competitionsModel: CompetitionsViewModel
    @StateObject private var gatheringsModel: GatheringListViewModel
    @StateObject private var eventsModel: GuestEventsViewModel
    @State private var segment: Segment = {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of: "-ActivitySegment"), args.indices.contains(i + 1),
           let seg = Segment(rawValue: args[i + 1]) { return seg }
        #endif
        return .competitions
    }()

    init(competitions: CompetitionRepository, gatherings: GatheringRepository, events: CampusEventRepository) {
        _competitionsModel = StateObject(wrappedValue: CompetitionsViewModel(repository: competitions))
        _gatheringsModel = StateObject(wrappedValue: GatheringListViewModel(mine: false, repository: gatherings))
        _eventsModel = StateObject(wrappedValue: GuestEventsViewModel(repository: events))
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "发现", title: "活动", lulu: .coreCelebrate)
                OMSeg(items: Segment.allCases, label: \.rawValue, selection: $segment)
                    .padding(.bottom, OMTheme.Spacing.s3)
                switch segment {
                case .competitions:
                    CompetitionsListContent(model: competitionsModel)
                case .gatherings:
                    PublicGatheringsContent(model: gatheringsModel)
                case .events:
                    CampusEventsContent(model: eventsModel)
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await competitionsModel.load() }
        .task { await gatheringsModel.load() }
        .task { await eventsModel.load() }
        .refreshable {
            await competitionsModel.load(force: true)
            await gatheringsModel.load()
            await eventsModel.load(force: true)
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-activity-discovery")
    }
}

/// 组局段：公开局列表（C1 内容的发现位版本）。
private struct PublicGatheringsContent: View {
    @ObservedObject var model: GatheringListViewModel
    @EnvironmentObject private var router: AppRouter

    var body: some View {
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
                OMCard { OMG5StateView(state: .empty, message: "暂时没有招募中的局，有进展时会告诉你。") }
            }
            ForEach(items) { item in
                Button { router.push(.gathering(item.id)) } label: {
                    gatheringCard(item)
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("public-gathering-\(item.id)")
            }
        }
    }

    private func gatheringCard(_ item: GatheringSummary) -> some View {
        OMCard {
            HStack {
                OMChip(text: item.gatheringType, kind: .soft)
                Spacer()
                OMChip(text: item.status.displayName, kind: .standard)
            }
            OMTextRole.t3(item.title)
                .padding(.top, OMTheme.Spacing.s2)
            if !item.goal.isEmpty {
                OMTextRole.foot(item.goal)
                    .padding(.top, 4)
                    .lineLimit(2)
            }
            HStack(spacing: 12) {
                if let location = item.location ?? item.campus {
                    Label(location, systemImage: "mappin")
                }
                if let startAt = item.startAt {
                    Label(startAt.formatted(date: .abbreviated, time: .shortened), systemImage: "clock")
                }
            }
            .font(OMTheme.TypeToken.footnote)
            .foregroundStyle(OMTheme.ColorToken.mist)
            .padding(.top, OMTheme.Spacing.s2)
            HStack(spacing: 10) {
                OMLuluSeatStrip(
                    filled: min(item.memberCount ?? item.confirmedCount ?? 0, item.targetSize),
                    total: item.targetSize
                )
                Text(seatCaption(item))
                    .font(OMTheme.TypeToken.footnote.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                Spacer()
                Image(om: .arrow)
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.mist)
            }
            .padding(.top, OMTheme.Spacing.s2)
        }
    }

    /// 「2/4 · 焦灼等待中」：纯计数 + 状态，不含任何身份。
    private func seatCaption(_ item: GatheringSummary) -> String {
        let filled = min(item.memberCount ?? item.confirmedCount ?? 0, item.targetSize)
        let state: String = switch item.status {
        case .pooling: "焦灼等待中"
        case .tentative: "待确认"
        case .confirmed: "已就位"
        default: item.status.displayName
        }
        return "\(filled)/\(item.targetSize) · \(state)"
    }
}
