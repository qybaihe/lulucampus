import { cookieReady, fail, llmReady, ok } from "../../../_http";

export async function onRequestGet(context: { env?: Record<string, string | undefined> }): Promise<Response> {
  try {
    const env = context.env || {};
    const ready = cookieReady(env);
    return ok({
      enabled: ready,
      douyin_import_enabled: ready,
      mode: "http",
      message: ready
        ? "支持分享链接 HTTP 导入（最近喜欢 + 作品，无需扫码滚动）"
        : "服务暂未就绪，请稍后再试。",
      http_link_import_ready: ready,
      llm_ready: llmReady(env),
    });
  } catch (err) {
    return fail(err);
  }
}

export async function onRequestPost(context: { env?: Record<string, string | undefined> }): Promise<Response> {
  return onRequestGet(context);
}
