import SwiftUI

@MainActor
final class TodayViewModel: ObservableObject {
    enum Phase { case loading, loaded(TodaySummary), failed(String) }
    @Published var phase: Phase = .loading
    private let repository: TodayRepository
    init(repository: TodayRepository) { self.repository = repository }
    func load(force: Bool = false) async {
        phase = .loading
        do { phase = .loaded(try await repository.summary(force: force)) }
        catch { phase = .failed(error.localizedDescription) }
    }
    func ignoreScene(_ key: String) async {
        do { _ = try await repository.ignoreSceneTrigger(key); await load(force: true) }
        catch { phase = .failed(error.localizedDescription) }
    }
}

/// B1 · 今天（Tab 根）。首屏收纳：日程 + Lulu + Hermes 对话框 + 工具图标格。
struct TodayView: View {
    @StateObject private var model: TodayViewModel
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var environment: AppEnvironment
    @State private var hermesText = ""
    init(repository: TodayRepository) { _model = StateObject(wrappedValue: TodayViewModel(repository: repository)) }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                // 顶部：日期 + Lulu
                HStack(alignment: .center) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(Self.dateLine)
                            .font(OMTheme.TypeToken.footnote.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.mist)
                        OMTextRole.t1("今天")
                    }
                    Spacer()
                    LuluView(clip: .homeReply, placement: .confirm)
                }
                .padding(.top, 8)

                if !environment.networkMonitor.isOnline {
                    OMCard {
                        OMG5StateView(state: .offline, message: "可浏览缓存；写操作会等待网络恢复。")
                    }
                }

                TodayPhaseContent(
                    phase: model.phase,
                    onRetry: { Task { await model.load(force: true) } },
                    onIgnoreScene: { key in Task { await model.ignoreScene(key) } },
                    onOpenTimeline: openTimeline,
                    onOpenTimetable: { router.push(.formal(.b3)) },
                    onOpenSceneDetail: { router.push(.formal(.b10)) }
                )

                // Hermes 对话框：首屏直接可问
                OMCard {
                    HStack(spacing: 10) {
                        LuluView(clip: .homeListening, placement: .avatar)
                        VStack(alignment: .leading, spacing: 2) {
                            OMTextRole.t3("问问 \(AppBrand.agentName)")
                            OMTextRole.cap("课表、DDL、场地、公选匹配")
                        }
                        Spacer()
                    }
                    HStack(spacing: 8) {
                        TextField("例如：按我的画像推荐公选", text: $hermesText)
                            .font(OMTheme.TypeToken.callout)
                            .padding(.horizontal, OMTheme.Spacing.s4)
                            .frame(minHeight: 42)
                            .background(OMTheme.ColorToken.paper)
                            .clipShape(Capsule())
                            .overlay { Capsule().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth) }
                            .accessibilityIdentifier("today-hermes-input")
                            .onSubmit { sendHermes() }
                        OMIconButton(icon: .arrow, size: 42, accessibilityLabel: "提问") { sendHermes() }
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                .padding(.top, OMTheme.Spacing.s3)
                .accessibilityIdentifier("today-hermes-entry")

                // 工具收纳：图标格
                OMSection(title: "校园工具")
                OMCard {
                    LazyVGrid(columns: Self.toolColumns, spacing: 14) {
                        toolIcon(sticker: "desk-calendar.png", label: "日程", identifier: "today-timetable") { router.push(.formal(.b3)) }
                        toolIcon(sticker: "poster-blank.png", label: "活动", identifier: "today-events") { router.push(.formal(.b7)) }
                        toolIcon(sticker: "school-bus.png", label: "班车", identifier: "today-transit") { router.push(.formal(.b9)) }
                        toolIcon(sticker: "chair-empty.png", label: "我的局", identifier: "today-my-gatherings") { router.push(.myGatherings) }
                    }
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
        .refreshable {
            await model.load(force: true)
            await environment.refreshAttention(force: true)
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-B1-today")
    }

    private static let toolColumns = Array(repeating: GridItem(.flexible(), spacing: 8), count: 4)

    private func toolIcon(sticker: String, label: String, identifier: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 6) {
                OMSticker(sticker, size: .s44)
                Text(label)
                    .font(OMTheme.TypeToken.caption.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 6)
            .contentShape(Rectangle())
        }
        .buttonStyle(OMButtonPressStyle())
        .accessibilityLabel(label)
        .accessibilityIdentifier(identifier)
    }

    private func sendHermes() {
        let query = hermesText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { router.push(.formal(.b2)); return }
        hermesText = ""
        router.hermesDraft = query
        router.push(.formal(.b2))
    }

    private func openTimeline(_ item: TodaySummary.TimelineItem) {
        if let gatheringID = item.gatheringId {
            router.push(.gathering(gatheringID))
            return
        }
        switch item.kind {
        case "assignment":
            router.push(.formal(.b4))
        case "course":
            router.push(.formal(.b3))
        default:
            router.push(.formal(.b3))
        }
    }

    private static var dateLine: String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "M 月 d 日 · EEEE"
        return formatter.string(from: .now)
    }
}

/// 首屏数据区：独立子视图，避免 LazyVStack 内 switch 不刷新的布局问题。
private struct TodayPhaseContent: View {
    let phase: TodayViewModel.Phase
    let onRetry: () -> Void
    let onIgnoreScene: (String) -> Void
    let onOpenTimeline: (TodaySummary.TimelineItem) -> Void
    let onOpenTimetable: () -> Void
    let onOpenSceneDetail: () -> Void

    var body: some View {
        switch phase {
        case .loading:
            OMCard { OMG5StateView(state: .loading, message: "正在同步…") }
        case let .failed(message):
            OMCard {
                OMG5StateView(state: .networkError, message: message, actionTitle: "重试", action: onRetry)
            }
        case let .loaded(summary):
            if let trigger = summary.sceneTrigger {
                OMCard {
                    HStack(alignment: .top, spacing: 10) {
                        LuluView(clip: .homeReply, placement: .avatar)
                        VStack(alignment: .leading, spacing: 4) {
                            OMTextRole.t3(Self.string(trigger, "title") ?? "现在有个合适的空档")
                            OMTextRole.foot(Self.string(trigger, "text") ?? "现在有一个适合短时协作的校园任务。")
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    HStack(spacing: 8) {
                        OMButton("看看详情", small: true, fillsWidth: false, action: onOpenSceneDetail)
                        OMButton("忽略", kind: .text, small: true, fillsWidth: false) {
                            if let key = Self.string(trigger, "scene_key") { onIgnoreScene(key) }
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                .accessibilityIdentifier("today-scene-trigger")
            }

            OMSection(title: "今日日程", more: ("周历", onOpenTimetable))
            if summary.timeline.isEmpty {
                OMCard {
                    HStack(spacing: 10) {
                        OMSticker("desk-calendar.png", size: .s44)
                        OMTextRole.foot("今天没有课，也没有安排中的活动。")
                        Spacer()
                    }
                }
            } else {
                TodayScheduleTimeline(items: summary.timeline, onTap: onOpenTimeline)
            }
        }
    }

    private static func string(_ value: [String: JSONValue], _ key: String) -> String? {
        guard case let .string(text)? = value[key] else { return nil }
        return text
    }
}

/// Vertical day timeline. Each entry is one `TodayTimelineRow` component:
/// fixed time column · through-going rail · self-contained content card.
private struct TodayScheduleTimeline: View {
    let items: [TodaySummary.TimelineItem]
    let onTap: (TodaySummary.TimelineItem) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(Array(items.enumerated()), id: \.element.id) { index, item in
                TodayTimelineRow(
                    item: item,
                    isFirst: index == 0,
                    isLast: index == items.count - 1,
                    onTap: { onTap(item) }
                )
            }
        }
        .accessibilityIdentifier("today-schedule-timeline")
    }
}

/// 今日日程单条组件：所有排布约束都收在这里，方便针对组件做定制。
private struct TodayTimelineRow: View {
    let item: TodaySummary.TimelineItem
    let isFirst: Bool
    let isLast: Bool
    let onTap: () -> Void

    /// 圆点中心相对行顶的固定距离：内容卡 padding(12) + 标题首行半高(10)。
    /// 时间列与圆点都锚定这个值，保证三列精准对齐。
    private static let anchorY: CGFloat = 22
    private static let timeColumnWidth: CGFloat = 46
    private static let railWidth: CGFloat = 26

    private enum Phase { case past, current, upcoming }

    private var phase: Phase {
        let now = Date.now
        guard let start = item.startAt else { return .upcoming }
        if let end = item.endAt {
            if now > end { return .past }
            return now >= start ? .current : .upcoming
        }
        return now >= start ? .past : .upcoming
    }

    var body: some View {
        Button(action: onTap) {
            HStack(alignment: .top, spacing: 0) {
                timeColumn
                rail
                contentCard
            }
            .padding(.bottom, isLast ? 0 : 10)
            .contentShape(Rectangle())
        }
        .buttonStyle(OMButtonPressStyle())
        .accessibilityLabel("\(item.displayTimeRange) \(item.displayTitle)")
    }

    // MARK: 左列 · 时间

    private var timeColumn: some View {
        VStack(alignment: .trailing, spacing: 2) {
            Text(startLabel)
                .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                .foregroundStyle(phase == .past ? OMTheme.ColorToken.mist : OMTheme.ColorToken.ink)
            if let end = endLabel {
                Text(end)
                    .font(OMTheme.TypeToken.mono(.caption2, weight: .semibold))
                    .foregroundStyle(phase == .past ? OMTheme.ColorToken.mist40 : OMTheme.ColorToken.mist)
            }
        }
        .frame(width: Self.timeColumnWidth, alignment: .trailing)
        .padding(.top, Self.anchorY - 9)
    }

    // MARK: 中列 · 轨道（线贯穿行高，圆点锚定标题行）

    private var rail: some View {
        ZStack(alignment: .top) {
            VStack(spacing: 0) {
                Rectangle()
                    .fill(isFirst ? Color.clear : OMTheme.ColorToken.line)
                    .frame(width: 2, height: Self.anchorY)
                Rectangle()
                    .fill(isLast ? Color.clear : OMTheme.ColorToken.line)
                    .frame(width: 2)
                    .frame(maxHeight: .infinity)
            }
            dot.padding(.top, Self.anchorY - 8)
        }
        .frame(width: Self.railWidth)
        .frame(maxHeight: .infinity)
    }

    @ViewBuilder private var dot: some View {
        switch phase {
        case .current:
            Circle()
                .fill(OMTheme.ColorToken.yolk)
                .frame(width: 12, height: 12)
                .overlay { Circle().stroke(OMTheme.ColorToken.yolkBorder, lineWidth: 1.5) }
                .background {
                    Circle().fill(OMTheme.ColorToken.yolk30).frame(width: 22, height: 22)
                }
                .frame(width: 16, height: 16)
        case .past:
            Circle()
                .fill(OMTheme.ColorToken.mist40)
                .frame(width: 9, height: 9)
                .frame(width: 16, height: 16)
        case .upcoming:
            Circle()
                .fill(OMTheme.ColorToken.card)
                .frame(width: 12, height: 12)
                .overlay { Circle().stroke(OMTheme.ColorToken.ink, lineWidth: 2) }
                .frame(width: 16, height: 16)
        }
    }

    // MARK: 右列 · 内容卡

    private var contentCard: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(item.displayTitle)
                    .font(OMTheme.TypeToken.callout.weight(.semibold))
                    .foregroundStyle(phase == .past ? OMTheme.ColorToken.mist : OMTheme.ColorToken.ink)
                    .multilineTextAlignment(.leading)
                    .lineLimit(2)
                Spacer(minLength: 0)
                kindChip
            }
            if !item.displayDetail.isEmpty {
                HStack(spacing: 4) {
                    Image(systemName: "mappin.and.ellipse")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(OMTheme.ColorToken.mist40)
                    Text(item.displayDetail)
                        .font(OMTheme.TypeToken.footnote)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .multilineTextAlignment(.leading)
                        .lineLimit(1)
                }
            }
            if phase == .current {
                HStack(spacing: 5) {
                    Circle().fill(OMTheme.ColorToken.yolkBorder).frame(width: 6, height: 6)
                    Text("进行中 · \(item.displayTimeRange)")
                        .font(OMTheme.TypeToken.caption.weight(.semibold))
                        .foregroundStyle(OMTheme.ColorToken.ink.opacity(0.72))
                }
                .padding(.top, 1)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(phase == .current ? OMTheme.ColorToken.yolk14 : OMTheme.ColorToken.card)
        .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: OMTheme.Radius.small, style: .continuous)
                .stroke(
                    phase == .current ? OMTheme.ColorToken.yolkBorder : OMTheme.ColorToken.line,
                    lineWidth: OMTheme.Radius.borderWidth
                )
        }
        .opacity(phase == .past ? 0.78 : 1)
    }

    private var kindChip: some View {
        Text(item.kindLabel)
            .font(OMTheme.TypeToken.caption.weight(.semibold))
            .foregroundStyle(OMTheme.ColorToken.ink60)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(chipBackground)
            .clipShape(Capsule())
    }

    private var chipBackground: Color {
        switch item.kind {
        case "gathering": OMTheme.ColorToken.sage.opacity(0.45)
        case "assignment": OMTheme.ColorToken.yolk30
        default: OMTheme.ColorToken.ink06
        }
    }

    // MARK: 时间标签

    private var startLabel: String {
        if let startAt = item.startAt {
            return Self.timeFormatter.string(from: startAt)
        }
        if let head = item.displayTimeRange.split(separator: "–").first { return String(head) }
        return "—"
    }

    private var endLabel: String? {
        if let endAt = item.endAt {
            return Self.timeFormatter.string(from: endAt)
        }
        let parts = item.displayTimeRange.split(separator: "–")
        return parts.count > 1 ? String(parts[1]) : nil
    }

    /// 统一 24 小时制，避免随系统 12/24 设置产生「下午3:00」宽度抖动。
    private static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "HH:mm"
        return formatter
    }()
}
