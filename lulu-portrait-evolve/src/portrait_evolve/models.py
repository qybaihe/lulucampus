"""Named models used by the living portrait.

The learning loop is fully deterministic. Large language models are listed
here only as optional narrative renderers — they never write scores.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Loop = Literal["in_loop", "optional", "upstream"]


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    loop: Loop
    writes_scores: bool
    role: str
    formulation: str
    lineage: str
    default: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# In-loop models. These decide who the person is becoming.
# ---------------------------------------------------------------------------

HEA = ModelSpec(
    id="hea-v1",
    name="Hierarchical Evidence Accumulator",
    loop="in_loop",
    writes_scores=True,
    role="把每一次平台行为写成可衰减、可饱和的证据，再投影成三层画像。",
    formulation=(
        "s ← s + α·w·(1−s)  （正向）；s ← s·(1−α·w)  （负向场景收缩）。"
        "α=0.55 为饱和步长，w 为事件证据强度。"
    ),
    lineage="在线学习里的 saturating EMA；可视为 Beta-Bernoulli 均值在线更新的一阶近似。",
)

FORGET = ModelSpec(
    id="exp-forget-v1",
    name="Layered Exponential Forgetting",
    loop="in_loop",
    writes_scores=True,
    role="让过时口味褪色，同时保住学校记录。按层设置半衰期，增量衰减，禁止对同一时间戳重复折算。",
    formulation="s(t)=s(t0)·2^{−Δt/τ}，τ_academic=365d，τ_taste=180d，τ_lived=60d。",
    lineage="Ebbinghaus 遗忘曲线的指数形式；推荐系统里的 time-decay CF。",
)

HIERARCHY = ModelSpec(
    id="hier-blend-v1",
    name="Three-Layer Hierarchical Prior",
    loop="in_loop",
    writes_scores=True,
    role="academic / taste 是先验，lived 是似然。混合时行为权最高，课表事实不可被行为抹掉。",
    formulation="x = 0.25 x_academic + 0.30 x_taste + 0.45 x_lived",
    lineage="层次贝叶斯的经验分层：慢变量作 prior，快变量作 likelihood。",
)

TAG_SCORE = ModelSpec(
    id="tag-linear-v1",
    name="Linear Persona Projector",
    loop="in_loop",
    writes_scores=True,
    role="把域分数与行为信号投到 7 个主标签上，得到探索型 Builder / AI 实践派等人格卡。",
    formulation=(
        "score(tag)= (Σ d_i w^d_i + Σ s_j w^s_j + b·breadth) / (Σw^d+Σw^s+b)，"
        "再 clip 到 [0,1]。"
    ),
    lineage="与主站 taste-v2 的 TAG_DEFINITIONS 对齐，保证匹配词表不分裂。",
)

HYSTERESIS = ModelSpec(
    id="schmitt-primary-v1",
    name="Schmitt-Trigger Primary Tag",
    loop="in_loop",
    writes_scores=True,
    role="主标签翻转必须越过 0.06 滞回带，避免卡片在两个标签之间闪。",
    formulation="flip only if score(leader) ≥ score(current) + 0.06",
    lineage="控制理论里的 Schmitt trigger；稳定分类器的 hysteresis band。",
)

CONFIDENCE = ModelSpec(
    id="evidence-confidence-v1",
    name="Evidence-Mass Confidence",
    loop="in_loop",
    writes_scores=True,
    role="置信度来自行为质量，不是问卷填了多少。先验只给一个很小的地板。",
    formulation="c = clip( 0.18·1_academic + 0.18·1_taste + (1−e^{−m/3.2}) )",
    lineage="1−exp(−mass) 是泊松到达的覆盖函数，也常见于证据理论。",
)

AFFINITY = ModelSpec(
    id="lived-affinity-v1",
    name="Lived Affinity Matcher",
    loop="in_loop",
    writes_scores=False,
    role="用进化后的向量做相似 / 互补匹配：口味相近加分，自己会的对上对方缺的再加分。",
    formulation=(
        "sim = 0.45 cos(d)+0.20 cos(k)+0.15 Jaccard(scene)+0.20 complement(offered,sought)"
    ),
    lineage="主站 matching 的 taste Jaccard + 互补覆盖，收到独立引擎里可回放。",
)

# ---------------------------------------------------------------------------
# Optional / upstream. Cited so reviewers know what is and is not in the loop.
# ---------------------------------------------------------------------------

TASTE_V2 = ModelSpec(
    id="taste-v2",
    name="Douyin Taste Analyzer",
    loop="upstream",
    writes_scores=False,
    role="主站冷启动：喜欢/收藏 → 域分布与主标签。本引擎只把它当作 taste 先验，不在这里重算。",
    formulation="关键词域份额 × 行为信号 × 可选 3–5 题校准",
    lineage="onemore/modules/taste_profile（taste-v2）",
    default="taste-v2",
)

ACADEMIC_ETL = ModelSpec(
    id="academic-etl-v1",
    name="Curriculum Capability ETL",
    loop="upstream",
    writes_scores=False,
    role="主站冷启动：培养方案 + 选课 → 能力向量。只用「修过什么」，不用成绩。",
    formulation="weight(course_type) ∈ {必修 1.0, 限选 1.2, 任选 1.4, 跨专业 1.8, 辅修 2.0}",
    lineage="onemore/modules/profile.init_profile",
)

LLM_NARRATIVE = ModelSpec(
    id="llm-narrative-v1",
    name="Optional Narrative Renderer",
    loop="optional",
    writes_scores=False,
    role="只改写人格短文与破冰句。分数、主标签、置信度一律不交给它。失败则回退模板。",
    formulation="Chat Completions · temperature≤0.4 · JSON {persona, icebreakers}",
    lineage="OpenAI-compatible；与主站抖音画像同一条 DeepSeek 通道可复用。",
    default="deepseek-v4-flash",
)

IN_LOOP = (HEA, FORGET, HIERARCHY, TAG_SCORE, HYSTERESIS, CONFIDENCE, AFFINITY)
UPSTREAM = (TASTE_V2, ACADEMIC_ETL)
OPTIONAL = (LLM_NARRATIVE,)
ALL_MODELS = (*IN_LOOP, *UPSTREAM, *OPTIONAL)


def model_card() -> dict[str, Any]:
    return {
        "system": "lulu-portrait-evolve",
        "version": "evolve-v2",
        "learning_loop": "deterministic",
        "llm_in_learning_loop": False,
        "in_loop": [item.to_dict() for item in IN_LOOP],
        "upstream": [item.to_dict() for item in UPSTREAM],
        "optional": [item.to_dict() for item in OPTIONAL],
        "invariants": [
            "academic 层不可被 lived 事件抹掉，只可被时间缓慢衰减或再次选课加强。",
            "roles_sought 不写入 skills。",
            "同一 event_id 至多生效一次。",
            "大模型不得写回任何 score / tag / confidence。",
        ],
    }
