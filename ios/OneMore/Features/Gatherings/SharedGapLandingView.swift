import SwiftUI

@MainActor
final class SharedGapLandingViewModel: ObservableObject {
    enum Phase { case loading, loaded(GapShare), joining(GapShare), failed(String) }
    @Published var phase: Phase = .loading
    let token: String
    private let repository: GatheringRepository
    init(token: String, repository: GatheringRepository) { self.token = token; self.repository = repository }
    func load() async {
        phase = .loading
        do { phase = .loaded(try await repository.resolveShare(token)) }
        catch { phase = .failed(error.localizedDescription) }
    }
    func join() async throws -> GatheringSummary {
        if case let .loaded(share) = phase { phase = .joining(share) }
        do { return try await repository.joinShare(token) }
        catch { phase = .failed(error.localizedDescription); throw error }
    }
}

/// C4 · 缺口卡落地。视觉对齐 mobile-ios.html#/s/C4：缺口是全场最高视觉权重。
struct SharedGapLandingView: View {
    @StateObject private var model: SharedGapLandingViewModel
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    init(token: String, repository: GatheringRepository) {
        _model = StateObject(wrappedValue: SharedGapLandingViewModel(token: token, repository: repository))
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "匿名缺口卡", title: "这个局，还差一个", lulu: .poolWaiting)
                    .accessibilityIdentifier("screen-C4-share-landing")
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: "正在解析缺口卡…") }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                case let .loaded(share), let .joining(share):
                    shareCard(share)
                }
                OMButton("关闭", kind: .text, small: true, fillsWidth: false) {
                    router.dismissPublicShare()
                    router.popToRoot()
                }
                .padding(.top, OMTheme.Spacing.s3)
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-C4-share-landing")
    }

    @ViewBuilder private func shareCard(_ share: GapShare) -> some View {
        OMCard {
            HStack {
                OMChip(text: share.gatheringType, kind: .gap)
                Spacer()
            }
            OMTextRole.t2(share.title).padding(.top, OMTheme.Spacing.s3)
            OMTextRole.call(share.goal)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .padding(.top, OMTheme.Spacing.s2)
            if let looking = share.lookingFor, !looking.isEmpty {
                OMFlowLayout {
                    ForEach(looking, id: \.self) { role in
                        OMChip(text: CapabilityLabel.displayName(for: role), kind: .gap)
                    }
                }
                .padding(.top, OMTheme.Spacing.s2)
            }
            if let campus = share.campus {
                HStack(spacing: 6) {
                    Image(om: .pin).font(.system(size: 13))
                    Text(campus)
                }
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.top, OMTheme.Spacing.s2)
            }
        }
        if share.joinable {
            OMButton(
                environment.session.isAuthenticated ? "我来" : "认证后我来",
                systemIcon: "person.badge.plus",
                loading: { if case .joining = model.phase { true } else { false } }()
            ) {
                if environment.session.isAuthenticated {
                    Task {
                        do {
                            let gathering = try await model.join()
                            router.dismissPublicShare(); router.path = [.gathering(gathering.id)]
                        } catch {
                            if let requirement = TrustRequirementContext(
                                error: error,
                                recoveryTarget: .share(model.token)
                            ) {
                                router.push(.trustRequirement(requirement))
                            }
                        }
                    }
                } else {
                    environment.recovery.saveExternalRoute(.share(model.token))
                    router.authenticateForShare(model.token)
                }
            }
            .padding(.top, OMTheme.Spacing.s3)
            .accessibilityIdentifier("share-join-button")
        } else {
            OMButton("当前不可加入", disabledReason: "服务端显示该局已结束招募") {}
                .padding(.top, OMTheme.Spacing.s3)
        }
    }
}
