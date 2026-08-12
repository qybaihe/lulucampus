# 11 · iOS 前后端联调现状与范围

> 快照时间：2026-08-11  
> 工作区：`/Users/baihe/Documents/compusone`  
> 本文 1–10 节记录 2026-08-11 实现前快照。**2026-08-12 更新：原生 iOS 工程、真实 API 联调、57 帧动效与测试证据已经完成；最终事实以第 11 节和 `TEST_RESULTS.md` 为准。**

## 1. 一句话结论

现在已经有 **可启动的 FastAPI 后端、固定 OpenAPI、已核验赛事与中大静态数据、返回的 36 状态移动端原型、选定的粉发女孩 57 帧动作包**；但 **iOS 工程仍为空**，设计稿只覆盖 74 个正式节点中的 34 个，后端当前也有 1 个测试回归和 1 条演示赛事污染。下一任务应从“修复基线 → 原生 SwiftUI 还原 → 真实 API 联调 → 动效/系统能力 → 独立视觉与测试闭环”连续执行。

## 2. 当前资产总表

| 层 | 当前状态 | 已有证据 | 下一任务动作 |
|---|---|---|---|
| 产品规格 | 已冻结为 V2.1、F1–F31、74 节点 | `docs/00_产品方案_V2.1.md`、`docs/01_iOS客户端开发指南.md`、`docs/05_iOS设计交接提示词.md` | 作为功能与红线事实源 |
| 返回设计稿 | 已复制、解压、校验 | `design/received/2026-08-11-one-more-mobile-prototype/` | 1:1 还原 36 状态；同风格补齐 40 节点 |
| 设计运行检查 | 36/36 状态可进入，核心内存交互可点击 | `design/.../SOURCE_MANIFEST.json`、`output/playwright/one-more-design-return/` | 转成原生 SwiftUI，不使用 WKWebView |
| 后端服务 | FastAPI 可启动，健康检查通过 | `onemore/`、`docs/06_后端实现与前端联调.md` | 先修回归，再作为唯一业务后端 |
| API 契约 | OpenAPI 3.1，85 paths / 93 operations / 124 schemas | `openapi/onemore.openapi.json` | 生成或手写强类型 Swift API Client |
| 比赛雷达 | V1.1 快照 24 条通过验证 | `fixtures/competition_snapshot_2026-08-11_v1.1.json` | 前端只消费 API；清掉可见 demo 赛事 |
| 中大静态包 | 5 校区、76 地点、137 场馆、22 交通记录、11 节次，验证通过 | `data/reference/sysu/` | 版本化打包/服务，不重新联网抓取 |
| 最终 IP | 粉发女孩已选定，57 帧、9 状态、14 条事件规则 | `assets/ip/selected/aiia-pink-girl-business-v1/` | 转入 Asset Catalog 并实现业务状态播放器 |
| iOS 工程 | **尚不存在** | 未发现 `.swift`、`.xcodeproj`、`.xcworkspace` | 在 `ios/` 从零初始化 SwiftUI 工程 |
| 本机工具链 | 可用 | Xcode 26.0.1、Swift 6.2、XcodeGen、iOS 17/18/26 Simulator | 新任务内重新探测 XcodeBuildMCP；否则用 xcodebuild |
| 版本控制 | 当前目录不是 Git 仓库 | `git status` 返回非仓库 | 开始大量改动前建立可回滚基线或明确备份策略 |

## 3. 返回设计稿验收

### 3.1 固定目录

```text
/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/
├── README.md
├── SOURCE_MANIFEST.json
├── SCREEN_CONTACT_SHEET.png
├── raw/Mobile app scope questionnaire.zip
├── export/ONE MORE 原型.dc.html
├── export/ds/_ds_bundle.css
├── export/support.js
├── export/assets/azou.png
├── export/assets/azou-alt.png
└── screens/*.png                      # 36 张 402×874 画板
```

压缩包 SHA-256：

```text
6e6630b369601f4ad517648521af3357772c74fba183775e70fdfc9536df53cb
```

### 3.2 视觉语言

- 画板：`402 × 874`；
- 页面底色：`#010001`；
- 青色主操作：`#00FFE1`，深青色前景；
- 洋红强调：`#FF4FD3`；
- 半透明玻璃面、细描边、20/32 pt 圆角、胶囊按钮；
- iOS 使用 PingFang/SF 系统字体，不从网页 CDN 打包字体；
- 原型示例中的比赛数、日期、人数与状态是 mock，不能进入运行版。

### 3.3 覆盖结论

- 返回稿：36 个交互状态；
- 对正式 74 节点的覆盖：34；
- 返回稿额外组合态：`B12.2 牌桌`、`MSG 消息`；
- 未单独出图的正式节点：40。

未出图节点：

```text
A1 A8
B2 B3 B3.1 B6 B6.1 B8 B9 B10 B11
C2 C3
D3.1 D3.2 D3.3 D3.4
E2 E4 E8 E11 E12 E13 E15
M2 M4 M5 M6 M7 M8 M9 M10
O1 O2 O3 O4
G1 G3 G4 G5
```

### 3.4 原型实测

本地 HTTP 加载返回 `200`，没有 console error/page error。实测通过：

1. 36 个状态逐项切换；
2. 赛事牌桌入座 `3/4 → 4/4`；
3. 意图输入 → 两轮澄清 → 意图卡 → 招募；
4. 多人确认 `2/4 → 4/4`；
5. 执行结果 → 日历权限模拟 → 已加入日历；
6. 群聊发送文本。

这只证明返回稿交互脚本正常，尚未证明 iOS 或后端联调。

## 4. 最终 IP 资产结论

唯一生产根目录：

```text
/Users/baihe/Documents/compusone/assets/ip/selected/aiia-pink-girl-business-v1/
```

已验收：

- `validation.json.ok = true`；
- `qa/retina-validation.json.ok = true`；
- 57 张透明 PNG，单帧 `192 × 208`；
- 标准图集 `1536 × 1872`，Retina 图集 `3072 × 3744`；
- 九个业务状态及逐帧时长齐全；
- 14 条业务事件序列；
- 支持优先级抢占、成功/失败不可中断、去抖、后台暂停、离屏暂停、Reduce Motion；
- 透明残留与未使用图集单元检查通过。

返回原型的十处图片实际引用 `export/assets/azou.png`，它是橙色团子占位图。`export/assets/azou-alt.png` 与最终 `base-transparent.png` SHA-256 相同，但最终 App 仍须从选定资产根目录导入，避免设计稿副本与生产资源分叉。

业务事件必须按 `motion-contract.json` 映射，例如：

| 事件 | 动画序列 |
|---|---|
| 首次可见 | `appear → greeting → idle` |
| 意图聚焦/编译 | `closed-eye-sensing` |
| 意图发布/开始撮合 | `executing → idle` |
| 等待确认/授权 | `waiting-confirmation` |
| 执行成功 | `success → exit` |
| 执行失败 | `needs-adjustment → waiting-confirmation` |
| 真人双向对话开始 | `exit` |

## 5. 后端现状

### 5.1 可运行能力

服务入口：

```text
/Users/baihe/Documents/compusone/onemore/main.py
```

固定契约：

```text
/Users/baihe/Documents/compusone/openapi/onemore.openapi.json
```

当前契约规模：

```text
OpenAPI 3.1.0
85 paths
93 operations
124 schemas
```

主要业务组已存在：身份认证、画像、课表与空档、校园工具、赛事、意图、匹配、局状态机、信任、行动预览/执行、通知、群聊/关系/共同目标、T4 主理人、账号与隐私、抖音兴趣画像导入。

2026-08-11 本地冒烟：

- `/health/live`：200；
- `/health/ready`：`database=ok`、`redis=ok`、`hermes_mode=fake`；
- `/today/summary`：成功；
- `/competitions`：成功，但当前返回 25 条，见已知问题。

### 5.2 当前自动检查不是全绿

```text
pytest: 50 passed, 1 failed
ruff: 1 error
mypy: 1 error
比赛快照验证: PASS（24）
中大静态包验证: PASS
```

三项代码检查都指向同一处：

```text
/Users/baihe/Documents/compusone/onemore/modules/taste_profile/api.py:219-233
```

`verify_mobile_login()` 调用 `_wait_for_status()` 后缺少返回值，导致：

- `POST /profile/imports/{import_id}/verify` 触发响应模型校验错误；
- `ruff F841`（`session` 未使用）；
- `mypy Missing return statement`；
- `tests/test_douyin_taste_import.py::test_separate_qr_and_mobile_verification_apis` 失败。

新任务第一步应恢复正确的 `APIResponse[LoginVerificationView]`，并让 pytest/ruff/mypy 全绿后再接 iOS。

### 5.3 比赛库有一条演示数据污染

生产候选快照本身通过验证，共 24 条：

```text
snapshot_version = competition-radar-cn-v1.1-2026-08-11
```

当前开发数据库另有一条种子演示赛事：

```text
external_key = demo-innovation-2026
snapshot_version = demo-2026-08-11
name = 2026 校园创新应用大赛
```

因此 `/competitions` 目前返回 25 条。iOS 不应写死“21 场”，服务端也不应把 demo 记录混入生产列表。应在服务端摄取/查询或 seed 策略中实现明确隔离，然后增加测试保证生产快照导入后只返回 24 条已核验、可行动赛事。

### 5.4 中大静态包已准备，但缺少明确分发契约

`/Users/baihe/Documents/compusone/data/reference/sysu/` 已有版本化、带校验和的数据包：

- 5 个校区；
- 21 个别名；
- 76 个地点；
- 137 个场馆/房间；
- 22 条交通记录与 10 个方向通勤矩阵；
- 6 个方向含用户确认的典型通勤时长；
- 2026–2027 校历；
- 2026 秋季 11 节标准节次；
- 468 条证据审计；
- 13 个已记录缺口。

现有 OpenAPI 只暴露实时场馆查询和课表等业务接口，尚无静态目录的版本/清单/地点搜索/交通/校历接口。新任务应明确采用以下一种可验证方案，且不得重新在线抓取：

1. **推荐**：将 `manifest.json` 与必要 JSON 放入 iOS Bundle，构建 `StaticReferenceRepository`；后端只提供实时空闲、预约和用户态数据；
2. 或增加只读 `/reference/*` 版本化接口，由服务端从固定 JSON/数据库返回，并用 ETag/版本号缓存。

两种方案都必须保留 `bundle_version` 和校验和，更新时整包切换，不能让 App 混用不同版本。

## 6. 设计状态到后端接口的主映射

| 返回稿状态 | 主要真实接口/系统能力 |
|---|---|
| A3 扫码认证 | `POST /auth/session`、`GET /auth/session/{id}`、cancel |
| A4 分项授权 | `POST /auth/grants` |
| A5/A6 画像 | `POST /profile/init`、`GET /profile/me`、`PATCH /profile/tags` |
| A7 社交开关 | `PATCH /me/privacy` |
| B1 今天 | `GET /today/summary`、`GET /notifications` |
| B4/B4.1 | `GET /assignments`、`GET /assignments/{id}` |
| B5/B5.1 | `GET /venues/gym/available`、意图/行动链 |
| B7/B7.1 | `GET /events`、`GET /events/{id}`、官方 URL |
| B12/B12.1 | `GET /competitions`、`GET /competitions/{id}` |
| C1/C4/B12.2 | `GET /gatherings/open`、detail、join、Universal Link |
| D1–D4 | `POST /intent/compile`、get/patch/publish/delete |
| E1 | `GET /gatherings/mine`、`GET /relations` |
| E3 | gathering detail/confirm/time-options/reschedule/leave |
| E5/E6 | `POST /actions/preview`、execute、`GET /actions/{id}`、EventKit |
| E7/E14 | channel messages、mention-azou、WebSocket、系统媒体权限 |
| E9/E10 | gathering complete/recur |
| E16/E17 | relations detail/recur/goals/delete |
| M1/M3 | auth/profile/trust、appeal |
| G2 | ShareLink/UIActivityViewController + Universal Link |

客户端必须以 `status` 和服务端字段驱动页面，不从按钮点击本地伪造局状态、确认人数、预约成功或赛事资格。

## 7. 接口/产品仍需核对的缺口

这些不是开始开发的阻塞项，但必须在联调阶段逐项关闭：

1. `O4` 要求模板编辑/复制/停用，现有 OpenAPI 只有模板列表、创建、实例化；
2. `M9` 要求查看申诉状态/结果，当前只有 `POST /trust/appeal`；
3. `E14` 支持 `text/image/location` 类型，但没有文件上传/签名 URL 契约；需要明确图片存储和位置 payload 格式；
4. `M7` 的通知分类开关没有服务端偏好接口；可先明确哪些是系统本地设置、哪些需要跨设备同步；
5. 74 节点之外的抖音兴趣画像导入已有 13 个 OpenAPI operation，但返回设计稿没有对应画板；需要按同一视觉系统补做“开始、二维码、进度、问题、结果、删除/重试”状态；
6. `C4` 是 Web 落地页，iOS 只能实现 Universal Link 接收；Web 落地页本体仍需独立实现或确认已有站点；
7. 正式 APNs、Associated Domains、隐私文案、Bundle ID、签名 Team、后台模式与生产 Base URL 均未配置。

## 8. 新任务的实施顺序

### Gate 0 · 基线恢复

1. 修复 `taste_profile` 返回值回归；
2. 隔离 demo 赛事，确认 API 只返回 24 条生产快照；
3. 全量运行 pytest/ruff/mypy、数据验证；
4. 导出并对比 OpenAPI；
5. 建立可回滚基线。

### Gate 1 · 设计还原

1. 在 `ios/` 初始化 iOS 17+ SwiftUI/XcodeGen 工程；
2. 建立颜色、排版、圆角、玻璃面、按钮、卡片和导航 Tokens；
3. 先还原 36 个返回画板，保持 `402×874` 层级与 CTA；
4. 导出 Simulator 截图与 `screens/*.png` 对照；
5. 由独立视觉复核任务判定无 major drift 后再接真实业务。

### Gate 2 · 补齐设计节点

按 `docs/01_iOS客户端开发指南.md` 补齐 40 节点和全局状态，保持同一视觉系统；同时补充抖音画像导入状态。

### Gate 3 · 真实联调

1. 强类型 API Client、统一 envelope/error/request-id；
2. Dev Token/扫码 Bearer 切换；
3. 赛事、意图、成局、确认、行动、群聊/WS、关系、信任、主理人逐链路联调；
4. 禁止运行版回退到 hard-coded happy path；
5. 校园静态包离线消费，实时空闲与预约走后端。

### Gate 4 · IP 动效与系统能力

1. 导入 57 帧和动作契约；
2. 事件状态机、优先级、抢占、去抖、后台/离屏暂停；
3. Reduce Motion 静态帧；
4. EventKit、APNs、语音、照片、位置、分享、Universal Link；
5. 主线程不做图片解码，列表滚动和动画保持流畅。

### Gate 5 · 独立测试闭环

1. Swift 单测、ViewModel/Repository 测试；
2. 关键 UI Tests；
3. 后端 51+ 测试全绿；
4. Simulator 构建、启动、日志、截图与动效录屏；
5. 36 返回画板逐屏对照、74 节点可达性审计、所有 CTA 审计；
6. 发现问题后修复并重跑，直到通过或记录真实外部阻塞。

## 9. 本地启动与验证命令

后端：

```bash
cd /Users/baihe/Documents/compusone
uv sync --dev
uv run alembic upgrade head
uv run onemore-seed
uv run uvicorn onemore.main:app --host 127.0.0.1 --port 8000
```

开发认证：

```http
X-User-ID: u_demo_1
```

或：

```http
Authorization: Bearer dev:u_demo_1
```

验证：

```bash
cd /Users/baihe/Documents/compusone
uv run ruff check onemore tests migrations
uv run mypy onemore
uv run pytest -o addopts='' -ra
uv run python scripts/validate_competition_snapshot.py fixtures/competition_snapshot_2026-08-11_v1.1.json
uv run python scripts/validate_sysu_reference.py
uv run onemore-export-openapi
```

设计稿：

```bash
cd "/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/export"
python3 -m http.server 8765 --bind 127.0.0.1
```

## 10. 交付判定

“App 完成”至少同时满足：

- 原生 SwiftUI，不是 WebView 包壳；
- 36 个返回画板完成视觉对照；
- 74 个正式节点均有映射且可达；
- 返回稿额外 `B12.2/MSG` 可达；
- 后端主链路使用真实 API；
- 比赛列表为 24 条生产候选且不含 demo；
- 粉发女孩是唯一阿凑形象，九个状态可由真实事件触发；
- 所有 CTA 有行为，无死按钮；
- 权限拒绝、离线、错误、加载、空态与重复点击可恢复；
- 后端 pytest/ruff/mypy 与数据验证全绿；
- iOS build/test/run 通过并有 Simulator 截图、日志、动效证据；
- 独立视觉复核与独立测试复核均已产出文件并关闭高优先级问题。

## 11. 2026-08-12 完整实现更新

原“iOS 工程仍为空”的基线已关闭。当前交付位于 `/Users/baihe/Documents/compusone/ios`：

- 原生 SwiftUI / iOS 17+ / XcodeGen；正式 registry 为 74 个定义、69 个唯一生产 runtime identifier，另保留 B12.2 与 MSG；
- 36 个返回画板由独立 Debug fidelity harness 捕获；正式节点通过生产路由、服务端状态或系统事件触发，不再声称 74+2 均可 direct launch；
- FastAPI 154/154 pytest、ruff、106 个 mypy source files、空库迁移至 `20260811_0017`、赛事与 SYSU 数据验证全绿；
- `/competitions` 使用 24 条 V1.1 生产候选且不含 demo；冻结 OpenAPI 为 118 paths / 204 schemas；
- Swift 真实 API 流覆盖 compile → publish → Pooling detail → leave，另有 15 项 Python live smoke；
- 唯一阿凑为 AIIA 粉发女孩，57 帧、9 状态、14 业务事件，含前后台/离屏/抢占/Reduce Motion 和两段录屏；
- EventKit、APNs、Share、custom/universal deep link、Voice、Image、Location 均按需接入；
- 72 项 iOS unit 与 21 个 UI test methods 全绿；全量 UI 使用 iPhone 15 / iOS 17，iPhone SE / 15 Pro / 15 Pro Max 的布局证据齐全；
- fresh Release Bundle ID 为 `com.onemore.campus`，只含 HTTPS/WSS 生产槽，不包含 localhost、开发 user/header、ATS 例外、WebView 或旧橙色 IP；
- Round 4 视觉、8 种异常态与两段动效均绑定最终 product-source tree SHA-256 `8857dedffff006e66f98b4cd8ab367a7018a4ce176796e90343d9c1203befc25` 和 Debug executable SHA-256 `44986a13c702a07dc5c47e7627cfd80ee63897ace5cceb0034996cd287041e52`。

最终命令、通过数、设备、截图/录屏和外部配置槽：

- `/Users/baihe/Documents/compusone/docs/TEST_LOOP.md`
- `/Users/baihe/Documents/compusone/docs/TEST_RESULTS.md`
- `/Users/baihe/Documents/compusone/docs/TEST_NEXT_STEPS.md`
- `/Users/baihe/Documents/compusone/ios/BUILD_NOTES.md`
