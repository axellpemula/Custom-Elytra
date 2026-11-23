#!/usr/bin/env python3
"""
Pack the resource pack into a .mcpack file ready to import into Minecraft
Bedrock (Windows / Android / iOS).

Usage:
    python3 tools/build_mcpack.py

Output:
    dist/Skin-Custom-Elytra.mcpack
"""

import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "Custom Elytra")
DIST = os.path.join(ROOT, "dist")
OUT = os.path.join(DIST, "Skin-Custom-Elytra.mcpack")


def main():
    os.makedirs(DIST, exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)

    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        # the pack contents must sit at the archive root, not inside a folder
        for base, dirs, files in os.walk(PACK):
            dirs.sort()
            for name in sorted(files):
                full = os.path.join(base, name)
                rel = os.path.relpath(full, PACK)
                zf.write(full, rel)
                count += 1

    size = os.path.getsize(OUT)
    print("built %s (%d files, %.1f KB)" % (os.path.relpath(OUT, ROOT), count, size / 1024.0))


if __name__ == "__main__":
    main()
