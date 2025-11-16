#!/usr/bin/env python3
"""
Regenerates the PNG favicons and app icons stored under static/assets.
Requires Pillow to be installed in the active Python environment.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from PIL import Image, ImageDraw

OUTPUT_SIZES: Dict[str, int] = {
    "static/assets/favicon-16x16.png": 16,
    "static/assets/favicon-32x32.png": 32,
    "static/assets/apple-touch-icon.png": 180,
    "static/assets/android-chrome-192x192.png": 192,
    "static/assets/android-chrome-512x512.png": 512,
}

COLORS = {
    "top": (255, 222, 0),
    "bottom": (255, 182, 60),
    "border": (230, 155, 0),
    "bolt": (59, 76, 202),
    "bolt_shadow": (26, 44, 121),
}

BOLT_POINTS = [
    (0.42, 0.12),
    (0.56, 0.12),
    (0.50, 0.35),
    (0.68, 0.33),
    (0.32, 0.92),
    (0.44, 0.60),
    (0.26, 0.62),
]


def build_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(size):
        ratio = y / max(size - 1, 1)
        red = int(COLORS["top"][0] * (1 - ratio) + COLORS["bottom"][0] * ratio)
        green = int(COLORS["top"][1] * (1 - ratio) + COLORS["bottom"][1] * ratio)
        blue = int(COLORS["top"][2] * (1 - ratio) + COLORS["bottom"][2] * ratio)
        draw.line([(0, y), (size, y)], fill=(red, green, blue, 255))

    margin = int(size * 0.08)
    radius = int(size * 0.22)
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=radius,
        outline=COLORS["border"],
        width=max(2, int(size * 0.04)),
    )

    highlight_bbox = (
        size * 0.20,
        size * 0.16,
        size * 0.72,
        size * 0.68,
    )
    draw.ellipse(highlight_bbox, fill=(255, 255, 255, 28))

    bolt_width = max(1, int(size * 0.05))
    points = [(x * size, y * size) for x, y in BOLT_POINTS]
    draw.polygon(points, fill=COLORS["bolt"], outline=COLORS["bolt_shadow"], width=bolt_width)

    shadow_offset = size * 0.03
    shadow_points = [(x + shadow_offset, y + shadow_offset) for x, y in points]
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.polygon(shadow_points, fill=(0, 0, 0, 60))
    img.alpha_composite(shadow)

    return img


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for rel_path, size in OUTPUT_SIZES.items():
        output_path = repo_root / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        icon = build_icon(size)
        icon.save(output_path, format="PNG")
        print(f"wrote {output_path.relative_to(repo_root)} ({size}px)")


if __name__ == "__main__":
    main()
