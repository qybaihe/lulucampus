#!/usr/bin/env python3
"""色键抠图：把生成图的纯色背景转成透明，带软边与去溢色。

原 Lulu 管线的 `remove_chroma_key.py` 在交接目录里已丢失（`GENERATION_NOTES.md`
仍引用它）。本文件按该文档记录的参数重建：显式色键、软边遮罩、阈值 40/160、去溢色。

用法：
    python3 remove_chroma_key.py in.png out.png --key "#ff00ff"
    python3 remove_chroma_key.py in.png out.png --key "#00ff00" --low 40 --high 160

参数：
    --key   背景色键。Lulu 精灵表用 #ff00ff，贴纸六宫格用纯绿 #00ff00。
    --low   低于此距离判定为纯背景（全透明）。
    --high  高于此距离判定为纯主体（全不透明）。两者之间线性过渡成软边。
    --no-despill  关闭去溢色（默认开启）。
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
from PIL import Image


def parse_hex(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) != 6:
        raise argparse.ArgumentTypeError(f"色键需要 6 位十六进制，收到 {value!r}")
    return tuple(int(v[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def remove_chroma(
    img: Image.Image,
    key: tuple[int, int, int],
    low: float,
    high: float,
    despill: bool,
) -> Image.Image:
    if high <= low:
        raise ValueError("--high 必须大于 --low")

    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    dist = np.sqrt(((rgb - np.array(key, dtype=np.float32)) ** 2).sum(axis=-1))

    # 软边：low 以下全透明，high 以上全不透明，中间线性过渡
    alpha = np.clip((dist - low) / (high - low), 0.0, 1.0)

    if despill:
        # 去溢色：把主体边缘沾到的背景色压回到另外两个通道的均值
        key_idx = int(np.argmax(key))
        others = [i for i in range(3) if i != key_idx]
        cap = rgb[..., others].mean(axis=-1)
        spill = rgb[..., key_idx] > cap
        rgb[..., key_idx] = np.where(spill, cap, rgb[..., key_idx])

    out = np.dstack([rgb, alpha * 255.0]).astype(np.uint8)
    return Image.fromarray(out, mode="RGBA")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--key", type=parse_hex, default="#ff00ff")
    ap.add_argument("--low", type=float, default=40.0)
    ap.add_argument("--high", type=float, default=160.0)
    ap.add_argument("--no-despill", dest="despill", action="store_false")
    args = ap.parse_args()

    img = Image.open(args.src)
    out = remove_chroma(img, args.key, args.low, args.high, args.despill)
    out.save(args.dst)

    opaque = (np.asarray(out)[..., 3] > 250).mean()
    print(f"{args.src} -> {args.dst}  {out.size[0]}×{out.size[1]}  不透明像素占比 {opaque:.1%}")
    if opaque < 0.02:
        print("⚠️  主体几乎全被抠掉，检查 --key 是否与实际背景色一致", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
