import { useCallback, useEffect, useRef, useState } from "react";
import { useApp } from "../../app/AppContext";
import type {
  TasteImportProgress,
  TasteImportSession,
  TasteProfileResult,
  TasteQuestions,
  TasteSourceProfile,
} from "../../core/api/repositories";
import { LuluSprite } from "../../components/lulu/LuluSprite";
import { Btn, Card, NavBar, Note, Screen, Scroll } from "../../components/ui/primitives";
import { PersonaCard } from "./PersonaCard";

type Phase =
  | { kind: "starting" }
  | { kind: "scan" }
  | { kind: "phone" }
  | { kind: "sms" }
  | { kind: "verified" }
  | { kind: "generating" }
  | { kind: "ready" }
  | { kind: "questions"; questions: TasteQuestions }
  | { kind: "failed"; message: string };

const POLL_MS = 2000;
const TERMINAL = new Set(["READY", "FAILED", "CANCELLED"]);
const IDENTIFIED = new Set(["AUTHENTICATED", "RESOLVING_PROFILE", "COLLECTING", "ANALYZING", "READY"]);
const PHONE_STATUSES = new Set(["PHONE_REQUIRED"]);
const SMS_STATUSES = new Set(["WAITING_SMS_CODE"]);

function errMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/** 抖音头像：加载失败时退化为昵称首字 */
export function DouyinAvatar({
  profile,
  size = 64,
}: {
  profile: TasteSourceProfile | null | undefined;
  size?: number;
}) {
  const [broken, setBroken] = useState(false);
  const initial = (profile?.nickname?.trim() || "抖").slice(0, 1);
  const style = { width: size, height: size };
  if (!profile?.avatar_url || broken) {
    return (
      <div className="dy-avatar dy-avatar-fallback" style={style} aria-hidden>
        {initial}
      </div>
    );
  }
  return (
    <img
      className="dy-avatar"
      style={style}
      src={profile.avatar_url}
      alt={profile.nickname ?? "抖音头像"}
      referrerPolicy="no-referrer"
      onError={() => setBroken(true)}
    />
  );
}

export function VerifiedBadge() {
  return (
    <span className="verified-badge">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="m4.5 12.5 5 5 10-11" />
      </svg>
      已认证
    </span>
  );
}

export function TasteImportScreen() {
  const { repos } = useApp();
  const [phase, setPhase] = useState<Phase>({ kind: "starting" });
  const [session, setSession] = useState<TasteImportSession | null>(null);
  const [result, setResult] = useState<TasteProfileResult | null>(null);
  const [profile, setProfile] = useState<TasteSourceProfile | null>(null);
  const [progress, setProgress] = useState<TasteImportProgress | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const [countryCode, setCountryCode] = useState("86");
  const [phone, setPhone] = useState("");
  const [smsCode, setSmsCode] = useState("");
  const [phoneMasked, setPhoneMasked] = useState<string | null>(null);
  const [phoneWorking, setPhoneWorking] = useState(false);
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [submittingQuiz, setSubmittingQuiz] = useState(false);

  const importIdRef = useRef<string | null>(null);
  const pollTimerRef = useRef<number | null>(null);
  const generateRequestedRef = useRef(false);
  const goneRef = useRef(false);
  const refreshingRef = useRef(false);

  const showToast = useCallback((text: string) => {
    setToast(text);
    window.setTimeout(() => setToast((cur) => (cur === text ? null : cur)), 2400);
  }, []);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current !== null) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  /** 轮询 tick：拉状态 → 迁移 phase → 自排下一跳（自引用在运行时已完成初始化） */
  const tick = useCallback(async (): Promise<void> => {
    const id = importIdRef.current;
    if (!id || goneRef.current) return;

    const scheduleNext = () => {
      if (goneRef.current) return;
      stopPolling();
      pollTimerRef.current = window.setTimeout(() => void tick(), POLL_MS);
    };

    const apply = (snap: TasteImportSession) => {
      if (goneRef.current) return;
      setSession(snap);
      if (snap.progress) setProgress(snap.progress);
      if (snap.source_profile) setProfile(snap.source_profile);

      if (snap.status === "FAILED" || snap.status === "CANCELLED") {
        stopPolling();
        setPhase({
          kind: "failed",
          message: snap.error?.message ?? "导入没有完成，可以重新扫码再试一次。",
        });
        return;
      }

      // 抖音要求手机号验证（对齐 iOS phoneEntry / verificationEntry）
      if (PHONE_STATUSES.has(snap.status)) {
        setPhase((cur) => (cur.kind === "phone" ? cur : { kind: "phone" }));
        scheduleNext();
        return;
      }
      if (SMS_STATUSES.has(snap.status)) {
        setPhase((cur) => (cur.kind === "sms" ? cur : { kind: "sms" }));
        scheduleNext();
        return;
      }

      const readyResult =
        snap.status === "READY" ? (snap.result ?? null) : null;
      if (readyResult) setResult(readyResult);

      if (readyResult && generateRequestedRef.current) {
        stopPolling();
        setPhase({ kind: "ready" });
        return;
      }

      const identified =
        Boolean(snap.source_profile) || IDENTIFIED.has(snap.status);
      if (identified) {
        // 扫码识别成功：先停在「已认证」确认卡，等用户点「生成画像」
        setPhase((cur) =>
          cur.kind === "generating" || cur.kind === "ready" || cur.kind === "questions"
            ? cur
            : { kind: "verified" },
        );
      } else {
        setPhase((cur) =>
          cur.kind === "scan" || cur.kind === "starting"
            ? { kind: "scan" }
            : cur,
        );
      }

      if (!TERMINAL.has(snap.status)) scheduleNext();
      else stopPolling();
    };

    try {
      const snap = await repos.taste.importStatus(id);
      if (snap.status === "QR_EXPIRED" && !refreshingRef.current) {
        refreshingRef.current = true;
        try {
          const fresh = await repos.taste.refreshDouyinQR(id);
          showToast("二维码已过期，为你更新了一张");
          apply(fresh);
        } finally {
          refreshingRef.current = false;
        }
        scheduleNext();
        return;
      }
      apply(snap);
    } catch (err) {
      if (goneRef.current) return;
      stopPolling();
      setPhase({ kind: "failed", message: errMessage(err) });
    }
  }, [repos, showToast, stopPolling]);

  const start = useCallback(
    async (force: boolean) => {
      stopPolling();
      generateRequestedRef.current = false;
      setResult(null);
      setProfile(null);
      setProgress(null);
      setSecondsLeft(null);
      setPhase({ kind: "starting" });
      try {
        const qr = await repos.taste.createDouyinQR({ force }, 10);
        if (goneRef.current) return;
        importIdRef.current = qr.import_id;
        setSession({
          id: qr.import_id,
          status: qr.status,
          qr_image_data_url: qr.qr_image_data_url,
          qr_version: qr.qr_version,
          qr_expires_at: qr.qr_expires_at,
          error: qr.error,
        });
        setPhase({ kind: "scan" });
        stopPolling();
        pollTimerRef.current = window.setTimeout(() => void tick(), 600);
      } catch (err) {
        if (!goneRef.current) {
          setPhase({ kind: "failed", message: errMessage(err) });
        }
      }
    },
    [repos, tick, stopPolling],
  );

  useEffect(() => {
    goneRef.current = false;
    void start(false);
    return () => {
      goneRef.current = true;
      stopPolling();
    };
  }, [start, stopPolling]);

  // 二维码过期倒计时
  useEffect(() => {
    if (phase.kind !== "scan" || !session?.qr_expires_at) return;
    const expiry = new Date(session.qr_expires_at).getTime();
    const tickdown = () => {
      const left = Math.max(0, Math.round((expiry - Date.now()) / 1000));
      setSecondsLeft(Number.isFinite(left) ? left : null);
    };
    tickdown();
    const t = window.setInterval(tickdown, 1000);
    return () => window.clearInterval(t);
  }, [phase.kind, session?.qr_expires_at, session?.qr_version]);

  const onGenerate = () => {
    generateRequestedRef.current = true;
    if (result) {
      setPhase({ kind: "ready" });
      return;
    }
    setPhase({ kind: "generating" });
    stopPolling();
    pollTimerRef.current = window.setTimeout(() => void tick(), 400);
  };

  const onRestart = () => {
    const id = importIdRef.current;
    if (id) void repos.taste.cancelDouyinImport(id).catch(() => undefined);
    void start(true);
  };

  const onManualRefresh = () => {
    const id = importIdRef.current;
    if (!id || refreshingRef.current) return;
    refreshingRef.current = true;
    repos.taste
      .refreshDouyinQR(id)
      .then((fresh) => {
        showToast("已换上新鲜二维码");
        setSession(fresh);
      })
      .catch((err) => setPhase({ kind: "failed", message: errMessage(err) }))
      .finally(() => {
        refreshingRef.current = false;
      });
  };

  /** 发送短信验证码（对齐 iOS requestPhoneCode）。 */
  const onSendPhoneCode = async () => {
    const id = importIdRef.current;
    const digits = phone.replace(/\D/g, "");
    const cc = countryCode.replace(/\D/g, "");
    if (!id || phoneWorking) return;
    if (!cc || digits.length < 5) {
      setPhoneError("请输入有效的国家或地区代码与手机号");
      return;
    }
    setPhoneWorking(true);
    setPhoneError(null);
    try {
      const state = await repos.taste.phoneCode(id, digits, cc);
      setPhone("");
      setPhoneMasked(state.phone_masked ?? null);
      setPhase({ kind: "sms" });
    } catch (err) {
      setPhoneError(errMessage(err));
    } finally {
      setPhoneWorking(false);
    }
  };

  /** 验证短信验证码并继续导入（对齐 iOS submitPhoneCode）。 */
  const onSubmitSmsCode = async () => {
    const id = importIdRef.current;
    const digits = smsCode.replace(/\D/g, "");
    if (!id || phoneWorking) return;
    if (digits.length < 4 || digits.length > 8) {
      setPhoneError("请输入 4–8 位短信验证码");
      return;
    }
    setPhoneWorking(true);
    setPhoneError(null);
    try {
      const state = await repos.taste.phoneVerify(id, digits);
      setSmsCode("");
      setPhoneMasked(state.phone_masked ?? phoneMasked);
      // 验证提交后回到轮询，由服务端状态推进后续阶段
      setPhase({ kind: "starting" });
      stopPolling();
      pollTimerRef.current = window.setTimeout(() => void tick(), 400);
    } catch (err) {
      setPhoneError(errMessage(err));
    } finally {
      setPhoneWorking(false);
    }
  };

  const onCheckPhoneStatus = async () => {
    const id = importIdRef.current;
    if (!id || phoneWorking) return;
    try {
      const state = await repos.taste.phoneStatus(id);
      setPhoneMasked(state.phone_masked ?? phoneMasked);
      showToast(state.code_sent ? "验证码已发送" : "等待发送验证码");
    } catch (err) {
      setPhoneError(errMessage(err));
    }
  };

  /** 打开可选细化题（对齐 iOS openOptionalQuestions：优先用状态内嵌 JSON）。 */
  const onOpenQuestions = async () => {
    const id = importIdRef.current;
    if (!id) return;
    try {
      const embedded = session?.questions as TasteQuestions | null | undefined;
      const quiz =
        embedded && Array.isArray(embedded.questions) && embedded.questions.length
          ? embedded
          : await repos.taste.questions(id);
      if (!quiz.questions?.length) {
        showToast("暂时没有细化题");
        return;
      }
      setSelections({});
      setPhase({ kind: "questions", questions: quiz });
    } catch (err) {
      showToast(errMessage(err));
    }
  };

  /** 提交细化答案 → AI 精修画像（对齐 iOS submit）。 */
  const onSubmitQuiz = async () => {
    const id = importIdRef.current;
    if (!id || submittingQuiz) return;
    const answers = Object.entries(selections).map(([question_id, option_id]) => ({
      question_id,
      option_id,
    }));
    setSubmittingQuiz(true);
    try {
      const refined = await repos.taste.submitAnswers(id, answers);
      setResult(refined);
      setPhase({ kind: "ready" });
      showToast("画像已按你的选择细化");
    } catch (err) {
      showToast(errMessage(err));
    } finally {
      setSubmittingQuiz(false);
    }
  };

  /** 删除抖音兴趣画像（对齐 iOS deleteProfile）。 */
  const onDeleteProfile = async () => {
    if (!window.confirm("确定删除抖音兴趣画像吗？此操作立即生效。")) return;
    try {
      await repos.taste.deleteDouyinProfile();
      setResult(null);
      showToast("画像已删除");
      void start(true);
    } catch (err) {
      showToast(errMessage(err));
    }
  };

  const pct =
    progress?.percent != null
      ? Math.round(progress.percent)
      : progress?.total
        ? Math.round((progress.current / Math.max(1, progress.total)) * 100)
        : null;

  return (
    <Screen id="screen-taste-import">
      <NavBar title="兴趣画像" backTo="/me" />
      <Scroll>
        {phase.kind === "starting" ? (
          <div className="taste-stage">
            <LuluSprite clip="home.thinking" size={150} />
            <div className="t-t2 mt-3">正在为你准备二维码</div>
            <div className="t-foot mt-1">噜噜正在联系抖音，马上就好。</div>
          </div>
        ) : null}

        {phase.kind === "scan" ? (
          <div className="taste-stage">
            <div className="qr-stage">
              {session?.qr_image_data_url ? (
                <img
                  key={session.qr_version}
                  className="qr-image"
                  src={session.qr_image_data_url}
                  alt="抖音登录二维码"
                />
              ) : (
                <div className="qr-image qr-loading">正在更新二维码…</div>
              )}
              <span className="qr-corner tl" /><span className="qr-corner tr" />
              <span className="qr-corner bl" /><span className="qr-corner br" />
            </div>
            <div className="t-t2 mt-4">打开抖音，扫一扫</div>
            <div className="t-foot mt-1">
              抖音 → 右上角「扫一扫」
              {secondsLeft !== null && secondsLeft > 0 ? (
                <span className="mono">
                  {" "}· {Math.floor(secondsLeft / 60)}:{String(secondsLeft % 60).padStart(2, "0")} 后自动换新
                </span>
              ) : null}
            </div>
            <div className="mt-5" style={{ width: "100%" }}>
              <Btn kind="ghost" onClick={onManualRefresh}>刷新二维码</Btn>
            </div>
            <div className="mt-4" style={{ width: "100%" }}>
              <Note sticker="qr-plaque-blank.png">
                扫码只在抖音内确认登录，噜噜不会保存你的账号密码；二维码过期会自动更新。
              </Note>
            </div>
            <LuluSprite clip="home.listening" size={96} caption="噜噜在等你扫码" />
          </div>
        ) : null}

        {phase.kind === "phone" ? (
          <div className="taste-stage">
            <LuluSprite clip="home.listening" size={110} />
            <Card className="mt-3" id="taste-phone-entry">
              <div className="t-t3">完成抖音手机号验证</div>
              <div className="t-foot mt-1">抖音要求补充手机号验证，验证码只发到你的手机。</div>
              <div className="flex mt-3" style={{ gap: 8 }}>
                <input
                  className="om-input"
                  style={{ width: 72, flex: "none" }}
                  placeholder="区号"
                  inputMode="numeric"
                  value={countryCode}
                  onChange={(e) => setCountryCode(e.target.value)}
                  aria-label="国家或地区代码"
                />
                <input
                  className="om-input"
                  placeholder="手机号"
                  inputMode="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  data-od-id="taste-phone-input"
                />
              </div>
              {phoneError ? <div className="t-foot mt-2">{phoneError}</div> : null}
              <div className="mt-3">
                <Btn
                  kind="primary"
                  disabled={phoneWorking || phone.replace(/\D/g, "").length < 5}
                  onClick={() => void onSendPhoneCode()}
                >
                  {phoneWorking ? "发送中…" : "发送短信验证码"}
                </Btn>
              </div>
            </Card>
          </div>
        ) : null}

        {phase.kind === "sms" ? (
          <div className="taste-stage">
            <LuluSprite clip="home.listening" size={110} />
            <Card className="mt-3" id="taste-sms-entry">
              <div className="t-t3">输入短信验证码</div>
              <div className="t-foot mt-1">
                {phoneMasked || progress?.phone_masked
                  ? `验证码已发送至 ${phoneMasked ?? progress?.phone_masked}`
                  : "验证码已发送；仅展示服务端返回的脱敏号码。"}
              </div>
              <input
                className="om-input mt-3"
                placeholder="4–8 位验证码"
                inputMode="numeric"
                type="password"
                value={smsCode}
                onChange={(e) => setSmsCode(e.target.value)}
                data-od-id="taste-phone-code-input"
              />
              {phoneError ? <div className="t-foot mt-2">{phoneError}</div> : null}
              <div className="mt-3">
                <Btn
                  kind="primary"
                  disabled={phoneWorking || smsCode.replace(/\D/g, "").length < 4}
                  onClick={() => void onSubmitSmsCode()}
                >
                  {phoneWorking ? "验证中…" : "验证并继续导入"}
                </Btn>
              </div>
              <div className="mt-2">
                <Btn kind="ghost" sm disabled={phoneWorking} onClick={() => void onCheckPhoneStatus()}>
                  检查验证码状态
                </Btn>
              </div>
            </Card>
          </div>
        ) : null}

        {phase.kind === "questions" ? (
          <div className="taste-stage" style={{ alignItems: "stretch" }}>
            <div className="t-t2 center mt-2">
              {phase.questions.optional ? "答几题，让画像更准" : "确认你的兴趣"}
            </div>
            <div className="t-foot center mt-1">
              {phase.questions.intro ??
                `服务端下发 ${phase.questions.questions?.length ?? 0} 道单选题；答完后 AI 会按你的选择再精修画像。`}
            </div>
            <div className="t-cap center mt-2">
              已选 {Object.keys(selections).length} / 需至少{" "}
              {Math.max(1, phase.questions.min_answers ?? 3)} 题
            </div>
            {(phase.questions.questions ?? []).map((q) => (
              <Card key={q.id} className="mt-2">
                <div className="t-t3">{q.prompt ?? "选一个更像你的"}</div>
                {(q.options ?? []).map((opt) => {
                  const on = selections[q.id] === opt.id;
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      className="om-row"
                      onClick={() =>
                        setSelections((cur) => {
                          const next = { ...cur };
                          if (on) delete next[q.id];
                          else next[q.id] = opt.id;
                          return next;
                        })
                      }
                    >
                      <span className="row-main">
                        <span className="row-title">{opt.label ?? opt.id}</span>
                      </span>
                      <span className="row-right">{on ? "●" : "○"}</span>
                    </button>
                  );
                })}
              </Card>
            ))}
            <div className="mt-3">
              <Btn
                kind="primary"
                disabled={
                  submittingQuiz ||
                  Object.keys(selections).length <
                    Math.max(1, phase.questions.min_answers ?? 3)
                }
                onClick={() => void onSubmitQuiz()}
              >
                {submittingQuiz ? "提交中…" : "提交并让 AI 精修"}
              </Btn>
            </div>
            <div className="mt-2">
              <Btn kind="ghost" onClick={() => setPhase(result ? { kind: "ready" } : { kind: "verified" })}>
                跳过，先用当前画像
              </Btn>
            </div>
          </div>
        ) : null}

        {phase.kind === "verified" ? (
          <div className="taste-stage">
            <LuluSprite clip="home.reply" size={110} />
            <div className="id-card">
              <DouyinAvatar profile={profile} size={64} />
              <div className="id-name">
                {profile?.nickname ?? "抖音用户"}
                <VerifiedBadge />
              </div>
              <div className="id-sub">抖音号 {profile?.uid ?? "—"} · 扫码识别成功</div>
            </div>
            <div className="t-foot center mt-3" style={{ maxWidth: 280 }}>
              接下来噜噜会读取你的「喜欢」，生成一张只属于你的兴趣画像卡。
            </div>
          </div>
        ) : null}

        {phase.kind === "generating" ? (
          <div className="taste-stage">
            <LuluSprite clip="home.thinking" size={150} />
            <div className="t-t2 mt-3">噜噜正在生成你的画像</div>
            <div className="t-foot mt-1">
              {progress?.message ?? "正在分析你的喜欢内容…"}
            </div>
            <div className="gen-progress">
              <div className="om-progress">
                <i style={{ width: `${pct ?? 12}%` }} />
              </div>
              <div className="gen-progress-meta mono">{pct !== null ? `${pct}%` : "…"}</div>
            </div>
          </div>
        ) : null}

        {phase.kind === "ready" && result ? (
          <PersonaCard result={result} profile={profile} />
        ) : null}

        {phase.kind === "failed" ? (
          <div className="taste-stage">
            <LuluSprite clip="core.care" size={140} />
            <div className="t-t2 mt-3">这次没成功</div>
            <div className="t-foot mt-1 center" style={{ maxWidth: 300 }}>{phase.message}</div>
            <div className="mt-5" style={{ width: "100%" }}>
              <Btn kind="primary" onClick={onRestart}>重新扫码</Btn>
            </div>
          </div>
        ) : null}
      </Scroll>

      {phase.kind === "verified" ? (
        <div className="om-footer over-sheet">
          <Btn kind="primary" onClick={onGenerate}>生成我的画像卡</Btn>
        </div>
      ) : null}

      {phase.kind === "ready" ? (
        <div className="om-footer over-sheet">
          {result && !result.calibrated ? (
            <Btn kind="primary" onClick={() => void onOpenQuestions()}>
              可选 · 答细化题
            </Btn>
          ) : null}
          <Btn kind="ghost" onClick={onRestart}>重新扫码导入</Btn>
          <Btn kind="text" sm onClick={() => void onDeleteProfile()}>
            删除抖音兴趣画像
          </Btn>
        </div>
      ) : null}

      <div className={`om-toast ${toast ? "show" : ""}`}>{toast}</div>
    </Screen>
  );
}
