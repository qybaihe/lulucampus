#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UDID="${SIMULATOR_UDID:-5BEE7D9F-B906-43B3-A508-2930BB4EFAF3}"
cd "$ROOT"
xcodegen generate
xcodebuild -project OneMore.xcodeproj -scheme OneMore -configuration Debug \
  -destination "platform=iOS Simulator,id=$UDID" -derivedDataPath .derived test

