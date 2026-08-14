# Lulu Portrait Evolve

**活的用户画像：层次先验 × 行为证据累积 × 滞回稳态。**

课表和抖音是目前最无感、也最准的冷启动。  
画像的最终形态却不该停在导入那天——一个人是什么样的人，取决于他在平台上每一次真实行为：找什么样的搭子，参加什么样的比赛，把哪些局打完。

本系统把这套自进化从主站拆到分支 `feat/lulu-portrait-evolve`。学习发生在事件进入的同步路径上，可回放、可解释、主标签带滞回。主站雏形上线后回写不稳定，所以没有直接推给用户；这里先把内核长成可对外讲清楚的模型。

```
事件源 ──► HEA 饱和更新 ──► 分层指数遗忘 ──► 0.25/0.30/0.45 层次混合
                                              │
                                              ├─► 线性人格投影 + Schmitt 滞回 ──► 主标签
                                              ├─► 证据质量置信度
                                              ├─► 轨迹 / 阶段
                                              └─► 相似 ⊕ 互补亲和
```

**学习闭环不调用大模型。** DeepSeek 只作为可选叙事渲染，失败即回退模板，且被禁止写回任何分数。

---

## 整体效果

输入是一条校园行为时间线，输出不是「又打了一批标签」，而是一张**会随使用校准的活画像**，外加它是怎么长成这样的。

| 产物 | 你能看到什么 |
|---|---|
| Living card | 主标签、兴趣域、自己常站的位置、组队在找的位置、打完的局、阶段 |
| Trajectory | 每一次事件之后主标签 / 置信度 / lived mass 怎么走 |
| Explain | 用中文说明：冷启动是学校记录，改写它的是后来打完的局 |
| Affinity | 两个人为什么能成局：口味重叠，还是「我会的正好是你缺的」 |
| Narrative | 人格短文、成局提示、破冰句（模板；可选 LLM 只润色文字） |
| Model card | 这份报告引用了哪些模型、谁写分数、谁不准写分数 |

林予安回放后的典型效果（`fixtures/linyuan_timeline.json`）：

- 冷启动：软件工程课表 + 抖音「探索型 Builder」
- 行为：问 Hermes 公选 → 跨校区选修 → 智能应用开发大赛（自己后端/数据，缺前端/产品）→ 英东订场并复局 → 数模再找建模和论文
- 结果：主标签落到 **AI 实践派 / 探索型 Builder**，兴趣域被行为抬到 AI/编程 与 运动健康，`roles_sought` 出现前端/产品/论文，阶段进入 **活画像**
- 对照周衡：他站前端，她站后端——亲和分来自互补和同局，不是来自两人填了同一张问卷

```bash
cd lulu-portrait-evolve
pip install -e ".[dev]"
portrait-evolve report fixtures/linyuan_timeline.json
portrait-evolve compare fixtures/linyuan_timeline.json fixtures/zhouheng_timeline.json
```

---

## 引用到的模型

分三层写清楚：**谁在闭环里写分数，谁只是上游冷启动，谁可以被引用但默认不跑。**

### 闭环内 · 决定「他正在变成谁」

| ID | 模型 | 写分数 | 作用 |
|---|---|---|---|
| `hea-v1` | Hierarchical Evidence Accumulator | 是 | 饱和型在线更新。越接近 1 越难再涨，对应 Beta-Bernoulli 均值的一阶近似。 |
| `exp-forget-v1` | Layered Exponential Forgetting | 是 | 分层半衰期：课表 365 天、口味 180 天、行为 60 天。增量衰减，禁止对同一时间戳折两次。 |
| `hier-blend-v1` | Three-Layer Hierarchical Prior | 是 | `0.25·academic + 0.30·taste + 0.45·lived`。行为权最高，课表事实不可抹掉。 |
| `tag-linear-v1` | Linear Persona Projector | 是 | 域 + 行为信号线性投影到 7 个主标签，词表与主站 taste-v2 对齐。 |
| `schmitt-primary-v1` | Schmitt-Trigger Primary Tag | 是 | 主标签翻转必须越过 0.06 滞回带，卡片不会闪。 |
| `evidence-confidence-v1` | Evidence-Mass Confidence | 是 | `1−exp(−mass)`。置信度来自行为质量，不是问卷长度。 |
| `lived-affinity-v1` | Lived Affinity Matcher | 否 | 余弦 + 场景 Jaccard + 互补覆盖 + 同局同伴。 |

形式：

```
s ← s + α w (1 − s)          # 正向证据，α = 0.55
s ← s (1 − α w)              # 临期退出：只收缩场景
s(t) = s(t0) · 2^(−Δt / τ)   # 分层遗忘
flip ⇔ score(leader) ≥ score(current) + 0.06
```

完整公式与不变量见 [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md)。  
机器可读清单：`portrait-evolve models` 或 `GET /v1/models`。

### 上游 · 本仓库不重算，只吃先验

| ID | 模型 | 默认实现 | 本引擎如何用 |
|---|---|---|---|
| `academic-etl-v1` | 培养方案 / 选课能力 ETL | `onemore.modules.profile.init_profile` | `seed_academic`。课程类型加权，**不用成绩**。 |
| `taste-v2` | 抖音兴趣分析 | `onemore.modules.taste_profile` | `seed_taste`。主站里可选 DeepSeek V4 Flash 润色短文，**不决定标签归属**。 |

这两条是「最无感、也最准」的冷启动。自进化吃的是它们之后的行为。

### 可选引用 · 默认关闭

| ID | 可引用模型 | 写分数 | 何时出现 |
|---|---|---|---|
| `llm-narrative-v1` | **DeepSeek V4 Flash**（`deepseek-v4-flash`，OpenAI-compatible；与主站抖音画像同一通道） | **否** | 仅当设置 `PORTRAIT_LLM_API_KEY`，且调用 `report --llm` |

约束：只改写人格短文和破冰句。任何分数、主标签、置信度都不进 prompt 的可写回位置。无 Key、超时、非 JSON，一律回退模板。

---

## 代码体量与模块

跑 `portrait-evolve inventory` 看当前数字。evolve-v2 量级如下：

| 项 | 规模 |
|---|---|
| 源码模块 | 17 个（`src/portrait_evolve/*.py`） |
| 源码非空行 | **1953**（`portrait-evolve inventory` 现测） |
| 事件类型 | 16（浏览 / 提问 / 选修 / 订场 / 发意图 / 入队 / 成局 / 复局 / 临期退出…） |
| 人格标签 / 兴趣域 / 技能 | 7 / 11 / 14 |
| 命名模型 | 10（闭环 7 + 上游 2 + 可选 1） |
| 对照剧本 | 林予安完整学期、周衡互补对照 |
| 测试 | 引擎、衰减、幂等、新事件、报告、亲和、模型卡 |

| 模块 | 职责 |
|---|---|
| `events` / `taxonomy` | 行为事件与校园词表 |
| `engine` / `portrait` / `store` | 学习核、三层状态、事件源投影 |
| `models` | 命名模型与 Model Card |
| `metrics` / `trajectory` | 阶段、覆盖、漂移、逐事件快照 |
| `affinity` | 相似 ⊕ 互补匹配 |
| `narrative` / `llm` / `explain` | 模板叙事、可选 DeepSeek、中文解释 |
| `report` / `inventory` / `cli` / `api` | 报告、体量、命令行、HTTP |

目录在主仓库：`lulu-portrait-evolve/`。

---

## 事件即证据

| 事件 | 强度 | 它在说什么 |
|---|---|---|
| `ask_hermes` | 0.10 | 问了校园代理，弱意图 |
| `browse_competition` / `open_competition` | 0.08 / 0.12 | 看过，接近噪声 |
| `enroll_elective` | 0.50 | 主动选了课，比「说感兴趣」硬 |
| `book_gym` | 0.30 | 把场订下来了 |
| `post_intent` / `seek_teammate` | 0.35–0.40 | 他想干什么、想找谁 |
| `join_team` / `join_competition` | 0.55 | 愿意把自己押进去 |
| `complete_gathering` | 0.80 | 这件事真实发生过 |
| `recur_gathering` | 1.00 | 同一桌人愿意再来 |
| `late_exit` | 0.20（负向） | 只收缩场景，不改写这个人是谁 |

找队友时**自己站的位置**进 `roles_offered`，**缺的位置**只进 `roles_sought`。  
「我做后端，缺前端」不会把前端算成她会的技能。  
`peer_ids` 只累积「和谁一起成过局」，不进技能袋。

---

## 稳定触发

1. 学习在 `ingest` 同步路径，不靠巡检碰运气。  
2. `event_id` 幂等。  
3. 主标签 Schmitt 滞回 0.06。  
4. lived 与 academic 隔离；画像是投影，事件日志可整段回放。  
5. 分数变化 < 0.01 且主标签没变，不发更新。  
6. 大模型不在学习闭环。

---

## 使用

```bash
cd lulu-portrait-evolve
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q

portrait-evolve replay fixtures/linyuan_timeline.json
portrait-evolve report fixtures/linyuan_timeline.json
portrait-evolve compare fixtures/linyuan_timeline.json fixtures/zhouheng_timeline.json
portrait-evolve models
portrait-evolve inventory
```

```python
from portrait_evolve import BehaviorEvent, build_report, model_card

events = [...]  # seed + 找搭子 + 参赛 + 成局
report = build_report("u_demo_1", events, display_name="林予安")
print(report["portrait"]["primary_tag"], report["metrics"]["stage"])
print(model_card()["llm_in_learning_loop"])  # False
```

HTTP（可选）：

```
GET  /v1/models
GET  /v1/inventory
POST /v1/events
POST /v1/replay
POST /v1/compare
GET  /v1/portraits/{id}/report
```

主站继续做教务和抖音冷启动。本引擎只吃行为事件，吐出永不过时的 lived 层。接回时在发意图、入队、成局、复局、订场、选修处打 `POST /v1/events` 即可。
