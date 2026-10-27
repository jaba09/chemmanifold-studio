"""Stage 0 (flame mode only): reference thermochemical space of the burner's non-premixed flame.

Solves counterflow diffusion flamelets between the fuel and oxidizer streams of the burner, from
low strain up to extinction (the upper branch of the S-curve). `flame.transport` selects the
transport model: "mixture-averaged" (default) is closest to Fluent's kinetic-theory diffusivities;
"unity-Lewis-number" makes Z and h exact conserved scalars. `flame.radiation` lists the families to
solve: [false] adiabatic only (default); [false, true] adds a second strain sweep with optically thin
gas radiation (CO2, H2O, Cantera's radiation model), whose states carry the radiative heat loss of
a real flame. Flamelets are numbered across families, adiabatic first.

Writes 00_flame/flamelets.npz        every flamelet grid point: Z, Y, T, h, strain index
       00_flame/burnt_reference.npz  lowest-strain flamelet resampled on a Z grid (burnt state per Z)
       00_flame/flame_reference.json Z_st, adiabatic T(Z), peak T and strain of every flamelet
"""

import cantera as ct
import numpy as np

from chemmanifold.chemistry import make_gas
from chemmanifold.flame import BilgerZ, flame_pressure, stoichiometric_z, stream_states
from chemmanifold.io import base_parser, load_config, save_json, save_npz, stage_dir


def solve_flamelets(gas, cfg, radiation=False):
    fc, c = cfg["flame"], cfg["chemistry"]
    P = flame_pressure(cfg)
    gas.TPY = c["fuel_T"], P, c["fuel"]
    rho_f = gas.density
    gas.TPY = c["oxidizer_T"], P, c["oxidizer"]
    rho_o = gas.density
    ratio = np.sqrt(rho_o / rho_f)          # equal inlet momentum flux: mdot^2 / rho equal

    f = ct.CounterflowDiffusionFlame(gas, width=fc["width"])
    f.transport_model = fc.get("transport", "mixture-averaged")
    f.radiation_enabled = bool(radiation)
    f.P = P
    f.fuel_inlet.Y, f.fuel_inlet.T = c["fuel"], c["fuel_T"]
    f.oxidizer_inlet.Y, f.oxidizer_inlet.T = c["oxidizer"], c["oxidizer_T"]
    f.set_refine_criteria(ratio=3, slope=0.08, curve=0.15, prune=0.02)

    mdot = fc["mdot_fuel_min"]
    tag = "radiating " if radiation else ""
    out = []
    for i in range(fc["max_flamelets"]):
        f.fuel_inlet.mdot, f.oxidizer_inlet.mdot = mdot, mdot * ratio
        try:
            f.solve(loglevel=0, auto=(i == 0))
        except ct.CanteraError:
            print(f"  {tag}flamelet {i}: solver failed, stopping the strain sweep")
            break
        T_max, a = float(f.T.max()), float(f.strain_rate("max"))
        if T_max < fc["extinction_T"]:
            print(f"  {tag}flamelet {i}: extinguished at strain ~{a:.0f} 1/s")
            break
        print(f"  {tag}flamelet {i}: strain={a:7.1f} 1/s  T_max={T_max:.0f} K  points={len(f.grid)}")
        out.append(dict(Y=f.Y.T.copy(), T=f.T.copy(), h=f.enthalpy_mass.copy(), strain=a, T_max=T_max,
                        radiation=bool(radiation)))
        mdot *= fc["strain_factor"]
    return out


def fc_radiation(cfg):
    return [bool(r) for r in cfg["flame"].get("radiation", [False])]


def main(cfg):
    gas = make_gas(cfg)
    P = flame_pressure(cfg)
    (Yf, hf), (Yo, ho) = stream_states(gas, cfg)
    bz = BilgerZ(gas, Yf, Yo)
    z_st = stoichiometric_z(gas, cfg)

    flamelets = [fl for rad in fc_radiation(cfg) for fl in solve_flamelets(gas, cfg, rad)]
    if not flamelets:
        raise RuntimeError("no burning flamelet found - check the flame section of the config")
    for fl in flamelets:
        fl["Z"] = np.clip(bz(fl["Y"]), 0.0, 1.0)

    # burnt reference: the lowest-strain flamelet, sorted by Z, with the pure streams at Z = 0 and 1
    fl0 = flamelets[0]
    order = np.argsort(fl0["Z"])
    Z0, Y0, h0 = fl0["Z"][order], fl0["Y"][order], fl0["h"][order]
    keep = np.concatenate([[True], np.diff(Z0) > 1e-9])
    Z0, Y0, h0 = Z0[keep], Y0[keep], h0[keep]
    Zg = np.unique(np.concatenate([np.linspace(0, 1, 201), np.linspace(0, 4 * z_st, 201)]))
    Yg = np.column_stack([np.interp(Zg, Z0, Y0[:, k]) for k in range(gas.n_species)])
    hg = np.interp(Zg, Z0, h0)
    Yg[0], hg[0], Yg[-1], hg[-1] = Yo, ho, Yf, hf
    Yg /= Yg.sum(1, keepdims=True)

    # adiabatic equilibrium temperature of the fresh mixture, for reference
    T_ad = []
    for Z in Zg:
        gas.HPY = Z * hf + (1 - Z) * ho, P, Z * Yf + (1 - Z) * Yo
        gas.equilibrate("HP")
        T_ad.append(gas.T)
    T_ad = np.array(T_ad)

    out = stage_dir(cfg, "flame")
    save_npz(out / "flamelets.npz",
             Z=np.concatenate([fl["Z"] for fl in flamelets]),
             Y=np.vstack([fl["Y"] for fl in flamelets]),
             T=np.concatenate([fl["T"] for fl in flamelets]),
             h=np.concatenate([fl["h"] for fl in flamelets]),
             strain_id=np.concatenate([np.full(len(fl["T"]), i) for i, fl in enumerate(flamelets)]))
    save_npz(out / "burnt_reference.npz", Z=Zg, Y=Yg, h=hg, T_ad=T_ad)
    save_json(out / "flame_reference.json", dict(
        P=P, Z_st=z_st, T_ad_max=float(T_ad.max()), Z_at_T_ad_max=float(Zg[np.argmax(T_ad)]),
        strain_rates=[fl["strain"] for fl in flamelets], T_max=[fl["T_max"] for fl in flamelets],
        radiation=[fl["radiation"] for fl in flamelets],
        species=list(gas.species_names)))
    print(f"  Z_st={z_st:.4f}  T_ad,max={T_ad.max():.0f} K  {len(flamelets)} flamelets, "
          f"strain {flamelets[0]['strain']:.0f}-{flamelets[-1]['strain']:.0f} 1/s, "
          f"T_max {flamelets[-1]['T_max']:.0f}-{flamelets[0]['T_max']:.0f} K")


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))
