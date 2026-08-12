#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="$(cd "$ROOT/.." && pwd)"
SIMULATOR_UDID="${SIMULATOR_UDID:-5BEE7D9F-B906-43B3-A508-2930BB4EFAF3}"
APP_PATH="${APP_PATH:-/tmp/onemore-root-dd-e2e-r1/Build/Products/Debug-iphonesimulator/ONE MORE.app}"
BUNDLE_ID="com.onemore.campus.dev"
ROUND="${ROUND:-4}"

RUNTIME_DIR="$ROOT/artifacts/screenshots/runtime"
STATE_DIR="$ROOT/artifacts/screenshots/states"
RUNTIME_CSV="$ROOT/artifacts/logs/runtime-screenshot-capture.csv"
STATE_CSV="$ROOT/artifacts/logs/state-evidence-capture.csv"
mkdir -p "$RUNTIME_DIR" "$STATE_DIR" "$ROOT/artifacts/logs"

xcrun simctl boot "$SIMULATOR_UDID" >/dev/null 2>&1 || true
xcrun simctl bootstatus "$SIMULATOR_UDID" -b
xcrun simctl install "$SIMULATOR_UDID" "$APP_PATH"

printf 'prototype_id,design_node,pid,file,round,timestamp_utc\n' > "$RUNTIME_CSV"
while IFS=$'\t' read -r prototype_id design_node; do
  xcrun simctl terminate "$SIMULATOR_UDID" "$BUNDLE_ID" >/dev/null 2>&1 || true
  launch_output="$(xcrun simctl launch "$SIMULATOR_UDID" "$BUNDLE_ID" --args \
    -UI_TESTING YES -UIAccessibilityReduceMotionEnabled YES \
    -PrototypeScreenID "$design_node")"
  pid="${launch_output##*: }"
  sleep 1
  xcrun simctl io "$SIMULATOR_UDID" screenshot --type=png \
    "$RUNTIME_DIR/$prototype_id.png" >/dev/null
  printf '%s,%s,%s,%s,%s,%s\n' \
    "$prototype_id" "$design_node" "$pid" \
    "artifacts/screenshots/runtime/$prototype_id.png" "$ROUND" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$RUNTIME_CSV"
done < <(python3 - "$WORKSPACE/design/received/2026-08-11-one-more-mobile-prototype/SOURCE_MANIFEST.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
for screen in manifest["screens"]["map"]:
    print(f'{screen["prototype_id"]}\t{screen["design_node"]}')
PY
)

runtime_files=()
while IFS= read -r file; do
  runtime_files+=("$file")
done < <(python3 - "$RUNTIME_CSV" "$RUNTIME_DIR" <<'PY'
import csv
import sys

with open(sys.argv[1], newline="") as handle:
    for row in csv.DictReader(handle):
        print(f'{sys.argv[2]}/{row["prototype_id"]}.png')
PY
)
magick montage "${runtime_files[@]}" -thumbnail '180x390>' \
  -font /System/Library/Fonts/SFNS.ttf \
  -background '#010001' -gravity center -tile 6x6 -geometry 190x475+0+0 \
  "$ROOT/artifacts/screenshots/RUNTIME_CONTACT_SHEET.png"

states=(loading empty network-error offline permission-denied session-expired duplicate-tap stale-state)
printf 'state,pid,file,round,timestamp_utc\n' > "$STATE_CSV"
state_files=()
for state in "${states[@]}"; do
  xcrun simctl terminate "$SIMULATOR_UDID" "$BUNDLE_ID" >/dev/null 2>&1 || true
  launch_output="$(xcrun simctl launch "$SIMULATOR_UDID" "$BUNDLE_ID" --args \
    -UI_TESTING YES -UIAccessibilityReduceMotionEnabled YES -StateEvidence "$state")"
  pid="${launch_output##*: }"
  sleep 1
  file="$STATE_DIR/$state.png"
  xcrun simctl io "$SIMULATOR_UDID" screenshot --type=png "$file" >/dev/null
  state_files+=("$file")
  printf '%s,%s,%s,%s,%s\n' "$state" "$pid" \
    "artifacts/screenshots/states/$state.png" "$ROUND" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$STATE_CSV"
done
magick montage "${state_files[@]}" -thumbnail '222x481>' \
  -font /System/Library/Fonts/SFNS.ttf \
  -background '#010001' -gravity center -tile 4x2 -geometry 232x562+0+0 \
  "$ROOT/artifacts/screenshots/STATE_EVIDENCE_CONTACT_SHEET.png"

xcrun simctl terminate "$SIMULATOR_UDID" "$BUNDLE_ID" >/dev/null 2>&1 || true
printf 'Captured 36 runtime boards and 8 state boards on %s (round %s).\n' \
  "$SIMULATOR_UDID" "$ROUND"
