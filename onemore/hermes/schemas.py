from __future__ import annotations

from datetime import date as Date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ActionName(StrEnum):
    TIMETABLE_FETCH_TERM = "timetable.fetch_term"
    TIMETABLE_TODAY = "timetable.today"
    TIMETABLE_SECTION_TIMES = "timetable.section_times"
    ASSIGNMENT_LIST_UNFINISHED = "assignment.list_unfinished"
    ROOM_AVAILABLE = "room.available"
    ROOM_ROOM_TYPES = "room.room_types"
    ROOM_RESERVE_PREVIEW = "room.reserve_preview"
    ROOM_RESERVE_COMMIT = "room.reserve_commit"
    GYM_AVAILABLE = "gym.available"
    GYM_BOOK_PREVIEW = "gym.book_preview"
    GYM_BOOK_COMMIT = "gym.book_commit"
    SEMINAR_LIST = "seminar.list"
    SEMINAR_RESERVE_PREVIEW = "seminar.reserve_preview"
    SEMINAR_RESERVE_COMMIT = "seminar.reserve_commit"
    CAREER_TEACHIN_LIST = "career.teachin_list"
    CAREER_JOBFAIR_LIST = "career.jobfair_list"
    TRANSIT_BUS = "transit.bus"
    TRANSIT_QIGUAN = "transit.qiguan"


class ActionParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyParams(ActionParams):
    pass


class TimetableFetchParams(ActionParams):
    scan_from: int = Field(default=1, ge=1, le=30)
    scan_to: int = Field(default=25, ge=1, le=30)
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    academic_term: int | None = Field(default=None, ge=1, le=3)

    @model_validator(mode="after")
    def validate_scan_range(self) -> TimetableFetchParams:
        if self.scan_from > self.scan_to:
            raise ValueError("scan_from 必须小于等于 scan_to")
        return self


class RoomTypesParams(ActionParams):
    query: str | None = Field(default=None, max_length=80)


class RoomAvailableParams(ActionParams):
    kind: str = Field(min_length=1, max_length=100)
    date: Date
    lab: str | None = Field(default=None, max_length=100)
    room: str | None = Field(default=None, max_length=100)


class RoomReserveParams(ActionParams):
    kind: str = Field(min_length=1, max_length=100)
    room: str = Field(min_length=1, max_length=100)
    date: Date
    start: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    lab: str | None = Field(default=None, max_length=100)
    members: list[str] = Field(default_factory=list, max_length=20)
    title: str | None = Field(default=None, max_length=80)
    memo: str | None = Field(default=None, max_length=200)
    services: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("members")
    @classmethod
    def validate_members(cls, value: list[str]) -> list[str]:
        for member in value:
            if (
                not member
                or len(member) > 32
                or any(
                    char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                    for char in member
                )
            ):
                raise ValueError("成员标识格式错误")
        return value

    @model_validator(mode="after")
    def validate_time(self) -> RoomReserveParams:
        if self.start >= self.end:
            raise ValueError("预约结束时间必须晚于开始时间")
        return self


class GymAvailableParams(ActionParams):
    venue_type: str = Field(min_length=1, max_length=100)
    date: Date | None = None
    days: int = Field(default=1, ge=1, le=7)
    venue: str | None = Field(default=None, max_length=100)
    include_full: bool = False


class GymBookParams(ActionParams):
    venue_type: str = Field(min_length=1, max_length=100)
    venue: str | None = Field(default=None, max_length=100)
    date: Date
    start: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def validate_time(self) -> GymBookParams:
        if self.start >= self.end:
            raise ValueError("预约结束时间必须晚于开始时间")
        return self


class SeminarListParams(ActionParams):
    kind: Literal["todayHot", "latest", "hot", "like"] = "todayHot"
    keyword: str | None = Field(default=None, max_length=80)
    department: str | None = Field(default=None, max_length=80)
    college: str | None = Field(default=None, max_length=80)
    tag: str | None = Field(default=None, max_length=80)


class SeminarReserveParams(ActionParams):
    seminar_id: str = Field(min_length=1, max_length=128)
    source: Literal["todayHot", "latest", "hot", "like", "calendar", "notice"] = "calendar"


class CareerListParams(ActionParams):
    title: str | None = Field(default=None, max_length=100)
    event_type: str | None = Field(default=None, max_length=16)
    start: Date | None = None
    end: Date | None = None
    limit: int = Field(default=20, ge=1, le=100)


class BusParams(ActionParams):
    day_type: Literal[0, 1] | None = None
    from_campus: str | None = Field(default=None, max_length=80)
    to_campus: str | None = Field(default=None, max_length=80)
    query: str | None = Field(default=None, max_length=80)
    upcoming: bool = False


class QiguanParams(ActionParams):
    start: str | None = Field(default=None, max_length=32)
    to: str | None = Field(default=None, max_length=32)
    station: str | None = Field(default=None, max_length=64)
    date: Date | None = None
    available_only: bool = True


PARAM_MODELS: dict[ActionName, type[ActionParams]] = {
    ActionName.TIMETABLE_FETCH_TERM: TimetableFetchParams,
    ActionName.TIMETABLE_TODAY: EmptyParams,
    ActionName.TIMETABLE_SECTION_TIMES: EmptyParams,
    ActionName.ASSIGNMENT_LIST_UNFINISHED: EmptyParams,
    ActionName.ROOM_AVAILABLE: RoomAvailableParams,
    ActionName.ROOM_ROOM_TYPES: RoomTypesParams,
    ActionName.ROOM_RESERVE_PREVIEW: RoomReserveParams,
    ActionName.ROOM_RESERVE_COMMIT: RoomReserveParams,
    ActionName.GYM_AVAILABLE: GymAvailableParams,
    ActionName.GYM_BOOK_PREVIEW: GymBookParams,
    ActionName.GYM_BOOK_COMMIT: GymBookParams,
    ActionName.SEMINAR_LIST: SeminarListParams,
    ActionName.SEMINAR_RESERVE_PREVIEW: SeminarReserveParams,
    ActionName.SEMINAR_RESERVE_COMMIT: SeminarReserveParams,
    ActionName.CAREER_TEACHIN_LIST: CareerListParams,
    ActionName.CAREER_JOBFAIR_LIST: CareerListParams,
    ActionName.TRANSIT_BUS: BusParams,
    ActionName.TRANSIT_QIGUAN: QiguanParams,
}


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ActionName
    user_id: str
    params: dict[str, Any]
    gathering_id: str | None = None
    confirm: bool = False
    idempotency_key: str = Field(min_length=8, max_length=128)

    def validated_params(self) -> ActionParams:
        return PARAM_MODELS[self.action].model_validate(self.params)


class HermesResult(BaseModel):
    action: ActionName
    ok: bool
    data: Any = None
    error_category: str | None = None
    cached: bool = False
