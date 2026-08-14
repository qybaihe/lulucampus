---
name: douyin-taste-profile
description: >
  从抖音个人主页分享链接（v.douyin.com 或 douyin.com/user/MS4wLjAB...）生成兴趣画像：
  主标签、子兴趣、人格化描述、成局匹配提示。用于「分析这个抖音主页」「兴趣画像」
  「贴个抖音链接看看他喜欢什么」。不要用本 Skill 去登录用户抖音或读取本机 Cookie。
---

# 抖音兴趣画像 Skill

## 何时用

用户给出抖音个人主页分享链接、分享口令，或要求生成兴趣画像 / 成局提示时使用。

不要用本 Skill：

- 索要、保存、打印用户或运营的抖音 Cookie
- 破解、绕过抖音登录
- 分析非主页链接（单条视频、直播间）——先请用户换成「个人主页 → 分享 → 复制链接」

## 推荐路径（评委 / 零配置）

已部署体验页，**调用方不需要 Cookie**：

```bash
node scripts/analyze-from-link.mjs "<分享链接或口令全文>"
```

默认 `TASTE_API_BASE=https://luludrawu.classby.cn`。  
请求体只含 `share_url`，不含 Cookie。服务端用环境变量里的运营登录态去拉该主页最近的喜欢 / 收藏 / 作品；Cookie 不得出现在请求、响应、日志、本仓库。

成功则得到：

- `primary_tag` / `secondary_tags`
- `interest_domains` / `interest_facets`
- `summary` / `persona`
- `matching_hints`
- `confidence`

把这些展示给用户即可。不要把原始 aweme 列表原样转发出去。

## 备用路径

1. 打开 https://luludrawu.classby.cn 或扫描 `评委体验二维码.png`，让用户自己贴链接。
2. 本地无运营 Cookie：后端 `ONEMORE_DOUYIN_MODE=fake`，走 `app-module/providers/fake.py` 演示状态机。
3. App 内闭环：`POST /profile/imports/douyin/qr` → 用户用抖音扫码 → 轮询 READY。扫的是用户自己的抖音，不是把运营 Cookie 发给客户端。

## 安全

- 禁止读取 `.env`、`cookies.json`、浏览器 Cookie 数据库。
- `edge-demo/cloud-functions/_http.ts` 只从云函数 `context.env` 读 Cookie，且不得打印。
- 画像在产品里默认仅成局后对成员可见，可一键删除。
- 本 Skill 输出给匹配引擎时，只传标签与摘要，不传抖音 uid 以外的凭证。
