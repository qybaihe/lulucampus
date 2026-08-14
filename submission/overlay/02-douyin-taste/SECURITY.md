# 本包安全边界

## 故意不包含

- 任何 `.env`（含 EdgeOne 拉取下来的本地 env）
- `DOUYIN_COOKIE` / `DOUYIN_COOKIE_B64` 的真实值
- `douyin_like_profile/` 原始采集、Chrome Profile、`cookies.json`
- `runtime/douyin/` 扫码会话与浏览器 Cookie 库
- 模型网关 API Key

`.env.example` 里的 Cookie 字段必须保持空。部署时用 `edgeone makers env set` 注入，不要把填好的 env 传给评委。

## 分享链接 ≠ 用户 Cookie

评委粘贴的是目标主页的公开分享 URL。服务端用运营账号的登录态去读该主页最近喜欢/收藏/作品。这是「服务端代拉公开页」，不是把评委的抖音登录打进压缩包。

## 扫码路径

App 内二维码由导入会话现场生成，用户用自己的抖音 App 扫。运营 Cookie 不参与这条路径，也不进 git。
