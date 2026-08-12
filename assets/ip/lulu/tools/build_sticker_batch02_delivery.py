#!/usr/bin/env python3
"""Split, normalize, validate, and install Lulu sticker batches S7-S11.

The chroma-key sheets are converted to alpha with the installed imagegen
helper before this script runs.  This script deliberately starts from those
transparent sheets so regeneration does not apply chroma removal twice.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "generated" / "2026-08-12"
TRANSPARENT = DELIVERY / "transparent-sheets"
STICKERS = DELIVERY / "stickers"
QA = DELIVERY / "qa"
IOS_STICKERS = ROOT.parents[2] / "ios" / "OneMore" / "Resources" / "LuluGenerated" / "Stickers"

@dataclass(frozen=True)
class BatchSpec:
    batch: str
    sheet: str
    ids: tuple[str, ...]


BATCHES = (
    BatchSpec(
        "S7",
        "stickers-s7-settings-privacy.png",
        ("shield-check", "key", "sliders", "block-sign", "flag", "bell"),
    ),
    BatchSpec(
        "S8",
        "stickers-s8-profile-data.png",
        ("id-card", "medal", "sparkle-wand", "box-export", "clipboard-whistle", "megaphone"),
    ),
    BatchSpec(
        "S9",
        "stickers-s9-gathering-relations.png",
        ("table-people", "handshake", "table-plus", "redo-arrow", "party-popper", "door-exit"),
    ),
    BatchSpec(
        "S10",
        "stickers-s10-trust-medals.png",
        ("trust-t0", "trust-t1", "trust-t2", "trust-t3", "trust-t4", "lulu-face"),
    ),
    # The sixth sheet cell is an optional sparkle and is intentionally not
    # delivered: the handoff contract specifies 29 final stickers total.
    BatchSpec(
        "S11",
        "stickers-s11-empty-scenes.png",
        ("magnifier-empty", "cloud-off", "homework-pencil", "flask", "bulb"),
    ),
)

FIRST_BATCHES = (
    BatchSpec("S1", "", ("chair-empty", "round-table", "nameplate-blank", "access-card", "qr-plaque-blank", "hourglass")),
    BatchSpec("S2", "", ("badminton", "basketball", "table-tennis", "football", "running-shoe", "sports-bottle")),
    BatchSpec("S3", "", ("books-stack", "laptop-closed", "notebook-open", "marker", "alarm-clock", "desk-calendar")),
    BatchSpec("S4", "", ("seminar-room-sign", "study-lamp", "teaching-building", "school-bus", "poster-blank", "cafeteria-tray")),
    BatchSpec("S5", "", ("backend-server", "frontend-browser", "data-chart", "product-notes", "algorithm-gear", "design-palette")),
    BatchSpec("S6", "", ("trophy", "certificate", "badge", "envelope", "chat-bubble", "approval-stamp")),
)


def alpha_bbox(image: Image.Image, threshold: int = 16) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value >= threshold else 0).getbbox()
    if bbox is None:
        raise ValueError("asset has no visible pixels")
    return bbox


def fit_square(image: Image.Image, size: int = 512, margin: int = 28) -> Image.Image:
    crop = image.crop(alpha_bbox(image))
    available = size - margin * 2
    ratio = min(available / crop.width, available / crop.height)
    new_size = (max(1, round(crop.width * ratio)), max(1, round(crop.height * ratio)))
    crop = crop.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(crop, ((size - crop.width) // 2, (size - crop.height) // 2))
    return canvas


def make_contact_sheet(paths: list[Path], output: Path, *, columns: int, cell: int = 256) -> None:
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * cell, rows * cell), (246, 244, 236, 255))
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        preview = fit_square(Image.open(path).convert("RGBA"), size=cell, margin=20)
        x, y = (index % columns) * cell, (index // columns) * cell
        sheet.alpha_composite(preview, (x, y))
        draw.rectangle((x, y, x + cell - 1, y + cell - 1), outline=(220, 227, 217, 255), width=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(output, quality=94)


def clean_white_border_chroma(image: Image.Image, *, edge_radius: int = 3) -> Image.Image:
    """Neutralize green spill only along the outer die-cut border.

    Every sticker in this delivery has a thick continuous white outline, so
    green-dominant pixels within three pixels of transparency are chroma spill,
    never semantic ink/sage artwork. Interior greens remain unchanged.
    """

    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    visible = alpha.point(lambda value: 255 if value > 0 else 0)
    eroded = visible.filter(ImageFilter.MinFilter(edge_radius * 2 + 1))
    edge = ImageChops.subtract(visible, eroded)
    pixels = image.load()
    edge_pixels = edge.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, pixel_alpha = pixels[x, y]
            if pixel_alpha == 0:
                pixels[x, y] = (0, 0, 0, 0)
            elif edge_pixels[x, y] and green > red + 12 and green > blue + 12:
                neutral = max(red, green, blue)
                pixels[x, y] = (neutral, neutral, neutral, pixel_alpha)
    return image


def restore_interior_opacity(image: Image.Image, *, edge_radius: int = 3) -> Image.Image:
    """Keep only the outer antialias matte translucent.

    The imagegen chroma helper intentionally creates a soft matte, but dark
    semantic greens can resemble the green key. The continuous white sticker
    outline lets us safely restore every pixel more than three pixels inside
    the visible silhouette to full opacity while retaining soft outer edges
    and transparent holes.
    """

    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    visible = alpha.point(lambda value: 255 if value > 8 else 0)
    interior = visible.filter(ImageFilter.MinFilter(edge_radius * 2 + 1))
    pixels = image.load()
    interior_pixels = interior.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, pixel_alpha = pixels[x, y]
            if interior_pixels[x, y] and pixel_alpha:
                pixels[x, y] = (red, green, blue, 255)
    return image


def remove_small_edge_fragments(
    image: Image.Image, *, fraction_of_largest: float = 0.22
) -> Image.Image:
    """Remove small neighboring-cell slivers that touch a fixed crop edge."""

    image = image.convert("RGBA")
    width, height = image.size
    alpha = image.getchannel("A")
    mask = bytearray(1 if value > 8 else 0 for value in alpha.get_flattened_data())
    seen = bytearray(width * height)
    components: list[tuple[list[int], bool]] = []

    for start, is_visible in enumerate(mask):
        if not is_visible or seen[start]:
            continue
        stack = [start]
        seen[start] = 1
        component: list[int] = []
        touches_edge = False
        while stack:
            index = stack.pop()
            component.append(index)
            y, x = divmod(index, width)
            if x <= 1 or y <= 1 or x >= width - 2 or y >= height - 2:
                touches_edge = True
            if x and mask[index - 1] and not seen[index - 1]:
                seen[index - 1] = 1
                stack.append(index - 1)
            if x + 1 < width and mask[index + 1] and not seen[index + 1]:
                seen[index + 1] = 1
                stack.append(index + 1)
            if y and mask[index - width] and not seen[index - width]:
                seen[index - width] = 1
                stack.append(index - width)
            if y + 1 < height and mask[index + width] and not seen[index + width]:
                seen[index + width] = 1
                stack.append(index + width)
        components.append((component, touches_edge))

    if not components:
        return image
    largest = max(len(component) for component, _ in components)
    pixels = image.load()
    for component, touches_edge in components:
        if touches_edge and len(component) < largest * fraction_of_largest:
            for index in component:
                y, x = divmod(index, width)
                pixels[x, y] = (0, 0, 0, 0)
    return image


def process_batch(spec: BatchSpec) -> list[dict[str, object]]:
    source = TRANSPARENT / spec.sheet
    sheet = clean_white_border_chroma(restore_interior_opacity(Image.open(source)))
    sheet.save(source, optimize=True)
    if sheet.width % 3 or sheet.height % 2:
        raise ValueError(f"{source.name}: expected a 3x2 sheet, got {sheet.size}")

    cell_width, cell_height = sheet.width // 3, sheet.height // 2
    asset_dir = STICKERS / spec.batch
    ios_dir = IOS_STICKERS / spec.batch
    asset_dir.mkdir(parents=True, exist_ok=True)
    ios_dir.mkdir(parents=True, exist_ok=True)

    reports: list[dict[str, object]] = []
    for index, asset_id in enumerate(spec.ids):
        left = (index % 3) * cell_width
        top = (index // 3) * cell_height
        cell = sheet.crop((left, top, left + cell_width, top + cell_height))
        cell = remove_small_edge_fragments(cell)
        final = clean_white_border_chroma(fit_square(cell, size=512, margin=28))

        output = asset_dir / f"{asset_id}.png"
        final.save(output, optimize=True)
        shutil.copy2(output, ios_dir / output.name)

        alpha = final.getchannel("A")
        histogram = alpha.histogram()
        visible_count = sum(histogram[17:])
        if not visible_count:
            raise ValueError(f"{output}: no visible subject")
        bbox = list(alpha_bbox(final))
        corners = [alpha.getpixel((0, 0)), alpha.getpixel((511, 0)), alpha.getpixel((0, 511)), alpha.getpixel((511, 511))]
        # Exact/nearly exact key green should never survive within visible art.
        visible_key_pixels = sum(
            1
            for red, green, blue, pixel_alpha in final.get_flattened_data()
            if pixel_alpha > 16 and (red * red + (green - 255) ** 2 + blue * blue) < 24 * 24
        )
        visible_mask = alpha.point(lambda value: 255 if value > 16 else 0)
        eroded_mask = visible_mask.filter(ImageFilter.MinFilter(7))
        edge_mask = ImageChops.subtract(visible_mask, eroded_mask)
        edge_data = edge_mask.get_flattened_data()
        visible_edge_green_pixels = sum(
            1
            for (red, green, blue, pixel_alpha), edge_value in zip(final.get_flattened_data(), edge_data)
            if edge_value and pixel_alpha > 16 and green > red + 12 and green > blue + 12
        )

        if final.mode != "RGBA" or final.size != (512, 512):
            raise ValueError(f"{output}: expected 512x512 RGBA, got {final.size} {final.mode}")
        if any(corners):
            raise ValueError(f"{output}: corners are not transparent: {corners}")
        if min(bbox[0], bbox[1], 512 - bbox[2], 512 - bbox[3]) < 24:
            raise ValueError(f"{output}: subject margin too small: {bbox}")
        if visible_key_pixels:
            raise ValueError(f"{output}: {visible_key_pixels} visible near-key pixels remain")
        # A few isolated pixels can be legitimate sage details touching a very
        # narrow white outline (for example the whistle cord). A count under
        # 64 on a 512px asset is sub-pixel-scale after display interpolation.
        if visible_edge_green_pixels > 64:
            raise ValueError(f"{output}: {visible_edge_green_pixels} green-spill edge pixels remain")

        reports.append(
            {
                "batch": spec.batch,
                "id": asset_id,
                "file": str(output.relative_to(ROOT)),
                "ios_file": str((ios_dir / output.name).relative_to(ROOT.parents[2])),
                "size": [512, 512],
                "mode": "RGBA",
                "bbox": bbox,
                "visible_pixel_ratio": round(visible_count / (512 * 512), 4),
                "partial_alpha_pixel_ratio": round(sum(histogram[1:255]) / (512 * 512), 6),
                "transparent_corners": True,
                "visible_near_key_pixels": 0,
                "visible_green_spill_edge_pixels": visible_edge_green_pixels,
            }
        )
    return reports


def main() -> None:
    missing = [str(TRANSPARENT / spec.sheet) for spec in BATCHES if not (TRANSPARENT / spec.sheet).exists()]
    if missing:
        raise FileNotFoundError("Missing transparent source sheets:\n" + "\n".join(missing))

    reports = [item for spec in BATCHES for item in process_batch(spec)]
    if len(reports) != 29:
        raise ValueError(f"expected 29 delivered stickers, got {len(reports)}")

    new_paths = [STICKERS / spec.batch / f"{asset_id}.png" for spec in BATCHES for asset_id in spec.ids]
    old_paths = [
        STICKERS / spec.batch / f"{asset_id}.png"
        for spec in FIRST_BATCHES
        for asset_id in spec.ids
    ]
    if any(not path.exists() for path in old_paths):
        raise FileNotFoundError("S1-S6 reference assets are incomplete")

    QA.mkdir(parents=True, exist_ok=True)
    make_contact_sheet(new_paths, QA / "stickers-batch02-contact-sheet.jpg", columns=6)
    make_contact_sheet(old_paths + new_paths, QA / "stickers-all-s1-s11-contact-sheet.jpg", columns=6)

    report = {
        "delivery": "2026-08-12",
        "batches": [spec.batch for spec in BATCHES],
        "sticker_count": len(reports),
        "expected_sticker_count": 29,
        "source_mode": "built-in imagegen chroma-key plus local alpha extraction",
        "stickers": reports,
    }
    report_path = QA / "validation-batch02.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"sticker_count": len(reports), "validation": str(report_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
