import SwiftUI
import UIKit
import UserNotifications

enum NotificationDeepLinkParser {
    static func url(from userInfo: [AnyHashable: Any]) -> URL? {
        var values = userInfo
        if let payload = userInfo["payload"] as? [String: Any] {
            for (key, value) in payload { values[key] = value }
        }
        // Reauthorization notifications carry a generic auth deep link plus
        // the exact action/gathering to resume. Preserve the business target.
        if let action = values["action_id"] as? String {
            return URL(string: "onemore://action/\(action)")
        }
        if let gathering = values["gathering_id"] as? String,
           (values["deep_link"] as? String) == "onemore://auth/reauthorize" {
            return URL(string: "onemore://gathering/\(gathering)")
        }
        for key in ["deep_link", "url"] {
            if let raw = values[key] as? String, let url = URL(string: raw) { return url }
        }
        if let relation = values["relation_id"] as? String {
            return URL(string: "onemore://relation/\(relation)")
        }
        if let gathering = values["gathering_id"] as? String {
            return URL(string: "onemore://gathering/\(gathering)")
        }
        if let channel = values["channel_id"] as? String {
            return URL(string: "onemore://channel/\(channel)")
        }
        if let screen = values["screen_id"] as? String {
            return URL(string: "onemore://screen/\(screen)")
        }
        if let route = values["route"] as? String {
            return URL(string: route.contains("://") ? route : "onemore://screen/\(route)")
        }
        return nil
    }
}

enum CalendarPushEvent: Equatable {
    case remove(gatheringID: String)
    case sync(gatheringID: String)
    case refresh(gatheringID: String)
}

enum CalendarPushEventParser {
    static func event(from userInfo: [AnyHashable: Any]) -> CalendarPushEvent? {
        var values = userInfo
        if let payload = userInfo["payload"] as? [String: Any] {
            for (key, value) in payload { values[key] = value }
        }
        guard let gatheringID = values["gathering_id"] as? String else { return nil }
        let type = (values["type"] as? String) ?? (values["notification_type"] as? String)
        if values["remove_event"] as? Bool == true || type == "calendar_revoked" {
            return .remove(gatheringID: gatheringID)
        }
        if type == "execution_succeeded", values["calendar_event"] != nil {
            return .sync(gatheringID: gatheringID)
        }
        if ["gathering_rescheduled", "calendar_updated"].contains(type) {
            return .refresh(gatheringID: gatheringID)
        }
        return nil
    }
}

final class OneMoreAppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    static var tokenHandler: ((Data) -> Void)?
    static var notificationURLHandler: ((URL) -> Void)?
    static var calendarHandler: ((CalendarPushEvent) -> Void)?
    private static var pendingTokens: [Data] = []
    private static var pendingNotificationURLs: [URL] = []
    private static var pendingCalendarEvents: [CalendarPushEvent] = []

    @MainActor
    static func installDeliveryHandlers(
        token: @escaping (Data) -> Void,
        notificationURL: @escaping (URL) -> Void,
        calendar: @escaping (CalendarPushEvent) -> Void
    ) {
        tokenHandler = token
        notificationURLHandler = notificationURL
        calendarHandler = calendar
        let tokens = pendingTokens
        let urls = pendingNotificationURLs
        let events = pendingCalendarEvents
        pendingTokens.removeAll()
        pendingNotificationURLs.removeAll()
        pendingCalendarEvents.removeAll()
        tokens.forEach(token)
        urls.forEach(notificationURL)
        events.forEach(calendar)
    }

    @MainActor static func receiveToken(_ value: Data) {
        if let tokenHandler { tokenHandler(value) } else { pendingTokens.append(value) }
    }

    @MainActor static func receiveNotificationURL(_ value: URL) {
        if let notificationURLHandler { notificationURLHandler(value) }
        else { pendingNotificationURLs.append(value) }
    }

    @MainActor static func receiveCalendarEvent(_ value: CalendarPushEvent) {
        if let calendarHandler { calendarHandler(value) }
        else { pendingCalendarEvents.append(value) }
    }

    @MainActor static func resetDeliveryStateForTests() {
        tokenHandler = nil
        notificationURLHandler = nil
        calendarHandler = nil
        pendingTokens.removeAll()
        pendingNotificationURLs.removeAll()
        pendingCalendarEvents.removeAll()
    }

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        return true
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        Task { @MainActor in Self.receiveToken(deviceToken) }
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        if let event = CalendarPushEventParser.event(from: notification.request.content.userInfo) {
            DispatchQueue.main.async { Self.receiveCalendarEvent(event) }
        }
        completionHandler([.banner, .badge, .sound])
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        if let event = CalendarPushEventParser.event(from: response.notification.request.content.userInfo) {
            DispatchQueue.main.async { Self.receiveCalendarEvent(event) }
        }
        if let url = NotificationDeepLinkParser.url(from: response.notification.request.content.userInfo) {
            DispatchQueue.main.async { Self.receiveNotificationURL(url) }
        }
        completionHandler()
    }
}

@main
struct OneMoreApp: App {
    @UIApplicationDelegateAdaptor(OneMoreAppDelegate.self) private var appDelegate
    @StateObject private var router = AppRouter()
    @StateObject private var environment = AppEnvironment()
    @Environment(\.scenePhase) private var scenePhase
    #if DEBUG
    private let prototypeLaunchID: String? = {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of: "-PrototypeScreenID"),
              arguments.indices.contains(index + 1) else { return nil }
        return arguments[index + 1].uppercased()
    }()
    private let luluEvidenceClip: LuluClip? = {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of: "-LuluClip"),
              arguments.indices.contains(index + 1) else { return nil }
        return LuluClip(rawValue: arguments[index + 1])
    }()
    private let stateEvidence: RuntimeStateEvidence? = {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of: "-StateEvidence"),
              arguments.indices.contains(index + 1) else { return nil }
        return RuntimeStateEvidence(rawValue: arguments[index + 1])
    }()
    private let productionLaunchID: String? = {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of: "-ProductionScreenID"),
              arguments.indices.contains(index + 1) else { return nil }
        return arguments[index + 1].uppercased()
    }()
    private let productionDeepLink: URL? = {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of: "-ProductionDeepLink"),
              arguments.indices.contains(index + 1) else { return nil }
        return URL(string: arguments[index + 1])
    }()
    #endif

    var body: some Scene {
        WindowGroup {
            Group {
                #if DEBUG
                if let luluEvidenceClip {
                    LuluClipEvidenceView(clip: luluEvidenceClip)
                } else if let stateEvidence {
                    RuntimeStateEvidenceView(state: stateEvidence)
                } else if let prototypeLaunchID {
                    PrototypeLaunchRoot(initialID: prototypeLaunchID)
                } else if productionLaunchID != nil || productionDeepLink != nil {
                    ProductionLaunchRoot(screenID: productionLaunchID, deepLink: productionDeepLink)
                } else {
                    RootView()
                }
                #else
                RootView()
                #endif
            }
                .environmentObject(router)
                .environmentObject(environment)
                .preferredColorScheme(.light)
                .onOpenURL {
                    if !environment.session.isAuthenticated, let route = AppRoute.parse($0) {
                        environment.recovery.saveExternalRoute(route)
                    }
                    router.handle(url: $0, isAuthenticated: environment.session.isAuthenticated)
                }
                .onAppear {
                    OneMoreAppDelegate.installDeliveryHandlers(
                        token: { data in environment.pushTokens.receive(deviceToken: data) },
                        notificationURL: { url in
                            if !environment.session.isAuthenticated, let route = AppRoute.parse(url) {
                                environment.recovery.saveExternalRoute(route)
                            }
                            router.handle(url: url, isAuthenticated: environment.session.isAuthenticated)
                        },
                        calendar: { event in
                            Task { await environment.reconcileCalendarPush(event) }
                        }
                    )
                }
        }.onChange(of: scenePhase) { _, phase in
            let foreground = phase == .active
            Task {
                await environment.webSocket.setForeground(foreground)
                if foreground {
                    await environment.permissions.refreshDeniedPermissions()
                    await environment.api.resumePendingMutations()
                    await environment.pushTokens.flush()
                    await environment.retryPendingCalendarPush()
                    await environment.refreshCalendarPreference()
                }
            }
        }
    }
}

#if DEBUG
/// UI-test bootstrap that still renders `RootView`, typed `AppRoute`s,
/// repositories and the live FastAPI client. It is deliberately separate
/// from the visual prototype harness.
private struct ProductionLaunchRoot: View {
    let screenID: String?
    let deepLink: URL?
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var environment: AppEnvironment
    @State private var didApply = false

    var body: some View {
        RootView()
            .task {
                guard !didApply else { return }
                didApply = true
                if let deepLink {
                    if !environment.session.isAuthenticated, let route = AppRoute.parse(deepLink) {
                        environment.recovery.saveExternalRoute(route)
                    }
                    router.handle(
                        url: deepLink,
                        isAuthenticated: environment.session.isAuthenticated
                    )
                } else if let screenID {
                    if let node = FormalNodeID(rawValue: screenID) {
                        router.path = [.formal(node)]
                    } else {
                        router.path = [.screen(screenID)]
                    }
                }
            }
    }
}

/// Deterministic native screen harness used by UI tests and fidelity capture.
/// It keeps the same injected actions as production while making a requested
/// design state the navigation root instead of pushing it during launch.
private struct PrototypeLaunchRoot: View {
    let initialID: String
    @EnvironmentObject private var router: AppRouter

    var body: some View {
        NavigationStack(path: $router.path) {
            PrototypeHostView(initialID: initialID)
                .navigationDestination(for: AppRoute.self) { route in
                    if case let .prototypeScreen(id) = route {
                        PrototypeHostView(initialID: id)
                    } else {
                        EmptyView()
                    }
                }
        }
    }
}
#endif
