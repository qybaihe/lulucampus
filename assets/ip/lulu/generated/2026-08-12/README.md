# Lulu / OneMore 视觉素材交付 · 2026-08-12

依据 `docs/14_素材生成交接提示词.md`，使用内置 `image_gen` 生成，并以现有
Lulu 图集与白边贴纸为模板完成风格锁定。

## 已交付

- Lulu 新状态：`intent.card`、`pool.waiting`、`confirm.gather`、
  `action.preview`、`action.executing`、`exit.bow`
- 白边贴纸：S1–S11，共 65 张 512×512 透明 PNG；其中第二批 S7–S11
  新增 29 张
- Lulu 图集：写入 `assets/ip/lulu/atlases/Lulu*Atlas.png`
- 动效注册：写入 `assets/ip/lulu/manifest/lulu-motion.v1.json`
- iOS 可消费副本：写入 `ios/OneMore/Resources/LuluGenerated/`
- QA：首批 `qa/stickers-contact-sheet.jpg`，第二批
  `qa/stickers-batch02-contact-sheet.jpg`，全量对照
  `qa/stickers-all-s1-s11-contact-sheet.jpg`；机器验收数据为
  `qa/validation.json` 与 `qa/validation-batch02.json`

## 目录

| 目录 | 内容 |
|---|---|
| `raw/` | image_gen 原始品红/绿色键控源图 |
| `transparent-sheets/` | 抠图后的整张透明图 |
| `frames/` | 6 个 Lulu 状态各 4 帧，已做 muzzle + foot 注册 |
| `stickers/S1` … `stickers/S11` | 65 张单体透明贴纸 |
| `qa/` | 联系表及机器验收数据 |

## 重建

使用含 Pillow 与 NumPy 的 Python 环境执行：

```bash
python assets/ip/lulu/tools/build_generated_delivery.py
```

脚本会从 `raw/` 非破坏性重建透明图、逐帧图集、单体贴纸和 QA 文件。

第二批 S7–S11 在透明六宫格生成后执行：

```bash
.venv/bin/python assets/ip/lulu/tools/build_sticker_batch02_delivery.py
```

脚本拆分 3×2 六宫格、剔除跨格碎片、恢复墨绿主体不透明度、清理白边绿溢色，
并同步 29 张成品至 `ios/OneMore/Resources/LuluGenerated/Stickers/S7` … `S11`。

## 最终生成提示词

所有生成均逐字保留 `docs/14_素材生成交接提示词.md` 中对应条目的主体提示词，
只增加以下共享模板约束：

- Lulu：以 `LuluHomeIdleAtlas.png` 和 `LuluCoreStatesAtlas.png` 为身份、材质、
  比例和 2×2 布局参考；恰好四格；锁定相机、躯干中心和脚底线；纯
  `#ff00ff` 背景。
- 贴纸：以 `ingredient-stickers-batch01-sheet.png` 为半写实手绘、光照、质感、
  白边与 3×2 排布参考；恰好六格；纯 `#00ff00` 背景。
- S3 定向修订：打开的活页本纸面改为完全空白。
- S4 定向修订：强制 3 列 × 2 行，并移除门牌上的符号。
- S7–S11 的完整最终提示词与定向修订记录：
  `qa/stickers-batch02-prompts.md`。
