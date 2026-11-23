#!/usr/bin/env python3
"""
Offline renderer for Minecraft Bedrock geometry files.

Used to preview the elytra models without launching the game. It understands
bedrock bone hierarchies (pivot/rotation/parent), per-face uv / uv_size,
"inflate", and can apply a pose (a dict of bone -> [x, y, z] rotation) so the
same model can be rendered in its gliding or idle animation pose.

Usage:
    python3 tools/render_model.py --geometry "Custom Elytra/models/mobs.json" \
        --texture "Custom Elytra/textures/models/intity/samurai.png" --out /tmp/x.png
"""

import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image

# --------------------------------------------------------------------------
# small 3d helpers
# --------------------------------------------------------------------------


def rot_matrix(deg):
    """Bedrock rotation order: z, then y, then x (all in degrees)."""
    if isinstance(deg, (int, float)):
        deg = [deg, deg, deg]
    rx, ry, rz = [math.radians(a) for a in deg]

    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)

    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float64)
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float64)
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=np.float64)
    return mx @ my @ mz


def bone_matrix(bone, overrides=None):
    pivot = np.array(bone.get("pivot", [0, 0, 0]), dtype=np.float64)
    rotation = bone.get("rotation", [0, 0, 0])
    if overrides and bone["name"] in overrides:
        base = list(rotation) if not isinstance(rotation, (int, float)) else [rotation] * 3
        rotation = [base[i] + overrides[bone["name"]][i] for i in range(3)]
    r = rot_matrix(rotation) if any(rotation) else np.eye(3)
    return pivot, r


def collect_bones(geometries, bone_overrides=None):
    """Flatten the bone list, resolving parent chains into world matrices."""
    out = []

    def walk(bone, parent_local, parent_world):
        local_pivot, local_rot = bone_matrix(bone, bone_overrides)
        # local transform: T(pivot) * R * T(-pivot)
        def apply(pts):
            p = np.asarray(pts, dtype=np.float64)
            p = (p - local_pivot) @ local_rot.T + local_pivot
            if parent_local is not None:
                p = parent_local(p)
            return p

        if parent_local is None:
            def world(pts):
                return apply(pts)
        else:
            def world(pts, apply=apply, parent_world=parent_world):
                # cube coords are absolute; rotate around this bone then parent
                p = np.asarray(pts, dtype=np.float64)
                p = (p - local_pivot) @ local_rot.T + local_pivot
                return parent_world(p)

        out.append((bone, world))
        for child in bone.get("bones", []):
            walk(child, None, world)

    for geo in geometries:
        for bone in geo.get("bones", []):
            walk(bone, None, None)
    return out


# --------------------------------------------------------------------------
# geometry -> quads
# --------------------------------------------------------------------------

FACES = [
    # name, 4 corners (unit cube), outward normal
    ("north", [(1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)], (0, 0, -1)),
    ("south", [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)], (0, 0, 1)),
    ("west", [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)], (-1, 0, 0)),
    ("east", [(1, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1)], (1, 0, 0)),
    ("up", [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)], (0, 1, 0)),
    ("down", [(1, 0, 0), (0, 0, 0), (0, 0, 1), (1, 0, 1)], (0, -1, 0)),
]

FACE_LIGHT = {
    "north": 0.74,
    "south": 0.86,
    "west": 0.60,
    "east": 0.80,
    "up": 1.0,
    "down": 0.52,
}


def build_quads(geometry, bone_overrides=None):
    bones = collect_bones([geometry], bone_overrides)
    quads = []
    for bone, world in bones:
        for cube in bone.get("cubes", []):
            origin = np.array(cube["origin"], dtype=np.float64)
            size = np.array(cube["size"], dtype=np.float64)
            inflate = float(cube.get("inflate", 0.0))
            uv = cube.get("uv")
            if isinstance(uv, (list, tuple)):
                base_uv = uv
                uv = {}
                x, y = base_uv
                w, h, d = size
                # classic box layout
                uv = {
                    "east": {"uv": [x, y + d], "uv_size": [d, h]},
                    "north": {"uv": [x + d, y + d], "uv_size": [w, h]},
                    "west": {"uv": [x + d + w, y + d], "uv_size": [d, h]},
                    "south": {"uv": [x + d + w + d, y + d], "uv_size": [w, h]},
                    "up": {"uv": [x + d, y], "uv_size": [w, d]},
                    "down": {"uv": [x + d + w, y], "uv_size": [w, d]},
                }
            rotation = cube.get("rotation", [0, 0, 0])
            pivot = np.array(cube.get("pivot", [0, 0, 0]), dtype=np.float64)
            if any(rotation):
                r = rot_matrix(rotation)
            else:
                r = None

            local_pts = {}
            for ix in (0, 1):
                for iy in (0, 1):
                    for iz in (0, 1):
                        p = origin + np.array([ix, iy, iz]) * size
                        p = p + (np.array([ix, iy, iz]) * 2 - 1) * inflate
                        if r is not None:
                            p = (p - pivot) @ r.T + pivot
                        local_pts[(ix, iy, iz)] = p

            for fname, corners, normal in FACES:
                geo_face = uv.get(fname)
                if geo_face is None:
                    continue
                u0, v0 = geo_face["uv"]
                du, dv = geo_face["uv_size"]
                # uv corners follow the face corner order
                uvs = [
                    (u0, v0),
                    (u0 + du, v0),
                    (u0 + du, v0 + dv),
                    (u0, v0 + dv),
                ]
                pts = np.array([local_pts[c] for c in corners])
                pts = world(pts)
                quads.append(
                    {
                        "pts": pts,
                        "uvs": np.array(uvs, dtype=np.float64),
                        "normal": np.array(normal, dtype=np.float64),
                        "face": fname,
                        "bone": bone.get("name", "?"),
                    }
                )
    return quads


# --------------------------------------------------------------------------
# camera + rasterizer
# --------------------------------------------------------------------------


def make_camera(yaw, pitch):
    y = math.radians(yaw)
    p = math.radians(pitch)
    # camera basis (looking from +z towards -z after rotation)
    cy, sy = math.cos(y), math.sin(y)
    cp, sp = math.cos(p), math.sin(p)
    right = np.array([cy, 0, -sy])
    up = np.array([sy * sp, cp, cy * sp])
    fwd = np.array([sy * cp, -sp, cy * cp])
    return right, up, fwd


def render(
    geometry,
    texture_path,
    out_path,
    size=900,
    yaw=32.0,
    pitch=12.0,
    pose=None,
    bg=(248, 249, 252, 255),
    outline=True,
    zoom=1.0,
    center=None,
    supersample=2,
):
    tex = Image.open(texture_path).convert("RGBA")
    tw, th = tex.size
    tex_np = np.asarray(tex)
    uv_w = geometry["description"].get("texture_width", 64)
    uv_h = geometry["description"].get("texture_height", 64)

    quads = build_quads(geometry, pose)
    if not quads:
        raise SystemExit("no quads")

    all_pts = np.concatenate([q["pts"] for q in quads], axis=0)
    right, up, fwd = make_camera(yaw, pitch)

    if center is None:
        center = np.array([0.0, 24.0, 0.0])
    center = np.asarray(center, dtype=np.float64)

    rel = all_pts - center
    cam = np.stack([rel @ right, rel @ up, rel @ fwd], axis=1)

    ss = supersample
    W = H = size * ss
    margin = 0.92
    span = max(cam[:, 0].max() - cam[:, 0].min(), cam[:, 1].max() - cam[:, 1].min())
    scale = (min(W, H) * margin) / max(span, 1e-6) * zoom
    cx = (cam[:, 0].max() + cam[:, 0].min()) / 2.0
    cy = (cam[:, 1].max() + cam[:, 1].min()) / 2.0

    img = np.zeros((H, W, 4), dtype=np.float32)
    img[..., 0] = bg[0]
    img[..., 1] = bg[1]
    img[..., 2] = bg[2]
    img[..., 3] = bg[3]
    depth = np.full((H, W), -1e9, dtype=np.float64)

    # to screen: x right, y down
    def project(p):
        return np.array(
            [
                W * 0.5 + (p[:, 0] - cx) * scale,
                H * 0.5 - (p[:, 1] - cy) * scale,
                p[:, 2],
            ]
        ).T

    order = sorted(range(len(quads)), key=lambda i: np.mean(cam[np.isin(all_pts, quads[i]["pts"])][:, 2]) if False else 0)
    # sort by average camera depth of the quad's points
    quad_depth = []
    for i, q in enumerate(quads):
        rel_q = q["pts"] - center
        quad_depth.append(np.mean(rel_q @ fwd))
    order = np.argsort(quad_depth)

    for qi in order:
        q = quads[qi]
        pts3 = project(np.stack([(q["pts"] - center) @ right, (q["pts"] - center) @ up, (q["pts"] - center) @ fwd], axis=1))
        xy = pts3[:, :2]
        z = pts3[:, 2]
        uv = q["uvs"].copy()

        # texture sampling coordinates (uv space -> pixels)
        uvpix = np.stack([uv[:, 0] / uv_w * tw, uv[:, 1] / uv_h * th], axis=1)

        x0, y0 = np.floor(xy.min(axis=0)).astype(int)
        x1, y1 = np.ceil(xy.max(axis=0)).astype(int)
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(W - 1, x1)
        y1 = min(H - 1, y1)
        if x1 < x0 or y1 < y0:
            continue

        # triangulate quad (0,1,2) + (0,2,3)
        light = FACE_LIGHT.get(q["face"], 0.8)
        rgb = tex_np[..., :3].astype(np.float32)
        alpha = tex_np[..., 3].astype(np.float32) / 255.0

        for tri in ((0, 1, 2), (0, 2, 3)):
            p0, p1, p2 = xy[tri[0]], xy[tri[1]], xy[tri[2]]
            denom = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])
            if abs(denom) < 1e-9:
                continue
            ys, xs = np.mgrid[y0 : y1 + 1, x0 : x1 + 1]
            px = xs + 0.5
            py = ys + 0.5
            w0 = ((p1[0] - px) * (p2[1] - py) - (p2[0] - px) * (p1[1] - py)) / denom
            w1 = ((p2[0] - px) * (p0[1] - py) - (p0[0] - px) * (p2[1] - py)) / denom
            w2 = 1.0 - w0 - w1
            inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not inside.any():
                continue

            zz = w0 * z[tri[0]] + w1 * z[tri[1]] + w2 * z[tri[2]]
            uu = w0 * uvpix[tri[0], 0] + w1 * uvpix[tri[1], 0] + w2 * uvpix[tri[2], 0]
            vv = w0 * uvpix[tri[0], 1] + w1 * uvpix[tri[1], 1] + w2 * uvpix[tri[2], 1]

            tx = np.clip(uu.astype(int), 0, tw - 1)
            ty = np.clip(vv.astype(int), 0, th - 1)
            col = rgb[ty, tx] * light  # 0..255
            a = alpha[ty, tx]

            sub_depth = depth[y0 : y1 + 1, x0 : x1 + 1]
            sub_img = img[y0 : y1 + 1, x0 : x1 + 1]
            take = inside & (a > 0.5) & (zz > sub_depth)
            if not take.any():
                continue
            sub_depth[take] = zz[take]
            sub_img[take, :3] = col[take]
            sub_img[take, 3] = 255

    # downsample supersample buffer
    if ss > 1:
        img = img.reshape(size, ss, size, ss, 4).mean(axis=(1, 3))

    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGBA")

    if outline:
        arr = np.asarray(out).copy()
        op = arr[..., 3] > 0
        edge = np.zeros_like(op)
        edge[1:, :] |= op[1:, :] & ~op[:-1, :]
        edge[:-1, :] |= op[:-1, :] & ~op[1:, :]
        edge[:, 1:] |= op[:, 1:] & ~op[:, :-1]
        edge[:, :-1] |= op[:, :-1] & ~op[:, 1:]
        arr[edge] = [26, 22, 30, 255]
        out = Image.fromarray(arr, "RGBA")

    out.save(out_path)
    return out_path


def load_geometry(path):
    with open(path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if "minecraft:geometry" in data:
        return data["minecraft:geometry"][0]
    if data.get("format_version") and "bones" in data:
        return data
    raise SystemExit("unsupported geometry file: %s" % path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geometry", default=os.path.join("Custom Elytra", "models", "mobs.json"))
    ap.add_argument("--texture", default=os.path.join("Custom Elytra", "textures", "models", "intity", "samurai.png"))
    ap.add_argument("--out", default="/tmp/render.png")
    ap.add_argument("--size", type=int, default=900)
    ap.add_argument("--yaw", type=float, default=32.0)
    ap.add_argument("--pitch", type=float, default=12.0)
    ap.add_argument("--zoom", type=float, default=1.0)
    ap.add_argument("--pose", default=None, help="json file with bone -> [x,y,z]")
    ap.add_argument("--no-outline", action="store_true")
    ap.add_argument("--transparent", action="store_true")
    args = ap.parse_args()

    pose = None
    if args.pose:
        with open(args.pose, encoding="utf-8") as fh:
            pose = json.load(fh)

    geo = load_geometry(args.geometry)
    render(
        geo,
        args.texture,
        args.out,
        size=args.size,
        yaw=args.yaw,
        pitch=args.pitch,
        pose=pose,
        zoom=args.zoom,
        outline=not args.no_outline,
        bg=(255, 255, 255, 0) if args.transparent else (248, 249, 252, 255),
    )
    print("wrote", args.out)


if __name__ == "__main__":
    main()
