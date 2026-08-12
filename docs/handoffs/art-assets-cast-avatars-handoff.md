# 美术素材交接 · 中大测试剧组卡通大头（2×3 一张出齐）

> 交接对象：特斯（生图线程）
> 发起日期：2026-08-13
> 范围：六名演示用户的**卡通人物大头**，一次生成一张 2×3 六宫格。
> **不涉及** Lulu 动作图集、功能贴纸、Tab 图标。这批是真人用户头像，不是 IP。
> 风格基准：产品七色 + 贴纸批的半写实手绘质感；人物脸按本节锁定，不要画成 Lulu。

---

## 1. 任务

噜噜成局有六名已注册的中大测试剧组（`u_demo_1`–`u_demo_6`）。联调、演示、「我」页、成局后协作空间需要能一眼分清是谁。现在 `avatar_url` 全是空的。

本批只要 **6 个大头**：锁骨以上、一张脸占满格子、卡通人物、男女可读、性格可读。一次出 2×3，不要拆成六次（六次会漂成六种画风）。

**这不是交友软件的人物卡。** 不要美型、不要网红、不要滤镜自拍。他们是会一起打球、赶 DDL、组比赛的中大学生。头像要像「同学」，不要像「可滑动的对象」。

---

## 2. 六宫格排位（从左到右、从上到下，禁止打乱）

| 格 | 文件 id | 姓名 | 性别 | 年级 / 学院 | 性格一句话 | 头像要读出的感觉 |
|---|---|---|---|---|---|---|
| 1 左上 | `lin-yuan.png` | 林予安 | 女 | 大三 · 珠海软工 | 把事做成的局主 | 利落、专注、来办事 |
| 2 中上 | `zhou-heng.png` | 周衡 | 男 | 大四 · 东校计科 | 高质量沉默成员 | 安静、眼镜、不太对视 |
| 3 右上 | `chen-kewei.png` | 陈可薇 | 女 | 大二 · 东校传设 | 让局不像开会 | 松、暖、有点设计感 |
| 4 左下 | `liang-jingxing.png` | 梁景行 | 男 | 大三 · 南校岭南 | 把人凑齐的润滑剂 | 清爽、好说话、阳光 |
| 5 中下 | `su-wanning.png` | 苏晚宁 | 女 | 大一 · 南校外语 | 冷启动本人 | 更幼、礼貌、有点认路茫 |
| 6 右下 | `he-yu.png` | 何屿 | 男 | 大二 · 东校生科 | 周期球局固定搭子 | 运动、轻松、晒过一点 |

男女交错：女 / 男 / 女 / 男 / 女 / 男。验收时六张并排，性别必须 0.5 秒内读对。

---

## 3. 统一画风（六格必须像同一套角色设定）

- **媒介**：半写实手绘卡通人物头像。有纸张颗粒、有明确勾线，不是扁平 emoji，不是 3D 渲染，不是真人照片，不是日系美型立绘，不是 Q 版三头身。
- **取景**：只画大头。头顶到锁骨，脸在格子正中，脸宽约占格子 55–65%。能看到一点肩膀和衣领，**不要**半身、双手、书包全身、场景。
- **朝向**：全部正面略 3/4，微微转向画面左（观众右），六人转角一致。
- **光照**：统一左上柔光，鼻梁与脸颊有一点暖纸色高光。
- **五官模具**：东亚大学生脸型；眼睛有虹膜和高光，但不要漫画夸张瞳；鼻子小而明确；耳朵完整画进格子（圆形裁切时不能缺耳朵）。
- **年龄阶梯**（必须拉开）：苏晚宁最幼（大一）→ 陈可薇 / 何屿（大二）→ 林予安 / 梁景行（大三）→ 周衡最成熟（大四）。不要六张都画成同一张 20 岁网红脸。
- **配色只走产品七色及同色系明暗**，衣服用它们来区分人，不要高饱和红蓝紫：

| token | 值 | 在头像里怎么用 |
|---|---|---|
| 纸 `--paper` | `#F6F4EC` | 肤色高光倾向、浅色衣 |
| 墨 `--ink` | `#1F2D25` | 勾线、深发、深色衣 |
| 蛋黄 `--yolk` | `#F6C945` | **每人最多一个小点缀**（抽绳 / 耳钉 / 领口 / 拉链），不要六人满身黄 |
| 卡 `--card` | `#FFFDF8` | 白衬衫、polo |
| 雾 `--mist` | `#5D6B63` | 灰绿外套、运动外套 |
| 线 `--line` | `#DCE3D9` | 内部分界 |
| 鼠尾草 `--sage` | `#CBD4CC` | 针织开衫、学院背心 |

- **背景**：每格纯绿 `#00FF00`，便于色键。格子之间不要共用背景、不要桌面、不要校园建筑。
- **不要白色贴纸切边**（那是物件贴纸的语言）。头像后处理会做成圆形裁切。
- **无文字、无数字、无姓名、无 netid、无校徽、无品牌 logo、无 Lulu、无第二个人、无阴影落地、无自拍杆、无美颜泪痣网红妆。**

圆形裁切安全区：脸心对准格子中心；发顶、下巴、双耳都落在直径约 80% 的圆内。

---

## 4. 每人怎么画（特斯按这张表，不要自己发明网红造型）

### 格 1 · 林予安 · 女 · 来办事

- **脸**：偏鹅蛋，眉眼利落，看镜头。嘴角只有一点自信的闭唇笑，不要甜、不要冷脸嫌弃。
- **发**：深棕近黑，低马尾，额前两缕碎发，耳后利落。不要大波浪、不要齐刘海遮眼。
- **衣**：浅灰（纸色偏灰）连帽卫衣，帽子放下；左腕隐约一条墨色运动表，刚好卡在画幅下沿。
- **点缀**：卫衣抽绳一端一点点蛋黄。
- **气质**：珠海软工大三，电脑包不离身的那种人——头像里用卫衣和表说完，不要画电脑。

### 格 2 · 周衡 · 男 · 不太对视

- **脸**：偏瘦长，肤色更冷一点。目光微微偏下右，不是死盯镜头。闭唇，几乎不笑。
- **发**：短黑发，刘海略乱，不是油头。
- **关键道具**：细黑框眼镜，镜片不要反成白块，要能看见眼睛。
- **衣**：炭灰连帽衫，领口松，不修边幅但干净。
- **点缀**：无。他是六人里最素的一格。
- **气质**：大四秋招里的安静开发者。不要画成阴郁二次元、不要眼下重黑眼圈漫画化。

### 格 3 · 陈可薇 · 女 · 空气感

- **脸**：比林予安圆一点、暖一点。眼睛弯，有浅浅开口笑，像刚要说话。
- **发**：锁骨发，深棕带一点暖，一侧轻轻别到耳后。
- **点缀**：一对很小的蛋黄耳钉（豆粒大，不要耳环垂坠）。
- **衣**：鼠尾草针织开衫，里面卡色白 T，领口干净。
- **气质**：传设视传，有设计感但不网红。不要画美瞳、不要画浓妆、不要画彩色染发。

### 格 4 · 梁景行 · 男 · 好说话

- **脸**：比周衡宽、比何屿白，南校园阳光感。笑眼，嘴角明确上扬，可以露出一点点牙齿，但不要牙膏广告。
- **发**：清爽短发，分线干净，不是杀马特也不是寸头。
- **衣**：卡色白 polo，领子立起来一点点。
- **点缀**：polo 领口内侧一条极细蛋黄滚边（若怕花可以去掉，保留白 polo 即可）。
- **气质**：岭南经济、会带新人的润滑剂。不要画成销售油腻、不要画成偶像剧男主。

### 格 5 · 苏晚宁 · 女 · 有点茫

- **脸**：六人里最幼。五官更小，眼睛略睁大，礼貌的闭唇浅笑，笑意不到眼睛里——还在认路。
- **发**：齐肩直黑发，中分或很浅的偏分，服帖，新生刚理过的那种整齐。
- **衣**：白衬衫 + 雾绿学院针织背心，衬衫领外翻。
- **点缀**：肩带刚入画一条卡色新书包带（只露一截，不要画整只包）。
- **气质**：外语院大一。不要画成高中生制服，不要画成害羞捂脸。比林予安明显更嫩即可。

### 格 6 · 何屿 · 男 · 球场皮肤

- **脸**：运动型，下颌比梁景行利一点，肤色微晒（仍是东亚学生，不要画成欧美健美）。轻松半笑。
- **发**：短碎发，有一点被风吹过的纹理，不是油头。
- **衣**：雾绿运动拉链外套，拉链拉到锁骨；内里白 T。
- **点缀**：拉链头一点点蛋黄。
- **气质**：生科大二，实验周会消失、球场从不消失。画的是球场皮肤，不要白大褂、不要球拍（大头里塞球拍会变贴纸）。

六人并排时的速查差：

| | 发 | 眼镜 | 衣 | 表情 |
|---|---|---|---|---|
| 林予安 | 低马尾 | 无 | 灰卫衣 | 自信闭唇 |
| 周衡 | 短、略乱 | **有** | 炭灰帽衫 | 几乎不笑 |
| 陈可薇 | 锁骨发 | 无 | 鼠尾草开衫 | 要说话的笑 |
| 梁景行 | 清爽短发 | 无 | 白 polo | 开口浅笑 |
| 苏晚宁 | 齐肩直发 | 无 | 衬衫+背心 | 礼貌浅笑偏茫 |
| 何屿 | 短碎发 | 无 | 运动外套 | 轻松半笑 |

---

## 5. 线上教学提示词（整段复制，不要改写风格段）

风格一致性靠逐字复用。特斯若模型更吃英文，用 5.2；吃中文用 5.1。**不要中英混着改写**，改写会让六张脸漂成一套模板脸。

### 5.1 中文版（推荐先跑）

```text
请把下面当成一堂必须按顺序完成的绘画课。不要跳步，不要自己加戏。

第一课 · 画布
在一张正方形画布上画精确的 2×3 六宫格。六格一样大，中间用极细的纯绿分隔，不要黑线框。整张背景和每格背景都是纯绿 #00FF00。每格只画一个人物大头，人物之间不重叠、不共享道具。

第二课 · 统一模具
半写实手绘卡通校园人物头像，轻纸张颗粒，明确勾线，左上柔光。不是照片、不是 3D、不是日系美型、不是 Q 版。全部东亚大学生，锁骨以上大头特写，脸在格子正中，脸宽约占格子 55% 到 65%，正面略 3/4 转向画面左侧。六人同一透视、同一线宽、同一眼睛画法（有虹膜和高光，但不夸张）。无文字、无姓名、无校徽、无 logo、无第二个人、无 Lulu、无落地阴影、无白色贴纸切边。配色只用深墨绿 #1F2D25、蛋黄 #F6C945、暖纸 #F6F4EC、卡其白 #FFFDF8、雾灰绿 #5D6B63、鼠尾草 #CBD4CC。每人最多一处蛋黄小点缀。

第三课 · 六个学生，从左到右、从上到下，顺序锁死

格1 左上 女大学生 林予安：大三执行者。鹅蛋脸，深棕低马尾，额前两缕碎发，看镜头，自信的闭唇浅笑，不要甜。浅灰连帽卫衣，帽子放下，左腕墨色运动表刚入画，抽绳一端一点点蛋黄。利落、来办事。

格2 中上 男大学生 周衡：大四安静开发者。瘦长脸，短黑发略乱，细黑框眼镜，目光微微偏下右，闭唇几乎不笑。炭灰连帽衫。最素的一格。不要阴郁漫画黑眼圈。

格3 右上 女大学生 陈可薇：大二设计学生。脸比格1圆而暖，锁骨发深棕偏暖，一侧别到耳后，一对豆粒大蛋黄耳钉。眼睛弯，浅浅开口笑像要说话。鼠尾草针织开衫，内里白 T。有设计感但不网红，无浓妆无染发。

格4 左下 男大学生 梁景行：大三商科组织者。脸比格2宽，清爽短发，笑眼，嘴角上扬可露一点点牙齿。卡色白 polo。南校园阳光、好说话。不要油腻男主。

格5 中下 女大学生 苏晚宁：大一新生，六人里最幼。齐肩直黑发很服帖，五官更小，眼睛略睁大，礼貌闭唇浅笑但有点认路的茫。白衬衫加雾绿学院针织背心，肩带只露一截新书包带。不要高中制服，不要捂脸。

格6 右下 男大学生 何屿：大二运动搭子。短碎发，微晒的东亚学生脸，下颌利一点，轻松半笑。雾绿运动拉链外套拉到锁骨，拉链头一点点蛋黄。球场皮肤，不要白大褂，不要球拍。

第四课 · 验收自检
六张脸必须一眼可分：马尾女 / 眼镜男 / 锁骨发女 / polo 男 / 齐肩幼女 / 运动男。性别女男女男女男。年龄格5最幼、格2最成熟。圆形裁切时耳朵和发顶都还在。纯绿背景，无字。
```

### 5.2 英文版（模型偏英文时用，语义与 5.1 锁定同一套）

```text
Follow this as a drawing lesson. Do not skip steps. Do not add extra story.

Lesson 1 — Canvas
Paint an exact 2×3 grid on a square canvas. Six equal cells. Entire background and every cell background are flat chroma green #00FF00. One character bust per cell. No overlapping, no shared props, no black cell borders.

Lesson 2 — Shared mold
Semi-realistic hand-drawn cartoon campus portrait, light paper grain, clear ink line, soft light from upper left. Not photoreal, not 3D, not anime bishoujo, not chibi. East Asian university students only. Head-and-shoulders crop from crown to collarbone, face centered, face width 55–65% of the cell. All six face slightly three-quarter toward the left of the image. Same perspective, same line weight, same eye construction (iris and catchlight, not super-deformed). No text, no names, no university crest, no logo, no second person, no mascot, no cast shadow on the ground, no white sticker die-cut. Palette only: ink #1F2D25, yolk #F6C945, paper #F6F4EC, card #FFFDF8, mist #5D6B63, sage #CBD4CC. At most one tiny yolk accent per person.

Lesson 3 — Six students, left-to-right, top-to-bottom, order locked

Cell 1 top-left, woman, Lin Yuan: third-year executor. Oval face, dark-brown low ponytail, two wisps at the temples, looking at camera, confident closed-mouth smile, not cute. Heather-grey hoodie, hood down, ink-colored sports watch just entering at the left wrist, one hoodie drawstring tipped in yolk. Neat, here to get things done.

Cell 2 top-middle, man, Zhou Heng: quiet fourth-year CS student. Longer thin face, short slightly messy black hair, thin black rectangular glasses, gaze slightly down and to his left, closed mouth almost no smile. Charcoal hoodie. The plainest cell. No emo raccoon-eye shading.

Cell 3 top-right, woman, Chen Kewei: second-year design student. Rounder warmer face than cell 1, collarbone-length warm dark hair tucked behind one ear, tiny yolk stud earrings. Crescent eyes, a small open smile as if about to speak. Sage knit cardigan over a white tee. Design-aware, not influencer. No heavy makeup, no dyed hair.

Cell 4 bottom-left, man, Liang Jingxing: third-year economics organizer. Broader healthier face than cell 2, clean short hair, smiling eyes, mouth upturned with a hint of teeth. Off-white polo. Sunny, easy to talk to. Not oily, not idol-drama male lead.

Cell 5 bottom-middle, woman, Su Wanning: first-year, the youngest of the six. Neat shoulder-length straight black hair, smaller features, eyes a little wide, polite closed-mouth smile with a hint of being lost. White collared shirt under a mist-green knit vest, only a sliver of a new backpack strap in frame. Not a high-school uniform, not covering her face.

Cell 6 bottom-right, man, He Yu: second-year athlete-lab student. Short textured hair, lightly sun-touched East Asian face, a bit more jaw, easy half-smile. Mist-green zip sport jacket closed to the collarbone, zipper pull tipped in yolk. Sports-skin, no lab coat, no racket.

Lesson 4 — Self-check
Six faces must be instantly distinct: ponytail woman / glasses man / collarbone-hair woman / polo man / youngest straight-hair woman / sport-jacket man. Gender order F M F M F M. Cell 5 youngest, cell 2 most mature. Ears and hair-top survive a circular crop. Flat green, no type.
```

### 5.3 单人补跑（某一格崩了才用）

把下面前缀接到「这一格的人物段」后面，单独出一张正方形大头，再贴回六宫格。

```text
半写实手绘卡通东亚大学生大头，锁骨以上，脸居中占 60%，正面略 3/4 向左，左上柔光，轻纸张颗粒，明确勾线。纯绿 #00FF00 背景。无文字无校徽无第二人无白边无阴影。配色仅 #1F2D25 #F6C945 #F6F4EC #FFFDF8 #5D6B63 #CBD4CC。
```

---

## 6. 生成规格与后处理

| 项 | 值 |
|---|---|
| 一次出图 | 1 张正方形 2×3 sheet |
| 建议尺寸 | 2048×2048 或 1536×1536（六格拆完每格仍清晰） |
| 色键 | 纯绿 `#00FF00`，阈值可复用贴纸工具 40 / 160 |
| 拆格 | 六等分 → 每人一张 |
| 成品 | 1024×1024 PNG，透明背景，脸居中，四周留白约 8% |
| 圆形预览 | 额外导出一版圆形裁切 512×512，给 App 头像位看 |

```bash
# 色键（与贴纸同一工具）
python3 assets/ip/lulu/tools/remove_chroma_key.py \
  raw/cast-avatars-chroma.png \
  out/cast-avatars-sheet.png \
  --key "#00ff00" --low 40 --high 160

# 拆格后建议落地
# assets/ip/cast/avatars/lin-yuan.png
# assets/ip/cast/avatars/zhou-heng.png
# assets/ip/cast/avatars/chen-kewei.png
# assets/ip/cast/avatars/liang-jingxing.png
# assets/ip/cast/avatars/su-wanning.png
# assets/ip/cast/avatars/he-yu.png
```

接入先不做（等特斯回图）。回图后：`avatar_url` 现在是 `None`（`onemore/db/seed.py` 剧组画像），再把六张挂上 `u_demo_1`–`u_demo_6`。

---

## 7. 验收清单

- [ ] 一张 2×3，顺序锁死为 林予安 / 周衡 / 陈可薇 / 梁景行 / 苏晚宁 / 何屿
- [ ] 六格同一套线、光、脸模，不像六次不同模型拼的
- [ ] 性别女男女男女男，44pt 圆裁仍能分清男女
- [ ] 苏晚宁明显比林予安幼；周衡是唯一戴眼镜、几乎不笑的
- [ ] 全是大头（头顶–锁骨），没有半身场景、没有球拍电脑书包全身
- [ ] 无文字、无校徽、无 Lulu、无交友软件美型脸
- [ ] 纯绿背景可抠；圆裁不切耳朵、不切下巴
- [ ] 蛋黄只是点缀，没有人满身黄

## 8. 失败重做条件（出现任一条就整张重出，不要局部修补）

- 六张脸五官几乎一样，只靠衣服区分
- 画成照片、AI 网红、或日系大眼美型
- 有人画出身体/双手/教室背景
- 绿幕被衣服或头发吃掉（雾绿外套尤其危险：外套必须比 `#00FF00` 灰、暗，不能荧光绿）
- 格子顺序错了

何屿、陈可薇的衣服是鼠尾草/雾绿，**必须灰绿不能碰到色键绿**。如果绿幕互吃，改用纯品红 `#FF00FF` 背景重出，并在回图时注明。
