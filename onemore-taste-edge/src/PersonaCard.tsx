import { forwardRef, useState } from "react";
import { LuluStill } from "./LuluSprite";
import type { TasteProfileResult, TasteSourceProfile } from "./api";

function DouyinAvatar({
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

export const PersonaCard = forwardRef<
  HTMLDivElement,
  { result: TasteProfileResult; profile: TasteSourceProfile | null }
>(function PersonaCard({ result, profile }, ref) {
  const domains = [...result.interest_domains].sort((a, b) => b.score - a.score).slice(0, 5);
  const maxDomain = domains[0]?.score ?? 1;

  return (
    <div ref={ref} className="persona-card persona-card-share">
      <div className="pc-hero">
        <div className="pc-hero-center">
          <div className="pc-avatar-ring pc-avatar-lg">
            <DouyinAvatar profile={profile} size={88} />
          </div>
          <div className="pc-name">{profile?.nickname ?? "抖音用户"}</div>
          {profile?.uid ? <div className="pc-uid">抖音号 {profile.uid}</div> : null}
          <div className="pc-primary">
            <div className="pc-primary-label">我的主标签</div>
            <div className="pc-primary-tag">
              <span className="pc-primary-name">{result.primary_tag.label}</span>
              <span className="pc-primary-score">{Math.round(result.primary_tag.score * 100)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="pc-body">
        {result.secondary_tags.length > 0 ? (
          <section className="pc-row">
            <header className="pc-row-head">副标签</header>
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
            <header className="pc-row-head">兴趣领域</header>
            <div className="pc-domains">
              {domains.map((d) => (
                <div key={d.key} className="pc-domain">
                  <span className="pc-domain-label">{d.label}</span>
                  <span className="pc-domain-bar">
                    <i style={{ width: `${Math.max(8, Math.round((d.score / maxDomain) * 100))}%` }} />
                  </span>
                  <span className="pc-domain-score">{Math.round(d.score * 100)}</span>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {result.interest_facets.length > 0 ? (
          <section className="pc-row">
            <header className="pc-row-head">兴趣切面</header>
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
            <header className="pc-row-head">画像摘要</header>
            <p className="pc-text">{result.summary}</p>
          </section>
        ) : null}

        {result.persona ? (
          <section className="pc-row">
            <header className="pc-row-head">噜噜评语</header>
            <p className="pc-text">{result.persona}</p>
          </section>
        ) : null}

        {result.matching_hints.length > 0 ? (
          <section className="pc-row">
            <header className="pc-row-head">组队提示</header>
            <ul className="pc-hints">
              {result.matching_hints.map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>

      <div className="pc-lulu-foot">
        <LuluStill clip="core.celebrate" size={72} />
        <div className="pc-lulu-foot-copy">
          <div className="pc-lulu-foot-title">噜噜看完啦</div>
          <div className="pc-lulu-foot-sub">让噜噜看看你的抖音画像</div>
        </div>
      </div>
    </div>
  );
});
