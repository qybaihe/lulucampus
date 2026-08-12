# 12 · iOS 完整实现 · Goal 模式新任务交接提示词

下面代码块可原样复制到一个新的 Codex 任务。它要求新任务持续执行到原生 iOS App、后端联调、IP 动效和测试证据全部落地，而不是只再输出一份分析。

```text
/goal

目标：在 `/Users/baihe/Documents/compusone` 内，把「差一个 · ONE MORE」实现为可构建、可启动、可点击、可完成主要业务闭环的原生 SwiftUI iOS App，并与现有 FastAPI 后端完成真实联调。必须使用已经返回的移动端设计稿还原 UI，必须用选定的 AIIA 粉发女孩作为唯一阿凑 IP，必须实现其业务动画。持续执行、修复、构建、运行、截图、测试，直到下面的 Definition of Done 全部满足；不要停在方案、脚手架、静态页面或“后续建议”。

一、先读取的事实源

开始改代码前完整读取以下文件，不要凭摘要猜实现：

1. 产品与客户端规格
   - `/Users/baihe/Documents/compusone/docs/00_产品方案_V2.1.md`
   - `/Users/baihe/Documents/compusone/docs/01_iOS客户端开发指南.md`
   - `/Users/baihe/Documents/compusone/docs/05_iOS设计交接提示词.md`
2. 后端与行动代理
   - `/Users/baihe/Documents/compusone/docs/02_后端服务开发指南.md`
   - `/Users/baihe/Documents/compusone/docs/03_行动代理与Hermes设计.md`
   - `/Users/baihe/Documents/compusone/docs/06_后端实现与前端联调.md`
   - `/Users/baihe/Documents/compusone/openapi/onemore.openapi.json`
3. 本轮状态与已知缺口
   - `/Users/baihe/Documents/compusone/docs/11_iOS前后端联调现状与范围.md`
4. 返回设计稿
   - `/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/README.md`
   - `/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/SOURCE_MANIFEST.json`
   - `/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/SCREEN_CONTACT_SHEET.png`
   - `/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/screens/`
   - `/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/export/ONE MORE 原型.dc.html`
   - `/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/export/ds/_ds_bundle.css`
5. 最终 IP 与动作契约
   - `/Users/baihe/Documents/compusone/assets/ip/selected/aiia-pink-girl-business-v1/README.md`
   - `/Users/baihe/Documents/compusone/assets/ip/selected/aiia-pink-girl-business-v1/pet.json`
   - `/Users/baihe/Documents/compusone/assets/ip/selected/aiia-pink-girl-business-v1/motion-contract.json`
   - `/Users/baihe/Documents/compusone/assets/ip/selected/aiia-pink-girl-business-v1/frames/frames-manifest.json`
6. 数据资产
   - `/Users/baihe/Documents/compusone/docs/09_比赛雷达V1.1质量验收与入库说明.md`
   - `/Users/baihe/Documents/compusone/fixtures/competition_snapshot_2026-08-11_v1.1.json`
   - `/Users/baihe/Documents/compusone/data/reference/sysu/manifest.json`
   - `/Users/baihe/Documents/compusone/docs/08_中山大学校园基础数据资产说明.md`
7. 额外已实现后端功能
   - `/Users/baihe/Documents/compusone/docs/07_抖音兴趣标签导入接口.md`

事实源优先级：

- 功能、隐私、状态机、禁止项：V2.1 产品文档和 iOS 指南优先；
- 36 个已返回状态的视觉、布局、层级和 CTA：返回设计稿与 `screens/*.png` 优先；
- API 字段与状态：固定 OpenAPI 和后端实现优先；
- 阿凑身份、帧、时长与事件策略：选定 IP 目录的 JSON 优先；
- 返回原型里的赛事、日期、人数、确认进度和聊天内容只是 mock，不是业务事实。

最新明确视觉决议：保留返回稿展示的五个主入口视觉结构——`今天 / 比赛 / ⊕差一个 / 消息 / 我`。同时必须让 `公开局 / 我的局 / 搭子关系` 从今天、消息或我内的清晰入口可达，不能因为 Tab 变化丢失 74 节点中的功能。记录这项导航映射到 `ios/SCREEN_MAP.md`。

二、工作方式

1. 先建立 task plan，按 Gate 推进；每完成一个 Gate 更新状态和证据。
2. 这是持续实现任务，不是咨询任务。直接检查文件、修改代码、运行服务、构建 Simulator、点击验证和修复。
3. 当前工作区不是 Git 仓库。开始大量改动前先建立明确可回滚基线：优先初始化本地 Git 并做 baseline commit；如果环境不适合提交，则制作带时间戳的文件清单和备份，并记录在 `ios/BUILD_NOTES.md`。
4. 显式使用多个独立子任务/子代理：
   - UI Restore：只负责根据 36 张设计截图和 HTML/CSS 建立 SwiftUI 视觉壳；
   - Fidelity Review：不得参与初版实现，独立对比 Simulator 截图和设计截图；
   - Testing：独立运行后端/iOS/交互/红线测试并形成失败清单；
   - 主任务负责整合、修复并反复重跑，不能把子任务结果当作完成本身。
5. 每个新任务都重新检查 `xcodebuildmcp` 是否真实可用；若可用，先读取 session defaults，再设置 project/scheme/simulator。若不可用，使用本机 `xcodebuild`、`xcrun simctl` 和 Xcode 继续，不因此停工。
6. 本项目后端模式是 `existing-fastapi`，不是 Supabase，也不是 local-only mock。不要引入 Supabase，不要替换现有后端。
7. 不需要重新做市场调研、PRD 或视觉方向探索；产品、设计和后端已经存在。
8. 真实企业微信、APNs、签名 Team、线上域名等外部凭证未给出时，继续完成 dev/fake 模式闭环并把生产配置槽留好，不要因此停在半成品。

三、Gate 0：先恢复后端基线

在写 iOS 前先执行：

```bash
cd /Users/baihe/Documents/compusone
uv sync --dev
uv run alembic upgrade head
uv run ruff check onemore tests migrations
uv run mypy onemore
uv run pytest -o addopts='' -ra
uv run python scripts/validate_competition_snapshot.py fixtures/competition_snapshot_2026-08-11_v1.1.json
uv run python scripts/validate_sysu_reference.py
```

当前已知基线问题必须先修：

1. `/Users/baihe/Documents/compusone/onemore/modules/taste_profile/api.py:219-233` 的 `verify_mobile_login()` 缺少 `APIResponse[LoginVerificationView]` 返回，当前结果是 `50 passed, 1 failed`，ruff/mypy 同点失败；
2. 当前 `/competitions` 返回 25 条：24 条 V1.1 生产快照 + 1 条 `demo-innovation-2026`。修复 seed/摄取/查询隔离，生产列表只返回 24 条；增加回归测试；
3. 修复后重新导出 OpenAPI：`uv run onemore-export-openapi`，检查 diff，并同步 Swift Client；
4. 启动 API，真实冒烟 `/health/live`、`/health/ready`、`/today/summary`、`/competitions`；
5. 后端 pytest、ruff、mypy、两项数据验证全绿，才进入 Gate 1。

同时审计并在实现过程中关闭以下后端契约缺口：

- O4 模板编辑/复制/停用；
- M9 申诉状态/结果查询；
- E14 图片上传与 location payload 的稳定契约；
- M7 跨设备通知偏好与纯本地系统设置的边界；
- 中大静态数据的版本化分发策略；
- 如 iOS 主流程发现 OpenAPI 缺字段，优先补后端契约和测试，不在客户端伪造字段。

四、Gate 1：初始化原生 iOS 工程

在下面目录创建工程：

```text
/Users/baihe/Documents/compusone/ios
```

硬性要求：

- SwiftUI；
- iOS deployment target 17.0+；
- Swift Concurrency；
- XcodeGen 生成可复现 `.xcodeproj`；
- 不使用 WKWebView 包装 `.dc.html`；
- 不把 Debug mock 混入 Release；
- 暂无正式值时使用可替换的 dev Bundle ID，并记录在 `ios/APP_METADATA.json`，不要停下来询问；
- Base URL、认证模式、Associated Domains、签名配置走 xcconfig/Info.plist 配置，不散落硬编码；
- 为本地 Simulator 的 HTTP 联调提供 Debug 配置，Release 不放宽 ATS；
- `ios/README.md` 给出一条命令生成工程、一条命令构建、一条命令测试、一条命令运行。

推荐目录：

```text
ios/
├── project.yml
├── Config/
├── OneMore/
│   ├── App/
│   ├── Core/
│   │   ├── DesignSystem/
│   │   ├── Networking/
│   │   ├── Auth/
│   │   ├── Persistence/
│   │   ├── DeepLink/
│   │   ├── Motion/
│   │   └── ReferenceData/
│   ├── Features/
│   │   ├── Onboarding/
│   │   ├── Today/
│   │   ├── Competitions/
│   │   ├── PublicGatherings/
│   │   ├── Intent/
│   │   ├── Gatherings/
│   │   ├── Messages/
│   │   ├── Relations/
│   │   ├── Profile/
│   │   ├── Organizer/
│   │   └── TasteImport/
│   └── Resources/
├── OneMoreTests/
└── OneMoreUITests/
```

状态架构至少包含：

- 单一 App Router / typed route；
- `NavigationStack` 与可恢复 deep link；
- `AppEnvironment` 注入 API、Auth、WebSocket、ReferenceData、Calendar、Notification、Motion；
- ViewModel/Store 不直接拼 URL；
- Repository 不直接持有 View；
- Auth Token 存 Keychain，Debug dev user 由构建配置启用，Release 不包含 `X-User-ID` 快捷路径；
- 写操作具备 loading、disabled、idempotency、防重复点击和错误恢复。

必须生成：

- `ios/APP_METADATA.json`
- `ios/SCREEN_MAP.md`
- `ios/SERVICE_MAP.md`
- `ios/BUILD_NOTES.md`
- `docs/handoffs/gemini-ui-handoff.md`

五、Gate 2：设计还原与视觉门禁

先完成 UI Restore，再接真实业务逻辑。

1. 将 `screens/*.png` 作为 36 个返回状态的像素级视觉基准；HTML/CSS 只用于读取布局、颜色 token、交互意图和文案。
2. 建立原生 Design System：
   - 页面底色 `#010001`；
   - cyan `#00FFE1` 与对应渐变；
   - magenta `#FF4FD3`；
   - white opacity surface/border/text ladder；
   - 8/20/32/pill 圆角；
   - 玻璃面与 blur；
   - PingFang/SF 字号、字重、行高；
   - Primary/Secondary/Ghost Button；
   - GlassPanel、SourceChip、GatheringCard、GapCard、ConfirmCard、ActionPreviewSheet、TimeSlotPicker、TrustProgress、ReasonBlock、HermesResultCard、AzouBubble、ChatBubble、CompanionCard、ExperienceTimeline、Skeleton、Empty/Error/Permission State。
3. 首轮必须逐一还原 36 个原型状态；正式映射见 `SOURCE_MANIFEST.json`。
4. 原型里的两个额外组合态 `B12.2` 与 `MSG` 也必须保留。
5. 补齐正式 74 节点中未出图的 40 项：

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

6. 缺失节点要沿用返回稿的视觉语言，不另起一套 UI；功能和红线严格按 iOS 指南。
7. 抖音兴趣画像导入不在 74 节点内，但后端已实现。按同一设计系统补充：入口、开始说明、二维码、扫码中、采集中、不确定进度、3–5 道单选题、结果、删除、取消、二维码过期、失败重试。
8. 所有页面补全 loading、empty、error、offline、permission denied、session expired、duplicate tap、stale state。
9. 在接业务逻辑前，用 Simulator 输出对应截图，由独立 Fidelity Review 子任务对比：
   - 层级与区块顺序；
   - 间距、字号、字重；
   - CTA 位置与权重；
   - 颜色、玻璃面、圆角；
   - Tab/Navigation；
   - 图片与 IP；
   - 空/错/加载状态。
10. 产出并反复更新：
   - `ios/FIDELITY_REVIEW.md`
   - `ios/FIDELITY_CHECKLIST.md`
   - `ios/FIDELITY_NEXT_STEPS.md`
11. major drift 未清零前不进入真实业务联调。

六、Gate 3：最终 IP 与丝滑动画

返回 HTML 十处引用的 `export/assets/azou.png` 是废弃橙色占位图，最终 App 不得出现。唯一来源：

```text
/Users/baihe/Documents/compusone/assets/ip/selected/aiia-pink-girl-business-v1/
```

实现要求：

1. 导入 57 张透明帧及 `motion-contract.json`、`frames-manifest.json`；保留来源与 checksum 记录；
2. 写 `AzouMotionContract: Decodable`、`AzouMotionEvent`、`AzouMotionState`、`AzouMotionEngine`、`AzouMotionView`；
3. 按每帧 `durationsMs` 播放，不把所有状态统一成固定 FPS；
4. 业务层只使用：
   - `idle`
   - `appear`
   - `exit`
   - `greeting`
   - `success`
   - `needs-adjustment`
   - `waiting-confirmation`
   - `executing`
   - `closed-eye-sensing`
5. 实现契约中的 14 条 event rules、priority、cooldown、debounce、sequence；
6. 同时只播放一个动作；高优先级可抢占；success/failure 不可中断；长循环按 maxLoops 停止；
7. App 后台、View 离屏时暂停；恢复时不要高速补帧；
8. `UIAccessibility.isReduceMotionEnabled` 开启时使用 `reducedMotionColumn` 静态帧，不循环；
9. 禁止角色做横向跑动，`running-left/right` 只是图集兼容源名；
10. 在后台预解码/缓存 CGImage，主线程不做 PNG 解码；57 帧内存预算可记录，列表内复用播放器；
11. View 消失时释放时钟和事件订阅，不造成 retain cycle；
12. 视觉尺寸遵守 `runtimeAtlasMaxDisplayWidthPt = 170`，大图展示使用 Retina 资产；
13. 真正绑定业务事件：意图聚焦/编译、发布、撮合、等待确认、预览就绪、执行开始、成功、失败、补位、@阿凑、真人对话开始；
14. 补齐 motion 单元测试：时长选择、序列、抢占、不可中断、cooldown、Reduce Motion、后台暂停；
15. 输出至少一段 Simulator 动效录屏或连续帧证据，不能只放静态图后声称动画完成。

七、Gate 4：真实 API 与系统能力联调

网络层：

1. 基于 `openapi/onemore.openapi.json` 建强类型 Swift 模型；可生成，也可手写，但必须有契约测试；
2. 统一解析成功 envelope `data/meta` 与错误 envelope `error.code/message/details/request_id`；
3. 保存并展示可复制的 `X-Request-ID` 到 Debug 诊断，不向普通用户暴露原始 stderr；
4. URLSession async/await；合理 timeout；读请求可重试，写请求只按幂等规则重试；
5. ISO-8601、时区、可空字段、snake_case、enum unknown fallback 全覆盖；
6. Auth actor 管理 dev header/Bearer，401/session expired 统一进入 G3 并恢复原动作；
7. WebSocket actor 支持连接、鉴权、指数退避、前后台恢复、重复消息去重；不实现已读、在线、正在输入；
8. NetworkMonitor 驱动离线读缓存与写操作可恢复状态；
9. Release 运行版不得静默回退到本地成功 mock。

逐链路联调：

1. 首次使用：A2 → A3 扫码 → A4 授权 → A5/A6 画像 → A7 → B1；
2. 比赛组队：B12 → B12.1 → B12.2/D3 → D4 → E3 → E5 → E6 → E7/E14 → E9/E10；
3. 自然语言“差一个”：D1 → D2 最多两轮 → D3 编辑 → publish → Pooling；
4. 运动搭子：B5/B5.1 → 意图 → 匹配 → 确认 → 行动；
5. 同课 DDL：B3/B3.1 或 B4/B4.1 → 预填冲刺局；
6. 活动同行：B7/B7.1 → 外部官方入口或同行局；
7. 分享获客：G2 → custom scheme/Universal Link → C4/C2 → 认证恢复 → join；
8. 我的局/关系：E1/E2/E7/E14/E15/E16/E17；
9. 信任：M1/M3/M9 与 T0–T4 门槛；
10. T4 主理人：O1–O4；
11. 抖音兴趣画像：创建 → 二维码 → verify/poll → collection → questions → answers → result → delete；
12. 异常：成员退出、确认超时、改约、补位、资源冲突、登录失效、回滚、离线、重复提交。

系统能力：

- EventKit：只在真实预约成功后请求；写入、更新、删除；保存 eventIdentifier；拒绝/稍后/去设置可恢复；iOS 17 使用正确的 full access API 与 usage description；
- APNs：首次成局时请求；上传 device token；深链到 E3/E5/E6/E7/E14/E16/G3/M3；
- Universal Link：保存原始目标，认证后返回；无正式域名时同时完成可测试的 `onemore://` dev scheme；
- Share：系统 ShareLink/UIActivityViewController；缺口卡不含分享者身份；
- Voice：用户首次主动语音输入时请求麦克风/语音权限；
- Image：用户首次发送图片时请求照片权限并接真实上传契约；
- Location：只在用户主动发送位置时请求一次，不做实时位置/在场者；
- OpenURL：赛事与活动官方报名由用户本人完成；没有 URL 时显示明确状态，不能是死按钮。

中大静态数据：

1. 不重新联网采集；
2. 优先把 `data/reference/sysu` 中 manifest、校区、别名、地点、场馆、交通、校历、节次作为 versioned Bundle Resource；
3. 写 `StaticReferenceRepository` 做中文别名搜索、地点匹配、场馆目录、通勤时长和节次解释；
4. 实时空闲、用户课表、预约、登录仍走后端；
5. 校验 bundle_version 和 checksums；版本不一致时整包拒绝混用；
6. 13 个缺口保持 unknown/partial，不构造数据。

八、客户端边界和红线

必须由代码结构与测试保证：

1. 客户端不计算匹配分、不计算多人空档、不推断局状态；
2. 客户端不直接调用 sysu-anything CLI；
3. hermes 与阿凑物理分离；hermes 不进入局内群聊；
4. Pooling 不展示报名人数和报名者；
5. 双向确认前不展示真实身份；
6. 不展示他人等级、他人原始课表、同课名单、成绩、绩点；
7. 没有用户搜索、好友申请、人物刷卡流、公开个人主页；
8. 没有已读、在线、输入中、评价、排行榜、关系回顾；
9. 共同经历只显示事实字段；
10. 阿凑成局后退场，不做主动闲聊、签到、召回；
11. 所有真实校园写操作都经过 preview → 分别确认 → execute；
12. 赛事报名、宣讲会报名、请假、选课、成绩、支付、岗位申请不代理执行；
13. 图书馆自习区和健身房器械区不做现场连接；
14. 退出、拉黑、举报始终可达；
15. 解除关系单方静默，不给对方通知。

九、测试与独立复核

后端：

- pytest 全绿且测试数不得少于当前 51；
- ruff/mypy 全绿；
- Alembic 从空库升级通过；
- 赛事/静态包验证通过；
- 新增接口同步 OpenAPI 和测试；
- `/competitions` 不含 demo；
- 关键隐私字段做结构性断言。

iOS 单测：

- API envelope/error/enum/date decoding；
- Auth、401 恢复、request id；
- Router/deep-link/认证后恢复；
- 局状态到 Screen 的映射；
- Repository cache/invalidations；
- ReferenceData checksum/alias/search/commute；
- Motion engine；
- EventKit adapter 用 protocol fake 测试；
- ViewModel 重复点击与错误恢复。

iOS UI Tests：

- 五个主入口与所有二级入口；
- 36 返回画板可达；
- 74 正式节点有 `SCREEN_MAP` 且可达或由明确状态触发；
- 九条产品端到端流程；
- 所有 CTA 审计：每个可见按钮要么导航、执行、打开系统/外部链接，要么有清晰 disabled reason；无空闭包；
- 权限拒绝、离线、空态、错误、Session 失效；
- Dynamic Type、VoiceOver label、Reduce Motion；
- 深色界面在 iPhone SE、标准尺寸、Pro Max 至少做布局冒烟。

运行证据：

1. XcodeGen 生成工程；
2. `xcodebuild build` 成功；
3. unit/UI test 成功；
4. Simulator 安装并启动；
5. 收集日志；
6. 36 张关键对照截图，至少为每个返回画板保留一张 runtime 截图或覆盖记录；
7. IP 动效录屏/连续帧；
8. 独立 Fidelity Review；
9. 独立 Testing 子任务反复执行，主任务修复后再重跑，直到高优先级问题为 0。

测试文档必须生成：

- `docs/TEST_LOOP.md`
- `docs/TEST_RESULTS.md`
- `docs/TEST_NEXT_STEPS.md`
- `ios/FIDELITY_REVIEW.md`
- `ios/FIDELITY_CHECKLIST.md`
- `ios/FIDELITY_NEXT_STEPS.md`

十、必须交付的文件

至少包含：

```text
ios/project.yml
ios/OneMore.xcodeproj
ios/OneMore/**/*.swift
ios/OneMore/Resources/**
ios/OneMoreTests/**
ios/OneMoreUITests/**
ios/APP_METADATA.json
ios/SCREEN_MAP.md
ios/SERVICE_MAP.md
ios/BUILD_NOTES.md
ios/FIDELITY_REVIEW.md
ios/FIDELITY_CHECKLIST.md
ios/FIDELITY_NEXT_STEPS.md
ios/README.md
docs/handoffs/gemini-ui-handoff.md
docs/TEST_LOOP.md
docs/TEST_RESULTS.md
docs/TEST_NEXT_STEPS.md
openapi/onemore.openapi.json
```

更新：

- `/Users/baihe/Documents/compusone/README.md`
- `/Users/baihe/Documents/compusone/docs/README.md`
- 如新增/修改 API，同步后端实现、迁移、测试、OpenAPI、联调文档。

十一、Definition of Done

只有以下全部成立才标记目标完成：

1. 原生 SwiftUI App 已存在，不是 WebView；
2. 36 个返回画板完成视觉还原和映射；
3. 74 个正式节点全部在 `SCREEN_MAP` 中，且可以导航到或由合法状态触发；
4. `B12.2` 和 `MSG` 额外状态保留；
5. 所有可见 CTA 有真实行为，没有死按钮；
6. FastAPI 主流程真实联调，Release 不依赖本地 happy-path mock；
7. 比赛列表实际读取 24 条 V1.1 生产数据，不含 demo，设计稿“21 场”不再出现；
8. 中大静态数据离线版本化消费，不反复抓取；
9. 粉发女孩是唯一阿凑形象，九个业务状态和事件序列真实可触发；
10. 动画在前后台、离屏、抢占、Reduce Motion 下正确，且有运行证据；
11. EventKit、通知、分享、Deep Link、语音、图片、位置按需权限链完整；
12. 九条产品端到端流程和异常恢复可运行；
13. 所有隐私与产品红线有实现和测试；
14. 后端 pytest/ruff/mypy/数据验证全绿；
15. iOS build/unit/UI tests 全绿，Simulator 可安装启动；
16. Fidelity Review 无 major drift；Testing Review 无 P0/P1 未关闭问题；
17. `APP_METADATA/SCREEN_MAP/SERVICE_MAP/BUILD_NOTES/TEST_*` 等交付文档齐全；
18. 最终报告列出实际执行命令、通过数、Simulator/OS、截图与录屏绝对路径、剩余仅限真实外部凭证的配置项；没有运行证据时不得声称完成。

现在开始执行 Gate 0。不要先回复一份新方案；先检查并修复基线，然后持续推进实现。
```

## 最短启动版

如果新任务支持直接读取文件，也可以只发送下面这段；完整约束仍以本文件正文为准：

```text
/goal
完整读取并执行 `/Users/baihe/Documents/compusone/docs/12_iOS完整实现_Goal模式线程交接提示词.md` 中的 Goal 提示词。工作目录是 `/Users/baihe/Documents/compusone`。从 Gate 0 开始实际改代码、搭建原生 SwiftUI iOS 17+ 工程、还原返回设计稿、接通现有 FastAPI、集成选定粉发女孩 57 帧动作、构建运行并反复测试，直到该文件 Definition of Done 全部满足。不要停在分析或脚手架。
```

