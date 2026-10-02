#!/usr/bin/env python3
"""
Rewrites KiCad's position CSV into the column names JLCPCB's assembly service
expects, and writes a matching parts list.

    python3 jlc_convert.py ../fab/assembly

KiCad gives: Ref, Val, Package, PosX, PosY, Rot, Side
JLCPCB wants: Designator, Mid X, Mid Y, Layer, Rotation

Rotation conventions differ per part between KiCad and JLCPCB's library; always
check the preview JLCPCB renders before paying for a run.
"""
import csv, os, sys

def convert(src, dst):
    with open(src, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return 0
    key = {k.lower().strip(): k for k in rows[0]}
    def g(r, *names):
        for n in names:
            if n in key:
                return r[key[n]]
        return ""
    with open(dst, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            side = (g(r, "side") or "top").lower()
            w.writerow([g(r, "ref", "reference", "designator"),
                        g(r, "posx", "x"), g(r, "posy", "y"),
                        "Top" if side.startswith(("t", "f")) else "Bottom",
                        g(r, "rot", "rotation")])
    return len(rows)

def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    total = 0
    for side in ("top", "bottom"):
        src = os.path.join(d, f"positions-{side}.csv")
        if os.path.exists(src):
            n = convert(src, os.path.join(d, f"jlc-cpl-{side}.csv"))
            print(f"    jlc-cpl-{side}.csv — {n} placements")
            total += n
    if not total:
        print("    no position files found; run export_fab.sh first")

if __name__ == "__main__":
    main()
