from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.contact_policy import channel_has_blocked_peer, users_have_block_between
from onemore.core.errors import AppError, ForbiddenError, NotFoundError
from onemore.db.models import (
    Channel,
    ChannelParticipant,
    ChannelStatus,
    GatheringMember,
    MediaAsset,
    MediaChannelGrant,
    Relation,
    RelationStatus,
)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ("jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": ("png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/heic": ("heic", lambda data: len(data) > 12 and data[4:8] == b"ftyp"),
    "image/heif": ("heif", lambda data: len(data) > 12 and data[4:8] == b"ftyp"),
}


def asset_view(asset: MediaAsset) -> dict:
    return {
        "media_id": asset.id,
        "url": f"/media/images/{asset.id}",
        "content_type": asset.content_type,
        "byte_count": asset.byte_count,
        "sha256": asset.sha256,
        "width": asset.width,
        "height": asset.height,
    }


def store_image(
    db: Session,
    user_id: str,
    payload: bytes,
    content_type: str,
    filename: str,
    width: int | None,
    height: int | None,
) -> MediaAsset:
    settings = get_settings()
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    spec = ALLOWED_IMAGE_TYPES.get(normalized_type)
    if spec is None:
        raise AppError("UNSUPPORTED_IMAGE_TYPE", "仅支持 JPEG、PNG、HEIC 或 HEIF 图片", 415)
    if not payload or len(payload) > settings.media_max_image_bytes:
        raise AppError(
            "IMAGE_SIZE_INVALID",
            f"图片大小必须在 1 到 {settings.media_max_image_bytes} 字节之间",
            413,
        )
    if not spec[1](payload):
        raise AppError("IMAGE_SIGNATURE_INVALID", "图片内容与 Content-Type 不一致", 422)
    if width is not None and not 1 <= width <= 20000:
        raise AppError("IMAGE_DIMENSION_INVALID", "图片宽度超出范围", 422)
    if height is not None and not 1 <= height <= 20000:
        raise AppError("IMAGE_DIMENSION_INVALID", "图片高度超出范围", 422)

    digest = hashlib.sha256(payload).hexdigest()
    existing = db.scalar(
        select(MediaAsset).where(
            MediaAsset.owner_user_id == user_id,
            MediaAsset.sha256 == digest,
        )
    )
    if existing is not None:
        return existing

    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(filename).stem).strip(".-") or "image"
    original_filename = f"{safe_stem[:180]}.{spec[0]}"
    asset = MediaAsset(
        owner_user_id=user_id,
        content_type=normalized_type,
        original_filename=original_filename,
        storage_path="pending",
        byte_count=len(payload),
        sha256=digest,
        width=width,
        height=height,
    )
    db.add(asset)
    db.flush()

    root = settings.media_root.resolve()
    user_root = root / user_id
    user_root.mkdir(parents=True, exist_ok=True)
    destination = user_root / f"{asset.id}.{spec[0]}"
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, destination)
    asset.storage_path = str(destination)
    db.commit()
    db.refresh(asset)
    return asset


def get_authorized_asset(db: Session, asset_id: str, user_id: str) -> MediaAsset:
    asset = db.get(MediaAsset, asset_id)
    if asset is None:
        raise NotFoundError("图片", asset_id)
    if asset.owner_user_id != user_id:
        candidate_channels = list(
            db.scalars(
            select(Channel)
            .join(MediaChannelGrant, MediaChannelGrant.channel_id == Channel.id)
            .join(
                ChannelParticipant,
                ChannelParticipant.channel_id == Channel.id,
            )
            .where(
                MediaChannelGrant.media_id == asset_id,
                ChannelParticipant.user_id == user_id,
                Channel.status == ChannelStatus.OPEN.value,
            )
            )
        )
        permitted = False
        for channel in candidate_channels:
            if channel.gathering_id is not None:
                active_member = db.scalar(
                    select(GatheringMember.id).where(
                        GatheringMember.gathering_id == channel.gathering_id,
                        GatheringMember.user_id == user_id,
                        GatheringMember.left_at.is_(None),
                    )
                )
                if (
                    active_member is not None
                    and not channel_has_blocked_peer(db, channel.id, user_id)
                    and not users_have_block_between(db, user_id, asset.owner_user_id)
                ):
                    permitted = True
                    break
            elif channel.relation_id is not None:
                relation = db.scalar(
                    select(Relation).where(
                        Relation.id == channel.relation_id,
                        Relation.status == RelationStatus.ACTIVE.value,
                        or_(
                            Relation.participant_a_id == user_id,
                            Relation.participant_b_id == user_id,
                        ),
                    )
                )
                if relation is None:
                    continue
                other_id = (
                    relation.participant_b_id
                    if relation.participant_a_id == user_id
                    else relation.participant_a_id
                )
                if not users_have_block_between(db, user_id, other_id):
                    permitted = True
                    break
        if not permitted:
            raise ForbiddenError("只有发送者和所在会话成员可查看该图片")
    path = Path(asset.storage_path)
    if not path.is_file():
        raise AppError("MEDIA_FILE_MISSING", "图片文件暂不可用", 503)
    return asset
