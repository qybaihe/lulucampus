#!/usr/bin/env python3
"""Register Lulu animation frames to a stable face and foot anchor.

Generated sprite sheets often contain a few dozen pixels of character drift even
when the prompt asks for a locked camera.  Aligning by the whole alpha bounding box
does not work for kitchen clips because pans, baskets and vegetables legitimately
move.  This tool instead finds Lulu's large orange muzzle and yellow feet, shifts
the complete composition, verifies that no visible pixels were clipped, and then
rebuilds the atlas.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class Component:
    area: int
    left: int
    top: int
    right: int
    bottom: int
    center_x: float
    center_y: float

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1


@dataclass(frozen=True)
class FrameAnchor:
    muzzle_x: float
    muzzle_y: float
    foot_baseline: int
    alpha_bbox: tuple[int, int, int, int]


def connected_components(mask: np.ndarray, *, minimum_area: int = 1) -> list[Component]:
    """Return four-connected components without requiring scipy or OpenCV."""

    height, width = mask.shape
    seen = np.zeros(mask.shape, dtype=np.uint8)
    components: list[Component] = []

    for start_y, start_x in zip(*np.nonzero(mask)):
        if seen[start_y, start_x]:
            continue

        stack = [(int(start_y), int(start_x))]
        seen[start_y, start_x] = 1
        area = 0
        sum_x = 0
        sum_y = 0
        left = right = int(start_x)
        top = bottom = int(start_y)

        while stack:
            y, x = stack.pop()
            area += 1
            sum_x += x
            sum_y += y
            left = min(left, x)
            right = max(right, x)
            top = min(top, y)
            bottom = max(bottom, y)

            for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and mask[next_y, next_x]
                    and not seen[next_y, next_x]
                ):
                    seen[next_y, next_x] = 1
                    stack.append((next_y, next_x))

        if area >= minimum_area:
            components.append(
                Component(
                    area=area,
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                    center_x=sum_x / area,
                    center_y=sum_y / area,
                )
            )

    return components


def alpha_bbox(image: Image.Image, threshold: int = 16) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value >= threshold else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("frame has no visible pixels")
    return bbox


def detect_muzzle_anchor(image: Image.Image) -> tuple[float, float]:
    """Find the centroid of Lulu's large orange muzzle.

    The y crop excludes orange shorts, while selecting the largest connected
    orange region excludes the small fruit and food props.
    """

    rgba = image.convert("RGBA")
    hsv = np.asarray(rgba.convert("HSV"))
    alpha = np.asarray(rgba.getchannel("A"))
    hue, saturation, value = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    rows = np.arange(rgba.height)[:, None]
    mask = (
        (hue >= 9)
        & (hue <= 31)
        & (saturation >= 125)
        & (value >= 90)
        & (alpha >= 96)
        & (rows >= round(rgba.height * 0.18))
        & (rows < round(rgba.height * 0.70))
    )

    components = connected_components(mask, minimum_area=800)
    if not components:
        raise ValueError("could not locate Lulu's orange muzzle")
    muzzle = max(components, key=lambda component: component.area)
    return muzzle.center_x, muzzle.center_y


def detect_foot_baseline(image: Image.Image, muzzle_x: float) -> int:
    """Find Lulu's feet while ignoring low kitchen props such as baskets."""

    rgba = image.convert("RGBA")
    hsv = np.asarray(rgba.convert("HSV"))
    alpha = np.asarray(rgba.getchannel("A"))
    hue, saturation, value = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    rows = np.arange(rgba.height)[:, None]

    yellow = (
        (hue >= 24)
        & (hue <= 48)
        & (saturation >= 70)
        & (value >= 100)
        & (alpha >= 96)
        & (rows >= round(rgba.height * 0.68))
    )
    components = connected_components(yellow, minimum_area=350)
    feet = [
        component
        for component in components
        if component.top >= round(rgba.height * 0.70)
        and component.width <= round(rgba.width * 0.20)
        and component.height <= round(rgba.height * 0.15)
        and abs(component.center_x - muzzle_x) <= round(rgba.width * 0.30)
    ]
    if feet:
        return max(component.bottom for component in feet)

    # Conservative fallback for unusual lighting: use the bottommost visible
    # pixel in a narrow band beneath the detected face.
    visible = alpha >= 96
    columns = np.arange(rgba.width)[None, :]
    central = (
        visible
        & (rows >= round(rgba.height * 0.70))
        & (columns >= muzzle_x - rgba.width * 0.22)
        & (columns <= muzzle_x + rgba.width * 0.22)
    )
    candidates = np.nonzero(central)[0]
    if not len(candidates):
        raise ValueError("could not locate Lulu's foot baseline")
    return int(candidates.max())


def detect_frame_anchor(image: Image.Image, *, alpha_threshold: int = 16) -> FrameAnchor:
    muzzle_x, muzzle_y = detect_muzzle_anchor(image)
    return FrameAnchor(
        muzzle_x=muzzle_x,
        muzzle_y=muzzle_y,
        foot_baseline=detect_foot_baseline(image, muzzle_x),
        alpha_bbox=alpha_bbox(image, alpha_threshold),
    )


def safe_target_range(
    anchors: list[FrameAnchor],
    *,
    dimension: int,
    source_value: str,
    bbox_start: int,
    bbox_end: int,
) -> tuple[float, float]:
    minimum = float("-inf")
    maximum = float("inf")
    for anchor in anchors:
        value = float(getattr(anchor, source_value))
        bbox = anchor.alpha_bbox
        minimum = max(minimum, value - bbox[bbox_start])
        maximum = min(maximum, value + dimension - bbox[bbox_end])
    if minimum > maximum:
        raise ValueError("frames cannot be registered without clipping visible pixels")
    return minimum, maximum


def clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def translate(image: Image.Image, dx: int, dy: int) -> Image.Image:
    output = Image.new("RGBA", image.size, (0, 0, 0, 0))
    output.alpha_composite(image.convert("RGBA"), (dx, dy))
    return output


def alpha_mass(image: Image.Image) -> int:
    return int(np.asarray(image.getchannel("A"), dtype=np.uint64).sum())


def build_atlas(frames: list[Image.Image], *, columns: int) -> Image.Image:
    if not frames:
        raise ValueError("no frames supplied")
    width, height = frames[0].size
    if any(frame.size != (width, height) for frame in frames):
        raise ValueError("all frames must share one canvas size")
    rows = (len(frames) + columns - 1) // columns
    atlas = Image.new("RGBA", (width * columns, height * rows), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        atlas.alpha_composite(frame, ((index % columns) * width, (index // columns) * height))
    return atlas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--atlas-out", required=True)
    parser.add_argument("--columns", type=int, default=2)
    parser.add_argument("--target-x", type=float)
    parser.add_argument("--target-baseline", type=float)
    parser.add_argument("--no-align-y", action="store_true")
    parser.add_argument("--alpha-threshold", type=int, default=16)
    parser.add_argument("--max-alpha-loss", type=float, default=0.0005)
    args = parser.parse_args()

    frames_dir = Path(args.frames_dir)
    paths = sorted(frames_dir.glob("*.png"))
    if not paths:
        raise FileNotFoundError(f"no PNG frames in {frames_dir}")
    images = [Image.open(path).convert("RGBA") for path in paths]
    if len({image.size for image in images}) != 1:
        raise ValueError("all frames must share one canvas size")
    width, height = images[0].size

    anchors = [detect_frame_anchor(image, alpha_threshold=args.alpha_threshold) for image in images]
    muzzle_values = [anchor.muzzle_x for anchor in anchors]
    baseline_values = [anchor.foot_baseline for anchor in anchors]

    desired_x = (
        float(args.target_x)
        if args.target_x is not None
        else (min(muzzle_values) + max(muzzle_values)) / 2
    )
    safe_x = safe_target_range(
        anchors,
        dimension=width,
        source_value="muzzle_x",
        bbox_start=0,
        bbox_end=2,
    )
    target_x = clamp(desired_x, *safe_x)

    desired_baseline = (
        float(args.target_baseline)
        if args.target_baseline is not None
        else float(median(baseline_values))
    )
    safe_y = safe_target_range(
        anchors,
        dimension=height,
        source_value="foot_baseline",
        bbox_start=1,
        bbox_end=3,
    )
    target_baseline = clamp(desired_baseline, *safe_y)

    registered: list[Image.Image] = []
    print(
        f"before: muzzle-x={','.join(f'{value:.2f}' for value in muzzle_values)} "
        f"drift={max(muzzle_values) - min(muzzle_values):.2f}px "
        f"feet={','.join(str(value) for value in baseline_values)}"
    )
    print(f"target: muzzle-x={target_x:.2f} foot-baseline={target_baseline:.2f}")

    for path, image, anchor in zip(paths, images, anchors):
        dx = round(target_x - anchor.muzzle_x)
        dy = 0 if args.no_align_y else round(target_baseline - anchor.foot_baseline)
        before_mass = alpha_mass(image)
        shifted = translate(image, dx, dy)
        after_mass = alpha_mass(shifted)
        loss = max(0, before_mass - after_mass) / max(1, before_mass)
        if loss > args.max_alpha_loss:
            raise ValueError(f"{path.name}: alpha loss {loss:.6%} exceeds limit")
        shifted.save(path, optimize=True)
        registered.append(shifted)
        print(f"{path.name}: dx={dx:+d} dy={dy:+d} alpha-loss={loss:.6%}")

    after_anchors = [
        detect_frame_anchor(image, alpha_threshold=args.alpha_threshold) for image in registered
    ]
    after_muzzles = [anchor.muzzle_x for anchor in after_anchors]
    after_feet = [anchor.foot_baseline for anchor in after_anchors]
    print(
        f"after:  muzzle-x={','.join(f'{value:.2f}' for value in after_muzzles)} "
        f"drift={max(after_muzzles) - min(after_muzzles):.2f}px "
        f"feet={','.join(str(value) for value in after_feet)}"
    )

    atlas_path = Path(args.atlas_out)
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    build_atlas(registered, columns=args.columns).save(atlas_path, optimize=True)
    print(f"atlas: {atlas_path}")


if __name__ == "__main__":
    main()
