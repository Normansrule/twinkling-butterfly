#!/usr/bin/env python3
"""
Generates the Twinkling Butterfly schematic sheets, the project symbol
library and the board outline file, in KiCad 10 format.

The sheets are label-driven: every device pin gets a short stub wire and a
label (local, hierarchical, or a power symbol).  Connectivity is therefore
defined entirely by net name, which keeps the generated netlist exact and
avoids fragile point-to-point routing.  Open the project and run ERC; then
rearrange symbols freely -- the labels travel with their pins.

Run from this directory:  python3 generate_sheets.py
"""
import hashlib, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("BUTTERFLY_SRC", "")   # optional: the original project, for first import
OUT = os.path.join(HERE, "LED Butterfly")
PROJECT = "LED Butterfly"
ROOT_UUID = "0990cd1a-6f2f-42c4-8ff0-1145230920ec"   # must match the existing root
MCU_SHEET_UUID = "d7a52ce2-71b1-4248-9f7c-5195963708f6"  # existing Microcontroller instance

VERSION_HDR = ('(kicad_sch\n\t(version 20260306)\n\t(generator "eeschema")\n'
               '\t(generator_version "10.0")\n\t(uuid "{uuid}")\n\t(paper "A3")\n')

_counter = [0]
def uid(tag=""):
    """Deterministic UUIDs so re-running produces a byte-identical file."""
    _counter[0] += 1
    h = hashlib.sha1(f"butterfly::{tag}::{_counter[0]}".encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-4{h[13:16]}-a{h[17:20]}-{h[20:32]}"

# --------------------------------------------------------------- s-expr bits
def eff(size=1.27, justify=None, hide=False):
    j = f"\n\t\t\t(justify {justify})" if justify else ""
    return (f"\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n\t\t\t)"
            f"{j}\n\t\t)")

def prop(name, value, x, y, rot=0, hide=False, indent=2):
    t = "\t" * indent
    h = f"\n{t}\t(hide yes)" if hide else ""
    v = value.replace("\\", "\\\\").replace('"', '\\"')
    return (f'\n{t}(property "{name}" "{v}"\n{t}\t(at {x:.4f} {y:.4f} {rot})'
            f'{h}\n{t}\t(show_name no)\n{t}\t(do_not_autoplace no)\n{t}\t(effects\n'
            f'{t}\t\t(font\n{t}\t\t\t(size 1.27 1.27)\n{t}\t\t)\n{t}\t)\n{t})')

# ------------------------------------------------------------ symbol library
class PinDef:
    def __init__(self, num, name, etype, x, y, ang, length=2.54):
        self.num, self.name, self.etype = num, name, etype
        self.x, self.y, self.ang, self.length = x, y, ang, length

def box_symbol(libname, ref_prefix, value, pins, w, h, footprint="",
               desc="", keywords="", hide_pin_names=False, power=False):
    """Build a rectangular KiCad symbol definition."""
    body = (f'\t\t(rectangle\n\t\t\t(start {-w/2:.2f} {h/2:.2f})\n'
            f'\t\t\t(end {w/2:.2f} {-h/2:.2f})\n'
            f'\t\t\t(stroke\n\t\t\t\t(width 0.254)\n\t\t\t\t(type default)\n\t\t\t)\n'
            f'\t\t\t(fill\n\t\t\t\t(type background)\n\t\t\t)\n\t\t)')
    pin_txt = []
    for p in pins:
        pin_txt.append(
            f'\t\t(pin {p.etype} line\n\t\t\t(at {p.x:.2f} {p.y:.2f} {p.ang})\n'
            f'\t\t\t(length {p.length})\n'
            f'\t\t\t(name "{p.name}"\n\t\t\t\t(effects\n\t\t\t\t\t(font\n'
            f'\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t)\n'
            f'\t\t\t(number "{p.num}"\n\t\t\t\t(effects\n\t\t\t\t\t(font\n'
            f'\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t)\n\t\t\t\t)\n\t\t\t)\n\t\t)')
    hidden_names = "\n\t\t(hide yes)" if hide_pin_names else ""
    pwr = "\n\t\t(power)" if power else ""
    return (f'\t(symbol "{libname}"'
            f'{pwr}'
            f'\n\t\t(pin_numbers\n\t\t\t(offset 0.508)\n\t\t)'
            f'\n\t\t(pin_names\n\t\t\t(offset 0.508){hidden_names}\n\t\t)'
            f'\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)'
            + prop("Reference", ref_prefix, 0, h/2 + 2.54, indent=2)
            + prop("Value", value, 0, -h/2 - 2.54, indent=2)
            + prop("Footprint", footprint, 0, 0, hide=True, indent=2)
            + prop("Datasheet", "", 0, 0, hide=True, indent=2)
            + prop("Description", desc, 0, 0, hide=True, indent=2)
            + f'\n\t\t(symbol "{libname.split(":")[-1]}_0_1"\n{body}\n\t\t)'
            + f'\n\t\t(symbol "{libname.split(":")[-1]}_1_1"\n'
            + "\n".join(pin_txt) + "\n\t\t)\n\t)")

P = PinDef
NEW_SYMBOLS = {
 "R_1206": box_symbol("R_1206", "R", "R",
    [P("1", "~", "passive", -5.08, 0, 0), P("2", "~", "passive", 5.08, 0, 180)],
    5.08, 2.03, "Resistor_SMD:R_1206_3216Metric", "Resistor, 1206 (3216 metric)", hide_pin_names=True),
 "C_1206": box_symbol("C_1206", "C", "C",
    [P("1", "~", "passive", -5.08, 0, 0), P("2", "~", "passive", 5.08, 0, 180)],
    5.08, 2.03, "Capacitor_SMD:C_1206_3216Metric", "Ceramic capacitor, 1206 (3216 metric)", hide_pin_names=True),
 "C_POL_SMD": box_symbol("C_POL_SMD", "C", "CP",
    [P("1", "+", "passive", -5.08, 0, 0), P("2", "-", "passive", 5.08, 0, 180)],
    5.08, 3.0, "Capacitor_SMD:CP_Elec_8x10.5",
    "Polarised aluminium electrolytic, SMD 8 mm can. Two large pads, easy by hand"),
 "LED_1206": box_symbol("LED_1206", "D", "LED",
    [P("1", "A", "passive", -5.08, 0, 0), P("2", "K", "passive", 5.08, 0, 180)],
    5.08, 2.54, "LED_SMD:LED_1206_3216Metric", "LED, 1206. Pin 1 anode, pin 2 cathode"),
 "MCP73831": box_symbol("MCP73831", "U", "MCP73831T-2ACI/OT",
    [P("1", "STAT", "open_collector", -10.16, 5.08, 0),
     P("4", "VDD", "power_in", -10.16, 0, 0),
     P("5", "PROG", "input", -10.16, -5.08, 0),
     P("3", "VBAT", "power_out", 10.16, 2.54, 180),
     P("2", "VSS", "power_in", 10.16, -5.08, 180)],
    15.24, 15.24, "Package_TO_SOT_SMD:SOT-23-5",
    "Single-cell Li-Ion/Li-Po charge controller, SOT-23-5. I_REG[mA] = 1000 / R_PROG[kOhm]"),
 "AP2112K-3.3": box_symbol("AP2112K-3.3", "U", "AP2112K-3.3TRG1",
    [P("1", "VIN", "power_in", -10.16, 2.54, 0),
     P("3", "EN", "input", -10.16, -2.54, 0),
     P("5", "VOUT", "power_out", 10.16, 2.54, 180),
     P("4", "NC", "no_connect", 10.16, -2.54, 180),
     P("2", "GND", "power_in", 0, -10.16, 90)],
    15.24, 12.7, "Package_TO_SOT_SMD:SOT-23-5", "600 mA LDO regulator, fixed 3.3 V, SOT-23-5"),
 "WS2812B": box_symbol("WS2812B", "D", "WS2812B",
    [P("4", "DIN", "input", -10.16, 0, 0),
     P("1", "VDD", "power_in", 0, 7.62, 270),
     P("3", "VSS", "power_in", 0, -7.62, 90),
     P("2", "DOUT", "output", 10.16, 0, 180)],
    12.7, 10.16, "LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm",
    "Addressable RGB LED, PLCC-4 5050. Pin1 VDD, pin2 DOUT, pin3 VSS, pin4 DIN"),
 "SW_SPDT": box_symbol("SW_SPDT", "SW", "JS102011SAQN",
    [P("1", "A", "passive", -7.62, 2.54, 0),
     P("2", "COM", "passive", -7.62, -2.54, 0),
     P("3", "B", "passive", 7.62, 2.54, 180)],
    10.16, 10.16, "Button_Switch_SMD:SW_SPDT_CK-JS102011SAQN",
    "SPDT slide switch, surface mount. Pin 2 is the common terminal"),
 "BATT_HOLDER": box_symbol("BATT_HOLDER", "BT", "LIR2032",
    [P("1", "+", "passive", -7.62, 2.54, 0), P("2", "-", "passive", -7.62, -2.54, 0)],
    10.16, 10.16, "Battery:BatteryHolder_Keystone_3034_1x20mm",
    "LIR2032 rechargeable coin cell, Keystone 3034 SMT retainer. LIR ONLY - never fit a CR2032"),
 "TESTPOINT": box_symbol("TESTPOINT", "TP", "TestPoint",
    [P("1", "~", "passive", -5.08, 0, 0)],
    2.54, 2.54, "TestPoint:TestPoint_Pad_1.5x1.5mm", "Bare pad for a probe or flying lead"),
 "PWR_FLAG": box_symbol("PWR_FLAG", "#FLG", "PWR_FLAG",
    [P("1", "pwr", "power_out", 0, -2.54, 90)],
    2.54, 2.54, "", "Marks a net as externally powered so ERC stops asking", power=True),
}

def write_symbol_lib(path):
    body = "\n".join(NEW_SYMBOLS[k] for k in sorted(NEW_SYMBOLS))
    open(path, "w", encoding="utf-8").write(
        '(kicad_symbol_lib\n\t(version 20260306)\n\t(generator "butterfly-generator")\n'
        '\t(generator_version "10.0")\n' + body + "\n)\n")

# --------------------------------------------------------- sheet construction
STUB = 2.54
DIRS = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}
LBL_ROT = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}

class Part:
    def __init__(self, lib_id, ref, value, x, y, pins, footprint="", fields=None):
        self.lib_id, self.ref, self.value = lib_id, ref, value
        self.x, self.y, self.pins = x, y, pins       # pins: {num: (px, py, ang)}
        self.footprint, self.fields = footprint, fields or {}
        self.uuid = uid(ref)
    def at(self, num):
        px, py, _ = self.pins[num]
        return (self.x + px, self.y - py)
    def dirn(self, num):
        return DIRS[int(self.pins[num][2]) % 360]

class Sheet:
    def __init__(self, name, filename, sheet_uuid=None):
        self.name, self.filename = name, filename
        self.uuid = sheet_uuid or uid("sheet" + name)
        self.file_uuid = uid("file" + name)
        self.pwr_base = 100
        self.parts, self.wires, self.labels, self.hlabels = [], [], [], []
        self.glabels, self.nocon, self.junctions, self.powers = [], [], [], []
        self.lib_ids = set()

    def add(self, part):
        self.parts.append(part); self.lib_ids.add(part.lib_id); return part

    def _stub(self, part, num):
        x, y = part.at(num); dx, dy = part.dirn(num)
        ex, ey = x + dx * STUB, y + dy * STUB
        self.wires.append(((x, y), (ex, ey)))
        return (ex, ey), (dx, dy)

    def label(self, part, num, net, kind="local"):
        (ex, ey), d = self._stub(part, num)
        rot = LBL_ROT[d]
        if kind == "local":   self.labels.append((net, ex, ey, rot))
        elif kind == "hier":  self.hlabels.append((net, ex, ey, rot))
        elif kind == "global":self.glabels.append((net, ex, ey, rot))
        elif kind == "power":
            pw = Part("power:" + net, "#PWR", net, ex, ey, {"1": (0, 0, 0)})
            pw.rot = {(-1, 0): 270, (1, 0): 90, (0, 1): 0, (0, -1): 180}[d]
            self.powers.append(pw); self.lib_ids.add(pw.lib_id)

    def nc(self, part, num):
        x, y = part.at(num); self.nocon.append((x, y))

    # ----------------------------------------------------------- serialisation
    def render(self, lib_defs):
        out = [VERSION_HDR.format(uuid=self.file_uuid)]
        out.append("\t(lib_symbols")
        for lid in sorted(self.lib_ids):
            out.append(lib_defs[lid])
        out.append("\t)")
        for (a, b) in self.wires:
            out.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {a[0]:.4f} {a[1]:.4f}) (xy {b[0]:.4f} {b[1]:.4f})\n\t\t)\n'
                       f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{uid("w")}")\n\t)')
        for (x, y) in self.junctions:
            out.append(f'\t(junction\n\t\t(at {x:.4f} {y:.4f})\n\t\t(diameter 0)\n'
                       f'\t\t(color 0 0 0 0)\n\t\t(uuid "{uid("j")}")\n\t)')
        for (x, y) in self.nocon:
            out.append(f'\t(no_connect\n\t\t(at {x:.4f} {y:.4f})\n\t\t(uuid "{uid("nc")}")\n\t)')
        for (net, x, y, rot) in self.labels:
            out.append(f'\t(label "{net}"\n\t\t(at {x:.4f} {y:.4f} {rot})\n\t\t(effects\n\t\t\t(font\n'
                       f'\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n'
                       f'\t\t(uuid "{uid("l")}")\n\t)')
        for (net, x, y, rot) in self.glabels:
            out.append(f'\t(global_label "{net}"\n\t\t(shape bidirectional)\n\t\t(at {x:.4f} {y:.4f} {rot})\n'
                       f'\t\t(fields_autoplaced yes)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n'
                       f'\t\t\t)\n\t\t\t(justify left)\n\t\t)\n\t\t(uuid "{uid("g")}")'
                       + prop("Intersheetrefs", "${INTERSHEET_REFS}", x, y, hide=True, indent=2)
                       + "\n\t)")
        for (net, x, y, rot) in self.hlabels:
            out.append(f'\t(hierarchical_label "{net}"\n\t\t(shape bidirectional)\n\t\t(at {x:.4f} {y:.4f} {rot})\n'
                       f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left)\n'
                       f'\t\t)\n\t\t(uuid "{uid("h")}")\n\t)')
        pwr_n = [self.pwr_base]
        for p in self.parts + self.powers:
            out.append(self._symbol(p, pwr_n))
        out.append("\t(embedded_fonts no)\n)")
        return "\n".join(out) + "\n"

    def _symbol(self, p, pwr_n):
        is_pwr = p.lib_id.startswith("power:")
        if is_pwr:
            pwr_n[0] += 1
            ref = f"#PWR{pwr_n[0]:03d}"
        else:
            ref = p.ref
        rot = getattr(p, "rot", 0)
        s = [f'\t(symbol\n\t\t(lib_id "{p.lib_id}")\n\t\t(at {p.x:.4f} {p.y:.4f} {rot})\n'
             f'\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n'
             f'\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(fields_autoplaced yes)\n'
             f'\t\t(uuid "{p.uuid}")']
        s.append(prop("Reference", ref, p.x, p.y - 6.35, hide=is_pwr))
        s.append(prop("Value", p.value, p.x, p.y + 6.35))
        s.append(prop("Footprint", p.footprint, p.x, p.y, hide=True))
        s.append(prop("Datasheet", "", p.x, p.y, hide=True))
        s.append(prop("Description", "", p.x, p.y, hide=True))
        for k, v in p.fields.items():
            s.append(prop(k, v, p.x, p.y, hide=True))
        for num in p.pins:
            s.append(f'\n\t\t(pin "{num}"\n\t\t\t(uuid "{uid("p")}")\n\t\t)')
        s.append(f'\n\t\t(instances\n\t\t\t(project "{PROJECT}"\n'
                 f'\t\t\t\t(path "/{ROOT_UUID}/{self.uuid}"\n'
                 f'\t\t\t\t\t(reference "{ref}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)')
        s.append("\n\t)")
        return "".join(s)

# ------------------------------------------------------- harvest lib_symbols
def _sexp_blocks(text, head):
    """Yield top-level (head ...) blocks from a kicad file as raw strings."""
    for m in re.finditer(re.escape(head), text):
        i = m.start()
        if i and text[i-1] not in "\n\t ":
            continue
        depth = 0; j = i
        while j < len(text):
            c = text[j]
            if c == '"':
                j += 1
                while text[j] != '"':
                    j += 2 if text[j] == "\\" else 1
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    yield text[i:j+1]; break
            j += 1

def harvest(paths):
    """Return {lib_id: definition_text} and {lib_id: {pin: (x, y, ang)}}."""
    defs, pins = {}, {}
    for path in paths:
        text = open(path, encoding="utf-8", errors="replace").read()
        libsec = next(_sexp_blocks(text, "(lib_symbols"), None)
        if not libsec:
            continue
        for blk in _sexp_blocks(libsec, "(symbol "):
            name = re.match(r'\(symbol\s+"([^"]+)"', blk).group(1)
            if ":" not in name:
                continue
            defs[name] = "\t" + blk.replace("\n\t\t", "\n\t\t").rstrip()
            pm = {}
            for pb in _sexp_blocks(blk, "(pin "):
                at = re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\)', pb)
                num = re.search(r'\(number\s+"([^"]+)"', pb)
                if at and num:
                    pm[num.group(1)] = (float(at.group(1)), float(at.group(2)), float(at.group(3)))
            pins[name] = pm
    return defs, pins

# ------------------------------------------------------------------- sheets
def build_usb_uart(defs, pins):
    sh = Sheet("USB_UART", "USB_UART.kicad_sch"); sh.pwr_base = 100
    K = "Kicad-Custom-Components:"; B = "butterfly:"
    def mk(lib, ref, val, x, y, fp="", fields=None):
        return sh.add(Part(lib, ref, val, x, y, pins[lib], fp, fields))

    J1 = mk(K+"USB4110GFA", "J1", "USB4110-GF-A", 60, 110)
    U4 = mk(K+"USBLC6-2SC6", "U4", "USBLC6-2SC6", 125, 105)
    U5 = mk(K+"FT231XS-R", "U5", "FT231XS-R", 200, 105)
    Q1 = mk(B+"MMBT2222A" if B+"MMBT2222A" in pins else K+"MMBT2222A", "Q1", "MMBT2222A", 285, 90)
    Q2 = mk(K+"MMBT2222A", "Q2", "MMBT2222A", 285, 135)
    R  = lambda ref, val, x, y: mk(B+"R_1206", ref, val, x, y, "Resistor_SMD:R_1206_3216Metric")
    C  = lambda ref, val, x, y: mk(B+"C_1206", ref, val, x, y, "Capacitor_SMD:C_1206_3216Metric")
    R5  = R("R5", "5.1k", 60, 160);  R6  = R("R6", "5.1k", 60, 175)
    R11 = R("R11", "27",  160, 95);  R12 = R("R12", "27",  160, 110)
    R9  = R("R9", "470",  250, 100); R10 = R("R10", "470", 250, 115)
    R7  = R("R7", "10k",  250, 75);  R8  = R("R8", "10k",  250, 150)
    C13 = C("C13", "4.7uF", 100, 165); C14 = C("C14", "100nF", 100, 180)
    C15 = C("C15", "100nF", 160, 180)

    # --- USB-C receptacle
    for p in ("A4/B9", "B4/A9"):          sh.label(J1, p, "VBUS", "global")
    for p in ("A1/B12", "B1/A12", "S1", "S2", "S3", "S4"): sh.label(J1, p, "GND", "power")
    sh.label(J1, "A5", "CC1"); sh.label(R5, "1", "CC1"); sh.label(R5, "2", "GND", "power")
    sh.label(J1, "B5", "CC2"); sh.label(R6, "1", "CC2"); sh.label(R6, "2", "GND", "power")
    sh.label(J1, "A6", "USB_DP_CONN"); sh.label(J1, "B6", "USB_DP_CONN")
    sh.label(J1, "A7", "USB_DM_CONN"); sh.label(J1, "B7", "USB_DM_CONN")
    sh.nc(J1, "A8"); sh.nc(J1, "B8")
    # --- ESD protection
    sh.label(U4, "1", "USB_DP_CONN"); sh.label(U4, "3", "USB_DM_CONN")
    sh.label(U4, "5", "VBUS", "global"); sh.label(U4, "2", "GND", "power")
    sh.label(U4, "6", "USB_DP_P");  sh.label(R11, "1", "USB_DP_P"); sh.label(R11, "2", "USB_DP")
    sh.label(U4, "4", "USB_DM_P");  sh.label(R12, "1", "USB_DM_P"); sh.label(R12, "2", "USB_DM")
    # --- FT231XS
    sh.label(U5, "11", "USB_DP"); sh.label(U5, "12", "USB_DM")
    sh.label(U5, "15", "VBUS", "global")
    sh.label(U5, "6", "GND", "power"); sh.label(U5, "16", "GND", "power")
    for p in ("13", "3", "14"):  sh.label(U5, p, "FT_3V3")
    sh.label(U5, "9", "GND", "power")                      # CTS# asserted
    for p in ("5", "7", "8", "10", "17", "18", "19"): sh.nc(U5, p)
    sh.label(U5, "20", "FT_TXD"); sh.label(R9, "1", "FT_TXD"); sh.label(R9, "2", "UART_RX", "hier")
    sh.label(U5, "4", "FT_RXD");  sh.label(R10, "1", "FT_RXD"); sh.label(R10, "2", "UART_TX", "hier")
    sh.label(U5, "1", "DTR"); sh.label(U5, "2", "RTS")
    # native-USB test pads: the backup flashing path off GPIO18/19
    TP1 = mk(B+"TESTPOINT", "TP1", "USB_D+", 330, 95, "TestPoint:TestPoint_Pad_1.5x1.5mm")
    TP2 = mk(B+"TESTPOINT", "TP2", "USB_D-", 330, 110, "TestPoint:TestPoint_Pad_1.5x1.5mm")
    sh.label(TP1, "1", "USB_DATA+", "hier"); sh.label(TP2, "1", "USB_DATA-", "hier")
    # --- decoupling
    for c in (C13, C14):
        sh.label(c, "1", "VBUS", "global"); sh.label(c, "2", "GND", "power")
    sh.label(C15, "1", "FT_3V3"); sh.label(C15, "2", "GND", "power")
    # --- auto-reset cross: Q1 pulls CHIP_ENABLE, Q2 pulls BOOT
    sh.label(R7, "1", "DTR"); sh.label(R7, "2", "Q1_BASE")
    sh.label(Q1, "1", "Q1_BASE"); sh.label(Q1, "2", "RTS"); sh.label(Q1, "3", "CHIP_ENABLE", "hier")
    sh.label(R8, "1", "RTS"); sh.label(R8, "2", "Q2_BASE")
    sh.label(Q2, "1", "Q2_BASE"); sh.label(Q2, "2", "DTR"); sh.label(Q2, "3", "BOOT", "hier")
    return sh

def build_power(defs, pins):
    sh = Sheet("Power", "Power.kicad_sch"); sh.pwr_base = 200
    B = "butterfly:"
    def mk(lib, ref, val, x, y, fp="", fields=None):
        return sh.add(Part(lib, ref, val, x, y, pins[lib], fp, fields))
    R = lambda ref, val, x, y: mk(B+"R_1206", ref, val, x, y, "Resistor_SMD:R_1206_3216Metric")
    C = lambda ref, val, x, y: mk(B+"C_1206", ref, val, x, y, "Capacitor_SMD:C_1206_3216Metric")

    U2  = mk(B+"MCP73831", "U2", "MCP73831T-2ACI/OT", 95, 80, "Package_TO_SOT_SMD:SOT-23-5")
    U3  = mk(B+"AP2112K-3.3", "U3", "AP2112K-3.3TRG1", 230, 80, "Package_TO_SOT_SMD:SOT-23-5")
    SW1 = mk(B+"SW_SPDT", "SW1", "JS102011SAQN", 165, 80, "Button_Switch_SMD:SW_SPDT_CK-JS102011SAQN")
    BTa = mk(B+"BATT_HOLDER", "BT1a", "LIR2032", 95, 140, "Battery:BatteryHolder_Keystone_3034_1x20mm")
    BTb = mk(B+"BATT_HOLDER", "BT1b", "LIR2032", 95, 165, "Battery:BatteryHolder_Keystone_3034_1x20mm")
    D7  = mk(B+"LED_1206", "D7", "LED_CHG", 60, 55, "LED_SMD:LED_1206_3216Metric")
    R13 = R("R13", "1k",  30, 55)
    R14 = R("R14", "24k", 95, 110)
    C16 = C("C16", "4.7uF", 30, 95); C17 = C("C17", "4.7uF", 135, 95)
    C18 = C("C18", "1uF", 200, 110); C19 = C("C19", "1uF", 265, 110)

    # charge-status LED: VBUS -> 1k -> LED -> STAT (open drain, sinks when charging)
    sh.label(R13, "1", "VBUS", "global"); sh.label(R13, "2", "CHG_A")
    sh.label(D7, "1", "CHG_A");           sh.label(D7, "2", "STAT")
    sh.label(U2, "1", "STAT")
    sh.label(U2, "4", "VBUS", "global"); sh.label(U2, "2", "GND", "power")
    sh.label(U2, "3", "VBAT")
    sh.label(U2, "5", "PROG");  sh.label(R14, "1", "PROG"); sh.label(R14, "2", "GND", "power")
    sh.label(C16, "1", "VBUS", "global"); sh.label(C16, "2", "GND", "power")
    sh.label(C17, "1", "VBAT");           sh.label(C17, "2", "GND", "power")
    # cells in parallel, charger stays on the battery side of the switch
    for bt in (BTa, BTb):
        sh.label(bt, "1", "VBAT"); sh.label(bt, "2", "GND", "power")
    # slide switch: common feeds the load rail
    sh.label(SW1, "1", "VBAT"); sh.label(SW1, "2", "VBAT_SW", "global"); sh.nc(SW1, "3")
    # LDO
    sh.label(U3, "1", "VBAT_SW", "global"); sh.label(U3, "3", "VBAT_SW", "global")
    sh.label(U3, "2", "GND", "power");      sh.label(U3, "5", "+3.3V", "power"); sh.nc(U3, "4")
    sh.label(C18, "1", "VBAT_SW", "global"); sh.label(C18, "2", "GND", "power")
    sh.label(C19, "1", "+3.3V", "power");    sh.label(C19, "2", "GND", "power")
    # power flags so ERC knows these rails are driven
    for i, net in enumerate(("VBUS", "VBAT", "VBAT_SW")):
        f = mk(B+"PWR_FLAG", f"#FLG{i:02d}", "PWR_FLAG", 300, 50 + i * 15)
        sh.label(f, "1", net, "global" if net != "VBAT" else "local")
    return sh

def build_led(defs, pins):
    sh = Sheet("LED", "LED.kicad_sch"); sh.pwr_base = 300
    B = "butterfly:"
    def mk(lib, ref, val, x, y, fp=""):
        return sh.add(Part(lib, ref, val, x, y, pins[lib], fp))
    R15 = mk(B+"R_1206", "R15", "470", 40, 70, "Resistor_SMD:R_1206_3216Metric")
    sh.label(R15, "1", "LED_DATA", "hier"); sh.label(R15, "2", "PIX_D0")
    C26 = mk(B+"C_POL_SMD", "C26", "470uF", 40, 160, "Capacitor_SMD:CP_Elec_8x10.5")
    sh.label(C26, "1", "VBAT_SW", "global"); sh.label(C26, "2", "GND", "power")
    for i in range(6):
        x = 80 + i * 40
        d = mk(B+"WS2812B", f"D{i+1}", "WS2812B", x, 70,
               "LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm")
        sh.label(d, "4", f"PIX_D{i}")
        if i == 5:
            sh.nc(d, "2")          # last DOUT in the chain goes nowhere
        else:
            sh.label(d, "2", f"PIX_D{i+1}")
        sh.label(d, "1", "VBAT_SW", "global")
        sh.label(d, "3", "GND", "power")
        c = mk(B+"C_1206", f"C{20+i}", "100nF", x, 120, "Capacitor_SMD:C_1206_3216Metric")
        sh.label(c, "1", "VBAT_SW", "global"); sh.label(c, "2", "GND", "power")
    return sh

# --------------------------------------------------------------- root sheet
ROOT_SHEETS = [
    # (name, filename, uuid_or_None, x, y, w, h, [pins], page)
    ("Microcontroller", "Main.kicad_sch", MCU_SHEET_UUID, 110, 40, 60, 40,
     ["BOOT", "CHIP_ENABLE", "LED_DATA", "UART_RX", "UART_TX", "USB_DATA+", "USB_DATA-"], "2"),
    ("USB_UART", "USB_UART.kicad_sch", None, 110, 100, 60, 30,
     ["CHIP_ENABLE", "BOOT", "UART_RX", "UART_TX", "USB_DATA+", "USB_DATA-"], "3"),
    ("Power", "Power.kicad_sch", None, 110, 145, 60, 20, [], "4"),
    ("LED", "LED.kicad_sch", None, 110, 180, 60, 20, ["LED_DATA"], "5"),
]

def build_root(sheets_by_name):
    out = [VERSION_HDR.format(uuid=ROOT_UUID), "\t(lib_symbols)"]
    wires, labels = [], []
    for name, fname, suuid, x, y, w, h, pinlist, page in ROOT_SHEETS:
        suuid = suuid or sheets_by_name[name].uuid
        blk = [f'\t(sheet\n\t\t(at {x} {y})\n\t\t(size {w} {h})\n\t\t(exclude_from_sim no)\n'
               f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(fields_autoplaced yes)\n'
               f'\t\t(stroke\n\t\t\t(width 0.1524)\n\t\t\t(type solid)\n\t\t)\n'
               f'\t\t(fill\n\t\t\t(color 0 0 0 0)\n\t\t)\n\t\t(uuid "{suuid}")']
        blk.append(prop("Sheetname", name, x, y - 0.7116))
        blk.append(prop("Sheetfile", fname, x, y + h + 0.95))
        for i, pn in enumerate(pinlist):
            py = y + 7.62 + i * 5.08
            blk.append(f'\n\t\t(pin "{pn}" bidirectional\n\t\t\t(at {x} {py} 180)\n'
                       f'\t\t\t(uuid "{uid("sp")}")\n\t\t\t(effects\n\t\t\t\t(font\n'
                       f'\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(justify left)\n\t\t\t)\n\t\t)')
            wires.append(((x, py), (x - STUB * 3, py)))
            labels.append((pn, x - STUB * 3, py, 180))
        blk.append(f'\n\t\t(instances\n\t\t\t(project "{PROJECT}"\n\t\t\t\t(path "/{ROOT_UUID}"\n'
                   f'\t\t\t\t\t(page "{page}")\n\t\t\t\t)\n\t\t\t)\n\t\t)')
        blk.append("\n\t)")
        out.append("".join(blk))
    for (a, b) in wires:
        out.append(f'\t(wire\n\t\t(pts\n\t\t\t(xy {a[0]:.4f} {a[1]:.4f}) (xy {b[0]:.4f} {b[1]:.4f})\n\t\t)\n'
                   f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "{uid("rw")}")\n\t)')
    for (net, x, y, rot) in labels:
        out.append(f'\t(label "{net}"\n\t\t(at {x:.4f} {y:.4f} {rot})\n\t\t(effects\n\t\t\t(font\n'
                   f'\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify right bottom)\n\t\t)\n'
                   f'\t\t(uuid "{uid("rl")}")\n\t)')
    out.append(f'\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)')
    out.append("\t(embedded_fonts no)\n)")
    return "\n".join(out) + "\n"

# ----------------------------------------------------------------- board file
def build_pcb(template_path, out_path):
    """Drop the butterfly outline into a copy of the existing board file."""
    sys.path.insert(0, os.path.join(HERE, "..", "mechanical"))
    import butterfly_outline as bo
    poly = bo.build(); pts = bo.resample(poly)
    geom = bo.edge_cuts(pts) + bo.silk(poly)
    text = open(template_path, encoding="utf-8", errors="replace").read()
    # strip any outline that is already there, then append ours
    text = re.sub(r'\n\t\(gr_(line|arc|circle|rect|poly)\b.*?\n\t\)(?=\n)', "",
                  text, flags=re.S)
    cut = text.rstrip().rfind(")")
    open(out_path, "w", encoding="utf-8").write(
        text[:cut] + "\n".join(geom) + "\n)\n")
    return len(geom)

# ----------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    lib_path = os.path.join(OUT, "butterfly.kicad_sym")
    write_symbol_lib(lib_path)

    # Symbol definitions come from the sheets already in the project; on a
    # first import they can instead be pulled from the original project with
    # BUTTERFLY_SRC=/path/to/old/project.
    candidates = [os.path.join(OUT, "Main.kicad_sch"),
                  os.path.join(OUT, "USB_UART.kicad_sch")]
    if SRC:
        candidates += [os.path.join(SRC, f) for f in ("Main.kicad_sch", "untitled.kicad_sch")]
    defs, pins = harvest([p for p in candidates if os.path.exists(p)])
    # our own library: re-read it so pin maps come from the same parser
    libtext = open(lib_path, encoding="utf-8").read()
    for blk in _sexp_blocks(libtext, "(symbol "):
        nm = re.match(r'\(symbol\s+"([^"]+)"', blk).group(1)
        if ":" in nm:
            continue
        defs["butterfly:" + nm] = "\t" + blk.replace(f'(symbol "{nm}"',
                                                     f'(symbol "butterfly:{nm}"', 1).rstrip()
        pm = {}
        for pb in _sexp_blocks(blk, "(pin "):
            at = re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\)', pb)
            num = re.search(r'\(number\s+"([^"]+)"', pb)
            if at and num:
                pm[num.group(1)] = (float(at.group(1)), float(at.group(2)), float(at.group(3)))
        pins["butterfly:" + nm] = pm

    sheets = [build_usb_uart(defs, pins), build_power(defs, pins), build_led(defs, pins)]
    by_name = {s.name: s for s in sheets}
    for s in sheets:
        open(os.path.join(OUT, s.filename), "w", encoding="utf-8").write(s.render(defs))
        print(f"  {s.filename:24} {len(s.parts):3} parts  {len(s.wires):3} wires  "
              f"{len(s.labels)+len(s.hlabels)+len(s.glabels):3} labels  {len(s.nocon):2} NC")

    # carry the untouched Microcontroller sheet across, plus project settings
    for f in ("Main.kicad_sch", "LED Butterfly.kicad_pro"):
        src = os.path.join(SRC, f) if SRC else ""
        dst = os.path.join(OUT, f)
        if src and os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy2(src, dst)

    open(os.path.join(OUT, "LED Butterfly.kicad_sch"), "w", encoding="utf-8").write(build_root(by_name))
    print("  LED Butterfly.kicad_sch   root, 4 sheets")

    # keep the project's sheet index in step with the root schematic
    pro = os.path.join(OUT, "LED Butterfly.kicad_pro")
    if os.path.exists(pro):
        import json
        d = json.load(open(pro, encoding="utf-8"))
        d["sheets"] = [[ROOT_UUID, PROJECT]] + [
            [(su or by_name[nm].uuid), nm]
            for nm, _f, su, *_rest in [(r[0], r[1], r[2]) + tuple(r[3:]) for r in ROOT_SHEETS]]
        json.dump(d, open(pro, "w", encoding="utf-8"), indent=2)
        print(f"  LED Butterfly.kicad_pro   sheet index: {len(d['sheets'])} entries")

    open(os.path.join(OUT, "sym-lib-table"), "w").write(
        '(sym_lib_table\n  (version 7)\n  (lib (name "butterfly")(type "KiCad")'
        '(uri "${KIPRJMOD}/butterfly.kicad_sym")(options "")(descr "Twinkling Butterfly parts"))\n)\n')

    pcb_tpl = os.path.join(SRC, "LED Butterfly.kicad_pcb") if SRC else ""
    if not (pcb_tpl and os.path.exists(pcb_tpl)):
        pcb_tpl = os.path.join(OUT, "LED Butterfly.kicad_pcb")
    n = build_pcb(pcb_tpl, os.path.join(OUT, "LED Butterfly.kicad_pcb"))
    print(f"  LED Butterfly.kicad_pcb   {n} outline/silk primitives")

if __name__ == "__main__":
    main()
