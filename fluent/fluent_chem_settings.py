#!/usr/bin/env python3
"""Report the chemistry settings of a Fluent .cas.h5 and optionally write a Direct Integration copy.

Reads the Scheme settings Fluent stores in the case (settings/Rampant Variables). Model flags come
from the (case-config ...) block, which holds the active values; the plain (rp-...? #f) entries at
the top of the variable list are not the active models.

--di-copy writes a copy of the case with the DEFINE_CHEM_STEP hook set to "none" and ISAT off, so
Fluent integrates the chemistry itself (Direct Integration). The edited entries are padded with
spaces (inside the parentheses) to keep the fixed-length HDF5 string the same size; nothing else in the file is touched.

Usage:
    python fluent_chem_settings.py case.cas.h5
    python fluent_chem_settings.py case.cas.h5 --di-copy case-DI.cas.h5
"""
import argparse
import re
import shutil

import h5py

RV = "settings/Rampant Variables"
MODEL_FLAGS = ("rp-axi?", "rf-energy?", "rp-unsteady?", "rp-lam?", "rp-kw?", "rp-react?", "rp-spe?")
KEYS = (
    ("species/reaction-model", "turbulence-chemistry interaction"),
    ("species/edc?", "EDC"),
    ("stiff-chem-seg?", "stiff chemistry (pressure-based)"),
    ("species/isat?", "ISAT (#f = Direct Integration)"),
    ("udf/chem-step-fcn", "DEFINE_CHEM_STEP hook"),
    ("udf/compile/files", "compiled UDF source"),
    ("species/ode-rtol", "ODE relative tolerance"),
    ("species/ode-atol", "ODE absolute tolerance"),
    ("species/min-temp-chemistry", "minimum chemistry temperature [K]"),
    ("species/agglom-chemistry?", "chemistry agglomeration"),
    ("species/dimension-reduction", "dimension reduction (0 = off)"),
    ("species/thermal-diffusion?", "thermal diffusion"),
    ("species/isat-errtol", "ISAT error tolerance (unused when ISAT off)"),
    ("pseudo-transient-formulation?", "pseudo-transient"),
    ("pseudo-auto-time-step", "pseudo-time step [s]"),
    ("operating-pressure", "operating pressure [Pa]"),
)
# entry -> replacement value for the DI copy
DI_EDITS = {"udf/chem-step-fcn": '"none"', "species/isat?": "#f"}


def entry(rv, key):
    m = re.search(r"\n\(" + re.escape(key) + r" ([^\n]*)\)\n", rv)
    return m.group(1).rstrip() if m else None


def report(rv):
    out = []
    i = rv.find("(case-config ")
    cfg = dict(re.findall(r"\(([a-z-]+\??) \. ([^()\s]+)\)", rv[i:rv.find("\n", i)]))
    out.append("models: " + ", ".join(f"{k} {cfg.get(k, '?')}" for k in MODEL_FLAGS))
    sst = re.search(r"\(kw-sst-on\? (#[tf])\)", rv)
    out.append(f"k-omega SST: {sst.group(1) if sst else '?'}")
    for key, label in KEYS:
        out.append(f"{label:45s} {key} = {entry(rv, key)}")
    mix = re.search(r"\(chemkin-import mixture .*?\(species \(names ([^)]*)\)\)", rv)
    if mix:
        species = mix.group(1).split()
        j = rv.find("(chemkin-import mixture")
        nrxn = len(set(re.findall(r'\("reaction-(\d+)"', rv[j:rv.find("\n", j)])))
        out.append(f"mechanism: {len(species)} species, {nrxn} reactions: {' '.join(species)}")
    return "\n".join(out)


def di_copy(src, dst):
    shutil.copyfile(src, dst)
    with h5py.File(dst, "r+") as f:
        raw = f[RV][0]
        rv = raw.decode()
        for key, val in DI_EDITS.items():
            old = f"\n({key} {entry(rv, key)})"
            pad = len(old) - len(f"\n({key} {val})")
            if pad < 0:
                raise SystemExit(f"new value for {key} is longer than the old one")
            rv = rv.replace(old, f"\n({key} {val}{' ' * pad})", 1)
        assert len(rv.encode()) == len(raw)
        f[RV][0] = rv.encode()
    with h5py.File(dst, "r") as f:
        return f[RV][0].decode()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cas")
    ap.add_argument("--di-copy", metavar="OUT.cas.h5")
    args = ap.parse_args()
    with h5py.File(args.cas, "r") as f:
        print(f"Fluent {f['settings/Version'][0].decode()}")
        print(report(f[RV][0].decode()))
    if args.di_copy:
        rv = di_copy(args.cas, args.di_copy)
        print(f"\nwrote {args.di_copy}:")
        for key in DI_EDITS:
            print(f"  {key} = {entry(rv, key)}")


if __name__ == "__main__":
    main()
