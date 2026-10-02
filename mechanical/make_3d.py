#!/usr/bin/env python3
"""
3D files for the Twinkling Butterfly.

    butterfly_board.stl    the board profile extruded to 1.6 mm, with the hang
                           hole, for checking fit against a case or a stand
    butterfly_stand.stl    a printable desk stand the board slots into

Both are derived from the same outline as the PCB, so they stay in step with it.
For a full board-with-components model, use KiCad's own exporter once the
footprints are placed:  File > Export > STEP.

    python3 make_3d.py
"""
import os
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point
from shapely import affinity

import butterfly_outline as bo

BOARD_T = 1.6          # mm, standard 2-layer stackup
STAND = dict(width=34.0,      # along the board's X, i.e. how wide the stand is
             depth=46.0,      # front to back
             height=22.0,
             slot_w=2.4,      # board thickness plus clearance
             slot_depth=13.0,
             lean_deg=14.0,   # backwards lean of the board
             wall=3.0)


def board_mesh(tolerance=0.08):
    # the PCB outline is resampled at 0.4 mm for Edge.Cuts; that is far more
    # detail than a fit-check model needs, so simplify before extruding
    poly = bo.build().simplify(tolerance)
    hole = Point(bo.HANG_HOLE["x"], bo.HANG_HOLE["y"]).buffer(bo.HANG_HOLE["d"] / 2, quad_segs=48)
    poly = poly.difference(hole)
    mesh = trimesh.creation.extrude_polygon(poly, height=BOARD_T)
    mesh.apply_translation([0, 0, -BOARD_T / 2])
    return mesh


def stand_mesh(p=STAND):
    """Side profile in X/Y, extruded along Z, then stood upright."""
    w, h = p["depth"], p["height"]
    body = Polygon([(-w / 2, 0), (w / 2, 0),
                    (w / 2 * 0.55, h), (-w / 2 * 0.55, h)])
    # the slot: a thin rectangle, leaned back, cut from the top face
    slot = Polygon([(-p["slot_w"] / 2, h - p["slot_depth"]),
                    (p["slot_w"] / 2, h - p["slot_depth"]),
                    (p["slot_w"] / 2, h + 2), (-p["slot_w"] / 2, h + 2)])
    slot = affinity.rotate(slot, -p["lean_deg"], origin=(0, h - p["slot_depth"]))
    profile = body.difference(slot)
    # hollow the underside so it prints without a solid block of plastic
    cav = Polygon([(-w / 2 + p["wall"], 0), (w / 2 - p["wall"], 0),
                   (w / 2 - p["wall"], h - p["slot_depth"] - p["wall"]),
                   (-w / 2 + p["wall"], h - p["slot_depth"] - p["wall"])])
    profile = profile.difference(cav)
    if profile.geom_type == "MultiPolygon":
        profile = max(profile.geoms, key=lambda g: g.area)
    mesh = trimesh.creation.extrude_polygon(profile, height=p["width"])
    # lay it so +Z is up and the slot opens upward
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    mesh.apply_translation([0, p["width"] / 2, 0])
    return mesh


def report(name, mesh):
    e = mesh.extents
    return dict(file=name, watertight=bool(mesh.is_watertight), volume_cm3=round(mesh.volume / 1000, 2),
                size_mm=[round(float(v), 2) for v in e], triangles=int(len(mesh.faces)))


if __name__ == "__main__":
    import json
    out = []
    b = board_mesh()
    b.export("butterfly_board.stl")
    out.append(report("butterfly_board.stl", b))
    s = stand_mesh()
    s.export("butterfly_stand.stl")
    out.append(report("butterfly_stand.stl", s))
    open("3d_report.json", "w").write(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
