#!/usr/bin/env node
/**
 * 调用已部署的抖音画像接口。本机不读取、不需要 Cookie。
 * 用法: node scripts/analyze-from-link.mjs "https://v.douyin.com/xxxx/"
 */
const base = (process.env.TASTE_API_BASE || "https://luludrawu.classby.cn").replace(/\/$/, "");
const share = process.argv.slice(2).join(" ").trim();

if (!share) {
  console.error("用法: node scripts/analyze-from-link.mjs '<抖音主页分享链接或口令>'");
  process.exit(1);
}

const res = await fetch(`${base}/demo/taste/from-link`, {
  method: "POST",
  headers: { Accept: "application/json", "Content-Type": "application/json" },
  body: JSON.stringify({
    share_url: share,
    likes_limit: 30,
    posts_limit: 20,
    collects_limit: 30,
    use_llm: true,
  }),
});

const json = await res.json().catch(() => null);
if (!res.ok || !json || json.error) {
  const msg = json?.error?.message || `HTTP ${res.status}`;
  console.error(msg);
  process.exit(1);
}

const data = json.data ?? json;
const result = data.result ?? data;
process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
