# ONE MORE 36 状态 Fidelity Checklist（Round 4）

## 证据前缀

- 设计：`/Users/baihe/Documents/compusone/design/received/2026-08-11-one-more-mobile-prototype/screens/`
- 运行：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/runtime/`
- 36 屏捕获记录：`/Users/baihe/Documents/compusone/ios/artifacts/logs/runtime-screenshot-capture.csv`
- 状态证据：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/states/`
- 状态总览：`/Users/baihe/Documents/compusone/ios/artifacts/screenshots/STATE_EVIDENCE_CONTACT_SHEET.png`
- 最终证据索引：`/Users/baihe/Documents/compusone/ios/artifacts/logs/visual-evidence-final-r4.json`
- 每行 `证据` 表示同名设计 PNG 与 Round 4 运行 PNG 的一对一映射。
- `SSIM-D` 为 ImageMagick `compare -metric SSIM` 返回的归一化差异值；与 RMSE 一样，`0` 最接近。
- 指标为辅助证据，不自动决定判级；A3 动态二维码、24 场真实数据和指定粉发女孩替换不会被误判为业务缺陷。
- 证据绑定：产品源码树 `8857dedffff006e66f98b4cd8ab367a7018a4ce176796e90343d9c1203befc25`（144 文件）；实际可执行文件 `44986a13c702a07dc5c47e7627cfd80ee63897ace5cceb0034996cd287041e52`。

## 逐屏结论

| 证据 | 节点 | 标题 | RMSE | SSIM-D | 判定 | Round 4 视觉差异与剩余收口 |
|---|---|---|---:|---:|---|---|
| `a2.png` | A2 | 价值引导 | 0.277 | 0.181 | minor | 粉发女孩首帧稳定且旧橙图为零；全身素材比设计占位图窄、小。增大显示框或使用安全裁切，提高主视觉重量。 |
| `a3.png` | A3 | 扫码认证 | 0.413 | 0.265 | minor | 动态二维码不同可接受；运行 QR glass 更大、更亮，状态 pill 和 CTA 略上移。收紧卡高/内边距并降低 surface 不透明度。 |
| `a4.png` | A4 | 分项授权 | 0.286 | 0.233 | minor | 四开关、红线说明和双动作顺序正确；运行行卡更亮、更密。统一 12–16 pt 节奏和 glass alpha。 |
| `a5.png` | A5 | 画像初始化 | 0.240 | 0.130 | pass | 标题、四步状态、进度线、CTA 和次动作一致；仅原生 spinner、状态栏及小幅字距不同。 |
| `a6.png` | A6 | 画像确认 | 0.252 | 0.186 | minor | 认证事实维持单卡；运行内容更紧、surface 更实，能力标签/可用时段略上移。只需调 card padding、divider 节奏和透明度。 |
| `a7.png` | A7 | 社交开关 | 0.268 | 0.188 | pass | 标题、开关、红线、主/次动作和层级一致；剩余为状态栏、字距和轻微纵向差。 |
| `b1.png` | B1 | 今天 / hermes | 0.169 | 0.232 | minor | 时间线、Hermes、Tab 和提醒卡正确；同一粉发女孩已出现但小位过窄，提醒卡 surface 偏亮。 |
| `c1.png` | C1 | 公开局 | 0.173 | 0.221 | minor | 两张公开局卡、人数进度、动作和 Tab 正确；运行首卡偏高，信息顺序/行距略有差异。 |
| `b12.png` | B12 | 比赛 | 0.191 | 0.271 | minor | 每场赛事保持完整单卡。24 场是正确业务数据；剩余为卡面偏亮、首屏密度和 tag 间距。 |
| `b12d.png` | B12.1 | 赛事详情 | 0.193 | 0.255 | pass | 赛程、规则、要求、能力标签、CTA 和 Tab 安全区与基准层级一致；真实文案差异可接受。 |
| `table.png` | B12.2 | 牌桌 · 差一个 | 0.270 | 0.271 | minor | 四席位、中心目标、4/4 状态和主 CTA 齐全；圆桌直径/纵向中心有偏移，确认条偏灰。 |
| `msg.png` | MSG | 消息 | 0.143 | 0.206 | minor | “阿”字头像已替换为同一粉发女孩，9/9 IP 位一致；该列表小图仍过窄，需用专用安全裁切提高辨识度。 |
| `d1.png` | D1 | 意图输入 | 0.253 | 0.175 | minor | “交给阿凑”完整固定在底部，原 major 持续关闭；运行 CTA 约高 50 px，小型粉发女孩过窄。 |
| `d2.png` | D2 | 澄清追问 | 0.117 | 0.124 | minor | 对话、三选项和轮次文案接近；同一女孩已出现，但 38×42 pt 内可辨识面积偏小。 |
| `d3.png` | D3 | 意图卡确认 | 0.268 | 0.272 | minor | 所有字段、divider、发布 CTA 和存草稿均完整；运行事实卡比设计短、行距偏紧，CTA 略高。 |
| `d4.png` | D4 | 招募中 | 0.253 | 0.192 | minor | 三动作均完整进入 bottom safe area，原裁切 major 持续关闭；运行 action stack 约高 20–25 px，glass 偏亮。 |
| `e3.png` | E3 | 多人确认 | 0.254 | 0.228 | minor | 4/4 单一动作状态正确，状态摘要与 CTA 已落底；运行摘要为轻量图标文字而非设计描边条，整体约高 50 px。 |
| `e5.png` | E5 | 预览与授权 | 0.233 | 0.207 | minor | 主/次动作已从正文拆出并落到底部，权重正确；预览卡更紧、更实，动作区约高 35–40 px。 |
| `e6.png` | E6 | 执行结果 | 0.253 | 0.197 | minor | 凭证、日历卡和“进入协作空间”完整可见；运行卡面偏实，内容与 CTA 略高。 |
| `e7.png` | E7 | 协作空间 | 0.268 | 0.275 | minor | 地点、阿凑气泡、待办、成员和四动作完整；同一粉发女孩可见，整体更紧、更亮。 |
| `e14.png` | E14 | 局内群聊 | 0.165 | 0.203 | minor | 聊天方向、输入栏、@ 和粉发女孩气泡齐全；小 IP 过窄，mention/气泡锚点略有偏差。 |
| `b5.png` | B5 | 场馆空场 | 0.115 | 0.168 | pass | 两个场馆均为单卡内标题 + 时段行，Tab 和说明层级接近；仅动态时段文案和轻微 surface 差。 |
| `b5s.png` | B5.1 | 时段选择 | 0.133 | 0.122 | pass | 2×2 时段栅格、禁用/选中态、底部 CTA 与设计一致。 |
| `e9.png` | E9 | 完成确认 | 0.216 | 0.179 | pass | 标题、三选项、事实补充框和底部提交 CTA 均完整，主要视觉权重一致。 |
| `e10.png` | E10 | 复局选择 | 0.132 | 0.158 | minor | 中央粉发女孩和三个复局选项齐全；人物比设计旧占位图窄、小，可继续放大或安全裁切。 |
| `b4.png` | B4 | 作业与 DDL | 0.126 | 0.163 | pass | 首条作业为完整横向卡，DDL、主动作、其余列表和 Tab 层级一致。 |
| `b4d.png` | B4.1 | 作业详情 | 0.201 | 0.167 | minor | 标题、DDL、说明、CTA 和粉发女孩提示卡齐全；角色过窄，提示正文换行/对齐略偏。 |
| `b7.png` | B7 | 活动（免登录） | 0.119 | 0.118 | pass | 两张活动卡、筛选、提示和 Tab 保持完整横向布局，内容密度接近设计。 |
| `b7d.png` | B7.1 | 活动详情 | 0.139 | 0.154 | minor | 官方报名 CTA 完整位于 safe area，原裁切 major 持续关闭；运行图标在文字前而非末尾，按钮约高 50 px。 |
| `g2.png` | G2 | 缺口卡分享 | 0.135 | 0.208 | minor | 分享 sheet、缺口卡和四动作齐全；运行 sheet 更窄、上沿更低，卡片右下使用 cyan 箭头。 |
| `c4.png` | C4 | 缺口卡落地页 | 0.229 | 0.339 | pass | 浏览器条、标题、需求卡、说明和“我来”CTA 层级一致；指标偏高主要来自浏览器/字体/背景。 |
| `e1.png` | E1 | 我的局 / 搭子 | 0.177 | 0.283 | minor | 搭子内容保持一体卡；运行仍显示额外卡内“进入对话”文字，第二项更高、surface 更实。 |
| `e16.png` | E16 | 搭子详情 | 0.135 | 0.149 | pass | 经历时间线、共同点单卡和三动作完整，主要位置与设计接近。 |
| `e17.png` | E17 | 解除关系 | 0.114 | 0.189 | minor | 保持底部短 sheet；运行 sheet 左右留白更大、上沿约高 20 px。 |
| `m1.png` | M1 | 我 | 0.156 | 0.253 | minor | T2 进度和 `7 / 3 / 100%` 三统计块正确；glass 偏亮，后续列表密度与设计略有差异。 |
| `m3.png` | M3 | 等级详情 | 0.250 | 0.246 | minor | “列表→CTA→免责声明”顺序和首帧可见性保持；整体核心内容比设计下移约 70–80 px，glass 更实。 |

## 汇总

| 等级 | 数量 | 节点 |
|---|---:|---|
| major | **0** | — |
| minor | **26** | A2, A3, A4, A6, B1, C1, B12, B12.2, MSG, D1, D2, D3, D4, E3, E5, E6, E7, E14, E10, B4.1, B7.1, G2, E1, E17, M1, M3 |
| pass | **10** | A5, A7, B12.1, B5, B5.1, E9, B4, B7, C4, E16 |

## Round 3 → Round 4 新鲜度复核

| 项目 | Round 3 | Round 4 | 变化 |
|---|---:|---:|---:|
| major | 0 | 0 | 0 |
| minor | 26 | 26 | 0 |
| pass | 10 | 10 | 0 |

Round 4 使用最终产品源码树重新构建并重新捕获，取代早于后续源码修改的 Round 3 截图。36 屏逐项视觉结构与判级均无回归；没有新增 major。

## 8 类状态证据检查

| 状态 | 证据 | 覆盖 | Round 4 视觉结论 |
|---|---|---|---|
| loading / skeleton | `states/loading.png` | 是 | skeleton、spinner 和防旧成功态说明完整 |
| empty | `states/empty.png` | 是 | 图标、说明和“去看公开局”CTA 完整 |
| network error | `states/network-error.png` | 是 | 错误说明和重试动作完整 |
| offline | `states/offline.png` | 是 | 缓存边界说明和联网后重试完整 |
| permission denied | `states/permission-denied.png` | 是 | 去系统设置主动作和暂不次动作完整 |
| session expired | `states/session-expired.png` | 是 | 重新扫码恢复动作完整 |
| duplicate tap | `states/duplicate-tap.png` | 是 | 已接收状态和 disabled processing CTA 完整 |
| stale state | `states/stale-state.png` | 是 | 服务端变化说明和刷新动作完整 |

## IP、旧资源与证据完整性检查

- A2、E10 主位：同一粉发女孩。
- B1、D1、D2、E7、E14、B4.1、MSG 小位：同一粉发女孩。
- 9/9 可见位一致。
- 36 张关键运行图：旧橙色近似像素 `0`。
- 8 张状态图：旧橙色近似像素 `0`。
- 36/36 运行 PNG 与 `runtime-screenshot-sha256.txt` 匹配。
- 8/8 状态 PNG 与 `state-evidence-sha256.txt` 匹配。
- 运行/状态 contact sheet 哈希分别为 `8112156a5a976204740c1bdd3550260a10ee00f332698090a8dfad9e639cff6a`、`5c4e904a0d04c7cb73e6ca40e6943a5c671ba9e6008d7969e8a7ce09dafbebe0`。

**Round 4 Gate 结果：major 0，Gate 2 通过。**
