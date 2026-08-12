"""Render transparent GIF and animated WebP previews from extracted IP frames.

This utility intentionally shells out to ImageMagick rather than Pillow so the
same RGBA source frames can be encoded consistently on local design machines.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

STATE_DURATIONS_MS: dict[str, list[int]] = {
    "idle": [280, 110, 110, 140, 140, 320],
    "running-right": [120, 120, 120, 120, 120, 120, 120, 220],
    "running-left": [120, 120, 120, 120, 120, 120, 120, 220],
    "waving": [140, 140, 140, 280],
    "jumping": [140, 140, 140, 140, 280],
    "failed": [140, 140, 140, 140, 140, 140, 140, 240],
    "waiting": [150, 150, 150, 150, 150, 260],
    "running": [120, 120, 120, 120, 120, 220],
    "review": [150, 150, 150, 150, 150, 280],
}


def frame_paths(frames_root: Path, state: str, expected: int) -> list[Path]:
    frames = sorted((frames_root / state).glob("*.png"))
    if len(frames) != expected:
        raise SystemExit(
            f"{state}: expected {expected} PNG frames under "
            f"{frames_root / state}, found {len(frames)}"
        )
    return frames


def timed_inputs(frames: list[Path], durations_ms: list[int]) -> list[str]:
    args: list[str] = []
    for frame, duration_ms in zip(frames, durations_ms, strict=True):
        args.extend(["-delay", str(max(1, round(duration_ms / 10))), str(frame)])
    return args


def render_state(
    magick: str,
    state: str,
    frames: list[Path],
    durations_ms: list[int],
    output_dir: Path,
) -> dict[str, object]:
    gif_path = output_dir / f"{state}.gif"
    webp_path = output_dir / f"{state}.webp"
    inputs = timed_inputs(frames, durations_ms)

    subprocess.run(
        [
            magick,
            "-dispose",
            "Background",
            *inputs,
            "-loop",
            "0",
            "-layers",
            "OptimizeTransparency",
            str(gif_path),
        ],
        check=True,
    )
    subprocess.run(
        [magick, *inputs, "-loop", "0", str(webp_path)],
        check=True,
    )
    return {
        "state": state,
        "frames": len(frames),
        "durations_ms": durations_ms,
        "gif": str(gif_path),
        "webp": str(webp_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    magick = shutil.which("magick")
    if not magick:
        raise SystemExit("ImageMagick `magick` is required")

    frames_root = args.frames_root.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    previews = []
    for state, durations_ms in STATE_DURATIONS_MS.items():
        frames = frame_paths(frames_root, state, len(durations_ms))
        previews.append(
            render_state(magick, state, frames, durations_ms, output_dir)
        )

    manifest = {
        "schema_version": 1,
        "frames_root": str(frames_root),
        "output_dir": str(output_dir),
        "previews": previews,
    }
    manifest_path = output_dir / "previews-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
