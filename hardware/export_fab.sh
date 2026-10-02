#!/usr/bin/env bash
# Export everything a board house needs, from the KiCad project.
#
#   ./export_fab.sh            # gerbers, drill, pick-and-place, BOM, STEP
#   ./export_fab.sh --zip      # ...and a fab.zip ready to upload
#
# Needs kicad-cli, which ships with KiCad 7 and newer:
#   kicad-cli version
# On Ubuntu, if it is missing:
#   sudo add-apt-repository --yes ppa:kicad/kicad-9.0-releases
#   sudo apt update && sudo apt install --install-recommends kicad
#
# Run this only once the board is routed. Before that it still works, but the
# copper layers come out empty and the board house will reject the job.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ="$HERE/LED Butterfly"
PCB="$PROJ/LED Butterfly.kicad_pcb"
SCH="$PROJ/LED Butterfly.kicad_sch"
OUT="$HERE/../fab"

command -v kicad-cli >/dev/null || { echo "kicad-cli not found; see the header of this script"; exit 1; }
[ -f "$PCB" ] || { echo "no board at $PCB"; exit 1; }

rm -rf "$OUT"; mkdir -p "$OUT/gerbers" "$OUT/assembly"

echo "==> gerbers"
kicad-cli pcb export gerbers \
  --output "$OUT/gerbers/" \
  --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
  --no-protel-ext --subtract-soldermask --use-drill-file-origin \
  "$PCB"

echo "==> drill files"
kicad-cli pcb export drill \
  --output "$OUT/gerbers/" \
  --format excellon --drill-origin plot --excellon-units mm \
  --excellon-separate-th --generate-map --map-format gerberx2 \
  "$PCB"

echo "==> pick and place"
kicad-cli pcb export pos --output "$OUT/assembly/positions-top.csv" \
  --format csv --units mm --side front "$PCB"
kicad-cli pcb export pos --output "$OUT/assembly/positions-bottom.csv" \
  --format csv --units mm --side back "$PCB"

echo "==> bill of materials"
kicad-cli sch export bom --output "$OUT/assembly/bom-grouped.csv" \
  --fields 'Reference,Value,Footprint,${QUANTITY}' --group-by Value,Footprint "$SCH" \
  || echo "    (kicad-cli sch export bom needs KiCad 8+; docs/bom.csv is the fallback)"
cp "$HERE/../docs/bom.csv" "$OUT/assembly/bom.csv"

echo "==> JLCPCB-shaped CPL"
python3 "$HERE/jlc_convert.py" "$OUT/assembly" || true

echo "==> 3D model"
kicad-cli pcb export step --output "$OUT/butterfly.step" --subst-models --no-dnp "$PCB" \
  || echo "    (STEP export needs the 3D models installed; skipping)"

cp "$HERE/../docs/manufacturing.md" "$OUT/README-for-the-fab.md"

if [ "${1:-}" = "--zip" ]; then
  ( cd "$OUT" && zip -qr ../fab.zip gerbers assembly butterfly.step README-for-the-fab.md 2>/dev/null || \
    zip -qr ../fab.zip gerbers assembly README-for-the-fab.md )
  echo "==> wrote fab.zip"
fi

echo
echo "Done. Upload fab/gerbers (or fab.zip) to the board house."
echo "Check it in a viewer first: https://www.gerber-viewer.com or KiCad's own GerbView."
