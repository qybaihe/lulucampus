"""Deterministic fake provider for tests and local demos.

Walks the entire state machine without a real browser: produces a stable PNG
QR, simulates a scan after a short delay, resolves a demo account and streams
a fixed set of like items (with has_more=0 on the last page).
"""

from __future__ import annotations

import base64
import io
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

from onemore.modules.taste_profile.analyzer import normalize_item
from onemore.modules.taste_profile.providers.base import (
    DouyinProvider,
    PageResult,
    ProviderError,
    QRResult,
)

_SCAN_DELAY_SECONDS = 0.15
_PAGE_DELAY_SECONDS = 0.03
_PHONE_REQUIRED = False

# (description, hashtags, platform_tags) per interest domain — deterministic.
_CATEGORY_SAMPLES: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "ai_programming": (
        (
            "AI 大模型入门教程 手把手写一个智能体",
            "开源项目复盘 我是怎么用 Python 做工具的",
            "ChatGPT 提示词技巧 一键提升效率",
            "用 DeepSeek 做 rag 检索 实用指南",
        ),
        ("AI", "编程", "开源"),
        ("科技",),
    ),
    "tech_devices": (
        ("新 iPhone 测评 值不值得买", "MacBook 效率工具推荐 干货", "相机镜头怎么选 避坑指南", "桌面数码清单 低成本装备"),
        ("数码",),
        ("科技",),
    ),
    "gaming_strategy": (
        ("王者荣耀 马超连招教学", "三国杀高手心得 策略复盘", "steam 年度好游戏推荐", "电竞选手操作拆解 干货"),
        ("游戏",),
        ("游戏",),
    ),
    "visual_creation": (
        ("电影感调色教程 摄影构图技巧", "vlog 拍摄转场 后期剪辑思路", "大疆航拍风景 画面美学", "人像写真焦段选择 摄影指南"),
        ("摄影",),
        ("摄影",),
    ),
    "music_literature": (
        ("周杰伦经典歌词 文学感文案", "钢琴弹唱翻唱 氛围感音乐", "现代诗书摘 治愈系文字", "哲学美学思考 传统文化之美"),
        ("音乐",),
        ("音乐",),
    ),
    "travel_city": (
        ("城市周末出游攻略 机票酒店省钱", "日本旅行签证指南 性价比路线", "海边风景治愈 旅行记录", "大学生穷游避坑 低成本攻略"),
        ("旅行",),
        ("旅行",),
    ),
    "career_growth": (
        ("大学生求职面试技巧 干货", "黑客松竞赛复盘 获奖项目分享", "应届生实习成长 职场认知", "副业赚钱信息差 商业案例分析"),
        ("求职", "竞赛"),
        ("职场",),
    ),
    "health_sports": (
        ("跑步健身入门 康复训练指南", "减脂增肌饮食方法 干货", "膝盖损伤恢复 体态改善教程", "睡眠饮食健康科普"),
        ("健康",),
        ("健康",),
    ),
    "relationship_family": (
        ("情侣相处之道 情感治愈", "亲子陪伴 家庭幸福小技巧", "治愈系情感文案 陪伴", "朋友人际交往 情商干货"),
        ("情感",),
        ("情感",),
    ),
    "humor_pets": (
        ("猫meme 抽象段子 哈哈", "离谱搞笑日常 萌宠合集", "土狗搞笑视频 反差萌", "万万没想到 搞笑反转"),
        ("搞笑",),
        ("萌宠",),
    ),
    "finance_consumption": (
        ("理财基金入门 省钱避坑指南", "性价比消费决策 信息差", "买房租房 财经科普", "股票投资 经济学常识"),
        ("理财",),
        ("财经",),
    ),
    "knowledge_method": (
        ("学习方法干货 教程指南", "冷知识科普 原理讲解", "高效方法论 效率工具指南", "为什么系列 手把手入门"),
        ("知识",),
        ("科普",),
    ),
}

_AUTHOR_POOL = (
    "科技君",
    "阿元",
    "数字匠人",
    "影客",
    "青云",
    "代码鱼",
    "日常研究所",
    "玩法研究所",
    "知识星球君",
    "旅行罐头",
    "书房里的猫",
    "慢跑同学",
    "小满与三餐",
    "离谱本离",
    "账本先生",
    "方法论社",
    "先锋小队",
    "美学散步",
    "比赛狂人",
    "开源爱好者",
)


class FakeDouyinProvider(DouyinProvider):
    """Self-contained provider used in fake mode (default for tests)."""

    def __init__(self, import_id: str, runtime_dir, settings) -> None:
        super().__init__(import_id, runtime_dir, settings)
        self._cancelled = threading.Event()
        self._logged_in = False
        self._sms_requested = False
        self._qr_scanned = False
        self._started_at = time.monotonic()

    def start(self) -> None:
        self._started_at = time.monotonic()
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        time.sleep(0.02)

    def prepare_qr(self, version: int) -> QRResult:
        import qrcode

        buffer = io.BytesIO()
        qrcode.make(f"onemore://douyin/fake/{self.import_id}?v={version}").save(
            buffer, format="PNG"
        )
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return QRResult(
            image_data_url=f"data:image/png;base64,{encoded}",
            expires_in_seconds=self.settings.douyin_qr_timeout_seconds,
        )

    def is_logged_in(self) -> bool:
        if not self._qr_scanned and time.monotonic() - self._started_at >= _SCAN_DELAY_SECONDS:
            self._qr_scanned = True
            if not _PHONE_REQUIRED:
                self._logged_in = True
        return self._logged_in

    def is_qr_scanned(self) -> bool:
        return self._qr_scanned

    def is_phone_verification_required(self) -> bool:
        return _PHONE_REQUIRED and self._qr_scanned and not self._logged_in

    def request_sms_code(self, phone: str, country_code: str) -> None:
        if not self._qr_scanned:
            raise ProviderError("DOUYIN_SCAN_REQUIRED", "请先完成抖音二维码扫码")
        if not phone.isdigit() or not country_code.isdigit():
            raise ProviderError("DOUYIN_PHONE_INVALID", "手机号格式不正确")
        self._sms_requested = True

    def submit_sms_code(self, code: str) -> None:
        if not self._sms_requested:
            raise ProviderError("DOUYIN_SMS_NOT_REQUESTED", "请先获取短信验证码")
        if code != "123456":
            raise ProviderError("DOUYIN_SMS_CODE_INVALID", "验证码错误或已过期")
        self._logged_in = True

    def resolve_profile(self) -> dict[str, Any]:
        return {
            "nickname": "演示用户",
            "avatar_url": "https://p3.douyinpic.com/aweme/100x100/demo.png",
            "uid": "3913884925184093",
            "sec_uid": "MS4wLjABAAAAfake-demo-sec-uid",
        }

    def collect(
        self,
        max_items: int,
        is_cancelled: Callable[[], bool],
    ) -> Iterator[PageResult]:
        pages = self._build_pages()
        unique: dict[str, dict[str, Any]] = {}
        for page_index, (raw_items, has_more) in enumerate(pages):
            if is_cancelled():
                break
            api_pages = page_index + 1
            if max_items:
                remaining = max_items - len(unique)
                if remaining <= 0:
                    break
                if len(raw_items) > remaining:
                    raw_items = raw_items[:remaining]
            for raw in raw_items:
                unique[str(raw["aweme_id"])] = raw
            time.sleep(_PAGE_DELAY_SECONDS)
            yield PageResult(
                page_index=page_index,
                items=[normalize_item(raw) for raw in raw_items],
                api_pages=api_pages,
                items_collected=len(unique),
                has_more=has_more,
            )
            if not has_more or (max_items and len(unique) >= max_items):
                break

    def cancel(self) -> None:
        self._cancelled.set()

    def cleanup(self) -> None:
        self._cancelled.set()

    def _build_pages(self) -> list[tuple[list[dict[str, Any]], bool]]:
        domain_names = list(_CATEGORY_SAMPLES.keys())
        total = 260
        first_boundary = 100
        second_boundary = 190
        items: list[dict[str, Any]] = []
        for index in range(total):
            if index < 120:
                domain = domain_names[index % 3]  # ai_programming, tech_devices, gaming_strategy
            elif index < 200:
                domain = domain_names[4 + (index % 3)]  # music, travel, career
            else:
                domain = domain_names[(index % 4) + 7]
            samples = _CATEGORY_SAMPLES[domain]
            description = samples[0][index % len(samples[0])]
            author = _AUTHOR_POOL[index % len(_AUTHOR_POOL)]
            items.append(
                {
                    "aweme_id": 7530000000000000000 + index,
                    "desc": description,
                    "item_title": "",
                    "author": {
                        "nickname": author,
                        "uid": f"uid-{index % 40}",
                        "sec_uid": f"sec-{index % 40}",
                    },
                    "create_time": 1780000000 + index * 3600,
                    "statistics": {
                        "digg_count": (index * 7) % 5000,
                        "comment_count": index % 300,
                        "collect_count": index % 100,
                        "share_count": index % 40,
                    },
                    "text_extra": [
                        {"hashtag_name": tag}
                        for tag in samples[1]
                    ],
                    "video_tag": [
                        {"tag_name": tag, "level": 1}
                        for tag in samples[2]
                    ],
                    "video": {"duration": 30000 + (index % 5) * 10000},
                    "aweme_type": 0,
                    "is_aigc_media": index % 5 == 0,
                }
            )
        # Deliberately re-expose the last 10 items of each boundary so the
        # aweme_id dedupe path is exercised: raw payloads > unique items.
        page0 = items[:first_boundary]
        page1 = items[first_boundary - 10 : second_boundary]
        page2 = items[second_boundary - 10 :]
        return [
            (page0, True),
            (page1, True),
            (page2, False),
        ]
