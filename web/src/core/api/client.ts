/**
 * HTTP client for FastAPI — mirrors iOS APIClient envelope + Bearer + 401 gate.
 */

import {
  isSessionExpiredError,
  parseEnvelope,
  type APIErrorBody,
  type JSONValue,
} from "./envelope";
import type { SessionStore } from "./session";

export type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

export class APIClientError extends Error {
  readonly kind:
    | "invalidConfiguration"
    | "invalidResponse"
    | "transport"
    | "server"
    | "decoding"
    | "sessionExpired"
    | "offline";
  readonly status?: number;
  readonly body?: APIErrorBody;
  readonly requestId?: string | null;

  constructor(
    kind: APIClientError["kind"],
    message: string,
    opts: { status?: number; body?: APIErrorBody; requestId?: string | null } = {},
  ) {
    super(message);
    this.name = "APIClientError";
    this.kind = kind;
    this.status = opts.status;
    this.body = opts.body;
    this.requestId = opts.requestId ?? opts.body?.request_id ?? null;
  }
}

export interface APIClientOptions {
  baseURL: string;
  session: SessionStore;
  fetchImpl?: typeof fetch;
  onSessionExpired?: () => void;
  /** Dev-only default Authorization when no token (mirrors DEV_AUTH pattern). */
  devAuthHeader?: string | null;
}

export interface RequestOptions {
  method?: HttpMethod;
  query?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
  headers?: Record<string, string>;
  idempotencyKey?: string;
  auth?: boolean;
  signal?: AbortSignal;
}

function buildURL(
  baseURL: string,
  path: string,
  query?: RequestOptions["query"],
): string {
  const base = baseURL.replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  // Support a relative API base (e.g. "/onemore/api" behind a same-origin
  // reverse proxy) by resolving against the current page origin.
  const absolute = /^https?:\/\//i.test(base)
    ? `${base}${p}`
    : `${
        typeof window !== "undefined" && window.location
          ? window.location.origin
          : "http://127.0.0.1"
      }${base}${p}`;
  const url = new URL(absolute);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === null) continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

export class APIClient {
  readonly baseURL: string;
  private readonly session: SessionStore;
  private readonly fetchImpl: typeof fetch;
  private readonly onSessionExpired?: () => void;
  private readonly devAuthHeader?: string | null;
  lastRequestId: string | null = null;
  lastPath: string | null = null;

  constructor(opts: APIClientOptions) {
    this.baseURL = opts.baseURL;
    this.session = opts.session;
    this.fetchImpl = opts.fetchImpl ?? fetch.bind(globalThis);
    this.onSessionExpired = opts.onSessionExpired;
    this.devAuthHeader = opts.devAuthHeader ?? null;
  }

  async get<T>(path: string, options: Omit<RequestOptions, "method" | "body"> = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: "GET" });
  }

  async post<T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, "method" | "body"> = {},
  ): Promise<T> {
    return this.request<T>(path, { ...options, method: "POST", body });
  }

  async patch<T>(
    path: string,
    body?: unknown,
    options: Omit<RequestOptions, "method" | "body"> = {},
  ): Promise<T> {
    return this.request<T>(path, { ...options, method: "PATCH", body });
  }

  async delete<T>(path: string, options: Omit<RequestOptions, "method" | "body"> = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: "DELETE" });
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    if (!this.baseURL) {
      throw new APIClientError("invalidConfiguration", "服务地址配置无效");
    }

    const method = options.method ?? "GET";
    const url = buildURL(this.baseURL, path, options.query);
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...options.headers,
    };

    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    if (options.idempotencyKey) {
      headers["Idempotency-Key"] = options.idempotencyKey;
    }

    const useAuth = options.auth !== false;
    if (useAuth) {
      const token = this.session.getToken();
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      } else if (this.devAuthHeader) {
        headers.Authorization = this.devAuthHeader;
      }
    }

    let response: Response;
    try {
      response = await this.fetchImpl(url, {
        method,
        headers,
        body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
        signal: options.signal,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (/Failed to fetch|NetworkError|offline/i.test(message)) {
        throw new APIClientError("offline", "当前离线，写操作将在联网后恢复");
      }
      throw new APIClientError("transport", `网络连接失败：${message}`);
    }

    const requestId = response.headers.get("X-Request-ID");
    this.lastRequestId = requestId;
    this.lastPath = path;

    let json: unknown = null;
    const text = await response.text();
    if (text) {
      try {
        json = JSON.parse(text);
      } catch {
        throw new APIClientError("decoding", "数据格式不兼容：非 JSON 响应", {
          status: response.status,
          requestId,
        });
      }
    }

    // 401 on an unauthenticated call (e.g. login with a wrong password) is a
    // business error, not an expired session — let the envelope error surface.
    if (response.status === 401 && useAuth) {
      this.session.markExpired();
      this.onSessionExpired?.();
      throw new APIClientError("sessionExpired", "登录已失效，请重新认证", {
        status: 401,
        requestId,
        body: {
          code: "UNAUTHORIZED",
          message: "登录已失效，请重新认证",
        },
      });
    }

    const parsed = parseEnvelope<T>(json, response.status);
    if (!parsed.ok) {
      if (useAuth && isSessionExpiredError(parsed.error, response.status)) {
        this.session.markExpired();
        this.onSessionExpired?.();
        throw new APIClientError("sessionExpired", "登录已失效，请重新认证", {
          status: response.status,
          body: parsed.error,
          requestId,
        });
      }
      if (!response.ok) {
        throw new APIClientError("server", parsed.error.message, {
          status: response.status,
          body: parsed.error,
          requestId,
        });
      }
      throw new APIClientError("decoding", parsed.error.message, {
        status: response.status,
        body: parsed.error,
        requestId,
      });
    }

    if (!response.ok) {
      throw new APIClientError(
        "server",
        `请求失败 (${response.status})`,
        { status: response.status, requestId },
      );
    }

    return parsed.data;
  }

  /** Health probe — returns raw readiness payload when backend is up. */
  async healthReady(): Promise<JSONValue> {
    return this.get<JSONValue>("/health/ready", { auth: false });
  }

  /** Same auth resolution as request() — for WS handshakes and media fetches. */
  authToken(): string | null {
    const token = this.session.getToken();
    if (token) return token;
    if (this.devAuthHeader?.toLowerCase().startsWith("bearer ")) {
      return this.devAuthHeader.slice(7).trim();
    }
    return null;
  }

  authHeaders(): Record<string, string> {
    const token = this.authToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  /**
   * POST /media/images — raw binary body（非 multipart），对齐 iOS
   * APIClient.uploadImage：Content-Type + X-Filename (+ X-Image-Width/Height)。
   */
  async uploadImage(
    data: Blob,
    opts: {
      filename?: string;
      contentType?: string;
      width?: number;
      height?: number;
    } = {},
  ): Promise<{
    media_id: string;
    url: string;
    content_type: string;
    byte_count?: number;
    sha256?: string;
    width?: number | null;
    height?: number | null;
  }> {
    const headers: Record<string, string> = {
      "Content-Type": opts.contentType ?? data.type ?? "image/jpeg",
      "X-Filename": opts.filename ?? "web-photo.jpg",
      ...this.authHeaders(),
    };
    if (opts.width) headers["X-Image-Width"] = String(opts.width);
    if (opts.height) headers["X-Image-Height"] = String(opts.height);

    let response: Response;
    try {
      response = await this.fetchImpl(buildURL(this.baseURL, "/media/images"), {
        method: "POST",
        headers,
        body: data,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      throw new APIClientError("transport", `图片上传失败：${message}`);
    }

    if (response.status === 401) {
      this.session.markExpired();
      this.onSessionExpired?.();
      throw new APIClientError("sessionExpired", "登录已失效，请重新认证", {
        status: 401,
      });
    }

    let json: unknown = null;
    try {
      json = await response.json();
    } catch {
      throw new APIClientError("decoding", "图片上传失败：非 JSON 响应", {
        status: response.status,
      });
    }
    const parsed = parseEnvelope<{
      media_id: string;
      url: string;
      content_type: string;
      byte_count?: number;
      sha256?: string;
      width?: number | null;
      height?: number | null;
    }>(json, response.status);
    if (!parsed.ok) {
      throw new APIClientError(response.ok ? "decoding" : "server", parsed.error.message, {
        status: response.status,
        body: parsed.error,
      });
    }
    if (!response.ok) {
      throw new APIClientError("server", `图片上传失败 (${response.status})`, {
        status: response.status,
      });
    }
    return parsed.data;
  }
}

export function defaultBaseURL(): string {
  if (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_BASE) {
    return String(import.meta.env.VITE_API_BASE);
  }
  return "http://127.0.0.1:8000";
}
