#!/usr/bin/env python3
"""Pull the solver settings out of a Fluent .cas.h5 file.

Writes, into <outdir>:
  chem.inp, therm.dat, tran.dat   the Chemkin files Fluent stored with the case (if any)
  settings_summary.txt            enabled models, species order, UDF hooks and every boundary zone
  *.scm                           the raw Scheme settings blocks, for anything not summarised

Usage:
    python fluent_cas_settings.py case.cas.h5 <outdir>
"""
import argparse
import os
import re

import h5py

TOK = re.compile(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+')
THERMAL_BC = {0: "fixed temperature", 1: "heat flux", 2: "convection", 3: "coupled", 4: "radiation", 5: "mixed"}
BC_KEYS = ("thermal-bc", "t", "q", "h", "tinf", "t0", "p", "vmag", "velocity-spec", "flow-spec", "mass-flow",
           "direction-spec", "ni", "nj", "ke-spec", "turb-intensity", "turb-viscosity-ratio", "mf")


def sexp(s):
    stack = [[]]
    for t in TOK.findall(s):
        if t == "(":
            stack.append([])
        elif t == ")":
            if len(stack) == 1:  # unmatched close: the chunk was cut mid-list
                continue
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(t)
    return stack[0]


def balanced(s, i):
    """Index of the parenthesis closing the one at s[i], skipping strings."""
    depth, ins, j = 0, False, i
    while True:
        c = s[j]
        if ins:
            if c == "\\":
                j += 1
            elif c == '"':
                ins = False
        elif c == '"':
            ins = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1


def flat(v):
    """Scheme value -> text; (constant . x) (profile "" "") collapses to x."""
    if isinstance(v, list):
        if len(v) == 3 and v[1] == ".":
            return flat(v[2]) if v[0] == "constant" else f"{v[0]}={flat(v[2])}"
        if v and isinstance(v[0], list) and v[0][:2] == ["constant", "."]:
            return flat(v[0])
        return " ".join(flat(x) for x in v)
    return v


def foam_chemkin(name, text):
    """chemkinToFoam's lexer is stricter than Chemkin: rewrite what Cantera's yaml2ck emits."""
    if name == "chem.inp":
        return re.sub(r"^(REACTIONS.*\s)MOLE\s*$", r"\1MOLES", text, flags=re.M | re.I)
    if name == "therm.dat":
        def temps(m):
            return "THERMO ALL\n" + "".join(f"{float(t):10.3f}" for t in m.group(1).split()) + "\n"
        text = re.sub(r"^THERMO[^\n]*\n\s*([\d.]+\s+[\d.]+\s+[\d.]+)\s*\n", temps, text, flags=re.M)
        # Species whose fit starts at 300 K (N2, CH3O here): extend it to 200 K. Otherwise every
        # cell that dips a hair below the 300 K boundary temperature prints a janafThermo
        # warning, which floods the log (GBs) and slows the run to a crawl.
        return re.sub(r"^(.{44}G) *300\.0*(?= )", lambda m: m.group(1) + "200.000", text, flags=re.M)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cas")
    ap.add_argument("outdir")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    with h5py.File(args.cas, "r") as f:
        settings = {k: f["settings"][k][0].decode(errors="replace") for k in f["settings"]}
    for k, v in settings.items():
        with open(os.path.join(args.outdir, k.replace(" ", "_") + ".scm"), "w") as fh:
            fh.write(v)
    rv, tv = settings["Rampant Variables"], settings["Thread Variables"]
    out = [f"Fluent {settings.get('Version', '?')} ({settings.get('Origin', '').strip()})"]

    i = rv.find("(case-config ")
    if i >= 0:
        cfg = re.findall(r"\(([a-z-]+\?) \. #t\)", rv[i:balanced(rv, i)])
        out.append("enabled models: " + " ".join(cfg))
    for key in ("species/reaction-model", "udf/chem-step-fcn", "operating-pressure", "gravity/x", "gravity/y",
                "species/sct", "species/ode-rtol", "species/ode-atol"):
        m = re.search(r"\n\(" + re.escape(key) + r" ([^\n]*)\)\n", rv)
        if m:
            out.append(f"{key}: {m.group(1)}")

    i = rv.find("(names ")
    if i >= 0:
        out.append("species order: " + rv[i + 7:rv.find(")", i)])

    i = rv.find("(chemkinfiles ")
    if i >= 0:
        files = [t for t in sexp(rv[i:balanced(rv, i) + 1])[0][1:] if t.startswith('"')]
        for name, text in zip(("chem.inp", "therm.dat", "tran.dat"), files):
            text = text[1:-1].encode().decode("unicode_escape").replace("\r\n", "\n")
            if text.strip():
                with open(os.path.join(args.outdir, name), "w") as fh:
                    fh.write(text)
                out.append(f"wrote {name} ({len(text)} chars)")
                foam = foam_chemkin(name, text)
                if foam is not None:
                    stem, ext = os.path.splitext(name)
                    with open(os.path.join(args.outdir, f"{stem}.foam{ext}"), "w") as fh:
                        fh.write(foam)
                    out.append(f"wrote {stem}.foam{ext} (chemkinToFoam-readable copy)")

    out.append("\nboundary zones:")
    hdr = list(re.finditer(r"\((\d+) ([a-z-]+) ([^\s()]+) (\d+)\)\(", tv))
    for k, h in enumerate(hdr):
        zid, ztype, name = h.group(1), h.group(2), h.group(3)
        if ztype == "interior":
            continue
        out.append(f"  [{zid}] {name}: {ztype}")
        body = tv[h.end():hdr[k + 1].start() if k + 1 < len(hdr) else len(tv)]
        props = {}
        for item in sexp("(" + body):
            for p in item if isinstance(item, list) else []:
                if isinstance(p, list) and p and p[0] in BC_KEYS:
                    props[p[0]] = flat(p[2]) if len(p) > 2 and p[1] == "." else (
                        [flat(x) for x in p[1:]] if p[0] == "mf" else flat(p[1:]))
        if ztype == "fluid":
            m = re.search(r"\(material \. ([^)]+)\)", body)
            out.append(f"      material {m.group(1) if m else '?'}")
            continue
        for key in BC_KEYS:
            if key in props and key != "thermal-bc":
                val = props[key]
                if key == "mf":
                    if not any(float(x) for x in val):
                        continue
                    val = " ".join(val)
                out.append(f"      {key} = {val}")
        if "thermal-bc" in props:
            out.append(f"      thermal-bc = {THERMAL_BC.get(int(props['thermal-bc']), props['thermal-bc'])}")

    with open(os.path.join(args.outdir, "settings_summary.txt"), "w") as fh:
        fh.write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
