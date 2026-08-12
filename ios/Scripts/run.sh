#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UDID="${SIMULATOR_UDID:-5BEE7D9F-B906-43B3-A508-2930BB4EFAF3}"
APP="$ROOT/.derived/Build/Products/Debug-iphonesimulator/ONE MORE.app"
"$ROOT/Scripts/build.sh"
xcrun simctl boot "$UDID" 2>/dev/null || true
xcrun simctl bootstatus "$UDID" -b
xcrun simctl install "$UDID" "$APP"
xcrun simctl launch --terminate-running-process "$UDID" com.onemore.campus.dev

