#!/usr/bin/env python3
"""
New elytra designs - each one is an original model + texture built from scratch
(not a recolour of the samurai pack).

  phoenix  sweeping firebird wings, layered ember feathers, a molten backplate
           and long tail streamers.
  seraph   crystal angel wings: silver spars carrying faceted ice shards, plus
           trailing ribbons of light.
  dragon   bat/void wings: charred finger bones with a glowing membrane
           stretched between them and dorsal spikes along the spine.

Every design uses the identifier ``geometry.elytra`` and the texture path
``textures/models/intity/samurai.png`` so a design can be dropped into a subpack
as a full replacement of the default look.

Usage:
    python3 tools/build_designs.py                    # all designs
    python3 tools/build_designs.py --only phoenix      # one design
"""

import argparse
import json
import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wingkit import Model  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "Custom Elytra")

# --------------------------------------------------------------------------
# palettes
# --------------------------------------------------------------------------

PALETTES = {
    # -- phoenix -----------------------------------------------------------
    "phoenix_body": {
        "stops": ["#2a0a12", "#5e1220", "#b3202c", "#ff6a1e", "#ffc94a"],
        "outline": "#160409", "outline_width": 0, "rim": "#ffd98a", "rim_end": False,
    },
    "phoenix_feather": {
        "stops": ["#8d1224", "#c8202e", "#ff5c1c", "#ff9f2c", "#ffe27a", "#fff8d8"],
        "outline": "#3a0b13", "outline_width": 0, "rim": "#fff3cc", "rim_end": True,
    },
    "phoenix_tail": {
        "stops": ["#6d1020", "#b81f2c", "#ff6a1e", "#ffc24a", "#fff0bc"],
        "outline": "#2e0a11", "outline_width": 0, "rim": "#ffefa8", "rim_end": True,
    },
    "phoenix_crest": {
        "stops": ["#a8162a", "#e6392b", "#ff8a1e", "#ffc94a", "#fff0bc"],
        "outline": "#3a0c14", "outline_width": 0, "rim": "#fff0bc", "rim_end": True,
    },
    # -- seraph ------------------------------------------------------------
    "seraph_frame": {
        "stops": ["#6b6252", "#a39a8c", "#ded4c2", "#fffaf0"],
        "outline": "#332d24", "outline_width": 0, "rim": "#ffffff", "rim_end": False,
    },
    "seraph_shard": {
        "stops": ["#3d7fa6", "#6fb3d6", "#b6e4f7", "#eafbff"],
        "outline": "#1d516f", "outline_width": 0, "rim": "#ffffff", "rim_end": False,
        "spot": "#f6feff",
    },
    # -- dragon ------------------------------------------------------------
    "dragon_bone": {
        "stops": ["#1a1229", "#33224e", "#4c3a68", "#6a558c"],
        "outline": "#08050f", "outline_width": 0, "rim": "#8a6ab0", "rim_end": False,
    },
    "dragon_membrane": {
        "stops": ["#2a1746", "#46246e", "#6636a0", "#8f4fce", "#c07cf5"],
        "outline": "#0d0718", "outline_width": 0, "rim": "#cf9cff", "rim_end": True,
        "spot": "#8f52d8",
    },
    "dragon_claw": {
        "stops": ["#080610", "#1a1728", "#322e4c", "#504a70"],
        "outline": "#030206", "outline_width": 0, "rim": "#6f6aa8", "rim_end": False,
    },
}

# dark / variants reuse the same shapes with a shifted palette
VARIANTS = {
    "phoenix": {},
    "phoenix_dark": {
        "phoenix_feather": {
            "stops": ["#3a0614", "#7a0d24", "#c21f2a", "#ff6a2a", "#ffb347", "#ffe6a8"],
            "outline": "#170309", "outline_width": 0, "rim": "#ffcb7a", "rim_end": True,
        },
        "phoenix_tail": {
            "stops": ["#2f0710", "#6d0f20", "#b81f26", "#ff7a28", "#ffd070"],
            "outline": "#140308", "outline_width": 0, "rim": "#ffd99a", "rim_end": True,
        },
    },
    "seraph": {},
    "seraph_gold": {
        "seraph_frame": {
            "stops": ["#8a6a1e", "#d3ac3c", "#f7dd84", "#fffbe8"],
            "outline": "#5c4410", "outline_width": 0, "rim": "#ffffff", "rim_end": False,
        },
        "seraph_shard": {
            "stops": ["#b08a2a", "#e8c85c", "#fff2b0", "#fffdf2"],
            "outline": "#5c4410", "outline_width": 0, "rim": "#ffffff", "rim_end": False,
            "spot": "#fffdf2",
        },
    },
    "dragon": {},
    "dragon_ember": {
        "dragon_bone": {
            "stops": ["#160907", "#36150e", "#572311", "#7a3818"],
            "outline": "#0a0403", "outline_width": 0, "rim": "#a8602c", "rim_end": False,
        },
        "dragon_membrane": {
            "stops": ["#2c120c", "#521f0d", "#7d3414", "#b85620", "#f08a36"],
            "outline": "#0d0503", "outline_width": 0, "rim": "#ffab52", "rim_end": True,
            "spot": "#c95a1c",
        },
        "dragon_claw": {
            "stops": ["#0d0705", "#241610", "#3d2a20", "#5c4634"],
            "outline": "#050302", "outline_width": 0, "rim": "#8a6a4a", "rim_end": False,
        },
    },
}


def palette(name, variant):
    """Palette lookup with per-variant overrides."""
    base = PALETTES[name]
    return VARIANTS.get(variant, {}).get(name, base)


# --------------------------------------------------------------------------
# phoenix
# --------------------------------------------------------------------------


def build_phoenix(identifier="geometry.elytra", variant="phoenix", atlas=256):
    m = Model(identifier, atlas_size=atlas, texture_width=atlas, texture_height=atlas,
              visible_bounds=(11, 6, 0, 1.75, 0))
    body_pal = palette("phoenix_body", variant)
    feather_pal = palette("phoenix_feather", variant)
    tail_pal = palette("phoenix_tail", variant)
    crest_pal = palette("phoenix_crest", variant)

    body = m.bone("body", pivot=[0, 24, 0])

    # -- backplate + collar + gem ------------------------------------------
    spine = m.bone("phoenix_spine", pivot=[0, 23, 2.0], parent="body")
    m.box(spine, [-2.1, 23.2, 1.7], [4.2, 5.0, 1.15], body_pal, style="grad")
    m.box(spine, [-2.5, 27.7, 1.55], [5.0, 1.0, 1.55], crest_pal, style="grad")
    m.box(spine, [-1.1, 24.9, 2.72], [2.2, 2.2, 0.40], crest_pal, style="facet")

    # -- wings -------------------------------------------------------------
    # (count, length, width, thickness, sweep0, sweep1, droop0, droop1, y, z)
    layers = [
        (9, 9.6, 1.50, 0.38, 44, -12, 34, 2, 25.6, 1.95),
        (7, 7.2, 1.40, 0.36, 62, 4, 24, -6, 24.9, 2.20),
        (5, 5.0, 1.30, 0.34, 78, 20, 14, -12, 24.2, 2.45),
    ]
    for side, name in ((1, "phoenix_wing_l"), (-1, "phoenix_wing_r")):
        wing = m.bone(name, pivot=[2.1 * side, 25.3, 1.6], parent="body")
        for li, (count, length, width, thick, s0, s1, d0, d1, y, z) in enumerate(layers):
            for i in range(count):
                t = i / max(1, count - 1)
                sweep = s0 + (s1 - s0) * t
                droop = d0 + (d1 - d0) * t
                # the outer primaries of a wing are the longest ones
                grow = 0.74 + 0.26 * math.sin(math.pi * (0.15 + 0.85 * t))
                m.feather(
                    wing, pivot=[1.95 * side, y, z],
                    length=length * grow, width=width, thickness=thick,
                    palette=feather_pal, sweep=sweep, droop=droop,
                    twist=10 * t, segments=3, taper=0.45, dir=side,
                    style="barb", back=0.04 * li, overlap=0.05,
                )
        # shoulder plate that hides the feather roots
        m.box(
            spine,
            [1.55, 24.6, 1.5] if side > 0 else [-2.75, 24.6, 1.5],
            [1.2, 2.2, 1.7], crest_pal, style="facet",
        )

    # -- tail streamers ----------------------------------------------------
    tail = m.bone("phoenix_tail", pivot=[0, 22.6, 2.2], parent="body")
    # centre streamer plus mirrored pairs, so the fan is symmetrical
    m.feather(tail, pivot=[0, 22.6, 2.4], length=8.0, width=1.2, thickness=0.3,
              palette=tail_pal, sweep=0, droop=58, segments=3, taper=0.35,
              dir=1, style="barb", lift=-0.6)
    for i in range(3):
        sweep = 18 + i * 17
        ln = 7.2 - i * 1.1
        droop = 50 + i * 6
        for d in (1, -1):
            m.feather(tail, pivot=[0.18 * d, 22.6, 2.4], length=ln, width=1.15,
                      thickness=0.3, palette=tail_pal, sweep=sweep, droop=droop,
                      segments=3, taper=0.38, dir=d, style="barb", lift=-0.6)
    return m


# --------------------------------------------------------------------------
# seraph
# --------------------------------------------------------------------------


def build_seraph(identifier="geometry.elytra", variant="seraph", atlas=256):
    m = Model(identifier, atlas_size=atlas, texture_width=atlas, texture_height=atlas,
              visible_bounds=(11, 6, 0, 1.75, 0))
    frame_pal = palette("seraph_frame", variant)
    shard_pal = palette("seraph_shard", variant)

    body = m.bone("body", pivot=[0, 24, 0])
    spine = m.bone("seraph_spine", pivot=[0, 23, 2.0], parent="body")
    m.box(spine, [-2.0, 23.4, 1.75], [4.0, 4.8, 1.05], frame_pal, style="grad")
    m.box(spine, [-2.4, 27.6, 1.6], [4.8, 0.9, 1.45], frame_pal, style="grad")
    m.box(spine, [-1.0, 25.0, 2.66], [2.0, 2.0, 0.35], shard_pal, style="facet")

    for side, name in ((1, "seraph_wing_l"), (-1, "seraph_wing_r")):
        wing = m.bone(name, pivot=[2.0 * side, 25.4, 1.7], parent="body")
        root = 1.9

        # --- crystalline membrane filling the gaps between the shards ------
        panels = [(10, 40, 11.0, 9.0), (40, 70, 9.0, 6.4)]
        for pa, pb, ln_a, ln_b in panels:
            webs = 4
            for i in range(webs):
                t = (i + 0.5) / webs
                sweep = pa + (pb - pa) * t
                ln = (ln_a + (ln_b - ln_a) * t) * (0.9 + 0.1 * math.sin(math.pi * t))
                m.feather(
                    wing, pivot=[root * side, 25.0, 1.62],
                    length=ln, width=2.2, thickness=0.18, palette=shard_pal,
                    sweep=sweep, droop=42 + 14 * t, segments=2, taper=0.5,
                    dir=side, style="crystal", overlap=0.14,
                    faces=("north", "south"),
                )

        # --- stacked crystal shards (the actual feathers) ------------------
        layers = [
            # count, length, width, thickness, sweep0, sweep1, droop0, droop1, y, z
            (7, 11.0, 1.80, 0.55, 34, -20, 52, 22, 25.6, 1.90),
            (5, 8.2, 1.65, 0.52, 54, -4, 44, 16, 25.0, 2.15),
            (4, 5.6, 1.50, 0.50, 72, 14, 36, 10, 24.4, 2.40),
        ]
        for li, (count, length, width, thick, s0, s1, d0, d1, y, z) in enumerate(layers):
            for i in range(count):
                t = i / max(1, count - 1)
                sweep = s0 + (s1 - s0) * t
                droop = d0 + (d1 - d0) * t
                grow = 0.76 + 0.24 * math.sin(math.pi * (0.15 + 0.85 * t))
                m.feather(
                    wing, pivot=[root * side, y, z],
                    length=length * grow, width=width, thickness=thick,
                    palette=shard_pal, sweep=sweep, droop=droop,
                    twist=5 * t, segments=2, taper=0.52, dir=side,
                    style="crystal", back=0.04 * li, overlap=0.10,
                    faces=("north", "south", "up", "down"),
                )

        # --- silver spar along the leading edge ---------------------------
        m.feather(wing, pivot=[root * side, 26.3, 1.72], length=7.4, width=0.9,
                  thickness=0.9, palette=frame_pal, sweep=20, droop=30,
                  segments=2, taper=0.62, dir=side, style="facet")

        # --- ribbons of light trailing off the wing tips ------------------
        for i in range(2):
            t = float(i)
            m.feather(wing, pivot=[root * side, 22.8 - 1.0 * t, 2.45 + 0.12 * t],
                      length=6.2 - 1.2 * t, width=0.95, thickness=0.3,
                      palette=shard_pal, sweep=44 + 18 * t, droop=62 + 12 * t,
                      segments=3, taper=0.42, dir=side, style="crystal",
                      faces=("north", "south"))
    return m


# --------------------------------------------------------------------------
# dragon
# --------------------------------------------------------------------------


def build_dragon(identifier="geometry.elytra", variant="dragon", atlas=256):
    m = Model(identifier, atlas_size=atlas, texture_width=atlas, texture_height=atlas,
              visible_bounds=(11, 6, 0, 1.75, 0))
    bone_pal = palette("dragon_bone", variant)
    mem_pal = palette("dragon_membrane", variant)
    claw_pal = palette("dragon_claw", variant)

    body = m.bone("body", pivot=[0, 24, 0])
    spine = m.bone("dragon_spine", pivot=[0, 23, 2.0], parent="body")
    m.box(spine, [-2.1, 23.2, 1.7], [4.2, 5.0, 1.2], bone_pal, style="grad")
    for i in range(4):
        m.box(spine, [-0.6, 23.6 + i * 1.2, 2.55], [1.2, 0.95, 0.85], claw_pal,
              rotation=[-26, 0, 0], pivot=[0, 23.6 + i * 1.2, 2.55], style="facet")
    m.box(spine, [-2.6, 27.8, 1.5], [5.2, 1.0, 1.5], bone_pal, style="grad")

    for side, name in ((1, "dragon_wing_l"), (-1, "dragon_wing_r")):
        wing = m.bone(name, pivot=[2.1 * side, 25.4, 1.7], parent="body")
        root = 1.95

        # --- webbing first, so the bones sit on top of it ------------------
        # (sweep_from, sweep_to, outer length, inner length)
        panels = [(10, 34, 11.0, 9.4), (34, 58, 9.4, 7.8), (58, 82, 7.8, 5.6)]
        for pa, pb, ln_a, ln_b in panels:
            webs = 5
            for i in range(webs):
                t = (i + 0.5) / webs
                sweep = pa + (pb - pa) * t
                ln = (ln_a + (ln_b - ln_a) * t) * (0.86 + 0.14 * math.sin(math.pi * t))
                m.feather(
                    wing, pivot=[root * side, 25.2, 1.55],
                    length=ln, width=2.05, thickness=0.22, palette=mem_pal,
                    sweep=sweep, droop=34 + 6 * t, segments=2, taper=0.42,
                    dir=side, style="spot", overlap=0.12,
                )

        # --- arm + finger bones over the webbing --------------------------
        m.feather(wing, pivot=[root * side, 25.9, 1.75], length=7.0, width=0.9,
                  thickness=0.9, palette=bone_pal, sweep=10, droop=30,
                  segments=2, taper=0.7, dir=side, style="facet")
        fingers = (12, 36, 60, 84)
        for k, fa in enumerate(fingers):
            m.feather(wing, pivot=[root * side, 25.9, 1.78], length=11.0 - k * 1.7,
                      width=0.62, thickness=0.62, palette=bone_pal, sweep=fa,
                      droop=32 + k * 2, segments=3, taper=0.72, dir=side,
                      style="facet")
            # claw at the finger tip
            a = math.radians(fa)
            dist = (11.0 - k * 1.7) * 0.96
            tipx = (root + math.cos(a) * dist * math.cos(math.radians(32))) * side
            tipy = 25.9 - math.sin(math.radians(32)) * dist
            tipz = 1.78 + math.sin(a) * dist * 0.85
            m.box(wing, [tipx - 0.5, tipy - 0.6, tipz - 0.5], [1.0, 1.2, 0.9],
                  claw_pal, rotation=[-18, -fa, 0], pivot=[tipx, tipy, tipz],
                  style="facet")
    return m


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

DESIGNS = {
    "phoenix": dict(builder=build_phoenix, variant="phoenix", label="Phoenix",
                    icon_bg="#2b0d10", accent="#ff7a1e"),
    "phoenix_dark": dict(builder=build_phoenix, variant="phoenix_dark", label="Dark Phoenix",
                         icon_bg="#1a070b", accent="#ff5a2a"),
    "seraph": dict(builder=build_seraph, variant="seraph", label="Seraph",
                   icon_bg="#10202c", accent="#8fd8ff"),
    "seraph_gold": dict(builder=build_seraph, variant="seraph_gold", label="Golden Seraph",
                        icon_bg="#2a2010", accent="#ffe08a"),
    "dragon": dict(builder=build_dragon, variant="dragon", label="Void Dragon",
                   icon_bg="#150c22", accent="#b06cf0"),
    "dragon_ember": dict(builder=build_dragon, variant="dragon_ember", label="Ember Dragon",
                         icon_bg="#1c0c07", accent="#ff8a3c"),
}


# --------------------------------------------------------------------------
# subpack writer
# --------------------------------------------------------------------------

# every new design re-uses the pack's animation set; the bone names are mapped
# onto the wing/spine bones so the elytra still moves with the player.
CONTROLLER = "controller.animation.elytra.default"


def make_animations(design, bone_l="wing_l", bone_r="wing_r"):
    """Animations written for the new wing bones.

    The original pack's controller references animation names that do not exist
    in its animations file, so the new designs ship their own pair of files with
    matching names instead of relying on the broken ones.
    """
    idle = "animation.%s.idle" % design
    glide = "animation.%s.glide" % design
    sneak = "animation.%s.sneak" % design
    swim = "animation.%s.swim" % design
    sleep = "animation.%s.sleep" % design

    animations = {
        idle: {
            "loop": True,
            "animation_length": 4.0,
            "bones": {
                bone_l: {"rotation": {"0.0": [0, 0, 4], "2.0": [0, 0, 9], "4.0": [0, 0, 4]}},
                bone_r: {"rotation": {"0.0": [0, 0, -4], "2.0": [0, 0, -9], "4.0": [0, 0, -4]}},
            },
        },
        glide: {
            "loop": True,
            "animation_length": 1.2,
            "bones": {
                bone_l: {"rotation": {"0.0": [0, 0, 26], "0.45": [0, 0, -8],
                                      "0.8": [0, 0, 20], "1.2": [0, 0, 26]}},
                bone_r: {"rotation": {"0.0": [0, 0, -26], "0.45": [0, 0, 8],
                                      "0.8": [0, 0, -20], "1.2": [0, 0, -26]}},
            },
        },
        sneak: {
            "loop": "hold_on_last_frame",
            "animation_length": 0.3,
            "bones": {
                bone_l: {"rotation": [0, 62, -18]},
                bone_r: {"rotation": [0, -62, 18]},
            },
        },
        swim: {
            "loop": True,
            "animation_length": 2.0,
            "bones": {
                bone_l: {"rotation": {"0.0": [0, -18, -12], "1.0": [0, -26, -4],
                                      "2.0": [0, -18, -12]}},
                bone_r: {"rotation": {"0.0": [0, 18, 12], "1.0": [0, 26, 4],
                                      "2.0": [0, 18, 12]}},
            },
        },
        sleep: {
            "loop": True,
            "bones": {
                bone_l: {"rotation": [0, 70, -30]},
                bone_r: {"rotation": [0, -70, 30]},
            },
        },
    }

    controller = {
        "format_version": "1.10.0",
        "animation_controllers": {
            CONTROLLER: {
                "initial_state": "default",
                "states": {
                    "default": {
                        "animations": [idle],
                        "transitions": [
                            {"gliding": "query.is_gliding"},
                            {"sneaking": "query.is_sneaking"},
                            {"swimming": "query.is_swimming"},
                            {"sleeping": "query.is_sleeping"},
                        ],
                    },
                    "gliding": {
                        "animations": [glide],
                        "transitions": [
                            {"default": "!query.is_gliding"},
                            {"swimming": "query.is_swimming"},
                        ],
                    },
                    "sneaking": {
                        "animations": [sneak],
                        "transitions": [{"default": "!query.is_sneaking"}],
                    },
                    "swimming": {
                        "animations": [swim],
                        "transitions": [{"default": "!query.is_swimming"}],
                    },
                    "sleeping": {
                        "animations": [sleep],
                        "transitions": [{"default": "!query.is_sleeping"}],
                    },
                },
            }
        },
    }

    attachable_animations = {
        "default_controller": CONTROLLER,
        "idle": idle,
        "glide": glide,
        "sneak": sneak,
        "swim": swim,
        "sleep": sleep,
    }
    return animations, controller, attachable_animations


def write_subpack(name, m, spec, target=None):
    """Create Custom Elytra/subpacks/<name>/ ready to be zipped."""
    if target is None:
        target = os.path.join(PACK, "subpacks", name)
    tex_dir = os.path.join(target, "textures", "models", "intity")
    geo_dir = os.path.join(target, "models")
    att_dir = os.path.join(target, "attachables")
    for folder in (tex_dir, geo_dir, att_dir):
        os.makedirs(folder, exist_ok=True)

    # model + texture
    m.save_geometry(os.path.join(geo_dir, "mobs.json"))
    m.save_texture(os.path.join(tex_dir, "samurai.png"))

    # attachable: points at the same texture path the pack already uses, but at
    # this design's own geometry
    attachable = {
        "format_version": "1.10.0",
        "minecraft:attachable": {
            "description": {
                "identifier": "minecraft:elytra",
                "materials": {"default": "phantom", "enchanted": "elytra_glint"},
                "textures": {
                    "default": "textures/models/intity/samurai",
                    "enchanted": "textures/misc/enchanted_item_glint",
                },
                "geometry": {"default": m.identifier},
                "animations": {},
                "scripts": {
                    "parent_setup": "variable.chest_layer_visible = 0.0;",
                    "animate": ["default_controller"],
                },
                "render_controllers": ["controller.render.armor"],
            }
        },
    }
    with open(os.path.join(att_dir, "elytra.json"), "w", encoding="utf-8") as fh:
        json.dump(attachable, fh, indent=2)
        fh.write("\n")

    # design specific animations (idle / flap / folded ...); bone names differ
    # per design, so read them from the model instead of hard coding them
    bone_names = [b["name"] for b in m.bones]
    wing_l = next((b for b in bone_names if b.endswith("wing_l")), "wing_l")
    wing_r = next((b for b in bone_names if b.endswith("wing_r")), "wing_r")
    animations, controller, anims = make_animations(name, wing_l, wing_r)
    anim_dir = os.path.join(target, "animations")
    ctrl_dir = os.path.join(target, "animation_controllers")
    os.makedirs(anim_dir, exist_ok=True)
    os.makedirs(ctrl_dir, exist_ok=True)
    with open(os.path.join(anim_dir, "elytra.animation.json"), "w", encoding="utf-8") as fh:
        json.dump({"format_version": "1.8.0", "animations": animations}, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(ctrl_dir, "elytra.animation_controllers.json"), "w",
              encoding="utf-8") as fh:
        json.dump(controller, fh, indent=2)
        fh.write("\n")

    # the attachable needs the animation names now, so write it last
    attachable["minecraft:attachable"]["description"]["animations"] = anims
    with open(os.path.join(att_dir, "elytra.json"), "w", encoding="utf-8") as fh:
        json.dump(attachable, fh, indent=2)
        fh.write("\n")
    return target


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--outdir", default="/tmp/designs")
    ap.add_argument("--subpack", action="store_true",
                    help="also write installable subpacks into the resource pack")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    names = [args.only] if args.only else list(DESIGNS)
    for name in names:
        spec = DESIGNS[name]
        m = spec["builder"](variant=spec["variant"])
        geo_path = os.path.join(args.outdir, name + ".geo.json")
        tex_path = os.path.join(args.outdir, name + ".png")
        m.save_geometry(geo_path)
        m.save_texture(tex_path)
        if args.subpack:
            write_subpack(name, m, spec)
        print("%-14s %2d bones %3d cubes -> %s%s" % (
            name, len(m.bones), sum(len(b["cubes"]) for b in m.bones),
            os.path.basename(tex_path), "  (+subpack)" if args.subpack else ""))


if __name__ == "__main__":
    main()
