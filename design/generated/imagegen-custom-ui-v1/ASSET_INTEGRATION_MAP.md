# ONE MORE ImageGen 素材集成映射

> 本目录只提供素材与集成说明，未修改 SwiftUI 业务代码，也未覆盖现有粉发女孩 57 帧资源。

## 1. 导入约定

- 运行尺寸位于 `/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/runtime/`。
- 每个 asset 均有 `@1x`、`@2x`、`@3x` PNG；导入 Xcode Asset Catalog 时，imageset 名称使用 `asset_id`，三个文件分别放入对应 scale 槽位。
- 这些图片自带 cyan / magenta / 冷白色彩，应使用 `.renderingMode(.original)`，不要套 `.foregroundStyle` 或 template tint。
- 所有标题、数字、Tier、T0–T4、按钮文案、状态文案和动态数据继续由 SwiftUI 渲染。
- 返回、关闭、Chevron、系统分享面板入口等基础导航符号继续保留 SF Symbols。

```swift
Image(isSelected ? "om_tab_today_active" : "om_tab_today_idle")
    .resizable()
    .renderingMode(.original)
    .interpolation(.high)
    .scaledToFit()
    .frame(width: 32, height: 32)
```

## 2. Home Bar：SF Symbols → 定制资产

涉及现有位置：

- `/Users/baihe/Documents/compusone/ios/OneMore/Core/DeepLink/AppRouter.swift`
- `/Users/baihe/Documents/compusone/ios/OneMore/App/RootView.swift`
- `/Users/baihe/Documents/compusone/ios/OneMore/Core/DesignSystem/OMControls.swift`

| Tab | 当前 SF Symbol | Idle | Active | 建议展示尺寸 |
|---|---|---|---|---:|
| 今天 | `sparkles` / `clock` | `om_tab_today_idle` | `om_tab_today_active` | 32pt |
| 比赛 | `trophy` / `diamond` | `om_tab_competitions_idle` | `om_tab_competitions_active` | 32pt |
| 差一个 | `plus` / `plus.circle` | `om_tab_create_idle` | `om_tab_create_active` | 38pt |
| 消息 | `message` / `rectangle.split.2x1` | `om_tab_messages_idle` | `om_tab_messages_active` | 32pt |
| 我 | `person` / `circle.lefthalf.filled` | `om_tab_profile_idle` | `om_tab_profile_active` | 32pt |

切换规则：

1. `selected == tab` 时使用 `_active`，否则使用 `_idle`。
2. 不通过 tint 模拟 active；直接交换图片。
3. “差一个”保持 38pt，并保留现有更大的点击热区；图片本身不是普通加号。
4. 消息红点继续由 SwiftUI 在 `om_tab_messages_*` 右上角叠加。
5. VoiceOver 标签继续使用现有中文 Tab 名称；图片不承担文字语义。

## 3. 首页 ToolTile

现有 ToolTile 位于 `/Users/baihe/Documents/compusone/ios/OneMore/Features/PrototypeGallery/ReturnedMainScreens.swift`。

| 当前入口 | 当前符号 | 对应 asset | 建议尺寸 | 说明 |
|---|---|---|---:|---|
| 课表 | `calendar` | `om_tool_schedule` | 40pt | B3 / B3.1 |
| 作业 | `clock` | `om_tool_deadline` | 40pt | B4 / B4.1，语义覆盖 DDL |
| 研讨室 | `building.2` | `om_tool_study_room` | 40pt | B6 / B6.1 |
| 场馆 | `circle.circle` | `om_tool_sports` | 40pt | B5 / B5.1，当前原型主场景为羽毛球 |
| 公开局 | `diamond` | `om_feature_public_gathering` | 40pt | C1 |
| 班车 | `bus` | `om_tool_shuttle` | 40pt | B9 |
| 赛事 | `trophy` | `om_feature_competition_team` | 40pt | B12 / B12.1 |
| 我的局 | `person.2` | `om_feature_my_gatherings` | 40pt | E1 |
| 活动 / 宣讲会（新增或 B7 卡片入口） | — | `om_tool_official_event` | 40pt | B7 / B7.1 |

`OMHermesResultCard.Kind.schedule`、`.deadline`、`.venue` 可分别换成 `om_tool_schedule`、`om_tool_deadline`、`om_tool_study_room`，继续保留原生文字和 CTA。

## 4. 发现、成局与比赛

| 业务位置 / 节点 | asset | 建议尺寸 |
|---|---|---:|
| C1 公开局 | `om_feature_public_gathering` | 40pt / 56pt hero |
| E1 我的局 | `om_feature_my_gatherings` | 40pt |
| E15–E17 搭子关系 | `om_feature_relations` | 40pt |
| B12 / B12.2 比赛组队 | `om_feature_competition_team` | 40pt / 56pt hero |
| 备赛搭子卡 | `om_feature_prep_partner` | 40pt |
| D1–D3 意图编译 | `om_feature_intent` | 40pt / 56pt hero |

## 5. 业务行动生命周期

与 `/Users/baihe/Documents/compusone/assets/ip/selected/aiia-pink-girl-business-v1/motion-contract.json` 的动作状态并行使用；图标表达系统状态，粉发女孩仍由现有 57 帧资源表达代理动作。

| 状态 / 节点 | asset | 建议尺寸 |
|---|---|---:|
| E3 / `gathering.tentative` 等待确认 | `om_state_waiting_confirmation` | 56pt |
| B11、E5 / `action.preview.ready` | `om_state_action_preview` | 56pt |
| `action.execute.started` | `om_state_executing` | 56pt |
| E6、E9 / `action.execute.succeeded` | `om_state_success` | 56pt |
| 执行失败后调整 / `needs-adjustment` | `om_state_needs_adjustment` | 56pt |
| E8 / `gathering.backfill.started` | `om_state_backfill` | 56pt |

## 6. 协作与共同经历

| 位置 / 语义 | asset | 建议尺寸 |
|---|---|---:|
| E14 局内群聊 | `om_collab_group_chat` | 40pt |
| 阿凑被提及、感知中 | `om_collab_azou_mention` | 40pt |
| E11 共同目标 | `om_collab_shared_goal` | 40pt |
| E10 复局 | `om_collab_recurrence` | 40pt |
| 日历承诺已执行 | `om_collab_calendar_commit` | 40pt |
| E16 共同经历时间线 | `om_collab_experience` | 40pt |

## 7. 信任、隐私与账号

| 原型节点 / 入口 | asset | 建议尺寸 |
|---|---|---:|
| M3 信任等级详情 | `om_settings_trust` | 40pt |
| A4 / A8 / M4 授权管理 | `om_settings_permissions` | 40pt |
| M5 隐私与安全 | `om_settings_privacy` | 40pt |
| E13 举报与拉黑、M8 黑名单 | `om_settings_block_report` | 40pt |
| M9 申诉 | `om_settings_appeal` | 40pt |
| M10 账号与数据 | `om_settings_account_data` | 40pt |

`M3` 的 T 等级、进度和解释仍由 `Text` / `ProgressView` 呈现；不要把等级文字烘焙进图片。

## 8. 主理人、消息图片与单次位置

| 原型节点 / 控件 | asset | 建议尺寸 |
|---|---|---:|
| O1 主理人台首页 | `om_organizer_official` | 40pt / 56pt hero |
| O1 数据看板 | `om_organizer_dashboard` | 40pt |
| O3 报名与到场 | `om_organizer_attendance` | 40pt |
| O4 局模板 | `om_organizer_template` | 40pt |
| E14 发送图片入口 | `om_message_image` | 40pt；紧凑输入栏可使用 24pt |
| E14 单次位置入口 | `om_message_location_once` | 40pt；紧凑输入栏可使用 24pt |

动态签到二维码本体继续由运行时生成；`om_ornament_qr_frame` 只能包围二维码，不能替代二维码。

## 9. Ornament：只作无障碍隐藏装饰

以下六项均不承担独立操作或语义，叠加到 `OMGlassPanel` / 卡片时使用 `.allowsHitTesting(false).accessibilityHidden(true)`：

- `om_ornament_gap_ring`
- `om_ornament_sensing_halo`
- `om_ornament_card_corner`
- `om_ornament_qr_frame`
- `om_ornament_verified_source`
- `om_ornament_share_gap`

来源核验、分享、扫码等真实语义必须由相邻 SwiftUI 文案或真实控件提供。

## 10. Spot Illustration 与空状态

### 卡片 hero / 场景页

| 场景 | asset | 建议尺寸 |
|---|---|---:|
| DDL 冲刺 | `om_spot_deadline_sprint` | 160pt |
| 羽毛球 | `om_spot_badminton` | 160pt |
| 研讨室 | `om_spot_study_room` | 160pt |
| 比赛项目 | `om_spot_competition_project` | 160pt |
| 校园活动 | `om_spot_campus_event` | 160pt |
| 校园班车 | `om_spot_campus_shuttle` | 160pt |

### Empty / Recovery

| 状态 | asset | 建议尺寸 |
|---|---|---:|
| 今天为空 | `om_empty_today` | 160pt |
| 暂无公开局 | `om_empty_public_gatherings` | 160pt |
| 暂无比赛 | `om_empty_competitions` | 160pt |
| 暂无消息 | `om_empty_messages` | 160pt |
| 离线 | `om_state_offline` | 160pt |
| 登录会话失效 | `om_state_session_expired` | 160pt |

`OMStateView` 可按具体业务状态注入对应图片；错误标题、恢复动作和重试按钮继续使用 SwiftUI。

## 11. App Icon 合成

`om_brand_gap_mark_active` 可作为 App Icon 合成的中心图形，但不要直接把透明 PNG 放入 Apple App Icon 槽位：

1. 创建 1024×1024、完全不透明的 `#010001` 底图。
2. 将 `om_brand_gap_mark_active` 居中，保留足够安全区；可由 SwiftUI / Core Graphics 添加受控 cyan 光感。
3. 合成后确认所有像素 alpha=255，再生成 AppIcon 所需尺寸。
4. 不在图标中加入文字、数字或动态二维码。

