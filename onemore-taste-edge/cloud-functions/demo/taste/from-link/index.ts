import { analyzeItems, mergeItems, normalizeItem } from "../../../_analyze";
import { collectRecent, extractShareUrl } from "../../../_collect";
import { AppError, fail, ok } from "../../../_http";
import { enrichWithLlm } from "../../../_llm";

type Ctx = {
  request: Request;
  env?: Record<string, string | undefined>;
};

export async function onRequestPost(context: Ctx): Promise<Response> {
  try {
    const env = context.env || {};
    let body: Record<string, unknown> = {};
    try {
      body = (await context.request.json()) as Record<string, unknown>;
    } catch {
      body = {};
    }
    const shareUrl = String(body.share_url || body.shareUrl || "").trim();
    if (!shareUrl || !extractShareUrl(shareUrl)) {
      throw new AppError(
        "DOUYIN_SHARE_URL_INVALID",
        "请粘贴抖音个人主页分享链接（v.douyin.com/...）",
        400,
      );
    }
    const likesLimit = Math.min(40, Math.max(1, Number(body.likes_limit ?? body.likesLimit ?? 30) || 30));
    const postsLimit = Math.min(30, Math.max(0, Number(body.posts_limit ?? body.postsLimit ?? 20) || 20));
    const collectsLimit = Math.min(
      40,
      Math.max(0, Number(body.collects_limit ?? body.collectsLimit ?? 30) || 30),
    );
    const useLlm = body.use_llm !== false && body.useLlm !== false;

    const bundle = await collectRecent(shareUrl, env, { likesLimit, postsLimit, collectsLimit });
    const likesItems = bundle.likes_raw.map(normalizeItem);
    const collectItems = bundle.collects_raw.map(normalizeItem);
    const postItems = bundle.posts_raw.map(normalizeItem);
    const items = mergeItems(likesItems, collectItems, postItems);
    const pages =
      Number(bundle.meta.likes.pages || 0) +
      Number(bundle.meta.collects.pages || 0) +
      Number(bundle.meta.posts.pages || 0);
    let result = analyzeItems(items, pages);
    if (useLlm) {
      result = (await enrichWithLlm(result, items, env)) as typeof result;
    }

    return ok(
      {
        source: "douyin_http_link",
        share_url: extractShareUrl(shareUrl),
        profile_url: bundle.profile_url,
        source_profile: bundle.source_profile,
        posts_count: postItems.length,
        likes_count: likesItems.length,
        collects_count: collectItems.length,
        items_used: items.length,
        collection: bundle.meta,
        result,
      },
      {
        collector: "http",
        note: "默认约 30 条最近喜欢 + 30 条收藏 + 若干作品；喜欢和收藏里的视频需公开",
      },
    );
  } catch (err) {
    return fail(err);
  }
}
