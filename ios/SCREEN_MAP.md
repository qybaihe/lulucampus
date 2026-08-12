# SCREEN MAP · ONE MORE iOS

> 冻结日期：2026-08-12。生产映射的唯一代码事实源是 `OneMore/Core/DeepLink/FormalNodeRegistry.swift`：74 个正式节点、69 个唯一 runtime accessibility identifier；`B12.2` 与 `MSG` 是返回稿额外组合态，不计入 74。

## 证据口径

- **生产运行证据**来自 `OneMoreNavigationUITests` 的真实 `RootView`、typed route、repository 与 FastAPI 流；正式节点没有被声称为“全部 prototype direct launch”。
- **合法状态证据**用于必须由服务端状态/系统事件产生的节点：表中同时写明 endpoint/predicate、生产组件与稳定 identifier；`AuthRouterTests.testAllSeventyFourFormalNodesHaveConcreteProductionTriggers` 校验 74/74 定义。
- `OneMoreNavigationUITests.testThirtySixReturnedBoardsRemainReachableForFidelityEvidence` 只证明 36 张返回设计画板的视觉还原可捕获，不作为 74 个生产节点的业务可达证明。
- 最终全量日志路径在 `docs/TEST_RESULTS.md` 冻结；表内缩写：`MAIN` 五主入口，`GRAPH` 生产二级入口，`COMP24` 24 赛事，`LIVE` compile→publish→detail→leave，`F1…F9` 九条业务流，`F9-GATE` 真实 T1→T2 门槛恢复，`ORG` 主理人/兴趣导入，`STATE` 八异常态，`A11Y` Dynamic Type/VoiceOver/Reduce Motion，`CTA` 命名 CTA，`U74` 74 节点结构单测，`SYS` 系统权限单测，`ROUTER` typed route/恢复单测。

## 主导航决议

- 返回稿五入口保持为 `今天 / 比赛 / ⊕差一个 / 消息 / 我`。
- `公开局 / 我的局 / 搭子关系` 从 Today 的“业务入口”可达；个人设置从“我”进入。
- Release 使用 `AppRouter` + `NavigationStack`；`-PrototypeScreenID` 仅在 Debug fidelity harness 中存在。
- 比赛、人数、局状态、信任与消息内容一律来自 FastAPI；客户端不以返回稿 mock 推断业务事实。

## 74 个正式节点

| ID | 标题 | 触发类型 | 精确生产触发 | 生产组件 | Runtime identifier | 证据 |
|---|---|---|---|---|---|---|
| A1 | 启动路由 | `app` | App 根状态 | `RootView + AppSessionController` | `app-root` | 运行：MAIN、F1 |
| A2 | 认证说明 | `route` | 路由 `/auth` | `AuthenticationFlowView.intro` | `screen-A2-auth-intro` | 运行：F1；A3/G3 另见 F7 |
| A3 | 扫码认证 | `route` | 路由 `/auth/scan` | `RealLoginView` | `screen-A3-real-login` | 运行：F1；A3/G3 另见 F7 |
| A4 | 授权范围 | `server-state` | 服务端 `/auth/grants`；条件 `first-use route saves each selected grant, then refreshes /auth/me` | `FirstUseSetupView.grants` | `screen-A4-grants` | 运行：F1；A3/G3 另见 F7 |
| A5 | 画像初始化 | `server-state` | 服务端 `/auth/me`；条件 `identity facts loading after authentication` | `FirstUseSetupView.facts` | `screen-A5-A6-facts` | 运行：F1；A3/G3 另见 F7 |
| A6 | 画像确认 | `server-state` | 服务端 `/auth/me`；条件 `verified identity facts loaded` | `FirstUseSetupView.facts` | `screen-A5-A6-facts` | 运行：F1；A3/G3 另见 F7 |
| A7 | 社交开关 | `server-state` | 服务端 `/me/privacy`；条件 `first-use social opt-in` | `FirstUseSetupView.social` | `screen-A7-social` | 运行：F1；A3/G3 另见 F7 |
| A8 | 系统权限 | `system-event` | 系统/用户事件 `permission denied/recheck` | `OMPermissionRecoveryNotice + PermissionCoordinator` | `permission-recovery-notice` | 运行：STATE；单元：SYS |
| B1 | 今天 | `route` | 路由 `/today` | `TodayView` | `screen-B1-today` | 运行：MAIN、A11Y |
| B2 | Hermes 问答 | `route` | 路由 `/today/ask` | `HermesAskView` | `screen-B2-hermes` | 运行：CTA |
| B3 | 我的课表 | `route` | 路由 `/today/timetable` | `TimetableView` | `screen-B3-timetable` | 运行：GRAPH；B4/B5/B7 另见 F5/F4/F6 |
| B3.1 | 课程详情 | `server-state` | 服务端 `/schedule/courses/{course_id}`；条件 `selected course` | `CourseDetailView` | `screen-B3.1-course-detail` | 合法服务状态：U74 + 对应 CampusToolsView/API 契约 |
| B4 | 作业与 DDL | `route` | 路由 `/today/assignments` | `AssignmentsView` | `screen-B4-assignments` | 运行：GRAPH；B4/B5/B7 另见 F5/F4/F6 |
| B4.1 | 作业详情 | `server-state` | 服务端 `/assignments/{assignment_id}`；条件 `selected assignment` | `AssignmentDetailView` | `screen-B4.1-assignment-detail` | 合法服务状态：U74 + 对应 CampusToolsView/API 契约 |
| B5 | 体育场馆 | `route` | 路由 `/today/gym` | `VenueToolView.gym` | `screen-B5-gym` | 运行：GRAPH；B4/B5/B7 另见 F5/F4/F6 |
| B5.1 | 体育时段 | `server-state` | 服务端 `/venues/gym/available`；条件 `availability loaded` | `VenueToolView.gym slots` | `screen-B5-gym` | 合法服务状态：U74 + 对应 CampusToolsView/API 契约 |
| B6 | 研讨室 | `route` | 路由 `/today/room` | `VenueToolView.room` | `screen-B6-room` | 运行：GRAPH；B4/B5/B7 另见 F5/F4/F6 |
| B6.1 | 研讨室时段 | `server-state` | 服务端 `/venues/room/available`；条件 `availability loaded` | `VenueToolView.room slots` | `screen-B6-room` | 合法服务状态：U74 + 对应 CampusToolsView/API 契约 |
| B7 | 校园活动 | `route` | 路由 `/today/events` | `CampusEventsView` | `screen-B7-events` | 运行：GRAPH；B4/B5/B7 另见 F5/F4/F6 |
| B7.1 | 活动详情 | `server-state` | 服务端 `/events/{event_id}`；条件 `selected event` | `CampusEventsView.detail` | `screen-B7.1-event-detail` | 合法服务状态：U74 + 对应 CampusToolsView/API 契约 |
| B8 | 组会与课题 | `route` | 路由 `/today/research` | `CampusPresetQueryView` | `screen-B8-campus-query` | 运行：GRAPH；B4/B5/B7 另见 F5/F4/F6 |
| B9 | 班车与节次 | `route` | 路由 `/today/transit` | `CampusTransitReferenceView` | `screen-B9-transit-reference` | 运行：GRAPH；B4/B5/B7 另见 F5/F4/F6 |
| B10 | 场景触发 | `server-state` | 服务端 `/today/summary`；条件 `scene_trigger != null` | `SceneTriggerDetailView` | `screen-B10-scene-trigger` | 合法服务状态：U74 + `/today/summary.scene_trigger` |
| B11 | 个人行动预览 | `server-state` | 服务端 `/actions/preview`；条件 `personal action previewed` | `PersonalActionPreviewView` | `screen-B11-personal-action-preview` | 合法服务状态：U74 + action preview pytest |
| B12 | 比赛雷达 | `route` | 路由 `/competitions` | `CompetitionsView` | `screen-B12-competitions` | 运行：COMP24、F2 |
| B12.1 | 赛事详情 | `route` | 路由 `/competition/{competition_id}` | `CompetitionDetailView` | `screen-B12.1-competition-detail` | 运行：F2 |
| C1 | 公开局 | `route` | 路由 `/gatherings/open` | `GatheringListView.open` | `screen-C1-public-gatherings` | 运行：GRAPH、F9 |
| C2 | 公开局详情 | `route` | 路由 `/gathering/{gathering_id}` | `GatheringDetailView` | `screen-E3-gathering-detail` | 运行：F9-GATE |
| C3 | 准入门槛 | `server-state` | 服务端 `/gatherings/{gathering_id}/join`；条件 `TRUST_LEVEL_REQUIRED` | `TrustRequirementView + typed recovery target` | `screen-C3-trust-requirement` | 运行：F9-GATE；单元：ROUTER |
| C4 | 缺口卡落地 | `route` | 路由 `/g/{share_token}` | `SharedGapLandingView` | `screen-C4-share-landing` | 运行：F7 |
| D1 | 意图输入 | `route` | 路由 `/intent` | `IntentComposerView.editing` | `screen-D1-intent` | 运行：F3；D1/D4 另见 LIVE |
| D2 | 澄清追问 | `server-state` | 服务端 `/intent/compile`；条件 `needs_clarification` | `IntentComposerView.clarification` | `screen-D2-clarification` | 运行：F3；D1/D4 另见 LIVE |
| D3 | 意图卡确认 | `server-state` | 服务端 `/intent/compile`；条件 `card Draft` | `IntentComposerView.editor` | `screen-D3-intent-editor` | 运行：F3；D1/D4 另见 LIVE |
| D3.1 | 能力编辑 | `server-state` | 服务端 `/intent/{card_id}`；条件 `Draft capabilities` | `IntentComposerView.editor capabilities` | `intent-capabilities-editor` | 合法 Draft 子状态：U74 + IntentComposerView |
| D3.2 | 空档选择 | `server-state` | 服务端 `/intent/{card_id}`；条件 `Draft available_windows` | `IntentComposerView.editor availability` | `intent-availability-editor` | 合法 Draft 子状态：U74 + IntentComposerView |
| D3.3 | 角色编辑 | `server-state` | 服务端 `/intent/{card_id}`；条件 `Draft required_roles` | `IntentComposerView.editor roles` | `intent-roles-editor` | 合法 Draft 子状态：U74 + IntentComposerView |
| D3.4 | 安全偏好 | `server-state` | 服务端 `/intent/{card_id}`；条件 `Draft social/safety` | `IntentComposerView.editor safety` | `intent-safety-editor` | 合法 Draft 子状态：U74 + IntentComposerView |
| D4 | 匿名池 | `server-state` | 服务端 `/intent/publish`；条件 `Pooling` | `IntentComposerView.published` | `intent-view-gathering` | 运行：F3；D1/D4 另见 LIVE |
| E1 | 我的局 | `route` | 路由 `/gatherings/mine` | `GatheringListView.mine` | `screen-E1-my-gatherings` | 运行：GRAPH、LIVE |
| E2 | 局详情 | `route` | 路由 `/gathering/{gathering_id}` | `GatheringDetailView` | `screen-E3-gathering-detail` | 运行：LIVE、F2/F8/F9-GATE |
| E3 | 多人确认 | `server-state` | 服务端 `/gatherings/{gathering_id}`；条件 `Tentative` | `GatheringDetailView.confirmationActions` | `gathering-confirmation-actions` | 运行：F2/F4/F9-GATE |
| E4 | 改约协商 | `server-state` | 服务端 `/gatherings/{gathering_id}/reschedule`；条件 `proposal open` | `GatheringDetailView.rescheduleActions` | `gathering-reschedule-actions` | 合法服务状态：U74 + reschedule pytest |
| E5 | 行动预览 | `server-state` | 服务端 `/actions/preview`；条件 `previewed` | `GatheringDetailView.actionActions` | `gathering-action-preview` | 运行：F2 |
| E6 | 执行结果 | `server-state` | 服务端 `/actions/{action_id}`；条件 `succeeded/failed` | `GatheringDetailView.action result` | `gathering-action-result` | 运行：F2 |
| E7 | 协作空间 | `server-state` | 服务端 `/gatherings/{gathering_id}`；条件 `Confirmed/Executed/Active` | `GatheringDetailView.collaboration` | `gathering-collaboration-space` | 运行：F2 |
| E8 | 补位 | `server-state` | 服务端 `/gatherings/{gathering_id}/backfill`；条件 `gap opened` | `GatheringDetailView.backfillActions` | `gathering-backfill-actions` | 合法服务状态：U74 + backfill pytest |
| E9 | 完成确认 | `server-state` | 服务端 `/gatherings/{gathering_id}/complete`；条件 `completion pending` | `GatheringDetailView.completionActions` | `gathering-completion-actions` | 运行：F2 |
| E10 | 复局选择 | `server-state` | 服务端 `/gatherings/{gathering_id}/recur`；条件 `Completed` | `GatheringDetailView.recurrence` | `gathering-recurrence-actions` | 运行：F2 |
| E11 | 共同目标 | `route` | 路由 `/goal/{relation_id}` | `SharedGoalsView` | `screen-E11-shared-goals` | 合法关系路由：U74 + shared-goal contract tests |
| E12 | 退出 | `system-event` | 系统/用户事件 `user taps leave` | `GatheringDetailView.leave confirmation` | `gathering-leave-action` | 运行：LIVE；后端 leave contract |
| E13 | 举报与拉黑 | `system-event` | 系统/用户事件 `user opens safety sheet` | `GatheringDetailView.report sheet` | `gathering-safety-report` | 合法用户事件：U74 + report/block pytest |
| E14 | 局内群聊 | `route` | 路由 `/channel/{channel_id}` | `ChannelView` | `screen-E14-channel` | 运行：F2 |
| E15 | 搭子关系 | `route` | 路由 `/relations` | `RelationsView` | `screen-E15-relations` | 运行：F8 |
| E16 | 共同经历 | `route` | 路由 `/relation/{relation_id}` | `RelationDetailView` | `screen-E16-relation-detail` | 运行：F8 |
| E17 | 解除关系 | `system-event` | 系统/用户事件 `user confirms silent dissolve` | `RelationDetailView.dissolve` | `relation-dissolve-action` | 运行：F8 |
| M1 | 个人中心 | `route` | 路由 `/me` | `ProfileView` | `screen-M1-profile` | 运行：MAIN |
| M2 | 画像编辑 | `route` | 路由 `/me/profile` | `ProfileEditorView` | `screen-M2-profile-editor` | 运行：GRAPH；单元/pytest 覆盖对应契约 |
| M3 | 信任进度 | `route` | 路由 `/me/trust` | `TrustView` | `screen-M3-trust` | 运行：F9 |
| M4 | 授权管理 | `server-state` | 服务端 `/auth/me`；条件 `profile route /me/grants loads grants; mutations POST /auth/grants` | `GrantManagementView` | `screen-M4-grants` | 运行：GRAPH；单元/pytest 覆盖对应契约 |
| M5 | 隐私与安全 | `route` | 路由 `/me/privacy` | `PrivacySettingsView` | `screen-M5-privacy` | 运行：GRAPH；单元/pytest 覆盖对应契约 |
| M6 | 匹配偏好 | `route` | 路由 `/me/preferences` | `MatchingPreferencesView` | `screen-M6-matching-preferences` | 运行：GRAPH；单元/pytest 覆盖对应契约 |
| M7 | 通知与日历 | `route` | 路由 `/me/notifications` | `NotificationPreferencesView` | `screen-M7-notification-settings` | 运行：GRAPH；单元/pytest 覆盖对应契约 |
| M8 | 黑名单 | `route` | 路由 `/me/blocks` | `BlockListView` | `screen-M8-block-list` | 运行：GRAPH；单元/pytest 覆盖对应契约 |
| M9 | 信任申诉 | `route` | 路由 `/me/appeals` | `TrustAppealsView` | `screen-M9-appeals` | 运行：F9 |
| M10 | 账号与数据 | `route` | 路由 `/me/account` | `AccountDataView` | `screen-M10-account` | 运行：GRAPH；单元/pytest 覆盖对应契约 |
| O1 | 主理人控制台 | `route` | 路由 `/organizer` | `OrganizerView` | `screen-O1-organizer` | 运行：ORG；后端 organizer pytest |
| O2 | 创建官方局 | `system-event` | 系统/用户事件 `organizer taps create` | `OfficialGatheringEditor` | `screen-O2-create-official` | 运行：ORG；后端 organizer pytest |
| O3 | 报名与到场看板 | `route` | 路由 `/organizer/gatherings/{gathering_id}/dashboard` | `OrganizerDashboardView` | `screen-O3-organizer-dashboard` | 合法 T4 路由：U74 + organizer dashboard pytest |
| O4 | 官方局模板 | `server-state` | 服务端 `/organizer/templates`；条件 `T4 verified` | `OrganizerView.templateSection` | `screen-O4-templates` | 运行：ORG；后端 organizer pytest |
| G1 | Hermes 唤起 | `system-event` | 系统/用户事件 `today hermes entry` | `HermesAskView` | `today-hermes-entry` | 运行：CTA |
| G2 | 缺口卡分享 | `system-event` | 系统/用户事件 `gap share created` | `GatheringDetailView ShareLink` | `gathering-share-link` | 合法用户事件：U74 + share endpoint/F7 |
| G3 | 认证恢复 | `system-event` | 系统/用户事件 `401/deep link` | `AuthenticationFlowView + AppRouter.pendingAfterAuthentication` | `screen-A3-real-login` | 运行：F7；单元：ROUTER |
| G4 | 静默解散 | `server-state` | 服务端 `/gatherings/{gathering_id}`；条件 `Dissolved/Expired` | `GatheringDetailView terminal state` | `gathering-terminal-state` | 合法终态：U74 + expiry/leave pytest |
| G5 | 状态规范 | `system-event` | 系统/用户事件 `loading/empty/error/offline/permission/session/stale` | `OMAsyncStateView/OMStateView` | `runtime-state-library` | 运行：STATE |

## 返回稿额外组合态（不计入 74）

| ID | 含义 | 性质 | 可达/证据 |
|---|---|---|---|
| B12.2 | 赛事牌桌 · 差一个 | 返回稿组合态；没有伪装成独立生产 endpoint | Debug fidelity harness；`testThirtySixReturnedBoardsRemainReachableForFidelityEvidence` |
| MSG | 消息总览 | 返回稿组合态；生产消息入口是五 Tab 之一 | Debug fidelity harness + `testFiveMainEntriesAreReachable` |

## 36 张返回画板映射

以下 36 项以 `design/received/2026-08-11-one-more-mobile-prototype/screens/` 为视觉基线，以 `ios/artifacts/screenshots/runtime/` 同名文件为 runtime 捕获；业务事实仍由上表生产触发决定。

| 节点/组合态 | 设计与 runtime 文件 |
|---|---|
| A2 | `screens/a2.png` ↔ `ios/artifacts/screenshots/runtime/a2.png` |
| A3 | `screens/a3.png` ↔ `ios/artifacts/screenshots/runtime/a3.png` |
| A4 | `screens/a4.png` ↔ `ios/artifacts/screenshots/runtime/a4.png` |
| A5 | `screens/a5.png` ↔ `ios/artifacts/screenshots/runtime/a5.png` |
| A6 | `screens/a6.png` ↔ `ios/artifacts/screenshots/runtime/a6.png` |
| A7 | `screens/a7.png` ↔ `ios/artifacts/screenshots/runtime/a7.png` |
| B1 | `screens/b1.png` ↔ `ios/artifacts/screenshots/runtime/b1.png` |
| B12 | `screens/b12.png` ↔ `ios/artifacts/screenshots/runtime/b12.png` |
| B12.1 | `screens/b12d.png` ↔ `ios/artifacts/screenshots/runtime/b12d.png` |
| B4 | `screens/b4.png` ↔ `ios/artifacts/screenshots/runtime/b4.png` |
| B4.1 | `screens/b4d.png` ↔ `ios/artifacts/screenshots/runtime/b4d.png` |
| B5 | `screens/b5.png` ↔ `ios/artifacts/screenshots/runtime/b5.png` |
| B5.1 | `screens/b5s.png` ↔ `ios/artifacts/screenshots/runtime/b5s.png` |
| B7 | `screens/b7.png` ↔ `ios/artifacts/screenshots/runtime/b7.png` |
| B7.1 | `screens/b7d.png` ↔ `ios/artifacts/screenshots/runtime/b7d.png` |
| C1 | `screens/c1.png` ↔ `ios/artifacts/screenshots/runtime/c1.png` |
| C4 | `screens/c4.png` ↔ `ios/artifacts/screenshots/runtime/c4.png` |
| D1 | `screens/d1.png` ↔ `ios/artifacts/screenshots/runtime/d1.png` |
| D2 | `screens/d2.png` ↔ `ios/artifacts/screenshots/runtime/d2.png` |
| D3 | `screens/d3.png` ↔ `ios/artifacts/screenshots/runtime/d3.png` |
| D4 | `screens/d4.png` ↔ `ios/artifacts/screenshots/runtime/d4.png` |
| E1 | `screens/e1.png` ↔ `ios/artifacts/screenshots/runtime/e1.png` |
| E10 | `screens/e10.png` ↔ `ios/artifacts/screenshots/runtime/e10.png` |
| E14 | `screens/e14.png` ↔ `ios/artifacts/screenshots/runtime/e14.png` |
| E16 | `screens/e16.png` ↔ `ios/artifacts/screenshots/runtime/e16.png` |
| E17 | `screens/e17.png` ↔ `ios/artifacts/screenshots/runtime/e17.png` |
| E3 | `screens/e3.png` ↔ `ios/artifacts/screenshots/runtime/e3.png` |
| E5 | `screens/e5.png` ↔ `ios/artifacts/screenshots/runtime/e5.png` |
| E6 | `screens/e6.png` ↔ `ios/artifacts/screenshots/runtime/e6.png` |
| E7 | `screens/e7.png` ↔ `ios/artifacts/screenshots/runtime/e7.png` |
| E9 | `screens/e9.png` ↔ `ios/artifacts/screenshots/runtime/e9.png` |
| G2 | `screens/g2.png` ↔ `ios/artifacts/screenshots/runtime/g2.png` |
| M1 | `screens/m1.png` ↔ `ios/artifacts/screenshots/runtime/m1.png` |
| M3 | `screens/m3.png` ↔ `ios/artifacts/screenshots/runtime/m3.png` |
| MSG | `screens/msg.png` ↔ `ios/artifacts/screenshots/runtime/msg.png` |
| B12.2 | `screens/table.png` ↔ `ios/artifacts/screenshots/runtime/table.png` |

## 可核验数量与路径

- 正式节点：74/74；触发类型仅 `app / route / server-state / system-event`。
- 正式节点唯一 runtime identifier：69；共享 identifier 只发生在同一生产容器的相邻状态（例如 A5/A6、B5/B5.1、C2/E2）。
- 额外组合态：2/2（`B12.2`、`MSG`）。
- 返回画板 runtime 捕获：36/36；总览：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/RUNTIME_CONTACT_SHEET.png`。
- 八异常态：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/`。
- 独立视觉结论：`/Users/baihe/Documents/compusone/ios/FIDELITY_REVIEW.md`（fresh Round 4：major 0 / minor 26 / pass 10）。
- 独立测试结论：`/Users/baihe/Documents/compusone/docs/TESTING_REVIEW.md`。
