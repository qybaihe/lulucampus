from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from onemore.hermes.schemas import (
    ActionName,
    ActionParams,
    BusParams,
    CareerListParams,
    EmptyParams,
    GymAvailableParams,
    GymBookParams,
    QiguanParams,
    RoomAvailableParams,
    RoomReserveParams,
    RoomTypesParams,
    SeminarListParams,
    SeminarReserveParams,
    TimetableFetchParams,
)


class ActionTier(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"


@dataclass(frozen=True, slots=True)
class ActionDefinition:
    name: ActionName
    tier: ActionTier
    subsystem: str
    required_grant: str | None
    required_trust_level: str
    is_write: bool
    supports_state_dir: bool
    params_type: type[ActionParams]
    argv_builder: Callable[[ActionParams, bool], list[str]]


def _optional(argv: list[str], flag: str, value: object | None) -> None:
    if value is not None and value != "":
        argv.extend([flag, str(value)])


def timetable_fetch(p: ActionParams, _: bool) -> list[str]:
    params = TimetableFetchParams.model_validate(p.model_dump())
    argv = [
        "jwxt",
        "timetable",
        "--scan-from",
        str(params.scan_from),
        "--scan-to",
        str(params.scan_to),
    ]
    _optional(argv, "--academic-year", params.academic_year)
    _optional(argv, "--academic-term", params.academic_term)
    return argv + ["--json"]


def room_types(p: ActionParams, _: bool) -> list[str]:
    params = RoomTypesParams.model_validate(p.model_dump())
    argv = ["libic", "room-types"]
    _optional(argv, "--query", params.query)
    return argv + ["--json"]


def room_available(p: ActionParams, _: bool) -> list[str]:
    params = RoomAvailableParams.model_validate(p.model_dump())
    argv = ["libic", "available", "--kind", params.kind, "--date", params.date.isoformat()]
    _optional(argv, "--lab", params.lab)
    _optional(argv, "--room", params.room)
    return argv + ["--json"]


def room_reserve(p: ActionParams, confirm: bool) -> list[str]:
    params = RoomReserveParams.model_validate(p.model_dump())
    argv = [
        "libic",
        "reserve",
        "--kind",
        params.kind,
        "--room",
        params.room,
        "--date",
        params.date.isoformat(),
        "--start",
        params.start,
        "--end",
        params.end,
    ]
    _optional(argv, "--lab", params.lab)
    if params.members:
        argv.extend(["--members", ",".join(params.members)])
    _optional(argv, "--title", params.title)
    _optional(argv, "--memo", params.memo)
    if params.services:
        argv.extend(["--services", ",".join(params.services)])
    if confirm:
        argv.append("--confirm")
    return argv + ["--json"]


def gym_available(p: ActionParams, _: bool) -> list[str]:
    params = GymAvailableParams.model_validate(p.model_dump())
    argv = ["gym", "available", "--venue-type", params.venue_type, "--days", str(params.days)]
    _optional(argv, "--date", params.date.isoformat() if params.date else None)
    _optional(argv, "--venue", params.venue)
    if params.include_full:
        argv.append("--include-full")
    return argv + ["--json"]


def gym_book(p: ActionParams, confirm: bool) -> list[str]:
    params = GymBookParams.model_validate(p.model_dump())
    argv = [
        "gym",
        "book",
        "--venue-type",
        params.venue_type,
        "--date",
        params.date.isoformat(),
        "--start",
        params.start,
        "--end",
        params.end,
    ]
    _optional(argv, "--venue", params.venue)
    if confirm:
        argv.append("--confirm")
    return argv + ["--json"]


def seminar_list(p: ActionParams, _: bool) -> list[str]:
    params = SeminarListParams.model_validate(p.model_dump())
    argv = ["explore", "seminar", "list", "--kind", params.kind]
    _optional(argv, "--keyword", params.keyword)
    _optional(argv, "--dept", params.department)
    _optional(argv, "--college", params.college)
    _optional(argv, "--tag", params.tag)
    return argv + ["--json"]


def seminar_reserve(p: ActionParams, confirm: bool) -> list[str]:
    params = SeminarReserveParams.model_validate(p.model_dump())
    argv = ["explore", "seminar", "reserve", "--id", params.seminar_id, "--source", params.source]
    if confirm:
        argv.append("--confirm")
    return argv + ["--json"]


def career_list(kind: str) -> Callable[[ActionParams, bool], list[str]]:
    def builder(p: ActionParams, _: bool) -> list[str]:
        params = CareerListParams.model_validate(p.model_dump())
        argv = ["career", kind, "list", "--limit", str(params.limit)]
        _optional(argv, "--title", params.title)
        _optional(argv, "--type", params.event_type)
        _optional(argv, "--start", params.start.isoformat() if params.start else None)
        _optional(argv, "--end", params.end.isoformat() if params.end else None)
        return argv + ["--json"]

    return builder


def bus(p: ActionParams, _: bool) -> list[str]:
    params = BusParams.model_validate(p.model_dump())
    argv = ["bus"]
    _optional(argv, "--bus", params.day_type)
    _optional(argv, "--from", params.from_campus)
    _optional(argv, "--to", params.to_campus)
    _optional(argv, "--query", params.query)
    if params.upcoming:
        argv.append("--upcoming")
    return argv + ["--json"]


def qiguan(p: ActionParams, _: bool) -> list[str]:
    params = QiguanParams.model_validate(p.model_dump())
    argv = ["qg", "list"]
    _optional(argv, "--start", params.start)
    _optional(argv, "--to", params.to)
    _optional(argv, "--station", params.station)
    if params.date:
        argv.extend(["--date", params.date.isoformat()])
    else:
        argv.append("--today")
    if params.available_only:
        argv.append("--available")
    return argv + ["--json"]


CATALOG: dict[ActionName, ActionDefinition] = {
    ActionName.TIMETABLE_FETCH_TERM: ActionDefinition(
        ActionName.TIMETABLE_FETCH_TERM,
        ActionTier.GREEN,
        "jwxt",
        "timetable",
        "T1",
        False,
        True,
        TimetableFetchParams,
        timetable_fetch,
    ),
    ActionName.TIMETABLE_TODAY: ActionDefinition(
        ActionName.TIMETABLE_TODAY,
        ActionTier.GREEN,
        "jwxt",
        "timetable",
        "T1",
        False,
        True,
        EmptyParams,
        lambda p, c: ["today", "--json"],
    ),
    ActionName.TIMETABLE_SECTION_TIMES: ActionDefinition(
        ActionName.TIMETABLE_SECTION_TIMES,
        ActionTier.GREEN,
        "jwxt",
        "timetable",
        "T1",
        False,
        True,
        EmptyParams,
        lambda p, c: ["jwxt", "section-times", "--json"],
    ),
    ActionName.ASSIGNMENT_LIST_UNFINISHED: ActionDefinition(
        ActionName.ASSIGNMENT_LIST_UNFINISHED,
        ActionTier.GREEN,
        "matrix",
        "enrollment",
        "T1",
        False,
        False,
        EmptyParams,
        lambda p, c: ["matrix", "assignments", "list", "--unfinished", "--json"],
    ),
    ActionName.ROOM_AVAILABLE: ActionDefinition(
        ActionName.ROOM_AVAILABLE,
        ActionTier.GREEN,
        "libic",
        "timetable",
        "T1",
        False,
        True,
        RoomAvailableParams,
        room_available,
    ),
    ActionName.ROOM_ROOM_TYPES: ActionDefinition(
        ActionName.ROOM_ROOM_TYPES,
        ActionTier.GREEN,
        "libic",
        None,
        "T0",
        False,
        True,
        RoomTypesParams,
        room_types,
    ),
    ActionName.ROOM_RESERVE_PREVIEW: ActionDefinition(
        ActionName.ROOM_RESERVE_PREVIEW,
        ActionTier.YELLOW,
        "libic",
        "agent_booking",
        "T2",
        True,
        True,
        RoomReserveParams,
        room_reserve,
    ),
    ActionName.ROOM_RESERVE_COMMIT: ActionDefinition(
        ActionName.ROOM_RESERVE_COMMIT,
        ActionTier.YELLOW,
        "libic",
        "agent_booking",
        "T2",
        True,
        True,
        RoomReserveParams,
        room_reserve,
    ),
    ActionName.GYM_AVAILABLE: ActionDefinition(
        ActionName.GYM_AVAILABLE,
        ActionTier.GREEN,
        "gym",
        "timetable",
        "T1",
        False,
        True,
        GymAvailableParams,
        gym_available,
    ),
    ActionName.GYM_BOOK_PREVIEW: ActionDefinition(
        ActionName.GYM_BOOK_PREVIEW,
        ActionTier.YELLOW,
        "gym",
        "agent_booking",
        "T2",
        True,
        True,
        GymBookParams,
        gym_book,
    ),
    ActionName.GYM_BOOK_COMMIT: ActionDefinition(
        ActionName.GYM_BOOK_COMMIT,
        ActionTier.YELLOW,
        "gym",
        "agent_booking",
        "T2",
        True,
        True,
        GymBookParams,
        gym_book,
    ),
    ActionName.SEMINAR_LIST: ActionDefinition(
        ActionName.SEMINAR_LIST,
        ActionTier.GREEN,
        "explore",
        None,
        "T0",
        False,
        True,
        SeminarListParams,
        seminar_list,
    ),
    ActionName.SEMINAR_RESERVE_PREVIEW: ActionDefinition(
        ActionName.SEMINAR_RESERVE_PREVIEW,
        ActionTier.YELLOW,
        "explore",
        "agent_booking",
        "T2",
        True,
        True,
        SeminarReserveParams,
        seminar_reserve,
    ),
    ActionName.SEMINAR_RESERVE_COMMIT: ActionDefinition(
        ActionName.SEMINAR_RESERVE_COMMIT,
        ActionTier.YELLOW,
        "explore",
        "agent_booking",
        "T2",
        True,
        True,
        SeminarReserveParams,
        seminar_reserve,
    ),
    ActionName.CAREER_TEACHIN_LIST: ActionDefinition(
        ActionName.CAREER_TEACHIN_LIST,
        ActionTier.GREEN,
        "career",
        None,
        "T0",
        False,
        False,
        CareerListParams,
        career_list("teachin"),
    ),
    ActionName.CAREER_JOBFAIR_LIST: ActionDefinition(
        ActionName.CAREER_JOBFAIR_LIST,
        ActionTier.GREEN,
        "career",
        None,
        "T0",
        False,
        False,
        CareerListParams,
        career_list("jobfair"),
    ),
    ActionName.TRANSIT_BUS: ActionDefinition(
        ActionName.TRANSIT_BUS,
        ActionTier.GREEN,
        "transit",
        None,
        "T0",
        False,
        False,
        BusParams,
        bus,
    ),
    ActionName.TRANSIT_QIGUAN: ActionDefinition(
        ActionName.TRANSIT_QIGUAN,
        ActionTier.GREEN,
        "transit",
        None,
        "T0",
        False,
        False,
        QiguanParams,
        qiguan,
    ),
}


COMMIT_FOR_PREVIEW = {
    ActionName.ROOM_RESERVE_PREVIEW: ActionName.ROOM_RESERVE_COMMIT,
    ActionName.GYM_BOOK_PREVIEW: ActionName.GYM_BOOK_COMMIT,
    ActionName.SEMINAR_RESERVE_PREVIEW: ActionName.SEMINAR_RESERVE_COMMIT,
}


def build_argv(
    action: ActionName, params: ActionParams, *, server_confirmed: bool = False
) -> list[str]:
    definition = CATALOG[action]
    confirm = server_confirmed and action in {
        ActionName.ROOM_RESERVE_COMMIT,
        ActionName.GYM_BOOK_COMMIT,
        ActionName.SEMINAR_RESERVE_COMMIT,
    }
    return definition.argv_builder(params, confirm)
