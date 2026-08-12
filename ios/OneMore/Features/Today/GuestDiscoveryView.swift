import SwiftUI

@MainActor
final class GuestEventsViewModel: ObservableObject {
    enum Phase { case loading, loaded([CampusEvent]), failed(String) }
    @Published var phase: Phase = .loading
    private let repository: CampusEventRepository

    init(repository: CampusEventRepository) { self.repository = repository }

    func load(force: Bool = false) async {
        phase = .loading
        do { phase = .loaded(try await repository.list(force: force)) }
        catch { phase = .failed(error.localizedDescription) }
    }
}

/// T0 remains a real browsing mode: official events and the 24 verified
/// competitions are public; joining or forming a team crosses the auth gate.
struct GuestDiscoveryView: View {
    @StateObject private var model: GuestEventsViewModel
    @EnvironmentObject private var environment: AppEnvironment
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
                        OMTextRole.hero("先逛校园，\n再决定加入")
                    }
                    Spacer()
                    LuluView(clip: .homeIdle, placement: .confirm)
                }
                .padding(.top, 8)

                OMSection(title: "校园活动")
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
                                OMChip(text: event.type, kind: .soft)
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
