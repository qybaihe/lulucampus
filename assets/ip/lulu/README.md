# Lulu 美术资产 · 从 Lulu's Kitchen 复用

> 拷入时间：2026-08-12
> 来源：`~/Documents/HKphysical/ShiguangKitchen-iOS`（Lulu's Fridge / Lulu's Kitchen）
> 角色：「差一个 / ONE MORE」的 IP 形象与视觉系统基线，替换原 aiia 粉发少女（阿凑）

## 目录

| 目录 | 内容 | 可用性 |
|---|---|---|
| `atlases/` | 12 个 1254×1254 状态图集（2×2 四帧精灵表） | 6 个可直接用，6 个厨房专用作废 |
| `manifest/lulu-motion.v1.json` | 动效清单 | 需按新状态改写 |
| `brand/` | App 图标 1024/512、横向 lockup、品牌展示图 | 图标需重做（含冰箱元素），lockup 可参考 |
| `docs/` | 动效系统、状态矩阵、生成注记、锚点 QA | 架构可直接复用 |
| `tools/` | 帧锚点注册 + 色键抠图 | 可直接用 |
| `style-reference/` | 白边贴纸风格基准 | 生成新贴纸的比对基准 |

## 图集可用性

**可直接用（6）**
`LuluCoreStatesAtlas`（含 idle / concern / celebrate 等核心态）、
`LuluHomeIdleAtlas`、`LuluHomeListeningAtlas`、`LuluHomeThinkingAtlas`、`LuluHomeReplyAtlas`

**厨房专用，本项目作废（6）**
`LuluInventoryScanAtlas`、`LuluInventoryReviewAtlas`、`LuluRecipePlanAtlas`、
`LuluShoppingOrganizeAtlas`、`LuluCookingGuideAtlas`、`LuluDeviceConnectAtlas`、`LuluKitchenRolesAtlas`

**需新生成（6）**
`intent.card`、`pool.waiting`、`confirm.gather`、`action.preview`、`action.executing`、`exit.bow`

提示词见 `docs/14_素材生成交接提示词.md`。

## ⚠️ 两个必须知道的坑

### 1. `brand/BRAND_README.md` 的色板已过时

那份文档写的「叶绿 `#33964F` / 柑橘橙 `#F5992E` / 番茄红 `#E64538`」是**被废弃的旧色板**。
出码事实源是 `ShiguangKitchen/Core/DesignSystem/KitchenDesign.swift` 的 `KitchenPalette`，
七色、只有一个强调色：

```
canvas #F6F4EC   paper #FFFDF8   ink #1F2D25   yellow #F6C945
sage   #5D6B63   line  #DCE3D9   mist #CBD4CC
```

布局常量 `KitchenLayout`：radius 8 / 16、控件高 44、页边距 20、tabbar 62。

**本项目的语义色映射**：已具备 = 墨线实框（不上色）；缺口 = `yellow #F6C945` 实底。
刻意不用红——红会被读成「错误」，而缺口是邀请。

另注：`mist #CBD4CC` 在 `paper` 上只有约 1.8:1 对比度，**不能用于可点击标签**（Tab 文字、按钮），
只能做纯装饰分隔。可点击文字最低用 `sage`。

### 2. 不要照搬 `docs/STATE_MATRIX.md` 的优先级表

Lulu's Kitchen 把 Lulu 当**常驻陪伴**：每个 Tab 的 idle 态都有 Lulu，首页 hero 240–300pt，
品牌文档原话是 "emotional recognition and companionship"。

「差一个」的红线 17 禁止「AI 主动闲聊、人格养成或维持活跃度的机制」，
阿凑设定是「越早退场越好」。**形象整套复用，但出场策略必须反过来写**：
Lulu 只在意图澄清、招募、确认、执行几个节点出现，办完就消失，不做 idle 常驻，
局内群聊（E14）明确不出场。

允许 / 禁止的完整边界见 `docs/13_功能全量清单与美术需求.md` 第一节。

## 可直接复用的工程资产

- **placement scale 表**（`docs/STATE_MATRIX.md` 末段）：hero 240–300pt / page header 96–140pt /
  空错态 140–190pt / 确认卡 72–96pt / 消息头像 36–48pt。
  这张表直接修掉了原生 App 的 bug——D1 里阿凑缩成看不清的小色块就是因为没有它。
- **双锚点注册**（`tools/register_lulu_frames.py`）：muzzle + foot baseline，动道具不位移角色。
- **色键抠图**（`tools/remove_chroma_key.py`）：原管线脚本已丢失，按 `docs/GENERATION_NOTES.md`
  记录的参数（显式色键、软边、阈值 40/160、去溢色）重建并跑通冒烟测试。
