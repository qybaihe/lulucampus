import Foundation

struct IntentRecoveryDraft: Codable, Equatable, Sendable {
    var text: String
    var goal: String
    var capabilitiesText: String
    var rolesText: String
    var campus: String
    var intensity: String
    var socialMode: String
    var sameGenderOnly: Bool? = nil
    var minimumSize: Int
    var targetSize: Int
    var startAt: Date
    var endAt: Date
    var cardID: String?
    var competitionID: String?
    var pendingAction: String?
    var idempotencyKey: String?
}

private struct RecoveryRoute: Codable, Equatable, Sendable {
    let kind: String
    let value: String?

    init?(_ route: AppRoute?) {
        guard let route else { return nil }
        switch route {
        case let .onboarding(value): kind = "onboarding"; self.value = value
        case let .formal(node): kind = "formal"; value = node.rawValue
        case let .screen(value): kind = "screen"; self.value = value
        case .publicGatherings: kind = "public"; value = nil
        case .myGatherings: kind = "mine"; value = nil
        case .relations: kind = "relations"; value = nil
        case let .competition(value): kind = "competition"; self.value = value
        case let .competitionTable(value): kind = "competition-table"; self.value = value
        case let .competitionTeam(competitionID, teamID):
            kind = "competition-team"; self.value = "\(competitionID)/\(teamID)"
        case let .intent(value): kind = "intent"; self.value = value
        case let .intentPreset(value): kind = "intent-preset"; self.value = value.rawValue
        case let .gathering(value): kind = "gathering"; self.value = value
        case let .action(value): kind = "action"; self.value = value
        case let .channel(value): kind = "channel"; self.value = value
        case let .relation(value): kind = "relation"; self.value = value
        case let .share(value): kind = "share"; self.value = value
        case .trust: kind = "trust"; value = nil
        case .organizer: kind = "organizer"; value = nil
        case .tasteImport: kind = "taste"; value = nil
        case .accountData: kind = "account"; value = nil
        case .diagnostics: kind = "diagnostics"; value = nil
        case .departedSafety: kind = "departed-safety"; value = nil
        case .grants: kind = "grants"; value = nil
        case .matchingPreferences: kind = "matching-preferences"; value = nil
        case .blocks: kind = "blocks"; value = nil
        case .initiateGathering: kind = "initiate"; value = nil
        case let .sharedGoals(value): kind = "shared-goals"; self.value = value
        case let .recurringGathering(value): kind = "recurring"; self.value = value
        case let .trustRequirement(context):
            kind = "trust-requirement"
            value = (try? JSONEncoder.oneMore.encode(context)).map { String(decoding: $0, as: UTF8.self) }
        #if DEBUG
        case .prototypeGallery, .prototypeScreen(_): return nil
        #endif
        }
    }

    var route: AppRoute? {
        switch kind {
        case "onboarding": value.map(AppRoute.onboarding)
        case "formal": value.flatMap(FormalNodeID.init(rawValue:)).map(AppRoute.formal)
        case "screen": value.map(AppRoute.screen)
        case "public": .publicGatherings
        case "mine": .myGatherings
        case "relations": .relations
        case "competition": value.map(AppRoute.competition)
        case "competition-table": value.map(AppRoute.competitionTable)
        case "competition-team":
            value.flatMap { raw -> AppRoute? in
                guard let slash = raw.firstIndex(of: "/") else { return nil }
                let competitionID = String(raw[..<slash])
                let teamID = String(raw[raw.index(after: slash)...])
                guard !competitionID.isEmpty, !teamID.isEmpty else { return nil }
                return .competitionTeam(competitionID: competitionID, teamID: teamID)
            }
        case "intent": .intent(competitionID: value)
        case "intent-preset": value.flatMap(IntentPreset.init(rawValue:)).map(AppRoute.intentPreset)
        case "gathering": value.map(AppRoute.gathering)
        case "action": value.map(AppRoute.action)
        case "channel": value.map(AppRoute.channel)
        case "relation": value.map(AppRoute.relation)
        case "share": value.map(AppRoute.share)
        case "trust": .trust
        case "organizer": .organizer
        case "taste": .tasteImport
        case "account": .accountData
        case "diagnostics": .diagnostics
        case "departed-safety": .departedSafety
        case "grants": .grants
        case "matching-preferences": .matchingPreferences
        case "blocks": .blocks
        case "initiate": .initiateGathering
        case "shared-goals": value.map(AppRoute.sharedGoals)
        case "recurring": value.map(AppRoute.recurringGathering)
        case "trust-requirement": value
            .flatMap { $0.data(using: .utf8) }
            .flatMap { try? JSONDecoder.oneMore.decode(TrustRequirementContext.self, from: $0) }
            .map(AppRoute.trustRequirement)
        default: nil
        }
    }
}

private struct SessionRecoverySnapshot: Codable, Equatable, Sendable {
    var scope: String
    var rootTab: String
    var route: RecoveryRoute?
    var intentDraft: IntentRecoveryDraft?
}

/// A Keychain-backed recovery journal. It records intent content and the
/// idempotency key before a write begins, then restores only for the same
/// authenticated account after a 401/relaunch.
@MainActor
final class SessionRecoveryStore: ObservableObject {
    @Published private(set) var intentDraft: IntentRecoveryDraft?
    private let keychain: KeychainStore
    private let account = "session-recovery-v1"
    private let externalAccount = "pending-external-route-v1"
    private var snapshot: SessionRecoverySnapshot?

    init(keychain: KeychainStore = .init(service: "com.onemore.campus.recovery")) {
        self.keychain = keychain
        if let raw = keychain.read(account: account),
           let data = raw.data(using: .utf8),
           let decoded = try? JSONDecoder.oneMore.decode(SessionRecoverySnapshot.self, from: data) {
            snapshot = decoded
            intentDraft = decoded.intentDraft
        }
    }

    func updateIntentDraft(_ draft: IntentRecoveryDraft, scope: String) {
        var value = snapshotForScope(scope)
        value.intentDraft = draft
        snapshot = value
        intentDraft = draft
        persist()
    }

    func captureNavigation(scope: String, tab: RootTab, route: AppRoute?) {
        guard !Self.isUITesting else { return }
        var value = snapshotForScope(scope)
        value.rootTab = tab.rawValue
        value.route = RecoveryRoute(route)
        snapshot = value
        persist()
    }

    func draft(for scope: String) -> IntentRecoveryDraft? {
        guard snapshot?.scope == scope else { return nil }
        return snapshot?.intentDraft
    }

    func saveExternalRoute(_ route: AppRoute) {
        guard let record = RecoveryRoute(route),
              let data = try? JSONEncoder().encode(record) else { return }
        keychain.write(String(decoding: data, as: UTF8.self), account: externalAccount)
    }

    func clearExternalRoute() {
        keychain.delete(account: externalAccount)
    }

    /// UI 测试要求确定性导航：手动会话遗留的导航快照不得覆盖深链，
    /// 但外部深链路由（externalAccount）仍需正常恢复。
    private static let isUITesting = ProcessInfo.processInfo.arguments.contains("-UI_TESTING")

    @discardableResult
    func restoreNavigation(scope: String, into router: AppRouter) -> Bool {
        if let raw = keychain.read(account: externalAccount),
           let data = raw.data(using: .utf8),
           let route = try? JSONDecoder().decode(RecoveryRoute.self, from: data).route {
            keychain.delete(account: externalAccount)
            router.publicShareToken = nil
            router.path = [route]
            return true
        }
        guard !Self.isUITesting else { return false }
        guard let value = snapshot, value.scope == scope else { return false }
        if let tab = RootTab(rawValue: value.rootTab) { router.selectedTab = tab }
        if let route = value.route?.route { router.path = [route] }
        return true
    }

    func clearIntentDraft(scope: String) {
        guard snapshot?.scope == scope else { return }
        snapshot?.intentDraft = nil
        intentDraft = nil
        persist()
    }

    private func snapshotForScope(_ scope: String) -> SessionRecoverySnapshot {
        if let snapshot, snapshot.scope == scope { return snapshot }
        return SessionRecoverySnapshot(scope: scope, rootTab: RootTab.today.rawValue, route: nil, intentDraft: nil)
    }

    private func persist() {
        guard let snapshot,
              let data = try? JSONEncoder.oneMore.encode(snapshot) else {
            keychain.delete(account: account)
            return
        }
        keychain.write(String(decoding: data, as: UTF8.self), account: account)
    }
}
