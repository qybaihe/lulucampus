import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import {
  asList,
  gapCountOf,
  gatheringStatusName,
  seatsFromGathering,
  type ActionCapability,
  type BackfillOpportunity,
  type CampusAction,
  type DepartedSafetyContext,
  type Gathering,
  type Icebreaker,
  type RescheduleProposal,
} from "../../core/api/repositories";
import {
  isTrustRequirementContext,
  parseTrustRequirement,
  trustCapabilityTitle,
  trustLevelRank,
  trustRecoveryTitle,
  type TrustRequirementContext,
} from "../../core/campus/trustRequirement";
import {
  Btn,
  Card,
  Chip,
  Footer,
  GapBadge,
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
  SeatStrip,
  StateView,
  Stepper,
  Sticker,
  Switch,
} from "../../components/ui/primitives";

function GatheringList({
  id,
  title,
  mode,
}: {
  id: string;
  title: string;
  mode: "open" | "mine";
}) {
  const { repos } = useApp();
  const nav = useNavigate();
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [items, setItems] = useState<Gathering[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setPhase("loading");
    try {
      const raw =
        mode === "open"
          ? await repos.gatherings.open()
          : await repos.gatherings.mine();
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
  }, [repos, mode]);

  return (
    <Screen id={id}>
      <NavBar backTo={mode === "mine" ? "/today" : "/competitions"} />
      <Scroll>
        <PageHeader
          eyebrow={mode === "mine" ? "我发起的" : "正在招募"}
          title={title}
          clip="pool.waiting"
        />
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
          ? items.map((g) => {
              const gap = gapCountOf(g);
              const filled = g.member_count ?? g.filled_count ?? 0;
              const seats = seatsFromGathering(g);
              return (
                <Card key={g.id} onClick={() => nav(`/gathering/${g.id}`)}>
                  <div className="between">
                    <div className="flex">
                      <Sticker name="round-table.png" size="st-44" />
                      <div>
                        <div className="t-t3">{g.title ?? "未命名局"}</div>
                        <div className="t-foot">
                          {gatheringStatusName(g.status)}
                          {g.location || g.location_label
                            ? ` · ${g.location ?? g.location_label}`
                            : ""}
                        </div>
                      </div>
                    </div>
                    {gap > 0 ? (
                      <GapBadge n={gap} />
                    ) : (
                      <span className="om-chip solid">已满员</span>
                    )}
                  </div>
                  {g.target_size ? (
                    <div className="mt-3">
                      <Progress value={(filled / g.target_size) * 100} />
                    </div>
                  ) : null}
                  {seats.length > 0 ? (
                    <div className="mt-3">
                      <SeatStrip seats={seats} />
                    </div>
                  ) : null}
                  {(g.looking_for ?? []).length > 0 &&
                  /Pooling/i.test(String(g.status ?? "")) ? (
                    <div className="flex wrap mt-2" style={{ gap: 6 }}>
                      {g.looking_for!.slice(0, 3).map((role) => (
                        <Chip key={role} kind="gap">
                          {role}
                        </Chip>
                      ))}
                    </div>
                  ) : null}
                </Card>
              );
            })
          : null}
      </Scroll>
    </Screen>
  );
}

export function OpenGatheringsScreen() {
  return (
    <GatheringList
      id="screen-C1-public-gatherings"
      title="公开局"
      mode="open"
    />
  );
}

export function MyGatheringsScreen() {
  return (
    <GatheringList
      id="screen-E1-my-gatherings"
      title="我的局"
      mode="mine"
    />
  );
}

/* ---------- 破冰卡（GET /gatherings/{id}/icebreaker） ---------- */

function IcebreakerCard({
  icebreaker,
  onOpenChannel,
}: {
  icebreaker: Icebreaker;
  onOpenChannel: (channelId: string) => void;
}) {
  const [copied, setCopied] = useState<string | null>(null);
  const checklist = icebreaker.next_steps?.checklist ?? [];
  return (
    <Card data-od-id="gathering-icebreaker-card">
      <div className="t-t3">为什么是你们</div>
      {icebreaker.headline ? (
        <div className="t-call mt-1">{icebreaker.headline}</div>
      ) : null}
      {(icebreaker.facts ?? []).length > 0 ? (
        <div className="flex wrap mt-2">
          {(icebreaker.facts ?? []).map((fact, i) => (
            <span key={i} className="om-chip soft">
              {fact.text}
            </span>
          ))}
        </div>
      ) : null}

      {(icebreaker.first_lines ?? []).length > 0 ? (
        <>
          <div className="t-t3 mt-3">第一句可以这样开</div>
          {(icebreaker.first_lines ?? []).map((line, i) => (
            <button
              key={i}
              type="button"
              className="om-row"
              onClick={() => {
                void navigator.clipboard?.writeText(line).then(() => {
                  setCopied(line);
                });
              }}
            >
              <span className="row-main">
                <span className="row-title">“{line}”</span>
                {copied === line ? <div className="row-sub">已复制</div> : null}
              </span>
            </button>
          ))}
        </>
      ) : null}

      {checklist.length > 0 ? (
        <>
          <div className="t-t3 mt-3">下一步</div>
          {checklist.map((item, i) => (
            <div key={i} className="t-foot mt-1">
              ☐ {item}
            </div>
          ))}
        </>
      ) : null}

      {icebreaker.next_steps?.channel_id ? (
        <Btn
          kind="primary"
          onClick={() => onOpenChannel(icebreaker.next_steps!.channel_id!)}
        >
          带着第一句进群聊
        </Btn>
      ) : null}
    </Card>
  );
}

/* ---------- E5 行动授权 / 修改提案 ---------- */

const MODIFIABLE_PARAM_LABELS: Record<string, string> = {
  room: "研讨室编号",
  venue: "场地资源",
  seminar_id: "研讨资源",
  date: "日期",
  start: "开始",
  end: "结束",
};

function CampusActionCard({
  action,
  currentUserId,
  busy,
  onAuthorize,
  onExecute,
  onProposeModification,
  onApplySuggestion,
}: {
  action: CampusAction;
  currentUserId: string | null;
  busy: boolean;
  onAuthorize: () => void;
  onExecute: () => void;
  onProposeModification: () => void;
  onApplySuggestion: () => void;
}) {
  const auth = action.authorization;
  const previewed = action.status === "previewed";
  const mine = action.user_id === currentUserId;
  const myDecision = auth?.actor_decision;
  const allAuthorized = auth?.all_authorized === true;

  return (
    <Card data-od-id="gathering-action-preview">
      <div className="t-t3">校园写操作预览</div>
      <div className="t-call mt-1">{action.action_name}</div>
      {Object.keys(action.params ?? {}).length > 0 ? (
        <>
          <div className="t-cap mt-2">将提交</div>
          {Object.entries(action.params ?? {}).map(([k, v]) => (
            <div className="between mt-1" key={k}>
              <span className="t-foot">{MODIFIABLE_PARAM_LABELS[k] ?? k}</span>
              <span className="t-foot mono">{String(v)}</span>
            </div>
          ))}
        </>
      ) : null}
      {Object.keys(action.preview_snapshot ?? {}).length > 0 ? (
        <>
          <div className="t-cap mt-2">服务端预览</div>
          {Object.entries(action.preview_snapshot ?? {})
            .slice(0, 6)
            .map(([k, v]) => (
              <div className="between mt-1" key={k}>
                <span className="t-foot">{k}</span>
                <span className="t-foot mono">
                  {typeof v === "object" ? JSON.stringify(v) : String(v)}
                </span>
              </div>
            ))}
        </>
      ) : null}
      {auth ? (
        <div className="t-foot mt-2">
          {auth.authorized_count ?? 0} / {auth.required_count ?? 0} 位成员已核对
        </div>
      ) : null}

      {previewed ? (
        <>
          {myDecision === "not_required" ? (
            <div className="t-foot mt-2">这是找球友的时段参考，不用核对提交。</div>
          ) : myDecision !== "authorized" ? (
            <Btn kind="primary" disabled={busy} onClick={onAuthorize}>
              核对无误，分别确认
            </Btn>
          ) : !allAuthorized ? (
            <>
              <Btn kind="primary" disabled>
                等待其他成员确认
              </Btn>
              <div className="t-cap center mt-1">
                每位当前成员都要核对同一份预览
              </div>
            </>
          ) : mine ? (
            <Btn kind="primary" disabled={busy} onClick={onExecute}>
              全员已确认，由我执行
            </Btn>
          ) : (
            <>
              <Btn kind="primary" disabled>
                已完成分别确认
              </Btn>
              <div className="t-cap center mt-1">
                等待本局发起人的授权代理提交
              </div>
            </>
          )}
          <Btn kind="ghost" disabled={busy} onClick={onProposeModification}>
            提议修改预览…
          </Btn>
        </>
      ) : null}

      {action.modification ? (
        <div className="mt-3" data-od-id="action-pending-modification">
          <div className="divider" />
          <div className="t-t3">成员匿名修改建议</div>
          <div className="t-foot mt-1">{action.modification.reason}</div>
          {Object.keys(action.modification.proposed_params ?? {}).length > 0 ? (
            <>
              <div className="t-cap mt-2">建议后的完整参数</div>
              {Object.entries(action.modification.proposed_params ?? {}).map(
                ([k, v]) => (
                  <div className="between mt-1" key={k}>
                    <span className="t-foot">
                      {MODIFIABLE_PARAM_LABELS[k] ?? k}
                    </span>
                    <span className="t-foot mono">{String(v)}</span>
                  </div>
                ),
              )}
            </>
          ) : null}
          {mine && action.modification.status !== "applied" ? (
            <Btn kind="ghost" disabled={busy} onClick={onApplySuggestion}>
              应用建议并生成新版预览
            </Btn>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}

/* ---------- E3 局详情 ---------- */

export function GatheringDetailScreen() {
  const { gatheringId } = useParams();
  const { repos } = useApp();
  const nav = useNavigate();
  const [g, setG] = useState<Gathering | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sheet, setSheet] = useState<
    "leave" | "report" | "recur" | "recurring" | "modify" | null
  >(null);
  const [reportReason, setReportReason] = useState("");
  const [reportTargetId, setReportTargetId] = useState<string | null>(null);
  const [reportAndBlock, setReportAndBlock] = useState(false);
  const [reschedule, setReschedule] = useState<RescheduleProposal | null>(null);
  const [timeOptions, setTimeOptions] = useState<Array<Record<string, unknown>>>(
    [],
  );
  const [backfill, setBackfill] = useState<BackfillOpportunity | null>(null);
  const [capability, setCapability] = useState<ActionCapability | null>(null);
  const [bookingOptions, setBookingOptions] = useState<
    Array<Record<string, unknown>>
  >([]);
  const [campusAction, setCampusAction] = useState<CampusAction | null>(null);
  const [icebreaker, setIcebreaker] = useState<Icebreaker | null>(null);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // 复局三选一
  const [keepIds, setKeepIds] = useState<Set<string>>(new Set());
  // T3 固定周期
  const [recFirstStart, setRecFirstStart] = useState(defaultStartValue(1));
  const [recOccurrences, setRecOccurrences] = useState(4);
  const [recIntervalWeeks, setRecIntervalWeeks] = useState(1);
  const [recDuration, setRecDuration] = useState(90);
  const [recCreated, setRecCreated] = useState<Gathering[] | null>(null);
  // 修改提案
  const [modifyReason, setModifyReason] = useState("");
  const [modifyParams, setModifyParams] = useState<Record<string, string>>({});
  const [celebrate, setCelebrate] = useState(false);

  async function load(): Promise<Gathering | null> {
    if (!gatheringId) return null;
    try {
      let detail = await repos.gatherings.get(gatheringId);
      if (
        /Pooling/i.test(detail.status ?? "") &&
        detail.my_confirmation != null &&
        /比赛/.test(detail.gathering_type ?? "") &&
        (detail.member_count ?? 0) >= (detail.min_size ?? 2)
      ) {
        try {
          const sealed = await repos.gatherings.join(
            gatheringId,
            detail.required_roles?.length === 1
              ? { role: detail.required_roles[0] }
              : {},
            crypto.randomUUID(),
          );
          if (/Confirmed/i.test(sealed.status ?? "")) {
            setCelebrate(true);
          }
          detail = sealed;
        } catch {
          /* stay on pooling detail */
        }
      }
      setG(detail);
      setError(null);
      // Side loads — soft: surface only when server has data / allows
      const [rs, times, bf, cap, book] = await Promise.all([
        repos.gatherings.currentReschedule(gatheringId).catch(() => null),
        repos.gatherings.timeOptions(gatheringId).catch(() => []),
        repos.gatherings.backfill(gatheringId).catch(() => null),
        repos.gatherings.actionCapability(gatheringId).catch(() => null),
        repos.gatherings.bookingOptions(gatheringId).catch(() => []),
      ]);
      setReschedule(rs);
      setTimeOptions(Array.isArray(times) ? times : []);
      setBackfill(bf);
      setCapability(cap);
      setBookingOptions(Array.isArray(book) ? book : []);
      if (detail.action_id) {
        setCampusAction(
          await repos.actions.get(detail.action_id).catch(() => null),
        );
      } else {
        setCampusAction(null);
      }
      // 破冰：成局后静默拉取（对齐 iOS try?）
      const status = detail.status ?? "";
      if (
        /confirmed|previewed|executed|active/i.test(status) &&
        detail.my_confirmation != null
      ) {
        setIcebreaker(
          await repos.gatherings.icebreaker(gatheringId).catch(() => null),
        );
      } else {
        setIcebreaker(null);
      }
      return detail;
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      return null;
    }
  }

  useEffect(() => {
    void load();
    void repos.profile
      .me()
      .then((me) => setCurrentUserId(me.user_id ?? null))
      .catch(() => setCurrentUserId(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gatheringId, repos]);

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(true);
    try {
      const before = g?.status ?? "";
      await fn();
      const detail = await load();
      if (
        /(Pooling|Tentative)/i.test(before) &&
        /Confirmed/i.test(detail?.status ?? "")
      ) {
        setCelebrate(true);
      }
    } catch (e) {
      const trust = parseTrustRequirement(e, {
        kind: "gathering",
        id: gatheringId ?? "",
      });
      if (trust) {
        nav(`/gathering/${gatheringId}/trust`, { state: trust });
      } else {
        setError(e instanceof Error ? e.message : `${label}失败`);
      }
    } finally {
      setBusy(false);
    }
  }

  const status = g?.status ?? "";
  const terminal = /Dissolved|Expired/i.test(status);
  const completed = /Completed/i.test(status);
  const seats = g ? seatsFromGathering(g) : [];
  const gap = g ? gapCountOf(g) : 0;
  const filled = g?.member_count ?? g?.filled_count ?? 0;
  const modifiableKeys = Object.keys(campusAction?.params ?? {}).filter(
    (k) => k in MODIFIABLE_PARAM_LABELS,
  );

  function openModifySheet() {
    const params = campusAction?.params ?? {};
    const preset: Record<string, string> = {};
    for (const key of Object.keys(params)) {
      if (key in MODIFIABLE_PARAM_LABELS) preset[key] = String(params[key] ?? "");
    }
    setModifyParams(preset);
    setModifyReason("");
    setSheet("modify");
  }

  const changedModifyParams = () => {
    const out: Record<string, unknown> = {};
    const params = campusAction?.params ?? {};
    for (const [k, v] of Object.entries(modifyParams)) {
      if (String(params[k] ?? "") !== v && v.trim()) out[k] = v.trim();
    }
    return out;
  };

  return (
    <Screen id="screen-E3-gathering-detail">
      <NavBar
        backTo="/gatherings/mine"
        right={
          <button
            type="button"
            className="nav-back"
            aria-label="安全"
            onClick={() => setSheet("report")}
          >
            <Icon name="warn" size={18} />
          </button>
        }
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
        ) : !g ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : (
          <>
            <PageHeader
              eyebrow={`${g.gathering_type ? `${g.gathering_type} · ` : ""}${gatheringStatusName(status)}`}
              title={g.title ?? "未命名局"}
              clip="confirm.gather"
            />
            {g.location || g.location_label ? (
              <div className="t-foot" style={{ marginTop: -4, marginBottom: 12 }}>
                {g.location ?? g.location_label}
              </div>
            ) : null}

            {typeof g.mood_note === "string" && g.mood_note ? (
              <Note sticker="chat-bubble.png">{g.mood_note}</Note>
            ) : null}

            {typeof g.match_reason === "string" && g.match_reason ? (
              <Card>
                <div className="t-t3">为什么是你们</div>
                <div className="t-foot mt-2">{g.match_reason}</div>
              </Card>
            ) : null}

            {(g.looking_for ?? []).length > 0 && /Pooling/i.test(status) ? (
              <Card className="mt-3">
                <div className="t-t3">这桌还在找</div>
                <div className="flex wrap mt-2" style={{ gap: 6 }}>
                  {g.looking_for!.map((role) => (
                    <Chip key={role} kind="gap">
                      {role}
                    </Chip>
                  ))}
                </div>
              </Card>
            ) : null}

            {(g.participants ?? []).length > 0 && !/Pooling/i.test(status) ? (
              <Card className="mt-3">
                <div className="t-t3">参与成员</div>
                {g.participants!.map((p, i) => {
                  const uid = String(p.user_id ?? i);
                  const name =
                    (typeof p.display_name === "string" && p.display_name) ||
                    p.label ||
                    `成员 ···${uid.slice(-4)}`;
                  return (
                    <div key={uid} className="mt-2">
                      <div className="t-call">{name}</div>
                      {(p.interest_tags ?? []).length > 0 ? (
                        <div className="t-foot mt-1">
                          {p.interest_tags!.slice(0, 4).join(" · ")}
                        </div>
                      ) : null}
                      {p.taste_summary ? (
                        <div className="t-cap mt-1">{p.taste_summary}</div>
                      ) : null}
                    </div>
                  );
                })}
              </Card>
            ) : null}

            <Card className="mt-4">
              <div className="between mb-2">
                <span className="t-foot">
                  已就位 <b className="mono">{filled}</b> / {g.target_size ?? "—"}
                  {typeof g.min_size === "number" &&
                  g.min_size > 0 &&
                  g.min_size !== g.target_size
                    ? ` · ${g.min_size}–${g.target_size} 人`
                    : ""}
                </span>
                {gap > 0 ? (
                  <GapBadge n={gap} />
                ) : (
                  <span className="om-chip solid">已满员</span>
                )}
              </div>
              {g.target_size ? (
                <Progress value={(filled / g.target_size) * 100} />
              ) : null}
              {seats.length > 0 ? (
                <div className="mt-3" data-od-id="gathering-seats-from-server">
                  <SeatStrip seats={seats} />
                </div>
              ) : (
                <div className="t-cap mt-2">席位以服务端人数为准，暂无角色明细</div>
              )}
              {/Pooling/i.test(status) ? (
                <div className="t-foot mt-2">噜噜正在翻今晚有空的同学……</div>
              ) : null}
            </Card>

            {message ? (
              <Card>
                <div className="t-foot">{message}</div>
              </Card>
            ) : null}

            {terminal ? (
              <Card data-od-id="gathering-terminal-state">
                <StateView kind="empty" message={`局已结束：${gatheringStatusName(status)}`} />
              </Card>
            ) : null}

            {/* 破冰卡 */}
            {icebreaker ? (
              <IcebreakerCard
                icebreaker={icebreaker}
                onOpenChannel={(cid) => nav(`/channel/${cid}`)}
              />
            ) : null}

            {/* E3 多人确认 */}
            {/Tentative/i.test(status) ? (
              <Card data-od-id="gathering-confirmation-actions">
                <div className="t-t3">多人确认</div>
                <div className="t-foot mt-1">
                  差你的一票，局才能锁定
                  {g.my_confirmation ? ` · 当前：${g.my_confirmation}` : ""}
                </div>
                <Btn
                  kind="primary"
                  disabled={busy}
                  onClick={() =>
                    void run("确认", () =>
                      repos.gatherings.confirm(g.id, true, crypto.randomUUID()),
                    )
                  }
                >
                  确认参加
                </Btn>
                <Btn
                  kind="ghost"
                  disabled={busy}
                  onClick={() =>
                    void run("暂不参加", () =>
                      repos.gatherings.confirm(g.id, false, crypto.randomUUID()),
                    )
                  }
                >
                  暂不参加
                </Btn>
              </Card>
            ) : null}

            {/* E7 协作空间 */}
            {/Confirmed|Executed|Active/i.test(status) ? (
              <Card data-od-id="gathering-collaboration-space">
                <div className="t-t3">协作空间</div>
                <div className="t-foot mt-1">
                  已确认/执行中 · 场次与行动由服务端驱动
                </div>
                {g.channel_id ? (
                  <Btn kind="ghost" to={`/channel/${g.channel_id}`}>
                    进入局内消息
                  </Btn>
                ) : (
                  <div className="t-cap mt-2">成局后开启群聊</div>
                )}
              </Card>
            ) : null}

            {/* E4 改约（仅协商阶段，对齐 iOS 按状态加载） */}
            {/Tentative|Confirmed|Previewed/i.test(status) || reschedule ? (
              <Card data-od-id="gathering-reschedule-actions">
                <div className="t-t3">改约协商</div>
                {reschedule ? (
                  <>
                    <div className="t-foot mt-1">
                      进行中提案
                      {reschedule.start_at
                        ? ` · ${new Date(reschedule.start_at).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}`
                        : ""}
                      {reschedule.status ? ` · ${reschedule.status}` : ""}
                    </div>
                    <div className="flex mt-2" style={{ gap: 8 }}>
                      <Btn
                        kind="primary"
                        sm
                        disabled={busy}
                        onClick={() =>
                          void run("投票", () =>
                            repos.gatherings.voteReschedule(
                              g.id,
                              reschedule.id ?? reschedule.proposal_id ?? "",
                              true,
                              crypto.randomUUID(),
                            ),
                          )
                        }
                      >
                        同意
                      </Btn>
                      <Btn
                        kind="ghost"
                        sm
                        disabled={busy}
                        onClick={() =>
                          void run("投票", () =>
                            repos.gatherings.voteReschedule(
                              g.id,
                              reschedule.id ?? reschedule.proposal_id ?? "",
                              false,
                              crypto.randomUUID(),
                            ),
                          )
                        }
                      >
                        不同意
                      </Btn>
                    </div>
                  </>
                ) : timeOptions.length > 0 ? (
                  <>
                    <div className="t-foot mt-1">可选时段来自服务端</div>
                    {timeOptions.slice(0, 4).map((opt, i) => {
                      const start = String(opt.start_at ?? opt.startAt ?? "");
                      const end = String(opt.end_at ?? opt.endAt ?? "");
                      return (
                        <Row
                          key={i}
                          icon={<Icon name="clock" size={20} />}
                          title={start || `时段 ${i + 1}`}
                          sub={end || undefined}
                          right={
                            <Btn
                              kind="ghost"
                              sm
                              disabled={busy || !start || !end}
                              onClick={() =>
                                void run("改约", () =>
                                  repos.gatherings.reschedule(
                                    g.id,
                                    { start_at: start, end_at: end },
                                    crypto.randomUUID(),
                                  ),
                                )
                              }
                            >
                              提议
                            </Btn>
                          }
                        />
                      );
                    })}
                  </>
                ) : (
                  <div className="t-foot mt-1">当前无开放改约提案</div>
                )}
              </Card>
            ) : null}

            {/* E5 行动预览：授权/执行/修改提案状态机 */}
            {campusAction ? (
              <CampusActionCard
                action={campusAction}
                currentUserId={currentUserId}
                busy={busy}
                onAuthorize={() =>
                  void run("授权", () =>
                    repos.actions.authorize(
                      campusAction.id,
                      campusAction.snapshot_hash ?? "",
                      crypto.randomUUID(),
                    ),
                  )
                }
                onExecute={() =>
                  void run("执行", () =>
                    repos.actions.execute(
                      { action_id: campusAction.id, confirm: true },
                      crypto.randomUUID(),
                    ),
                  )
                }
                onProposeModification={openModifySheet}
                onApplySuggestion={() =>
                  void run("应用建议", async () => {
                    await repos.actions.preview({
                      action: campusAction.action_name,
                      params: {
                        ...(campusAction.params ?? {}),
                        ...(campusAction.modification?.proposed_params ?? {}),
                      },
                      gathering_id: g.id,
                    });
                    setMessage("旧预览已失效；请让全员重新核对新版预览。");
                  })
                }
              />
            ) : (
              <Card data-od-id="gathering-action-preview">
                <div className="t-t3">行动能力</div>
                {capability ? (
                  <>
                    <div className="t-foot mt-1">
                      {capability.enabled
                        ? `可执行：${capability.action ?? "行动"}`
                        : capability.disabled_reason ?? "暂不可用"}
                    </div>
                    {capability.enabled ? (
                      <Btn
                        kind="primary"
                        disabled={busy}
                        onClick={() =>
                          void run("行动预览", () =>
                            repos.actions.preview({
                              action: capability.action,
                              params: capability.params ?? {},
                              gathering_id: g.id,
                            }),
                          )
                        }
                      >
                        预览行动
                      </Btn>
                    ) : null}
                  </>
                ) : (
                  <div className="t-foot mt-1">正在读取能力…或当前状态无行动</div>
                )}
                {bookingOptions.length > 0 ? (
                  <>
                    <Section title="预约选项" />
                    {bookingOptions.slice(0, 4).map((opt, i) => (
                      <Row
                        key={i}
                        title={String(opt.label ?? opt.option_token ?? `选项 ${i + 1}`)}
                        sub={String(opt.location ?? opt.start_at ?? "")}
                        right={
                          <Btn
                            kind="ghost"
                            sm
                            disabled={busy}
                            onClick={() =>
                              void run("选预约", () =>
                                repos.gatherings.bookingPlan(
                                  g.id,
                                  String(opt.option_token ?? ""),
                                  crypto.randomUUID(),
                                ),
                              )
                            }
                          >
                            选用
                          </Btn>
                        }
                      />
                    ))}
                  </>
                ) : null}
              </Card>
            )}

            {campusAction?.execution_result ? (
              <Card data-od-id="gathering-action-result">
                <div className="t-t3">执行结果</div>
                <div className="t-foot mt-1">
                  {String(
                    campusAction.execution_result.status ??
                      campusAction.execution_result.message ??
                      campusAction.status ??
                      "已有执行记录",
                  )}
                </div>
              </Card>
            ) : null}

            {/* E8 补位 */}
            <Card data-od-id="gathering-backfill-actions">
              <div className="t-t3">补位</div>
              {backfill?.available || gap > 0 ? (
                <>
                  <div className="t-foot mt-1">
                    {backfill?.eligibility ??
                      (gap > 0 ? `还缺 ${gap} 人` : "可补位")}
                  </div>
                  <Btn
                    kind="primary"
                    disabled={busy}
                    onClick={() =>
                      void run("认领补位", () =>
                        repos.gatherings.claimBackfill(g.id, crypto.randomUUID()),
                      )
                    }
                  >
                    认领补位
                  </Btn>
                  {(backfill?.options ?? []).map((opt) => (
                    <Btn
                      key={opt.key}
                      kind="ghost"
                      disabled={busy}
                      onClick={() =>
                        void run("补位兜底", () =>
                          repos.gatherings.backfillFallback(
                            g.id,
                            String(opt.key),
                            crypto.randomUUID(),
                          ),
                        )
                      }
                    >
                      {opt.label ?? opt.key}
                    </Btn>
                  ))}
                </>
              ) : (
                <div className="t-foot mt-1">当前无需补位</div>
              )}
            </Card>

            {/* E9 完成 */}
            {/Executed|Active/i.test(status) ? (
              <Card data-od-id="gathering-completion-actions">
                {(() => {
                  const endAt = g.end_at ?? g.ends_at;
                  const ended = endAt ? new Date(endAt).getTime() <= Date.now() : false;
                  if (!ended) {
                    return (
                      <>
                        <div className="flex">
                          <Sticker name="alarm-clock.png" size="st-44" />
                          <div style={{ marginLeft: 10 }}>
                            <div className="t-t3">
                              {/Active/i.test(status)
                                ? "这次局正在进行"
                                : "预约已完成，等待开始"}
                            </div>
                            <div className="t-foot mt-1">
                              服务端记录的结束时间到达后，才会开放完成确认。
                            </div>
                          </div>
                        </div>
                        <Btn kind="primary" disabled disabledReason="尚未到服务端结束时间">
                          结束后确认完成
                        </Btn>
                      </>
                    );
                  }
                  return (
                    <>
                      <div className="t-t3">完成确认</div>
                      <div className="t-foot mt-1">结束后可发起复局</div>
                      <Btn
                        kind="primary"
                        disabled={busy}
                        onClick={() =>
                          void run("完成", () =>
                            repos.gatherings.complete(g.id, true, crypto.randomUUID()),
                          )
                        }
                      >
                        确认本次已完成
                      </Btn>
                      <Btn
                        kind="ghost"
                        disabled={busy}
                        onClick={() =>
                          void run("未完成", () =>
                            repos.gatherings.complete(g.id, false, crypto.randomUUID()),
                          )
                        }
                      >
                        这次没有完成
                      </Btn>
                    </>
                  );
                })()}
              </Card>
            ) : null}

            {/* E10 复局（Completed 后） */}
            {completed ? (
              <Card data-od-id="gathering-recurrence-actions">
                <div className="t-t3">复局选择</div>
                {g.my_recurrence_decision ? (
                  <>
                    <div className="t-foot mt-1">
                      {recurrenceDecisionLabel(g.my_recurrence_decision)}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="t-foot mt-1">
                      同一桌人、同样的类型；时间地点可以再商量。
                    </div>
                    <Btn
                      kind="primary"
                      disabled={busy}
                      onClick={() => {
                        setKeepIds(new Set());
                        setSheet("recur");
                      }}
                    >
                      再来一次
                    </Btn>
                    <Btn
                      kind="ghost"
                      disabled={busy}
                      onClick={() => {
                        setRecCreated(null);
                        setSheet("recurring");
                      }}
                    >
                      T3 · 周期固定局
                    </Btn>
                  </>
                )}
              </Card>
            ) : null}

            <Section title="协作" />
            <Card tight>
              {g.channel_id ? (
                <Row
                  icon={<Sticker name="chat-bubble.png" size="st-24" />}
                  title="局内群聊"
                  sub="只有已成局的人"
                  to={`/channel/${g.channel_id}`}
                />
              ) : (
                <Row
                  icon={<Sticker name="chat-bubble.png" size="st-24" />}
                  title="局内群聊"
                  sub="成局后开启"
                />
              )}
              <Row
                icon={<Icon name="share" size={20} />}
                title="分享缺口卡"
                sub="匿名落地页"
                onClick={() =>
                  void run("分享", async () => {
                    const s = await repos.gatherings.share(g.id);
                    if (s.share_token) nav(`/g/${s.share_token}`);
                  })
                }
              />
              {g.my_confirmation && !terminal && !completed ? (
                <Row
                  icon={<Icon name="exit" size={20} />}
                  title="退出这个局…"
                  sub={
                    typeof g.leave_capability?.message === "string"
                      ? g.leave_capability.message
                      : "确定退出这个局？"
                  }
                  onClick={
                    g.leave_capability?.enabled === false
                      ? undefined
                      : () => setSheet("leave")
                  }
                />
              ) : null}
            </Card>
          </>
        )}
      </Scroll>

      {g && /Pooling/i.test(status) && !g.my_confirmation ? (
        <Footer>
          <Btn
            kind="primary"
            onClick={() =>
              void run("入局", () =>
                repos.gatherings.join(
                  g.id,
                  (g.required_roles?.length === 1
                    ? { role: g.required_roles[0] }
                    : {}),
                  crypto.randomUUID(),
                ),
              )
            }
            disabled={busy}
          >
            加入这个局
          </Btn>
        </Footer>
      ) : null}

      {sheet === "leave" ? (
        <div className="om-sheet" data-od-id="gathering-leave-action">
          <div className="sheet-grab" />
          <div className="t-t3">确认退出？</div>
          <div className="t-foot mt-2">
            {typeof g?.leave_capability?.message === "string"
              ? g.leave_capability.message
              : "确定退出这个局？"}
          </div>
          <Btn
            kind="primary"
            onClick={() =>
              void run("退出", async () => {
                await repos.gatherings.leave(g!.id, crypto.randomUUID());
                setSheet(null);
                nav("/gatherings/mine");
              })
            }
            disabled={busy}
          >
            确认退出
          </Btn>
          <Btn kind="text" onClick={() => setSheet(null)}>
            取消
          </Btn>
        </div>
      ) : null}

      {sheet === "report" && g ? (
        <div className="om-sheet" data-od-id="gathering-safety-report">
          <div className="sheet-grab" />
          <div className="t-t3">举报本局 / 拉黑成员</div>
          {(g.participants ?? []).length > 0 ? (
            <>
              <div className="t-cap mt-2">举报对象</div>
              <div className="flex wrap mt-1">
                <Chip
                  kind={reportTargetId === null ? "gap" : "soft"}
                  onClick={() => {
                    setReportTargetId(null);
                    setReportAndBlock(false);
                  }}
                >
                  只举报本局
                </Chip>
                {(g.participants ?? []).map((p, i) => {
                  const uid = String(p.user_id ?? i);
                  return (
                    <Chip
                      key={uid}
                      kind={reportTargetId === uid ? "gap" : "soft"}
                      onClick={() => {
                        setReportTargetId(uid);
                        setReportAndBlock(true);
                      }}
                    >
                      {p.display_name || "已披露成员"}
                    </Chip>
                  );
                })}
              </div>
            </>
          ) : null}
          <textarea
            className="om-input mt-2"
            placeholder="说明事实经过"
            value={reportReason}
            onChange={(e) => setReportReason(e.target.value)}
          />
          {reportTargetId ? (
            <div className="between mt-2">
              <span className="t-call">同时拉黑该成员</span>
              <Switch on={reportAndBlock} onChange={setReportAndBlock} />
            </div>
          ) : null}
          <Btn
            kind="primary"
            disabled={busy || !reportReason.trim()}
            onClick={() =>
              void run("举报", async () => {
                await repos.gatherings.report(
                  g.id,
                  {
                    reason: reportReason.trim(),
                    reported_user_id: reportTargetId ?? undefined,
                    block: Boolean(reportTargetId) && reportAndBlock,
                  },
                  crypto.randomUUID(),
                );
                setSheet(null);
                setReportReason("");
                setReportTargetId(null);
                setReportAndBlock(false);
              })
            }
          >
            提交举报
          </Btn>
          <Btn kind="ghost" onClick={() => setSheet(null)}>
            关闭
          </Btn>
        </div>
      ) : null}

      {/* 复局三选一（keep_user_ids） */}
      {sheet === "recur" && g ? (
        <div className="om-sheet" data-od-id="gathering-recurrence-choice">
          <div className="sheet-grab" />
          <div className="t-t3">复局选择</div>
          <div className="t-foot mt-1">
            同一桌人、同样的类型；时间地点可以再商量。
          </div>
          <Btn
            kind="primary"
            disabled={busy}
            onClick={() =>
              void run("复局", async () => {
                const clone = await repos.gatherings.recur(
                  g.id,
                  undefined,
                  crypto.randomUUID(),
                );
                setSheet(null);
                if (clone?.id) nav(`/gathering/${clone.id}`);
              })
            }
          >
            原班再来一次
          </Btn>

          {(g.participants ?? []).length > 0 ? (
            <>
              <div className="t-cap mt-3">保留部分成员，再差一个</div>
              {(g.participants ?? []).map((p, i) => {
                const uid = String(p.user_id ?? i);
                const label =
                  (typeof p.display_name === "string" && p.display_name) ||
                  p.label ||
                  `成员 ···${uid.slice(-4)}`;
                return (
                  <div className="between mt-2" key={uid}>
                    <span className="t-call">{String(label)}</span>
                    <Switch
                      on={keepIds.has(uid)}
                      onChange={(on) =>
                        setKeepIds((prev) => {
                          const next = new Set(prev);
                          if (on) next.add(uid);
                          else next.delete(uid);
                          return next;
                        })
                      }
                    />
                  </div>
                );
              })}
              <Btn
                kind="ghost"
                disabled={busy || keepIds.size === 0}
                onClick={() =>
                  void run("复局", async () => {
                    const clone = await repos.gatherings.recur(
                      g.id,
                      Array.from(keepIds),
                      crypto.randomUUID(),
                    );
                    setSheet(null);
                    if (clone?.id) nav(`/gathering/${clone.id}`);
                  })
                }
              >
                保留所选并回池补人
              </Btn>
            </>
          ) : null}

          <div className="t-cap mt-3">
            不再发起复局；其他成员看不到你的选择。
          </div>
          <Btn
            kind="text"
            disabled={busy}
            onClick={() =>
              void run("安静结束", async () => {
                await repos.gatherings.finishRecur(g.id, crypto.randomUUID());
                setSheet(null);
              })
            }
          >
            安静结束
          </Btn>
          <Btn kind="text" onClick={() => setSheet(null)}>
            取消
          </Btn>
        </div>
      ) : null}

      {/* T3 固定周期（POST /gatherings/{id}/recurring） */}
      {sheet === "recurring" && g ? (
        <div className="om-sheet" data-od-id="gathering-recurring-series">
          <div className="sheet-grab" />
          <div className="t-t3">周期性固定局</div>
          <div className="t-foot mt-1">固定周期 · 从这局克隆多期</div>
          {recCreated ? (
            <>
              <div className="t-call mt-2">已创建 {recCreated.length} 期</div>
              {recCreated.map((item) => (
                <Row
                  key={item.id}
                  icon={<Icon name="clock" size={18} />}
                  title={item.title ?? "固定局"}
                  sub={item.start_at ?? undefined}
                  onClick={() => {
                    setSheet(null);
                    nav(`/gathering/${item.id}`);
                  }}
                />
              ))}
              <Btn kind="text" onClick={() => setSheet(null)}>
                关闭
              </Btn>
            </>
          ) : (
            <>
              <div className="t-cap mt-2">首期开始时间</div>
              <input
                type="datetime-local"
                className="om-input mt-1"
                value={recFirstStart}
                onChange={(e) => setRecFirstStart(e.target.value)}
              />
              <div className="between mt-3">
                <span className="t-call">期数</span>
                <Stepper
                  value={recOccurrences}
                  min={2}
                  max={12}
                  onChange={setRecOccurrences}
                />
              </div>
              <div className="between mt-2">
                <span className="t-call">间隔 · 周</span>
                <Stepper
                  value={recIntervalWeeks}
                  min={1}
                  max={4}
                  onChange={setRecIntervalWeeks}
                />
              </div>
              <div className="between mt-2">
                <span className="t-call">每期时长（分钟）</span>
                <Stepper
                  value={recDuration}
                  min={30}
                  max={1440}
                  step={30}
                  onChange={setRecDuration}
                />
              </div>
              <Btn
                kind="primary"
                disabled={busy || !recFirstStart}
                onClick={() =>
                  void run("创建固定周期", async () => {
                    const created = await repos.gatherings.recurring(
                      g.id,
                      {
                        first_start_at: new Date(recFirstStart).toISOString(),
                        occurrences: recOccurrences,
                        interval_weeks: recIntervalWeeks,
                        duration_minutes: recDuration,
                      },
                      crypto.randomUUID(),
                    );
                    setRecCreated(created);
                  })
                }
              >
                创建固定周期
              </Btn>
              <Btn kind="text" onClick={() => setSheet(null)}>
                取消
              </Btn>
            </>
          )}
        </div>
      ) : null}

      {/* E5 修改提案 sheet */}
      {sheet === "modify" && campusAction ? (
        <div className="om-sheet" data-od-id="screen-E5-action-modification">
          <div className="sheet-grab" />
          <div className="t-t3">提议修改</div>
          <div className="t-cap mt-2">为什么需要修改</div>
          <textarea
            className="om-input mt-1"
            placeholder="例如：时间可以，但希望换成东区 401"
            value={modifyReason}
            onChange={(e) => setModifyReason(e.target.value)}
          />
          {modifiableKeys.length > 0 ? (
            <>
              <div className="t-cap mt-2">修改后的可执行参数</div>
              {modifiableKeys.map((key) => (
                <input
                  key={key}
                  className="om-input mt-1"
                  placeholder={MODIFIABLE_PARAM_LABELS[key]}
                  value={modifyParams[key] ?? ""}
                  onChange={(e) =>
                    setModifyParams((prev) => ({ ...prev, [key]: e.target.value }))
                  }
                />
              ))}
            </>
          ) : null}
          <Btn
            kind="primary"
            disabled={
              busy ||
              modifyReason.trim().length < 5 ||
              Object.keys(changedModifyParams()).length === 0
            }
            onClick={() =>
              void run("提交建议", async () => {
                await repos.actions.proposeModification(
                  campusAction.id,
                  {
                    snapshot_hash: campusAction.snapshot_hash ?? "",
                    reason: modifyReason.trim(),
                    proposed_params: changedModifyParams(),
                  },
                  crypto.randomUUID(),
                );
                setSheet(null);
                setMessage(
                  "旧预览已失效；请由发起人生成新预览并让全员重新核对。",
                );
              })
            }
          >
            提交建议
          </Btn>
          <Btn kind="text" onClick={() => setSheet(null)}>
            取消
          </Btn>
        </div>
      ) : null}
      {celebrate && g ? (
        <GatheringCelebrationOverlay
          gathering={g}
          onEnterChat={() => {
            setCelebrate(false);
            if (g.channel_id) nav(`/channel/${g.channel_id}`);
          }}
          onDismiss={() => setCelebrate(false)}
        />
      ) : null}
    </Screen>
  );
}

function GatheringCelebrationOverlay({
  gathering,
  onEnterChat,
  onDismiss,
}: {
  gathering: Gathering;
  onEnterChat: () => void;
  onDismiss: () => void;
}) {
  const [stage, setStage] = useState(0);
  const finished = useRef(false);
  const seated = gathering.member_count ?? gathering.target_size ?? 0;

  function enterChat() {
    if (finished.current) return;
    finished.current = true;
    onEnterChat();
  }

  useEffect(() => {
    const t1 = window.setTimeout(() => setStage(1), 120);
    const t2 = window.setTimeout(() => setStage(2), 900);
    const t3 = window.setTimeout(() => setStage(3), 1600);
    const t4 = window.setTimeout(enterChat, 2800);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.clearTimeout(t3);
      window.clearTimeout(t4);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="om-celebration" data-od-id="gathering-celebration-overlay">
      <LuluMark placement="confirm" clip="confirm.gather" />
      <div className="t-t1 mt-3" style={{ opacity: stage >= 2 ? 1 : 0 }}>
        凑齐了！
      </div>
      <div className="t-foot mt-2" style={{ opacity: stage >= 2 ? 1 : 0 }}>
        {seated} 个人的「{gathering.title ?? "这一局"}」正式成局
      </div>
      {stage >= 3 ? (
        <div className="stack mt-4" style={{ width: "100%", gap: 10 }}>
          <Btn kind="primary" onClick={enterChat}>
            {gathering.channel_id ? "进入群聊" : "看看为什么是你们"}
          </Btn>
          <Btn
            kind="text"
            onClick={() => {
              finished.current = true;
              onDismiss();
            }}
          >
            稍后再说
          </Btn>
        </div>
      ) : null}
    </div>
  );
}

function recurrenceDecisionLabel(decision: string): string {
  if (/finish|quiet|end/i.test(decision)) return "已安静结束";
  if (/partial|keep/i.test(decision)) return "已选择保留部分成员";
  return "已选择原班复局";
}

function defaultStartValue(daysFromNow: number): string {
  const d = new Date();
  d.setDate(d.getDate() + daysFromNow);
  d.setMinutes(0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`;
}

/* ---------- E2 直接发起局（POST /gatherings/initiate） ---------- */

export function InitiateGatheringScreen() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [title, setTitle] = useState("");
  const [goal, setGoal] = useState("");
  const [gatheringType, setGatheringType] = useState("自习");
  const [campus, setCampus] = useState("珠海校区");
  const [location, setLocation] = useState("");
  const [minSize, setMinSize] = useState(3);
  const [targetSize, setTargetSize] = useState(4);
  const [crossCollege, setCrossCollege] = useState(false);
  const [fixedTime, setFixedTime] = useState(false);
  const [startAt, setStartAt] = useState(defaultStartValue(1));
  const [endAt, setEndAt] = useState(() => {
    const base = defaultStartValue(1);
    const d = new Date(base);
    d.setMinutes(d.getMinutes() + 90);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const valid =
    title.trim().length >= 2 &&
    goal.trim().length >= 2 &&
    gatheringType.trim().length >= 1 &&
    minSize <= targetSize &&
    (!fixedTime || new Date(endAt) > new Date(startAt));

  async function create() {
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    try {
      const created = await repos.gatherings.initiate(
        {
          title: title.trim(),
          goal: goal.trim(),
          gathering_type: gatheringType.trim(),
          mode: "similar",
          campus: campus.trim() || null,
          location: location.trim() || null,
          start_at: fixedTime ? new Date(startAt).toISOString() : null,
          end_at: fixedTime ? new Date(endAt).toISOString() : null,
          min_size: minSize,
          target_size: targetSize,
          required_roles: [],
          cross_college: crossCollege,
        },
        crypto.randomUUID(),
      );
      nav(`/gathering/${created.id}`, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen id="screen-E2-self-initiate">
      <NavBar backTo="/me" />
      <Scroll>
        <PageHeader eyebrow="自行发起" title="直接发起局" clip="confirm.gather" />
        <Section title="局信息" />
        <Card>
          <input
            className="om-input"
            placeholder="局标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <textarea
            className="om-input mt-2"
            placeholder="要一起完成什么"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
          />
          <input
            className="om-input mt-2"
            placeholder="类型（如：自习）"
            value={gatheringType}
            onChange={(e) => setGatheringType(e.target.value)}
          />
          <input
            className="om-input mt-2"
            placeholder="校区"
            value={campus}
            onChange={(e) => setCampus(e.target.value)}
          />
          <input
            className="om-input mt-2"
            placeholder="地点（可稍后确定）"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </Card>

        <Section title="人数与范围" />
        <Card>
          <div className="between">
            <span className="t-call">最低人数</span>
            <Stepper value={minSize} min={2} max={20} onChange={setMinSize} />
          </div>
          <div className="between mt-2">
            <span className="t-call">目标人数</span>
            <Stepper
              value={targetSize}
              min={minSize}
              max={20}
              onChange={setTargetSize}
            />
          </div>
          <div className="between mt-2">
            <span className="t-call">跨院系匹配</span>
            <Switch on={crossCollege} onChange={setCrossCollege} />
          </div>
        </Card>

        <Section title="固定时段" />
        <Card>
          <div className="between">
            <span className="t-call">现在确定时间</span>
            <Switch on={fixedTime} onChange={setFixedTime} />
          </div>
          {fixedTime ? (
            <>
              <div className="t-cap mt-2">开始</div>
              <input
                type="datetime-local"
                className="om-input mt-1"
                value={startAt}
                onChange={(e) => setStartAt(e.target.value)}
              />
              <div className="t-cap mt-2">结束</div>
              <input
                type="datetime-local"
                className="om-input mt-1"
                value={endAt}
                onChange={(e) => setEndAt(e.target.value)}
              />
            </>
          ) : null}
        </Card>

        {error ? (
          <Card>
            <div className="t-foot">{error}</div>
          </Card>
        ) : null}
        {!valid ? (
          <div className="t-cap center">
            先补全标题与目标，并确认人数与时间
          </div>
        ) : null}
        <Btn kind="primary" disabled={busy || !valid} onClick={() => void create()}>
          {busy ? "创建中…" : "创建并进入匿名池"}
        </Btn>
      </Scroll>
    </Screen>
  );
}

/* ---------- E13 历史局安全与举报（GET /gatherings/history/safety） ---------- */

export function SafetyHistoryScreen() {
  const { repos } = useApp();
  const [rows, setRows] = useState<DepartedSafetyContext[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reporting, setReporting] = useState<DepartedSafetyContext | null>(null);
  const [targetId, setTargetId] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [block, setBlock] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      setRows(await repos.gatherings.safetyHistory());
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

  const participants = reporting?.reportable_participants ?? [];
  const canSubmit =
    reason.trim().length >= 5 && (participants.length === 0 || targetId !== null);

  async function submit() {
    if (!reporting || !canSubmit || busy) return;
    setBusy(true);
    try {
      await repos.gatherings.report(
        reporting.gathering_id,
        {
          reported_user_id: targetId ?? undefined,
          reason: reason.trim(),
          block: targetId ? block : false,
        },
        crypto.randomUUID(),
      );
      setMessage(targetId && block ? "举报与拉黑已提交" : "安全举报已提交");
      setReporting(null);
      setReason("");
      setTargetId(null);
      setBlock(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen id="screen-E13-departed-safety-history">
      <NavBar backTo="/me" />
      <Scroll>
        <PageHeader eyebrow="安全与举报" title="历史局安全与举报" clip="core.care" />
        {message ? (
          <Card>
            <div className="t-foot">{message}</div>
          </Card>
        ) : null}
        {loading ? (
          <Card>
            <StateView kind="loading" message="噜噜正在取数，稍等一下。" />
          </Card>
        ) : error ? (
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
          rows.map((row) => (
            <Card key={row.gathering_id}>
              <div className="flex wrap" style={{ gap: 6 }}>
                {row.gathering_type ? (
                  <span className="om-chip soft">{row.gathering_type}</span>
                ) : null}
                {row.status ? (
                  <span className="om-chip">{gatheringStatusName(row.status)}</span>
                ) : null}
              </div>
              <div className="t-t3 mt-2">{row.title ?? "已退出的局"}</div>
              {row.left_at ? (
                <div className="t-foot mt-1">
                  已于 {new Date(row.left_at).toLocaleString("zh-CN")} 退出
                </div>
              ) : null}
              {(row.reportable_participants ?? []).length > 0 ? (
                <div className="t-cap mt-1">
                  {(row.reportable_participants ?? [])
                    .map((p) => p.display_name || "已披露成员")
                    .join("、")}
                </div>
              ) : null}
              <Btn
                kind="ghost"
                sm
                onClick={() => {
                  setReporting(row);
                  setTargetId(null);
                  setReason("");
                  setBlock(false);
                }}
              >
                举报本局 / 拉黑曾同局成员…
              </Btn>
            </Card>
          ))
        )}
      </Scroll>

      {reporting ? (
        <div className="om-sheet" data-od-id="departed-safety-report">
          <div className="sheet-grab" />
          <div className="t-t3">历史局安全上报</div>
          <div className="t-cap mt-2">举报对象</div>
          <div className="flex wrap mt-1">
            <Chip
              kind={targetId === null ? "gap" : "soft"}
              onClick={() => setTargetId(null)}
            >
              匿名安全上报
            </Chip>
            {participants.map((p, i) => {
              const uid = String(p.user_id ?? i);
              return (
                <Chip
                  key={uid}
                  kind={targetId === uid ? "gap" : "soft"}
                  onClick={() => setTargetId(uid)}
                >
                  {p.display_name || "已披露成员"}
                </Chip>
              );
            })}
          </div>
          <div className="t-cap mt-2">举报原因</div>
          <textarea
            className="om-input mt-1"
            placeholder="描述需要平台核查的事实"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          {targetId ? (
            <div className="between mt-2">
              <span className="t-call">同时拉黑该成员</span>
              <Switch on={block} onChange={setBlock} />
            </div>
          ) : null}
          <Btn kind="primary" disabled={!canSubmit || busy} onClick={() => void submit()}>
            {busy ? "提交中…" : "提交"}
          </Btn>
          <Btn kind="text" onClick={() => setReporting(null)}>
            取消
          </Btn>
        </div>
      ) : null}
    </Screen>
  );
}

export function TrustRequirementScreen() {
  const { gatheringId } = useParams();
  const location = useLocation();
  const nav = useNavigate();
  const { repos } = useApp();
  const passed = isTrustRequirementContext(location.state)
    ? location.state
    : null;
  const context: TrustRequirementContext = passed ?? {
    requiredLevel: "—",
    serverMessage: "该局要求更高的信任等级。完成更多成局可解锁。",
    recoveryKind: "gathering",
    recoveryId: gatheringId ?? "",
  };
  const [trust, setTrust] = useState<Awaited<
    ReturnType<typeof repos.profile.trust>
  > | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
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

  const currentLevel = trust?.level ?? "—";
  const satisfied =
    trust != null &&
    trustLevelRank(currentLevel) >= trustLevelRank(context.requiredLevel);
  const resumeTo =
    context.recoveryKind === "share"
      ? `/g/${context.recoveryId}`
      : `/gathering/${context.recoveryId}`;
  const rows =
    trust?.conditions && trust.conditions.length > 0
      ? trust.conditions.map((c) => ({
          label: c.label,
          met: c.met,
          detail: c.detail,
        }))
      : (trust?.gaps ?? []).map((gap) => ({
          label: gap,
          met: false,
          detail: undefined as string | undefined,
        }));
  const progress = trust?.overall_progress ?? trust?.progress ?? 0;

  return (
    <Screen id="screen-C3-trust-requirement">
      <NavBar backTo="/gatherings/open" />
      <Scroll>
        <PageHeader eyebrow="信任门槛" title="先积累一次可靠履约" clip="core.care" />
        <Card>
          <div className="t-t3">这次操作由服务端暂缓</div>
          <div className="t-foot mt-1">{context.serverMessage}</div>
          <div className="between mt-3">
            <div data-od-id="trust-current-level">
              <div className="t-cap">当前</div>
              <div className="t-t1 mono">{currentLevel}</div>
            </div>
            <Icon name="arrow" size={18} />
            <div data-od-id="trust-required-level">
              <div className="t-cap">要求</div>
              <div
                className="t-t1 mono"
                style={{
                  background: "var(--yolk)",
                  borderRadius: 8,
                  padding: "2px 8px",
                }}
              >
                {context.requiredLevel}
              </div>
            </div>
          </div>
          <div className="t-call mt-3" style={{ fontWeight: 700 }} data-od-id="trust-capability">
            能力：{trustCapabilityTitle(context.capability)}
          </div>
        </Card>
        {loading && !trust ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : null}
        {trust && satisfied ? (
          <>
            <Card>
              <div className="flex">
                <Sticker name="medal.png" size="st-44" />
                <div style={{ marginLeft: 10 }}>
                  <div className="t-t3">服务端已确认门槛满足</div>
                  <div className="t-foot mt-1">
                    原任务仍保留，可从这里继续，不必重新寻找。
                  </div>
                </div>
              </div>
            </Card>
            <Btn
              kind="primary"
              id="trust-resume-original"
              onClick={() => nav(resumeTo)}
            >
              {trustRecoveryTitle(context.recoveryKind)}
            </Btn>
          </>
        ) : null}
        {trust && !satisfied ? (
          <>
            <Section title="先从低风险公开局开始" />
            <Card>
              <div className="between">
                <span className="t-t3">
                  {trust.next_level
                    ? `升到 ${trust.next_level} 还需`
                    : "只展示你自己的升级条件"}
                </span>
                {trust.next_level ? (
                  <span className="mono" style={{ fontWeight: 700 }}>
                    {Math.round(progress * 100)}%
                  </span>
                ) : null}
              </div>
              {trust.next_level ? <Progress value={progress * 100} /> : null}
              {rows.map((row, i) => (
                <div key={i} className="flex mt-2" data-od-id="trust-gap-item">
                  <span style={{ marginRight: 8 }}>{row.met ? "✓" : "○"}</span>
                  <div>
                    <div className="t-call">{row.label}</div>
                    {!row.met && row.detail && row.detail !== row.label ? (
                      <div className="t-foot">{row.detail}</div>
                    ) : null}
                  </div>
                </div>
              ))}
            </Card>
            <Btn kind="primary" to="/gatherings/open" id="trust-open-low-risk">
              去参加低风险公开局
            </Btn>
          </>
        ) : null}
        {error && !trust ? (
          <Card>
            <StateView
              kind="network"
              message={error}
              actionTitle="重试"
              onAction={() => void load()}
            />
          </Card>
        ) : null}
        {trust || error ? (
          <Btn kind="ghost" disabled={loading} onClick={() => void load()} id="trust-refresh">
            {loading ? "正在刷新…" : "刷新信任进度"}
          </Btn>
        ) : null}
        <Btn kind="text" to="/me/trust">
          查看完整 T0–T4 说明
        </Btn>
      </Scroll>
    </Screen>
  );
}

/* ---------- C4 缺口卡落地（GET /shares/g/{token} + POST join） ---------- */

export function ShareLandingScreen() {
  const { shareToken } = useParams();
  const { repos, session, sessionState } = useApp();
  const nav = useNavigate();
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    if (!shareToken) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await repos.gatherings.shareLanding(shareToken);
        if (!cancelled) setPayload(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [shareToken, repos]);

  const joinable = payload?.joinable !== false;

  async function join() {
    if (!shareToken || joining) return;
    setJoining(true);
    try {
      const gathering = await repos.gatherings.shareJoin(
        shareToken,
        `share-join-${shareToken}`,
      );
      nav(`/gathering/${gathering.id}`, { replace: true });
    } catch (e) {
      const trust = parseTrustRequirement(e, {
        kind: "share",
        id: shareToken,
      });
      if (trust) {
        const gid =
          (typeof payload?.gathering_id === "string" && payload.gathering_id) ||
          undefined;
        nav(gid ? `/gathering/${gid}/trust` : "/gatherings/open", {
          state: trust,
        });
      } else {
        setError(e instanceof Error ? e.message : "加入失败");
      }
    } finally {
      setJoining(false);
    }
  }

  return (
    <Screen id="screen-C4-share-landing">
      <Scroll>
        <div className="center mt-6">
          <LuluMark placement="hero" caption="匿名缺口卡" />
        </div>
        <div className="t-t2 center mt-3">这个局，还差一个</div>
        {error ? (
          <Card>
            <StateView kind="network" message={error} />
          </Card>
        ) : !payload ? (
          <Card>
            <StateView kind="loading" />
          </Card>
        ) : (
          <Card className="mt-4">
            <div className="flex wrap" style={{ gap: 6 }}>
              {typeof payload.gathering_type === "string" ? (
                <span className="om-chip soft">{payload.gathering_type}</span>
              ) : null}
              {typeof payload.campus === "string" && payload.campus ? (
                <span className="om-chip">{payload.campus}</span>
              ) : null}
              {typeof payload.missing_count === "number" &&
              payload.missing_count > 0 ? (
                <GapBadge n={payload.missing_count} />
              ) : null}
            </div>
            <div className="t-t3 mt-2">
              {(payload.title as string) ?? "有人差你一个"}
            </div>
            <div className="t-foot mt-1">
              {(payload.goal as string) ?? "匿名缺口 · 认证后可加入"}
            </div>
            {Array.isArray(payload.looking_for) && payload.looking_for.length > 0 ? (
              <div className="flex wrap mt-2" style={{ gap: 6 }}>
                {(payload.looking_for as string[]).map((role) => (
                  <Chip key={role} kind="gap">
                    {role}
                  </Chip>
                ))}
              </div>
            ) : null}
            <div className="mt-4">
              {sessionState.status === "authenticated" ? (
                <>
                  <Btn
                    kind="primary"
                    disabled={!joinable || joining}
                    onClick={() => void join()}
                  >
                    {joining ? "加入中…" : joinable ? "我来" : "当前不可加入"}
                  </Btn>
                  {!joinable ? (
                    <div className="t-cap center mt-1">
                      服务端显示该局已结束招募
                    </div>
                  ) : null}
                </>
              ) : (
                <Btn
                  kind="primary"
                  onClick={() => {
                    session.setPendingRoute(`/g/${shareToken}`);
                    nav("/auth/scan");
                  }}
                >
                  认证后我来
                </Btn>
              )}
            </div>
          </Card>
        )}
        <Note sticker="round-table.png">分享文案不含分享者身份。</Note>
      </Scroll>
    </Screen>
  );
}
