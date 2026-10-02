#!/usr/bin/env python3
"""
Independent check of the generated schematic: re-parses the written .kicad_sch
files (it does not trust the generator's own data structures), rebuilds the
netlist by walking wires, labels and power symbols, and reports:

  * s-expression balance and lib_symbols completeness
  * duplicate reference designators
  * device pins that are neither connected nor flagged no-connect
  * single-pin nets (a connection that goes nowhere)
  * the full netlist, written to docs/netlist.md

Exit status is non-zero if anything structural is wrong.
"""
import os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, "LED Butterfly")
SHEETS = ["USB_UART.kicad_sch", "Power.kicad_sch", "LED.kicad_sch",
          "LED Butterfly.kicad_sch", "Main.kicad_sch"]

def blocks(text, head):
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
            elif c == "(": depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    yield text[i:j+1]; break
            j += 1

def balanced(text):
    depth = 0; j = 0
    while j < len(text):
        c = text[j]
        if c == '"':
            j += 1
            while j < len(text) and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
        elif c == "(": depth += 1
        elif c == ")":
            depth -= 1
            if depth < 0: return False
        j += 1
    return depth == 0

def pinmap(libblk):
    pm = {}
    for pb in blocks(libblk, "(pin "):
        at = re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\)', pb)
        num = re.search(r'\(number\s+"([^"]+)"', pb)
        nm = re.search(r'\(name\s+"([^"]*)"', pb)
        ty = re.match(r'\(pin\s+(\S+)', pb)
        if at and num and num.group(1) not in pm:
            # a symbol with several units repeats pin numbers; unit 1 comes first
            pm[num.group(1)] = (float(at.group(1)), float(at.group(2)),
                                nm.group(1) if nm else "", ty.group(1) if ty else "")
    return pm

class UF(dict):
    def find(self, a):
        self.setdefault(a, a)
        while self[a] != a:
            self[a] = self[self[a]]; a = self[a]
        return a
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self[ra] = rb

NC_PINS = {}   # (sheet, ref, pin) -> pin name, filled in by analyse()


def analyse(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    name = os.path.basename(path)
    problems = []
    if not balanced(text):
        problems.append(f"{name}: unbalanced parentheses")
        return problems, {}, {}
    libsec = next(blocks(text, "(lib_symbols"), "")
    libs = {}
    for blk in blocks(libsec, "(symbol "):
        n = re.match(r'\(symbol\s+"([^"]+)"', blk).group(1)
        if ":" in n: libs[n] = pinmap(blk)

    uf = UF(); pinnodes = {}; refs = {}
    body = text[len(libsec) + text.index("(lib_symbols"):] if libsec else text
    for blk in blocks(body, "(symbol\n"):
        lid = re.search(r'\(lib_id\s+"([^"]+)"', blk)
        at = re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\)', blk)
        rf = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not (lid and at and rf): continue
        lid, ref = lid.group(1), rf.group(1)
        if lid not in libs:
            problems.append(f"{name}: {ref} uses {lid} with no definition in lib_symbols")
            continue
        sx, sy = float(at.group(1)), float(at.group(2))
        rot = int(float(at.group(3))) % 360
        mir = re.search(r'\(mirror\s+(\w+)\)', blk)
        refs.setdefault(ref, []).append(name)
        for num, (px, py, pname, ptype) in libs[lid].items():
            qx, qy = px, py
            if mir and mir.group(1) == "x":   qy = -qy
            if mir and mir.group(1) == "y":   qx = -qx
            if   rot == 90:  qx, qy = -qy,  qx
            elif rot == 180: qx, qy = -qx, -qy
            elif rot == 270: qx, qy =  qy, -qx
            node = (round(sx + qx, 2), round(sy - qy, 2))
            pinnodes[(ref, num)] = (node, pname, ptype, lid)
            if lid.startswith("power:"):
                vp = re.search(r'\(property "Value" "([^"]+)"', blk)
                if vp: uf.union(node, "NET:" + vp.group(1))
    for w in blocks(body, "(wire"):
        xy = re.findall(r'\(xy\s+(-?[\d.]+)\s+(-?[\d.]+)\)', w)
        a = (round(float(xy[0][0]), 2), round(float(xy[0][1]), 2))
        b = (round(float(xy[1][0]), 2), round(float(xy[1][1]), 2))
        uf.union(a, b)
    for kind in ("(label ", "(global_label ", "(hierarchical_label "):
        for l in blocks(body, kind):
            net = re.match(r'\(\w+\s+"([^"]+)"', l).group(1)
            at = re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)', l)
            uf.union((round(float(at.group(1)), 2), round(float(at.group(2)), 2)), "NET:" + net)
    ncs = set()
    for nc in blocks(body, "(no_connect"):
        at = re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)', nc)
        ncs.add((round(float(at.group(1)), 2), round(float(at.group(2)), 2)))

    nets = collections.defaultdict(list)
    for (ref, num), (node, pname, ptype, lid) in pinnodes.items():
        if ref.startswith("#"):          # power / flag symbols
            root = uf.find(node)
            nets[root].append((ref, num, pname))
            continue
        if node in ncs:
            NC_PINS[(name, ref, num)] = pname
            continue
        if node not in uf:
            problems.append(f"{name}: {ref} pin {num} ({pname}) is floating - no wire, no no-connect")
            continue
        nets[uf.find(node)].append((ref, num, pname))
    named = {}
    for root, members in nets.items():
        label = None
        for k in uf:
            if isinstance(k, str) and k.startswith("NET:") and uf.find(k) == root:
                label = k[4:]; break
        named.setdefault(label or f"<unnamed@{root}>", []).extend(members)
    return problems, named, refs

def main():
    allprob, allnets, allrefs = [], {}, collections.defaultdict(list)
    for f in SHEETS:
        p = os.path.join(PROJ, f)
        if not os.path.exists(p):
            allprob.append(f"missing {f}"); continue
        prob, nets, refs = analyse(p)
        allprob += prob
        for n, m in nets.items():
            allnets.setdefault(n, []).extend(m)
        for r, where in refs.items():
            allrefs[r] += where
    for r, where in sorted(allrefs.items()):
        if r.startswith("#"): continue
        if len(where) > 1:
            allprob.append(f"duplicate reference {r} in {', '.join(where)}")
    for n, members in sorted(allnets.items()):
        real = [m for m in members if not m[0].startswith("#")]
        if len(real) < 2 and n not in ("GND",):
            allprob.append(f"net {n} has only {len(real)} device pin(s): {real}")

    os.makedirs(os.path.join(HERE, "..", "docs"), exist_ok=True)
    with open(os.path.join(HERE, "..", "docs", "netlist.md"), "w") as fh:
        fh.write("# Netlist\n\nGenerated by `hardware/validate_sheets.py` from the "
                 "written schematic files.\n\n| Net | Connections |\n|---|---|\n")
        for n in sorted(allnets, key=lambda s: (s.startswith("<"), s)):
            conn = ", ".join(f"{r}.{p}" + (f" ({nm})" if nm and nm != "~" else "")
                             for r, p, nm in sorted(allnets[n]) if not r.startswith("#"))
            fh.write(f"| `{n}` | {conn} |\n")
    print(f"nets: {len(allnets)}   references: {len([r for r in allrefs if not r.startswith('#')])}")
    if allprob:
        print("\nPROBLEMS:")
        for p in allprob: print("  -", p)
        return 1
    print("no structural problems found")
    return 0

if __name__ == "__main__":
    sys.exit(main())
