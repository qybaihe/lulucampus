import Foundation

actor TodayRepository {
    private let api: APIClient
    private var cached: (String, Date, TodaySummary)?
    init(api: APIClient) { self.api = api }
    func summary(force: Bool = false) async throws -> TodaySummary {
        let scope = await api.authScope()
        if !force, let cached, cached.0 == scope, Date().timeIntervalSince(cached.1) < 60 { return cached.2 }
        let value: TodaySummary = try await api.get("/today/summary")
        cached = (scope, .now, value); return value
    }
    func invalidate() { cached = nil }
    func askHermes(_ text: String, context: [String: JSONValue] = [:]) async throws -> HermesAskResult {
        struct Body: Encodable, Sendable { let text: String; let context: [String: JSONValue] }
        return try await api.send("/hermes/ask", method: .post, body: Body(text: text, context: context))
    }
    func startHermesPeerChat(peerUserID: String, reason: String, overlap: String) async throws -> HermesPeerChatResult {
        struct Body: Encodable, Sendable {
            let peerUserId: String
            let reason: String
            let overlap: String
        }
        return try await api.send(
            "/hermes/peers/start",
            method: .post,
            body: Body(peerUserId: peerUserID, reason: reason, overlap: overlap),
            idempotencyKey: "hermes-peer-\(peerUserID)"
        )
    }
    func timetable(week: Int) async throws -> Timetable {
        try await api.get(
            "/schedule/timetable",
            query: [URLQueryItem(name: "week", value: String(min(30, max(1, week))))]
        )
    }
    func refreshTimetable() async throws -> [String: JSONValue] {
        try await api.send(
            "/schedule/refresh", method: .post, body: EmptyRequest(),
            idempotencyKey: "schedule-refresh"
        )
    }
    func course(_ id: String) async throws -> CampusCourseDetail {
        try await api.get("/schedule/courses/\(id)")
    }
    func assignments() async throws -> [CampusAssignment] {
        try await api.get(
            "/assignments", query: [URLQueryItem(name: "status", value: "unfinished")]
        )
    }
    func assignment(_ id: String) async throws -> CampusAssignmentDetail {
        try await api.get("/assignments/\(id)")
    }
    func roomAvailability(kind: String, date: Date, lab: String? = nil) async throws -> JSONValue {
        var query = [
            URLQueryItem(name: "kind", value: kind),
            URLQueryItem(name: "date", value: CampusDayCodec.string(from: date)),
        ]
        if let lab, !lab.isEmpty { query.append(URLQueryItem(name: "lab", value: lab)) }
        return try await api.get("/venues/room/available", query: query)
    }
    func gymAvailability(venueType: String, date: Date, venue: String? = nil) async throws -> JSONValue {
        var query = [
            URLQueryItem(name: "venue_type", value: venueType),
            URLQueryItem(name: "date", value: CampusDayCodec.string(from: date)),
            URLQueryItem(name: "days", value: "1"),
        ]
        if let venue, !venue.isEmpty { query.append(URLQueryItem(name: "venue", value: venue)) }
        return try await api.get("/venues/gym/available", query: query)
    }
    func ignoreSceneTrigger(_ sceneKey: String) async throws -> [String: JSONValue] {
        struct Body: Encodable, Sendable { let ignored = true }
        return try await api.send(
            "/today/triggers/\(sceneKey)/ignore", method: .post, body: Body(),
            idempotencyKey: "scene-ignore-\(sceneKey)"
        )
    }

}

struct CampusEventDraft: Encodable, Sendable {
    let title: String
    let type: String
    let startsAt: Date?
    let endsAt: Date?
    let location: String?
    let description: String?
    let officialUrl: String?
}

actor CampusEventRepository {
    private let api: APIClient
    private var cache: (Date, [CampusEvent])?
    init(api: APIClient) { self.api = api }
    func list(force: Bool = false) async throws -> [CampusEvent] {
        if !force, let cache, Date().timeIntervalSince(cache.0) < 300 { return cache.1 }
        let value: [CampusEvent] = try await api.get("/events")
        cache = (.now, value)
        return value
    }
    func detail(_ id: String) async throws -> CampusEvent {
        try await api.get("/events/\(id)")
    }
    /// 用户发布校园活动（服务端 T4 门槛）；成功后失效列表缓存。
    @discardableResult
    func publish(_ draft: CampusEventDraft) async throws -> CampusEvent {
        let event: CampusEvent = try await api.send("/events", method: .post, body: draft, idempotencyKey: "event-\(UUID().uuidString)")
        cache = nil
        return event
    }
    func invalidate() { cache = nil }
}

actor CompetitionRepository {
    private let api: APIClient
    private var cache: [Competition]?
    init(api: APIClient) { self.api = api }
    func list(force: Bool = false, tier: String? = nil) async throws -> [Competition] {
        if !force, tier == nil, let cache, !cache.isEmpty { return cache }
        let query = tier.map { [URLQueryItem(name: "recommendation_tier", value: $0)] } ?? []
        let value: [Competition] = try await api.get("/competitions", query: query)
        if tier == nil { cache = value.isEmpty ? nil : value }
        return value
    }
    /// 推荐档筛选目录；失败时返回 nil，由 UI 用稳定码兜底渲染。
    func tiers() async -> [RecommendationTierMeta]? {
        try? await api.get("/competitions/recommendation-tiers")
    }
    /// 招募中的赛事队伍；失败时返回 nil，UI 隐藏该区块。
    func teams(competitionID: String) async -> [CompetitionTeam]? {
        try? await api.get("/competitions/\(competitionID)/teams")
    }
    func team(competitionID: String, teamID: String) async throws -> CompetitionTeam {
        try await api.get("/competitions/\(competitionID)/teams/\(teamID)")
    }
    func invalidate() { cache = nil }
}

actor IntentRepository {
    private let api: APIClient
    init(api: APIClient) { self.api = api }
    func compile(text: String, moodNote: String? = nil, competitionID: String?, clarificationRound: Int = 0, answers: [String: String] = [:]) async throws -> IntentCompileResult {
        try await api.send(
            "/intent/compile",
            method: .post,
            body: IntentCompileRequest(text: text, moodNote: moodNote, competitionId: competitionID, clarificationRound: clarificationRound, answers: answers),
            idempotencyKey: "intent-compile-\(UUID().uuidString)"
        )
    }
    func publish(cardID: String, idempotencyKey: String = "ios-publish-\(UUID().uuidString)") async throws -> IntentPublishResult {
        try await api.send("/intent/publish", method: .post, body: IntentPublishRequest(cardId: cardID), idempotencyKey: idempotencyKey)
    }
    func card(_ id: String) async throws -> IntentCard { try await api.get("/intent/\(id)") }
    func publication(_ id: String) async throws -> IntentPublishResult { try await api.get("/intent/\(id)/publication") }
    func update(_ id: String, patch: IntentCardPatch) async throws -> IntentCard {
        try await api.send("/intent/\(id)", method: .patch, body: patch, idempotencyKey: "intent-edit-\(id)-\(UUID().uuidString)")
    }
    func withdraw(_ id: String) async throws -> [String: JSONValue] {
        try await api.send("/intent/\(id)", method: .delete, body: EmptyRequest(), idempotencyKey: "intent-withdraw-\(UUID().uuidString)")
    }
}

actor IdentityRepository {
    private let api: APIClient
    init(api: APIClient) { self.api = api }
    func registerPhone(phone: String, password: String, displayName: String?) async throws -> PhoneAuthResult {
        try await api.send(
            "/auth/register",
            method: .post,
            body: PhoneRegisterBody(phone: phone, password: password, displayName: displayName),
            idempotencyKey: "phone-register-\(phone)"
        )
    }
    func loginPhone(phone: String, password: String) async throws -> PhoneAuthResult {
        try await api.send(
            "/auth/login",
            method: .post,
            body: PhoneLoginBody(phone: phone, password: password),
            idempotencyKey: "phone-login-\(phone)-\(UUID().uuidString)"
        )
    }
    func facts() async throws -> IdentityFacts { try await api.get("/auth/me") }
    func updateDisplayName(_ displayName: String) async throws -> IdentityFacts {
        struct Body: Encodable, Sendable { let displayName: String }
        return try await api.send(
            "/me/display-name",
            method: .patch,
            body: Body(displayName: displayName),
            idempotencyKey: "display-name-\(UUID().uuidString)"
        )
    }
    func profile() async throws -> UserProfilePayload { try await api.get("/profile/me") }
    func updateProfileTags(
        selfReported: [String], hiddenVerified: [String]
    ) async throws -> UserProfilePayload {
        struct Body: Encodable, Sendable {
            let tags: [String]
            let hiddenVerifiedTags: [String]
        }
        return try await api.send(
            "/profile/tags", method: .patch,
            body: Body(tags: selfReported, hiddenVerifiedTags: hiddenVerified),
            idempotencyKey: "profile-tags-full-state"
        )
    }
    func setGrant(scope: String, granted: Bool) async throws -> AuthorizationGrantView {
        struct Body: Encodable, Sendable { let scope: String; let granted: Bool }
        return try await api.send("/auth/grants", method: .post, body: Body(scope: scope, granted: granted), idempotencyKey: "grant-\(scope)-\(UUID().uuidString)")
    }
    func setSocialEnabled(_ enabled: Bool) async throws -> SocialPreferences {
        struct Body: Encodable, Sendable {
            let socialEnabled: Bool
            let courseMatchingEnabled: Bool
            let identityDisclosure = "after_confirmed"
        }
        return try await api.send(
            "/me/privacy",
            method: .patch,
            body: Body(
                socialEnabled: enabled,
                courseMatchingEnabled: enabled
            ),
            idempotencyKey: "first-use-social-\(enabled ? "on" : "off")-\(UUID().uuidString)"
        )
    }
    func enableSocial() async throws -> SocialPreferences { try await setSocialEnabled(true) }
    func privacy() async throws -> SocialPreferences { try await api.get("/me/privacy") }
    func updatePrivacy(_ value: SocialPreferences) async throws -> SocialPreferences {
        struct Body: Encodable, Sendable {
            let socialEnabled: Bool
            let courseMatchingEnabled: Bool
            let identityDisclosure: String
            let sameGenderOnly: Bool
            let minimumGroupSize: Int
        }
        return try await api.send(
            "/me/privacy",
            method: .patch,
            body: Body(
                socialEnabled: value.socialEnabled,
                courseMatchingEnabled: value.courseMatchingEnabled,
                identityDisclosure: value.identityDisclosure,
                sameGenderOnly: value.sameGenderOnly,
                minimumGroupSize: value.minimumGroupSize
            ),
            idempotencyKey: "privacy-\(UUID().uuidString)"
        )
    }
    func matchingPreferences() async throws -> MatchingPreferences {
        try await api.get("/me/matching-preferences")
    }
    func updateMatchingPreferences(_ value: MatchingPreferences) async throws -> MatchingPreferences {
        try await api.send(
            "/me/matching-preferences",
            method: .patch,
            body: value,
            idempotencyKey: "matching-preferences-\(UUID().uuidString)"
        )
    }
    func blocks() async throws -> [BlockedUser] { try await api.get("/me/blocks") }
    func unblock(_ userID: String) async throws {
        let _: [String: JSONValue] = try await api.send(
            "/me/blocks/\(userID)", method: .delete, body: EmptyRequest(),
            idempotencyKey: "unblock-\(userID)"
        )
    }
    func exportData() async throws -> [String: JSONValue] { try await api.get("/me/data-export") }
    func deleteAccount() async throws -> [String: JSONValue] {
        struct Body: Encodable, Sendable { let confirmation = "DELETE" }
        return try await api.send("/me/account", method: .delete, body: Body(), idempotencyKey: "account-delete")
    }
}

actor SocialRepository {
    private let api: APIClient
    init(api: APIClient) { self.api = api }
    func relations() async throws -> [RelationSummary] { try await api.get("/relations") }
    func relation(_ id: String) async throws -> RelationSummary { try await api.get("/relations/\(id)") }
    func messages(channelID: String) async throws -> [MessagePayload] { try await api.get("/channels/\(channelID)/messages") }
    func channelHeader(channelID: String) async throws -> ChannelHeader {
        try await api.get("/channels/\(channelID)")
    }
    func channelScenePolicy(channelID: String) async throws -> ChannelScenePolicy {
        try await api.get("/channels/\(channelID)/scene-policy")
    }
    func sendText(channelID: String, text: String) async throws -> MessagePayload { try await api.send("/channels/\(channelID)/messages", method: .post, body: TextMessageCreate(content: text), idempotencyKey: "text-message-\(UUID().uuidString)") }
    func mentionAzou(channelID: String, text: String) async throws -> MentionAzouResult {
        struct Body: Encodable, Sendable { let text: String }
        return try await api.send("/channels/\(channelID)/mention-azou", method: .post, body: Body(text: text), idempotencyKey: "mention-\(channelID)-\(UUID().uuidString)")
    }
    func uploadAndSendImage(channelID: String, data: Data, width: Int?, height: Int?, caption: String? = nil) async throws -> MessagePayload {
        let asset = try await api.uploadImage(data, filename: "ios-photo.jpg", width: width, height: height)
        return try await api.send("/channels/\(channelID)/messages", method: .post, body: ImageMessageCreate(image: .init(mediaId: asset.mediaId, caption: caption)), idempotencyKey: "image-message-\(UUID().uuidString)")
    }
    func sendLocation(channelID: String, latitude: Double, longitude: Double, label: String, address: String? = nil) async throws -> MessagePayload {
        try await api.send("/channels/\(channelID)/messages", method: .post, body: LocationMessageCreate(location: .init(latitude: latitude, longitude: longitude, label: label, address: address)), idempotencyKey: "location-\(UUID().uuidString)")
    }
    func trust() async throws -> TrustProgress { try await api.get("/trust/me") }
    func appeals() async throws -> [TrustAppeal] { try await api.get("/trust/appeals") }
    func appeal(id: String) async throws -> TrustAppeal { try await api.get("/trust/appeals/\(id)") }
    func submitAppeal(reason: String) async throws -> TrustAppeal {
        struct Body: Encodable, Sendable { let reason: String }
        return try await api.send("/trust/appeal", method: .post, body: Body(reason: reason), idempotencyKey: "appeal-\(UUID().uuidString)")
    }
    func notificationPreferences() async throws -> NotificationPreferences { try await api.get("/me/notification-preferences") }
    func notifications() async throws -> [InboxNotification] {
        try await api.get("/notifications", query: [URLQueryItem(name: "limit", value: "50")])
    }
    func updatePreferences(_ value: NotificationPreferences) async throws -> NotificationPreferences {
        struct Body: Encodable, Sendable { let overallEnabled: Bool; let calendarSyncEnabled: Bool; let categories: NotificationPreferences.Categories }
        return try await api.send("/me/notification-preferences", method: .patch, body: Body(overallEnabled: value.overallEnabled, calendarSyncEnabled: value.calendarSyncEnabled, categories: value.categories), idempotencyKey: "notification-preferences-\(UUID().uuidString)")
    }
    func goals(relationID: String) async throws -> [SharedGoal] {
        try await api.get("/relations/\(relationID)/goals")
    }
    func createGoal(
        relationID: String, definition: String, periodStart: String,
        periodEnd: String, targetValue: Double, unit: String
    ) async throws -> SharedGoal {
        struct Body: Encodable, Sendable {
            let definition: String
            let periodStart: String
            let periodEnd: String
            let targetValue: Double
            let unit: String
        }
        return try await api.send(
            "/relations/\(relationID)/goals", method: .post,
            body: Body(
                definition: definition, periodStart: periodStart,
                periodEnd: periodEnd, targetValue: targetValue, unit: unit
            ),
            idempotencyKey: "shared-goal-\(relationID)-\(UUID().uuidString)"
        )
    }
    func updateGoal(_ id: String, nextAction: String) async throws -> SharedGoal {
        struct Body: Encodable, Sendable { let nextAction: String }
        return try await api.send(
            "/goals/\(id)", method: .patch, body: Body(nextAction: nextAction),
            idempotencyKey: "shared-goal-next-action-\(id)-\(nextAction.hashValue)"
        )
    }
    func recur(relationID: String) async throws -> String {
        struct Result: Decodable, Sendable { let gatheringId: String }
        let value: Result = try await api.send(
            "/relations/\(relationID)/recur", method: .post, body: EmptyRequest(),
            idempotencyKey: "relation-recur-\(relationID)-\(UUID().uuidString)"
        )
        return value.gatheringId
    }
    func dissolve(relationID: String) async throws {
        let _: [String: JSONValue] = try await api.send("/relations/\(relationID)", method: .delete, body: EmptyRequest(), idempotencyKey: "dissolve-\(relationID)")
    }
}

actor GatheringRepository {
    private let api: APIClient
    init(api: APIClient) { self.api = api }
    func open() async throws -> [GatheringSummary] { try await api.get("/gatherings/open") }
    func mine() async throws -> [GatheringSummary] { try await api.get("/gatherings/mine") }
    func departedSafetyHistory() async throws -> [DepartedSafetyContext] {
        try await api.get("/gatherings/history/safety")
    }
    func detail(_ id: String) async throws -> GatheringSummary { try await api.get("/gatherings/\(id)") }
    func join(_ id: String, role: String? = nil) async throws -> GatheringSummary {
        struct Body: Encodable, Sendable { let role: String? }
        return try await api.send(
            "/gatherings/\(id)/join",
            method: .post,
            body: Body(role: role),
            idempotencyKey: "join-\(UUID().uuidString)"
        )
    }
    func leave(_ id: String) async throws -> GatheringLeaveResult { try await api.send("/gatherings/\(id)/leave", method: .post, body: EmptyRequest(), idempotencyKey: "leave-\(UUID().uuidString)") }
    func confirm(_ id: String, confirmed: Bool) async throws -> GatheringSummary {
        struct Body: Encodable, Sendable { let confirmed: Bool }
        return try await api.send("/gatherings/\(id)/confirm", method: .post, body: Body(confirmed: confirmed), idempotencyKey: "confirm-\(UUID().uuidString)")
    }
    func timeOptions(_ id: String) async throws -> [GatheringTimeOption] { try await api.get("/gatherings/\(id)/time-options") }
    func currentReschedule(_ id: String) async throws -> RescheduleProposal? {
        try await api.get("/gatherings/\(id)/reschedule")
    }
    func reschedule(_ id: String, startAt: Date, endAt: Date) async throws -> RescheduleProposal {
        struct Body: Encodable, Sendable { let startAt: Date; let endAt: Date }
        return try await api.send("/gatherings/\(id)/reschedule", method: .post, body: Body(startAt: startAt, endAt: endAt), idempotencyKey: "reschedule-\(UUID().uuidString)")
    }
    func voteReschedule(_ id: String, proposalID: String, accepted: Bool) async throws -> RescheduleProposal {
        struct Body: Encodable, Sendable { let accepted: Bool }
        return try await api.send(
            "/gatherings/\(id)/reschedule/\(proposalID)/vote", method: .post,
            body: Body(accepted: accepted),
            idempotencyKey: "reschedule-vote-\(proposalID)-\(accepted)"
        )
    }
    func complete(_ id: String, completed: Bool) async throws -> GatheringSummary {
        struct Body: Encodable, Sendable { let completed: Bool }
        return try await api.send("/gatherings/\(id)/complete", method: .post, body: Body(completed: completed), idempotencyKey: "complete-\(UUID().uuidString)")
    }
    func recur(_ id: String, keepUserIDs: [String]? = nil) async throws -> GatheringSummary {
        struct Body: Encodable, Sendable { let keepUserIds: [String]? }
        return try await api.send("/gatherings/\(id)/recur", method: .post, body: Body(keepUserIds: keepUserIDs), idempotencyKey: "recur-\(id)-\(UUID().uuidString)")
    }
    func finishRecurrenceChoice(_ id: String) async throws {
        let _: [String: JSONValue] = try await api.send(
            "/gatherings/\(id)/recur/finish", method: .post,
            body: EmptyRequest(), idempotencyKey: "recur-finish-\(id)"
        )
    }
    func report(_ id: String, userID: String?, reason: String, block: Bool) async throws -> [String: JSONValue] {
        struct Body: Encodable, Sendable { let reportedUserId: String?; let reason: String; let block: Bool }
        return try await api.send("/gatherings/\(id)/report", method: .post, body: Body(reportedUserId: userID, reason: reason, block: block), idempotencyKey: "report-\(id)-\(userID ?? "gathering")-\(UUID().uuidString)")
    }
    func createShare(_ id: String) async throws -> GapShare {
        try await api.send("/gatherings/\(id)/share", method: .post, body: EmptyRequest(), idempotencyKey: "share-\(id)")
    }
    /// 成局后 30 秒破冰包（身份披露后可见）。
    func icebreaker(_ id: String) async throws -> IcebreakerPack {
        try await api.get("/gatherings/\(id)/icebreaker")
    }
    /// 学期成局回忆录。
    func semesterRecap() async throws -> SemesterRecap {
        try await api.get("/me/recap")
    }
    func resolveShare(_ token: String) async throws -> GapShare { try await api.get("/shares/g/\(token)") }
    func joinShare(_ token: String) async throws -> GatheringSummary {
        try await api.send("/shares/g/\(token)/join", method: .post, body: EmptyRequest(), idempotencyKey: "share-join-\(UUID().uuidString)")
    }
    func actionCapability(_ id: String) async throws -> GatheringActionCapability {
        try await api.get("/gatherings/\(id)/action-capability")
    }
    func bookingOptions(_ id: String) async throws -> [GatheringBookingOption] {
        try await api.get("/gatherings/\(id)/booking-options")
    }
    func selectBookingPlan(_ id: String, optionToken: String) async throws -> GatheringSummary {
        struct Body: Encodable, Sendable { let optionToken: String }
        return try await api.send(
            "/gatherings/\(id)/booking-plan", method: .post,
            body: Body(optionToken: optionToken),
            idempotencyKey: "booking-plan-\(id)-\(optionToken.hashValue)"
        )
    }
    func initiate(_ draft: InitiateGatheringDraft) async throws -> GatheringSummary {
        try await api.send(
            "/gatherings/initiate", method: .post, body: draft,
            idempotencyKey: "initiate-gathering-\(UUID().uuidString)"
        )
    }
    func createRecurring(
        _ id: String, firstStartAt: Date, occurrences: Int,
        intervalWeeks: Int, durationMinutes: Int
    ) async throws -> [GatheringSummary] {
        struct Body: Encodable, Sendable {
            let firstStartAt: Date
            let occurrences: Int
            let intervalWeeks: Int
            let durationMinutes: Int
        }
        return try await api.send(
            "/gatherings/\(id)/recurring", method: .post,
            body: Body(
                firstStartAt: firstStartAt, occurrences: occurrences,
                intervalWeeks: intervalWeeks, durationMinutes: durationMinutes
            ),
            idempotencyKey: "recurring-\(id)-\(Int(firstStartAt.timeIntervalSince1970))"
        )
    }
    func backfill(_ id: String) async throws -> BackfillOpportunity {
        try await api.get("/gatherings/\(id)/backfill")
    }
    func claimBackfill(_ id: String) async throws -> GatheringSummary {
        try await api.send(
            "/gatherings/\(id)/backfill/claim", method: .post, body: EmptyRequest(),
            idempotencyKey: "backfill-claim-\(id)"
        )
    }
    func applyBackfillFallback(_ id: String, optionKey: String) async throws -> GatheringSummary {
        struct Body: Encodable, Sendable { let optionKey: String }
        return try await api.send(
            "/gatherings/\(id)/backfill/fallback", method: .post,
            body: Body(optionKey: optionKey),
            idempotencyKey: "backfill-fallback-\(id)-\(optionKey)"
        )
    }
}

actor ActionRepository {
    private let api: APIClient
    init(api: APIClient) { self.api = api }
    func preview(action: String, params: [String: JSONValue], gatheringID: String?) async throws -> CampusAction {
        struct Body: Encodable, Sendable {
            let action: String
            let params: [String: JSONValue]
            let gatheringId: String?
            let idempotencyKey: String
            let confirm = false
        }
        let key = "ios-preview-\(UUID().uuidString)"
        return try await api.send("/actions/preview", method: .post, body: Body(action: action, params: params, gatheringId: gatheringID, idempotencyKey: key), idempotencyKey: key)
    }
    func execute(_ action: CampusAction) async throws -> CampusAction {
        struct Body: Encodable, Sendable { let actionId: String; let confirm: Bool; let params: [String: JSONValue] }
        return try await api.send("/actions/execute", method: .post, body: Body(actionId: action.id, confirm: true, params: action.params), idempotencyKey: "ios-execute-\(action.id)")
    }
    func authorize(_ action: CampusAction, authorized: Bool) async throws -> CampusAction {
        struct Body: Encodable, Sendable {
            let authorized: Bool
            let snapshotHash: String
        }
        return try await api.send(
            "/actions/\(action.id)/authorization",
            method: .post,
            body: Body(authorized: authorized, snapshotHash: action.snapshotHash),
            idempotencyKey: "action-authorization-\(action.id)-\(authorized)"
        )
    }
    func proposeModification(
        _ action: CampusAction, reason: String,
        proposedParams: [String: JSONValue]
    ) async throws -> CampusAction {
        struct Body: Encodable, Sendable {
            let snapshotHash: String
            let reason: String
            let proposedParams: [String: JSONValue]
        }
        return try await api.send(
            "/actions/\(action.id)/propose-modification", method: .post,
            body: Body(
                snapshotHash: action.snapshotHash,
                reason: reason,
                proposedParams: proposedParams
            ),
            idempotencyKey: "action-modification-\(action.id)-\(reason.hashValue)"
        )
    }
    func detail(_ id: String) async throws -> CampusAction { try await api.get("/actions/\(id)") }
}

actor TasteImportRepository {
    private let api: APIClient
    init(api: APIClient) { self.api = api }

    /// Recommended entry: create import and wait up to `waitSeconds` for a QR payload.
    func fromLink(_ shareUrl: String, force: Bool = true) async throws -> TasteImportStatus {
        try await api.send(
            "/profile/taste/from-link",
            method: .post,
            body: TasteFromLinkRequest(shareUrl: shareUrl, force: force)
        )
    }

    func createWithQR(force: Bool = false, waitSeconds: Int = 10) async throws -> TasteImportStatus {
        let qr: TasteQRLoginView = try await api.send(
            "/profile/imports/douyin/qr",
            method: .post,
            body: TasteImportCreate(force: force),
            query: [URLQueryItem(name: "wait_seconds", value: String(waitSeconds))]
        )
        // Prefer full session view so progress/collection/result stay available.
        if let session = try? await status(qr.importId) { return session }
        return TasteImportStatus(
            id: qr.importId,
            source: "douyin",
            status: qr.status,
            expiresAt: qr.qrExpiresAt ?? .now.addingTimeInterval(180),
            qrExpiresAt: qr.qrExpiresAt,
            qrImageDataUrl: qr.qrImageDataUrl,
            qrVersion: qr.qrVersion,
            progress: TasteProgressPayload(
                phase: "qr", current: 0, total: nil, percent: nil,
                message: "等待扫码", qrScanned: nil, phoneMasked: nil, codeSent: nil
            ),
            collection: nil,
            sourceProfile: nil,
            candidateTags: [],
            questionCount: 0,
            questions: nil,
            result: nil,
            error: qr.error
        )
    }

    func create(force: Bool = false) async throws -> TasteImportStatus {
        try await api.send("/profile/imports/douyin", method: .post, body: TasteImportCreate(force: force))
    }

    func status(_ id: String) async throws -> TasteImportStatus {
        try await api.get("/profile/imports/\(id)")
    }

    func cancel(_ id: String) async throws -> TasteImportStatus {
        try await api.send(
            "/profile/imports/\(id)/cancel", method: .post, body: EmptyRequest(),
            idempotencyKey: "taste-cancel-\(id)"
        )
    }

    func refreshQR(_ id: String) async throws -> TasteImportStatus {
        try await api.send(
            "/profile/imports/\(id)/qr/refresh", method: .post, body: EmptyRequest(),
            idempotencyKey: "taste-qr-\(id)-\(UUID().uuidString)"
        )
    }

    func requestPhoneCode(_ id: String, phone: String, countryCode: String) async throws -> TastePhoneLoginStatus {
        struct Body: Encodable, Sendable { let phone: String; let countryCode: String }
        return try await api.send(
            "/profile/imports/\(id)/phone/code", method: .post,
            body: Body(phone: phone, countryCode: countryCode)
        )
    }

    func phoneStatus(_ id: String) async throws -> TastePhoneLoginStatus {
        try await api.get("/profile/imports/\(id)/phone")
    }

    func submitPhoneCode(_ id: String, code: String) async throws -> TastePhoneLoginStatus {
        struct Body: Encodable, Sendable { let code: String }
        return try await api.send(
            "/profile/imports/\(id)/phone/verify", method: .post,
            body: Body(code: code)
        )
    }

    func verifyLogin(_ id: String, waitSeconds: Int = 2) async throws -> TasteLoginVerification {
        try await api.send(
            "/profile/imports/\(id)/verify",
            method: .post,
            body: EmptyRequest(),
            query: [URLQueryItem(name: "wait_seconds", value: String(waitSeconds))]
        )
    }

    func questions(_ id: String) async throws -> TasteQuestionSet {
        try await api.get("/profile/imports/\(id)/questions")
    }

    func submitAnswers(_ id: String, answers: [TasteQuizAnswer]) async throws -> TasteProfileResult {
        struct Body: Encodable, Sendable { let answers: [TasteQuizAnswer] }
        return try await api.send(
            "/profile/imports/\(id)/answers", method: .post,
            body: Body(answers: answers),
            idempotencyKey: "taste-answers-\(id)"
        )
    }

    func currentProfile() async throws -> TasteProfileResult? {
        try await api.get("/profile/taste/me")
    }

    func refreshAINarrative() async throws -> TasteProfileResult {
        try await api.send(
            "/profile/taste/me/ai-refresh", method: .post, body: EmptyRequest(),
            idempotencyKey: "taste-ai-refresh-\(UUID().uuidString)"
        )
    }

    func deleteProfile() async throws -> [String: JSONValue] {
        try await api.send(
            "/profile/taste/me/douyin", method: .delete, body: EmptyRequest(),
            idempotencyKey: "taste-delete-douyin"
        )
    }
}

actor OrganizerRepository {
    private let api: APIClient
    init(api: APIClient) { self.api = api }
    func gatherings() async throws -> [OfficialGatheringSummary] {
        try await api.get("/organizer/gatherings")
    }
    func createGathering(_ draft: OfficialGatheringDraft) async throws -> OfficialGatheringCreateResult {
        try await api.send(
            "/organizer/gatherings", method: .post, body: draft,
            idempotencyKey: "official-create-\(UUID().uuidString)"
        )
    }
    func dashboard(_ gatheringID: String) async throws -> OrganizerDashboard {
        try await api.get("/organizer/gatherings/\(gatheringID)/dashboard")
    }
    func closeRegistration(_ gatheringID: String) async throws -> OrganizerGatheringStatus {
        try await api.send(
            "/organizer/gatherings/\(gatheringID)/close-registration",
            method: .post, body: EmptyRequest(),
            idempotencyKey: "official-close-\(gatheringID)"
        )
    }
    func finalize(_ gatheringID: String) async throws -> OrganizerGatheringStatus {
        try await api.send(
            "/organizer/gatherings/\(gatheringID)/finalize",
            method: .post, body: EmptyRequest(),
            idempotencyKey: "official-finalize-\(gatheringID)"
        )
    }
    func checkIn(_ participantID: String, gatheringID: String) async throws -> OrganizerAttendanceResult {
        try await api.send(
            "/organizer/gatherings/\(gatheringID)/attendance/\(participantID)",
            method: .post, body: EmptyRequest(),
            idempotencyKey: "official-attendance-\(gatheringID)-\(participantID)"
        )
    }
    func templates() async throws -> [OfficialTemplate] { try await api.get("/organizer/templates") }
    func create(_ draft: OfficialTemplateDraft) async throws -> OfficialTemplate { try await api.send("/organizer/templates", method: .post, body: draft, idempotencyKey: "template-create-\(UUID().uuidString)") }
    func update(id: String, draft: OfficialTemplateDraft) async throws -> OfficialTemplate { try await api.send("/organizer/templates/\(id)", method: .patch, body: draft, idempotencyKey: "template-update-\(id)-\(UUID().uuidString)") }
    func copy(id: String, title: String?) async throws -> OfficialTemplate {
        struct Body: Encodable, Sendable { let title: String? }
        return try await api.send("/organizer/templates/\(id)/copy", method: .post, body: Body(title: title), idempotencyKey: "template-copy-\(id)-\(UUID().uuidString)")
    }
    func deactivate(id: String) async throws -> OfficialTemplate { try await api.send("/organizer/templates/\(id)", method: .delete, body: EmptyRequest(), idempotencyKey: "template-deactivate-\(id)") }
    func instantiate(id: String, startAt: Date) async throws -> [String: JSONValue] {
        struct Body: Encodable, Sendable { let startAt: Date; let quotaBatches: [String] = [] }
        return try await api.send("/organizer/templates/\(id)/instantiate", method: .post, body: Body(startAt: startAt), idempotencyKey: "template-instantiate-\(id)-\(Int(startAt.timeIntervalSince1970))")
    }
}
