#!/usr/bin/env python3
"""
Draws docs/block-diagram.svg: how power and data move through the board.

Hand-written SVG so the output is deterministic and the file stays small enough
to sit in a README. Run it after changing the architecture, not before.
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "block-diagram.svg")
W, H = 1180, 500

INK = "#1b2127"; MUTE = "#5b6670"; LINE = "#c3ccd3"
PWR = "#b5651d"; DATA = "#1f6f8b"; CTRL = "#7a4fa3"; LED = "#1f7a5a"

# name: (x, y, w, h, title, subtitle, accent)
BOX = {
 "J1":  (18,  46, 140, 62, "J1 — USB-C", "USB4110-GF-A", DATA),
 "U4":  (232, 46, 128, 62, "U4 — ESD", "USBLC6-2SC6", DATA),
 "U5":  (434, 46, 150, 62, "U5 — USB/UART", "FT231XS", DATA),
 "QQ":  (696, 46, 140, 62, "Q1 · Q2", "auto-reset pair", CTRL),
 "U1":  (872, 180, 196, 120, "U1 — ESP32-C3FH4", "QFN-32 · 4 MB flash · 40 MHz", CTRL),
 "U2":  (18,  208, 140, 62, "U2 — charger", "MCP73831 · ~42 mA", PWR),
 "BT":  (232, 208, 148, 62, "BT1a · BT1b", "2 × LIR2032 in parallel", PWR),
 "SW":  (454, 208, 120, 62, "SW1", "power slide switch", PWR),
 "U3":  (648, 208, 150, 62, "U3 — LDO", "AP2112K-3.3", PWR),
 "LEDS":(232, 382, 566, 74, "D1 → D2 → D3 → D4 → D5 → D6", "6 × WS2812B, fed from VBAT_SW", LED),
}

# (from, to, label, colour, route)  route: "h" straight, or a list of points
EDGE = [
 ("J1", "U4", "D+ / D−", DATA),
 ("U4", "U5", "27 Ω", DATA),
 ("U5", "QQ", "DTR# · RTS#", CTRL),
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def box(k):
    x, y, w, h, t, s, c = BOX[k]
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" '
            f'fill="#ffffff" stroke="{c}" stroke-width="1.8"/>'
            f'<rect x="{x}" y="{y}" width="5" height="{h}" rx="2.5" fill="{c}"/>'
            f'<text x="{x+w/2}" y="{y+h/2-4}" text-anchor="middle" font-size="15" '
            f'font-weight="600" fill="{INK}">{esc(t)}</text>'
            f'<text x="{x+w/2}" y="{y+h/2+15}" text-anchor="middle" font-size="11.5" '
            f'fill="{MUTE}">{esc(s)}</text></g>')


def anchor(k, side):
    x, y, w, h, *_ = BOX[k]
    return {"l": (x, y + h / 2), "r": (x + w, y + h / 2),
            "t": (x + w / 2, y), "b": (x + w / 2, y + h)}[side]


def arrow(pts, label, colour, lx=None, ly=None, dash=False):
    d = "M " + " L ".join(f"{x},{y}" for x, y in pts)
    da = ' stroke-dasharray="6 4"' if dash else ""
    mid = pts[len(pts) // 2]
    tx = lx if lx is not None else (pts[0][0] + pts[-1][0]) / 2
    ty = ly if ly is not None else min(p[1] for p in pts) - 8
    return (f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="2"{da} '
            f'marker-end="url(#a{colour[1:]})"/>'
            f'<text x="{tx}" y="{ty}" text-anchor="middle" font-size="12" '
            f'font-weight="600" fill="{colour}">{esc(label)}</text>')


def main():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'width="{W}" height="{H}" font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">',
             f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    for c in (PWR, DATA, CTRL, LED):
        parts.append(f'<defs><marker id="a{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
                     f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                     f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker></defs>')

    # ---- straight runs along the top (data) and middle (power)
    for a, b, lab, col in EDGE:
        p0 = anchor(a, "r"); p1 = anchor(b, "l")
        parts.append(arrow([p0, p1], lab, col,
                           lx=(p0[0] + p1[0]) / 2, ly=p0[1] - 13))

    # VBUS down from the connector into the charger
    j = anchor("J1", "b"); u2 = anchor("U2", "t")
    parts.append(arrow([(j[0], j[1]), (j[0], u2[1] - 20), u2],
                       "VBUS 5 V", PWR, lx=j[0] + 46, ly=(j[1] + u2[1]) / 2 + 4))
    # VBUS also feeds the bridge
    u5t = anchor("U5", "t")
    parts.append(arrow([(j[0] + 40, 46), (j[0] + 40, 18), (u5t[0], 18), u5t],
                       "VBUS 5 V", PWR, lx=300, ly=14))

    # power chain
    for a, b, lab in (("U2", "BT", "VBAT"), ("BT", "SW", "VBAT"),
                      ("SW", "U3", "VBAT_SW"), ("U3", "U1", "+3.3 V")):
        p0 = anchor(a, "r"); p1 = anchor(b, "l")
        parts.append(arrow([p0, p1], lab, PWR,
                           lx=(p0[0] + p1[0]) / 2, ly=p0[1] - 13))

    # auto-reset into the MCU
    q = anchor("QQ", "r"); u1t = anchor("U1", "t")
    parts.append(arrow([q, (u1t[0], q[1]), u1t], "CHIP_ENABLE · BOOT", CTRL,
                       lx=u1t[0] + 2, ly=q[1] - 10))
    # UART, routed over the transistor block
    u5r = anchor("U5", "r")
    parts.append(arrow([(u5r[0] - 40, 108), (u5r[0] - 40, 148), (u1t[0] - 62, 148),
                        (u1t[0] - 62, 180)], "UART_TX / UART_RX  (470 Ω)", DATA,
                       lx=640, ly=142))

    # switched rail down to the pixels
    swb = anchor("SW", "b"); ledt = (BOX["LEDS"][0] + 120, BOX["LEDS"][1])
    parts.append(arrow([swb, (swb[0], 336), (ledt[0], 336), ledt], "VBAT_SW", PWR,
                       lx=swb[0] - 52, ly=332))
    # pixel data from the MCU
    u1b = anchor("U1", "b"); ledr = (BOX["LEDS"][0] + BOX["LEDS"][2], BOX["LEDS"][1] + 36)
    parts.append(arrow([u1b, (u1b[0], 419), ledr], "LED_DATA (GPIO4) → 470 Ω", LED,
                       lx=u1b[0] - 128, ly=356))

    for k in BOX:
        parts.append(box(k))

    # legend
    leg = [("power", PWR), ("USB / UART data", DATA), ("control", CTRL), ("pixel data", LED)]
    x = 18
    for name, c in leg:
        parts.append(f'<rect x="{x}" y="{H-26}" width="22" height="4" rx="2" fill="{c}"/>'
                     f'<text x="{x+28}" y="{H-19}" font-size="12" fill="{MUTE}">{esc(name)}</text>')
        x += 36 + len(name) * 7
    parts.append(f'<text x="{W-18}" y="{H-19}" text-anchor="end" font-size="11.5" fill="{MUTE}">'
                 f'The charger sits on the battery side of SW1, so the board charges '
                 f'with the switch off</text>')
    parts.append("</svg>")
    open(OUT, "w").write("\n".join(parts) + "\n")
    print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
