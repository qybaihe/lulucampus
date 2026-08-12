import { AppError, type EnvMap, requireCookie } from "./_http";

const SHORT_LINK_RE = /(?:https?:\/\/)?v\.douyin\.com\/([A-Za-z0-9_-]{4,32})\/?/i;
const USER_PATH_RE = /\/user\/(MS4wLjAB[\w-]+)/;
const SEC_UID_RE = /(MS4wLjAB[\w-]{20,})/;

const DEFAULT_UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36";

export type AwemeRaw = Record<string, unknown>;

export type CollectBundle = {
  sec_uid: string;
  profile_url: string;
  resolved_url: string;
  source_profile: {
    nickname: string | null;
    avatar_url: string | null;
    uid: string | null;
    sec_uid: string;
  };
  posts_raw: AwemeRaw[];
  likes_raw: AwemeRaw[];
  collects_raw: AwemeRaw[];
  meta: {
    posts: PageMeta;
    likes: PageMeta;
    collects: PageMeta;
    host: string;
  };
};

type PageMeta = {
  pages: number;
  stopped: string;
  returned: number;
  http_status?: number;
};

export function extractShareUrl(text: string): string | null {
  const raw = (text || "").trim();
  if (!raw) return null;
  const short = SHORT_LINK_RE.exec(raw);
  if (short) return `https://v.douyin.com/${short[1]}/`;
  const user = USER_PATH_RE.exec(raw);
  if (user) return `https://www.douyin.com/user/${user[1]}`;
  const sec = SEC_UID_RE.exec(raw);
  if (sec && raw.length < 80) return `https://www.douyin.com/user/${sec[1]}`;
  return null;
}

function headers(cookie: string, extra: Record<string, string> = {}): HeadersInit {
  return {
    "User-Agent": DEFAULT_UA,
    Accept: "application/json, text/plain, */*",
    Cookie: cookie,
    ...extra,
  };
}

async function fetchText(
  url: string,
  cookie: string,
  extra: Record<string, string>,
  timeoutMs: number,
  init: { method?: string; body?: string } = {},
): Promise<{ status: number; url: string; text: string }> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const resp = await fetch(url, {
      method: init.method ?? "GET",
      redirect: "follow",
      headers: headers(cookie, extra),
      body: init.body,
      signal: ctrl.signal,
    });
    const text = await resp.text();
    return { status: resp.status, url: resp.url, text };
  } finally {
    clearTimeout(timer);
  }
}

export async function resolveSecUid(
  shareText: string,
  cookie: string,
): Promise<{ sec_uid: string; profile_url: string; resolved_url: string }> {
  const url = extractShareUrl(shareText);
  if (!url) {
    throw new AppError(
      "DOUYIN_SHARE_URL_INVALID",
      "请粘贴抖音个人主页分享链接（v.douyin.com/...）",
      400,
    );
  }
  const already = USER_PATH_RE.exec(url);
  if (already && !url.includes("v.douyin.com")) {
    return { sec_uid: already[1], profile_url: url, resolved_url: url };
  }

  const resp = await fetchText(
    url,
    cookie,
    { Referer: "https://www.douyin.com/", Accept: "text/html,*/*" },
    12000,
  );
  const fromFinal = USER_PATH_RE.exec(resp.url);
  if (fromFinal) {
    const sec = fromFinal[1];
    return {
      sec_uid: sec,
      profile_url: `https://www.douyin.com/user/${sec}`,
      resolved_url: resp.url,
    };
  }
  const fromBody = USER_PATH_RE.exec(resp.text) || SEC_UID_RE.exec(resp.text);
  if (fromBody) {
    const sec = fromBody[1] && fromBody[1].startsWith("MS4wLjAB") ? fromBody[1] : fromBody[0];
    if (sec.startsWith("MS4wLjAB")) {
      return {
        sec_uid: sec,
        profile_url: `https://www.douyin.com/user/${sec}`,
        resolved_url: resp.url,
      };
    }
  }
  throw new AppError(
    "DOUYIN_PROFILE_RESOLVE_FAILED",
    "无法从分享链接解析到个人主页，请确认链接有效且喜欢列表已公开",
    422,
  );
}

async function fetchAwemePages(opts: {
  apiPath: string;
  secUid: string;
  referer: string;
  limit: number;
  cookie: string;
}): Promise<{ items: AwemeRaw[]; meta: PageMeta }> {
  if (opts.limit <= 0) {
    return { items: [], meta: { pages: 0, stopped: "limit_zero", returned: 0 } };
  }
  const items = new Map<string, AwemeRaw>();
  let cursor: string | number = 0;
  let pages = 0;
  let stopped = "complete";
  let httpStatus: number | undefined;

  while (items.size < opts.limit && pages < 8) {
    const count = Math.min(18, opts.limit - items.size);
    const params = new URLSearchParams({
      device_platform: "webapp",
      aid: "6383",
      channel: "channel_pc_web",
      sec_user_id: opts.secUid,
      max_cursor: String(cursor),
      min_cursor: "0",
      count: String(count),
      publish_video_strategy_type: "2",
      version_code: "170400",
      version_name: "17.4.0",
      cookie_enabled: "true",
      platform: "PC",
    });
    const url = `https://www.douyin.com${opts.apiPath}?${params.toString()}`;
    const resp = await fetchText(url, opts.cookie, { Referer: opts.referer }, 15000);
    pages += 1;
    httpStatus = resp.status;
    if (resp.status === 403 || resp.text.includes("ArgusSecurityPlugin")) {
      stopped = "blocked";
      break;
    }
    if (resp.status !== 200) {
      stopped = "http_error";
      break;
    }
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(resp.text) as Record<string, unknown>;
    } catch {
      stopped = "bad_json";
      break;
    }
    const statusCode = data.status_code;
    if (statusCode !== 0 && statusCode !== undefined && statusCode !== null) {
      stopped = `status_${String(statusCode)}`;
      break;
    }
    const batch = Array.isArray(data.aweme_list) ? (data.aweme_list as AwemeRaw[]) : [];
    for (const raw of batch) {
      const aid = String(raw.aweme_id || "");
      if (aid && !items.has(aid)) items.set(aid, raw);
    }
    const hasMore = data.has_more;
    cursor = (data.max_cursor as string | number | undefined) ?? (data.cursor as string | number | undefined) ?? cursor;
    if (hasMore === 0 || hasMore === false || batch.length === 0) {
      stopped = "end";
      break;
    }
    if (items.size >= opts.limit) {
      stopped = "limit";
      break;
    }
  }

  const list = [...items.values()].slice(0, opts.limit);
  return {
    items: list,
    meta: {
      pages,
      stopped,
      returned: list.length,
      ...(httpStatus ? { http_status: httpStatus } : {}),
    },
  };
}

async function fetchCollectionPages(opts: {
  secUid: string;
  referer: string;
  limit: number;
  cookie: string;
}): Promise<{ items: AwemeRaw[]; meta: PageMeta }> {
  if (opts.limit <= 0) {
    return { items: [], meta: { pages: 0, stopped: "limit_zero", returned: 0 } };
  }
  const items = new Map<string, AwemeRaw>();
  let cursor: string | number = 0;
  let pages = 0;
  let stopped = "complete";
  let httpStatus: number | undefined;
  const query = new URLSearchParams({
    device_platform: "webapp",
    aid: "6383",
    channel: "channel_pc_web",
    sec_user_id: opts.secUid,
    publish_video_strategy_type: "2",
    version_code: "170400",
    version_name: "17.4.0",
    cookie_enabled: "true",
    platform: "PC",
  });

  while (items.size < opts.limit && pages < 8) {
    const count = Math.min(18, opts.limit - items.size);
    const url = `https://www.douyin.com/aweme/v1/web/aweme/listcollection/?${query.toString()}`;
    const body = new URLSearchParams({
      count: String(count),
      cursor: String(cursor),
      sec_user_id: opts.secUid,
    }).toString();
    const resp = await fetchText(
      url,
      opts.cookie,
      {
        Referer: opts.referer,
        Origin: "https://www.douyin.com",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      15000,
      { method: "POST", body },
    );
    pages += 1;
    httpStatus = resp.status;
    if (resp.status === 403 || resp.text.includes("ArgusSecurityPlugin")) {
      stopped = "blocked";
      break;
    }
    if (resp.status !== 200) {
      stopped = "http_error";
      break;
    }
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(resp.text) as Record<string, unknown>;
    } catch {
      stopped = "bad_json";
      break;
    }
    const statusCode = data.status_code;
    if (statusCode === 3002279) {
      stopped = "private";
      break;
    }
    if (statusCode !== 0 && statusCode !== undefined && statusCode !== null) {
      stopped = `status_${String(statusCode)}`;
      break;
    }
    const batch = Array.isArray(data.aweme_list) ? (data.aweme_list as AwemeRaw[]) : [];
    for (const raw of batch) {
      const aid = String(raw.aweme_id || "");
      if (aid && !items.has(aid)) items.set(aid, raw);
    }
    const hasMore = data.has_more;
    cursor = (data.cursor as string | number | undefined) ?? cursor;
    if (hasMore === 0 || hasMore === false || batch.length === 0) {
      stopped = "end";
      break;
    }
    if (items.size >= opts.limit) {
      stopped = "limit";
      break;
    }
  }

  const list = [...items.values()].slice(0, opts.limit);
  return {
    items: list,
    meta: {
      pages,
      stopped,
      returned: list.length,
      ...(httpStatus ? { http_status: httpStatus } : {}),
    },
  };
}

function avatarUrl(author: Record<string, unknown> | undefined): string | null {
  if (!author) return null;
  for (const key of ["avatar_thumb", "avatar_medium", "avatar_larger"]) {
    const blob = author[key];
    if (blob && typeof blob === "object") {
      const urls = (blob as { url_list?: unknown }).url_list;
      if (Array.isArray(urls) && urls[0]) return String(urls[0]);
    }
  }
  return null;
}

async function avatarAsDataUrl(url: string | null): Promise<string | null> {
  if (!url) return null;
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 8000);
    const resp = await fetch(url, {
      redirect: "follow",
      headers: {
        "User-Agent": DEFAULT_UA,
        Referer: "https://www.douyin.com/",
        Accept: "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
      },
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    if (!resp.ok) return null;
    const buf = new Uint8Array(await resp.arrayBuffer());
    if (!buf.byteLength) return null;
    let ctype = (resp.headers.get("content-type") || "image/jpeg").split(";")[0].trim();
    if (!ctype.startsWith("image/")) ctype = "image/jpeg";
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < buf.length; i += chunk) {
      binary += String.fromCharCode(...buf.subarray(i, i + chunk));
    }
    return `data:${ctype};base64,${btoa(binary)}`;
  } catch {
    return null;
  }
}

export async function collectRecent(
  shareText: string,
  env: EnvMap,
  opts: { likesLimit: number; postsLimit: number; collectsLimit: number },
): Promise<CollectBundle> {
  const cookie = requireCookie(env);
  const resolved = await resolveSecUid(shareText, cookie);
  const likeReferer = `${resolved.profile_url}?showTab=like`;
  const collectReferer = `${resolved.profile_url}?showTab=favorite_collection`;

  const [posts, likes, collects] = await Promise.all([
    fetchAwemePages({
      apiPath: "/aweme/v1/web/aweme/post/",
      secUid: resolved.sec_uid,
      referer: resolved.profile_url,
      limit: opts.postsLimit,
      cookie,
    }),
    fetchAwemePages({
      apiPath: "/aweme/v1/web/aweme/favorite/",
      secUid: resolved.sec_uid,
      referer: likeReferer,
      limit: opts.likesLimit,
      cookie,
    }),
    fetchCollectionPages({
      secUid: resolved.sec_uid,
      referer: collectReferer,
      limit: opts.collectsLimit,
      cookie,
    }),
  ]);

  if (!posts.items.length && !likes.items.length && !collects.items.length) {
    throw new AppError(
      "DOUYIN_HTTP_EMPTY",
      "未拉到作品、喜欢或收藏。请把主页「喜欢」和「收藏里的视频」设为公开后再试",
      422,
    );
  }

  let author: Record<string, unknown> = {};
  for (const raw of [...posts.items, ...likes.items, ...collects.items]) {
    const next = (raw.author as Record<string, unknown> | undefined) || {};
    if (next.nickname || next.unique_id) {
      author = next;
      break;
    }
  }
  const remoteAvatar = avatarUrl(author);
  const inlined = await avatarAsDataUrl(remoteAvatar);

  return {
    sec_uid: resolved.sec_uid,
    profile_url: resolved.profile_url,
    resolved_url: resolved.resolved_url,
    source_profile: {
      nickname: author.nickname ? String(author.nickname) : null,
      avatar_url: inlined || remoteAvatar,
      uid: author.uid ? String(author.uid) : author.unique_id ? String(author.unique_id) : null,
      sec_uid: resolved.sec_uid,
    },
    posts_raw: posts.items,
    likes_raw: likes.items,
    collects_raw: collects.items,
    meta: {
      posts: posts.meta,
      likes: likes.meta,
      collects: collects.meta,
      host: "www.douyin.com",
    },
  };
}
