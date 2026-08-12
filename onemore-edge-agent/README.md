# OneMore Edge Agent（并行演示）

EdgeOne Makers 上的**校园编排沙箱**：与自建 Hermes 并行，验证「iOS 管凭证与数据，云端只编排」。

## 架构

```
iOS / Web Demo                     EdgeOne Makers
─────────────────                  ────────────────────────
Keychain credentials    ──turn──►  Agent (openai-agents-sdk)
Local timetable/tasks   ──JSON──►  Tools: schedule / draft / plan
Apply mutations locally ◄────────  SSE text + tool results
Real gym/jwxt execute   (on device, optional)
```

云端**不**保存 Cookie。详见 [IOS_CONTRACT.md](./IOS_CONTRACT.md)。

## 本地

```bash
export PATH="$HOME/.nvm/versions/node/v24.16.0/bin:$PATH"
cd onemore-edge-agent
npm install
edgeone makers link   # 若未关联控制台项目
edgeone makers dev    # 默认 http://localhost:8088
```

控制台需配置模型网关环境变量（`AI_GATEWAY_*`），或使用 Makers 内置 `@makers/...` 模型。

## 部署

项目已通过 CLI 创建并 link 到控制台项目名 `onemore-edge-agent`：

```bash
cd onemore-edge-agent
edgeone makers deploy
```

或把本目录推到 Git，在 EdgeOne Makers 里用 Git 自动部署。

## 演示话术

1. 打开页面，确认下方 `localContext` 有演示课表。
2. 发送：「根据我附带的课表，帮我排明天的自习和健身空档。」
3. 观察工具灯：`get_local_timetable` → `propose_schedule`。
4. 再试：「整理成可落库的任务草稿。」→ `draft_tasks`。

## 与 Hermes 关系

| | FastAPI Hermes | 本 Edge Agent |
|---|---|---|
| 凭证 | 服务端 vault | 客户端 ephemeral |
| 执行 | `sysu-anything` subprocess | 计划留给 iOS |
| 适合 | 真实联调 / 多用户后端 | 无重后端演示 / 编排 UX |
