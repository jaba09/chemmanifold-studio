"""ctypes wrapper of the ARC_GRI30_NOx22 C core (for validation)."""
import ctypes, os
import numpy as np
NODE, NQ, NSP = 22, 21, 43
_lib = ctypes.CDLL(os.environ.get("ARC_LIB", "/tmp/claude-0/libarc.so"))
D = ctypes.POINTER(ctypes.c_double)
_lib.arc_species_name.restype = ctypes.c_char_p
_lib.arc_species_W.restype = ctypes.c_double
names = [_lib.arc_species_name(k).decode() for k in range(NSP)]
W = np.array([_lib.arc_species_W(k) for k in range(NSP)])
def _p(a): return a.ctypes.data_as(D)
def wdot(T, p, c):
    c = np.ascontiguousarray(c, float); w = np.zeros(NODE); x = np.zeros(NQ)
    _lib.arc_wdot(ctypes.c_double(T), ctypes.c_double(p), _p(c), _p(w), _p(x)); return w, x
def wdot_skel(T, c43):
    c = np.ascontiguousarray(c43, float); w = np.zeros(NSP)
    _lib.arc_wdot_skeletal(ctypes.c_double(T), _p(c), _p(w)); return w
def rhs(p, y):
    y = np.ascontiguousarray(y, float); d = np.zeros(NODE + 1)
    _lib.arc_rhs(ctypes.c_double(p), _p(y), _p(d)); return d
def elements(Y):
    Y = np.ascontiguousarray(Y, float); e = np.zeros(4); _lib.arc_elements(_p(Y), _p(e)); return e
def project(Y, el0):
    Y = np.array(Y, float); e = np.ascontiguousarray(el0, float); _lib.arc_project(_p(Y), _p(e)); return Y
