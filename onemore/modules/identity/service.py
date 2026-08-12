from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from onemore.core.auth import issue_access_token
from onemore.core.config import get_settings
from onemore.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from onemore.core.locks import identity_locks
from onemore.core.passwords import hash_password, verify_password
from onemore.core.time import ensure_utc
from onemore.db.models import (
    ActionStatus,
    AuthorizationGrant,
    CampusAction,
    Enrollment,
    Gathering,
    GatheringMember,
    GatheringStatus,
    GrantScope,
    IntentCard,
    IntentStatus,
    LoginSession,
    LoginStatus,
    Profile,
    SessionHealth,
    TimeWindow,
    TrustLevel,
    TrustProfile,
    User,
    new_id,
    utcnow,
)
from onemore.hermes.vault import vault_manager


def register_phone_account(
    db: Session,
    phone: str,
    password: str,
    display_name: str | None = None,
) -> tuple[User, str]:
    """Create a phone+password account and issue an access token."""

    existing = db.scalar(select(User).where(User.phone == phone))
    if existing is not None:
        raise ConflictError("PHONE_ALREADY_REGISTERED", "该手机号已注册，请直接登录")
    user = User(
        phone=phone,
        password_hash=hash_password(password),
        display_name=(display_name or f"同学{phone[-4:]}").strip(),
        account_status="active",
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("PHONE_ALREADY_REGISTERED", "该手机号已注册，请直接登录") from exc
    _ensure_authenticated_trust_floor(db, user.id)
    db.commit()
    db.refresh(user)
    return user, issue_access_token(user.id)


def login_phone_account(db: Session, phone: str, password: str) -> tuple[User, str]:
    """Verify phone+password credentials and issue an access token."""

    user = db.scalar(select(User).where(User.phone == phone))
    if user is None or not verify_password(password, user.password_hash):
        # Single error for both cases so the endpoint doesn't leak which
        # phone numbers are registered.
        raise AppError("INVALID_CREDENTIALS", "手机号或密码不正确", 401)
    if user.account_status != "active":
        raise AppError("ACCOUNT_UNAVAILABLE", "该账号当前不可用", 403)
    _ensure_authenticated_trust_floor(db, user.id)
    db.commit()
    return user, issue_access_token(user.id)


def create_login_session(
    db: Session,
    user_id: str | None = None,
    device_install_id: str | None = None,
) -> tuple[LoginSession, str]:
    user = db.get(User, user_id) if user_id else None
    if user is not None and user.account_status != "active":
        user = None
    if user is None:
        user = User(id=user_id or new_id(), account_status="pending_identity")
        db.add(user)
        db.flush()
        db.add(TrustProfile(user_id=user.id, level=TrustLevel.T0.value))
    redemption_token = secrets.token_urlsafe(32)
    session = LoginSession(
        user_id=user.id,
        status=LoginStatus.PENDING.value,
        expires_at=datetime.now(UTC) + timedelta(seconds=200),
        redemption_token_hash=hashlib.sha256(redemption_token.encode()).hexdigest(),
        device_install_id_hash=(
            hashlib.sha256(device_install_id.encode()).hexdigest() if device_install_id else None
        ),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, redemption_token


def _validate_redemption_token(session: LoginSession, redemption_token: str) -> None:
    supplied = hashlib.sha256(redemption_token.encode()).hexdigest()
    expected = session.redemption_token_hash
    if expected is None or not hmac.compare_digest(supplied, expected):
        raise ForbiddenError("登录会话的设备兑换凭证无效")


def _expire_login_if_needed(db: Session, session: LoginSession) -> None:
    if ensure_utc(session.expires_at) >= datetime.now(UTC):
        return
    if session.status != LoginStatus.TIMEOUT.value:
        session.status = LoginStatus.TIMEOUT.value
        session.error_category = "SESSION_EXPIRED"
        db.commit()


def _login_response_key() -> bytes:
    return hashlib.sha256(
        f"login-redemption-response:{get_settings().auth_signing_key}".encode()
    ).digest()


def _encrypt_login_response(token: str, session_id: str, operation_hash: str) -> str:
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(_login_response_key()).encrypt(
        nonce, token.encode(), f"{session_id}:{operation_hash}".encode()
    )
    return base64.urlsafe_b64encode(nonce + encrypted).decode()


def _decrypt_login_response(ciphertext: str, session_id: str, operation_hash: str) -> str:
    raw = base64.urlsafe_b64decode(ciphertext.encode())
    return (
        AESGCM(_login_response_key())
        .decrypt(raw[:12], raw[12:], f"{session_id}:{operation_hash}".encode())
        .decode()
    )


def prepare_fake_login(db: Session, session_id: str) -> None:
    session = db.get(LoginSession, session_id)
    if session is None:
        return
    fake_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180">'
        '<rect width="180" height="180" fill="white"/><text x="20" y="92" '
        'font-size="18">DEMO QR</text></svg>'
    )
    encoded = base64.b64encode(fake_svg.encode()).decode()
    session.qr_image_data_url = f"data:image/svg+xml;base64,{encoded}"
    session.deep_link = f"onemore://auth/scan/{session.id}"
    session.status = LoginStatus.WAITING_SCAN.value
    db.commit()


def campus_identity_hash(subject_identifier: str) -> str:
    """Pseudonymize a campus login subject without persisting the raw NetID."""

    normalized = unicodedata.normalize("NFKC", subject_identifier).strip().casefold()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._@-]{2,127}", normalized):
        raise AppError("CAMPUS_IDENTITY_INVALID", "校园身份标识格式无效", 422)
    settings = get_settings()
    key = settings.identity_hash_key
    if not key:
        if settings.is_production:
            raise AppError("IDENTITY_HASH_KEY_UNAVAILABLE", "校园身份绑定服务不可用", 503)
        key = f"development-campus-identity:{settings.auth_signing_key}"
    digest = hmac.new(key.encode(), normalized.encode(), hashlib.sha256).hexdigest()
    return f"v1:{digest}"


def _bind_campus_identity(
    db: Session, session: LoginSession, subject_identifier: str
) -> tuple[User, str | None]:
    subject_hash = campus_identity_hash(subject_identifier)
    original = db.get(User, session.user_id)
    if original is None:
        raise NotFoundError("用户", session.user_id)

    target = db.scalar(select(User).where(User.netid_hash == subject_hash))
    if target is None:
        if original.netid_hash in {None, subject_hash}:
            target = original
            target.netid_hash = subject_hash
        else:
            # A signed-in user may deliberately scan another campus account.
            # Bind that identity to a fresh account instead of merging histories.
            target = User(netid_hash=subject_hash, account_status="active")
            db.add(target)
            db.flush()

    provisional_to_purge: str | None = None
    if target.id != original.id:
        session.user_id = target.id
        db.flush()
        has_other_sessions = db.scalar(
            select(LoginSession.id).where(
                LoginSession.user_id == original.id,
                LoginSession.id != session.id,
            )
        )
        if (
            original.account_status == "pending_identity"
            and original.netid_hash is None
            and original.verified_at is None
            and has_other_sessions is None
        ):
            provisional_to_purge = original.id
            db.delete(original)

    target.account_status = "active"
    target.verified_at = target.verified_at or utcnow()
    _ensure_authenticated_trust_floor(db, target.id)
    return target, provisional_to_purge


def _ensure_authenticated_trust_floor(db: Session, user_id: str) -> None:
    """Authentication raises the T0 floor but never erases earned trust."""

    trust = db.get(TrustProfile, user_id)
    if trust is None:
        db.add(TrustProfile(user_id=user_id, level=TrustLevel.T1.value))
    elif trust.level == TrustLevel.T0.value:
        trust.level = TrustLevel.T1.value


def _mark_login_subsystems(db: Session, user_id: str, *, fake: bool) -> None:
    for subsystem in ("cas", "jwxt", "libic", "gym", "explore"):
        health = db.scalar(
            select(SessionHealth).where(
                SessionHealth.user_id == user_id, SessionHealth.subsystem == subsystem
            )
        )
        if health is None:
            health = SessionHealth(user_id=user_id, subsystem=subsystem)
            db.add(health)
        health.healthy = fake or subsystem == "cas"
        health.last_checked_at = utcnow() if health.healthy else None
        health.error_category = None


def complete_fake_login(
    db: Session, session_id: str, campus_subject: str = "demo-default"
) -> LoginSession:
    session = db.get(LoginSession, session_id)
    if session is None:
        raise NotFoundError("登录会话", session_id)
    _expire_login_if_needed(db, session)
    if session.status in {
        LoginStatus.TIMEOUT.value,
        LoginStatus.CANCELLED.value,
    }:
        raise ConflictError("LOGIN_SESSION_TERMINAL", "登录会话已结束")
    subject_hash = campus_identity_hash(campus_subject)
    with identity_locks.acquire(subject_hash):
        db.expire_all()
        session = db.get(LoginSession, session_id)
        if session is None:
            raise NotFoundError("登录会话", session_id)
        original = db.get(User, session.user_id)
        if original is None:
            raise NotFoundError("用户", session.user_id)
        # ``resume_user_id`` is a development-only login fixture.  When its
        # already-bound active account completes the default fake scan, keep
        # that exact identity instead of binding every test run to the shared
        # ``demo-default`` subject.  Explicit demo subjects continue through
        # the same stable pseudonymous binding path as real campus identities.
        if (
            campus_subject == "demo-default"
            and original.account_status == "active"
            and original.netid_hash is not None
        ):
            user = original
            user.verified_at = user.verified_at or utcnow()
            _ensure_authenticated_trust_floor(db, user.id)
        else:
            user, _ = _bind_campus_identity(db, session, campus_subject)
        user.display_name = user.display_name or "中大同学"
        user.college = user.college or "软件工程学院"
        user.major = user.major or "软件工程"
        user.grade_year = user.grade_year or 2024
        user.campus = user.campus or "珠海校区"
        session.status = LoginStatus.SUCCESS.value
        session.error_category = None
        _mark_login_subsystems(db, user.id, fake=True)
        db.commit()
        db.refresh(session)
        return session


def mark_login_waiting(db: Session, session_id: str, *, qr_image_data_url: str) -> LoginSession:
    session = db.get(LoginSession, session_id)
    if session is None:
        raise NotFoundError("登录会话", session_id)
    if session.status != LoginStatus.PENDING.value:
        return session
    session.qr_image_data_url = qr_image_data_url
    session.deep_link = f"onemore://auth/scan/{session.id}"
    session.status = LoginStatus.WAITING_SCAN.value
    db.commit()
    return session


def bind_real_login_identity(
    db: Session, session_id: str, subject_identifier: str
) -> tuple[LoginSession, str | None]:
    session = db.get(LoginSession, session_id)
    if session is None:
        raise NotFoundError("登录会话", session_id)
    _expire_login_if_needed(db, session)
    if session.status in {LoginStatus.CANCELLED.value, LoginStatus.TIMEOUT.value}:
        return session, None
    subject_hash = campus_identity_hash(subject_identifier)
    with identity_locks.acquire(subject_hash):
        # Re-read inside the distributed subject lock.  This serializes two
        # successful scans of the same campus identity across workers.
        db.expire_all()
        session = db.get(LoginSession, session_id)
        if session is None:
            raise NotFoundError("登录会话", session_id)
        _, provisional_to_purge = _bind_campus_identity(
            db, session, subject_identifier
        )
        # Keep the session non-redeemable until the orchestrator has encrypted
        # the authenticated CLI state into the stable account's vault.
        session.error_category = None
        db.commit()
        db.refresh(session)
        return session, provisional_to_purge


def finalize_real_login(db: Session, session_id: str) -> LoginSession:
    session = db.get(LoginSession, session_id)
    if session is None:
        raise NotFoundError("登录会话", session_id)
    _expire_login_if_needed(db, session)
    if session.status in {
        LoginStatus.CANCELLED.value,
        LoginStatus.TIMEOUT.value,
        LoginStatus.FAILED.value,
    }:
        return session
    user = db.get(User, session.user_id)
    if user is None or user.netid_hash is None:
        raise AppError("CAMPUS_IDENTITY_UNBOUND", "校园身份尚未完成绑定", 409)
    _mark_login_subsystems(db, user.id, fake=False)
    session.status = LoginStatus.SUCCESS.value
    session.error_category = None
    db.commit()
    db.refresh(session)
    return session


def mark_login_terminal(
    db: Session, session_id: str, status: str, error_category: str | None = None
) -> LoginSession | None:
    session = db.get(LoginSession, session_id)
    if session is None or session.status in {
        LoginStatus.SUCCESS.value,
        LoginStatus.CANCELLED.value,
    }:
        return session
    session.status = status
    session.error_category = error_category
    db.commit()
    return session


def cancel_login_session(
    db: Session,
    session_id: str,
    redemption_token: str,
    user_id: str | None = None,
) -> LoginSession:
    session = db.get(LoginSession, session_id)
    if session is None:
        raise NotFoundError("登录会话", session_id)
    if user_id is not None and session.user_id != user_id:
        raise NotFoundError("登录会话", session_id)
    _validate_redemption_token(session, redemption_token)
    _expire_login_if_needed(db, session)
    if session.redeemed_at is not None:
        raise ConflictError("LOGIN_ALREADY_REDEEMED", "登录凭证已经兑换")
    if session.status not in {
        LoginStatus.CANCELLED.value,
        LoginStatus.TIMEOUT.value,
        LoginStatus.FAILED.value,
    }:
        session.status = LoginStatus.CANCELLED.value
        session.error_category = None
        db.commit()
    return session


def get_login_session(db: Session, session_id: str, redemption_token: str) -> LoginSession:
    session = db.get(LoginSession, session_id)
    if session is None:
        raise NotFoundError("登录会话", session_id)
    _validate_redemption_token(session, redemption_token)
    _expire_login_if_needed(db, session)
    return session


def redeem_login_session(
    db: Session,
    session_id: str,
    redemption_token: str,
    operation_key: str,
) -> str:
    session = db.get(LoginSession, session_id)
    if session is None:
        raise NotFoundError("登录会话", session_id)
    _validate_redemption_token(session, redemption_token)
    operation_hash = hashlib.sha256(operation_key.encode()).hexdigest()
    if session.redeemed_at is not None:
        if (
            session.redemption_operation_hash == operation_hash
            and session.redemption_response_ciphertext is not None
        ):
            return _decrypt_login_response(
                session.redemption_response_ciphertext, session.id, operation_hash
            )
        raise ConflictError("LOGIN_ALREADY_REDEEMED", "登录凭证已经兑换")
    _expire_login_if_needed(db, session)
    if session.status == LoginStatus.TIMEOUT.value:
        raise AppError("LOGIN_SESSION_EXPIRED", "登录会话已过期", 410)
    if session.status == LoginStatus.CANCELLED.value:
        raise ConflictError("LOGIN_SESSION_CANCELLED", "登录会话已取消")
    if session.status != LoginStatus.SUCCESS.value:
        raise ConflictError("LOGIN_NOT_READY", "登录认证尚未完成")
    now = datetime.now(UTC)
    access_token = issue_access_token(session.user_id)
    encrypted_response = _encrypt_login_response(access_token, session_id, operation_hash)
    updated = cast(
        CursorResult[Any],
        db.execute(
            update(LoginSession)
            .where(
                LoginSession.id == session_id,
                LoginSession.status == LoginStatus.SUCCESS.value,
                LoginSession.redeemed_at.is_(None),
                LoginSession.expires_at >= now,
                LoginSession.redemption_token_hash
                == hashlib.sha256(redemption_token.encode()).hexdigest(),
            )
            .values(
                redeemed_at=now,
                redemption_operation_hash=operation_hash,
                redemption_response_ciphertext=encrypted_response,
            )
            .execution_options(synchronize_session=False)
        ),
    )
    if updated.rowcount != 1:
        db.rollback()
        current = db.get(LoginSession, session_id)
        if current is not None:
            db.refresh(current)
            _validate_redemption_token(current, redemption_token)
            if (
                current.redemption_operation_hash == operation_hash
                and current.redemption_response_ciphertext is not None
            ):
                return _decrypt_login_response(
                    current.redemption_response_ciphertext,
                    current.id,
                    operation_hash,
                )
        raise ConflictError("LOGIN_ALREADY_REDEEMED", "登录凭证已经兑换")
    db.commit()
    return access_token


def change_grant(db: Session, user_id: str, scope: str, granted: bool) -> AuthorizationGrant:
    grant = db.scalar(
        select(AuthorizationGrant).where(
            AuthorizationGrant.user_id == user_id, AuthorizationGrant.scope == scope
        )
    )
    if grant is None:
        grant = AuthorizationGrant(user_id=user_id, scope=scope)
        db.add(grant)
    grant.granted = granted
    now = utcnow()
    if granted:
        grant.granted_at = now
        grant.revoked_at = None
    else:
        grant.revoked_at = now
        cascade_purge(db, user_id, scope)
    vault_manager.set_grant(user_id, scope, granted)
    db.commit()
    db.refresh(grant)
    return grant


def cascade_purge(db: Session, user_id: str, scope: str) -> None:
    if scope == GrantScope.TIMETABLE.value:
        db.execute(delete(TimeWindow).where(TimeWindow.user_id == user_id))
        db.execute(
            update(IntentCard)
            .where(
                IntentCard.user_id == user_id,
                IntentCard.status == IntentStatus.POOLING.value,
            )
            .values(status=IntentStatus.WITHDRAWN.value)
        )
    elif scope == GrantScope.ENROLLMENT.value:
        db.execute(delete(Enrollment).where(Enrollment.user_id == user_id))
        profile = db.get(Profile, user_id)
        if profile:
            profile.verified_tags = []
            profile.capability_vector = {
                key: value
                for key, value in profile.capability_vector.items()
                if key in profile.self_reported_tags
            }
    elif scope == GrantScope.CURRICULUM.value:
        profile = db.get(Profile, user_id)
        if profile:
            profile.cross_major_score = 0.0
            profile.interest_domains = []
    elif scope == GrantScope.AGENT_BOOKING.value:
        db.execute(
            update(CampusAction)
            .where(
                CampusAction.user_id == user_id,
                CampusAction.status == ActionStatus.PREVIEWED.value,
            )
            .values(status=ActionStatus.INVALIDATED.value)
        )


def identity_facts(db: Session, user_id: str) -> tuple[User, list, list]:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("用户", user_id)
    grants = list(
        db.scalars(
            select(AuthorizationGrant)
            .where(AuthorizationGrant.user_id == user_id)
            .order_by(AuthorizationGrant.scope)
        )
    )
    health = list(
        db.scalars(
            select(SessionHealth)
            .where(SessionHealth.user_id == user_id)
            .order_by(SessionHealth.subsystem)
        )
    )
    return user, grants, health


def social_preferences(user: User) -> dict[str, Any]:
    return {
        "social_enabled": user.social_enabled,
        "course_matching_enabled": user.course_matching_enabled,
        "identity_disclosure": user.identity_disclosure,
        "same_gender_only": user.same_gender_only,
        "minimum_group_size": user.minimum_group_size,
        "scene_sensitive_policy": "mute_onsite",
    }


MATCHING_PREFERENCE_DEFAULTS = {
    "interaction_style": "balanced",
    "sport_level": "casual",
    "study_intensity": "balanced",
}


def matching_preferences(user: User) -> dict[str, str]:
    return {**MATCHING_PREFERENCE_DEFAULTS, **(user.matching_preferences or {})}


def update_matching_preferences(
    db: Session, user: User, changes: dict[str, str]
) -> dict[str, str]:
    value = matching_preferences(user)
    value.update(changes)
    user.matching_preferences = value
    db.commit()
    db.refresh(user)
    return matching_preferences(user)


def update_social_preferences(
    db: Session, user: User, changes: dict[str, Any]
) -> dict[str, Any]:
    old_minimum = user.minimum_group_size
    disables_social = changes.get("social_enabled") is False and user.social_enabled
    disables_course_matching = (
        changes.get("course_matching_enabled") is False
        and user.course_matching_enabled
    )
    raises_minimum = int(changes.get("minimum_group_size", old_minimum)) > old_minimum
    tightens_same_gender = (
        changes.get("same_gender_only") is True and not user.same_gender_only
    )
    for key, value in changes.items():
        setattr(user, key, value)
    db.commit()

    # A user who opts out, or raises their minimum above an already-open pool,
    # must not be matched from stale state.  Persist the preference first so
    # matching's locked recheck fails closed, then leave only pre-confirmation
    # groups; confirmed commitments remain intact.
    if disables_social or raises_minimum or tightens_same_gender:
        gathering_ids = list(
            db.scalars(
                select(GatheringMember.gathering_id)
                .join(Gathering, Gathering.id == GatheringMember.gathering_id)
                .where(
                    GatheringMember.user_id == user.id,
                    GatheringMember.left_at.is_(None),
                    Gathering.status.in_(
                        [
                            GatheringStatus.POOLING.value,
                            GatheringStatus.TENTATIVE.value,
                        ]
                    ),
                )
            )
        )
        from onemore.modules.gathering import service as gathering_service

        for gathering_id in gathering_ids:
            if tightens_same_gender and not disables_social and not raises_minimum:
                active_user_ids = list(
                    db.scalars(
                        select(GatheringMember.user_id).where(
                            GatheringMember.gathering_id == gathering_id,
                            GatheringMember.left_at.is_(None),
                        )
                    )
                )
                active_users = [db.get(User, item) for item in active_user_ids]
                genders = {
                    (item.gender_code or "").strip().lower()
                    for item in active_users
                    if item is not None
                }
                # A same-gender preference can stay in a pre-confirmation group
                # only when every current member has the same explicit gender.
                if (
                    len(active_users) == len(active_user_ids)
                    and len(genders) == 1
                    and not genders.intersection({"", "unknown", "unspecified"})
                ):
                    continue
            try:
                gathering_service.leave(
                    db,
                    gathering_id,
                    user.id,
                    reason="privacy_preference_changed",
                )
            except AppError:
                db.rollback()

        db.execute(
            update(IntentCard)
            .where(
                IntentCard.user_id == user.id,
                IntentCard.status == IntentStatus.POOLING.value,
            )
            .values(status=IntentStatus.WITHDRAWN.value)
        )

    if raises_minimum:
        minimum = int(changes["minimum_group_size"])
        draft_cards = list(
            db.scalars(
                select(IntentCard).where(
                    IntentCard.user_id == user.id,
                    IntentCard.status.in_(
                        [
                            IntentStatus.DRAFT.value,
                            IntentStatus.NEEDS_CLARIFICATION.value,
                        ]
                    ),
                )
            )
        )
        for card in draft_cards:
            card.min_size = max(card.min_size, minimum)
            card.target_size = max(card.target_size, minimum)
    if disables_course_matching:
        cards = list(
            db.scalars(
                select(IntentCard).where(
                    IntentCard.user_id == user.id,
                    IntentCard.status.in_(
                        [
                            IntentStatus.DRAFT.value,
                            IntentStatus.NEEDS_CLARIFICATION.value,
                            IntentStatus.POOLING.value,
                        ]
                    ),
                )
            )
        )
        for card in cards:
            card.capabilities = [
                item
                for item in card.capabilities
                if item.get("source") != "verified"
            ]
    db.commit()
    db.refresh(user)
    return social_preferences(user)
