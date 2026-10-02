# Manufacturing

Everything a board house needs, and what to tell them.

## Board specification

| | |
|---|---|
| Size | 83.8 × 63.3 mm, irregular (butterfly) profile |
| Area | 3392 mm² |
| Layers | 2 |
| Thickness | 1.6 mm |
| Copper | 1 oz (35 µm) |
| Finish | HASL is fine; ENIG if you want the pads flat for the QFN |
| Soldermask | any colour — green and black both look good against the gold silkscreen |
| Silkscreen | top only (the wing veins, body and antennae live there) |
| Min track / clearance | 0.2 mm / 0.2 mm — nothing on this board needs finer |
| Min drill | 0.3 mm (the via stitching under the QFN pad) |
| Min board width | 5.4 mm, at the wing roots |
| Min internal radius | 0.8 mm, so a 1.5 mm router bit can follow the profile |
| Castellations / edge plating | none |
| Panelisation | not needed; the profile routes as a single piece |

The outline is a closed polyline on `Edge.Cuts` plus one 3.2 mm circle for the
hang hole. No slots, no cut-outs.

> **Tell the fab it is a routed profile, not a V-score.** Some houses default to
> V-scoring and will come back asking; saying "irregular outline, rout to the
> Edge.Cuts layer" up front saves a day.

## Producing the files

```bash
cd hardware
./export_fab.sh --zip
```

That writes `fab/` and `fab.zip`:

```
fab/
  gerbers/          F.Cu B.Cu F.Mask B.Mask F.Paste B.Paste
                    F.Silkscreen B.Silkscreen Edge.Cuts + Excellon drill
  assembly/
    bom.csv               the human BOM
    positions-top.csv     KiCad pick-and-place
    positions-bottom.csv
    jlc-cpl-top.csv       same data in JLCPCB's column names
    jlc-cpl-bottom.csv
  butterfly.step    3D model, if the KiCad 3D models are installed
```

It needs `kicad-cli`, which ships with KiCad 7 and newer. On Ubuntu:

```bash
sudo add-apt-repository --yes ppa:kicad/kicad-9.0-releases
sudo apt update && sudo apt install --install-recommends kicad
kicad-cli version
```

**Run it only once the board is routed.** Before that the script still works but
the copper layers come out empty.

Always open the gerbers in a viewer before paying — KiCad's own GerbView, or any
web viewer. Look for: the profile closed, the hang hole present, silkscreen not
sitting on pads, and the drill file lining up with the copper.

## Ordering

Any of the usual houses will take this as-is. Prices move, so check rather than
trust a number here.

| | |
|---|---|
| Bare boards | Upload `fab.zip`. Specify 2 layers, 1.6 mm, 1 oz, routed outline. |
| Assembled | Upload gerbers + `jlc-cpl-top.csv` + `assembly/bom.csv`. |

If you have them assemble it, three parts are worth checking by hand in the
preview before you confirm:

1. **U1, the QFN-32.** Its exposed pad is the chip's only ground connection. It
   must be soldered, and the stencil aperture should be a window pattern, not
   one big square, or the chip floats on solder.
2. **J1, the USB-C.** Orientation is easy to get wrong; look at the render.
3. **Rotation on the SOT-23 parts.** KiCad and JLCPCB disagree about zero
   degrees for several of them. The preview is the only reliable check.

The coin cells themselves are not an assembly-house item — fit those yourself,
and see `power-and-charging.md` for why they must be LIR2032 and never CR2032.

## Building it by hand instead

The whole board is surface mount with nothing below 1206, which is the point: it
is designed to be built with tweezers, a normal iron and a bit of patience. See
[`assembly.md`](assembly.md) for the order to place parts in and what to check
before the cells go in.

## Licensing

Hardware is under CERN-OHL-P v2, firmware and scripts under MIT. You can make
these, sell them, or change them; keep the notices.
