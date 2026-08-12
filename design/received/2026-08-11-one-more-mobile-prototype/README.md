# ONE MORE 移动端返回设计稿 · 冻结副本

> 导入时间：2026-08-11 21:43（Asia/Shanghai）  
> 角色：iOS 视觉与交互基准，不是可直接嵌入 App 的生产代码

## 1. 固定入口

- 原始压缩包：`/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/raw/Mobile app scope questionnaire.zip`
- 解压入口：`/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/export/ONE MORE 原型.dc.html`
- 文件与校验清单：`/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/SOURCE_MANIFEST.json`
- 36 个手机画板：`/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/screens/`
- 画板总览：`/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/SCREEN_CONTACT_SHEET.png`
- 浏览器检查证据：`/Users/baihe/Documents/compusone/output/playwright/one-more-design-return/`

原始压缩包 SHA-256：

```text
6e6630b369601f4ad517648521af3357772c74fba183775e70fdfc9536df53cb
```

## 2. 本地预览

```bash
cd "/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/export"
python3 -m http.server 8765 --bind 127.0.0.1
```

浏览器打开：

```text
http://127.0.0.1:8765/ONE%20MORE%20%E5%8E%9F%E5%9E%8B.dc.html
```

不要只通过 `file://` 打开；HTTP 预览能稳定加载同目录的 `support.js`、CSS 与图片。

## 3. 设计基线

- 设备画板：`402 × 874`，设计稿标注为 iPhone 17。
- 页面底色：`#010001`。
- 主强调：青色 `#00FFE1` 与青色渐变。
- 次强调：洋红 `#FF4FD3`。
- 组件：黑底、半透明玻璃面、细边框、20/32 pt 圆角、胶囊按钮。
- 字体：生产 iOS 使用系统中文字体（PingFang SC）；压缩包没有可再分发的 DouyinSans 字体文件。
- 主导航：今天、比赛/公开局、中央“⊕ 差一个”、消息/我的局、我。最终实现需以 74 节点指南规定的主导航语义为准，并保留设计稿的视觉语言。

## 4. 画板覆盖

返回原型含 **36 个可交互状态**，浏览器逐个切换检查为 **36/36 通过**，无控制台错误或页面错误。

其中 **34 个状态**直接覆盖 74 个正式设计节点：

```text
A2 A3 A4 A5 A6 A7
B1 B4 B4.1 B5 B5.1 B7 B7.1 B12 B12.1
C1 C4
D1 D2 D3 D4
E1 E3 E5 E6 E7 E9 E10 E14 E16 E17
M1 M3
G2
```

两个额外组合状态：

- `B12.2`：赛事牌桌/补位座位；
- `MSG`：消息聚合页。

正式 74 节点中仍有 **40 个未在返回原型中单独出图**：

```text
A1 A8
B2 B3 B3.1 B6 B6.1 B8 B9 B10 B11
C2 C3
D3.1 D3.2 D3.3 D3.4
E2 E4 E8 E11 E12 E13 E15
M2 M4 M5 M6 M7 M8 M9 M10
O1 O2 O3 O4
G1 G3 G4 G5
```

因此该返回稿是重要视觉基准，但不是 74 节点全量交付。iOS 实现必须先 1:1 还原已有 36 个状态，再根据 `/Users/baihe/Documents/compusone/docs/01_iOS客户端开发指南.md` 与 `/Users/baihe/Documents/compusone/docs/05_iOS设计交接提示词.md`，以相同设计系统补齐上述 40 个节点及空、错、加载、离线、权限拒绝等状态。

## 5. 已验证交互

本轮只验证返回稿自身，不进行了 iOS 合并。以下浏览器原型交互已实际点击通过：

1. 赛事列表与详情切换；
2. 牌桌入座，`3/4 → 4/4`；
3. 意图输入 → 两轮澄清 → 意图卡 → 匿名招募；
4. 多人确认，`2/4 → 3/4 → 4/4`；
5. 行动执行结果 → 日历权限模拟 → “已加入日历”；
6. 局内群聊输入并发送文本；
7. 36 个原型状态均可由左侧轨道进入。

这些交互当前全是 HTML 内存状态与示例数据，不能当作前后端已联调证据。

## 6. IP 形象替换规则

原型 HTML 的十处 `<img>` 当前都引用：

```text
export/assets/azou.png
```

它是橙色团子占位图，最终 App **不得使用**。同包中的 `export/assets/azou-alt.png` 已与当前选定粉发女孩的 `base-transparent.png` 做到字节级一致，但生产端也不要从返回稿目录散拷贝资源。

唯一生产来源：

```text
/Users/baihe/Documents/compusone/assets/ip/selected/aiia-pink-girl-business-v1/
```

SwiftUI 必须读取该目录的 `motion-contract.json` 与 `frames/frames-manifest.json`，按九个业务状态播放 57 张透明帧；业务层只使用 `idle / appear / exit / greeting / success / needs-adjustment / waiting-confirmation / executing / closed-eye-sensing`，不使用图集兼容名称 `running-left`、`running-right` 等。

## 7. 生产实现规则

1. HTML 只作为布局、层级、文案与动效意图参考，不以 `WKWebView` 包装交付。
2. 使用原生 SwiftUI 重建视图、导航、状态与无障碍语义。
3. 示例赛事“21 场”必须替换为后端返回数据；当前生产快照是 24 条。
4. 示例日期、人数、确认进度、场馆状态与聊天内容必须由 API 或明确的 Preview Fixture 提供，运行版不得混用硬编码成功态。
5. 外部 URL、系统分享、EventKit、通知、照片、语音、位置均走 iOS 原生能力。
6. 所有主要按钮要有真实导航或业务动作，不保留无处理的 `cursor:pointer` 等原型占位。
7. 降低动态效果开启时，按 `motion-contract.json` 的 `reducedMotionColumn` 使用静态帧。

