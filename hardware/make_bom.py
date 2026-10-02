#!/usr/bin/env python3
"""
Builds docs/bom.csv from the actual schematic files, so the BOM cannot drift
away from the design.  Reference designators and values are read out of the
.kicad_sch files; the manufacturer part numbers and purchase links come from
the PARTS table below, keyed by value.
"""
import csv, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, "LED Butterfly")
OUT = os.path.join(HERE, "..", "docs", "bom.csv")
DK = "https://www.digikey.com/en/products/result?keywords="

# value -> (manufacturer part, package, note, digikey search)
PARTS = {
 "ESP32-C3FH4":         ("ESP32-C3FH4", "QFN-32", "Bare MCU, 4 MB internal flash", DK+"ESP32-C3FH4"),
 "MCP73831T-2ACI/OT":   ("MCP73831T-2ACI/OT", "SOT-23-5", "Li-ion charger, I_REG = 1000/R_PROG", DK+"MCP73831T-2ACI%2FOT"),
 "AP2112K-3.3TRG1":     ("AP2112K-3.3TRG1", "SOT-23-5", "3.3 V LDO, 600 mA", DK+"AP2112K-3.3TRG1"),
 "USBLC6-2SC6":         ("USBLC6-2SC6", "SOT-23-6", "USB ESD protection", DK+"USBLC6-2SC6"),
 "FT231XS-R":           ("FT231XS-R", "SSOP-20", "USB to UART bridge, runs from 5 V VBUS", DK+"FT231XS-R"),
 "MMBT2222A":           ("MMBT2222A", "SOT-23", "NPN, auto-reset cross", DK+"MMBT2222A"),
 "USB4110-GF-A":        ("USB4110-GF-A", "USB-C 16P", "All-SMD USB-C receptacle", DK+"USB4110-GF-A"),
 "WS2812B":             ("WS2812B", "PLCC-4 5050", "Addressable RGB LED", DK+"WS2812B"),
 "LIR2032":             ("LIR2032", "coin 20 mm", "RECHARGEABLE ONLY - a CR2032 here is a fire risk", DK+"LIR2032"),
 "Keystone 3034":       ("Keystone 3034", "SMT retainer", "Surface-mount retainer for the 20 mm cell", DK+"Keystone%203034"),
 "JS102011SAQN":        ("JS102011SAQN", "SPDT slide, SMD", "Power switch, pin 2 common", DK+"JS102011SAQN"),
 "LED_CHG":             ("any 1206 LED", "1206", "Charge status indicator", DK+"1206%20LED"),
 "TestPoint":           ("-", "1.5 mm pad", "Native-USB flashing fallback", ""),
 "470uF":               ("470 uF 10 V SMD aluminium, 8 mm can (Panasonic FK or similar)", "SMD 8x10.5",
                        "Bulk at the first pixel. 100-220 uF is ample at 10% brightness if you want a smaller can",
                        DK+"470uF%2010V%20SMD%20aluminum%20electrolytic"),
 "10k":   ("RC1206FR-0710KL", "1206", "", DK+"RC1206FR-0710KL"),
 "5.1k":  ("RC1206FR-075K1L", "1206", "USB-C CC pulldowns, mark the board as a sink", DK+"RC1206FR-075K1L"),
 "470":   ("RC1206FR-07470RL", "1206", "UART series and WS2812B data series", DK+"RC1206FR-07470RL"),
 "27":    ("RC1206FR-0727RL", "1206", "USB D+/D- series", DK+"RC1206FR-0727RL"),
 "24k":   ("RC1206FR-0724KL", "1206", "PROG: sets ~42 mA charge current", DK+"24k%20ohm%201206%201%25"),
 "1k":    ("RC1206FR-071KL", "1206", "Charge LED series", DK+"1k%20ohm%201206%201%25"),
 "100nF": ("C1206C104K5RACTU", "1206", "", DK+"C1206C104K5RACTU"),
 "1uF":   ("C1206C105K3RACTU", "1206", "", DK+"C1206C105K3RACTU"),
 "4.7uF": ("C1206C475K8RACTU", "1206", "", DK+"4.7uF%201206%20X5R%2025V"),
 "10uF":  ("CL31A106KAHNNNE", "1206", "", DK+"CL31A106KAHNNNE"),
 "12pF":  ("C1206C120J5GACTU", "1206 C0G", "Crystal load caps", DK+"C1206C120J5GACTU"),
}
# values that appear in the existing Microcontroller sheet under a vendor MPN
ALIAS = {"10kOhm": "10k", "0.1uF": "100nF", "12pF": "12pF",
         "ABM3B-40.000MHZ-10-1-U-T": "40 MHz crystal",
         "40.0MHz-Crystal": "40 MHz crystal", "40.0MHz-Crystral": "40 MHz crystal",
         "USB_D+": "TestPoint", "USB_D-": "TestPoint"}
PARTS["40 MHz crystal"] = ("ABM3B-40.000MHZ-10-1-U-T", "5032 4-pad",
                           "Hand-solderable 4-pad package", DK+"ABM3B-40.000MHZ-10-1-U-T")

SKIP_PREFIX = ("#PWR", "#FLG")

def scan():
    rows = collections.defaultdict(list)
    for f in sorted(os.listdir(PROJ)):
        if not f.endswith(".kicad_sch"):
            continue
        text = open(os.path.join(PROJ, f), encoding="utf-8", errors="replace").read()
        if "(lib_symbols" in text:
            text = text[text.index("(lib_symbols"):]
        for m in re.finditer(r'\(symbol\n\t\t\(lib_id "([^"]+)"(.*?)\n\t\)\n', text, re.S):
            blk = m.group(2)
            ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
            val = re.search(r'\(property "Value" "([^"]+)"', blk)
            if not (ref and val) or ref.group(1).startswith(SKIP_PREFIX):
                continue
            if m.group(1).startswith("power:"):
                continue
            v = ALIAS.get(val.group(1), val.group(1))
            rows[v].append(ref.group(1))
    return rows

def natural(r):
    m = re.match(r'([^\d]*)(\d*)(.*)', r)
    return (m.group(1), int(m.group(2) or 0), m.group(3)) if m else (r, 0, "")

def main():
    rows = scan()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    unknown = []
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Qty", "References", "Value", "Manufacturer part",
                    "Package", "Note", "DigiKey search"])
        for v in sorted(rows, key=lambda s: (-len(rows[s]), s)):
            refs = sorted(set(rows[v]), key=natural)
            mpn, pkg, note, link = PARTS.get(v, ("", "", "", ""))
            if v not in PARTS:
                unknown.append(v)
            w.writerow([len(refs), " ".join(refs), v, mpn, pkg, note, link])
    print(f"wrote {OUT} - {sum(len(set(r)) for r in rows.values())} parts, {len(rows)} line items")
    if unknown:
        print("  no PARTS entry for:", ", ".join(unknown))

if __name__ == "__main__":
    main()
