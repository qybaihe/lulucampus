/**
 * Repository adapters — same endpoint set as iOS SERVICE_MAP / Repositories.swift.
 * No mock business success paths.
 */

import type { APIClient } from "./client";

export interface TodaySummary {
  date?: string;
  greeting?: string;
  hermes_hint?: string;
  scene_trigger?: {
    key?: string;
    title?: string;
    body?: string;
    cta_label?: string;
  } | null;
  pending?: Array<Record<string, unknown>>;
  timeline?: Array<{
    id?: string;
    title?: string;
    subtitle?: string;
    time_label?: string | null;
    location?: string | null;
    gathering_id?: string | null;
    course_id?: string | null;
    kind?: string;
    start_at?: string | null;
    end_at?: string | null;
    starts_at?: string;
  }>;
  tools?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export interface Competition {
  id: string;
  name: string;
  tracks?: string[];
  tier?: string;
  summary?: string;
  registration_deadline?: string | null;
  official_url?: string | null;
  registration_url?: string;
  registration_instructions?: string | null;
  rewards?: string | null;
  location?: string | null;
  mode?: string;
  recommendation_tier?: string;
  recommendation_label?: string;
  recommendation_description?: string;
  team_forming_supported?: boolean;
  collaboration_action?: string;
  taste_fit?: number | null;
  taste_fit_label?: string | null;
  taste_fit_reasons?: string[];
  recruit_hints?: string[];
  recruit_gap_count?: number;
  recruit_gap_labels?: string[];
  team_constraints?: { team_size_min?: number; team_size_max?: number };
  required_skills?: Array<{ key?: string; label?: string; [key: string]: unknown }>;
  [key: string]: unknown;
}

/** 能力键 → 中文名（对齐 iOS CapabilityLabel；未知键原样透出）。 */
export function capabilityLabel(key: string): string {
  const table: Record<string, string> = {
    frontend: "前端",
    backend: "后端",
    design: "设计",
    visual_design: "视觉",
    product: "产品",
    data_analysis: "数据分析",
    machine_learning: "机器学习",
    algorithm: "算法",
    presentation: "路演",
    writing: "文案",
    paper_writing: "写作",
    research: "调研",
    video: "视频",
    operations: "运营",
    business_analysis: "商业分析",
    modeling: "建模",
    programming: "编程",
  };
  return table[key] ?? table[key.toLowerCase()] ?? key;
}

export interface GatheringParticipant {
  user_id?: string;
  display_name?: string | null;
  college?: string | null;
  major?: string | null;
  role?: string | null;
  interest_tags?: string[];
  taste_summary?: string | null;
  label?: string | null;
  confirmation_status?: string | null;
  [key: string]: unknown;
}

export interface Gathering {
  id: string;
  title?: string;
  status?: string;
  /** Server field names from GatheringView */
  member_count?: number;
  confirmed_count?: number;
  filled_count?: number;
  target_size?: number;
  gap_count?: number;
  start_at?: string | null;
  end_at?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  location?: string | null;
  location_label?: string | null;
  channel_id?: string | null;
  competition_id?: string | null;
  required_roles?: string[];
  looking_for?: string[];
  filled_roles?: string[];
  roster_highlights?: string[];
  match_reason?: string | null;
  participants?: GatheringParticipant[];
  my_confirmation?: string | null;
  my_recurrence_decision?: string | null;
  action_id?: string | null;
  leave_capability?: Record<string, unknown> | null;
  [key: string]: unknown;
}

export interface RescheduleProposal {
  id?: string;
  proposal_id?: string;
  start_at?: string;
  end_at?: string;
  status?: string;
  [key: string]: unknown;
}

export interface BackfillOpportunity {
  available?: boolean;
  gap_count?: number;
  eligibility?: string;
  options?: Array<{ key?: string; label?: string; [key: string]: unknown }>;
  [key: string]: unknown;
}

export interface ActionCapability {
  enabled?: boolean;
  action?: string | null;
  disabled_reason?: string | null;
  params?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface SharedGoalMilestone {
  fraction: number;
  target_value: number;
  reached: boolean;
  reached_at?: string | null;
}

export interface SharedGoalMemberProgress {
  user_id: string;
  display_name?: string | null;
  current_value: number;
  last_progress_at?: string | null;
}

/** GET /relations/{id}/goals — 对齐 iOS SharedGoal */
export interface SharedGoal {
  id: string;
  relation_id?: string;
  definition?: string;
  period_start?: string;
  period_end?: string;
  target_value?: number;
  current_value?: number;
  unit?: string;
  status?: string;
  milestones?: SharedGoalMilestone[];
  member_progress?: SharedGoalMemberProgress[];
  next_action?: string | null;
  last_broadcast?: string | null;
  last_progress_at?: string | null;
  progress_source?: string;
  [key: string]: unknown;
}

export interface OrganizerGatheringSummary {
  id: string;
  title?: string;
  status?: string;
  target_size?: number;
  start_at?: string | null;
  [key: string]: unknown;
}

export interface OrganizerQuotaBatch {
  label: string;
  slots: number;
}

export interface OrganizerParticipant {
  user_id: string;
  display_name?: string | null;
  confirmation_status?: string;
  attended?: boolean;
}

/** GET /organizer/gatherings/{id}/dashboard — OrganizerDashboardView */
export interface OrganizerDashboard {
  gathering_id?: string;
  status?: string;
  target_size?: number;
  registered_count?: number;
  confirmed_count?: number;
  attended_count?: number;
  quota_batches?: OrganizerQuotaBatch[];
  participants?: OrganizerParticipant[] | null;
  identity_visibility?: string;
  [key: string]: unknown;
}

/** GET /organizer/templates — OfficialTemplateView */
export interface OrganizerTemplate {
  id: string;
  title?: string;
  goal?: string;
  gathering_type?: string;
  location?: string;
  campus?: string | null;
  min_size?: number;
  target_size?: number;
  duration_minutes?: number;
  required_roles?: string[];
  recurrence_rule?: string | null;
  active?: boolean;
  [key: string]: unknown;
}

/** 局状态 → 中文显示名（对齐 iOS GatheringStatus.displayName）。 */
export function gatheringStatusName(status?: string | null): string {
  switch (status) {
    case "Draft":
      return "草稿";
    case "Pooling":
      return "招募中";
    case "Tentative":
      return "待确认";
    case "Confirmed":
      return "已确认";
    case "Previewed":
      return "待核对";
    case "Executed":
      return "已执行";
    case "Active":
      return "进行中";
    case "Completed":
      return "已完成";
    case "Recurred":
      return "已复局";
    case "Archived":
      return "已归档";
    case "Dissolved":
      return "已解散";
    default:
      return "状态同步中";
  }
}

/** Derive seat UI only from server-provided roles/participants — never invent names. */
export function seatsFromGathering(g: Gathering): Array<{
  role: string;
  state: "filled" | "gap";
  sticker: string;
}> {
  const roles = g.required_roles?.filter(Boolean) ?? [];
  const participants = g.participants ?? [];
  const target = g.target_size ?? Math.max(roles.length, participants.length, 0);
  const filled =
    g.member_count ??
    g.filled_count ??
    participants.length ??
    0;
  if (roles.length > 0) {
    return roles.map((role, i) => {
      const matched = participants.find(
        (p) => p.role === role || p.label === role,
      );
      const state: "filled" | "gap" =
        matched || i < filled ? "filled" : "gap";
      return {
        role,
        state,
        sticker: state === "gap" ? "chair-empty.png" : "badge.png",
      };
    });
  }
  // No role names from server: show anonymous filled/gap dots only if target known
  if (target > 0) {
    return Array.from({ length: target }, (_, i) => {
      const state: "filled" | "gap" = i < filled ? "filled" : "gap";
      return {
        role: state === "gap" ? "空位" : "已就位",
        state,
        sticker: state === "gap" ? "chair-empty.png" : "badge.png",
      };
    });
  }
  return [];
}

export function gapCountOf(g: Gathering): number {
  if (typeof g.gap_count === "number") return g.gap_count;
  const target = g.target_size ?? 0;
  const filled = g.member_count ?? g.filled_count ?? 0;
  return Math.max(0, target - filled);
}

export interface IntentCompileResult {
  needs_clarification?: boolean;
  max_rounds?: number;
  questions?: Array<{ id?: string; prompt?: string; key?: string }>;
  card?: IntentCard;
  taste_fit_label?: string | null;
  recruit_hints?: string[];
  [key: string]: unknown;
}

export interface IntentCapability {
  key: string;
  source: "verified" | "self_reported" | "ai_inferred" | string;
}

export interface IntentWindow {
  start_at?: string;
  end_at?: string;
  stability?: number;
  [key: string]: unknown;
}

export interface IntentCard {
  id?: string;
  status?: string;
  gathering_type?: string;
  mode?: string;
  goal?: string;
  mood_note?: string | null;
  raw_text?: string;
  capabilities?: IntentCapability[];
  required_roles?: string[];
  intensity?: string;
  available_windows?: IntentWindow[];
  campus?: string | null;
  min_size?: number;
  minimum_size?: number;
  target_size?: number;
  social_mode?: "after_confirmed" | "after_full" | string;
  same_gender_only?: boolean;
  competition_id?: string | null;
  expires_at?: string | null;
  [key: string]: unknown;
}

/** GET /intent/{card_id}/publication — IntentPublishResult */
export interface IntentPublishResult {
  intent_id?: string;
  gathering_id?: string;
  status?: string;
  expires_at?: string;
  [key: string]: unknown;
}

/** Wire contract from MessageView — same fields as iOS MessagePayload. */
export interface MessageImage {
  media_id: string;
  url: string;
  content_type: string;
  byte_count?: number;
  sha256?: string;
  width?: number | null;
  height?: number | null;
  caption?: string | null;
}

export interface MessageLocation {
  latitude: number;
  longitude: number;
  label: string;
  address?: string | null;
}

export interface MessagePayload {
  id: string;
  channel_id: string;
  sender_id: string;
  sender_type: "human" | "azou" | "system" | string;
  content_type: "text" | "image" | "location" | string;
  content?: string | null;
  image?: MessageImage | null;
  location?: MessageLocation | null;
  sent_at: string;
  sender_display_name?: string | null;
  [key: string]: unknown;
}

export type MessageCreate =
  | { content: string; content_type: "text" }
  | { content_type: "image"; image: { media_id: string; caption?: string | null } }
  | { content_type: "location"; location: MessageLocation };

export interface ChannelScenePolicy {
  mode: string;
  phase: string;
  sending_enabled: boolean;
  live_connection_enabled: boolean;
  reason?: string | null;
  next_change_at?: string | null;
  source?: string;
}

export interface MentionAzouResult {
  message: MessagePayload;
  action_hint?: Record<string, unknown> | null;
}

export interface ImageAsset {
  media_id: string;
  url: string;
  content_type: string;
  byte_count?: number;
  sha256?: string;
  width?: number | null;
  height?: number | null;
}

export interface RelationParticipant {
  user_id: string;
  display_name?: string | null;
  college?: string | null;
  major?: string | null;
  interest_tags?: string[];
  taste_summary?: string | null;
}

export interface RelationExperience {
  id: string;
  participants?: string[];
  gathering_type: string;
  occurred_at?: string;
  outcome?: string;
  common_grounds?: string[];
}

/** 搭子里程碑：1/3/5/10/20 次同局的纪念节点（纯事实，非互评）。 */
export interface RelationMilestone {
  reached: number;
  reached_label?: string | null;
  next?: number | null;
  next_label?: string | null;
  remaining?: number | null;
}

/** 仅双方可见的经历时间线。 */
export interface RelationTimelineEntry {
  gathering_id: string;
  title?: string | null;
  gathering_type: string;
  occurred_at?: string;
  location?: string | null;
  duration_minutes?: number | null;
  outcome?: string;
  common_grounds?: string[];
  via_recurrence?: boolean;
}

export interface RelationGoalSummary {
  id: string;
  definition: string;
  current_value: number;
  target_value: number;
  unit: string;
  period_end: string;
}

/** GET /relations — 对齐 iOS RelationSummary */
export interface RelationSummary {
  id: string;
  participants: RelationParticipant[];
  status?: string;
  experiences?: RelationExperience[];
  latest_experience_at?: string | null;
  channel_id?: string | null;
  times_together?: number;
  recur_count?: number;
  is_fixed_partner?: boolean;
  partner_title?: string | null;
  milestone?: RelationMilestone | null;
  timeline?: RelationTimelineEntry[];
  next_window?: { start_at: string; end_at: string } | null;
  active_goal?: RelationGoalSummary | null;
  [key: string]: unknown;
}

export interface TrustCondition {
  key: string;
  label: string;
  met: boolean;
  current?: number | null;
  required?: number | null;
  unit?: string | null;
  detail?: string | null;
}

export interface TrustMetricProgress {
  key: string;
  label: string;
  current: number;
  required: number;
  unit: string;
}

export interface TrustLevelGuideItem {
  level: string;
  name: string;
  how: string;
  benefits?: string[];
  is_current?: boolean;
  is_reached?: boolean;
}

/** GET /trust/me — 对齐 iOS TrustProgress */
export interface TrustMe {
  level?: string;
  level_name?: string;
  level_narrative?: string | null;
  next_level?: string | null;
  next_level_name?: string | null;
  next_level_progress?: TrustMetricProgress[];
  conditions?: TrustCondition[];
  current_benefits?: string[];
  next_benefits?: string[];
  overall_progress?: number;
  level_guide?: TrustLevelGuideItem[];
  gaps?: string[];
  statistics?: Record<string, unknown>;
  unlocks?: Array<{
    capability: string;
    required_level: string;
    unlocked: boolean;
  }> | null;
  observation?: Record<string, unknown> | null;
  /** 兼容旧字段 */
  progress?: number;
  label?: string;
  next_requirement?: string | null;
  [key: string]: unknown;
}

/** GET/PATCH /me/privacy — SocialPreferences */
export interface SocialPreferences {
  social_enabled: boolean;
  course_matching_enabled: boolean;
  identity_disclosure: "after_confirmed" | "after_full" | string;
  same_gender_only: boolean;
  minimum_group_size: number;
  scene_sensitive_policy?: string;
  [key: string]: unknown;
}

/** GET/PATCH /me/matching-preferences */
export interface MatchingPreferences {
  interaction_style: "quiet" | "balanced" | "talkative" | string;
  sport_level: "beginner" | "casual" | "intermediate" | "advanced" | string;
  study_intensity: "light" | "balanced" | "focused" | string;
  [key: string]: unknown;
}

/** GET/PATCH /me/notification-preferences */
export interface NotificationPreferences {
  overall_enabled: boolean;
  calendar_sync_enabled: boolean;
  categories: {
    gathering_updates?: boolean;
    action_updates?: boolean;
    chat_messages?: boolean;
    trust_updates?: boolean;
    competition_deadlines?: boolean;
    schedule_reminders?: boolean;
    [key: string]: boolean | undefined;
  };
  system_settings_managed_locally?: string[];
  [key: string]: unknown;
}

/** GET /notifications */
export interface InboxNotification {
  id: string;
  type: string;
  category?: string;
  title?: string;
  payload?: Record<string, unknown>;
  created_at: string;
  delivered_at?: string | null;
  [key: string]: unknown;
}

export interface BlockEntry {
  blocked_user_id: string;
  created_at?: string;
  [key: string]: unknown;
}

export interface TrustAppeal {
  id?: string;
  reason?: string;
  status?: string;
  result?: string | null;
  created_at?: string;
  updated_at?: string;
  decided_at?: string | null;
  [key: string]: unknown;
}

/** GET /profile/me — ProfileView（画像编辑用，区别于 /auth/me） */
export interface ProfileCapability {
  key?: string;
  label?: string;
  source?: "verified" | "self_reported" | string;
  weight?: number;
  hidden?: boolean;
  [key: string]: unknown;
}

/** /profile/me 内嵌的抖音兴趣画像摘要卡（非完整 TasteProfileResult）。 */
export interface TasteProfileSummary {
  status?: string | null;
  primary_tag?: { key?: string; label?: string; score?: number } | null;
  secondary_tags?: string[] | null;
  interest_domains?: string[] | null;
  interest_tags?: string[] | null;
  summary?: string | null;
  persona?: string | null;
  matching_hints?: string[] | null;
  confidence?: number | null;
  calibrated?: boolean | null;
  source?: string | null;
  visibility?: string | null;
}

export interface UserProfile {
  user_id?: string;
  init_status?: string;
  init_progress?: number;
  identity?: Record<string, unknown>;
  capabilities?: ProfileCapability[];
  available_capabilities?: Array<
    | string
    | { key?: string; label?: string; [key: string]: unknown }
  >;
  interest_domains?: unknown[];
  trust_progress?: Record<string, unknown>;
  taste_profile?: TasteProfileSummary | null;
  [key: string]: unknown;
}

/** GET /me/recap — SemesterRecap */
export interface SemesterRecap {
  term_label?: string;
  since?: string;
  gatherings_completed?: number;
  partners_met?: number;
  total_hours?: number;
  recurrences?: number;
  top_partner?: { display_name?: string | null; times_together?: number } | null;
  top_types?: Array<{ gathering_type?: string; count?: number }>;
  top_location?: string | null;
  highlights?: string[];
  share_text?: string;
  [key: string]: unknown;
}

/** GET /gatherings/{id}/icebreaker — IcebreakerView */
export interface Icebreaker {
  gathering_id?: string;
  headline?: string;
  facts?: Array<{ kind?: string; text?: string }>;
  first_lines?: string[];
  next_steps?: {
    start_at?: string | null;
    end_at?: string | null;
    location?: string | null;
    campus?: string | null;
    channel_id?: string | null;
    checklist?: string[];
  };
  [key: string]: unknown;
}

/** GET /gatherings/history/safety */
export interface DepartedSafetyContext {
  gathering_id: string;
  title?: string;
  gathering_type?: string;
  status?: string;
  left_at?: string;
  reportable_participants?: Array<{
    user_id?: string;
    display_name?: string | null;
    [key: string]: unknown;
  }>;
  [key: string]: unknown;
}

/** POST /gatherings/initiate */
export interface InitiateGatheringDraft {
  title: string;
  goal: string;
  gathering_type: string;
  mode?: "similar" | "complementary";
  campus?: string | null;
  location?: string | null;
  start_at?: string | null;
  end_at?: string | null;
  min_size?: number;
  target_size?: number;
  required_roles?: string[];
  cross_college?: boolean;
}

/** GET /competitions/recommendation-tiers */
export interface RecommendationTier {
  code: string;
  label: string;
  description?: string;
  sort_order?: number;
}

/** GET /competitions/{id}/teams */
export interface CompetitionTeam {
  id: string;
  title?: string;
  gathering_type?: string;
  status?: string;
  location?: string | null;
  campus?: string | null;
  start_at?: string | null;
  target_size?: number;
  member_count?: number;
  required_roles?: string[];
  expires_at?: string | null;
  goal?: string | null;
  missing_count?: number;
  missing_roles?: string[];
  filled_roles?: string[];
  roster_highlights?: string[];
  [key: string]: unknown;
}

/** GET /actions/{id} — CampusActionView */
export interface CampusAction {
  id: string;
  user_id?: string;
  gathering_id?: string | null;
  action_name?: string;
  status?: string;
  params?: Record<string, unknown>;
  preview_snapshot?: Record<string, unknown>;
  snapshot_hash?: string;
  authorization?: {
    required_count?: number;
    authorized_count?: number;
    actor_decision?: string | null;
    all_authorized?: boolean;
    [key: string]: unknown;
  } | null;
  modification?: {
    reason?: string;
    proposed_params?: Record<string, unknown>;
    status?: string;
    created_at?: string;
    [key: string]: unknown;
  } | null;
  execution_result?: Record<string, unknown> | null;
  error_category?: string | null;
  [key: string]: unknown;
}

/** 抖音导入手机号验证 — PhoneLoginView */
export interface PhoneLoginState {
  import_id: string;
  status: string;
  phone_masked?: string | null;
  code_sent?: boolean;
  verified?: boolean;
  authenticated_at?: string | null;
  submit_code?: string;
  verify?: string;
  error?: TasteImportError | null;
}

export interface TasteQuestions {
  schema_version?: string | number;
  import_id?: string;
  candidate_tags?: TasteTagScore[];
  questions?: Array<{
    id: string;
    type?: string;
    prompt?: string;
    required?: boolean;
    options?: Array<{ id: string; label?: string }>;
  }>;
  calibrated?: boolean;
  optional?: boolean;
  min_answers?: number;
  max_answers?: number;
  intro?: string;
  submit_path?: string;
  [key: string]: unknown;
}

/** POST /auth/session — same contract as iOS LoginSession */
export interface LoginSession {
  id: string;
  user_id?: string;
  status: string;
  qr_image_data_url?: string | null;
  deep_link?: string | null;
  expires_at?: string;
  access_token?: string | null;
  redemption_token?: string | null;
  error_category?: string | null;
  [key: string]: unknown;
}

export interface AuthRedeemResult {
  access_token: string;
}

/** POST /auth/register · POST /auth/login — PhoneAuthView */
export interface PhoneAuthResult {
  access_token: string;
  user_id: string;
  display_name?: string | null;
  is_new_user?: boolean;
}

export interface GrantView {
  scope: string;
  granted: boolean;
  granted_at?: string | null;
  revoked_at?: string | null;
}

/** GET /auth/me — IdentityFactsView */
export interface AuthMe {
  user_id?: string;
  display_name?: string | null;
  verified?: boolean;
  college?: string | null;
  major?: string | null;
  grade_year?: number | null;
  campus?: string | null;
  gender_code?: string | null;
  social_enabled?: boolean;
  course_matching_enabled?: boolean;
  identity_disclosure?: string;
  same_gender_only?: boolean;
  minimum_group_size?: number;
  grants?: GrantView[];
  session_health?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export type GrantScope =
  | "timetable"
  | "curriculum"
  | "enrollment"
  | "agent_booking";

const DEVICE_INSTALL_KEY = "onemore.device.install.id";
/** Fallback when localStorage is unavailable (tests / SSR). */
let memoryDeviceInstallId: string | null = null;

export function getOrCreateDeviceInstallId(): string {
  try {
    if (typeof localStorage !== "undefined") {
      let id = localStorage.getItem(DEVICE_INSTALL_KEY);
      if (!id) {
        id =
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        localStorage.setItem(DEVICE_INSTALL_KEY, id);
      }
      return id;
    }
  } catch {
    /* fall through to memory */
  }
  if (!memoryDeviceInstallId) {
    memoryDeviceInstallId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
  return memoryDeviceInstallId;
}

/* ---------- 抖音兴趣画像（taste_profile） ---------- */

export interface TasteSourceProfile {
  nickname?: string | null;
  avatar_url?: string | null;
  uid?: string | null;
  sec_uid?: string | null;
}

export interface TasteImportProgress {
  phase: string;
  current: number;
  total?: number | null;
  percent?: number | null;
  message?: string;
  qr_scanned?: boolean | null;
  phone_masked?: string | null;
}

export interface TasteTagScore {
  key: string;
  label: string;
  score: number;
}

export interface TasteDomainScore {
  key: string;
  label: string;
  score: number;
}

export interface TasteInterestFacet {
  domain: string;
  facet: string;
  label: string;
  source?: string | null;
}

export interface TasteProfileResult {
  status?: string;
  primary_tag: TasteTagScore;
  secondary_tags: TasteTagScore[];
  interest_domains: TasteDomainScore[];
  interest_facets: TasteInterestFacet[];
  dimensions: Record<string, number>;
  summary: string;
  persona?: string | null;
  matching_hints: string[];
  confidence: number;
  calibrated: boolean;
  calibrated_at?: string | null;
  sample?: {
    items?: number;
    unique_authors?: number;
    generation?: string | null;
    [key: string]: unknown;
  };
  source?: string;
  model_version?: string;
  visibility?: string;
}

export interface TasteImportError {
  code?: string;
  message?: string;
}

export interface TasteImportSession {
  id: string;
  source?: string;
  status: string;
  qr_image_data_url?: string | null;
  qr_version: number;
  qr_expires_at?: string | null;
  expires_at?: string;
  source_profile?: TasteSourceProfile | null;
  progress?: TasteImportProgress;
  candidate_tags?: TasteTagScore[];
  result?: TasteProfileResult | null;
  questions?: Record<string, unknown> | null;
  error?: TasteImportError | null;
}

export interface TasteQRLogin {
  import_id: string;
  status: string;
  qr_image_data_url?: string | null;
  qr_version: number;
  qr_expires_at?: string | null;
  qr_image_url: string;
  error?: TasteImportError | null;
}

export function createRepositories(client: APIClient) {
  return {
    today: {
      summary: (force = false) =>
        client.get<TodaySummary>("/today/summary", {
          query: force ? { force: 1 } : undefined,
        }),
      ignoreSceneTrigger: (sceneKey: string) =>
        client.post(`/today/triggers/${sceneKey}/ignore`, {}),
    },
    competitions: {
      list: (tier?: string | null) =>
        client.get<Competition[] | { items: Competition[] }>("/competitions", {
          query: tier ? { recommendation_tier: tier } : undefined,
        }),
      get: (id: string) => client.get<Competition>(`/competitions/${id}`),
      recommendationTiers: () =>
        client.get<RecommendationTier[]>("/competitions/recommendation-tiers", {
          auth: false,
        }),
      teams: (id: string) =>
        client.get<CompetitionTeam[]>(`/competitions/${id}/teams`, {
          auth: false,
        }),
      team: (competitionId: string, teamId: string) =>
        client.get<CompetitionTeam>(
          `/competitions/${competitionId}/teams/${teamId}`,
          { auth: false },
        ),
    },
    intent: {
      compile: (body: {
        text: string;
        mood_note?: string;
        competition_id?: string | null;
        clarification_round?: number;
        answers?: Record<string, string>;
      }) => client.post<IntentCompileResult>("/intent/compile", body),
      get: (cardId: string) => client.get<IntentCard>(`/intent/${cardId}`),
      publish: (body: { card_id: string }, idempotencyKey?: string) =>
        client.post<IntentPublishResult>("/intent/publish", body, {
          idempotencyKey,
        }),
      publication: (cardId: string) =>
        client.get<IntentPublishResult>(`/intent/${cardId}/publication`),
      patch: (cardId: string, body: Record<string, unknown>, key?: string) =>
        client.patch<IntentCard>(`/intent/${cardId}`, body, {
          idempotencyKey: key,
        }),
      remove: (cardId: string, key?: string) =>
        client.delete<{ id?: string; status?: string }>(`/intent/${cardId}`, {
          idempotencyKey: key,
        }),
    },
    gatherings: {
      open: () =>
        client.get<Gathering[] | { items: Gathering[] }>("/gatherings/open"),
      mine: () =>
        client.get<Gathering[] | { items: Gathering[] }>("/gatherings/mine"),
      get: (id: string) => client.get<Gathering>(`/gatherings/${id}`),
      /** T2 · 直接发起具体局（screen-E2-self-initiate） */
      initiate: (body: InitiateGatheringDraft, key?: string) =>
        client.post<Gathering>("/gatherings/initiate", body, {
          idempotencyKey: key,
        }),
      /** E13 · 历史局安全与举报 */
      safetyHistory: () =>
        client.get<DepartedSafetyContext[]>("/gatherings/history/safety"),
      /** 成局后 30 秒破冰包；调用方自行吞错（对齐 iOS try?） */
      icebreaker: (id: string) =>
        client.get<Icebreaker>(`/gatherings/${id}/icebreaker`),
      /** T3 · 固定周期系列（从已完成局创建多期） */
      recurring: (
        id: string,
        body: {
          first_start_at: string;
          occurrences?: number;
          interval_weeks?: number;
          duration_minutes?: number;
        },
        key?: string,
      ) =>
        client.post<Gathering[]>(`/gatherings/${id}/recurring`, body, {
          idempotencyKey: key,
        }),
      join: (id: string, body: Record<string, unknown> = {}, key?: string) =>
        client.post<Gathering>(`/gatherings/${id}/join`, body, {
          idempotencyKey: key,
        }),
      confirm: (
        id: string,
        confirmed = true,
        key?: string,
      ) =>
        client.post<Gathering>(
          `/gatherings/${id}/confirm`,
          { confirmed },
          { idempotencyKey: key },
        ),
      leave: (id: string, key?: string) =>
        client.post(`/gatherings/${id}/leave`, {}, { idempotencyKey: key }),
      timeOptions: (id: string) =>
        client.get<Array<Record<string, unknown>>>(
          `/gatherings/${id}/time-options`,
        ),
      currentReschedule: (id: string) =>
        client.get<RescheduleProposal | null>(`/gatherings/${id}/reschedule`),
      reschedule: (
        id: string,
        body: { start_at: string; end_at: string },
        key?: string,
      ) =>
        client.post<RescheduleProposal>(`/gatherings/${id}/reschedule`, body, {
          idempotencyKey: key,
        }),
      voteReschedule: (
        id: string,
        proposalId: string,
        accepted: boolean,
        key?: string,
      ) =>
        client.post<RescheduleProposal>(
          `/gatherings/${id}/reschedule/${proposalId}/vote`,
          { accepted },
          { idempotencyKey: key },
        ),
      backfill: (id: string) =>
        client.get<BackfillOpportunity>(`/gatherings/${id}/backfill`),
      claimBackfill: (id: string, key?: string) =>
        client.post<Gathering>(
          `/gatherings/${id}/backfill/claim`,
          {},
          { idempotencyKey: key },
        ),
      backfillFallback: (id: string, optionKey: string, key?: string) =>
        client.post<Gathering>(
          `/gatherings/${id}/backfill/fallback`,
          { option_key: optionKey },
          { idempotencyKey: key },
        ),
      complete: (id: string, completed = true, key?: string) =>
        client.post<Gathering>(
          `/gatherings/${id}/complete`,
          { completed },
          { idempotencyKey: key },
        ),
      recur: (id: string, keepUserIds?: string[], key?: string) =>
        client.post<Gathering>(
          `/gatherings/${id}/recur`,
          { keep_user_ids: keepUserIds },
          { idempotencyKey: key },
        ),
      finishRecur: (id: string, key?: string) =>
        client.post(
          `/gatherings/${id}/recur/finish`,
          {},
          { idempotencyKey: key },
        ),
      actionCapability: (id: string) =>
        client.get<ActionCapability>(`/gatherings/${id}/action-capability`),
      bookingOptions: (id: string) =>
        client.get<Array<Record<string, unknown>>>(
          `/gatherings/${id}/booking-options`,
        ),
      bookingPlan: (id: string, optionToken: string, key?: string) =>
        client.post<Gathering>(
          `/gatherings/${id}/booking-plan`,
          { option_token: optionToken },
          { idempotencyKey: key },
        ),
      report: (
        id: string,
        body: { reported_user_id?: string; reason: string; block?: boolean },
        key?: string,
      ) =>
        client.post(`/gatherings/${id}/report`, body, { idempotencyKey: key }),
      share: (id: string) =>
        client.post<{ share_token?: string; url?: string }>(
          `/gatherings/${id}/share`,
          {},
        ),
      shareLanding: (token: string) =>
        client.get<Record<string, unknown>>(`/shares/g/${token}`, {
          auth: false,
        }),
      /** C4 落地页加入 — joined_via="share"，与普通 join 区分 */
      shareJoin: (token: string, key?: string) =>
        client.post<Gathering>(`/shares/g/${token}/join`, {}, {
          idempotencyKey: key,
        }),
    },
    actions: {
      preview: (body: Record<string, unknown>) =>
        client.post<CampusAction>("/actions/preview", body),
      get: (actionId: string) =>
        client.get<CampusAction>(`/actions/${actionId}`),
      execute: (body: Record<string, unknown>, key?: string) =>
        client.post<CampusAction>("/actions/execute", body, {
          idempotencyKey: key,
        }),
      /** 核对无误，分别确认（authorized 恒为 true，对齐 iOS） */
      authorize: (actionId: string, snapshotHash: string, key?: string) =>
        client.post<CampusAction>(
          `/actions/${actionId}/authorization`,
          { authorized: true, snapshot_hash: snapshotHash },
          { idempotencyKey: key },
        ),
      /** 提议修改预览（reason ≥ 5 字，仅变更字段进 proposed_params） */
      proposeModification: (
        actionId: string,
        body: {
          snapshot_hash: string;
          reason: string;
          proposed_params?: Record<string, unknown>;
        },
        key?: string,
      ) =>
        client.post<CampusAction>(
          `/actions/${actionId}/propose-modification`,
          body,
          { idempotencyKey: key },
        ),
    },
    hermes: {
      ask: (text: string, context?: Record<string, unknown>) =>
        client.post<{
          kind?: string;
          card_type?: string;
          data?: {
            message?: string;
            peers?: Array<{
              user_id: string;
              display_name: string;
              persona_label?: string | null;
              reason: string;
              overlap: string;
            }>;
          };
          answer?: string;
          text?: string;
          message?: string;
        }>("/hermes/ask", { text, context }),
      startPeerChat: (body: {
        peer_user_id: string;
        reason?: string;
        overlap?: string;
      }) =>
        client.post<{ channel_id: string; gathering_id: string }>(
          "/hermes/peers/start",
          body,
          { idempotencyKey: `hermes-peer-${body.peer_user_id}` },
        ),
    },
    channels: {
      messages: (channelId: string) =>
        client.get<MessagePayload[] | { items: MessagePayload[] }>(
          `/channels/${channelId}/messages`,
        ),
      send: (channelId: string, body: MessageCreate, key?: string) =>
        client.post<MessagePayload>(`/channels/${channelId}/messages`, body, {
          idempotencyKey: key,
        }),
      scenePolicy: (channelId: string) =>
        client.get<ChannelScenePolicy>(`/channels/${channelId}/scene-policy`),
      /** 草稿含 @Lulu 时走这里；服务端回 azou 消息 + action_hint */
      mentionAzou: (channelId: string, text: string, key?: string) =>
        client.post<MentionAzouResult>(
          `/channels/${channelId}/mention-azou`,
          { text },
          { idempotencyKey: key ?? `mention-${channelId}-${crypto.randomUUID()}` },
        ),
    },
    media: {
      /** POST /media/images — raw body 上传（非 multipart） */
      uploadImage: (
        data: Blob,
        opts: { filename?: string; contentType?: string; width?: number; height?: number } = {},
      ) => client.uploadImage(data, opts),
    },
    relations: {
      list: () =>
        client.get<RelationSummary[] | { items: RelationSummary[] }>(
          "/relations",
        ),
      get: (id: string) => client.get<RelationSummary>(`/relations/${id}`),
      dissolve: (id: string) => client.delete(`/relations/${id}`),
      /** 从搭子关系一键复局，返回新局 id */
      recur: (id: string, key?: string) =>
        client.post<{ gathering_id: string }>(
          `/relations/${id}/recur`,
          {},
          { idempotencyKey: key },
        ),
      goals: (relationId: string) =>
        client.get<SharedGoal[] | { items: SharedGoal[] }>(
          `/relations/${relationId}/goals`,
        ),
      createGoal: (
        relationId: string,
        body: {
          definition: string;
          period_start: string;
          period_end: string;
          target_value: number;
          unit: string;
        },
        key?: string,
      ) =>
        client.post<SharedGoal>(`/relations/${relationId}/goals`, body, {
          idempotencyKey: key,
        }),
      /** 只更新双方可见的下一步，不改事实进度 */
      updateGoal: (goalId: string, nextAction: string, key?: string) =>
        client.patch<SharedGoal>(
          `/goals/${goalId}`,
          { next_action: nextAction },
          { idempotencyKey: key },
        ),
    },
    profile: {
      me: () => client.get<AuthMe>("/auth/me"),
      trust: () => client.get<TrustMe>("/trust/me"),
      /** M2 · 画像编辑：GET /profile/me（写入走 updateProfileTags，后端无 PATCH /profile/me） */
      profileMe: () => client.get<UserProfile>("/profile/me"),
      updateProfileTags: (
        tags: string[],
        hiddenVerifiedTags: string[] = [],
        key?: string,
      ) =>
        client.patch<UserProfile>(
          "/profile/tags",
          { tags, hidden_verified_tags: hiddenVerifiedTags },
          { idempotencyKey: key ?? "profile-tags-full-state" },
        ),
      privacy: () => client.get<SocialPreferences>("/me/privacy"),
      patchPrivacy: (body: Record<string, unknown>, key?: string) =>
        client.patch<SocialPreferences>("/me/privacy", body, {
          idempotencyKey: key ?? "privacy-full-state",
        }),
      matchingPreferences: () =>
        client.get<MatchingPreferences>("/me/matching-preferences"),
      patchMatchingPreferences: (
        body: Partial<MatchingPreferences>,
        key?: string,
      ) =>
        client.patch<MatchingPreferences>("/me/matching-preferences", body, {
          idempotencyKey: key ?? "matching-preferences-full-state",
        }),
      notificationPreferences: () =>
        client.get<NotificationPreferences>("/me/notification-preferences"),
      listNotifications: (limit = 50, category?: string) =>
        client.get<InboxNotification[]>("/notifications", {
          query: { limit, category },
        }),
      patchNotificationPreferences: (
        body: Record<string, unknown>,
        key?: string,
      ) =>
        client.patch<NotificationPreferences>(
          "/me/notification-preferences",
          body,
          { idempotencyKey: key ?? "notification-preferences-full-state" },
        ),
      blocks: () => client.get<BlockEntry[]>("/me/blocks"),
      unblock: (blockedUserId: string, key?: string) =>
        client.delete<{ blocked_user_id?: string; blocked?: boolean }>(
          `/me/blocks/${blockedUserId}`,
          { idempotencyKey: key ?? `unblock-${blockedUserId}` },
        ),
      appeals: () => client.get<TrustAppeal[]>("/trust/appeals"),
      appeal: (appealId: string) =>
        client.get<TrustAppeal>(`/trust/appeals/${appealId}`),
      submitAppeal: (reason: string, key?: string) =>
        client.post<TrustAppeal>(
          "/trust/appeal",
          { reason },
          { idempotencyKey: key ?? `appeal-${crypto.randomUUID()}` },
        ),
      dataExport: () => client.get<Record<string, unknown>>("/me/data-export"),
      deleteAccount: (key?: string) =>
        client.request<{ status?: string }>("/me/account", {
          method: "DELETE",
          body: { confirmation: "DELETE" },
          idempotencyKey: key ?? "account-delete",
        }),
      /** 学期回忆录 */
      recap: () => client.get<SemesterRecap>("/me/recap"),
    },
    auth: {
      /** 手机号+密码注册（暂不需要短信验证码）。 */
      registerPhone: (body: {
        phone: string;
        password: string;
        display_name?: string;
      }) => client.post<PhoneAuthResult>("/auth/register", body, { auth: false }),
      /** 手机号+密码登录。 */
      loginPhone: (body: { phone: string; password: string }) =>
        client.post<PhoneAuthResult>("/auth/login", body, { auth: false }),
      /** Create login session; redemption_token is one-shot and only on create. */
      startSession: (body: {
        device_install_id?: string;
        resume_user_id?: string | null;
      } = {}) =>
        client.post<LoginSession>(
          "/auth/session",
          {
            device_install_id: body.device_install_id ?? getOrCreateDeviceInstallId(),
            resume_user_id: body.resume_user_id ?? null,
          },
          { auth: false },
        ),
      /** Poll status / refreshed QR; requires X-Login-Redemption (iOS parity). */
      pollSession: (sessionId: string, redemptionToken: string) =>
        client.get<LoginSession>(`/auth/session/${sessionId}`, {
          auth: false,
          headers: { "X-Login-Redemption": redemptionToken },
        }),
      redeem: (sessionId: string, redemptionToken: string, key?: string) =>
        client.post<AuthRedeemResult>(
          `/auth/session/${sessionId}/redeem`,
          { redemption_token: redemptionToken },
          {
            auth: false,
            idempotencyKey: key ?? `login-redeem-${sessionId}`,
          },
        ),
      /** Debug-only when backend DEV_AUTH / demo-complete is enabled. */
      demoComplete: (sessionId: string, redemptionToken: string) =>
        client.post(
          `/auth/session/${sessionId}/demo-complete`,
          {},
          {
            auth: false,
            headers: { "X-Login-Redemption": redemptionToken },
          },
        ),
      /** One scope per call — same as iOS setGrant. */
      setGrant: (scope: GrantScope, granted: boolean, key?: string) =>
        client.post(
          "/auth/grants",
          { scope, granted },
          { idempotencyKey: key ?? `grant-${scope}-${granted}` },
        ),
      setSocialEnabled: (enabled: boolean, key?: string) =>
        client.patch(
          "/me/privacy",
          {
            social_enabled: enabled,
            course_matching_enabled: enabled,
            identity_disclosure: "after_confirmed",
          },
          { idempotencyKey: key ?? `first-use-social-${enabled ? "on" : "off"}` },
        ),
      me: () => client.get<AuthMe>("/auth/me"),
    },
    organizer: {
      list: () =>
        client.get<
          OrganizerGatheringSummary[] | { items: OrganizerGatheringSummary[] }
        >("/organizer/gatherings"),
      create: (body: Record<string, unknown>, key?: string) =>
        client.post<{ id: string; status?: string; is_official?: boolean }>(
          "/organizer/gatherings",
          body,
          { idempotencyKey: key },
        ),
      dashboard: (id: string) =>
        client.get<OrganizerDashboard>(
          `/organizer/gatherings/${id}/dashboard`,
        ),
      closeRegistration: (id: string, key?: string) =>
        client.post<{ id?: string; status?: string }>(
          `/organizer/gatherings/${id}/close-registration`,
          {},
          { idempotencyKey: key },
        ),
      finalize: (id: string, key?: string) =>
        client.post<{ id?: string; status?: string }>(
          `/organizer/gatherings/${id}/finalize`,
          {},
          { idempotencyKey: key },
        ),
      markAttendance: (id: string, participantId: string, key?: string) =>
        client.post<{ user_id?: string; attended?: boolean }>(
          `/organizer/gatherings/${id}/attendance/${participantId}`,
          {},
          { idempotencyKey: key },
        ),
      templates: () =>
        client.get<OrganizerTemplate[] | { items: OrganizerTemplate[] }>(
          "/organizer/templates",
        ),
      createTemplate: (body: Record<string, unknown>, key?: string) =>
        client.post<OrganizerTemplate>("/organizer/templates", body, {
          idempotencyKey: key,
        }),
      patchTemplate: (
        templateId: string,
        body: Record<string, unknown>,
        key?: string,
      ) =>
        client.patch<OrganizerTemplate>(
          `/organizer/templates/${templateId}`,
          body,
          { idempotencyKey: key },
        ),
      deactivateTemplate: (templateId: string, key?: string) =>
        client.delete<OrganizerTemplate>(
          `/organizer/templates/${templateId}`,
          { idempotencyKey: key },
        ),
      copyTemplate: (templateId: string, title?: string, key?: string) =>
        client.post<OrganizerTemplate>(
          `/organizer/templates/${templateId}/copy`,
          title ? { title } : {},
          { idempotencyKey: key },
        ),
      instantiateTemplate: (
        templateId: string,
        body: { start_at: string; quota_batches?: Array<Record<string, unknown>> },
        key?: string,
      ) =>
        client.post<{ id: string; status?: string; is_official?: boolean }>(
          `/organizer/templates/${templateId}/instantiate`,
          body,
          { idempotencyKey: key },
        ),
    },
    taste: {
      me: () => client.get<TasteProfileResult | null>("/profile/taste/me"),
      fromLink: (body: {
        share_url: string;
        likes_limit?: number;
        posts_limit?: number;
        collects_limit?: number;
        use_llm?: boolean;
        force?: boolean;
      }) =>
        client.post<TasteImportSession>(
          "/profile/taste/from-link",
          {
            likes_limit: 30,
            posts_limit: 20,
            collects_limit: 30,
            use_llm: true,
            force: true,
            ...body,
          },
          { timeoutMs: 120_000 },
        ),
      importDouyin: (body: Record<string, unknown>) =>
        client.post("/profile/imports/douyin", body),
      /** 创建导入任务并等待新鲜二维码（最长 waitSeconds 秒）。 */
      createDouyinQR: (
        body: { max_items?: number; force?: boolean } = {},
        waitSeconds = 10,
      ) =>
        client.post<TasteQRLogin>("/profile/imports/douyin/qr", body, {
          query: { wait_seconds: waitSeconds },
        }),
      importStatus: (importId: string) =>
        client.get<TasteImportSession>(`/profile/imports/${importId}`),
      refreshDouyinQR: (importId: string) =>
        client.post<TasteImportSession>(
          `/profile/imports/${importId}/qr/refresh`,
          {},
        ),
      cancelDouyinImport: (importId: string) =>
        client.post<TasteImportSession>(
          `/profile/imports/${importId}/cancel`,
          {},
        ),
      aiRefresh: () =>
        client.post<TasteProfileResult>("/profile/taste/me/ai-refresh", {}),
      deleteDouyinProfile: () =>
        client.delete<Record<string, unknown>>("/profile/taste/me/douyin"),
      /* 手机号验证登录（挂在 import_id 下，对齐 iOS TasteImportView） */
      phoneCode: (importId: string, phone: string, countryCode = "86") =>
        client.post<PhoneLoginState>(
          `/profile/imports/${importId}/phone/code`,
          { phone, country_code: countryCode },
        ),
      phoneStatus: (importId: string) =>
        client.get<PhoneLoginState>(`/profile/imports/${importId}/phone`),
      phoneVerify: (importId: string, code: string) =>
        client.post<PhoneLoginState>(
          `/profile/imports/${importId}/phone/verify`,
          { code },
        ),
      verifyLogin: (importId: string, waitSeconds = 2) =>
        client.post<{
          import_id?: string;
          status?: string;
          verified?: boolean;
          authenticated_at?: string | null;
          source_profile?: TasteSourceProfile | null;
          next?: string;
          error?: TasteImportError | null;
        }>(`/profile/imports/${importId}/verify`, {}, {
          query: { wait_seconds: waitSeconds },
        }),
      questions: (importId: string) =>
        client.get<TasteQuestions>(`/profile/imports/${importId}/questions`),
      submitAnswers: (
        importId: string,
        answers: Array<{ question_id: string; option_id: string }>,
      ) =>
        client.post<TasteProfileResult>(
          `/profile/imports/${importId}/answers`,
          { answers },
        ),
    },
    campus: {
      timetable: (week?: number) =>
        client.get<Record<string, unknown> | unknown[]>("/schedule/timetable", {
          query:
            week != null
              ? { week: Math.min(30, Math.max(1, week)) }
              : undefined,
        }),
      /** 202 accepted → 稍候再拉 timetable（meta.poll） */
      refreshSchedule: () =>
        client.post<{ status?: string }>("/schedule/refresh", {}, {
          idempotencyKey: "schedule-refresh",
        }),
      course: (id: string) =>
        client.get<Record<string, unknown>>(`/schedule/courses/${id}`),
      assignments: (status = "unfinished") =>
        client.get<unknown[] | { items: unknown[] }>("/assignments", {
          query: { status },
        }),
      assignment: (id: string) =>
        client.get<Record<string, unknown>>(`/assignments/${id}`),
      gymAvailable: () =>
        client.get<unknown[] | { items: unknown[] }>("/venues/gym/available"),
      roomAvailable: () =>
        client.get<unknown[] | { items: unknown[] }>("/venues/room/available"),
      events: () =>
        client.get<unknown[] | { items: unknown[] }>("/events"),
      event: (id: string) =>
        client.get<Record<string, unknown>>(`/events/${id}`),
    },
  };
}

export type Repositories = ReturnType<typeof createRepositories>;

/** Normalize list-or-wrapped list payloads from FastAPI. */
export function asList<T>(payload: T[] | { items?: T[] } | null | undefined): T[] {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.items)) return payload.items;
  return [];
}
