export type EnvMap = Record<string, string | undefined>;

export const JSON_HEADERS = {
  "Content-Type": "application/json; charset=UTF-8",
  "Cache-Control": "no-store",
} as const;

export class AppError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status = 400) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export function ok<T>(data: T, meta?: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify({ data, error: null, meta: meta ?? {} }), {
    status,
    headers: JSON_HEADERS,
  });
}

export function fail(err: unknown): Response {
  if (err instanceof AppError) {
    return new Response(
      JSON.stringify({
        data: null,
        error: { code: err.code, message: err.message },
      }),
      { status: err.status, headers: JSON_HEADERS },
    );
  }
  const message = err instanceof Error ? err.message : "服务暂时不可用";
  return new Response(
    JSON.stringify({
      data: null,
      error: { code: "INTERNAL", message },
    }),
    { status: 500, headers: JSON_HEADERS },
  );
}

function decodeCookie(env: EnvMap): string {
  const direct = (env.DOUYIN_COOKIE || "").trim();
  if (direct) return direct;
  const b64 = (env.DOUYIN_COOKIE_B64 || "").trim();
  if (!b64) return "";
  try {
    return Buffer.from(b64, "base64").toString("utf8").trim();
  } catch {
    return "";
  }
}

export function cookieReady(env: EnvMap): boolean {
  const cookie = decodeCookie(env);
  if (!cookie) return false;
  return /(?:^|;\s*)(sessionid|sessionid_ss|sid_tt|sid_guard)=/.test(cookie);
}

export function requireCookie(env: EnvMap): string {
  const cookie = decodeCookie(env);
  if (!cookie) {
    throw new AppError("DOUYIN_COOKIE_MISSING", "服务暂未配置抖音登录态，请稍后再试", 503);
  }
  if (!/(?:^|;\s*)(sessionid|sessionid_ss|sid_tt|sid_guard)=/.test(cookie)) {
    throw new AppError("DOUYIN_COOKIE_INVALID", "抖音登录态无效，请更新环境变量后重试", 503);
  }
  return cookie;
}

export function llmReady(env: EnvMap): boolean {
  return Boolean((env.AI_GATEWAY_API_KEY || "").trim());
}
