#!/usr/bin/env python3
"""Render a clean scannable QR for the Douyin taste demo."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import qrcode
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
LULU_PATH = ROOT / "onemore-taste-edge/src/assets/lulu-wave.png"
OUT_PATH = ROOT / "onemore-taste-edge/public/share/lulu-taste-qr.png"
URL = "https://luludrawu.classby.cn"

WHITE = (255, 255, 255, 255)
INK = (31, 45, 37, 255)
YOLK = (246, 201, 69, 255)


def cutout_lulu(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    bgr = cv2.cvtColor(np.array(im), cv2.COLOR_RGBA2BGR)
    h, w = bgr.shape[:2]
    flood = np.zeros((h + 2, w + 2), np.uint8)
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        cv2.floodFill(
            bgr,
            flood,
            seed,
            (0, 0, 0),
            loDiff=(14, 14, 14),
            upDiff=(14, 14, 14),
            flags=cv2.FLOODFILL_MASK_ONLY | 4,
        )
    bg = flood[1:-1, 1:-1] > 0
    dist = cv2.distanceTransform((~bg).astype(np.uint8), cv2.DIST_L2, 5)
    alpha = np.clip(dist * 180.0, 0, 255).astype(np.uint8)
    alpha[bg] = 0
    arr = np.array(im)
    arr[:, :, 3] = np.minimum(arr[:, :, 3], alpha)
    return Image.fromarray(arr, "RGBA")


def circle_badge(src: Image.Image, diameter: int, ring: int = 8) -> Image.Image:
    size = diameter + ring * 2
    badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    draw.ellipse((0, 0, size - 1, size - 1), fill=YOLK)
    inner = ring - 2
    draw.ellipse((inner, inner, size - 1 - inner, size - 1 - inner), fill=WHITE)
    mascot = src.copy()
    mascot.thumbnail((diameter - 8, diameter - 8), Image.Resampling.LANCZOS)
    bx = (size - mascot.width) // 2
    by = (size - mascot.height) // 2 + 2
    badge.alpha_composite(mascot, (bx, by))
    return badge


def finder_boxes(n: int) -> list[tuple[int, int, int, int]]:
    return [(0, 0, 7, 7), (n - 7, 0, 7, 7), (0, n - 7, 7, 7)]


def in_rect(x: int, y: int, box: tuple[int, int, int, int]) -> bool:
    ox, oy, w, h = box
    return ox <= x < ox + w and oy <= y < oy + h


def render_qr(url: str, pixel: int, logo: Image.Image) -> Image.Image:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=1,
        border=0,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    quiet = 4
    modules = n + quiet * 2
    m = max(8, pixel // modules)
    canvas = modules * m
    img = Image.new("RGBA", (canvas, canvas), WHITE)
    draw = ImageDraw.Draw(img)

    def cell(x: int, y: int) -> tuple[int, int, int, int]:
        sx = (x + quiet) * m
        sy = (y + quiet) * m
        return (sx, sy, sx + m - 1, sy + m - 1)

    finders = finder_boxes(n)
    for y, row in enumerate(matrix):
        for x, on in enumerate(row):
            if not on or any(in_rect(x, y, box) for box in finders):
                continue
            r = max(1, m // 5)
            draw.rounded_rectangle(cell(x, y), radius=r, fill=INK)

    for ox, oy, _w, _h in finders:
        outer = cell(ox, oy)
        outer = (outer[0], outer[1], cell(ox + 6, oy + 6)[2], cell(ox + 6, oy + 6)[3])
        draw.rounded_rectangle(outer, radius=max(3, m // 4), fill=INK)
        inner = cell(ox + 1, oy + 1)
        inner = (inner[0], inner[1], cell(ox + 5, oy + 5)[2], cell(ox + 5, oy + 5)[3])
        draw.rounded_rectangle(inner, radius=max(2, m // 5), fill=WHITE)
        core = cell(ox + 2, oy + 2)
        core = (core[0], core[1], cell(ox + 4, oy + 4)[2], cell(ox + 4, oy + 4)[3])
        draw.rounded_rectangle(core, radius=max(1, m // 6), fill=INK)

    max_logo = int(canvas * 0.16)
    badge = circle_badge(logo, max_logo, ring=max(6, m))
    img.alpha_composite(badge, ((canvas - badge.width) // 2, (canvas - badge.height) // 2))
    return img


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lulu = cutout_lulu(LULU_PATH)
    qr = render_qr(URL, 1024, lulu)
    qr.save(OUT_PATH, "PNG", optimize=True)
    poster = OUT_PATH.with_name("lulu-taste-qr-poster.png")
    if poster.exists():
        poster.unlink()
    print(OUT_PATH)


if __name__ == "__main__":
    main()
