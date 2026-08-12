import { forwardRef } from "react";
import type {
  TasteProfileResult,
  TasteSourceProfile,
} from "../../core/api/repositories";
import { LuluSprite, LuluStill } from "../../components/lulu/LuluSprite";
import { Sticker } from "../../components/ui/primitives";
import { DouyinAvatar, VerifiedBadge } from "./TasteImportScreen";

/**
 * 抖音画像卡 — 后端 READY 结果的定制展示卡。
 * variant=default：原 App 导入流布局
 * variant=share：头像居中，噜噜在底部，适合分享导出
 */
export const PersonaCard = forwardRef<
  HTMLDivElement,
  {
    result: TasteProfileResult;
    profile: TasteSourceProfile | null;
    variant?: "default" | "share";
  }
>(function PersonaCard({ result, profile, variant = "default" }, ref) {
  const domains = [...result.interest_domains]
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);
  const maxDomain = domains[0]?.score ?? 1;
  const share = variant === "share";

  return (
    <div
      ref={ref}
      className={`persona-card ${share ? "persona-card-share" : ""}`}
      data-od-id="persona-card"
    >
      <div className="pc-hero">
        {share ? (
          <div className="pc-hero-center">
            <div className="pc-avatar-ring pc-avatar-lg">
              <DouyinAvatar profile={profile} size={88} />
            </div>
            <div className="pc-name">
              {profile?.nickname ?? "抖音用户"}
              <VerifiedBadge />
            </div>
            {profile?.uid ? (
              <div className="pc-uid mono">抖音号 {profile.uid}</div>
            ) : null}
            <div className="pc-primary">
              <div className="pc-primary-label">我的主标签</div>
              <div className="pc-primary-tag">
                <span className="pc-primary-name">{result.primary_tag.label}</span>
                <span className="pc-primary-score mono">
                  {Math.round(result.primary_tag.score * 100)}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <>
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
                {profile?.uid ? (
                  <div className="pc-uid mono">抖音号 {profile.uid}</div>
                ) : null}
              </div>
            </div>
            <div className="pc-primary">
              <div className="pc-primary-label">我的主标签</div>
              <div className="pc-primary-tag">
                <span className="pc-primary-name">{result.primary_tag.label}</span>
                <span className="pc-primary-score mono">
                  {Math.round(result.primary_tag.score * 100)}
                </span>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="pc-body">
        {result.secondary_tags.length > 0 ? (
          <section className="pc-row">
            <header className="pc-row-head">
              <Sticker name="design-palette.png" size={20} />
              <span>副标签</span>
            </header>
            <div className="pc-chips">
              {result.secondary_tags.map((t) => (
                <span key={t.key} className="om-chip soft">
                  {t.label}
                </span>
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
                    <i
                      style={{
                        width: `${Math.max(8, Math.round((d.score / maxDomain) * 100))}%`,
                      }}
                    />
                  </span>
                  <span className="pc-domain-score mono">
                    {Math.round(d.score * 100)}
                  </span>
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
            </header>
            <div className="pc-chips">
              {result.interest_facets.slice(0, 12).map((f) => (
                <span key={`${f.domain}-${f.facet}`} className="om-chip">
                  {f.label}
                </span>
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
            <p className="pc-text">{result.persona}</p>
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

        {!share ? (
          <section className="pc-row">
            <header className="pc-row-head">
              <Sticker name="certificate.png" size={20} />
              <span>画像档案</span>
            </header>
            <div className="pc-meta">
              <div className="pc-meta-row">
                <span>置信度</span>
                <b className="mono">{Math.round(result.confidence * 100)}%</b>
              </div>
              <div className="pc-meta-row">
                <span>校准状态</span>
                <b>{result.calibrated ? "已答题校准" : "未校准 · 可直接使用"}</b>
              </div>
            </div>
          </section>
        ) : null}
      </div>

      {share ? (
        <div className="pc-lulu-foot">
          <LuluStill clip="core.celebrate" size={72} />
          <div className="pc-lulu-foot-copy">
            <div className="pc-lulu-foot-title">噜噜看完啦</div>
            <div className="pc-lulu-foot-sub">让噜噜看看你的抖音画像</div>
          </div>
        </div>
      ) : (
        <footer className="pc-footer">
          <Sticker name="badge.png" size={16} />
          噜噜成局 · 噜噜为你生成
        </footer>
      )}
    </div>
  );
});
