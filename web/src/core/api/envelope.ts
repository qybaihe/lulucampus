/**
 * FastAPI envelope helpers — mirrors iOS APIModels.swift
 * Response: { data, meta? } | { error: { code, message, details?, request_id? } }
 */

export type JSONValue =
  | string
  | number
  | boolean
  | null
  | JSONValue[]
  | { [key: string]: JSONValue };

export interface APIErrorBody {
  code: string;
  message: string;
  details?: Record<string, JSONValue>;
  request_id?: string | null;
  requestId?: string | null;
}

export interface APIEnvelope<T> {
  data: T;
  meta?: Record<string, JSONValue>;
}

export interface APIErrorEnvelope {
  error: APIErrorBody;
}

export type ParseResult<T> =
  | { ok: true; data: T; meta: Record<string, JSONValue> }
  | { ok: false; error: APIErrorBody; status?: number };

export function normalizeErrorBody(raw: APIErrorBody): APIErrorBody {
  return {
    code: raw.code ?? "UNKNOWN",
    message: raw.message ?? "未知错误",
    details: raw.details ?? {},
    request_id: raw.request_id ?? raw.requestId ?? null,
  };
}

/**
 * Parse a JSON body already decoded from the network.
 * Does not invent business success — empty/missing data is an error.
 */
export function parseEnvelope<T = unknown>(
  body: unknown,
  status?: number,
): ParseResult<T> {
  if (body == null || typeof body !== "object") {
    return {
      ok: false,
      status,
      error: {
        code: "INVALID_RESPONSE",
        message: "服务响应无效",
        details: {},
      },
    };
  }

  const obj = body as Record<string, unknown>;

  if ("error" in obj && obj.error != null && typeof obj.error === "object") {
    return {
      ok: false,
      status,
      error: normalizeErrorBody(obj.error as APIErrorBody),
    };
  }

  if (!("data" in obj)) {
    return {
      ok: false,
      status,
      error: {
        code: "INVALID_ENVELOPE",
        message: "响应缺少 data 字段",
        details: {},
      },
    };
  }

  return {
    ok: true,
    data: obj.data as T,
    meta: (obj.meta as Record<string, JSONValue>) ?? {},
  };
}

export function isSessionExpiredError(error: APIErrorBody, status?: number): boolean {
  if (status === 401) return true;
  const code = (error.code ?? "").toUpperCase();
  return (
    code === "UNAUTHORIZED" ||
    code === "SESSION_EXPIRED" ||
    code === "TOKEN_EXPIRED" ||
    code === "NOT_AUTHENTICATED"
  );
}
