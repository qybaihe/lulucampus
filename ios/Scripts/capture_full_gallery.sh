#!/usr/bin/env bash
# 全量生产页面截图：74 正式节点 + 实体深链 + 5 主 Tab，供 HTML 画廊使用。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIMULATOR_UDID="${SIMULATOR_UDID:-5BEE7D9F-B906-43B3-A508-2930BB4EFAF3}"
APP_PATH="${APP_PATH:-$HOME/Library/Developer/Xcode/DerivedData/OneMore-fmhtiljszzeeapcjnmjpjxaxrjsh/Build/Products/Debug-iphonesimulator/ONE MORE.app}"
BUNDLE_ID="com.onemore.campus.dev"
OUT_DIR="$ROOT/artifacts/screenshots/gallery"
mkdir -p "$OUT_DIR"

xcrun simctl boot "$SIMULATOR_UDID" >/dev/null 2>&1 || true
xcrun simctl install "$SIMULATOR_UDID" "$APP_PATH"

capture() { # $1=文件名 $2...=launch args
  local name="$1"; shift
  xcrun simctl terminate "$SIMULATOR_UDID" "$BUNDLE_ID" >/dev/null 2>&1 || true
  xcrun simctl launch "$SIMULATOR_UDID" "$BUNDLE_ID" --args \
    -UI_TESTING YES -DevUserIDOverride u_demo_1 \
    -UIAccessibilityReduceMotionEnabled YES "$@" >/dev/null
  sleep 5
  xcrun simctl io "$SIMULATOR_UDID" screenshot --type=png "$OUT_DIR/$name.png" >/dev/null
  echo "captured $name"
}

NODES=(
  A1 A2 A3 A4 A5 A6 A7 A8
  B1 B2 B3 B3.1 B4 B4.1 B5 B5.1 B6 B6.1 B7 B7.1 B8 B9 B10 B11 B12 B12.1
  C1 C2 C3 C4
  D1 D2 D3 D3.1 D3.2 D3.3 D3.4 D4
  E1 E2 E3 E4 E5 E6 E7 E8 E9 E10 E11 E12 E13 E14 E15 E16 E17
  M1 M2 M3 M4 M5 M6 M7 M8 M9 M10
  O1 O2 O3 O4
  G1 G2 G3 G4 G5
)

for id in "${NODES[@]}"; do
  capture "$id" -ProductionScreenID "$id"
done

# 实体页用种子数据深链重拍（覆盖占位版本）
capture "B12.1" -ProductionDeepLink "onemore://competition/1a45ef2a-454b-46b4-adbf-a0064bcc0788"
capture "E3"    -ProductionDeepLink "onemore://gathering/4c50803a-5c34-4438-9471-68c7b5272e29"
capture "E16"   -ProductionDeepLink "onemore://relation/d72fc369-8c38-4849-b6b2-e636bbb2870f"
capture "E14"   -ProductionDeepLink "onemore://channel/099982ee-1048-4d9e-b0c1-fe12c84d45e9"

# 五个主 Tab（带底栏）
capture "TAB-today"        -InitialTab today
capture "TAB-competitions" -InitialTab competitions
capture "TAB-create"       -InitialTab create
capture "TAB-messages"     -InitialTab messages
capture "TAB-profile"      -InitialTab profile

xcrun simctl terminate "$SIMULATOR_UDID" "$BUNDLE_ID" >/dev/null 2>&1 || true
echo "DONE: $(ls "$OUT_DIR" | wc -l) screenshots in $OUT_DIR"
