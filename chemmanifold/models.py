"""Surrogate architectures (Section 4.3, 4.4) wrapped with encoding and hard physics layers."""

import numpy as np
import torch
import torch.nn as nn

from .boxcox import boxcox, inv_boxcox
from .physics import NasaTemperatureSolver, NullSpaceProjection


def mlp(n_in, n_hidden, n_out, n_layers=2):
    layers, d = [], n_in
    for _ in range(n_layers):
        layers += [nn.Linear(d, n_hidden), nn.SiLU()]
        d = n_hidden
    layers.append(nn.Linear(d, n_out))
    return nn.Sequential(*layers)


class FiLMBlock(nn.Module):
    """One FiLM-modulated residual block (Eqs. 33-36)."""

    def __init__(self, hidden, n_ctx=4):
        super().__init__()
        self.film = nn.Linear(n_ctx, 2 * hidden)
        self.lin1 = nn.Linear(hidden, hidden)
        self.norm = nn.LayerNorm(hidden)
        self.lin2 = nn.Linear(hidden, hidden)
        self.act = nn.SiLU()

    def forward(self, h, c):
        gamma, beta = self.film(c).chunk(2, dim=-1)
        u = self.act(self.norm(self.lin1(h)))
        u = u * (1.0 + gamma) + beta
        return h + self.act(self.lin2(u))


class ResNetFiLM(nn.Module):
    """Architecture A: variable-dt FiLM-modulated residual network."""

    def __init__(self, n_species, hidden=192, n_blocks=3, n_ctx=4):
        super().__init__()
        self.inp = nn.Linear(n_species + n_ctx, hidden)
        self.blocks = nn.ModuleList([FiLMBlock(hidden, n_ctx) for _ in range(n_blocks)])
        self.out = nn.Linear(hidden, n_species)
        nn.init.zeros_(self.out.weight)  # start as the identity map: dy = 0
        nn.init.zeros_(self.out.bias)
        self.act = nn.SiLU()

    def forward(self, yt, c, dt_star):
        h = self.act(self.inp(torch.cat([yt, c], dim=-1)))   # Eq. 32
        for blk in self.blocks:
            h = blk(h, c)
        return yt + self.out(h), {}                            # Eq. 37


class PhyChemNODE(nn.Module):
    """Architecture B: manifold autoencoder + latent neural ODE integrated with RK4."""

    def __init__(self, n_species, latent_dim=4, hidden=128, n_substeps=2):
        super().__init__()
        self.encoder = mlp(n_species + 1, hidden, latent_dim)
        self.field = mlp(latent_dim + 2, hidden, latent_dim)
        self.decoder = mlp(latent_dim, hidden, n_species)
        self.n_substeps = n_substeps
        last = self.field[-1]
        nn.init.normal_(last.weight, std=1e-3)
        nn.init.zeros_(last.bias)

    def f(self, z, ph):
        return self.field(torch.cat([z, ph], dim=-1))

    def forward(self, yt, c, dt_star):
        z0 = self.encoder(torch.cat([yt, c[:, :1]], dim=-1))  # E([y~; T~])
        ph = c[:, 1:3]                                          # (P~, h~)
        hs = (dt_star / self.n_substeps).unsqueeze(-1)
        z = z0
        for _ in range(self.n_substeps):                        # Eqs. 38-40
            k1 = self.f(z, ph)
            k2 = self.f(z + 0.5 * hs * k1, ph)
            k3 = self.f(z + 0.5 * hs * k2, ph)
            k4 = self.f(z + hs * k3, ph)
            z = z + hs / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        d0 = self.decoder(z0)
        y_cand = yt + (self.decoder(z) - d0)                    # Eq. 41
        return y_cand, {"ae_recon": d0}


class Surrogate(nn.Module):
    """F_theta: (Y, T, P, h, dt) -> (Y_hat, T_hat) with Box-Cox/z-score encoding and hard physics."""

    def __init__(self, net, scalers, thermo):
        super().__init__()
        self.net = net
        f64 = dict(dtype=torch.float64)
        self.lam = float(scalers["boxcox_lambda"])
        self.dt_base = float(scalers["dt_base"])
        for k in ("mu_y", "sigma_y", "ctx_mu", "ctx_sigma", "sigma_dy"):
            self.register_buffer(k, torch.as_tensor(np.asarray(scalers[k]), **f64))
        self.project = NullSpaceProjection(thermo["A"])
        self.temperature = NasaTemperatureSolver(thermo["W"], thermo["T_mid"], thermo["a_lo"], thermo["a_hi"])

    def encode_Y(self, Y):
        return (boxcox(Y.to(torch.float64), self.lam) - self.mu_y) / self.sigma_y

    def decode_Y(self, yt):
        return inv_boxcox(yt.to(torch.float64) * self.sigma_y + self.mu_y, self.lam)

    def context(self, T, P, h, dt):
        raw = torch.stack([T, P, h, torch.log10(dt)], dim=-1).to(torch.float64)
        return (raw - self.ctx_mu) / self.ctx_sigma

    def forward(self, Y, T, P, h, dt):
        yt = self.encode_Y(Y)
        c = self.context(T, P, h, dt)
        dt_star = dt / self.dt_base
        # The network may live on an accelerator (CUDA / Apple MPS) in float32, while the
        # encoding and hard physics layers always stay in float64 on the CPU (MPS has no float64).
        p = next(self.net.parameters())
        y_cand, extras = self.net(yt.to(p.device, p.dtype), c.to(p.device, p.dtype), dt_star.to(p.device, p.dtype))
        y_cand = y_cand.to(yt.device, torch.float64)
        extras = {k: v.to(yt.device, torch.float64) for k, v in extras.items()}
        Y_cand = self.decode_Y(y_cand)
        Y_phys = self.project(Y, Y_cand)
        T_hat = self.temperature(Y_phys, h, T)
        return {"Y": Y_phys, "T": T_hat, "Y_cand": Y_cand, "yt_cand": y_cand, "yt_in": yt, "extras": extras}

    @torch.no_grad()
    def project_state(self, Y_ref, yt_noisy, h, T_init):
        """Decode a perturbed Box-Cox state and project it onto the polytope of Y_ref (Section 5.2)."""
        Y = self.project(Y_ref, self.decode_Y(yt_noisy))
        return Y, self.temperature(Y, h, T_init)


def resolve_device(name="auto"):
    """'auto' -> CPU unless CUDA is present. Apple MPS must be asked for explicitly: for networks of
    this size (~0.2M parameters) the per-batch CPU<->GPU transfers needed by the float64 physics
    layers usually make MPS slower than the M1's CPU cores."""
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if name == "mps" and not torch.backends.mps.is_available():
        print("  MPS requested but not available - falling back to CPU")
        return torch.device("cpu")
    return torch.device(name)


def build_surrogate(arch, cfg, scalers, thermo, latent_dim=4):
    Ns = len(scalers["mu_y"])
    m = cfg["model"]
    if arch == "resnet_film":
        net = ResNetFiLM(Ns, hidden=m["hidden"], n_blocks=m["n_blocks"])
    elif arch == "chemnode":
        net = PhyChemNODE(Ns, latent_dim=latent_dim, hidden=m["node_hidden"], n_substeps=m["node_substeps"])
    else:
        raise ValueError(f"unknown architecture {arch!r}")
    return Surrogate(net, scalers, thermo)
