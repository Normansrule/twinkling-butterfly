#!/usr/bin/env python3
"""
Parametric board outline and silkscreen artwork for the Twinkling Butterfly.

The silhouette is three Catmull-Rom splines -- forewing, hindwing, body --
unioned and mirrored about x = 0, with scallops added along the hindwing's
outer margin and the whole thing filleted so a router can follow it.

The wings and body are separated by SILKSCREEN, not by cut-outs: veins, a
marginal band and the body outline.  A 3 mm slot between body and wing kept
closing under the fillet and would have blocked every trace heading out to the
hindwing pixels, so the copper stays one solid piece and the butterfly is drawn
on top of it.

Outputs, written next to this script:
    butterfly_outline.svg        1:1 drawing including the silkscreen art
    butterfly_outline.dxf        KiCad: File > Import > Graphics... (R12, mm)
    butterfly_edge_cuts.txt      gr_line/gr_circle s-expressions for a .kicad_pcb
    butterfly_placement.json     metrics, fit checks, suggested part centres
    butterfly_preview.png        annotated preview

Board coordinates: (0,0) at the centre of the thorax, +X right, +Y up.  The
KiCad exporters flip Y and offset to the page origin.
"""
import json, math
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely import affinity

# ------------------------------------------------------------- silhouette
FOREWING = [(4.0, 18.0), (11.0, 25.5), (23.0, 31.0), (34.0, 33.5), (41.0, 32.0),
            (41.8, 30.6), (39.5, 22.0), (35.5, 13.5), (29.0, 7.0), (19.0, 3.6), (8.0, 2.8)]
HINDWING = [(10.0, 1.5), (18.5, 0.0), (27.0, -4.5), (32.0, -12.0), (30.5, -21.0),
            (23.0, -27.0), (15.5, -28.0), (11.0, -20.0), (9.5, -10.0)]
BODY = [(0, 30.0), (3.4, 27.5), (5.2, 22.0), (6.0, 13.0), (5.8, 3.0), (5.6, -7.0),
        (5.5, -16.0), (5.2, -24.0), (3.6, -28.5), (0, -29.5),
        (-3.6, -28.5), (-5.2, -24.0), (-5.5, -16.0), (-5.6, -7.0), (-5.8, 3.0),
        (-6.0, 13.0), (-5.2, 22.0), (-3.4, 27.5)]
HEAD = dict(x=0.0, y=26.5, r=4.4)

SCALLOP_CENTRE = (17.5, -13.5)   # scallops are placed around this point
SCALLOP_R = 3.0
SCALLOP_N = 6
SCALLOP_ARC = (-100, 28)         # degrees, outer margin only
FILLET = 0.8                     # rounds every join; also the min concave radius
SEG_LEN = 0.40                   # max exported straight segment
HANG_HOLE = dict(x=0.0, y=27.0, d=3.2)

# ------------------------------------------------------- silkscreen artwork
SILK_W = 0.22
MARGIN_BAND = 2.6                # inner line, offset in from the board edge
FOREWING_ROOT = (5.0, 9.0)
HINDWING_ROOT = (7.0, -3.0)
FOREWING_VEINS = 7
HINDWING_VEINS = 6
VEIN_STOP = 3.4                  # veins stop this far short of the board edge
ABDOMEN_SEGMENTS = 6
ANTENNA = [(1.6, 29.0), (5.0, 33.5), (10.0, 37.0), (14.5, 38.0)]
ANTENNA_CLUB = 1.1
SPOTS = [  # (x, y, r) on the right half, mirrored
    (34.0, 28.0, 1.5), (37.0, 24.0, 1.1),
    (26.0, -21.0, 1.9), (18.5, -24.5, 1.5), (13.0, -22.5, 1.1),
]

PLACEMENT = [
    dict(ref="BT1a", what="LIR2032 holder (back)", x=-22.0, y=17.0, r=11.0),
    dict(ref="BT1b", what="LIR2032 holder (back)", x=22.0, y=17.0, r=11.0),
    dict(ref="U1",   what="ESP32-C3FH4 (back)",    x=0.0,  y=10.0, r=5.0),
    dict(ref="U5",   what="FT231XS (back)",        x=0.0,  y=0.0,  r=4.5),
    dict(ref="J1",   what="USB-C, overhangs edge", x=0.0,  y=-24.0, r=4.8),
    dict(ref="SW1",  what="slide switch (SMD)",    x=-21.0, y=-14.0, r=4.5),
    dict(ref="C26",  what="470 uF bulk, next to D4", x=21.0, y=-14.0, r=4.5),
    dict(ref="D1",   what="WS2812B",  x=-14.0, y=22.0, r=3.2),
    dict(ref="D2",   what="WS2812B",  x=-30.0, y=20.0, r=3.2),
    dict(ref="D3",   what="WS2812B",  x=-28.0, y=-20.0, r=3.2),
    dict(ref="D4",   what="WS2812B",  x=28.0, y=-20.0, r=3.2),
    dict(ref="D5",   what="WS2812B",  x=30.0, y=20.0, r=3.2),
    dict(ref="D6",   what="WS2812B",  x=14.0, y=22.0, r=3.2),
    dict(ref="D7",   what="charge LED", x=0.0, y=-16.0, r=2.2),
]


def catmull(points, n=30):
    P = [points[-1]] + list(points) + [points[0], points[1]]
    out = []
    for i in range(len(P) - 3):
        p0, p1, p2, p3 = P[i:i + 4]
        for j in range(n):
            t = j / n; t2 = t * t; t3 = t2 * t
            out.append((
                0.5 * (2*p1[0] + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2
                       + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3),
                0.5 * (2*p1[1] + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2
                       + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)))
    return out


def build():
    fore = Polygon(catmull(FOREWING)).buffer(0)
    hind = Polygon(catmull(HINDWING, 40)).buffer(0)
    body = Polygon(catmull(BODY)).buffer(0)

    cx, cy = SCALLOP_CENTRE
    margin = [(x, y) for x, y in hind.exterior.coords
              if SCALLOP_ARC[0] <= math.degrees(math.atan2(y - cy, x - cx)) <= SCALLOP_ARC[1]
              and x >= cx - 3.0]
    if margin:
        step = max(1, len(margin) // SCALLOP_N)
        for i in range(0, len(margin), step):
            x, y = margin[i]
            v = math.hypot(x - cx, y - cy) or 1.0
            hind = unary_union([hind, Point(x - (x - cx) / v * 1.4,
                                            y - (y - cy) / v * 1.4
                                            ).buffer(SCALLOP_R, quad_segs=40)])

    right = unary_union([fore, hind])
    shape = unary_union([right, affinity.scale(right, xfact=-1, origin=(0, 0)), body,
                         Point(HEAD["x"], HEAD["y"]).buffer(HEAD["r"], quad_segs=64)])
    f = FILLET
    shape = (shape.buffer(f, quad_segs=96, join_style=1)
                  .buffer(-2 * f, quad_segs=96, join_style=1)
                  .buffer(f, quad_segs=96, join_style=1))
    if shape.geom_type == "MultiPolygon":
        shape = max(shape.geoms, key=lambda g: g.area)
    return Polygon(shape.exterior)


def resample(poly, seg_len=SEG_LEN):
    ring = list(poly.exterior.coords)
    out = []
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / seg_len))
        out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n)]
    out.append(out[0])
    return out


# --------------------------------------------------------------- silkscreen
def silk_polylines(poly):
    """Every silkscreen element, as a list of point lists (open polylines)."""
    out = []

    # marginal band: the board edge brought inward
    band = poly.buffer(-MARGIN_BAND, quad_segs=48)
    for g in (band.geoms if band.geom_type == "MultiPolygon" else [band]):
        if g.is_empty:
            continue
        out.append([(round(x, 3), round(y, 3)) for x, y in g.exterior.coords])

    # wing veins, fanned from each wing root out to just short of the edge
    # keep every piece: eroding past the wing-root pinch splits the board, and
    # discarding the small pieces is what loses the hindwing veins
    inner = poly.buffer(-VEIN_STOP, quad_segs=48)
    veins = []
    for root, count, a0, a1 in ((FOREWING_ROOT, FOREWING_VEINS, 16, 80),
                                (HINDWING_ROOT, HINDWING_VEINS, -84, -10)):
        for k in range(count):
            a = math.radians(a0 + (a1 - a0) * k / (count - 1))
            ray = LineString([root, (root[0] + math.cos(a) * 90, root[1] + math.sin(a) * 90)])
            hit = ray.intersection(inner)
            if hit.is_empty:
                continue
            segs = list(hit.geoms) if hit.geom_type == "MultiLineString" else [hit]
            # the piece that actually starts at the wing root, not one further out
            seg = min(segs, key=lambda g: Point(root).distance(g))
            pts = list(seg.coords)
            if len(pts) < 2 or seg.length < 6.0:
                continue
            veins.append(((pts[0][0], pts[0][1]), (pts[-1][0], pts[-1][1])))
    for (ax_, ay), (bx, by) in veins:
        out.append([(round(ax_, 3), round(ay, 3)), (round(bx, 3), round(by, 3))])
        out.append([(round(-ax_, 3), round(ay, 3)), (round(-bx, 3), round(by, 3))])

    # body: outline plus abdomen segments
    out.append([(round(x, 3), round(y, 3)) for x, y in Polygon(catmull(BODY)).exterior.coords])
    for i in range(ABDOMEN_SEGMENTS):
        y = -6.0 - i * 3.6
        hw = 5.6 - i * 0.28
        out.append([(-hw, y), (hw, y)])

    # antennae, clubbed at the tip
    out.append([(round(x, 3), round(y, 3)) for x, y in ANTENNA])
    out.append([(round(-x, 3), round(y, 3)) for x, y in ANTENNA])
    return out


def silk_circles():
    """(x, y, r) filled-looking spots, mirrored, plus the antenna clubs."""
    out = []
    for x, y, r in SPOTS:
        out += [(x, y, r), (-x, y, r)]
    out += [(ANTENNA[-1][0], ANTENNA[-1][1], ANTENNA_CLUB),
            (-ANTENNA[-1][0], ANTENNA[-1][1], ANTENNA_CLUB)]
    return out


# ---------------------------------------------------------------- exporters
def _line(x0, y0, x1, y1, layer, width, origin):
    ox, oy = origin
    return (f'\t(gr_line\n\t\t(start {ox+x0:.4f} {oy-y0:.4f})\n'
            f'\t\t(end {ox+x1:.4f} {oy-y1:.4f})\n'
            f'\t\t(stroke\n\t\t\t(width {width})\n\t\t\t(type default)\n\t\t)\n'
            f'\t\t(layer "{layer}")\n\t)')


def _circle(x, y, r, layer, width, origin, fill="none"):
    ox, oy = origin
    return (f'\t(gr_circle\n\t\t(center {ox+x:.4f} {oy-y:.4f})\n'
            f'\t\t(end {ox+x+r:.4f} {oy-y:.4f})\n'
            f'\t\t(stroke\n\t\t\t(width {width})\n\t\t\t(type default)\n\t\t)\n'
            f'\t\t(fill {fill})\n\t\t(layer "{layer}")\n\t)')


def edge_cuts(pts, origin=(148.5, 105.0), width=0.1):
    out = [_line(a[0], a[1], b[0], b[1], "Edge.Cuts", width, origin)
           for a, b in zip(pts, pts[1:])]
    out.append(_circle(HANG_HOLE["x"], HANG_HOLE["y"], HANG_HOLE["d"] / 2,
                       "Edge.Cuts", width, origin))
    return out


def silk(poly, origin=(148.5, 105.0)):
    out = []
    for pl in silk_polylines(poly):
        for a, b in zip(pl, pl[1:]):
            out.append(_line(a[0], a[1], b[0], b[1], "F.SilkS", SILK_W, origin))
    for x, y, r in silk_circles():
        out.append(_circle(x, y, r, "F.SilkS", SILK_W, origin, fill="solid"))
    return out


def write_svg(pts, poly, path, pad=5.0):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    minx, maxx = min(xs + [-16]), max(xs + [16])
    miny, maxy = min(ys), max(ys + [39])
    w = maxx - minx + 2 * pad; h = maxy - miny + 2 * pad
    ox = -minx + pad; oy = maxy + pad
    parts = ['M ' + ' L '.join(f"{x+ox:.3f},{oy-y:.3f}" for x, y in pts) + ' Z']
    silkd = []
    for pl in silk_polylines(poly):
        silkd.append('M ' + ' L '.join(f"{x+ox:.3f},{oy-y:.3f}" for x, y in pl))
    hh = HANG_HOLE
    circles = "".join(
        f'<circle cx="{x+ox:.3f}" cy="{oy-y:.3f}" r="{r:.3f}" fill="#000"/>'
        for x, y, r in silk_circles())
    open(path, "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" '
        f'viewBox="0 0 {w:.3f} {h:.3f}">\n'
        f'  <path d="{parts[0]}" fill="none" stroke="#000" stroke-width="0.15"/>\n'
        f'  <circle cx="{hh["x"]+ox:.3f}" cy="{oy-hh["y"]:.3f}" r="{hh["d"]/2:.3f}" '
        f'fill="none" stroke="#000" stroke-width="0.15"/>\n'
        f'  <path d="{" ".join(silkd)}" fill="none" stroke="#000" '
        f'stroke-width="{SILK_W}"/>\n  {circles}\n</svg>\n')


def write_dxf(pts, path):
    """Minimal R12 DXF: one closed POLYLINE plus the hang hole as a CIRCLE.

    Written by hand rather than through a library so the file is deterministic --
    DXF writers stamp a save time and fresh GUIDs into every file, which makes the
    repo show a spurious change every time the generator runs.
    """
    def rec(code, value):
        return f"{code:>3}\n{value}\n"

    out = [rec(0, "SECTION"), rec(2, "ENTITIES"),
           rec(0, "POLYLINE"), rec(8, "EdgeCuts"), rec(66, 1),
           rec(70, 1), rec(10, "0.0"), rec(20, "0.0"), rec(30, "0.0")]
    for x, y in pts[:-1]:
        out += [rec(0, "VERTEX"), rec(8, "EdgeCuts"),
                rec(10, f"{x:.4f}"), rec(20, f"{y:.4f}"), rec(30, "0.0")]
    out += [rec(0, "SEQEND"), rec(8, "EdgeCuts")]
    out += [rec(0, "CIRCLE"), rec(8, "EdgeCuts"),
            rec(10, f"{HANG_HOLE['x']:.4f}"), rec(20, f"{HANG_HOLE['y']:.4f}"),
            rec(30, "0.0"), rec(40, f"{HANG_HOLE['d'] / 2:.4f}")]
    out += [rec(0, "ENDSEC"), rec(0, "EOF")]
    open(path, "w", newline="\n").write("".join(out))


def write_preview(poly, pts, path, show_parts=True):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.5, 7.2), dpi=170)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax.fill(xs, ys, facecolor="#155244", edgecolor="#c9a227", linewidth=1.4, zorder=1)
    for pl in silk_polylines(poly):
        ax.plot([p[0] for p in pl], [p[1] for p in pl],
                color="#f2efe6", lw=0.8, zorder=3)
    for x, y, r in silk_circles():
        ax.add_patch(plt.Circle((x, y), r, color="#f2efe6", zorder=3))
    ax.add_patch(plt.Circle((HANG_HOLE["x"], HANG_HOLE["y"]), HANG_HOLE["d"] / 2,
                            facecolor="white", edgecolor="#c9a227", lw=1, zorder=4))
    if show_parts:
        for p in PLACEMENT:
            col = "#ffd166" if p["ref"].startswith("D") else "#8ecae6"
            ax.add_patch(plt.Circle((p["x"], p["y"]), p["r"], fill=False,
                                    edgecolor=col, linestyle="--", lw=0.9, zorder=5))
            ax.annotate(p["ref"], (p["x"], p["y"]), color=col, fontsize=6,
                        ha="center", va="center", zorder=6)
    minx, miny, maxx, maxy = poly.bounds
    ax.set_aspect("equal"); ax.grid(alpha=.15, lw=.4)
    ax.set_title(f"Twinkling Butterfly — {maxx-minx:.1f} x {maxy-miny:.1f} mm, "
                 f"{poly.area:.0f} mm²", fontsize=10)
    ax.set_xlabel("mm"); ax.set_ylabel("mm")
    fig.tight_layout(); fig.savefig(path, facecolor="white"); plt.close(fig)


def min_board_width(poly):
    for t in [i / 10 for i in range(3, 41)]:
        e = poly.buffer(-t)
        if e.is_empty or e.geom_type == "MultiPolygon":
            return round(2 * t, 1)
    return None


def fit_report(poly):
    rows = []
    for p in PLACEMENT:
        disc = Point(p["x"], p["y"]).buffer(p["r"], quad_segs=64)
        rows.append(dict(ref=p["ref"], what=p["what"], x=p["x"], y=p["y"],
                         clearance_r_mm=p["r"], fits=bool(poly.contains(disc)),
                         margin_mm=round(poly.exterior.distance(Point(p["x"], p["y"])) - p["r"], 2)))
    return rows


if __name__ == "__main__":
    poly = build()
    pts = resample(poly)
    write_svg(pts, poly, "butterfly_outline.svg")
    write_dxf(pts, "butterfly_outline.dxf")
    geom = edge_cuts(pts) + silk(poly)
    open("butterfly_edge_cuts.txt", "w").write("\n".join(geom) + "\n")
    write_preview(poly, pts, "butterfly_preview.png")
    write_preview(poly, pts, "butterfly_artwork.png", show_parts=False)
    minx, miny, maxx, maxy = poly.bounds
    rpt = dict(span_mm=round(maxx - minx, 2), height_mm=round(maxy - miny, 2),
               area_mm2=round(poly.area, 1), edge_segments=len(pts) - 1,
               silk_primitives=len(geom) - len(pts) + 1,
               min_board_width_mm=min_board_width(poly),
               min_concave_radius_mm=FILLET, hang_hole=HANG_HOLE,
               placement=fit_report(poly))
    open("butterfly_placement.json", "w").write(json.dumps(rpt, indent=2))
    bad = [r["ref"] for r in rpt["placement"] if not r["fits"]]
    print(json.dumps({k: rpt[k] for k in
                      ("span_mm", "height_mm", "area_mm2", "edge_segments",
                       "silk_primitives", "min_board_width_mm")}, indent=2))
    print("parts that do NOT fit:", bad or "none")
