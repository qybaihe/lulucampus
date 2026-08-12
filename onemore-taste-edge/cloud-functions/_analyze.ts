import { TAXONOMY } from "./_taxonomy";

const MODEL_VERSION = "taste-v2";
const SAMPLE_FULL_THRESHOLD = 200;
const IMAGE_POST_TYPES = new Set([2, 68, 150]);

type Item = Record<string, unknown>;

function clamp(value: number, low = 0, high = 1): number {
  return Math.min(high, Math.max(low, value));
}

function asSeconds(value: unknown): number | null {
  if (typeof value === "number" && value) {
    return value > 1000 ? Math.round(value / 100) / 10 : Math.round(value * 10) / 10;
  }
  return null;
}

function publishedAt(raw: Record<string, unknown>): string | null {
  const created = raw.create_time;
  if (typeof created !== "number" || !created) return null;
  const date = new Date(created * 1000);
  const offset = 8 * 60;
  const local = new Date(date.getTime() + offset * 60 * 1000);
  return local.toISOString().replace("Z", "+08:00");
}

export function normalizeItem(raw: Record<string, unknown>): Item {
  const awemeId = String(raw.aweme_id || "");
  const images = raw.images || raw.image_post_info;
  const isImage = Boolean(images) || IMAGE_POST_TYPES.has(Number(raw.aweme_type));
  const kind = isImage ? "note" : "video";
  const author = (raw.author as Record<string, unknown>) || {};
  const stats = (raw.statistics as Record<string, unknown>) || {};
  const video = (raw.video as Record<string, unknown>) || {};
  const description = String(raw.desc || raw.item_title || "").trim();
  const extras = Array.isArray(raw.text_extra) ? raw.text_extra : [];
  const hashtags = extras
    .map((entry) => (entry && typeof entry === "object" ? (entry as { hashtag_name?: string }).hashtag_name : null))
    .filter((name): name is string => Boolean(name));
  const tags = Array.isArray(raw.video_tag) ? raw.video_tag : [];
  const platformTags = tags
    .map((entry) => (entry && typeof entry === "object" ? (entry as { tag_name?: string }).tag_name : null))
    .filter((name): name is string => Boolean(name));
  return {
    aweme_id: awemeId,
    kind,
    url: `https://www.douyin.com/${kind}/${awemeId}`,
    title: String(raw.item_title || ""),
    description,
    hashtags,
    platform_tags: platformTags,
    author: {
      nickname: String(author.nickname || ""),
      uid: String(author.uid || ""),
      sec_uid: String(author.sec_uid || ""),
    },
    published_at: publishedAt(raw),
    duration_seconds: asSeconds(video.duration || raw.duration),
    statistics: {
      likes: Number(stats.digg_count || 0),
      comments: Number(stats.comment_count || 0),
      collects: Number(stats.collect_count || 0),
      shares: Number(stats.share_count || 0),
    },
    is_aigc: Boolean(raw.is_aigc_media),
  };
}

function itemText(item: Item): string {
  const author = (item.author as Record<string, unknown>) || {};
  const parts = [
    String(item.description || ""),
    String(item.title || ""),
    String(author.nickname || ""),
    ...((item.hashtags as string[]) || []),
    ...((item.platform_tags as string[]) || []),
  ];
  return parts.join(" ").toLowerCase();
}

function keywordHits(texts: string[], keywords: readonly string[]): number {
  return texts.reduce((sum, text) => (keywords.some((word) => text.includes(word)) ? sum + 1 : sum), 0);
}

function domainShares(texts: string[]): Record<string, number> {
  const total = texts.length || 1;
  const out: Record<string, number> = {};
  for (const domain of TAXONOMY.domains) {
    out[domain.key] = Math.round((keywordHits(texts, domain.keywords) / total) * 10000) / 10000;
  }
  return out;
}

function signalShares(texts: string[]): Record<string, number> {
  const total = texts.length || 1;
  const out: Record<string, number> = {};
  for (const signal of TAXONOMY.signals) {
    out[signal.key] = Math.round((keywordHits(texts, signal.keywords) / total) * 10000) / 10000;
  }
  return out;
}

function breadthOf(shares: Record<string, number>): number {
  const top = Object.values(shares).sort((a, b) => b - a).slice(0, 4);
  const meanTop = top.length ? top.reduce((s, x) => s + x, 0) / top.length : 0;
  const coverage = Object.values(shares).filter((share) => share >= 0.02).length / Object.keys(shares).length;
  return Math.round(clamp(meanTop * 0.7 + coverage * 0.3) * 10000) / 10000;
}

function tagContentScores(
  domains: Record<string, number>,
  signals: Record<string, number>,
  breadth: number,
): Record<string, number> {
  const scores: Record<string, number> = {};
  for (const tag of TAXONOMY.tags) {
    const domainPart = Object.entries(tag.domains).reduce(
      (sum, [key, weight]) => sum + (domains[key] || 0) * Number(weight),
      0,
    );
    const signalPart = Object.entries(tag.signals).reduce(
      (sum, [key, weight]) => sum + (signals[key] || 0) * Number(weight),
      0,
    );
    const breadthPart = breadth * Number(tag.breadth);
    const weightTotal =
      Object.values(tag.domains).reduce((s, w) => s + Number(w), 0) +
      Object.values(tag.signals).reduce((s, w) => s + Number(w), 0) +
      Number(tag.breadth);
    scores[tag.key] = weightTotal
      ? Math.round(((domainPart + signalPart + breadthPart) / weightTotal) * 10000) / 10000
      : 0;
  }
  return scores;
}

function tagLabel(key: string): string {
  return TAXONOMY.tags.find((tag) => tag.key === key)?.label || key;
}

function pickSecondary(ranked: Array<[string, number]>, primaryKey: string) {
  const groups = TAXONOMY.groups as Record<string, string>;
  const primaryGroup = groups[primaryKey] || "other";
  const secondary: Array<{ key: string; label: string; score: number }> = [];
  const used = new Set<string>();
  for (const [key, score] of ranked.slice(1)) {
    const group = groups[key] || "other";
    if (group === primaryGroup || used.has(group) || score < 0.05) continue;
    secondary.push({ key, label: tagLabel(key), score });
    used.add(group);
    if (secondary.length === 3) break;
  }
  if (secondary.length < 2) {
    for (const [key, score] of ranked.slice(1)) {
      if (secondary.length >= 2) break;
      if (!secondary.some((item) => item.key === key) && score >= 0.05) {
        secondary.push({ key, label: tagLabel(key), score });
      }
    }
  }
  return secondary;
}

function buildSummary(
  primaryLabel: string,
  dimensions: Record<string, number>,
  interestDomains: Array<{ label: string }>,
): string {
  const traits: string[] = [];
  if ((dimensions.action_orientation || 0) >= 0.08) traits.push("偏实践与工具向");
  if ((dimensions.openness || 0) >= 0.15) traits.push("兴趣面较广");
  if ((dimensions.aesthetic_orientation || 0) >= 0.08) traits.push("有审美与氛围偏好");
  if ((dimensions.competition_orientation || 0) >= 0.08) traits.push("关注成长与挑战");
  if (!traits.length) traits.push("口味较均衡");
  const focus = interestDomains.map((d) => d.label).filter(Boolean).slice(0, 3);
  let center = "多元内容";
  if (focus.length >= 3) center = `${focus[0]}、${focus[1]}，并延伸到${focus[2]}`;
  else if (focus.length >= 2) center = focus.join("、");
  else if (focus.length === 1) center = focus[0];
  return `你身上最显眼的是「${primaryLabel}」：${traits.join("，")}。最近更往${center}那边钻。`;
}

function buildPersona(primaryLabel: string, interestDomains: Array<{ label: string }>): string {
  const focus = interestDomains.map((d) => d.label).filter(Boolean).slice(0, 2).join("、") || "好多不一样的东西";
  return `我慢慢看完啦。你这味儿很「${primaryLabel}」，老往${focus}那边钻。我不急着下结论——要成局，找能把一件小事一起做完的人就好。`;
}

function ruleHints(primaryLabel: string, domains: Array<{ label: string }>): string[] {
  const focus = domains.slice(0, 2).map((d) => d.label).filter(Boolean);
  const hints = [`找也带点「${primaryLabel}」劲儿的人一起成局`];
  if (focus.length) hints.push(`从${focus.join("、")}开口，比先交换标签顺`);
  hints.push("先约一件能做完的小事，别先聊人设");
  return hints.slice(0, 3);
}

export function analyzeItems(items: Item[], apiPages: number) {
  const texts = items.map(itemText);
  const domains = domainShares(texts);
  const signals = signalShares(texts);
  const breadth = breadthOf(domains);
  const contentScores = tagContentScores(domains, signals, breadth);
  const topDomains = [...TAXONOMY.domains]
    .map((domain) => ({
      key: domain.key,
      label: domain.label,
      score: domains[domain.key] || 0,
    }))
    .filter((d) => d.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 4);
  const dimensions = {
    openness: breadth,
    action_orientation: signals.action_oriented || 0,
    aesthetic_orientation: signals.aesthetic || 0,
    competition_orientation: signals.competitive || 0,
  };
  const authors = new Set<string>();
  for (const item of items) {
    const author = (item.author as Record<string, unknown>) || {};
    const id = String(author.sec_uid || author.nickname || "");
    if (id) authors.add(id);
  }
  const ranked = Object.entries(contentScores).sort((a, b) => b[1] - a[1]) as Array<[string, number]>;
  const [primaryKey, primaryScore] = ranked[0] || ["explorer_builder", 0];
  const margin = ranked[1] ? primaryScore - ranked[1][1] : 1;
  const sufficiency = Math.min(1, items.length / SAMPLE_FULL_THRESHOLD);
  const marginNorm = Math.min(1, margin / 0.12);
  const strength = Math.min(1, primaryScore / 0.35);
  const confidence = Math.round(clamp(0.4 * sufficiency + 0.3 * marginNorm + 0.3 * strength) * 10000) / 10000;
  const primary = { key: primaryKey, label: tagLabel(primaryKey), score: primaryScore };
  const secondary = pickSecondary(ranked, primaryKey);
  const summary = buildSummary(primary.label, dimensions, topDomains);
  const persona = buildPersona(primary.label, topDomains);
  const matchingHints = ruleHints(primary.label, topDomains);
  return {
    status: "ready",
    primary_tag: primary,
    secondary_tags: secondary,
    interest_domains: topDomains,
    interest_facets: [] as Array<Record<string, string>>,
    dimensions,
    summary,
    persona,
    matching_hints: matchingHints,
    confidence,
    calibrated: false,
    calibrated_at: null,
    sample: {
      items: items.length,
      unique_authors: authors.size,
      api_pages: apiPages,
      calibrated: false,
      generation: "rule",
    },
    source: "douyin",
    model_version: MODEL_VERSION,
    visibility: "members",
  };
}

export function mergeItems(likes: Item[], collects: Item[], posts: Item[]): Item[] {
  const likeIds = new Set(likes.map((item) => String(item.aweme_id || "")).filter(Boolean));
  const collectIds = new Set(collects.map((item) => String(item.aweme_id || "")).filter(Boolean));
  const merged = new Map<string, Item>();
  for (const item of [...likes, ...collects, ...posts]) {
    const aid = String(item.aweme_id || "");
    if (!aid || merged.has(aid)) continue;
    let bucket = "post";
    if (likeIds.has(aid)) bucket = "like";
    else if (collectIds.has(aid)) bucket = "collect";
    merged.set(aid, { ...item, source_bucket: bucket });
  }
  return [...merged.values()];
}
