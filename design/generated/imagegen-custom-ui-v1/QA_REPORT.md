# ONE MORE ImageGen Custom UI v1 — QA 报告

## 结论

**通过：11 / 11 批，66 / 66 个透明 master，198 / 198 个运行尺寸。**

机器可读明细：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/qa-data.json`

## 执行摘要

- 内置 ImageGen 调用：12 次。
  - Sheet 01–11：11 个最终批次。
  - Sheet 04：额外 1 次定向编辑尝试并保留版本；最终只修复首格缺少的第三个已占节点，其余五格采用 Sheet 04 v1。
- 透明流程：`remove_chroma_key.py`，`--auto-key border --soft-matte --transparent-threshold 12 --opaque-threshold 220 --despill`。
- Sheet 03 额外保留一次 `--edge-contract 1` 对照版；最终版经视觉对比采用边缘更完整的 v1 透明结果。
- 母版拆分：固定 1536×1024 → 精确 3×2 → 每格 512×512；最终 PNG 始终保留 512×512 统一安全画布，不输出 tight-trim 文件。
- 视觉尺寸归一：每项可见轮廓最大跨度为 73.24%–73.44%，位于 70%–76% 门禁内；统一安全边距为 68px。
- 下采样：Pillow Lanczos，RGBA 预乘 alpha 路径，输出 `@1x` / `@2x` / `@3x`。

## 自动门禁结果

| 检查项 | 结果 |
|---|---:|
| 固定批次数 | 11 / 11 |
| 每批对象数 | 6 / 6 |
| 独立 master | 66 / 66 |
| RGBA master | 66 / 66 |
| 四角 alpha 全为 0 | 66 / 66 |
| 运行尺寸文件 | 198 / 198 |
| 24px 可见像素 | 最低 70px，全部通过 |
| `#010001` 深色背景平均主体亮度 | 156.26–221.04，全部通过 |
| 检出的绿色残边像素 | 0 |
| 裁切到单元格边缘 | 0 |
| 光学跨度 70%–76% | 66 / 66 |
| 综合 `qa_status=pass` | 66 / 66 |

## Home Bar idle / active 几何一致性

alpha mask IoU（1.0 表示完全相同）：

| 配对 | IoU |
|---|---:|
| Today | 0.9560 |
| Competitions | 0.9703 |
| Create | 0.9630 |
| Messages | 0.9739 |
| Profile | 0.9750 |
| Brand gap mark | 0.9446 |

全部配对保持同一轮廓、格位和光学尺寸；差异来自 active 颜色涂层边缘与轻微高光。

## 调色检查

- active Home Bar 中与 `#00FFE1` 最近的像素色差距离为 19.5–30.9；与 `#FF4FD3` 最近的像素色差距离为 3.0–9.4。
- 单态业务素材均包含接近 cyan token 的主强调；magenta 只用于焦点、缺口、连接或待确认节点。
- idle Home Bar 保持冷白 / 浅灰 / 少量暗 cyan，未引入大面积 magenta。

## 视觉人工复核

- 顺序：11 张均按第一行 1–3、第二行 4–6 固定格位。
- 文字：未发现素材内文字、字母、数字、Logo 文案或水印。
- 人物：未生成新角色、头像或替代阿凑；仅保留需求明确指定的匿名几何人物节点 / 轮廓。
- 现有 IP：未覆盖 `/Users/baihe/Documents/compusone/assets/ip/selected/aiia-pink-girl-business-v1/` 内任何文件。
- 二维码：仅生成空扫描框，未生成动态二维码本体。
- 小尺寸：每批均生成 24px / 32px / 40px 深色背景预览并完成识别检查。
- 深色融合：冷白轮廓和 cyan 节点在 `#010001` 页面上均保持足够对比。

## 定向修复记录

1. `om_feature_public_gathering`：首版只有两个已占节点；先执行 ImageGen 定向编辑并保留 v2，因其余格发生漂移而未采用。最终复用同一首格中的已批准节点造型补足第三个已占节点，其他五格仍来自 Sheet 04 v1。
2. Sheet 03 的相邻格微小边缘片段，以及 `om_feature_prep_partner` / `om_feature_intent` 的格边安全区，使用确定性单格修复；未更改其他格语义。
3. 所有源母版、透明过程版和修复版均保留，没有覆盖旧版本。

## QA 预览

- 总览：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/previews/FINAL_CONTACT_SHEET.png`
- 66 项索引：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/previews/ALL_66_ASSET_INDEX.png`
- 每批 512px 单元格 master contact：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/previews/sheet-XX-master-contact-512-cells-dark.png`
- 每批 24 / 32 / 40px：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/previews/sheet-XX-24-32-40px-dark.png`

