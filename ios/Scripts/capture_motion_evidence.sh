#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SIMULATOR_UDID="${SIMULATOR_UDID:-5BEE7D9F-B906-43B3-A508-2930BB4EFAF3}"
APP_PATH="${APP_PATH:-/tmp/onemore-root-dd-e2e-r1/Build/Products/Debug-iphonesimulator/ONE MORE.app}"
BUNDLE_ID="com.onemore.campus.dev"
MOTION_DIR="$ROOT/artifacts/motion"
LOG_DIR="$ROOT/artifacts/logs"
mkdir -p "$MOTION_DIR" "$LOG_DIR"

xcrun simctl boot "$SIMULATOR_UDID" >/dev/null 2>&1 || true
xcrun simctl bootstatus "$SIMULATOR_UDID" -b
xcrun simctl install "$SIMULATOR_UDID" "$APP_PATH"

# 用法：capture_motion_evidence.sh [clip ...]，默认录主链路四个 once clip。
# clip 名即 lulu-motion.v1.json 的 clip key（如 home.idle、exit.bow）。
capture() {
  clip="$1"
  stem="${clip//./-}"
  frame_dir="$MOTION_DIR/$stem-frames"
  contact="$MOTION_DIR/$stem-frames-contact.png"
  video="$MOTION_DIR/lulu-$stem.mp4"
  record_log="$LOG_DIR/record-$stem.log"
  mkdir -p "$frame_dir"

  find "$frame_dir" -type f -name 'frame-*.png' -delete

  xcrun simctl terminate "$SIMULATOR_UDID" "$BUNDLE_ID" >/dev/null 2>&1 || true
  xcrun simctl io "$SIMULATOR_UDID" recordVideo --codec=h264 --force "$video" \
    >"$record_log" 2>&1 &
  recorder_pid=$!
  sleep 0.35
  xcrun simctl launch "$SIMULATOR_UDID" "$BUNDLE_ID" --args \
    -UI_TESTING YES -LuluClip "$clip" >>"$record_log" 2>&1
  sleep 6.5
  kill -INT "$recorder_pid" >/dev/null 2>&1 || true
  wait "$recorder_pid" || true

  ffprobe -v error -show_entries \
    stream=codec_name,width,height,avg_frame_rate:format=duration,size \
    -of json "$video" > "$MOTION_DIR/lulu-$stem.ffprobe.json"
  ffmpeg -y -loglevel error -ss 0.8 -i "$video" -vf fps=3 -frames:v 10 \
    "$frame_dir/frame-%02d.png"
  magick montage "$frame_dir"/frame-*.png -thumbnail '180x390>' \
    -font /System/Library/Fonts/SFNS.ttf \
    -background '#f6f4ec' -gravity center -tile 5x2 -geometry 190x420+0+0 \
    "$contact"
}

clips=("$@")
if [ "${#clips[@]}" -eq 0 ]; then
  clips=(intent.card confirm.gather action.executing exit.bow)
fi
for clip in "${clips[@]}"; do
  capture "$clip"
done

xcrun simctl terminate "$SIMULATOR_UDID" "$BUNDLE_ID" >/dev/null 2>&1 || true
printf 'Captured Lulu motion evidence (%s) on %s.\n' "${clips[*]}" "$SIMULATOR_UDID"
