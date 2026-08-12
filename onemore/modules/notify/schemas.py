from __future__ import annotations

from datetime import datetime

from pydantic import Field

from onemore.core.schemas import APIModel


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


class NotificationCategories(APIModel):
    gathering_updates: bool = True
    action_updates: bool = True
    chat_messages: bool = True
    trust_updates: bool = True
    competition_deadlines: bool = True


class NotificationCategoriesPatch(APIModel):
    gathering_updates: bool | None = None
    action_updates: bool | None = None
    chat_messages: bool | None = None
    trust_updates: bool | None = None
    competition_deadlines: bool | None = None


class NotificationPreferencesPatch(APIModel):
    overall_enabled: bool | None = None
    calendar_sync_enabled: bool | None = None
    categories: NotificationCategoriesPatch | None = None


class NotificationPreferencesView(APIModel):
    overall_enabled: bool
    calendar_sync_enabled: bool
    categories: NotificationCategories
    system_settings_managed_locally: list[str]
