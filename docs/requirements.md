# Requirements

What the board has to do, and how each one gets checked. Written before the
schematic and kept honest afterwards.

## Functional

| ID | Requirement | Verified by |
|---|---|---|
| F-1 | Six independently addressable RGB LEDs twinkle while powered on | Inspection, powered board |
| F-2 | Runs from internal rechargeable cells with no external supply | Measurement, cells only |
| F-3 | Recharges over the USB-C connector | Measurement, charge current at `VBAT` |
| F-4 | Reflashes over the same USB-C connector, no extra programmer | Test, upload from Arduino IDE |
| F-5 | No push buttons; reset and bootloader entry are automatic | Test, upload with no manual intervention |
| F-6 | One physical control: a power switch that cuts the load | Inspection |
| F-7 | Charging works with the power switch off | Measurement, SW1 off, charge LED lit |
| F-8 | Shuts itself off after a period so forgotten cells are not drained | Test, firmware deep-sleep timer |
| F-9 | Readable as a butterfly from across a room | Inspection |

## Electrical

| ID | Requirement | Target | Verified by |
|---|---|---|---|
| E-1 | Battery rail range the design must tolerate | 3.0 – 4.2 V | Analysis, LIR2032 chemistry |
| E-2 | Regulated rail for the MCU | 3.3 V ±3 % | Measurement at `+3.3V` |
| E-3 | Charge current, safe for the cell pair | ~42 mA (≈0.5 C of 80 mAh) | R_PROG = 24 kΩ; I = 1000/R |
| E-4 | Average current while twinkling | ≤ 15 mA | Measurement in series with `VBAT_SW` |
| E-5 | Runtime per charge | 3 – 4 h | Measurement, run to brownout |
| E-6 | Peak current must stay inside what two LIR2032 can give | ≤ 60 mA | Firmware caps brightness and lit count |
| E-7 | USB data pair impedance-sane and protected | 27 Ω series + USBLC6 | Inspection |
| E-8 | The bridge's internal 3.3 V must not back-drive the regulator | separate net `FT_3V3` | Inspection, netlist |

## Mechanical and manufacturing

| ID | Requirement | Target | Verified by |
|---|---|---|---|
| M-1 | Buildable by hand with an iron | all SMD, nothing below 1206 | BOM review |
| M-2 | Profile routable at a normal board house | min width 5.4 mm, min internal radius 0.8 mm | `butterfly_outline.py` reports both |
| M-3 | Hangs as an ornament | 3.2 mm hole at the head | Inspection |
| M-4 | Two 20 mm cells fit without fouling anything | clearance checked per part | `butterfly_placement.json` fit report |
| M-5 | Board files regenerate identically from source | byte-identical reruns | `validate_sheets.py`, CI |

## Safety

| ID | Requirement | Verified by |
|---|---|---|
| S-1 | Cell holders accept only rechargeable LIR2032 | Silkscreen marking, documentation, BOM note |
| S-2 | Charge current stays below the cell's rated charge rate | R_PROG selection, measurement |
| S-3 | No exposed mains or stored high voltage anywhere on the board | Inspection |

> S-1 is the one that actually matters. A CR2032 is not rechargeable. Put one in
> this board with USB plugged in and the charger will push current into a cell
> that cannot absorb it, which vents or burns. Mark both retainers on the
> silkscreen and again wherever the board ends up living.
