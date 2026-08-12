import type { EnvMap } from "./_http";

const DEFAULT_BASE = "https://ai-gateway.edgeone.link/v1";
const DEFAULT_MODEL = "@makers/deepseek-v4-flash";

type Result = Record<string, unknown>;
type Item = Record<string, unknown>;

function pickForSnippets(items: Item[]): Item[] {
  const buckets: Record<string, Item[]> = { like: [], collect: [], post: [] };
  for (const item of items) {
    const bucket = String(item.source_bucket || "post");
    (buckets[bucket] || buckets.post).push(item);
  }
  return [...buckets.like.slice(0, 16), ...buckets.collect.slice(0, 16), ...buckets.post.slice(0, 8)];
}

function snippets(items: Item[]): Array<{ source: string; text: string }> {
  const out: Array<{ source: string; text: string }> = [];
  const seen = new Set<string>();
  for (const item of pickForSnippets(items)) {
    const text = [item.description, item.title, ...(((item.hashtags as string[]) || []).slice(0, 5))]
      .map((part) => String(part || "").trim())
      .filter(Boolean)
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();
    if (text.length < 8) continue;
    const key = text.slice(0, 48);
    if (seen.has(key)) continue;
    seen.add(key);
    const source = String(item.source_bucket || "post");
    out.push({ source: source === "collect" || source === "like" ? source : "post", text: text.slice(0, 110) });
    if (out.length >= 36) break;
  }
  return out;
}

function parseJson(text: string): Record<string, unknown> | null {
  const trimmed = text.trim().replace(/^```json\s*/i, "").replace(/^```\s*/, "").replace(/```$/, "").trim();
  try {
    return JSON.parse(trimmed) as Record<string, unknown>;
  } catch {
    const match = trimmed.match(/\{[\s\S]*\}/);
    if (!match) return null;
    try {
      return JSON.parse(match[0]) as Record<string, unknown>;
    } catch {
      return null;
    }
  }
}

export async function enrichWithLlm(
  result: Result,
  items: Item[],
  env: EnvMap,
): Promise<Result> {
  const apiKey = (env.AI_GATEWAY_API_KEY || "").trim();
  if (!apiKey || !items.length) return result;
  const sample = snippets(items);
  if (!sample.length) return result;

  const primary = (result.primary_tag as { key?: string }) || {};
  const secondary = Array.isArray(result.secondary_tags) ? result.secondary_tags : [];
  const domains = Array.isArray(result.interest_domains) ? result.interest_domains : [];
  const allowedTags = [primary.key, ...secondary.map((tag) => (tag as { key?: string }).key)].filter(Boolean);
  const domainKeys = domains.map((d) => (d as { key?: string }).key).filter(Boolean);

  const system =
    "你现在不是分析师，你是「噜噜成局」里的水豚噜噜：圆、慢半拍、刚看完对方的内容，抬起头跟「你」说话。\n" +
    "用户把个人主页分享链接给你看。样本来自最近的喜欢、收藏和作品；收藏是更有意存下来的，和喜欢一起看。\n" +
    "硬性要求：\n" +
    "1) persona 必须第一人称（我）对第二人称（你）；像口头说的短句，不要书面鉴定腔。\n" +
    "2) 先点出 content_snippets 里 1-2 件具体事（比赛、工具、地方、习惯都行），再轻轻落到这个人怎么成局。\n" +
    "3) 允许一点点水豚身体感：慢慢看完、嗯了一下、拍拍、把局凑上。不要堆叠萌词、不要口头禅刷屏。\n" +
    "4) 禁止：这位用户、该账号、作为一名、画像、标签、算法、模型、抖音、喜欢列表、说教、鸡汤、列点。\n" +
    "5) 不要改动 primary_tag.key；interest_facets.domain 必须在 allowed_domain_keys 内。\n" +
    "6) 只输出 JSON：\n" +
    "   - summary: 40-90字，给卡片看的一句人味描述，仍用「你」，不要鉴定报告\n" +
    "   - persona: 70-140字，噜噜刚看完抬头发的评语\n" +
    "   - interest_facets: [{domain,facet,label}] 2-5个\n" +
    "   - matching_hints: 2-4条，也是噜噜口吻，每条不超过28字，像在帮你找能一起做事的人\n" +
    "   - tone: 短词";

  const user = JSON.stringify(
    {
      allowed_tag_keys: allowedTags,
      allowed_domain_keys: domainKeys,
      scores: {
        primary_tag: result.primary_tag,
        secondary_tags: result.secondary_tags,
        interest_domains: result.interest_domains,
        dimensions: result.dimensions,
      },
      content_snippets: sample,
      sample_size: items.length,
    },
    null,
    0,
  );

  const base = ((env.AI_GATEWAY_BASE_URL || DEFAULT_BASE).replace(/\/$/, ""));
  const model = env.AI_GATEWAY_MODEL || DEFAULT_MODEL;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 25000);
  try {
    const resp = await fetch(`${base}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        temperature: 0.7,
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: system },
          { role: "user", content: user },
        ],
      }),
      signal: ctrl.signal,
    });
    if (!resp.ok) {
      const sampleBag = { ...((result.sample as Record<string, unknown>) || {}) };
      sampleBag.generation = "rule";
      sampleBag.llm_error = `http_${resp.status}`;
      return { ...result, sample: sampleBag };
    }
    const payload = (await resp.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    const content = payload.choices?.[0]?.message?.content || "";
    const data = parseJson(content);
    if (!data) {
      const sampleBag = { ...((result.sample as Record<string, unknown>) || {}) };
      sampleBag.generation = "rule";
      sampleBag.llm_error = "bad_json";
      return { ...result, sample: sampleBag };
    }

    const next = { ...result };
    const sampleBag = { ...((next.sample as Record<string, unknown>) || {}) };
    if (typeof data.summary === "string" && data.summary.trim().length >= 12) {
      next.summary = data.summary.trim().slice(0, 200);
    }
    if (typeof data.persona === "string" && data.persona.trim().length >= 12) {
      next.persona = data.persona.trim().slice(0, 280);
      sampleBag.persona = next.persona;
    }
    if (Array.isArray(data.matching_hints)) {
      const hints = data.matching_hints
        .map((item) => String(item).trim().slice(0, 36))
        .filter(Boolean)
        .slice(0, 4);
      if (hints.length) {
        next.matching_hints = hints;
        sampleBag.matching_hints = hints;
      }
    }
    const domainSet = new Set(domainKeys);
    if (Array.isArray(data.interest_facets)) {
      const facets: Array<Record<string, string>> = [];
      for (const entry of data.interest_facets) {
        if (!entry || typeof entry !== "object") continue;
        const row = entry as Record<string, string>;
        const domain = String(row.domain || row.domain_key || "");
        const facet = String(row.facet || row.key || "");
        const label = String(row.label || row.facet_label || facet);
        if (!domainSet.has(domain) || !facet) continue;
        facets.push({ domain, facet: facet.slice(0, 48), label: label.slice(0, 48), source: "llm" });
        if (facets.length >= 6) break;
      }
      if (facets.length) {
        next.interest_facets = facets;
        sampleBag.interest_facets = facets;
      }
    }
    sampleBag.generation = "llm";
    sampleBag.llm_model = model;
    next.sample = sampleBag;
    return next;
  } catch (err) {
    const sampleBag = { ...((result.sample as Record<string, unknown>) || {}) };
    sampleBag.generation = "rule";
    sampleBag.llm_error = err instanceof Error && err.name === "AbortError" ? "timeout" : "llm_fail";
    return { ...result, sample: sampleBag };
  } finally {
    clearTimeout(timer);
  }
}
