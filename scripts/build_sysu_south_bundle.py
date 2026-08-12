#!/usr/bin/env python3
"""Build the South-Campus-first SYSU static reference bundle."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path('/Users/baihe/Documents/compusone')
OUT = ROOT / 'data/reference/sysu'
EVIDENCE = OUT / 'evidence'
RAW = EVIDENCE / 'raw'
DOCS = ROOT / 'docs'
TODAY = '2026-08-11'
GENERATED_AT = '2026-08-11T21:05:00+08:00'
EFFECTIVE_FROM = '2026-09-07'
BUNDLE_VERSION = 'sysu-campus-reference-v1.1-south-first'
USER_COMMUTE_EVIDENCE = 'evidence/user_confirmed_commute_times_2026-08-11.md'

CAMPUS_URL = 'https://www.sysu.edu.cn/xxg/zdxq.htm'
MAP_URL = 'https://www.sysu.edu.cn/images/map-south-2024-10.jpg'
CALENDAR_URL = 'https://www.sysu.edu.cn/images/xl2026-2027-01.jpg'
CALENDAR_INDEX_URL = 'https://www.sysu.edu.cn/index/xl.htm'
FOOD_URL = 'https://www.sysu.edu.cn/info/1171/1611.htm'
LIB_URL = 'https://library.sysu.edu.cn/campus-library-1'
LIB_BASIC_URL = 'https://library.sysu.edu.cn/basic/3728'
MUSEUM_URL = 'https://bwgxsg.sysu.edu.cn/zh-hans/service/open-guide'
SPORT_URL = 'https://ce.sysu.edu.cn/zh-hans/article/1215'
SPORT_HISTORY_URL = 'https://tiyu.sysu.edu.cn/about/history'
STUDENT_URL = 'https://xsc.sysu.edu.cn/article/282'
ARTS_URL = 'https://arts.sysu.edu.cn/article/556'
JWB_URL = 'https://jwb.sysu.edu.cn/article/4194'
JWB_DEPT_URL = 'https://jwb.sysu.edu.cn/lx/department'
ROOM_ARTICLE_URL = 'https://zwc.sysu.edu.cn/article/757'
ROOM_PDF_URL = 'https://zwc.sysu.edu.cn/sites/default/files/2026-01/%E9%99%84%E4%BB%B61.%E4%B8%AD%E5%B1%B1%E5%A4%A7%E5%AD%A6%E5%85%AC%E5%85%B1%E7%94%A8%E6%88%BF%E5%85%B1%E4%BA%AB%E5%85%B1%E7%94%A8%E6%94%B6%E8%B4%B9%E4%BF%A1%E6%81%AF%E6%B1%87%E6%80%BB%E8%A1%A8.pdf'
GATE_NOTICE_URL = 'https://zwc.sysu.edu.cn/article/495'
SPORT_PASS_URL = 'https://tiyu.sysu.edu.cn/node/1927'
SUMMER_NOTICE_URL = 'https://zwc.sysu.edu.cn/article/926'

CLI_BUS_WORKDAY = 'sysu-anything bus --bus 1 --json'
CLI_BUS_HOLIDAY = 'sysu-anything bus --bus 0 --json'
CLI_QG_ROUTES = 'sysu-anything qg routes'
CLI_QG_LIST = 'sysu-anything qg list --today --all --json'
CLI_USC_APPS = 'sysu-anything usc apps --json'
CLI_USC_CLASSROOM_CAMPUSES = 'sysu-anything usc classroom campuses --json'
CLI_USC_MEETING_CAMPUSES = 'sysu-anything usc meeting campuses --json'
CLI_USC_ACTIVITY_ROOMS = 'sysu-anything usc activity rooms --json'
CLI_USC_MEETING_SOUTH = 'sysu-anything usc meeting venues --campus 南校园 --json'
CLI_USC_CLASSROOM_SOUTH = 'sysu-anything usc classroom rooms --campus 南校园 --date 2026-08-11 --section-start 1 --section-end 2 --json'
CLI_JWXT_SECTIONS = 'sysu-anything jwxt section-times --school-year 2026-1 --json'
CLI_JWXT_STATUS = 'sysu-anything jwxt status'
CLI_GYM_PROFILE = 'sysu-anything gym profile'
CLI_LIBIC_ROOMS = 'sysu-anything libic room-types --json'

SOUTH = 'guangzhou_south'
NORTH = 'guangzhou_north'
EAST = 'guangzhou_east'
ZHUHAI = 'zhuhai'
SHENZHEN = 'shenzhen'


def write_json(filename: str, data: Any) -> None:
    path = OUT / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def source_refs(*refs: str) -> list[str]:
    return list(dict.fromkeys(refs))


def place_record(place_id: str, campus_id: str, category: str, name: str,
                 aliases: list[str] | None = None, building: str | None = None,
                 floor: str | None = None, location_text: str | None = None,
                 latitude: float | None = None, longitude: float | None = None,
                 opening_hours: str | None = None, services: list[str] | None = None,
                 refs: list[str] | None = None, confidence: str = 'verified',
                 note: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        'id': place_id, 'campus_id': campus_id, 'category': category,
        'canonical_name': name, 'aliases': aliases or [], 'building': building,
        'floor': floor, 'location_text': location_text, 'latitude': latitude,
        'longitude': longitude, 'opening_hours': opening_hours,
        'services': services or [], 'source_refs': refs or [CAMPUS_URL],
        'verified_at': TODAY, 'confidence': confidence,
    }
    if note:
        item['verification_note'] = note
    return item


def venue_record(venue_id: str, place_id: str, name: str, venue_type: str,
                 capacity: int | str | None, services: list[str], refs: list[str],
                 source_system: str = 'official', source_parameter_id: str | None = None,
                 aliases: list[str] | None = None, confidence: str = 'verified',
                 note: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        'id': venue_id, 'campus_id': SOUTH, 'place_id': place_id,
        'source_system': source_system, 'source_parameter_id': source_parameter_id,
        'venue_type': venue_type, 'canonical_name': name, 'aliases': aliases or [],
        'capacity': capacity, 'services': services, 'opening_hours': None,
        'reservation_window_days': None, 'minimum_duration_minutes': None,
        'maximum_duration_minutes': None, 'requires_member_list': None,
        'cancellation_rules': None,
        'official_url': next((r for r in refs if r.startswith('http')), None),
        'source_refs': refs, 'verified_at': TODAY, 'confidence': confidence,
    }
    if note:
        item['verification_note'] = note
    return item


def normalize_time(value: str) -> str:
    h, m = value.strip().split(':')
    return f'{int(h):02d}:{int(m):02d}'


def campus_from_station(name: str) -> str | None:
    if '南校园' in name:
        return SOUTH
    if '北校园' in name:
        return NORTH
    if '东校园' in name:
        return EAST
    return None


def bus_place_id(name: str) -> str:
    mapping = {
        '南校园南门停车场': 'south_bus_south_gate_parking',
        '北校园南门车房楼下': 'north_bus_south_gate_carhouse',
        '东校园兰园3号（原生科院大楼）': 'east_bus_lanyuan3',
        '东校园兰园3号（原生科院大楼）停车场': 'east_bus_lanyuan3',
    }
    return mapping.get(name, re.sub(r'[^0-9A-Za-z一-龥]+', '_', name).strip('_').lower())


def clean_bus_note(note: str) -> str:
    lines = [line.strip() for line in note.splitlines() if line.strip()]
    keep: list[str] = []
    for line in lines:
        if line.startswith('备注:') or line.startswith('温馨提示'):
            continue
        if '咨询及投诉电话' in line or re.search(r'\d{7,}', line):
            continue
        if '易燃' in line or '枪支' in line:
            continue
        if line.startswith(('1、', '2、', '3、', '4、', '（1）', '（2）')):
            keep.append(line)
    return ' '.join(keep)


# ---------- campuses and aliases ----------
campuses = [
    {'id': SOUTH, 'canonical_name': '广州校区南校园', 'city': '广州',
     'aliases': ['南校园', '广州南校园', '南校区', '广州校区南校'],
     'official_address': '广州市海珠区新港西路135号（510275）', 'latitude': None, 'longitude': None,
     'official_url': CAMPUS_URL,
     'source_refs': source_refs(CAMPUS_URL, CLI_USC_CLASSROOM_CAMPUSES, CLI_USC_MEETING_CAMPUSES),
     'verified_at': TODAY, 'confidence': 'partial',
     'verification_note': '官方名称与地址已核验；官方页面未提供可直接复用的校园中心坐标，坐标保留 null。'},
    {'id': NORTH, 'canonical_name': '广州校区北校园', 'city': '广州',
     'aliases': ['北校园', '广州北校园', '北校区', '广州校区北校'],
     'official_address': '广州市越秀区中山二路74号（510080）', 'latitude': None, 'longitude': None,
     'official_url': CAMPUS_URL,
     'source_refs': source_refs(CAMPUS_URL, CLI_USC_CLASSROOM_CAMPUSES, CLI_USC_MEETING_CAMPUSES),
     'verified_at': TODAY, 'confidence': 'partial', 'verification_note': '官方名称与地址已核验；校园中心坐标待补充。'},
    {'id': EAST, 'canonical_name': '广州校区东校园', 'city': '广州',
     'aliases': ['东校园', '广州东校园', '东校区', '广州校区东校'],
     'official_address': '广州市番禺区大学城外环东路132号（510006）', 'latitude': None, 'longitude': None,
     'official_url': CAMPUS_URL,
     'source_refs': source_refs(CAMPUS_URL, CLI_USC_CLASSROOM_CAMPUSES, CLI_USC_MEETING_CAMPUSES),
     'verified_at': TODAY, 'confidence': 'partial', 'verification_note': '官方名称与地址已核验；校园中心坐标待补充。'},
    {'id': ZHUHAI, 'canonical_name': '珠海校区', 'city': '珠海',
     'aliases': ['珠海', '珠海校园'], 'official_address': '珠海市香洲区唐家湾（519082）',
     'latitude': None, 'longitude': None, 'official_url': CAMPUS_URL,
     'source_refs': source_refs(CAMPUS_URL, CLI_USC_CLASSROOM_CAMPUSES, CLI_USC_MEETING_CAMPUSES, CLI_QG_LIST),
     'verified_at': TODAY, 'confidence': 'partial', 'verification_note': '官方名称与地址已核验；校园中心坐标待补充。'},
    {'id': SHENZHEN, 'canonical_name': '深圳校区', 'city': '深圳',
     'aliases': ['深圳', '深圳校园'], 'official_address': '深圳市光明区公常路66号',
     'latitude': None, 'longitude': None, 'official_url': CAMPUS_URL,
     'source_refs': source_refs(CAMPUS_URL, CLI_USC_CLASSROOM_CAMPUSES, CLI_USC_MEETING_CAMPUSES),
     'verified_at': TODAY, 'confidence': 'partial', 'verification_note': '官方名称与地址已核验；校园中心坐标待补充。'},
]
write_json('campuses.v1.json', {'version': 'v1', 'verified_at': TODAY, 'campuses': campuses})
aliases: list[dict[str, Any]] = []
for c in campuses:
    for alias in [c['canonical_name'], *c['aliases']]:
        aliases.append({'alias': alias, 'canonical_id': c['id'], 'kind': 'campus', 'source_refs': c['source_refs'], 'verified_at': TODAY})
write_json('aliases.v1.json', {'version': 'v1', 'aliases': aliases})


# ---------- places ----------
places: list[dict[str, Any]] = []
place_ids: set[str] = set()
def add_place(**kwargs: Any) -> None:
    item = place_record(**kwargs)
    if item['id'] not in place_ids:
        places.append(item)
        place_ids.add(item['id'])

for pid, name, aliases_, loc in [
    ('south_gate', '南门', ['南校园南门', '南校南门'], '南校园南侧校门'),
    ('north_gate', '北门', ['南校园北门'], '南校园北侧校门'),
    ('east_gate', '东门', ['南校园东门'], '南校园东侧校门'),
    ('west_gate', '西门', ['南校园西门'], '南校园西侧校门'),
]:
    add_place(place_id=pid, campus_id=SOUTH, category='gate', name=name, aliases=aliases_, location_text=loc, refs=[MAP_URL, CAMPUS_URL], services=['校园出入口'])
add_place(place_id='south_qg_stop', campus_id=SOUTH, category='transit_stop', name='广中大南校区岐关服务部', aliases=['南门岐关车站', '南校园岐关车站', '南校岐关车站'], location_text='南门左边方向前50米的位置岐关车站', latitude=23.092043, longitude=113.297367, services=['岐关车静态站点'], refs=[CLI_QG_LIST, CLI_QG_ROUTES])
add_place(place_id='south_bus_south_gate_parking', campus_id=SOUTH, category='transit_stop', name='南校园南门停车场', aliases=['南校南门停车场', '南校园班车站'], location_text='南校园南门停车场；广州校区校际班车站点', services=['广州校区班车'], refs=[CLI_BUS_WORKDAY, CLI_BUS_HOLIDAY, GATE_NOTICE_URL])
add_place(place_id='south_bus_new_gym_west_gate', campus_id=SOUTH, category='transit_stop', name='南校园新体育馆西门班车点', aliases=['新体育馆西门班车点'], location_text='南校园新体育馆西门；官方通知所列校内班车候车点', services=['校内班车'], refs=[GATE_NOTICE_URL], confidence='partial')
for pid, campus, name, aliases_, loc in [
    ('north_bus_south_gate_carhouse', NORTH, '北校园南门车房楼下', ['北校南门车房楼下'], '北校园南门车房楼下'),
    ('east_bus_lanyuan3', EAST, '东校园兰园3号（原生科院大楼）', ['东校园兰园3号', '兰园3号（原生科院大楼）'], '东校园兰园3号（原生科院大楼）停车场'),
    ('east_bus_teaching_a_north', EAST, '东校园教学楼A座北侧', ['教学楼A座北侧'], '东校园校内班车停靠点'),
    ('east_bus_admin_bridge', EAST, '东校园行政楼北侧桥头', ['行政楼北侧桥头'], '东校园校内班车停靠点'),
    ('east_bus_yingyuan1', EAST, '东校园樱园1号', ['樱园1号'], '东校园校内班车停靠点'),
    ('east_bus_yingyuan3', EAST, '东校园樱园3号', ['樱园3号'], '东校园校内班车停靠点'),
    ('east_bus_staff_apartment', EAST, '东校园教工公寓对面', ['教工公寓对面'], '东校园校内班车停靠点'),
    ('east_bus_chem_material', EAST, '东校园化学材料综合楼', ['化学材料综合楼'], '东校园校内班车停靠点'),
]:
    add_place(place_id=pid, campus_id=campus, category='transit_stop', name=name, aliases=aliases_, location_text=loc, services=['广州校区班车'], refs=[CLI_BUS_WORKDAY, CLI_BUS_HOLIDAY])

teaching_specs = [
    ('teaching_1', '第一教学楼', ['一教', '第一教'], '348栋', '南校园教学区', [JWB_DEPT_URL, MAP_URL, 'https://zwc.sysu.edu.cn/article/647']),
    ('teaching_2', '第二教学楼', ['二教', '第二教'], '389栋', '南校园教学区', [JWB_DEPT_URL, ROOM_PDF_URL, MAP_URL]),
    ('teaching_3', '第三教学楼', ['三教', '第三教'], None, '南校园教学区', [JWB_DEPT_URL, 'https://sbc.sysu.edu.cn/article/885', MAP_URL]),
    ('teaching_4', '第四教学楼（丰盛堂）', ['四教', '丰盛堂', '第四教学楼'], None, '南校园教学区', [JWB_DEPT_URL, MAP_URL]),
    ('teaching_5', '第五教学楼（逸夫楼）', ['五教', '逸夫楼', '逸夫教学楼'], '494栋', '南校园教学区', [JWB_DEPT_URL, 'https://zwc.sysu.edu.cn/article/920', MAP_URL]),
    ('teaching_6', '第六教学楼', ['六教', '第六教', '392栋'], '392栋', '南校园教学区', [JWB_DEPT_URL, 'https://cse.sysu.edu.cn/article/3576', MAP_URL]),
    ('liberal_arts_building', '文科楼', ['文科楼'], '275栋', '南校园西区', [ROOM_PDF_URL, MAP_URL]),
    ('chinese_hall', '中文堂', ['中文堂'], '274栋', '南校园西区', [ROOM_PDF_URL, MAP_URL]),
    ('foreign_language_building', '外国语学院', ['外院', '外国语学院楼'], '258栋', '南校园西区', [ROOM_PDF_URL, MAP_URL]),
]
for pid, name, aliases_, building, loc, refs in teaching_specs:
    add_place(place_id=pid, campus_id=SOUTH, category='teaching_building', name=name, aliases=aliases_, building=building, location_text=loc, services=['教学用房'], refs=refs)
add_place(place_id='south_library', campus_id=SOUTH, category='library', name='南校园图书馆', aliases=['图书总馆', '中山大学图书馆'], building='335栋', location_text='广州市海珠区新港西路135号中山大学图书馆', services=['中文图书', '外文图书', '参考咨询', '特藏服务', '报刊阅览'], refs=[LIB_URL, LIB_BASIC_URL, MAP_URL])

canteens = [
    ('canteen_zijing', '紫荆园餐厅', ['紫荆园'], '南校园东南区（外国语学院后方）', '7:00-9:30；11:30-14:00；17:30-21:30'),
    ('canteen_kangle', '康乐园餐厅', ['康乐园'], '南校园蒲园区609号；西门入内右转约200米', '食堂：6:30-9:00；11:00-13:00；17:00-19:00；餐厅：7:00-10:30；11:00-14:00；17:00-21:00'),
    ('canteen_student_1', '学一食堂', ['学一'], '逸夫艺术中心西侧', '6:00-10:30；10:30-13:30；17:00-19:00；晚餐延时：17:00-22:30'),
    ('canteen_student_5', '学五食堂', ['学五'], '南校园东区107栋首层附近', '6:30-9:30；11:00-13:20；17:00-19:00；晚餐延时：18:30-22:00'),
    ('canteen_wuyue', '五月餐厅', ['五月'], '南校园东区107栋二楼', '11:00-14:00；17:00-20:00'),
    ('canteen_chunhui', '春晖园食堂', ['春晖园'], '南校园东北区', '7:00-9:30；11:00-13:20；17:00-19:00；晚餐延时：19:00-21:30'),
    ('canteen_staff_puyuan', '教工（蒲园）餐厅', ['蒲园教工餐厅', '教工餐厅'], '南校园西区蒲园路', '食堂：6:00-8:30；11:00-13:00；17:00-19:00；餐厅：6:30-9:30；11:00-14:00；17:00-20:30'),
    ('canteen_south_lawn', '南草坪食堂', ['南草坪'], '南校园中央区', '10:30-19:00；餐段：10:30-13:30；17:00-19:00'),
    ('canteen_northwest_flavor', '西北风味食堂', ['西北风味'], '南校园东区107栋首层学五食堂旁', '7:00-9:00；10:45-13:20；16:45-19:00'),
    ('canteen_xuerenguan_west', '中大学人馆西餐厅', ['学人馆西餐厅'], '南校园北门中大学人馆1楼', '7:00-10:00；11:30-14:30；17:30-21:30'),
    ('canteen_xuerenguan_chinese', '中大学人馆中餐厅', ['学人馆中餐厅'], '南校园北门中大学人馆2-3楼', '11:00-14:30；17:30-21:30'),
    ('canteen_shuizhuyuxiang', '水煮鱼乡', ['水煮鱼乡'], '南校园北门中大学人馆1楼', '11:30-14:00；17:00-21:30'),
]
for pid, name, aliases_, loc, hours in canteens:
    add_place(place_id=pid, campus_id=SOUTH, category='canteen', name=name, aliases=aliases_, location_text=loc, opening_hours=hours, services=['餐饮'], refs=[FOOD_URL], confidence='partial' if pid == 'canteen_chunhui' else 'verified', note='学校当前餐饮页面仍列示；历史通知曾出现阶段性调整，营业状态需按当前现场/页面复核。' if pid == 'canteen_chunhui' else None)

for pid, name, aliases_, services_, loc, refs in [
    ('yingdong_sports_center', '英东体育中心', ['英东体育场馆'], ['体育馆', '田径运动场', '网球场', '综合球类场', '游泳场'], '南校园东南区英东体育中心', [SPORT_HISTORY_URL, SPORT_URL]),
    ('yingdong_gymnasium', '英东体育馆', ['英东馆'], ['室内篮球场', '排球场', '羽毛球场'], '南校园英东体育中心', [SPORT_HISTORY_URL, SPORT_URL, 'https://tiyu.sysu.edu.cn/node/1935']),
    ('yingdong_track', '英东田径运动场', ['英东田径场', '田径场'], ['400米田径场', '足球场'], '南校园英东体育中心', [SPORT_HISTORY_URL, SPORT_URL, 'https://tiyu.sysu.edu.cn/node/1843']),
    ('yingdong_tennis', '英东网球场', ['网球场'], ['网球'], '南校园英东体育中心', [SPORT_HISTORY_URL, SPORT_URL]),
    ('yingdong_ball_courts', '英东综合球类场', ['综合球类场'], ['球类运动'], '南校园英东体育中心', [SPORT_HISTORY_URL, SPORT_URL]),
    ('yingdong_pool', '英东游泳场', ['游泳场'], ['游泳', '跳水'], '南校园英东体育中心', [SPORT_HISTORY_URL, SPORT_URL, SPORT_PASS_URL]),
    ('south_new_gym', '南校园新体育馆', ['新体育馆'], ['体育活动', '游泳相关活动'], '南校园新体育馆', [SPORT_PASS_URL, 'https://edf-edaao.sysu.edu.cn/article/489']),
]:
    add_place(place_id=pid, campus_id=SOUTH, category='sports', name=name, aliases=aliases_, location_text=loc, services=services_, refs=refs, confidence='partial' if pid == 'south_new_gym' else 'verified')
add_place(place_id='xiongdellong_center', campus_id=SOUTH, category='activity_center', name='熊德龙学生活动中心', aliases=['学生活动中心', '熊德龙中心'], building='301栋', location_text='南校园学生活动中心', services=['音乐厅', '报告厅', '舞蹈室', '画室'], refs=[STUDENT_URL, ARTS_URL, ROOM_PDF_URL])
add_place(place_id='yifu_art_center', campus_id=SOUTH, category='activity_center', name='逸夫文化艺术中心', aliases=['逸夫艺术中心', '艺术中心'], location_text='南校园逸夫文化艺术中心', services=['艺术活动', '餐饮邻近点'], refs=[FOOD_URL, MAP_URL])
for pid, name, aliases_, building, loc, services_, refs in [
    ('museum', '中山大学博物馆', ['博物馆'], '543栋', '南校园新港西路135号', ['博物馆参观'], [MUSEUM_URL, MAP_URL]),
    ('school_history_museum', '校史馆', ['格兰堂校史馆'], '333栋格兰堂', '南校园格兰堂', ['校史展览'], [MUSEUM_URL, MAP_URL]),
    ('biology_museum', '生物馆', ['马文辉堂生物馆'], '475栋马文辉堂', '南校园西南区', ['生物标本展览'], [MUSEUM_URL, MAP_URL]),
    ('sun_yat_sen_memorial', '孙中山纪念馆', ['孙中山纪念堂'], '503栋', '南校园西北区', ['纪念馆参观'], [MUSEUM_URL, MAP_URL]),
    ('chen_yinke_home', '陈寅恪故居', [], '309号', '南校园东北区', ['历史建筑'], [MUSEUM_URL, MAP_URL]),
    ('chen_xintao_home', '陈心陶故居', [], '241号', '南校园东南区', ['历史建筑'], [MUSEUM_URL, MAP_URL]),
    ('south_lawn', '南草坪', ['中央草坪'], None, '南校园中央区', ['集合点', '户外空间'], [MAP_URL, FOOD_URL]),
    ('songtao_garden', '松涛园', ['松涛园'], '359栋附近', '南校园东区', ['校园景观'], [MAP_URL]),
    ('north_gate_square', '北门广场', ['南校园北门广场'], None, '南校园北门内侧', ['集合点', '班车路线节点'], [MAP_URL, CLI_BUS_WORKDAY]),
]:
    add_place(place_id=pid, campus_id=SOUTH, category='landmark', name=name, aliases=aliases_, building=building, location_text=loc, services=services_, refs=refs)

public_buildings = [
    ('huishitang', '怀士堂', ['怀士堂'], '492栋', 'auditorium', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('liangqiujutang', '梁銶琚堂', ['梁銶琚堂'], '487栋', 'auditorium', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('fulantang', '芙兰堂', ['芙兰堂'], '262栋', 'auditorium', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('xianweijiantang', '冼为坚堂', ['冼为坚堂'], '260栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('yebaodingtang', '叶葆定堂', ['叶葆定堂'], '394栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('lingnantang', '岭南堂', ['岭南堂'], '577栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('mba_building', 'MBA大楼', ['MBA楼'], '395栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('math_building', '数学楼', ['数学楼'], '266栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('zhenhuantang', '震寰堂', ['震寰堂'], '629栋', 'teaching_building', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('xiongdellong_center', '熊德龙学生活动中心', ['熊德龙中心'], '301栋', 'activity_center', '南校园公共用房目录', [ROOM_PDF_URL, STUDENT_URL]),
    ('arts_building', '艺术学院楼', ['艺术学院楼'], '104栋', 'activity_center', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('yongfangtang', '永芳堂', ['永芳堂'], '503栋', 'auditorium', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('teaching_2', '第二教学楼', ['二教'], '389栋', 'teaching_building', '南校园公共用房目录', [ROOM_PDF_URL, JWB_DEPT_URL]),
    ('life_science_1', '生命科学楼1号楼', ['生科楼1号楼'], '408栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('life_science_2', '生命科学楼2号楼', ['生科楼2号楼'], '408栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('hedanqingtang', '贺丹青堂', ['贺丹青堂'], '478栋', 'auditorium', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('shansitang', '善思堂', ['善思堂'], '386栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('shanhengtang', '善衡堂', ['善衡堂'], '387栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('xichang_tang', '锡昌堂', ['锡昌堂'], '269栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('liberal_arts_building', '文科楼', ['文科楼'], '275栋', 'teaching_building', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('chinese_hall', '中文堂', ['中文堂'], '274栋', 'teaching_building', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('small_red_building', '小红楼', ['小红楼'], '261栋', 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('foreign_language_building', '外国语学院', ['外国语学院楼'], '258栋', 'teaching_building', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('alumni_hall', '校友会堂', ['校友会堂'], None, 'auditorium', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
    ('guest_reception_room', '大外宾接待室', ['大外宾接待室'], None, 'meeting', '南校园公共用房目录', [ROOM_PDF_URL]),
    ('yongsheng_building', '永生楼', ['永生楼'], None, 'meeting', '南校园公共用房目录', [ROOM_PDF_URL, MAP_URL]),
]
for pid, name, aliases_, building, cat, loc, refs in public_buildings:
    if pid in place_ids:
        for item in places:
            if item['id'] == pid:
                item['aliases'] = list(dict.fromkeys(item['aliases'] + aliases_))
                if '公共用房目录宿主建筑' not in item['services']:
                    item['services'].append('公共用房目录宿主建筑')
                break
    else:
        add_place(place_id=pid, campus_id=SOUTH, category=cat, name=name, aliases=aliases_, building=building, location_text=loc, services=['公共用房目录宿主建筑'], refs=refs)
write_json('places.v1.json', {'version': 'v1', 'verified_at': TODAY, 'places': places})


# ---------- venues ----------
PUBLIC_ROWS: list[tuple[str, int | str | None]] = [
    ('怀士堂（492栋）小礼堂', 250), ('梁銶琚堂（487栋）大礼堂-会议', 1433), ('梁銶琚堂（487栋）大礼堂-演出', 1433),
    ('梁銶琚堂（487栋）第一会议室', 53), ('梁銶琚堂（487栋）第二会议室', 38), ('芙兰堂（262栋）一楼讲学厅', 365),
    ('芙兰堂（262栋）213讲学厅', 148), ('冼为坚堂（260栋）一楼117多媒体室', 60), ('冼为坚堂（260栋）一楼讲学厅', 210),
    ('冼为坚堂（260栋）一楼111多媒体室', 50), ('冼为坚堂（260栋）一楼112多媒体室', 30), ('叶葆定堂（394栋）三楼讲学厅（含大堂、贵宾室）', 400),
    ('岭南堂（577栋）101汪道涵会议室', 40), ('岭南堂（577栋）102黄华会议室', 12), ('岭南堂（577栋）103林植宣会议室', '内14 外6'),
    ('岭南堂（577栋）104贵宾室', '内12 外6'), ('岭南堂（577栋）106值班会议室', 10), ('岭南堂（577栋）201咖啡厅', '内24 外19'),
    ('岭南堂（577栋）202叶葆定会议室', '内12 外6'), ('岭南堂（577栋）203黄炳礼会议室', '内14 外10'), ('岭南堂（577栋）204伍沾德会议室', '内20 外10'),
    ('岭南堂（577栋）205伍舜德会议室', '内12 外7'), ('岭南堂（577栋）302陈荣捷讲学厅', 120), ('岭南堂（577栋）三楼大堂', 50),
    ('MBA大楼（395栋）1001贵宾厅', 14), ('MBA大楼（395栋）1002多功能厅', 160), ('MBA大楼（395栋）501-504讨论室', 8),
    ('MBA大楼（395栋）505-509讨论室', 6), ('MBA大楼（395栋）402讲学厅', 168), ('MBA大楼201课室', 66),
    ('MBA大楼202课室', 70), ('MBA大楼701课室', 61), ('MBA大楼702课室', 141), ('叶葆定堂101课室', 64),
    ('叶葆定堂102课室', 64), ('叶葆定堂103课室', 88), ('叶葆定堂201课室', 64), ('叶葆定堂202课室', 64),
    ('叶葆定堂203课室', 50), ('叶葆定堂204课室', 60), ('数学楼（266栋）301会议室', 14), ('数学楼（266栋）519会议室', 15),
    ('数学楼（266栋）810会议室', 22), ('数学楼（266栋）415、416讲学室', 48), ('数学楼（266栋）209报告厅', 149),
    ('震寰堂（629栋）C218课室', 47), ('震寰堂（629栋）C219课室', 52), ('震寰堂（629栋）C318课室', 63), ('震寰堂（629栋）C319课室', 35),
    ('震寰堂（629栋）C418课室', 49), ('震寰堂（629栋）C419课室', 58), ('熊德龙学生活动中心（301栋）205音乐厅', 450),
    ('熊德龙学生活动中心（301栋）105报告厅', 150), ('熊德龙学生活动中心（301栋）313舞蹈室', 25), ('熊德龙学生活动中心（301栋）203画室', 60),
    ('艺术学院楼（104栋）301电钢琴室', 40), ('艺术学院楼（104栋）206报告厅', 154), ('艺术学院楼（104栋）303排练厅', 50),
    ('艺术学院楼（104栋）701、702录音棚', None), ('永芳堂（503栋）433讲学厅', 70), ('永芳堂（503栋）233讲学厅', 190),
    ('永芳堂（503栋）201研讨室', 20), ('永芳堂（503栋）202研讨室', 20), ('永芳堂（503栋）231研讨室', 20), ('永芳堂（503栋）232研讨室', 20),
    ('永芳堂（503栋）333研讨室', 20), ('永芳堂（503栋）431研讨室', 20), ('永芳堂（503栋）437研讨室', 20), ('第二教学楼（389栋）414讲学厅', 68),
    ('第二教学楼（389栋）405会议室', 40), ('第二教学楼（389栋）506会议室', 45), ('第二教学楼（389栋）631会议室', 35), ('第二教学楼（389栋）720会议室', 35),
    ('生命科学楼1号楼（408栋）124国际会议厅', 298), ('生命科学楼2号楼（408栋）102讲学厅', 89), ('贺丹青堂（478栋）101讲学厅', 250),
    ('生命科学楼2号楼（408栋）1017会议室', 50), ('生命科学楼2号楼（408栋）403会议室', 38), ('生命科学楼2号楼（408栋）503会议室', 38),
    ('生命科学楼2号楼（408栋）601会议室', 40), ('生命科学楼2号楼（408栋）701会议室', 40), ('生命科学楼2号楼（408栋）801会议室', 40),
    ('生命科学楼2号楼（408栋）901会议室', 40), ('贺丹青堂（478栋）103会议室', 40), ('善思堂（386栋）M203多功能国际会议厅', 410),
    ('善衡堂（387栋）南座S109会议室', '44-50'), ('善衡堂（387栋）南座S201会议室', '64-100'), ('锡昌堂（269栋）801讲学厅', 240),
    ('锡昌堂（269栋）103讲学厅', 90), ('锡昌堂（269栋）1楼多功能厅', 50), ('锡昌堂（269栋）515会议室', 35), ('锡昌堂（269栋）504会议室', 20),
    ('锡昌堂（269栋）727会议室', 25), ('锡昌堂（269栋）513会议室', 12), ('锡昌堂（269栋）202-204、208-210课室', 20), ('文科楼（275栋）223课室', 60),
    ('文科楼（275栋）225讲学厅', 169), ('文科楼（275栋）310讲学厅', 35), ('文科楼（275栋）307讲学厅', 30), ('善衡堂（387栋）S131党校讲学厅', 193),
    ('善思堂（386栋）M201党校课室', 56), ('善衡堂（387栋）S412会议室', 40), ('善衡堂（387栋）S502会议室', 25), ('中文堂（274栋）206会议厅', 143),
    ('中文堂（274栋）301会议厅', 66), ('中文堂（274栋）201课室', 93), ('中文堂（274栋）105讲学厅', 382), ('中文堂（274栋）207课室', 193),
    ('中文堂（274栋）203课室', 48), ('中文堂（274栋）204课室', 54), ('中文堂（274栋）305课室', 60), ('冼为坚堂（260栋）3楼会议室', 60),
    ('小红楼（261栋）206会议室', 58), ('外国语学院（258栋）101讲学厅', 268), ('外国语学院（258栋）315讲学厅', 138), ('外国语学院（258栋）210讲学厅', 50),
    ('外国语学院（258栋）406、408、409课室', 60), ('外国语学院（258栋）311-313、403、411-413课室', 35), ('外国语学院（258栋）一楼校友之家', 36),
    ('校友会堂报告厅-会议', 539), ('校友会堂报告厅-演出', 539), ('大外宾接待室', 70), ('永生楼4楼讲学厅', 161),
]
PREFIX_TO_PLACE = [
    ('熊德龙学生活动中心', 'xiongdellong_center'), ('艺术学院楼', 'arts_building'), ('第二教学楼', 'teaching_2'),
    ('生命科学楼1号楼', 'life_science_1'), ('生命科学楼2号楼', 'life_science_2'), ('冼为坚堂', 'xianweijiantang'),
    ('梁銶琚堂', 'liangqiujutang'), ('怀士堂', 'huishitang'), ('芙兰堂', 'fulantang'), ('叶葆定堂', 'yebaodingtang'),
    ('岭南堂', 'lingnantang'), ('MBA大楼', 'mba_building'), ('数学楼', 'math_building'), ('震寰堂', 'zhenhuantang'),
    ('永芳堂', 'yongfangtang'), ('贺丹青堂', 'hedanqingtang'), ('善思堂', 'shansitang'), ('善衡堂', 'shanhengtang'),
    ('锡昌堂', 'xichang_tang'), ('文科楼', 'liberal_arts_building'), ('中文堂', 'chinese_hall'), ('小红楼', 'small_red_building'),
    ('外国语学院', 'foreign_language_building'), ('校友会堂', 'alumni_hall'), ('大外宾接待室', 'guest_reception_room'), ('永生楼', 'yongsheng_building'),
]
def public_place_id(name: str) -> str:
    for prefix, pid in PREFIX_TO_PLACE:
        if name.startswith(prefix):
            return pid
    raise KeyError(name)
def classify_venue(name: str) -> tuple[str, list[str]]:
    if '录音棚' in name: return 'studio', ['录音室', '监听控制室']
    if any(x in name for x in ['舞蹈室', '画室', '排练厅', '电钢琴室']): return 'activity_room', ['活动空间']
    if '课室' in name or '多媒体室' in name or '讲学室' in name: return 'teaching_room', ['教学/讲学空间']
    if any(x in name for x in ['小礼堂', '大礼堂', '报告厅', '音乐厅', '讲学厅', '会议厅', '多功能厅']): return 'auditorium', ['报告/讲学空间']
    return 'meeting_room', ['会议/研讨空间']
venues: list[dict[str, Any]] = []
for idx, (name, capacity) in enumerate(PUBLIC_ROWS, start=1):
    typ, services_ = classify_venue(name)
    venues.append(venue_record(f'south_public_{idx:03d}', public_place_id(name), name, typ, capacity, services_ + ['官方公共用房共享目录'], [ROOM_PDF_URL, ROOM_ARTICLE_URL], note='容量/名称取自2026年官方公共用房共享共用收费信息汇总表；不表示实时可用状态。'))
for idx, (pid, name, typ, capacity, services_, refs) in enumerate([
    ('yingdong_sports_center', '英东体育中心', 'sports_complex', None, ['体育馆', '田径运动场', '网球场', '综合球类场', '游泳场'], [SPORT_HISTORY_URL, SPORT_URL]),
    ('yingdong_gymnasium', '英东体育馆', 'gymnasium', None, ['室内篮球场', '排球场', '羽毛球场'], [SPORT_HISTORY_URL, SPORT_URL]),
    ('yingdong_track', '英东田径运动场', 'track_field', None, ['400米田径场', '足球场'], [SPORT_HISTORY_URL, SPORT_URL]),
    ('yingdong_tennis', '英东网球场', 'tennis_court', None, ['网球'], [SPORT_HISTORY_URL, SPORT_URL]),
    ('yingdong_ball_courts', '英东综合球类场', 'ball_court', None, ['球类运动'], [SPORT_HISTORY_URL, SPORT_URL]),
    ('yingdong_pool', '英东游泳场', 'swimming_pool', None, ['游泳', '跳水'], [SPORT_HISTORY_URL, SPORT_URL, SPORT_PASS_URL]),
    ('south_new_gym', '南校园新体育馆', 'gymnasium', None, ['体育活动'], [SPORT_PASS_URL, 'https://edf-edaao.sysu.edu.cn/article/489']),
], start=1):
    venues.append(venue_record(f'south_sports_{idx:03d}', pid, name, typ, capacity, services_, refs, confidence='partial' if pid == 'south_new_gym' else 'verified', note='官方场馆目录；未写入日期级空闲结果。'))
for idx, (name, pid, capacity) in enumerate([
    ('逸夫楼 逸403 有声研讨室', 'teaching_5', 40), ('逸夫楼 逸503 有声研讨室', 'teaching_5', 40),
    ('第一教学楼 1103 有声研讨室', 'teaching_1', 20), ('第一教学楼 1106 有声研讨室', 'teaching_1', 69),
    ('第一教学楼 1603 有声研讨室', 'teaching_1', 20), ('第二教学楼 2117 有声研讨室', 'teaching_2', 40),
    ('第二教学楼 2213 有声研讨室', 'teaching_2', 36),
], start=1):
    venues.append(venue_record(f'south_discussion_{idx:03d}', pid, name, 'discussion_room', capacity, ['有声研讨室'], [JWB_URL], confidence='partial', note='教务处按学期公布的自习/研讨空间；具体开放时段需随学期通知更新。'))
write_json('venues.v1.json', {'version': 'v1', 'verified_at': TODAY, 'venues': venues})


# ---------- transit ----------
def load_bus(filename: str) -> dict[str, Any]:
    return json.loads((RAW / filename).read_text(encoding='utf-8'))
def clean_bus_dataset(filename: str, date_label: str, cli_ref: str) -> list[dict[str, Any]]:
    data = load_bus(filename)['result']
    result: list[dict[str, Any]] = []
    for idx, route in enumerate(data['routes'], start=1):
        start, end = route['startStation'], route['endStation']
        from_id, to_id = campus_from_station(start), campus_from_station(end)
        if from_id is None or to_id is None: raise ValueError((start, end))
        departures = []
        for moment in route.get('schoolBusShuttleMomentList') or []:
            departures.append({'time': normalize_time(moment['time']), 'route_note': moment.get('drivingRoute'), 'passenger': moment.get('passenger'), 'vehicle_type': moment.get('vehiclesType')})
        passengers = sorted({x['passenger'] for x in departures if x.get('passenger')})
        result.append({'id': f'bus_{date_label}_{idx:02d}', 'route_name': route.get('drivingDirectionName') or f'{start}-{end}', 'from_campus_id': from_id, 'to_campus_id': to_id, 'direction': route.get('drivingDirectionName'), 'stops': [{'place_id': bus_place_id(start), 'name': start, 'role': 'origin'}, {'place_id': bus_place_id(end), 'name': end, 'role': 'destination'}], 'scheduled_departures': departures, 'passenger_restrictions': passengers, 'static_notes': [clean_bus_note(route.get('note') or ''), '票价3元/次，使用校园卡支付。'], 'date_type': date_label, 'source_refs': [cli_ref], 'verified_at': TODAY, 'confidence': 'verified'})
    return result
workday = clean_bus_dataset('bus_workday.json', 'workday', CLI_BUS_WORKDAY)
holiday = clean_bus_dataset('bus_holiday.json', 'holiday', CLI_BUS_HOLIDAY)

user_commute_evidence = f'''# 用户确认的校区通勤典型时长

- 确认日期：{TODAY}
- 数据性质：用户提供的常用通勤典型值
- 单位：分钟
- 方向口径：只记录用户明确给出的方向，不自动推导反向时长
- 时间口径：行程典型时长；`buffer_minutes` 与 `minimum_safe_gap_minutes` 仍保持空值

| 出发校园 | 到达校园 | 典型时长 |
|---|---|---:|
| 广州校区南校园 | 广州校区东校园 | 30 |
| 广州校区东校园 | 珠海校区 | 90 |
| 广州校区东校园 | 深圳校区 | 120 |
| 广州校区南校园 | 珠海校区 | 120 |
| 广州校区南校园 | 深圳校区 | 150 |
| 广州校区南校园 | 广州校区北校园 | 30 |

这些值用于地点匹配后的通勤时间计算和前端行程提示，不替代固定班车时刻表。
'''
(OUT / USER_COMMUTE_EVIDENCE).write_text(user_commute_evidence, encoding='utf-8')

user_typical_minutes = {
    (SOUTH, EAST): 30,
    (EAST, ZHUHAI): 90,
    (EAST, SHENZHEN): 120,
    (SOUTH, ZHUHAI): 120,
    (SOUTH, SHENZHEN): 150,
    (SOUTH, NORTH): 30,
}
matrix_pairs = [
    (SOUTH, EAST),
    (EAST, SOUTH),
    (SOUTH, NORTH),
    (NORTH, SOUTH),
    (EAST, NORTH),
    (NORTH, EAST),
    (EAST, ZHUHAI),
    (EAST, SHENZHEN),
    (SOUTH, ZHUHAI),
    (SOUTH, SHENZHEN),
]
matrix: list[dict[str, Any]] = []
for a, b in matrix_pairs:
    minutes = user_typical_minutes.get((a, b))
    is_guangzhou_bus_pair = a in {SOUTH, EAST, NORTH} and b in {SOUTH, EAST, NORTH}
    if is_guangzhou_bus_pair:
        route_refs = [CLI_BUS_WORKDAY, CLI_BUS_HOLIDAY]
        transport_mode = 'university_shuttle'
    elif ZHUHAI in {a, b}:
        route_refs = [CLI_QG_ROUTES, CLI_QG_LIST]
        transport_mode = 'intercampus_coach'
    else:
        route_refs = []
        transport_mode = 'intercampus_transfer'
    if minutes is None:
        matrix.append({
            'from_campus_id': a,
            'to_campus_id': b,
            'transport_mode': transport_mode,
            'typical_minutes': None,
            'buffer_minutes': None,
            'minimum_safe_gap_minutes': None,
            'duration_source_type': None,
            'duration_verified_at': None,
            'evidence': route_refs,
            'source_refs': route_refs,
            'confidence': 'partial',
            'note': '已核验固定线路与班次，但当前证据未提供该方向的典型行驶时长。',
        })
        continue
    refs = source_refs(*route_refs, USER_COMMUTE_EVIDENCE)
    matrix.append({
        'from_campus_id': a,
        'to_campus_id': b,
        'transport_mode': transport_mode,
        'typical_minutes': minutes,
        'buffer_minutes': None,
        'minimum_safe_gap_minutes': None,
        'duration_source_type': 'user_confirmed_typical',
        'duration_verified_at': TODAY,
        'evidence': refs,
        'source_refs': refs,
        'confidence': 'partial',
        'note': '用户确认的典型行程时长；不含额外候车或安全缓冲，只适用于当前记录方向。',
    })
transit = {
    'version': '2026_fall_v1.1', 'verified_at': TODAY,
    'campus_bus': {'workday_routes': workday, 'holiday_routes': holiday, 'fare_note': '3元/次，使用校园卡支付。', 'static_boundary': '只固化线路、站点、日期类型和固定发车时刻；不固化运行状态。', 'source_refs': [CLI_BUS_WORKDAY, CLI_BUS_HOLIDAY]},
    'qiguan': {
        'campus_keys': {'zhuhai': ZHUHAI, 'south': SOUTH, 'east': EAST}, 'station_keys': {'zhuhai': 'qg_zhuhai', 'boya': 'qg_boya', 'fifth': 'qg_fifth'}, 'route_keys': ['zhuhai_to_south', 'zhuhai_to_east'],
        'stations': [
            {'id': 'qg_zhuhai', 'campus_id': ZHUHAI, 'canonical_name': '珠海中大岐关服务点', 'aliases': ['珠海中大岐关服务点'], 'location_text': '广东省珠海市香洲区唐家湾镇中山大学（珠海校区）', 'latitude': 22.34756, 'longitude': 113.589353, 'source_refs': [CLI_QG_ROUTES, CLI_QG_LIST], 'verified_at': TODAY, 'confidence': 'verified'},
            {'id': 'qg_boya', 'campus_id': ZHUHAI, 'canonical_name': '博雅苑', 'aliases': ['博雅苑站点'], 'location_text': '珠海校区岐关站点键；详细位置待补官方坐标。', 'latitude': None, 'longitude': None, 'source_refs': [CLI_QG_ROUTES], 'verified_at': TODAY, 'confidence': 'partial'},
            {'id': 'qg_fifth', 'campus_id': ZHUHAI, 'canonical_name': '中大五院正门', 'aliases': ['中大五院正门站点'], 'location_text': '珠海校区岐关站点键；详细位置待补官方坐标。', 'latitude': None, 'longitude': None, 'source_refs': [CLI_QG_ROUTES], 'verified_at': TODAY, 'confidence': 'partial'},
            {'id': 'qg_south', 'campus_id': SOUTH, 'canonical_name': '广中大南校区岐关服务部', 'aliases': ['南门岐关车站'], 'location_text': '南门左边方向前50米的位置岐关车站；广东省广州市海珠区新港街道逸仙路中山大学（广州校区南校园）', 'latitude': 23.092043, 'longitude': 113.297367, 'source_refs': [CLI_QG_ROUTES, CLI_QG_LIST], 'verified_at': TODAY, 'confidence': 'verified'},
            {'id': 'qg_east', 'campus_id': EAST, 'canonical_name': '广中大东校区（大学城）岐关服务部', 'aliases': ['东校区岐关服务部'], 'location_text': '广州校区东校园岐关服务部', 'latitude': 23.061221, 'longitude': 113.388421, 'source_refs': [CLI_QG_ROUTES, CLI_QG_LIST], 'verified_at': TODAY, 'confidence': 'verified'},
        ],
        'routes': [
            {'route_key': 'zhuhai_to_south', 'from_campus_id': ZHUHAI, 'to_campus_id': SOUTH, 'from_station_id': 'qg_zhuhai', 'to_station_id': 'qg_south', 'order_entry_note': '通过岐关服务入口按出行日期查询和下单。', 'source_refs': [CLI_QG_ROUTES, CLI_QG_LIST], 'confidence': 'partial'},
            {'route_key': 'zhuhai_to_east', 'from_campus_id': ZHUHAI, 'to_campus_id': EAST, 'from_station_id': 'qg_zhuhai', 'to_station_id': 'qg_east', 'order_entry_note': '通过岐关服务入口按出行日期查询和下单。', 'source_refs': [CLI_QG_ROUTES, CLI_QG_LIST], 'confidence': 'partial'},
        ],
        'static_boundary': '仅固化校区键、站点键、上下车点和入口说明；不固化日期级班次、价格、座位或运行状态。', 'source_refs': [CLI_QG_ROUTES, CLI_QG_LIST],
    },
    'campus_commute_matrix': matrix,
}
write_json('transit_2026_fall.json', transit)


# ---------- calendar and section times ----------
calendar = {
    'academic_year': '2026-2027', 'term': 'fall', 'term_start': '2026-09-07', 'term_end': '2027-01-17', 'teaching_week_start': '2026-09-07', 'teaching_week_count': 19,
    'holidays': [
        {'name': '中秋节', 'start_date': '2026-09-25', 'end_date': '2026-09-27', 'days': 3, 'note': '按官方校历。'},
        {'name': '国庆节', 'start_date': '2026-10-01', 'end_date': '2026-10-07', 'days': 7, 'note': '按官方校历。'},
        {'name': '元旦', 'start_date': '2027-01-01', 'end_date': '2027-01-01', 'days': 1, 'note': '按官方校历。'},
    ],
    'adjusted_workdays': [{'date': '2026-09-20', 'weekday': '星期日', 'make_up_for': '国庆节假期安排'}, {'date': '2026-10-10', 'weekday': '星期六', 'make_up_for': '国庆节假期安排'}],
    'exam_weeks': [18, 19], 'breaks': [{'name': '寒假', 'start_date': '2027-01-18', 'end_date': '2027-02-21', 'weeks': 5}, {'name': '暑假（前一学年）', 'start_date': '2026-07-13', 'end_date': '2026-09-06', 'note': '用于解释2026年秋季学期起始边界。'}],
    'special_weeks': [{'name': '本科生阅读实践周', 'week': 9}, {'name': '校庆日', 'date': '2026-11-12'}],
    'registration_dates': [{'name': '本科新生报到', 'date': '2026-08-18'}, {'name': '研究生新生报到', 'date': '2026-09-04'}, {'name': '非新生报到注册', 'start_date': '2026-09-05', 'end_date': '2026-09-06'}],
    'source_refs': [CALENDAR_URL, CALENDAR_INDEX_URL, SUMMER_NOTICE_URL], 'verified_at': TODAY, 'confidence': 'verified', 'verification_note': '学期起止、教学周、节假日与考试周以2026-2027官方校历图为准。',
}
write_json('academic_calendar_2026_2027.json', calendar)
section_rows = [(1, '08:00', '08:45'), (2, '08:55', '09:40'), (3, '10:10', '10:55'), (4, '11:05', '11:50'), (5, '14:20', '15:05'), (6, '15:15', '16:00'), (7, '16:30', '17:15'), (8, '17:25', '18:10'), (9, '19:00', '19:45'), (10, '19:55', '20:40'), (11, '20:50', '21:35')]
section_times = {
    'academic_year': '2026-2027', 'term': 'fall', 'campus_id': None,
    'sections': [{'section_number': n, 'start_time': start, 'end_time': end, 'source_refs': [CLI_JWXT_SECTIONS, 'sysu-anything usc classroom sections --json'], 'verified_at': TODAY, 'confidence': 'verified'} for n, start, end in section_rows],
    'break_windows': [{'window_key': 'midday_5_1', 'label': '午间窗口（USC原始节次键5.1）', 'start_time': '12:00', 'end_time': '14:00', 'source_refs': ['sysu-anything usc classroom sections --json'], 'confidence': 'partial'}],
    'source_refs': [CLI_JWXT_SECTIONS, 'sysu-anything usc classroom sections --json'], 'verified_at': TODAY, 'confidence': 'verified', 'verification_note': '标准第1-11节在JWXT 2026-1查询结果与USC节次字典中一致；jwxt status当前学期字段另见缺口。',
}
write_json('section_times_2026_fall.json', section_times)


# ---------- evidence audit ----------
AUDIT_HEADERS = ['dataset', 'record_id', 'field', 'source_type', 'source_url_or_command', 'captured_at', 'confidence', 'note']
def source_type(ref: str) -> str:
    return 'official_web' if ref.startswith('http') else 'sysu_anything_cli' if ref.startswith('sysu-anything') else 'local_evidence'
audit_rows: list[dict[str, Any]] = []
def audit(dataset: str, record_id: str, field: str, ref: str, confidence: str, note: str = '') -> None:
    audit_rows.append({'dataset': dataset, 'record_id': record_id, 'field': field, 'source_type': source_type(ref), 'source_url_or_command': ref, 'captured_at': TODAY, 'confidence': confidence, 'note': note})
for c in campuses:
    for field in ['canonical_name', 'official_address']:
        for ref in c['source_refs']: audit('campuses.v1.json', c['id'], field, ref, c['confidence'], '官方名称/地址与系统校区枚举交叉核验。')
for p in places:
    for ref in p['source_refs']: audit('places.v1.json', p['id'], 'canonical_name/location_text', ref, p['confidence'], p.get('verification_note', ''))
for v in venues:
    for ref in v['source_refs']: audit('venues.v1.json', v['id'], 'canonical_name/capacity', ref, v['confidence'], v.get('verification_note', ''))
for ref in [CLI_BUS_WORKDAY, CLI_BUS_HOLIDAY]: audit('transit_2026_fall.json', 'campus_bus', 'routes/scheduled_departures', ref, 'verified', '从离线班车源清洗，删除运行状态与联系方式。')
for ref in [CLI_QG_ROUTES, CLI_QG_LIST]: audit('transit_2026_fall.json', 'qiguan', 'station_keys/routes', ref, 'partial', '仅保留站点与路线证据，不保留日期级班次字段。')
for item in matrix:
    if item['typical_minutes'] is not None:
        record_id = f"{item['from_campus_id']}->{item['to_campus_id']}"
        audit('transit_2026_fall.json', record_id, 'typical_minutes', USER_COMMUTE_EVIDENCE, 'partial', f"用户确认典型时长为 {item['typical_minutes']} 分钟；方向不自动反推。")
for ref in [CALENDAR_URL, CALENDAR_INDEX_URL, SUMMER_NOTICE_URL]: audit('academic_calendar_2026_2027.json', '2026-2027-fall', 'term_dates/holidays', ref, 'verified', '官方校历与正式通知。')
for ref in [CLI_JWXT_SECTIONS, 'sysu-anything usc classroom sections --json']: audit('section_times_2026_fall.json', 'global', 'sections', ref, 'verified', '标准第1-11节时间一致。')
for rid, ref, note in [
    ('gym_live_inventory', CLI_GYM_PROFILE, '读取检查失败，未写入动态场地参数。'), ('libic_room_inventory', CLI_LIBIC_ROOMS, '站点启动响应非JSON，未写入房间参数。'), ('usc_meeting_south', CLI_USC_MEETING_SOUTH, '返回空列表，未构造南校园会议场地。'), ('usc_classroom_south', CLI_USC_CLASSROOM_SOUTH, '返回CODE_ERROR，未构造南校园动态课室。'), ('usc_activity_rooms', CLI_USC_ACTIVITY_ROOMS, '返回结果仅含东校园/深圳场地，南校园不补造。')]:
    audit('evidence/cli_inventory.md', rid, 'probe_result', ref, 'partial', note)
with (EVIDENCE / 'source_audit.csv').open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=AUDIT_HEADERS); writer.writeheader(); writer.writerows(audit_rows)


# ---------- docs ----------
cli_inventory = f'''# SysU Anything CLI 盘点（南校园优先版）

- 采集日期：{TODAY}
- 可执行文件：`/Users/baihe/.local/bin/sysu-anything`
- 本地项目：`/Users/baihe/Documents/AnythingSYSU`
- 原始只读证据目录：`{RAW}`
- 原则：仅把清洗后的静态字段写入正式数据集；登录检查不写入姓名、学号、余额、课表、Token、Cookie、Session。

## 已执行命令与结果

| 命令 | 结果 | 正式资产用途 |
|---|---|---|
| `{CLI_BUS_WORKDAY}` | 工作日6条线路、61个发车时刻 | 写入广州校区班车静态表 |
| `{CLI_BUS_HOLIDAY}` | 节假日4条线路、8个发车时刻 | 写入广州校区班车静态表 |
| `{CLI_QG_ROUTES}` | 返回珠海/南/东校园键与珠海站点键 | 写入岐关静态字典 |
| `{CLI_QG_LIST}` | 返回站点名称、地址、坐标与路线证据 | 只写入站点与路线键，不写入日期级动态字段 |
| `{CLI_USC_APPS}` | 返回课室、学生活动中心、会议场所3类应用 | 写入来源盘点 |
| `sysu-anything usc schema classroom --json` | 返回课室字段定义 | 写入来源盘点，不构造动态课室 |
| `sysu-anything usc schema activity --json` | 返回活动场地字段定义 | 写入来源盘点 |
| `sysu-anything usc schema meeting --json` | 返回会议场所字段定义 | 写入来源盘点 |
| `sysu-anything usc reserve-config --json` | 返回预约配置元数据 | 写入来源盘点，不写入预约结果 |
| `{CLI_USC_ACTIVITY_ROOMS}` | 返回结果仅见东校园/深圳场地 | 南校园活动场地记录留缺口 |
| `{CLI_USC_MEETING_CAMPUSES}` | 返回5个系统校区名 | 交叉核验五校园 ID |
| `{CLI_USC_CLASSROOM_CAMPUSES}` | 返回5个系统校区名/参数 | 交叉核验五校园 ID |
| `{CLI_USC_MEETING_SOUTH}` | 返回空列表 | 不自行构造南校园动态会议场地 |
| `{CLI_USC_CLASSROOM_SOUTH}` | 返回 `CODE_ERROR` | 不自行构造南校园动态课室 |
| `{CLI_JWXT_STATUS}` | 登录状态正常；状态字段显示2025-2026第2学期第3周 | 只记录为缺口，不写入个人课表 |
| `{CLI_JWXT_SECTIONS}` | 返回11节标准节次，和USC节次时间一致 | 写入节次表 |
| `{CLI_GYM_PROFILE}` | 当前请求链失败 | 只记录体育官网静态场馆，缺少实时参数 ID |
| `sysu-anything gym venue-types --json` | 当前请求链失败 | 不写入动态场地类型 |
| `sysu-anything libic whoami` | 站点启动响应非JSON/请求失败 | 不写入图书馆房间参数 |
| `{CLI_LIBIC_ROOMS}` | 站点启动响应非JSON/请求失败 | 只保留图书馆建筑与官方服务信息 |

## 原始文件

正式包只引用以下原始证据文件的采集结论，不把原始动态字段导入静态资产：

- `bus_workday.json`
- `bus_holiday.json`
- `qg_routes.txt`
- `qg_today_all.json`
- `usc_apps.txt`
- `usc_schema_classroom.txt`
- `usc_schema_activity.txt`
- `usc_schema_meeting.txt`
- `usc_reserve_config.txt`
- `usc_activity_rooms.txt`
- `usc_meeting_campuses.txt`
- `usc_classroom_campuses.txt`
- `usc_meeting_venues_south.txt`
- `usc_classroom_rooms_south.txt`
- `jwxt_section_times_fall_2026.txt`

原始文件位于 `{RAW}`，仅作为证据留存；服务端导入时只读取正式 JSON/CSV 数据集。
'''
(EVIDENCE / 'cli_inventory.md').write_text(cli_inventory, encoding='utf-8')

gaps = '''# 南校园优先版数据缺口与待核对项

| 数据项 | 当前找到的信息 | 缺失/冲突原因 | 候选值 | 推荐值 | 是否需要用户确认 |
|---|---|---|---|---|---|
| 五校园中心坐标 | 官方校园页核验了名称、地址和面积；未给可直接复用的校园中心坐标 | 不推断坐标 | 保持 `null`；后续补官方地图坐标 | 保持 `null`，另行补坐标来源 | 是 |
| 南校园体育实时参数 | 体育官网确认英东体育中心及新体育馆；`gym profile`/venue-types 当前请求链失败 | 未取得系统 venue-type/参数 ID | 仅保留官网场馆静态目录 | 先用官方场馆名，待 CLI 恢复后补参数 | 是 |
| 南校园图书馆研讨室 | 图书馆官网确认南校园图书总馆及楼层服务 | `libic` 站点启动响应非 JSON，无法获得房型/房间参数 | 仅保留图书馆建筑与服务 | 不构造房间；CLI 恢复后再补 | 是 |
| 南校园 USC 会议场地 | `usc meeting venues --campus 南校园` 返回空列表 | 当前系统接口结果为空 | 不新增动态会议场地 | 采用官方公共用房目录的静态场馆，单独标记来源 | 是 |
| 南校园 USC 课室 | 查询返回真实 `CODE_ERROR` | 课室数据源参数/接口异常 | 不构造课室列表 | 保留错误证据，后续重试 | 是 |
| 南校园 USC 学生活动场地 | `usc activity rooms` 当前结果只出现东校园、深圳 | 返回结果没有南校园条目 | 不补造南校园活动场地 | 采用官方公共用房目录中的熊德龙中心/艺术学院楼记录 | 是 |
| 校际班车行驶时长 | 用户已补充6个方向的典型时长：南→东30、东→珠海90、东→深圳120、南→珠海120、南→深圳150、南→北30分钟 | 离线班车源未提供时长；其余方向仍没有用户或官方数据 | 已确认方向写入 `typical_minutes`；其余保持 `null` | 采用用户确认值并保留方向；不自动镜像反向时长 | 是（仅剩余方向） |
| 岐关车日期级班次 | 采集到路线、站点、站点坐标 | `qg list` 是日期级动态数据，不应固化 | 只保留路线键与站点键 | 当前静态包不写班次、价格、座位、状态 | 是 |
| JWXT 当前学期字段 | `jwxt status` 显示2025-2026第2学期第3周；官方校历显示2026-2027秋季学期9月7日开始 | 系统状态与当前日期/目标学期不一致 | 节次采用明确查询的 `2026-1`，学期日期采用官方校历 | 以官方校历为学期权威，保留状态冲突 | 是 |
| 公共用房容量 | 2026官方PDF与2025网页文章在梁銶琚堂、芙兰堂等容量上存在差异 | 文件版本不同 | 2025网页值；2026 PDF值 | 采用2026官方PDF，旧值只作为冲突证据 | 是 |
| 生命科学楼栋号 | 2026官方PDF将生命科学楼1/2号楼均列为408栋；地图/其他资料的楼栋标注需复核 | 可能是楼群统一栋号或目录写法 | 保留PDF原文，不擅自拆分栋号 | 栋号降为可选元数据，不参与主名称匹配或用户展示 | 否（非阻塞） |
| 第三、四教学楼栋号 | 官方教务处核验了名称；当前正式来源未给稳定栋号 | 不足以确认编号 | 空值 | 使用“第三教学楼”“第四教学楼（丰盛堂）”名称匹配，栋号继续留空 | 否（非阻塞） |
| 逸夫楼施工后状态 | 2026年7月正式通知列明494栋逸夫楼施工至8月13日 | 当前采集日仍接近施工结束节点 | 维持名称记录；不写开放状态 | 9月开学前重新核验 | 是 |
| 春晖园食堂 | 学校当前餐饮页面仍列示营业时段；历史通知曾出现阶段性暂停 | 页面和历史通知时点不同 | 当前页面时段；暂停通知 | 静态目录保留，标记 `partial`，开学前复核 | 是 |
| “南校园全部搞齐”的边界 | 已覆盖官方公开建筑、主要教学楼、食堂、体育、活动、博物馆、校门、班车点、公共用房目录 | 未覆盖每间办公室、宿舍、所有普通教室及实时预约结果 | 扩展到全校建筑/房间 | 本版先以可公开核验的公共地点和场馆为完整边界 | 是 |

## 建议用户优先复核

1. 是否还需要补东→北、北→东、东→南、北→南等剩余方向的典型通勤时长。
2. 2026年秋季开学后逸夫楼、春晖园的实际开放状态。
3. 公共用房目录采用2026 PDF版本容量是否符合你的产品口径。
4. 是否需要把校园中心坐标、图书馆房间、体育场馆参数作为第二轮单独采集任务。
'''
(OUT / 'data_gaps.md').write_text(gaps, encoding='utf-8')

confidence_counts: dict[str, int] = {'verified': 0, 'partial': 0, 'unverified': 0}
for collection in [campuses, places, venues]:
    for item in collection: confidence_counts[item.get('confidence', 'unverified')] += 1
for item in workday + holiday + matrix: confidence_counts[item.get('confidence', 'unverified')] += 1
for item in transit['qiguan']['routes']: confidence_counts[item.get('confidence', 'unverified')] += 1
confidence_counts[calendar['confidence']] += 1
confidence_counts[section_times['confidence']] += 1
for item in section_times['sections'] + section_times['break_windows']: confidence_counts[item.get('confidence', 'unverified')] += 1
category_counts: dict[str, int] = {}
for p in places: category_counts[p['category']] = category_counts.get(p['category'], 0) + 1
filled_matrix_count = sum(item['typical_minutes'] is not None for item in matrix)
completeness = f'''# 中山大学校园基础数据资产包 V1.1 完整度报告（南校园优先）

- 生成日期：{TODAY}
- 当前版本：`{BUNDLE_VERSION}`
- 生效边界：2026-2027秋季学期（节次表自2026-09-07起使用）

## 记录数量

| 数据集 | 数量 | 说明 |
|---|---:|---|
| 校区 | {len(campuses)} | 五校园统一ID；名称/地址已核验，坐标待补 |
| 地点 | {len(places)} | 南校园优先；含公交端点和岐关/校门等站点 |
| 场馆 | {len(venues)} | 2026官方公共用房目录、官方体育场馆、教务处有声研讨室 |
| 班车工作日线路 | {len(workday)} | 固定线路与发车时刻 |
| 班车节假日线路 | {len(holiday)} | 固定线路与发车时刻 |
| 岐关静态路线 | {len(transit['qiguan']['routes'])} | 珠海到南/东的路线键与站点 |
| 通勤矩阵 | {len(matrix)} | {filled_matrix_count}个方向已写入用户确认典型时长；其余方向保留空值 |
| 标准节次 | {len(section_times['sections'])} | 第1-11节 |
| 校历 | 1 | 2026-2027秋季学期 |

## 地点类别数量（当前正式地点库）

''' + '\n'.join(f'- `{k}`：{v}' for k, v in sorted(category_counts.items())) + f'''

## 核验状态

- `verified`：{confidence_counts['verified']}
- `partial`：{confidence_counts['partial']}
- `unverified`：{confidence_counts['unverified']}

## 五校园覆盖率

| 校园 | 当前覆盖 | 完整度 |
|---|---|---|
| 广州校区南校园 | 教学楼、图书馆、食堂、体育、活动中心、博物馆、校门、公交站、官方公共用房目录、校历/节次 | 南校园静态公共资产第一版，待补坐标/实时房间参数 |
| 广州校区北校园 | 校区身份、班车端点 | 基础 |
| 广州校区东校园 | 校区身份、班车端点、岐关站点、CLI 场地探测结果 | 基础 |
| 珠海校区 | 校区身份、岐关站点、到南/东路线键 | 基础 |
| 深圳校区 | 校区身份、USC 返回校区枚举 | 基础 |

## 已完成的“南校园全部搞齐”边界

本版把“齐”定义为：当前公开官方来源能够核验的主要教学楼、公共建筑、食堂、体育设施、活动中心、报告厅/会议室/研讨室、校门、班车点、岐关站点、校历与节次。普通办公室、宿舍全量、全部非公开教室、图书馆房间日期级状态、体育日期级状态、USC 日期级场地结果不进入静态包。

## 质量结论

南校园静态名称和公共用房目录已经形成可导入版本；教学楼以名称和别名作为主匹配字段，栋号仅为可选元数据。6个用户确认的方向性通勤时长已写入，剩余高价值不确定项集中在 `data_gaps.md`。
'''
(OUT / 'completeness_report.md').write_text(completeness, encoding='utf-8')


# ---------- manifest ----------
formal_files = ['campuses.v1.json', 'aliases.v1.json', 'places.v1.json', 'venues.v1.json', 'transit_2026_fall.json', 'academic_calendar_2026_2027.json', 'section_times_2026_fall.json', 'evidence/source_audit.csv', 'evidence/cli_inventory.md', USER_COMMUTE_EVIDENCE, 'data_gaps.md', 'completeness_report.md']
record_counts = {'campuses.v1.json': len(campuses), 'aliases.v1.json': len(aliases), 'places.v1.json': len(places), 'venues.v1.json': len(venues), 'transit_2026_fall.json': len(workday) + len(holiday) + len(matrix) + len(transit['qiguan']['routes']), 'academic_calendar_2026_2027.json': 1, 'section_times_2026_fall.json': len(section_times['sections']), 'evidence/source_audit.csv': len(audit_rows), 'evidence/cli_inventory.md': 1, USER_COMMUTE_EVIDENCE: 1, 'data_gaps.md': 1, 'completeness_report.md': 1}
checksums = {rel: hashlib.sha256((OUT / rel).read_bytes()).hexdigest() for rel in formal_files}
unique_sources = {row['source_url_or_command'] for row in audit_rows}
manifest = {'bundle_version': BUNDLE_VERSION, 'schema_version': '1.1.0', 'generated_at': GENERATED_AT, 'effective_from': EFFECTIVE_FROM, 'datasets': [{'file': rel, 'record_count': record_counts[rel]} for rel in formal_files], 'record_counts': record_counts, 'checksums': checksums, 'source_count': len(unique_sources), 'unresolved_gap_count': 13}
write_json('manifest.json', manifest)


# ---------- final package document ----------
final_doc = f'''# 中山大学校园基础数据资产说明 V1.1（南校园优先）

- 版本：`{BUNDLE_VERSION}`
- 生成日期：{TODAY}
- 数据目录：`{OUT}`
- 当前策略：先把南校园公开、可核验的静态地点和公共场馆做成可导入版本，再补动态系统参数与其他校园全量。

## 一、已覆盖范围

### 南校园

- 校门：南门、北门、东门、西门。
- 教学楼：第一至第六教学楼、第五教学楼（逸夫楼）、第四教学楼（丰盛堂）、文科楼、中文堂、外国语学院等；名称和别名是主匹配字段，栋号仅作可选元数据。
- 图书馆：南校园图书馆/图书总馆及官网公开的楼层服务。
- 餐饮：学校当前餐饮页面列示的12个南校园餐饮点及营业时段。
- 体育：英东体育中心、英东体育馆、英东田径运动场、英东网球场、英东综合球类场、英东游泳场、南校园新体育馆。
- 活动与地标：熊德龙学生活动中心、逸夫文化艺术中心、博物馆、校史馆、生物馆、孙中山纪念馆、故居、南草坪等。
- 公共用房：2026年官方公共用房共享共用收费信息汇总表中的南校园报告厅、讲学厅、会议室、课室、研讨室、活动空间和录音棚名称/容量。
- 交通：广州校区工作日/节假日班车；南校园南门停车场、新体育馆西门班车点、南门岐关车站；岐关珠海—南/东路线键与站点；6个用户确认的方向性典型通勤时长。
- 教学时间：2026-2027秋季校历与第1-11节标准节次。

### 其他校园

五校园统一 ID 和官方地址已建立；班车端点、岐关相关站点和系统校区枚举已形成基础层，其他校园的地点/场馆全量留到下一轮。

## 二、证据来源

1. [中山大学校区介绍]({CAMPUS_URL}) 与 [南校园官方地图]({MAP_URL})。
2. [中山大学校历列表]({CALENDAR_INDEX_URL}) 与 [2026-2027学年校历图]({CALENDAR_URL})。
3. [教务处教学/自习空间通知]({JWB_URL})、[教务处教学楼名称页]({JWB_DEPT_URL})。
4. [学校餐饮服务页面]({FOOD_URL})。
5. [中山大学图书馆校园馆舍]({LIB_URL}) 与 [南校园图书馆服务说明]({LIB_BASIC_URL})。
6. [博物馆开放指南]({MUSEUM_URL})。
7. [英东体育中心介绍]({SPORT_URL}) 与 [体育部历史页]({SPORT_HISTORY_URL})。
8. [公共用房共享共用收费信息汇总表说明页]({ROOM_ARTICLE_URL}) 及对应 [2026官方PDF]({ROOM_PDF_URL})。
9. 本地 `sysu-anything` 只读命令，具体命令和输出摘要见 `evidence/cli_inventory.md`。
10. 用户于2026-08-11确认的6个方向性通勤典型时长，原始归一化记录见 `evidence/user_confirmed_commute_times_2026-08-11.md`。

## 三、静态与实时边界

正式数据集只写入稳定名称、地址、坐标（有证据时）、固定班车时刻、典型通勤时长、官方公共目录容量、校历和节次。岐关日期级班次、实时座位/状态、体育场馆日期级空闲、图书馆房间日期级空闲、USC 日期级场地结果不写入静态包。

## 四、文件结构

- `campuses.v1.json`：五校园稳定 ID、名称、地址与别名。
- `aliases.v1.json`：校区名称归一化。
- `places.v1.json`：地点库。
- `venues.v1.json`：静态场馆/会议室/研讨室目录。
- `transit_2026_fall.json`：班车、岐关静态字典、通勤矩阵。
- `academic_calendar_2026_2027.json`：学期、节假日、教学周和考试周。
- `section_times_2026_fall.json`：第1-11节时间。
- `evidence/source_audit.csv`：字段级证据审计。
- `evidence/cli_inventory.md`：CLI 盘点与真实限制。
- `evidence/user_confirmed_commute_times_2026-08-11.md`：用户确认的通勤时长及分钟归一化记录。
- `data_gaps.md`：冲突、缺失、候选值和推荐值。
- `completeness_report.md`：范围与完整度。
- `manifest.json`：版本、数量和校验和。

## 五、服务端导入建议

建议按 `campus_id`、`place_id`、`venue_id` 建三张维表，保留 `bundle_version`、`verified_at`、`confidence` 和 `source_refs`；交通、校历、节次作为版本化快照表。动态系统只在行动代理执行前临时查询，查询结果不要回写本静态包。

## 六、每学期更新方法

1. 先更新官方校历与节次，并记录系统命令的学年学期参数。
2. 再更新公共用房目录、教学处自习/研讨空间和体育/图书馆的参数元数据。
3. 重新采集班车工作日/节假日源，岐关只更新路线键和站点字典。
4. 运行 `python3 /Users/baihe/Documents/compusone/scripts/validate_sysu_reference.py`。
5. 通过 `manifest.json` 校验和导入新版本，旧版本保留回滚。

## 七、用户复核清单

- 剩余方向的典型通勤时长（如东→北、北→东、东→南、北→南）。
- 逸夫楼施工后的开放状态。
- 春晖园当前营业状态。
- 公共用房容量采用2026 PDF还是旧网页版本。
- 是否补充校园中心坐标、图书馆房间参数和体育场馆参数。
'''
DOCS.mkdir(parents=True, exist_ok=True)
(DOCS / '08_中山大学校园基础数据资产说明.md').write_text(final_doc, encoding='utf-8')

print(json.dumps({'out': str(OUT), 'campuses': len(campuses), 'aliases': len(aliases), 'places': len(places), 'venues': len(venues), 'workday_routes': len(workday), 'holiday_routes': len(holiday), 'matrix': len(matrix), 'sections': len(section_times['sections']), 'audit_rows': len(audit_rows), 'sources': len(unique_sources), 'confidence_counts': confidence_counts}, ensure_ascii=False, indent=2))
