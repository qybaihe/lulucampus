from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = ROOT / "data" / "reference" / "sysu"


def load_json(filename: str) -> dict:
    return json.loads((REFERENCE_ROOT / filename).read_text(encoding="utf-8"))


def test_user_confirmed_commute_durations_are_directional_and_normalized():
    transit = load_json("transit_2026_fall.json")
    matrix = {
        (item["from_campus_id"], item["to_campus_id"]): item
        for item in transit["campus_commute_matrix"]
    }
    expected = {
        ("guangzhou_south", "guangzhou_east"): 30,
        ("guangzhou_east", "zhuhai"): 90,
        ("guangzhou_east", "shenzhen"): 120,
        ("guangzhou_south", "zhuhai"): 120,
        ("guangzhou_south", "shenzhen"): 150,
        ("guangzhou_south", "guangzhou_north"): 30,
    }

    assert len(matrix) == len(transit["campus_commute_matrix"]) == 10
    assert {
        pair: item["typical_minutes"]
        for pair, item in matrix.items()
        if item["typical_minutes"] is not None
    } == expected
    for pair in expected:
        item = matrix[pair]
        assert item["duration_source_type"] == "user_confirmed_typical"
        assert item["duration_verified_at"] == "2026-08-11"
        assert item["buffer_minutes"] is None
        assert item["minimum_safe_gap_minutes"] is None

    # The user supplied one direction for each pair; reverse values are not inferred.
    assert matrix[("guangzhou_east", "guangzhou_south")]["typical_minutes"] is None
    assert matrix[("guangzhou_north", "guangzhou_south")]["typical_minutes"] is None


def test_reference_bundle_names_and_manifest_checksums():
    places = {item["id"]: item for item in load_json("places.v1.json")["places"]}
    assert places["teaching_1"]["canonical_name"] == "第一教学楼"
    assert places["teaching_2"]["canonical_name"] == "第二教学楼"
    assert places["teaching_5"]["canonical_name"] == "第五教学楼（逸夫楼）"
    assert places["teaching_6"]["canonical_name"] == "第六教学楼"

    manifest = load_json("manifest.json")
    assert manifest["bundle_version"] == "sysu-campus-reference-v1.1-south-first"
    assert manifest["schema_version"] == "1.1.0"
    assert manifest["record_counts"]["transit_2026_fall.json"] == 22
    assert manifest["record_counts"]["evidence/source_audit.csv"] == 468
    for filename, expected_hash in manifest["checksums"].items():
        actual_hash = hashlib.sha256((REFERENCE_ROOT / filename).read_bytes()).hexdigest()
        assert actual_hash == expected_hash
