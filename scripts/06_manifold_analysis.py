"""Stage 6 (Section 3.3): Global PCA and Vector-Quantized Local PCA manifold diagnostics.

Reads  04_prep/dataset.npz.
Writes 05_manifold/manifold_report.json (explained variance, d_99.5, R2_VQ(d), recommended latent d)
       05_manifold/pca_spectrum.png, 05_manifold/vqpca_r2.png
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import MiniBatchKMeans

from chemmanifold.io import base_parser, load_config, load_npz, save_json, stage_dir


def global_pca(X):
    Xc = X - X.mean(0)
    cov = Xc.T @ Xc / (len(X) - 1)
    evals, evecs = np.linalg.eigh(cov)
    order = np.argsort(evals)[::-1]
    return np.clip(evals[order], 0, None), evecs[:, order]


def vq_pca_r2(X, labels, K, d):
    num = 0.0
    for k in range(K):
        Xk = X[labels == k]
        if len(Xk) <= d:
            continue
        mean = Xk.mean(0)
        _, U = global_pca(Xk)
        Ud = U[:, :d]
        Xhat = mean + (Xk - mean) @ Ud @ Ud.T                 # Eq. 21
        num += np.sum((Xk - Xhat) ** 2)
    return 1.0 - num / np.sum((X - X.mean(0)) ** 2)           # Eq. 22


def main(cfg):
    m = cfg["manifold"]
    ds = load_npz(stage_dir(cfg, "prep") / "dataset.npz")
    X = ds["yt_in"][~ds["is_val"]]
    rng = np.random.default_rng(cfg["seed"] + 3)
    if len(X) > m["max_samples"]:
        X = X[rng.choice(len(X), m["max_samples"], replace=False)]
    Ns = X.shape[1]

    evals, _ = global_pca(X)
    ratio = evals / evals.sum()
    cum = np.cumsum(ratio)
    d_global = int(np.searchsorted(cum, m["variance_target"]) + 1)

    K = m["n_clusters"]
    labels = MiniBatchKMeans(n_clusters=K, random_state=cfg["seed"], n_init=5).fit_predict(X)
    dims = [d for d in m["candidate_dims"] if d < Ns]
    r2 = {d: float(vq_pca_r2(X, labels, K, d)) for d in dims}
    ok = [d for d in dims if r2[d] >= m["variance_target"]]
    d_latent = min(ok) if ok else d_global

    report = dict(
        n_samples=len(X), n_species=Ns, explained_variance_ratio=ratio, cumulative=cum,
        d_global=d_global, vq_clusters=K, vq_cluster_sizes=np.bincount(labels, minlength=K),
        r2_vq={str(d): v for d, v in r2.items()}, recommended_latent_dim=int(d_latent),
    )
    out = stage_dir(cfg, "manifold")
    save_json(out / "manifold_report.json", report)

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.bar(np.arange(1, Ns + 1), ratio, color="#4C72B0", label="per component")
    ax.plot(np.arange(1, Ns + 1), cum, "o-", color="#C44E52", label="cumulative")
    ax.axhline(m["variance_target"], ls="--", c="gray", lw=0.8)
    ax.set(xlabel="principal component", ylabel="explained variance ratio", title=f"Global PCA (d={d_global})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "pca_spectrum.png", dpi=150)

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.plot(dims, [r2[d] for d in dims], "s-", color="#55A868")
    ax.axhline(m["variance_target"], ls="--", c="gray", lw=0.8)
    ax.set(xlabel="local dimension d", ylabel=r"$R^2_{VQ}(d)$", title=f"VQ-PCA (K={K})")
    fig.tight_layout()
    fig.savefig(out / "vqpca_r2.png", dpi=150)
    print(f"  global d_99.5={d_global}, R2_VQ={r2}, recommended latent d={d_latent}")


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))
