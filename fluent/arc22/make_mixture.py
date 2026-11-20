"""Write the 22-species CHEMKIN files Fluent imports for the ARC_GRI30_NOx22 mixture.

The thermo and transport data are copied, entry by entry, from the CHEMKIN files stored inside Javier's
Fluent GRI-Mech 3.0 case (quemadorUnicoTesis_60KCells-GRI--ID.cas.h5, mixture "chemkin-import"), so the
ARC case has exactly the GRI case's thermodynamics and transport for the species they share.

    python fluent/arc22/make_mixture.py <path to the GRI .cas.h5>     (needs h5py)

Output in fluent/arc22/mechanism/: arc22_chem.inp, arc22_therm.dat, arc22_tran.dat.
"""
import pathlib, sys
import h5py

ARC = ["H2", "H", "O", "O2", "OH", "H2O", "HO2", "H2O2", "CH4", "CH3", "CO", "CO2", "CH2O", "CH3OH",
       "C2H2", "C2H4", "C2H6", "NO", "NO2", "N2O", "HCN", "N2"]   # N2 last: Fluent's bulk species
out = pathlib.Path(__file__).resolve().parent / "mechanism"


def chemkin_strings(cas):
    rv = h5py.File(cas, "r")["settings"]["Rampant Variables"][0]
    s = rv.decode(errors="replace") if isinstance(rv, bytes) else str(rv)
    i = s.index("(chemkinfiles ", s.index("(chemkin-import mixture")) + len("(chemkinfiles ")
    parts = []
    while s[i] in ' \n':
        i += 1
    while s[i] == '"':
        j = s.index('"', i + 1)
        parts.append(s[i + 1:j])
        i = j + 1
        while s[i] in ' \n':
            i += 1
    return parts   # mechanism, thermo, transport


def main(cas):
    mech, thermo, tran = chemkin_strings(cas)[:3]
    # thermo: 4-line NASA-7 records; keep the header line with the default T ranges
    lines = thermo.splitlines()
    head = [l for l in lines[:2]]
    recs = {}
    k = 0
    while k < len(lines):
        l = lines[k]
        if len(l) >= 80 and l[79] == "1":
            recs[l[:18].split()[0].upper()] = lines[k:k + 4]
            k += 4
        else:
            k += 1
    missing = [n for n in ARC if n not in recs]
    assert not missing, f"thermo missing {missing}"
    t = ["THERMO", head[1] if head[0].strip().upper().startswith("THERMO") else head[0]]
    t += ["! ARC_GRI30_NOx22 transported species; records copied from the Fluent GRI-Mech 3.0 case"]
    for n in ARC:
        t += recs[n]
    t += ["END"]
    (out / "arc22_therm.dat").write_text("\n".join(t) + "\n")

    trec = {}
    for l in tran.splitlines():
        f = l.split()
        if f and not l.startswith("!"):
            trec[f[0].upper()] = l
    missing = [n for n in ARC if n not in trec]
    assert not missing, f"transport missing {missing}"
    (out / "arc22_tran.dat").write_text("\n".join(trec[n] for n in ARC) + "\n")

    # one real GRI reaction among the 22 species (R38, H+O2<=>O+OH): Fluent needs a reaction to enable
    # volumetric chemistry, but with the arc22_chem_step hook its rate is never used
    rx = [l for l in mech.splitlines() if l.replace(" ", "").upper().startswith("H+O2<=>O+OH")]
    assert rx, "H+O2<=>O+OH not found in the GRI mechanism"
    m = ["! ARC_GRI30_NOx22 (22 transported species of the analytically reduced GRI-Mech 3.0) for Fluent.",
         "! The chemistry is computed by the UDF arc22_chem_step (fluent/arc22/udf): 22 ODE species +",
         "! 21 QSS radicals, 262 reactions. The single reaction below only lets Fluent switch volumetric",
         "! reactions on; it is NOT used while the chemistry-step hook is set.",
         "ELEMENTS", "O  H  C  N", "END", "SPECIES"]
    m += ["  ".join(ARC[i:i + 8]) for i in range(0, len(ARC), 8)]
    m += ["END", "REACTIONS", rx[0], "END"]
    (out / "arc22_chem.inp").write_text("\n".join(m) + "\n")
    print("wrote", *(out / f for f in ("arc22_chem.inp", "arc22_therm.dat", "arc22_tran.dat")))


if __name__ == "__main__":
    main(sys.argv[1])
