#!/usr/bin/env python3
"""Validate the versioned SYSU static reference bundle."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path('/Users/baihe/Documents/compusone')
OUT = ROOT / 'data/reference/sysu'
ALLOWED_CONFIDENCE = {'verified', 'partial', 'unverified'}
TIME_RE = re.compile(r'^(?:[01][0-9]|2[0-3]):[0-5][0-9]$')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
FORMAL_JSON = [
    'campuses.v1.json', 'aliases.v1.json', 'places.v1.json', 'venues.v1.json',
    'transit_2026_fall.json', 'academic_calendar_2026_2027.json', 'section_times_2026_fall.json',
]
FORMAL_FILES = FORMAL_JSON + [
    'evidence/source_audit.csv',
    'evidence/cli_inventory.md',
    'evidence/user_confirmed_commute_times_2026-08-11.md',
    'data_gaps.md',
    'completeness_report.md',
]
EXPECTED_BUNDLE_VERSION = 'sysu-campus-reference-v1.1-south-first'
USER_COMMUTE_EVIDENCE = 'evidence/user_confirmed_commute_times_2026-08-11.md'
EXPECTED_USER_TYPICAL_MINUTES = {
    ('guangzhou_south', 'guangzhou_east'): 30,
    ('guangzhou_east', 'zhuhai'): 90,
    ('guangzhou_east', 'shenzhen'): 120,
    ('guangzhou_south', 'zhuhai'): 120,
    ('guangzhou_south', 'shenzhen'): 150,
    ('guangzhou_south', 'guangzhou_north'): 30,
}
EXPECTED_TEACHING_NAMES = {
    'teaching_1': '第一教学楼',
    'teaching_2': '第二教学楼',
    'teaching_3': '第三教学楼',
    'teaching_4': '第四教学楼（丰盛堂）',
    'teaching_5': '第五教学楼（逸夫楼）',
    'teaching_6': '第六教学楼',
}
FORBIDDEN_KEYS = {
    'token', 'cookie', 'session', 'freewindows', 'remain', 'balance', 'studentid',
    'student_id', 'studentname', 'student_name', 'personal_timetable', '个人课表',
    '学号', '姓名', '余额', '余票', 'freewindows', 'booking_result', 'reservation_result',
}

errors: list[str] = []

def fail(message: str) -> None:
    errors.append(message)

def load_json(name: str) -> Any:
    path = OUT / name
    if not path.exists():
        fail(f'missing file: {path}')
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        fail(f'invalid JSON {path}: {exc}')
        return None

def check_confidence(item: Any, context: str) -> None:
    if isinstance(item, dict) and 'confidence' in item and item['confidence'] not in ALLOWED_CONFIDENCE:
        fail(f'{context}: invalid confidence {item.get("confidence")!r}')

def check_sources(item: Any, context: str, required: bool = True) -> None:
    if not isinstance(item, dict):
        return
    refs = item.get('source_refs')
    if required and (not isinstance(refs, list) or not refs):
        fail(f'{context}: source_refs missing or empty')
    check_confidence(item, context)
    if item.get('confidence') == 'verified':
        if not any(isinstance(ref, str) and (ref.startswith('http://') or ref.startswith('https://') or ref.startswith('sysu-anything')) for ref in (refs or [])):
            fail(f'{context}: verified record has no official URL or SysU Anything CLI source')

def check_time(value: Any, context: str) -> None:
    if not isinstance(value, str) or not TIME_RE.fullmatch(value):
        fail(f'{context}: invalid time {value!r}')

def check_date(value: Any, context: str) -> None:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        fail(f'{context}: invalid date {value!r}')

def check_forbidden_keys(value: Any, path: str = '$') -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_norm = str(key).replace('-', '_').lower()
            if key_norm in FORBIDDEN_KEYS:
                fail(f'{path}: forbidden static-data key {key!r}')
            check_forbidden_keys(child, f'{path}.{key}')
    elif isinstance(value, list):
        for i, child in enumerate(value):
            check_forbidden_keys(child, f'{path}[{i}]')


def main() -> int:
    campuses_doc = load_json('campuses.v1.json')
    aliases_doc = load_json('aliases.v1.json')
    places_doc = load_json('places.v1.json')
    venues_doc = load_json('venues.v1.json')
    transit_doc = load_json('transit_2026_fall.json')
    calendar_doc = load_json('academic_calendar_2026_2027.json')
    sections_doc = load_json('section_times_2026_fall.json')
    manifest = load_json('manifest.json')
    if errors:
        return report()

    campuses = campuses_doc.get('campuses', [])
    places = places_doc.get('places', [])
    venues = venues_doc.get('venues', [])
    campus_ids = {item.get('id') for item in campuses}
    place_ids = {item.get('id') for item in places}
    venue_ids = {item.get('id') for item in venues}
    if len(campus_ids) != len(campuses): fail('duplicate campus id')
    if len(place_ids) != len(places): fail('duplicate place id')
    if len(venue_ids) != len(venues): fail('duplicate venue id')
    all_ids = list(campus_ids) + list(place_ids) + list(venue_ids)
    if len(set(all_ids)) != len(all_ids): fail('ID collision across campuses/places/venues')

    for item in campuses:
        context = f'campus:{item.get("id")}'
        check_sources(item, context)
        if item.get('id') not in campus_ids or not item.get('canonical_name'):
            fail(f'{context}: missing id/name')
    for item in places:
        context = f'place:{item.get("id")}'
        check_sources(item, context)
        if item.get('campus_id') not in campus_ids: fail(f'{context}: invalid campus_id')
        if item.get('category') not in {'teaching_building', 'library', 'canteen', 'sports', 'meeting', 'activity_center', 'auditorium', 'gate', 'transit_stop', 'landmark', 'other'}:
            fail(f'{context}: invalid category {item.get("category")!r}')
    place_by_id = {item.get('id'): item for item in places}
    for place_id, expected_name in EXPECTED_TEACHING_NAMES.items():
        actual = place_by_id.get(place_id, {}).get('canonical_name')
        if actual != expected_name:
            fail(f'{place_id}: expected canonical_name {expected_name!r}, got {actual!r}')
    for item in venues:
        context = f'venue:{item.get("id")}'
        check_sources(item, context)
        if item.get('campus_id') not in campus_ids: fail(f'{context}: invalid campus_id')
        if item.get('place_id') not in place_ids: fail(f'{context}: invalid place_id {item.get("place_id")!r}')
        if not item.get('venue_type'): fail(f'{context}: missing venue_type')

    # Campus alias collision check.
    alias_targets: dict[str, set[str]] = {}
    for item in aliases_doc.get('aliases', []):
        alias = str(item.get('alias', '')).strip()
        target = item.get('canonical_id')
        if not alias or target not in campus_ids: fail(f'alias:{alias}: invalid target')
        alias_targets.setdefault(alias, set()).add(target)
        check_sources(item, f'alias:{alias}')
    for alias, targets in alias_targets.items():
        if len(targets) > 1: fail(f'campus alias collision: {alias} -> {sorted(targets)}')

    # Transit references and times.
    bus = transit_doc.get('campus_bus', {})
    for group_name in ('workday_routes', 'holiday_routes'):
        for route in bus.get(group_name, []):
            context = f'transit:{group_name}:{route.get("id")}'
            check_sources(route, context)
            if route.get('from_campus_id') not in campus_ids or route.get('to_campus_id') not in campus_ids:
                fail(f'{context}: invalid route campus')
            for stop in route.get('stops', []):
                if stop.get('place_id') not in place_ids: fail(f'{context}: invalid stop place {stop.get("place_id")!r}')
            for moment in route.get('scheduled_departures', []): check_time(moment.get('time'), f'{context}:departure')
    qg = transit_doc.get('qiguan', {})
    qg_station_ids = {s.get('id') for s in qg.get('stations', [])}
    for station in qg.get('stations', []):
        if station.get('campus_id') not in campus_ids: fail(f'qg station {station.get("id")}: invalid campus')
        if station.get('id') in {None, ''}: fail('qg station missing id')
    for key, station_id in qg.get('station_keys', {}).items():
        if station_id not in qg_station_ids: fail(f'qg station key {key}: missing station {station_id}')
    for route in qg.get('routes', []):
        check_sources(route, f'qg:{route.get("route_key")}')
        if route.get('from_campus_id') not in campus_ids or route.get('to_campus_id') not in campus_ids: fail(f'qg:{route.get("route_key")}: invalid campus')
        for key in ('from_station_id', 'to_station_id'):
            if route.get(key) not in qg_station_ids: fail(f'qg:{route.get("route_key")}: invalid station {route.get(key)!r}')
    matrix = transit_doc.get('campus_commute_matrix', [])
    seen_matrix_pairs: set[tuple[str, str]] = set()
    actual_user_minutes: dict[tuple[str, str], int] = {}
    for item in matrix:
        context = f'matrix:{item.get("from_campus_id")}->{item.get("to_campus_id")}'
        check_sources(item, context)
        if item.get('from_campus_id') not in campus_ids or item.get('to_campus_id') not in campus_ids: fail(f'{context}: invalid campus')
        pair = (item.get('from_campus_id'), item.get('to_campus_id'))
        if pair[0] == pair[1]: fail(f'{context}: same-campus matrix entry')
        if pair in seen_matrix_pairs: fail(f'{context}: duplicate directional pair')
        seen_matrix_pairs.add(pair)
        minutes = item.get('typical_minutes')
        if minutes is not None and (not isinstance(minutes, int) or isinstance(minutes, bool) or not 0 < minutes <= 1440):
            fail(f'{context}: invalid typical_minutes {minutes!r}')
        for key in ('buffer_minutes', 'minimum_safe_gap_minutes'):
            value = item.get(key)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                fail(f'{context}: invalid {key} {value!r}')
        if minutes is not None:
            if item.get('duration_source_type') != 'user_confirmed_typical':
                fail(f'{context}: filled duration missing user_confirmed_typical source type')
            check_date(item.get('duration_verified_at'), f'{context}:duration_verified_at')
            if USER_COMMUTE_EVIDENCE not in item.get('source_refs', []):
                fail(f'{context}: user commute evidence missing')
            actual_user_minutes[pair] = minutes
        elif item.get('duration_source_type') is not None or item.get('duration_verified_at') is not None:
            fail(f'{context}: empty duration must not claim duration provenance')
    if actual_user_minutes != EXPECTED_USER_TYPICAL_MINUTES:
        fail(f'user commute durations mismatch: {actual_user_minutes!r}')

    # Calendar and sections.
    check_sources(calendar_doc, 'calendar')
    for field in ('term_start', 'term_end', 'teaching_week_start'):
        check_date(calendar_doc.get(field), f'calendar:{field}')
    for holiday in calendar_doc.get('holidays', []):
        check_date(holiday.get('start_date'), 'calendar:holiday.start_date')
        check_date(holiday.get('end_date'), 'calendar:holiday.end_date')
    for item in calendar_doc.get('adjusted_workdays', []): check_date(item.get('date'), 'calendar:adjusted_workday')
    for item in calendar_doc.get('breaks', []):
        if item.get('start_date'): check_date(item.get('start_date'), 'calendar:break.start_date')
        if item.get('end_date'): check_date(item.get('end_date'), 'calendar:break.end_date')
    check_sources(sections_doc, 'sections')
    for section in sections_doc.get('sections', []):
        check_sources(section, f'section:{section.get("section_number")}')
        check_time(section.get('start_time'), f'section:{section.get("section_number")}:start')
        check_time(section.get('end_time'), f'section:{section.get("section_number")}:end')
    for item in sections_doc.get('break_windows', []):
        check_time(item.get('start_time'), f'break_window:{item.get("window_key")}:start')
        check_time(item.get('end_time'), f'break_window:{item.get("window_key")}:end')
        check_confidence(item, f'break_window:{item.get("window_key")}')

    # Static-data boundary: check formal JSON keys only.  Evidence markdown
    # explains why dynamic fields are excluded, but is not a runtime dataset.
    for filename in FORMAL_JSON:
        check_forbidden_keys(load_json(filename), filename)

    # CSV shape and source audit coverage.
    audit_path = OUT / 'evidence/source_audit.csv'
    if not audit_path.exists():
        fail(f'missing file: {audit_path}')
    else:
        with audit_path.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        expected = {'dataset', 'record_id', 'field', 'source_type', 'source_url_or_command', 'captured_at', 'confidence', 'note'}
        if not rows: fail('source_audit.csv is empty')
        if set(rows[0]) != expected: fail(f'source_audit.csv headers mismatch: {set(rows[0])}')
        for row in rows:
            if row['confidence'] not in ALLOWED_CONFIDENCE: fail(f'audit row invalid confidence: {row}')
            if not row['source_url_or_command']: fail(f'audit row missing source: {row}')

    # Manifest files and hashes.
    if manifest.get('bundle_version') != EXPECTED_BUNDLE_VERSION:
        fail(f'manifest bundle_version mismatch: {manifest.get("bundle_version")!r}')
    if manifest.get('schema_version') != '1.1.0':
        fail(f'manifest schema_version mismatch: {manifest.get("schema_version")!r}')
    for rel in FORMAL_FILES:
        path = OUT / rel
        if not path.exists(): fail(f'manifest file missing: {rel}')
        elif manifest.get('checksums', {}).get(rel) != hashlib.sha256(path.read_bytes()).hexdigest():
            fail(f'manifest checksum mismatch: {rel}')
        if manifest.get('record_counts', {}).get(rel) is None: fail(f'manifest record count missing: {rel}')
    expected_transit_count = (
        len(bus.get('workday_routes', []))
        + len(bus.get('holiday_routes', []))
        + len(qg.get('routes', []))
        + len(matrix)
    )
    audit_count = sum(
        1
        for _ in csv.DictReader(
            (OUT / 'evidence/source_audit.csv').open(encoding='utf-8-sig')
        )
    )
    for rel, expected in [('campuses.v1.json', len(campuses)), ('aliases.v1.json', len(aliases_doc.get('aliases', []))), ('places.v1.json', len(places)), ('venues.v1.json', len(venues)), ('transit_2026_fall.json', expected_transit_count), ('section_times_2026_fall.json', len(sections_doc.get('sections', []))), ('evidence/source_audit.csv', audit_count)]:
        if manifest.get('record_counts', {}).get(rel) != expected: fail(f'manifest record count mismatch: {rel}')

    return report(campuses=len(campuses), places=len(places), venues=len(venues), audit_rows=sum(1 for _ in csv.DictReader((OUT / 'evidence/source_audit.csv').open(encoding='utf-8-sig'))))


def report(**counts: int) -> int:
    if errors:
        print('SYSU reference validation: FAILED')
        for error in errors: print(f'- {error}')
        return 1
    print('SYSU reference validation: PASS')
    for key, value in counts.items(): print(f'{key}: {value}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
