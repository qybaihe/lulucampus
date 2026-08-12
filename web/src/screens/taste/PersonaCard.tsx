import type {
  TasteProfileResult,
  TasteSourceProfile,
} from "../../core/api/repositories";
import { LuluSprite } from "../../components/lulu/LuluSprite";
import { Sticker } from "../../components/ui/primitives";
import { DouyinAvatar, VerifiedBadge } from "./TasteImportScreen";

/**
 * 抖音画像卡 — 后端 READY 结果的定制展示卡。
 * 头部：Lulu + 抖音头像 + 已认证；正文一条一条排布画像字段。
 */
export function PersonaCard({
  result,
  profile,
}: {
  result: TasteProfileResult;
  profile: TasteSourceProfile | null;
}) {
  const domains = [...result.interest_domains]
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);
  const maxDomain = domains[0]?.score ?? 1;
  const sampleItems =
    typeof result.sample?.items === "number" ? result.sample.items : null;
  const generation = result.sample?.generation === "llm" ? "AI 精修" : "规则生成";

  return (
    <div className="persona-card" data-od-id="persona-card">
      {/* — 卡头：Lulu × 抖音头像 — */}
      <div className="pc-hero">
        <div className="pc-hero-top">
          <LuluSprite clip="core.celebrate" size={92} />
          <div className="pc-identity">
            <div className="pc-avatar-ring">
              <DouyinAvatar profile={profile} size={72} />
            </div>
            <div className="pc-name">
              {profile?.nickname ?? "抖音用户"}
              <VerifiedBadge />
            </div>
            {profile?.uid ? <div className="pc-uid mono">抖音号 {profile.uid}</div> : null}
          </div>
        </div>
        <div className="pc-primary">
          <div className="pc-primary-label">我的主标签</div>
          <div className="pc-primary-tag">
            <span className="pc-primary-name">{result.primary_tag.label}</span>
            <span className="pc-primary-score mono">{Math.round(result.primary_tag.score * 100)}</span>
          </div>
        </div>
      </div>

      {/* — 正文：一条一条 — */}
      <div className="pc-body">
        {result.secondary_tags.length > 0 ? (
          <section className="pc-row">
            <header className="pc-row-head">
              <Sticker name="design-palette.png" size={20} />
              <span>副标签</span>
              <em className="mono">{result.secondary_tags.length}</em>
            </header>
            <div className="pc-chips">
              {result.secondary_tags.map((t) => (
                <span key={t.key} className="om-chip soft">{t.label}</span>
              ))}
            </div>
          </section>
        ) : null}

        {domains.length > 0 ? (
          <section className="pc-row">
            <header className="pc-row-head">
              <Sticker name="data-chart.png" size={20} />
              <span>兴趣领域</span>
            </header>
            <div className="pc-domains">
              {domains.map((d) => (
                <div key={d.key} className="pc-domain">
                  <span className="pc-domain-label">{d.label}</span>
                  <span className="pc-domain-bar">
                    <i style={{ width: `${Math.max(8, Math.round((d.score / maxDomain) * 100))}%` }} />
                  </span>
                  <span className="pc-domain-score mono">{Math.round(d.score * 100)}</span>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {result.interest_facets.length > 0 ? (
          <section className="pc-row">
            <header className="pc-row-head">
              <Sticker name="algorithm-gear.png" size={20} />
              <span>兴趣切面</span>
              <em className="mono">{result.interest_facets.length}</em>
            </header>
            <div className="pc-chips">
              {result.interest_facets.slice(0, 12).map((f) => (
                <span key={`${f.domain}-${f.facet}`} className="om-chip">{f.label}</span>
              ))}
            </div>
          </section>
        ) : null}

        {result.summary ? (
          <section className="pc-row">
            <header className="pc-row-head">
              <Sticker name="notebook-open.png" size={20} />
              <span>画像摘要</span>
            </header>
            <p className="pc-text">{result.summary}</p>
          </section>
        ) : null}

        {result.persona ? (
          <section className="pc-row">
            <header className="pc-row-head">
              <Sticker name="chat-bubble.png" size={20} />
              <span>噜噜评语</span>
            </header>
            <div className="pc-persona">
              <div className="pc-persona-lulu">
                <LuluSprite clip="home.reply" size={44} />
              </div>
              <p className="pc-text">{result.persona}</p>
            </div>
          </section>
        ) : null}

        {result.matching_hints.length > 0 ? (
          <section className="pc-row">
            <header className="pc-row-head">
              <Sticker name="round-table.png" size={20} />
              <span>组队提示</span>
            </header>
            <ul className="pc-hints">
              {result.matching_hints.map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="pc-row">
          <header className="pc-row-head">
            <Sticker name="certificate.png" size={20} />
            <span>画像档案</span>
          </header>
          <div className="pc-meta">
            {sampleItems !== null ? (
              <div className="pc-meta-row">
                <span>分析样本</span>
                <b className="mono">{sampleItems} 条喜欢</b>
              </div>
            ) : null}
            <div className="pc-meta-row">
              <span>置信度</span>
              <b className="mono">{Math.round(result.confidence * 100)}%</b>
            </div>
            <div className="pc-meta-row">
              <span>校准状态</span>
              <b>{result.calibrated ? "已答题校准" : "未校准 · 可直接使用"}</b>
            </div>
            <div className="pc-meta-row">
              <span>文案生成</span>
              <b>{generation}</b>
            </div>
            <div className="pc-meta-row">
              <span>可见范围</span>
              <b>{result.visibility === "members" ? "成局后成员可见" : result.visibility}</b>
            </div>
          </div>
        </section>
      </div>

      <footer className="pc-footer">
        <Sticker name="badge.png" size={16} />
        噜噜成局 · 噜噜为你生成
      </footer>
    </div>
  );
}
