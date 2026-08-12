"""中大测试剧组：六名已沉淀的演示用户。

ID 仍用 u_demo_1–6，避免打爆现有联调与测试；人设、学院、校区、信任与画像按真实中大学生写。
手机号可走正式登录，密码见 CAST_PASSWORD。哈希预计算，避免每个测试重做 PBKDF2。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CAST_PASSWORD = "cast-onemore"
CAST_PASSWORD_HASH = (
    "pbkdf2_sha256$310000$HmDtP8i4cS4B9eJyTq38-A==$STdz9KzfdPfmTkaFXJoi3fFO1Y-a3avthg07s7gyYGs="
)

LIN, ZHOU, CHEN, LIANG, SU, HE = (
    "u_demo_1",
    "u_demo_2",
    "u_demo_3",
    "u_demo_4",
    "u_demo_5",
    "u_demo_6",
)


@dataclass(frozen=True)
class CastUser:
    id: str
    display_name: str
    gender_code: str
    college: str
    major: str
    campus: str
    grade_year: int
    phone: str
    trust_level: str
    completed_gatherings: int
    initiated_gatherings: int
    recurrences: int
    on_time_confirm_rate: float
    interaction_style: str
    sport_level: str
    study_intensity: str
    minimum_group_size: int = 3
    identity_disclosure: str = "after_confirmed"
    course_codes: tuple[str, ...] = ()
    assignment: tuple[str, str] | None = None
    netid_index: int = 0


CAST_USERS: tuple[CastUser, ...] = (
    CastUser(
        id=LIN,
        display_name="林予安",
        gender_code="F",
        college="软件工程学院",
        major="软件工程",
        campus="珠海校区",
        grade_year=2024,
        phone="13900001001",
        trust_level="T3",
        completed_gatherings=12,
        initiated_gatherings=5,
        recurrences=3,
        on_time_confirm_rate=1.0,
        interaction_style="talkative",
        sport_level="intermediate",
        study_intensity="focused",
        course_codes=("SE1001", "CS2002", "SE2104"),
        assignment=("SE1001", "软件工程迭代作业"),
        netid_index=0,
    ),
    CastUser(
        id=ZHOU,
        display_name="周衡",
        gender_code="M",
        college="计算机学院",
        major="计算机科学与技术",
        campus="东校园",
        grade_year=2023,
        phone="13900001002",
        trust_level="T2",
        completed_gatherings=4,
        initiated_gatherings=0,
        recurrences=0,
        on_time_confirm_rate=1.0,
        interaction_style="quiet",
        sport_level="beginner",
        study_intensity="focused",
        course_codes=("CS2002", "FE1001", "GE4101"),
        assignment=("CS2002", "机器学习课程项目"),
        netid_index=1,
    ),
    CastUser(
        id=CHEN,
        display_name="陈可薇",
        gender_code="F",
        college="传播与设计学院",
        major="视觉传达设计",
        campus="东校园",
        grade_year=2025,
        phone="13900001003",
        trust_level="T2",
        completed_gatherings=6,
        initiated_gatherings=2,
        recurrences=1,
        on_time_confirm_rate=0.92,
        interaction_style="talkative",
        sport_level="beginner",
        study_intensity="light",
        course_codes=("DS3001", "GE4101", "PE1203"),
        assignment=("DS3001", "视觉传达期末海报"),
        netid_index=2,
    ),
    CastUser(
        id=LIANG,
        display_name="梁景行",
        gender_code="M",
        college="岭南学院",
        major="经济学",
        campus="南校园",
        grade_year=2024,
        phone="13900001004",
        trust_level="T3",
        completed_gatherings=10,
        initiated_gatherings=4,
        recurrences=2,
        on_time_confirm_rate=0.86,
        interaction_style="talkative",
        sport_level="casual",
        study_intensity="balanced",
        course_codes=("BA2001", "GE2208"),
        assignment=("BA2001", "商业模式案例报告"),
        netid_index=3,
    ),
    CastUser(
        id=SU,
        display_name="苏晚宁",
        gender_code="F",
        college="外国语学院",
        major="英语",
        campus="南校园",
        grade_year=2026,
        phone="13900001005",
        trust_level="T1",
        completed_gatherings=2,
        initiated_gatherings=0,
        recurrences=0,
        on_time_confirm_rate=1.0,
        interaction_style="quiet",
        sport_level="beginner",
        study_intensity="light",
        minimum_group_size=4,
        identity_disclosure="after_full",
        course_codes=("EN1002", "GE2208"),
        assignment=("EN1002", "学术英语写作第一篇"),
        netid_index=4,
    ),
    CastUser(
        id=HE,
        display_name="何屿",
        gender_code="M",
        college="生命科学学院",
        major="生物科学",
        campus="东校园",
        grade_year=2025,
        phone="13900001006",
        trust_level="T2",
        completed_gatherings=8,
        initiated_gatherings=1,
        recurrences=2,
        on_time_confirm_rate=0.95,
        interaction_style="balanced",
        sport_level="advanced",
        study_intensity="balanced",
        course_codes=("BIO2101", "PE1203"),
        assignment=("BIO2101", "细胞生物学实验报告"),
        netid_index=5,
    ),
)

CAST_BY_ID = {item.id: item for item in CAST_USERS}

EXTRA_COURSES: tuple[tuple[str, str, str, list[str], str], ...] = (
    ("SE2104", "移动应用开发", "computer_science", ["frontend", "backend"], "limited_elective"),
    ("GE4101", "人工智能伦理", "computer_science", ["product"], "cross_major"),
    ("GE2208", "城市与社会", "business", ["business_analysis"], "elective"),
    ("PE1203", "体育选修乒乓球", "design", ["operations"], "elective"),
    ("BIO2101", "细胞生物学", "computer_science", ["data_analysis"], "required"),
    ("EN1002", "学术英语写作", "business", ["operations"], "required"),
)

COURSE_MEETINGS: dict[str, tuple[str, int]] = {
    "SE1001": ("珠海校区教学楼 A301", 9),
    "CS2002": ("东校园实验楼 B203", 10),
    "SE2104": ("珠海校区教学楼 C105", 14),
    "FE1001": ("东校园教学楼 D201", 15),
    "GE4101": ("东校园文科楼 204", 16),
    "DS3001": ("东校园传设楼 305", 13),
    "PE1203": ("东校园体育馆乒乓球室", 18),
    "BA2001": ("南校园岭南堂 201", 10),
    "GE2208": ("南校园文科楼 108", 14),
    "EN1002": ("南校园外国语学院 302", 8),
    "BIO2101": ("东校园生科楼 401", 9),
}


def _taste(
    *,
    primary: dict[str, Any],
    secondary: list[dict[str, Any]],
    domains: list[dict[str, Any]],
    facets: list[dict[str, Any]],
    dimensions: dict[str, float],
    summary: str,
    persona: str,
    hints: list[str],
    items: int,
    confidence: float,
) -> dict[str, Any]:
    return {
        "status": "READY",
        "primary_tag": primary,
        "secondary_tags": secondary,
        "interest_domains": domains,
        "interest_facets": facets,
        "dimensions": dimensions,
        "summary": summary,
        "persona": persona,
        "matching_hints": hints,
        "confidence": confidence,
        "calibrated": True,
        "sample": {
            "items": items,
            "unique_authors": 18,
            "api_pages": 3,
            "generation": "seed",
            "persona": persona,
            "matching_hints": hints,
            "interest_facets": facets,
            "calibrated": True,
        },
        "model_version": "taste-v2",
        "visibility": "members",
    }


CAST_TASTE: dict[str, dict[str, Any]] = {
    LIN: _taste(
        primary={"key": "explorer_builder", "label": "探索型 Builder", "score": 0.31},
        secondary=[
            {"key": "ai_practitioner", "label": "AI 实践派", "score": 0.24},
            {"key": "knowledge_curator", "label": "知识策展人", "score": 0.18},
        ],
        domains=[
            {"key": "ai_programming", "label": "AI / 编程 / 开源", "score": 0.34},
            {"key": "career_growth", "label": "成长/职业", "score": 0.22},
            {"key": "health_sports", "label": "运动健康", "score": 0.18},
        ],
        facets=[
            {"domain": "ai_programming", "facet": "hackathon_ai", "label": "黑客松/AI创变"},
            {"domain": "health_sports", "facet": "badminton", "label": "羽毛球"},
        ],
        dimensions={"ai_programming": 0.34, "career_growth": 0.22, "health_sports": 0.18},
        summary="珠海过来把事做成的人：黑客松当项目打，周末英东打球也把场次定死。",
        persona="她是一位自带节奏的执行者。不爱闲聊，习惯把「要不要一起」收成时间、地点和人数；珠海到广州的岐关是她的社交半径，不是旅游。",
        hints=["组队黑客松", "羽毛球周期局", "跨校区比赛筹备"],
        items=240,
        confidence=0.88,
    ),
    ZHOU: _taste(
        primary={"key": "ai_practitioner", "label": "AI 实践派", "score": 0.33},
        secondary=[
            {"key": "knowledge_curator", "label": "知识策展人", "score": 0.22},
            {"key": "explorer_builder", "label": "探索型 Builder", "score": 0.16},
        ],
        domains=[
            {"key": "ai_programming", "label": "AI / 编程 / 开源", "score": 0.38},
            {"key": "knowledge_method", "label": "知识方法", "score": 0.24},
            {"key": "career_growth", "label": "成长/职业", "score": 0.21},
        ],
        facets=[
            {"domain": "ai_programming", "facet": "open_source", "label": "开源"},
            {"domain": "career_growth", "facet": "campus_recruit", "label": "秋招/宣讲会"},
        ],
        dimensions={"ai_programming": 0.38, "knowledge_method": 0.24, "career_growth": 0.21},
        summary="大四秋招里的安静开发者：确认了就到，几乎不发起，互补组队缺他不行。",
        persona="他话少、靠谱、略社恐。更愿意做事而不是认识人；宣讲会讨厌单独去，这是他愿意进公开局的少数理由。",
        hints=["数模/智能应用开发", "宣讲会同行", "安静自习"],
        items=190,
        confidence=0.84,
    ),
    CHEN: _taste(
        primary={"key": "aesthetic_observer", "label": "审美观察者", "score": 0.34},
        secondary=[
            {"key": "practical_romantic", "label": "务实浪漫", "score": 0.21},
            {"key": "explorer_builder", "label": "探索型 Builder", "score": 0.15},
        ],
        domains=[
            {"key": "visual_creation", "label": "视觉创作", "score": 0.36},
            {"key": "music_literature", "label": "音乐文学", "score": 0.22},
            {"key": "travel_city", "label": "城市漫游", "score": 0.16},
        ],
        facets=[
            {"domain": "visual_creation", "facet": "poster_design", "label": "海报/视觉"},
            {"domain": "visual_creation", "facet": "exhibition", "label": "展览"},
        ],
        dimensions={"visual_creation": 0.36, "music_literature": 0.22, "travel_city": 0.16},
        summary="让局不像开会的人：设计位、会写心情备注、会先开口。",
        persona="她不是队长，是空气感。共同经历有她在才会留下温度，而不是四个人各干各的。",
        hints=["海报赶工", "逸夫看展", "比赛视觉"],
        items=210,
        confidence=0.83,
    ),
    LIANG: _taste(
        primary={"key": "growth_driver", "label": "成长驱动者", "score": 0.32},
        secondary=[
            {"key": "knowledge_curator", "label": "知识策展人", "score": 0.2},
            {"key": "strategic_player", "label": "策略玩家", "score": 0.17},
        ],
        domains=[
            {"key": "career_growth", "label": "成长/职业", "score": 0.33},
            {"key": "knowledge_method", "label": "知识方法", "score": 0.2},
            {"key": "health_sports", "label": "运动健康", "score": 0.14},
        ],
        facets=[
            {"domain": "career_growth", "facet": "case_comp", "label": "商赛/案例"},
            {"domain": "career_growth", "facet": "campus_recruit", "label": "宣讲会"},
        ],
        dimensions={"career_growth": 0.33, "knowledge_method": 0.2, "health_sports": 0.14},
        summary="南校园把人凑齐的润滑剂：会带新人，会把角色缺口写清楚。",
        persona="商科组织者。林予安凑事，他凑人。话偏多，偶尔把局开太大，但第一局有他在，大一才敢进。",
        hints=["商赛组队", "宣讲会", "带新人进局"],
        items=200,
        confidence=0.82,
    ),
    SU: _taste(
        primary={"key": "practical_romantic", "label": "务实浪漫", "score": 0.3},
        secondary=[
            {"key": "aesthetic_observer", "label": "审美观察者", "score": 0.22},
            {"key": "knowledge_curator", "label": "知识策展人", "score": 0.16},
        ],
        domains=[
            {"key": "music_literature", "label": "音乐文学", "score": 0.28},
            {"key": "travel_city", "label": "城市漫游", "score": 0.22},
            {"key": "knowledge_method", "label": "知识方法", "score": 0.18},
        ],
        facets=[
            {"domain": "music_literature", "facet": "language", "label": "语言学习"},
            {"domain": "travel_city", "facet": "campus_walk", "label": "认路/讲座"},
        ],
        dimensions={"music_literature": 0.28, "travel_city": 0.22, "knowledge_method": 0.18},
        summary="刚入学的冷启动本人：不敢开局，只敢进人多的低风险公开局。",
        persona="不是社恐，是状态。新校园、还在认路。同课破冰和被带进第一局，是她开口的两条路。",
        hints=["讲座同行", "同课自习", "认路但不单独约"],
        items=120,
        confidence=0.74,
    ),
    HE: _taste(
        primary={"key": "strategic_player", "label": "策略玩家", "score": 0.29},
        secondary=[
            {"key": "growth_driver", "label": "成长驱动者", "score": 0.2},
            {"key": "practical_romantic", "label": "务实浪漫", "score": 0.16},
        ],
        domains=[
            {"key": "health_sports", "label": "运动健康", "score": 0.36},
            {"key": "knowledge_method", "label": "知识方法", "score": 0.18},
            {"key": "travel_city", "label": "城市漫游", "score": 0.14},
        ],
        facets=[
            {"domain": "health_sports", "facet": "badminton", "label": "羽毛球"},
            {"domain": "knowledge_method", "facet": "lab_life", "label": "实验室日常"},
        ],
        dimensions={"health_sports": 0.36, "knowledge_method": 0.18, "travel_city": 0.14},
        summary="实验周会消失，球场上从不消失。周期球局能成立，关键靠他定场。",
        persona="生科作息和文社科错开，羽毛球是他唯一不用动脑的事。从东校园骑去南校园英东，是常规通勤。",
        hints=["英东周期球局", "实验报告冲刺", "体育课破冰"],
        items=160,
        confidence=0.81,
    ),
}


@dataclass(frozen=True)
class CastMember:
    user_id: str
    role: str | None = None
    joined_via: str = "matching"
    confirmation: str = "confirmed"


@dataclass(frozen=True)
class CastGathering:
    title: str
    gathering_type: str
    goal: str
    campus: str
    location: str
    status: str
    owner_user_id: str
    members: tuple[CastMember, ...]
    mode: str = "similar"
    min_size: int = 3
    target_size: int = 4
    required_trust_level: str = "T1"
    identity_disclosure: str = "after_confirmed"
    required_roles: tuple[str, ...] = ()
    mood_note: str | None = None
    start_days_ago: int | None = None
    start_weekday: int | None = None
    start_hour: int = 19
    duration_hours: int = 2
    messages: tuple[tuple[str, str], ...] = ()
    official_metadata: dict[str, Any] = field(default_factory=dict)


COMPLETED_GATHERINGS: tuple[CastGathering, ...] = (
    CastGathering(
        title="英东周三羽毛球",
        gathering_type="羽毛球",
        goal="打两小时，认真出汗，不鸽",
        campus="南校园",
        location="南校园英东体育中心",
        status="Completed",
        owner_user_id=LIN,
        members=(
            CastMember(LIN, joined_via="owner"),
            CastMember(HE, joined_via="owner"),
            CastMember(LIANG),
            CastMember(CHEN, role="玩票"),
        ),
        start_days_ago=21,
        start_hour=19,
        messages=(
            (LIN, "场订好了，英东 3 号场，差的自己带拍。"),
            (HE, "我从东校骑过去，7 点前到。"),
            (LIANG, "我带水，可薇你来玩就行，别跟何屿认真对拉。"),
        ),
        official_metadata={"created_via": "self_initiation"},
    ),
    CastGathering(
        title="东校图书馆赶 DDL",
        gathering_type="DDL冲刺",
        goal="三小时各自赶作业，互相看住别刷手机",
        campus="东校园",
        location="东校园图书馆三楼",
        status="Completed",
        owner_user_id=HE,
        members=(
            CastMember(HE, joined_via="owner"),
            CastMember(ZHOU),
            CastMember(CHEN),
        ),
        min_size=3,
        target_size=3,
        start_days_ago=14,
        start_hour=19,
        duration_hours=3,
        messages=(
            (HE, "我实验报告还差讨论部分，你们自便，别跟我说话就行。"),
            (ZHOU, "好。"),
            (CHEN, "我戴耳机赶海报，结束一起下楼。"),
        ),
    ),
    CastGathering(
        title="逸夫讲座同行",
        gathering_type="讲座",
        goal="一起听完，讲座后在门口认个路",
        campus="南校园",
        location="南校园逸夫文化艺术中心",
        status="Completed",
        owner_user_id=LIANG,
        members=(
            CastMember(LIANG, joined_via="owner"),
            CastMember(SU),
            CastMember(CHEN),
        ),
        min_size=3,
        target_size=4,
        identity_disclosure="after_full",
        start_days_ago=10,
        start_hour=16,
        messages=(
            (LIANG, "晚宁你到南门跟我说，我在逸夫门口等。"),
            (SU, "好，我班车时刻看了三遍。"),
            (CHEN, "听完要不要去看一眼展览，人多我带路。"),
        ),
        official_metadata={"created_via": "self_initiation", "first_gathering_for": SU},
    ),
    CastGathering(
        title="智能应用开发大赛筹备",
        gathering_type="比赛组队",
        goal="把初赛材料角色分清楚，本周内交一版",
        campus="东校园",
        location="东校园研讨室 15-401",
        status="Completed",
        owner_user_id=LIN,
        mode="complementary",
        required_trust_level="T2",
        required_roles=("product", "backend", "visual_design", "business_analysis"),
        members=(
            CastMember(LIN, role="产品", joined_via="owner"),
            CastMember(ZHOU, role="后端"),
            CastMember(CHEN, role="视觉"),
            CastMember(LIANG, role="路演"),
        ),
        start_days_ago=7,
        start_hour=20,
        duration_hours=2,
        messages=(
            (LIN, "角色就这样：我写产品说明，周衡接口，可薇演示页，景行路演稿。"),
            (ZHOU, "接口今晚能出一版。"),
            (CHEN, "演示页我按你们的信息架构来，别中途改主色。"),
            (LIANG, "路演我压到三分钟，你们别超时。"),
        ),
        official_metadata={
            "created_via": "self_initiation",
            "competition_name": "2026全国大学生智能应用开发大赛",
        },
    ),
    CastGathering(
        title="东校研讨室补进度",
        gathering_type="DDL冲刺",
        goal="把各自卡住的作业往前推一截",
        campus="东校园",
        location="东校园研讨室 15-203",
        status="Completed",
        owner_user_id=LIN,
        members=(
            CastMember(LIN, joined_via="owner"),
            CastMember(ZHOU),
            CastMember(HE),
        ),
        min_size=3,
        target_size=3,
        start_days_ago=4,
        start_hour=20,
        official_metadata={"created_via": "self_initiation"},
    ),
)

OPEN_GATHERINGS: tuple[CastGathering, ...] = (
    CastGathering(
        title="周六英东羽毛球",
        gathering_type="羽毛球",
        goal="打两小时，中等水平，差一个不鸽的",
        campus="南校园",
        location="南校园英东体育中心",
        status="Pooling",
        owner_user_id=LIN,
        mood_note="考完想出出汗，来个不咕的",
        members=(
            CastMember(LIN, joined_via="owner"),
            CastMember(HE),
            CastMember(LIANG),
        ),
        min_size=3,
        target_size=4,
        start_weekday=5,
        start_hour=14,
        official_metadata={"created_via": "self_initiation", "gap_for_real_user": True},
    ),
    CastGathering(
        title="数模组队差建模",
        gathering_type="比赛组队",
        goal="高教社杯数模，已有编程和写作，差一个建模",
        campus="东校园",
        location="东校园实验楼研讨室",
        status="Pooling",
        owner_user_id=ZHOU,
        mode="complementary",
        required_trust_level="T2",
        required_roles=("machine_learning", "data_analysis", "backend"),
        mood_note="不需要很熟，把题做完就行",
        members=(
            CastMember(ZHOU, role="编程", joined_via="owner"),
            CastMember(LIN, role="写作"),
        ),
        min_size=3,
        target_size=3,
        start_weekday=6,
        start_hour=19,
        duration_hours=3,
        official_metadata={
            "created_via": "self_initiation",
            "competition_name": "2026高教社杯全国大学生数学建模竞赛（广东赛区）",
            "gap_for_real_user": True,
        },
    ),
)

EXTERNAL_EVENTS: tuple[dict[str, Any], ...] = (
    {
        "source": "teachin",
        "external_key": "demo-teachin-1",
        "title": "科技企业校园宣讲会",
        "location": "南校园熊德龙学生活动中心",
        "official_url": "https://www.sysu.edu.cn/events/teachin-1",
        "details": {"registration": "official_link_only"},
        "days": 3,
    },
    {
        "source": "seminar",
        "external_key": "demo-seminar-1",
        "title": "可信人工智能前沿讲座",
        "location": "东校园学术交流中心",
        "official_url": "https://www.sysu.edu.cn/events/seminar-1",
        "details": {"registration": "official_link_only"},
        "days": 5,
    },
)
