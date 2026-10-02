# Design decisions

Settled, with the reasoning, so they do not get relitigated by accident.

| Decision | Why |
|---|---|
| Bare ESP32-C3FH4, not a module | Deliberate choice to route the hard version. 4 MB internal flash means no external SPI flash — pins 19–24 are no-connects. |
| FT231XS, not CH340C | DigiKey no longer stocks CH340C as a bare chip. Bonus: the FT231XS runs from 5 V VBUS and regulates its own 3.3 V I/O, which deleted a second LDO. |
| USB4110-GF-A, all SMD | Replaced the hybrid through-hole USB4105 so the whole board is one soldering technique. |
| Two LIR2032 in **parallel** | Keeps single-cell charging and a 3.0–4.2 V rail. See `power-and-charging.md`. |
| Six WS2812B, not eight | Each one idles at ~0.8 mA whether lit or not. On 80 mAh that is the dominant term. |
| No BOOT/RESET buttons | DTR#/RTS# drive a cross-coupled transistor pair, so esptool handles reset and boot mode. The only control is the power slide switch. |
| Direct 3.0–4.2 V pixel drive | A proper 5 V pixel rail needs a boost *and* a level shifter, and the current draw is beyond two coin cells. Capped at 10 % brightness the colour shift is barely visible. |
| `FT_3V3` kept off `+3.3V` | The bridge's internal regulator would otherwise back-drive the AP2112K whenever USB is plugged in with SW1 off. |
| CTS# tied to GND | Leaves hardware flow control permanently asserted so the port never stalls. |
| All surface mount, nothing smaller than 1206 | Every part can be placed with tweezers and heated from one side. The slide switch, the coin-cell retainers and the bulk electrolytic are the SMD variants of what the first draft had as through-hole, so there is no second soldering technique and no leads to clip on a board people will handle. |
| Body and wings drawn in silkscreen, not cut out | A 3 mm slot between body and wing closed up under the 0.8 mm fillet and would have blocked every trace heading out to the hindwing pixels. The copper stays one piece; the butterfly is drawn on top of it. |
| Label-driven schematic | The generated sheets connect by net name rather than long wire runs, so symbols can be rearranged without breaking the netlist. |

## Superseded

Amber-only single-colour LEDs, the pouch-cell variant and the XIAO-module
version were v1/v2 and are not part of this design. The pouch cell returns only
if the 5 V brightness upgrade is taken.
