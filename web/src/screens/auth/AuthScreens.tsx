/**
 * Auth + first-use — mirrors iOS OnboardingView / AuthenticationFlowView /
 * RealLoginView / FirstUseSetupView against the same FastAPI identity endpoints.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import { AppBrand } from "../../core/brand";
import type {
  AuthMe,
  GrantScope,
  LoginSession,
} from "../../core/api/repositories";
import { getOrCreateDeviceInstallId } from "../../core/api/repositories";
import {
  Btn,
  Card,
  Footer,
  LuluMark,
  NavBar,
  Note,
  Screen,
  Scroll,
  Stage,
  StateView,
} from "../../components/ui/primitives";

const ONBOARDING_SEEN_KEY = "onemore.onboarding.seen.v1";
const FIRST_USE_DONE_KEY = "onemore.firstuse.done.v1";
const SCHOOL_KEY = "onemore.school.affiliation.v1";
const CAMPUS_GATE_KEY = "onemore.school.campusGate.v1";

export type SchoolAffiliation = "sysu" | "other";

function hasSeenOnboarding(): boolean {
  try {
    return localStorage.getItem(ONBOARDING_SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

function markOnboardingSeen() {
  try {
    localStorage.setItem(ONBOARDING_SEEN_KEY, "1");
  } catch {
    /* ignore */
  }
}

function isFirstUseDone(): boolean {
  try {
    return localStorage.getItem(FIRST_USE_DONE_KEY) === "1";
  } catch {
    return false;
  }
}

export function markFirstUseDone() {
  try {
    localStorage.setItem(FIRST_USE_DONE_KEY, "1");
  } catch {
    /* ignore */
  }
}

function getSchool(): SchoolAffiliation | null {
  try {
    const raw = localStorage.getItem(SCHOOL_KEY);
    return raw === "sysu" || raw === "other" ? raw : null;
  } catch {
    return null;
  }
}

function saveSchool(value: SchoolAffiliation) {
  try {
    localStorage.setItem(SCHOOL_KEY, value);
    if (value !== "sysu") localStorage.removeItem(CAMPUS_GATE_KEY);
  } catch {
    /* ignore */
  }
}

function campusGatePassed(): boolean {
  try {
    return localStorage.getItem(CAMPUS_GATE_KEY) === "1";
  } catch {
    return false;
  }
}

function markCampusGatePassed() {
  try {
    localStorage.setItem(CAMPUS_GATE_KEY, "1");
  } catch {
    /* ignore */
  }
}

/** 设置页重置引导时一并清选校。 */
export function resetAuthOnboardingLocal() {
  try {
    localStorage.removeItem(ONBOARDING_SEEN_KEY);
    localStorage.removeItem(FIRST_USE_DONE_KEY);
    localStorage.removeItem(SCHOOL_KEY);
    localStorage.removeItem(CAMPUS_GATE_KEY);
  } catch {
    /* ignore */
  }
}

const SCHOOL_OPTIONS: {
  id: SchoolAffiliation;
  title: string;
  subtitle: string;
}[] = [
  {
    id: "sysu",
    title: "中山大学",
    subtitle: "我们为中大校园做了针对优化",
  },
  {
    id: "other",
    title: "其他",
    subtitle: "同样可以用，后续可补充校园认证",
  },
];

/** A1 · cold start */
export function BootScreen() {
  const { sessionState, repos } = useApp();
  const nav = useNavigate();

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(() => {
      void (async () => {
        if (cancelled) return;
        if (sessionState.status === "expired") {
          nav("/auth/phone", { replace: true });
          return;
        }
        if (sessionState.status === "authenticated") {
          // Prefer server facts to decide first-use vs today
          try {
            const me = await repos.auth.me();
            if (cancelled) return;
            // social_enabled false and not marked done → first use if grants incomplete
            if (!isFirstUseDone() && me.social_enabled === false) {
              nav("/auth/grants", { replace: true });
              return;
            }
          } catch {
            /* fall through to today / re-auth handled by 401 */
          }
          nav("/today", { replace: true });
          return;
        }
        // anonymous
        if (!hasSeenOnboarding()) {
          nav("/onboarding", { replace: true });
        } else {
          nav("/auth", { replace: true });
        }
      })();
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [sessionState, nav, repos]);

  return (
    <Screen id="app-root">
      <Scroll>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "70vh",
          }}
        >
          <LuluMark placement="empty" clip="home.idle" />
          <div className="t-t2 mt-4">噜噜成局</div>
          <div className="t-foot mt-1">差一个，就成局</div>
          <div className="mt-6" style={{ width: 120 }}>
            <div className="om-progress">
              <i style={{ width: "64%" }} />
            </div>
          </div>
          <div className="t-cap mt-3">正在检查登录状态…</div>
        </div>
      </Scroll>
    </Screen>
  );
}

/** Multi-page first launch guide：品牌页 + 选学校（对齐 iOS OnboardingView） */
export function OnboardingGuideScreen() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [school, setSchool] = useState<SchoolAffiliation | null>(getSchool());
  const brandPages = [
    {
      clip: "home.idle" as const,
      title: "噜噜成局",
      subtitle:
        "差一个，就成局。从真实课业与校园场景出发——拼课、约球、组队比赛，不刷人、不闲聊。",
    },
    {
      clip: "home.listening" as const,
      title: "说一句，剩下的交给噜噜",
      subtitle:
        `想找什么人、什么时候有空，告诉 ${AppBrand.agentName} 一句话，噜噜帮你把缺口补齐。`,
    },
  ];
  const pageCount = brandPages.length + 1;
  const isSchoolStep = step >= brandPages.length;
  const page = brandPages[Math.min(step, brandPages.length - 1)];

  return (
    <Screen id="screen-onboarding-guide">
      <Stage
        title={isSchoolStep ? "你在哪所学校？" : page.title}
        subtitle={
          isSchoolStep
            ? "选好后用手机号登录；中大同学登录后可绑定校园身份。"
            : page.subtitle
        }
        clip={isSchoolStep ? "core.care" : page.clip}
      >
        {isSchoolStep ? (
          <div style={{ display: "grid", gap: 10, marginBottom: 16 }}>
            {SCHOOL_OPTIONS.map((option) => {
              const selected = school === option.id;
              return (
                <button
                  key={option.id}
                  type="button"
                  data-od-id={`onboarding-school-${option.id}`}
                  onClick={() => setSchool(option.id)}
                  style={{
                    textAlign: "left",
                    cursor: "pointer",
                    border: selected
                      ? "1.5px solid var(--ink)"
                      : "1px solid var(--line)",
                    background: "var(--card)",
                    padding: 16,
                    borderRadius: 20,
                  }}
                >
                  <div className="t-call" style={{ fontWeight: 700 }}>
                    {option.title}
                  </div>
                  <div className="t-foot muted mt-1">{option.subtitle}</div>
                </button>
              );
            })}
          </div>
        ) : null}
        <div
          className="flex"
          style={{ justifyContent: "center", gap: 8, marginBottom: 8 }}
        >
          {Array.from({ length: pageCount }).map((_, i) => (
            <span
              key={i}
              style={{
                width: i === step ? 22 : 8,
                height: 8,
                borderRadius: 999,
                background: i === step ? "var(--yolk)" : "var(--line)",
                display: "inline-block",
              }}
            />
          ))}
        </div>
      </Stage>
      <Footer>
        <Btn
          kind="primary"
          disabled={isSchoolStep && !school}
          onClick={() => {
            if (!isSchoolStep) {
              setStep((s) => s + 1);
              return;
            }
            if (!school) return;
            saveSchool(school);
            markOnboardingSeen();
            nav("/auth", { replace: true });
          }}
        >
          {isSchoolStep ? "开始使用" : "继续"}
        </Btn>
      </Footer>
    </Screen>
  );
}

/** A2 · 认证入口：一律先手机号；中大登录后再绑定校园身份 */
export function AuthIntroScreen() {
  const nav = useNavigate();
  const school = getSchool();

  useEffect(() => {
    if (!school) {
      nav("/onboarding", { replace: true });
      return;
    }
    nav("/auth/phone", { replace: true });
  }, [school, nav]);

  return (
    <Screen id="screen-A2-auth-intro">
      <Scroll>
        <div className="center mt-8">
          <LuluMark placement="hero" clip="home.reply" />
          <div className="t-t2 mt-4">正在进入登录…</div>
        </div>
      </Scroll>
    </Screen>
  );
}

/** A2b · phone + password login / register — POST /auth/login · /auth/register */
export function PhoneAuthScreen() {
  const { repos, session } = useApp();
  const nav = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const phoneValid = /^1[3-9]\d{9}$/.test(phone);
  const passwordValid = password.length >= 6 && password.length <= 64;
  const canSubmit = phoneValid && passwordValid && !busy;

  async function submit() {
    if (!canSubmit) {
      if (!phoneValid) setError("请输入 11 位大陆手机号");
      else if (!passwordValid) setError("密码长度需在 6–64 位之间");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result =
        mode === "register"
          ? await repos.auth.registerPhone({
              phone,
              password,
              ...(displayName.trim()
                ? { display_name: displayName.trim() }
                : {}),
            })
          : await repos.auth.loginPhone({ phone, password });
      session.setSession(result.access_token, {
        user_id: result.user_id,
        display_name: result.display_name ?? undefined,
      });
      const pending = session.getPendingRoute();
      session.setPendingRoute(null);

      // 中大且尚未校园核验 → 先绑定；否则进首次设置 / 今天。页面不提信任等级。
      if (getSchool() === "sysu" && !campusGatePassed()) {
        try {
          const me = await repos.auth.me();
          if (!me.verified) {
            nav("/auth/scan", { replace: true });
            return;
          }
          markCampusGatePassed();
        } catch {
          nav("/auth/scan", { replace: true });
          return;
        }
      }

      if (result.is_new_user || !isFirstUseDone()) {
        nav("/auth/grants", { replace: true });
        return;
      }
      nav(pending && pending !== "/" ? pending : "/today", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "请求失败，请稍后重试");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen id="screen-A2b-phone-auth">
      <NavBar title="手机号登录" backTo="/onboarding" />
      <Scroll>
        <div className="center mt-4">
          <LuluMark
            placement="header"
            clip="home.listening"
            caption={
              mode === "login"
                ? "欢迎回来，差一个就成局"
                : "一分钟注册，暂不需要短信验证码"
            }
          />
        </div>
        <div
          className="flex mt-5"
          style={{ justifyContent: "center", gap: 8 }}
          role="tablist"
        >
          {(
            [
              ["login", "登录"],
              ["register", "注册"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              role="tab"
              aria-selected={mode === key}
              className={`om-chip ${mode === key ? "solid" : ""}`}
              style={{ cursor: "pointer", border: "none" }}
              onClick={() => {
                setMode(key);
                setError(null);
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <Card className="mt-4">
          <label className="t-cap" htmlFor="phone-auth-phone">
            手机号
          </label>
          <input
            id="phone-auth-phone"
            className="om-input mt-1"
            type="tel"
            inputMode="numeric"
            autoComplete="tel"
            maxLength={11}
            placeholder="11 位手机号"
            value={phone}
            onChange={(e) =>
              setPhone(e.target.value.replace(/\D/g, "").slice(0, 11))
            }
          />
          <label className="t-cap mt-3" htmlFor="phone-auth-password" style={{ display: "block" }}>
            密码
          </label>
          <input
            id="phone-auth-password"
            className="om-input mt-1"
            type="password"
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            placeholder={mode === "register" ? "6–64 位，注册后请牢记" : "输入密码"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void submit();
            }}
          />
          {mode === "register" ? (
            <>
              <label
                className="t-cap mt-3"
                htmlFor="phone-auth-nickname"
                style={{ display: "block" }}
              >
                昵称（可选）
              </label>
              <input
                id="phone-auth-nickname"
                className="om-input mt-1"
                type="text"
                maxLength={80}
                placeholder="不填则默认「同学+手机尾号」"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void submit();
                }}
              />
            </>
          ) : null}
        </Card>
        {error ? (
          <div className="t-foot mt-2" role="alert" style={{ color: "var(--warn, #c0392b)" }}>
            {error}
          </div>
        ) : null}
        <Note sticker="access-card.png">
          {mode === "register"
            ? "注册即创建校园账号；后续可在设置中补充校园身份认证解锁更多能力。"
            : "登录凭证仅保存在本设备；忘记密码请联系管理员重置。"}
        </Note>
      </Scroll>
      <Footer>
        <div data-od-id="phone-auth-submit">
          <Btn kind="primary" disabled={!canSubmit} onClick={() => void submit()}>
            {busy
              ? mode === "register"
                ? "注册中…"
                : "登录中…"
              : mode === "register"
                ? "注册并进入"
                : "登录"}
          </Btn>
        </div>
      </Footer>
    </Screen>
  );
}

type ScanPhase =
  | { kind: "intro" }
  | { kind: "creating" }
  | { kind: "waiting"; login: LoginSession; redemptionToken: string }
  | { kind: "redeeming" }
  | { kind: "failed"; message: string };

/** A3 · 中大校园绑定：手机号登录后扫码，兑换会话把校园身份绑到当前账号。 */
export function AuthScanScreen() {
  const { repos, session } = useApp();
  const nav = useNavigate();
  const [phase, setPhase] = useState<ScanPhase>({ kind: "intro" });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stopped = useRef(false);

  const stopPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopped.current = true;
      stopPoll();
    };
  }, [stopPoll]);

  const finishBind = useCallback(
    (accessToken?: string) => {
      if (accessToken) {
        session.setSession(accessToken);
      }
      markCampusGatePassed();
      if (!isFirstUseDone()) {
        nav("/auth/grants", { replace: true });
        return;
      }
      nav("/today", { replace: true });
    },
    [session, nav],
  );

  const pollAndMaybeRedeem = useCallback(
    async (sessionId: string, redemptionToken: string) => {
      try {
        const current = await repos.auth.pollSession(sessionId, redemptionToken);
        if (stopped.current) return;
        setPhase({ kind: "waiting", login: current, redemptionToken });
        if (current.status === "SUCCESS") {
          stopPoll();
          setPhase({ kind: "redeeming" });
          const redeemed = await repos.auth.redeem(sessionId, redemptionToken);
          if (!redeemed.access_token) {
            setPhase({
              kind: "failed",
              message: "服务端未返回 access_token",
            });
            return;
          }
          finishBind(redeemed.access_token);
          return;
        }
        if (["TIMEOUT", "CANCELLED", "FAILED"].includes(current.status)) {
          stopPoll();
          setPhase({
            kind: "failed",
            message: current.error_category ?? "认证未完成",
          });
        }
      } catch (e) {
        if (stopped.current) return;
        stopPoll();
        setPhase({
          kind: "failed",
          message: e instanceof Error ? e.message : "轮询失败",
        });
      }
    },
    [repos, stopPoll, finishBind],
  );

  async function startLogin() {
    stopPoll();
    stopped.current = false;
    setPhase({ kind: "creating" });
    try {
      const installId = getOrCreateDeviceInstallId();
      const login = await repos.auth.startSession({
        device_install_id: installId,
      });
      const redemptionToken = login.redemption_token;
      if (!redemptionToken) {
        setPhase({
          kind: "failed",
          message: "服务端未返回本设备的登录兑换凭证（redemption_token）",
        });
        return;
      }
      setPhase({ kind: "waiting", login, redemptionToken });
      // Poll every 2s like iOS
      pollRef.current = setInterval(() => {
        void pollAndMaybeRedeem(login.id, redemptionToken);
      }, 2000);
      // immediate first poll (QR may arrive async from Hermes)
      void pollAndMaybeRedeem(login.id, redemptionToken);
    } catch (e) {
      setPhase({
        kind: "failed",
        message: e instanceof Error ? e.message : "无法创建认证会话",
      });
    }
  }

  async function demoComplete() {
    if (phase.kind !== "waiting") return;
    try {
      await repos.auth.demoComplete(phase.login.id, phase.redemptionToken);
      await pollAndMaybeRedeem(phase.login.id, phase.redemptionToken);
    } catch (e) {
      setPhase({
        kind: "failed",
        message: e instanceof Error ? e.message : "demo-complete 失败",
      });
    }
  }

  const qrUrl =
    phase.kind === "waiting" ? phase.login.qr_image_data_url : null;
  const status = phase.kind === "waiting" ? phase.login.status : null;
  const isDemoSvg =
    typeof qrUrl === "string" &&
    (qrUrl.includes("image/svg") || qrUrl.includes("DEMO"));

  return (
    <Screen id="screen-A3-real-login">
      <NavBar title="绑定校园身份" backTo="/auth/phone" />
      <Stage
        subtitle={
          phase.kind === "waiting"
            ? "打开企业微信，扫一扫"
            : phase.kind === "failed"
              ? "这次没连上，可以重试或稍后再说"
              : "用企业微信扫码完成绑定；也可以稍后再说，不影响先使用基础功能。"
        }
        clip={phase.kind === "failed" ? "core.care" : "home.idle"}
        hero={
          phase.kind === "waiting" ? (
            <div className="qr-box" data-od-id="auth-qr-image">
              {qrUrl ? (
                <img
                  src={qrUrl}
                  alt="统一身份认证二维码"
                  style={{
                    width: 180,
                    height: 180,
                    objectFit: "contain",
                    imageRendering: isDemoSvg ? "auto" : "pixelated",
                  }}
                />
              ) : (
                <div className="t-foot center" style={{ padding: 24 }}>
                  二维码生成中…
                  <br />
                  <span className="t-cap">状态 {status ?? "…"}</span>
                </div>
              )}
            </div>
          ) : phase.kind === "creating" || phase.kind === "redeeming" ? (
            <StateView
              kind="loading"
              message={
                phase.kind === "creating"
                  ? "正在创建认证会话…"
                  : "扫码已确认，正在兑换会话…"
              }
            />
          ) : undefined
        }
      >
        {phase.kind === "intro" ? (
          <>
            <div data-od-id="auth-start-button">
              <Btn kind="primary" onClick={() => void startLogin()}>
                生成绑定二维码
              </Btn>
            </div>
            <div className="mt-2">
              <Btn
                kind="ghost"
                onClick={() => {
                  nav("/auth/grants", { replace: true });
                }}
              >
                稍后再说
              </Btn>
            </div>
          </>
        ) : null}

        {phase.kind === "waiting" ? (
          <>
            <div className="center">
              <span className="om-chip solid">{status ?? "WAITING"}</span>
            </div>
            {isDemoSvg ? (
              <Note sticker="access-card.png">
                当前是演示用二维码，企业微信扫不了。开发环境可点下方「完成扫码」。
              </Note>
            ) : null}
            {(import.meta.env.DEV || import.meta.env.VITE_DEV_AUTH) && (
              <div className="mt-2" data-od-id="demo-complete-login">
                <Btn kind="ghost" onClick={() => void demoComplete()}>
                  开发环境：完成扫码
                </Btn>
              </div>
            )}
            <div className="mt-2">
              <Btn
                kind="ghost"
                onClick={() => {
                  stopPoll();
                  nav("/auth/grants", { replace: true });
                }}
              >
                稍后再说
              </Btn>
            </div>
          </>
        ) : null}

        {phase.kind === "failed" ? (
          <>
            <Card>
              <StateView
                kind="network"
                message={phase.message}
                actionTitle="重试"
                onAction={() => setPhase({ kind: "intro" })}
              />
            </Card>
            <div className="mt-2">
              <Btn
                kind="ghost"
                onClick={() => nav("/auth/grants", { replace: true })}
              >
                稍后再说
              </Btn>
            </div>
          </>
        ) : null}
      </Stage>
    </Screen>
  );
}

const GRANT_DEFS: Array<{ scope: GrantScope; title: string; sub: string }> = [
  {
    scope: "timetable",
    title: "课表与空闲",
    sub: "用来找你的真实空档",
  },
  {
    scope: "curriculum",
    title: "课程画像",
    sub: "生成能力标签的来源之一",
  },
  {
    scope: "enrollment",
    title: "同课匹配",
    sub: "辅助判断你上过哪些课",
  },
  {
    scope: "agent_booking",
    title: "校园预约代理",
    sub: "订场、写日历前的最后一步确认权永远在你手里",
  },
];

/** A4 · grants — 噜噜居中 + 底部四格确认按钮（对齐 iOS FirstUseSetupView.grants） */
export function AuthGrantsScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [selected, setSelected] = useState<Set<GrantScope>>(
    () => new Set(["timetable", "curriculum", "enrollment", "agent_booking"]),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(scope: GrantScope) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(scope)) next.delete(scope);
      else next.add(scope);
      return next;
    });
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      for (const def of GRANT_DEFS) {
        await repos.auth.setGrant(def.scope, selected.has(def.scope));
      }
      nav("/auth/facts");
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存授权失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen id="screen-A4-grants" className="auth-grants">
      <Stage
        title="授权由你掌控"
        subtitle="点选你愿意开放的数据边界，随时可在设置里撤回"
        clip="core.care"
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 10,
          }}
        >
          {GRANT_DEFS.map((g) => {
            const on = selected.has(g.scope);
            return (
              <button
                key={g.scope}
                type="button"
                data-od-id={`first-use-grant-${g.scope}`}
                onClick={() => toggle(g.scope)}
                aria-pressed={on}
                style={{
                  textAlign: "left",
                  cursor: "pointer",
                  minHeight: 52,
                  padding: "12px 12px",
                  borderRadius: 14,
                  border: on
                    ? "1.5px solid var(--ink)"
                    : "1px solid var(--line)",
                  background: on
                    ? "color-mix(in srgb, var(--yolk) 35%, var(--card))"
                    : "var(--card)",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span
                  aria-hidden
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: 999,
                    border: on ? "none" : "1.5px solid var(--sage)",
                    background: on ? "var(--ink)" : "transparent",
                    flex: "0 0 auto",
                    position: "relative",
                  }}
                >
                  {on ? (
                    <span
                      style={{
                        position: "absolute",
                        inset: 0,
                        color: "var(--card)",
                        fontSize: 11,
                        lineHeight: "16px",
                        textAlign: "center",
                        fontWeight: 700,
                      }}
                    >
                      ✓
                    </span>
                  ) : null}
                </span>
                <span
                  className="t-foot"
                  style={{ fontWeight: 600, color: "var(--ink)" }}
                >
                  {g.title}
                </span>
              </button>
            );
          })}
        </div>

        {error ? (
          <div className="t-foot mt-2" role="alert" style={{ color: "#c0392b" }}>
            {error}
          </div>
        ) : null}

        <div className="mt-3" data-od-id="first-use-save-grants">
          <Btn kind="primary" onClick={() => void save()} disabled={busy}>
            {busy ? "保存中…" : "确认授权，继续"}
          </Btn>
        </div>
      </Stage>
    </Screen>
  );
}

/** A5/A6 · identity facts from GET /auth/me */
export function AuthFactsScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [phase, setPhase] = useState<"loading" | "ready" | "failed">("loading");
  const [me, setMe] = useState<AuthMe | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setPhase("loading");
    try {
      const facts = await repos.auth.me();
      setMe(facts);
      setPhase("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "读取身份失败");
      setPhase("failed");
    }
  }

  useEffect(() => {
    void load();
  }, [repos]);

  if (phase === "loading") {
    return (
      <Screen id="screen-A5-A6-facts">
        <Stage
          title="确认你的校园画像"
          subtitle="正在读取校园身份…"
          clip="home.reply"
        />
      </Screen>
    );
  }

  if (phase === "failed") {
    return (
      <Screen id="screen-A5-A6-facts">
        <Stage
          title="确认你的校园画像"
          subtitle={error ?? "这次没读到，可以再试一次"}
          clip="core.care"
        >
          <Btn kind="primary" onClick={() => void load()}>
            重试
          </Btn>
        </Stage>
      </Screen>
    );
  }

  const line = [me?.college, me?.major].filter(Boolean).join(" · ");
  const meta = [
    me?.campus,
    me?.grade_year != null ? String(me.grade_year) : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Screen id="screen-A5-A6-facts">
      <Stage
        title="确认你的校园画像"
        subtitle="来自校园身份核验，只给你自己看"
        clip="home.reply"
      >
        <Card tight>
          <div className="t-t3">
            {me?.verified ? "校园身份已核验" : "身份待核验"}
          </div>
          {line ? <div className="t-call mt-1">{line}</div> : null}
          {meta ? <div className="t-foot mt-1">{meta}</div> : null}
        </Card>
        <div className="mt-3">
          <Btn kind="primary" onClick={() => nav("/auth/social")}>
            身份事实无误
          </Btn>
        </div>
      </Stage>
    </Screen>
  );
}

/** A7 · social opt-in — 与授权页同构：居中大噜噜 + 底部双按钮 */
export function AuthSocialScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function finish(enabled: boolean) {
    setBusy(true);
    setError(null);
    try {
      await repos.auth.setSocialEnabled(enabled);
      markFirstUseDone();
      nav("/today", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen id="screen-A7-social" className="auth-social">
      <Stage
        title="由你开启校园成局"
        subtitle="开启后才能发布意图与加入局"
        clip="confirm.gather"
      >
        {error ? (
          <div className="t-foot mt-2" role="alert" style={{ color: "#c0392b" }}>
            {error}
          </div>
        ) : null}

        <div data-od-id="first-use-enable-social">
          <Btn kind="primary" disabled={busy} onClick={() => void finish(true)}>
            {busy ? "保存中…" : "开启并继续"}
          </Btn>
        </div>
        <div className="mt-2" data-od-id="first-use-skip-social">
          <Btn kind="ghost" disabled={busy} onClick={() => void finish(false)}>
            暂不开启，保持关闭并继续
          </Btn>
        </div>
      </Stage>
    </Screen>
  );
}
