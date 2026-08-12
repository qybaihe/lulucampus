import Foundation

enum FormalNodeID: String, CaseIterable, Codable, Hashable, Sendable {
    case a1 = "A1", a2 = "A2", a3 = "A3", a4 = "A4", a5 = "A5", a6 = "A6", a7 = "A7", a8 = "A8"
    case b1 = "B1", b2 = "B2", b3 = "B3", b31 = "B3.1", b4 = "B4", b41 = "B4.1"
    case b5 = "B5", b51 = "B5.1", b6 = "B6", b61 = "B6.1", b7 = "B7", b71 = "B7.1"
    case b8 = "B8", b9 = "B9", b10 = "B10", b11 = "B11", b12 = "B12", b121 = "B12.1"
    case c1 = "C1", c2 = "C2", c3 = "C3", c4 = "C4"
    case d1 = "D1", d2 = "D2", d3 = "D3", d31 = "D3.1", d32 = "D3.2", d33 = "D3.3", d34 = "D3.4", d4 = "D4"
    case e1 = "E1", e2 = "E2", e3 = "E3", e4 = "E4", e5 = "E5", e6 = "E6", e7 = "E7", e8 = "E8", e9 = "E9", e10 = "E10", e11 = "E11", e12 = "E12", e13 = "E13", e14 = "E14", e15 = "E15", e16 = "E16", e17 = "E17"
    case m1 = "M1", m2 = "M2", m3 = "M3", m4 = "M4", m5 = "M5", m6 = "M6", m7 = "M7", m8 = "M8", m9 = "M9", m10 = "M10"
    case o1 = "O1", o2 = "O2", o3 = "O3", o4 = "O4"
    case g1 = "G1", g2 = "G2", g3 = "G3", g4 = "G4", g5 = "G5"
}

enum FormalNodeTrigger: Equatable, Sendable {
    case app(component: String)
    case route(path: String, component: String)
    case serverState(endpoint: String, predicate: String, component: String)
    case systemEvent(event: String, component: String)

    var component: String {
        switch self {
        case let .app(component), let .route(_, component), let .serverState(_, _, component), let .systemEvent(_, component): component
        }
    }
}

struct FormalNodeDefinition: Equatable, Sendable {
    let id: FormalNodeID
    let title: String
    let trigger: FormalNodeTrigger
    let accessibilityIdentifier: String
}

enum FormalNodeRegistry {
    static let all: [FormalNodeDefinition] = [
        d(.a1, "启动路由", .app(component: "RootView + AppSessionController"), "app-root"),
        d(.a2, "认证说明", .route(path: "/auth", component: "AuthenticationFlowView.intro"), "screen-A2-auth-intro"),
        d(.a3, "扫码认证", .route(path: "/auth/scan", component: "RealLoginView"), "screen-A3-real-login"),
        d(.a4, "授权范围", .serverState(endpoint: "/auth/grants", predicate: "first-use route saves each selected grant, then refreshes /auth/me", component: "FirstUseSetupView.grants"), "screen-A4-grants"),
        d(.a5, "画像初始化", .serverState(endpoint: "/auth/me", predicate: "identity facts loading after authentication", component: "FirstUseSetupView.facts"), "screen-A5-A6-facts"),
        d(.a6, "画像确认", .serverState(endpoint: "/auth/me", predicate: "verified identity facts loaded", component: "FirstUseSetupView.facts"), "screen-A5-A6-facts"),
        d(.a7, "社交开关", .serverState(endpoint: "/me/privacy", predicate: "first-use social opt-in", component: "FirstUseSetupView.social"), "screen-A7-social"),
        d(.a8, "系统权限", .systemEvent(event: "permission denied/recheck", component: "OMPermissionRecoveryNotice + PermissionCoordinator"), "permission-recovery-notice"),
        d(.b1, "今天", .route(path: "/today", component: "TodayView"), "screen-B1-today"),
        d(.b2, "Hermes 问答", .route(path: "/today/ask", component: "HermesAskView"), "screen-B2-hermes"),
        d(.b3, "我的课表", .route(path: "/today/timetable", component: "TimetableView"), "screen-B3-timetable"),
        d(.b31, "课程详情", .serverState(endpoint: "/schedule/courses/{course_id}", predicate: "selected course", component: "CourseDetailView"), "screen-B3.1-course-detail"),
        d(.b4, "作业与 DDL", .route(path: "/today/assignments", component: "AssignmentsView"), "screen-B4-assignments"),
        d(.b41, "作业详情", .serverState(endpoint: "/assignments/{assignment_id}", predicate: "selected assignment", component: "AssignmentDetailView"), "screen-B4.1-assignment-detail"),
        d(.b5, "体育场馆", .route(path: "/today/gym", component: "VenueToolView.gym"), "screen-B5-gym"),
        d(.b51, "体育时段", .serverState(endpoint: "/venues/gym/available", predicate: "availability loaded", component: "VenueToolView.gym slots"), "screen-B5-gym"),
        d(.b6, "研讨室", .route(path: "/today/room", component: "VenueToolView.room"), "screen-B6-room"),
        d(.b61, "研讨室时段", .serverState(endpoint: "/venues/room/available", predicate: "availability loaded", component: "VenueToolView.room slots"), "screen-B6-room"),
        d(.b7, "校园活动", .route(path: "/today/events", component: "CampusEventsView"), "screen-B7-events"),
        d(.b71, "活动详情", .serverState(endpoint: "/events/{event_id}", predicate: "selected event", component: "CampusEventsView.detail"), "screen-B7.1-event-detail"),
        d(.b8, "组会与课题", .route(path: "/today/research", component: "CampusPresetQueryView"), "screen-B8-campus-query"),
        d(.b9, "班车与节次", .route(path: "/today/transit", component: "CampusTransitReferenceView"), "screen-B9-transit-reference"),
        d(.b10, "场景触发", .serverState(endpoint: "/today/summary", predicate: "scene_trigger != null", component: "SceneTriggerDetailView"), "screen-B10-scene-trigger"),
        d(.b11, "个人行动预览", .serverState(endpoint: "/actions/preview", predicate: "personal action previewed", component: "PersonalActionPreviewView"), "screen-B11-personal-action-preview"),
        d(.b12, "比赛雷达", .route(path: "/competitions", component: "CompetitionsView"), "screen-B12-competitions"),
        d(.b121, "赛事详情", .route(path: "/competition/{competition_id}", component: "CompetitionDetailView"), "screen-B12.1-competition-detail"),
        d(.c1, "公开局", .route(path: "/gatherings/open", component: "GatheringListView.open"), "screen-C1-public-gatherings"),
        d(.c2, "公开局详情", .route(path: "/gathering/{gathering_id}", component: "GatheringDetailView"), "screen-E3-gathering-detail"),
        d(.c3, "准入门槛", .serverState(endpoint: "/gatherings/{gathering_id}/join", predicate: "TRUST_LEVEL_REQUIRED", component: "TrustRequirementView + typed recovery target"), "screen-C3-trust-requirement"),
        d(.c4, "缺口卡落地", .route(path: "/g/{share_token}", component: "SharedGapLandingView"), "screen-C4-share-landing"),
        d(.d1, "意图输入", .route(path: "/intent", component: "IntentComposerView.editing"), "screen-D1-intent"),
        d(.d2, "澄清追问", .serverState(endpoint: "/intent/compile", predicate: "needs_clarification", component: "IntentComposerView.clarification"), "screen-D2-clarification"),
        d(.d3, "意图卡确认", .serverState(endpoint: "/intent/compile", predicate: "card Draft", component: "IntentComposerView.editor"), "screen-D3-intent-editor"),
        d(.d31, "能力编辑", .serverState(endpoint: "/intent/{card_id}", predicate: "Draft capabilities", component: "IntentComposerView.editor capabilities"), "intent-capabilities-editor"),
        d(.d32, "空档选择", .serverState(endpoint: "/intent/{card_id}", predicate: "Draft available_windows", component: "IntentComposerView.editor availability"), "intent-availability-editor"),
        d(.d33, "角色编辑", .serverState(endpoint: "/intent/{card_id}", predicate: "Draft required_roles", component: "IntentComposerView.editor roles"), "intent-roles-editor"),
        d(.d34, "安全偏好", .serverState(endpoint: "/intent/{card_id}", predicate: "Draft social/safety", component: "IntentComposerView.editor safety"), "intent-safety-editor"),
        d(.d4, "匿名池", .serverState(endpoint: "/intent/publish", predicate: "Pooling", component: "IntentComposerView.published"), "intent-view-gathering"),
        d(.e1, "我的局", .route(path: "/gatherings/mine", component: "GatheringListView.mine"), "screen-E1-my-gatherings"),
        d(.e2, "局详情", .route(path: "/gathering/{gathering_id}", component: "GatheringDetailView"), "screen-E3-gathering-detail"),
        d(.e3, "多人确认", .serverState(endpoint: "/gatherings/{gathering_id}", predicate: "Tentative", component: "GatheringDetailView.confirmationActions"), "gathering-confirmation-actions"),
        d(.e4, "改约协商", .serverState(endpoint: "/gatherings/{gathering_id}/reschedule", predicate: "proposal open", component: "GatheringDetailView.rescheduleActions"), "gathering-reschedule-actions"),
        d(.e5, "行动预览", .serverState(endpoint: "/actions/preview", predicate: "previewed", component: "GatheringDetailView.actionActions"), "gathering-action-preview"),
        d(.e6, "执行结果", .serverState(endpoint: "/actions/{action_id}", predicate: "succeeded/failed", component: "GatheringDetailView.action result"), "gathering-action-result"),
        d(.e7, "协作空间", .serverState(endpoint: "/gatherings/{gathering_id}", predicate: "Confirmed/Executed/Active", component: "GatheringDetailView.collaboration"), "gathering-collaboration-space"),
        d(.e8, "补位", .serverState(endpoint: "/gatherings/{gathering_id}/backfill", predicate: "gap opened", component: "GatheringDetailView.backfillActions"), "gathering-backfill-actions"),
        d(.e9, "完成确认", .serverState(endpoint: "/gatherings/{gathering_id}/complete", predicate: "completion pending", component: "GatheringDetailView.completionActions"), "gathering-completion-actions"),
        d(.e10, "复局选择", .serverState(endpoint: "/gatherings/{gathering_id}/recur", predicate: "Completed", component: "GatheringDetailView.recurrence"), "gathering-recurrence-actions"),
        d(.e11, "共同目标", .route(path: "/goal/{relation_id}", component: "SharedGoalsView"), "screen-E11-shared-goals"),
        d(.e12, "退出", .systemEvent(event: "user taps leave", component: "GatheringDetailView.leave confirmation"), "gathering-leave-action"),
        d(.e13, "举报与拉黑", .systemEvent(event: "user opens safety sheet", component: "GatheringDetailView.report sheet"), "gathering-safety-report"),
        d(.e14, "局内群聊", .route(path: "/channel/{channel_id}", component: "ChannelView"), "screen-E14-channel"),
        d(.e15, "搭子关系", .route(path: "/relations", component: "RelationsView"), "screen-E15-relations"),
        d(.e16, "共同经历", .route(path: "/relation/{relation_id}", component: "RelationDetailView"), "screen-E16-relation-detail"),
        d(.e17, "解除关系", .systemEvent(event: "user confirms silent dissolve", component: "RelationDetailView.dissolve"), "relation-dissolve-action"),
        d(.m1, "个人中心", .route(path: "/me", component: "ProfileView"), "screen-M1-profile"),
        d(.m2, "画像编辑", .route(path: "/me/profile", component: "ProfileEditorView"), "screen-M2-profile-editor"),
        d(.m3, "信任进度", .route(path: "/me/trust", component: "TrustView"), "screen-M3-trust"),
        d(.m4, "授权管理", .serverState(endpoint: "/auth/me", predicate: "profile route /me/grants loads grants; mutations POST /auth/grants", component: "GrantManagementView"), "screen-M4-grants"),
        d(.m5, "隐私与安全", .route(path: "/me/privacy", component: "PrivacySettingsView"), "screen-M5-privacy"),
        d(.m6, "匹配偏好", .route(path: "/me/preferences", component: "MatchingPreferencesView"), "screen-M6-matching-preferences"),
        d(.m7, "通知与日历", .route(path: "/me/notifications", component: "NotificationPreferencesView"), "screen-M7-notification-settings"),
        d(.m8, "黑名单", .route(path: "/me/blocks", component: "BlockListView"), "screen-M8-block-list"),
        d(.m9, "信任申诉", .route(path: "/me/appeals", component: "TrustAppealsView"), "screen-M9-appeals"),
        d(.m10, "账号与数据", .route(path: "/me/account", component: "AccountDataView"), "screen-M10-account"),
        d(.o1, "主理人控制台", .route(path: "/organizer", component: "OrganizerView"), "screen-O1-organizer"),
        d(.o2, "创建官方局", .systemEvent(event: "organizer taps create", component: "OfficialGatheringEditor"), "screen-O2-create-official"),
        d(.o3, "报名与到场看板", .route(path: "/organizer/gatherings/{gathering_id}/dashboard", component: "OrganizerDashboardView"), "screen-O3-organizer-dashboard"),
        d(.o4, "官方局模板", .serverState(endpoint: "/organizer/templates", predicate: "T4 verified", component: "OrganizerView.templateSection"), "screen-O4-templates"),
        d(.g1, "Hermes 唤起", .systemEvent(event: "today hermes entry", component: "HermesAskView"), "today-hermes-entry"),
        d(.g2, "缺口卡分享", .systemEvent(event: "gap share created", component: "GatheringDetailView ShareLink"), "gathering-share-link"),
        d(.g3, "认证恢复", .systemEvent(event: "401/deep link", component: "AuthenticationFlowView + AppRouter.pendingAfterAuthentication"), "screen-A3-real-login"),
        d(.g4, "静默解散", .serverState(endpoint: "/gatherings/{gathering_id}", predicate: "Dissolved/Expired", component: "GatheringDetailView terminal state"), "gathering-terminal-state"),
        d(.g5, "状态规范", .systemEvent(event: "loading/empty/error/offline/permission/session/stale", component: "OMG5StateView/OMStateViews"), "runtime-state-library")
    ]

    static let extraCompositeIDs = ["B12.2", "MSG"]

    static func definition(for id: FormalNodeID) -> FormalNodeDefinition {
        all.first(where: { $0.id == id })!
    }

    private static func d(
        _ id: FormalNodeID,
        _ title: String,
        _ trigger: FormalNodeTrigger,
        _ accessibilityIdentifier: String
    ) -> FormalNodeDefinition {
        .init(id: id, title: title, trigger: trigger, accessibilityIdentifier: accessibilityIdentifier)
    }
}
