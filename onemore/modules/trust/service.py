from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onemore.core.errors import AppError, NotFoundError
from onemore.core.time import ensure_utc
from onemore.db.models import (
    Gathering,
    GatheringMember,
    GatheringStatus,
    TrustAppeal,
    TrustEvent,
    TrustLevel,
    TrustProfile,
    User,
)

LEVEL_ORDER = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}
LEVEL_NAMES = {
    "T0": "访客",
    "T1": "已认证同学",
    "T2": "靠谱同学",
    "T3": "组局者",
    "T4": "校园主理人",
}
# 用户可读权益文案。客户端展示它，而不是 UNLOCK_LEVEL 里的技术能力键。
LEVEL_BENEFITS: dict[str, list[str]] = {
    "T0": ["浏览公开内容与校园资讯"],
    "T1": [
        "参加 3 人及以上的低风险公开局",
        "创建意图卡，等待系统成局",
        "同课破冰、DDL 冲刺等校园场景",
    ],
    "T2": [
        "进入比赛 / 项目组队池",
        "自行发起公开局",
        "参与双人局与跨院系匹配",
        "使用校园预约代理",
    ],
    "T3": [
        "创建长期共同目标",
        "发起周期性固定局 / 复局",
        "组织 6 人以上的大组",
        "使用补位快线",
    ],
    "T4": [
        "创建与管理官方局",
        "使用主理人管理台与模板",
    ],
}
# 升级文档：每一级「如何达到」的标准说明（面向用户，不是内部阈值键名）。
LEVEL_HOW: dict[str, str] = {
    "T0": "下载 App 即可进入",
    "T1": "完成统一身份认证与画像初始化",
    "T2": "完成 3 次有效成局 · 准时确认率 ≥ 80% · 近 30 天无临期爽约 · 无有效举报",
    "T3": "累计 10 次有效成局 · 其中 ≥ 3 次由本人发起 · 复局 ≥ 2 次 · 爽约率 < 10%",
    "T4": "经社团 / 院系 / 平台核验的主理人认证（不靠刷数据）",
}
UNLOCK_LEVEL = {
    "browse_open_gatherings": "T1",
    "create_intent": "T1",
    "join_group_3plus": "T1",
    "course_breakice": "T1",
    "ddl_sprint": "T1",
    "competition_pool": "T2",
    "initiate_gathering": "T2",
    "duo_gathering": "T2",
    "cross_college_matching": "T2",
    "agent_booking": "T2",
    "shared_goal": "T3",
    "recurring_gathering": "T3",
    "large_group": "T3",
    "backfill_fast_lane": "T3",
    "official_gathering": "T4",
    "organizer_console": "T4",
    "campus_event_publish": "T4",
}
EVENT_WEIGHT = {
    "on_time_confirm": 1.0,
    "early_cancel": 0.0,
    "late_exit": -2.0,
    "no_show": -3.0,
    "action_succeeded": 1.0,
    "completion_confirmed": 1.0,
    "completion_unresolved": 0.0,
    "recurred": 2.0,
    "valid_report": -100.0,
}


def ensure_trust_profile(db: Session, user_id: str) -> TrustProfile:
    profile = db.get(TrustProfile, user_id)
    if profile is None:
        user = db.get(User, user_id)
        initial = TrustLevel.T1.value if user and user.verified_at else TrustLevel.T0.value
        profile = TrustProfile(user_id=user_id, level=initial)
        db.add(profile)
        db.flush()
    return profile


def check_unlock(db: Session, user_id: str, capability: str) -> bool:
    required = UNLOCK_LEVEL.get(capability)
    if required is None:
        raise AppError("UNKNOWN_CAPABILITY", "未知的能力开关", 500)
    profile = ensure_trust_profile(db, user_id)
    return LEVEL_ORDER[profile.level] >= LEVEL_ORDER[required]


def require_unlock(db: Session, user_id: str, capability: str) -> None:
    if not check_unlock(db, user_id, capability):
        required = UNLOCK_LEVEL[capability]
        raise AppError(
            "TRUST_LEVEL_REQUIRED",
            f"此能力要求 {required} 及以上",
            403,
            {"required_level": required, "capability": capability},
        )


def record_event(
    db: Session, user_id: str, event_type: str, reference_id: str | None = None
) -> TrustEvent:
    if event_type not in EVENT_WEIGHT:
        raise AppError("UNKNOWN_TRUST_EVENT", "未知的信任事件", 500)
    event = TrustEvent(
        user_id=user_id,
        event_type=event_type,
        reference_id=reference_id,
        weight=EVENT_WEIGHT[event_type],
    )
    db.add(event)
    if event_type == "valid_report":
        profile = ensure_trust_profile(db, user_id)
        profile.previous_level = profile.level
        profile.level = TrustLevel.T1.value
        profile.valid_report_count += 1
        profile.observation_until = datetime.now(UTC) + timedelta(days=30)
    db.flush()
    return event


def record_event_once(
    db: Session, user_id: str, event_type: str, reference_id: str | None = None
) -> TrustEvent:
    existing = db.scalar(
        select(TrustEvent).where(
            TrustEvent.user_id == user_id,
            TrustEvent.event_type == event_type,
            TrustEvent.reference_id == reference_id,
        )
    )
    return existing or record_event(db, user_id, event_type, reference_id)


def recompute_level(db: Session, user_id: str) -> TrustProfile:
    profile = ensure_trust_profile(db, user_id)
    previous_level = profile.level
    now = datetime.now(UTC)
    recent_cutoff = now - timedelta(days=30)
    completed = (
        db.scalar(
            select(func.count(GatheringMember.id))
            .join(Gathering, Gathering.id == GatheringMember.gathering_id)
            .where(
                GatheringMember.user_id == user_id,
                GatheringMember.completion_confirmed.is_(True),
                Gathering.status.in_(
                    [
                        GatheringStatus.COMPLETED.value,
                        GatheringStatus.RECURRENCE_PENDING.value,
                        GatheringStatus.ARCHIVED.value,
                    ]
                ),
            )
        )
        or 0
    )
    initiated = (
        db.scalar(
            select(func.count(GatheringMember.id))
            .join(Gathering, Gathering.id == GatheringMember.gathering_id)
            .where(
                GatheringMember.user_id == user_id,
                GatheringMember.joined_via == "owner",
                GatheringMember.completion_confirmed.is_(True),
                Gathering.owner_user_id == user_id,
                Gathering.status.in_(
                    [
                        GatheringStatus.COMPLETED.value,
                        GatheringStatus.RECURRENCE_PENDING.value,
                        GatheringStatus.ARCHIVED.value,
                    ]
                ),
            )
        )
        or 0
    )
    events = list(db.scalars(select(TrustEvent).where(TrustEvent.user_id == user_id)))
    recurrences = sum(event.event_type == "recurred" for event in events)
    confirms = sum(event.event_type == "on_time_confirm" for event in events)
    late_exits = sum(event.event_type == "late_exit" for event in events)
    no_shows = sum(event.event_type == "no_show" for event in events)
    recent_events = [
        event for event in events if ensure_utc(event.occurred_at) >= recent_cutoff
    ]
    confirms_30d = sum(event.event_type == "on_time_confirm" for event in recent_events)
    late_exits_30d = sum(event.event_type == "late_exit" for event in recent_events)
    no_shows_30d = sum(
        event.event_type == "no_show" for event in recent_events
    )
    recorded_commitments = confirms + late_exits + no_shows
    failure_rate = (
        (late_exits + no_shows) / recorded_commitments
        if recorded_commitments
        else 0.0
    )
    recent_exit_commitments = confirms_30d + late_exits_30d
    recent_late_exit_rate = (
        late_exits_30d / recent_exit_commitments
        if recent_exit_commitments
        else 0.0
    )
    profile.completed_gatherings = int(completed)
    profile.initiated_gatherings = int(initiated)
    profile.recurrences = recurrences
    if recorded_commitments:
        profile.on_time_confirm_rate = confirms / recorded_commitments
        # The stored legacy field backs the product's displayed "爽约率" and
        # therefore includes both late exits and confirmed no-shows.
        profile.late_exit_rate = failure_rate
    else:
        profile.on_time_confirm_rate = 0.0
        profile.late_exit_rate = 0.0
    profile.no_show_count_30d = no_shows_30d

    user = db.get(User, user_id)
    desired_level = TrustLevel.T1.value if user and user.verified_at else TrustLevel.T0.value
    if (
        completed >= 3
        and profile.on_time_confirm_rate >= 0.8
        and no_shows_30d == 0
        and profile.valid_report_count == 0
    ):
        desired_level = TrustLevel.T2.value
    if completed >= 10 and initiated >= 3 and recurrences >= 2 and failure_rate < 0.1:
        desired_level = TrustLevel.T3.value
    if profile.organizer_verified:
        desired_level = TrustLevel.T4.value
    if profile.valid_report_count:
        desired_level = TrustLevel.T1.value

    observation_active = bool(
        profile.observation_until and ensure_utc(profile.observation_until) > now
    )
    downgrade_reason: str | None = None
    if no_shows_30d >= 2:
        downgrade_reason = "近 30 天临期爽约达到 2 次"
    elif recent_late_exit_rate > 0.25:
        downgrade_reason = "近 30 天临期退出率超过 25%"

    if profile.valid_report_count:
        level = TrustLevel.T1.value
    elif observation_active:
        # Observation freezes capability recovery. It also prevents repeated
        # recomputes of the same rolling-window events from cascading levels.
        level = profile.level
    elif downgrade_reason:
        base_level = previous_level
        profile.previous_level = base_level
        profile.observation_until = now + timedelta(days=30)
        level = f"T{max(1, LEVEL_ORDER[base_level] - 1)}"
    else:
        level = desired_level
        if profile.observation_until is not None:
            profile.observation_until = None
            profile.previous_level = None
    profile.level = level
    if level != previous_level:
        from onemore.modules.notify.service import push

        push(
            db,
            user_id,
            "trust_level_changed",
            {
                "level": level,
                "previous_level": previous_level,
                "reason": downgrade_reason or "已按当前履约记录自动重新计算",
                "screen_id": "M3",
                "deep_link": "onemore://trust/progress",
                "appeal": "/trust/appeal" if downgrade_reason else None,
                "public_badge": False,
            },
        )
    db.commit()
    db.refresh(profile)
    return profile


def enter_observation(db: Session, user_id: str) -> TrustProfile:
    profile = ensure_trust_profile(db, user_id)
    current = LEVEL_ORDER[profile.level]
    profile.previous_level = profile.level
    profile.level = f"T{max(1, current - 1)}"
    profile.observation_until = datetime.now(UTC) + timedelta(days=30)
    from onemore.modules.notify.service import push

    push(
        db,
        user_id,
        "trust_level_changed",
        {
            "level": profile.level,
            "previous_level": profile.previous_level,
            "reason": "已进入观察期",
            "appeal": "/trust/appeal",
            "screen_id": "M3",
            "deep_link": "onemore://trust/progress",
            "public_badge": False,
        },
    )
    db.commit()
    return profile


def restore(db: Session, user_id: str) -> TrustProfile:
    profile = ensure_trust_profile(db, user_id)
    if profile.observation_until is None:
        return recompute_level(db, user_id)
    if ensure_utc(profile.observation_until) > datetime.now(UTC):
        return profile
    level_before_restore = profile.level
    profile.valid_report_count = 0
    profile.observation_until = None
    profile.previous_level = None
    db.flush()
    restored = recompute_level(db, user_id)
    from onemore.modules.notify.service import push

    if restored.level == level_before_restore:
        push(
            db,
            user_id,
            "trust_level_changed",
            {
                "level": restored.level,
                "reason": "观察期结束，已按当前履约记录重新计算",
                "screen_id": "M3",
                "deep_link": "onemore://trust/progress",
            },
        )
    db.commit()
    return restored


def _metric_condition(
    *,
    key: str,
    label: str,
    current: float,
    required: float,
    unit: str,
    higher_is_better: bool = True,
) -> dict:
    if higher_is_better:
        met = current >= required
        remaining = max(0.0, required - current)
        if unit == "%":
            detail = None if met else f"当前 {current:g}%，目标 {required:g}%"
        elif remaining == int(remaining):
            detail = None if met else f"还差 {int(remaining)} {unit}"
        else:
            detail = None if met else f"还差 {remaining:g} {unit}"
        ratio = 1.0 if met else min(1.0, current / required) if required else 0.0
    else:
        # Caps such as 爽约率 < 10%：current/required 均为同一单位（如百分点）。
        met = current < required if unit == "%" else current < required
        if unit == "%":
            detail = None if met else f"当前 {current:g}%，需低于 {required:g}%"
        else:
            detail = None if met else f"当前 {current:g}，需低于 {required:g}"
        # Inverted completion: staying under the cap fills the bar.
        if met:
            ratio = 1.0
        elif required <= 0:
            ratio = 0.0
        else:
            ratio = max(0.0, 1.0 - min(1.0, current / required))
    return {
        "key": key,
        "label": label,
        "met": met,
        "current": float(current),
        "required": float(required),
        "unit": unit,
        "detail": detail,
        "_ratio": ratio,
    }


def _binary_condition(*, key: str, label: str, met: bool, detail: str | None = None) -> dict:
    return {
        "key": key,
        "label": label,
        "met": met,
        "current": 1.0 if met else 0.0,
        "required": 1.0,
        "unit": None,
        "detail": None if met else detail,
        "_ratio": 1.0 if met else 0.0,
    }


def _build_next_level_plan(profile: TrustProfile, user: User | None) -> dict:
    """Build next-level conditions/progress for the trust progress page.

    Main screen should only show the path to the *next* level. Full standards
    live in level_guide (upgrade handbook).
    """
    gaps: list[str] = []
    conditions: list[dict] = []
    next_level: str | None = None
    next_level_progress: list[dict] = []

    if profile.level == "T0":
        next_level = "T1"
        verified = bool(user and user.verified_at)
        conditions.append(
            _binary_condition(
                key="identity_verified",
                label="完成统一身份认证",
                met=verified,
                detail="完成校园身份认证后进入 T1",
            )
        )
        if not verified:
            gaps.append("完成统一身份认证与画像初始化")
    elif profile.level == "T1":
        next_level = "T2"
        conditions.append(
            _metric_condition(
                key="completed_gatherings",
                label="有效成局",
                current=profile.completed_gatherings,
                required=3,
                unit="次",
            )
        )
        conditions.append(
            _metric_condition(
                key="on_time_confirm_rate",
                label="准时确认率",
                current=round(profile.on_time_confirm_rate * 100, 1),
                required=80,
                unit="%",
            )
        )
        no_show_met = profile.no_show_count_30d == 0
        conditions.append(
            _binary_condition(
                key="no_show_30d",
                label="近 30 天无临期爽约",
                met=no_show_met,
                detail=f"近 30 天已有 {profile.no_show_count_30d} 次临期爽约",
            )
        )
        clean_record = profile.valid_report_count == 0
        conditions.append(
            _binary_condition(
                key="no_valid_report",
                label="无有效举报记录",
                met=clean_record,
                detail="存在有效举报时无法升至 T2",
            )
        )
        for cond in conditions:
            if (
                cond["key"] in {"completed_gatherings", "on_time_confirm_rate"}
                and cond.get("required") is not None
            ):
                next_level_progress.append(
                    {
                        "key": cond["key"],
                        "label": cond["label"],
                        "current": cond["current"],
                        "required": cond["required"],
                        "unit": cond["unit"] or "",
                    }
                )
            if not cond["met"] and cond.get("detail"):
                gaps.append(cond["detail"])
            elif not cond["met"]:
                gaps.append(cond["label"])
    elif profile.level == "T2":
        next_level = "T3"
        conditions.extend(
            [
                _metric_condition(
                    key="completed_gatherings",
                    label="有效成局",
                    current=profile.completed_gatherings,
                    required=10,
                    unit="次",
                ),
                _metric_condition(
                    key="initiated_gatherings",
                    label="本人发起并完成",
                    current=profile.initiated_gatherings,
                    required=3,
                    unit="次",
                ),
                _metric_condition(
                    key="recurrences",
                    label="复局",
                    current=profile.recurrences,
                    required=2,
                    unit="次",
                ),
                _metric_condition(
                    key="late_exit_rate",
                    label="爽约率（越低越好）",
                    current=round(profile.late_exit_rate * 100, 1),
                    required=10,
                    unit="%",
                    higher_is_better=False,
                ),
            ]
        )
        for cond in conditions:
            if (
                cond["key"]
                in {"completed_gatherings", "initiated_gatherings", "recurrences"}
                and cond.get("required") is not None
            ):
                next_level_progress.append(
                    {
                        "key": cond["key"],
                        "label": cond["label"],
                        "current": cond["current"],
                        "required": cond["required"],
                        "unit": cond["unit"] or "",
                    }
                )
            if not cond["met"]:
                if cond["key"] == "late_exit_rate":
                    gaps.append("将爽约率控制在 10% 以下")
                elif cond.get("detail"):
                    gaps.append(cond["detail"])
                else:
                    gaps.append(cond["label"])
    elif profile.level == "T3":
        next_level = "T4"
        verified = bool(profile.organizer_verified)
        conditions.append(
            _binary_condition(
                key="organizer_verified",
                label="完成主理人认证",
                met=verified,
                detail="主理人身份需要社团或院系认证，不靠刷数据",
            )
        )
        if not verified:
            gaps.append("主理人身份需要社团或院系认证，不靠刷数据")
    # T4: no next level

    ratios = [float(c.get("_ratio", 1.0 if c["met"] else 0.0)) for c in conditions]
    overall = round(sum(ratios) / len(ratios), 4) if ratios else 1.0

    # Strip internal helper keys before returning as API payload.
    public_conditions = [
        {k: v for k, v in cond.items() if not k.startswith("_")} for cond in conditions
    ]
    return {
        "next_level": next_level,
        "next_level_name": LEVEL_NAMES.get(next_level) if next_level else None,
        "next_level_progress": next_level_progress,
        "conditions": public_conditions,
        "gaps": gaps,
        "overall_progress": overall if next_level else 1.0,
    }


def get_progress(db: Session, user_id: str) -> dict:
    profile = recompute_level(db, user_id)
    user = db.get(User, user_id)
    plan = _build_next_level_plan(profile, user)
    unlocked_narrative = {
        "T0": "完成身份认证后，就能开始低风险公开局",
        "T1": "你已经可以进公开局、发意图卡了",
        "T2": "比赛组队、自行发起和双人局已经打开",
        "T3": "可以开周期局、带共同目标，像老搭子一样组局",
        "T4": "校园主理人：官方局与主理人台已解锁",
    }.get(profile.level)
    current_rank = LEVEL_ORDER[profile.level]
    level_guide = [
        {
            "level": level,
            "name": LEVEL_NAMES[level],
            "how": LEVEL_HOW[level],
            "benefits": list(LEVEL_BENEFITS[level]),
            "is_current": level == profile.level,
            "is_reached": LEVEL_ORDER[level] <= current_rank,
        }
        for level in ("T0", "T1", "T2", "T3", "T4")
    ]
    next_level = plan["next_level"]
    return {
        "level": profile.level,
        "level_name": LEVEL_NAMES[profile.level],
        "level_narrative": unlocked_narrative,
        "next_level": next_level,
        "next_level_name": plan["next_level_name"],
        "next_level_progress": plan["next_level_progress"],
        "conditions": plan["conditions"],
        "current_benefits": list(LEVEL_BENEFITS.get(profile.level, [])),
        "next_benefits": list(LEVEL_BENEFITS.get(next_level, [])) if next_level else [],
        "overall_progress": plan["overall_progress"],
        "level_guide": level_guide,
        "gaps": plan["gaps"],
        "statistics": {
            "completed_gatherings": profile.completed_gatherings,
            "initiated_gatherings": profile.initiated_gatherings,
            "recurrences": profile.recurrences,
            "on_time_confirm_rate": round(profile.on_time_confirm_rate, 4),
            "late_exit_rate": round(profile.late_exit_rate, 4),
            "no_show_count_30d": profile.no_show_count_30d,
        },
        # 保留技术能力表供服务端/调试；iOS 主路径不再渲染 capability 键名。
        "unlocks": [
            {
                "capability": capability,
                "required_level": required,
                "unlocked": LEVEL_ORDER[profile.level] >= LEVEL_ORDER[required],
            }
            for capability, required in UNLOCK_LEVEL.items()
        ],
        "observation": (
            {
                "until": profile.observation_until,
                "previous_level": profile.previous_level,
            }
            if profile.observation_until
            else None
        ),
    }


def create_appeal(db: Session, user_id: str, reason: str) -> TrustAppeal:
    appeal = TrustAppeal(user_id=user_id, reason=reason)
    db.add(appeal)
    db.commit()
    db.refresh(appeal)
    return appeal


def list_appeals(db: Session, user_id: str) -> list[TrustAppeal]:
    return list(
        db.scalars(
            select(TrustAppeal)
            .where(TrustAppeal.user_id == user_id)
            .order_by(TrustAppeal.created_at.desc())
        )
    )


def get_appeal(db: Session, appeal_id: str, user_id: str) -> TrustAppeal:
    appeal = db.scalar(
        select(TrustAppeal).where(
            TrustAppeal.id == appeal_id,
            TrustAppeal.user_id == user_id,
        )
    )
    if appeal is None:
        raise NotFoundError("申诉", appeal_id)
    return appeal


def resolve_appeal(
    db: Session, appeal_id: str, status: str, result: str
) -> TrustAppeal:
    appeal = db.get(TrustAppeal, appeal_id)
    if appeal is None:
        raise NotFoundError("申诉", appeal_id)
    if appeal.status != "submitted":
        raise AppError("APPEAL_ALREADY_DECIDED", "申诉已经处理", 409)
    appeal.status = status
    appeal.result = result.strip()
    appeal.decided_at = datetime.now(UTC)
    db.commit()
    db.refresh(appeal)
    return appeal
