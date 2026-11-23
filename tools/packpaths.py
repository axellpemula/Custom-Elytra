#!/usr/bin/env python3
"""Shared paths for the build scripts."""

import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
PACK = os.path.join(ROOT, "Custom Elytra")
SUBPACKS = os.path.join(PACK, "subpacks")
DOCS = os.path.join(ROOT, "docs")
DIST = os.path.join(ROOT, "dist")

if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
