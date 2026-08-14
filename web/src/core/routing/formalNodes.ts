/**
 * Formal production node registry — mirrors iOS FormalNodeRegistry.swift
 * 74 formal nodes + 2 composite (B12.2, MSG).
 */

export type FormalNodeTrigger =
  | { kind: "app"; component: string }
  | { kind: "route"; path: string; component: string }
  | {
      kind: "server-state";
      endpoint: string;
      predicate: string;
      component: string;
    }
  | { kind: "system-event"; event: string; component: string };

export interface FormalNodeDefinition {
  id: string;
  title: string;
  trigger: FormalNodeTrigger;
  accessibilityIdentifier: string;
  /** Feature area for inventory grouping */
  area:
    | "auth"
    | "today"
    | "competitions"
    | "intent"
    | "gatherings"
    | "messages"
    | "profile"
    | "relations"
    | "organizer"
    | "shared"
    | "taste";
  /** Path used by React router when trigger is route-like */
  webPath?: string;
}

function app(
  id: string,
  title: string,
  component: string,
  a11y: string,
  area: FormalNodeDefinition["area"],
): FormalNodeDefinition {
  return {
    id,
    title,
    trigger: { kind: "app", component },
    accessibilityIdentifier: a11y,
    area,
  };
}

function route(
  id: string,
  title: string,
  path: string,
  component: string,
  a11y: string,
  area: FormalNodeDefinition["area"],
): FormalNodeDefinition {
  return {
    id,
    title,
    trigger: { kind: "route", path, component },
    accessibilityIdentifier: a11y,
    area,
    webPath: path,
  };
}

function server(
  id: string,
  title: string,
  endpoint: string,
  predicate: string,
  component: string,
  a11y: string,
  area: FormalNodeDefinition["area"],
  webPath?: string,
): FormalNodeDefinition {
  return {
    id,
    title,
    trigger: { kind: "server-state", endpoint, predicate, component },
    accessibilityIdentifier: a11y,
    area,
    webPath,
  };
}

function system(
  id: string,
  title: string,
  event: string,
  component: string,
  a11y: string,
  area: FormalNodeDefinition["area"],
  webPath?: string,
): FormalNodeDefinition {
  return {
    id,
    title,
    trigger: { kind: "system-event", event, component },
    accessibilityIdentifier: a11y,
    area,
    webPath,
  };
}

/** All 74 formal production nodes. */
export const FORMAL_NODES: FormalNodeDefinition[] = [
  app("A1", "启动路由", "RootView + AppSessionController", "app-root", "auth"),
  route("A2", "认证说明", "/auth", "AuthenticationFlowView.intro", "screen-A2-auth-intro", "auth"),
  route("A3", "扫码认证", "/auth/scan", "RealLoginView", "screen-A3-real-login", "auth"),
  server("A4", "授权范围", "/auth/grants", "first-use route saves each selected grant", "FirstUseSetupView.grants", "screen-A4-grants", "auth", "/auth/grants"),
  server("A5", "画像初始化", "/auth/me", "identity facts loading after authentication", "FirstUseSetupView.facts", "screen-A5-A6-facts", "auth", "/auth/facts"),
  server("A6", "画像确认", "/auth/me", "verified identity facts loaded", "FirstUseSetupView.facts", "screen-A5-A6-facts", "auth", "/auth/facts"),
  server("A7", "社交开关", "/me/privacy", "first-use social opt-in", "FirstUseSetupView.social", "screen-A7-social", "auth", "/auth/social"),
  system("A8", "系统权限", "permission denied/recheck", "OMPermissionRecoveryNotice", "permission-recovery-notice", "shared"),

  route("B1", "今天", "/today", "TodayView", "screen-B1-today", "today"),
  route("B2", "Lulu Hermes 问答", "/today/ask", "HermesAskView", "screen-B2-hermes", "today"),
  route("B3", "我的课表", "/today/timetable", "TimetableView", "screen-B3-timetable", "today"),
  server("B3.1", "课程详情", "/schedule/courses/{course_id}", "selected course", "CourseDetailView", "screen-B3.1-course-detail", "today", "/today/course/:courseId"),
  route("B4", "作业与 DDL", "/today/assignments", "AssignmentsView", "screen-B4-assignments", "today"),
  server("B4.1", "作业详情", "/assignments/{assignment_id}", "selected assignment", "AssignmentDetailView", "screen-B4.1-assignment-detail", "today", "/today/assignment/:assignmentId"),
  route("B5", "体育场馆", "/today/gym", "VenueToolView.gym", "screen-B5-gym", "today"),
  server("B5.1", "体育时段", "/venues/gym/available", "availability loaded", "VenueToolView.gym slots", "screen-B5-gym", "today", "/today/gym"),
  route("B6", "研讨室", "/today/room", "VenueToolView.room", "screen-B6-room", "today"),
  server("B6.1", "研讨室时段", "/venues/room/available", "availability loaded", "VenueToolView.room slots", "screen-B6-room", "today", "/today/room"),
  route("B7", "校园活动", "/today/events", "CampusEventsView", "screen-B7-events", "today"),
  server("B7.1", "活动详情", "/events/{event_id}", "selected event", "CampusEventsView.detail", "screen-B7.1-event-detail", "today", "/today/event/:eventId"),
  route("B8", "组会与课题", "/today/research", "CampusPresetQueryView", "screen-B8-campus-query", "today"),
  route("B9", "班车与节次", "/today/transit", "CampusTransitReferenceView", "screen-B9-transit-reference", "today"),
  server("B10", "场景触发", "/today/summary", "scene_trigger != null", "SceneTriggerDetailView", "screen-B10-scene-trigger", "today", "/today/scene"),
  server("B11", "个人行动预览", "/actions/preview", "personal action previewed", "PersonalActionPreviewView", "screen-B11-personal-action-preview", "today", "/today/action-preview"),
  route("B12", "比赛雷达", "/competitions", "CompetitionsView", "screen-B12-competitions", "competitions"),
  route("B12.1", "赛事详情", "/competition/:competitionId", "CompetitionDetailView", "screen-B12.1-competition-detail", "competitions"),

  route("C1", "公开局", "/gatherings/open", "GatheringListView.open", "screen-C1-public-gatherings", "gatherings"),
  route("C2", "公开局详情", "/gathering/:gatheringId", "GatheringDetailView", "screen-E3-gathering-detail", "gatherings"),
  server("C3", "准入门槛", "/gatherings/{gathering_id}/join", "TRUST_LEVEL_REQUIRED", "TrustRequirementView", "screen-C3-trust-requirement", "gatherings", "/gathering/:gatheringId/trust"),
  route("C4", "缺口卡落地", "/g/:shareToken", "SharedGapLandingView", "screen-C4-share-landing", "gatherings"),

  route("D1", "意图输入", "/intent", "IntentComposerView.editing", "screen-D1-intent", "intent"),
  server("D2", "澄清追问", "/intent/compile", "needs_clarification", "IntentComposerView.clarification", "screen-D2-clarification", "intent", "/intent"),
  server("D3", "意图卡确认", "/intent/compile", "card Draft", "IntentComposerView.editor", "screen-D3-intent-editor", "intent", "/intent"),
  server("D3.1", "能力编辑", "/intent/{card_id}", "Draft capabilities", "IntentComposerView.editor capabilities", "intent-capabilities-editor", "intent", "/intent/capabilities"),
  server("D3.2", "空档选择", "/intent/{card_id}", "Draft available_windows", "IntentComposerView.editor availability", "intent-availability-editor", "intent", "/intent/availability"),
  server("D3.3", "角色编辑", "/intent/{card_id}", "Draft required_roles", "IntentComposerView.editor roles", "intent-roles-editor", "intent", "/intent/roles"),
  server("D3.4", "安全偏好", "/intent/{card_id}", "Draft social/safety", "IntentComposerView.editor safety", "intent-safety-editor", "intent", "/intent/safety"),
  server("D4", "匿名池", "/intent/publish", "Pooling", "IntentComposerView.published", "intent-view-gathering", "intent", "/intent/published"),

  route("E1", "我的局", "/gatherings/mine", "GatheringListView.mine", "screen-E1-my-gatherings", "gatherings"),
  route("E2", "局详情", "/gathering/:gatheringId", "GatheringDetailView", "screen-E3-gathering-detail", "gatherings"),
  server("E3", "多人确认", "/gatherings/{gathering_id}", "Tentative", "GatheringDetailView.confirmationActions", "gathering-confirmation-actions", "gatherings"),
  server("E4", "改约协商", "/gatherings/{gathering_id}/reschedule", "proposal open", "GatheringDetailView.rescheduleActions", "gathering-reschedule-actions", "gatherings"),
  server("E5", "行动预览", "/actions/preview", "previewed", "GatheringDetailView.actionActions", "gathering-action-preview", "gatherings"),
  server("E6", "执行结果", "/actions/{action_id}", "succeeded/failed", "GatheringDetailView.action result", "gathering-action-result", "gatherings"),
  server("E7", "协作空间", "/gatherings/{gathering_id}", "Confirmed/Executed/Active", "GatheringDetailView.collaboration", "gathering-collaboration-space", "gatherings"),
  server("E8", "补位", "/gatherings/{gathering_id}/backfill", "gap opened", "GatheringDetailView.backfillActions", "gathering-backfill-actions", "gatherings"),
  server("E9", "完成确认", "/gatherings/{gathering_id}/complete", "completion pending", "GatheringDetailView.completionActions", "gathering-completion-actions", "gatherings"),
  server("E10", "复局选择", "/gatherings/{gathering_id}/recur", "Completed", "GatheringDetailView.recurrence", "gathering-recurrence-actions", "gatherings"),
  route("E11", "共同目标", "/goal/:relationId", "SharedGoalsView", "screen-E11-shared-goals", "relations"),
  system("E12", "退出", "user taps leave", "GatheringDetailView.leave confirmation", "gathering-leave-action", "gatherings"),
  system("E13", "举报与拉黑", "user opens safety sheet", "GatheringDetailView.report sheet", "gathering-safety-report", "gatherings"),
  route("E14", "局内群聊", "/channel/:channelId", "ChannelView", "screen-E14-channel", "messages"),
  route("E15", "搭子关系", "/relations", "RelationsView", "screen-E15-relations", "relations"),
  route("E16", "共同经历", "/relation/:relationId", "RelationDetailView", "screen-E16-relation-detail", "relations"),
  system("E17", "解除关系", "user confirms silent dissolve", "RelationDetailView.dissolve", "relation-dissolve-action", "relations"),

  route("M1", "个人中心", "/me", "ProfileView", "screen-M1-profile", "profile"),
  route("M2", "画像编辑", "/me/profile", "ProfileEditorView", "screen-M2-profile-editor", "profile"),
  route("M3", "信任进度", "/me/trust", "TrustView", "screen-M3-trust", "profile"),
  server("M4", "授权管理", "/auth/me", "profile route /me/grants", "GrantManagementView", "screen-M4-grants", "profile", "/me/grants"),
  route("M5", "隐私与安全", "/me/privacy", "PrivacySettingsView", "screen-M5-privacy", "profile"),
  route("M6", "匹配偏好", "/me/preferences", "MatchingPreferencesView", "screen-M6-matching-preferences", "profile"),
  route("M7", "通知与日历", "/me/notifications", "NotificationPreferencesView", "screen-M7-notification-settings", "profile"),
  route("M8", "黑名单", "/me/blocks", "BlockListView", "screen-M8-block-list", "profile"),
  route("M9", "信任申诉", "/me/appeals", "TrustAppealsView", "screen-M9-appeals", "profile"),
  route("M10", "账号与数据", "/me/account", "AccountDataView", "screen-M10-account", "profile"),

  route("O1", "主理人控制台", "/organizer", "OrganizerView", "screen-O1-organizer", "organizer"),
  system("O2", "创建官方局", "organizer taps create", "OfficialGatheringEditor", "screen-O2-create-official", "organizer", "/organizer/create"),
  route("O3", "报名与到场看板", "/organizer/gatherings/:gatheringId/dashboard", "OrganizerDashboardView", "screen-O3-organizer-dashboard", "organizer"),
  server("O4", "官方局模板", "/organizer/templates", "T4 verified", "OrganizerView.templateSection", "screen-O4-templates", "organizer", "/organizer/templates"),

  system("G1", "Lulu Hermes 唤起", "today hermes entry", "HermesAskView", "today-hermes-entry", "today", "/today/ask"),
  system("G2", "缺口卡分享", "gap share created", "GatheringDetailView ShareLink", "gathering-share-link", "gatherings"),
  system("G3", "认证恢复", "401/deep link", "AuthenticationFlowView + pendingAfterAuthentication", "screen-A3-real-login", "auth", "/auth/scan"),
  server("G4", "静默解散", "/gatherings/{gathering_id}", "Dissolved/Expired", "GatheringDetailView terminal state", "gathering-terminal-state", "gatherings"),
  system("G5", "状态规范", "loading/empty/error/offline/permission/session/stale", "OMAsyncStateView/OMStateView", "runtime-state-library", "shared", "/states"),

  // Taste import (iOS Feature; not a numbered formal node but production surface)
];

/** Extra composite states from return boards (not counted in 74). */
export const EXTRA_COMPOSITE_NODES = [
  {
    id: "B12.2",
    title: "赛事牌桌 · 差一个",
    accessibilityIdentifier: "screen-B12.2-table",
    area: "competitions" as const,
    webPath: "/competition/:competitionId/table",
  },
  {
    id: "MSG",
    title: "消息总览",
    accessibilityIdentifier: "screen-MSG-messages",
    area: "messages" as const,
    webPath: "/messages",
  },
];

/** Taste import production surface (iOS TasteImport feature). */
export const TASTE_IMPORT_ROUTE = {
  id: "TASTE",
  title: "兴趣画像导入",
  webPath: "/me/taste",
  accessibilityIdentifier: "screen-taste-import",
  area: "taste" as const,
};

export const FIVE_TAB_LABELS = ["今天", "活动", "差一个", "消息", "我"] as const;

export const TAB_ROOTS = {
  today: { label: "今天", path: "/today", formalId: "B1" },
  competitions: { label: "活动", path: "/competitions", formalId: "B12" },
  create: { label: "差一个", path: "/intent", formalId: "D1" },
  messages: { label: "消息", path: "/messages", formalId: "MSG" },
  me: { label: "我", path: "/me", formalId: "M1" },
} as const;

export type TabId = keyof typeof TAB_ROOTS;

export function formalNodeById(id: string): FormalNodeDefinition | undefined {
  return FORMAL_NODES.find((n) => n.id === id);
}

/** Production routes with a dedicated web path (formal + composite + taste). */
export function productionWebRoutes(): {
  id: string;
  path: string;
  a11y: string;
  area: string;
}[] {
  const fromFormal = FORMAL_NODES.filter((n) => n.webPath).map((n) => ({
    id: n.id,
    path: n.webPath!,
    a11y: n.accessibilityIdentifier,
    area: n.area,
  }));
  const extras = EXTRA_COMPOSITE_NODES.map((n) => ({
    id: n.id,
    path: n.webPath,
    a11y: n.accessibilityIdentifier,
    area: n.area,
  }));
  return [
    ...fromFormal,
    ...extras,
    {
      id: TASTE_IMPORT_ROUTE.id,
      path: TASTE_IMPORT_ROUTE.webPath,
      a11y: TASTE_IMPORT_ROUTE.accessibilityIdentifier,
      area: TASTE_IMPORT_ROUTE.area,
    },
  ];
}

export const FORMAL_NODE_COUNT = 74;
