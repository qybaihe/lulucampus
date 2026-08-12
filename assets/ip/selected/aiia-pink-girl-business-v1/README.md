# AIIA 粉发创变者 · 阿凑业务动作版 V1

当前选定的动态 IP 资产包。角色视觉参考来自[抖音 AI 创变者计划 2026 官网](https://aiia.douyin.com/)，动作系统围绕「差一个」产品中的意图理解、撮合、确认、执行与退场设计。

## 资产规格

- `base-transparent.png`：透明基准形象；
- `frames/`：57 张透明 PNG 帧，单帧 `192×208`；
- `spritesheet.webp` / `spritesheet.png`：`1536×1872`、8 列 × 9 行图集；
- `spritesheet@2x.webp` / `spritesheet@2x.png`：`3072×3744` 高清演示图集，避免桌面大尺寸预览插值发糊；
- `previews/`：九组 GIF 与动画 WebP；
- `previews@2x/`：九组 384×416 高清动画 WebP，供桌面演示页使用；
- `motion-contract.json`：业务状态、逐帧时长、事件序列与运行时策略；
- `pet.json`：角色身份与业务状态映射；
- `contact-sheet.png`：全部动作帧总览；
- `validation.json`、`qa/`：自动检查结果；
- `generation-prompts.md`：最终图像生成提示词组。

## 九个业务状态

| 行 | 业务状态 | 图集源行 | 含义 |
|---:|---|---|---|
| 0 | `idle` | `idle` | 安静待机 |
| 1 | `appear` | `running-right` | 闭眼休眠到睁眼显现 |
| 2 | `exit` | `running-left` | 闭眼收束并退场 |
| 3 | `greeting` | `waving` | 轻量招呼 |
| 4 | `success` | `jumping` | 冷静的执行成功确认 |
| 5 | `needs-adjustment` | `failed` | 分析、重算、准备重试 |
| 6 | `waiting-confirmation` | `waiting` | 等待确认、授权或选择 |
| 7 | `executing` | `running` | 正在撮合或执行任务 |
| 8 | `closed-eye-sensing` | `review` | 标志性闭眼感知与意图编译 |

`running-right`、`running-left`、`jumping` 等名称仅为固定图集协议的兼容行名，业务层必须使用对应的业务状态名，不应添加左右跑动。

## 演示入口

打开 `prototypes/aiia-pink-girl-motion-preview/index.html`，可逐项触发首次出现、闭眼感知、正在执行、等待确认、成功、暂未完成和真人对话退场。
