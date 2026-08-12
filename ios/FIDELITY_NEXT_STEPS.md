# ONE MORE Fidelity Next Steps（Round 4）

**当前 Gate 2 状态：通过。Round 4 为 `major 0 / minor 26 / pass 10`，没有 screenshot-level fidelity blocker。**

Round 4 已使用最终产品源码树重新构建与捕获，36/36 运行画板和 8/8 状态画板均为新鲜证据。以下工作用于继续压缩 minor 与防止回归，不影响当前 Gate 2 结论。

## P1：保持 bottom action 回归门禁

可靠 bottom action slot 已关闭 D1、D4、E3、E5、B7.1 的首帧阻断。后续改动必须保持：

1. D1“交给阿凑”完整位于 home indicator 上方。
2. D4 分享、满员、撤回三动作均在首帧。
3. E3 只显示 4/4 状态和一个主 CTA，且动作位于底部区域。
4. E5 参数在正文，授权/修改在底部主次动作区。
5. B7.1 官方报名 CTA 的图标、文字和点击框完整。
6. 有 Tab 页面同时为 Tab 与 CTA 预留安全区。

建议把“按钮 frame 完全包含于 viewport/safe area”加入 UI 截图断言，禁止重新用大 `Spacer(minLength:)` 定位动作。

## P2：粉发女孩的小尺寸可辨识度

9 个设计稿可见 IP 位已经统一，旧橙图为 0；剩余问题只是全身素材在 38–46 pt 位过窄。

1. 为 B1、D1、D2、E7、E14、B4.1、MSG 使用同一来源的专用安全裁切或缩略图。
2. 去掉透明边缘，让头部/上半身在小位占更多像素；保持发色、服装和轮廓一致。
3. A2/E10 可适度增大角色框，让主视觉重量更接近原型，但不改变文案和动作几何。
4. 继续保留动画未解码时的同步静态 fallback。
5. 每轮继续执行橙色像素审计，期望关键图和状态图均为 0。

## P3：Glass、密度与局部几何收口

### Surface 与卡片密度

- A3、A4、A6、B1、C1、B12、D3、E5、E6、E7、E1、M1、M3：降低中灰 surface 的不透明感，让 cyan/magenta 背景光晕更接近设计穿透效果。
- D3：增加 key/value 行垂直 padding，恢复设计卡高，同时维持单卡归组。
- C1/B12/M1：收紧或校准列表卡间距，不改变 24 场真实数据。

### Bottom action 微调

- D1、E3、B7.1：动作区相对基准约高 50 px，可在不触碰 safe area 的前提下向下校准。
- D4、E5：动作区约高 20–40 px；保持所有按钮完整，不能以裁切换取像素位置。
- B7.1：把 external-link 图标从文字前调整到设计稿的文字末尾。
- M3：整体内容比设计下移约 70–80 px；收紧顶部/区块间距，同时保留 CTA 后免责声明完整可见。

### 其他局部项

- TABLE：校准圆桌直径与纵向中心，恢复 4/4 cyan 线框确认条。
- E17：扩大 sheet 宽度并将上沿下移约 20 px；保持底部短 sheet。
- G2：校准 sheet 宽度、上沿、缺口卡 padding 和分享图标重量。
- E1：弱化卡内“进入对话”次动作并收紧搭子卡高度。

## P4：状态证据回归

8 类状态证据已补齐并在 Round 4 重新捕获。后续 Design System 或网络状态改动后，重新覆盖：

- `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/loading.png`
- `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/empty.png`
- `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/network-error.png`
- `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/offline.png`
- `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/permission-denied.png`
- `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/session-expired.png`
- `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/duplicate-tap.png`
- `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/stale-state.png`

保持 `state-evidence-capture.csv`、`state-evidence-sha256.txt` 与 `STATE_EVIDENCE_CONTACT_SHEET.png` 同步；任何状态都不得残留过期成功内容或出现另一套默认系统视觉语言。

## P5：强制证据新鲜度与来源绑定

Round 4 的最终绑定基线：

- 产品源码树：`8857dedffff006e66f98b4cd8ab367a7018a4ce176796e90343d9c1203befc25`（144 文件）。
- Debug Simulator 可执行文件：`44986a13c702a07dc5c47e7627cfd80ee63897ace5cceb0034996cd287041e52`。
- 设计来源 manifest：`28c08107cc6dad426c980f865b0c446c1110e4c1b296fa24b9d4c15f351fc8ec`。
- 运行 contact sheet：`8112156a5a976204740c1bdd3550260a10ee00f332698090a8dfad9e639cff6a`。
- 状态 contact sheet：`5c4e904a0d04c7cb73e6ca40e6943a5c671ba9e6008d7969e8a7ce09dafbebe0`。
- 索引：`/Users/baihe/Documents/compusone/ios/artifacts/logs/visual-evidence-final-r4.json`。

后续任何进入 `ios/OneMore/**`、`ios/Config/**`、`ios/project.yml` 或 `ios/OneMore.entitlements` 的变更，都使以上视觉证据失效；必须先重新构建，再重新捕获 36+8，并生成新的源码、二进制、逐图和 contact sheet 哈希。禁止只更新时间标签或复用旧 PNG。

## 后续视觉回归流程

仅在 SwiftUI/Design System/IP 资源发生影响布局的变化后重跑完整回归：

1. 固定 iPhone 15 Pro / iOS 17。
2. 生成产品源码 scope 的逐文件 manifest 与 tree hash。
3. 从该源码树 fresh build，记录实际 App 可执行文件 SHA-256。
4. 覆盖 36 张 `/Users/baihe/Documents/compusone/ios/artifacts/screenshots/runtime/*.png`。
5. 更新 `runtime-screenshot-capture.csv`、`runtime-screenshot-sha256.txt` 和 `RUNTIME_CONTACT_SHEET.png`。
6. 覆盖 8 张状态图及其 capture CSV、hash manifest、contact sheet。
7. 生成类似 `visual-evidence-final-r4.json` 的单一证据索引，把设备、源码、二进制、设计与 PNG 全部绑定。
8. 确定性缩放到 402×874，重跑 RMSE/SSIM-D 和橙色像素审计。
9. 重点回归 D1、D4、E3、E5、B7.1、M3 的动作完整性，以及 9 个 IP 位。
10. 独立 Fidelity Review 重新判级；只有出现新的 screenshot-level major 才重新关闭 Gate 2。

## Gate 2 持续成立条件

- 36/36 映射完整，24 场真实数据不回退。
- screenshot-level `major = 0`。
- 所有设计主 CTA 首帧完整可见、主次权重成立。
- 不出现拆卡、空 divider 卡、窄竖排标题或 Tab/底边覆盖。
- 9/9 可见 IP 位均为同一粉发女孩，旧橙图持续为 0。
- E3 保持 4/4 单一动作，E17 保持底部短 sheet。
- 8 类状态证据持续可重复生成。
- 捕获日志和逐文件哈希匹配，证据捕获时间晚于绑定源码与二进制；产品 scope 改动后必须 fresh recapture。

**Round 4 已满足以上条件，Gate 2 通过；剩余仅为 minor 收口。**
