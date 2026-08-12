# ONE MORE · 最终测试结果

> 验证日期：2026-08-12（Asia/Shanghai）  
> 工作区：`/Users/baihe/Documents/compusone`  
> 产品代码冻结哈希：`8857dedffff006e66f98b4cd8ab367a7018a4ce176796e90343d9c1203befc25`（范围与逐文件哈希见 `ios/artifacts/logs/final-product-source-sha256.txt`）  
> 当前状态：实现及主任务证据全绿；独立 Fidelity/Testing 最终结论将在对应报告落盘后把本页第 16 项改为 PASS。

## 1. 最终汇总

| 门禁 | 结果 | 实际事实 |
|---|---|---|
| 后端 pytest | PASS | 154/154；1 条第三方 deprecation warning；45.28s |
| ruff | PASS | `onemore tests migrations`：All checks passed |
| mypy | PASS | 106 source files 无问题 |
| Alembic | PASS | 当前库与全新 SQLite 均到 `20260811_0017 (head)` |
| 比赛 V1.1 | PASS | 24 条；17 team-forming / 7 prep-partner；demo=0 |
| SYSU 静态包 | PASS | 5 校区、76 地点、137 场馆、468 audit rows；13 个已知缺口保持 unknown/partial |
| OpenAPI | PASS | 118 paths / 204 schemas；SHA-256 `a05a6dcae7f75f69ea109ef40b5d8dc4cda624f4aa0493ef93f5344951ab9abd` |
| live API | PASS | 15/15；health、today、24 赛事、compile/publish/Pooling privacy/leave、media/location、M7/M9/O4/兴趣导入 |
| XcodeGen | PASS | 2.45.3；生成前后 pbxproj SHA-256 均为 `a9f58727884ae33bd87b38e5406ca1dea48f95261f6fc903010eebf8f4e84b06` |
| iOS unit | PASS | 72/72；duplicate-tap 竞态修复后 targeted 20/20 |
| iOS UI | PASS | 21/21；0 failures；906.275s；canonical 日志含 `TEST EXECUTE SUCCEEDED` |
| Debug runtime | PASS | iOS 17 Simulator 安装/启动；最终 executable SHA-256 `44986a13c702a07dc5c47e7627cfd80ee63897ace5cceb0034996cd287041e52` |
| Release | PASS | fresh clean generic Simulator build；Bundle ID `com.onemore.campus` |
| Release 审计 | PASS | HTTPS/WSS；无 localhost、DevUserID、`u_demo_1`、`X-User-ID`、ATS 例外、WKWebView、`azou.png` |
| 视觉证据 | PASS | fresh Round 4：36/36 返回画板 + 8/8 异常态；CSV、contact sheet、逐 PNG hash 完整 |
| 动效证据 | PASS | success/failure 两段 H.264；各 10 张 fresh 连续帧；ffprobe/hash manifest 完整 |
| 三尺寸布局 | PASS | SE、15 Pro、15 Pro Max 截图；SE/Pro Max accessibility-large + Reduce Motion smoke；标准 iPhone 15 全量 UI 含同一项 |
| Delivery audit | PASS | 22/22；74 definitions、69 unique runtime IDs、30 server-state nodes、36 boards、57 frames 等全部精确断言 |
| 独立 Fidelity | PASS | fresh Round 4：36/36 + 8/8；major 0 / minor 26 / pass 10；9/9 粉发女孩，旧橙色 0 |
| 独立 Testing | RUNNING | fresh 72+21 与源码冻结审计：`/Users/baihe/Documents/compusone/docs/TESTING_REVIEW.md` |

## 2. 页面与测试口径

### 正式节点与返回画板

- `FormalNodeRegistry`：**74 个正式节点定义**，对应 **69 个唯一生产 runtime accessibility identifier**。
- 触发方式只分 `app / route / server-state / system-event`；其中 **30 个 server-state node** 的 endpoint 与冻结 OpenAPI 精确匹配。
- `B12.2`、`MSG` 是返回稿额外组合态，不计入 74。
- 36 张返回画板使用独立 Debug `-PrototypeScreenID` fidelity harness 捕获；该 harness 只证明视觉映射，不被写成“74+2 全部生产 direct launch”。
- 生产可达性由 typed Router、五入口/二级入口 UI、九条业务流、合法服务端状态与结构单测共同证明，详见 `/Users/baihe/Documents/compusone/ios/SCREEN_MAP.md`。

### 72 项 unit

覆盖：

- success/error envelope、request ID、snake_case、RFC3339/上海 civil day、nullable/unknown enum、最小 leave DTO；
- Debug/Bearer Auth、Keychain、401/session 恢复、APNs/deep link、74 formal triggers、30 OpenAPI server-state endpoints；
- GET retry/cache、幂等写恢复、非幂等不重试、WebSocket 生命周期；
- 57 帧 checksum/provenance；9 状态、14 事件、逐帧时长、序列/抢占/不可中断/cooldown/debounce、前后台/离屏、Reduce Motion；
- EventKit protocol fake、日历写入/更新/删除、权限恢复、APNs token 所有权；
- SYSU version/checksum/alias/search/commute/section、fail-closed；
- ViewModel duplicate tap、错误恢复、commit 后丢响应恢复。

### 21 项 UI

覆盖：

- 五个返回稿主入口、Today/Profile 二级生产入口图；
- 36 个返回画板 fidelity reachability；
- 九条端到端产品流及 T1→T2 真实信任门槛恢复；
- Organizer 与抖音兴趣画像入口；24 场生产赛事；SYSU bundle 消费；
- loading、empty、network-error、offline、permission-denied、session-expired、duplicate-tap、stale-state；
- named CTA、所有可见业务入口、Dynamic Type/VoiceOver label/Reduce Motion；
- SwiftUI 真实连接运行中的 FastAPI：compile → publish → Pooling detail → leave → Dissolved。

## 3. Definition of Done 逐条

| # | 结果 | 可核验证据 |
|---:|---|---|
| 1 | PASS | 58 个产品 Swift 文件；SwiftUI；源码/Release binary 无 WebKit/WKWebView |
| 2 | PASS | Round 4 runtime 36/36、capture CSV、逐 PNG hash、contact sheet 与独立 review 入口 |
| 3 | PASS | `SCREEN_MAP` 精确 74 行；74 definitions/69 runtime IDs；生产 route/state/event 触发有代码和测试 |
| 4 | PASS | B12.2、MSG 分别且仅出现一次；36-board harness 可达 |
| 5 | PASS | named CTA UI、入口图、空 action closure 审计=0；行为为导航/执行/系统或清晰 disabled reason |
| 6 | PASS | 15 live smoke + Swift live UI；Release 只用 HTTPS/WSS/Bearer，无 local happy-path fallback |
| 7 | PASS | fixture、API、UI 均为 24 条 V1.1；demo=0；运行产品无“21 场” |
| 8 | PASS | SYSU versioned Bundle、整包 checksum、fail-closed repository；无客户端联网抓取 |
| 9 | PASS | 唯一 AIIA 粉发女孩；57 帧；9 状态/14 event rules 均有业务 trigger；旧橙图为 0 |
| 10 | PASS | motion unit/lifecycle + 两段 MP4 + 20 连续帧；抢占、不可中断、后台/离屏、Reduce Motion 均覆盖 |
| 11 | PASS | EventKit、APNs、Share、custom/universal deep link、Voice、Image、Location 按需权限与拒绝恢复 |
| 12 | PASS | 9 flow UI、8 exception state、live FastAPI 流与错误恢复 |
| 13 | PASS | 后端结构隐私断言 + Swift forbidden implementation audit；Pooling/身份/关系/行动边界落实 |
| 14 | PASS | 154 pytest、ruff、mypy 106、空库 Alembic 0017、比赛/SYSU/OpenAPI 全绿 |
| 15 | PASS | XcodeGen、Debug/Release build、72 unit、21 UI、Simulator install/launch、三尺寸布局 |
| 16 | REVIEWING | fresh Round 4 Fidelity 与独立 fresh Testing 完成后，以两份独立报告的 `major=0`、`P0/P1=0` 关闭 |
| 17 | PASS | APP_METADATA、SCREEN_MAP、SERVICE_MAP、BUILD_NOTES、TEST_*、Fidelity 文档与 handoff 齐全 |
| 18 | PASS | 本文列命令结果、计数、设备、绝对证据、截图/录屏及仅外部凭证槽 |

## 4. 实际设备

| 设备 | OS | UDID | 实际角色与结果 |
|---|---|---|---|
| iPhone 15 | 17.0 | `424DDFE8-0C85-409E-A7E6-434089238BD4` | 最终全量 UI 21/21；独立 fresh 72+21 设备 |
| iPhone SE (3rd generation) | 17.0 | `96D28839-621E-4E12-BE07-F89CFC185158` | normal layout 截图；accessibility-large + Reduce Motion 1/1 |
| iPhone 15 Pro | 17.0 | `5BEE7D9F-B906-43B3-A508-2930BB4EFAF3` | Round 4 36+8、两段动作、normal layout |
| iPhone 15 Pro Max | 17.0 | `52EB6107-993E-4242-AC66-99FC0B7265E0` | 最终主任务 unit 72/72；normal layout；accessibility-large + Reduce Motion 1/1 |

环境：macOS 26.6.1（25G76）arm64；Xcode 26.0.1（17A400）；iPhoneSimulator SDK 26.0；deployment target 17.0；XcodeGen 2.45.3。

## 5. 绝对证据索引

### 后端

- pytest：`/Users/baihe/Documents/compusone/ios/artifacts/logs/backend-pytest-final-r3.log`
- ruff：`/Users/baihe/Documents/compusone/ios/artifacts/logs/backend-ruff-final-r3.log`
- mypy：`/Users/baihe/Documents/compusone/ios/artifacts/logs/backend-mypy-final-r3.log`
- 空库迁移：`/Users/baihe/Documents/compusone/ios/artifacts/logs/backend-alembic-empty-final-r3.log`
- 赛事/SYSU：`/Users/baihe/Documents/compusone/ios/artifacts/logs/competition-validation-final-r3.log`、`/Users/baihe/Documents/compusone/ios/artifacts/logs/sysu-validation-final-r3.log`
- OpenAPI exact：`/Users/baihe/Documents/compusone/ios/artifacts/logs/openapi-semantic-final-r3.log`
- live：`/Users/baihe/Documents/compusone/ios/artifacts/logs/live-api-smoke.json`

### iOS build/test/release

- XcodeGen：`/Users/baihe/Documents/compusone/ios/artifacts/logs/xcodegen-final.log`
- unit canonical/summary：`/Users/baihe/Documents/compusone/ios/artifacts/logs/unit-tests-final.log`、`/Users/baihe/Documents/compusone/ios/artifacts/logs/unit-tests-final-summary.json`
- duplicate-tap 20x：`/Users/baihe/Documents/compusone/ios/artifacts/logs/unit-racefix-20x.log`
- UI canonical/summary：`/Users/baihe/Documents/compusone/ios/artifacts/logs/ui-tests-final.log`、`/Users/baihe/Documents/compusone/ios/artifacts/logs/ui-tests-final-summary.json`
- Release：`/Users/baihe/Documents/compusone/ios/artifacts/logs/build-release.log`
- Release audit：`/Users/baihe/Documents/compusone/ios/artifacts/logs/release-audit.txt`
- delivery audit：`/Users/baihe/Documents/compusone/ios/artifacts/logs/delivery-audit.json`

### 视觉/动效/布局

- Round 4 provenance：`/Users/baihe/Documents/compusone/ios/artifacts/logs/visual-evidence-final-r4.json`
- 36 屏总览：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/RUNTIME_CONTACT_SHEET.png`
- 8 状态总览：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/STATE_EVIDENCE_CONTACT_SHEET.png`
- 动效 provenance：`/Users/baihe/Documents/compusone/ios/artifacts/logs/motion-evidence-final-r2.json`
- success/failure：`/Users/baihe/Documents/compusone/ios/artifacts/motion/azou-execute-succeeded.mp4`、`/Users/baihe/Documents/compusone/ios/artifacts/motion/azou-execute-failed.mp4`
- 动效帧总览：`/Users/baihe/Documents/compusone/ios/artifacts/motion/success-frames-contact.png`、`/Users/baihe/Documents/compusone/ios/artifacts/motion/failed-frames-contact.png`
- 三尺寸 provenance/contact：`/Users/baihe/Documents/compusone/ios/artifacts/logs/layout-evidence-final-r2.json`、`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/layout/LAYOUT_CONTACT_SHEET.png`
- 独立 Fidelity：`/Users/baihe/Documents/compusone/ios/FIDELITY_REVIEW.md`
- 独立 Testing：`/Users/baihe/Documents/compusone/docs/TESTING_REVIEW.md`

## 6. 仅外部配置槽

1. Apple Team、App Store Connect App ID、分发证书/provisioning 与真机 Archive；
2. 正式 HTTPS API、WSS 域名与 TLS/基础设施；
3. APNs provider key、production provisioning 与服务端发送配置；
4. 正式域名 `apple-app-site-association`；
5. 企业微信真实 Corp/App/回调/secret。
