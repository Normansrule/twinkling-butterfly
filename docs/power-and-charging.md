# Power and charging

## The rails

| Rail | Source | Range | Feeds |
|---|---|---|---|
| `VBUS` | USB-C | 5 V | MCP73831 charger, FT231XS VCC, charge LED |
| `VBAT` | the coin cells | 3.0 – 4.2 V | charger output, SW1 input |
| `VBAT_SW` | `VBAT` through SW1 | 3.0 – 4.2 V | AP2112K input, WS2812B chain |
| `+3.3V` | AP2112K | 3.3 V | ESP32-C3FH4 only |

The charger sits on the battery side of SW1 on purpose, so the board charges
with the switch off. The ESP32 sits behind SW1, so **SW1 must be on to flash**.

The FT231XS makes its own 3.3 V internally (`3V3OUT`, pin 13) and that node is
kept separate from `+3.3V` as the net `FT_3V3`. Tying them together would let
the bridge back-drive the regulator whenever USB is plugged in with SW1 off.

## Why two LIR2032 in parallel

A LIR2032 is a rechargeable 3.6 V lithium coin cell — same 20 mm format as the
familiar CR2032, different chemistry. Two in parallel give roughly 80 mAh and
can sustain about 40–60 mA before the voltage sags enough to brown out the
regulator. In **parallel**, not series, because:

* the rail stays 3.0–4.2 V, which a single-cell charger like the MCP73831 can
  charge directly and the AP2112K can regulate down from;
* capacity adds while the charge profile stays a one-cell problem — no
  balancing, no stacked protection.

Use the same brand and batch, and replace them as a pair. A tired cell
paralleled with a fresh one just drags the fresh one down.

The holders are Keystone 3034 retainers, which are surface mount — the clip
solders to the board and the board's own pad is the negative contact. That keeps
the build all-SMD and puts the cells flat against the back of the wings.

> **The retainers are LIR-only.** A CR2032 is primary (non-rechargeable). Put one
> in this board, plug in USB, and the charger will drive current into a cell
> that cannot take it — vent, leak or fire. Label both holders on the
> silkscreen and again on the back of the enclosure.

## Setting the charge current

The MCP73831 sets its fast-charge current from one resistor:

```
I_REG (mA) = 1000 / R_PROG (kΩ)
```

| R_PROG | I_REG | Use |
|---|---|---|
| **24 kΩ** | **~42 mA** | the coin-cell build — about 0.5 C for the 80 mAh pair |
| 10 kΩ | 100 mA | only if you move to a larger cell |
| 2 kΩ | 500 mA | the 500 mAh pouch-cell variant |

R14 is the PROG resistor and it returns to GND, not to a rail.

A full charge from flat takes roughly 2.5 hours at 42 mA. D7 lights while
charging and goes out when the charger tapers off — it is driven from `VBUS`
through R13 (1 kΩ) into the open-drain `STAT` pin, so it only works with USB
connected.

## Runtime

Six WS2812Bs idle at about 0.8 mA each just to keep their controllers alive,
which is 4.8 mA before a single LED is lit. The firmware adds roughly 5–8 mA
average: brightness capped near 10 %, never more than three pixels above zero,
and the CPU in light sleep between frames.

That lands around 12 mA average, so **3–4 hours per charge**. The sketch deep
sleeps after 8 hours regardless, so a butterfly left switched on does not
deep-discharge its cells.

## If you want it brighter

WS2812Bs are noticeably brighter and truer at 5 V; below about 3.5 V the blue
and green dice fade faster than the red, so colours drift warm as the cells
empty. Driving them properly at 5 V needs a boost converter (MCP1640) *and* a
level shifter (SN74AHCT1G125) because a 5 V pixel wants data high at ≥ 3.5 V.

The honest arithmetic: six pixels at 40 % brightness is roughly 290 mA at 5 V,
which is over 450 mA out of the battery through the boost. Two LIR2032s cannot
do that. The upgrade only makes sense paired with a 500 mAh pouch cell and
R_PROG changed to 2 kΩ. Footprints for the boost, the buffer and a JST
connector can be laid out and left unpopulated on coin-cell builds — one board,
both personalities. See `docs/handoff-2026-08-31.md` for the full part list.
