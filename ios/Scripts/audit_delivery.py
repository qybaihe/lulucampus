#!/usr/bin/env python3
"""Deterministic delivery, privacy-boundary, asset, and evidence audit."""

from __future__ import annotations

import hashlib
import json
import plistlib
import re
import sys
from pathlib import Path


IOS = Path(__file__).resolve().parents[1]
ROOT = IOS.parent
OUT = IOS / "artifacts" / "logs" / "delivery-audit.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    assertions: list[dict[str, object]] = []

    def require(name: str, condition: bool, detail: object) -> None:
        assertions.append({"name": name, "passed": bool(condition), "detail": detail})

    swift_files = sorted((IOS / "OneMore").rglob("*.swift"))
    swift = "\n".join(path.read_text() for path in swift_files)
    require("native_swiftui", "import SwiftUI" in swift and "WKWebView" not in swift and "import WebKit" not in swift, {"swift_files": len(swift_files)})

    screen_source = (IOS / "OneMore/Features/PrototypeGallery/PrototypeScreenID.swift").read_text()
    case_values = re.findall(r'case\s+\w+\s*=\s*"([A-Z0-9.]+)"', screen_source)
    # Lines with multiple cases need a broader literal count.  Restrict the
    # scan to PrototypeScreenID itself: PrototypeScreenGroup also defines an
    # earlier `var id`, which would otherwise truncate the catalog to zero.
    screen_enum = screen_source.split("enum PrototypeScreenID:", 1)[1]
    enum_prefix = screen_enum.split("var id:", 1)[0]
    all_ids = re.findall(r'=\s*"([A-Z]+[0-9.]*(?:[0-9])?|MSG)"', enum_prefix)
    all_ids = list(dict.fromkeys(all_ids))
    require("screen_catalog_74_plus_2", len(all_ids) == 76 and {"B12.2", "MSG"}.issubset(all_ids), {"count": len(all_ids)})

    screen_map = IOS / "SCREEN_MAP.md"
    map_text = screen_map.read_text() if screen_map.exists() else ""
    missing_map = [item for item in all_ids if f"| {item} |" not in map_text]
    require("screen_map_complete", screen_map.exists() and not missing_map, {"missing": missing_map})

    registry_source = (IOS / "OneMore/Core/DeepLink/FormalNodeRegistry.swift").read_text()
    formal_enum = registry_source.split("enum FormalNodeID:", 1)[1].split("enum FormalNodeTrigger:", 1)[0]
    enum_pairs = re.findall(r'\b(\w+)\s*=\s*"([A-Z][A-Z0-9.]*)"', formal_enum)
    enum_id_by_case = dict(enum_pairs)
    registry_rows = re.findall(
        r'^\s*d\(\.(\w+),\s*"([^"]+)",\s*\.(app|route|serverState|systemEvent)\((.+)\),\s*"([^"]+)"\),?$',
        registry_source,
        re.MULTILINE,
    )
    registry_ids = [enum_id_by_case.get(case_name, f"UNKNOWN:{case_name}") for case_name, *_ in registry_rows]
    registry_identifiers = [identifier for *_, identifier in registry_rows]
    require(
        "formal_node_registry_74_ids_69_runtime_identifiers",
        len(enum_pairs) == 74
        and len(registry_rows) == 74
        and len(set(registry_ids)) == 74
        and set(registry_ids) == set(enum_id_by_case.values())
        and len(set(registry_identifiers)) == 69,
        {
            "enum_ids": len(enum_pairs),
            "definitions": len(registry_rows),
            "unique_definition_ids": len(set(registry_ids)),
            "unique_runtime_identifiers": len(set(registry_identifiers)),
        },
    )

    formal_table = map_text.split("## 74 个正式节点", 1)[1].split("## 返回稿额外组合态", 1)[0] if "## 74 个正式节点" in map_text and "## 返回稿额外组合态" in map_text else ""
    formal_map_ids = re.findall(
        r'^\|\s*([A-Z]+[0-9]+(?:\.[0-9]+)?)\s*\|',
        formal_table,
        re.MULTILINE,
    )
    formal_map_counts = {item: formal_map_ids.count(item) for item in set(formal_map_ids)}
    require(
        "formal_screen_map_exactly_once",
        len(formal_map_ids) == 74
        and set(formal_map_ids) == set(registry_ids)
        and all(count == 1 for count in formal_map_counts.values()),
        {
            "rows": len(formal_map_ids),
            "missing": sorted(set(registry_ids) - set(formal_map_ids)),
            "extra": sorted(set(formal_map_ids) - set(registry_ids)),
            "duplicates": sorted(item for item, count in formal_map_counts.items() if count != 1),
        },
    )

    composite_table = map_text.split("## 返回稿额外组合态", 1)[1].split("## 36 张返回画板映射", 1)[0] if "## 返回稿额外组合态" in map_text and "## 36 张返回画板映射" in map_text else ""
    composite_ids = re.findall(
        r'^\|\s*([A-Z]+[0-9]+(?:\.[0-9]+)?|MSG)\s*\|',
        composite_table,
        re.MULTILINE,
    )
    require(
        "returned_composites_separate_exactly_once",
        composite_ids == ["B12.2", "MSG"],
        {"rows": composite_ids},
    )

    openapi_path = ROOT / "openapi/onemore.openapi.json"
    openapi_paths = set(json.loads(openapi_path.read_text())["paths"]) if openapi_path.exists() else set()
    normalize_endpoint = lambda value: re.sub(r"\{[^/]+\}", "{}", value)
    normalized_openapi_paths = {normalize_endpoint(path) for path in openapi_paths}
    server_endpoints: dict[str, str] = {}
    for case_name, _title, trigger_kind, trigger_arguments, _identifier in registry_rows:
        if trigger_kind != "serverState":
            continue
        endpoint_match = re.search(r'endpoint:\s*"([^"]+)"', trigger_arguments)
        if endpoint_match:
            server_endpoints[enum_id_by_case[case_name]] = endpoint_match.group(1)
    missing_normalized = {
        node_id: endpoint
        for node_id, endpoint in server_endpoints.items()
        if normalize_endpoint(endpoint) not in normalized_openapi_paths
    }
    inexact_placeholders = {
        node_id: endpoint
        for node_id, endpoint in server_endpoints.items()
        if endpoint not in openapi_paths
    }
    require(
        "formal_server_state_endpoints_match_frozen_openapi",
        bool(server_endpoints) and not missing_normalized and not inexact_placeholders,
        {
            "server_state_nodes": len(server_endpoints),
            "openapi_paths": len(openapi_paths),
            "missing_normalized": missing_normalized,
            "inexact_placeholders": inexact_placeholders,
        },
    )
    require(
        "no_false_74_direct_launch_claim",
        "testAllSeventyFourFormalNodesAndTwoCompositesDirectLaunch" not in map_text
        and not re.search(r"74[^\n]{0,80}(?:prototype|原型)[^\n]{0,40}(?:direct launch|直启)", map_text, re.IGNORECASE),
        "SCREEN_MAP distinguishes production reachability from the 36-board fidelity harness",
    )

    design_manifest = json.loads((ROOT / "design/received/2026-08-11-one-more-mobile-prototype/SOURCE_MANIFEST.json").read_text())
    expected_screens = {Path(item["path"]).name for item in design_manifest["screens"]["screenshotFiles"]}
    runtime_screens = {path.name for path in (IOS / "artifacts/screenshots/runtime").glob("*.png")}
    require("returned_runtime_screens_36", len(expected_screens) == 36 and runtime_screens == expected_screens, {"expected": len(expected_screens), "actual": len(runtime_screens), "missing": sorted(expected_screens - runtime_screens)})

    state_names = {path.stem for path in (IOS / "artifacts/screenshots/states").glob("*.png")}
    expected_states = {"loading", "empty", "network-error", "offline", "permission-denied", "session-expired", "duplicate-tap", "stale-state"}
    require("runtime_exception_states_8", state_names == expected_states, {"states": sorted(state_names)})

    source_ip = ROOT / "assets/ip/selected/aiia-pink-girl-business-v1"
    source_manifest = json.loads((source_ip / "frames/frames-manifest.json").read_text())
    resource_manifest = json.loads((IOS / "OneMore/Resources/azou-frames-manifest.json").read_text())
    frame_errors: list[str] = []
    for state in source_manifest["states"]:
        state_name = state["state"].replace("-", "_")
        for frame in state["frames"]:
            target = IOS / "OneMore/Resources/AzouFrames" / f"azou_{state_name}_{frame['index']:02d}.png"
            if not target.exists() or sha256(target) != frame["sha256"]:
                frame_errors.append(str(target))
    frame_files = list((IOS / "OneMore/Resources/AzouFrames").glob("*.png"))
    require("azou_frames_57_checksums", len(frame_files) == 57 and not frame_errors and resource_manifest["frameCount"] == 57, {"count": len(frame_files), "errors": frame_errors})

    motion = json.loads((IOS / "OneMore/Resources/azou-motion-contract.json").read_text())
    motion_source = (IOS / "OneMore/Core/Motion/AzouMotion.swift").read_text()
    feature_source = "\n".join(path.read_text() for path in (IOS / "OneMore/Features").rglob("*.swift")) + (IOS / "OneMore/App/OneMoreApp.swift").read_text()
    raw_events = [rule["event"] for rule in motion["eventRules"]]
    swift_case = {
        "azou.entry.first-visible": "firstVisible",
        "intent.input.focused": "intentFocused",
        "intent.compile.started": "intentCompileStarted",
        "intent.published": "intentPublished",
        "gathering.tentative": "gatheringTentative",
        "action.preview.ready": "previewReady",
        "action.execute.started": "executeStarted",
        "action.execute.succeeded": "executeSucceeded",
        "action.execute.failed": "executeFailed",
        "gathering.backfill.started": "backfillStarted",
        "gathering.pooling.expired.visible": "poolingExpired",
        "chat.azou.mentioned": "azouMentioned",
        "chat.azou.response.completed": "azouResponseCompleted",
        "chat.human.bidirectional-started": "humanConversationStarted",
    }
    missing_triggers = [event for event in raw_events if f"trigger(.{swift_case[event]}" not in feature_source]
    require("azou_9_states_14_bound_events", len(motion["rows"]) == 9 and len(raw_events) == 14 and not missing_triggers and "maxWidth: CGFloat = 170" in motion_source, {"states": len(motion["rows"]), "events": len(raw_events), "missing_triggers": missing_triggers})

    videos = [IOS / "artifacts/motion/azou-execute-failed.mp4", IOS / "artifacts/motion/azou-execute-succeeded.mp4"]
    require("motion_runtime_evidence", all(path.exists() and path.stat().st_size > 500_000 for path in videos), {"files": {path.name: path.stat().st_size if path.exists() else 0 for path in videos}})

    release_plist = plistlib.loads((IOS / "Config/Info-Release.plist").read_bytes())
    release_config = (IOS / "Config/Release.xcconfig").read_text()
    require("release_no_dev_happy_path", "https:" in release_config and "wss:" in release_config and "DEV_AUTH_ENABLED = NO" in release_config and "DevUserID" not in release_plist and "NSAppTransportSecurity" not in release_plist, {"api": "https", "websocket": "wss", "dev_auth": False})

    entitlements = plistlib.loads((IOS / "OneMore/Resources/OneMore.entitlements").read_bytes())
    require("apns_and_universal_link_entitlements", "aps-environment" in entitlements and "com.apple.developer.associated-domains" in entitlements, sorted(entitlements))

    forbidden_source = {
        "sysu_cli_process": r"Process\s*\(|sysu-anything",
        "webview": r"WKWebView|import\s+WebKit",
        "match_score": r"matchScore|computeMatch|calculateMatch",
        "raw_academic_fields": r"\b(gpa|gradePoint|otherUserSchedule|classmateList)\b",
    }
    violations = {name: bool(re.search(pattern, swift, re.IGNORECASE)) for name, pattern in forbidden_source.items()}
    require("privacy_forbidden_implementations_absent", not any(violations.values()), violations)
    require(
        "pooling_identity_and_count_hidden",
        "item.status != .pooling" in swift and "let memberCount = item.memberCount" in swift,
        "server status controls disclosure; pooling cards omit member counts without didactic copy",
    )

    empty_action_patterns = [r"action:\s*\{\s*\}", r"Button\s*\{\s*\}\s*label", r"Button\([^\n]*action:\s*\{\s*\}\)"]
    empty_hits = [pattern for pattern in empty_action_patterns if re.search(pattern, swift)]
    require("no_empty_button_closures", not empty_hits, empty_hits)

    competition_snapshot = json.loads((ROOT / "fixtures/competition_snapshot_2026-08-11_v1.1.json").read_text())
    competition_rows = competition_snapshot.get("competitions") or competition_snapshot.get("items") or []
    require("competition_fixture_24_no_demo", len(competition_rows) == 24 and "demo-innovation-2026" not in json.dumps(competition_rows), {"count": len(competition_rows)})

    sysu_manifest = json.loads((IOS / "OneMore/Resources/SYSU/sysu-manifest.json").read_text())
    require("sysu_versioned_bundle", sysu_manifest["bundle_version"] == "sysu-campus-reference-v1.1-south-first" and sysu_manifest["unresolved_gap_count"] == 13 and "loadAndValidate" in swift, {"bundle_version": sysu_manifest["bundle_version"], "unresolved_gaps": sysu_manifest["unresolved_gap_count"]})

    system_tokens = ["requestFullAccessToEvents", "registerForRemoteNotifications", "ShareLink", "requestVoice", "PHPickerViewController", "requestOneShotLocation", ".onOpenURL"]
    missing_system = [token for token in system_tokens if token not in swift]
    require("system_capabilities_wired", not missing_system, {"missing": missing_system})

    docs = [
        IOS / "APP_METADATA.json", IOS / "SCREEN_MAP.md", IOS / "SERVICE_MAP.md", IOS / "BUILD_NOTES.md", IOS / "README.md",
        ROOT / "docs/handoffs/gemini-ui-handoff.md", ROOT / "docs/TEST_LOOP.md", ROOT / "docs/TEST_RESULTS.md", ROOT / "docs/TEST_NEXT_STEPS.md",
        IOS / "FIDELITY_REVIEW.md", IOS / "FIDELITY_CHECKLIST.md", IOS / "FIDELITY_NEXT_STEPS.md",
    ]
    require("required_documents", all(path.exists() and path.stat().st_size > 100 for path in docs), {"missing": [str(path) for path in docs if not path.exists() or path.stat().st_size <= 100]})

    failed = [item for item in assertions if not item["passed"]]
    report = {"schema_version": 1, "result": "passed" if not failed else "failed", "assertion_count": len(assertions), "failed_count": len(failed), "assertions": assertions}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{report['result'].upper()}: {len(assertions) - len(failed)}/{len(assertions)} assertions -> {OUT}")
    if failed:
        for item in failed: print(f"- {item['name']}: {item['detail']}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
