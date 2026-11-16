"""ARC_GRI30_NOx22 reference chemistry for the pipeline: the same C kernel as OpenFOAM's arcChemStep
(mechanisms/arc_gri30_nox22: arc_rhs_original = the unrolled LQSSA kernel, arc_project = the C/H/O/N
restoration onto CO2/H2O/O2/N2), called through ctypes and integrated with a stiff SciPy BDF solver.

One step from (Y[22], T, p) over dt is what arcChemStep does to a cell: constant-pressure adiabatic ODE,
then arc_project to the input's element totals. Here the integration is tight (rtol 1e-8, atol 1e-14 on Y,
as the Cantera references of the pipeline) and the output T is taken at the input's enthalpy in the
22-species thermo (OpenFOAM keeps h and derives T; the projection moves ~1e-6 of the mass).

The shared library is built on first use (gcc/g++ -O3) into build/libarc22.so, or taken from $ARC22_LIB.
"""

import ctypes
import os
import subprocess
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "mechanisms" / "arc_gri30_nox22"
N = 22
NAMES = ["H2", "H", "O", "O2", "OH", "H2O", "HO2", "H2O2", "CH4", "CH3", "CO", "CO2", "CH2O", "CH3OH",
         "C2H2", "C2H4", "C2H6", "N2", "NO", "NO2", "N2O", "HCN"]

_HELPER = r"""
#include "arc_gri30_nox22.h"
#include <math.h>
/* finite-difference Jacobian of arc_rhs_original, as arcChemStep (row-major J[i*23+j] = d f_i / d y_j) */
void arc_jac_fd(double p, const double* y0, double* J)
{
    const int n = ARC_N_ODE + 1;
    double y[ARC_N_ODE + 1], f0[ARC_N_ODE + 1], f1[ARC_N_ODE + 1];
    for (int k = 0; k < n; k++) y[k] = y0[k];
    if (y[ARC_N_ODE] < 200) y[ARC_N_ODE] = 200;
    arc_rhs_original(p, y, f0);
    for (int j = 0; j < n; j++) {
        const double v = y[j];
        const double h = (j == ARC_N_ODE) ? 1e-6 * (v > 300 ? v : 300) : 1e-7 * (fabs(v) > 1e-9 ? fabs(v) : 1e-9);
        y[j] = v + h;
        arc_rhs_original(p, y, f1);
        y[j] = v;
        for (int i = 0; i < n; i++) J[i * n + j] = (f1[i] - f0[i]) / h;
    }
}
void arc_rhs_clamped(double p, const double* y0, double* f)
{
    double y[ARC_N_ODE + 1];
    for (int k = 0; k <= ARC_N_ODE; k++) y[k] = y0[k];
    if (y[ARC_N_ODE] < 200) y[ARC_N_ODE] = 200;
    arc_rhs_original(p, y, f);
}
"""


def _build(out):
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "arc22_build"
    tmp.mkdir(exist_ok=True)
    (tmp / "arc_helpers.c").write_text(_HELPER)
    inc = ["-I", str(SRC)]
    cmds = [["gcc", "-O3", "-fPIC", "-c", str(SRC / "arc_gri30_nox22.c"), "-o", str(tmp / "core.o")] + inc,
            ["gcc", "-O3", "-fPIC", "-c", str(tmp / "arc_helpers.c"), "-o", str(tmp / "helpers.o")] + inc,
            ["g++", "-O3", "-std=c++17", "-fPIC", "-c", str(SRC / "arc_kernel_original.cpp"), "-o",
             str(tmp / "orig.o")] + inc,
            ["g++", "-shared", "-o", str(out), str(tmp / "core.o"), str(tmp / "helpers.o"), str(tmp / "orig.o"), "-lm"]]
    for c in cmds:
        subprocess.run(c, check=True)


_lib = None


def lib():
    global _lib
    if _lib is None:
        path = Path(os.environ.get("ARC22_LIB", ROOT / "build" / "libarc22.so"))
        if not path.exists():
            _build(path)
        L = ctypes.CDLL(str(path))
        D = ctypes.POINTER(ctypes.c_double)
        L.arc_species_name.restype = ctypes.c_char_p
        L.arc_species_W.restype = ctypes.c_double
        for f in (L.arc_rhs_clamped, L.arc_jac_fd):
            f.argtypes = [ctypes.c_double, D, D]
        L.arc_elements.argtypes = [D, D]
        L.arc_project.argtypes = [D, D]
        names = [L.arc_species_name(k).decode() for k in range(N)]
        if names != NAMES:
            raise RuntimeError(f"ARC species order differs: {names}")
        _lib = L
    return _lib


def _p(a):
    return a.ctypes.data_as(ctypes.POINTER(ctypes.c_double))


def rhs(p, y):
    y = np.ascontiguousarray(y, float)
    f = np.empty(N + 1)
    lib().arc_rhs_clamped(p, _p(y), _p(f))
    return f


def jac(p, y):
    y = np.ascontiguousarray(y, float)
    J = np.empty((N + 1) * (N + 1))
    lib().arc_jac_fd(p, _p(y), _p(J))
    return J.reshape(N + 1, N + 1)


def elements(Y):
    Y = np.ascontiguousarray(Y, float)
    e = np.empty(4)
    lib().arc_elements(_p(Y), _p(e))
    return e


def project(Y, el0):
    Y = np.array(Y, float)
    e = np.ascontiguousarray(el0, float)
    lib().arc_project(_p(Y), _p(e))
    return np.maximum(Y, 0.0)


def advance(Y, T, p, times, rtol=1e-8, atol=1e-14):
    """ARC from (Y[22] in NAMES order, T, p) to each of the increasing `times` [s]: returns
    (Y[len(times), 22] after arc_project to the input's elements, T[len(times)] of the ODE)."""
    Y = np.asarray(Y, float)
    y0 = np.r_[Y, T]
    el0 = elements(Y)
    sol = solve_ivp(lambda t, y: rhs(p, y), (0.0, float(times[-1])), y0, method="BDF", t_eval=list(times),
                    jac=lambda t, y: jac(p, y), rtol=rtol, atol=np.r_[np.full(N, atol), 1e-8])
    if not sol.success or sol.y.shape[1] != len(times):
        raise RuntimeError(f"ARC integration failed: {sol.message}")
    Yo = np.array([project(np.maximum(sol.y[:N, k], 0.0), el0) for k in range(len(times))])
    return Yo, sol.y[N].copy()
