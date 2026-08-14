import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import { AppBrand } from "../../core/brand";
import { asList, type CampusAction, type Gathering, type HermesAskResult, type HermesPeer, type TodaySummary } from "../../core/api/repositories";
import { normalizeSceneTrigger } from "../../core/campus/sceneTrigger";
import {
  campusEventDisplayType,
  campusEventLocation,
  campusEventTime,
} from "../../core/campus/events";
import { makeCampusActionCopy } from "../../core/campus/actionCopy";
import {
  BUS_CAMPUSES,
  busDayKind,
  busDepartures,
  campusShortLabel,
  findBusRoute,
  nextBusDeparture,
  type BusDayKind,
} from "../../core/campus/busSchedule";
import { sectionTime } from "../../core/campus/sectionTimes";
import {
  splitTimeRange,
  timelineDetail,
  timelineHref,
  timelineKindLabel,
  timelinePhase,
  timelineRange,
  type TimelineItem,
} from "../../core/campus/dayTimeline";
import { CAMPUS_HOME_TOOLS } from "../../core/campus/todayTools";
import {
  addDays,
  blocksFromGatherings,
  blocksFromTimetable,
  formatMonthDay,
  gridTitle,
  hourRange,
  startOfWeekMonday,
  timeRangeLabel,
  weekdayLabel,
  weekRangeLabel,
  type ScheduleBlock,
} from "../../core/campus/weekSchedule";
import { ActionReviewCard } from "../../components/campus/ActionReviewCard";
import { SessionExpiredWall } from "../../components/shell/SocialAccessGate";
import {
  Btn,
  Card,
  Chip,
  Icon,
  LuluMark,
  NavBar,
  PageHeader,
  Note,
  Row,
  Screen,
  Scroll,
  Section,
  Seg,
  StateView,
  Stepper,
  Sticker,
} from "../../components/ui/primitives";

function dateLine() {
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      month: "long",
      day: "numeric",
      weekday: "long",
    }).format(new Date());
  } catch {
    return "今天";
  }
}

function useOnline() {
  const [online, setOnline] = useState(
    () => typeof navigator === "undefined" || navigator.onLine,
  );
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}

function TodayTimeline({ items }: { items: TimelineItem[] }) {
  return (
    <div className="day-timeline" data-od-id="today-schedule-timeline">
      {items.map((item, i) => (
        <TodayTimelineRow
          key={item.id ?? i}
          item={item}
          isFirst={i === 0}
          isLast={i === items.length - 1}
        />
      ))}
    </div>
  );
}

function TodayTimelineRow({
  item,
  isFirst,
  isLast,
}: {
  item: TimelineItem;
  isFirst: boolean;
  isLast: boolean;
}) {
  const range = timelineRange(item);
  const [start, end] = splitTimeRange(range);
  const phase = timelinePhase(item);
  const kind = item.kind ?? "course";
  const detail = timelineDetail(item);
  return (
    <Link
      to={timelineHref(item)}
      className={`day-tl-item ${phase} ${isFirst ? "first" : ""} ${isLast ? "last" : ""}`}
    >
      <div className="day-tl-time-col">
        <div className="day-tl-time">{start || "—"}</div>
        {end ? <div className="day-tl-time end">{end}</div> : null}
      </div>
      <div className="day-tl-rail">
        <span className={`day-tl-dot ${phase} ${kind}`} />
      </div>
      <div className={`day-tl-card ${phase}`}>
        <div className="day-tl-card-head">
          <div className="day-tl-title">{item.title ?? "今日事项"}</div>
          <span className={`day-tl-chip ${kind}`}>{timelineKindLabel(kind)}</span>
        </div>
        {detail ? (
          <div className="day-tl-detail">
            <Icon name="pin" size={10} />
            <span>{detail}</span>
          </div>
        ) : null}
        {phase === "current" ? (
          <div className="day-tl-now">
            <span className="day-tl-now-dot" />
            进行中 · {range}
          </div>
        ) : null}
      </div>
    </Link>
  );
}

/** 未登录 Today Tab，对齐 iOS GuestDiscoveryView。 */
function GuestDiscoveryScreen() {
  const { repos, session } = useApp();
  const nav = useNavigate();
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setPhase("loading");
    try {
      setItems(asList(await repos.campus.events()) as Record<string, unknown>[]);
      setPhase("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPhase("failed");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  function goLogin() {
    session.setPendingRoute("/today");
    nav("/auth");
  }

  return (
    <Screen id="screen-B7-guest-events">
      <Scroll>
        <div className="between" style={{ alignItems: "flex-start", paddingTop: 8 }}>
          <div>
            <div className="t-foot" style={{ fontWeight: 700, letterSpacing: 2 }}>
              访客模式
            </div>
            <div className="t-hero mt-1">
              先看看校园，
              <br />
              登录后再加入
            </div>
          </div>
          <LuluMark placement="confirm" clip="home.idle" />
        </div>
        <Card tight className="mt-3">
          <div className="t-t3">登录后，噜噜才能帮你成局</div>
          <div className="t-foot mt-1">
            课表、订场、找搭子和组队比赛都需要先登录。访客只能看看公开活动。
          </div>
        </Card>
        <div className="mt-3" data-od-id="guest-login-cta">
          <Btn kind="primary" onClick={goLogin}>
            去登录
          </Btn>
        </div>
        <Section title="公开活动预览" />
        {phase === "loading" ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : null}
        {phase === "failed" ? (
          <Card>
            <StateView
              kind="network"
              message={error ?? undefined}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : null}
        {phase === "loaded" && items.length === 0 ? (
          <Card>
            <StateView kind="empty" />
          </Card>
        ) : null}
        {phase === "loaded"
          ? items.map((item, i) => {
              const id = String(item.id ?? i);
              const official =
                typeof item.official_url === "string"
                  ? item.official_url
                  : typeof item.officialUrl === "string"
                    ? item.officialUrl
                    : null;
              return (
                <Card key={id}>
                  <Chip kind="soft">
                    {campusEventDisplayType(String(item.type ?? ""))}
                  </Chip>
                  <div className="t-t3 mt-2">
                    {String(item.title ?? item.name ?? "活动")}
                  </div>
                  <div className="t-foot mt-2">{campusEventTime(item)}</div>
                  <div className="t-foot mt-1">{campusEventLocation(item)}</div>
                  {official ? (
                    <div className="mt-3">
                      <Btn kind="ghost" sm onClick={() => window.open(official, "_blank")}>
                        打开官方活动页
                      </Btn>
                    </div>
                  ) : (
                    <div className="t-cap mt-3">登录后可报名或找同行</div>
                  )}
                </Card>
              );
            })
          : null}
      </Scroll>
    </Screen>
  );
}

export function TodayScreen() {
  const { sessionState } = useApp();
  if (sessionState.status === "expired") {
    return <SessionExpiredWall />;
  }
  if (sessionState.status !== "authenticated") {
    return <GuestDiscoveryScreen />;
  }
  return <AuthenticatedTodayScreen />;
}

function AuthenticatedTodayScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const online = useOnline();
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [data, setData] = useState<TodaySummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hermes, setHermes] = useState("");
  const [ignoringScene, setIgnoringScene] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  async function load(force = false) {
    setPhase("loading");
    try {
      const summary = await repos.today.summary(force);
      setData(summary);
      setPhase("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPhase("failed");
    }
  }

  useEffect(() => {
    void load();
  }, [repos]);

  async function ignoreScene(key: string) {
    if (ignoringScene) return;
    setIgnoringScene(true);
    try {
      await repos.today.ignoreSceneTrigger(key);
      await load(true);
    } catch (e) {
      setToast(e instanceof Error ? e.message : "忽略失败");
      window.setTimeout(() => setToast(null), 2800);
    } finally {
      setIgnoringScene(false);
    }
  }

  return (
    <Screen id="screen-B1-today">
      <Scroll>
        <div className="om-header">
          <div className="om-header-text">
            <div className="t-foot" style={{ fontWeight: 600 }}>
              {dateLine()}
            </div>
            <div className="om-header-title">今天</div>
          </div>
          <LuluMark placement="avatar" clip="home.reply" />
        </div>

        {!online ? (
          <Card className="mt-3">
            <StateView
              kind="offline"
              message="可浏览缓存；写操作会等待网络恢复。"
            />
          </Card>
        ) : null}

        {phase === "loading" ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : null}
        {phase === "failed" ? (
          <Card>
            <StateView
              kind="network"
              message={error ?? undefined}
              actionTitle="重试"
              onAction={() => void load(true)}
            />
          </Card>
        ) : null}

        {phase === "loaded" && data?.scene_trigger ? (
          <Card className="mt-3" data-od-id="today-scene-trigger">
            <div className="flex" style={{ alignItems: "flex-start", gap: 10 }}>
              <LuluMark placement="avatar" clip="home.reply" />
              <div className="grow">
                <div className="t-t3">{data.scene_trigger.title ?? "现在有个合适的空档"}</div>
                <div className="t-foot mt-1">{data.scene_trigger.body}</div>
              </div>
            </div>
            <div className="flex mt-3" style={{ gap: 8 }}>
              <Btn
                kind="primary"
                sm
                onClick={() =>
                  nav("/today/scene", {
                    state: { scene_trigger: data.scene_trigger },
                  })
                }
              >
                看看详情
              </Btn>
              {data.scene_trigger.key ? (
                <Btn
                  kind="text"
                  sm
                  disabled={ignoringScene}
                  onClick={() => void ignoreScene(data.scene_trigger!.key)}
                >
                  忽略
                </Btn>
              ) : null}
            </div>
          </Card>
        ) : null}

        {phase === "loaded" ? (
          <>
            <Section title="今日日程" more={{ label: "周历", to: "/today/timetable" }} />
            {data?.timeline && data.timeline.length > 0 ? (
              <TodayTimeline items={data.timeline} />
            ) : (
              <Card>
                <div className="flex">
                  <Sticker name="desk-calendar.png" size="st-44" />
                  <div className="t-foot" style={{ marginLeft: 10 }}>
                    今天没有课，也没有安排中的活动。
                  </div>
                </div>
              </Card>
            )}
          </>
        ) : null}

        <Card className="mt-3" data-od-id="today-hermes-entry">
          <div className="flex">
            <LuluMark placement="avatar" clip="home.listening" />
            <div className="grow">
              <div className="t-t3">问问 {AppBrand.agentName}</div>
              <div className="t-cap">课表、DDL、场地、公选匹配</div>
            </div>
          </div>
          <div className="flex mt-3">
            <input
              className="om-input"
              style={{ minHeight: 42, borderRadius: 999 }}
              placeholder="例如：按我的画像推荐公选"
              value={hermes}
              onChange={(e) => setHermes(e.target.value)}
              data-od-id="today-hermes-input"
              onKeyDown={(e) => {
                if (e.key === "Enter") nav("/today/ask", { state: { q: hermes } });
              }}
            />
            <button
              type="button"
              className="nav-back"
              aria-label="提问"
              onClick={() => nav("/today/ask", { state: { q: hermes } })}
            >
              <Icon name="arrow" size={18} />
            </button>
          </div>
        </Card>

        <Section title="校园工具" />
        <Card>
          <div className="campus-tool-grid">
            {CAMPUS_HOME_TOOLS.map((t) => (
              <Link key={t.to} to={t.to} data-od-id={t.id}>
                <Sticker name={t.sticker} size="st-44" />
                <div className="t-cap" style={{ color: "var(--ink)", fontWeight: 600, marginTop: 6 }}>
                  {t.label}
                </div>
              </Link>
            ))}
          </div>
        </Card>
      </Scroll>
      <div className={`om-toast ${toast ? "show" : ""}`}>{toast}</div>
    </Screen>
  );
}

export function HermesAskScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const location = useLocation();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [q, setQ] = useState("");
  const [messages, setMessages] = useState<HermesChatMsg[]>([]);
  const [busy, setBusy] = useState(false);
  const [startingPeer, setStartingPeer] = useState<string | null>(null);
  const [peerError, setPeerError] = useState<string | null>(null);
  const draftConsumed = useRef(false);

  const suggestions = [
    "按我的画像推荐公选",
    "今天有什么课？",
    "宿舍晚上会断电吗？",
    "还有谁也选了机器学习？",
    "还有谁也约了羽毛球？",
  ];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  useEffect(() => {
    if (draftConsumed.current) return;
    const draft = (location.state as { q?: string } | null)?.q?.trim();
    if (draft) {
      draftConsumed.current = true;
      void ask(draft);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state]);

  function uid() {
    return crypto.randomUUID();
  }

  async function ask(text = q) {
    const value = text.trim();
    if (!value || busy) return;
    setBusy(true);
    setPeerError(null);
    const thinkingId = uid();
    setMessages((prev) => [
      ...prev,
      { id: uid(), kind: "user", text: value },
      { id: thinkingId, kind: "thinking", text: "正在询问校园 Agent…", active: true },
    ]);
    setQ("");
    try {
      const res = await repos.hermes.ask(value);
      const traces = res.tool_trace ?? res.data?.tool_trace ?? [];
      setMessages((prev) => {
        const next = prev.map((m) =>
          m.id === thinkingId
            ? {
                ...m,
                text: traces.length ? "已理解意图，正在调用校园工具" : "已完成回复",
                active: false,
              }
            : m,
        );
        for (const trace of traces) {
          next.push({
            id: uid(),
            kind: "tool",
            text:
              trace.summary ||
              (trace.ok === false ? "调用失败" : "已完成"),
            toolName: trace.name,
          });
        }
        next.push({
          id: uid(),
          kind: "answer",
          text: hermesAnswerText(res),
        });
        next.push({ id: uid(), kind: "result", result: res });
        return next;
      });
    } catch (e) {
      const message = e instanceof Error ? e.message : "提问失败";
      setMessages((prev) => [
        ...prev.map((m) =>
          m.id === thinkingId
            ? { ...m, text: "询问失败", active: false }
            : m,
        ),
        { id: uid(), kind: "error", text: message },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function startChat(peer: HermesPeer) {
    if (startingPeer) return;
    setStartingPeer(peer.user_id);
    setPeerError(null);
    try {
      const opened = await repos.hermes.startPeerChat({
        peer_user_id: peer.user_id,
        reason: peer.reason,
        overlap: peer.overlap,
      });
      nav(`/channel/${opened.channel_id}`);
    } catch (e) {
      setPeerError(e instanceof Error ? e.message : "发起聊天失败");
    } finally {
      setStartingPeer(null);
    }
  }

  return (
    <Screen id="screen-B2-hermes" className="hermes-screen">
      <NavBar backTo="/today" />
      <div className="hermes-thread">
        <div className="hermes-intro">
          <div className="flex" style={{ alignItems: "center", gap: 10 }}>
            <LuluMark placement="avatar" clip="home.listening" />
            <div>
              <div className="t-t3">{AppBrand.agentName}</div>
              <div className="t-cap">校园事务助手 · 会先想清楚再查工具</div>
            </div>
          </div>
          <div className="bubble-sys mt-3">课表 · DDL · 场地 · 公选 · 同课/同时段的人</div>
        </div>
        {messages.length === 0 ? (
          <div className="mt-3">
            <div className="t-cap mb-2">试试这样问</div>
            <div className="flex wrap" style={{ gap: 8 }}>
              {suggestions.map((c) => (
                <Chip key={c} kind="soft" onClick={() => void ask(c)}>
                  {c}
                </Chip>
              ))}
            </div>
          </div>
        ) : null}
        {messages.map((message) => (
          <HermesRow
            key={message.id}
            message={message}
            startingPeer={startingPeer}
            peerError={peerError}
            onStartChat={(peer) => void startChat(peer)}
            onPreview={(action, params) =>
              nav("/today/action-preview", { state: { action, params } })
            }
          />
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="hermes-composer">
        <input
          className="om-input"
          placeholder="问校园相关的事…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void ask();
          }}
          data-od-id="hermes-input"
          id="hermes-question-input"
        />
        <button
          type="button"
          className="hermes-send"
          disabled={busy || !q.trim()}
          onClick={() => void ask()}
          aria-label="发送"
        >
          {busy ? "…" : "↑"}
        </button>
      </div>
    </Screen>
  );
}

type HermesChatMsg =
  | { id: string; kind: "user"; text: string }
  | { id: string; kind: "thinking"; text: string; active?: boolean }
  | { id: string; kind: "tool"; text: string; toolName?: string }
  | { id: string; kind: "answer"; text: string }
  | { id: string; kind: "result"; result: HermesAskResult }
  | { id: string; kind: "error"; text: string };

function hermesAnswerText(res: HermesAskResult): string {
  const items = res.data?.items;
  const hasItems = Array.isArray(items) && items.length > 0;
  const raw = String(res.data?.message ?? res.answer ?? res.text ?? res.message ?? "");
  if (raw) return compactHermesMessage(raw, res.card_type, hasItems);
  if (res.kind === "help") return "我主要处理课表、DDL、场地、活动、班车、校园日常知识，以及按画像推荐公选。";
  if (res.kind === "clarification") return "还差几个参数，补齐后我就能继续查。";
  if (res.kind === "action_preview") return "已生成预览，确认后再执行。";
  if (res.card_type === "elective_match") return "按你的画像挑了这几门。";
  return "查到了，结果在下面。";
}

function compactHermesMessage(
  raw: string,
  cardType?: string,
  hasStructuredItems?: boolean,
): string {
  let text = raw
    .replace(/提醒一句[：:].*?(不会自动帮你选课|不会自动选课)[。.]?/g, "")
    .replace(/这只是只读推荐[^。\n]*[。.]?/g, "")
    .replace(/只读推荐[，,]不会自动选课[。.]?/g, "")
    .replace(/正式选课请在教务确认[。.]?/g, "")
    .replace(/不会自动帮你选课[。.]?/g, "")
    .replace(/不会自动选课[。.]?/g, "")
    .replace(/不会代选课[。.]?/g, "")
    .replace(/\n{3,}/g, "\n\n");
  if (hasStructuredItems) {
    const cut = text.search(/\n?\s*1[\.、]/);
    if (cut >= 0) text = text.slice(0, cut);
    for (const marker of ["几点提醒", "提醒一句", "想再按", "需要我帮你", "要不要我"]) {
      const i = text.indexOf(marker);
      if (i >= 0) text = text.slice(0, i);
    }
  }
  text = text.trim();
  if (!text) return cardType === "elective_match" ? "按你的画像挑了这几门。" : "查到了。";
  return text;
}

function HermesRow({
  message,
  startingPeer,
  peerError,
  onStartChat,
  onPreview,
}: {
  message: HermesChatMsg;
  startingPeer: string | null;
  peerError: string | null;
  onStartChat: (peer: HermesPeer) => void;
  onPreview: (action: string, params: Record<string, unknown>) => void;
}) {
  if (message.kind === "user") {
    return (
      <div className="bubble-group me mt-3">
        <div className="bubble me">{message.text}</div>
      </div>
    );
  }
  if (message.kind === "thinking" || message.kind === "tool") {
    return (
      <div className="hermes-step">
        <span className="hermes-step-label">
          {message.kind === "tool" ? "调用工具" : "思考"}
        </span>
        {message.kind === "tool" && message.toolName ? (
          <span className="hermes-tool-name">{message.toolName}</span>
        ) : null}
        <span className="t-cap">
          {message.kind === "thinking" && message.active ? "…" : message.text}
        </span>
      </div>
    );
  }
  if (message.kind === "answer") {
    return (
      <div className="flex mt-3" style={{ alignItems: "flex-start", gap: 8 }}>
        <LuluMark placement="avatar" clip="home.reply" />
        <div className="bubble" data-od-id="hermes-answer">
          {message.text}
        </div>
      </div>
    );
  }
  if (message.kind === "error") {
    return (
      <Card className="mt-3">
        <StateView kind="network" message={message.text} />
      </Card>
    );
  }
  return (
    <HermesResultBlock
      result={message.result}
      startingPeer={startingPeer}
      peerError={peerError}
      onStartChat={onStartChat}
      onPreview={onPreview}
    />
  );
}

function HermesResultBlock({
  result,
  startingPeer,
  peerError,
  onStartChat,
  onPreview,
}: {
  result: HermesAskResult;
  startingPeer: string | null;
  peerError: string | null;
  onStartChat: (peer: HermesPeer) => void;
  onPreview: (action: string, params: Record<string, unknown>) => void;
}) {
  const data = result.data ?? {};
  const peers = Array.isArray(data.peers) ? data.peers : [];
  const params =
    data.params && typeof data.params === "object"
      ? (data.params as Record<string, unknown>)
      : null;
  const copy =
    (result.kind === "action_preview" || result.requires_preview) && params
      ? makeCampusActionCopy({
          action_name: result.action,
          status: "previewed",
          params,
        })
      : result.action && params
        ? makeCampusActionCopy({
            action_name: result.action,
            status: "previewed",
            params,
          })
        : null;
  const items = Array.isArray(data.items) ? data.items : [];
  const showElective = result.card_type === "elective_match" && items.length > 0;
  const showGeneric =
    !copy &&
    !showElective &&
    result.card_type !== "peer_list" &&
    result.kind !== "help" &&
    result.card_type !== "agent_reply" &&
    result.card_type !== "knowledge_answer" &&
    result.kind !== "clarification" &&
    items.length > 0;

  return (
    <div className="stack mt-3" style={{ gap: 10 }}>
      {showElective ? (
        <Card>
          <div className="between">
            <div className="t-t3">公选匹配</div>
            {data.persona_label ? (
              <Chip kind="soft">{String(data.persona_label)}</Chip>
            ) : null}
          </div>
          {items.map((item, i) => (
            <div key={i} className="mt-3">
              <div className="t-call">
                {String(item.name ?? item.title ?? item.course_name ?? `课程 ${i + 1}`)}
              </div>
              {item.match_reasons || item.reason ? (
                <div className="t-cap mt-1">
                  {Array.isArray(item.match_reasons)
                    ? item.match_reasons.join(" · ")
                    : String(item.reason ?? "")}
                </div>
              ) : null}
            </div>
          ))}
        </Card>
      ) : null}
      {copy ? (
        <ActionReviewCard copy={copy} testId="hermes-action-copy-card">
          {result.requires_preview && result.action && params ? (
            <Btn
              kind="ghost"
              sm
              id="hermes-open-action-preview"
              onClick={() => onPreview(result.action!, params)}
            >
              去核对预约
            </Btn>
          ) : null}
        </ActionReviewCard>
      ) : null}
      {showGeneric ? (
        <Card>
          {items.map((item, i) => (
            <div key={i} className={i ? "mt-2" : undefined}>
              <div className="t-call">
                {String(item.title ?? item.name ?? item.course_name ?? `结果 ${i + 1}`)}
              </div>
              {item.summary || item.location || item.time_label ? (
                <div className="t-cap mt-1">
                  {String(item.summary ?? item.location ?? item.time_label)}
                </div>
              ) : null}
            </div>
          ))}
        </Card>
      ) : null}
      {Array.isArray(data.hits) && data.hits.length > 0 ? (
        <Card>
          <div className="t-t3">依据校园知识库</div>
          {data.hits.map((hit, i) => (
            <div key={i} className="mt-2">
              <div className="t-call">{String(hit.title ?? `条目 ${i + 1}`)}</div>
              {hit.snippet ? <div className="t-cap mt-1">{String(hit.snippet)}</div> : null}
            </div>
          ))}
        </Card>
      ) : null}
      {peers.length > 0 ? (
        <Card data-od-id="hermes-peers">
          <div className="t-t3">可能合得来的人</div>
          {peers.map((peer) => (
            <div key={peer.user_id} className="mt-3">
              <div className="t-call">
                {peer.display_name}
                {peer.persona_label ? ` · ${peer.persona_label}` : ""}
              </div>
              <div className="t-cap mt-1">{peer.reason}</div>
              <Btn
                kind="ghost"
                sm
                disabled={Boolean(startingPeer)}
                onClick={() => onStartChat(peer)}
              >
                {startingPeer === peer.user_id ? "正在发起…" : "一键发起聊天"}
              </Btn>
            </div>
          ))}
          {peerError ? <div className="t-foot mt-2">{peerError}</div> : null}
        </Card>
      ) : null}
      {result.requires_preview && result.action && params && !copy ? (
        <Btn
          kind="ghost"
          sm
          id="hermes-open-action-preview"
          onClick={() => onPreview(result.action!, params)}
        >
          去核对预约
        </Btn>
      ) : null}
    </div>
  );
}

function ApiListScreen({
  id,
  title,
  eyebrow,
  clip,
  load,
  mapRow,
  back = "/today",
}: {
  id: string;
  title: string;
  eyebrow?: string;
  clip?: "home.idle" | "home.thinking" | "home.listening";
  load: () => Promise<unknown>;
  mapRow: (
    item: Record<string, unknown>,
    index: number,
  ) => { title: string; sub?: string; to?: string; right?: string; chipKind?: string };
  back?: string;
}) {
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [rows, setRows] = useState<
    Array<{ title: string; sub?: string; to?: string; right?: string; chipKind?: string }>
  >([]);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setPhase("loading");
    try {
      const raw = await load();
      const list = Array.isArray(raw)
        ? raw
        : Array.isArray((raw as { items?: unknown[] })?.items)
          ? (raw as { items: unknown[] }).items
          : [];
      setRows(
        list.map((item, i) =>
          mapRow((item ?? {}) as Record<string, unknown>, i),
        ),
      );
      setPhase("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPhase("failed");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <Screen id={id}>
      <NavBar backTo={back} />
      <Scroll>
        <PageHeader eyebrow={eyebrow} title={title} clip={clip} />
        {phase === "loading" ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : null}
        {phase === "failed" ? (
          <Card>
            <StateView
              kind="network"
              message={error ?? undefined}
              actionTitle="重试"
              onAction={() => void refresh()}
            />
          </Card>
        ) : null}
        {phase === "loaded" && rows.length === 0 ? (
          <Card>
            <StateView kind="empty" />
          </Card>
        ) : null}
        {phase === "loaded" && rows.length > 0 ? (
          <Card tight>
            {rows.map((r, i) => (
              <Row
                key={i}
                icon={<Icon name="clock" size={20} />}
                title={r.title}
                sub={r.sub}
                to={r.to}
                right={
                  r.right ? (
                    <span className={`om-chip ${r.chipKind ?? ""}`}>
                      {r.right}
                    </span>
                  ) : undefined
                }
              />
            ))}
          </Card>
        ) : null}
      </Scroll>
    </Screen>
  );
}

export function TimetableScreen() {
  const { repos } = useApp();
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [entries, setEntries] = useState<Array<Record<string, unknown>>>([]);
  const [gatherings, setGatherings] = useState<Gathering[]>([]);
  const [week, setWeek] = useState(1);
  const [windowStart, setWindowStart] = useState(0);
  const [anchor, setAnchor] = useState<{ week: number; monday: Date } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const located = useRef(false);

  async function load() {
    setPhase("loading");
    try {
      const [raw, mine] = await Promise.all([
        repos.campus.timetable(week),
        repos.gatherings.mine().catch(() => [] as Gathering[] | { items: Gathering[] }),
      ]);
      const record = raw as {
        entries?: unknown[];
        courses?: unknown[];
        items?: unknown[];
      };
      const list = Array.isArray(raw)
        ? raw
        : Array.isArray(record?.entries)
          ? record.entries
          : Array.isArray(record?.courses)
            ? record.courses
            : Array.isArray(record?.items)
              ? record.items
              : [];
      setEntries(list as Array<Record<string, unknown>>);
      setGatherings(asList(mine));
      setPhase("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPhase("failed");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos, week]);

  const courseBlocks = blocksFromTimetable(entries);
  const earliestCourse = courseBlocks
    .map((b) => b.start)
    .sort((a, b) => a.getTime() - b.getTime())[0];
  const earliestTs = earliestCourse?.getTime() ?? null;
  const weekStart = earliestCourse
    ? startOfWeekMonday(earliestCourse)
    : anchor
      ? addDays(anchor.monday, 7 * (week - anchor.week))
      : null;
  const gatheringBlocks = weekStart
    ? blocksFromGatherings(gatherings, weekStart)
    : [];
  const blocks = [...courseBlocks, ...gatheringBlocks];

  useEffect(() => {
    if (earliestTs == null) return;
    const monday = startOfWeekMonday(new Date(earliestTs));
    setAnchor((prev) =>
      prev && prev.week === week && prev.monday.getTime() === monday.getTime()
        ? prev
        : { week, monday },
    );
  }, [earliestTs, week]);

  useEffect(() => {
    if (!weekStart || located.current) return;
    located.current = true;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const index = Math.round((today.getTime() - weekStart.getTime()) / 86_400_000);
    setWindowStart((0 <= index && index < 7) ? Math.min(index, 4) : 0);
  }, [weekStart]);

  const currentWeek = (() => {
    if (!anchor) return null;
    const todayMonday = startOfWeekMonday(new Date());
    const days = Math.round(
      (todayMonday.getTime() - anchor.monday.getTime()) / 86_400_000,
    );
    const target = anchor.week + Math.round(days / 7);
    return target >= 1 && target <= 30 ? target : null;
  })();

  return (
    <Screen id="screen-B3-timetable">
      <NavBar backTo="/today" />
      <Scroll>
        <PageHeader title="我的日程" clip="home.idle" />
        <Card tight>
          <div className="week-switcher">
            <button
              type="button"
              className="week-shift"
              disabled={week <= 1}
              aria-label="上一周"
              onClick={() => setWeek((w) => Math.max(1, w - 1))}
            >
              ‹
            </button>
            <div className="week-switcher-title">
              <div className="t-call" style={{ fontWeight: 700 }}>
                第 {week} 周
              </div>
              {weekStart ? (
                <div className="t-cap">{weekRangeLabel(weekStart)}</div>
              ) : null}
            </div>
            {currentWeek && currentWeek !== week ? (
              <button
                type="button"
                className="week-this"
                onClick={() => setWeek(currentWeek)}
              >
                本周
              </button>
            ) : null}
            <button
              type="button"
              className="week-shift"
              disabled={week >= 30}
              aria-label="下一周"
              onClick={() => setWeek((w) => Math.min(30, w + 1))}
            >
              ›
            </button>
          </div>
        </Card>
        {phase === "loading" ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : null}
        {phase === "failed" ? (
          <Card>
            <StateView
              kind="network"
              message={error ?? undefined}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : null}
        {phase === "loaded" && weekStart ? (
          <>
            <div className="week-legend mt-3">
              <span>
                <i className="week-dot course" /> 课程
              </span>
              <span>
                <i className="week-dot gathering" /> 约局
              </span>
              <span className="t-cap">滑动看更多天</span>
            </div>
            <Card tight className="mt-2">
              <WeekScheduleGrid
                weekStart={weekStart}
                blocks={blocks}
                windowStart={windowStart}
                onWindowStart={setWindowStart}
                onOverflow={(dir) => {
                  const target = week + dir;
                  if (target < 1 || target > 30) return;
                  setWindowStart(dir > 0 ? 0 : 4);
                  setWeek(target);
                }}
              />
            </Card>
            {blocks.length === 0 ? (
              <div className="t-cap center mt-2">
                这周暂时空着；发起一局，让它热闹起来。
              </div>
            ) : null}
          </>
        ) : null}
        {phase === "loaded" && !weekStart ? (
          <Card>
            <StateView kind="empty" message="这周还没有日程数据。" />
          </Card>
        ) : null}
        <Note>仅显示你的缓存课表与已入的局；不会展示教务内部编码。</Note>
      </Scroll>
    </Screen>
  );
}

function WeekScheduleGrid({
  weekStart,
  blocks,
  windowStart,
  onWindowStart,
  onOverflow,
}: {
  weekStart: Date;
  blocks: ScheduleBlock[];
  windowStart: number;
  onWindowStart: (next: number) => void;
  onOverflow: (dir: number) => void;
}) {
  const visibleDays = 3;
  const days = [0, 1, 2].map((i) => addDays(weekStart, windowStart + i));
  const lower = days[0];
  const upper = addDays(days[2], 1);
  const visible = blocks.filter((b) => b.start >= lower && b.start < upper);
  const hours = hourRange(visible);
  const hourHeight = 36;
  const gutter = 28;
  const totalHours = Math.max(1, hours.end - hours.start);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  function shift(dir: number) {
    const next = windowStart + dir;
    if (next < 0) onOverflow(-1);
    else if (next > 7 - visibleDays) onOverflow(1);
    else onWindowStart(next);
  }

  return (
    <div data-od-id="week-schedule-grid">
      <div className="week-grid-head">
        <button type="button" className="week-shift" onClick={() => shift(-1)} aria-label="前一天">
          ‹
        </button>
        {days.map((day) => {
          const isToday = day.getTime() === today.getTime();
          return (
            <div key={day.toISOString()} className={`week-day ${isToday ? "today" : ""}`}>
              <div className="t-cap">{weekdayLabel(day)}</div>
              <div className={isToday ? "week-day-num today" : "week-day-num"}>
                {formatMonthDay(day)}
              </div>
            </div>
          );
        })}
        <button type="button" className="week-shift" onClick={() => shift(1)} aria-label="后一天">
          ›
        </button>
      </div>
      <div
        className="week-grid-body"
        style={{
          height: totalHours * hourHeight,
          gridTemplateColumns: `${gutter}px repeat(3, 1fr)`,
        }}
      >
        {Array.from({ length: totalHours }, (_, i) => hours.start + i).map((hour) => (
          <div
            key={hour}
            className="week-hour"
            style={{ top: (hour - hours.start) * hourHeight }}
          >
            {String(hour).padStart(2, "0")}
          </div>
        ))}
        {visible.map((block) => {
          const dayStart = new Date(
            block.start.getFullYear(),
            block.start.getMonth(),
            block.start.getDate(),
          );
          const col = Math.round((dayStart.getTime() - lower.getTime()) / 86_400_000);
          if (col < 0 || col > 2) return null;
          const startMin = block.start.getHours() * 60 + block.start.getMinutes();
          const endMin = block.end.getHours() * 60 + block.end.getMinutes();
          const top = ((startMin - hours.start * 60) / 60) * hourHeight;
          const height = Math.max(28, ((endMin - startMin) / 60) * hourHeight);
          const past = block.end.getTime() < Date.now();
          return (
            <Link
              key={block.id}
              to={block.href}
              className={`week-block ${block.kind}${past ? " past" : ""}`}
              style={{
                left: `calc(${gutter}px + ${col} * (100% - ${gutter}px) / 3)`,
                width: `calc((100% - ${gutter}px) / 3 - 4px)`,
                top,
                height,
              }}
            >
              <div className="week-block-title">{gridTitle(block.title)}</div>
              <div className="week-block-time">{timeRangeLabel(block.start, block.end)}</div>
              {block.detail ? (
                <div className="week-block-detail">{block.detail}</div>
              ) : null}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export function CourseDetailScreen() {
  const { courseId } = useParams();
  const { repos } = useApp();
  const [item, setItem] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!courseId) return;
    void repos.campus
      .course(courseId)
      .then(setItem)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, [courseId, repos]);

  return (
    <Screen id="screen-B3.1-course-detail">
      <NavBar backTo="/today/timetable" />
      <Scroll>
        <PageHeader eyebrow="课程" title="课程详情" clip="home.thinking" />
        {error ? (
          <Card>
            <StateView kind="network" message={error} />
          </Card>
        ) : !item ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : (
          <>
            <Card>
              <div className="t-t2">{String(item.name ?? item.title ?? "课程")}</div>
              <div className="t-foot mt-2">{`课程 · ${courseId ?? ""}`}</div>
            </Card>
            <Card tight>
              <Row
                icon={<Icon name="clock" size={20} />}
                title={String(item.time_label ?? item.schedule ?? "时间未提供")}
                sub={String(item.weeks ?? item.term ?? "")}
              />
              <Row
                icon={<Icon name="pin" size={20} />}
                title={String(item.location ?? item.building ?? "地点未提供")}
                sub={String(item.campus ?? "")}
              />
            </Card>
            <div className="mt-3">
              <Btn kind="primary" to="/intent">
                就这门课发起复习局
              </Btn>
            </div>
          </>
        )}
      </Scroll>
    </Screen>
  );
}

export function AssignmentsScreen() {
  const { repos } = useApp();
  return (
    <ApiListScreen
      id="screen-B4-assignments"
      eyebrow="截止在即"
      title="未完成作业"
      clip="home.thinking"
      load={() => repos.campus.assignments()}
      mapRow={(item, i) => ({
        title: String(item.title ?? item.name ?? `作业 ${i + 1}`),
        sub: String(item.course_name ?? item.course ?? item.due_at ?? ""),
        to: `/today/assignment/${item.id ?? i}`,
        right: item.urgent ? "紧急" : undefined,
        chipKind: item.urgent ? "gap" : undefined,
      })}
    />
  );
}

export function AssignmentDetailScreen() {
  const { assignmentId } = useParams();
  const { repos } = useApp();
  const [item, setItem] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!assignmentId) return;
    void repos.campus
      .assignment(assignmentId)
      .then(setItem)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, [assignmentId, repos]);

  return (
    <Screen id="screen-B4.1-assignment-detail">
      <NavBar backTo="/today/assignments" />
      <Scroll>
        <PageHeader
          eyebrow="作业"
          title={String(item?.title ?? item?.name ?? "作业")}
          clip="home.thinking"
        />
        {error ? (
          <Card>
            <StateView kind="network" message={error} />
          </Card>
        ) : !item ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : (
          <>
            <Card tight>
              <Row
                icon={<Icon name="clock" size={20} />}
                title={String(item.due_at ?? item.deadline ?? "截止时间未提供")}
                sub={String(item.course_name ?? item.course ?? "")}
              />
            </Card>
            {item.description || item.summary ? (
              <Card>
                <div className="t-call">{String(item.description ?? item.summary)}</div>
              </Card>
            ) : null}
            <Btn kind="primary" to="/intent">
              发起研讨局
            </Btn>
            <Btn kind="ghost" to="/today/action-preview">
              单人行动预览
            </Btn>
          </>
        )}
      </Scroll>
    </Screen>
  );
}

export function GymScreen() {
  return <VenueToolScreen kind="gym" />;
}

export function RoomScreen() {
  return <VenueToolScreen kind="room" />;
}

function localDayInput(offsetDays = 1): string {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function venueSlotRows(result: Record<string, unknown> | null): Array<Record<string, unknown>> {
  if (!result) return [];
  for (const key of ["slots", "items", "venues", "rooms", "options"]) {
    const value = result[key];
    if (Array.isArray(value)) return value as Array<Record<string, unknown>>;
  }
  return [];
}

function VenueToolScreen({ kind }: { kind: "gym" | "room" }) {
  const { repos } = useApp();
  const nav = useNavigate();
  const isRoom = kind === "room";
  const [category, setCategory] = useState(isRoom ? "15" : "羽毛球");
  const [date, setDate] = useState(() => localDayInput(1));
  const [resource, setResource] = useState("");
  const [start, setStart] = useState("19:00");
  const [end, setEnd] = useState("21:00");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  async function query() {
    if (!category.trim() || working) return;
    setWorking(true);
    setError(null);
    try {
      const data = isRoom
        ? await repos.campus.roomAvailable({ kind: category.trim(), date, room: resource || undefined })
        : await repos.campus.gymAvailable({
            venueType: category.trim(),
            date,
            venue: resource || undefined,
          });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "查询失败");
      setResult(null);
    } finally {
      setWorking(false);
    }
  }

  const canPreview = Boolean(resource.trim()) && start < end;
  const slots = venueSlotRows(result);

  return (
    <Screen id={isRoom ? "screen-B6-room" : "screen-B5-gym"}>
      <NavBar backTo="/today" />
      <Scroll>
        <PageHeader
          eyebrow={isRoom ? "可预约空间" : "运动场地"}
          title={isRoom ? "图书馆研讨室" : "体育场馆"}
          clip="home.idle"
        />
        <Card>
          <input
            className="om-input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder={isRoom ? "房型（如 15）" : "项目（如 羽毛球）"}
          />
          <input
            className="om-input mt-2"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <Btn
            kind="primary"
            disabled={working || !category.trim()}
            onClick={() => void query()}
          >
            {working ? "查询中…" : "查询实时空档"}
          </Btn>
        </Card>
        {error ? (
          <Card>
            <StateView
              kind="network"
              message={error}
              actionTitle="重试"
              onAction={() => void query()}
            />
          </Card>
        ) : null}
        {result ? (
          <Card>
            <div className="t-t3">服务端空档</div>
            {slots.length > 0 ? (
              slots.slice(0, 12).map((slot, i) => (
                <Row
                  key={i}
                  title={String(slot.name ?? slot.venue ?? slot.room ?? slot.label ?? `空档 ${i + 1}`)}
                  sub={String(slot.slot ?? slot.start ?? slot.location ?? slot.status ?? "")}
                  onClick={() => {
                    const name = String(slot.name ?? slot.venue ?? slot.room ?? "");
                    if (name) setResource(name);
                    if (typeof slot.start === "string") setStart(slot.start.slice(0, 5));
                    if (typeof slot.end === "string") setEnd(slot.end.slice(0, 5));
                  }}
                />
              ))
            ) : (
              <div className="t-foot mt-2">
                {typeof result.message === "string"
                  ? result.message
                  : "已返回空档结果。填写资源与时段后可生成预览。"}
              </div>
            )}
          </Card>
        ) : null}
        <Card>
          <div className="t-t3">选择时段并生成预览</div>
          <input
            className="om-input mt-2"
            value={resource}
            onChange={(e) => setResource(e.target.value)}
            placeholder={isRoom ? "研讨室编号" : "场馆名称"}
          />
          <div className="flex mt-2" style={{ gap: 8 }}>
            <input
              className="om-input"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              placeholder="开始 HH:mm"
            />
            <input
              className="om-input"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              placeholder="结束 HH:mm"
            />
          </div>
          <Btn
            kind="primary"
            disabled={!canPreview}
            onClick={() =>
              nav("/today/action-preview", {
                state: isRoom
                  ? {
                      action: "room.reserve_preview",
                      params: {
                        kind: category,
                        room: resource,
                        date,
                        start,
                        end,
                        members: [],
                        services: [],
                      },
                    }
                  : {
                      action: "gym.book_preview",
                      params: {
                        venue_type: category,
                        venue: resource,
                        date,
                        start,
                        end,
                      },
                    },
              })
            }
          >
            进入个人行动预览
          </Btn>
        </Card>
        {!isRoom ? (
          <Btn kind="ghost" to="/intent?preset=sport" id="gym-find-sport-partner">
            用这个时段找运动搭子
          </Btn>
        ) : (
          <Note>研讨室预约以学校图书馆系统为准。噜噜只做代预约，且每次都会先给你看预览。</Note>
        )}
      </Scroll>
    </Screen>
  );
}

export function EventsScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);

  async function load() {
    setPhase("loading");
    try {
      setItems(asList(await repos.campus.events()) as Record<string, unknown>[]);
      setPhase("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPhase("failed");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos]);

  const types = items.reduce<string[]>((acc, item) => {
    const t = campusEventDisplayType(String(item.type ?? ""));
    if (!acc.includes(t)) acc.push(t);
    return acc;
  }, []);
  const visible = typeFilter
    ? items.filter(
        (item) => campusEventDisplayType(String(item.type ?? "")) === typeFilter,
      )
    : items;

  return (
    <Screen id="screen-B7-events">
      <NavBar backTo="/today" />
      <Scroll>
        <PageHeader eyebrow="官方活动" title="校园活动" clip="core.celebrate" />
        {types.length >= 2 ? (
          <div className="om-seg mb-3">
            <button
              type="button"
              className={typeFilter == null ? "on" : ""}
              onClick={() => setTypeFilter(null)}
            >
              全部
            </button>
            {types.map((t) => (
              <button
                key={t}
                type="button"
                className={typeFilter === t ? "on" : ""}
                onClick={() => setTypeFilter(t)}
              >
                {t}
              </button>
            ))}
          </div>
        ) : null}
        {phase === "loading" ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : null}
        {phase === "failed" ? (
          <Card>
            <StateView
              kind="network"
              message={error ?? undefined}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : null}
        {phase === "loaded" && visible.length === 0 ? (
          <Card>
            <StateView kind="empty" />
          </Card>
        ) : null}
        {phase === "loaded"
          ? visible.map((item, i) => {
              const id = String(item.id ?? i);
              return (
                <Card key={id} onClick={() => nav(`/today/event/${id}`)}>
                  <Chip kind="soft">
                    {campusEventDisplayType(String(item.type ?? ""))}
                  </Chip>
                  <div className="t-t3 mt-2">
                    {String(item.title ?? item.name ?? "活动")}
                  </div>
                  <div className="t-call mt-1">{campusEventTime(item)}</div>
                  <div className="t-foot mt-1">{campusEventLocation(item)}</div>
                </Card>
              );
            })
          : null}
        <div className="mt-2">
          <Btn kind="ghost" to="/intent">
            找活动同行
          </Btn>
        </div>
      </Scroll>
    </Screen>
  );
}

export function EventDetailScreen() {
  const { eventId } = useParams();
  const { repos } = useApp();
  const [item, setItem] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!eventId) return;
    void repos.campus
      .event(eventId)
      .then(setItem)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, [eventId, repos]);

  return (
    <Screen id="screen-B7.1-event-detail">
      <NavBar backTo="/today/events" />
      <Scroll>
        {error ? (
          <Card>
            <StateView kind="network" message={error} />
          </Card>
        ) : !item ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : (
          <>
            <div className="flex wrap" style={{ gap: 6 }}>
              <Chip kind="soft">
                {campusEventDisplayType(String(item.type ?? ""))}
              </Chip>
            </div>
            <div className="t-t2 mt-2">
              {String(item.title ?? item.name ?? "活动")}
            </div>
            <Card className="mt-3">
              <div className="flex" style={{ alignItems: "flex-start", gap: 8 }}>
                <Icon name="clock" size={16} />
                <span className="t-call">{campusEventTime(item)}</span>
              </div>
              <div className="flex mt-2" style={{ alignItems: "flex-start", gap: 8 }}>
                <Icon name="pin" size={16} />
                <span className="t-call">{campusEventLocation(item)}</span>
              </div>
            </Card>
            {item.summary || item.description ? (
              <Card>
                <div className="t-t3">活动说明</div>
                <div className="t-call mt-2">
                  {String(item.summary ?? item.description)}
                </div>
              </Card>
            ) : null}
            <Note>官方报名由你本人完成；App 不代理支付或材料提交。</Note>
            <div className="mt-3">
              <Btn kind="ghost" to="/intent">
                想找同去的人，开个局
              </Btn>
            </div>
          </>
        )}
      </Scroll>
    </Screen>
  );
}

export function ResearchScreen() {
  const { repos } = useApp();
  // Prefer hermes campus context when list endpoint is absent
  return (
    <ApiListScreen
      id="screen-B8-campus-query"
      eyebrow="HERMES"
      title="组会与课题"
      clip="home.listening"
      load={async () => {
        try {
          const ans = await repos.hermes.ask("我本周的组会与课题安排");
          return [
            {
              title: `${AppBrand.agentName} 摘要`,
              summary: ans.data?.message ?? ans.answer ?? ans.text ?? "无摘要",
            },
          ];
        } catch {
          return [];
        }
      }}
      mapRow={(item) => ({
        title: String(item.title ?? "组会与课题"),
        sub: String(item.summary ?? item.sub ?? ""),
      })}
    />
  );
}

export function TransitScreen() {
  const [fromCampus, setFromCampus] = useState<(typeof BUS_CAMPUSES)[number]>("东校园");
  const [toCampus, setToCampus] = useState<(typeof BUS_CAMPUSES)[number]>("北校园");
  const [kind, setKind] = useState<BusDayKind>(() => busDayKind());
  const [sectionNumber, setSectionNumber] = useState(1);
  const route = findBusRoute(fromCampus, toCampus);
  const isTodayKind = kind === busDayKind();
  const times = sectionTime(sectionNumber);
  const campusOptions = BUS_CAMPUSES.map((campus) => ({
    value: campus,
    label: campusShortLabel(campus),
  }));

  return (
    <Screen id="screen-B9-transit-reference">
      <NavBar backTo="/today" />
      <Scroll>
        <PageHeader eyebrow="跨校区" title="班车" clip="home.idle" />
        <Card data-od-id="transit-campus-picker">
          <div className="transit-campus-row">
            <span className="t-t3">从</span>
            <Seg options={campusOptions} value={fromCampus} onChange={setFromCampus} />
          </div>
          <div className="transit-campus-row mt-2">
            <span className="t-t3">到</span>
            <Seg options={campusOptions} value={toCampus} onChange={setToCampus} />
          </div>
        </Card>
        <Seg
          options={[
            { value: "工作日", label: "工作日" },
            { value: "节假日", label: "节假日" },
          ]}
          value={kind}
          onChange={setKind}
        />
        {fromCampus === toCampus ? (
          <Card>
            <div className="flex">
              <Sticker name="school-bus.png" size="st-44" />
              <div className="t-foot" style={{ marginLeft: 10 }}>
                选两个不同的校区就能查班次。
              </div>
            </div>
          </Card>
        ) : route ? (
          <Card data-od-id="transit-schedule-card">
            <div className="flex">
              <Sticker name="school-bus.png" size="st-44" />
              <div style={{ marginLeft: 10 }}>
                <div className="t-t3">{route.from} → {route.to}</div>
                <div className="t-foot mt-1">
                  {route.fromStation} → {route.toStation}
                </div>
              </div>
            </div>
            {route.isQiguan ? (
              <div className="t-foot mt-2">
                岐关公路班线 · ¥40 · 约 100 分钟，需在岐关小程序购票。
              </div>
            ) : null}
            {(() => {
              const departures = busDepartures(route, kind);
              const next = isTodayKind ? nextBusDeparture(route, kind) : undefined;
              if (departures.length === 0) {
                return (
                  <div className="flex mt-3">
                    <Sticker name="school-bus.png" size="st-44" />
                    <div className="t-foot" style={{ marginLeft: 10 }}>
                      节假日这个方向没有班车，换工作日看看。
                    </div>
                  </div>
                );
              }
              return (
                <div className="mt-2">
                  {departures.map((dep) => (
                    <div key={`${dep.time}-${dep.arrive ?? ""}`} className="between" style={{ padding: "7px 0" }}>
                      <div className="flex" style={{ gap: 10, minWidth: 0 }}>
                        <span className="t-call" style={{ fontWeight: 700, width: 52 }}>
                          {dep.time}
                        </span>
                        {dep.arrive ? (
                          <span className="t-foot">→ {dep.arrive}</span>
                        ) : null}
                        {dep.via ? (
                          <span className="t-foot" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {dep.via}
                          </span>
                        ) : null}
                      </div>
                      <div className="flex" style={{ gap: 6 }}>
                        {route.isQiguan ? (
                          <Chip kind="soft">{dep.express ? "直达" : "经停"}</Chip>
                        ) : null}
                        {dep.staffOnly ? <Chip kind="soft">教职工</Chip> : null}
                        {next?.time === dep.time ? <Chip kind="gap">下一班</Chip> : null}
                      </div>
                    </div>
                  ))}
                </div>
              );
            })()}
          </Card>
        ) : (
          <Card data-od-id="transit-schedule-card">
            <div className="flex">
              <Sticker name="school-bus.png" size="st-44" />
              <div className="t-foot" style={{ marginLeft: 10 }}>
                这两个校区之间没有直达班车。去珠海校区可从南校园或东校园坐岐关车。
              </div>
            </div>
          </Card>
        )}
        <Section title="节次时间" />
        <Card data-od-id="reference-transit-section-card">
          <div className="between">
            <span className="t-call">第几节</span>
            <Stepper value={sectionNumber} min={1} max={11} onChange={setSectionNumber} />
          </div>
          {times ? (
            <div className="between mt-3">
              <span className="t-t3">第 {sectionNumber} 节</span>
              <span className="t-call" style={{ fontWeight: 600 }}>
                {times[0]} – {times[1]}
              </span>
            </div>
          ) : null}
        </Card>
        <Note>法定节假日调休以学校通知为准；周末按节假日班次显示。</Note>
      </Scroll>
    </Screen>
  );
}

type SceneTrigger = NonNullable<TodaySummary["scene_trigger"]>;

export function SceneTriggerScreen() {
  const { repos } = useApp();
  const location = useLocation();
  const nav = useNavigate();
  const [trigger, setTrigger] = useState<SceneTrigger | null>(() =>
    normalizeSceneTrigger(
      (location.state as { scene_trigger?: unknown } | null)?.scene_trigger,
    ),
  );
  const [phase, setPhase] = useState<"loading" | "loaded" | "empty" | "failed">(
    () =>
      normalizeSceneTrigger(
        (location.state as { scene_trigger?: unknown } | null)?.scene_trigger,
      )
        ? "loaded"
        : "loading",
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const fromNav = normalizeSceneTrigger(
      (location.state as { scene_trigger?: unknown } | null)?.scene_trigger,
    );
    if (fromNav) {
      setTrigger(fromNav);
      setPhase("loaded");
      return;
    }
    let cancelled = false;
    (async () => {
      setPhase("loading");
      try {
        const summary = await repos.today.summary();
        if (cancelled) return;
        if (summary.scene_trigger) {
          setTrigger(summary.scene_trigger);
          setPhase("loaded");
        } else {
          setTrigger(null);
          setPhase("empty");
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "加载失败");
        setPhase("failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [location.state, repos]);

  async function ignore() {
    const key = trigger?.key;
    if (!key || busy) return;
    setBusy(true);
    try {
      await repos.today.ignoreSceneTrigger(key);
      nav("/today", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "忽略失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen id="screen-B10-scene-trigger">
      <NavBar backTo="/today" />
      <Scroll>
        <PageHeader eyebrow="克制的场景触发" title="场景触发" clip="home.listening" />
        {phase === "loading" ? (
          <Card className="mt-4">
            <StateView kind="loading" />
          </Card>
        ) : null}
        {phase === "failed" ? (
          <Card className="mt-4">
            <StateView
              kind="network"
              message={error ?? undefined}
              actionTitle="重试"
              onAction={() => {
                setPhase("loading");
                void repos.today
                  .summary(true)
                  .then((s) => {
                    if (s.scene_trigger) {
                      setTrigger(s.scene_trigger);
                      setPhase("loaded");
                    } else setPhase("empty");
                  })
                  .catch((e) => {
                    setError(e instanceof Error ? e.message : "加载失败");
                    setPhase("failed");
                  });
              }}
            />
          </Card>
        ) : null}
        {phase === "empty" ? (
          <Card className="mt-4">
            <StateView
              kind="empty"
              message="当前没有场景建议。有进展时会出现在「今天」。"
            />
          </Card>
        ) : null}
        {phase === "loaded" && trigger ? (
          <>
            <Card className="mt-4" data-od-id="scene-trigger-body">
              <div className="t-t3" data-od-id="scene-trigger-title">
                {trigger.title ?? "场景建议"}
              </div>
              <div className="t-foot mt-2" data-od-id="scene-trigger-text">
                {trigger.body ?? ""}
              </div>
            </Card>
            <div className="mt-3">
              <Btn kind="primary" to="/intent">
                {trigger.cta_label ?? "差一个人，开个局"}
              </Btn>
              <Btn kind="ghost" to="/today/action-preview">
                单人行动预览
              </Btn>
              {trigger.key ? (
                <Btn kind="text" disabled={busy} onClick={() => void ignore()}>
                  忽略这条建议
                </Btn>
              ) : null}
            </div>
            {error ? <div className="t-foot mt-2">{error}</div> : null}
          </>
        ) : null}
      </Scroll>
    </Screen>
  );
}

export function PersonalActionPreviewScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const location = useLocation();
  const [search] = useSearchParams();
  const actionId = search.get("action");
  const passed = location.state as
    | { action?: string; params?: Record<string, unknown> }
    | null;
  const [action, setAction] = useState<CampusAction | null>(null);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      if (actionId) {
        setAction(await repos.actions.get(actionId));
        setPreview(null);
      } else if (passed?.action) {
        setAction(
          await repos.actions.preview({
            action: passed.action,
            params: passed.params ?? {},
          }),
        );
        setPreview(null);
      } else {
        setPreview(await repos.actions.preview({ kind: "personal" }));
        setAction(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "预览失败");
      setAction(null);
      setPreview(null);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos, actionId, passed?.action]);

  const resolvedAction =
    action ??
    (preview && typeof preview.action_name === "string"
      ? (preview as CampusAction)
      : null);
  const copy = resolvedAction ? makeCampusActionCopy(resolvedAction) : null;
  const auth = resolvedAction?.authorization;
  const previewed = resolvedAction?.status === "previewed";

  return (
    <Screen
      id={
        actionId
          ? "screen-action-detail"
          : "screen-B11-personal-action-preview"
      }
    >
      <NavBar backTo={actionId ? "/messages" : "/today"} />
      <Scroll>
        <PageHeader
          eyebrow={actionId ? "核对后执行" : "行动预览"}
          title={copy?.title ?? (actionId ? "行动核对" : "个人行动预览")}
          clip={actionId ? "action.executing" : "action.preview"}
        />
        {error ? (
          <Card>
            <StateView
              kind="network"
              message={error}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : !resolvedAction && !preview ? (
          <Card>
            <StateView kind="loading" message={busy ? "正在预览…" : undefined} />
          </Card>
        ) : copy && resolvedAction ? (
          <ActionReviewCard
            copy={copy}
            authorizedCount={
              auth?.actor_decision === "not_required"
                ? undefined
                : auth?.authorized_count
            }
            requiredCount={
              auth?.actor_decision === "not_required"
                ? undefined
                : auth?.required_count
            }
            testId="campus-action-review"
          >
            <div className="t-foot mt-3">
              {auth?.actor_decision === "not_required"
                ? "这不是一笔要提交的预约。只是用来找同一时段打球的同学，不用核对。"
                : "核对的是时间、地点和项目，不是技术参数。"}
            </div>
          </ActionReviewCard>
        ) : (
          <Card>
            <div className="t-t3">个人行动</div>
            <div className="t-foot mt-2">确认后才会真正执行；你随时可以取消。</div>
          </Card>
        )}
        {resolvedAction && previewed && auth?.actor_decision === "pending" ? (
          <Btn
            kind="primary"
            disabled={busy}
            onClick={() =>
              void (async () => {
                setBusy(true);
                try {
                  setAction(
                    await repos.actions.authorize(
                      resolvedAction.id,
                      resolvedAction.snapshot_hash ?? "",
                      crypto.randomUUID(),
                    ),
                  );
                } catch (e) {
                  setError(e instanceof Error ? e.message : "核对失败");
                } finally {
                  setBusy(false);
                }
              })()
            }
          >
            核对无误，分别确认
          </Btn>
        ) : null}
        {resolvedAction &&
        previewed &&
        auth?.actor_decision === "authorized" &&
        auth?.all_authorized &&
        !resolvedAction.gathering_id ? (
          <Btn
            kind="primary"
            disabled={busy}
            onClick={() =>
              void (async () => {
                setBusy(true);
                try {
                  setAction(
                    await repos.actions.execute(
                      { action_id: resolvedAction.id, confirm: true },
                      crypto.randomUUID(),
                    ),
                  );
                } catch (e) {
                  setError(e instanceof Error ? e.message : "执行失败");
                } finally {
                  setBusy(false);
                }
              })()
            }
          >
            执行个人行动
          </Btn>
        ) : null}
        {resolvedAction?.gathering_id ? (
          <Btn
            kind="ghost"
            onClick={() => nav(`/gathering/${resolvedAction.gathering_id}`)}
          >
            返回局内继续
          </Btn>
        ) : auth?.actor_decision === "not_required" ? (
          <Btn kind="primary" to="/messages">
            知道了
          </Btn>
        ) : (
          <Btn kind="text" to={actionId ? "/messages" : "/today"}>
            先不了
          </Btn>
        )}
      </Scroll>
    </Screen>
  );
}
