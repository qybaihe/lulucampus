import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import {
  asList,
  capabilityLabel,
  gatheringStatusName,
  type Competition,
  type CompetitionTeam,
  type Gathering,
  type RecommendationTier,
} from "../../core/api/repositories";
import {
  campusEventDisplayType,
  campusEventLocation,
  campusEventTime,
} from "../../core/campus/events";
import {
  hotSeatChip,
  isHotSeat,
  isHotTeam,
  rankCompetitionsForYou,
  spotlightFitLabel,
} from "../../core/competitions/spotlight";
import {
  competitionSticker,
  competitionTitleClass,
  deadlineBadge,
} from "../../core/competitions/card";
import {
  gapDescription,
  recruitingHeadline,
  teamFilled,
} from "../../core/competitions/teams";
import {
  Btn,
  Card,
  Chip,
  Divider,
  Icon,
  NavBar,
  PageHeader,
  Screen,
  Scroll,
  LuluSeatStrip,
  Seg,
  StateView,
  Sticker,
} from "../../components/ui/primitives";

const FALLBACK_TIER_LABELS: Record<string, string> = {
  A: "优先推荐",
  B: "可报名",
  C: "补充参考",
};

function formatDeadline(iso: string, style: "short" | "long" = "short"): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  if (style === "long") {
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${time}`;
  }
  return `${date.getMonth() + 1}月${date.getDate()}日 ${time}`;
}

/** 活动 Tab 根：比赛 / 组局 / 校园活动，对齐 iOS ActivityDiscoveryView。 */
export function CompetitionsScreen() {
  const [segment, setSegment] = useState<"比赛" | "组局" | "校园活动">("比赛");

  return (
    <Screen id="screen-activity-discovery">
      <Scroll>
        <PageHeader eyebrow="发现" title="活动" clip="core.celebrate" />
        <Seg
          options={[
            { value: "比赛", label: "比赛" },
            { value: "组局", label: "组局" },
            { value: "校园活动", label: "校园活动" },
          ]}
          value={segment}
          onChange={setSegment}
        />
        <div className="mt-3" id="screen-B12-competitions">
          {segment === "比赛" ? <CompetitionsListContent /> : null}
          {segment === "组局" ? <PublicGatheringsContent /> : null}
          {segment === "校园活动" ? <CampusEventsContent /> : null}
        </div>
      </Scroll>
    </Screen>
  );
}

function CompetitionsListContent() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [tier, setTier] = useState<string | null>(null);
  const [tierCatalog, setTierCatalog] = useState<RecommendationTier[]>([]);
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [items, setItems] = useState<Competition[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setPhase("loading");
    try {
      const raw = await repos.competitions.list(tier);
      setItems(asList(raw));
      setPhase("loaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
      setPhase("failed");
    }
    try {
      const catalog = asList(await repos.competitions.recommendationTiers());
      catalog.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
      setTierCatalog(catalog);
    } catch {
      /* 目录取不到时按稳定码兜底 */
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos, tier]);

  function tierLabel(code: string | null): string {
    if (!code) return "全部";
    return (
      tierCatalog.find((t) => t.code === code)?.label ??
      FALLBACK_TIER_LABELS[code] ??
      code
    );
  }

  const tierCodes: Array<string | null> = [
    null,
    ...(tierCatalog.length ? tierCatalog.map((t) => t.code) : ["A", "B", "C"]),
  ];

  return (
    <>
      <div className="om-seg mb-3">
        {tierCodes.map((code) => (
          <button
            key={code ?? "all"}
            type="button"
            className={tier === code ? "on" : ""}
            onClick={() => setTier(code)}
          >
            {tierLabel(code)}
          </button>
        ))}
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
            onAction={() => void load()}
          />
        </Card>
      ) : null}
      {phase === "loaded" ? (
        <>
          <div className="t-foot mb-3" data-od-id="competition-count">
            {items.length} 场可行动赛事
          </div>
          {items.length === 0 ? (
            <Card>
              <StateView kind="empty" message="暂时没有内容，有进展时会告诉你。" />
            </Card>
          ) : (
            rankCompetitionsForYou(items).map((c) => {
              const hot = isHotSeat(c);
              const jackpot = hotSeatChip(c);
              const fitLabel = spotlightFitLabel(c);
              const due = c.registration_deadline
                ? deadlineBadge(c.registration_deadline)
                : null;
              return (
                <Card
                  key={c.id}
                  className={hot ? "hot-seat" : ""}
                  onClick={() => nav(`/competition/${c.id}`)}
                >
                  <div className="flex" style={{ alignItems: "flex-start" }}>
                    <Sticker name={competitionSticker(c)} size="st-44" />
                    <div style={{ minWidth: 0 }}>
                      <div
                        className={competitionTitleClass(c.name)}
                        style={{ fontWeight: 700 }}
                      >
                        {c.name}
                      </div>
                      <div className="t-foot mt-1">
                        {(c.tracks ?? []).slice(0, 3).join(" · ") ||
                          c.summary ||
                          "已核验赛事"}
                      </div>
                    </div>
                  </div>
                  <div className="flex wrap mt-3" style={{ gap: 6 }}>
                    {fitLabel ? (
                      <span className="om-chip gap">{fitLabel}</span>
                    ) : null}
                    {jackpot ? <span className="om-chip gap">{jackpot}</span> : null}
                    <span
                      className={`om-chip ${c.recommendation_tier === "A" ? "gap" : ""}`}
                    >
                      {c.recommendation_label ??
                        FALLBACK_TIER_LABELS[c.recommendation_tier ?? ""] ??
                        "已核验"}
                    </span>
                    <Chip kind="soft">
                      {c.team_forming_supported === false ? "备赛搭子" : "官方组队"}
                    </Chip>
                  </div>
                  {due ? (
                    due.kind === "gap" ? (
                      <div className="mt-2">
                        <Chip kind="gap">{due.label}</Chip>
                      </div>
                    ) : (
                      <div className="t-foot mt-2 flex" style={{ alignItems: "center", gap: 4 }}>
                        <Icon name="clock" size={12} />
                        {due.label}
                      </div>
                    )
                  ) : null}
                </Card>
              );
            })
          )}
        </>
      ) : null}
    </>
  );
}

function seatCaption(item: Gathering): string {
  const target = item.target_size ?? 0;
  const filled = Math.min(
    item.member_count ?? item.confirmed_count ?? item.filled_count ?? 0,
    target || Infinity,
  );
  const status = String(item.status ?? "");
  const state = /Pooling/i.test(status)
    ? "焦灼等待中"
    : /Tentative/i.test(status)
      ? "待确认"
      : /Confirmed/i.test(status)
        ? "已就位"
        : gatheringStatusName(item.status);
  if (!target) return state;
  return `${filled}/${target} · ${state}`;
}

function formatGatheringWhen(iso?: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function PublicGatheringsContent() {
  const { repos } = useApp();
  const nav = useNavigate();
  const [phase, setPhase] = useState<"loading" | "loaded" | "failed">("loading");
  const [items, setItems] = useState<Gathering[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setPhase("loading");
    try {
      setItems(asList(await repos.gatherings.open()));
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

  if (phase === "loading") {
    return (
      <Card>
        <StateView kind="loading" />
      </Card>
    );
  }
  if (phase === "failed") {
    return (
      <Card>
        <StateView
          kind="network"
          message={error ?? undefined}
          actionTitle="重试"
          onAction={() => void load()}
        />
      </Card>
    );
  }
  if (items.length === 0) {
    return (
      <Card>
        <StateView kind="empty" message="暂时没有招募中的局，有进展时会告诉你。" />
      </Card>
    );
  }

  return (
    <>
      {items.map((item) => {
        const target = item.target_size ?? 0;
        const filled = Math.min(
          item.member_count ?? item.confirmed_count ?? item.filled_count ?? 0,
          target || filledFallback(item),
        );
        const when = formatGatheringWhen(item.start_at ?? item.starts_at);
        const place = item.location ?? item.location_label ?? item.campus;
        return (
          <Card
            key={item.id}
            onClick={() => nav(`/gathering/${item.id}`)}
            id={`public-gathering-${item.id}`}
          >
            <div className="between">
              {item.gathering_type ? (
                <Chip kind="soft">{item.gathering_type}</Chip>
              ) : (
                <span />
              )}
              <Chip kind="solid">{gatheringStatusName(item.status)}</Chip>
            </div>
            <div className="t-t3 mt-2">{item.title ?? "未命名局"}</div>
            {item.goal ? (
              <div className="t-foot mt-1" style={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                {item.goal}
              </div>
            ) : null}
            {/Pooling/i.test(String(item.status ?? "")) &&
            (item.looking_for ?? []).length > 0 ? (
              <div className="flex wrap mt-2" style={{ gap: 6 }}>
                {item.looking_for!.slice(0, 3).map((role) => (
                  <Chip key={role} kind="gap">
                    {role}
                  </Chip>
                ))}
              </div>
            ) : null}
            <div className="t-foot mt-2">
              {[place, when].filter(Boolean).join(" · ")}
            </div>
            {target > 0 ? (
              <div className="flex mt-2" style={{ alignItems: "center", gap: 10 }}>
                <LuluSeatStrip filled={filled} total={Math.min(target, 8)} />
                <span className="t-foot" style={{ fontWeight: 600 }}>
                  {seatCaption(item)}
                </span>
              </div>
            ) : null}
          </Card>
        );
      })}
    </>
  );
}

function filledFallback(item: Gathering): number {
  return item.member_count ?? item.confirmed_count ?? item.filled_count ?? 0;
}

function CampusEventsContent() {
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

  if (phase === "loading") {
    return (
      <Card>
        <StateView kind="loading" />
      </Card>
    );
  }
  if (phase === "failed") {
    return (
      <Card>
        <StateView
          kind="network"
          message={error ?? undefined}
          actionTitle="重试"
          onAction={() => void load()}
        />
      </Card>
    );
  }
  if (items.length === 0) {
    return (
      <>
        <Card>
          <StateView kind="empty" message="暂时没有内容，有进展时会告诉你。" />
        </Card>
        <div className="mt-2">
          <Btn kind="ghost" sm to="/intent">
            找活动同行
          </Btn>
        </div>
      </>
    );
  }

  const types = items.reduce<string[]>((acc, item) => {
    const t = campusEventDisplayType(String(item.type ?? item.display_type ?? ""));
    if (!acc.includes(t)) acc.push(t);
    return acc;
  }, []);
  const visible = typeFilter
    ? items.filter(
        (item) =>
          campusEventDisplayType(String(item.type ?? item.display_type ?? "")) ===
          typeFilter,
      )
    : items;

  return (
    <>
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
      {visible.length === 0 ? (
        <Card>
          <StateView kind="empty" message="这个分类暂时没有活动。" />
        </Card>
      ) : (
        visible.map((item, i) => {
          const id = String(item.id ?? i);
          const publisher =
            item.publisher ??
            (item.details as { publisher?: string } | undefined)?.publisher;
          return (
            <Card key={id} onClick={() => nav(`/today/event/${id}`)}>
              <div className="flex wrap" style={{ gap: 6 }}>
                <Chip kind="soft">
                  {campusEventDisplayType(String(item.type ?? ""))}
                </Chip>
                {publisher === "user" ? <Chip kind="solid">同学发布</Chip> : null}
              </div>
              <div className="t-t3 mt-2">
                {String(item.title ?? item.name ?? "活动")}
              </div>
              <div className="t-call mt-1">{campusEventTime(item)}</div>
              <div className="t-foot mt-1">{campusEventLocation(item)}</div>
            </Card>
          );
        })
      )}
      <div className="mt-2">
        <Btn kind="ghost" sm to="/intent">
          找活动同行
        </Btn>
      </div>
    </>
  );
}

/** 队伍席位条（对齐 iOS OMLuluSeatStrip：噜噜脸已就位 / 虚位待补）。 */
function TeamSeatStrip({ filled, total }: { filled: number; total: number }) {
  return <LuluSeatStrip filled={filled} total={total} />;
}

/** B12.1 · 赛事详情，对齐 iOS CompetitionDetailView。 */
export function CompetitionDetailScreen() {
  const { competitionId } = useParams();
  const { repos } = useApp();
  const nav = useNavigate();
  const [item, setItem] = useState<Competition | null>(null);
  const [teams, setTeams] = useState<CompetitionTeam[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shareTip, setShareTip] = useState<string | null>(null);

  async function load() {
    if (!competitionId) return;
    try {
      const c = await repos.competitions.get(competitionId);
      setItem(c);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
    try {
      setTeams(asList(await repos.competitions.teams(competitionId)));
    } catch {
      setTeams(null); // 队伍是补充信息，取不到时静默隐藏（对齐 iOS 软失败）
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [competitionId, repos]);

  const registrationUrl = item?.registration_url ?? item?.official_url ?? null;

  async function share() {
    if (!item || !registrationUrl) return;
    try {
      if (navigator.share) {
        await navigator.share({ title: item.name, text: item.name, url: registrationUrl });
      } else {
        await navigator.clipboard.writeText(registrationUrl);
        setShareTip("链接已复制");
        setTimeout(() => setShareTip(null), 2000);
      }
    } catch {
      /* 用户取消分享 */
    }
  }

  const sizeMin = item?.team_constraints?.team_size_min;
  const sizeMax = item?.team_constraints?.team_size_max;
  const sizeLabel =
    sizeMin != null && sizeMax != null ? `${sizeMin}–${sizeMax} 人` : null;
  const hot = item ? isHotSeat(item) : false;
  const jackpot = item ? hotSeatChip(item) : null;
  const fitLabel = item ? spotlightFitLabel(item) : null;

  return (
    <Screen id="screen-B12.1-competition-detail">
      <NavBar backTo="/competitions" />
      <Scroll>
        {error ? (
          <Card>
            <StateView kind="network" message={error} actionTitle="重试" onAction={() => void load()} />
          </Card>
        ) : !item ? (
          <Card>
            <StateView kind="loading" message="噜噜正在取数，稍等一下。" />
          </Card>
        ) : (
          <>
            <div className="center mt-2">
              <Sticker name={competitionSticker(item)} size="st-72" />
            </div>
            <div className="t-t1 center mt-2">{item.name}</div>
            <div className="t-foot center mb-3">
              {fitLabel ? `${fitLabel} · ` : ""}
              {jackpot ? `${jackpot} · ` : ""}
              {item.recommendation_label ?? "已核验"} · 已核验
              {sizeLabel ? ` · 队伍 ${sizeLabel}` : ""}
            </div>

            {item.taste_fit_reasons?.length || item.recruit_hints?.length ? (
              <Card className={`mb-3${hot ? " hot-seat" : ""}`}>
                <div className="t-t3">按你的兴趣画像</div>
                {(item.taste_fit_reasons ?? []).map((reason) => (
                  <div className="t-foot mt-2" key={reason}>
                    {reason}
                  </div>
                ))}
                {(item.recruit_hints ?? []).length > 0 ? (
                  <div className="t-call mt-3">招什么样的人</div>
                ) : null}
                {(item.recruit_hints ?? []).map((hint) => (
                  <div className="t-foot mt-1" key={hint}>
                    {hint}
                  </div>
                ))}
                {jackpot ? (
                  <div className="mt-3">
                    <Chip kind="gap">{jackpot}</Chip>
                  </div>
                ) : null}
              </Card>
            ) : null}

            <Card>
              <div className="flex" style={{ gap: 10 }}>
                <Sticker
                  name={item.team_forming_supported === false ? "chair-empty.png" : "round-table.png"}
                  size="st-44"
                />
                <div>
                  <div className="t-t3">
                    {item.team_forming_supported === false ? "仅找备赛搭子" : "支持赛事组队"}
                  </div>
                  {sizeLabel ? <div className="t-foot">队伍范围 {sizeLabel}</div> : null}
                </div>
              </div>
              {item.registration_deadline ? (
                <>
                  <Divider />
                  <div className="flex" style={{ alignItems: "center", gap: 8 }}>
                    <Icon name="clock" size={14} />
                    <span className="t-call">
                      报名截止 {formatDeadline(item.registration_deadline, "long")}
                    </span>
                  </div>
                </>
              ) : null}
              <Divider />
              <div className="t-foot">{item.registration_instructions ?? "以官方页面为准"}</div>
            </Card>

            {item.rewards ? (
              <Card className="mt-3">
                <div className="t-t3">奖励与规则</div>
                <div className="t-foot mt-2">{item.rewards}</div>
              </Card>
            ) : null}

            <button
              type="button"
              className="om-row"
              style={{ display: "block", width: "100%", padding: 0, marginTop: 12 }}
              onClick={() => nav(`/competition/${item.id}/table`)}
              data-od-id="competition-recruiting-teams"
            >
              <Card>
                <div className="flex" style={{ gap: 10, alignItems: "center" }}>
                  <Sticker name="round-table.png" size="st-44" />
                  <div style={{ flex: 1, textAlign: "left" }}>
                    <div className="t-t3">{recruitingHeadline(teams?.length ?? null)}</div>
                    <div className="t-foot">点进去看每队几/几，以及还缺什么</div>
                  </div>
                  <Icon name="arrow" size={12} />
                </div>
              </Card>
            </button>

            <div className="stack mt-3" style={{ gap: 10 }}>
              <Btn kind="primary" to={`/competition/${item.id}/table`}>
                {item.team_forming_supported === false ? "找备赛搭子" : "找队友"}
              </Btn>
              {registrationUrl ? (
                <Btn
                  kind="ghost"
                  onClick={() => window.open(registrationUrl, "_blank", "noopener")}
                >
                  打开官方报名页面
                </Btn>
              ) : null}
              {registrationUrl ? (
                <Btn kind="text" sm onClick={() => void share()}>
                  {shareTip ?? "系统分享赛事"}
                </Btn>
              ) : null}
            </div>
          </>
        )}
      </Scroll>
    </Screen>
  );
}

export function CompetitionTableScreen() {
  const { competitionId } = useParams();
  const { repos } = useApp();
  const nav = useNavigate();
  const [item, setItem] = useState<Competition | null>(null);
  const [teams, setTeams] = useState<CompetitionTeam[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!competitionId) return;
    try {
      const [c, listed] = await Promise.all([
        repos.competitions.get(competitionId),
        repos.competitions.teams(competitionId),
      ]);
      setItem(c);
      setTeams(asList(listed));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [competitionId, repos]);

  const count = teams?.length ?? null;

  return (
    <Screen id="screen-B12.2-table">
      <NavBar backTo={`/competition/${competitionId}`} />
      <Scroll>
        <PageHeader
          eyebrow="赛事牌桌"
          title={recruitingHeadline(count)}
          clip="confirm.gather"
        />
        {error ? (
          <Card>
            <StateView kind="network" message={error} actionTitle="重试" onAction={() => void load()} />
          </Card>
        ) : teams == null ? (
          <Card>
            <StateView kind="loading" message="噜噜正在取数，稍等一下。" />
          </Card>
        ) : teams.length === 0 ? (
          <Card>
            <StateView kind="empty" message="暂时还没有队伍在招人。你可以自己组一队，发布后会出现在这里。" />
          </Card>
        ) : (
          teams.map((team) => {
            const filled = teamFilled(team);
            const gap = gapDescription(team);
            const teamHot = item ? isHotTeam(item, team) : false;
            return (
              <button
                key={team.id}
                type="button"
                className={`om-row${teamHot ? " hot-seat-inline" : ""}`}
                style={{ display: "block", width: "100%", padding: 0, marginBottom: 12 }}
                onClick={() => nav(`/competition/${competitionId}/team/${team.id}`)}
                data-od-id={`competition-team-${team.id}`}
              >
                <Card className={teamHot ? "hot-seat" : undefined}>
                  <div className="between" style={{ display: "flex" }}>
                    <span className="flex" style={{ alignItems: "center", gap: 10 }}>
                      <TeamSeatStrip filled={filled} total={team.target_size ?? 0} />
                      <span className="t-foot" style={{ fontWeight: 600 }}>
                        {filled}/{team.target_size ?? 0}
                        {team.min_size && team.min_size !== team.target_size
                          ? ` · ${team.min_size}–${team.target_size} 人`
                          : ""}
                      </span>
                    </span>
                    <Icon name="arrow" size={12} />
                  </div>
                  <div className="t-t3 mt-2">{team.title}</div>
                  <div className="flex wrap mt-2" style={{ gap: 6 }}>
                    {teamHot && !gap ? <Chip kind="gap">正好差一个</Chip> : null}
                    {gap ? <Chip kind="gap">{gap}</Chip> : null}
                    {team.start_at ? <Chip kind="soft">{formatDeadline(team.start_at)}</Chip> : null}
                  </div>
                </Card>
              </button>
            );
          })
        )}
        <div className="stack mt-3" style={{ gap: 10 }}>
          <Btn kind="primary" to={`/intent?competition=${competitionId}`}>
            自己组一队
          </Btn>
        </div>
      </Scroll>
    </Screen>
  );
}

export function CompetitionTeamDetailScreen() {
  const { competitionId, teamId } = useParams();
  const { repos } = useApp();
  const [item, setItem] = useState<Competition | null>(null);
  const [team, setTeam] = useState<CompetitionTeam | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!competitionId || !teamId) return;
    try {
      const [c, detail] = await Promise.all([
        repos.competitions.get(competitionId),
        repos.competitions.team(competitionId, teamId),
      ]);
      setItem(c);
      setTeam(detail);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [competitionId, teamId, repos]);

  const filled = team ? teamFilled(team) : 0;
  const gap = team ? gapDescription(team) : null;
  const missing = team?.missing_roles ?? team?.required_roles ?? [];
  const filledRoles = team?.filled_roles ?? [];
  const hot = item && team ? isHotTeam(item, team) : false;

  return (
    <Screen id="screen-B12.2-team-detail">
      <NavBar backTo={`/competition/${competitionId}/table`} />
      <Scroll>
        {error ? (
          <Card>
            <StateView kind="network" message={error} actionTitle="重试" onAction={() => void load()} />
          </Card>
        ) : !team ? (
          <Card>
            <StateView kind="loading" message="噜噜正在取数，稍等一下。" />
          </Card>
        ) : (
          <>
            <div className="center mt-2">
              <Sticker name="round-table.png" size="st-72" />
            </div>
            <div className="t-t1 center mt-2">{team.title}</div>
            <div className="t-foot center mb-3">
              {filled}/{team.target_size ?? 0}
              {team.min_size && team.min_size !== team.target_size
                ? ` · ${team.min_size}–${team.target_size} 人`
                : ""}{" "}
              · 正在招人
            </div>
            <Card className={hot ? "hot-seat" : undefined}>
              <div className="flex" style={{ alignItems: "center", gap: 10 }}>
                <TeamSeatStrip filled={filled} total={team.target_size ?? 0} />
                <span className="t-t1">
                  {filled}/{team.target_size ?? 0}
                </span>
              </div>
              {gap ? (
                <div className="mt-3">
                  <Chip kind="gap">{gap}</Chip>
                </div>
              ) : null}
            </Card>
            {filledRoles.length > 0 ? (
              <Card className="mt-3">
                <div className="t-t3">已经有人覆盖</div>
                <div className="flex wrap mt-2" style={{ gap: 6 }}>
                  {filledRoles.map((role) => (
                    <Chip key={role} kind="soft">
                      {role}
                    </Chip>
                  ))}
                </div>
              </Card>
            ) : null}
            {missing.length > 0 ? (
              <Card className="mt-3">
                <div className="t-t3">还缺这些</div>
                <div className="flex wrap mt-2" style={{ gap: 6 }}>
                  {missing.map((role) => (
                    <Chip key={role} kind="gap">
                      {capabilityLabel(role)}
                    </Chip>
                  ))}
                </div>
                <div className="t-foot mt-2">席位只显示角色缺口，不显示已就位者是谁。</div>
              </Card>
            ) : null}
            {team.goal ? (
              <Card className="mt-3">
                <div className="t-t3">这支队伍在找什么</div>
                <div className="t-foot mt-2">{team.goal}</div>
              </Card>
            ) : null}
            {team.campus || team.location || team.start_at ? (
              <Card className="mt-3">
                {team.campus || team.location ? (
                  <div className="t-call">
                    {[team.campus, team.location].filter(Boolean).join(" · ")}
                  </div>
                ) : null}
                {team.start_at ? (
                  <>
                    {team.campus || team.location ? <Divider /> : null}
                    <div className="t-call">{formatDeadline(team.start_at)}</div>
                  </>
                ) : null}
              </Card>
            ) : null}
            <div className="stack mt-3" style={{ gap: 10 }}>
              <Btn kind="primary" to={`/gathering/${team.id}`}>
                想加入这支队伍
              </Btn>
              <Btn kind="ghost" to={`/competition/${competitionId}/table`}>
                看其他招人队伍
              </Btn>
            </div>
          </>
        )}
      </Scroll>
    </Screen>
  );
}
