"""Deterministic taxonomy used by the taste analyzer (no external LLM).

Everything in this module is a pure data table plus lightweight helpers, so
the analyzer is reproducible and unit-testable offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainDef:
    key: str
    label: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class SignalDef:
    key: str
    label: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class TagDef:
    key: str
    label: str
    domains: dict[str, float] = field(default_factory=dict)
    signals: dict[str, float] = field(default_factory=dict)
    breadth: float = 0.0


@dataclass(frozen=True)
class OptionDef:
    id: str
    label: str
    tag_delta: dict[str, float] = field(default_factory=dict)
    dimension_delta: dict[str, float] = field(default_factory=dict)
    domain_delta: dict[str, float] = field(default_factory=dict)
    facet_key: str | None = None
    facet_label: str | None = None


@dataclass(frozen=True)
class QuestionDef:
    id: str
    dimension: str
    prompt: str
    options: tuple[OptionDef, ...] = field(default_factory=tuple)
    target_domain: str | None = None
    purpose: str = "refine_interest"


INTEREST_DOMAINS: tuple[DomainDef, ...] = (
    DomainDef(
        "ai_programming",
        "AI / 编程 / 开源",
        (
            "ai",
            "人工智能",
            "大模型",
            "chatgpt",
            "gpt",
            "claude",
            "gemini",
            "deepseek",
            "codex",
            "openclaw",
            "agent",
            "智能体",
            "aigc",
            "github",
            "开源",
            "编程",
            "代码",
            "程序员",
            "python",
            "vibecoding",
            "llm",
            "rag",
            "docker",
            "软件开发",
            "开发者",
            "prompt",
            "提示词",
            "模型",
            "开源项目",
        ),
    ),
    DomainDef(
        "tech_devices",
        "科技 / 数码 / 设备",
        (
            "科技",
            "数码",
            "手机",
            "iphone",
            "苹果",
            "macbook",
            "mac mini",
            "电脑",
            "相机",
            "镜头",
            "尼康",
            "索尼",
            "佳能",
            "富士",
            "大疆",
            "耳机",
            "音箱",
            "平板",
            "硬件",
            "软件",
            "app",
            "安卓",
            "ios",
            "测评",
            "华强北",
            "卡贴机",
            "有锁机",
        ),
    ),
    DomainDef(
        "gaming_strategy",
        "游戏 / 策略 / 电竞",
        (
            "游戏",
            "王者荣耀",
            "王者",
            "三国杀",
            "和平精英",
            "象棋",
            "steam",
            "switch",
            "电竞",
            "达摩",
            "艾琳",
            "马超",
            "关羽",
            "吃鸡",
            "我的世界",
            "原神",
            "英雄联盟",
            "游戏机",
            "策略",
        ),
    ),
    DomainDef(
        "visual_creation",
        "摄影 / 影像创作",
        (
            "摄影",
            "拍照",
            "镜头",
            "航拍",
            "电影感",
            "调色",
            "转场",
            "剪辑",
            "vlog",
            "拍摄",
            "写真",
            "构图",
            "焦段",
            "影像",
            "后期",
            "画面",
            "短片",
        ),
    ),
    DomainDef(
        "music_literature",
        "音乐 / 文学 / 审美",
        (
            "音乐",
            "钢琴",
            "吉他",
            "歌曲",
            "唱歌",
            "翻唱",
            "清唱",
            "周杰伦",
            "配音",
            "文学",
            "诗词",
            "古诗",
            "现代诗",
            "书摘",
            "读书",
            "文案",
            "哲学",
            "艺术",
            "美学",
            "氛围感",
            "治愈系风景",
            "人文艺术",
            "传统文化",
        ),
    ),
    DomainDef(
        "travel_city",
        "旅行 / 城市 / 生活",
        (
            "旅行",
            "旅游",
            "出游",
            "机票",
            "酒店",
            "攻略",
            "城市",
            "深圳",
            "广州",
            "天津",
            "北京",
            "上海",
            "香港",
            "澳门",
            "加拿大",
            "马尔代夫",
            "日本",
            "移民",
            "留学",
            "签证",
            "航空",
            "航班",
            "景点",
            "海景",
            "山地",
        ),
    ),
    DomainDef(
        "career_growth",
        "成长 / 职业 / 商业",
        (
            "成长",
            "职场",
            "求职",
            "应届生",
            "面试",
            "实习",
            "大学生",
            "校园",
            "大学",
            "竞赛",
            "比赛",
            "黑客松",
            "获奖",
            "项目",
            "创业",
            "商业",
            "营销",
            "赚钱",
            "副业",
            "认知",
            "效率",
            "办公",
            "ppt",
            "excel",
            "简历",
            "演讲",
            "产品",
            "运营",
            "工作",
        ),
    ),
    DomainDef(
        "health_sports",
        "健康 / 运动 / 康复",
        (
            "健康",
            "运动",
            "跑步",
            "健身",
            "康复",
            "膝关节",
            "韧带",
            "髌骨",
            "滑膜炎",
            "损伤",
            "医生",
            "医院",
            "治疗",
            "体态",
            "睡眠",
            "饮食",
            "疼痛",
            "医疗",
            "减脂",
            "增肌",
        ),
    ),
    DomainDef(
        "relationship_family",
        "关系 / 家庭 / 情感",
        (
            "情感",
            "恋爱",
            "爱情",
            "情侣",
            "男友",
            "女友",
            "婚姻",
            "家庭",
            "爸妈",
            "爸爸",
            "妈妈",
            "父母",
            "朋友",
            "人际",
            "幸福",
            "陪伴",
            "治愈",
            "亲子",
            "宝宝",
            "孩子",
        ),
    ),
    DomainDef(
        "humor_pets",
        "幽默 / 萌宠 / 轻松",
        (
            "搞笑",
            "哈哈",
            "抽象",
            "段子",
            "猫meme",
            "meme",
            "梗",
            "离谱",
            "万万没想到",
            "萌宠",
            "宠物",
            "猫",
            "狗",
            "土狗",
            "熊出没",
            "反差",
        ),
    ),
    DomainDef(
        "finance_consumption",
        "财经 / 消费决策",
        (
            "财经",
            "金融",
            "股票",
            "港股",
            "银行",
            "基金",
            "投资",
            "理财",
            "存款",
            "经济",
            "财富",
            "省钱",
            "价格",
            "便宜",
            "避坑",
            "信息差",
            "性价比",
            "买房",
            "租房",
            "消费",
            "账号交易",
        ),
    ),
    DomainDef(
        "knowledge_method",
        "知识 / 科普 / 方法论",
        (
            "知识",
            "科普",
            "教程",
            "技巧",
            "干货",
            "方法",
            "教学",
            "学习",
            "为什么",
            "原理",
            "指南",
            "入门",
            "手把手",
            "一键",
            "如何",
            "怎么",
            "冷知识",
            "揭秘",
            "分析",
        ),
    ),
)

BEHAVIOR_SIGNALS: tuple[SignalDef, ...] = (
    SignalDef(
        "action_oriented",
        "行动导向",
        (
            "教程",
            "攻略",
            "技巧",
            "干货",
            "方法",
            "指南",
            "入门",
            "手把手",
            "一键",
            "如何",
            "怎么",
            "解决",
            "工具",
            "上手",
            "实操",
        ),
    ),
    SignalDef(
        "cost_efficient",
        "低成本优化",
        (
            "免费",
            "省钱",
            "低成本",
            "便宜",
            "性价比",
            "避坑",
            "信息差",
            "效率",
            "自动",
            "批量",
            "一键",
        ),
    ),
    SignalDef(
        "aesthetic",
        "审美氛围",
        (
            "氛围",
            "治愈",
            "摄影",
            "音乐",
            "诗",
            "文学",
            "美学",
            "电影感",
            "画面",
            "浪漫",
            "风景",
            "色调",
        ),
    ),
    SignalDef(
        "competitive",
        "竞争成就",
        (
            "比赛",
            "竞赛",
            "黑客松",
            "获奖",
            "冠军",
            "排名",
            "成长",
            "挑战",
            "创业",
            "赚钱",
            "优秀",
            "高手",
            "拿下",
        ),
    ),
    SignalDef(
        "light_entertainment",
        "轻松娱乐",
        (
            "哈哈",
            "搞笑",
            "抽象",
            "离谱",
            "段子",
            "meme",
            "梗",
            "万万没想到",
            "摸鱼",
        ),
    ),
)

TAG_GROUPS: dict[str, str] = {
    "explorer_builder": "maker",
    "ai_practitioner": "maker",
    "growth_driver": "maker",
    "practical_romantic": "aesthetic",
    "aesthetic_observer": "aesthetic",
    "strategic_player": "player",
    "knowledge_curator": "curator",
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

# Dimensions referenced by quiz selection.
DIMENSIONS: tuple[str, ...] = (
    "openness",
    "action_orientation",
    "aesthetic_orientation",
    "competition_orientation",
)

QUESTION_BANK: tuple[QuestionDef, ...] = (
    QuestionDef(
        "q_action_intent",
        "action_orientation",
        "你收藏工具/教程类内容通常是为了？",
        (
            OptionDef(
                "apply_now",
                "看完就动手实践",
                tag_delta={"explorer_builder": 0.30, "ai_practitioner": 0.30},
                dimension_delta={"action_orientation": 0.25},
            ),
            OptionDef(
                "project_later",
                "先存起来，等项目用到",
                tag_delta={"knowledge_curator": 0.30},
                dimension_delta={"action_orientation": 0.05},
            ),
            OptionDef(
                "curiosity",
                "单纯了解新东西",
                tag_delta={"aesthetic_observer": 0.15, "knowledge_curator": 0.15},
                dimension_delta={"openness": 0.20, "action_orientation": -0.10},
            ),
        ),
    ),
    QuestionDef(
        "q_ai_motivation",
        "openness",
        "你关注 AI / 新技术内容，主要是为了？",
        (
            OptionDef(
                "build_product",
                "用它们做出自己的东西",
                tag_delta={"explorer_builder": 0.30, "ai_practitioner": 0.35},
                dimension_delta={"action_orientation": 0.15, "openness": 0.10},
            ),
            OptionDef(
                "improve_workflow",
                "优化学习/工作流程",
                tag_delta={"growth_driver": 0.30, "knowledge_curator": 0.20},
                dimension_delta={"action_orientation": 0.15},
            ),
            OptionDef(
                "stay_informed",
                "保持信息不落伍",
                tag_delta={"knowledge_curator": 0.30},
                dimension_delta={"openness": 0.25},
            ),
        ),
    ),
    QuestionDef(
        "q_aesthetic_role",
        "aesthetic_orientation",
        "你保存的摄影/音乐/风景类内容是？",
        (
            OptionDef(
                "creative_input",
                "给创作当素材灵感",
                tag_delta={"aesthetic_observer": 0.30, "explorer_builder": 0.15},
                dimension_delta={"aesthetic_orientation": 0.20, "action_orientation": 0.10},
            ),
            OptionDef(
                "mood_escape",
                "给自己放松和治愈",
                tag_delta={"practical_romantic": 0.30, "aesthetic_observer": 0.15},
                dimension_delta={"aesthetic_orientation": 0.15},
            ),
            OptionDef(
                "appreciate_only",
                "欣赏为主，很少动手",
                tag_delta={"aesthetic_observer": 0.25},
                dimension_delta={"aesthetic_orientation": 0.25, "action_orientation": -0.10},
            ),
        ),
    ),
    QuestionDef(
        "q_competition_attitude",
        "competition_orientation",
        "面对比赛/挑战类的机会，你通常？",
        (
            OptionDef(
                "sign_up_now",
                "先报名再想细节",
                tag_delta={"strategic_player": 0.30, "growth_driver": 0.30},
                dimension_delta={"competition_orientation": 0.25, "action_orientation": 0.10},
            ),
            OptionDef(
                "evaluate_first",
                "评估胜算和投入再决定",
                tag_delta={"strategic_player": 0.20, "knowledge_curator": 0.15},
                dimension_delta={"competition_orientation": 0.15},
            ),
            OptionDef(
                "mostly_watch",
                "围观学习，不参与",
                tag_delta={"aesthetic_observer": 0.10},
                dimension_delta={"competition_orientation": -0.10},
            ),
        ),
    ),
    QuestionDef(
        "q_learning_style",
        "openness",
        "进入一个陌生领域时，你的第一反应是？",
        (
            OptionDef(
                "dive_deep",
                "先搭个最小作品跑起来",
                tag_delta={"explorer_builder": 0.30, "ai_practitioner": 0.25},
                dimension_delta={"action_orientation": 0.20, "openness": 0.10},
            ),
            OptionDef(
                "build_with_it",
                "把它接到手头任务上用",
                tag_delta={"practical_romantic": 0.20, "growth_driver": 0.20},
                dimension_delta={"action_orientation": 0.15},
            ),
            OptionDef(
                "collect_first",
                "先收集资料理清脉络",
                tag_delta={"knowledge_curator": 0.30},
                dimension_delta={"openness": 0.20},
            ),
        ),
    ),
    QuestionDef(
        "q_social_motivation",
        "openness",
        "你向朋友分享好内容时，主要图什么？",
        (
            OptionDef(
                "inspire_others",
                "想带动大家一起行动",
                tag_delta={"growth_driver": 0.30, "explorer_builder": 0.15},
                dimension_delta={"action_orientation": 0.10, "openness": 0.10},
            ),
            OptionDef(
                "record_myself",
                "记录自己的口味偏好",
                tag_delta={"aesthetic_observer": 0.15},
                dimension_delta={"aesthetic_orientation": 0.10},
            ),
            OptionDef(
                "rarely_share",
                "基本不主动分享",
                tag_delta={},
            ),
        ),
    ),
)


def _refinement_question(
    domain: str,
    prompt: str,
    options: tuple[tuple[str, str, dict[str, float]], ...],
) -> QuestionDef:
    return QuestionDef(
        id=f"q_refine_{domain}",
        dimension="interest_refinement",
        prompt=prompt,
        options=tuple(
            OptionDef(
                id=option_id,
                label=label,
                tag_delta=tag_delta,
                domain_delta={domain: 0.18},
                facet_key=option_id,
                facet_label=label,
            )
            for option_id, label, tag_delta in options
        ),
        target_domain=domain,
    )


REFINEMENT_QUESTION_BANK: tuple[QuestionDef, ...] = (
    _refinement_question(
        "ai_programming",
        "从画像看，你明显关注 AI / 编程。你最想深入的是？",
        (
            (
                "ai_agents",
                "AI 应用、智能体与自动化",
                {"ai_practitioner": 1.0, "explorer_builder": 0.6},
            ),
            (
                "open_source_engineering",
                "编程工程、开源项目与技术实现",
                {"explorer_builder": 1.0, "ai_practitioner": 0.5},
            ),
            (
                "ai_productivity",
                "用 AI 优化学习与工作流程",
                {"growth_driver": 0.8, "ai_practitioner": 0.7},
            ),
            (
                "ai_frontier",
                "模型前沿、行业动态与趋势",
                {"knowledge_curator": 1.0, "ai_practitioner": 0.4},
            ),
        ),
    ),
    _refinement_question(
        "tech_devices",
        "在科技 / 数码内容里，你最关心哪一类？",
        (
            ("hardware", "电脑、手机与硬件体验", {"explorer_builder": 0.7}),
            ("cameras", "相机、镜头与影像设备", {"aesthetic_observer": 0.8}),
            ("apps_tools", "软件、App 与效率工具", {"growth_driver": 0.7}),
            ("buying_decisions", "评测、选购与性价比", {"practical_romantic": 0.7}),
        ),
    ),
    _refinement_question(
        "gaming_strategy",
        "在游戏内容里，你最享受的是？",
        (
            ("competitive_play", "竞技操作与提升水平", {"strategic_player": 1.0}),
            ("strategy_analysis", "阵容、机制与策略研究", {"strategic_player": 0.9}),
            ("console_indie", "主机、独立游戏与世界体验", {"explorer_builder": 0.5}),
            ("casual_fun", "轻松娱乐、梗与社交氛围", {"practical_romantic": 0.4}),
        ),
    ),
    _refinement_question(
        "visual_creation",
        "你对摄影 / 影像创作最想深入哪个方向？",
        (
            ("photography", "摄影、构图与镜头语言", {"aesthetic_observer": 1.0}),
            ("video_editing", "视频拍摄、剪辑与调色", {"aesthetic_observer": 0.8}),
            ("visual_design", "视觉设计与审美体系", {"aesthetic_observer": 0.9}),
            ("storytelling", "用影像表达故事和观点", {"explorer_builder": 0.5}),
        ),
    ),
    _refinement_question(
        "music_literature",
        "音乐 / 文学 / 审美内容中，哪一部分最吸引你？",
        (
            ("music", "音乐、演奏与声音表达", {"aesthetic_observer": 0.8}),
            ("literature", "文学、诗词与文字表达", {"knowledge_curator": 0.6}),
            ("philosophy", "哲学、人文与思想讨论", {"knowledge_curator": 0.9}),
            ("aesthetic_life", "审美氛围与生活感受", {"practical_romantic": 0.8}),
        ),
    ),
    _refinement_question(
        "travel_city",
        "旅行 / 城市内容里，你主要想获得什么？",
        (
            ("route_planning", "路线、目的地与实用攻略", {"knowledge_curator": 0.5}),
            ("city_life", "城市生活与本地体验", {"practical_romantic": 0.7}),
            ("budget_travel", "低成本旅行与性价比", {"practical_romantic": 0.9}),
            ("scenery", "风景、人文与视觉感受", {"aesthetic_observer": 0.8}),
        ),
    ),
    _refinement_question(
        "career_growth",
        "成长 / 职业内容中，你现阶段最关心的是？",
        (
            ("projects_competitions", "项目、竞赛与作品成果", {"growth_driver": 0.9}),
            ("career_skills", "求职、职场与专业能力", {"growth_driver": 1.0}),
            ("entrepreneurship", "产品、创业与商业机会", {"explorer_builder": 0.7}),
            ("personal_productivity", "效率、方法与自我管理", {"knowledge_curator": 0.6}),
        ),
    ),
    _refinement_question(
        "health_sports",
        "健康 / 运动内容里，你更关注哪方面？",
        (
            ("fitness", "健身、跑步与体能提升", {"growth_driver": 0.7}),
            ("rehabilitation", "伤病康复与身体恢复", {"knowledge_curator": 0.5}),
            ("healthy_routines", "睡眠、饮食与日常习惯", {"practical_romantic": 0.5}),
            ("health_science", "医学科普与原理知识", {"knowledge_curator": 0.8}),
        ),
    ),
    _refinement_question(
        "relationship_family",
        "关系 / 家庭内容中，你最关注什么？",
        (
            ("intimacy", "亲密关系与相处方式", {"practical_romantic": 0.8}),
            ("family", "家庭、父母与陪伴", {"practical_romantic": 0.7}),
            ("social_skills", "朋友、人际与沟通", {"growth_driver": 0.5}),
            ("emotional_healing", "情绪理解与自我治愈", {"aesthetic_observer": 0.4}),
        ),
    ),
    _refinement_question(
        "humor_pets",
        "轻松内容里，哪种最对你的胃口？",
        (
            ("comedy", "搞笑日常与反差内容", {"practical_romantic": 0.4}),
            ("memes", "抽象、梗与 meme", {"strategic_player": 0.3}),
            ("pets", "猫狗、萌宠与陪伴", {"practical_romantic": 0.6}),
            ("relaxation", "单纯放松和调节情绪", {"aesthetic_observer": 0.3}),
        ),
    ),
    _refinement_question(
        "finance_consumption",
        "财经 / 消费决策内容里，你想重点了解什么？",
        (
            ("investing", "投资、基金与资产配置", {"strategic_player": 0.6}),
            ("smart_spending", "选购、避坑与理性消费", {"practical_romantic": 0.9}),
            ("saving", "储蓄、省钱与现金流", {"growth_driver": 0.4}),
            ("economy", "经济趋势与商业逻辑", {"knowledge_curator": 0.8}),
        ),
    ),
    _refinement_question(
        "knowledge_method",
        "知识 / 方法论内容里，你最需要哪一种？",
        (
            ("practical_guides", "教程、攻略与可执行步骤", {"explorer_builder": 0.7}),
            ("principles", "原理、分析与深度解释", {"knowledge_curator": 1.0}),
            ("structured_learning", "系统学习与知识框架", {"knowledge_curator": 0.9}),
            ("information_curation", "信息收集、筛选与整理", {"knowledge_curator": 0.8}),
        ),
    ),
)

REFINEMENT_OUTCOME_QUESTION = QuestionDef(
    id="q_refine_outcome",
    dimension="interest_refinement",
    prompt="你最希望这些兴趣最后帮你获得什么？",
    options=(
        OptionDef(
            "make_something",
            "做出产品、作品或项目",
            tag_delta={"explorer_builder": 1.0, "ai_practitioner": 0.5},
            facet_key="make_something",
            facet_label="产品与作品输出",
        ),
        OptionDef(
            "solve_problems",
            "解决学习、工作或生活中的具体问题",
            tag_delta={"growth_driver": 0.8, "ai_practitioner": 0.4},
            facet_key="solve_problems",
            facet_label="实际问题解决",
        ),
        OptionDef(
            "understand_deeply",
            "建立更深、更系统的理解",
            tag_delta={"knowledge_curator": 1.0},
            facet_key="understand_deeply",
            facet_label="系统理解",
        ),
        OptionDef(
            "enrich_life",
            "拓展体验、审美和生活趣味",
            tag_delta={"aesthetic_observer": 0.7, "practical_romantic": 0.7},
            facet_key="enrich_life",
            facet_label="生活与审美体验",
        ),
    ),
)


def domain_by_key(key: str) -> DomainDef | None:
    for domain in INTEREST_DOMAINS:
        if domain.key == key:
            return domain
    return None


def question_by_id(question_id: str) -> QuestionDef | None:
    for question in (*REFINEMENT_QUESTION_BANK, REFINEMENT_OUTCOME_QUESTION, *QUESTION_BANK):
        if question.id == question_id:
            return question
    return None


def tag_by_key(key: str) -> TagDef | None:
    for tag in TAG_DEFINITIONS:
        if tag.key == key:
            return tag
    return None
