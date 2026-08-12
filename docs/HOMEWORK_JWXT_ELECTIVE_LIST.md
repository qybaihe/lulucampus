# 作业提示词：封装 SYSU JWXT「可选选修课 / 选课列表」

把下面整段复制到**另一个 Agent 线程**执行即可。

---

## 目标

在仓库 `/Users/baihe/Documents/AnythingSYSU` 中，为 `sysu-anything` 增加 **JWXT 选修/选课列表只读能力**，复用当前已登录的 CAS / JWXT Cookie（`~/.sysu-anything/session.json` + `jwxt-session.json`），输出可被 OneMore Edge Agent 直接消费的结构化选修目录。

**本作业只做读列表 / 搜索，不要实现真正选课/退课提交。**

下游已有消费方（无需改也能先出 CLI）：

- EdgeOne：`onemore-edge-agent` 的 `search_electives` / `POST /v1/electives/search`
- 期望字段形状（对齐 `agents/_electives.ts`）：

```ts
{
  code: string;
  title: string;
  category: string;      // 通识选修 / 专业选修 / 体育选修 ...
  credits: number;
  campus?: string;
  college?: string;
  capacity?: number;
  remaining?: number;
  weekday?: string;
  time?: string;
  teacher?: string;
  tags?: string[];
  selectable?: boolean;
}
```

---

## 现状结论（已探过，别重复踩坑）

1. **AnythingSYSU 目前没有选课列表封装。**
   - 已有：`jwxt status` / `today` / `timetable` / `timetable-import` / `training-program` / `leave`
   - 文档：`skills/sysu-anything-cli/references/jwxt.md`
2. **源码落点（请在这里扩展，不要另起炉灶）：**
   - HTTP / 会话：`src/jwxt-client.ts`
     - `JWXT_BASE_URL = https://jwxt.sysu.edu.cn/jwxt`
     - 会话：`createJwxtSession` / `loadUsableJwxtSession` / `jwxt-session.json`
     - 已有 SPA menu id 范例：`jwxsd_xskbcx`（课表）、`jwxsd_qjsq`（请假）、`jwxsd_grpyfack`（培养方案）
   - CLI 路由：`src/cli.ts`（搜 `training-program` 附近仿写）
   - Help：`src/cli-help.ts`
   - Skill 文档：`skills/sysu-anything-cli/references/jwxt.md`（并同步到用户的 codex/zcode skill 副本若仓库有同步脚本）
3. **培养方案里已有「专选」计数线索**（`cli.ts` 打印 `proSelect` / `proSelectBigClass`），`getTableByProgramId` 可先挖出方案内选修课，但这是「方案要求」，不等于「选课季实时可选」。
4. **前端包 `.jwxt-schedule-app.js` 几乎只有教师侧「公选课申请」菜单名**，学生网上选课很可能在 JWXT 其它 `mk/#/...` 路由 / 其它 chunk；需要用已登录 Cookie 在浏览器里抓包，而不是只扫这个 schedule bundle。
5. 官方选课入口是 `https://jwxt.sysu.edu.cn`（企业微信也有本科生选课模块）。第三方抢课项目仅作接口线索参考，**不要抄抢课/自动提交逻辑**。

---

## 推荐实现分两阶段

### Phase A（先交付，可马上接 EdgeOne）— `jwxt electives-from-program`

从**个人培养方案课程表**提取选修类课程，做成稳定只读 CLI。

复用已有：

```bash
sysu-anything jwxt training-program --json
# 内部已有：
# POST .../undergradute/student/list
# GET  .../baseinfo/left
# GET  .../getBasicInformation
# GET  .../schemeSubmitAgg/getTableByProgramId
# GET  .../showReqGraduateCreits
```

要求：

1. 新增命令：
   ```bash
   sysu-anything jwxt electives [--keyword <k>] [--category <c>] [--json] [--state-dir <dir>]
   # 或更明确：
   sysu-anything jwxt electives program [--keyword ...] [--json]
   ```
2. 解析 `getTableByProgramId` 返回里与选修相关的表（专选/公选/通识等；注意字段名可能是 `proSelect`、`publicElective`、中文 category 等——以真实 JSON 为准）。
3. 归一化到上面的 `ElectiveCourse` 形状；`selectable` 可先标 `null/unknown` 或省略，并在 JSON 里注明 `source: "training_program"`。
4. 必须复用现有 JWXT session 加载路径；Cookie 失效时错误信息与 `jwxt status` 同类（提示 AppGateway / 重登）。

验收：

```bash
sysu-anything jwxt status
sysu-anything jwxt electives --json | head
sysu-anything jwxt electives --keyword 算法 --json
```

### Phase B（真正的「选课列表」）— `jwxt course-selection list`

用**当前用户 Cookie**对 JWXT 选课前端抓包，封装实时可选课列表。

步骤：

1. 用已有会话打开 JWXT（或把 `session.json`/`jwxt-session.json` 导入浏览器调试配置）。
2. 进入本科生选课页面，在 DevTools Network 里找出：
   - 课程分类列表接口
   - 某分类下可选课分页接口
   - 已选课程接口（只读）
3. 记录：method、path、query/body、必要 headers（尤其 `menuId` / `code=jwxsd_*` / Referer / SPA hash）。
4. 在 `jwxt-client.ts` 增加 typed client；CLI：
   ```bash
   sysu-anything jwxt course-selection status --json
   sysu-anything jwxt course-selection categories --json
   sysu-anything jwxt course-selection list --category <id|name> [--keyword ...] [--page N] [--json]
   sysu-anything jwxt course-selection mine --json   # 已选，只读
   ```
5. 输出同样归一化到 `ElectiveCourse`，并带：
   ```json
   { "source": "course_selection", "queriedAt": "...", "items": [...] }
   ```
6. **明确禁止**：默认写操作；若以后加 `elect`/`drop`，必须 `--confirm` 且本作业不做。

若选课季关闭导致列表为空：CLI 仍应成功返回结构化结果，并说明 `selectionWindow: closed|unknown`。

验收：

```bash
sysu-anything jwxt course-selection categories --json
sysu-anything jwxt course-selection list --keyword AI --json
```

---

## 工程约束（跟仓库现有风格）

- TypeScript；先改 `src/`，再 `npm run build`（或仓库惯用构建）后测 `node dist/cli.js ...` / `sysu-anything ...`。
- HTTP 走现有 `HttpSession`（注意 fake-ip / 超时；`src/http-session.ts` 已有加固）。
- 所有读写路径支持 `--state-dir`。
- Help 写入 `cli-help.ts`；`jwxt.md` 补一节「选修 / 选课列表」。
- 不要把 Cookie 打印到日志；`--json` 输出课程数据即可。
- 可选：给 OneMore Edge 加一行 bridge：
  - `plan_campus_action` 增加 `jwxt.electives` / `jwxt.course_selection.list`
  - 或文档说明 iOS 跑完 CLI 后把 JSON 塞进 `localContext.electiveCatalog`

---

## 建议工作顺序

1. `jwxt status` 确认本机 Cookie 可用。
2. 先做 Phase A（培养方案选修提取）并出 `--json`。
3. 浏览器抓包 Phase B；把原始 endpoint 样例记到 `skills/.../jwxt.md` 的「选课接口笔记」。
4. 实现 `course-selection list`，与 Phase A 字段对齐。
5. 用同一份 JSON 打 EdgeOne：
   ```bash
   curl -s -X POST https://onemore-edge-agent-ngkk9wvb.edgeone.cool/v1/electives/search \
     -H 'Content-Type: application/json' \
     -d @<(python3 -c 'import json,sys; print(json.dumps({"localContext":{"electiveCatalog": json.load(open("electives.json")["items"])}}))')
   ```

---

## 完成定义（Definition of Done）

- [ ] `sysu-anything jwxt electives --json`（Phase A）可用  
- [ ] `sysu-anything jwxt course-selection list --json`（Phase B）在选课开放或关闭时都有明确结构化响应  
- [ ] help + `jwxt.md` 已更新  
- [ ] 输出字段可直接作为 EdgeOne `localContext.electiveCatalog`  
- [ ] 无自动选课/退课  

---

## 参考文件速查

| 文件 | 作用 |
|---|---|
| `AnythingSYSU/src/jwxt-client.ts` | JWXT API / session |
| `AnythingSYSU/src/cli.ts` | 命令分发 |
| `AnythingSYSU/src/cli-help.ts` | 帮助文案 |
| `AnythingSYSU/skills/sysu-anything-cli/references/jwxt.md` | 能力文档 |
| `AnythingSYSU/src/http-session.ts` | Cookie 持久化与网络 |
| `compusone/onemore-edge-agent/agents/_electives.ts` | 下游目录 schema |
| `compusone/onemore-edge-agent/IOS_API.md` | iOS/API 消费方式 |
