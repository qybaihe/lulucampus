# Ingredient Stickers · Batch 01

## 内容

2×3 六宫格首批食材：洋葱、西红柿、鸡蛋、牛奶、牛腩、胡萝卜。

## 视觉方向

- 参考 `source/style-reference.jpg` 的轻白边贴纸观感
- 半写实手绘卡通食材
- 统一光照、质感和视角
- 无表情、无文字、无品牌
- 每个主体带连续白色切边

## 生成与处理

- 生成方式：Codex 内置 ImageGen
- 源图：`source/ingredient-stickers-batch01-chroma.png`
- 背景：纯绿色色键背景
- 透明总图：`transparent/ingredient-stickers-batch01-sheet.png`
- 独立图：`transparent/*.png`
- 独立图规格：512×512 PNG，透明背景
- 预览：`preview/ingredient-stickers-batch01-preview.png`

## 生成提示词摘要

在一张正方形 2×3 六宫格中生成六个独立食材贴纸，依次为洋葱、西红柿、鸡蛋、无标签牛奶盒、牛腩和无叶胡萝卜。采用统一的半写实手绘卡通风格，略带质感，每个食材有约主体宽度 5% 的连续白色贴纸切边。严格每格一个主体，不重叠，不添加文字、品牌、餐具、阴影或额外物体；使用纯绿色背景方便透明抠图。

## Milk V2

新增 `transparent/milk-lettered-v2.png`：奶油色牛奶盒，正面使用蓝色圆润奶油手写字 `Milk`。原始无字版本继续保留，便于对比和回滚。
