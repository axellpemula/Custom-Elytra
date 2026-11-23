#!/usr/bin/env python3
"""
Render a pack icon for every subpack.

The icon shows the subpack's own model in a three-quarter view on a coloured
card, so the Pack Settings list is readable without opening the game.

Usage:
    python3 tools/build_icons.py
"""

import os

import numpy as np
from PIL import Image, ImageDraw

import packpaths  # noqa: F401
from packpaths import PACK
from render_model import load_geometry, render

ICON = 512          # rendered icon size
TEXTURE = "textures/models/intity/samurai.png"
GEOMETRY = "models/mobs.json"


def _label_font(size):
    from PIL import ImageFont

    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def render_icon(geometry, texture, bg, accent, size=ICON, yaw=152.0, pitch=14.0):
    """Render a model on a tinted card and return a PIL image."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "icon.png")
        render(
            geometry, texture, out,
            size=size, yaw=yaw, pitch=pitch,
            bg=(255, 255, 255, 0), outline=False, supersample=2,
        )
        art = Image.open(out).convert("RGBA")

    bbox = art.getbbox()
    if bbox:
        art = art.crop(bbox)

    # card: soft vertical gradient in the subpack's theme colour
    card = Image.new("RGBA", (size, size), bg + (255,))
    grad = np.zeros((size, size, 3), dtype=np.float32)
    base = np.array(bg, dtype=np.float32)
    glow = np.array(bg, dtype=np.float32) * 0.45 + np.array((18, 18, 22), dtype=np.float32) * 0.55
    for y in range(size):
        t = y / (size - 1)
        grad[y, :, :] = glow * (1 - t) + base * t
    card = Image.fromarray(np.clip(grad, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    # accent ring
    draw = ImageDraw.Draw(card)
    accent_rgb = tuple(int(accent.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    draw.rectangle([0, 0, size - 1, size - 1], outline=accent_rgb + (110,), width=3)

    scale = min((size - 56) / art.width, (size - 56) / art.height)
    art = art.resize((max(1, int(art.width * scale)), max(1, int(art.height * scale))), Image.LANCZOS)
    card.paste(art, ((size - art.width) // 2, (size - art.height) // 2), art)
    return card


def icon_for_subpack(subpack_dir, bg, accent):
    """Write <subpack>/pack_icon.png for one subpack folder."""
    geo_path = os.path.join(subpack_dir, GEOMETRY)
    tex_path = os.path.join(subpack_dir, TEXTURE)
    if not os.path.exists(geo_path):
        # recolour subpacks only ship a texture: preview the pack's own model
        geo_path = os.path.join(PACK, GEOMETRY)
    if not os.path.exists(tex_path):
        tex_path = os.path.join(PACK, TEXTURE)

    geometry = load_geometry(geo_path)
    card = render_icon(geometry, tex_path, bg, accent)
    out = os.path.join(subpack_dir, "pack_icon.png")
    card.save(out, optimize=True)
    return out


def main():
    from packpaths import SUBPACKS

    themes = {
        "phoenix": ((46, 12, 14), "#ff8a3c"),
        "phoenix_dark": ((26, 6, 9), "#ff5a2a"),
        "seraph": ((14, 26, 36), "#a8e4ff"),
        "seraph_gold": ((38, 28, 12), "#ffe7a0"),
        "dragon": ((20, 10, 32), "#c07cf5"),
        "dragon_ember": ((28, 11, 6), "#ff9a52"),
        "fantasy_frost": ((14, 30, 42), "#a8e4ff"),
        "fantasy_inferno": ((40, 16, 8), "#ff9a45"),
        "fantasy_void": ((26, 12, 38), "#c88cff"),
        "fantasy_verdant": ((14, 32, 18), "#8ce8a0"),
        "fantasy_astral": ((22, 14, 40), "#e0a0f0"),
        "fantasy_celestial": ((34, 34, 40), "#ffe9b0"),
        "original_samurai": ((30, 26, 22), "#ffc75a"),
    }
    for folder, (bg, accent) in themes.items():
        path = os.path.join(SUBPACKS, folder)
        if os.path.isdir(path):
            print("icon", folder)
            icon_for_subpack(path, bg, accent)


if __name__ == "__main__":
    main()
