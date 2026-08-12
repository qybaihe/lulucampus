# Lulu 功能贴纸第二批（S7–S11）最终生成提示词

## 生成方式与参考

- 模式：Codex 内置 `image_gen`（`stylized-concept`）。
- 每批输出：一张正方形 3 列 × 2 行六宫格，严格固定格位。
- 第一风格参考：上一批原始六宫格
  `raw/stickers-s6-results-chroma.png` 或已经生成的 S7 六宫格。
- 第二风格参考：`qa/stickers-contact-sheet.jpg`。
- Lulu 身份参考：`raw/lulu-intent-card-chroma.png`。

## 五批共享约束

```text
Create ONE square sprite sheet containing exactly six independent stickers in a
strict 3 columns × 2 rows arrangement. Semi-realistic hand-painted cartoon
sticker style, subtle paper grain, polished cozy finish, gentle upper-left
material lighting, and a consistent 3/4 slightly top-down view where applicable.
Every subject has one continuous clean white die-cut border about 5% of subject
width. Use only deep ink green #1F2D25, egg-yolk yellow #F6C945, warm paper
#F6F4EC, fog gray-green #5D6B63, sage #CBD4CC, off-white #FFFDF8, line
green-gray #DCE3D9, and close tonal shades. Exactly one complete centered subject
per cell, generous separation, no cropping or cell crossing. Fill the full image
and every gap with perfectly flat uniform #00FF00 chroma-key green. No texture,
gradient, floor, horizon, cast/contact shadow, reflection, green halo, grid line,
text, letters, digits, labels, logo, watermark, captions, faces, or background
props. Do not use #00FF00 inside any subject.
```

## S7 · 设置与隐私

```text
Fixed order, top row then bottom row: a rounded deep-ink-green shield with an
egg-yolk-yellow recessed check mark; a vintage round-bow key with a yellow head;
exactly three horizontal slider rails with knobs at different positions; a
slightly tilted ink-green circular prohibition ring and slash; a small yellow
triangular flag mounted on a compact stand; a round plump yellow hand bell.
```

## S8 · 我的与数据

```text
Fixed order: a portrait identity card on a short lanyard with one faceless
head-and-shoulders silhouette and exactly two blank horizontal information bars;
a round blank yellow medal on a folded ribbon; a diagonal wand topped by one
four-point yellow star; an open warm-paper box with one bold upward arrow above
it; one clipboard holding blank paper with a referee whistle hanging from its
edge; one compact handheld megaphone aimed upper-right. Treat attached parts as
one cohesive sticker silhouette.
```

定向修订：首轮身份卡误生成为三条信息横线；最终 S8 仅删除最下面一条，保留其余
五格及身份卡的构图、角度、配色和白边不变。

## S9 · 局与关系

```text
Fixed order: a round table with exactly four evenly placed chairs, exactly one
chair yellow and three muted green; exactly two hands shaking, with one ink-green
sleeve and one sage sleeve; a round table with a small yellow circular plus badge
attached at upper right and no chairs; one thick rounded near-circular redo arrow
with a clear arrowhead; one tilted party-popper cone releasing a small contained
burst of yellow and sage confetti; one half-open simple door with a narrow wedge
of yellow light and no surrounding wall.
```

## S10 · 信任勋章套装

```text
The first five cells use the SAME frontal circular medal mold, silhouette,
dimensions, angle, lighting, and placement; only the manufacturing treatment
changes. Fixed order: T0 warm-paper unfilled-looking center with fog-green outline
only; T1 solid sage fill; T2 yellow fill with exactly one recessed tally notch;
T3 yellow fill with exactly two recessed tally notches and one tiny five-point
star; T4 yellow fill with one five-point star and two short bottom ribbon tails.
Bottom-right: Lulu static front portrait, preserving the reference identity—a
white round plump chick/bird body, tiny wings, small golden-orange beak and feet,
dark dot eyes, and egg-yolk-yellow bow tie, without props or text.
```

## S11 · 场景与空态

```text
Fixed order: a magnifying glass whose lens contains exactly one short dashed line
made of three fog-green dashes; a small rounded cloud with one diagonal slash; an
open school exercise notebook with pale-green square practice-grid lines and one
pencil laid horizontally across its lower part; one Erlenmeyer flask half filled
with opaque sage liquid and no bubbles/smoke/labels/measurements; one plump round
light bulb with yellow glass and an ink-green base; one standalone reasonably
large four-point yellow sparkle. Only the first five cells are delivered; the
sixth sparkle is an optional sheet filler, preserving the 29-asset contract.
```

## 透明后处理参数

原始六宫格先由安装版 imagegen 色键工具以边框自动取色、软遮罩
`transparent-threshold=12`、`opaque-threshold=220` 转为 RGBA。因主体包含语义墨绿，
交付脚本仅保留外缘三像素软遮罩、恢复白边内部为全不透明，并只在白色切边外缘
中和绿色溢色；随后拆格并以 28 px 边距适配到 512×512。
