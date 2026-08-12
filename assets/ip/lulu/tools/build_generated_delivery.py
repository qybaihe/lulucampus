#!/usr/bin/env python3
"""Build the 2026-08-12 Lulu motion and sticker delivery from generated sheets.

The input sheets are copied to ``generated/2026-08-12/raw`` first.  This tool:

1. converts the magenta/green chroma backgrounds to alpha;
2. splits Lulu 2x2 sheets into four 627px frames;
3. registers Lulu frames by muzzle and foot anchors;
4. splits each 3x2 sticker sheet and fits every sticker onto a 512px canvas;
5. writes a compact QA report and contact sheets.

It is intentionally deterministic so regenerated source sheets can be rebuilt
without changing the asset naming consumed by the app.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "generated" / "2026-08-12"
RAW = DELIVERY / "raw"
TRANSPARENT = DELIVERY / "transparent-sheets"
FRAMES = DELIVERY / "frames"
STICKERS = DELIVERY / "stickers"
QA = DELIVERY / "qa"
ATLASES = ROOT / "atlases"
IOS_RESOURCES = ROOT.parents[2] / "ios" / "OneMore" / "Resources" / "LuluGenerated"
REMOVE_CHROMA = ROOT / "tools" / "remove_chroma_key.py"
REGISTER = ROOT / "tools" / "register_lulu_frames.py"


@dataclass(frozen=True)
class MotionSpec:
    clip: str
    raw: str
    atlas: str


@dataclass(frozen=True)
class StickerSpec:
    batch: str
    raw: str
    ids: tuple[str, ...]


MOTIONS = (
    MotionSpec("intent.card", "lulu-intent-card-chroma.png", "LuluIntentCardAtlas.png"),
    MotionSpec("pool.waiting", "lulu-pool-waiting-chroma.png", "LuluPoolWaitingAtlas.png"),
    MotionSpec("confirm.gather", "lulu-confirm-gather-chroma.png", "LuluConfirmGatherAtlas.png"),
    MotionSpec("action.preview", "lulu-action-preview-chroma.png", "LuluActionPreviewAtlas.png"),
    MotionSpec("action.executing", "lulu-action-executing-chroma.png", "LuluActionExecutingAtlas.png"),
    MotionSpec("exit.bow", "lulu-exit-bow-chroma.png", "LuluExitBowAtlas.png"),
)

STICKER_BATCHES = (
    StickerSpec(
        "S1",
        "stickers-s1-table-seats-chroma.png",
        ("chair-empty", "round-table", "nameplate-blank", "access-card", "qr-plaque-blank", "hourglass"),
    ),
    StickerSpec(
        "S2",
        "stickers-s2-sports-chroma.png",
        ("badminton", "basketball", "table-tennis", "football", "running-shoe", "sports-bottle"),
    ),
    StickerSpec(
        "S3",
        "stickers-s3-academic-chroma.png",
        ("books-stack", "laptop-closed", "notebook-open", "marker", "alarm-clock", "desk-calendar"),
    ),
    StickerSpec(
        "S4",
        "stickers-s4-campus-chroma.png",
        ("seminar-room-sign", "study-lamp", "teaching-building", "school-bus", "poster-blank", "cafeteria-tray"),
    ),
    StickerSpec(
        "S5",
        "stickers-s5-capabilities-chroma.png",
        ("backend-server", "frontend-browser", "data-chart", "product-notes", "algorithm-gear", "design-palette"),
    ),
    StickerSpec(
        "S6",
        "stickers-s6-results-chroma.png",
        ("trophy", "certificate", "badge", "envelope", "chat-bubble", "approval-stamp"),
    ),
)


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def alpha_bbox(image: Image.Image, threshold: int = 16) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value >= threshold else 0).getbbox()
    if bbox is None:
        raise ValueError("asset has no visible pixels")
    return bbox


def clean_background_residue(path: Path, cutoff: int = 48) -> None:
    """Drop low-alpha chroma residue left by slightly non-uniform model keys."""

    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image).copy()
    rgba[..., 3] = np.where(rgba[..., 3] < cutoff, 0, rgba[..., 3])
    rgba[rgba[..., 3] == 0, :3] = 0
    Image.fromarray(rgba, mode="RGBA").save(path, optimize=True)


def despill_translucent_green_edges(path: Path) -> None:
    """Neutralize green only on the anti-aliased outer matte.

    Fully opaque semantic greens inside a sticker remain untouched.  This is
    safe for these sheets because every subject has a white die-cut outline.
    """

    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image).copy()
    red, green, blue, alpha = (rgba[..., index] for index in range(4))
    # Pixels that are both translucent *and* still extremely close to the
    # chroma hue belong to the matte.  Keep ordinary pale green antialiasing
    # around semantic green subjects (for example the approval check).
    mask = (
        (alpha > 0)
        & (alpha < 252)
        & (green > 180)
        & (green > red * 1.8)
        & (green > blue * 1.8)
    )
    # The sticker outline is white, so neutralize keyed fringe toward white
    # rather than toward dark red/blue channel values.
    rgba[..., 0] = np.where(mask, green, red)
    rgba[..., 2] = np.where(mask, green, blue)
    Image.fromarray(rgba, mode="RGBA").save(path, optimize=True)


def fit_square(image: Image.Image, size: int = 512, margin: int = 28) -> Image.Image:
    crop = image.crop(alpha_bbox(image))
    available = size - margin * 2
    ratio = min(available / crop.width, available / crop.height)
    new_size = (max(1, round(crop.width * ratio)), max(1, round(crop.height * ratio)))
    crop = crop.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(crop, ((size - crop.width) // 2, (size - crop.height) // 2))
    return canvas


def remove_small_edge_fragments(image: Image.Image, *, fraction_of_largest: float = 0.22) -> Image.Image:
    """Remove small neighbor fragments introduced by fixed-grid sheet crops.

    Generated objects can overhang a nominal grid line by a few pixels.  Such
    overhangs become disconnected slivers on the adjacent sticker.  Components
    touching a crop edge are removed only when much smaller than the dominant
    subject, so a legitimate large subject near an edge is retained.
    """

    rgba = np.asarray(image.convert("RGBA")).copy()
    mask = rgba[..., 3] > 8
    height, width = mask.shape
    seen = np.zeros(mask.shape, dtype=np.uint8)
    components: list[tuple[list[tuple[int, int]], bool]] = []
    for start_y, start_x in zip(*np.nonzero(mask)):
        if seen[start_y, start_x]:
            continue
        stack = [(int(start_y), int(start_x))]
        seen[start_y, start_x] = 1
        pixels: list[tuple[int, int]] = []
        touches_edge = False
        while stack:
            y, x = stack.pop()
            pixels.append((y, x))
            touches_edge = touches_edge or x <= 1 or y <= 1 or x >= width - 2 or y >= height - 2
            for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= next_y < height and 0 <= next_x < width and mask[next_y, next_x] and not seen[next_y, next_x]:
                    seen[next_y, next_x] = 1
                    stack.append((next_y, next_x))
        components.append((pixels, touches_edge))

    if not components:
        return image
    largest = max(len(pixels) for pixels, _ in components)
    for pixels, touches_edge in components:
        if touches_edge and len(pixels) < largest * fraction_of_largest:
            ys, xs = zip(*pixels)
            rgba[np.asarray(ys), np.asarray(xs), 3] = 0
            rgba[np.asarray(ys), np.asarray(xs), :3] = 0
    return Image.fromarray(rgba, mode="RGBA")


def make_contact_sheet(paths: list[Path], output: Path, *, columns: int, cell: int = 256) -> None:
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * cell, rows * cell), (246, 244, 236, 255))
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGBA")
        preview = fit_square(image, size=cell, margin=20)
        x, y = (index % columns) * cell, (index // columns) * cell
        sheet.alpha_composite(preview, (x, y))
        draw.rectangle((x, y, x + cell - 1, y + cell - 1), outline=(220, 227, 217, 255), width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(output, quality=94)


def process_motion(spec: MotionSpec) -> dict[str, object]:
    src = RAW / spec.raw
    transparent_sheet = TRANSPARENT / spec.raw.replace("-chroma", "")
    transparent_sheet.parent.mkdir(parents=True, exist_ok=True)
    # The generic helper's single-channel despill selects red for a magenta
    # key (red and blue are tied).  Lulu's canonical yellow/orange materials
    # legitimately contain strong red, so that mode changes the character's
    # colors and also breaks muzzle-anchor detection.  Alpha extraction is
    # still color-distance based; only destructive despill is disabled here.
    run(
        sys.executable,
        str(REMOVE_CHROMA),
        str(src),
        str(transparent_sheet),
        "--key",
        "#ff00ff",
        "--no-despill",
    )
    clean_background_residue(transparent_sheet)

    sheet = Image.open(transparent_sheet).convert("RGBA")
    if sheet.size[0] % 2 or sheet.size[1] % 2:
        raise ValueError(f"{src.name}: expected an even 2x2 sheet, got {sheet.size}")
    frame_w, frame_h = sheet.width // 2, sheet.height // 2
    frame_dir = FRAMES / spec.clip
    frame_dir.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        x = (index % 2) * frame_w
        y = (index // 2) * frame_h
        sheet.crop((x, y, x + frame_w, y + frame_h)).save(frame_dir / f"{index:02d}.png", optimize=True)

    atlas_out = ATLASES / spec.atlas
    run(
        sys.executable,
        str(REGISTER),
        "--frames-dir",
        str(frame_dir),
        "--atlas-out",
        str(atlas_out),
        "--columns",
        "2",
    )
    atlas = Image.open(atlas_out).convert("RGBA")
    alpha = np.asarray(atlas.getchannel("A"))
    return {
        "clip": spec.clip,
        "raw": str(src.relative_to(ROOT)),
        "atlas": str(atlas_out.relative_to(ROOT)),
        "size": list(atlas.size),
        "visible_pixel_ratio": round(float((alpha > 16).mean()), 4),
        "transparent_corners": all(alpha[y, x] == 0 for x, y in ((0, 0), (atlas.width - 1, 0), (0, atlas.height - 1), (atlas.width - 1, atlas.height - 1))),
    }


def process_stickers(spec: StickerSpec) -> list[dict[str, object]]:
    src = RAW / spec.raw
    transparent_sheet = TRANSPARENT / spec.raw.replace("-chroma", "")
    transparent_sheet.parent.mkdir(parents=True, exist_ok=True)
    # Sticker subjects intentionally include semantic green (the S5 data bar
    # and S6 approval check).  Their continuous white die-cut border already
    # prevents green-key spill at the outer silhouette, so preserve subject
    # color by disabling global single-channel despill here as well.
    run(
        sys.executable,
        str(REMOVE_CHROMA),
        str(src),
        str(transparent_sheet),
        "--key",
        "#00ff00",
        "--no-despill",
    )
    clean_background_residue(transparent_sheet)
    despill_translucent_green_edges(transparent_sheet)
    sheet = Image.open(transparent_sheet).convert("RGBA")
    if sheet.width % 3 or sheet.height % 2:
        raise ValueError(f"{src.name}: expected a 3x2 sheet, got {sheet.size}")
    cell_w, cell_h = sheet.width // 3, sheet.height // 2
    output_dir = STICKERS / spec.batch
    output_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []
    for index, asset_id in enumerate(spec.ids):
        x = (index % 3) * cell_w
        y = (index // 3) * cell_h
        cell = sheet.crop((x, y, x + cell_w, y + cell_h))
        cell = remove_small_edge_fragments(cell)
        output = output_dir / f"{asset_id}.png"
        final = fit_square(cell)
        final.save(output, optimize=True)
        alpha = np.asarray(final.getchannel("A"))
        reports.append(
            {
                "batch": spec.batch,
                "id": asset_id,
                "file": str(output.relative_to(ROOT)),
                "size": list(final.size),
                "visible_pixel_ratio": round(float((alpha > 16).mean()), 4),
                "transparent_corners": all(alpha[y, x] == 0 for x, y in ((0, 0), (511, 0), (0, 511), (511, 511))),
            }
        )
    return reports


def main() -> None:
    for directory in (TRANSPARENT, FRAMES, STICKERS, QA, ATLASES, IOS_RESOURCES):
        directory.mkdir(parents=True, exist_ok=True)

    missing = [str(RAW / spec.raw) for spec in (*MOTIONS, *STICKER_BATCHES) if not (RAW / spec.raw).exists()]
    if missing:
        raise FileNotFoundError("Missing generated source sheets:\n" + "\n".join(missing))

    motion_report = [process_motion(spec) for spec in MOTIONS]
    sticker_report = [item for spec in STICKER_BATCHES for item in process_stickers(spec)]

    # Keep app-consumable resources inside the Xcode project's resource tree;
    # project.yml includes this directory recursively during generation.
    ios_atlases = IOS_RESOURCES / "Atlases"
    ios_stickers = IOS_RESOURCES / "Stickers"
    ios_atlases.mkdir(parents=True, exist_ok=True)
    ios_stickers.mkdir(parents=True, exist_ok=True)
    for spec in MOTIONS:
        Image.open(ATLASES / spec.atlas).save(ios_atlases / spec.atlas, optimize=True)
    for spec in STICKER_BATCHES:
        batch_dir = ios_stickers / spec.batch
        batch_dir.mkdir(parents=True, exist_ok=True)
        for asset_id in spec.ids:
            Image.open(STICKERS / spec.batch / f"{asset_id}.png").save(
                batch_dir / f"{asset_id}.png", optimize=True
            )

    make_contact_sheet([ATLASES / spec.atlas for spec in MOTIONS], QA / "lulu-motion-contact-sheet.jpg", columns=3)
    make_contact_sheet([STICKERS / spec.batch / f"{asset_id}.png" for spec in STICKER_BATCHES for asset_id in spec.ids], QA / "stickers-contact-sheet.jpg", columns=6)

    report = {
        "delivery": "2026-08-12",
        "motion_count": len(motion_report),
        "sticker_count": len(sticker_report),
        "motion": motion_report,
        "stickers": sticker_report,
    }
    (QA / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"motion_count": len(motion_report), "sticker_count": len(sticker_report)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
