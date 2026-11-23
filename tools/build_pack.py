#!/usr/bin/env python3
"""
One command build for the Custom Elytra resource pack.

  1. generates the from-scratch designs (tools/build_designs.py)
  2. generates the recoloured samurai variants (tools/generate_variants.py)
  3. renders a pack icon for every subpack (tools/build_icons.py)
  4. writes the subpack list into manifest.json
  5. writes docs/skins-preview.png and dist/Skin-Custom-Elytra.mcpack

Subpack order matters: Bedrock picks the subpack with the highest available
memory tier as the default, so "Samurai (Original)" is always written last with
the highest tier and the pack stays visually unchanged until the player picks a
new skin.

Usage:
    python3 tools/build_pack.py
    python3 tools/build_pack.py --skip-render   # faster, re-uses icons
"""

import argparse
import json
import os
import zipfile

import packpaths  # noqa: F401  (adds tools/ to sys.path)
from packpaths import DIST, DOCS, PACK, SUBPACKS

import build_designs
import generate_variants


# --------------------------------------------------------------------------
# subpack catalogue
# --------------------------------------------------------------------------

# folder -> (display name, palette for the generated icon, accent colour)
DESIGN_ICONS = {
    "phoenix": ("Phoenix", (46, 12, 14), "#ff8a3c"),
    "phoenix_dark": ("Dark Phoenix", (26, 6, 9), "#ff5a2a"),
    "seraph": ("Seraph", (14, 26, 36), "#a8e4ff"),
    "seraph_gold": ("Golden Seraph", (38, 28, 12), "#ffe7a0"),
    "dragon": ("Void Dragon", (20, 10, 32), "#c07cf5"),
    "dragon_ember": ("Ember Dragon", (28, 11, 6), "#ff9a52"),
}

RECOLOUR_ICONS = {
    "fantasy_frost": ("Recolour - Frost", (14, 30, 42), "#a8e4ff"),
    "fantasy_inferno": ("Recolour - Inferno", (40, 16, 8), "#ff9a45"),
    "fantasy_void": ("Recolour - Void", (26, 12, 38), "#c88cff"),
    "fantasy_verdant": ("Recolour - Verdant", (14, 32, 18), "#8ce8a0"),
    "fantasy_astral": ("Recolour - Astral", (22, 14, 40), "#e0a0f0"),
    "fantasy_celestial": ("Recolour - Celestial", (34, 34, 40), "#ffe9b0"),
}

ORIGINAL = ("original_samurai", "Samurai (Original)")


# --------------------------------------------------------------------------
# build steps
# --------------------------------------------------------------------------


def generate_designs():
    for name, spec in build_designs.DESIGNS.items():
        m = spec["builder"](variant=spec["variant"])
        build_designs.write_subpack(name, m, spec)
        print("design   %-14s %2d bones %3d cubes" % (
            name, len(m.bones), sum(len(b["cubes"]) for b in m.bones)))


def generate_recolours():
    for sub in generate_variants.generate():
        print("recolour %-14s %s" % (sub["folder_name"], sub["name"]))


def generate_icons(skip_render=False):
    if skip_render:
        return 0
    import build_icons

    made = 0
    for folder, (label, bg, accent) in {**DESIGN_ICONS, **RECOLOUR_ICONS}.items():
        path = os.path.join(SUBPACKS, folder)
        if not os.path.isdir(path):
            continue
        build_icons.icon_for_subpack(path, bg, accent)
        made += 1
    return made


def write_manifest():
    manifest_path = os.path.join(PACK, "manifest.json")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    order = list(RECOLOUR_ICONS) + list(DESIGN_ICONS) + [ORIGINAL[0]]
    names = {folder: label for folder, (label, _bg, _ac) in
             {**RECOLOUR_ICONS, **DESIGN_ICONS}.items()}
    names[ORIGINAL[0]] = ORIGINAL[1]

    subpacks = []
    for tier, folder in enumerate(order, start=1):
        if not os.path.isdir(os.path.join(SUBPACKS, folder)):
            continue
        subpacks.append(
            {
                "folder_name": folder,
                "name": names[folder],
                "memory_tier": tier,
            }
        )
    manifest["subpacks"] = subpacks
    manifest["header"]["description"] = (
        "Custom elytra skins: original samurai, recolour themes and three new "
        "models (Phoenix, Seraph, Dragon). Pick one in Pack Settings. By xVoid Axell"
    )
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("manifest  %d subpacks (default: %s)" % (len(subpacks), subpacks[-1]["name"]))
    return subpacks


def write_preview():
    import build_preview

    build_preview.main()


def write_mcpack():
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "Skin-Custom-Elytra.mcpack")
    if os.path.exists(out):
        os.remove(out)
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for base, dirs, files in os.walk(PACK):
            dirs.sort()
            for name in sorted(files):
                full = os.path.join(base, name)
                zf.write(full, os.path.relpath(full, PACK))
                count += 1
    print("mcpack    %s (%d files, %.1f KB)" % (
        os.path.relpath(out, os.path.dirname(DIST)), count,
        os.path.getsize(out) / 1024.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-render", action="store_true",
                    help="do not re-render the subpack icons")
    args = ap.parse_args()

    print("== designs ==")
    generate_designs()
    print("== recolours ==")
    generate_recolours()
    print("== icons ==")
    n = generate_icons(args.skip_render)
    print("%d icons" % n)
    print("== manifest ==")
    write_manifest()
    print("== preview ==")
    write_preview()
    print("== package ==")
    write_mcpack()
    print("\ndone - run python3 tools/validate_pack.py to double check")


if __name__ == "__main__":
    main()
