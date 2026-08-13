# 噜噜成局 · ONE MORE

<p align="center">
  <strong>中文</strong>
  ·
  <a href="./README.en.md">English</a>
</p>

<p align="center">
  <img src="docs/readme-assets/app-icon.png" alt="噜噜成局 App Icon" width="120" />
  &nbsp;&nbsp;
  <img src="docs/readme-assets/lulu-ip.png" alt="噜噜 IP" width="120" />
</p>

<p align="center">
  <b>差一个，就成局。</b><br/>
  AI 不介绍人，AI 促成事。
</p>

<p align="center">
  原生 iOS（SwiftUI · iOS 17+）＋ FastAPI 业务服务 ＋ hermes 校园行动代理<br/>
  另有 React Web 对齐端 · 已针对中山大学三校区五校园深度优化
</p>

<p align="center">
  <a href="https://github.com/qybaihe/lulucampus/releases/latest"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/qybaihe/lulucampus?label=iOS%20Release&color=E8A0BF" /></a>
</p>

<p align="center">
  <a href="https://chengju.cutelulu.me"><strong>官网</strong></a>
  ·
  <a href="https://github.com/qybaihe/lulucampus/releases/download/v1.0.0/LuluCampus-1.0.0.ipa">下载 iOS App（IPA）</a>
  ·
  <a href="https://github.com/qybaihe/lulucampus/releases/latest">全部 Release 资源</a>
  ·
  <a href="https://hcnr0cwi1n15.feishu.cn/docx/HWhzdpMwAoWB3VxfypFc5Xz9nOg">产品说明文档（飞书）</a>
  ·
  <a href="https://luludrawu.classby.cn">扫码体验兴趣画像</a>
  ·
  <a href="docs/README.md">工程文档索引</a>
</p>

<p align="center">
  <img src="docs/readme-assets/hero-trio.png" alt="分项授权 · 今天 · 差一个" width="900" />
</p>

<p align="center"><sub>授权由你掌控 · hermes「今天」 · 「差一个」发起</sub></p>

---

## 下载 iOS App

第一个公开包在 GitHub Release **[v1.0.0](https://github.com/qybaihe/lulucampus/releases/tag/v1.0.0)**。

| 资源 | 说明 |
|---|---|
| **[LuluCampus-1.0.0.ipa](https://github.com/qybaihe/lulucampus/releases/download/v1.0.0/LuluCampus-1.0.0.ipa)** | 真机安装包 · iPhone · iOS 17+ · 连生产 API `lulu.classby.cn` |
| [LuluCampus-1.0.0-iphonesimulator.zip](https://github.com/qybaihe/lulucampus/releases/download/v1.0.0/LuluCampus-1.0.0-iphonesimulator.zip) | Mac + Xcode 模拟器包 |

**真机：** 用 [AltStore](https://altstore.io) 或 Sideloadly，以你自己的 Apple ID 签名后装到 iPhone。免费账号大约 7 天需要重新签一次。系统不会允许直接点开 IPA 安装。

**模拟器（Mac）：**

```bash
unzip LuluCampus-1.0.0-iphonesimulator.zip
xcrun simctl boot "iPhone 15 Pro"   # 若尚未启动
xcrun simctl install booted "ONE MORE.app"
xcrun simctl launch booted com.onemore.campus
```

本地从源码再打一份同样的包：`ios/Scripts/package_github_release.sh`

---

## 一句话定义

噜噜成局是一个能在用户授权下执行真实校园预约的 **AI 成局智能体**。  
它把主动表达的目标、课表推导出的真实共同空档和历史成局记录组合起来，匿名凑齐合适的同伴，把场地、活动与日程真正落实，然后退到幕后。

最小产品单元不是「人」，而是「局」。主场是比赛组队（缺前端、缺产品，把队伍凑齐）；日常是羽毛球、冲 DDL、校园活动同行。

**说人话，这套系统干两件事：**

1. **效率像开了挂** — 课表、作业 DDL、体育馆空场、研讨室、宣讲会、岐关车，从查到订再到写进日历，一句话搞定。
2. **干掉组队和社交里最尴尬的部分** — 你说「智能应用开发大赛，我做后端，还差前端和产品」，噜噜按赛道缺口互补撮合；凑齐了才全员确认，研讨室和日历一并落地。打球、冲 DDL、听讲座同行走同一套。事儿成了，AI 退场。

校园社交产品大多死在「想替代微信」。噜噜成局不空降社交：先有校园 AI 助手把事办完，人自然进来办事；没凑齐就不进群，座位满了才亮出这一桌的名字。入口是效率，转化是凑齐，沉淀是轻协作。

---

## 双 AI 架构

产品内并存两个物理分离、价值观相反的 AI：

| 维度 | hermes · 校园执行 AI | 噜噜 · 成局撮合 AI |
|---|---|---|
| 定位 | 私有校园执行器，服务一个人 | 跨用户成局撮合者，服务一个局 |
| 入口 | 「今天」Tab 常驻 | 「⊕ 差一个」中央入口，成局后淡出 |
| 原则 | 用得越多越好 | 用得越少越好，办完就退场 |
| 记忆 | 不持有人际记忆 | 持有共同经历，但禁止主动召回 |

<p align="center">
  <img src="docs/readme-assets/onboarding.png" alt="今天与差一个入口" width="720" />
</p>

<p align="center"><sub>左：hermes 常驻的「今天」· 右：「差一个，就说一句」发起页</sub></p>

---

## 三个 Skill

噜噜成局不是从零长出来的社交产品，而是校园 AI 助手的一次进化：先帮你高效管理校园生活，再顺手让你认识身边有意思的人。

### Skill 1 · SYSU Anything（校园行动引擎）

把中大校园系统接入 AI：教务课表与请假、雨课堂作业与签到、图书馆研讨室、体育场馆预约、宣讲会报名、组会、勤工助学、假期离返校、岐关车与校区班车、CAS 会话恢复，以及 Apple 日历 / 提醒事项同步。这是 hermes 执行链路的底座。

### Skill 2 · 软工 AI 迎新智能助手

[中山大学软件工程学院](https://hello.classby.cn) 官宣的新生校园问答：官方资料 + 三百余条在校生经验。报到入学、课程学业、宿舍食堂、办事出行，一句问完还能追问。直接用：[hello.classby.cn](https://hello.classby.cn)。它是「校园 AI 助手」底座的一部分：先能把事问清，才谈得上后面的成局。

### Skill 3 · 抖音兴趣画像

扫码或贴抖音主页链接 → 主标签 / 子兴趣 / 人格化描述 / 成局提示。默认仅成局后对成员可见，可一键删除。Cookie 不进响应与日志。

自己体验（贴抖音个人主页链接即可）：**[luludrawu.classby.cn](https://luludrawu.classby.cn)**

<p align="center">
  <img src="docs/readme-assets/taste-qr.png" alt="扫码体验抖音兴趣画像" width="180" />
</p>

<p align="center"><sub>扫码打开评委体验页 · 独立 EdgeOne 落地（`onemore-taste-edge/`）</sub></p>

### 演示高光：画像遇上公选课

抖音画像刚导完，对着 Hermes 说「帮我推荐一点适合我的公选课」——它调用校园工具 `elective_match_taste`，按画像捞课，并挂上拥挤程度。也可以问「这门课还有谁一起上」：开启社交的同学才会出现，点一下就能开两人成局频道（Hermes spark），NetID 永不返回。兴趣懂你的是画像 Skill，办事落地的是校园行动 Skill：不是陪你聊天选课，是真的认识你，再在真实课表世界里做决定。

<p align="center">
  <img src="docs/readme-assets/hermes-celebration.png" alt="问问 Hermes 与凑齐了" width="720" />
</p>

<p align="center"><sub>左：问问 Hermes · 右：凑齐了才进群</sub></p>

---

## 授权由你掌控

社交与校园能力默认不越权：课表与空闲、课程画像、同课匹配、校园预约代理均为**分项授权**，可随时在设置中单独撤回并级联清除派生数据。边界由用户点选，不是系统默认全开。

<p align="center">
  <img src="docs/readme-assets/privacy-duo.png" alt="分项授权与兴趣画像" width="720" />
</p>

<p align="center"><sub>左：授权由你掌控（四项可勾选）· 右：抖音兴趣画像，默认可一键删除</sub></p>

---

## 社交：先有场合，再凑齐进群

场合有主次：比赛组队是主场景，打球和冲 DDL 是日常高频，校园活动是最轻的第一局。无论哪一种，规则都一样：**没凑齐，就不进群。**

| 场合 | 怎么成局 |
|---|---|
| 比赛组队 | 按赛道缺口互补匹配，T2 才进比赛池；赛事牌桌展示正在招人的匿名席位与缺口；研讨室和日历落地，报名仍走官方入口 |
| 打球 / 冲 DDL | 共同空档 + 满员确认；运动搭子是攒信任的主通道，同课冲刺不依赖全校密度 |
| 活动同行 | 宣讲会、讲座免登录可发现，适合当第一局 |

<p align="center">
  <img src="docs/readme-assets/flow-main.png" alt="核心四步流程" width="900" />
</p>

<p align="center"><sub>意图卡 → 分别确认 → 「为什么是你们」与开场第一句 → 群聊系统成局卡</sub></p>

<p align="center">
  <img src="docs/readme-assets/product-quad.png" alt="活动 · 赛事详情 · 群聊 · 招募中" width="900" />
</p>

<p align="center"><sub>比赛雷达 · 「还差 N 个角色」· 局内群聊 · 噜噜招募中</sub></p>

成局状态机：`Draft → Pooling → Tentative → Confirmed → Previewed → Executed → Active → Completed`  
（之后可进入 Recurred 或 Archived；凑不齐静默解散，失败由系统承担。）

---

## 测试剧组

没有其他真实用户时，组队、凑齐、破冰演不出来。所以仓库里有六个已经注册进系统的中大测试剧组：像真人一样有课表、信任档、成局历史；开发态会按性格上课、发局、确认，不会每分钟刷屏。

<p align="center">
  <img src="docs/readme-assets/cast-row.png" alt="测试剧组六人" width="720" />
</p>

<p align="center"><sub>林予安 · 周衡 · 陈可薇 · 梁景行 · 苏晚宁 · 何屿</sub></p>

`u_demo_1`–`u_demo_6` 已核验、已授权、已开社交。也可用手机号 `13900001001`–`006`、密码 `cast-onemore` 走正式登录。

两场局故意留给真人，剧组自己不会坐满：①「周六英东羽毛球」差 1 个不鸽的；②「数模组队差建模」差一个建模（要 T2）。

开发态打开 `ONEMORE_CAST_DRIVER_ENABLED=true` 后，Celery beat 每 15 分钟走一次真实接口。真人在局内群聊说话后，在场剧组会用短句回一声（`ONEMORE_CAST_REACTIVE_CHAT_ENABLED`，与主动走动开关独立）。手动催一次：

```bash
uv run python -m onemore.scripts.tick_cast_driver
# 或 POST /internal/cast-driver/tick  （X-Admin-Token）
```

---

## 仓库结构

```text
onemore/                 FastAPI 业务服务 + Hermes 行动代理
  core/                  配置、认证、幂等、锁、HTTP
  hermes/                Action Schema、Vault、执行器、Campus MCP、Agent sidecar
  modules/               identity / profile / schedule / intent /
                         matching / gathering / trust / collab /
                         competitions / actions / notify /
                         campus / taste_profile / media / cast_driver
  tasks/                 Celery worker + beat
ios/                     原生 SwiftUI 客户端（XcodeGen）
web/                     React 19 对齐端（五 Tab · 74 节点）
onemore-edge-agent/      EdgeOne 校园 Agent 编排沙箱（凭证留端）
onemore-taste-edge/      EdgeOne 评委画像落地页（luludrawu.classby.cn）
migrations/              Alembic 迁移
openapi/                 前端契约 OpenAPI
fixtures/                赛事快照等可重复摄取数据
data/                    中大校园参考包、活动数据
assets/ip/               噜噜 IP、测试剧组头像
docs/                    产品与工程文档（含 README 配图）
tests/                   pytest 全量用例
```

---

## 快速启动

### 后端

```bash
uv sync --dev
cp .env.example .env
# 编辑 .env：按需填写 ONEMORE_VAULT_MASTER_KEY / ONEMORE_TASTE_LLM_API_KEY 等
uv run alembic upgrade head
uv run onemore-seed
uv run uvicorn onemore.main:app --reload
```

- Swagger：<http://127.0.0.1:8000/docs>
- OpenAPI：<http://127.0.0.1:8000/openapi.json>
- 就绪检查：<http://127.0.0.1:8000/health/ready>

本地演示身份：

```http
X-User-ID: u_demo_1
# 或
Authorization: Bearer dev:u_demo_1
```

Hermes Agent sidecar（公选课等自然语言走 DeepSeek，失败回退关键词规则）：

```bash
make stack          # API :8000 + Hermes Agent :8642
# 或分开启动：
make dev
make hermes
```

`.env` 里保持 `ONEMORE_HERMES_MODE=real`、`ONEMORE_HERMES_AGENT_MODE=sidecar`。单元测试仍强制 `fake` / `off`。

### Docker

```bash
docker compose up --build   # api + worker + beat + hermes-agent + postgres + redis
docker compose exec api uv run onemore-seed
```

生产编排见 `docker-compose.prod.yml`（含 `hermes-agent` sidecar）。

### iOS

```bash
cd ios
./Scripts/generate.sh
./Scripts/build.sh
./Scripts/test.sh
./Scripts/run.sh
```

要求：Xcode 15+、iOS 17+ Simulator。工程由 XcodeGen 生成，**不使用 WKWebView**。

### Web

```bash
cd web && yarn && yarn dev
```

PC 以手机框呈现，移动端全宽；与 iOS 共用同一 FastAPI 与响应契约。公开画像体验页也可走 `web` 的 `/demo/taste` 或独立仓库目录 `onemore-taste-edge/`。

---

## Hermes 模式

默认 `ONEMORE_HERMES_MODE=real`：走 `sysu-anything` 查课表/场馆，并启动 Hermes Agent sidecar。

本地无校园 CLI 时，`/health/ready` 会报 `hermes_cli: missing`，接口仍可启动；评委/单测继续用 `ONEMORE_HERMES_MODE=fake`。

```bash
ONEMORE_HERMES_MODE=real
ONEMORE_HERMES_AGENT_MODE=sidecar
ONEMORE_SYSU_CLI="$HOME/.local/bin/sysu-anything"
ONEMORE_VAULT_MASTER_KEY="$(openssl rand -hex 32)"
```

执行链路（确定性，LLM 不拼接命令）：

```text
自然语言 → LLM 意图编译（只产出结构）
  → Action Schema 白名单 / Campus MCP 工具
  → 七道校验（白名单 / 参数 / 授权 / 信任 / 全员确认 / 幂等）
  → argv 转译（shell=False）
  → 用户级串行锁 · 限流 · 熔断
  → 加密 Vault 临时挂载
  → sysu-anything CLI
  → 结果归一化后销毁挂载
```

写操作铁律：**预览 → 确认 → 执行**；客户端传来的 `confirm=true` 一律丢弃。

---

## 业务模块

| 模块 | 能力 |
|---|---|
| `identity` | 异步扫码会话、身份事实、分项授权、撤回级联清除 |
| `profile` | 课程映射、能力向量、跨专业信号、自述标签 |
| `schedule` | 课表缓存、空档 ETL、隐私交集、校区可达性 |
| `intent` | 强类型意图编译、两轮澄清、匿名发布与撤回 |
| `matching` | 相似搭子与互补组队、共同经历加权、冲突校验 |
| `gathering` | 单入口状态机、多人确认、改约、补位、复局、举报 |
| `trust` | T0–T4 自动计算、统一解锁、自有进度、申诉 |
| `collab` | 局内群聊、搭子关系、共同经历、共同目标、AI 退场 |
| `competitions` | 原子快照摄取、核验闸门、去重、能力映射、过期下架 |
| `actions` | 预览快照、服务端确认、幂等执行、失败归一化、回滚 |
| `notify` | 事务通知、分类收件箱、日历 DTO、群聊合并推送、提醒任务 |
| `campus` | 校园工具聚合 + 公选课画像匹配 + 同课/同场社交提示（只经 Hermes / MCP 白名单） |
| `taste_profile` | 抖音扫码 / 分享链接导入、规则画像、可选 LLM 人格重述、公开评委入口 |
| `cast_driver` | 测试剧组按课表与性格走动；真人发言后短句回应 |

附加：T4 主理人台、账号屏蔽、数据导出与注销闭环。

---

## 完成度（冻结基线 · 2026-08-12，此后持续增量）

**不是接近完成，是全部完成。** 全程不用一个 Mock——每个接口、每一屏、每条数据都是真的。

| 侧 | 证据 |
|---|---|
| 后端 | 11+ 业务模块 · pytest 全绿 · mypy 零错误 · OpenAPI 118 paths / 204 schemas · Alembic → 0019 |
| iOS | 原生 SwiftUI · 74 正式节点 · 72 unit + 21 UI · 36 画板还原 · major 缺陷为零 |
| Web | React 19 · 五 Tab / 74 节点与 iOS 对齐 · 公开画像体验页 |
| 数据 | 比赛雷达 24 条人工核验赛事 · 中大参考包 v1.1（5 校区 / 76 地点 / 137 场馆） |

官网：[chengju.cutelulu.me](https://chengju.cutelulu.me)  
也欢迎来拷打代码：[github.com/qybaihe/lulucampus](https://github.com/qybaihe/lulucampus)

更完整的产品叙事、赛题对应、创新点与延展路线，见飞书文档：  
**[噜噜成局 · ONE MORE 产品说明文档](https://hcnr0cwi1n15.feishu.cn/docx/HWhzdpMwAoWB3VxfypFc5Xz9nOg)**

---

## 测试与检查

```bash
uv run ruff check onemore tests migrations
uv run mypy onemore
uv run pytest
```

赛事与校园参考数据：

```bash
make competitions-validate && make competitions-ingest
make sysu-reference-build && make sysu-reference-validate
```

后台任务：

```bash
uv run celery -A onemore.tasks.celery_app:celery_app worker -l INFO
uv run celery -A onemore.tasks.celery_app:celery_app beat -l INFO
```

---

## 产品红线（服务端强制）

- `Enrollment` 不含成绩字段
- 空档交集 DTO 不含 `user_id`
- 没有查询他人信任等级的路由
- 没有用户搜索、好友申请或关系推荐路由
- `SharedExperience` 不含评价 / 印象 / 标签 / 备注
- `Message` 不含已读字段
- Pooling 视图不返回报名人数或报名者
- 红灯校园动作没有 ActionName，也没有 CLI 映射
- 记忆召回必须携带 intent / gathering / goal 上下文
- 不存在基于共同经历的主动召回通知

---

## 文档

| 文档 | 说明 |
|---|---|
| [README (English)](README.en.md) | English product + engineering README |
| [飞书 · 产品说明](https://hcnr0cwi1n15.feishu.cn/docx/HWhzdpMwAoWB3VxfypFc5Xz9nOg) | 对外产品文档（含配图） |
| [docs/README.md](docs/README.md) | 工程文档索引 |
| [docs/00_产品方案_V2.1.md](docs/00_产品方案_V2.1.md) | V2.1 产品方案 |
| [docs/01_iOS客户端开发指南.md](docs/01_iOS客户端开发指南.md) | iOS 开发指南 |
| [docs/02_后端服务开发指南.md](docs/02_后端服务开发指南.md) | 后端开发指南 |
| [docs/03_行动代理与Hermes设计.md](docs/03_行动代理与Hermes设计.md) | Hermes 设计 |
| [ios/README.md](ios/README.md) | iOS 交付说明 |
| [web/README.md](web/README.md) | Web 对齐端说明 |
| [onemore-taste-edge/README.md](onemore-taste-edge/README.md) | 评委画像 EdgeOne 落地 |

---

## 创新点（摘要）

- **零填表冷启动** — Day 1 画像来自培养方案与选课，不是自述标签  
- **真实共同空档** — 课表交集计算，只输出交集  
- **执行闭环** — 多人确认后预约落到校园系统  
- **静默成局** — 未满员不可见，凑不齐静默解散  
- **把自己删掉的 AI** — 成局后退场，优化「事成」而非停留时长  
- **授权由你掌控** — 分项勾选、随时撤回、级联清除  
- **画像遇上公选课** — 抖音兴趣 × 真实课表拥挤度，两套 Skill 接上  
- **安全即架构** — LLM 不碰命令行；红灯能力不可达；凭证按人加密隔离  

---

## License

本仓库用于产品演示与答辩；未单独声明许可证前，保留所有权利。
