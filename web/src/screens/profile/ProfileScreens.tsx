import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import type {
  AuthMe,
  BlockEntry,
  GrantScope,
  InboxNotification,
  MatchingPreferences,
  NotificationPreferences,
  ProfileCapability,
  SemesterRecap,
  SocialPreferences,
  TasteProfileSummary,
  TrustAppeal,
  TrustCondition,
  TrustLevelGuideItem,
  TrustMe,
  UserProfile,
} from "../../core/api/repositories";
import {
  Btn,
  Card,
  Chip,
  Icon,
  LuluMark,
  NavBar,
  Note,
  PageHeader,
  Progress,
  Row,
  Screen,
  Scroll,
  Section,
  Seg,
  StateView,
  Stepper,
  Sticker,
  Switch,
} from "../../components/ui/primitives";
import { resetAuthOnboardingLocal } from "../auth/AuthScreens";
import { appHref } from "../../core/assets";
import {
  categoryEnabled,
  categoryLabel,
  notificationSummary,
  pathFromNotification,
  relativeTimeLabel,
} from "./notificationInbox";

/* ---------- M1 个人中心 ---------- */

export function ProfileScreen() {
  const { repos, session } = useApp();
  const nav = useNavigate();
  const [me, setMe] = useState<AuthMe | null>(null);
  const [taste, setTaste] = useState<TasteProfileSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [facts, profile] = await Promise.all([
          repos.profile.me(),
          repos.profile.profileMe().catch(() => null),
        ]);
        if (!cancelled) {
          setMe(facts);
          setTaste(profile?.taste_profile ?? null);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [repos]);

  const hasTaste =
    taste != null && (taste.primary_tag != null || Boolean(taste.summary));
  const tasteTagsLine = (() => {
    if (!taste) return null;
    if (taste.interest_tags?.length)
      return taste.interest_tags.slice(0, 5).join(" · ");
    if (taste.secondary_tags?.length)
      return taste.secondary_tags.slice(0, 4).join(" · ");
    return null;
  })();

  return (
    <Screen id="screen-M1-profile">
      <Scroll>
        <PageHeader eyebrow="噜噜成局 · 我" />
        {loading ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : error ? (
          <Card>
            <StateView kind="network" message={error} />
          </Card>
        ) : (
          <Card
            onClick={() => nav("/me/nickname")}
            data-od-id="profile-edit-display-name"
          >
            <div className="flex" style={{ gap: 14, alignItems: "center" }}>
              <div className="profile-identity-mark">
                <LuluMark placement="avatar" clip="home.idle" />
              </div>
              <div className="grow">
                <div className="t-t2">{me?.display_name ?? "已认证同学"}</div>
                <div className="t-foot mt-1">
                  {[me?.campus, me?.major].filter(Boolean).join(" · ")}
                </div>
                <div className="t-cap mt-1">修改昵称</div>
              </div>
              <span className="chevron">›</span>
            </div>
          </Card>
        )}

        {hasTaste ? (
          <>
            <Section title="我的兴趣画像" />
            <Card id="profile-taste-summary">
              {taste?.primary_tag ? (
                <div className="t-call" style={{ fontWeight: 700 }}>
                  {taste.primary_tag.label ?? taste.primary_tag.key}
                </div>
              ) : null}
              {tasteTagsLine ? (
                <div className="t-foot mt-2" style={{ color: "var(--mist)" }}>
                  {tasteTagsLine}
                </div>
              ) : null}
              {taste?.summary ? (
                <div className="t-foot mt-2">{taste.summary}</div>
              ) : null}
              <Btn kind="ghost" sm to="/me/taste">
                管理 / 刷新画像
              </Btn>
            </Card>
          </>
        ) : null}

        <Section title="局与关系" />
        <Card tight>
          <Row
            icon={<Sticker name="table-people.png" size="st-24" />}
            title="我的局"
            to="/gatherings/mine"
          />
          <Row
            icon={<Sticker name="handshake.png" size="st-24" />}
            title="搭子关系"
            to="/relations"
          />
          <Row
            icon={<Sticker name="table-plus.png" size="st-24" />}
            title="直接发起局"
            to="/gatherings/initiate"
          />
          <Row
            icon={<Sticker name="trophy.png" size="st-24" />}
            title="学期回忆录"
            to="/me/recap"
          />
        </Card>

        <Section title="画像与信任" />
        <Card tight>
          <Row
            icon={<Sticker name="id-card.png" size="st-24" />}
            title="画像与能力"
            to="/me/profile"
          />
          <Row
            icon={<Sticker name="medal.png" size="st-24" />}
            title="信任进度"
            to="/me/trust"
          />
          <Row
            icon={<Sticker name="key.png" size="st-24" />}
            title="授权管理"
            to="/me/grants"
          />
          <Row
            icon={<Sticker name="sparkle-wand.png" size="st-24" />}
            title="抖音兴趣画像"
            sub="粘贴主页链接即可，不用扫码"
            to="/me/taste"
          />
        </Card>

        <Section title="隐私与安全" />
        <Card tight>
          <Row
            icon={<Sticker name="shield-check.png" size="st-24" />}
            title="隐私与安全"
            to="/me/privacy"
          />
          <Row
            icon={<Sticker name="sliders.png" size="st-24" />}
            title="匹配偏好"
            to="/me/preferences"
          />
          <Row
            icon={<Sticker name="block-sign.png" size="st-24" />}
            title="黑名单"
            to="/me/blocks"
          />
          <Row
            icon={<Sticker name="flag.png" size="st-24" />}
            title="历史局安全与举报"
            to="/me/safety-history"
          />
          <Row
            icon={<Sticker name="megaphone.png" size="st-24" />}
            title="信任申诉"
            to="/me/appeals"
          />
        </Card>

        <Section title="偏好与数据" />
        <Card tight>
          <Row
            icon={<Sticker name="bell.png" size="st-24" />}
            title="通知与日历"
            to="/me/notifications"
          />
          <Row
            icon={<Sticker name="clipboard-whistle.png" size="st-24" />}
            title="主理人控制台"
            to="/organizer"
          />
          <Row
            icon={<Sticker name="box-export.png" size="st-24" />}
            title="数据导出与注销"
            to="/me/account"
          />
          <Row
            icon={<Icon name="spark" size={20} />}
            title="重新查看新手引导"
            onClick={() => {
              resetAuthOnboardingLocal();
              window.location.href = appHref("/onboarding");
            }}
          />
        </Card>

        <Card tight>
          <Row
            icon={<Icon name="exit" size={20} />}
            title="退出登录"
            onClick={() => {
              session.clear();
              window.location.href = appHref("/auth");
            }}
          />
        </Card>
      </Scroll>
    </Screen>
  );
}

/* ---------- 修改昵称 ---------- */

export function DisplayNameScreen() {
  const { repos, session } = useApp();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await repos.profile.me();
        if (!cancelled) {
          setName(me.display_name ?? "");
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [repos]);

  const trimmed = name.trim();
  const canSave = trimmed.length >= 1 && trimmed.length <= 20 && !saving;

  async function save() {
    if (!canSave) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await repos.profile.updateDisplayName(trimmed);
      const state = session.getState();
      if (state.status === "authenticated") {
        session.setSession(state.token, {
          ...state.user,
          display_name: updated.display_name ?? trimmed,
          user_id: updated.user_id,
        });
      }
      nav("/me", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SettingsScaffold id="screen-display-name-editor" title="修改昵称">
      {loading ? (
        <Card>
          <StateView kind="loading" />
        </Card>
      ) : (
        <>
          <Card>
            <div className="t-foot">这个名字会出现在消息、局和搭子里</div>
            <label className="t-cap mt-3" htmlFor="display-name-field" style={{ display: "block" }}>
              昵称
            </label>
            <input
              id="display-name-field"
              className="om-input mt-1"
              type="text"
              maxLength={20}
              placeholder="1–20 个字"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void save();
              }}
            />
            <div className="t-cap mt-1" style={{ textAlign: "right" }}>
              {trimmed.length}/20
            </div>
          </Card>
          {error ? (
            <Card>
              <StateView kind="network" message={error} />
            </Card>
          ) : null}
          <Btn kind="primary" disabled={!canSave} onClick={() => void save()}>
            {saving ? "保存中…" : "保存昵称"}
          </Btn>
        </>
      )}
    </SettingsScaffold>
  );
}

/* ---------- 公共：设置页骨架 ---------- */

function SettingsScaffold({
  id,
  title,
  eyebrow,
  backTo = "/me",
  children,
}: {
  id: string;
  title: string;
  eyebrow?: string;
  backTo?: string;
  children: ReactNode;
}) {
  return (
    <Screen id={id}>
      <NavBar backTo={backTo} />
      <Scroll>
        <PageHeader eyebrow={eyebrow} title={title} />
        {children}
      </Scroll>
    </Screen>
  );
}

function ErrorCard({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <Card>
      <div className="t-foot">{message}</div>
    </Card>
  );
}

/* ---------- M2 画像与能力（GET /profile/me + PATCH /profile/tags） ---------- */

function identityValue(
  identity: Record<string, unknown> | undefined,
  key: string,
): string {
  const v = identity?.[key];
  if (typeof v === "string" && v.trim()) return v;
  if (typeof v === "number") return String(v);
  return "未提供";
}

function capabilityKey(
  cap: string | { key?: string; label?: string },
): string {
  return typeof cap === "string" ? cap : cap.key ?? "";
}

function capabilityLabel(
  cap: string | { key?: string; label?: string },
): string {
  return typeof cap === "string" ? cap : cap.label ?? cap.key ?? "";
}

export function ProfileEditorScreen() {
  const { repos } = useApp();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [hiddenVerified, setHiddenVerified] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  function apply(p: UserProfile) {
    setProfile(p);
    const caps = p.capabilities ?? [];
    setSelected(
      new Set(
        caps
          .filter((c) => c.source === "self_reported" && c.key)
          .map((c) => c.key!),
      ),
    );
    setHiddenVerified(
      new Set(
        caps
          .filter((c) => c.source === "verified" && c.hidden && c.key)
          .map((c) => c.key!),
      ),
    );
  }

  async function load() {
    setLoading(true);
    try {
      apply(await repos.profile.profileMe());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  async function save() {
    setSaving(true);
    setResultMessage(null);
    try {
      const updated = await repos.profile.updateProfileTags(
        Array.from(selected).sort(),
        Array.from(hiddenVerified).sort(),
      );
      apply(updated);
      setResultMessage(
        "画像设置已保存；能力标签与兴趣画像会用于匹配，成局后成员可见兴趣 chips。",
      );
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  const verified = (profile?.capabilities ?? []).filter(
    (c): c is ProfileCapability & { key: string } =>
      c.source === "verified" && !!c.key,
  );
  const verifiedKeys = new Set(verified.map((c) => c.key));
  const availableSelfReported = (profile?.available_capabilities ?? []).filter(
    (c) => !verifiedKeys.has(capabilityKey(c)),
  );

  return (
    <SettingsScaffold id="screen-M2-profile-editor" title="画像与能力">
      {loading ? (
        <Card>
          <StateView kind="loading" />
        </Card>
      ) : error && !profile ? (
        <Card>
          <StateView kind="network" message={error} actionTitle="重试" onAction={() => void load()} />
        </Card>
      ) : (
        <>
          <Card>
            <div className="t-t3">校方认证事实</div>
            <div className="mt-2">
              {[
                ["学院", "college"],
                ["专业", "major"],
                ["年级", "grade_year"],
                ["校区", "campus"],
              ].map(([label, key]) => (
                <div className="between mt-1" key={key}>
                  <span className="t-foot">{label}</span>
                  <span className="t-call">
                    {identityValue(profile?.identity, key!)}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <div className="t-t3">认证能力</div>
            {verified.length === 0 ? (
              <div className="t-foot mt-2">暂无认证能力标签</div>
            ) : (
              verified.map((cap) => (
                <div className="between mt-2" key={cap.key}>
                  <span>
                    <div className="t-call">{cap.label ?? cap.key}</div>
                    <div className="t-cap">
                      校方认证
                      {typeof cap.weight === "number"
                        ? ` · 权重 ${cap.weight.toFixed(1)}`
                        : ""}
                    </div>
                  </span>
                  <Switch
                    on={!hiddenVerified.has(cap.key)}
                    onChange={(visible) => {
                      setHiddenVerified((prev) => {
                        const next = new Set(prev);
                        if (visible) next.delete(cap.key);
                        else next.add(cap.key);
                        return next;
                      });
                    }}
                  />
                </div>
              ))
            )}
          </Card>

          <Card>
            <div className="t-t3">自述能力</div>
            {availableSelfReported.length === 0 ? (
              <div className="t-foot mt-2">暂无可选能力标签</div>
            ) : (
              <div className="flex wrap mt-2">
                {availableSelfReported.map((cap) => {
                  const key = capabilityKey(cap);
                  const on = selected.has(key);
                  const full = !on && selected.size >= 30;
                  return (
                    <Chip
                      key={key}
                      kind={on ? "gap" : "soft"}
                      onClick={
                        full
                          ? undefined
                          : () =>
                              setSelected((prev) => {
                                const next = new Set(prev);
                                if (next.has(key)) next.delete(key);
                                else next.add(key);
                                return next;
                              })
                      }
                    >
                      {on ? "✓ " : ""}
                      {capabilityLabel(cap)}
                    </Chip>
                  );
                })}
              </div>
            )}
            <div className="t-cap mt-2">最多选 30 个；成局后成员可见。</div>
          </Card>

          <ErrorCard message={error} />
          {resultMessage ? (
            <Card>
              <div className="t-foot">{resultMessage}</div>
            </Card>
          ) : null}
          <Btn kind="primary" disabled={saving} onClick={() => void save()}>
            {saving ? "保存中…" : "保存画像设置"}
          </Btn>
        </>
      )}
    </SettingsScaffold>
  );
}

/* ---------- M3 信任进度 ---------- */

function conditionRatio(condition: TrustCondition): number {
  const { current, required } = condition;
  if (current == null || required == null || required <= 0) {
    return condition.met ? 1 : 0;
  }
  if (condition.key === "late_exit_rate" || condition.label.includes("越低越好")) {
    return condition.met ? 1 : Math.max(0, 1 - Math.min(1, current / required));
  }
  return condition.met ? 1 : Math.min(1, current / required);
}

function conditionMetricText(condition: TrustCondition): string {
  const { current, required, unit } = condition;
  if (current == null || required == null || !unit) {
    return condition.met ? "已完成" : condition.detail ?? "未完成";
  }
  const fmt = (v: number) =>
    Number.isInteger(v) ? `${v}` : v.toFixed(1);
  if (unit === "%") {
    if (condition.key === "late_exit_rate" || condition.label.includes("越低越好")) {
      return `${fmt(current)}% / 低于 ${fmt(required)}%`;
    }
    return `${fmt(current)}% / ${fmt(required)}%`;
  }
  return `${fmt(current)} / ${fmt(required)} ${unit}`;
}

function conditionHasMetric(condition: TrustCondition): boolean {
  return (
    condition.required != null &&
    condition.required > 0 &&
    condition.unit != null &&
    condition.unit !== "" &&
    condition.current != null
  );
}

/** Prefer structured conditions; fall back to gaps for older payloads. */
function displayConditions(trust: TrustMe): TrustCondition[] {
  if (trust.conditions?.length) return trust.conditions;
  if (trust.next_level_progress?.length) {
    return trust.next_level_progress.map((metric) => ({
      key: metric.key,
      label: metric.label,
      met: metric.current >= metric.required,
      current: metric.current,
      required: metric.required,
      unit: metric.unit,
      detail:
        metric.current >= metric.required
          ? null
          : `还差 ${Math.max(0, Math.round(metric.required - metric.current))} ${metric.unit}`,
    }));
  }
  return (trust.gaps ?? []).map((gap, index) => ({
    key: `gap-${index}`,
    label: gap,
    met: false,
    detail: gap,
  }));
}

function overallCaption(trust: TrustMe): string {
  const conditions = trust.conditions ?? [];
  const remaining = conditions.filter((c) => !c.met).length;
  if (remaining === 0 && conditions.length > 0) {
    return "条件已齐，刷新后由服务端确认升级";
  }
  if (remaining > 0) return `还差 ${remaining} 项条件`;
  if (trust.gaps?.length) return trust.gaps[0];
  return "按履约事实自动计算，无需申请";
}

const FALLBACK_LEVEL_GUIDE: TrustLevelGuideItem[] = [
  { level: "T0", name: "访客", how: "下载 App 即可进入", benefits: ["浏览公开内容与校园资讯"] },
  {
    level: "T1",
    name: "已认证同学",
    how: "完成统一身份认证与画像初始化",
    benefits: ["参加 3 人及以上的低风险公开局", "创建意图卡", "同课破冰、DDL 冲刺"],
  },
  {
    level: "T2",
    name: "靠谱同学",
    how: "完成 3 次有效成局 · 准时确认率 ≥ 80% · 近 30 天无临期爽约 · 无有效举报",
    benefits: ["比赛 / 项目组队池", "自行发起公开局", "双人局与跨院系匹配", "校园预约代理"],
  },
  {
    level: "T3",
    name: "组局者",
    how: "累计 10 次有效成局 · ≥ 3 次本人发起 · 复局 ≥ 2 次 · 爽约率 < 10%",
    benefits: ["长期共同目标", "周期性固定局", "6 人以上大组", "补位快线"],
  },
  {
    level: "T4",
    name: "校园主理人",
    how: "经社团 / 院系 / 平台核验的主理人认证",
    benefits: ["官方局", "主理人管理台与模板"],
  },
];

function levelRank(level: string): number {
  const n = Number(level.slice(1));
  return Number.isFinite(n) ? n : -1;
}

function TrustBenefitsCard({
  title,
  benefits,
  muted,
  id,
}: {
  title: string;
  benefits: string[];
  muted: boolean;
  id?: string;
}) {
  return (
    <>
      <Section title={title} />
      <Card id={id}>
        {benefits.map((benefit, index) => (
          <div
            key={index}
            className="flex"
            style={{
              gap: 8,
              alignItems: "flex-start",
              marginTop: index === 0 ? 0 : 8,
            }}
          >
            <span style={{ color: muted ? "var(--sage)" : "var(--ink)" }}>
              {muted ? "○" : "✦"}
            </span>
            <span
              className="t-call"
              style={{ color: muted ? "var(--mist)" : "var(--ink)" }}
            >
              {benefit}
            </span>
          </div>
        ))}
      </Card>
    </>
  );
}

/** 升级说明：完整 T0–T4 达标标准与权益 */
function TrustLevelGuide({
  guide,
  currentLevel,
}: {
  guide: TrustLevelGuideItem[];
  currentLevel?: string;
}) {
  const current = currentLevel ?? "T0";
  const items = guide.length
    ? guide
    : FALLBACK_LEVEL_GUIDE.map((item) => ({
        ...item,
        is_current: item.level === current,
        is_reached: levelRank(item.level) <= levelRank(current),
      }));
  return (
    <div data-od-id="sheet-trust-level-guide">
      <Section title="T0–T4 标准说明" />
      {items.map((item) => (
        <Card key={item.level} id={`trust-guide-${item.level}`}>
          <div className="flex" style={{ gap: 12, alignItems: "flex-start" }}>
            <span style={{ opacity: item.is_reached ? 1 : 0.45 }}>
              <Sticker name="badge.png" size="st-44" />
            </span>
            <div style={{ flex: 1 }}>
              <div className="flex" style={{ gap: 6, alignItems: "baseline" }}>
                <span
                  className="mono t-foot"
                  style={{
                    fontWeight: 700,
                    color: item.is_current ? "var(--ink)" : "var(--sage)",
                  }}
                >
                  {item.level}
                </span>
                <span className="t-t3">{item.name}</span>
                {item.is_current ? <Chip kind="solid">当前</Chip> : null}
              </div>
              <div className="t-foot mt-1">如何达到：{item.how}</div>
              {(item.benefits ?? []).map((benefit, i) => (
                <div key={i} className="flex mt-1" style={{ gap: 6 }}>
                  <span style={{ color: "var(--sage)" }}>·</span>
                  <span className="t-foot" style={{ color: "var(--ink)" }}>
                    {benefit}
                  </span>
                </div>
              ))}
            </div>
            <span style={{ color: item.is_reached ? "var(--ink)" : "var(--sage)" }}>
              {item.is_reached ? "✓" : "🔒"}
            </span>
          </div>
        </Card>
      ))}
    </div>
  );
}

export function TrustScreen() {
  const { repos } = useApp();
  const [trust, setTrust] = useState<TrustMe | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showGuide, setShowGuide] = useState(false);

  async function load() {
    if (loading) return;
    setLoading(true);
    try {
      setTrust(await repos.profile.trust());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  const conditions = trust ? displayConditions(trust) : [];
  const overall = trust?.overall_progress ?? 0;

  return (
    <Screen id="screen-M3-trust">
      <NavBar backTo="/me" />
      <Scroll>
        <PageHeader eyebrow="信任等级" title="信任进度" />
        {!trust && !error ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : null}
        {!trust && error ? (
          <Card>
            <StateView
              kind="network"
              message={error}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : null}
        {trust ? (
          <>
            {/* Hero：等级 + 命名 + 叙事 */}
            <Card>
              <div className="flex" style={{ gap: 14, alignItems: "center" }}>
                <Sticker name="badge.png" size="st-56" />
                <div>
                  <div className="flex" style={{ gap: 8, alignItems: "baseline" }}>
                    <span
                      className="mono"
                      id="trust-current-level"
                      style={{ fontSize: 22, fontWeight: 800, color: "var(--ink)" }}
                    >
                      {trust.level ?? "T0"}
                    </span>
                    <span className="t-t2">{trust.level_name ?? ""}</span>
                  </div>
                  <div className="t-foot mt-1">
                    {trust.level_narrative ||
                      (trust.next_level
                        ? `下一等级 ${trust.next_level}${trust.next_level_name ? ` · ${trust.next_level_name}` : ""}`
                        : "当前最高等级")}
                  </div>
                </div>
              </div>
              {trust.observation && trust.observation["until"] != null ? (
                <>
                  <div className="divider" />
                  <div className="t-foot" data-od-id="trust-observation-banner">
                    观察期内等级暂时冻结，到期后按履约事实重新计算
                  </div>
                </>
              ) : null}
            </Card>

            {/* 升到下一级 / 已达最高 */}
            {trust.next_level ? (
              <>
                <Section title="升到下一级" />
                <Card id="trust-upgrade-card">
                  <div className="between">
                    <div>
                      <div className="t-call" style={{ fontWeight: 700 }}>
                        {trust.next_level} · {trust.next_level_name ?? trust.next_level}
                      </div>
                      <div className="t-foot mt-1">{overallCaption(trust)}</div>
                    </div>
                    <span
                      className="mono"
                      id="trust-overall-progress"
                      style={{ fontSize: 20, fontWeight: 800, color: "var(--ink)" }}
                    >
                      {Math.round(overall * 100)}%
                    </span>
                  </div>
                  <div className="mt-2">
                    <Progress value={overall * 100} />
                  </div>
                  {conditions.map((condition) => (
                    <div
                      key={condition.key}
                      className="mt-3"
                      data-od-id={`trust-condition-${condition.key}`}
                    >
                      <div className="between">
                        <span className="flex" style={{ gap: 8, alignItems: "baseline" }}>
                          <span
                            style={{
                              color: condition.met ? "var(--ink)" : "var(--sage)",
                            }}
                          >
                            {condition.met ? "●" : "○"}
                          </span>
                          <span className="t-call" style={{ fontWeight: 600 }}>
                            {condition.label}
                          </span>
                        </span>
                        <span
                          className="mono t-cap"
                          style={{
                            fontWeight: 700,
                            color: condition.met ? "var(--ink)" : "var(--mist)",
                          }}
                        >
                          {conditionMetricText(condition)}
                        </span>
                      </div>
                      {conditionHasMetric(condition) ? (
                        <div className="mt-1">
                          <Progress value={conditionRatio(condition) * 100} />
                        </div>
                      ) : !condition.met &&
                        condition.detail &&
                        condition.detail !== condition.label ? (
                        <div className="t-foot mt-1" style={{ paddingLeft: 23 }}>
                          {condition.detail}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </Card>
              </>
            ) : (
              <Card id="trust-max-level">
                <div className="flex" style={{ gap: 10, alignItems: "center" }}>
                  <Sticker name="trophy.png" size="st-44" />
                  <div>
                    <div className="t-t3">已达最高等级</div>
                    <div className="t-foot mt-1">T4 校园主理人权益已全部解锁。</div>
                  </div>
                </div>
              </Card>
            )}

            {trust.current_benefits?.length ? (
              <TrustBenefitsCard
                title="本级已解锁"
                benefits={trust.current_benefits}
                muted={false}
                id="trust-current-benefits"
              />
            ) : null}
            {trust.next_benefits?.length ? (
              <TrustBenefitsCard
                title={
                  trust.next_level_name
                    ? `升到 ${trust.next_level_name} 将解锁`
                    : "下一级将解锁"
                }
                benefits={trust.next_benefits}
                muted
                id="trust-next-benefits"
              />
            ) : null}

            {showGuide ? (
              <TrustLevelGuide
                guide={trust.level_guide ?? []}
                currentLevel={trust.level}
              />
            ) : null}
            <Btn
              kind="ghost"
              onClick={() => setShowGuide((v) => !v)}
              id="trust-open-guide"
            >
              {showGuide ? "收起升级说明" : "查看升级说明 · T0–T4 标准"}
            </Btn>
            <Btn kind="ghost" to="/me/appeals">
              查看信任申诉
            </Btn>
            <Btn kind="primary" to="/gatherings/open" id="trust-open-low-risk-gatherings">
              去看能马上参加的公开局
            </Btn>
            <Btn kind="text" sm onClick={() => void load()} disabled={loading}>
              {loading ? "正在刷新…" : "刷新信任进度"}
            </Btn>
          </>
        ) : null}
      </Scroll>
    </Screen>
  );
}

/* ---------- M4 授权管理（/auth/me grants + POST /auth/grants） ---------- */

const GRANT_ROWS: Array<{
  scope: GrantScope;
  title: string;
  sub: string;
  sticker: string;
}> = [
  { scope: "timetable", title: "课表", sub: "用于寻找空档", sticker: "books-stack.png" },
  { scope: "curriculum", title: "培养方案", sub: "用于能力标签", sticker: "notebook-open.png" },
  { scope: "enrollment", title: "选课记录", sub: "用于课程匹配", sticker: "desk-calendar.png" },
  { scope: "agent_booking", title: "代理执行", sub: "每次执行前仍需你确认", sticker: "approval-stamp.png" },
];

export function GrantsScreen() {
  const { repos } = useApp();
  const [granted, setGranted] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workingScope, setWorkingScope] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const me = await repos.profile.me();
      const map: Record<string, boolean> = {};
      for (const grant of me.grants ?? []) {
        map[grant.scope] = grant.granted;
      }
      setGranted(map);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  async function toggle(scope: GrantScope, next: boolean) {
    setWorkingScope(scope);
    try {
      await repos.auth.setGrant(scope, next);
      setGranted((prev) => ({ ...prev, [scope]: next }));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新失败");
    } finally {
      setWorkingScope(null);
    }
  }

  return (
    <SettingsScaffold id="screen-M4-grants" title="授权管理" eyebrow="分项授权">
      {loading ? (
        <Card>
          <StateView kind="loading" />
        </Card>
      ) : (
        <>
          <Card tight>
            {GRANT_ROWS.map((row) => (
              <Row
                key={row.scope}
                icon={<Sticker name={row.sticker} size="st-24" />}
                title={row.title}
                sub={granted[row.scope] ? row.sub : "未授权"}
                right={
                  <Switch
                    on={!!granted[row.scope]}
                    disabled={workingScope === row.scope}
                    onChange={(next) => void toggle(row.scope, next)}
                  />
                }
              />
            ))}
          </Card>
          <ErrorCard message={error} />
        </>
      )}
      <Note sticker="access-card.png">
        撤回立即生效，且不删除历史：已经订好的场、写好的日历保持原样。
      </Note>
    </SettingsScaffold>
  );
}

/* ---------- M5 隐私与安全（GET/PATCH /me/privacy） ---------- */

export function PrivacyScreen() {
  const { repos } = useApp();
  const [value, setValue] = useState<SocialPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      setValue(await repos.profile.privacy());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  async function save() {
    if (!value) return;
    setSaving(true);
    try {
      const saved = await repos.profile.patchPrivacy({
        social_enabled: value.social_enabled,
        course_matching_enabled: value.course_matching_enabled,
        identity_disclosure: value.identity_disclosure,
        same_gender_only: value.same_gender_only,
        minimum_group_size: value.minimum_group_size,
      });
      setValue(saved);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  const set = (patch: Partial<SocialPreferences>) =>
    setValue((prev) => (prev ? { ...prev, ...patch } : prev));

  async function setSocial(enabled: boolean) {
    set({ social_enabled: enabled, course_matching_enabled: enabled });
    setSaving(true);
    try {
      const saved = await repos.auth.setSocialEnabled(
        enabled,
        `privacy-social-${enabled ? "on" : "off"}-${Date.now()}`,
      );
      setValue(saved);
      setError(null);
    } catch (e) {
      set({ social_enabled: !enabled, course_matching_enabled: !enabled });
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SettingsScaffold id="screen-M5-privacy" title="隐私与安全">
      {loading ? (
        <Card>
          <StateView kind="loading" />
        </Card>
      ) : !value ? (
        <Card>
          <StateView
            kind="network"
            message={error ?? undefined}
            actionTitle="重试"
            onAction={() => void load()}
          />
        </Card>
      ) : (
        <>
          <Section title="进入匹配" />
          <Card tight>
            <Row
              icon={<Sticker name="chat-bubble.png" size="st-24" />}
              title="社交总开关"
              right={
                <Switch
                  on={value.social_enabled}
                  onChange={(on) => void setSocial(on)}
                />
              }
            />
            <Row
              icon={<Sticker name="books-stack.png" size="st-24" />}
              title="允许基于课程匹配"
              right={
                <Switch
                  on={value.course_matching_enabled}
                  onChange={(on) => set({ course_matching_enabled: on })}
                />
              }
            />
          </Card>

          <Section title="见面边界" />
          <Card>
            <div className="t-cap">身份公开时机</div>
            <div className="mt-2">
              <Seg
                options={[
                  { value: "after_confirmed", label: "全员确认后" },
                  { value: "after_full", label: "满员后" },
                ]}
                value={
                  value.identity_disclosure === "after_full"
                    ? "after_full"
                    : "after_confirmed"
                }
                onChange={(v) => set({ identity_disclosure: v })}
              />
            </div>
            <div className="between mt-3">
              <span className="t-call">只匹配同性成员</span>
              <Switch
                on={value.same_gender_only}
                onChange={(on) => set({ same_gender_only: on })}
              />
            </div>
            <div className="between mt-3">
              <span className="t-call">最低成局人数</span>
              <Stepper
                value={value.minimum_group_size}
                min={2}
                max={20}
                onChange={(n) => set({ minimum_group_size: n })}
              />
            </div>
          </Card>

          <Section title="场景敏感度" />
          <Card>
            <div className="t-foot">图书馆自习区 / 健身房器械区现场禁言</div>
          </Card>

          <ErrorCard message={error} />
          <Btn kind="primary" disabled={saving} onClick={() => void save()}>
            {saving ? "保存中…" : "保存隐私设置"}
          </Btn>
        </>
      )}
    </SettingsScaffold>
  );
}

/* ---------- M6 匹配偏好（GET/PATCH /me/matching-preferences） ---------- */

export function MatchingPreferencesScreen() {
  const { repos } = useApp();
  const [value, setValue] = useState<MatchingPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      setValue(await repos.profile.matchingPreferences());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  async function save() {
    if (!value) return;
    setSaving(true);
    try {
      const saved = await repos.profile.patchMatchingPreferences({
        interaction_style: value.interaction_style,
        sport_level: value.sport_level,
        study_intensity: value.study_intensity,
      });
      setValue(saved);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SettingsScaffold
      id="screen-M6-matching-preferences"
      title="匹配偏好"
      eyebrow="只影响推荐"
    >
      {loading ? (
        <Card>
          <StateView kind="loading" />
        </Card>
      ) : !value ? (
        <Card>
          <StateView
            kind="network"
            message={error ?? undefined}
            actionTitle="重试"
            onAction={() => void load()}
          />
        </Card>
      ) : (
        <>
          <Section title="互动节奏" />
          <Card>
            <Seg
              options={[
                { value: "quiet", label: "安静做事" },
                { value: "balanced", label: "自然平衡" },
                { value: "talkative", label: "愿意多交流" },
              ]}
              value={value.interaction_style as "quiet" | "balanced" | "talkative"}
              onChange={(v) => setValue({ ...value, interaction_style: v })}
            />
          </Card>
          <Section title="运动自述" />
          <Card>
            <Seg
              options={[
                { value: "beginner", label: "刚入门" },
                { value: "casual", label: "休闲" },
                { value: "intermediate", label: "稳定练习" },
                { value: "advanced", label: "高阶训练" },
              ]}
              value={
                value.sport_level as "beginner" | "casual" | "intermediate" | "advanced"
              }
              onChange={(v) => setValue({ ...value, sport_level: v })}
            />
          </Card>
          <Section title="学习强度" />
          <Card>
            <Seg
              options={[
                { value: "light", label: "轻量" },
                { value: "balanced", label: "平衡" },
                { value: "focused", label: "专注" },
              ]}
              value={value.study_intensity as "light" | "balanced" | "focused"}
              onChange={(v) => setValue({ ...value, study_intensity: v })}
            />
          </Card>
          <ErrorCard message={error} />
          <Btn kind="primary" disabled={saving} onClick={() => void save()}>
            {saving ? "保存中…" : "保存匹配偏好"}
          </Btn>
        </>
      )}
    </SettingsScaffold>
  );
}

/* ---------- M7 通知偏好（GET/PATCH /me/notification-preferences） ---------- */

const NOTIFICATION_CATEGORIES: Array<{ key: string; label: string; hint?: string }> = [
  { key: "gathering_updates", label: "成局", hint: "凑局、确认、改约" },
  { key: "schedule_reminders", label: "日程", hint: "上课、作业截止" },
  { key: "chat_messages", label: "消息" },
  { key: "action_updates", label: "行动执行" },
  { key: "trust_updates", label: "信任" },
  { key: "competition_deadlines", label: "赛事截止" },
];

/** 后端返回的本机系统设置 key → 中文显示名（对齐 iOS 文案）。 */
const LOCAL_SYSTEM_SETTING_LABELS: Record<string, string> = {
  notification_authorization: "系统通知权限",
  calendar_authorization: "日历访问权限",
  focus_mode: "专注模式",
};

export function NotificationSettingsScreen() {
  const { repos } = useApp();
  const [value, setValue] = useState<NotificationPreferences | null>(null);
  const [inbox, setInbox] = useState<InboxNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [prefs, items] = await Promise.all([
        repos.profile.notificationPreferences(),
        repos.profile.listNotifications().catch(() => [] as InboxNotification[]),
      ]);
      setValue(prefs);
      setInbox(items);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  async function save() {
    if (!value) return;
    setSaving(true);
    try {
      const saved = await repos.profile.patchNotificationPreferences({
        overall_enabled: value.overall_enabled,
        calendar_sync_enabled: value.calendar_sync_enabled,
        categories: value.categories,
      });
      setValue(saved);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  const visibleInbox = useMemo(
    () =>
      inbox.filter((item) =>
        categoryEnabled(value?.categories, item.category),
      ),
    [inbox, value],
  );

  return (
    <SettingsScaffold
      id="screen-M7-notification-settings"
      title="通知"
      eyebrow="提醒与日历"
    >
      {loading || !value ? (
        <Card>
          <StateView kind="loading" />
        </Card>
      ) : (
        <>
          <Card tight>
            <Row
              icon={<Icon name="bell" size={20} />}
              title="业务通知总开关"
              right={
                <Switch
                  on={value.overall_enabled}
                  onChange={(on) => setValue({ ...value, overall_enabled: on })}
                />
              }
            />
            <Row
              icon={<Sticker name="desk-calendar.png" size="st-24" />}
              title="执行成功后同步日历"
              right={
                <Switch
                  on={value.calendar_sync_enabled}
                  onChange={(on) =>
                    setValue({ ...value, calendar_sync_enabled: on })
                  }
                />
              }
            />
          </Card>

          <Section title="看哪些提醒" />
          <Card tight>
            {NOTIFICATION_CATEGORIES.map((cat) => (
              <Row
                key={cat.key}
                title={cat.label}
                sub={cat.hint}
                right={
                  <Switch
                    on={value.categories?.[cat.key] !== false}
                    onChange={(on) =>
                      setValue({
                        ...value,
                        categories: { ...value.categories, [cat.key]: on },
                      })
                    }
                  />
                }
              />
            ))}
          </Card>
          <Note>关掉的分类不会推送，也不会出现在下面的列表里。保存后同步到其他设备。</Note>

          <Section title="最近提醒" />
          {visibleInbox.length === 0 ? (
            <Card>
              <StateView
                kind="empty"
                message="打开上面的分类，这里会列出成局、日程和消息提醒。"
              />
            </Card>
          ) : (
            <Card tight>
              {visibleInbox.map((item) => {
                const path = pathFromNotification(item);
                return (
                  <Row
                    key={item.id}
                    title={notificationSummary(item.payload, item.title)}
                    sub={`${categoryLabel(item.category)} · ${relativeTimeLabel(item.created_at)}`}
                    to={path ?? undefined}
                  />
                );
              })}
            </Card>
          )}

          <Section title="只在本机系统管理" />
          <Card>
            {(value.system_settings_managed_locally ?? []).map((item) => (
              <div key={item} className="t-foot mt-1">
                {LOCAL_SYSTEM_SETTING_LABELS[item] ?? item}
              </div>
            ))}
            <div className="mt-2">
              <Btn kind="ghost" sm to="/permission">
                打开系统设置
              </Btn>
            </div>
          </Card>

          <ErrorCard message={error} />
          <Btn kind="primary" disabled={saving} onClick={() => void save()}>
            {saving ? "保存中…" : "保存偏好"}
          </Btn>
        </>
      )}
    </SettingsScaffold>
  );
}

/* ---------- M8 黑名单（GET /me/blocks + DELETE /me/blocks/{id}） ---------- */

function formatDateTime(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function BlockListScreen() {
  const { repos } = useApp();
  const [rows, setRows] = useState<BlockEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [workingId, setWorkingId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      setRows(await repos.profile.blocks());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  async function unblock(id: string) {
    setWorkingId(id);
    try {
      await repos.profile.unblock(id);
      setRows((prev) => prev.filter((r) => r.blocked_user_id !== id));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setWorkingId(null);
      setConfirming(null);
    }
  }

  return (
    <SettingsScaffold id="screen-M8-block-list" title="黑名单" eyebrow="安全">
      {loading ? (
        <Card>
          <StateView kind="loading" />
        </Card>
      ) : error && rows.length === 0 ? (
        <Card>
          <StateView
            kind="network"
            message={error}
            actionTitle="重试"
            onAction={() => void load()}
          />
        </Card>
      ) : rows.length === 0 ? (
        <Card>
          <StateView kind="empty" message="暂时没有内容，有进展时会告诉你。" />
        </Card>
      ) : (
        <>
          {rows.map((row) => (
            <Card key={row.blocked_user_id}>
              <div className="between">
                <div>
                  <div className="t-t3">已拉黑成员</div>
                  <div className="t-foot mt-1">
                    记录 ···{row.blocked_user_id.slice(-6)}
                  </div>
                  <div className="t-cap mt-1">{formatDateTime(row.created_at)}</div>
                </div>
                <Btn
                  kind="ghost"
                  sm
                  disabled={workingId !== null}
                  onClick={() => setConfirming(row.blocked_user_id)}
                >
                  {workingId === row.blocked_user_id ? "处理中…" : "解除拉黑…"}
                </Btn>
              </div>
            </Card>
          ))}
          <ErrorCard message={error} />
        </>
      )}
      <div className="t-foot center mt-3">
        被拉黑的人不会再出现在你的任何局里。对方不会知道自己被拉黑。
      </div>

      {confirming ? (
        <div className="om-sheet" data-od-id="unblock-confirm">
          <div className="sheet-grab" />
          <div className="t-t3">解除拉黑？</div>
          <div className="t-foot mt-2">
            解除是单方静默操作，对方不会收到通知。
          </div>
          <Btn
            kind="primary"
            disabled={workingId !== null}
            onClick={() => void unblock(confirming)}
          >
            确认解除
          </Btn>
          <Btn kind="text" onClick={() => setConfirming(null)}>
            取消
          </Btn>
        </div>
      ) : null}
    </SettingsScaffold>
  );
}

/* ---------- M9 信任申诉（POST /trust/appeal + GET /trust/appeals） ---------- */

export function AppealsScreen() {
  const { repos } = useApp();
  const [reason, setReason] = useState("");
  const [appeals, setAppeals] = useState<TrustAppeal[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      setAppeals(await repos.profile.appeals());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  const trimmed = reason.trim();
  const valid = trimmed.length >= 10;

  async function submit() {
    if (!valid || submitting) return;
    setSubmitting(true);
    try {
      await repos.profile.submitAppeal(trimmed);
      setReason("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SettingsScaffold
      id="screen-M9-appeals"
      title="信任申诉"
      eyebrow="信任复核"
      backTo="/me"
    >
      <Card>
        <div className="t-t3">申诉原因</div>
        <textarea
          className="om-input mt-2"
          placeholder="至少 10 个字，说明需要复核的事实"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        {!valid && trimmed.length > 0 ? (
          <div className="t-cap mt-1">请至少填写 10 个字</div>
        ) : null}
        <Btn
          kind="primary"
          disabled={!valid || submitting}
          onClick={() => void submit()}
        >
          {submitting ? "提交中…" : "提交申诉"}
        </Btn>
      </Card>

      {loading ? (
        <Card>
          <StateView kind="loading" />
        </Card>
      ) : appeals.length === 0 ? (
        <Card>
          <StateView kind="empty" message="暂时没有内容，有进展时会告诉你。" />
        </Card>
      ) : (
        appeals.map((appeal, i) => (
          <Card key={appeal.id ?? i}>
            <div className="between">
              <span className="om-chip soft">{appeal.status ?? "submitted"}</span>
              <span className="t-cap">{formatDateTime(appeal.updated_at)}</span>
            </div>
            <div className="t-call mt-2">{appeal.reason}</div>
            {appeal.result ? (
              <div className="t-foot mt-2">处理结果：{appeal.result}</div>
            ) : null}
          </Card>
        ))
      )}
      <ErrorCard message={error} />
    </SettingsScaffold>
  );
}

/* ---------- M10 数据与账号（/me/data-export + DELETE /me/account） ---------- */

export function AccountScreen() {
  const { repos, session } = useApp();
  const nav = useNavigate();
  const [exporting, setExporting] = useState(false);
  const [exportSummary, setExportSummary] = useState<string | null>(null);
  const [exportPayload, setExportPayload] = useState<Record<string, unknown> | null>(
    null,
  );
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function exportData() {
    setExporting(true);
    try {
      const data = await repos.profile.dataExport();
      setExportPayload(data);
      setExportSummary(
        `导出已生成，共 ${Object.keys(data).length} 个数据分区，可保存或分享。`,
      );
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "导出失败");
    } finally {
      setExporting(false);
    }
  }

  function downloadExport() {
    if (!exportPayload) return;
    const blob = new Blob([JSON.stringify(exportPayload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "噜噜成局-我的数据.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function deleteAccount() {
    setDeleting(true);
    try {
      await repos.profile.deleteAccount();
      session.clear();
      nav("/auth", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "注销失败");
      setDeleting(false);
      setConfirmDelete(false);
    }
  }

  return (
    <SettingsScaffold
      id="screen-M10-account"
      title="数据与账号"
      eyebrow="账号与数据"
    >
      {exportSummary ? (
        <Card>
          <div className="t-foot">{exportSummary}</div>
        </Card>
      ) : null}
      <Btn kind="primary" disabled={exporting} onClick={() => void exportData()}>
        {exporting ? "生成中…" : "生成我的数据导出"}
      </Btn>
      {exportPayload ? (
        <Btn kind="ghost" onClick={downloadExport}>
          保存或分享 JSON 文件
        </Btn>
      ) : null}

      <Card className="mt-3">
        <div className="t-t3">注销账号</div>
        <div className="t-foot mt-1">
          上传媒体和校园授权将被清理，此操作不可撤回。
        </div>
        <Btn kind="dark" sm onClick={() => setConfirmDelete(true)}>
          注销账号…
        </Btn>
      </Card>
      <ErrorCard message={error} />

      {confirmDelete ? (
        <div className="om-sheet" data-od-id="account-delete-confirm">
          <div className="sheet-grab" />
          <div className="t-t3">确认注销账号？</div>
          <div className="t-foot mt-2">
            上传媒体和校园授权将被清理，此操作不可撤回。
          </div>
          <Btn kind="primary" disabled={deleting} onClick={() => void deleteAccount()}>
            {deleting ? "处理中…" : "永久注销"}
          </Btn>
          <Btn kind="text" onClick={() => setConfirmDelete(false)}>
            取消
          </Btn>
        </div>
      ) : null}
    </SettingsScaffold>
  );
}

/* ---------- 学期回忆录（GET /me/recap） ---------- */

export function RecapScreen() {
  const { repos } = useApp();
  const [recap, setRecap] = useState<SemesterRecap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shared, setShared] = useState(false);

  async function load() {
    setError(null);
    try {
      setRecap(await repos.profile.recap());
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  async function share() {
    if (!recap?.share_text) return;
    try {
      if (navigator.share) {
        await navigator.share({ text: recap.share_text });
      } else {
        await navigator.clipboard.writeText(recap.share_text);
        setShared(true);
      }
    } catch {
      /* 用户取消分享 */
    }
  }

  const stats: Array<[string, string]> = useMemo(() => {
    if (!recap) return [];
    return [
      ["成局", String(recap.gatherings_completed ?? 0)],
      ["搭子", String(recap.partners_met ?? 0)],
      ["小时", (recap.total_hours ?? 0).toFixed(1).replace(/\.0$/, "")],
      ["复局", String(recap.recurrences ?? 0)],
    ];
  }, [recap]);

  return (
    <Screen id="screen-recap">
      <NavBar backTo="/me" />
      <Scroll>
        <PageHeader title="学期回忆录" clip="home.idle" />
        {error ? (
          <Card>
            <StateView
              kind="network"
              message={error}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : !recap ? (
          <Card>
            <StateView kind="loading" message="噜噜正在翻这学期的记录……" />
          </Card>
        ) : (
          <>
            <div className="center mt-3">
              <LuluMark
                placement="header"
                caption={recap.term_label}
              />
            </div>
            <Card className="mt-4">
              <div className="flex" style={{ justifyContent: "space-around" }}>
                {stats.map(([label, num]) => (
                  <div key={label} className="center">
                    <div className="t-t2 mono">{num}</div>
                    <div className="t-cap">{label}</div>
                  </div>
                ))}
              </div>
            </Card>
            {recap.top_partner?.display_name ? (
              <Card>
                <div className="t-t3">最稳的搭子</div>
                <div className="t-call mt-1">
                  {recap.top_partner.display_name} · 一起成了{" "}
                  {recap.top_partner.times_together ?? 0} 局
                </div>
              </Card>
            ) : null}
            {(recap.top_types ?? []).length > 0 ? (
              <Card>
                <div className="t-t3">这学期最常凑的</div>
                {(recap.top_types ?? []).map((t, i) => (
                  <div className="between mt-2" key={i}>
                    <span className="t-call">{t.gathering_type}</span>
                    <span className="t-foot mono">{t.count ?? 0} 局</span>
                  </div>
                ))}
                {recap.top_location ? (
                  <div className="t-cap mt-2">最常去：{recap.top_location}</div>
                ) : null}
              </Card>
            ) : null}
            {(recap.gatherings_completed ?? 0) === 0 ? (
              <Card>
                <StateView
                  kind="empty"
                  message="这学期还没有完成的局；先从一张意图卡开始。"
                />
              </Card>
            ) : null}
            {recap.share_text ? (
              <Btn kind="primary" onClick={() => void share()}>
                分享这学期
              </Btn>
            ) : null}
            {shared ? (
              <div className="t-cap center mt-2">分享文案已复制</div>
            ) : null}
          </>
        )}
      </Scroll>
    </Screen>
  );
}
