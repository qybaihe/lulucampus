/**
 * Public judge/demo taste API — no App login.
 * Bootstraps via POST /demo/taste/douyin/qr, then polls with ephemeral Bearer.
 */

import { defaultBaseURL } from "../../core/api/client";
import type {
  TasteImportSession,
  TasteProfileResult,
  TasteQRLogin,
  TasteQuestions,
  TasteSourceProfile,
} from "../../core/api/repositories";

const TOKEN_KEY = "onemore.demo.taste.token";
const IMPORT_KEY = "onemore.demo.taste.import";

export type DemoTasteStart = TasteQRLogin & {
  access_token: string;
  guest_user_id: string;
  mode?: string;
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
  collection?: Record<string, unknown>;
  result: TasteProfileResult;
};

type Envelope<T> = {
  data: T;
  error?: { message?: string; code?: string } | null;
  meta?: Record<string, unknown>;
};

function apiBase(): string {
  return defaultBaseURL().replace(/\/$/, "");
}

function loadToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function saveSession(token: string, importId: string) {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(IMPORT_KEY, importId);
  } catch {
    /* private mode */
  }
}

export function clearDemoTasteSession() {
  try {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(IMPORT_KEY);
  } catch {
    /* ignore */
  }
}

async function request<T>(
  path: string,
  opts: {
    method?: string;
    body?: unknown;
    query?: Record<string, string | number | boolean | undefined>;
    token?: string | null;
    auth?: boolean;
  } = {},
): Promise<T> {
  const url = new URL(`${apiBase()}${path.startsWith("/") ? path : `/${path}`}`);
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v === undefined) continue;
      url.searchParams.set(k, String(v));
    }
  }
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const token = opts.token ?? (opts.auth === false ? null : loadToken());
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(url.toString(), {
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

export async function fetchDemoStatus(): Promise<DemoTasteStatus> {
  return request<DemoTasteStatus>("/demo/taste/status", { auth: false });
}

export async function startDemoTasteQR(
  waitSeconds = 10,
): Promise<DemoTasteStart> {
  const data = await request<DemoTasteStart>("/demo/taste/douyin/qr", {
    method: "POST",
    body: { max_items: 0, force: true },
    query: { wait_seconds: waitSeconds },
    auth: false,
  });
  saveSession(data.access_token, data.import_id);
  return data;
}

/** Sync HTTP path: paste Douyin share card / v.douyin.com link → persona. */
export async function analyzeFromShareLink(
  shareUrl: string,
  opts: { likesLimit?: number; postsLimit?: number; collectsLimit?: number; useLlm?: boolean } = {},
): Promise<DemoTasteFromLink> {
  return request<DemoTasteFromLink>("/demo/taste/from-link", {
    method: "POST",
    body: {
      share_url: shareUrl,
      likes_limit: opts.likesLimit ?? 30,
      posts_limit: opts.postsLimit ?? 20,
      collects_limit: opts.collectsLimit ?? 30,
      use_llm: opts.useLlm ?? true,
    },
    auth: false,
  });
}

export async function pollImport(importId: string): Promise<TasteImportSession> {
  return request<TasteImportSession>(`/profile/imports/${importId}`);
}

export async function refreshQR(importId: string): Promise<TasteImportSession> {
  return request<TasteImportSession>(`/profile/imports/${importId}/qr/refresh`, {
    method: "POST",
    body: {},
  });
}

export async function cancelImport(importId: string): Promise<void> {
  await request(`/profile/imports/${importId}/cancel`, {
    method: "POST",
    body: {},
  });
}

export async function requestPhoneCode(
  importId: string,
  phone: string,
  countryCode = "86",
) {
  return request(`/profile/imports/${importId}/phone/code`, {
    method: "POST",
    body: { phone, country_code: countryCode },
  });
}

export async function verifyPhoneCode(importId: string, code: string) {
  return request(`/profile/imports/${importId}/phone/verify`, {
    method: "POST",
    body: { code },
  });
}

export async function fetchQuestions(importId: string): Promise<TasteQuestions> {
  return request<TasteQuestions>(`/profile/imports/${importId}/questions`);
}

export async function submitAnswers(
  importId: string,
  answers: Array<{ question_id: string; option_id: string }>,
): Promise<TasteProfileResult> {
  return request<TasteProfileResult>(`/profile/imports/${importId}/answers`, {
    method: "POST",
    body: { answers },
  });
}
