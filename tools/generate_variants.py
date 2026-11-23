#!/usr/bin/env python3
"""
Recoloured variants of the ORIGINAL samurai elytra.

These keep the samurai model and only shift its palette, so they are marked as
"Recolour" in the manifest to stay clearly separated from the from-scratch
models in tools/build_designs.py.

The original texture (textures/models/intity/samurai.png) uses exactly 32 opaque
colours, each belonging to a small "family" (charcoal armour, gold trim, red
blade, cyan crystal, ...).  Every variant is produced by remapping those
families onto a new theme palette in HSV space, which keeps the pixel-art
shading, the hue noise inside each family and the alpha channel untouched.

Usage:
    python3 tools/generate_variants.py      # writes the subpack textures
    python3 tools/build_pack.py             # rebuilds manifest + mcpack
"""

import colorsys
import json
import os
import shutil

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "Custom Elytra")
TEXTURE = os.path.join(PACK, "textures", "models", "intity", "samurai.png")
ICON = os.path.join(PACK, "pack_icon.png")

# --------------------------------------------------------------------------
# Colour families of the source texture -> base hue used for the hue shift.
# --------------------------------------------------------------------------
BASE_HUE = {
    "metal": 0.0,       # charcoal armour plates
    "slate": 214.0,     # bluish metal
    "slate_pale": 197.0,
    "gold": 36.0,       # gold trim
    "gold_pale": 56.0,
    "red": 355.0,       # blade / red cloth
    "red_pale": 1.0,
    "peach": 16.0,
    "cyan": 201.0,      # crystal highlights
    "white": 197.0,
    "green": 143.0,     # small glowing accents
}

ROLES = {
    (19, 17, 18): "metal",
    (33, 30, 31): "metal",
    (48, 43, 43): "metal",
    (62, 56, 56): "metal",
    (71, 65, 65): "metal",
    (81, 74, 73): "metal",
    (83, 97, 116): "slate",
    (110, 120, 140): "slate",
    (180, 212, 225): "slate_pale",
    (220, 125, 87): "gold",
    (220, 139, 87): "gold",
    (220, 153, 87): "gold",
    (220, 167, 87): "gold",
    (220, 181, 87): "gold",
    (220, 195, 87): "gold",
    (220, 209, 87): "gold",
    (248, 221, 114): "gold",
    (248, 186, 130): "gold",
    (255, 248, 153): "gold_pale",
    (200, 10, 71): "red",
    (237, 12, 48): "red",
    (244, 45, 45): "red",
    (244, 134, 134): "red_pale",
    (255, 167, 164): "red_pale",
    (247, 148, 102): "peach",
    (245, 101, 73): "peach",
    (91, 188, 244): "cyan",
    (123, 212, 255): "cyan",
    (236, 248, 253): "white",
    (67, 232, 141): "green",
    (123, 255, 163): "green",
}


# --------------------------------------------------------------------------
# Themes.  Each role maps to a dict with any of:
#   hue  : new absolute hue (the original hue offset inside the family is kept)
#   hue_k: multiplier for that hue offset (default 1.0, 0 = flatten it)
#   s    : absolute saturation (0..1)
#   s_mul: multiply the original saturation
#   v    : absolute value (0..1)
#   v_mul: multiply the original value
# --------------------------------------------------------------------------
THEMES = {
    "fantasy_frost": {
        "label": "Frost",
        "roles": {
            "metal": {"hue": 212, "s": 0.34, "v_mul": 1.30},
            "slate": {"hue": 205, "s_mul": 1.30, "v_mul": 1.20},
            "slate_pale": {"hue": 200, "s": 0.30, "v_mul": 1.05},
            "gold": {"hue": 198, "s": 0.22, "v_mul": 1.10},
            "gold_pale": {"hue": 190, "s": 0.12, "v": 1.0},
            "red": {"hue": 188, "s_mul": 0.85, "v_mul": 1.05},
            "red_pale": {"hue": 192, "s_mul": 0.55, "v": 1.0},
            "peach": {"hue": 195, "s_mul": 0.55, "v": 1.0},
            "cyan": {"hue": 200, "s_mul": 0.85, "v": 1.0},
            "white": {"hue": 200, "s": 0.06},
            "green": {"hue": 178, "s_mul": 0.80},
        },
    },
    "fantasy_inferno": {
        "label": "Inferno",
        "roles": {
            "metal": {"hue": 10, "s": 0.52, "v_mul": 1.45},
            "slate": {"hue": 12, "s_mul": 1.25, "v_mul": 1.10},
            "slate_pale": {"hue": 28, "s": 0.35, "v_mul": 1.0},
            "gold": {"hue": 32, "s": 0.82, "v_mul": 1.0},
            "gold_pale": {"hue": 50, "s": 0.55, "v": 1.0},
            "red": {"hue": 26, "s_mul": 1.0, "v_mul": 1.0},
            "red_pale": {"hue": 40, "s_mul": 0.80, "v": 1.0},
            "peach": {"hue": 34, "s_mul": 0.80, "v": 1.0},
            "cyan": {"hue": 50, "s_mul": 0.80, "v": 1.0},
            "white": {"hue": 45, "s": 0.22},
            "green": {"hue": 32, "s_mul": 1.0},
        },
    },
    "fantasy_void": {
        "label": "Void",
        "roles": {
            "metal": {"hue": 270, "s": 0.42, "v_mul": 0.92},
            "slate": {"hue": 266, "s_mul": 1.15, "v_mul": 0.95},
            "slate_pale": {"hue": 285, "s": 0.35, "v_mul": 1.0},
            "gold": {"hue": 288, "s": 0.55, "v_mul": 0.95},
            "gold_pale": {"hue": 300, "s": 0.40, "v": 1.0},
            "red": {"hue": 310, "s_mul": 0.95, "v_mul": 1.0},
            "red_pale": {"hue": 320, "s_mul": 0.70, "v": 1.0},
            "peach": {"hue": 300, "s_mul": 0.75, "v": 1.0},
            "cyan": {"hue": 280, "s_mul": 0.95, "v": 1.0},
            "white": {"hue": 290, "s": 0.12},
            "green": {"hue": 148, "s_mul": 1.0},
        },
    },
    "fantasy_verdant": {
        "label": "Verdant",
        "roles": {
            "metal": {"hue": 138, "s": 0.38, "v_mul": 0.95},
            "slate": {"hue": 160, "s_mul": 1.10, "v_mul": 0.95},
            "slate_pale": {"hue": 150, "s": 0.32, "v_mul": 1.0},
            "gold": {"hue": 92, "s": 0.52, "v_mul": 0.98},
            "gold_pale": {"hue": 80, "s": 0.40, "v": 1.0},
            "red": {"hue": 146, "s_mul": 0.95, "v_mul": 1.0},
            "red_pale": {"hue": 150, "s_mul": 0.65, "v": 1.0},
            "peach": {"hue": 120, "s_mul": 0.70, "v": 1.0},
            "cyan": {"hue": 165, "s_mul": 0.90, "v": 1.0},
            "white": {"hue": 150, "s": 0.12},
            "green": {"hue": 142, "s_mul": 1.0},
        },
    },
    "fantasy_astral": {
        "label": "Astral",
        "roles": {
            "metal": {"hue": 250, "s": 0.55, "v_mul": 1.55},
            "slate": {"hue": 245, "s_mul": 1.30, "v_mul": 1.15},
            "slate_pale": {"hue": 250, "s": 0.32, "v_mul": 1.0},
            "gold": {"hue": 42, "s": 0.66, "v_mul": 1.05},
            "gold_pale": {"hue": 55, "s": 0.42, "v": 1.0},
            "red": {"hue": 322, "s_mul": 0.90, "v_mul": 1.0},
            "red_pale": {"hue": 330, "s_mul": 0.70, "v": 1.0},
            "peach": {"hue": 315, "s_mul": 0.70, "v": 1.0},
            "cyan": {"hue": 282, "s_mul": 0.95, "v": 1.0},
            "white": {"hue": 280, "s": 0.14},
            "green": {"hue": 190, "s_mul": 0.85},
        },
    },
    "fantasy_celestial": {
        "label": "Celestial",
        "roles": {
            "metal": {"hue": 222, "s": 0.10, "v_mul": 1.95},
            "slate": {"hue": 218, "s_mul": 0.40, "v_mul": 1.15},
            "slate_pale": {"hue": 210, "s": 0.10, "v_mul": 1.05},
            "gold": {"hue": 46, "s": 0.68, "v_mul": 1.08},
            "gold_pale": {"hue": 55, "s": 0.35, "v": 1.0},
            "red": {"hue": 45, "s_mul": 0.60, "v_mul": 1.08},
            "red_pale": {"hue": 52, "s_mul": 0.45, "v": 1.0},
            "peach": {"hue": 40, "s_mul": 0.55, "v": 1.0},
            "cyan": {"hue": 198, "s_mul": 0.90, "v": 1.0},
            "white": {"hue": 210, "s": 0.04},
            "green": {"hue": 96, "s_mul": 0.75},
        },
    },
}


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def remap_rgb(rgb, spec, base_hue):
    """Map one source colour onto a themed colour."""
    r, g, b = [c / 255.0 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    hue_deg = h * 360.0

    # keep the small hue variation *inside* a family (gold noise, red shading)
    delta = (hue_deg - base_hue + 180.0) % 360.0 - 180.0
    if "hue" in spec:
        new_hue = spec["hue"] + delta * spec.get("hue_k", 1.0)
    else:
        new_hue = hue_deg
    new_hue %= 360.0

    if "s" in spec:
        new_s = spec["s"]
    else:
        new_s = s * spec.get("s_mul", 1.0)

    if "v" in spec:
        new_v = spec["v"]
    else:
        new_v = v * spec.get("v_mul", 1.0)

    r, g, b = colorsys.hsv_to_rgb(new_hue / 360.0, _clamp(new_s), _clamp(new_v))
    return tuple(int(round(c * 255)) for c in (r, g, b))


def build_lut(theme):
    lookup = {}
    for rgb, role in ROLES.items():
        lookup[rgb] = remap_rgb(rgb, theme["roles"][role], BASE_HUE[role])
    return lookup


def recolor_texture(src, lut, dst):
    """Exact palette swap - alpha and every non-palette pixel are preserved."""
    img = Image.open(src).convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            hit = lut.get((r, g, b))
            if hit is not None:
                px[x, y] = (hit[0], hit[1], hit[2], a)
    img.save(dst, optimize=True)
    return img


def nearest_lut(rgb, lut):
    """Fallback for anti-aliased pixels (pack icon): nearest palette colour."""
    best, best_d = None, None
    for src_rgb, dst_rgb in lut.items():
        d = sum((a - b) ** 2 for a, b in zip(rgb, src_rgb))
        if best_d is None or d < best_d:
            best, best_d = dst_rgb, d
    return best


def recolor_icon(src, lut, dst, tolerance=2600):
    """Recolour the pack icon using the same palette, keeping its shading."""
    img = Image.open(src).convert("RGBA")
    px = img.load()
    cache = {}
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            key = (r, g, b)
            if key in cache:
                new = cache[key]
            elif key in lut:
                new = lut[key]
            else:
                near, d = None, None
                for src_rgb, dst_rgb in lut.items():
                    dd = sum((c1 - c2) ** 2 for c1, c2 in zip(key, src_rgb))
                    if d is None or dd < d:
                        near, d = dst_rgb, dd
                if d is not None and d > tolerance:
                    # blend a little towards the nearest family so gradients stay smooth
                    near = tuple(
                        int(round(c1 * 0.65 + c2 * 0.35)) for c1, c2 in zip(key, near)
                    )
                new = near or key
                cache[key] = new
            px[x, y] = (new[0], new[1], new[2], a)
    img.save(dst, optimize=True)
    return img


def generate():
    """Write every recolour subpack and return its manifest entry."""
    os.makedirs(os.path.join(PACK, "subpacks"), exist_ok=True)
    subpacks = []

    # the original artwork is re-used as its own subpack so players can always
    # switch back to the untouched samurai look
    original_dir = os.path.join(PACK, "subpacks", "original_samurai")
    tex_dir = os.path.join(original_dir, "textures", "models", "intity")
    os.makedirs(tex_dir, exist_ok=True)
    shutil.copy2(TEXTURE, os.path.join(tex_dir, "samurai.png"))
    shutil.copy2(ICON, os.path.join(original_dir, "pack_icon.png"))
    subpacks.append({"folder_name": "original_samurai", "name": "Samurai (Original)"})

    for folder, theme in THEMES.items():
        lut = build_lut(theme)
        out_dir = os.path.join(PACK, "subpacks", folder)
        tex_dir = os.path.join(out_dir, "textures", "models", "intity")
        os.makedirs(tex_dir, exist_ok=True)
        recolor_texture(TEXTURE, lut, os.path.join(tex_dir, "samurai.png"))
        recolor_icon(ICON, lut, os.path.join(out_dir, "pack_icon.png"))
        subpacks.append({"folder_name": folder, "name": "Recolour - %s" % theme["label"]})
    return subpacks


def main():
    subpacks = generate()
    for sub in subpacks:
        print("generated", sub["folder_name"], "->", sub["name"])
    print("%d recolour subpacks ready" % len(subpacks))


if __name__ == "__main__":
    main()
