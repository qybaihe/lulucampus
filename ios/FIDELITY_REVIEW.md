# ONE MORE iOS Fidelity Review（Round 4，最终新鲜证据）

- 复核日期：2026-08-12（Asia/Shanghai）
- 复核角色：独立 Fidelity Review；未参与本轮 SwiftUI 实现
- 设计基准：`/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/screens/*.png`
- 运行证据：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/runtime/*.png`
- 36 屏捕获记录：`/Users/baihe/Documents/compusone/ios/artifacts/logs/runtime-screenshot-capture.csv`
- 运行总览：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/RUNTIME_CONTACT_SHEET.png`
- 状态证据：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/*.png`
- 状态捕获记录：`/Users/baihe/Documents/compusone/ios/artifacts/logs/state-evidence-capture.csv`
- 状态总览：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/STATE_EVIDENCE_CONTACT_SHEET.png`
- 最终证据索引：`/Users/baihe/Documents/compusone/ios/artifacts/logs/visual-evidence-final-r4.json`
- 设备证据：iPhone 15 Pro / iOS 17.0，截图 1179×2556（393×852 pt @3x）
- Round 4 捕获时间：2026-08-12 08:39:32 至 08:41:20（Asia/Shanghai）；36/36 运行行与 8/8 状态行均标记 `round=4`
- 基准画布：402×874；比较前将运行截图确定性缩放至 402×874

## Gate 结论

**Round 4 通过 Gate 2。36 个映射状态中：`major 0 / minor 26 / pass 10`。screenshot-level major 为 0。**

本轮是在所有影响画面的产品源码修改完成后，对同一最终源码树重新构建、安装、捕获与评审；它取代捕获时间早于后续源码修改的 Round 3 证据。新鲜证据没有发现回归，判级仍为 `0 / 26 / 10`。

已复核的关键关闭项：

1. **D1**：“交给阿凑”作为完整底部主 CTA 出现在首帧。
2. **D4**：“分享一张缺口卡 / 已经满员 / 撤回这个局”三动作均完整位于安全区内。
3. **E3**：保持正确 4/4 单一动作状态，状态摘要与唯一 CTA 位于底部动作区。
4. **E5**：“授权执行 / 修改参数”与正文分离，保持底部主/次动作权重。
5. **B7.1**：官方报名 CTA 完整显示，文字和点击框没有底边裁切。
6. **M3**：保持“列表 → CTA → 免责声明”的连续顺序，免责声明首帧可见。

同时确认：MSG 使用同一粉发女孩而非“阿”字头像；9 个设计稿可见 IP 位都使用同一角色；36 张关键运行图和 8 张状态证据中的旧橙色近似像素均为 0。

剩余 26 项均为 minor：主要是全身角色在小尺寸位过窄、glass 偏亮/偏实、部分卡片密度，以及 bottom action 相对设计高约 20–50 px。它们不改变页面类型、主层级、首帧可达性或 CTA 权重，不阻断 Gate 2。

## 最终证据与源码/二进制绑定

Round 4 的证据索引将截图明确绑定到设计来源、产品源码树与实际运行二进制：

| 对象 | SHA-256 / 数量 |
|---|---|
| 产品源码树（`ios/OneMore/**`、`ios/Config/**`、`ios/project.yml`、`ios/OneMore.entitlements`） | `8857dedffff006e66f98b4cd8ab367a7018a4ce176796e90343d9c1203befc25` / 144 文件 |
| Debug Simulator 可执行文件 | `44986a13c702a07dc5c47e7627cfd80ee63897ace5cceb0034996cd287041e52` |
| 设计来源 manifest | `28c08107cc6dad426c980f865b0c446c1110e4c1b296fa24b9d4c15f351fc8ec` |
| 运行截图 | 36/36；逐文件哈希见 `runtime-screenshot-sha256.txt` |
| 状态截图 | 8/8；逐文件哈希见 `state-evidence-sha256.txt` |
| 运行 contact sheet | `8112156a5a976204740c1bdd3550260a10ee00f332698090a8dfad9e639cff6a` |
| 状态 contact sheet | `5c4e904a0d04c7cb73e6ca40e6943a5c671ba9e6008d7969e8a7ce09dafbebe0` |

复核时再次验证：

- `final-product-source-sha256.txt` 的 144 个文件哈希全部匹配；按 manifest 顺序拼接文件哈希行后重算的 tree hash 与上表一致。
- 实际运行 App 的 `ONE MORE` 可执行文件哈希与 `visual-evidence-final-r4.json` 一致。
- `runtime-screenshot-sha256.txt` 36/36、`state-evidence-sha256.txt` 8/8 均可由当前 PNG 重算匹配。
- 两张 contact sheet 的当前文件哈希与证据索引一致。
- 运行捕获为 08:39:32–08:40:57，状态捕获为 08:41:05–08:41:20，均晚于产品源码树最后一次影响画面的修改；本评审只更新文档，不改变上述产品源码 scope。

因此，本轮视觉结论针对上述明确指纹的实际二进制，而不是旧截图或未构建源码。

## 评审方法

### 逐屏视觉判断

逐一检查 36 组设计/运行图，并检查 8 张状态图。判定标准：

- **major**：页面类型、主层级、卡片归组、主 CTA 完整可见性/位置权重、底部 sheet、IP 主视觉或核心信息密度发生实质变化。
- **minor**：主流程和主要区块一致，但间距、字体、玻璃透明度、圆角、次级图标、局部顺序或小型 IP 有清晰可见偏差。
- **pass**：区块顺序、主 CTA、导航和视觉权重一致，仅有状态栏时间、动态业务文案、原生字形或亚像素差异。

视觉判断覆盖：层级/区块顺序、间距、字号/字重、CTA、颜色/玻璃/圆角、Tab/Nav、图片/IP，以及空/错/加载状态。状态栏时间不计缺陷；运行展示 24 场比赛是 Definition of Done 要求，不回退到设计稿的过期“21 场”。

### 可复现 ImageMagick 辅助指标

以下指标以 0 为完全相同，仅用于定位，不替代视觉判断。A3 动态二维码、指定粉发女孩替换旧占位图、真实 24 场文案都会影响全屏像素值。

```bash
ROOT=/Users/baihe/Documents/compusone
ID=d1
magick "$ROOT/ios/artifacts/screenshots/runtime/$ID.png" \
  -resize '402x874!' "/tmp/$ID-runtime-402.png"
magick compare -metric RMSE \
  "$ROOT/design/received/2026-08-11-one-more-mobile-prototype/screens/$ID.png" \
  "/tmp/$ID-runtime-402.png" null:
magick compare -metric SSIM \
  "$ROOT/design/received/2026-08-11-one-more-mobile-prototype/screens/$ID.png" \
  "/tmp/$ID-runtime-402.png" null:
```

Round 4 的 36 组结果：

- 归一化 RMSE：范围 `0.113920–0.413151`，中位数 `0.196794`，均值 `0.203204`。
- ImageMagick SSIM 差异值：范围 `0.118128–0.338774`，中位数 `0.199991`，均值 `0.205794`。
- 与 Round 3 数值仅有截图时钟/渲染亚像素级变化；逐屏结构、判级与剩余项均未变化。
- D1/D4/E3/E5/B7.1/M3 的首帧动作与层级均由逐屏人工检查确认，不能用全屏指标替代这一结论。
- 逐屏数值和人工判定见 `/Users/baihe/Documents/compusone/ios/FIDELITY_CHECKLIST.md`。

### 橙色旧 IP 与粉发女孩审计

以统一 402×874 画布统计亮橙近似像素（`R>150, 55<G<210, B<135, R>1.08G, G>1.15B, R-G>20`）：

- 设计基准共 `10,435` 个橙色近似像素：A2 7,416；E10 1,198；B1 372；D1 332；B4.1 289；E7 289；D2 243；MSG 244；E14 52。
- Round 4 的 36 张运行截图合计 `0` 个橙色近似像素。
- Round 4 的 8 张状态证据合计 `0` 个橙色近似像素。

逐屏视觉确认结果：

- A2、E10 两个主视觉位均显示指定粉发女孩。
- B1、D1、D2、E7、E14、B4.1、MSG 七个小型位均显示同一全身素材。
- **9/9 可见 IP 位一致；废弃橙色阿凑为 0，红线通过。**
- 小尺寸全身素材仍显得窄，属于可读性 minor，不是资源不一致。
- 静态截图只证明首帧形象；57 帧序列、抢占、离屏、前后台及 Reduce Motion 由 Gate 3 的运行和录屏证据判断。

## 重点问题关闭审计

| 原 major | Round 4 | 关闭证据 |
|---|---|---|
| D1 | minor | 底部 cyan“交给阿凑”完整可见；剩余角色尺寸和约 50 px 纵向差。 |
| D4 | minor | 三动作完整且均在首帧；剩余 action stack 略高、glass 偏亮。 |
| E3 | minor | 4/4 状态与单 CTA 正确落底；剩余状态摘要样式和纵向差。 |
| E5 | minor | 主/次动作保持底部层级；剩余预览卡偏紧、surface 偏实。 |
| B7.1 | minor | 官方报名按钮及文字完整；剩余图标方向和约 50 px 纵向差。 |
| M3 | minor | CTA 与免责声明均可见且顺序正确；整体内容比设计下移、glass 偏亮。 |

## 8 类状态证据复核

8/8 文件存在、尺寸均为 1179×2556，捕获日志完整且标记 `round=4`。它们没有对应返回画板可做像素基准，因此按现有 Design System、状态语义、主动作和安全区一致性复核。

| 状态 | 文件 | 视觉结论 |
|---|---|---|
| loading | `loading.png` | 三段 skeleton、同步标题、spinner 和“不展示旧成功态”说明完整；与 glass 语言一致。 |
| empty | `empty.png` | 空态图标、标题、解释和“去看公开局”CTA 层级清晰。 |
| network error | `network-error.png` | 错误图标、说明和“重试”动作明确，没有残留成功态。 |
| offline | `offline.png` | 离线图标、15 分钟只读缓存说明和重试动作完整。 |
| permission denied | `permission-denied.png` | 日历权限卡、去系统设置主动作和“暂不”次动作完整。 |
| session expired | `session-expired.png` | 登录失效、恢复说明和“重新扫码”动作完整。 |
| duplicate tap | `duplicate-tap.png` | “提交已接收”与 disabled processing CTA 清楚表达重复触发被抑制。 |
| stale state | `stale-state.png` | 服务端状态变化说明和“刷新最新状态”动作完整。 |

**状态证据结论：8/8 已覆盖，未发现新的 screenshot-level major。**

## 跨屏视觉发现

### 1. 层级、归组与信息密度

- 36/36 文件映射有效；早期多子视图拆卡、空 divider 卡和窄竖排标题均未复发。
- D3、B12/B12.1、B4、B7、E16、M1/M3 的核心对象保持一体卡或一体列表。
- D3、A6、E5、E6、M1/M3 的运行卡片仍比设计紧或更实，均记为 minor。

### 2. CTA 位置与权重

- 设计要求的所有主 CTA 都在对应首帧完整可见；D1、D4、E3、E5、B7.1、M3 没有缺失或裁切。
- bottom action slot 消除了内容高度变化导致的首帧阻断。
- D1/E3/B7.1 约比基准高 50 px，D4/E5 约高 20–40 px；动作仍位于底部区域、主次权重正确，判 minor。

### 3. 颜色、玻璃面与圆角

- `#010001`、cyan、magenta、按钮渐变和背景光晕方向一致。
- 运行 surface 普遍比设计更接近不透明中灰；这是剩余 minor 最集中的全局项。
- TABLE 的确认条仍偏灰，圆桌几何略有偏差。

### 4. Tab / Navigation / Sheet

- 五入口 Tab、选中态、消息 magenta dot、返回按钮和标题栏一致。
- B7.1 CTA 完整位于 home indicator 上方。
- E17 保持底部短 sheet；只剩宽度与上沿小偏差。

### 5. 图片与唯一 IP

- 9 个可见位均为同一粉发女孩；MSG 不再有文字头像例外。
- 主位与小位都不存在旧橙图；小位可辨识面积仍可继续优化。

## 最终判定

- 36/36 文件映射：通过。
- 24 场真实业务事实：通过。
- 卡片归组与信息层级：通过。
- 所有设计主 CTA 首帧完整可见且权重成立：通过。
- E3 单一确认动作：通过。
- E17 底部短 sheet：通过。
- 9/9 粉发女孩 IP 位一致：通过。
- 废弃橙色阿凑：通过；关键图与状态图均为 0。
- loading/empty/error/offline/permission/session/duplicate/stale：8/8 已有新鲜视觉证据。
- 源码树、实际二进制、36+8 PNG 与 contact sheet 哈希绑定：通过。
- **screenshot-level major drift：0。Gate 2：通过。**

剩余 minor 和回归守则见 `/Users/baihe/Documents/compusone/ios/FIDELITY_NEXT_STEPS.md`。
