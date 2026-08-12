import Foundation
import Combine

/// 初始引导选校：中山大学 / 其他（iOS ↔ Web 同语义 sysu | other）。
enum SchoolAffiliation: String, CaseIterable, Identifiable, Sendable {
    case sysu
    case other

    var id: String { rawValue }

    var title: String {
        switch self {
        case .sysu: "中山大学"
        case .other: "其他"
        }
    }

    var subtitle: String {
        switch self {
        case .sysu: "我们为中大校园做了针对优化"
        case .other: "同样可以用，后续可补充校园认证"
        }
    }

    private static let schoolKey = "onemore.school.affiliation.v1"
    private static let campusGateKey = "onemore.school.campusGate.v1"

    static var current: SchoolAffiliation? {
        guard let raw = UserDefaults.standard.string(forKey: schoolKey) else { return nil }
        return SchoolAffiliation(rawValue: raw)
    }

    static func save(_ value: SchoolAffiliation) {
        UserDefaults.standard.set(value.rawValue, forKey: schoolKey)
    }

    static func clear() {
        UserDefaults.standard.removeObject(forKey: schoolKey)
        UserDefaults.standard.removeObject(forKey: campusGateKey)
    }

    /// 中大扫码闸门是否已通过（本机）。
    static var campusGatePassed: Bool {
        get { UserDefaults.standard.bool(forKey: campusGateKey) }
        set { UserDefaults.standard.set(newValue, forKey: campusGateKey) }
    }
}

@MainActor
final class AppSessionController: ObservableObject {
    @Published private(set) var isAuthenticated: Bool
    @Published private(set) var needsOnboarding: Bool
    private let auth: AuthManager
    private let resetSessionData: () async -> Void
    private let deactivateNotificationsBeforeSignOut: () async throws -> Void
    private let deactivateNotificationsAfterExpiry: () async -> Void
    private let resumeNotificationsAfterAuthentication: () async -> Void
    private var expiryCleanup: Task<Void, Never>?
    init(
        auth: AuthManager,
        resetSessionData: @escaping () async -> Void = {},
        deactivateNotificationsBeforeSignOut: @escaping () async throws -> Void = {},
        deactivateNotificationsAfterExpiry: @escaping () async -> Void = {},
        resumeNotificationsAfterAuthentication: @escaping () async -> Void = {}
    ) {
        self.auth = auth
        self.resetSessionData = resetSessionData
        self.deactivateNotificationsBeforeSignOut = deactivateNotificationsBeforeSignOut
        self.deactivateNotificationsAfterExpiry = deactivateNotificationsAfterExpiry
        self.resumeNotificationsAfterAuthentication = resumeNotificationsAfterAuthentication
        #if DEV_AUTH
        let forceSignedOut = Self.argumentValue("-ForceSignedOut")?.uppercased() == "YES"
        isAuthenticated = !forceSignedOut
        needsOnboarding = !forceSignedOut && Self.argumentValue("-ForceFirstUse")?.uppercased() == "YES"
        Task {
            if await auth.state != .authenticated {
                isAuthenticated = false
                needsOnboarding = false
            }
        }
        #else
        isAuthenticated = false
        needsOnboarding = false
        Task {
            isAuthenticated = await auth.state == .authenticated
            if isAuthenticated {
                let scope = await auth.cacheScope()
                needsOnboarding = !UserDefaults.standard.bool(forKey: "onboarding.completed.\(scope)")
            }
        }
        #endif
    }
    func install(token: String, needsOnboarding requested: Bool? = nil) async {
        await expiryCleanup?.value
        expiryCleanup = nil
        await auth.install(token: token)
        await resetSessionData()
        let scope = await auth.cacheScope()
        let completed = UserDefaults.standard.bool(forKey: "onboarding.completed.\(scope)")
        // The UI-test switch exercises the real A2→A7 chain even when a prior
        // simulator run has already persisted the account-scoped completion bit.
        // It is compiled only into DEV_AUTH builds and never changes Release
        // onboarding semantics.
        #if DEV_AUTH
        let forcedFirstUse = Self.argumentValue("-ForceFirstUse")?.uppercased() == "YES"
        needsOnboarding = requested ?? (forcedFirstUse || !completed)
        #else
        needsOnboarding = requested ?? !completed
        #endif
        isAuthenticated = true
        await resumeNotificationsAfterAuthentication()
    }
    func completeOnboarding() async {
        let scope = await auth.cacheScope()
        UserDefaults.standard.set(true, forKey: "onboarding.completed.\(scope)")
        needsOnboarding = false
    }
    /// 设置页「重新查看新手引导」：清除完成标记与选校，回到 A1 → 选校 → 登录链路。
    func resetOnboarding() async {
        let scope = await auth.cacheScope()
        UserDefaults.standard.set(false, forKey: "onboarding.completed.\(scope)")
        SchoolAffiliation.clear()
        needsOnboarding = true
    }
    func expire() {
        isAuthenticated = false
        needsOnboarding = false
        let cleanup = Task {
            await deactivateNotificationsAfterExpiry()
            await resetSessionData()
        }
        expiryCleanup = cleanup
    }
    func signOut() async throws {
        await expiryCleanup?.value
        expiryCleanup = nil
        try await deactivateNotificationsBeforeSignOut()
        await auth.clear()
        await resetSessionData()
        isAuthenticated = false
        needsOnboarding = false
    }
    private static func argumentValue(_ key: String) -> String? {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of: key), arguments.indices.contains(index + 1) else { return nil }
        return arguments[index + 1]
    }
}
