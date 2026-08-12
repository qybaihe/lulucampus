# Gemini UI Handoff · ONE MORE iOS

## 冻结结果

- 原生 SwiftUI，iOS 17+；未嵌入返回 HTML。
- 返回稿 36/36 已实现、截图并独立复核；正式节点 74/74，额外 `B12.2` / `MSG` 保留。
- Fidelity fresh Round 4：`major 0 / minor 26 / pass 10`。36/36 运行画板与 8/8 状态画板均由最终产品源码树重新构建捕获；minor 均为非阻断的字体渲染、系统安全区或像素级差异，详见 `/Users/baihe/Documents/compusone/ios/FIDELITY_REVIEW.md`。
- 唯一阿凑形象为 `aiia-pink-girl-business-v1` 粉发女孩；旧橙色 `export/assets/azou.png` 未进入 App。

## 事实源与产物

| 项 | 绝对路径 |
|---|---|
| 返回稿 | `/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/` |
| 设计截图 | `/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/screens/` |
| Simulator 36 图 | `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/runtime/` |
| Runtime 总览 | `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/RUNTIME_CONTACT_SHEET.png` |
| 8 异常态 | `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/STATE_EVIDENCE_CONTACT_SHEET.png` |
| 三尺寸布局 | `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/layout/LAYOUT_CONTACT_SHEET.png` |
| Screen Map | `/Users/baihe/Documents/compusone/ios/SCREEN_MAP.md` |
| Design System | `/Users/baihe/Documents/compusone/ios/OneMore/Core/DesignSystem/` |
| 粉发阿凑 | `/Users/baihe/Documents/compusone/ios/OneMore/Resources/AzouFrames/` |
| 动效证据 | `/Users/baihe/Documents/compusone/ios/artifacts/motion/` |

## 视觉 token

- Background `#010001`。
- Cyan `#00FFE1`；Magenta `#FF4FD3`。
- 白色 opacity ladder 用于 surface/border/text。
- Radius：8 / 20 / 32 / pill。
- 字体使用系统 PingFang/SF，按 Dynamic Type 运行；核心标题为 rounded/heavy。
- `OMPageBackground`、`OMGlassPanel`、`OMActionButton`、`OMSourceChip`、`OMGreeting` 等组件集中在 DesignSystem，业务页不另起主题。

## 导航与 CTA

- 五个视觉主入口冻结为：`今天 / 比赛 / ⊕差一个 / 消息 / 我`。
- `公开局 / 我的局 / 搭子关系` 从 Today/Profile/Message 的二级业务入口到达。
- 36 返回态中的主要 CTA 用 `PrototypeActions` 进入目标状态；`.named` 行为必须展示确定性结果，不存在空闭包。
- 真实业务 UI 使用 FastAPI Repository、系统 Share/OpenURL/EventKit/权限，不以静态提示冒充成功。

## 后续视觉修改规则

1. 先更新 DesignSystem token 或组件，不在单页复制颜色和玻璃面。
2. 返回稿状态改动后，同步 `SCREEN_MAP.md` 并重拍对应 runtime 图。
3. 重新执行 Fidelity checklist；major 必须保持 0。
4. 阿凑只能来自选定目录；展示宽度不超过 170pt；动画遵守每帧时长与 Reduce Motion。
5. 原型中的“21 场”、人数、日期、确认进度和聊天文案是视觉 mock，业务画面始终使用服务端事实。
