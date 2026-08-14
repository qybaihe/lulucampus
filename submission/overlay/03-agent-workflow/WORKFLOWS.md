# 四条核心 Workflow

## 1. Hermes 校园执行

```text
自然语言
  → LLM 只产出结构（不拼命令行）
  → Action Schema 白名单（capabilities.json，18 个动作）
  → Campus MCP 工具（campus_mcp.py，15 个；不含 --confirm）
  → 七道校验：白名单 / 参数 / 授权 / 信任 / 全员确认 / 幂等 / 限流
  → argv 转译，shell=False
  → 用户级串行锁 · Vault 临时挂载
  → sysu-anything CLI（见 01-Skill）
  → 结果归一化，销毁挂载
```

写操作：`/actions/preview` → 用户确认 → `/actions/execute`。  
红灯能力（代报名、查他人成绩等）没有 ActionName，也没有 CLI 映射。

## 2. 成局状态机（噜噜）

```text
Draft → Pooling → Tentative → Confirmed
     → Previewed → Executed → Active → Completed
     → Recurred | Archived
凑不齐 → Dissolved（静默解散，失败由系统承担）
```

规则：没凑齐不进群；空档 DTO 不含 `user_id`；Pooling 视图不返回报名者名单。代码在 `workflows/gathering/`。

## 3. 画像遇上公选课

```text
抖音主页分享链接或 App 内扫码
  → Skill 2 产出画像（标签 / persona / matching_hints）
  → Hermes 工具 elective_match_taste
  → 真实课表拥挤度
  → 可选：同课同学（需开启社交；NetID 永不返回）
```

画像默认仅成局后对成员可见，可一键删除。Cookie 不进响应与日志。

## 4. EdgeOne 编排沙箱（凭证留端）

`edge-agent/agents/_tools.ts` 工具：

- `get_local_timetable`
- `propose_schedule`
- `draft_tasks` / `list_local_tasks`
- `search_electives`
- `match_electives_to_persona`
- `plan_campus_action`（只出计划，不在云端执行校园写操作）

客户端附带 `localContext`；即使带了 ephemeral 凭证，也只在本轮内存使用，禁止写入 Store/KV。真实预约仍走 Hermes + Skill 1。

## 赛事组队（主场景）

`competition-discovery` 核验快照 → `fixtures` 入库 → 比赛雷达缺口牌桌。  
报名只跳转官方入口，无代提交（红灯）。组队要 T2；未核验线索永不进产品。
