import SwiftUI
import UIKit

/// Tab Bar 定制图标位图加载（带缓存）；资源未就位时返回 nil 走 SF Symbol。
private enum OMTabIconAssets {
    private static var cache: [String: UIImage?] = [:]

    static func image(for tab: RootTab, selected: Bool) -> UIImage? {
        let base: String = switch tab {
        case .today: "tab-today"
        case .competitions: "tab-activity"
        case .create: "tab-create"
        case .messages: "tab-messages"
        case .profile: "tab-profile"
        }
        let name = "\(base)-\(selected ? "active" : "inactive")"
        if let cached = cache[name] { return cached }
        // Xcode's Copy Bundle Resources phase flattens file-group resources;
        // keep the subdirectory lookup as a fallback for folder-based builds.
        let image = (Bundle.main.url(forResource: name, withExtension: "png")
            ?? Bundle.main.url(
                forResource: name,
                withExtension: "png",
                subdirectory: "LuluGenerated/TabBar"
            ))
            .flatMap { UIImage(contentsOfFile: $0.path) }
            .flatMap { source -> UIImage? in
                guard let cgImage = source.cgImage else {
                    return source.withRenderingMode(.alwaysOriginal)
                }
                // `tabItem` extracts the underlying UIImage and ignores normal
                // SwiftUI sizing modifiers. Give UIKit the intended point size
                // while preserving the 512px production master for resampling.
                let points: CGFloat = tab == .create ? 30 : 26
                return UIImage(
                    cgImage: cgImage,
                    scale: CGFloat(cgImage.width) / points,
                    orientation: source.imageOrientation
                ).withRenderingMode(.alwaysOriginal)
            }
        cache[name] = image
        return image
    }
}

private struct OMTabIcon: View {
    let tab: RootTab
    let selected: Bool

    var body: some View {
        if let image = OMTabIconAssets.image(for: tab, selected: selected) {
            Image(uiImage: image)
                .renderingMode(.original)
        } else {
            Image(systemName: tab == .create ? "plus.circle.fill" : tab.symbol)
        }
    }
}

struct RootView: View {
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var environment: AppEnvironment
    var body: some View {
        Group {
            if let token = router.publicShareToken {
                SharedGapLandingView(token: token, repository: environment.gatherings)
            } else {
                NavigationStack(path: $router.path) {
                    Group {
                        if environment.session.isAuthenticated && environment.session.needsOnboarding {
                            FirstUseSetupView(repository: environment.identity)
                        } else {
                            TabView(selection: $router.selectedTab) {
                                Group {
                                    if environment.session.isAuthenticated {
                                        TodayView(repository: environment.today)
                                    } else {
                                        GuestDiscoveryView(repository: environment.campusEvents)
                                    }
                                }
                                .tag(RootTab.today)
                                .tabItem { tabItemLabel(.today) }
                                authenticatedTab {
                                    ActivityDiscoveryView(competitions: environment.competitions, gatherings: environment.gatherings, events: environment.campusEvents)
                                }
                                    .tag(RootTab.competitions)
                                    .tabItem { tabItemLabel(.competitions) }
                                authenticatedTab {
                                    SocialAccessGate(repository: environment.identity) {
                                        IntentComposerView(repository: environment.intents)
                                    }
                                }
                                    .tag(RootTab.create)
                                    .tabItem { tabItemLabel(.create) }
                                authenticatedTab {
                                    SocialAccessGate(repository: environment.identity) {
                                        MessagesView(repository: environment.social, gatherings: environment.gatherings)
                                    }
                                }
                                    .tag(RootTab.messages)
                                    .tabItem { tabItemLabel(.messages) }
                                    .badge(environment.attentionItems.count)
                                authenticatedTab { ProfileView() }
                                    .tag(RootTab.profile)
                                    .tabItem { tabItemLabel(.profile) }
                            }
                            .tint(OMTheme.ColorToken.ink)
                            .toolbarBackground(OMTheme.ColorToken.card.opacity(0.92), for: .tabBar)
                            .toolbarBackground(.visible, for: .tabBar)
                            .task {
                                if environment.session.isAuthenticated {
                                    await environment.refreshAttention()
                                }
                            }
                            .onChange(of: router.selectedTab) { _, tab in
                                if tab == .messages, environment.session.isAuthenticated {
                                    Task { await environment.refreshAttention(force: true) }
                                }
                            }
                            .onChange(of: environment.session.isAuthenticated) { _, authenticated in
                                Task {
                                    if authenticated {
                                        await environment.refreshAttention(force: true)
                                    } else {
                                        await environment.refreshAttention()
                                    }
                                }
                            }
                        }
                    }
                    // Always register typed destinations *inside* the stack,
                    // including while first-use replaces the TabView root.
                    .navigationDestination(for: AppRoute.self) {
                        // 统一 inline 导航栏：避免 automatic 模式为空的大标题预留一段顶部空白。
                        destination($0).navigationBarTitleDisplayMode(.inline)
                    }
                }
                .tint(OMTheme.ColorToken.ink)
                .onReceive(NotificationCenter.default.publisher(for: .oneMoreSessionExpired)) { _ in
                    let tab = router.selectedTab
                    let intended = router.pendingAfterAuthentication ?? router.path.last
                    if let intended { router.pendingAfterAuthentication = intended }
                    Task {
                        let scope = await environment.auth.cacheScope()
                        environment.recovery.captureNavigation(scope: scope, tab: tab, route: intended)
                    }
                    environment.session.expire()
                }
                .onChange(of: environment.session.isAuthenticated) { _, authenticated in
                    guard authenticated else { return }
                    // Authentication can complete while G3 is the current
                    // destination.  First-use setup is the authenticated root,
                    // so clear only the visible auth route while preserving the
                    // pending external destination for A7 to resume.
                    if environment.session.needsOnboarding {
                        router.popToRoot()
                        return
                    }
                    Task {
                        let scope = await environment.auth.cacheScope()
                        router.resumePending()
                        environment.recovery.restoreNavigation(scope: scope, into: router)
                        await environment.refreshCalendarPreference()
                    }
                }
            }
        }
        // The public-share branch is a direct child rather than a
        // NavigationStack.  Keep its C4 identifier and controls exposed
        // instead of letting the app-root identifier replace that subtree.
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("app-root")
    }

    /// Tab 标签：定制位图（LuluGenerated/TabBar/tab-<name>-<active|inactive>.png）
    /// 缺失时回退 SF Symbol，素材可按张灰度替换。
    private func tabItemLabel(_ tab: RootTab) -> some View {
        Label {
            Text(tab.title)
        } icon: {
            OMTabIcon(tab: tab, selected: router.selectedTab == tab)
        }
    }

    @ViewBuilder private func destination(_ route: AppRoute) -> some View {
        switch route {
        case let .onboarding(id):
            if environment.session.isAuthenticated {
                OnboardingView(stateID: id)
            } else {
                AuthenticationFlowView()
            }
        case let .formal(node): StateDetailView(id: node.rawValue)
        case let .screen(id): StateDetailView(id: id)
        case .publicGatherings: authenticatedDestination(route) { socialGate { GatheringListView(mine: false, repository: environment.gatherings) } }
        case .myGatherings: authenticatedDestination(route) { socialGate { GatheringListView(mine: true, repository: environment.gatherings) } }
        case .relations: authenticatedDestination(route) { socialGate { RelationsView(repository: environment.social) } }
        case let .competition(id): authenticatedDestination(route) { CompetitionDetailView(id: id) }
        case let .competitionTable(id): authenticatedDestination(route) { CompetitionTeamBoardView(competitionID: id) }
        case let .competitionTeam(competitionID, teamID):
            authenticatedDestination(route) { CompetitionTeamDetailView(competitionID: competitionID, teamID: teamID) }
        case let .intent(id): authenticatedDestination(route) { socialGate { IntentComposerView(repository: environment.intents, competitionID: id) } }
        case let .intentPreset(preset): authenticatedDestination(route) { socialGate { IntentComposerView(repository: environment.intents, preset: preset) } }
        case let .gathering(id): authenticatedDestination(route) { GatheringDetailView(id: id) }
        case let .action(id): authenticatedDestination(route) { CampusActionDetailView(id: id, repository: environment.actions) }
        case let .share(token): SharedGapLandingView(token: token, repository: environment.gatherings)
        case let .channel(id): authenticatedDestination(route) { ChannelView(channelID: id, social: environment.social, socket: environment.webSocket) }
        case let .relation(id): authenticatedDestination(route) { RelationDetailView(relationID: id, repository: environment.social) }
        case .trust: authenticatedDestination(route) { TrustView() }
        case .organizer: authenticatedDestination(route) { OrganizerView(repository: environment.organizer) }
        case .tasteImport: authenticatedDestination(route) { TasteImportView(repository: environment.tasteImport) }
        case .accountData: authenticatedDestination(route) { AccountDataView(repository: environment.identity) }
        case .diagnostics: authenticatedDestination(route) { DiagnosticsView() }
        case .departedSafety: authenticatedDestination(route) { DepartedSafetyHistoryView(repository: environment.gatherings) }
        case .grants: authenticatedDestination(route) { GrantManagementView(repository: environment.identity) }
        case .matchingPreferences: authenticatedDestination(route) { MatchingPreferencesView(repository: environment.identity) }
        case .blocks: authenticatedDestination(route) { BlockListView(repository: environment.identity) }
        case .initiateGathering: authenticatedDestination(route) { InitiateGatheringView(repository: environment.gatherings) }
        case let .sharedGoals(relationID): authenticatedDestination(route) { SharedGoalsView(relationID: relationID, repository: environment.social) }
        case let .recurringGathering(gatheringID): authenticatedDestination(route) { RecurringGatheringView(gatheringID: gatheringID, repository: environment.gatherings) }
        case let .trustRequirement(context): authenticatedDestination(route) { TrustRequirementView(context: context) }
        #if DEBUG
        case .prototypeGallery: PrototypeHostView(initialID: nil)
        case let .prototypeScreen(id): PrototypeHostView(initialID: id)
        #endif
        }
    }

    @ViewBuilder private func authenticatedTab<Content: View>(
        @ViewBuilder content: () -> Content
    ) -> some View {
        if environment.session.isAuthenticated { content() }
        else { AuthenticationFlowView() }
    }

    @ViewBuilder private func authenticatedDestination<Content: View>(
        _ route: AppRoute,
        @ViewBuilder content: () -> Content
    ) -> some View {
        if environment.session.isAuthenticated {
            if environment.session.needsOnboarding {
                FirstUseSetupView(repository: environment.identity)
            } else {
                content()
            }
        } else {
            AuthenticationFlowView()
                .onAppear {
                    router.pendingAfterAuthentication = route
                    environment.recovery.saveExternalRoute(route)
                }
        }
    }

    private func socialGate<Content: View>(
        @ViewBuilder content: () -> Content
    ) -> some View {
        SocialAccessGate(repository: environment.identity, content: content)
    }
}

private struct SocialAccessGate<Content: View>: View {
    private enum Phase { case loading, enabled, disabled, failed(String) }
    let repository: IdentityRepository
    let content: Content
    @State private var phase: Phase = .loading
    @EnvironmentObject private var router: AppRouter

    init(
        repository: IdentityRepository,
        @ViewBuilder content: () -> Content
    ) {
        self.repository = repository
        self.content = content()
    }

    var body: some View {
        Group {
            switch phase {
            case .loading:
                OMG5StateView(state: .loading, message: AppBrand.loadingMessage)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(OMPageBackground())
            case .enabled:
                content
            case .disabled:
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        OMLargeTitle(title: "校园成局仍保持关闭", sub: "SOCIAL OFF")
                        OMCard {
                            OMTextRole.t3("认证不等于开启社交")
                            OMTextRole.foot("今天、比赛与个人设置仍可使用；发布意图、加入局和搭子关系需由你主动开启。")
                                .padding(.top, OMTheme.Spacing.s2)
                        }
                        OMButton("前往隐私与社交设置", icon: .shield) {
                            router.push(.formal(.m5))
                        }
                    }
                    .padding(.horizontal, OMTheme.Spacing.pageX)
                    .padding(.bottom, 44)
                }
                .background(OMPageBackground())
                .accessibilityIdentifier("social-feature-disabled")
            case let .failed(message):
                OMG5StateView(state: .networkError, message: message, actionTitle: "重试") { Task { await load() } }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(OMPageBackground())
            }
        }
        .task { await load() }
        .onAppear { Task { await load() } }
        .onReceive(NotificationCenter.default.publisher(for: .oneMoreSocialPreferencesDidChange)) { _ in
            Task { await load() }
        }
    }

    private func load() async {
        do {
            let value = try await repository.privacy()
            phase = value.socialEnabled ? .enabled : .disabled
        } catch {
            if error.isCancellation { return }
            if case .enabled = phase { return }
            phase = .failed(error.localizedDescription)
        }
    }
}

struct StateDetailView: View {
    let id: String
    @EnvironmentObject private var router: AppRouter
    var body: some View {
        Group {
            if id == "B2" { HermesAskView(repository: environment.today) }
            else if id == "B3" { TimetableView(repository: environment.today, gatherings: environment.gatherings) }
            else if id == "B4" { AssignmentsView(repository: environment.today) }
            else if id == "B5" || id == "B5.1" { VenueToolView(kind: .gym, repository: environment.today) }
            else if id == "B6" || id == "B6.1" { VenueToolView(kind: .room, repository: environment.today) }
            else if id == "B7" || id == "B7.1" { CampusEventsView(repository: environment.campusEvents) }
            else if id == "B8" { CampusPresetQueryView(screenID: "B8", title: "组会与课题", query: "今天有什么组会与课题活动？", repository: environment.today) }
            else if id == "B9" { CampusTransitReferenceView(repository: environment.today) }
            else if id == "B10" { SceneTriggerDetailView(repository: environment.today) }
            else if id == "B11" { ContextRequiredView(id: "B11", message: "个人写操作由 hermes 查询结果进入；参数必须先由服务端生成预览，再由本人核对授权。") }
            else if id == "M2" { ProfileEditorView(repository: environment.identity) }
            else if id == "M5" { PrivacySettingsView(repository: environment.identity) }
            else if id == "M4" { GrantManagementView(repository: environment.identity) }
            else if id == "M6" { MatchingPreferencesView(repository: environment.identity) }
            else if id == "M7" { NotificationPreferencesView(repository: environment.social) }
            else if id == "M8" { BlockListView(repository: environment.identity) }
            else if id == "M9" { TrustAppealsView(repository: environment.social) }
            else if id == "E8" { ContextRequiredView(id: "E8", message: "补位面板从发生缺口的局内进入，服务端会执行 T3 快速通道。") }
            else if id == "E11" { ContextRequiredView(id: "E11", message: "共同目标从一段已形成的搭子关系进入。") }
            else { generic }
        }
    }
    @EnvironmentObject private var environment: AppEnvironment
    private var generic: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMLargeTitle(title: ScreenCatalog.title(id), sub: "SCREEN \(id)")
                OMCard {
                    OMTextRole.t3(ScreenCatalog.description(id))
                    OMTextRole.foot("此状态由合法路由或服务端状态触发；客户端不推断匹配、空档或局状态。")
                        .padding(.top, OMTheme.Spacing.s2)
                }
                OMButton("返回相关主流程", icon: .back) { router.popToRoot() }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-\(id)")
    }
}

private struct ContextRequiredView: View {
    let id: String
    let message: String
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMLargeTitle(title: ScreenCatalog.title(id), sub: "SCREEN \(id)")
                OMCard {
                    HStack(spacing: 10) {
                        OMSticker("hourglass.png", size: .s44)
                        OMTextRole.t3("需要合法业务上下文")
                    }
                    OMTextRole.foot(message).padding(.top, OMTheme.Spacing.s2)
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-\(id)")
    }
}

enum ScreenCatalog {
    static let all = FormalNodeID.allCases.map(\.rawValue).sorted {
        $0.localizedStandardCompare($1) == .orderedAscending
    }
    static func title(_ id: String) -> String {
        let known = ["A1":"启动与价值主张", "A2":"认证说明", "A3":"扫码登录", "A4":"授权选择", "A5":"画像初始化", "A6":"画像确认", "A7":"准备完成", "A8":"授权恢复", "B1":"今天", "B12":"比赛雷达", "C1":"公开局", "D1":"自然语言意图", "D2":"澄清问题", "D3":"意图预览", "D4":"匿名池", "E1":"我的局", "E3":"待确认", "E5":"行动预览", "E6":"执行中", "E7":"局空间", "E12":"退出", "E13":"举报与拉黑", "E14":"局内消息", "E15":"搭子关系", "E16":"共同经历", "E17":"解除关系", "M1":"个人中心", "M3":"信任进度", "M7":"通知与日历", "M9":"申诉结果", "O1":"主理人控制台", "G2":"分享缺口卡", "G3":"认证恢复"]
        return known[id] ?? "\(AppBrand.displayName) · \(id)"
    }
    static func description(_ id: String) -> String { "\(title(id)) 的原生 SwiftUI 业务状态" }
}

#if DEBUG
struct FunctionalScreenIndexView: View {
    @EnvironmentObject private var router: AppRouter
    var body: some View {
        List {
            Section("74 正式节点") {
                ForEach(FormalNodeID.allCases, id: \.self) { node in
                    Button { router.push(.formal(node)) } label: {
                        HStack {
                            Text(node.rawValue)
                                .font(OMTheme.TypeToken.mono(.body, weight: .bold))
                                .foregroundStyle(OMTheme.ColorToken.ink)
                                .frame(width: 56, alignment: .leading)
                            Text(ScreenCatalog.title(node.rawValue))
                            Spacer()
                            Text("›").font(.system(size: 15, weight: .bold)).foregroundStyle(OMTheme.ColorToken.sage)
                        }
                    }
                    .accessibilityIdentifier("node-\(node.rawValue)")
                }
            }
            Section("额外组合态") {
                Button("B12.2 比赛到组队") { router.push(.screen("B12.2")) }
                Button("MSG 消息组合态") { router.push(.screen("MSG")) }
            }
        }
        .scrollContentBackground(.hidden)
        .background(OMPageBackground())
        .navigationTitle("画板与节点")
    }
}
#endif
