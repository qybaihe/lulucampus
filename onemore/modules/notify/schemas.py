from __future__ import annotations

from datetime import datetime

from pydantic import Field, computed_field

from onemore.core.schemas import APIModel

DEFAULT_NOTIFICATION_CATEGORY = "gathering_updates"

CATEGORY_BY_TYPE: dict[str, str] = {
    "chat_message": "chat_messages",
    "trust_level_changed": "trust_updates",
    "competition_deadline": "competition_deadlines",
    "execution_succeeded": "action_updates",
    "authorization_required": "action_updates",
    "reauthorization_required": "action_updates",
    "action_modification_requested": "action_updates",
    "calendar_revoked": "action_updates",
    "schedule_reminder": "schedule_reminders",
    "assignment_reminder": "schedule_reminders",
    "confirmation_required": "gathering_updates",
    "gathering_reminder": "gathering_updates",
    "backfill_invitation": "gathering_updates",
    "silent_dissolution": "gathering_updates",
    "completion_confirmation": "gathering_updates",
    "gathering_rescheduled": "gathering_updates",
    "reschedule_vote_required": "gathering_updates",
    "reschedule_vote_rejected": "gathering_updates",
    "relation_ready": "gathering_updates",
    "shared_goal_peer_support": "gathering_updates",
}

NOTIFICATION_TITLES: dict[str, str] = {
    "schedule_reminder": "课表快到了",
    "assignment_reminder": "作业临近",
    "gathering_reminder": "成局提醒",
    "confirmation_required": "待你确认",
    "authorization_required": "需要授权",
    "execution_succeeded": "行动完成",
    "backfill_invitation": "补位邀请",
    "silent_dissolution": "未能成局",
    "reauthorization_required": "需要重新认证",
    "trust_level_changed": "信任更新",
    "chat_message": "新消息",
    "calendar_revoked": "日历已撤销",
    "competition_deadline": "赛事截止",
    "completion_confirmation": "确认完成",
    "gathering_rescheduled": "时间调整",
    "reschedule_vote_required": "改约待确认",
    "reschedule_vote_rejected": "改约未通过",
    "action_modification_requested": "预览需调整",
    "relation_ready": "搭子关系",
    "shared_goal_peer_support": "共同目标",
}

NOTIFICATION_CATEGORIES = (
    "gathering_updates",
    "action_updates",
    "chat_messages",
    "trust_updates",
    "competition_deadlines",
    "schedule_reminders",
)


def category_for_type(notification_type: str) -> str:
    return CATEGORY_BY_TYPE.get(notification_type, DEFAULT_NOTIFICATION_CATEGORY)


def notification_title(notification_type: str) -> str:
    return NOTIFICATION_TITLES.get(notification_type, "提醒")


class DeviceRegister(APIModel):
    token: str = Field(min_length=16, max_length=512)
    platform: str = Field(default="ios", pattern="^ios$")


class DeviceDeactivate(APIModel):
    token: str = Field(min_length=16, max_length=512)


class DeviceInstallationDeactivate(DeviceDeactivate):
    deactivation_token: str = Field(min_length=32, max_length=2048)


class NotificationView(APIModel):
    id: str
    type: str
    payload: dict
    created_at: datetime
    delivered_at: datetime | None

    @computed_field
    @property
    def category(self) -> str:
        return category_for_type(self.type)

    @computed_field
    @property
    def title(self) -> str:
        return notification_title(self.type)


class NotificationCategories(APIModel):
    gathering_updates: bool = True
    action_updates: bool = True
    chat_messages: bool = True
    trust_updates: bool = True
    competition_deadlines: bool = True
    schedule_reminders: bool = True


class NotificationCategoriesPatch(APIModel):
    gathering_updates: bool | None = None
    action_updates: bool | None = None
    chat_messages: bool | None = None
    trust_updates: bool | None = None
    competition_deadlines: bool | None = None
    schedule_reminders: bool | None = None


class NotificationPreferencesPatch(APIModel):
    overall_enabled: bool | None = None
    calendar_sync_enabled: bool | None = None
    categories: NotificationCategoriesPatch | None = None


class NotificationPreferencesView(APIModel):
    overall_enabled: bool
    calendar_sync_enabled: bool
    categories: NotificationCategories
    system_settings_managed_locally: list[str]
