export type TasteSourceProfile = {
  nickname?: string | null;
  avatar_url?: string | null;
  uid?: string | null;
  sec_uid?: string | null;
};

export type TasteProfileResult = {
  primary_tag: { key: string; label: string; score: number };
  secondary_tags: Array<{ key: string; label: string; score: number }>;
  interest_domains: Array<{ key: string; label: string; score: number }>;
  interest_facets: Array<{ domain: string; facet: string; label: string }>;
  summary?: string;
  persona?: string;
  matching_hints: string[];
  confidence: number;
  calibrated: boolean;
};

export type DemoTasteStatus = {
  enabled: boolean;
  douyin_import_enabled: boolean;
  mode: string;
  message: string;
  http_link_import_ready?: boolean;
};

export type DemoTasteFromLink = {
  source: string;
  share_url: string;
  profile_url: string;
  source_profile?: TasteSourceProfile | null;
  posts_count: number;
  likes_count: number;
  collects_count?: number;
  items_used: number;
  result: TasteProfileResult;
};

type Envelope<T> = {
  data: T;
  error?: { message?: string; code?: string } | null;
};

async function request<T>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(path, {
    method: opts.method ?? (opts.body !== undefined ? "POST" : "GET"),
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  let json: Envelope<T> | null = null;
  try {
    json = (await res.json()) as Envelope<T>;
  } catch {
    throw new Error(`服务无响应 (${res.status})`);
  }
  if (!res.ok || json.error) {
    throw new Error(json.error?.message || `请求失败 (${res.status})`);
  }
  return json.data;
}

export function fetchDemoStatus(): Promise<DemoTasteStatus> {
  return request<DemoTasteStatus>("/demo/taste/status");
}

export function analyzeFromShareLink(shareUrl: string): Promise<DemoTasteFromLink> {
  return request<DemoTasteFromLink>("/demo/taste/from-link", {
    method: "POST",
    body: {
      share_url: shareUrl,
      likes_limit: 30,
      posts_limit: 20,
      collects_limit: 30,
      use_llm: true,
    },
  });
}
