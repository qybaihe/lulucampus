# iOS API（无浏览器）

EdgeOne 后台可当作纯 API 使用；网页只是调试台。

Base URL 示例：

```text
https://onemore-edge-agent-ngkk9wvb.edgeone.cool
```

## 1. 能力发现

`GET|POST /v1/capabilities`

## 2. 选修课结构化查询（不走 LLM）

`POST /v1/electives/search`

```json
{
  "keyword": "AI",
  "campus": "珠海",
  "only_selectable": true,
  "limit": 10,
  "localContext": {
    "electiveCatalog": []
  }
}
```

`electiveCatalog` 为空时使用服务端演示目录。

## 2b. 画像匹配公选 / 选修（不走 LLM）

`POST /v1/electives/match`

```json
{
  "limit": 12,
  "min_score": 1.2,
  "localContext": {
    "tastePersona": {
      "主标签": "探索型 Builder",
      "领域": ["AI/编程", "科技数码"],
      "子兴趣": ["黑客松/AI创变", "运动康复"],
      "匹配提示": ["组队黑客松", "跑步康复"]
    },
    "electiveCatalog": []
  }
}
```

需要同时带上 `tastePersona` + `electiveCatalog`（JWXT `course-selection list` 结果）。Agent 对话里也可直接问「按我的抖音画像推荐公选」，工具名 `match_electives_to_persona`。

本地 CLI：

```bash
.venv/bin/python scripts/match_taste_to_electives.py \
  --persona artifacts/taste/persona-explorer-builder.json \
  --live --categories 公选,学院公选,专选,体育选修
```

## 3. 对话编排（SSE）

`POST /ask`（推荐）或 `POST /chat`

Headers:

```http
Content-Type: application/json
Makers-Conversation-Id: conv_ios_<uuid无连字符前缀裁剪到36内>
```

Body:

```json
{
  "message": "珠海还能选哪些 AI 相关选修？",
  "userId": "ios-device-id",
  "localContext": {
    "campusHint": "珠海校区",
    "timetable": [],
    "tasks": [],
    "electiveCatalog": []
  },
  "credentials": {}
}
```

SSE events: `text_delta` / `tool_called` / `done` / `error`.

Swift 侧用 `URLSession` 读 stream，不要打开 WebView。

## 工具限制（当前）

| 能力 | 状态 |
|---|---|
| 排程 / 任务草稿 | ✅ 纯客户端数据 |
| 选修搜索 | ✅ 客户端目录或 demo 目录 |
| 画像匹配公选 | ✅ `match_electives_to_persona` / `POST /v1/electives/match` |
| 真实选课系统「此刻可选」 | ✅ CLI `jwxt course-selection list`（iOS 同步进 catalog） |
| 培养方案 | 📱 iOS 执行 `jwxt training-program` |
| 场馆预约 | 📱 iOS 执行 gym CLI |

## 安全

- 凭证只放本轮 `credentials`，云端不落盘
- 生产环境建议再加 Agent 鉴权（JWT / App Attest），见 EdgeOne Agents Authentication 文档
