# 噜噜抖音画像（EdgeOne）

线上地址：https://lulu-douyin-taste-zvkfpu79.edgeone.cool

评委体验页：粘贴抖音个人主页分享链接 → 云函数用 HTTP 拉最近喜欢/收藏/作品 → 生成可导出的兴趣画像卡。

独立于 `onemore-edge-agent`，不要把校园 Agent 和评委画像混在同一个 Makers 项目里。

## 凭据（只走环境变量）

抖音 Cookie、模型网关 Key **禁止**写进源码或提交 git。部署时 EdgeOne 会把本地被 gitignore 的 `.env` 注入到云函数的 `context.env`（不要用 `process.env`）。

把值写进被 gitignore 的本地 `.env`（部署时注入 `context.env`），或用 CLI：

```bash
# 推荐：Cookie 用 Base64，避免 ; = 被 dotenv 拆坏
# DOUYIN_COOKIE_B64=<base64 of Cookie header>
edgeone makers env set DOUYIN_COOKIE_B64 "<base64>"
edgeone makers env set AI_GATEWAY_API_KEY "<key>"
edgeone makers env set AI_GATEWAY_BASE_URL "https://ai-gateway.edgeone.link/v1"
edgeone makers env set AI_GATEWAY_MODEL "@makers/deepseek-v4-flash"
```

`DOUYIN_COOKIE` / `DOUYIN_COOKIE_B64` 需要包含登录态字段（`sessionid` / `sid_tt` 等）。Cookie 会过期，过期后更新 `.env` 再部署一次即可。

云函数只从 `context.env` 读取，日志不会打印 Cookie 或 API Key。

## 部署

```bash
export PATH="$HOME/.nvm/versions/node/v24.16.0/bin:$PATH"
npm install
edgeone makers deploy -n lulu-douyin-taste -t "$EDGEONE_API_TOKEN"
```

环境变量变更后需要再部署一次才会进新版本函数。
