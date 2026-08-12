# 美术素材交接 · 贴纸第二批（S7–S11，共 29 张）

> 交接对象：新线程的生成 Agent
> 发起日期：2026-08-12
> 范围：iOS App 功能贴纸补全与牵强素材替换，**不涉及** Lulu 动作图集（12 个 clip 已齐备）
> 风格基准：`assets/ip/lulu/style-reference/style-reference.jpg` + 首批 36 张成品 `assets/ip/lulu/generated/2026-08-12/stickers/`

---

## 1. 任务

iOS App 已完成 Lulu 亮色设计迁移，但功能贴纸只有首批 36 张（S1–S6），很多页面只能"就近借用"，用户反馈**图片和内容对不上、很牵强**（重灾区：「我的」页面）。本批新增 29 张贴纸，分 5 批生成，全部替换到位。

**硬性风格规范（与首批完全一致，违反即重做）：**

- 半写实手绘卡通贴纸风，轻白边 Ins 感：每个主体带**约主体宽度 5% 的连续白色切边**
- 统一光照（左上柔光）、统一质感（轻微纸张颗粒）、统一 3/4 俯视视角
- 配色从产品七色取：纸 `#F6F4EC`、墨 `#1F2D25`、蛋黄 `#F6C945`、卡 `#FFFDF8`、雾 `#5D6B63`、线 `#DCE3D9`、鼠尾草 `#CBD4CC`；可少量向外延展同色系明暗，**禁止高饱和红蓝紫**
- **无文字、无数字、无品牌 logo、无表情脸、无阴影、无背景杂物**，严格每格一个主体
- 生成在**纯绿 `#00FF00` 背景**上（色键抠图用），2×3 六宫格一张 sheet
- 成品规格：512×512 PNG，透明背景，主体居中、四周留白约 6%

## 2. 已有 36 张（不要重复生成）

| 批 | id |
|---|---|
| S1 桌与席位 | access-card / chair-empty / hourglass / nameplate-blank / qr-plaque-blank / round-table |
| S2 运动 | badminton / basketball / football / running-shoe / sports-bottle / table-tennis |
| S3 学业 | alarm-clock / books-stack / desk-calendar / laptop-closed / marker / notebook-open |
| S4 校园 | cafeteria-tray / poster-blank / school-bus / seminar-room-sign / study-lamp / teaching-building |
| S5 能力 | algorithm-gear / backend-server / data-chart / design-palette / frontend-browser / product-notes |
| S6 结果 | approval-stamp / badge / certificate / chat-bubble / envelope / trophy |

## 3. 牵强映射审计（为什么需要这批）

「我的」页面当前借用对照（→ 表示"实际语义"）：

| 页面元素 | 现在借用的贴纸 | 问题 |
|---|---|---|
| 隐私与安全 | nameplate-blank（空白名牌） | 与安全无关 → 需盾牌 |
| 黑名单 | notebook-open（笔记本） | 与屏蔽无关 → 需禁止标识 |
| 数据导出与注销 | laptop-closed（合上的电脑） | 无导出语义 → 需打包盒 |
| 匹配偏好 | marker（马克笔） | 无调节语义 → 需滑杆 |
| 授权管理 | certificate（证书） | 授权=钥匙更直观 |
| 信任进度 | approval-stamp（审批章） | 进度=勋章更直观 |
| 历史局安全与举报 | envelope（信封） | 举报=旗帜/哨声 |
| 主理人控制台 | trophy（奖杯） | 管理=哨子+写字板 |
| 搭子关系 | badge（徽章） | 关系=握手 |
| 我的局 | chair-empty（空椅子） | 空椅是"缺口"语义，不是"我的局" |
| 抖音兴趣画像 | design-palette（调色板） | 兴趣=魔法棒/爱心更轻 |
| 通知与日历 | desk-calendar（台历） | 通知=铃铛 |

## 4. 新增素材清单（29 张 / 5 批）

### S7 · 设置与隐私（P0，6 张）

| id | 画面描述 | 用在哪 / 替换谁 |
|---|---|---|
| `shield-check.png` | 圆润小盾牌，中央一个打勾刻痕，墨绿主体+蛋黄勾 | M1「隐私与安全」、M5 页、安全类脚注；替换 nameplate-blank / access-card 的安全用法 |
| `key.png` | 复古圆头钥匙，蛋黄钥匙头 | M1/M4「授权管理」；替换 certificate |
| `sliders.png` | 三根水平调节滑杆，滑块位置错落 | M1/M6「匹配偏好」；替换 marker |
| `block-sign.png` | 圆形禁止标识（墨绿圆环+斜杠），微倾斜 | M1/M8「黑名单」；替换 notebook-open |
| `flag.png` | 小三角旗插在旗座上，蛋黄旗面 | M1「历史局安全与举报」、E13 举报；替换 envelope |
| `bell.png` | 圆胖小铃铛，蛋黄铃身 | M1/M7「通知与日历」、通知开关；替换 desk-calendar 的通知用法 |

### S8 · 我的与数据（P0，6 张）

| id | 画面描述 | 用在哪 / 替换谁 |
|---|---|---|
| `id-card.png` | 挂绳身份卡，卡面有人像剪影与两条横线（无文字） | M1/M2「画像与能力」；替换 access-card |
| `medal.png` | 圆形勋章挂缎带，蛋黄勋章面 | M1/M3「信任进度」；替换 approval-stamp |
| `sparkle-wand.png` | 魔法棒顶端一颗四角星，星用蛋黄 | M1「抖音兴趣画像」；替换 design-palette |
| `box-export.png` | 打开的纸盒，上方一个向上箭头 | M1「数据导出与注销」；替换 laptop-closed |
| `clipboard-whistle.png` | 写字板夹着纸，纸边挂一只哨子 | M1/O1「主理人控制台」；替换 trophy |
| `megaphone.png` | 小手持扩音喇叭，喇叭口朝右上 | M1/M9「信任申诉」；替换 chat-bubble |

### S9 · 局与关系（P1，6 张）

| id | 画面描述 | 用在哪 / 替换谁 |
|---|---|---|
| `table-people.png` | 圆桌四周摆四把椅子，其中一把蛋黄高亮 | M1/E1「我的局」；替换 chair-empty |
| `handshake.png` | 两只手交握，袖口一墨绿一鼠尾草 | M1/E15「搭子关系」；替换 badge |
| `table-plus.png` | 圆桌右上一个蛋黄圆形加号角标 | M1/C2「直接发起局」；替换 round-table |
| `redo-arrow.png` | 圆润环形箭头，首尾相接 | E12「复局」、固定周期局 |
| `party-popper.png` | 彩带礼花筒，喷出蛋黄/鼠尾草纸屑 | E3 凑齐确认、成局庆祝态 |
| `door-exit.png` | 半开的门，门外一点蛋黄光 | E7 退场表达、E12 退出局 |

### S10 · 信任勋章套装（P1，6 张，统一模具只换工艺）

| id | 画面描述 | 用在哪 |
|---|---|---|
| `trust-t0.png` | 勋章轮廓线稿（无填充，雾色描边） | M3 信任进度 · T0 访客 |
| `trust-t1.png` | 勋章填鼠尾草色 | T1 已认证 |
| `trust-t2.png` | 勋章填蛋黄 + 一道刻痕 | T2 靠谱同学 |
| `trust-t3.png` | 勋章填蛋黄 + 两道刻痕 + 小星 | T3 稳定搭子 |
| `trust-t4.png` | 勋章填蛋黄 + 星 + 底部缎带 | T4 认证主理人 |
| `lulu-face.png` | Lulu 静态正面头像（与动作图集同形象：白色圆胖身体、蛋黄领结） | 列表小头像位、分享卡角标 |

### S11 · 场景与空态（P2，5 张）

| id | 画面描述 | 用在哪 |
|---|---|---|
| `magnifier-empty.png` | 放大镜镜片里一小条虚线 | 列表/搜索空态 |
| `cloud-off.png` | 小云朵中间一道斜杠 | 离线 / 网络错误态 |
| `homework-pencil.png` | 田字格作业本上横放一支铅笔 | B1/B4「作业」；替换 alarm-clock 的作业用法 |
| `flask.png` | 锥形烧瓶装半瓶鼠尾草色液体 | B12 科研类赛事卡 |
| `bulb.png` | 圆胖灯泡，蛋黄玻璃 | B12 创业/点子类赛事卡 |

## 5. 每批生成提示词（可直接粘贴）

通用前缀（每批都带）：

```text
在一张正方形 2×3 六宫格中生成六个独立贴纸，采用统一的半写实手绘卡通风格，略带纸张质感，统一左上柔光与 3/4 俯视视角。每个主体带约主体宽度 5% 的连续白色贴纸切边。配色取自暖纸色系：深墨绿 #1F2D25、蛋黄 #F6C945、暖纸 #F6F4EC、雾灰绿 #5D6B63、鼠尾草 #CBD4CC。严格每格一个主体，不重叠，不加文字、数字、品牌、表情脸、阴影或额外物体；纯绿色 #00FF00 背景。
```

- **S7**：六个主体依次为：带打勾刻痕的圆润盾牌、圆头复古钥匙、三根滑块错落的调节滑杆、圆形禁止标识、插在旗座上的小三角旗、圆胖小铃铛。
- **S8**：依次为：带挂绳与人像剪影的身份卡、挂缎带的圆形勋章、顶端有四角星的魔法棒、上方带向上箭头的打开纸盒、夹着纸并挂哨子的写字板、手持小扩音喇叭。
- **S9**：依次为：四把椅子围坐的圆桌（一把椅子蛋黄高亮）、两只交握的手、右上角带蛋黄加号角标的圆桌、首尾相接的圆润环形箭头、喷纸屑的彩带礼花筒、透出蛋黄光的半开的门。
- **S10**：同一款圆形勋章的五种工艺：雾色线稿轮廓、鼠尾草填充、蛋黄填充加一道刻痕、蛋黄填充加两道刻痕与小星、蛋黄填充加星与底部缎带；第六格为白色圆胖卡通小鸡形象的正面头像（蛋黄小领结，无表情文字）。
- **S11**：五个主体（第六格留空主体也接受，但优先放一只蛋黄四角星点缀 `sparkle.png`）：镜片里有虚线的放大镜、带斜杠的小云朵、田字格作业本上横放铅笔、装半瓶鼠尾草液体的锥形烧瓶、蛋黄玻璃圆灯泡。

## 6. 后处理与接入流程

```bash
# 1. 色键抠图（每张 sheet）
python3 assets/ip/lulu/tools/remove_chroma_key.py raw/s7-chroma.png out/s7.png --key "#00ff00" --low 40 --high 160

# 2. 拆格 + 512px 居中（参考 assets/ip/lulu/tools/build_generated_delivery.py 的
#    split/fit 逻辑；新批可照抄其 StickerSpec 模式扩展，或手写 6 等分裁剪）

# 3. 拷贝进 iOS bundle
cp stickers/S7/*.png ios/OneMore/Resources/LuluGenerated/Stickers/S7/
#    （S8–S11 同理，目录不存在则新建）

# 4. 注册批次：ios/OneMore/Core/Motion/LuluGeneratedAssets.swift
#    - LuluStickerBatch 增加 case settings = "S7" 等
#    - LuluStickerCatalog.batch(for:) 把每个新 id 映射到对应批次

# 5. 把新 PNG 加入 Xcode target 资源（project.pbxproj 的 PBXBuildFile /
#    PBXResourcesBuildPhase，参照现有 S1–S6 贴纸条目）

# 6. 替换调用点：按第 4 节表格把旧 id 换成新 id（全仓搜旧 id 字符串）
```

## 7. 验收清单

- [ ] 29 张成品全部 512×512 透明 PNG，白边连续、无文字无阴影
- [ ] 联系表（contact sheet）与首批 36 张并排，风格肉眼一致
- [ ] `LuluStickerCatalog` 能解析全部新 id（单测过）
- [ ] 第 3 节审计表里的牵强映射全部替换，模拟器截图逐页复核
- [ ] 信任勋章 T0–T4 在 M3 页成阶梯展示，视觉递进明确
- [ ] 构建通过，`xcodebuild test -only-testing:OneMoreTests` 全绿

## 8. 参考路径

| 用途 | 路径 |
|---|---|
| 风格基准图 | `assets/ip/lulu/style-reference/style-reference.jpg` |
| 首批成品（对照风格） | `assets/ip/lulu/generated/2026-08-12/stickers/S1–S6/` |
| 抠图工具 | `assets/ip/lulu/tools/remove_chroma_key.py` |
| 拆格/交付工具 | `assets/ip/lulu/tools/build_generated_delivery.py` |
| iOS 贴纸目录注册 | `ios/OneMore/Core/Motion/LuluGeneratedAssets.swift` |
| iOS 贴纸资源 | `ios/OneMore/Resources/LuluGenerated/Stickers/` |
| 设计 token | `design/received/2026-08-12-one-more-lulu-frontend/export/css/tokens.css` |
