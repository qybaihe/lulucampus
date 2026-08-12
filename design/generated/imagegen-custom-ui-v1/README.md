# ONE MORE ImageGen Custom UI v1

为 `/Users/baihe/Documents/compusone` 原生 SwiftUI iOS App 生成的定制位图 UI 素材包。

## 交付统计

- 11 张最终 3×2 ImageGen 母版
- 66 个 512×512 RGBA master PNG
- 198 个 Lanczos 运行尺寸 PNG
- 11 组 512px master contact QA 预览
- 11 组 24px / 32px / 40px 深色背景 QA 预览
- manifest、机器 QA、集成映射、QA 报告和总览图齐全

## 目录

```text
source-sheets/
  chroma/          ImageGen 原始绿幕母版与保留版本
  transparent/     remove_chroma_key 结果与定向修复版本
masters/           66 个 512×512 RGBA master
runtime/
  tab/
  tool/
  feature/
  state/
  ornament/
  spot/
previews/          每批 QA、总览和 66 项索引
prompts/           每批最终规范化提示词
scripts/           可重复构建脚本
manifest.json      66 项资产清单
qa-data.json       自动 QA 明细
ASSET_INTEGRATION_MAP.md
QA_REPORT.md
README.md
```

## 关键路径

- 输出根目录：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/`
- Masters：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/masters/`
- Runtime：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/runtime/`
- Manifest：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/manifest.json`
- 集成映射：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/ASSET_INTEGRATION_MAP.md`
- QA 报告：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/QA_REPORT.md`
- 最终总览：`/Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/previews/FINAL_CONTACT_SHEET.png`

## 重新构建派生文件

```bash
cd /Users/baihe/Documents/compusone
python /Users/baihe/Documents/compusone/design/generated/imagegen-custom-ui-v1/scripts/build_assets.py
```

脚本读取已经选定的透明 Sheet，固定等分、生成 master / runtime / preview / manifest / QA 数据；不调用 ImageGen，不修改 SwiftUI 业务代码。

## 透明底处理

最终流程使用内置 ImageGen 绿幕源和系统 helper：

```bash
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" \
  --input SOURCE.png \
  --out TRANSPARENT.png \
  --auto-key border \
  --soft-matte \
  --transparent-threshold 12 \
  --opaque-threshold 220 \
  --despill
```

所有最终 master 的四角 alpha 均为 0，绿色残边检测为 0。

## 集成优先级

1. Home Bar idle / active 两套与中央“差一个”。
2. 首页高频 ToolTile：课表、DDL、研讨室、体育、班车、活动。
3. 业务生命周期：等待、预览、执行、成功、调整、补位。
4. 公开局、我的局、关系、比赛组队、协作。
5. 信任 / 隐私 / 账号与主理人。
6. Ornament 和 Spot / Empty Illustration。

## 边界

- 所有实际文字仍由 SwiftUI 渲染。
- 动态二维码仍由运行时生成。
- 唯一人物资源仍为 `/Users/baihe/Documents/compusone/assets/ip/selected/aiia-pink-girl-business-v1/` 的粉发女孩 57 帧资源。
- 本交付未修改 `/Users/baihe/Documents/compusone/ios/OneMore/` 下业务代码。

