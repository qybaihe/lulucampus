import Foundation
import SwiftUI

enum RootTab: String, CaseIterable, Hashable, Identifiable {
    case today, competitions, create, messages, profile
    var id: String { rawValue }
    var title: String {
        switch self { case .today: "今天"; case .competitions: "活动"; case .create: "差一个"; case .messages: "消息"; case .profile: "我" }
    }
    var symbol: String {
        switch self { case .today: "sparkles"; case .competitions: "figure.2"; case .create: "plus"; case .messages: "message"; case .profile: "person" }
    }
}

enum IntentPreset: String, Hashable, CaseIterable, Sendable {
    case sport, courseDDL, event
    var title: String {
        switch self { case .sport: "运动搭子"; case .courseDDL: "同课 DDL"; case .event: "活动同行" }
    }
    var text: String {
        switch self {
        case .sport: "周六晚上珠海校区一起打羽毛球，4人"
        case .courseDDL: "今晚一起完成软件工程迭代作业，3人"
        case .event: "周五一起去听可信 AI 公开课，3人"
        }
    }
}

enum TrustRecoveryTarget: Hashable, Codable, Sendable {
    case gathering(String)
    case share(String)

    var route: AppRoute {
        switch self {
        case let .gathering(id): .gathering(id)
        case let .share(token): .share(token)
        }
    }

    var title: String {
        switch self {
        case .gathering: "继续加入原来的局"
        case .share: "继续响应原缺口卡"
        }
    }
}

struct TrustRequirementContext: Hashable, Codable, Sendable {
    let requiredLevel: String
    let capability: String?
    let serverMessage: String
    let recoveryTarget: TrustRecoveryTarget

    init?(
        error: Error,
        recoveryTarget: TrustRecoveryTarget
    ) {
        guard case let APIClientError.server(_, body) = error,
              body.code == "TRUST_LEVEL_REQUIRED" else { return nil }
        guard case let .string(requiredLevel)? = body.details["required_level"] else {
            return nil
        }
        let capability: String?
        if case let .string(value)? = body.details["capability"] {
            capability = value
        } else {
            capability = nil
        }
        self.requiredLevel = requiredLevel
        self.capability = capability
        serverMessage = body.message
        self.recoveryTarget = recoveryTarget
    }

    var capabilityTitle: String {
        switch capability {
        case "competition_pool": "比赛组队"
        case "duo_gathering": "双人高承诺局"
        case "cross_college_matching": "跨院系匹配"
        case "large_group": "大型多人局"
        case "backfill_fast_lane": "补位快速通道"
        case "initiate_gathering": "直接发起"
        case "recurring_gathering": "固定周期局"
        case let value?: value
        case nil: "当前局准入"
        }
    }
}

enum AppRoute: Hashable {
    case onboarding(String), formal(FormalNodeID), screen(String), publicGatherings, myGatherings, relations
    case competition(String), competitionTable(String), competitionTeam(competitionID: String, teamID: String)
    case intent(competitionID: String?), intentPreset(IntentPreset)
    case gathering(String), action(String), channel(String), relation(String), share(String)
    case trust, organizer, tasteImport, accountData, diagnostics, departedSafety
    case grants, matchingPreferences, blocks, initiateGathering
    case sharedGoals(String), recurringGathering(String)
    case trustRequirement(TrustRequirementContext)
    #if DEBUG
    case prototypeGallery
    case prototypeScreen(String)
    #endif

    static func formalOrScreen(_ rawValue: String) -> AppRoute {
        FormalNodeID(rawValue: rawValue).map(AppRoute.formal) ?? .screen(rawValue)
    }

    static func parse(_ url: URL) -> AppRoute? {
        let path = url.pathComponents.filter { $0 != "/" }
        let parts: [String]
        if url.scheme?.lowercased() == "onemore" { parts = [url.host].compactMap { $0 } + path }
        else if ["http", "https"].contains(url.scheme?.lowercased() ?? "") { parts = path }
        else { return nil }
        guard let head = parts.first else { return nil }
        switch head {
        case "g" where parts.count > 1: return .share(parts[1])
        case "gathering" where parts.count > 1: return .gathering(parts[1])
        case "action" where parts.count > 1: return .action(parts[1])
        case "channel" where parts.count > 1: return .channel(parts[1])
        case "relation" where parts.count > 1: return .relation(parts[1])
        case "goal" where parts.count > 1: return .sharedGoals(parts[1])
        case "competition" where parts.count > 1:
            if parts.count >= 3, parts[2] == "table" { return .competitionTable(parts[1]) }
            if parts.count >= 4, parts[2] == "team" {
                return .competitionTeam(competitionID: parts[1], teamID: parts[3])
            }
            return .competition(parts[1])
        case "intent": return .intent(competitionID: parts.dropFirst().first)
        case "relations": return .relations
        case "trust": return .trust
        case "auth": return .onboarding("G3")
        case "organizer": return .organizer
        case "taste-import": return .tasteImport
        case "account-data": return .accountData
        case "safety-history": return .departedSafety
        case "grants": return .grants
        case "matching-preferences": return .matchingPreferences
        case "blocks": return .blocks
        case "initiate": return .initiateGathering
        case "public-gatherings": return .publicGatherings
        case "my-gatherings": return .myGatherings
        case "screen" where parts.count > 1:
            let id = parts[1].uppercased()
            return FormalNodeID(rawValue: id).map(AppRoute.formal) ?? .screen(id)
        default: return nil
        }
    }
}

@MainActor
final class AppRouter: ObservableObject {
    @Published var selectedTab: RootTab = {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of: "-InitialTab"), args.indices.contains(i + 1),
           let tab = RootTab(rawValue: args[i + 1]) { return tab }
        #endif
        return .today
    }()
    @Published var path: [AppRoute] = []
    @Published var pendingAfterAuthentication: AppRoute?
    @Published var publicShareToken: String?
    /// 首屏 Hermes 输入框 → B2 的一次性问题草稿
    @Published var hermesDraft: String?

    func push(_ route: AppRoute) { path.append(route) }
    func popToRoot() { path.removeAll() }
    func handle(url: URL, isAuthenticated: Bool) {
        guard let route = AppRoute.parse(url) else { return }
        if case let .share(token) = route, !isAuthenticated {
            publicShareToken = token
        }
        else if isAuthenticated { push(route) }
        else { pendingAfterAuthentication = route; path = [.onboarding("G3")] }
    }
    func authenticateForShare(_ token: String) {
        publicShareToken = nil
        pendingAfterAuthentication = .share(token)
        path = [.onboarding("G3")]
    }
    func dismissPublicShare() { publicShareToken = nil }
    func resumePending() {
        if let pendingAfterAuthentication { self.pendingAfterAuthentication = nil; path = [pendingAfterAuthentication] }
    }
    func recoverAfterSessionExpired(_ intended: AppRoute) {
        pendingAfterAuthentication = intended; path = [.onboarding("G3")]
    }
}
