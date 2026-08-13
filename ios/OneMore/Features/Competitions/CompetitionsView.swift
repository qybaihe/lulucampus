import SwiftUI

@MainActor final class CompetitionsViewModel: ObservableObject {
    enum Phase { case loading, loaded([Competition]), failed(String) }
    @Published var phase: Phase = .loading
    @Published var tier: String? = nil
    @Published var tierCatalog: [RecommendationTierMeta] = []
    private let repository: CompetitionRepository
    init(repository: CompetitionRepository) { self.repository = repository }
    func load(force: Bool = false) async {
        if case .loaded = phase {} else { phase = .loading }
        do {
            let items = try await repository.list(force: force, tier: tier)
            guard !Task.isCancelled else { return }
            phase = .loaded(items)
        } catch {
            guard !error.isCancellation, !Task.isCancelled else { return }
            phase = .failed(error.localizedDescription)
        }
        if let catalog = await repository.tiers() {
            guard !Task.isCancelled else { return }
            tierCatalog = catalog.sorted { $0.sortOrder < $1.sortOrder }
        }
    }
    /// 筛选 chip 的可见文案：目录 label 优先，缺目录时按稳定码兜底。
    func tierLabel(_ code: String?) -> String {
        guard let code else { return "全部" }
        return tierCatalog.first { $0.code == code }?.label
            ?? ["A": "优先推荐", "B": "可报名", "C": "补充参考"][code] ?? code
    }
}

/// B12 · 比赛雷达（Tab 根）。视觉对齐 mobile-ios.html#/s/B12。
struct CompetitionsView: View {
    @StateObject private var model: CompetitionsViewModel
    init(repository: CompetitionRepository) { _model = StateObject(wrappedValue: CompetitionsViewModel(repository: repository)) }
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "已核验赛事", title: "比赛", lulu: .homeIdle)
                CompetitionsListContent(model: model)
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task(id: model.tier ?? "all") { await model.load() }
        .refreshable { await model.load(force: true) }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B12-competitions")
    }
}

/// 比赛列表内容（筛选 + 卡片 + 脚注），供 B12 页面与「活动」Tab 复用。
struct CompetitionsListContent: View {
    @ObservedObject var model: CompetitionsViewModel
    @EnvironmentObject private var router: AppRouter
    var body: some View {
        OMSeg(items: [String?.none, "A", "B", "C"], label: { model.tierLabel($0) }, selection: $model.tier)
            .padding(.bottom, OMTheme.Spacing.s3)
        switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load(force: true) }
                        }
                    }
                case let .loaded(items):
                    Text("\(items.count) 场可行动赛事")
                        .font(OMTheme.TypeToken.footnote)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .padding(.bottom, OMTheme.Spacing.s3)
                        .accessibilityIdentifier("competition-count")
                    if items.isEmpty {
                        OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
                    }
                    ForEach(CompetitionSpotlight.rank(items)) { item in
                        Button { router.push(.competition(item.id)) } label: {
                            OMCard(hotSeat: CompetitionSpotlight.isHotSeat(item)) {
                                HStack {
                                    HStack(spacing: 10) {
                                        OMSticker(item.sticker, size: .s44)
                                        VStack(alignment: .leading, spacing: 2) {
                                            competitionTitle(item.name)
                                            OMTextRole.foot(item.tracks.prefix(3).joined(separator: " · "))
                                                .lineLimit(1)
                                        }
                                    }
                                    Spacer()
                                    if let fit = CompetitionSpotlight.fitLabel(item) {
                                        OMChip(text: fit, kind: .gap)
                                    }
                                    OMChip(text: item.recommendationLabel, kind: .standard)
                                }
                                HStack {
                                    OMChip(text: item.teamFormingSupported ? "官方组队" : "备赛搭子", kind: .soft)
                                    if let jackpot = CompetitionSpotlight.chip(item) {
                                        OMChip(text: jackpot, kind: .gap)
                                    }
                                    Spacer()
                                    if let deadline = item.registrationDeadline {
                                        deadlineBadge(deadline)
                                    }
                                }
                                .padding(.top, OMTheme.Spacing.s3)
                            }
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(item.name)
                        .accessibilityIdentifier("competition-\(item.id)")
                    }
                }
    }

    /// 截止时间人性化：>3 天安静陈述，≤3 天才动用蛋黄紧迫标（缺口语义）。
    @ViewBuilder
    private func deadlineBadge(_ deadline: Date) -> some View {
        let daysLeft = max(
            Calendar.current.dateComponents(
                [.day],
                from: Calendar.current.startOfDay(for: Date()),
                to: Calendar.current.startOfDay(for: deadline)
            ).day ?? 0,
            0
        )
        if daysLeft <= 3 {
            OMChip(text: daysLeft == 0 ? "今天截止" : "还剩 \(daysLeft) 天截止", kind: .gap)
        } else {
            HStack(spacing: 4) {
                Image(om: .clock).font(.system(size: 12))
                Text("截止 \(deadline.formatted(.dateTime.month().day())) · 还剩 \(daysLeft) 天")
            }
            .font(OMTheme.TypeToken.footnote)
            .foregroundStyle(OMTheme.ColorToken.mist)
        }
    }

    /// 赛事名长短差异大：按字数阶梯降字号，长标题不再撑成多行大字。
    private func competitionTitle(_ name: String) -> some View {
        let font: Font = switch name.count {
        case ..<13: OMTheme.TypeToken.title3
        case 13..<22: .system(.subheadline, design: .default, weight: .bold)
        default: .system(.footnote, design: .default, weight: .bold)
        }
        return Text(name)
            .font(font)
            .foregroundStyle(OMTheme.ColorToken.ink)
            .lineLimit(2)
            .minimumScaleFactor(0.85)
    }
}
