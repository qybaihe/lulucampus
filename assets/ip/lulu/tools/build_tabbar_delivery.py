#!/usr/bin/env python3
"""Build the generated Lulu tab-bar icon delivery.

The two source sheets are 3 columns by 2 rows.  Five occupied cells are
exported in reading order and the bottom-right cell is intentionally unused.
Active/inactive pairs share one crop and one scale so state changes do not
shift the glyph inside the tab bar.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "generated" / "2026-08-12"
SHEETS = DELIVERY / "transparent-sheets"
TABBAR = DELIVERY / "tabbar"
QA = DELIVERY / "qa"
IOS_TABBAR = ROOT.parents[2] / "ios" / "OneMore" / "Resources" / "LuluGenerated" / "TabBar"

STATES = ("active", "inactive")
NAMES = ("today", "activity", "create", "messages", "profile")
SAGE = (203, 212, 204)
CANVAS_SIZE = 512
TARGET_EXTENT = 360  # 70.3% of the canvas; ~14.8% breathing room per side.


def alpha_bbox(image: Image.Image, threshold: int = 16) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value >= threshold else 0).getbbox()
    if bbox is None:
        raise ValueError("asset has no visible pixels")
    return bbox


def union_bbox(*boxes: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def normalize_inactive(image: Image.Image) -> Image.Image:
    """Enforce the inactive token exactly while preserving the generated matte."""

    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            alpha = pixels[x, y][3]
            pixels[x, y] = (*SAGE, alpha) if alpha else (0, 0, 0, 0)
    return rgba


def fit_shared_crop(image: Image.Image, crop_box: tuple[int, int, int, int]) -> Image.Image:
    crop = image.crop(crop_box)
    ratio = TARGET_EXTENT / max(crop.width, crop.height)
    resized = crop.resize(
        (max(1, round(crop.width * ratio)), max(1, round(crop.height * ratio))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(
        resized,
        ((CANVAS_SIZE - resized.width) // 2, (CANVAS_SIZE - resized.height) // 2),
    )
    return canvas


def make_contact_sheet(paths: dict[tuple[str, str], Path], output: Path) -> None:
    cell = 220
    sheet = Image.new("RGBA", (cell * 5, cell * 2), (246, 244, 236, 255))
    draw = ImageDraw.Draw(sheet)
    for row, state in enumerate(STATES):
        for column, name in enumerate(NAMES):
            icon = Image.open(paths[(state, name)]).convert("RGBA")
            icon.thumbnail((170, 170), Image.Resampling.LANCZOS)
            x = column * cell + (cell - icon.width) // 2
            y = row * cell + (cell - icon.height) // 2
            sheet.alpha_composite(icon, (x, y))
            draw.rounded_rectangle(
                (column * cell + 1, row * cell + 1, (column + 1) * cell - 2, (row + 1) * cell - 2),
                radius=24,
                outline=(220, 227, 217, 255),
                width=2,
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(output, quality=95)


def make_25pt_preview(paths: dict[tuple[str, str], Path], output: Path) -> None:
    """Render both states at 25pt on a simulated @3x tab-bar surface."""

    scale = 3
    icon_px = 25 * scale
    slot = 120 * scale
    bar_h = 62 * scale
    sheet = Image.new("RGBA", (slot * 5, bar_h * 2), (246, 244, 236, 255))
    draw = ImageDraw.Draw(sheet)
    draw.line((0, bar_h, slot * 5, bar_h), fill=(220, 227, 217, 255), width=2)
    for row, state in enumerate(STATES):
        for column, name in enumerate(NAMES):
            icon = Image.open(paths[(state, name)]).convert("RGBA")
            size = round(icon_px * (30 / 26)) if name == "create" else icon_px
            icon = icon.resize((size, size), Image.Resampling.LANCZOS)
            x = column * slot + (slot - size) // 2
            y = row * bar_h + (bar_h - size) // 2
            sheet.alpha_composite(icon, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(output, quality=95)


def main() -> None:
    sheets = {
        state: Image.open(SHEETS / f"tabbar-{state}.png").convert("RGBA")
        for state in STATES
    }
    sizes = {image.size for image in sheets.values()}
    if len(sizes) != 1:
        raise ValueError(f"state sheet sizes do not match: {sorted(sizes)}")
    width, height = next(iter(sizes))
    if width % 3 or height % 2:
        raise ValueError(f"expected a 3x2-divisible sheet, got {width}x{height}")

    cell_w, cell_h = width // 3, height // 2
    cells: dict[tuple[str, str], Image.Image] = {}
    for state, sheet in sheets.items():
        for index, name in enumerate(NAMES):
            x = (index % 3) * cell_w
            y = (index // 3) * cell_h
            cells[(state, name)] = sheet.crop((x, y, x + cell_w, y + cell_h))

    TABBAR.mkdir(parents=True, exist_ok=True)
    IOS_TABBAR.mkdir(parents=True, exist_ok=True)
    outputs: dict[tuple[str, str], Path] = {}
    report: dict[str, object] = {
        "sheet_size": [width, height],
        "grid": [3, 2],
        "canvas_size": [CANVAS_SIZE, CANVAS_SIZE],
        "target_extent": TARGET_EXTENT,
        "icons": {},
    }

    for name in NAMES:
        active_box = alpha_bbox(cells[("active", name)])
        inactive_box = alpha_bbox(cells[("inactive", name)])
        shared_box = union_bbox(active_box, inactive_box)
        report["icons"][name] = {
            "active_source_bbox": list(active_box),
            "inactive_source_bbox": list(inactive_box),
            "shared_source_bbox": list(shared_box),
        }
        for state in STATES:
            final = fit_shared_crop(cells[(state, name)], shared_box)
            if state == "inactive":
                final = normalize_inactive(final)
            # Ensure fully transparent pixels have neutral RGB values.
            rgba = final.load()
            for y in range(final.height):
                for x in range(final.width):
                    if rgba[x, y][3] == 0:
                        rgba[x, y] = (0, 0, 0, 0)

            output = TABBAR / f"tab-{name}-{state}.png"
            final.save(output, optimize=True)
            shutil.copy2(output, IOS_TABBAR / output.name)
            outputs[(state, name)] = output

            bbox = alpha_bbox(final)
            corners = [final.getpixel(point)[3] for point in ((0, 0), (511, 0), (0, 511), (511, 511))]
            report["icons"][name][state] = {
                "size": list(final.size),
                "mode": final.mode,
                "alpha_bbox": list(bbox),
                "transparent_corners": all(alpha == 0 for alpha in corners),
            }

    QA.mkdir(parents=True, exist_ok=True)
    make_contact_sheet(outputs, QA / "tabbar-contact-sheet.png")
    make_25pt_preview(outputs, QA / "tabbar-25pt-preview.png")
    (QA / "tabbar-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
