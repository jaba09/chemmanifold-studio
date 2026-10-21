"""Hard physics layers (Section 4.1 and 4.2), batched and differentiable, in float64."""

import torch
import torch.nn as nn

RU = 8314.462618


class NullSpaceProjection(nn.Module):
    """Abundance-Weighted Active-Set Null-Space Projection (Eqs. 23-27).

    Maps a raw candidate composition onto {Y >= 0, A Y = A Y0}, moving each species in
    proportion to its own abundance so that absent trace radicals receive no artificial mass.
    """

    def __init__(self, A, n_active=3, w_eps=1e-15, ridge=1e-18):
        super().__init__()
        self.register_buffer("A", torch.as_tensor(A, dtype=torch.float64))
        self.n_active = n_active
        self.w_eps = w_eps
        self.ridge = ridge

    def forward(self, Y0, Y_cand):
        Y0 = Y0.to(torch.float64)
        A = self.A
        Ne = A.shape[0]
        eye = torch.eye(Ne, dtype=torch.float64, device=A.device)
        Y = torch.clamp(Y_cand.to(torch.float64), min=0.0)  # Y0 + dY_raw, Eq. 23
        for _ in range(self.n_active):
            Y = torch.clamp(Y, min=0.0)
            r = (Y - Y0) @ A.T                                   # (B, Ne), Eq. 24
            w = Y + self.w_eps                                   # (B, Ns)
            G = torch.einsum("mk,bk,nk->bmn", A, w, A) + self.ridge * eye  # Eq. 25
            lam = torch.linalg.solve(G, r.unsqueeze(-1)).squeeze(-1)       # Eq. 26
            Y = Y - w * (lam @ A)                                # Eq. 27
        return torch.clamp(Y, min=0.0)


class NasaTemperatureSolver(nn.Module):
    """Vectorized NASA-7 Newton-Raphson recovery of T from (Y, h) (Eqs. 28-31)."""

    def __init__(self, W, T_mid, a_lo, a_hi, n_iter=4, T_bounds=(280.0, 3800.0)):
        super().__init__()
        f64 = dict(dtype=torch.float64)
        self.register_buffer("R", RU / torch.as_tensor(W, **f64))
        self.register_buffer("T_mid", torch.as_tensor(T_mid, **f64))
        self.register_buffer("a_lo", torch.as_tensor(a_lo, **f64))
        self.register_buffer("a_hi", torch.as_tensor(a_hi, **f64))
        self.n_iter = n_iter
        self.T_bounds = T_bounds

    def species_cp_h(self, T):
        """cp_k(T) [J/kg/K] and h_k(T) [J/kg] for a batch of temperatures T (B,)."""
        T = T.unsqueeze(-1)                                     # (B, 1)
        a = self._coeffs(T)                                     # (B, Ns, 7)
        cp = self.R * (a[..., 0] + a[..., 1] * T + a[..., 2] * T**2 + a[..., 3] * T**3 + a[..., 4] * T**4)
        h = self.R * T * (a[..., 0] + a[..., 1] / 2 * T + a[..., 2] / 3 * T**2 + a[..., 3] / 4 * T**3
                          + a[..., 4] / 5 * T**4 + a[..., 5] / T)
        return cp, h

    def _coeffs(self, T):
        hi = (T >= self.T_mid).unsqueeze(-1)                    # (B, Ns, 1)
        return torch.where(hi, self.a_hi, self.a_lo)            # (B, Ns, 7)

    def enthalpy(self, Y, T):
        _, h = self.species_cp_h(T.to(torch.float64))
        return (Y.to(torch.float64) * h).sum(-1)

    def forward(self, Y, h0, T_init):
        Y = Y.to(torch.float64)
        h0 = h0.to(torch.float64)
        T = T_init.to(torch.float64)
        for _ in range(self.n_iter):
            cp_k, h_k = self.species_cp_h(T)
            h_mix = (Y * h_k).sum(-1)
            cp_mix = (Y * cp_k).sum(-1)
            T = torch.clamp(T - (h_mix - h0) / torch.clamp(cp_mix, min=100.0), *self.T_bounds)
        return T
