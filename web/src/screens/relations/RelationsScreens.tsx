import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import {
  asList,
  type RelationSummary,
  type RelationTimelineEntry,
  type SharedGoal,
} from "../../core/api/repositories";
import {
  Btn,
  Card,
  Chip,
  Divider,
  NavBar,
  PageHeader,
  Progress,
  Screen,
  Scroll,
  Section,
  StateView,
  Sticker,
} from "../../components/ui/primitives";

/* ---------- 共用工具 ---------- */

function participantsLine(relation: RelationSummary): string {
  return relation.participants.map((p) => p.display_name ?? "同学").join(" × ");
}

/** C · 弱展示 → 强展示：「一起成过 3 局 · 最近一次是组队备赛」。 */
function relationSummaryLine(relation: RelationSummary): string {
  const parts: string[] = [];
  const times = relation.times_together ?? 0;
  const recur = relation.recur_count ?? 0;
  if (times > 0) parts.push(`一起成过 ${times} 局`);
  if (recur > 0) parts.push(`复局 ${recur} 次`);
  const latestTimeline = relation.timeline?.[0];
  if (latestTimeline) {
    parts.push(`最近一次是${latestTimeline.gathering_type}`);
  } else if (relation.experiences?.length) {
    const latest = [...relation.experiences].sort((a, b) =>
      (b.occurred_at ?? "").localeCompare(a.occurred_at ?? ""),
    )[0];
    parts.push(`最近一次是${latest.gathering_type}`);
  }
  return parts.length ? parts.join(" · ") : "共同经历只记事实";
}

function formatMonthDay(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

function formatLongDate(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatWindow(window: { start_at: string; end_at: string }): string {
  const start = new Date(window.start_at);
  const end = new Date(window.end_at);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "";
  const startLabel = start.toLocaleString("zh-CN", {
    weekday: "long",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const endLabel = end.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${startLabel} — ${endLabel}`;
}

/** 「4 月 3 日 · 珠海馆 · 羽毛球 2 小时」式的一行事实。 */
function timelineHeadline(entry: RelationTimelineEntry): string {
  const parts: string[] = [];
  if (entry.location) parts.push(entry.location);
  const minutes = entry.duration_minutes ?? 0;
  if (minutes > 0) {
    if (minutes >= 60) {
      const hours = minutes / 60;
      const label = Number.isInteger(hours)
        ? `${hours}`
        : hours.toFixed(1).replace(/\.0$/, "");
      parts.push(`${entry.gathering_type} ${label} 小时`);
    } else {
      parts.push(`${entry.gathering_type} ${minutes} 分钟`);
    }
  } else {
    parts.push(entry.gathering_type);
  }
  return parts.join(" · ");
}

function formatNumber(value: number): string {
  return Number.isInteger(value)
    ? `${value}`
    : value.toFixed(1).replace(/\.0$/, "");
}

/* ---------- 确认弹层（对齐 iOS alert） ---------- */

function ConfirmDissolveSheet({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="om-sheet" data-od-id="relation-dissolve-action">
      <div className="sheet-grab" />
      <div className="t-t3">解除这段搭子关系？</div>
      <div className="t-foot mt-2">
        这是单方静默操作，对方不会收到解除通知。共同经历只保留事实记录。
      </div>
      <Btn kind="primary" onClick={onConfirm}>
        确认解除
      </Btn>
      <Btn kind="text" onClick={onCancel}>
        取消
      </Btn>
    </div>
  );
}

/* ---------- E15 · 搭子关系（事实列表） ---------- */

export function RelationsScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [items, setItems] = useState<RelationSummary[]>([]);
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [error, setError] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [pendingDissolve, setPendingDissolve] = useState<string | null>(null);

  async function load() {
    setPhase("loading");
    try {
      const raw = await repos.relations.list();
      setItems(asList(raw));
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

  async function recur(id: string) {
    if (workingId) return;
    setWorkingId(id);
    try {
      const result = await repos.relations.recur(
        id,
        `relation-recur-${id}-${crypto.randomUUID()}`,
      );
      setMutationError(null);
      if (result.gathering_id) nav(`/gathering/${result.gathering_id}`);
    } catch (e) {
      setMutationError(e instanceof Error ? e.message : "复局失败");
    } finally {
      setWorkingId(null);
    }
  }

  async function dissolve(id: string) {
    if (workingId) return;
    setWorkingId(id);
    try {
      await repos.relations.dissolve(id);
      setMutationError(null);
      await load();
    } catch (e) {
      setMutationError(e instanceof Error ? e.message : "解除失败");
    } finally {
      setWorkingId(null);
    }
  }

  return (
    <Screen id="screen-E15-relations">
      <NavBar backTo="/messages" />
      <Scroll>
        <PageHeader eyebrow="共同经历事实" title="搭子关系" />
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
          <Card id="relations-empty-state">
            <StateView
              kind="empty"
              message="完成一次真实的共同活动后，搭子关系会出现在这里。"
            />
            <Btn kind="ghost" sm to="/gatherings/open">
              浏览公开局
            </Btn>
          </Card>
        ) : null}
        {phase === "loaded"
          ? items.map((relation) => {
              const working = workingId === relation.id;
              const milestone = relation.milestone;
              return (
                <Card key={relation.id}>
                  <div className="between">
                    <div className="t-t2">{participantsLine(relation)}</div>
                    {relation.partner_title ? (
                      <Chip kind="gap">{relation.partner_title}</Chip>
                    ) : null}
                  </div>
                  <div className="t-foot mt-1">
                    {relationSummaryLine(relation)}
                  </div>
                  {relation.participants.some((p) => (p.interest_tags ?? []).length) ? (
                    <div className="t-cap mt-1">
                      {relation.participants
                        .flatMap((p) => p.interest_tags ?? [])
                        .filter((tag, i, all) => all.indexOf(tag) === i)
                        .slice(0, 4)
                        .join(" · ")}
                    </div>
                  ) : null}
                  {milestone?.next != null && milestone.remaining != null ? (
                    <>
                      <div className="mt-2">
                        <Progress
                          value={
                            ((relation.times_together ?? 0) / milestone.next) *
                            100
                          }
                        />
                      </div>
                      <div className="t-cap mt-1">
                        再同局 {milestone.remaining} 次 →{" "}
                        {milestone.next_label ?? "下个纪念点"}
                      </div>
                    </>
                  ) : null}
                  <div className="flex mt-3" style={{ gap: 8, flexWrap: "wrap" }}>
                    <Btn
                      kind="ghost"
                      sm
                      disabled={working}
                      onClick={() => void recur(relation.id)}
                      id="relation-recur-action"
                    >
                      {working ? "创建中…" : "再来一次"}
                    </Btn>
                    {relation.channel_id ? (
                      <Btn
                        kind="ghost"
                        sm
                        onClick={() =>
                          nav(`/channel/${relation.channel_id}`, {
                            state: {
                              title: relation.peer_display_name ?? participantsLine(relation),
                            },
                          })
                        }
                        id="relation-open-chat"
                      >
                        进入对话
                      </Btn>
                    ) : (
                      <Btn
                        kind="ghost"
                        sm
                        disabled
                        disabledReason="共同完成并建立会话后开放"
                        id="relation-open-chat"
                      >
                        进入对话
                      </Btn>
                    )}
                    <Btn kind="ghost" sm to={`/relation/${relation.id}`}>
                      共同经历
                    </Btn>
                  </div>
                  <Btn
                    kind="text"
                    sm
                    disabled={workingId != null}
                    onClick={() => setPendingDissolve(relation.id)}
                  >
                    {working ? "处理中…" : "解除关系（单方静默）…"}
                  </Btn>
                </Card>
              );
            })
          : null}
        {mutationError ? (
          <Card>
            <StateView
              kind="network"
              message={mutationError}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : null}
      </Scroll>
      {pendingDissolve ? (
        <ConfirmDissolveSheet
          onConfirm={() => {
            const id = pendingDissolve;
            setPendingDissolve(null);
            void dissolve(id);
          }}
          onCancel={() => setPendingDissolve(null)}
        />
      ) : null}
    </Screen>
  );
}

/* ---------- E16 · 共同经历 ---------- */

function StatBlock({ value, label }: { value: string; label: string }) {
  return (
    <div style={{ flex: 1, textAlign: "center" }}>
      <div
        className="mono"
        style={{ fontSize: 24, fontWeight: 800, color: "var(--ink)" }}
      >
        {value}
      </div>
      <div className="t-cap mt-1">{label}</div>
    </div>
  );
}

function TimelineCard({ entry }: { entry: RelationTimelineEntry }) {
  return (
    <Card>
      <div className="flex" style={{ gap: 8, alignItems: "baseline" }}>
        <span className="mono t-foot" style={{ fontWeight: 700, color: "var(--ink)" }}>
          {formatMonthDay(entry.occurred_at)}
        </span>
        <span className="t-call" style={{ fontWeight: 600 }}>
          {timelineHeadline(entry)}
        </span>
        <span style={{ flex: 1 }} />
        {entry.via_recurrence ? <Chip kind="soft">复局</Chip> : null}
      </div>
      {entry.title ? <div className="t-foot mt-1">{entry.title}</div> : null}
      {entry.common_grounds?.length ? (
        <div className="t-cap mt-1">{entry.common_grounds.join(" · ")}</div>
      ) : null}
    </Card>
  );
}

export function RelationDetailScreen() {
  const { relationId } = useParams();
  const { repos } = useApp();
  const nav = useNavigate();
  const [phase, setPhase] = useState<
    | { kind: "loading" }
    | { kind: "loaded"; relation: RelationSummary }
    | { kind: "failed"; message: string }
    | { kind: "dissolved" }
  >({ kind: "loading" });
  const [working, setWorking] = useState(false);
  const [confirmDissolve, setConfirmDissolve] = useState(false);

  async function load() {
    if (!relationId) return;
    setPhase({ kind: "loading" });
    try {
      const relation = await repos.relations.get(relationId);
      setPhase({ kind: "loaded", relation });
    } catch (e) {
      setPhase({
        kind: "failed",
        message: e instanceof Error ? e.message : "加载失败",
      });
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [relationId, repos]);

  async function dissolve() {
    if (!relationId || working) return;
    setWorking(true);
    try {
      await repos.relations.dissolve(relationId);
      setPhase({ kind: "dissolved" });
    } catch (e) {
      setPhase({
        kind: "failed",
        message: e instanceof Error ? e.message : "解除失败",
      });
    } finally {
      setWorking(false);
    }
  }

  async function recur() {
    if (!relationId || working) return;
    setWorking(true);
    try {
      const result = await repos.relations.recur(
        relationId,
        `relation-recur-${relationId}-${crypto.randomUUID()}`,
      );
      if (result.gathering_id) nav(`/gathering/${result.gathering_id}`);
    } catch (e) {
      setPhase({
        kind: "failed",
        message: e instanceof Error ? e.message : "复局失败",
      });
    } finally {
      setWorking(false);
    }
  }

  return (
    <Screen id="screen-E16-relation-detail">
      <NavBar backTo="/relations" />
      <Scroll>
        <PageHeader eyebrow="事实记录" title="共同经历" />
        {phase.kind === "loading" ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : null}
        {phase.kind === "failed" ? (
          <Card>
            <StateView
              kind="network"
              message={phase.message}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : null}
        {phase.kind === "dissolved" ? (
          <>
            <Card>
              <StateView kind="empty" message="这段搭子关系已解除。" />
            </Card>
            <Btn kind="primary" to="/relations">
              返回搭子关系
            </Btn>
          </>
        ) : null}
        {phase.kind === "loaded" ? (
          <RelationDetailContent
            relation={phase.relation}
            working={working}
            onRecur={() => void recur()}
            onRequestDissolve={() => setConfirmDissolve(true)}
          />
        ) : null}
      </Scroll>
      {confirmDissolve ? (
        <ConfirmDissolveSheet
          onConfirm={() => {
            setConfirmDissolve(false);
            void dissolve();
          }}
          onCancel={() => setConfirmDissolve(false)}
        />
      ) : null}
    </Screen>
  );
}

function RelationDetailContent({
  relation,
  working,
  onRecur,
  onRequestDissolve,
}: {
  relation: RelationSummary;
  working: boolean;
  onRecur: () => void;
  onRequestDissolve: () => void;
}) {
  const nav = useNavigate();
  const milestone = relation.milestone;
  const timeline = relation.timeline ?? [];
  const goal = relation.active_goal;
  return (
    <>
      {/* 搭子档案头：称号 + 次数事实，全部来自 shared_experiences。 */}
      <Card>
        <div className="between">
          <div className="t-t2">{participantsLine(relation)}</div>
          {relation.partner_title ? (
            <Chip kind="gap">{relation.partner_title}</Chip>
          ) : null}
        </div>
        <div className="t-foot mt-1">{relationSummaryLine(relation)}</div>
        {relation.participants.some((p) => (p.interest_tags ?? []).length) ? (
          <div className="t-cap mt-2">
            {relation.participants
              .flatMap((p) => p.interest_tags ?? [])
              .filter((tag, i, all) => all.indexOf(tag) === i)
              .slice(0, 6)
              .join(" · ")}
          </div>
        ) : null}
        <div className="flex mt-3">
          <StatBlock value={`${relation.times_together ?? 0}`} label="次同局" />
          <StatBlock value={`${relation.recur_count ?? 0}`} label="次复局" />
          <StatBlock value={`${timeline.length}`} label="条经历" />
        </div>
        {milestone?.reached_label ? (
          <div className="flex mt-3" style={{ gap: 8, alignItems: "center" }}>
            <Sticker name="badge.png" size="st-44" />
            <div>
              <div className="t-t3">{milestone.reached_label}</div>
              {milestone.next != null && milestone.remaining != null ? (
                <div className="t-cap">
                  再同局 {milestone.remaining} 次解锁「
                  {milestone.next_label ?? `第 ${milestone.next} 次同局`}」
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
        {milestone?.next != null ? (
          <div className="mt-2">
            <Progress
              value={((relation.times_together ?? 0) / milestone.next) * 100}
            />
          </div>
        ) : null}
      </Card>

      {/* 下次可约：唯一由服务端算出的「你们都空着」窗口。 */}
      {relation.next_window ? (
        <Card id="relation-next-window">
          <div className="flex" style={{ gap: 10, alignItems: "center" }}>
            <Sticker name="desk-calendar.png" size="st-44" />
            <div>
              <div className="t-t3">下次你们都空着</div>
              <div className="t-foot mt-1">
                {formatWindow(relation.next_window)}
              </div>
            </div>
          </div>
        </Card>
      ) : null}

      {goal ? (
        <Card id="relation-active-goal">
          <div className="between">
            <div className="t-t3">{goal.definition}</div>
            <span className="mono t-foot" style={{ fontWeight: 700 }}>
              {formatNumber(goal.current_value)} /{" "}
              {formatNumber(goal.target_value)} {goal.unit}
            </span>
          </div>
          <div className="mt-2">
            <Progress
              value={(goal.current_value / Math.max(goal.target_value, 1)) * 100}
            />
          </div>
          <div className="t-cap mt-1">
            目标进度只由到场与完成事实自动更新 · {goal.period_end} 截止
          </div>
        </Card>
      ) : null}

      {/* 操作区：复局 / 会话 / 目标同为次级行动，等权 ghost 一排收拢。 */}
      <div className="flex mt-2" style={{ gap: 8, flexWrap: "wrap" }}>
        <Btn kind="ghost" sm disabled={working} onClick={onRecur} id="relation-detail-recur">
          {working ? "创建中…" : "再来一次"}
        </Btn>
        {relation.channel_id ? (
          <Btn
            kind="ghost"
            sm
            onClick={() =>
              nav(`/channel/${relation.channel_id}`, {
                state: {
                  title: relation.peer_display_name ?? participantsLine(relation),
                },
              })
            }
          >
            搭子会话
          </Btn>
        ) : null}
        <Btn kind="ghost" sm to={`/goal/${relation.id}`}>
          共同目标
        </Btn>
      </div>

      {/* 经历时间线：仅双方可见的「物证」，替代原始日志式列表。 */}
      {timeline.length > 0 ? (
        <>
          <Section title="经历时间线" />
          {timeline.map((entry) => (
            <TimelineCard key={entry.gathering_id} entry={entry} />
          ))}
        </>
      ) : (
        (relation.experiences ?? []).map((experience) => (
          <Card key={experience.id}>
            <div className="t-t3">{experience.gathering_type}</div>
            <div className="t-cap mt-1">
              {formatLongDate(experience.occurred_at)}
            </div>
            {experience.outcome ? (
              <div className="t-call mt-2">{experience.outcome}</div>
            ) : null}
            {experience.common_grounds?.length ? (
              <div className="t-foot mt-2">
                {experience.common_grounds.join(" · ")}
              </div>
            ) : null}
          </Card>
        ))
      )}

      <Btn kind="text" sm disabled={working} onClick={onRequestDissolve}>
        {working ? "处理中…" : "解除关系（单方静默）…"}
      </Btn>
    </>
  );
}

/* ---------- E11 · 共同目标（T3） ---------- */

function localDateValue(date: Date): string {
  const y = date.getFullYear();
  const m = `${date.getMonth() + 1}`.padStart(2, "0");
  const d = `${date.getDate()}`.padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function GoalCreateCard({
  working,
  onCreate,
  onCancel,
}: {
  working: boolean;
  onCreate: (draft: {
    definition: string;
    period_start: string;
    period_end: string;
    target_value: number;
    unit: string;
  }) => void;
  onCancel: () => void;
}) {
  const [definition, setDefinition] = useState("");
  const [target, setTarget] = useState("4");
  const [unit, setUnit] = useState("次");
  const [start, setStart] = useState(localDateValue(new Date()));
  const [end, setEnd] = useState(
    localDateValue(new Date(Date.now() + 30 * 86_400_000)),
  );

  const targetValue = Number(target);
  const invalid =
    working ||
    !definition.trim() ||
    !unit.trim() ||
    !Number.isFinite(targetValue) ||
    targetValue <= 0 ||
    end <= start;

  return (
    <Card id="shared-goal-create-card">
      <div className="t-t3">创建共同目标</div>
      <div className="om-form mt-3">
        <textarea
          className="om-input"
          rows={2}
          placeholder="共同目标"
          value={definition}
          onChange={(e) => setDefinition(e.target.value)}
        />
        <div className="flex" style={{ gap: 8 }}>
          <input
            className="om-input"
            type="number"
            min={1}
            placeholder="目标值"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
          />
          <input
            className="om-input"
            placeholder="单位"
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
          />
        </div>
        <label className="t-cap">
          开始
          <input
            className="om-input"
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label className="t-cap">
          结束
          <input
            className="om-input"
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
      </div>
      <div className="flex mt-3" style={{ gap: 8 }}>
        <Btn
          kind="primary"
          sm
          disabled={invalid}
          onClick={() =>
            onCreate({
              definition: definition.trim(),
              period_start: start,
              period_end: end,
              target_value: targetValue,
              unit: unit.trim(),
            })
          }
        >
          {working ? "创建中…" : "创建"}
        </Btn>
        <Btn kind="text" sm onClick={onCancel}>
          取消
        </Btn>
      </div>
    </Card>
  );
}

function GoalCard({
  goal,
  working,
  onSaveNextAction,
}: {
  goal: SharedGoal;
  working: boolean;
  onSaveNextAction: (goal: SharedGoal, nextAction: string) => Promise<boolean>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const current = goal.current_value ?? 0;
  const target = goal.target_value ?? 0;
  const milestones = goal.milestones ?? [];
  const members = goal.member_progress ?? [];

  return (
    <Card data-od-id="shared-goal-card">
      <div className="between">
        <div className="t-t3">{goal.definition ?? "共同目标"}</div>
        {goal.status ? <Chip kind="soft">{goal.status}</Chip> : null}
      </div>
      <div className="mt-3">
        <Progress value={(current / Math.max(target, 1)) * 100} />
      </div>
      <div className="t-foot mt-1" style={{ fontWeight: 700 }}>
        {formatNumber(current)} / {formatNumber(target)} {goal.unit ?? ""}
      </div>
      <div className="t-cap mt-2">系统自动进度 · 到场与完成事实</div>
      {goal.period_start || goal.period_end ? (
        <div className="t-cap mt-1">
          {goal.period_start ?? ""} — {goal.period_end ?? ""}
        </div>
      ) : null}
      {milestones.length ? (
        <div
          className="flex mt-2"
          style={{ gap: 8, justifyContent: "space-between" }}
          aria-label="共同目标里程碑"
        >
          {milestones.map((m) => (
            <div key={`${m.fraction}-${m.target_value}`} style={{ textAlign: "center" }}>
              <div style={{ color: m.reached ? "var(--ink)" : "var(--sage)" }}>
                {m.reached ? "●" : "○"}
              </div>
              <div className="mono t-cap">{Math.round(m.fraction * 100)}%</div>
            </div>
          ))}
        </div>
      ) : null}
      {members.length ? (
        <>
          <Divider />
          <div className="t-foot" style={{ fontWeight: 700, color: "var(--mist)" }}>
            成员事实进度
          </div>
          {members.map((member) => (
            <div key={member.user_id} className="between mt-1">
              <span className="t-foot">{member.display_name ?? "成员"}</span>
              <span className="mono t-foot" style={{ color: "var(--ink)" }}>
                {formatNumber(member.current_value)} {goal.unit ?? ""}
              </span>
            </div>
          ))}
        </>
      ) : null}
      {goal.last_broadcast ? (
        <div className="t-foot mt-2" style={{ color: "var(--mist)" }}>
          {goal.last_broadcast}
        </div>
      ) : null}
      {goal.next_action && !editing ? (
        <div className="mt-2">
          <div className="t-cap">下一步</div>
          <div className="t-call" style={{ fontWeight: 600 }}>
            {goal.next_action}
          </div>
        </div>
      ) : null}
      {editing ? (
        <div className="om-form mt-2">
          <input
            className="om-input"
            placeholder="下一次要一起做什么"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <div className="t-cap">
            这只更新双方可见的下一步，不改写系统记录的事实进度。
          </div>
          <div className="flex" style={{ gap: 8 }}>
            <Btn
              kind="primary"
              sm
              disabled={working || !draft.trim()}
              onClick={() => {
                void onSaveNextAction(goal, draft.trim()).then((ok) => {
                  if (ok) setEditing(false);
                });
              }}
            >
              保存
            </Btn>
            <Btn kind="text" sm onClick={() => setEditing(false)}>
              取消
            </Btn>
          </div>
        </div>
      ) : (
        <Btn
          kind="ghost"
          sm
          disabled={working || goal.status === "completed"}
          onClick={() => {
            setDraft(goal.next_action ?? "");
            setEditing(true);
          }}
        >
          编辑下一步
        </Btn>
      )}
    </Card>
  );
}

export function SharedGoalsScreen() {
  const { relationId } = useParams();
  const { repos } = useApp();
  const [goals, setGoals] = useState<SharedGoal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [showsCreate, setShowsCreate] = useState(false);

  async function load() {
    if (!relationId) return;
    setLoading(true);
    try {
      const raw = await repos.relations.goals(relationId);
      setGoals(asList(raw));
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
  }, [relationId, repos]);

  async function create(draft: {
    definition: string;
    period_start: string;
    period_end: string;
    target_value: number;
    unit: string;
  }) {
    if (!relationId || working) return;
    setWorking(true);
    try {
      await repos.relations.createGoal(
        relationId,
        draft,
        `shared-goal-${relationId}-${crypto.randomUUID()}`,
      );
      await load();
      setShowsCreate(false);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setWorking(false);
    }
  }

  async function saveNextAction(
    goal: SharedGoal,
    nextAction: string,
  ): Promise<boolean> {
    if (working) return false;
    setWorking(true);
    try {
      const updated = await repos.relations.updateGoal(
        goal.id,
        nextAction,
        `shared-goal-next-action-${goal.id}`,
      );
      setGoals((prev) => prev.map((g) => (g.id === updated.id ? updated : g)));
      setError(null);
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
      return false;
    } finally {
      setWorking(false);
    }
  }

  return (
    <Screen id="screen-E11-shared-goals">
      <NavBar backTo={`/relation/${relationId}`} />
      <Scroll>
        <PageHeader eyebrow="长期共同目标" title="共同目标" />
        {showsCreate ? (
          <GoalCreateCard
            working={working}
            onCreate={(draft) => void create(draft)}
            onCancel={() => setShowsCreate(false)}
          />
        ) : (
          <Btn kind="primary" onClick={() => setShowsCreate(true)}>
            创建长期共同目标
          </Btn>
        )}
        {loading ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : goals.length === 0 ? (
          <Card>
            <StateView kind="empty" message="暂时没有内容，有进展时会告诉你。" />
          </Card>
        ) : null}
        {goals.map((goal) => (
          <GoalCard
            key={goal.id}
            goal={goal}
            working={working}
            onSaveNextAction={saveNextAction}
          />
        ))}
        {error ? (
          <Card>
            <StateView
              kind="network"
              message={error}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : null}
      </Scroll>
    </Screen>
  );
}
