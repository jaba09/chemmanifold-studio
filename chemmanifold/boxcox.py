"""Invertible Box-Cox transform (Eqs. 17-18), for NumPy arrays and torch tensors."""

import numpy as np
import torch

EPS = 1e-15


def boxcox(Y, lam):
    if isinstance(Y, torch.Tensor):
        return ((torch.clamp(Y, min=0.0) + EPS) ** lam - 1.0) / lam
    return ((np.maximum(Y, 0.0) + EPS) ** lam - 1.0) / lam


def inv_boxcox(y, lam):
    if isinstance(y, torch.Tensor):
        base = torch.clamp(lam * y + 1.0, min=EPS)
        return torch.clamp(base ** (1.0 / lam), 0.0, 1.0)
    base = np.maximum(lam * y + 1.0, EPS)
    return np.clip(base ** (1.0 / lam), 0.0, 1.0)
