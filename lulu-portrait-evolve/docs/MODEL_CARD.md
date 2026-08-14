# Model Card · lulu-portrait-evolve / evolve-v2

状态：学习闭环已实现并可回放。叙事大模型为可选渲染，默认关闭。

## 1. 系统意图

用**不可自我美化的学校记录**做冷启动，用**平台上每一次真实行为**做持续校准，得到一张会呼吸、永不过时的校园用户画像。

不是推荐模型，不是聊天人格，不是问卷聚类。

## 2. 闭环内模型（写分数）

| ID | 名称 | 公式 / 规则 | 谱系 |
|---|---|---|---|
| `hea-v1` | Hierarchical Evidence Accumulator | 正向 `s←s+αw(1−s)`，负向 `s←s(1−αw)`，α=0.55 | 饱和 EMA；Beta-Bernoulli 均值的一阶在线近似 |
| `exp-forget-v1` | Layered Exponential Forgetting | `s(t)=s(t0)·2^{−Δt/τ}`，τ=365/180/60 天 | Ebbinghaus 指数遗忘；time-decay CF |
| `hier-blend-v1` | Three-Layer Hierarchical Prior | `0.25 academic + 0.30 taste + 0.45 lived` | 层次贝叶斯的经验分层 |
| `tag-linear-v1` | Linear Persona Projector | 域/信号加权线性投影到 7 个主标签 | 与主站 taste-v2 词表对齐 |
| `schmitt-primary-v1` | Schmitt-Trigger Primary Tag | 翻转阈值 +0.06 | 控制理论滞回 |
| `evidence-confidence-v1` | Evidence-Mass Confidence | `c=clip(0.18·1_a+0.18·1_t+1−e^{−m/3.2})` | 泊松覆盖 / 证据质量 |
| `lived-affinity-v1` | Lived Affinity Matcher | 余弦 + Jaccard + 互补覆盖 + 同局同伴 | 主站 matching 的可回放核 |

**不写分数的闭环模块：** `lived-affinity-v1` 只输出匹配解释。

## 3. 上游冷启动（本仓库不重算）

| ID | 来源 | 本引擎如何用 |
|---|---|---|
| `taste-v2` | `onemore/modules/taste_profile` | 写入 taste 先验。可选 DeepSeek V4 Flash 只润色抖音短文，不决定标签。 |
| `academic-etl-v1` | `onemore/modules/profile.init_profile` | 写入 academic 先验。课程类型加权，**不用成绩**。 |

## 4. 可选引用（默认不跑）

| ID | 默认模型 | 约束 |
|---|---|---|
| `llm-narrative-v1` | `deepseek-v4-flash`（OpenAI-compatible，主站同一通道） | 只改写 `persona` / `icebreakers`。禁止写回 score / tag / confidence。无 Key 或失败则回退模板。 |

环境变量：`PORTRAIT_LLM_API_KEY`、`PORTRAIT_LLM_BASE_URL`、`PORTRAIT_LLM_MODEL`。

## 5. 不变量

1. academic 不可被 lived 抹掉。
2. `roles_sought` 不进入 `skills`。
3. `event_id` 至多生效一次。
4. 大模型不得进入学习闭环。
5. 主标签翻转必须越过滞回带。

## 6. 评测方式

离线回放 `fixtures/linyuan_timeline.json` 与 `fixtures/zhouheng_timeline.json`。  
断言：阶段进入 converging/living、互补角色不被误认为本人技能、两人亲和分来自互补与同局而非自述。
