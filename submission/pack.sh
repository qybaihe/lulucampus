#!/usr/bin/env bash
# Build the 5 judge-facing zip packages. Never copies .env, cookies, or campus sessions.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OVERLAY="$ROOT/submission/overlay"
STAGE="$ROOT/submission/stage"
ZIPS="$ROOT/submission/zips"
SYSU="/Users/baihe/Documents/AnythingSYSU"

RSYNC=(rsync -a --delete --prune-empty-dirs)
COMMON_EXCLUDES=(
  --exclude '.git/'
  --exclude '.gitignore'
  --exclude '.DS_Store'
  --exclude '.env'
  --exclude '.env.*'
  --exclude '.edgeone/'
  --exclude '.edgeone.zip'
  --exclude 'node_modules/'
  --exclude '.venv/'
  --exclude '__pycache__/'
  --exclude '*.py[cod]'
  --exclude '.mypy_cache/'
  --exclude '.pytest_cache/'
  --exclude '.ruff_cache/'
  --exclude '*.log'
)

die() { echo "ERROR: $*" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p "$STAGE" "$ZIPS"

P01="$STAGE/01-Skill-SYSU-Anything"
P02="$STAGE/02-Skill-抖音兴趣画像"
P03="$STAGE/03-Agent-Workflow-噜噜成局"
P04="$STAGE/04-Source-噜噜成局源码"
P05="$STAGE/05-Art-噜噜美术资产"
mkdir -p "$P01" "$P02" "$P03" "$P04" "$P05"

echo "==> 01 SYSU Anything Skill"
for item in README.md LICENSE package.json package-lock.json tsconfig.json \
  src dist bin data skills install scripts docs assets; do
  if [[ -e "$SYSU/$item" ]]; then
    "${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" "$SYSU/$item" "$P01/"
  fi
done
cp "$OVERLAY/01-sysu-anything/00-评委请先看.md" "$P01/"
test ! -e "$P01/.sysu-anything" || die "01 leaked .sysu-anything"
test ! -e "$P01/.env" || die "01 leaked .env"

echo "==> 02 Douyin taste Skill"
mkdir -p "$P02/scripts" "$P02/edge-demo" "$P02/app-module"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" \
  --exclude 'dist/' \
  --exclude '.env.example' \
  "$ROOT/onemore-taste-edge/" "$P02/edge-demo/"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" \
  "$ROOT/onemore/modules/taste_profile/" "$P02/app-module/"
cp "$OVERLAY/02-douyin-taste/00-评委请先看.md" "$P02/"
cp "$OVERLAY/02-douyin-taste/SKILL.md" "$P02/"
cp "$OVERLAY/02-douyin-taste/SECURITY.md" "$P02/"
cp "$OVERLAY/02-douyin-taste/scripts/analyze-from-link.mjs" "$P02/scripts/"
cp "$OVERLAY/02-douyin-taste/env.example" "$P02/.env.example"
cp "$OVERLAY/02-douyin-taste/env.example" "$P02/edge-demo/.env.example"
cp "$ROOT/docs/readme-assets/taste-qr.png" "$P02/评委体验二维码.png"
test ! -e "$P02/edge-demo/.env" || die "02 leaked taste-edge .env"
test ! -e "$P02/.env" || die "02 leaked .env"

echo "==> 03 Agent / Workflow"
mkdir -p "$P03/hermes" "$P03/edge-agent" "$P03/workflows" "$P03/openapi"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" "$ROOT/onemore/hermes/" "$P03/hermes/"
# Drop machine-local CLI path from the capability dump.
python3 - "$P03/hermes/capabilities.json" <<'PY'
from pathlib import Path
import json, sys
p = Path(sys.argv[1])
data = json.loads(p.read_text())
data["cli"] = "sysu-anything"
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" \
  --exclude 'dist/' \
  --exclude 'agents-python/' \
  --exclude 'plan/' \
  --exclude 'agents-backup/' \
  "$ROOT/onemore-edge-agent/" "$P03/edge-agent/"
for mod in gathering intent matching actions campus; do
  mkdir -p "$P03/workflows/$mod"
  "${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" "$ROOT/onemore/modules/$mod/" "$P03/workflows/$mod/"
done
cp "$ROOT/openapi/onemore.openapi.json" "$P03/openapi/"
cp "$OVERLAY/03-agent-workflow/00-评委请先看.md" "$P03/"
cp "$OVERLAY/03-agent-workflow/WORKFLOWS.md" "$P03/"
test ! -e "$P03/edge-agent/.env" || die "03 leaked edge-agent .env"

echo "==> 04 Source"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" \
  --exclude 'submission/' \
  --exclude 'ios/.derived/' \
  --exclude 'ios/.derived-release/' \
  --exclude 'ios/build/' \
  --exclude 'ios/artifacts/' \
  --exclude 'web/dist/' \
  --exclude 'onemore-edge-agent/dist/' \
  --exclude 'onemore-taste-edge/dist/' \
  --exclude 'vaults/' \
  --exclude '*-vault/' \
  --exclude '*-vaults/' \
  --exclude 'runtime/' \
  --exclude 'test-runtime/' \
  --exclude 'test-vaults/' \
  --exclude 'douyin_like_profile/' \
  --exclude 'douyin-cookies/' \
  --exclude 'output/' \
  --exclude 'dist/' \
  --exclude 'artifacts/' \
  --exclude 'design/' \
  --exclude 'assets/' \
  --exclude '.claude/' \
  --exclude '.playwright-cli/' \
  --exclude '.uv/' \
  --exclude 'htmlcov/' \
  --exclude 'onemore.db' \
  --exclude 'douyin_demo.db' \
  --exclude 'test_onemore.db' \
  --exclude 'celerybeat-schedule*' \
  --exclude 'typewriter-videos/' \
  --exclude 'prototypes/' \
  --exclude '*.xcresult' \
  --exclude 'stitched-competition-recruitment-flow.png' \
  "$ROOT/" "$P04/"
cp "$OVERLAY/04-source/00-评委请先看.md" "$P04/"
# Keep the public example env only.
if [[ -f "$ROOT/.env.example" ]]; then
  cp "$ROOT/.env.example" "$P04/.env.example"
fi
rm -f "$P04/.env" "$P04/web/.env" "$P04/onemore-taste-edge/.env" "$P04/onemore-edge-agent/.env"
test ! -e "$P04/.env" || die "04 leaked .env"
test ! -d "$P04/douyin_like_profile" || die "04 leaked douyin_like_profile"
test ! -d "$P04/runtime" || die "04 leaked runtime"

echo "==> 05 Art"
mkdir -p "$P05/design/mobile-prototype" "$P05/design/lulu-frontend" \
  "$P05/ip/atlases" "$P05/ip/brand" "$P05/ip/style-reference" \
  "$P05/ip/docs" "$P05/ip/manifest" "$P05/ip/tools" "$P05/cast" "$P05/readme-assets"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" \
  --exclude 'raw/' \
  "$ROOT/design/received/2026-08-11-one-more-mobile-prototype/" \
  "$P05/design/mobile-prototype/"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" \
  --exclude 'raw/' \
  "$ROOT/design/received/2026-08-12-one-more-lulu-frontend/export/" \
  "$P05/design/lulu-frontend/export/"
cp "$ROOT/design/received/2026-08-12-one-more-lulu-frontend/SOURCE_MANIFEST.json" \
  "$P05/design/lulu-frontend/" 2>/dev/null || true
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" \
  --exclude 'LuluInventoryScanAtlas.png' \
  --exclude 'LuluInventoryReviewAtlas.png' \
  --exclude 'LuluRecipePlanAtlas.png' \
  --exclude 'LuluShoppingOrganizeAtlas.png' \
  --exclude 'LuluCookingGuideAtlas.png' \
  --exclude 'LuluDeviceConnectAtlas.png' \
  --exclude 'LuluKitchenRolesAtlas.png' \
  "$ROOT/assets/ip/lulu/atlases/" "$P05/ip/atlases/"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" "$ROOT/assets/ip/lulu/brand/" "$P05/ip/brand/"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" "$ROOT/assets/ip/lulu/style-reference/" "$P05/ip/style-reference/"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" "$ROOT/assets/ip/lulu/docs/" "$P05/ip/docs/"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" "$ROOT/assets/ip/lulu/manifest/" "$P05/ip/manifest/"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" "$ROOT/assets/ip/lulu/tools/" "$P05/ip/tools/"
cp "$ROOT/assets/ip/lulu/README.md" "$P05/ip/"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" "$ROOT/assets/ip/cast/" "$P05/cast/"
"${RSYNC[@]}" "${COMMON_EXCLUDES[@]}" "$ROOT/docs/readme-assets/" "$P05/readme-assets/"
cp "$OVERLAY/05-art/00-评委请先看.md" "$P05/"
test ! -d "$P05/ip/generated" || die "05 included generated frames"

echo "==> secret scan"
python3 - "$STAGE" <<'PY'
from pathlib import Path
import re, sys

root = Path(sys.argv[1])
forbidden_names = {
    ".env",
    "cookies.json",
    "cookie.txt",
    "session.json",
    "jwxt-session.json",
    "gym-session.json",
    "chat-session.json",
}
forbidden_dir_parts = {".sysu-anything", "douyin_like_profile", "vaults", "runtime"}
# Real cookie assignment, not the empty example.
# Real cookie assignment on the same line, not the empty example.
cookie_assign = re.compile(
    r"(?im)^(DOUYIN_COOKIE(?:_B64)?|ONEMORE_DOUYIN_HTTP_COOKIE(?:_B64)?)=[ \t]*([^\s#]+)"
)
sessionid_val = re.compile(r"sessionid\s*=\s*[A-Za-z0-9._-]{8,}")
sid_tt_val = re.compile(r"sid_tt\s*=\s*[A-Za-z0-9._-]{8,}")
api_key_assign = re.compile(
    r"(?im)^(AI_GATEWAY_API_KEY|ONEMORE_TASTE_LLM_API_KEY|ONEMORE_HERMES_AGENT_API_KEY)=[ \t]*([^\s#]+)"
)

errors = []
for path in root.rglob("*"):
    rel = path.relative_to(root)
    parts = set(rel.parts)
    if parts & forbidden_dir_parts:
        errors.append(f"forbidden dir in path: {rel}")
        continue
    if path.name in forbidden_names:
        errors.append(f"forbidden file: {rel}")
        continue
    if not path.is_file():
        continue
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".woff", ".woff2"}:
        continue
    if path.name == ".env.example":
        continue
    if path.stat().st_size > 2_000_000:
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    for rx, label in (
        (cookie_assign, "cookie assignment"),
        (sessionid_val, "sessionid"),
        (sid_tt_val, "sid_tt"),
        (api_key_assign, "api key assignment"),
    ):
        for m in rx.finditer(text):
            raw = m.group(0)
            value = raw.split("=", 1)[-1].strip().strip('"').strip("'")
            if not value:
                continue
            if value.startswith("<") and value.endswith(">"):
                continue
            if value in {"change-me", "replace-me"}:
                continue
            errors.append(f"{label} in {rel}: {raw[:80]}")

if errors:
    print("SECRET SCAN FAILED:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("secret scan passed")
PY

echo "==> zip"
rm -f "$ZIPS"/*.zip
cp "$OVERLAY/00-提交清单.md" "$ZIPS/"
(
  cd "$STAGE"
  for dir in 01-Skill-SYSU-Anything 02-Skill-抖音兴趣画像 03-Agent-Workflow-噜噜成局 04-Source-噜噜成局源码 05-Art-噜噜美术资产; do
    echo "  zipping $dir"
    (cd "$STAGE" && zip -r -X -q "$ZIPS/${dir}.zip" "$dir")
  done
)

echo
echo "==> sizes"
du -sh "$STAGE"/*/
echo "---"
du -sh "$ZIPS"/*.zip
python3 - <<PY
from pathlib import Path
zips = list(Path("$ZIPS").glob("*.zip"))
total = sum(p.stat().st_size for p in zips)
print(f"---\nzip total: {total/1024/1024:.1f} MB / 200 MB")
PY
echo
echo "Output: $ZIPS"
