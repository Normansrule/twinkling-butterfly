# Assembly notes

The board is all surface mount, chosen so it can still be built by hand. Every
passive is 1206 — big enough to hold with tweezers and heat from one side. The
only fine-pitch parts are the QFN-32 MCU, the SSOP-20 bridge, the SOT-23 family
and the USB-C receptacle. Nothing needs a through-hole: the coin-cell retainers,
the slide switch and the bulk electrolytic are all SMD.

## Suggested order

1. **U1 (ESP32-C3FH4, QFN-32).** Hardest part, do it while the board is
   otherwise bare and you can get a hot plate or hot air at it from any angle.
   The exposed pad underneath is the chip's *only* ground connection — it must
   be soldered, and it must be stitched to the ground plane with 4–9 vias.
2. **U5 (FT231XS), U2, U3, U4, Q1, Q2.** Drag-solder the SSOP-20, then the
   SOT-23s.
3. **J1 (USB-C).** The shield pads are the only mechanical anchor on an all-SMD
   receptacle, so flood them and make sure there is ground pour underneath.
4. **Passives**, grouped by value so you are not re-reading the reel every part.
5. **Y1 (crystal).** Within 5 mm of pins 29/30, ground pour under the case pads.
6. **D1–D6 (WS2812B)** and **C26**, the 8 mm SMD electrolytic. Two big pads, so a
   normal iron handles it — just tack one pad, straighten the can, then do the other.
7. **SW1** (surface-mount slide switch), then the two coin-cell retainers last so
   they are not in the way.

## Before you fit the cells

With the holders empty, plug in USB-C and check:

* 5 V on `VBUS`;
* the charger does not get hot (nothing to charge, so it should be cold);
* a COM port appears — that proves U5, J1 and the ESP-side wiring;
* with a bench supply at 3.7 V on `VBAT` and SW1 on, `+3.3V` reads 3.3 V.

Only then fit two LIR2032 cells, both the same brand and batch.

## Layout reminders

* QFN exposed pad stitched with 4–9 vias — it is the chip's only ground.
* USB differential pair short and length-matched, routed away from the crystal.
* Ground pour under the USB-C shield pads.
* C26 (470 µF) physically next to the first pixel it feeds, not at the regulator.
* Thermal relief on the MCP73831 — it dissipates the charge current.
* The board outline is a closed polyline on Edge.Cuts, 83.8 x 63.3 mm. Minimum
  board width is 5.4 mm at the wing roots and every concave corner has a 0.8 mm
  radius, so a 1.5 mm router bit can follow it.
* The 3.2 mm hole at the head is for hanging it.
* The wing veins, body and antennae are on F.SilkS. They are generated from the
  outline, so if you change the shape, rerun `mechanical/butterfly_outline.py`
  and the artwork follows.
