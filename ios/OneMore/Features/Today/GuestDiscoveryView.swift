import SwiftUI

@MainActor
final class GuestEventsViewModel: ObservableObject {
    enum Phase { case loading, loaded([CampusEvent]), failed(String) }
    @Published var phase: Phase = .loading
    private let repository: CampusEventRepository

    init(repository: CampusEventRepository) { self.repository = repository }

    func load(force: Bool = false) async {
        if case .loaded = phase {} else { phase = .loading }
        do {
            let items = try await repository.list(force: force)
            guard !Task.isCancelled else { return }
            phase = .loaded(items)
        } catch {
            guard !error.isCancellation, !Task.isCancelled else { return }
            phase = .failed(error.localizedDescription)
        }
    }
}

/// T0 remains a real browsing mode: official events are public;
/// joining, campus tools, and the 活动 tab cross the auth gate.
struct GuestDiscoveryView: View {
    @StateObject private var model: GuestEventsViewModel
    @EnvironmentObject private var router: AppRouter
    @Environment(\.openURL) private var openURL

    init(repository: CampusEventRepository) {
        _model = StateObject(wrappedValue: GuestEventsViewModel(repository: repository))
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("访客模式")
                            .font(OMTheme.TypeToken.footnote.weight(.bold))
                            .tracking(2)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                        OMTextRole.hero("先看看校园，\n登录后再加入")
                    }
                    Spacer()
                    LuluView(clip: .homeIdle, placement: .confirm)
                }
                .padding(.top, 8)

                OMCard {
                    OMTextRole.t3("登录后，噜噜才能帮你成局")
                    OMTextRole.foot("课表、订场、找搭子和组队比赛都需要先登录。访客只能看看公开活动。")
                        .padding(.top, OMTheme.Spacing.s2)
                }
                .padding(.top, OMTheme.Spacing.s3)
                OMButton("去登录", icon: .person) {
                    router.push(.onboarding("A2"))
                }
                .padding(.top, OMTheme.Spacing.s3)
                .accessibilityIdentifier("guest-login-cta")

                OMSection(title: "公开活动预览")
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load(force: true) }
                        }
                    }
                case let .loaded(events):
                    if events.isEmpty {
                        OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
                    }
                    ForEach(events) { event in
                        OMCard {
                            HStack {
                                OMChip(text: event.displayType, kind: .soft)
                                Spacer()
                            }
                            OMTextRole.t3(event.title).padding(.top, OMTheme.Spacing.s2)
                            HStack(spacing: 6) {
                                Image(om: .cal).font(.system(size: 13))
                                Text(event.startsAt?.formatted(date: .abbreviated, time: .shortened) ?? "时间待官方确认")
                            }
                            .font(OMTheme.TypeToken.footnote)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .padding(.top, OMTheme.Spacing.s2)
                            if let location = event.location {
                                HStack(spacing: 6) {
                                    Image(om: .pin).font(.system(size: 13))
                                    Text(location)
                                }
                                .font(OMTheme.TypeToken.footnote)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                                .padding(.top, 4)
                            }
                            if let url = event.officialUrl {
                                OMButton("打开官方活动页", kind: .ghost, small: true, fillsWidth: false) {
                                    openURL(url)
                                }
                                .padding(.top, OMTheme.Spacing.s3)
                            } else {
                                OMTextRole.cap("官方入口暂未提供").padding(.top, OMTheme.Spacing.s3)
                            }
                        }
                        .accessibilityIdentifier("guest-event-\(event.id)")
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .refreshable { await model.load(force: true) }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-B7-guest-events")
    }
}
