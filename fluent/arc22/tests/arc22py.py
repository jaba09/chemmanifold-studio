"""ctypes wrapper of the Fluent ARC22 core (fluent/arc22/udf/arc22_core.c + arc22_kernel.c)."""
import ctypes, os, pathlib, subprocess, tempfile
import numpy as np

UDF = pathlib.Path(__file__).resolve().parents[1] / "udf"
NSP = 22


class Options(ctypes.Structure):
    _fields_ = [("rtol", ctypes.c_double), ("atol", ctypes.c_double), ("atol_T", ctypes.c_double),
                ("T_freeze", ctypes.c_double), ("T_quiet", ctypes.c_double), ("max_steps", ctypes.c_int),
                ("project", ctypes.c_int), ("method", ctypes.c_int), ("jac_reuse", ctypes.c_int)]


class Info(ctypes.Structure):
    _fields_ = [("status", ctypes.c_int), ("n_steps", ctypes.c_int), ("n_reject", ctypes.c_int),
                ("n_jac", ctypes.c_int), ("T_out", ctypes.c_double), ("hrr", ctypes.c_double),
                ("elem_fix", ctypes.c_double)]


def build(cc=os.environ.get("CC", "gcc")):
    out = pathlib.Path(tempfile.gettempdir()) / "libarc22_fluent.so"
    subprocess.run([cc, "-std=c99", "-O2", "-shared", "-fPIC", "-o", str(out), str(UDF / "arc22_core.c"),
                    str(UDF / "arc22_kernel.c"), "-lm"], check=True)
    return out


class ARC22:
    def __init__(self, lib=None):
        self.lib = ctypes.CDLL(str(lib or build()))
        self.lib.arc22_name.restype = ctypes.c_char_p
        self.lib.arc22_W.restype = ctypes.c_double
        self.lib.arc22_h_mass.restype = ctypes.c_double
        self.names = [self.lib.arc22_name(k).decode() for k in range(NSP)]
        self.W = np.array([self.lib.arc22_W(ctypes.c_int(k)) for k in range(NSP)])
        self.opt = Options()
        self.lib.arc22_default_options(ctypes.byref(self.opt))

    def rhs(self, p, y):
        y = np.ascontiguousarray(y, float)
        d = np.zeros(NSP + 1)
        self.lib.arc22_rhs(ctypes.c_double(p), y.ctypes.data_as(ctypes.c_void_p), d.ctypes.data_as(ctypes.c_void_p))
        return d

    def advance(self, Y, T, p, dt):
        Y = np.ascontiguousarray(Y, float).copy()
        info = Info()
        self.lib.arc22_advance(ctypes.byref(self.opt), Y.ctypes.data_as(ctypes.c_void_p), ctypes.c_double(T),
                               ctypes.c_double(p), ctypes.c_double(dt), ctypes.byref(info))
        return Y, info

    def h_mass(self, Y, T):
        Y = np.ascontiguousarray(Y, float)
        return self.lib.arc22_h_mass(Y.ctypes.data_as(ctypes.c_void_p), ctypes.c_double(T))
