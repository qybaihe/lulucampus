# 噜噜成局 · Web（工程代号 ONE MORE）

React 网页端，视觉与导航对齐 iOS「噜噜成局」；「差一个」保留为中央成局动作：

- **PC**：手机模拟器外壳（iPhone 逻辑宽 393）
- **移动端**：全屏铺满，无桌面 chrome
- **五 Tab**：`今天 / 比赛 / ⊕差一个 / 消息 / 我`
- **后端**：同一 FastAPI（`data` / `error` envelope + Bearer）

## 开发

```bash
cd web
yarn
yarn dev
```

默认连线上接口：`http://42.194.219.172/onemore/api`（与 iOS / 线上 Web 同一套 Postgres）。

若要改连本机 FastAPI，在 `web/.env` 里设 `VITE_API_BASE=http://127.0.0.1:8000`。

## 测试

```bash
yarn test
yarn build
```

## 结构

- `src/core/` — API 客户端、session、正式节点注册表、shell 断点（可单测）
- `src/screens/` — 按 Feature 分区的生产界面
- `src/styles/tokens.css` — Lulu 七色与 4pt 间距（与 design export 同源）
- `public/assets/` — stickers / lulu 资源
