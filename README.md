# Twinkling Butterfly

A butterfly-shaped PCB ornament with six addressable RGB LEDs that twinkle at
night. Bare ESP32-C3FH4, two rechargeable LIR2032 coin cells, charged and
reflashed over the same USB-C port — no buttons, no programmer, no module.

![Board outline](docs/butterfly_preview.png)

83.8 × 63.3 mm, 3392 mm². All surface mount, nothing finer than 1206 except the
QFN, the SSOP-20 and the USB-C shell. Wing veins, body and antennae are
silkscreen, generated from the outline. A 3.2 mm hole at the head hangs it.

## How it works

USB-C `VBUS` feeds an MCP73831 charger (~42 mA, set by a 24 kΩ PROG resistor)
into two LIR2032 cells wired in parallel, and feeds the FT231XS bridge
directly. The cells run through slide switch **SW1** into an AP2112K-3.3 LDO
for the ESP32-C3FH4. The FT231XS converts USB to UART on GPIO20/21, and its
DTR#/RTS# lines drive two cross-coupled MMBT2222A transistors that pull
`CHIP_ENABLE` and `BOOT` so esptool can reset and enter the bootloader on its
own. GPIO4 drives the WS2812B chain from the *switched battery* rail, not the
regulator. GPIO18/19 go to test pads as a backup native-USB flashing path.

The charger stays on the battery side of SW1, so the board charges with the
switch off. The ESP32 is behind SW1, so **SW1 must be on to flash**.

## Layout

```
hardware/
  LED Butterfly/           the KiCad 10 project
    LED Butterfly.kicad_sch    root, four sheets
    Main.kicad_sch             Microcontroller  (hand-drawn, unchanged)
    USB_UART.kicad_sch         USB-C, ESD, FT231XS, auto-reset  (generated)
    Power.kicad_sch            charger, cells, switch, LDO      (generated)
    LED.kicad_sch              six WS2812B + decoupling         (generated)
    butterfly.kicad_sym        project symbols, footprints pre-assigned
    LED Butterfly.kicad_pcb    board file carrying the butterfly outline
  generate_sheets.py       regenerates the three generated sheets
  validate_sheets.py       re-parses the written files and rebuilds the netlist
  make_bom.py              builds docs/bom.csv from the schematic
mechanical/
  butterfly_outline.py     parametric outline -> SVG, DXF, Edge.Cuts, preview
firmware/
  butterfly_twinkle/       Arduino sketch
docs/
  bom.csv  netlist.md  power-and-charging.md  assembly.md  design-decisions.md
  publishing.md            how to push this to GitHub
```

## Regenerating

```sh
pip install shapely matplotlib
cd mechanical && python3 butterfly_outline.py     # outline + previews
cd ../hardware && python3 generate_sheets.py      # the three sheets + board
python3 validate_sheets.py                        # netlist check, exit 0 = clean
python3 make_bom.py                               # docs/bom.csv
```

`generate_sheets.py` reads the existing Microcontroller sheet for its symbol
definitions and never modifies it. The generated sheets are **label-driven**:
every pin gets a short stub and a label, so connectivity is by net name and you
can drag symbols around without breaking anything.

`validate_sheets.py` is an independent checker — it re-parses the files that
were actually written, rebuilds the netlist from wire geometry, and fails on
floating pins, duplicate references, unnamed single-pin nets or missing symbol
definitions. Current state: **41 nets, 60 references, clean**.

## Firmware

Arduino IDE, `esp32` core, board **ESP32C3 Dev Module**, `Adafruit NeoPixel`
library, upload over the FT231XS COM port. Brightness is capped near 10 %, at
most three pixels are lit at once, and the CPU light-sleeps between frames —
about 12 mA average, so 3–4 hours per charge. It deep sleeps after 8 hours.

## Status

Done: all four schematic sheets, netlist verified, board outline and silkscreen
artwork, BOM, firmware. Every part is surface mount.

Next: footprint assignment pass, then open the board file and
**Tools → Update PCB from Schematic (F8)** to pull the parts in, place and
route. `mechanical/butterfly_placement.json` has suggested centres for every
major part, each proven to fit inside the outline.

> **The coin-cell holders are LIR-only.** LIR2032 is rechargeable; a CR2032 is
> not. A CR2032 in this board with USB plugged in is a fire risk. Mark both
> holders on the silkscreen.

## Licence

Hardware under [CERN-OHL-P v2](LICENSE-HARDWARE), firmware and scripts under
MIT (see [LICENSE](LICENSE)).
