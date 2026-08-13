# 噜噜成局 · 原生 iOS（工程代号 ONE MORE）

SwiftUI / iOS 17+ 客户端，真实连接仓库现有 FastAPI。工程由 XcodeGen 生成；没有 WKWebView、Supabase 或 Release happy-path mock。

## 四条命令

先保证后端运行在 `127.0.0.1:8000`：

```bash
cd /Users/baihe/Documents/compusone
uv run uvicorn onemore.main:app --host 127.0.0.1 --port 8000
```

另一个终端：

```bash
cd /Users/baihe/Documents/compusone/ios
./Scripts/generate.sh   # 生成 OneMore.xcodeproj
./Scripts/build.sh      # Debug 构建 iPhone 15 Pro / iOS 17
./Scripts/test.sh       # Unit + UI 全量测试
./Scripts/run.sh        # 构建、安装并启动 Simulator
```

可用 `SIMULATOR_UDID=<UDID>` 替换设备；`CONFIGURATION=Release ./Scripts/build.sh` 构建 Release。

GitHub Release 安装包（真机 IPA + 模拟器 zip）：

```bash
./Scripts/package_github_release.sh
```

## 结构

- `OneMore/App`：AppEnvironment、SessionGate、Router root、APNs/deep link。
- `OneMore/Core`：Design System、网络/Auth/缓存/WS、Motion、ReferenceData、系统能力。
- `OneMore/Features`：真实业务 UI；74 个正式节点定义映射到 69 个唯一生产 runtime identifier，另保留 B12.2/MSG。
- `OneMore/Resources/AzouFrames`：唯一粉发阿凑 57 帧。
- `OneMore/Resources/SYSU`：版本化离线中大数据整包。
- `OneMoreTests`：72 项契约/网络/路由/动效/系统/ViewModel 测试。
- `OneMoreUITests`：21 项 UI test；覆盖五入口、生产入口图、9 流程、36 画板 fidelity harness、8 异常态、CTA、动态字体和真实 API 流。74 个正式节点由生产路由/服务端状态/系统事件触发，不声称全部 direct launch。
- `artifacts`：截图、录屏、连续帧和构建/测试/联调日志。

## 配置

| 配置 | Debug | Release |
|---|---|---|
| API | `http://127.0.0.1:8000` | `https://api.onemore.example` 槽 |
| WebSocket | `ws://127.0.0.1:8000` | `wss://api.onemore.example` 槽 |
| Auth | `DEV_AUTH` + 可替换 dev user | Keychain Bearer，仅生产路径 |
| ATS | 仅 local networking | 无例外 |
| APNs | development entitlement | production entitlement 槽 |
| Universal Link | dev associated-domain 槽 | production associated-domain 槽 |

## 验证与地图

- 页面：[`SCREEN_MAP.md`](/Users/baihe/Documents/compusone/ios/SCREEN_MAP.md)
- 服务：[`SERVICE_MAP.md`](/Users/baihe/Documents/compusone/ios/SERVICE_MAP.md)
- 构建：[`BUILD_NOTES.md`](/Users/baihe/Documents/compusone/ios/BUILD_NOTES.md)
- 视觉：[`FIDELITY_REVIEW.md`](/Users/baihe/Documents/compusone/ios/FIDELITY_REVIEW.md)
- 测试：[`docs/TEST_RESULTS.md`](/Users/baihe/Documents/compusone/docs/TEST_RESULTS.md)

快速联调与审计：

```bash
cd /Users/baihe/Documents/compusone
python3 ios/Scripts/live_api_smoke.py
python3 ios/Scripts/audit_delivery.py
```
