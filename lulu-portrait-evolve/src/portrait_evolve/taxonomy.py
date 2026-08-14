"""Deterministic map from campus behavior → domains / skills / signals / scenes.

Aligned with 噜噜成局's taste + capability tag space so this engine can plug
back into matching without a second vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TagDef:
    key: str
    label: str
    domains: dict[str, float] = field(default_factory=dict)
    signals: dict[str, float] = field(default_factory=dict)
    breadth: float = 0.0


DOMAIN_LABELS: dict[str, str] = {
    "ai_programming": "AI / 编程 / 开源",
    "tech_devices": "数码与工具",
    "gaming_strategy": "策略与博弈",
    "visual_creation": "视觉创作",
    "music_literature": "音乐与文字",
    "career_growth": "成长 / 职业",
    "knowledge_method": "知识与方法",
    "finance_consumption": "商业与消费",
    "health_sports": "运动健康",
    "travel_city": "旅行与城市",
    "relationship_family": "关系与生活",
}

SKILL_LABELS: dict[str, str] = {
    "frontend": "前端",
    "backend": "后端",
    "design": "设计",
    "visual_design": "视觉",
    "product": "产品",
    "data_analysis": "数据分析",
    "machine_learning": "机器学习",
    "algorithm": "算法",
    "presentation": "路演",
    "writing": "文案 / 论文",
    "research": "调研 / 建模",
    "video": "视频",
    "operations": "运营",
    "business_analysis": "商业分析",
}

SIGNAL_LABELS: dict[str, str] = {
    "action_oriented": "行动导向",
    "competitive": "竞争成就",
    "aesthetic": "审美导向",
    "cost_efficient": "低成本优化",
    "light_entertainment": "轻松娱乐",
}

SCENE_LABELS: dict[str, str] = {
    "比赛组队": "比赛组队",
    "比赛备赛搭子": "比赛备赛",
    "项目组队": "项目组队",
    "运动搭子": "运动搭子",
    "DDL冲刺": "DDL 冲刺",
    "自习搭子": "自习搭子",
    "活动同行": "活动同行",
    "通用搭子": "通用搭子",
}

ROLE_ALIASES: dict[str, str] = {
    "前端": "frontend",
    "frontend": "frontend",
    "后端": "backend",
    "backend": "backend",
    "产品": "product",
    "product": "product",
    "视觉": "visual_design",
    "设计": "design",
    "design": "design",
    "算法": "algorithm",
    "algorithm": "algorithm",
    "机器学习": "machine_learning",
    "machine_learning": "machine_learning",
    "数据": "data_analysis",
    "数据分析": "data_analysis",
    "data_analysis": "data_analysis",
    "建模": "research",
    "论文": "writing",
    "写作": "writing",
    "路演": "presentation",
    "运营": "operations",
    "调研": "research",
}

# Scene → lived prior. Completing a badminton gathering says more about
# health_sports than about the person's academic major.
SCENE_PRIORS: dict[str, dict[str, dict[str, float]]] = {
    "比赛组队": {
        "domains": {"career_growth": 0.35},
        "signals": {"action_oriented": 0.55, "competitive": 0.70},
    },
    "比赛备赛搭子": {
        "domains": {"career_growth": 0.25, "knowledge_method": 0.20},
        "signals": {"action_oriented": 0.45, "competitive": 0.50},
    },
    "项目组队": {
        "domains": {"career_growth": 0.30, "knowledge_method": 0.20},
        "signals": {"action_oriented": 0.50},
    },
    "运动搭子": {
        "domains": {"health_sports": 0.90},
        "signals": {"action_oriented": 0.35},
    },
    "DDL冲刺": {
        "domains": {"knowledge_method": 0.35, "career_growth": 0.20},
        "signals": {"action_oriented": 0.40, "cost_efficient": 0.30},
    },
    "自习搭子": {
        "domains": {"knowledge_method": 0.40},
        "signals": {"cost_efficient": 0.25},
    },
    "活动同行": {
        "domains": {"career_growth": 0.20, "relationship_family": 0.15},
        "signals": {"light_entertainment": 0.20},
    },
}

TEXT_DOMAIN_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("黑客松", "ai_programming"),
    ("hackathon", "ai_programming"),
    ("智能应用", "ai_programming"),
    ("人工智能", "ai_programming"),
    ("大模型", "ai_programming"),
    ("编程", "ai_programming"),
    ("开源", "ai_programming"),
    ("数模", "knowledge_method"),
    ("数学建模", "knowledge_method"),
    ("建模", "knowledge_method"),
    ("论文", "knowledge_method"),
    ("调研", "knowledge_method"),
    ("设计", "visual_creation"),
    ("视觉", "visual_creation"),
    ("视频", "visual_creation"),
    ("羽毛球", "health_sports"),
    ("篮球", "health_sports"),
    ("跑步", "health_sports"),
    ("健身", "health_sports"),
    ("球", "health_sports"),
    ("路演", "career_growth"),
    ("创业", "career_growth"),
    ("商业", "finance_consumption"),
    ("金融", "finance_consumption"),
    ("公选", "knowledge_method"),
    ("选修", "knowledge_method"),
    ("hermes", "career_growth"),
    ("场馆", "health_sports"),
    ("订场", "health_sports"),
    ("英东", "health_sports"),
)

SKILL_TO_DOMAIN: dict[str, str] = {
    "frontend": "ai_programming",
    "backend": "ai_programming",
    "machine_learning": "ai_programming",
    "algorithm": "ai_programming",
    "data_analysis": "knowledge_method",
    "research": "knowledge_method",
    "writing": "knowledge_method",
    "product": "career_growth",
    "operations": "career_growth",
    "presentation": "career_growth",
    "business_analysis": "finance_consumption",
    "design": "visual_creation",
    "visual_design": "visual_creation",
    "video": "visual_creation",
}

TAG_DEFINITIONS: tuple[TagDef, ...] = (
    TagDef(
        "explorer_builder",
        "探索型 Builder",
        domains={"ai_programming": 1.5, "knowledge_method": 1.5, "tech_devices": 1.0},
        signals={"action_oriented": 2.0},
        breadth=2.5,
    ),
    TagDef(
        "ai_practitioner",
        "AI 实践派",
        domains={"ai_programming": 3.0, "career_growth": 0.5},
        signals={"action_oriented": 2.0},
    ),
    TagDef(
        "practical_romantic",
        "务实浪漫",
        domains={"travel_city": 0.5, "relationship_family": 0.5},
        signals={"cost_efficient": 2.0, "aesthetic": 1.5},
    ),
    TagDef(
        "strategic_player",
        "策略玩家",
        domains={"gaming_strategy": 3.0, "career_growth": 0.5},
        signals={"competitive": 2.0, "light_entertainment": 0.5},
    ),
    TagDef(
        "knowledge_curator",
        "知识策展人",
        domains={"knowledge_method": 2.5, "career_growth": 1.0, "music_literature": 0.5},
        signals={"action_oriented": 0.5},
        breadth=1.5,
    ),
    TagDef(
        "aesthetic_observer",
        "审美观察者",
        domains={"visual_creation": 2.0, "music_literature": 2.0},
        signals={"aesthetic": 2.5},
    ),
    TagDef(
        "growth_driver",
        "成长驱动者",
        domains={"career_growth": 3.0, "health_sports": 0.5},
        signals={"competitive": 2.0, "action_oriented": 0.5},
    ),
)

TAG_BY_KEY = {tag.key: tag for tag in TAG_DEFINITIONS}


def normalize_role(raw: str) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    return ROLE_ALIASES.get(text) or ROLE_ALIASES.get(text.lower()) or (
        text if text in SKILL_LABELS else None
    )


def infer_domains(*parts: str | None) -> dict[str, float]:
    haystack = " ".join(part for part in parts if part).lower()
    weights: dict[str, float] = {}
    for keyword, domain in TEXT_DOMAIN_KEYWORDS:
        if keyword.lower() in haystack:
            weights[domain] = max(weights.get(domain, 0.0), 0.55)
    return weights


def infer_scene(text: str, competition: str | None = None) -> str | None:
    blob = f"{text} {competition or ''}".lower()
    rules = (
        (("比赛", "大赛", "黑客松", "竞赛", "数模"), "比赛组队"),
        (("项目", "课题"), "项目组队"),
        (("羽毛球", "篮球", "足球", "网球", "跑步", "健身"), "运动搭子"),
        (("ddl", "作业", "冲刺"), "DDL冲刺"),
        (("自习", "复习"), "自习搭子"),
        (("活动", "讲座", "宣讲会"), "活动同行"),
    )
    for keywords, scene in rules:
        if any(keyword in blob for keyword in keywords):
            return scene
    return None


def skill_domain(skill: str) -> str | None:
    return SKILL_TO_DOMAIN.get(skill)


def label_of(kind: str, key: str) -> str:
    tables = {
        "domain": DOMAIN_LABELS,
        "skill": SKILL_LABELS,
        "signal": SIGNAL_LABELS,
        "scene": SCENE_LABELS,
        "tag": {tag.key: tag.label for tag in TAG_DEFINITIONS},
    }
    return tables.get(kind, {}).get(key, key)
