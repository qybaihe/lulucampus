#!/usr/bin/env bash
# Rebuild a fine-grained commit history for github.com/qybaihe/lulucampus
# and push to origin. Run from repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REMOTE_URL="${REMOTE_URL:-https://github.com/qybaihe/lulucampus.git}"
BRANCH="${BRANCH:-main}"

commit() {
  local msg="$1"
  shift || true
  if [[ $# -gt 0 ]]; then
    git add -- "$@" 2>/dev/null || true
  fi
  if git diff --cached --quiet; then
    echo "skip (empty): $msg"
    return 0
  fi
  git commit -m "$msg"
  echo "ok: $msg"
}

echo "==> preparing orphan branch ${BRANCH}"
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"

git checkout --orphan "$BRANCH"
git rm -rf --cached . >/dev/null 2>&1 || true

# 01
commit "chore: initialize project scaffolding and ignore rules" \
  .gitignore pyproject.toml uv.lock alembic.ini Makefile Dockerfile docker-compose.yml .env.example

# 02
commit "docs: add product README with screenshots and Feishu link" \
  README.md docs/readme-assets

# 03
commit "docs: import V2.1 product and platform guides" \
  docs/00_产品方案_V2.1.md \
  docs/01_iOS客户端开发指南.md \
  docs/02_后端服务开发指南.md \
  docs/03_行动代理与Hermes设计.md \
  docs/README.md \
  差一个_ONE_MORE_融合产品规划方案.md

# 04
commit "docs: add IP motion and design handoff notes" \
  docs/04_阿凑IP形象与文档设计评审.md \
  docs/05_阿凑动态IP候选与事件系统.md \
  docs/05_iOS设计交接提示词.md \
  docs/07_阿凑D动态资产交付说明.md \
  docs/10_AIIA粉发创变者业务动作交付说明.md \
  docs/14_素材生成交接提示词.md \
  docs/15_设计交接提示词.md \
  docs/16_设计迁移线程交接提示词.md

# 05
commit "docs: add backend integration and competition data notes" \
  docs/06_后端实现与前端联调.md \
  docs/07_比赛雷达离线数据说明.md \
  docs/07_抖音兴趣标签导入接口.md \
  docs/08_中山大学校园基础数据资产说明.md \
  docs/08_抖音兴趣标签导入_线程交接提示词.md \
  docs/09_比赛雷达V1.1质量验收与入库说明.md \
  docs/11_iOS前后端联调现状与范围.md \
  docs/12_iOS完整实现_Goal模式线程交接提示词.md \
  docs/13_功能全量清单与美术需求.md \
  docs/14_Hermes真实部署_线程交接提示词.md \
  docs/17_抖音兴趣画像接口_后端交接.md \
  docs/18_抖音兴趣画像_完成情况与使用交接.md \
  docs/19_社交层前后端联调交付.md \
  docs/HOMEWORK_JWXT_ELECTIVE_LIST.md \
  docs/TEST_LOOP.md \
  docs/TEST_NEXT_STEPS.md \
  docs/TEST_RESULTS.md \
  docs/handoffs

# 06
commit "feat(core): add config, auth, http, locks and contact policy" \
  onemore/__init__.py onemore/main.py onemore/core

# 07
commit "feat(db): add SQLAlchemy models and seed helpers" \
  onemore/db

# 08
commit "feat(hermes): add Action Schema, vault and executor pool" \
  onemore/hermes

# 09
commit "feat(identity): async scan login, grants and account lifecycle" \
  onemore/modules/__init__.py onemore/modules/identity

# 10
commit "feat(profile): course mapping and capability vectors" \
  onemore/modules/profile

# 11
commit "feat(schedule): timetable cache and privacy free-slot intersection" \
  onemore/modules/schedule

# 12
commit "feat(intent): typed intent compilation and anonymous publish" \
  onemore/modules/intent

# 13
commit "feat(matching): similar buddy and complementary team ranking" \
  onemore/modules/matching

# 14
commit "feat(gathering): gathering state machine and booking plans" \
  onemore/modules/gathering

# 15
commit "feat(trust): T0-T4 trust ladder, unlocks and appeals" \
  onemore/modules/trust

# 16
commit "feat(collab): in-gathering chat, relations and shared goals" \
  onemore/modules/collab

# 17
commit "feat(competitions): verified snapshot ingest and radar APIs" \
  onemore/modules/competitions

# 18
commit "feat(actions): preview-confirm-execute action pipeline" \
  onemore/modules/actions

# 19
commit "feat(notify): transactional notifications and APNs outbox" \
  onemore/modules/notify

# 20
commit "feat(campus): Hermes-backed campus tool aggregation" \
  onemore/modules/campus

# 21
commit "feat(taste): Douyin interest import and persona enrichment" \
  onemore/modules/taste_profile

# 22
commit "feat(media): binary media storage service" \
  onemore/modules/media

# 23
commit "feat(tasks): Celery worker and beat schedules" \
  onemore/tasks

# 24
commit "feat(scripts): seed, ingest and OpenAPI export CLIs" \
  onemore/scripts

# 25
commit "chore(openapi): export frontend contract snapshot" \
  openapi

# 26
commit "chore(fixtures): add competition radar snapshot v1.1" \
  fixtures

# 27
commit "chore(db): add Alembic migrations through 0019" \
  migrations

# 28
commit "test: add identity, account and privacy suites" \
  tests/conftest.py \
  tests/test_account.py \
  tests/test_identity_and_relations.py \
  tests/test_system_and_privacy.py \
  tests/test_privacy_matching_controls.py \
  tests/test_trust_boundaries.py \
  tests/test_trust_capability_paths.py \
  tests/test_phone_auth.py \
  tests/test_websocket_auth.py

# 29
commit "test: add gathering, matching and social-layer suites" \
  tests/test_organizer.py \
  tests/test_matching_preferences.py \
  tests/test_matching_block_safety.py \
  tests/test_gathering_booking_plan.py \
  tests/test_gathering_detail_privacy.py \
  tests/test_social_layer.py \
  tests/test_completion_attendance.py \
  tests/test_recurrence_choices.py \
  tests/test_scene_sensitivity.py \
  tests/test_expiry_boundaries.py \
  tests/test_public_event_contract.py \
  tests/test_intent_edit_and_capability.py

# 30
commit "test: add Hermes actions, Douyin taste and contract suites" \
  tests/test_hermes_and_actions.py \
  tests/test_action_authorizations.py \
  tests/test_douyin_taste_import.py \
  tests/test_competitions.py \
  tests/test_ios_contract_gaps.py \
  tests/test_login_schedule_and_runtime.py \
  tests/test_idempotency_replay.py \
  tests/test_migration_push_token_ownership.py \
  tests/test_push_device_isolation.py \
  tests/test_backfill_channel_history.py

# 31 catch remaining tests
commit "test: add remaining API and regression suites" \
  tests

# 32
commit "data: add SYSU campus reference pack v1.1" \
  data/reference

# 33
commit "data: add campus events corpus and import helpers" \
  data/campus-events \
  scripts/import_campus_events.py

# 34
commit "assets: add AIIA pink-girl business motion pack" \
  assets/ip/selected \
  assets/ip/animation \
  assets/ip/candidates \
  assets/ip/references \
  assets/ip/azou-candidate-v1.png

# 35
commit "assets: add Lulu IP stickers, atlases and brand kit" \
  assets/ip/lulu

# 36
commit "design: import mobile prototype boards and handoff" \
  design/received/2026-08-11-one-more-mobile-prototype

# 37
commit "design: import Lulu frontend export and generated UI maps" \
  design

# 38
commit "feat(ios): bootstrap XcodeGen project and app shell" \
  ios/project.yml \
  ios/Config \
  ios/Scripts \
  ios/APP_METADATA.json \
  ios/README.md \
  ios/BUILD_NOTES.md \
  ios/OneMore/App \
  ios/OneMore/Core

# 39
commit "feat(ios): implement feature screens and navigation" \
  ios/OneMore/Features

# 40
commit "feat(ios): add resources, SYSU pack and AppIcon" \
  ios/OneMore/Resources

# 41
commit "feat(ios): add unit and UI test targets" \
  ios/OneMoreTests \
  ios/OneMoreUITests

# 42
commit "docs(ios): add screen map, service map and fidelity notes" \
  ios/SCREEN_MAP.md \
  ios/SERVICE_MAP.md \
  ios/FIDELITY_CHECKLIST.md \
  ios/FIDELITY_REVIEW.md \
  ios/FIDELITY_NEXT_STEPS.md \
  ios/OneMore.xcodeproj

# 43
commit "chore(ios): archive runtime screenshots and motion evidence" \
  ios/artifacts/screenshots \
  ios/artifacts/motion

# 44
commit "feat(web): add React shell aligned with iOS tabs" \
  web/package.json \
  web/yarn.lock \
  web/vite.config.ts \
  web/tsconfig.json \
  web/tsconfig.app.json \
  web/tsconfig.node.json \
  web/index.html \
  web/README.md \
  web/src \
  web/public

# 45
commit "feat(edge): add onemore-edge-agent orchestration sandbox" \
  onemore-edge-agent

# 46
commit "chore(ops): add production Docker compose and packaging" \
  Dockerfile.prod \
  docker-compose.prod.yml

# 47
commit "chore(scripts): add taste matching and demo seed helpers" \
  scripts

# 48
commit "chore(prototypes): add IP motion and UI prototypes" \
  prototypes

# 49
commit "chore(artifacts): add product screenshot gallery for demos" \
  artifacts

# 50 catch-all
git add -A
if ! git diff --cached --quiet; then
  git commit -m "chore: include remaining project files for full delivery"
  echo "ok: chore: include remaining project files for full delivery"
fi

COUNT=$(git rev-list --count HEAD)
echo "==> created ${COUNT} commits on ${BRANCH}"
git log --oneline

# Safety: refuse to push if known leaked key pattern is present in the tree
if git grep -n "sk-Kk7YCXLEMuDA79JklMxvsCfyiZhWy42vDSw3eAX0rAgq3eFkVg9tNCsaNKvNgpZB" >/dev/null 2>&1; then
  echo "ERROR: secret key still present in tree; aborting push" >&2
  exit 1
fi

echo "==> pushing to ${REMOTE_URL}"
git push -u origin "${BRANCH}" --force

echo "done. commits=${COUNT} url=${REMOTE_URL}"
