# 阿凑 D 动作生成提示词组

生成模式：内置 `image_gen`。每个状态独立生成一条横向动作带；纯 `#FF00FF` 色键背景；随后本地透明化与逐帧提取。

## 所有状态共享块

```text
Use case: stylized-concept
Asset type: horizontal character animation sprite strip

Identity lock: tiny warm-cream mochi helper inside one thick incomplete
translucent coral-orange gummy connector collar; one mint-teal bead attached
at the collar gap on the character's own upper-right; glossy dark oval eyes,
tiny curved smile, apricot cheek dots, cream mitten hands and tiny feet;
compact low center of gravity.

Style: premium youthful East Asian app mascot, stylized soft-matte 3D vinyl
toy, smooth rounded forms, restrained highlights, clear silhouette.

Scene: perfectly flat uniform pure #FF00FF chroma-key background, no floor.
Composition: one complete full-body pose per invisible equal-width slot,
evenly spaced, constant apparent scale, generous padding, no overlap or clipping.

Preserve exact face, silhouette, proportions, palette, gummy material, collar
gap and the bead on the character's own upper-right across every frame.

Avoid: text, symbols, labels, borders, guide lines, flame, droplet, animal ears,
hair, clothing, logo, props, shadows, floor, glow, gradients in background,
motion blur, speed lines, dust, detached effects, stray pixels, or #FF00FF
inside the mascot.
```

输入图角色：

1. `base-transparent.png`：批准的角色身份参考；
2. 对应状态的布局图：只提供槽位数量、间距与留白，不复制辅助线；
3. `base-transparent.png` 的 canonical 副本：身份与比例的最高优先级参考；
4. `running-left` 额外参考右向动作节奏，但明确禁止直接镜像非对称薄荷珠。

## 九个状态差异块

### `idle` · 6 帧

```text
Neutral open eyes → subtle inhale/up → tiny blink → exhale/down → micro sway
→ return almost exactly to frame 1. Feet remain planted; first and last frames
must form a calm seamless loop.
```

### `running-right` · 8 帧

```text
Cheerful screen-entry gait oriented right: anticipation, first step, passing
pose, upbeat bounce, opposite step, passing pose, bounce, return. Alternate
arms and tiny feet; remain centered in each slot. The runtime moves the outer
container to create actual entry displacement.
```

### `running-left` · 8 帧

```text
New left-facing retreat poses with the same cadence as running-right. Do not
horizontally mirror the identity: the mint bead remains on the mascot's own
upper-right. The runtime moves the outer container to create actual exit.
```

### `waving` · 4 帧

```text
Viewer-left hand down → lifted beside face → tilted outward with bigger smile
→ halfway down. Feet planted. Gesture uses the hand only; no wave arcs,
sparkles, marks or floating effects.
```

### `jumping` · 5 帧

```text
Gentle crouch/squish → lift with hands rising → airborne peak with joyful
closed eyes → descent → planted soft settle. Express height only through body
position; no ground shadow, landing mark, dust or confetti.
```

### `failed` · 8 帧

```text
Neutral → shoulders lower → slight compression → closed-eye pause → lowest
composed deflate → eyes reopen → rise halfway → nearly neutral. Supportive,
brief and non-blaming; no tears, red X, smoke or detached symbols.
```

### `waiting` · 6 帧

```text
Attentive neutral → hands inward → hands meet and body leans forward → curious
head tilt with expectant eyes → patient blink → return. Distinct from idle;
no question marks, speech bubbles or clocks.
```

### `running` · 6 帧

```text
Focused stance → left hand taps inner collar → right hand taps with focused
eyes → both hands move inward and body bobs down → focused blink with tiny
attached-bead compression → return. Feet planted; this means task processing,
not literal locomotion. Keep the coral-orange hue stable in all frames.
```

工作态执行了一次定向重生成：保留六帧节奏，只修正个别帧软环从珊瑚橙偏向粉红的问题，并再次强调六帧的色相、饱和度、明度与材质高光一致。

### `review` · 6 帧

```text
Focused neutral → lean left and gaze down-left → one-eye thoughtful squint and
head tilt → lean right with hands still → slow concentrated blink → subtle
satisfied nod. No magnifying glass, paper, screen, UI or checkmark.
```
