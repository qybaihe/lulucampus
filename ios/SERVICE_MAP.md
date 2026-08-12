# SERVICE MAP · ONE MORE iOS

> 后端模式：`existing-fastapi`。Debug 指向 `http://127.0.0.1:8000`，Release 只接受 xcconfig 中的 `https://` / `wss://` 生产槽；App 没有本地成功 mock 或 Supabase 路径。

## 共享基础设施

| 能力 | iOS 实现 | 契约与行为 |
|---|---|---|
| HTTP | `APIClient` | URLSession async/await；`data/meta` 与 `error` envelope；RFC3339；snake_case；20s/45s timeout；GET 重试与离线 cache；写请求仅凭 Idempotency-Key 重试 |
| 认证 | `AuthManager`, `AppSessionController` | Bearer 存 Keychain；401 统一触发 SessionGate/G3 并保留待恢复路由；`DEV_AUTH` 仅 Debug 编译 |
| 诊断 | `NetworkDiagnostics`, `DiagnosticsView` | 保存响应 `X-Request-ID` 与 path；仅 Debug 诊断页展示并可复制 |
| WebSocket | `WebSocketClient` | token 鉴权、指数退避、消息 ID 去重、前后台断开/恢复、离屏终止；无已读/在线/输入中 |
| 离线 | `NetworkMonitor`, `ResponseCache` | 读缓存；写失败保持可重试状态，不伪造成功 |
| 路由 | `AppRouter` | typed route、custom scheme/Universal Link、认证后恢复、APNs payload 路由 |
| 静态数据 | `StaticReferenceRepository` | Bundle v1.1；整包 SHA-256；别名搜索、地点/场馆、通勤、节次；13 缺口保持 unknown/partial |
| 动效 | `LuluMotionPlayer` | 12 clip 精灵表（lulu-motion.v1.json）、逐帧时长、loop/once、poster 静帧、Reduce Motion/生命周期 |

## FastAPI 接口映射

| 业务 | Endpoint | Repository / Adapter | UI / 状态 | 验证 |
|---|---|---|---|---|
| 健康 | `GET /health/live`, `/health/ready` | `APIClient` / live smoke | Diagnostics | `live-api-smoke.json` |
| Today | `GET /today/summary` | `TodayRepository` | B1 / `TodayView` | UI 默认启动 + live smoke |
| 比赛 | `GET /competitions`, `GET /competitions/{competition_id}` | `CompetitionRepository`, typed `Competition` | B12/B12.1 | UI 断言 24、无 21/无 demo |
| 意图编译 | `POST /intent/compile` | `IntentRepository.compile` | D1/D2/D3 | Swift live UI test |
| 意图读取/发布 | `GET /intent/{card_id}`, `POST /intent/publish` | `IntentRepository` | D3.1–D3.4/D4 | Swift live UI test + live smoke |
| 公开/我的局 | `GET /gatherings/open`, `GET /gatherings/mine`, `GET /gatherings/{gathering_id}` | `GatheringRepository` | C1/E1/E2 | production graph + 九流程 |
| 入局/确认/退出 | `POST /gatherings/{gathering_id}/join`, `/confirm`, `/leave` | `GatheringRepository` | C2/C3/E3/E12 | typed mutation；服务端 T0–T4 gate；退出最小响应单测 |
| 改约 | `GET /gatherings/{gathering_id}/time-options`, `POST /gatherings/{gathering_id}/reschedule`, `POST /gatherings/{gathering_id}/reschedule/{proposal_id}/vote` | `GatheringRepository` | E4 | 服务端多人空档和匿名投票，不在客户端计算 |
| 补位 | `POST /gatherings/{gathering_id}/backfill`, `/backfill/claim`, `/backfill/fallback` | `GatheringRepository` | E8 | 服务端 eligibility/T3 fast-lane；客户端不推断 |
| 完成/复局 | `POST /gatherings/{gathering_id}/complete`, `/recur`, `/recur/finish` | `GatheringRepository` | E9/E10 | 分别完成确认、私密复局选择与新局路由 |
| 举报拉黑 | `POST /gatherings/{gathering_id}/report`, `POST /me/blocks` | `GatheringRepository`, `SocialRepository` | E13/M8 | 始终可达；服务端接触策略 |
| 行动能力/预约 | `GET /gatherings/{gathering_id}/action-capability`, `/booking-options`, `/booking-plan` | `ActionRepository` | E5 | 服务端能力、资源和计划事实 |
| 校园行动 | `POST /actions/preview`, `POST /actions/{action_id}/authorization`, `POST /actions/execute`, `GET /actions/{action_id}` | `ActionRepository` | E5/E6 | preview snapshot → 每位成员分别确认 → execute |
| 消息 | `GET/POST /channels/{channel_id}/messages`, `GET /channels/{channel_id}/scene-policy` | `SocialRepository` | E14 | text/image/location 强类型；场景静默策略；live smoke |
| 图片 | `POST /media/images` | `APIClient.uploadImage` | Channel photo picker | live smoke 上传并发送 |
| @阿凑 | `POST /channels/{channel_id}/mention-azou` | `SocialRepository` | E14 | 只在显式 @ 时调用并绑定动作 |
| 实时消息 | `WS /channels/{channel_id}`（握手带 Authorization/X-User-ID 头） | `WebSocketClient` | E14 | 鉴权/去重/退避/前后台单测 |
| 关系 | `GET /relations`, `GET/DELETE /relations/{relation_id}`, `POST /relations/{relation_id}/recur` | `SocialRepository` | E15/E16/E17 | 共同经历仅事实；解除单方静默；新共同经历原子重开关系通道 |
| 共同目标 | `GET/POST /relations/{relation_id}/goals`, `GET/PATCH /goals/{goal_id}` | `SocialRepository` | E11 | T3 gate；进度只取服务端出勤/完成事实 |
| 信任 | `GET /trust/me` | `SocialRepository` | M3 | T0–T4 服务端事实 |
| 申诉 | `POST /trust/appeal`, `GET /trust/appeals[/{id}]` | `SocialRepository` | M9 | 列表/详情/结果契约与后端测试 |
| 通知偏好 | `GET/PATCH /me/notification-preferences` | `SocialRepository` | M7 | 跨设备偏好；系统授权保留本地 |
| APNs token | `POST /notifications/devices` | `OneMoreAppDelegate` + `APIClient` | 首次 Tentative/Confirmed 请求 | entitlement + payload parser 单测 |
| 分享落地 | `POST /gatherings/{gathering_id}/share`, `GET /shares/g/{share_token}`, `POST /shares/g/{share_token}/join` | `GatheringRepository` | G2/C4/C2/G3 | 匿名缺口卡、认证后恢复原始 join |
| 主理人 | `GET/POST /organizer/gatherings`, `GET /organizer/gatherings/{gathering_id}/dashboard`, `/organizer/templates*` | `OrganizerRepository` | O1–O4 | T4 gate；官方局、到场、模板创建/编辑/复制/停用 |
| 抖音画像 | `POST /profile/imports/douyin[/qr]`, 轮询/verify/phone/qr、`GET/POST /profile/taste/me[/ai-refresh]`、`DELETE /profile/taste/me/douyin`、questions/answers | `TasteImportRepository` | 补充流程 `TasteImportView` | 主链路 READY 即用；可选细化；统一 `TasteProfileResult`；AI Flash 文案刷新 |
| 认证 | `POST /auth/session`, `GET /auth/session/{session_id}`, `POST /auth/session/{session_id}/redeem`, `GET /auth/me`, `POST /auth/grants` | `RealLoginViewModel`, `AuthManager` | A3–A7/G3/M4 | Release Bearer；Debug dev user 仅编译开关 |

## 系统能力

| 能力 | 实现 | 请求时机与恢复 |
|---|---|---|
| EventKit | `EventKitCalendarService` | 仅 Executed/Active/Completed 且有时间后由用户点击；iOS 17 `requestFullAccessToEvents`；保存 identifier，支持更新/删除；拒绝后显示“打开设置” |
| APNs | `PermissionCoordinator`, `OneMoreAppDelegate` | 首次进入待确认/已确认局；上传 token；通知 payload 支持 E3/E5/E6/E7/E14/E16/G3/M3、gathering/channel deep link |
| Universal Link | entitlements + `AppRouter` | `ASSOCIATED_DOMAIN` 配置；无正式域名时 `onemore://` 可测；认证前保存目标 |
| Share | `ShareLink`, `UIActivityViewController` | 赛事/缺口卡系统分享；分享文案不含分享者身份 |
| Voice | `AVAudioApplication` + Speech | 用户点“语音输入”时首次请求；拒绝可去设置 |
| Image | `PHPickerViewController` + `/media/images` | 用户点图片时请求/选择并真实上传，随后发送 typed message |
| Location | `CLLocationManager.requestLocation` | 用户点“发送一次位置”才请求；收到一次坐标即停止；无实时追踪/在场者 |
| OpenURL | SwiftUI `openURL` | 赛事/活动官方 URL 由用户本人完成；App 不代理报名、支付或材料提交 |

## 配置边界

- Debug：`Config/Debug.xcconfig`，本机 HTTP/WS、`DEV_AUTH`。
- Release：`Config/Release.xcconfig`，HTTPS/WSS、无 ATS 例外、无 `DevUserID`、无开发身份代码路径。
- 仍需部署方提供的仅有：正式 API/WSS 域名、`apple-app-site-association`、Apple Team/签名与 APNs capability、企业微信生产参数。
