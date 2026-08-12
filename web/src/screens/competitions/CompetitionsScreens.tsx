import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useApp } from "../../app/AppContext";
import {
  asList,
  capabilityLabel,
  type Competition,
  type CompetitionTeam,
  type RecommendationTier,
} from "../../core/api/repositories";
import {
  Btn,
  Card,
  Chip,
  Divider,
  Icon,
  LargeTitle,
  NavBar,
  Screen,
  Scroll,
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

/** 角色缺口文案（对齐 iOS CompetitionTeam.gapDescription）：「差一个算法」。 */
function gapDescription(team: CompetitionTeam): string | null {
  const roles = team.required_roles ?? [];
  if (!roles.length) return null;
  const labels = roles.map(capabilityLabel);
  return labels.length === 1
    ? `差一个${labels[0]}`
    : `还差 ${labels.length} 个角色：${labels.join("、")}`;
}

/** B12 · 比赛雷达（Tab 根），对齐 iOS CompetitionsView。 */
export function CompetitionsScreen() {
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
    <Screen id="screen-B12-competitions">
      <Scroll>
        <LargeTitle title="比赛" sub="已核验赛事 · 看出哪桌还差人" />
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
              items.map((c) => (
                <Card key={c.id} onClick={() => nav(`/competition/${c.id}`)}>
                  <div className="flex" style={{ alignItems: "flex-start" }}>
                    <Sticker name="trophy.png" size="st-44" />
                    <div style={{ minWidth: 0 }}>
                      <div className="t-t3">{c.name}</div>
                      <div className="t-foot mt-1">
                        {(c.tracks ?? []).slice(0, 3).join(" · ") || c.summary || "已核验赛事"}
                      </div>
                    </div>
                  </div>
                  <div className="between mt-3">
                    <span className="flex" style={{ gap: 6 }}>
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
                    </span>
                    {c.registration_deadline ? (
                      <span
                        className="t-foot flex"
                        style={{ alignItems: "center", gap: 4, flex: "none" }}
                      >
                        <Icon name="clock" size={12} />
                        {formatDeadline(c.registration_deadline)}
                      </span>
                    ) : null}
                  </div>
                </Card>
              ))
            )}
          </>
        ) : null}
      </Scroll>
    </Screen>
  );
}

/** 队伍席位条（对齐 iOS OMLuluSeatStrip：实心已就位 / 虚位待补）。 */
function TeamSeatStrip({ filled, total }: { filled: number; total: number }) {
  const seats = Array.from({ length: Math.max(total, 0) }, (_, i) => i < filled);
  return (
    <span style={{ display: "inline-flex", gap: 4 }}>
      {seats.map((on, i) => (
        <span
          key={i}
          style={{
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: on ? "var(--yolk)" : "transparent",
            border: on ? "1px solid var(--yolk-border)" : "1px dashed var(--mist)",
          }}
        />
      ))}
    </span>
  );
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

  return (
    <Screen id="screen-B12.1-competition-detail">
      <NavBar title="赛事详情" backTo="/competitions" />
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
              <Sticker name="trophy.png" size="st-72" />
            </div>
            <div className="t-t1 center mt-2">{item.name}</div>
            <div className="t-foot center mb-3">
              {item.recommendation_label ?? "已核验"} · 已核验
              {sizeLabel ? ` · 队伍 ${sizeLabel}` : ""}
            </div>

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

            {teams && teams.length > 0 ? (
              <Card className="mt-3">
                <div className="between">
                  <span className="t-t3">正在组队的队伍</span>
                  <span className="t-foot">{teams.length} 支</span>
                </div>
                {teams.map((team) => {
                  const filled = Math.min(team.member_count ?? 0, team.target_size ?? 0);
                  const gap = gapDescription(team);
                  return (
                    <div key={team.id}>
                      <Divider />
                      <button
                        type="button"
                        className="om-row"
                        style={{ display: "block", width: "100%", padding: "6px 0" }}
                        onClick={() => nav(`/gathering/${team.id}`)}
                        data-od-id={`competition-team-${team.id}`}
                      >
                        <span className="between" style={{ display: "flex" }}>
                          <span className="flex" style={{ alignItems: "center", gap: 10 }}>
                            <TeamSeatStrip filled={filled} total={team.target_size ?? 0} />
                            <span className="t-foot" style={{ fontWeight: 600 }}>
                              {filled}/{team.target_size ?? 0}
                            </span>
                          </span>
                          <Icon name="arrow" size={12} />
                        </span>
                        <span className="flex wrap mt-2" style={{ gap: 6 }}>
                          {gap ? <Chip kind="gap">{gap}</Chip> : null}
                          {team.start_at ? (
                            <Chip kind="soft">{formatDeadline(team.start_at)}</Chip>
                          ) : null}
                        </span>
                      </button>
                    </div>
                  );
                })}
              </Card>
            ) : null}

            <div className="stack mt-3" style={{ gap: 10 }}>
              <Btn kind="primary" to={`/intent?competition=${item.id}`}>
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
  return (
    <Screen id="screen-B12.2-table">
      <NavBar title="赛事牌桌" backTo={`/competition/${competitionId}`} />
      <Scroll>
        <LargeTitle title="差一个" sub="返回稿组合态 · 不是独立 endpoint" />
        <Card>
          <div className="t-foot">
            牌桌席位与缺口只来自真实局 / 意图发布结果；不在此页硬编码人数。
          </div>
          <div className="mt-4">
            <Btn kind="primary" to={`/intent?competition=${competitionId}`}>
              发起意图填缺口
            </Btn>
            <Btn kind="ghost" to="/gatherings/open">
              去看公开局
            </Btn>
          </div>
        </Card>
      </Scroll>
    </Screen>
  );
}
