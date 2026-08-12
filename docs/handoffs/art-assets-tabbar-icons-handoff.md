# 美术素材交接 · 底部 Tab Bar 定制图标（5 个 Tab × 2 态，共 10 张）

> 交接对象：新线程的生成 Agent
> 发起日期：2026-08-12
> 范围：iOS App 底部 5 个主 Tab 的定制图标，替换现役 SF Symbols。**不涉及**功能贴纸（S1–S11 共 65 张已齐备）与 Lulu 动作图集（12 个 clip 已齐备）
> 风格基准：`assets/ip/lulu/style-reference/style-reference.jpg` + 贴纸成品 `assets/ip/lulu/generated/2026-08-12/stickers/S1–S11/`

---

## 1. 任务

当前底部 Tab Bar 用的是系统 SF Symbols（sparkles / figure.2 / plus.circle.fill / message / person），是全套设计里**唯一不是定制的视觉元素**，与页面的贴纸语言脱节。本批为 5 个 Tab 各生成「选中 / 未选中」两态图标，共 10 张，让 Tab Bar 也进入 Lulu 视觉体系。

**与贴纸批的关键差异（务必读完再生成）：**

- Tab 图标渲染尺寸只有 **25pt（@3x ≈ 75px）**，贴纸的 5% 白边在这个尺寸会糊成一团 → 本批**不要白色切边**，改用**粗描边剪影**保证小尺寸可读性
- 主体细节必须极简：每个图标**一个主体、一种强调色**，禁止多物体组合
- 未选中态不是「变淡的全彩版」，而是**独立的灰绿线稿版**（见第 4 节）

## 2. 当前视觉系统分析（生成的依据）

### 2.1 七色体系（不新增颜色）

| token | 值 | 语义 | Tab 图标中的用法 |
|---|---|---|---|
| `--paper` | `#F6F4EC` | 页面画布 · 暖纸 | Tab Bar 底色（card 92% 透明叠在 paper 上） |
| `--ink` | `#1F2D25` | 正文标题 · 深墨绿黑 | **选中态主色**（描边与主体） |
| `--yolk` | `#F6C945` | 唯一强调 · 缺口 / 主行动 | **选中态点缀**；「差一个」中置按钮的主色 |
| `--card` | `#FFFDF8` | 卡片表面 | 图标内部留白面 |
| `--mist` | `#5D6B63` | 次要文字 · 灰绿 | 未选中态文字色 |
| `--line` | `#DCE3D9` | 描边分隔 | — |
| `--sage` | `#CBD4CC` | 次级行动 / 弱强调 | **未选中态图标主色** |

### 2.2 语义硬规则（不可违反）

- **蛋黄 = 缺口 / 主行动**，全屏最高视觉权重 → 只有「差一个」（产品的核心动作）可以大面积用蛋黄；其余 4 个 Tab 的蛋黄只能是点缀（≤20% 面积）
- **墨绿黑 = 已就位 / 已具备** → 选中态的主体色
- 缺口禁止用红色表达；本批图标**全程无红色**
- 未选中态用 sage/mist 灰绿系，**禁止用纯灰 #999 之类体系外颜色**

### 2.3 造型语言

- 半写实手绘卡通：圆润几何、粗描边（256px 画布下约 10–12px 墨绿描边）、左上柔光、轻纸张颗粒
- 圆角优先：所有转角走大圆角，与产品 8/14/20/28/pill 圆角阶梯同语言
- Lulu 形象：白色圆胖水豚、蛋黄小领结、极简豆豆眼（参考 `S10/lulu-face.png`）

## 3. 图标概念设计（5 Tab × 2 态）

| Tab | 当前 SF Symbol | 定制概念 | 选中态（active） | 未选中态（inactive） |
|---|---|---|---|---|
| 今天 `today` | sparkles | **小太阳从便签纸后升起**：蛋黄半圆太阳 + 卡色便签纸（纸上两条墨绿横线） | 全彩：墨绿描边 + 蛋黄太阳 | 灰绿线稿：同一构图，仅 sage 描边、无填充 |
| 活动 `activity` | figure.2 | **圆桌两侧各一把椅子**（呼应「比赛 + 组局」的聚集语义）：俯视小圆桌，桌面蛋黄 | 全彩：墨绿桌椅 + 蛋黄桌面 | 灰绿线稿 |
| 差一个 `create` | plus.circle.fill | **蛋黄圆形徽章 + 墨绿加号**：产品核心动作，唯一允许大面积蛋黄的图标；视觉重心略高于其他图标 | 蛋黄实心圆 + 墨绿粗加号 | 墨绿线稿圆 + 加号（不填蛋黄，保持层级：未选中时它不抢戏） |
| 消息 `messages` | message | **圆胖对话气泡**：卡色气泡身、墨绿描边，左下小尾巴，气泡内一个蛋黄小圆点 | 全彩 | 灰绿线稿 |
| 我 `profile` | person | **Lulu 正面头像**：白色圆胖水豚头 + 蛋黄小领结（与 S10/lulu-face.png 同形象） | 全彩 | 灰绿线稿轮廓（保留领结线稿） |

设计要点：

- 5 个图标并排时，蛋黄出现频率应为「2 次点缀 + 1 次主体」（今天/消息点缀、差一个主体），活动与我以墨绿为主——这样蛋黄的稀缺性才保得住
- 每个图标主体占画布约 68–72%，四周留白均匀；5 个图标的视觉重量（墨色面积）要一致，避免某个图标显得特别大或特别重
- 「差一个」允许比其他 4 个大约 12%（它是主行动）

## 4. 硬性规范（违反即重做）

- 256×256 画布，纯绿 `#00FF00` 背景（色键抠图用），2×3 六宫格 sheet（第 6 格留空）
- **无白色贴纸切边**（与贴纸批的最大区别）；主体用约 10–12px 墨绿描边收口
- 无文字、无数字、无品牌 logo、无表情脸（Lulu 头像的豆豆眼除外）、无阴影、无背景杂物
- 配色只允许第 2.1 节七色及其同色系明暗延展，禁止高饱和红蓝紫
- active / inactive 两版**构图完全一致**，只差配色工艺（inactive = sage `#CBD4CC` 描边 + 无填充或 20% sage 平涂）
- 成品规格：512×512 PNG，透明背景，主体居中、四周留白约 14%

## 5. 生成提示词（可直接粘贴）

### 5.1 Active 全彩版（5 格 + 1 空格）

```text
在一张正方形 2×3 六宫格中生成五个独立的 iOS 底部标签栏图标（第六格留空），采用统一的半写实手绘卡通风格，略带纸张质感，统一左上柔光。每个图标为单一主体、粗描边剪影风格：约 10px 深墨绿 #1F2D25 描边，大圆角，造型极简，无白色贴纸切边。配色取自暖纸色系：深墨绿 #1F2D25、蛋黄 #F6C945、暖纸 #F6F4EC、卡其白 #FFFDF8。严格每格一个主体，不重叠，不加文字、数字、品牌、表情脸、阴影或额外物体；纯绿色 #00FF00 背景。
五个主体依次为：
1. 小太阳从便签纸后升起：蛋黄半圆太阳，下方一张卡其白便签纸，纸上有两条墨绿短横线；
2. 俯视小圆桌，两侧各一把圆润椅子：墨绿桌椅轮廓，桌面填蛋黄；
3. 蛋黄实心圆形徽章，中央一个粗壮的墨绿加号（整体比其他五格大约 12%）；
4. 圆胖对话气泡：卡其白气泡身、墨绿描边、左下小尾巴，气泡内中央一个蛋黄小圆点；
5. 白色圆胖卡通水豚正面头像：极简豆豆眼、蛋黄小领结、墨绿轮廓线。
```

### 5.2 Inactive 灰绿线稿版（5 格 + 1 空格）

```text
在一张正方形 2×3 六宫格中生成五个独立的 iOS 底部标签栏图标的未选中态（第六格留空），与全彩版构图完全一致，但改为单色线稿工艺：仅使用灰绿 #CBD4CC 描边（约 10px），内部不填充或仅 20% 透明度灰绿平涂，无蛋黄、无墨绿填充。半写实手绘卡通风格，大圆角，造型极简，无白色贴纸切边。严格每格一个主体，不重叠，不加文字、数字、阴影或额外物体；纯绿色 #00FF00 背景。
五个主体依次为：
1. 小太阳从便签纸后升起（太阳与便签纸均为线稿）；
2. 俯视小圆桌与两侧椅子（线稿）；
3. 圆形徽章与中央加号（线稿，不填蛋黄）；
4. 圆胖对话气泡与内部小圆点（线稿）；
5. 白色圆胖卡通水豚正面头像轮廓（线稿，保留小领结线稿）。
```

## 6. 后处理与接入流程

```bash
# 1. 色键抠图（每张 sheet）
python3 assets/ip/lulu/tools/remove_chroma_key.py raw/tabbar-active-chroma.png out/tabbar-active.png --key "#00ff00" --low 40 --high 160

# 2. 拆格 + 512px 居中（参考 assets/ip/lulu/tools/build_generated_delivery.py 的 split/fit 逻辑）

# 3. 命名与落位（目录不存在则新建）
#    ios/OneMore/Resources/LuluGenerated/TabBar/
#      tab-today-active.png / tab-today-inactive.png
#      tab-activity-active.png / tab-activity-inactive.png
#      tab-create-active.png / tab-create-inactive.png
#      tab-messages-active.png / tab-messages-inactive.png
#      tab-profile-active.png / tab-profile-inactive.png

# 4. 加入 Xcode target 资源（project.pbxproj 的 PBXBuildFile / PBXFileReference /
#    PBXGroup(TabBar) / PBXResourcesBuildPhase，参照 Stickers S1–S11 条目）

# 5. 代码已就绪，无需改动：
#    ios/OneMore/App/RootView.swift 的 OMTabIcon 会按
#    "tab-<rawValue>-<active|inactive>.png" 自动加载位图；
#    资源缺失时自动回退到原 SF Symbol，可逐张灰度替换。
```

## 7. 验收清单

- [ ] 10 张成品全部 512×512 透明 PNG，无白边、无文字、无阴影
- [ ] active / inactive 同构图，仅配色工艺不同
- [ ] 蛋黄只出现在：今天（点缀）、消息（点缀）、差一个（主体）；其余图标纯墨绿/灰绿
- [ ] 25pt 实机尺寸下 5 个图标剪影清晰可辨、视觉重量一致（截图对比）
- [ ] 「差一个」明显是视觉重心，但选中其他 Tab 时它退为线稿不抢戏
- [ ] 与 S1–S11 贴纸并排，风格肉眼一致
- [ ] 构建通过，`xcodebuild test -only-testing:OneMoreTests` 全绿

## 8. 参考路径

| 用途 | 路径 |
|---|---|
| 风格基准图 | `assets/ip/lulu/style-reference/style-reference.jpg` |
| 贴纸成品（对照风格） | `assets/ip/lulu/generated/2026-08-12/stickers/S1–S11/` |
| Lulu 头像参照 | `assets/ip/lulu/generated/2026-08-12/stickers/S10/lulu-face.png` |
| 抠图工具 | `assets/ip/lulu/tools/remove_chroma_key.py` |
| 拆格/交付工具 | `assets/ip/lulu/tools/build_generated_delivery.py` |
| Tab 图标落位 | `ios/OneMore/Resources/LuluGenerated/TabBar/` |
| 自动加载代码 | `ios/OneMore/App/RootView.swift`（OMTabIcon） |
| 设计 token | `design/received/2026-08-12-one-more-lulu-frontend/export/css/tokens.css` |
