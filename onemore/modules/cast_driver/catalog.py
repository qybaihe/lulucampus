"""Persona rhythms for the six demo students.

This is not an LLM agent. Each person has a weekly class grid, a small set of
things they would actually type into 「差一个」, and a human cadence: quiet
people almost never host, talkative people still do not post every hour.
"""

from __future__ import annotations

from dataclasses import dataclass

from onemore.db.demo_cast import CHEN, HE, LIANG, LIN, SU, ZHOU

CAST_USER_IDS: tuple[str, ...] = (LIN, ZHOU, CHEN, LIANG, SU, HE)

# Seeded gap cards left for real testers. The driver must never sit in these.
RESERVED_GAP_TITLES: frozenset[str] = frozenset({"周六英东羽毛球", "数模组队差建模"})


@dataclass(frozen=True)
class ClassBlock:
    weekday: int  # Monday = 0
    start_hour: int
    duration_hours: int
    course_code: str
    course_name: str
    location: str


@dataclass(frozen=True)
class IntentScript:
    key: str
    text: str
    campus: str
    weekdays: tuple[int, ...]
    hours: tuple[int, ...]
    mood_note: str | None = None
    roles: str | None = None
    start_weekday: int | None = None
    start_hour: int = 19
    duration_hours: int = 2


@dataclass(frozen=True)
class DriverPersona:
    user_id: str
    hosts: bool
    join_types: tuple[str, ...]
    travel_campuses: tuple[str, ...]
    cooldown_hours: float
    confirm_delay_minutes: int
    act_probability: float
    chat_probability: float
    class_blocks: tuple[ClassBlock, ...]
    scripts: tuple[IntentScript, ...]
    chat_lines: tuple[str, ...]


PERSONAS: dict[str, DriverPersona] = {
    LIN: DriverPersona(
        user_id=LIN,
        hosts=True,
        join_types=("运动搭子", "羽毛球", "比赛组队", "项目组队"),
        travel_campuses=("珠海校区", "南校园", "东校园"),
        cooldown_hours=5.0,
        confirm_delay_minutes=8,
        act_probability=0.16,
        chat_probability=0.45,
        class_blocks=(
            ClassBlock(0, 9, 2, "SE1001", "软件工程导论", "珠海校区教学楼 A301"),
            ClassBlock(1, 10, 2, "CS2002", "数据结构", "东校园实验楼 B203"),
            ClassBlock(2, 14, 2, "SE2104", "移动应用开发", "珠海校区教学楼 C105"),
        ),
        scripts=(
            IntentScript(
                key="badminton",
                text="周六下午南校园英东一起打羽毛球，4人，中等水平，不鸽",
                campus="南校园",
                weekdays=(4, 5, 6),
                hours=(12, 13, 19, 20, 21),
                mood_note="考完想出出汗",
                start_weekday=5,
                start_hour=14,
            ),
            IntentScript(
                key="hackathon",
                text="这周想找人一起做智能应用开发，差一个后端，4人",
                campus="东校园",
                weekdays=(0, 1, 2),
                hours=(12, 20, 21),
                mood_note="把初赛材料分完就行",
                roles="后端",
                start_weekday=3,
                start_hour=19,
                duration_hours=3,
            ),
        ),
        chat_lines=(
            "场次我来订，差的自己带拍。",
            "时间地点人数就这些，确认了就别鸽。",
            "我从珠海过来，提前说一声。",
        ),
    ),
    ZHOU: DriverPersona(
        user_id=ZHOU,
        hosts=False,
        join_types=("比赛组队", "DDL冲刺", "自习搭子", "活动同行"),
        travel_campuses=("东校园",),
        cooldown_hours=10.0,
        confirm_delay_minutes=90,
        act_probability=0.06,
        chat_probability=0.12,
        class_blocks=(
            ClassBlock(1, 10, 2, "CS2002", "数据结构", "东校园实验楼 B203"),
            ClassBlock(3, 15, 2, "FE1001", "机器学习", "东校园教学楼 D201"),
            ClassBlock(4, 16, 2, "GE4101", "人工智能伦理", "东校园文科楼 204"),
        ),
        scripts=(),
        chat_lines=("好。", "我到了。", "材料我放研讨室桌上。"),
    ),
    CHEN: DriverPersona(
        user_id=CHEN,
        hosts=True,
        join_types=("活动同行", "讲座", "DDL冲刺", "比赛组队", "运动搭子"),
        travel_campuses=("东校园", "南校园"),
        cooldown_hours=4.0,
        confirm_delay_minutes=20,
        act_probability=0.14,
        chat_probability=0.55,
        class_blocks=(
            ClassBlock(0, 13, 2, "DS3001", "视觉传达", "东校园传设楼 305"),
            ClassBlock(2, 18, 2, "PE1203", "体育选修乒乓球", "东校园体育馆乒乓球室"),
            ClassBlock(4, 16, 2, "GE4101", "人工智能伦理", "东校园文科楼 204"),
        ),
        scripts=(
            IntentScript(
                key="poster",
                text="想找人把海报赶完，可以边听歌，别太安静，3人",
                campus="东校园",
                weekdays=(1, 2, 3),
                hours=(19, 20, 21),
                mood_note="别太安静",
                start_weekday=2,
                start_hour=19,
                duration_hours=3,
            ),
        ),
        chat_lines=(
            "我戴耳机赶图，结束一起下楼。",
            "要不要听完去看一眼展览，人多我带路。",
            "海报我先出一版构图，你们看颜色。",
        ),
    ),
    LIANG: DriverPersona(
        user_id=LIANG,
        hosts=True,
        join_types=("活动同行", "讲座", "比赛组队", "运动搭子", "自习搭子"),
        travel_campuses=("南校园", "东校园"),
        cooldown_hours=4.0,
        confirm_delay_minutes=25,
        act_probability=0.15,
        chat_probability=0.5,
        class_blocks=(
            ClassBlock(1, 10, 2, "BA2001", "商业模式", "南校园岭南堂 201"),
            ClassBlock(3, 14, 2, "GE2208", "城市与社会", "南校园文科楼 108"),
        ),
        scripts=(
            IntentScript(
                key="teachin",
                text="南校园有宣讲会，一起去听，大一也行，4人",
                campus="南校园",
                weekdays=(1, 2, 3),
                hours=(12, 18, 19, 20),
                mood_note="听完门口认个路",
                start_weekday=2,
                start_hour=16,
            ),
            IntentScript(
                key="case",
                text="案例讨论差一个做调研的，大一也行，3人",
                campus="南校园",
                weekdays=(0, 3),
                hours=(20, 21),
                mood_note="我可以讲清楚规则",
                roles="调研",
                start_weekday=0,
                start_hour=19,
            ),
        ),
        chat_lines=(
            "晚宁你到南门跟我说，我在门口等。",
            "差一个会做调研的，规则我讲。",
            "我带水，来了回我一声。",
        ),
    ),
    SU: DriverPersona(
        user_id=SU,
        hosts=False,
        join_types=("活动同行", "讲座", "自习搭子"),
        travel_campuses=("南校园",),
        cooldown_hours=12.0,
        confirm_delay_minutes=40,
        act_probability=0.05,
        chat_probability=0.2,
        class_blocks=(
            ClassBlock(0, 8, 2, "EN1002", "学术英语写作", "南校园外国语学院 302"),
            ClassBlock(2, 8, 2, "EN1002", "学术英语写作", "南校园外国语学院 302"),
            ClassBlock(3, 14, 2, "GE2208", "城市与社会", "南校园文科楼 108"),
        ),
        scripts=(),
        chat_lines=(
            "可以的话我想先看看。",
            "好，我班车时刻看了。",
            "人多一些我更自在。",
        ),
    ),
    HE: DriverPersona(
        user_id=HE,
        hosts=True,
        join_types=("运动搭子", "羽毛球", "DDL冲刺"),
        travel_campuses=("东校园", "南校园"),
        cooldown_hours=6.0,
        confirm_delay_minutes=15,
        act_probability=0.12,
        chat_probability=0.35,
        class_blocks=(
            ClassBlock(1, 9, 3, "BIO2101", "细胞生物学", "东校园生科楼 401"),
            ClassBlock(3, 9, 3, "BIO2101", "细胞生物学", "东校园生科楼 401"),
            ClassBlock(2, 18, 2, "PE1203", "体育选修乒乓球", "东校园体育馆乒乓球室"),
        ),
        scripts=(
            IntentScript(
                key="wednesday-court",
                text="周三晚南校园英东羽毛球我定了场，差人，3人",
                campus="南校园",
                weekdays=(1, 2),
                hours=(12, 20, 21),
                mood_note="来的回我",
                start_weekday=2,
                start_hour=19,
            ),
        ),
        chat_lines=(
            "我从东校骑过去，开场前到。",
            "这周三晚英东我定了，来的回我。",
            "实验周我可能晚一点，场别放。",
        ),
    ),
}
