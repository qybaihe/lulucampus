#!/usr/bin/env bash
# Build GitHub Release artifacts: unsigned device IPA + iPhone Simulator zip.
# The IPA talks to the production API in Config/Release.xcconfig.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IOS="$ROOT/ios"
VERSION="${MARKETING_VERSION:-1.0.0}"
OUT="${OUT_DIR:-$ROOT/dist/github-release}"
ARCHIVE="$OUT/LuluCampus-$VERSION.xcarchive"
IPA="$OUT/LuluCampus-$VERSION.ipa"
SIM_ZIP="$OUT/LuluCampus-$VERSION-iphonesimulator.zip"
DERIVED_DEVICE="$IOS/.derived-release-device"
DERIVED_SIM="$IOS/.derived-release"
SIM_UDID="${SIMULATOR_UDID:-5BEE7D9F-B906-43B3-A508-2930BB4EFAF3}"

mkdir -p "$OUT"
cd "$IOS"
command -v xcodegen >/dev/null
xcodegen generate

echo "==> Archive Release (unsigned device IPA)"
xcodebuild \
  -project OneMore.xcodeproj \
  -scheme OneMore \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath "$ARCHIVE" \
  -derivedDataPath "$DERIVED_DEVICE" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY=- \
  archive

APP="$(find "$ARCHIVE/Products/Applications" -maxdepth 1 -name '*.app' -print -quit)"
test -n "$APP" && test -d "$APP"

STAGE="$(mktemp -d)"
mkdir -p "$STAGE/Payload"
cp -R "$APP" "$STAGE/Payload/"
(
  cd "$STAGE"
  /usr/bin/zip -qry "$IPA" Payload
)
rm -rf "$STAGE"

echo "==> Build Release iPhone Simulator"
xcodebuild \
  -project OneMore.xcodeproj \
  -scheme OneMore \
  -configuration Release \
  -destination "platform=iOS Simulator,id=$SIM_UDID" \
  -derivedDataPath "$DERIVED_SIM" \
  build

SIM_APP="$DERIVED_SIM/Build/Products/Release-iphonesimulator/ONE MORE.app"
test -d "$SIM_APP"
ditto -c -k --keepParent "$SIM_APP" "$SIM_ZIP"

python3 - <<PY
import json, os, plistlib, pathlib, hashlib
out = pathlib.Path("$OUT")
ipa = pathlib.Path("$IPA")
sim = pathlib.Path("$SIM_ZIP")
info_path = pathlib.Path("$APP") / "Info.plist"
info = plistlib.loads(info_path.read_bytes())
def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
manifest = {
    "name": info.get("CFBundleDisplayName") or info.get("CFBundleName"),
    "bundle_id": info.get("CFBundleIdentifier"),
    "version": info.get("CFBundleShortVersionString"),
    "build": str(info.get("CFBundleVersion")),
    "api_base_url": info.get("APIBaseURL"),
    "websocket_base_url": info.get("WebSocketBaseURL"),
    "minimum_os": "17.0",
    "ipa": ipa.name,
    "ipa_bytes": ipa.stat().st_size,
    "ipa_sha256": sha256(ipa),
    "simulator_zip": sim.name,
    "simulator_bytes": sim.stat().st_size,
    "simulator_sha256": sha256(sim),
}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=2, ensure_ascii=False))
PY

echo "==> Artifacts in $OUT"
ls -lh "$IPA" "$SIM_ZIP" "$OUT/manifest.json"
