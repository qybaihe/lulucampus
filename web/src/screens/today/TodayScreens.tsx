import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import { AppBrand } from "../../core/brand";
import type { CampusAction, TodaySummary } from "../../core/api/repositories";
import { makeCampusActionCopy } from "../../core/campus/actionCopy";
import { ActionReviewCard } from "../../components/campus/ActionReviewCard";
import {
  Btn,
  Card,
  Chip,
  Icon,
  LargeTitle,
  LuluMark,
  NavBar,
  Note,
  Row,
  Screen,
  Scroll,
  Section,
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

function isTechnicalCode(value: unknown): boolean {
  if (typeof value !== "string") return true;
  const text = value.trim();
  if (!text) return true;
  if (text.toLowerCase().startsWith("jwxt:")) return true;
  if (/^\d{12,}$/.test(text)) return true;
  if (text.length >= 28 && /^[A-Za-z0-9:_-]+$/.test(text)) return true;
  return false;
}

function formatClock(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function formatTimelineRange(item: {
  time_label?: string | null;
  start_at?: string | null;
  end_at?: string | null;
  starts_at?: string;
}): string {
  if (item.time_label && String(item.time_label).trim()) return String(item.time_label);
  const start = formatClock(item.start_at ?? item.starts_at ?? null);
  const end = formatClock(item.end_at ?? null);
  if (start && end) return `${start}–${end}`;
  return start;
}

function splitTimeRange(range: string): [string, string] {
  if (!range) return ["", ""];
  const parts = range.split(/[–-]/);
  if (parts.length >= 2) return [parts[0]!.trim(), parts[1]!.trim()];
  return [range.trim(), ""];
}

function dayTitle(iso?: string | null): string {
  if (!iso) return "未标注日期";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "未标注日期";
  return d.toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "long" });
}

export function TodayScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [data, setData] = useState<TodaySummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hermes, setHermes] = useState("");

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

  const tools = [
    { sticker: "desk-calendar.png", label: "课表", to: "/today/timetable", id: "today-timetable" },
    { sticker: "alarm-clock.png", label: "作业", to: "/today/assignments", id: "today-assignments" },
    { sticker: "running-shoe.png", label: "场馆", to: "/today/gym", id: "today-gym" },
    { sticker: "study-lamp.png", label: "研讨室", to: "/today/room", id: "today-room" },
    { sticker: "poster-blank.png", label: "活动", to: "/today/events", id: "today-events" },
    { sticker: "notebook-open.png", label: "组会", to: "/today/research", id: "today-research" },
    { sticker: "school-bus.png", label: "班车", to: "/today/transit", id: "today-transit" },
    { sticker: "chair-empty.png", label: "我的局", to: "/gatherings/mine", id: "today-my-gatherings" },
  ];

  return (
    <Screen id="screen-B1-today">
      <Scroll>
        <div className="between" style={{ paddingTop: 8 }}>
          <div>
            <div className="t-foot" style={{ fontWeight: 600 }}>
              {dateLine()}
            </div>
            <div className="t-t1">今天</div>
          </div>
          <LuluMark placement="confirm" clip="home.reply" />
        </div>

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
          <Card
            className="mt-3"
            onClick={() =>
              nav("/today/scene", {
                state: { scene_trigger: data.scene_trigger },
              })
            }
            data-od-id="today-scene-trigger-card"
          >
            <div className="between">
              <div>
                <div className="t-t3">{data.scene_trigger.title ?? "场景建议"}</div>
                <div className="t-foot mt-1">{data.scene_trigger.body}</div>
              </div>
              <span className="om-chip gap">{data.scene_trigger.cta_label ?? "查看"}</span>
            </div>
          </Card>
        ) : null}

        {phase === "loaded" ? (
          <>
            <Section title="今日日程" more={{ label: "课表", to: "/today/timetable" }} />
            {data?.timeline && data.timeline.length > 0 ? (
              <Card>
                <div className="day-timeline" data-od-id="today-schedule-timeline">
                  {data.timeline.map((item, i) => {
                    const time = formatTimelineRange(item);
                    const [start, end] = splitTimeRange(time);
                    const kindLabel =
                      item.kind === "gathering"
                        ? "活动"
                        : item.kind === "assignment"
                          ? "作业"
                          : "课程";
                    const to =
                      item.gathering_id
                        ? `/gathering/${item.gathering_id}`
                        : item.kind === "assignment"
                          ? "/today/assignments"
                          : "/today/timetable";
                    return (
                      <Link key={item.id ?? i} to={to} className="day-tl-item">
                        <div className="day-tl-rail">
                          <div className="day-tl-time">{start || "—"}</div>
                          <div className={`day-tl-dot ${item.kind ?? "course"}`} />
                          {end ? <div className="day-tl-time end">{end}</div> : null}
                        </div>
                        <div className="day-tl-body">
                          <div className="between">
                            <div className="t-t3">{item.title ?? "安排"}</div>
                            <span className="om-chip">{kindLabel}</span>
                          </div>
                          {(item.subtitle || item.location) && (
                            <div className="t-foot mt-1">
                              {String(item.subtitle || item.location)}
                            </div>
                          )}
                          {time ? <div className="t-cap mt-1" style={{ fontWeight: 600 }}>{time}</div> : null}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </Card>
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
            <LuluMark placement="avatar" />
            <div className="grow">
              <div className="t-t3">问问 {AppBrand.agentName}</div>
              <div className="t-cap">课表、DDL、场地、活动与班车</div>
            </div>
          </div>
          <div className="flex mt-3">
            <input
              className="om-input"
              style={{ minHeight: 42, borderRadius: 999 }}
              placeholder="例如：今天有什么课？"
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
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 14,
            }}
          >
            {tools.map((t) => (
              <Link
                key={t.to}
                to={t.to}
                data-od-id={t.id}
                style={{
                  textAlign: "center",
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                <Sticker name={t.sticker} size="st-44" />
                <div className="t-cap" style={{ color: "var(--ink)", fontWeight: 600, marginTop: 6 }}>
                  {t.label}
                </div>
              </Link>
            ))}
          </div>
        </Card>

        <Section title="业务入口" />
        <Card tight>
          <Row
            icon={<Sticker name="round-table.png" size="st-24" />}
            title="公开局"
            sub="看看谁还差人"
            to="/gatherings/open"
          />
          <Row
            icon={<Sticker name="badge.png" size="st-24" />}
            title="搭子关系"
            sub="共同经历"
            to="/relations"
          />
        </Card>
      </Scroll>
    </Screen>
  );
}

export function HermesAskScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [peers, setPeers] = useState<
    Array<{
      user_id: string;
      display_name: string;
      persona_label?: string | null;
      reason: string;
      overlap: string;
    }>
  >([]);
  const [previewCopy, setPreviewCopy] = useState<ReturnType<
    typeof makeCampusActionCopy
  > | null>(null);
  const [busy, setBusy] = useState(false);
  const [startingPeer, setStartingPeer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function ask(text = q) {
    const value = text.trim();
    if (!value || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await repos.hermes.ask(value);
      const data = res.data ?? {};
      setAnswer(
        String(
          data.message ??
            res.answer ??
            res.text ??
            res.message ??
            `${AppBrand.agentName} 没有返回文案`,
        ),
      );
      setPeers(Array.isArray(data.peers) ? data.peers : []);
      if (
        (res.kind === "action_preview" || res.requires_preview) &&
        data.params &&
        typeof data.params === "object"
      ) {
        setPreviewCopy(
          makeCampusActionCopy({
            action_name: res.action,
            status: "previewed",
            params: data.params,
          }),
        );
      } else {
        setPreviewCopy(null);
      }
      setQ(value);
    } catch (e) {
      setError(e instanceof Error ? e.message : "提问失败");
      setAnswer(null);
      setPeers([]);
      setPreviewCopy(null);
    } finally {
      setBusy(false);
    }
  }

  async function startChat(peer: (typeof peers)[number]) {
    if (startingPeer) return;
    setStartingPeer(peer.user_id);
    setError(null);
    try {
      const opened = await repos.hermes.startPeerChat({
        peer_user_id: peer.user_id,
        reason: peer.reason,
        overlap: peer.overlap,
      });
      nav(`/channel/${opened.channel_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "发起聊天失败");
    } finally {
      setStartingPeer(null);
    }
  }

  return (
    <Screen id="screen-B2-hermes">
      <NavBar title={AppBrand.agentName} backTo="/today" />
      <Scroll>
        <div className="center mt-3">
          <LuluMark placement="header" caption="课表、场地、同课/同时段的人" />
        </div>
        <Card className="mt-4">
          <textarea
            className="om-input"
            placeholder="今天想问什么？"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            data-od-id="hermes-input"
          />
          <Btn
            kind="primary"
            disabled={busy || !q.trim()}
            onClick={() => void ask()}
          >
            {busy ? "思考中…" : "提问"}
          </Btn>
        </Card>
        <div className="flex wrap mt-3">
          {["按我的画像推荐公选", "还有谁也选了机器学习？", "还有谁也约了羽毛球？"].map((c) => (
            <Chip key={c} kind="soft" onClick={() => void ask(c)}>
              {c}
            </Chip>
          ))}
        </div>
        {error ? (
          <Card className="mt-3">
            <StateView kind="network" message={error} actionTitle="重试" onAction={() => void ask()} />
          </Card>
        ) : null}
        {answer ? (
          <Card className="mt-3" data-od-id="hermes-answer">
            <div className="t-t3">{AppBrand.agentName}</div>
            <div className="t-call mt-2" style={{ whiteSpace: "pre-wrap" }}>
              {answer}
            </div>
          </Card>
        ) : null}
        {previewCopy ? (
          <div className="mt-3">
            <ActionReviewCard copy={previewCopy} testId="hermes-action-copy-card" />
          </div>
        ) : null}
        {peers.length > 0 ? (
          <Card className="mt-3" data-od-id="hermes-peers">
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
                  disabled={Boolean(startingPeer)}
                  onClick={() => void startChat(peer)}
                >
                  {startingPeer === peer.user_id ? "正在发起…" : "一键发起聊天"}
                </Btn>
              </div>
            ))}
          </Card>
        ) : null}
        <Note>{AppBrand.agentName} 只读校园事实，预约仍需你在 App 里确认。</Note>
      </Scroll>
    </Screen>
  );
}

function ApiListScreen({
  id,
  title,
  load,
  mapRow,
  back = "/today",
}: {
  id: string;
  title: string;
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
      <NavBar title={title} backTo={back} />
      <Scroll>
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
  const [week, setWeek] = useState(1);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setPhase("loading");
    try {
      const raw = await repos.campus.timetable(week);
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

  const groups = groupEntriesByDay(entries);

  return (
    <Screen id="screen-B3-timetable">
      <NavBar title="我的课表" backTo="/today" />
      <Scroll>
        <Card>
          <div className="between">
            <span className="t-call" style={{ fontWeight: 600 }}>
              第 {week} 周
            </span>
            <Stepper value={week} min={1} max={30} onChange={setWeek} />
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
        {phase === "loaded" && entries.length === 0 ? (
          <Card>
            <StateView kind="empty" message="课表为空或尚未授权读取" />
          </Card>
        ) : null}
        {phase === "loaded" &&
          groups.map((group) => (
            <div key={group.key}>
              <Section title={group.title} />
              <Card>
                <div className="day-timeline">
                  {group.items.map((c, i) => {
                    const id = String(c.course_id ?? c.id ?? i);
                    const title = String(c.course_name ?? c.name ?? c.title ?? "课程");
                    const time = formatTimelineRange({
                      time_label: typeof c.time_label === "string" ? c.time_label : null,
                      start_at: typeof c.start_at === "string" ? c.start_at : null,
                      end_at: typeof c.end_at === "string" ? c.end_at : null,
                    });
                    const [start, end] = splitTimeRange(time);
                    const meta = [c.display_code, c.display_class_code, c.location]
                      .filter((v) => typeof v === "string" && !isTechnicalCode(v))
                      .join(" · ");
                    return (
                      <Link key={`${id}-${i}`} to={`/today/course/${id}`} className="day-tl-item">
                        <div className="day-tl-rail">
                          <div className="day-tl-time">{start || "—"}</div>
                          <div className="day-tl-dot course" />
                          {end ? <div className="day-tl-time end">{end}</div> : null}
                        </div>
                        <div className="day-tl-body">
                          <div className="t-t3">{title}</div>
                          {time ? (
                            <div className="t-cap mt-1" style={{ fontWeight: 600 }}>
                              {time}
                            </div>
                          ) : null}
                          {meta ? <div className="t-foot mt-1">{meta}</div> : null}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </Card>
            </div>
          ))}
        <Note>仅显示你的缓存课表；不会展示教务内部编码。</Note>
      </Scroll>
    </Screen>
  );
}

function groupEntriesByDay(entries: Array<Record<string, unknown>>) {
  const map = new Map<string, Array<Record<string, unknown>>>();
  for (const entry of entries) {
    const start = typeof entry.start_at === "string" ? entry.start_at : "";
    const key = start ? start.slice(0, 10) : "unknown";
    const bucket = map.get(key) ?? [];
    bucket.push(entry);
    map.set(key, bucket);
  }
  return Array.from(map.entries()).map(([key, items]) => ({
    key,
    title: dayTitle(typeof items[0]?.start_at === "string" ? items[0].start_at : null),
    items,
  }));
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
      <NavBar title="课程详情" backTo="/today/timetable" />
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
            <LargeTitle
              title={String(item.name ?? item.title ?? "课程")}
              sub={`课程 · ${courseId ?? ""}`}
            />
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
      title="作业与 DDL"
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
      <NavBar title="作业详情" backTo="/today/assignments" />
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
            <LargeTitle
              title={String(item.title ?? item.name ?? "作业")}
              sub={String(item.course_name ?? item.course ?? "")}
            />
            <Card tight>
              <Row
                icon={<Icon name="clock" size={20} />}
                title={String(item.due_at ?? item.deadline ?? "截止时间未提供")}
                sub={String(item.description ?? item.summary ?? "")}
              />
            </Card>
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
  const { repos } = useApp();
  return (
    <ApiListScreen
      id="screen-B5-gym"
      title="体育场馆"
      load={() => repos.campus.gymAvailable()}
      mapRow={(item, i) => ({
        title: String(item.name ?? item.venue ?? item.label ?? `场馆 ${i + 1}`),
        sub: String(item.location ?? item.slot ?? item.start_at ?? ""),
        right: item.available === false ? "已满" : String(item.status ?? "有空"),
        chipKind: item.available === false ? undefined : "gap",
      })}
    />
  );
}

export function RoomScreen() {
  const { repos } = useApp();
  return (
    <ApiListScreen
      id="screen-B6-room"
      title="研讨室"
      load={() => repos.campus.roomAvailable()}
      mapRow={(item, i) => ({
        title: String(item.name ?? item.room ?? item.label ?? `研讨室 ${i + 1}`),
        sub: String(item.location ?? item.capacity ?? item.slot ?? ""),
        right: String(item.status ?? (item.available === false ? "已满" : "空闲")),
        chipKind: item.available === false ? undefined : "gap",
      })}
    />
  );
}

export function EventsScreen() {
  const { repos } = useApp();
  return (
    <ApiListScreen
      id="screen-B7-events"
      title="校园活动"
      load={() => repos.campus.events()}
      mapRow={(item, i) => ({
        title: String(item.title ?? item.name ?? `活动 ${i + 1}`),
        sub: String(
          [item.start_at, item.location].filter(Boolean).join(" · ") ||
            item.summary ||
            "",
        ),
        to: `/today/event/${item.id ?? i}`,
      })}
    />
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
      <NavBar title="活动详情" backTo="/today/events" />
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
            <LargeTitle
              title={String(item.title ?? item.name ?? "活动")}
              sub={String(
                [item.start_at, item.location].filter(Boolean).join(" · "),
              )}
            />
            {item.summary || item.description ? (
              <Card>
                <div className="t-call">
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
      title="组会与课题"
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
  const { repos } = useApp();
  return (
    <ApiListScreen
      id="screen-B9-transit-reference"
      title="班车与节次"
      load={async () => {
        try {
          const ans = await repos.hermes.ask("东校园下一班校车与今日节次");
          return [
            {
              title: "班车与节次",
              summary: ans.data?.message ?? ans.answer ?? ans.text ?? "暂无数据",
            },
          ];
        } catch {
          return [];
        }
      }}
      mapRow={(item) => ({
        title: String(item.title ?? "班车与节次"),
        sub: String(item.summary ?? ""),
      })}
    />
  );
}

type SceneTrigger = NonNullable<TodaySummary["scene_trigger"]>;

export function SceneTriggerScreen() {
  const { repos } = useApp();
  const location = useLocation();
  const nav = useNavigate();
  const passed = (location.state as { scene_trigger?: SceneTrigger } | null)
    ?.scene_trigger;
  const [trigger, setTrigger] = useState<SceneTrigger | null>(passed ?? null);
  const [phase, setPhase] = useState<"loading" | "loaded" | "empty" | "failed">(
    passed ? "loaded" : "loading",
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (passed) {
      setTrigger(passed);
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
  }, [passed, repos]);

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
      <NavBar title="场景触发" backTo="/today" />
      <Scroll>
        <LuluMark placement="header" caption="来自 /today/summary.scene_trigger" />
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
              {trigger.key ? (
                <div className="t-cap mt-2 mono">key · {trigger.key}</div>
              ) : null}
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
  const [search] = useSearchParams();
  const actionId = search.get("action");
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
  }, [repos, actionId]);

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
      <NavBar
        title={copy?.title ?? (actionId ? "行动核对" : "个人行动预览")}
        backTo={actionId ? "/messages" : "/today"}
      />
      <Scroll>
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
        ) : (
          <Btn kind="text" to={actionId ? "/messages" : "/today"}>
            先不了
          </Btn>
        )}
      </Scroll>
    </Screen>
  );
}
