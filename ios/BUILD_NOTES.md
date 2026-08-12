# BUILD NOTES · 噜噜成局 iOS（工程代号 ONE MORE）

## 回滚基线

- 工作区在 Gate 0 初始化本地 Git。
- iOS 开工前基线：`03c9762 baseline: pre-iOS implementation workspace`。
- 后端契约：`d666a95 feat(api): close native iOS contract gaps`。
- 后端加固：`ae46bcf fix(api): harden preference and binary media contracts`。
- `design/generated/` 是任务前已有未跟踪目录，本轮未修改也不纳入 iOS 提交。

## 构建环境

| 项 | 实际值 |
|---|---|
| 主机 | macOS / Apple Silicon |
| Xcode | 26.0.1（17A400），`/Applications/Xcode.app` |
| SDK | iPhoneSimulator 26.0；deployment target 17.0 |
| 工程生成 | XcodeGen 2.45.3；最终生成前后 `project.pbxproj` SHA-256 均为 `a9f58727884ae33bd87b38e5406ca1dea48f95261f6fc903010eebf8f4e84b06` |
| 全量 UI | iPhone 15，iOS 17.0，`424DDFE8-0C85-409E-A7E6-434089238BD4` |
| 视觉/动效 | iPhone 15 Pro，iOS 17.0，`5BEE7D9F-B906-43B3-A508-2930BB4EFAF3` |
| 小屏 | iPhone SE (3rd generation)，iOS 17.0，`96D28839-621E-4E12-BE07-F89CFC185158` |
| 大屏 | iPhone 15 Pro Max，iOS 17.0，`52EB6107-993E-4242-AC66-99FC0B7265E0` |
| Debug Bundle ID | `com.onemore.campus.dev`（可替换槽） |

## 可复现命令

```bash
cd /Users/baihe/Documents/compusone/ios
./Scripts/generate.sh
./Scripts/build.sh
./Scripts/test.sh
./Scripts/run.sh
```

Release 审计构建：

```bash
cd /Users/baihe/Documents/compusone/ios
xcodebuild -project OneMore.xcodeproj -scheme OneMore -configuration Release \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/onemore-root-release-final-r2 clean build
```

真实 FastAPI 冒烟：

```bash
cd /Users/baihe/Documents/compusone
python3 ios/Scripts/live_api_smoke.py
```

结构、资产、红线与证据审计：

```bash
cd /Users/baihe/Documents/compusone
python3 ios/Scripts/audit_delivery.py
```

## 配置说明

- Debug 的 xcconfig 使用本机 `http://127.0.0.1:8000` / `ws://127.0.0.1:8000`，仅 Debug 编译 `DEV_AUTH`。
- Release 使用 `https://api.onemore.example` / `wss://api.onemore.example` 占位槽，无 ATS 放宽、无 `DevUserID`、无开发身份回退。
- `OneMore.entitlements` 已配置 `aps-environment` 与 `com.apple.developer.associated-domains`，值由 xcconfig 区分 Debug/Release。
- 生产归档前替换 Bundle ID、Team、域名、企业微信与 APNs 参数；这些是外部凭证槽，不影响 Simulator dev/fake 闭环。

## 已验证证据

- XcodeGen：`/Users/baihe/Documents/compusone/ios/artifacts/logs/xcodegen-final.log`。
- Debug app/final UI：`/Users/baihe/Documents/compusone/ios/artifacts/logs/ui-tests-final.log`（21/21）。
- Release build：`/Users/baihe/Documents/compusone/ios/artifacts/logs/build-release.log`。
- Release 审计：`/Users/baihe/Documents/compusone/ios/artifacts/logs/release-audit.txt`（Bundle ID `com.onemore.campus`；HTTPS/WSS；无 dev/ATS/WebView/旧 IP）。
- Unit tests：`/Users/baihe/Documents/compusone/ios/artifacts/logs/unit-tests-final.log`（72/72）。
- UI tests：`/Users/baihe/Documents/compusone/ios/artifacts/logs/ui-tests-final.log`。
- Swift 真实 API 流：`/Users/baihe/Documents/compusone/ios/artifacts/logs/ui-test-live-fastapi.log`。
- Live API 15 项：`/Users/baihe/Documents/compusone/ios/artifacts/logs/live-api-smoke.json`。
- 三尺寸截图：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/layout/LAYOUT_CONTACT_SHEET.png`。
- 36 张截图：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/RUNTIME_CONTACT_SHEET.png`。
- Round 4 源/二进制/截图哈希：`/Users/baihe/Documents/compusone/ios/artifacts/logs/visual-evidence-final-r4.json`。
- 动效：`/Users/baihe/Documents/compusone/ios/artifacts/motion/`。

最终通过数与 Definition of Done 审计见 `/Users/baihe/Documents/compusone/docs/TEST_RESULTS.md`。
