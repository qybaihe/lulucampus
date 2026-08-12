# iOS ↔ EdgeOne Campus Orchestrator Contract

## 分工

| 端 | 职责 |
|---|---|
| **iOS App** | Keychain 凭证、本地课表/任务库、真正执行 `sysu-anything` / 校园 API、用户确认写操作 |
| **EdgeOne Agent** | 对话编排、排程建议、任务草稿、校园动作 *计划*；**不持久化 Cookie/Token** |

## 请求

`POST /chat`

Headers:

- `Content-Type: application/json`
- `Makers-Conversation-Id: <6-36 chars>`

Body:

```json
{
  "message": "根据课表帮我排明天健身",
  "userId": "ios-device-or-account-id",
  "localContext": {
    "campusHint": "珠海校区",
    "timezone": "Asia/Shanghai",
    "preferredWindows": ["18:00-21:00"],
    "timetable": [
      {
        "id": "c1",
        "title": "软件工程",
        "day": "2026-08-13",
        "start": "09:00",
        "end": "11:30",
        "location": "海琴 3 号楼"
      }
    ],
    "tasks": [
      { "id": "t1", "title": "补交离散作业", "due": "2026-08-13T21:00:00+08:00", "status": "todo" }
    ]
  },
  "credentials": {
    "session": {},
    "jwxtSession": {},
    "gymSession": {},
    "gymAuth": {}
  }
}
```

规则：

1. `credentials` **可选**；演示排程/任务可不带。
2. 即使带了凭证，也只在本轮内存使用；Agent 不得写入 Store/KV/Blob。
3. `plan_campus_action` 返回的是执行计划，由 iOS 本地跑 CLI/API 后再把结果塞进下一轮 `localContext`。

## 工具

- `get_local_timetable`
- `list_local_tasks`
- `propose_schedule`
- `draft_tasks` → 返回 `mutations.upsert`，iOS 落本地库
- `plan_campus_action` → `timetable.*` / `gym.*` 计划

## 推荐产品流

1. iOS 登录校园系统，凭证进 Keychain。
2. 后台/本地同步课表进 App DB。
3. 用户对 Agent 说话时，App 附带 `localContext`（+ 可选 ephemeral credentials）。
4. Agent 给出排程/任务草稿。
5. 用户确认后，iOS 写本地；若涉及场馆预约，iOS 执行 preview → confirm。
