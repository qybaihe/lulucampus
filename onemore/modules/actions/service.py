from __future__ import annotations

import hashlib
import json
from contextlib import ExitStack
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from onemore.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from onemore.core.locks import action_locks, gathering_locks
from onemore.db.models import (
    ActionAuthorization,
    ActionModification,
    ActionStatus,
    AuthorizationGrant,
    CampusAction,
    ConfirmationStatus,
    Gathering,
    GatheringMember,
    GatheringStatus,
    SecurityEvent,
    User,
)
from onemore.hermes.catalog import CATALOG, COMMIT_FOR_PREVIEW, ActionTier
from onemore.hermes.executor import executor_pool
from onemore.hermes.schemas import ActionName, ActionRequest
from onemore.modules.gathering.state_machine import GatheringEvent, transition
from onemore.modules.trust import service as trust_service

COMMIT_ACTIONS = set(COMMIT_FOR_PREVIEW.values())


def modification_view(db: Session, action: CampusAction) -> dict | None:
    item = db.scalar(
        select(ActionModification)
        .where(ActionModification.action_id == action.id)
        .order_by(ActionModification.created_at.desc())
    )
    if item is None:
        return None
    return {
        "reason": item.reason,
        "proposed_params": item.proposed_params,
        "status": item.status,
        "created_at": item.created_at,
    }


def _active_action_members(db: Session, action: CampusAction) -> list[GatheringMember]:
    if action.gathering_id is None:
        return []
    return list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == action.gathering_id,
                GatheringMember.left_at.is_(None),
            )
        )
    )


def authorization_view(db: Session, action: CampusAction, actor_id: str) -> dict:
    member_ids = (
        {item.user_id for item in _active_action_members(db, action)}
        if action.gathering_id
        else {action.user_id}
    )
    rows = list(
        db.scalars(
            select(ActionAuthorization).where(
                ActionAuthorization.action_id == action.id,
                ActionAuthorization.user_id.in_(member_ids),
            )
        )
    ) if member_ids else []
    current = next((item for item in rows if item.user_id == actor_id), None)
    authorized = {
        item.user_id
        for item in rows
        if item.decision == "authorized" and item.snapshot_hash == action.snapshot_hash
    }
    return {
        "required_count": len(member_ids),
        "authorized_count": len(authorized),
        "actor_decision": current.decision if current else "not_required",
        "all_authorized": bool(member_ids) and authorized == member_ids,
    }


def get_for_member(db: Session, action_id: str, user_id: str) -> CampusAction:
    action = db.get(CampusAction, action_id)
    if action is None:
        raise NotFoundError("行动", action_id)
    if action.gathering_id is None:
        if action.user_id != user_id:
            raise ForbiddenError()
    else:
        member_ids = {item.user_id for item in _active_action_members(db, action)}
        if user_id not in member_ids:
            raise ForbiddenError("只有当前局成员可查看行动预览")
    return action


def authorize(
    db: Session,
    action_id: str,
    user_id: str,
    *,
    authorized: bool,
    snapshot_hash: str,
) -> CampusAction:
    current = db.get(CampusAction, action_id)
    gathering_id = current.gathering_id if current is not None else None
    with ExitStack() as stack:
        stack.enter_context(action_locks.acquire(f"action:{action_id}"))
        if gathering_id:
            stack.enter_context(gathering_locks.acquire(gathering_id))
        db.expire_all()
        action = get_for_member(db, action_id, user_id)
        if action.status != ActionStatus.PREVIEWED.value:
            raise ConflictError("ACTION_NOT_AUTHORIZABLE", "当前预览已失效或行动已结束")
        if snapshot_hash != action.snapshot_hash:
            raise ConflictError("PREVIEW_SNAPSHOT_MISMATCH", "行动预览已变化，请重新核对")
        row = db.scalar(
            select(ActionAuthorization).where(
                ActionAuthorization.action_id == action_id,
                ActionAuthorization.user_id == user_id,
            )
        )
        if row is None:
            raise ConflictError("ACTION_MEMBERSHIP_CHANGED", "当前成员确认集合已变化")
        if not authorized:
            return _invalidate_for_modification_locked(
                db,
                action,
                user_id,
                snapshot_hash=snapshot_hash,
                reason="成员要求修改行动预览",
                proposed_params={},
            )
        row.decision = "authorized" if authorized else "declined"
        row.decided_at = datetime.now(UTC)
        db.commit()
        db.refresh(action)
        return action


def propose_modification(
    db: Session,
    action_id: str,
    user_id: str,
    *,
    snapshot_hash: str,
    reason: str,
    proposed_params: dict,
) -> CampusAction:
    current = db.get(CampusAction, action_id)
    gathering_id = current.gathering_id if current is not None else None
    with ExitStack() as stack:
        stack.enter_context(action_locks.acquire(f"action:{action_id}"))
        if gathering_id:
            stack.enter_context(gathering_locks.acquire(gathering_id))
        db.expire_all()
        action = get_for_member(db, action_id, user_id)
        if action.status != ActionStatus.PREVIEWED.value:
            raise ConflictError("ACTION_NOT_MODIFIABLE", "当前预览已失效或行动已结束")
        if snapshot_hash != action.snapshot_hash:
            raise ConflictError("PREVIEW_SNAPSHOT_MISMATCH", "行动预览已变化，请重新核对")
        try:
            definition = CATALOG[ActionName(action.action_name)]
            merged_params = {**action.params, **proposed_params}
            canonical_params = definition.params_type.model_validate(
                merged_params
            ).model_dump(mode="json")
        except (KeyError, ValueError, ValidationError) as exc:
            raise AppError(
                "ACTION_MODIFICATION_PARAMS_INVALID",
                "修改后的行动参数不完整或无效",
                422,
                {
                    "issues": (
                        exc.errors(include_url=False)
                        if isinstance(exc, ValidationError)
                        else []
                    )
                },
            ) from exc
        if _canonical(canonical_params) == _canonical(action.params):
            raise ConflictError(
                "ACTION_MODIFICATION_UNCHANGED",
                "请至少修改一个可执行参数后再提交建议",
            )
        return _invalidate_for_modification_locked(
            db,
            action,
            user_id,
            snapshot_hash=snapshot_hash,
            reason=reason.strip(),
            proposed_params=canonical_params,
        )


def _invalidate_for_modification_locked(
    db: Session,
    action: CampusAction,
    user_id: str,
    *,
    snapshot_hash: str,
    reason: str,
    proposed_params: dict,
) -> CampusAction:
    if len(_canonical(proposed_params).encode()) > 4096:
        raise AppError("ACTION_MODIFICATION_TOO_LARGE", "修改建议内容过长", 422)
    modification = ActionModification(
        action_id=action.id,
        requester_user_id=user_id,
        snapshot_hash=snapshot_hash,
        reason=reason,
        proposed_params=proposed_params,
    )
    db.add(modification)
    action.status = ActionStatus.INVALIDATED.value
    db.query(ActionAuthorization).filter(
        ActionAuthorization.action_id == action.id
    ).update(
        {
            ActionAuthorization.decision: "invalidated",
            ActionAuthorization.decided_at: datetime.now(UTC),
        },
        synchronize_session=False,
    )
    if action.gathering_id:
        gathering = db.get(Gathering, action.gathering_id)
        if gathering is not None and gathering.status == GatheringStatus.PREVIEWED.value:
            transition(
                db,
                gathering,
                GatheringEvent.PREVIEW_INVALIDATED,
                actor_user_id=None,
            )
        from onemore.modules.notify.service import push

        for member in _active_action_members(db, action):
            push(
                db,
                member.user_id,
                "action_modification_requested",
                {
                    "action_id": action.id,
                    "gathering_id": action.gathering_id,
                    "deep_link": f"onemore://gathering/{action.gathering_id}/space",
                    "summary": "行动预览需要调整，请核对下一版预览",
                },
                dedupe_key=f"action-modification:{action.id}",
            )
    db.commit()
    db.refresh(action)
    return action


def _canonical(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: dict) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _security_event(db: Session, user_id: str, event_type: str, details: dict) -> None:
    db.add(SecurityEvent(user_id=user_id, event_type=event_type, details=details))
    db.commit()


def _check_grant(db: Session, user_id: str, scope: str | None) -> None:
    if scope is None:
        return
    granted = db.scalar(
        select(AuthorizationGrant.granted).where(
            AuthorizationGrant.user_id == user_id,
            AuthorizationGrant.scope == scope,
        )
    )
    if not granted:
        raise AppError(
            "GRANT_REQUIRED",
            "需要先授予对应的数据或代理权限",
            403,
            {"scope": scope},
        )


def _check_trust(db: Session, user_id: str, required_level: str) -> None:
    profile = trust_service.ensure_trust_profile(db, user_id)
    if trust_service.LEVEL_ORDER[profile.level] < trust_service.LEVEL_ORDER[required_level]:
        raise AppError(
            "TRUST_LEVEL_REQUIRED",
            f"此能力要求 {required_level} 及以上",
            403,
            {"required_level": required_level},
        )


def execute_read_action(db: Session, user_id: str, action: ActionName, params: dict) -> object:
    definition = CATALOG[action]
    if definition.is_write or definition.tier != ActionTier.GREEN:
        raise AppError("PREVIEW_REQUIRED", "写操作必须进入正式预览页", 409)
    try:
        validated = definition.params_type.model_validate(params)
    except ValidationError as exc:
        raise AppError(
            "ACTION_PARAMS_INVALID",
            "动作参数校验失败",
            422,
            {"issues": exc.errors(include_url=False)},
        ) from exc
    _check_grant(db, user_id, definition.required_grant)
    _check_trust(db, user_id, definition.required_trust_level)
    canonical_params = validated.model_dump(mode="json")
    request = ActionRequest(
        action=action,
        user_id=user_id,
        params=canonical_params,
        confirm=False,
        idempotency_key=_hash(
            {"user_id": user_id, "action": action.value, "params": canonical_params}
        ),
    )
    result = executor_pool.execute(request)
    if not result.ok:
        raise AppError(
            "CAMPUS_QUERY_FAILED",
            "校园数据暂时不可用",
            503,
            {"category": result.error_category},
        )
    return result.data


def _check_gathering_confirmed(db: Session, gathering_id: str, user_id: str) -> Gathering:
    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        raise NotFoundError("局", gathering_id)
    if gathering.status not in {
        GatheringStatus.CONFIRMED.value,
        GatheringStatus.PREVIEWED.value,
    }:
        raise ConflictError("GATHERING_NOT_CONFIRMED", "局尚未完成全员确认")
    members = list(
        db.scalars(
            select(GatheringMember).where(
                GatheringMember.gathering_id == gathering_id,
                GatheringMember.left_at.is_(None),
            )
        )
    )
    if user_id not in {member.user_id for member in members}:
        raise ForbiddenError("只有局成员可生成或执行行动")
    if gathering.owner_user_id != user_id:
        raise ForbiddenError("校园写操作只能由本局发起人的授权代理提交")
    if len(members) < gathering.min_size or not all(
        member.confirmation_status == ConfirmationStatus.CONFIRMED.value for member in members
    ):
        raise ConflictError("ALL_MEMBERS_NOT_CONFIRMED", "必须由全体成员分别确认")
    return gathering


def _validate_action(
    db: Session,
    user: User,
    action: ActionName,
    params: dict,
    gathering_id: str | None,
) -> ActionRequest:
    if action not in CATALOG:
        _security_event(db, user.id, "action_not_allowlisted", {"action": str(action)})
        raise AppError("ACTION_NOT_ALLOWED", "动作不在白名单内", 403)
    if action in COMMIT_ACTIONS:
        _security_event(db, user.id, "client_requested_commit_action", {"action": action.value})
        raise AppError("COMMIT_ACTION_INTERNAL_ONLY", "提交动作只能由服务端生成", 403)
    definition = CATALOG[action]
    request = ActionRequest(
        action=action,
        user_id=user.id,
        params=params,
        gathering_id=gathering_id,
        confirm=False,
        idempotency_key="validation-only",
    )
    try:
        request.validated_params()
    except ValidationError as exc:
        raise AppError(
            "ACTION_PARAMS_INVALID",
            "动作参数校验失败",
            422,
            {"issues": exc.errors(include_url=False)},
        ) from exc
    _check_grant(db, user.id, definition.required_grant)
    _check_trust(db, user.id, definition.required_trust_level)
    if definition.tier == ActionTier.YELLOW:
        if gathering_id:
            _check_gathering_confirmed(db, gathering_id, user.id)
        elif params.get("members"):
            raise AppError(
                "GATHERING_REQUIRED",
                "包含其他成员的可执行动作必须绑定已确认的局",
                422,
            )
    return request


def preview(
    db: Session,
    user: User,
    *,
    action: ActionName,
    params: dict,
    gathering_id: str | None,
    idempotency_key: str | None,
    client_confirm: bool,
) -> CampusAction:
    key = idempotency_key or _hash(
        {"user_id": user.id, "gathering_id": gathering_id, "action": action.value, "params": params}
    )
    with ExitStack() as stack:
        stack.enter_context(action_locks.acquire(f"preview:{key}"))
        if gathering_id:
            stack.enter_context(gathering_locks.acquire(gathering_id))
        return _preview_locked(
            db,
            user,
            action=action,
            params=params,
            gathering_id=gathering_id,
            idempotency_key=key,
            client_confirm=client_confirm,
        )


def _preview_locked(
    db: Session,
    user: User,
    *,
    action: ActionName,
    params: dict,
    gathering_id: str | None,
    idempotency_key: str,
    client_confirm: bool,
) -> CampusAction:
    if client_confirm:
        _security_event(
            db,
            user.id,
            "client_confirm_discarded",
            {"phase": "preview", "action": action.value},
        )
    _validate_action(db, user, action, params, gathering_id)
    if action not in COMMIT_FOR_PREVIEW:
        raise AppError("ACTION_NOT_PREVIEWABLE", "该动作不是可提交动作", 422)
    key = idempotency_key
    existing = db.scalar(select(CampusAction).where(CampusAction.idempotency_key == key))
    if existing:
        if existing.user_id != user.id:
            raise ConflictError("IDEMPOTENCY_KEY_CONFLICT", "幂等键已被占用")
        return existing
    request = ActionRequest(
        action=action,
        user_id=user.id,
        params=params,
        gathering_id=gathering_id,
        confirm=False,
        idempotency_key=key,
    )
    result = executor_pool.execute(request, server_confirmed=False)
    if not result.ok:
        raise AppError(
            "HERMES_PREVIEW_FAILED",
            "行动预览生成失败",
            503,
            {"category": result.error_category},
        )
    snapshot = {"action": action.value, "params": params, "result": result.data}
    record = CampusAction(
        user_id=user.id,
        gathering_id=gathering_id,
        action_name=action.value,
        commit_action_name=COMMIT_FOR_PREVIEW[action].value,
        params=params,
        preview_snapshot=snapshot,
        snapshot_hash=_hash(snapshot),
        status=ActionStatus.PREVIEWED.value,
        idempotency_key=key,
    )
    db.add(record)
    if gathering_id:
        gathering = _check_gathering_confirmed(db, gathering_id, user.id)
        if gathering.status == GatheringStatus.CONFIRMED.value:
            transition(db, gathering, GatheringEvent.PREVIEW_CREATED, actor_user_id=user.id)
        from onemore.modules.notify.service import notify_authorization_required

        db.flush()
        for member in _active_action_members(db, record):
            db.add(
                ActionAuthorization(
                    action_id=record.id,
                    user_id=member.user_id,
                    snapshot_hash=record.snapshot_hash,
                    decision="pending",
                )
            )
        notify_authorization_required(db, gathering_id, record.id)
        pending_modification = db.scalar(
            select(ActionModification)
            .join(CampusAction, CampusAction.id == ActionModification.action_id)
            .where(
                CampusAction.gathering_id == gathering_id,
                ActionModification.status == "requested",
            )
            .order_by(ActionModification.created_at.desc())
        )
        if (
            pending_modification is not None
            and _canonical(pending_modification.proposed_params)
            == _canonical(record.params)
        ):
            pending_modification.status = "applied"
    else:
        db.flush()
        db.add(
            ActionAuthorization(
                action_id=record.id,
                user_id=user.id,
                snapshot_hash=record.snapshot_hash,
                decision="pending",
            )
        )
    db.commit()
    db.refresh(record)
    return record


def execute(
    db: Session,
    user: User,
    *,
    action_id: str,
    params: dict | None,
    client_confirm: bool,
) -> CampusAction:
    record = db.get(CampusAction, action_id)
    gathering_id = record.gathering_id if record else None
    with ExitStack() as stack:
        stack.enter_context(action_locks.acquire(f"action:{action_id}"))
        if gathering_id:
            stack.enter_context(gathering_locks.acquire(gathering_id))
        db.expire_all()
        return _execute_locked(
            db,
            user,
            action_id=action_id,
            params=params,
            client_confirm=client_confirm,
        )


def _execute_locked(
    db: Session,
    user: User,
    *,
    action_id: str,
    params: dict | None,
    client_confirm: bool,
) -> CampusAction:
    record = db.get(CampusAction, action_id)
    if record is None:
        raise NotFoundError("行动预览", action_id)
    if record.user_id != user.id:
        raise ForbiddenError()
    if client_confirm:
        _security_event(
            db,
            user.id,
            "client_confirm_discarded",
            {"phase": "execute", "action_id": action_id},
        )
    if record.status == ActionStatus.SUCCEEDED.value:
        return record
    if record.status != ActionStatus.PREVIEWED.value:
        raise ConflictError("ACTION_NOT_EXECUTABLE", "预览已失效或行动已结束")
    if params is not None and _canonical(params) != _canonical(record.params):
        _security_event(db, user.id, "preview_params_mismatch", {"action_id": action_id})
        raise ConflictError("PREVIEW_PARAMS_MISMATCH", "执行参数与预览快照不一致")
    if _hash(record.preview_snapshot) != record.snapshot_hash:
        _security_event(db, user.id, "preview_snapshot_tampered", {"action_id": action_id})
        raise ConflictError("PREVIEW_SNAPSHOT_MISMATCH", "预览快照完整性校验失败")
    if not record.commit_action_name:
        raise AppError("MISSING_COMMIT_ACTION", "行动缺少内部提交映射", 500)
    commit_action = ActionName(record.commit_action_name)
    definition = CATALOG[commit_action]
    _check_grant(db, user.id, definition.required_grant)
    trust_service.require_unlock(db, user.id, "agent_booking")
    gathering = None
    if record.gathering_id:
        gathering = _check_gathering_confirmed(db, record.gathering_id, user.id)
        if gathering.status != GatheringStatus.PREVIEWED.value:
            raise ConflictError("PREVIEW_REQUIRED", "没有处于有效 Previewed 状态的局")
        member_ids = {item.user_id for item in _active_action_members(db, record)}
        authorized_ids = set(
            db.scalars(
                select(ActionAuthorization.user_id).where(
                    ActionAuthorization.action_id == record.id,
                    ActionAuthorization.user_id.in_(member_ids),
                    ActionAuthorization.snapshot_hash == record.snapshot_hash,
                    ActionAuthorization.decision == "authorized",
                )
            )
        )
        if not member_ids or authorized_ids != member_ids:
            raise ConflictError(
                "ACTION_AUTHORIZATION_INCOMPLETE",
                "需要每位当前成员分别核对并确认同一份行动预览",
                {
                    "required_count": len(member_ids),
                    "authorized_count": len(authorized_ids),
                },
            )
    else:
        self_authorized = db.scalar(
            select(ActionAuthorization.id).where(
                ActionAuthorization.action_id == record.id,
                ActionAuthorization.user_id == user.id,
                ActionAuthorization.snapshot_hash == record.snapshot_hash,
                ActionAuthorization.decision == "authorized",
            )
        )
        if self_authorized is None:
            raise ConflictError(
                "ACTION_AUTHORIZATION_INCOMPLETE",
                "请先核对并授权这份个人行动预览",
                {"required_count": 1, "authorized_count": 0},
            )
    record.status = ActionStatus.EXECUTING.value
    db.flush()
    request = ActionRequest(
        action=commit_action,
        user_id=user.id,
        params=record.params,
        gathering_id=record.gathering_id,
        confirm=False,
        idempotency_key=record.idempotency_key,
    )
    result = executor_pool.execute(request, server_confirmed=True)
    if result.ok:
        record.status = ActionStatus.SUCCEEDED.value
        record.execution_result = result.data
        if gathering:
            transition(db, gathering, GatheringEvent.ACTION_SUCCEEDED, actor_user_id=user.id)
            trust_service.record_event(db, user.id, "action_succeeded", gathering.id)
            from onemore.modules.collab.service import exit_protocol
            from onemore.modules.notify.service import sync_calendar

            exit_protocol(db, gathering.id)
            sync_calendar(db, gathering.id)
    else:
        record.status = ActionStatus.FAILED.value
        record.error_category = result.error_category
        record.execution_result = {"message": "校园操作未完成"}
        if gathering:
            transition(db, gathering, GatheringEvent.ACTION_FAILED, actor_user_id=user.id)
        if result.error_category == "login_expired":
            from onemore.modules.notify.service import notify_reauthorization_required

            notify_reauthorization_required(
                db,
                user.id,
                action_id=record.id,
                gathering_id=record.gathering_id,
            )
    db.commit()
    db.refresh(record)
    return record


def rollback(db: Session, action_id: str) -> CampusAction:
    record = db.get(CampusAction, action_id)
    if record is None:
        raise NotFoundError("行动", action_id)
    if record.status not in {ActionStatus.SUCCEEDED.value, ActionStatus.FAILED.value}:
        raise ConflictError("ACTION_NOT_ROLLBACKABLE", "当前行动不需要回滚")
    from onemore.modules.notify.service import revoke_calendar

    if record.gathering_id:
        revoke_calendar(db, record.gathering_id)
        gathering = db.get(Gathering, record.gathering_id)
        if gathering and gathering.status == GatheringStatus.EXECUTED.value:
            transition(db, gathering, GatheringEvent.ROLLBACK)
    record.status = ActionStatus.ROLLED_BACK.value
    db.commit()
    return record
