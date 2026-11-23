#!/usr/bin/env python3
"""
Build a preview sheet (docs/skins-preview.png) that shows every subpack skin
side by side with its name, so the skins can be compared without opening the
game.

Usage:
    python3 tools/build_preview.py
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "Custom Elytra")
OUT = os.path.join(ROOT, "docs", "skins-preview.png")

CARD_W = 300          # width of one card in the sheet
PAD = 18              # padding between cards
LABEL_H = 34          # space under each card for the name
BG = (22, 22, 27, 255)
CARD_BG = (34, 34, 41, 255)


def load_font(size):
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ):
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def card(path):
    img = Image.open(path).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    scale = min(CARD_W / img.width, CARD_W / img.height)
    return img.resize(
        (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
        Image.LANCZOS,
    )


def main():
    with open(os.path.join(PACK, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)

    subs = list(manifest.get("subpacks", []))

    def sort_key(sub):
        name = sub["name"]
        if name.startswith("Samurai"):
            return (0, name)
        if name.startswith("Recolour"):
            return (2, name)
        return (1, name)

    entries = []
    for sub in sorted(subs, key=sort_key):
        icon = os.path.join(PACK, "subpacks", sub["folder_name"], "pack_icon.png")
        if os.path.exists(icon):
            entries.append((sub["name"], card(icon)))
    if not entries:
        raise SystemExit("no subpack icons found")

    font = load_font(18)
    small = load_font(13)

    sheet_w = PAD + len(entries) * (CARD_W + PAD)
    sheet_h = PAD + CARD_W + LABEL_H + PAD + 26
    sheet = Image.new("RGBA", (sheet_w, sheet_h), BG)
    draw = ImageDraw.Draw(sheet)

    draw.text(
        (PAD, 8),
        "Custom Elytra - new models + recolours  (%d subpacks)" % len(entries),
        font=small,
        fill=(150, 156, 170, 255),
    )

    x = PAD
    top = PAD + 20
    for name, img in entries:
        draw.rectangle([x, top, x + CARD_W, top + CARD_W], fill=CARD_BG)
        sheet.paste(
            img,
            (x + (CARD_W - img.width) // 2, top + (CARD_W - img.height) // 2),
            img,
        )
        tw = draw.textlength(name, font=font)
        draw.text(
            (x + (CARD_W - tw) / 2, top + CARD_W + 8),
            name,
            font=font,
            fill=(238, 238, 244, 255),
        )
        x += CARD_W + PAD

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sheet.save(OUT, optimize=True)
    print(
        "wrote %s (%dx%d, %d skins)"
        % (os.path.relpath(OUT, ROOT), sheet_w, sheet_h, len(entries))
    )


if __name__ == "__main__":
    main()
