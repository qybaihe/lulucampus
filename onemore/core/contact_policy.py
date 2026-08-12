from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from onemore.db.models import ChannelParticipant, UserBlock


def users_have_block_between(db: Session, user_a: str, user_b: str) -> bool:
    """Return whether either account has blocked the other.

    A block is deliberately symmetric at every contact boundary even though the
    row records who initiated it.  This keeps message, media, websocket and push
    authorization on one policy instead of relying on UI filtering.
    """

    if user_a == user_b:
        return False
    return (
        db.scalar(
            select(UserBlock.id).where(
                or_(
                    (UserBlock.blocker_id == user_a) & (UserBlock.blocked_id == user_b),
                    (UserBlock.blocker_id == user_b) & (UserBlock.blocked_id == user_a),
                )
            )
        )
        is not None
    )


def channel_has_blocked_peer(db: Session, channel_id: str, user_id: str) -> bool:
    peer_ids = list(
        db.scalars(
            select(ChannelParticipant.user_id).where(
                ChannelParticipant.channel_id == channel_id,
                ChannelParticipant.user_id != user_id,
            )
        )
    )
    return any(users_have_block_between(db, user_id, peer_id) for peer_id in peer_ids)
