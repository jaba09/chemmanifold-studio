"""Sparse top-2 mixture of experts with dt as input and dY as output (COVLOOP, docs/COVERAGE-LOOP-ROADMAP.md s. 7).

Design follows the 2026-11-20 Gemini draft "A C1-smooth sparse Top-2 Mixture-of-Experts chemistry integrator"
adapted to our pipeline (ARC22, 22 transported species, wide dt range):

* features   x = [T, shifted Box-Cox(Y)] (lambda 0.1, floor 1e-10), standardised; log10(dt) is a separate input
  that only the experts see (the router reads the state only, so a changing dt cannot switch experts);
* partition  Jacobian-scaled (stiffness-weighted) k-means on the standardised state, clusters sorted by mean T,
  tangential overlap buffers (d_min / d_k >= theta) and an 8-component local PCA per buffered cluster;
* gate       top-2 Hermite C1 gate: w2 = (1-u)^2 (2+u)/4, w1 = 1-w2, u = clip((z1-z2)/tau, 0, 1);
* output     each expert predicts the substep-mean rate R = dY/dt in its own local scaling; dY = dt * R;
* training   three stages (router warm start, buffered experts, joint fine tuning), CPU only;
* export     local scaling folded into the last layer; numpy (BLAS) inference with the tri-modal trust gate
  (local PCA residual, inter-expert L1 discrepancy, positivity), element projection and NASA-7 T inversion.

Training data must come from the physics exploration only (javier-methodology): never pass DI pairs from a CFD
run to `fit`. The trust gate here is also the OOD flag used by the coverage tool (scripts/25_coverage.py).
"""

from dataclasses import dataclass, field, asdict
import json

import numpy as np

BC_LAMBDA = 0.1
BC_FLOOR = 1e-10


# ----------------------------------------------------------------------------------------------- features

def shifted_boxcox(Y, lam=BC_LAMBDA, eps=BC_FLOOR):
    """Shifted Box-Cox: smooth at Y = 0 (no infinite derivative), keeps ~9 decades of dynamic range."""
    return ((np.maximum(Y, 0.0) + eps) ** lam - 1.0) / lam


def raw_features(T, Y):
    return np.column_stack([np.asarray(T, float), shifted_boxcox(np.asarray(Y, float))])


def stiffness_proxy(Y, R, T=None, dTdt=None):
    """Dimensionless stiffness weight psi (paper Eq. 5) from the data alone.

    Chemical part: max_k |R_k| / max(Y_k, 1e-11) (1/s); thermal part |dT/dt| / T when available.
    """
    chem = np.max(np.abs(R) / np.maximum(Y, 1e-11), axis=1)
    therm = 0.0 if dTdt is None else np.abs(dTdt) / np.maximum(T, 1.0)
    return np.log1p(chem * 1e-6 + 10.0 * therm * 1e-6)   # scaled to O(1) for 1 us-1 ms steps


@dataclass
class MoEConfig:
    n_experts: int = 6
    router_hidden: int = 64
    expert_hidden: int = 128
    expert_layers: int = 3
    tau_gate: float = 2.5
    theta_buf: float = 0.80
    alpha_stiff: float = 4.0
    n_pca: int = 8
    gamma_pca: float = 2.4
    pca_quantile: float = 0.995
    disc_limit: float = 0.05
    pos_limit: float = -5e-3
    dt_min: float = 1e-6
    dt_max: float = 1e-3
    T_frozen: float = 450.0
    label_smooth: float = 0.008
    epochs_router: int = 20
    epochs_expert: int = 70
    epochs_joint: int = 120
    lr_router: float = 3e-3
    lr_expert: float = 2.5e-3
    lr_joint_router: float = 4.2e-4
    lr_joint_expert: float = 1.2e-3
    batch: int = 256
    w_local: float = 0.25
    w_anchor: float = 0.05
    w_balance: float = 0.01
    local_weight_cap: float = 25.0
    threads: int = 8
    seed: int = 0
    species: list = field(default_factory=list)


# ----------------------------------------------------------------------------------------------- partition

class Partition:
    """Stiffness-weighted k-means + overlap buffers + local PCA trust regions (on standardised state x~)."""

    def __init__(self, cfg: MoEConfig):
        self.cfg = cfg

    def fit(self, xs, T, psi):
        from sklearn.cluster import KMeans
        c = self.cfg
        km = KMeans(n_clusters=c.n_experts, n_init=20, random_state=c.seed)
        km.fit(xs, sample_weight=1.0 + c.alpha_stiff * psi)
        order = np.argsort([T[km.labels_ == k].mean() for k in range(c.n_experts)])
        self.centroids = km.cluster_centers_[order]
        self.labels = self.assign(xs)
        d = self.distances(xs)
        ratio = d.min(1, keepdims=True) / np.maximum(d, 1e-12)
        self.buffers = [np.where(ratio[:, k] >= c.theta_buf)[0] for k in range(c.n_experts)]
        self.pca_mean, self.pca_U, self.tau_pca = [], [], []
        for b in self.buffers:
            m = xs[b].mean(0)
            _, _, vt = np.linalg.svd(xs[b] - m, full_matrices=False)
            U = vt[: min(c.n_pca, vt.shape[0])]
            r = self._residual(xs[b], m, U)
            self.pca_mean.append(m), self.pca_U.append(U)
            self.tau_pca.append(c.gamma_pca * np.quantile(r, c.pca_quantile))
        self.pca_mean, self.tau_pca = np.array(self.pca_mean), np.array(self.tau_pca)
        self.pca_U = np.stack(self.pca_U)
        return self

    def distances(self, xs):
        return np.linalg.norm(xs[:, None, :] - self.centroids[None], axis=-1)

    def assign(self, xs):
        return self.distances(xs).argmin(1)

    @staticmethod
    def _residual(xs, m, U):
        v = xs - m
        return np.linalg.norm(v - (v @ U.T) @ U, axis=1)

    def pca_ratio(self, xs, k):
        """Residual of each row against expert k's local PCA, divided by its trust threshold (>1 = OOD)."""
        out = np.empty(len(xs))
        for kk in np.unique(k):
            i = k == kk
            out[i] = self._residual(xs[i], self.pca_mean[kk], self.pca_U[kk]) / self.tau_pca[kk]
        return out


# ----------------------------------------------------------------------------------------------- torch model

def _torch():
    import torch
    return torch


def hermite_top2(z, tau):
    """Top-2 Hermite C1 gate on router logits z (B, K): returns (w1, w2, k1, k2)."""
    torch = _torch()
    top, idx = torch.topk(z, 2, dim=-1)
    u = torch.clamp((top[:, 0] - top[:, 1]) / tau, 0.0, 1.0)
    w2 = 0.25 * (1.0 - u) ** 2 * (2.0 + u)
    return 1.0 - w2, w2, idx[:, 0], idx[:, 1]


def build_torch_model(n_feat, n_species, cfg: MoEConfig):
    torch = _torch()
    nn = torch.nn

    def expert():
        layers, d = [], n_feat + 1
        for _ in range(cfg.expert_layers):
            layers += [nn.Linear(d, cfg.expert_hidden), nn.SiLU()]
            d = cfg.expert_hidden
        layers.append(nn.Linear(d, n_species))
        return nn.Sequential(*layers)

    class Top2MoE(nn.Module):
        def __init__(self):
            super().__init__()
            self.router = nn.Sequential(nn.Linear(n_feat, cfg.router_hidden), nn.SiLU(),
                                        nn.Linear(cfg.router_hidden, cfg.n_experts))
            self.experts = nn.ModuleList([expert() for _ in range(cfg.n_experts)])
            # per-expert local -> global output scaling of the rate (fixed buffers, folded at export)
            self.register_buffer("s", torch.ones(cfg.n_experts, n_species))
            self.register_buffer("b", torch.zeros(cfg.n_experts, n_species))

        def expert_out(self, k, xs, ldt):
            """Expert k's rate prediction in GLOBAL standardised units."""
            return self.s[k] * self.experts[k](torch.cat([xs, ldt], -1)) + self.b[k]

        def forward(self, xs, ldt):
            z = self.router(xs)
            w1, w2, k1, k2 = hermite_top2(z, cfg.tau_gate)
            out = torch.zeros(xs.shape[0], self.s.shape[1], dtype=xs.dtype)
            loc = torch.zeros_like(out)
            for k in range(cfg.n_experts):
                for w, kk in ((w1, k1), (w2, k2)):
                    i = (kk == k) & (w > 0)
                    if i.any():
                        e = self.experts[k](torch.cat([xs[i], ldt[i]], -1))
                        out[i] += w[i, None] * (self.s[k] * e + self.b[k])
                        loc[i] += w[i, None] * e
            return out, z, (w1, w2, k1, k2)

    return Top2MoE()


# ----------------------------------------------------------------------------------------------- fit

class MoESurrogate:
    """Train, export and evaluate the dt-in / dY-out top-2 MoE (CPU)."""

    def __init__(self, cfg: MoEConfig):
        self.cfg = cfg

    # --- normalisation
    def _prep(self, T, Y, dt):
        x = raw_features(T, Y)
        return (x - self.x_mu) / self.x_sd, ((np.log10(dt) - self.ldt_mu) / self.ldt_sd)[:, None]

    def fit(self, T, Y, dt, dY, weight=None, psi=None, log=print):
        """T (N,), Y (N, S), dt (N,), dY (N, S): physics-exploration pairs only."""
        torch = _torch()
        c = self.cfg
        torch.manual_seed(c.seed), np.random.seed(c.seed)
        torch.set_num_threads(c.threads)
        N, S = Y.shape
        if not c.species:
            c.species = [f"Y{k}" for k in range(S)]
        R = dY / dt[:, None]
        x = raw_features(T, Y)
        self.x_mu, self.x_sd = x.mean(0), np.where(x.std(0) > 0, x.std(0), 1.0)
        ldt = np.log10(dt)
        self.ldt_mu, self.ldt_sd = ldt.mean(), max(ldt.std(), 1e-6)
        self.R_mu, self.R_sd = R.mean(0), np.where(R.std(0) > 0, R.std(0), 1.0)
        xs, ls = self._prep(T, Y, dt)
        Rs = (R - self.R_mu) / self.R_sd
        psi = stiffness_proxy(Y, R) if psi is None else psi
        w = np.ones(N) if weight is None else np.asarray(weight, float)

        self.part = Partition(c).fit(xs, T, psi)
        K = c.n_experts
        s = np.ones((K, S))
        b = np.zeros((K, S))
        for k, idx in enumerate(self.part.buffers):
            mu_k, sd_k = Rs[idx].mean(0), Rs[idx].std(0)
            s[k] = np.where(sd_k > 1e-12, sd_k, 1.0)
            b[k] = mu_k
        model = build_torch_model(xs.shape[1], S, c).double()
        model.s.copy_(torch.as_tensor(s)), model.b.copy_(torch.as_tensor(b))
        tx, tl, tR = (torch.as_tensor(a) for a in (xs, ls, Rs))
        tw = torch.as_tensor(w)
        lab = torch.as_tensor(self.part.labels)
        hist = {}

        # stage 1A: router warm start on cluster labels
        opt = torch.optim.AdamW(model.router.parameters(), lr=c.lr_router)
        ce = torch.nn.CrossEntropyLoss(label_smoothing=c.label_smooth)
        for ep in range(c.epochs_router):
            for i in torch.randperm(N).split(c.batch):
                opt.zero_grad()
                loss = ce(model.router(tx[i]), lab[i])
                loss.backward(), opt.step()
        acc = (model.router(tx).argmax(1) == lab).double().mean().item()
        hist["router_acc"] = acc
        log(f"[moe] stage 1A router accuracy {acc:.4f}")

        # stage 1B: each expert on its buffered subset, local normalised rate space
        for k, idx in enumerate(self.part.buffers):
            ex = model.experts[k]
            opt = torch.optim.AdamW(ex.parameters(), lr=c.lr_expert)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, max(c.epochs_expert, 1))
            ii = torch.as_tensor(idx)
            tgt = (tR[ii] - model.b[k]) / model.s[k]
            for ep in range(c.epochs_expert):
                for j in torch.randperm(len(ii)).split(c.batch):
                    opt.zero_grad()
                    e = ex(torch.cat([tx[ii[j]], tl[ii[j]]], -1))
                    loss = ((e - tgt[j]) ** 2 * tw[ii[j], None]).mean()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(ex.parameters(), 2.0)
                    opt.step()
                sched.step()
            log(f"[moe] stage 1B expert {k}: n={len(idx)} local MSE {loss.item():.4g}")

        # stage 2: joint fine tuning
        opt = torch.optim.AdamW([{"params": model.router.parameters(), "lr": c.lr_joint_router},
                                 {"params": model.experts.parameters(), "lr": c.lr_joint_expert}])
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, max(c.epochs_joint, 1))
        inv_s = torch.clamp(1.0 / model.s, max=c.local_weight_cap)
        for ep in range(c.epochs_joint):
            for i in torch.randperm(N).split(c.batch):
                opt.zero_grad()
                out, z, (w1, w2, k1, k2) = model(tx[i], tl[i])
                err = out - tR[i]
                l_glob = (err ** 2 * tw[i, None]).mean()
                l_loc = ((err * (w1[:, None] * inv_s[k1] + w2[:, None] * inv_s[k2])) ** 2).mean()
                l_ce = ce(z, lab[i])
                p = torch.softmax(z, -1).mean(0)
                frac = torch.zeros(K, dtype=z.dtype).index_add_(0, k1, w1).index_add_(0, k2, w2) / len(i)
                l_bal = K * (p * frac).sum()
                loss = l_glob + c.w_local * l_loc + c.w_anchor * l_ce + c.w_balance * l_bal
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
                opt.step()
            sched.step()
            if ep % max(1, c.epochs_joint // 10) == 0 or ep == c.epochs_joint - 1:
                log(f"[moe] stage 2 epoch {ep + 1}/{c.epochs_joint} glob {l_glob.item():.4g} loc {l_loc.item():.4g}")
        hist["final_glob_mse"] = l_glob.item()
        self.torch_model, self.history = model, hist
        self.export_arrays()
        return self

    # --- export
    def export_arrays(self):
        """Fold the global de-standardisation and per-expert scaling into each expert's last layer.

        Exported expert k returns the PHYSICAL rate R (1/s) directly: R = W_k h + d_k.
        """
        m, c = self.torch_model, self.cfg
        arr = {"x_mu": self.x_mu, "x_sd": self.x_sd, "ldt": np.array([self.ldt_mu, self.ldt_sd]),
               "centroids": self.part.centroids, "pca_mean": self.part.pca_mean, "pca_U": self.part.pca_U,
               "tau_pca": self.part.tau_pca,
               "cfg": np.array([c.tau_gate, c.disc_limit, c.pos_limit, c.dt_min, c.dt_max, c.T_frozen])}
        r = [l for l in m.router if hasattr(l, "weight")]
        arr["r_W0"], arr["r_b0"] = r[0].weight.detach().numpy(), r[0].bias.detach().numpy()
        arr["r_W1"], arr["r_b1"] = r[1].weight.detach().numpy(), r[1].bias.detach().numpy()
        for k, ex in enumerate(m.experts):
            lin = [l for l in ex if hasattr(l, "weight")]
            for j, l in enumerate(lin[:-1]):
                arr[f"e{k}_W{j}"], arr[f"e{k}_b{j}"] = l.weight.detach().numpy(), l.bias.detach().numpy()
            W, d = lin[-1].weight.detach().numpy(), lin[-1].bias.detach().numpy()
            s, b = m.s[k].numpy(), m.b[k].numpy()
            # R = R_sd * (s * (W h + d) + b) + R_mu
            g = self.R_sd * s
            arr[f"e{k}_W{len(lin) - 1}"] = W * g[:, None]
            arr[f"e{k}_b{len(lin) - 1}"] = g * d + self.R_sd * b + self.R_mu
        arr["n_layers"] = np.array([len(lin)])
        self.arrays = arr
        return arr

    def save(self, path_npz):
        np.savez(path_npz, **self.arrays)
        meta = {"format": "covloop-moe-v3", "species": self.cfg.species, "config": asdict(self.cfg),
                "history": getattr(self, "history", {})}
        with open(str(path_npz).replace(".npz", ".json"), "w") as f:
            json.dump(meta, f, indent=1)

    def torch_rate(self, T, Y, dt):
        """Physical rate from the torch model (for parity tests)."""
        torch = _torch()
        xs, ls = self._prep(T, Y, dt)
        with torch.no_grad():
            out, _, _ = self.torch_model(torch.as_tensor(xs), torch.as_tensor(ls))
        return out.numpy() * self.R_sd + self.R_mu


# ----------------------------------------------------------------------------------------------- numpy inference

def _silu(a):
    return a / (1.0 + np.exp(-a))


class CPUFastMoE:
    """Dependency-free numpy/BLAS inference of an exported model (same maths as the planned C++ loader)."""

    def __init__(self, arrays):
        self.a = dict(arrays)
        self.nl = int(self.a["n_layers"][0])
        self.K = self.a["centroids"].shape[0]
        self.tau, self.disc_limit, self.pos_limit, self.dt_min, self.dt_max, self.T_frozen = self.a["cfg"]

    @classmethod
    def load(cls, path_npz):
        return cls(np.load(path_npz))

    def features(self, T, Y, dt):
        xs = (raw_features(T, Y) - self.a["x_mu"]) / self.a["x_sd"]
        mu, sd = self.a["ldt"]
        return xs, ((np.log10(dt) - mu) / sd)[:, None]

    def _expert(self, k, xs, ls):
        h = np.concatenate([xs, ls], 1)
        for j in range(self.nl):
            h = h @ self.a[f"e{k}_W{j}"].T + self.a[f"e{k}_b{j}"]
            if j < self.nl - 1:
                h = _silu(h)
        return h

    def rate(self, T, Y, dt):
        """Physical rate R (N, S), gate info, and the trust flags of the tri-modal gate."""
        xs, ls = self.features(T, Y, dt)
        z = _silu(xs @ self.a["r_W0"].T + self.a["r_b0"]) @ self.a["r_W1"].T + self.a["r_b1"]
        idx = np.argsort(-z, 1)[:, :2]
        k1, k2 = idx[:, 0], idx[:, 1]
        zz = np.take_along_axis(z, idx, 1)
        u = np.clip((zz[:, 0] - zz[:, 1]) / self.tau, 0.0, 1.0)
        w2 = 0.25 * (1.0 - u) ** 2 * (2.0 + u)
        w1 = 1.0 - w2
        R = np.zeros((len(xs), self.a[f"e0_b{self.nl - 1}"].shape[0]))
        R2 = np.zeros_like(R)
        for k in range(self.K):
            i = k1 == k
            if i.any():
                R[i] += w1[i, None] * (e := self._expert(k, xs[i], ls[i]))
            j = (k2 == k) & (w2 > 0)
            if j.any():
                e2 = self._expert(k, xs[j], ls[j])
                R[j] += w2[j, None] * e2
                R2[j] = e2
        # trust gate (1): local PCA residual
        r1 = self._pca_ratio(xs, k1)
        boundary = w2 > 0
        pca_ood = r1 > 1.0
        if boundary.any():
            r2 = self._pca_ratio(xs[boundary], k2[boundary])
            pca_ood[boundary] = np.minimum(r1[boundary], r2) > 1.0
        info = {"k1": k1, "k2": k2, "w1": w1, "w2": w2, "pca_ratio": r1, "pca_ood": pca_ood,
                "boundary": boundary}
        # (2) inter-expert discrepancy, needs expert-1 output on boundary cells
        disc = np.zeros(len(xs))
        if boundary.any():
            b = np.where(boundary)[0]
            e1 = np.stack([self._expert(k1[i], xs[i:i + 1], ls[i:i + 1])[0] for i in b])
            disc[b] = np.abs((e1 - R2[b]) * dt[b, None]).sum(1)
        info["disc"] = disc
        return R, info

    def _pca_ratio(self, xs, k):
        out = np.empty(len(xs))
        for kk in np.unique(k):
            i = k == kk
            v = xs[i] - self.a["pca_mean"][kk]
            U = self.a["pca_U"][kk]
            out[i] = np.linalg.norm(v - (v @ U.T) @ U, axis=1) / self.a["tau_pca"][kk]
        return out

    def step(self, T, Y, dt, A=None):
        """One chemistry step: Y_new (projected if element matrix A given) and the trust mask (True = DI fallback)."""
        T, Y, dt = np.asarray(T, float), np.asarray(Y, float), np.asarray(dt, float)
        Y_new, fallback = Y.copy(), np.zeros(len(T), bool)
        act = T >= self.T_frozen
        out_dt = (dt < self.dt_min * (1 - 1e-9)) | (dt > self.dt_max * (1 + 1e-9))
        if act.any():
            R, info = self.rate(T[act], Y[act], dt[act])
            Yc = Y[act] + dt[act, None] * R
            fb = info["pca_ood"] | (info["disc"] > self.disc_limit) | (Yc.min(1) < self.pos_limit) | out_dt[act]
            if A is not None:
                Yc = project_elements(Y[act], Yc, A)
            Y_new[act] = Yc
            fallback[act] = fb
        return Y_new, fallback


def project_elements(Y0, Yc, A, n_iter=3, w_eps=1e-15):
    """Abundance-weighted active-set projection onto {Y >= 0, A Y = A Y0} (numpy twin of physics.NullSpaceProjection)."""
    Y = np.maximum(Yc, 0.0)
    for _ in range(n_iter):
        Y = np.maximum(Y, 0.0)
        r = (Y - Y0) @ A.T
        w = Y + w_eps
        G = np.einsum("mk,bk,nk->bmn", A, w, A) + 1e-18 * np.eye(A.shape[0])
        lam = np.linalg.solve(G, r[..., None])[..., 0]
        Y = Y - w * (lam @ A)
    return np.maximum(Y, 0.0)
