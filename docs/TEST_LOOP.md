# ONE MORE · iOS 完整实现测试闭环

> 工作区：`/Users/baihe/Documents/compusone`  
> 最终产品代码冻结：2026-08-12（Asia/Shanghai）  
> 原则：每个 Gate 都由主任务实际修复并重跑；独立 Fidelity/Testing 报告只作为复核，不替代主任务证据。

## 1. Gate 循环记录

| 轮次 | 发现 | 实际修复 | 最终重跑 |
|---|---|---|---|
| Gate 0 / 初始基线 | `verify_mobile_login` 漏返回；生产赛事混入 demo；当时为 50 pass / 1 fail | 恢复 typed response；隔离 demo/生产 seed；补 24 条且无 demo 回归 | 后续继续加固至 154/154 pytest；ruff、mypy 106 files、赛事/SYSU 验证全绿 |
| Gate 0 / 契约缺口 | O4、M9、E14、M7 与静态数据分发不完整 | 补模板编辑/复制/停用、申诉查询、媒体与 typed location、通知边界、版本化静态包；重导 OpenAPI | OpenAPI 精确 118 paths / 204 schemas；15/15 live smoke |
| Gate 0 / 数据与隐私加固 | 幂等、APNs 所有权、登录兑换、全员授权、偏好、改约、补位/关系通道等边界需结构化保证 | 加迁移 0006–0017、服务端约束与结构性隐私测试 | 全新 SQLite 从空库升级到 `20260811_0017 (head)`；独立后端复核同样通过 |
| Gate 1 / 原生工程 | 工作区原无 iOS 工程 | XcodeGen 建 iOS 17+ SwiftUI；Router/Environment/Repository/Auth/Keychain/缓存/WS/系统适配器分层 | `project.pbxproj` 再生成前后 SHA-256 相同；Debug/Release 构建、安装、启动通过 |
| Gate 2 / UI | 初轮存在拆卡、密度、CTA 裁切与旧橙色 IP | 建 Design System；逐屏实现 36 返回画板；沿同风格补 40 个缺图正式节点；保留 B12.2/MSG；全量替换为粉发女孩 | Round 4 fresh 36/36 + 8/8；源/二进制/PNG 哈希固化；独立结论见 `ios/FIDELITY_REVIEW.md` |
| Gate 2 / 可达性口径 | 早期文档把 74+2 错写为全部 direct launch；部分 Today/Profile 行命中不稳 | 建 74 定义的 `FormalNodeRegistry`；区分生产 route/server-state/system-event 与 36-board fidelity harness；修正全行 hit target/稳定 identifier | 74 definitions / 69 unique runtime IDs / 30 server-state nodes 精确匹配冻结 OpenAPI；生产入口图、36-board、CTA UI tests 通过 |
| Gate 3 / 动效 | 静态首帧不能证明动作/lifecycle | 实现逐帧 `durationsMs`、序列/抢占/不可中断/cooldown/debounce、前后台/离屏、Reduce Motion、后台预解码；绑定 14 事件 | motion unit tests 通过；success/failure 两段 MP4，各 10 张 fresh 连续帧及 ffprobe/hash manifest |
| Gate 4 / 联调 | live UI 流暴露键盘遮挡；leave 响应模型过宽；若干写操作恢复边界需验证 | 收键盘/滚动；使用权威最小 leave DTO；统一 envelope/request-ID/401/幂等/缓存/WS；服务端状态驱动 UI | Swift live compile → publish → Pooling detail → leave 通过；Python 15/15 live smoke |
| Gate 4 / Release | 旧 Release 证据误用了 `.dev` bundle；发布边界证据过期 | fresh generic Simulator `clean build`，Release ID 固定 `com.onemore.campus`；逐项审计 plist/binary/xcent | `BUILD SUCCEEDED`；HTTPS/WSS；无 localhost、DevUserID、`X-User-ID`、ATS 例外、WKWebView、`azou.png` |
| Final / UI 回归 | Today 二级入口 accessibility parent 覆盖 child；E12 CTA 会落入 TabBar；生产入口图 swipe 过粗 | 移除错误 parent identifier；详情底部加滚动安全区；稳定 CTA ID 和小步滚动 | 最终全量 UI 21/21，0 failures，906.275s |
| Final / unit 竞态 | 独立 fresh run 发现 duplicate-tap 测试的 `Task.yield()` 不保证 first task 先进入 MainActor | 测试用 XCTestExpectation 确认首请求进入，并用 semaphore 保持 `sending=true` 后再触发 duplicate | 主任务与独立 Testing 均 targeted 20/20；主任务全量 unit 72/72；独立 fresh 72/72 |
| Final / Flow 8 点击竞态 | 独立 fresh UI 暴露长 ScrollView 手势后 relation detail/解除 CTA 的首次 synthesized tap 偶发被底部 overlay 吞掉 | 仅加固 UI 测试：每次先小步滚动使控件离开 TabBar hit region，用稳定 identifier 重查并 center tap，以 E16 screen/确认按钮作状态观测 | 主任务 Flow 8 重复 10/10，0 failures；证据 `ui-flow8-fix-10x-r2.log` 与 xcresult summary |
| Final / Flow 4–5 导航转场 | 独立 fresh full 先后暴露 preset 入场后 compile tap、booking option tap 偶发在转场/滚动后被吞；服务端无对应 POST，排除 API 错误 | 仅加固 UI 测试：对 compile/clarification/booking-option 用稳定 ID、短 press，并以下一 phase/screen 作结果观测后有界重试 | 主任务 Flow 4 重复 10/10、Flow 5 重复 10/10，均 0 failures；对应 summary 已落盘 |
| Final / 三尺寸 | 需覆盖小屏、标准、Pro Max 与 Dynamic Type/Reduce Motion | SE、15 Pro、15 Pro Max 安装/启动/截图；SE/Pro Max 跑 accessibility-large/Reduce Motion；标准 iPhone 15 全量 UI 含同一 smoke | 三截图/contact sheet 与两份 targeted UI 日志通过 |

## 2. 最终后端命令

```bash
cd /Users/baihe/Documents/compusone
uv sync --dev
uv run alembic upgrade head
ONEMORE_DATABASE_URL=sqlite:////tmp/onemore-alembic-final.db uv run alembic upgrade head
uv run ruff check onemore tests migrations
uv run mypy onemore
uv run pytest -o addopts='' -ra
uv run python scripts/validate_competition_snapshot.py fixtures/competition_snapshot_2026-08-11_v1.1.json
uv run python scripts/validate_sysu_reference.py
uv run onemore-export-openapi
python3 ios/Scripts/live_api_smoke.py
```

最终结果：154 pytest；mypy 106 files；Alembic 0017；赛事 24；SYSU 5/76/137/468；OpenAPI 118/204；live smoke 15/15。对应日志为 `/Users/baihe/Documents/compusone/ios/artifacts/logs/*-final-r3.log` 与 `/Users/baihe/Documents/compusone/ios/artifacts/logs/live-api-smoke.json`。

## 3. 最终 iOS 命令

```bash
cd /Users/baihe/Documents/compusone/ios
./Scripts/generate.sh

xcodebuild -project OneMore.xcodeproj -scheme OneMore -configuration Debug \
  -destination 'platform=iOS Simulator,id=52EB6107-993E-4242-AC66-99FC0B7265E0' \
  -derivedDataPath /tmp/onemore-root-racefix-r1 \
  test-without-building -only-testing:OneMoreTests

xcodebuild -project OneMore.xcodeproj -scheme OneMore -configuration Debug \
  -destination 'platform=iOS Simulator,id=424DDFE8-0C85-409E-A7E6-434089238BD4' \
  -derivedDataPath /tmp/onemore-root-dd-e2e-r1 \
  test-without-building -only-testing:OneMoreUITests

xcodebuild -project OneMore.xcodeproj -scheme OneMore -configuration Release \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/onemore-root-release-final-r2 clean build

python3 Scripts/audit_delivery.py
```

结果：72/72 unit、21/21 UI、fresh Release 与 22/22 deterministic delivery assertions 全绿。canonical 日志位于 `/Users/baihe/Documents/compusone/ios/artifacts/logs/`。

## 4. 视觉、动作与布局命令

```bash
cd /Users/baihe/Documents/compusone
SIMULATOR_UDID=5BEE7D9F-B906-43B3-A508-2930BB4EFAF3 ROUND=4 \
  ios/Scripts/capture_visual_evidence.sh
SIMULATOR_UDID=5BEE7D9F-B906-43B3-A508-2930BB4EFAF3 \
  ios/Scripts/capture_motion_evidence.sh
```

- 36 张返回画板、8 种异常态：`/Users/baihe/Documents/compusone/ios/artifacts/logs/visual-evidence-final-r4.json`。
- 两段动作、20 张连续帧：`/Users/baihe/Documents/compusone/ios/artifacts/logs/motion-evidence-final-r2.json`。
- 三尺寸布局：`/Users/baihe/Documents/compusone/ios/artifacts/logs/layout-evidence-final-r2.json`。
- 三类 manifest 均绑定 product tree SHA-256 `8857dedffff006e66f98b4cd8ab367a7018a4ce176796e90343d9c1203befc25` 与 Debug executable SHA-256 `44986a13c702a07dc5c47e7627cfd80ee63897ace5cceb0034996cd287041e52`。

## 5. 闭环准则

- 产品代码变化：重跑相关 unit/UI/live、fresh Release 与哈希证据。
- 视觉依赖变化：重捕获 36+8，并由独立 Fidelity Review 重新判级。
- Testing P0/P1 非零：主任务修复后，由独立 Testing 使用 fresh DerivedData 再跑；不得以旧通过日志覆盖新失败。
- 只有 Apple Team/App Store、生产 HTTPS/WSS 域名、APNs provider/provisioning、AASA 与真实企业微信属于外部配置槽。
