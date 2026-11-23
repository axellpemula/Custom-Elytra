#!/usr/bin/env python3
"""
Sanity checks for the resource pack before shipping it.

Verifies that every JSON file parses, that the manifest lists subpacks whose
folders actually exist, that each subpack ships the texture the attachable
points at, and that the texture dimensions match the geometry's texture size.

Usage:
    python3 tools/validate_pack.py
"""

import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "Custom Elytra")

errors = []
warnings = []


def load(rel):
    path = os.path.join(PACK, rel)
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001 - report and keep checking
        errors.append("%s: %s" % (rel, exc))
        return None


def check_json_files():
    for base, _dirs, files in os.walk(PACK):
        if os.path.basename(base) == "subpacks":
            continue
        for name in files:
            if name.endswith(".json"):
                rel = os.path.relpath(os.path.join(base, name), PACK)
                load(rel)


def check_manifest():
    manifest = load("manifest.json")
    if manifest is None:
        return []
    for key in ("format_version", "header", "modules"):
        if key not in manifest:
            errors.append("manifest.json: missing %r" % key)
    header = manifest.get("header", {})
    for key in ("name", "description", "uuid", "version", "min_engine_version"):
        if key not in header:
            errors.append("manifest.json: header missing %r" % key)
    if not manifest.get("modules"):
        errors.append("manifest.json: no modules")

    engine = header.get("min_engine_version")
    if isinstance(engine, list) and len(engine) == 3:
        # a min_engine_version newer than the player's game hides the pack
        if tuple(engine) > (1, 21, 90):
            warnings.append(
                "manifest.json: min_engine_version %s may hide the pack on older game versions"
                % ".".join(str(v) for v in engine)
            )
    elif engine is not None:
        errors.append("manifest.json: min_engine_version must be [major, minor, patch]")

    subpacks = manifest.get("subpacks", [])
    if not subpacks:
        errors.append("manifest.json: no subpacks defined")
    seen = set()
    for sub in subpacks:
        folder = sub.get("folder_name")
        if not folder:
            errors.append("manifest.json: subpack without folder_name")
            continue
        if folder in seen:
            errors.append("manifest.json: duplicate subpack %r" % folder)
        seen.add(folder)
        if not os.path.isdir(os.path.join(PACK, "subpacks", folder)):
            errors.append("manifest.json: missing subpack folder %r" % folder)
        if "name" not in sub:
            warnings.append("manifest.json: subpack %r has no display name" % folder)
        if not isinstance(sub.get("memory_tier"), int):
            warnings.append("manifest.json: subpack %r has no integer memory_tier" % folder)

    tiers = [sub.get("memory_tier") for sub in subpacks if isinstance(sub.get("memory_tier"), int)]
    if tiers:
        # the game defaults to the highest available tier, last one wins on ties
        default = [
            sub for sub in subpacks if sub.get("memory_tier") == max(tiers)
        ][-1]
        print("INFO  default subpack on a full-memory device: %s" % default.get("name", default.get("folder_name")))
        if len(set(tiers)) != len(tiers):
            warnings.append(
                "manifest.json: duplicate memory_tier - the default subpack becomes ambiguous"
            )
    return subpacks


def check_attachable():
    attachable = load("attachables/elytra.json")
    if attachable is None:
        return None
    desc = attachable.get("minecraft:attachable", {}).get("description", {})
    tex = desc.get("textures", {}).get("default")
    geo = desc.get("geometry", {}).get("default")
    if not tex:
        errors.append("attachables/elytra.json: no default texture")
        return None
    if not geo:
        errors.append("attachables/elytra.json: no default geometry")
    if not os.path.exists(os.path.join(PACK, tex + ".png")):
        errors.append("attachable texture not found: %s.png" % tex)
    return tex


def check_geometry(tex_rel):
    geo_file = load("models/mobs.json")
    if geo_file is None:
        return None
    geos = geo_file.get("minecraft:geometry", [])
    if not geos:
        errors.append("models/mobs.json: no geometry")
        return None
    desc = geos[0].get("description", {})
    tw, th = desc.get("texture_width"), desc.get("texture_height")
    if not tw or not th:
        errors.append("models/mobs.json: geometry has no texture_width/height")
        return None
    if tex_rel:
        path = os.path.join(PACK, tex_rel + ".png")
        if os.path.exists(path):
            img = Image.open(path)
            # bedrock scales a WxH uv space onto the actual png size
            if img.width % tw or img.height % th:
                warnings.append(
                    "texture %s.png is %dx%d, not a multiple of the %dx%d uv space"
                    % (tex_rel, img.width, img.height, tw, th)
                )
    return tw, th


def check_subpack_models(subpacks):
    """Design subpacks (the ones that ship models/) must be self consistent."""
    for sub in subpacks:
        folder = sub.get("folder_name")
        if not folder:
            continue
        base = os.path.join(PACK, "subpacks", folder)
        att = os.path.join(base, "attachables", "elytra.json")
        if not os.path.exists(att):
            continue  # recolour subpacks only override the texture
        try:
            with open(att, encoding="utf-8-sig") as fh:
                desc = json.load(fh)["minecraft:attachable"]["description"]
        except Exception as exc:  # noqa: BLE001
            errors.append("subpack %r: bad attachable (%s)" % (folder, exc))
            continue

        geo_id = desc.get("geometry", {}).get("default")
        geo_path = os.path.join(base, "models", "mobs.json")
        if not os.path.exists(geo_path):
            errors.append("subpack %r: attachable but no models/mobs.json" % folder)
            continue
        try:
            with open(geo_path, encoding="utf-8-sig") as fh:
                geos = json.load(fh).get("minecraft:geometry", [])
        except Exception as exc:  # noqa: BLE001
            errors.append("subpack %r: bad models/mobs.json (%s)" % (folder, exc))
            continue
        ids = [g.get("description", {}).get("identifier") for g in geos]
        if geo_id not in ids:
            errors.append("subpack %r: geometry %r not found in models/mobs.json" % (folder, geo_id))

        tex = desc.get("textures", {}).get("default", "")
        if tex and not os.path.exists(os.path.join(base, tex + ".png")):
            errors.append("subpack %r: texture %s.png missing" % (folder, tex))
        ctrl = desc.get("animations", {}).get("default_controller")
        ctrl_files = []
        for root, _dirs, files in os.walk(base):
            ctrl_files += [os.path.join(root, f) for f in files if f.endswith(".json")]
        found_ctrl = False
        for cf in ctrl_files:
            try:
                with open(cf, encoding="utf-8-sig") as fh:
                    if "animation_controllers" in json.load(fh):
                        found_ctrl = True
                        break
            except Exception:  # noqa: BLE001
                continue
        if ctrl and not found_ctrl:
            errors.append("subpack %r: animation controller %r has no file" % (folder, ctrl))


def check_subpack_textures(subpacks, tex_rel):
    if not tex_rel:
        return
    for sub in subpacks:
        folder = sub.get("folder_name")
        if not folder:
            continue
        path = os.path.join(PACK, "subpacks", folder, tex_rel + ".png")
        if not os.path.exists(path):
            errors.append("subpack %r missing %s.png" % (folder, tex_rel))
        icon = os.path.join(PACK, "subpacks", folder, "pack_icon.png")
        if not os.path.exists(icon):
            warnings.append("subpack %r has no pack_icon.png" % folder)


def main():
    check_json_files()
    subpacks = check_manifest()
    tex_rel = check_attachable()
    check_geometry(tex_rel)
    check_subpack_textures(subpacks, tex_rel)
    check_subpack_models(subpacks)

    for w in warnings:
        print("WARN  " + w)
    for e in errors:
        print("ERROR " + e)
    if errors:
        print("\n%d error(s), %d warning(s)" % (len(errors), len(warnings)))
        return 1
    print("OK - %d subpack(s), no errors, %d warning(s)" % (len(subpacks), len(warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
