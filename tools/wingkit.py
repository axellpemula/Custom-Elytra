#!/usr/bin/env python3
"""
Small toolkit to author Minecraft Bedrock geometry + textures from code.

Everything the new elytra designs need lives here:

* ``Atlas``  - shelf-packs box face rectangles into a texture atlas and paints
  them with procedural styles (gradients, barbs, facets, spots...).
* ``Model``  - collects bones/cubes and writes a valid
  ``minecraft:geometry`` json plus the matching png.
* helpers to build feathered / bladed / lobed wings and mirror them.

The atlas is 1 uv unit = 1 texture pixel, i.e. ``texture_width`` equals the png
width, and one model unit gets ``PX`` pixels of texture.

    m = Model("geometry.elytra.phoenix")
    wing = m.bone("wing_l", pivot=[4.5, 23.5, 2.0])
    m.feather(wing, pivot=[4.5, 23.5, 2.0], length=9, width=2.4, ...)
    m.save_geometry(path, ...); m.save_texture(png_path)
"""

import json
import math

import numpy as np
from PIL import Image

PX = 4  # texture pixels per model unit


# --------------------------------------------------------------------------
# colour helpers
# --------------------------------------------------------------------------


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def ramp(stops, n):
    """Sample a colour ramp of ``len(stops)`` colours into ``n`` rgb rows."""
    stops = [hex_rgb(s) if isinstance(s, str) else tuple(s) for s in stops]
    if n <= 1:
        return np.array([stops[0]], dtype=np.float32)
    xs = np.linspace(0, len(stops) - 1, n)
    out = np.zeros((n, 3), dtype=np.float32)
    for i, x in enumerate(xs):
        a = int(math.floor(x))
        b = min(a + 1, len(stops) - 1)
        t = x - a
        out[i] = np.array(stops[a]) * (1 - t) + np.array(stops[b]) * t
    return out


def shade(rgb, factor):
    return tuple(int(max(0, min(255, c * factor))) for c in rgb)


# --------------------------------------------------------------------------
# atlas
# --------------------------------------------------------------------------

BOX_PAD = 1  # px gap between packed rectangles


class Atlas:
    """Very small shelf packer for rectangular box-face layouts."""

    def __init__(self, size=256, px_per_unit=PX):
        self.size = size
        self.px = px_per_unit
        self.img = np.zeros((size, size, 4), dtype=np.uint8)
        self._x = BOX_PAD
        self._y = BOX_PAD
        self._row_h = 0

    def alloc(self, w_px, h_px):
        """Reserve an integer block of pixels and return its top-left corner."""
        w_px = max(1, int(round(w_px)))
        h_px = max(1, int(round(h_px)))
        if self._x + w_px + BOX_PAD > self.size:
            self._x = BOX_PAD
            self._y += self._row_h + BOX_PAD
            self._row_h = 0
        if self._y + h_px + BOX_PAD > self.size:
            raise RuntimeError("texture atlas is full - increase Atlas(size=...)")
        pos = (self._x, self._y)
        self._x += w_px + BOX_PAD
        self._row_h = max(self._row_h, h_px)
        return pos, w_px, h_px

    def put(self, pos, w, h, arr):
        x, y = pos
        self.img[y : y + h, x : x + w, :3] = np.clip(arr, 0, 255).astype(np.uint8)
        self.img[y : y + h, x : x + w, 3] = 255

    def save(self, path):
        Image.fromarray(self.img, "RGBA").save(path, optimize=True)


# --------------------------------------------------------------------------
# face painters
# --------------------------------------------------------------------------


def _outline(arr, colour, width=1):
    if width <= 0:
        return arr
    arr[:width, :, :] = colour
    arr[-width:, :, :] = colour
    arr[:, :width, :] = colour
    arr[:, -width:, :] = colour
    return arr


def _edge_light(arr, colour, axis, at_start, width=1):
    if axis == "u":
        if at_start:
            arr[:, :width, :] = colour
        else:
            arr[:, -width:, :] = colour
    else:
        if at_start:
            arr[:width, :, :] = colour
        else:
            arr[-width:, :, :] = colour
    return arr


def paint_face(w, h, palette, style="grad", axis="auto", seed=0):
    """Procedurally paint one box face and return an (h, w, 3) float array.

    ``axis`` is the direction the gradient runs in: "u" (along width) or "v"
    (along height).  Feather-like parts are long in u, so the default picks u
    whenever that is the longer dimension.
    """
    w = max(1, int(w))
    h = max(1, int(h))
    if axis == "auto":
        axis = "u" if w >= h else "v"

    n = w if axis == "u" else h
    ramp_cols = ramp(palette["stops"], n)

    if style == "facet":
        # hard crystal bands instead of a smooth ramp
        bands = max(3, min(n, 5))
        ramp_cols = ramp(palette["stops"], bands)
        idx = (np.arange(n) * bands // n).clip(0, bands - 1)
        ramp_cols = ramp_cols[idx]
    else:
        idx = np.arange(n)

    if axis == "u":
        arr = np.repeat(ramp_cols[None, :, :], h, axis=0)   # (h, w, 3)
    else:
        arr = np.repeat(ramp_cols[:, None, :], w, axis=1)   # (h, w, 3)

    arr = arr.astype(np.float32)
    rng = np.random.default_rng(seed)

    if style == "barb":
        # feather barbs: thin darker lines across the long axis
        step = max(3, n // 7)
        for i in range(step, n, step):
            if axis == "u":
                arr[:, i : i + 1, :] *= 0.80
            else:
                arr[i : i + 1, :, :] *= 0.80
    elif style == "leaf":
        veins = max(2, (h if axis == "u" else w) // 4)
        for i in range(1, veins):
            pos = int(i * (h if axis == "u" else w) / veins)
            if axis == "u":
                arr[max(0, pos - 1) : pos + 1, :, :] *= 0.88
            else:
                arr[:, max(0, pos - 1) : pos + 1, :] *= 0.88
    elif style == "iris":
        # butterfly membrane: bright core fading to a dark iridescent edge
        hh, ww = arr.shape[:2]
        yy, xx = np.mgrid[0:hh, 0:ww]
        u = xx / max(1, ww - 1)
        v = yy / max(1, hh - 1)
        # radial-ish glow around 60% span
        glow = np.exp(-(((u - 0.62) ** 2) / 0.10 + ((v - 0.5) ** 2) / 0.22))
        arr += glow[..., None] * 26.0
        # fine veins fanning out from the root
        veins = np.abs(np.sin(np.arctan2(v - 0.5, u + 0.18) * 7.0)) < 0.10
        arr[veins] *= 0.78
        arr = np.clip(arr, 0, 255)
    elif style == "rivet":
        # metal plate with rivets along the long edges
        hh, ww = arr.shape[:2]
        col = np.array(hex_rgb(palette.get("rivet", "#f0d38a")), dtype=np.float32)
        for x in range(2, ww - 1, max(3, ww // 5)):
            for y in (1, hh - 2):
                if 0 <= y < hh:
                    arr[y, x] = col
    elif style == "crystal":
        # diagonal facet lines so shards read as cut gems, not stripes
        hh, ww = arr.shape[:2]
        yy, xx = np.mgrid[0:hh, 0:ww]
        arr[(xx + yy) % 7 == 0] *= 0.84
        arr[(xx - yy) % 11 == 0] *= 1.12
        arr = np.clip(arr, 0, 255)
    elif style == "spot":
        for _ in range(max(1, (w * h) // 70)):
            cx = int(rng.integers(1, max(2, w - 1)))
            cy = int(rng.integers(1, max(2, h - 1)))
            col = np.array(hex_rgb(palette.get("spot", "#ffffff")), dtype=np.float32)
            arr[cy : cy + 2, cx : cx + 2, :] = col

    if palette.get("rim"):
        _edge_light(arr, np.array(hex_rgb(palette["rim"]), float), axis,
                    not palette.get("rim_end", True), palette.get("rim_width", 1))
    if palette.get("outline", True):
        _outline(arr, np.array(hex_rgb(palette.get("outline_color", "#1b1720")), float),
                 palette.get("outline_width", 1))
    return arr


# --------------------------------------------------------------------------
# model builder
# --------------------------------------------------------------------------

FACES = ("north", "south", "east", "west", "up", "down")


class Model:
    def __init__(self, identifier, atlas_size=256, texture_width=256, texture_height=256,
                 visible_bounds=(8, 6, 0, 1.75, 0)):
        self.identifier = identifier
        self.atlas = Atlas(atlas_size)
        self.texture_width = texture_width
        self.texture_height = texture_height
        self.bones = []
        self._by_name = {}
        self.vb = visible_bounds

    # -- structure ---------------------------------------------------------
    def bone(self, name, pivot=(0, 24, 0), parent=None, rotation=None):
        if name in self._by_name:
            return self._by_name[name]
        bone = {"name": name, "pivot": list(pivot), "cubes": []}
        if parent is not None:
            bone["parent"] = parent
        if rotation is not None:
            bone["rotation"] = list(rotation)
        self.bones.append(bone)
        self._by_name[name] = bone
        return bone

    # -- geometry ----------------------------------------------------------
    def box(self, bone, origin, size, palette, rotation=None, pivot=None,
            style="grad", mirror=False, inflate=None, faces=None, compact=False):
        """Add a cube. ``bone`` may be a name or a bone dict.

        The atlas block is reserved from the *rounded* face sizes, so every face
        rectangle always fits inside it (a mismatch used to leave faces
        unpainted, which rendered as invisible geometry).
        """
        if isinstance(bone, str):
            bone = self._by_name[bone]
        w, h, d = size
        pu = self.atlas.px

        ww = max(1, int(round(w * pu)))
        hh = max(1, int(round(h * pu)))
        dd = max(1, int(round(d * pu)))

        if compact:
            block_w, block_h = ww + dd, max(hh, dd)
        else:
            block_w, block_h = 2 * (dd + ww), dd + hh

        pos, pw, ph = self.atlas.alloc(block_w, block_h)
        assert pw >= block_w and ph >= block_h, (pw, ph, block_w, block_h)

        if compact:
            rects = {
                "north": (pos[0], pos[1], ww, hh),
                "south": (pos[0], pos[1], ww, hh),
                "up": (pos[0] + ww, pos[1], dd, dd),
                "down": (pos[0] + ww, pos[1], dd, dd),
                "east": (pos[0] + ww, pos[1], dd, hh),
                "west": (pos[0] + ww, pos[1], dd, hh),
            }
        else:
            rects = {
                "up": (pos[0] + dd, pos[1], ww, dd),
                "down": (pos[0] + dd + ww, pos[1], ww, dd),
                "east": (pos[0], pos[1] + dd, dd, hh),
                "north": (pos[0] + dd, pos[1] + dd, ww, hh),
                "west": (pos[0] + dd + ww, pos[1] + dd, dd, hh),
                "south": (pos[0] + dd + ww + dd, pos[1] + dd, ww, hh),
            }

        for name, (rx, ry, rw, rh) in rects.items():
            if faces is not None and name not in faces:
                continue
            style_name = style
            if isinstance(style, dict):
                style_name = style.get(name, style.get("default", "grad"))
            arr = paint_face(rw, rh, palette, style=style_name, seed=hash((name, rx, ry)) % 1000)
            self.atlas.put((rx, ry), rw, rh, arr)

        uv = {}
        for name, (rx, ry, rw, rh) in rects.items():
            if faces is not None and name not in faces:
                continue
            uv[name] = {"uv": [rx, ry], "uv_size": [rw, rh]}
        cube = {
            "origin": list(origin),
            "size": list(size),
            "uv": uv,
        }
        if rotation is not None and any(rotation):
            cube["rotation"] = list(rotation)
        if pivot is not None:
            cube["pivot"] = list(pivot)
        if inflate is not None:
            cube["inflate"] = inflate
        if mirror:
            cube["mirror"] = True
        bone["cubes"].append(cube)
        return cube

    # -- composite parts ---------------------------------------------------
    def feather(self, bone, pivot, length, width, thickness, palette,
                sweep=0.0, droop=0.0, twist=0.0, segments=3, taper=0.5,
                dir=1, style="barb", lift=0.0, back=0.0, overlap=0.06,
                faces=None):
        """A tapered feather lying along the bone's x axis.

        ``sweep``  degrees swept towards the back of the player (+z)
        ``droop``  degrees tilted down
        ``twist``  degrees rolled around the feather's own long axis
        ``dir``    +1 grows towards +x, -1 mirrors it towards -x
        ``lift``   y offset, ``back`` z offset (both in model units)
        """
        sx, sy, sz = pivot
        weights = [(1 - i / (segments + 1.0)) for i in range(segments)]
        total = sum(weights)
        done = 0.0
        for i, wgt in enumerate(weights):
            seg = length * wgt / total
            w = width * (1 - (1 - taper) * (i / max(1, segments - 1)))
            if dir > 0:
                ox = sx + done
                rot = [twist, -sweep, -droop]
            else:
                ox = sx - done - seg
                rot = [twist, sweep, droop]
            self.box(
                bone,
                [ox, sy - w / 2 + lift, sz - thickness / 2 + back],
                [seg + overlap, w, thickness],
                palette,
                rotation=rot,
                pivot=[sx, sy, sz],
                style=style,
                faces=faces,
            )
            done += seg

    # -- output ------------------------------------------------------------
    def geometry(self):
        return {
            "format_version": "1.12.0",
            "minecraft:geometry": [
                {
                    "description": {
                        "identifier": self.identifier,
                        "texture_width": self.texture_width,
                        "texture_height": self.texture_height,
                        "visible_bounds_width": self.vb[0],
                        "visible_bounds_height": self.vb[1],
                        "visible_bounds_offset": [self.vb[2], self.vb[3], self.vb[4]],
                    },
                    "bones": self.bones,
                }
            ],
        }

    def save_geometry(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.geometry(), fh, indent=2)
            fh.write("\n")

    def save_texture(self, path):
        self.atlas.save(path)
