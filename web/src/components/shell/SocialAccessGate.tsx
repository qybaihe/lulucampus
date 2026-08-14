import { useEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import {
  Btn,
  Card,
  PageHeader,
  Screen,
  Scroll,
  Stage,
  StateView,
} from "../ui/primitives";

/** 未登录时留在当前 Tab，明确提示去登录，而不是只有「差一个」才跳进认证流。 */
export function GuestLoginWall({
  title = "登录后继续",
  subtitle = "课表、订场、找搭子和组队比赛都需要先登录。访客只能看看公开活动。",
}: {
  title?: string;
  subtitle?: string;
}) {
  const { session } = useApp();
  const nav = useNavigate();
  const location = useLocation();

  return (
    <Screen id="screen-guest-login">
      <Stage title={title} subtitle={subtitle} clip="home.reply" density="gate">
        <div data-od-id="guest-login-cta">
          <Btn
            kind="primary"
            onClick={() => {
              session.setPendingRoute(location.pathname + location.search);
              nav("/auth");
            }}
          >
            去登录
          </Btn>
        </div>
      </Stage>
    </Screen>
  );
}

/** Token 过期：与访客墙分开，对齐 iOS OMG5 expired。 */
export function SessionExpiredWall() {
  const { session } = useApp();
  const nav = useNavigate();
  const location = useLocation();

  return (
    <Screen id="screen-session-expired">
      <Scroll>
        <Card>
          <StateView
            kind="expired"
            actionTitle="重新登录"
            onAction={() => {
              session.setPendingRoute(location.pathname + location.search);
              nav("/auth/phone");
            }}
          />
        </Card>
      </Scroll>
    </Screen>
  );
}

/**
 * 对齐 iOS SocialAccessGate + authenticatedTab：
 * 未登录显示登录墙；社交关闭时拦截发布意图 / 消息。
 */
export function SocialAccessGate({
  children,
  requireSocial = true,
  title,
  subtitle,
}: {
  children: ReactNode;
  requireSocial?: boolean;
  title?: string;
  subtitle?: string;
}) {
  const { repos, sessionState } = useApp();
  const [phase, setPhase] = useState<
    "loading" | "enabled" | "disabled" | "failed"
  >("loading");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!requireSocial) {
      setPhase("enabled");
      return;
    }
    setPhase("loading");
    try {
      const privacy = await repos.profile.privacy();
      setPhase(privacy.social_enabled ? "enabled" : "disabled");
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPhase("failed");
    }
  }

  useEffect(() => {
    if (sessionState.status !== "authenticated") return;
    void load();
    const onFocus = () => {
      if (document.visibilityState === "hidden") return;
      void load();
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos, sessionState, requireSocial]);

  if (sessionState.status === "expired") {
    return <SessionExpiredWall />;
  }
  if (sessionState.status !== "authenticated") {
    return <GuestLoginWall title={title} subtitle={subtitle} />;
  }

  if (!requireSocial || phase === "enabled") {
    return <>{children}</>;
  }

  if (phase === "loading") {
    return (
      <Screen id="social-feature-loading">
        <Scroll>
          <Card>
            <StateView kind="loading" />
          </Card>
        </Scroll>
      </Screen>
    );
  }

  if (phase === "failed") {
    return (
      <Screen id="social-feature-failed">
        <Scroll>
          <Card>
            <StateView
              kind="network"
              message={error ?? undefined}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        </Scroll>
      </Screen>
    );
  }

  return (
    <Screen id="social-feature-disabled">
      <Scroll>
        <PageHeader eyebrow="SOCIAL OFF" title="校园成局仍保持关闭" />
        <Card>
          <div className="t-t3">认证不等于开启社交</div>
          <div className="t-foot mt-2">
            今天、活动与个人设置仍可使用；发布意图、加入局和搭子关系需由你主动开启。
          </div>
        </Card>
        <div className="mt-3">
          <Btn kind="primary" to="/me/privacy">
            前往隐私与社交设置
          </Btn>
        </div>
      </Scroll>
    </Screen>
  );
}

/** 只需登录、不要求社交开关的页面（活动、校园工具、个人设置等）。 */
export function AuthOnly({
  children,
  title,
  subtitle,
}: {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}) {
  return (
    <SocialAccessGate requireSocial={false} title={title} subtitle={subtitle}>
      {children}
    </SocialAccessGate>
  );
}
