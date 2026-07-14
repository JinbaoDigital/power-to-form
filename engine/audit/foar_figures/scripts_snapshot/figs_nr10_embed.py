"""
figs_nr10_embed.py — NEXT_RUN_10, Task E (SUPPLEMENTARY): the MAP stage, seen in latent space.

    python3 figs_nr10_embed.py e1 | e2 | e3 | all

The loop is READ -> MAP -> TRANSFORM -> READ BACK.  figs_cake / figs_nr10 draw the transform and the
read-back.  This sheet draws the MAP: the step where a building's metadata (what the survey happens to
record about it) becomes a stakeholder, a weakness score, and therefore a position in the queue of things
that can be taken.  We put every building of all eight sites into one feature vector, project it to 2D,
and colour it by the readings the model makes from it.

The feature vector per building (nothing here is invented; every column is already computed by
pf_common / cake / measure):
    physical block (7)   log h, log footprint area, log GFA, log slenderness h/sqrt(area),
                         AGE (cake's clamped age term), age_known, FAR_actual (cake.far_actual,
                         = site coverage * h / floor_h)
    metadata block (14)  FAR_allowed (cake.far_allowed, a lookup on EULUC), FAR_GAP, weakness score,
                         and the EULUC land-use one-hot (10 classes + unlabelled)

Two feature sets are embedded, and the difference between them IS the finding:
    ALL   = physical + metadata      (what the model actually reads)
    PHYS  = physical only            (what the building itself looks like)

Method notes.  PCA is sklearn.  The autoencoder and the beta-VAE are written in numpy (no torch in the
engine env); the VAE follows the hyper-parameters of data_collection/generative/vae_manifold.py
(beta = 0.05, Adam 2e-3, tanh MLP, Gaussian latent) so the two projects stay comparable.  Those scripts
themselves do not transfer: they embed 100 m cells of a tile, not single buildings.

Writes only into out/cake_figs/  (E1, E2, E3 png + E_embed_stats.json).  metrics_cake.json,
invariance.csv, the frozen site outputs and paper/figures/cake/ are never touched.
"""
import sys
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Patch
from matplotlib.gridspec import GridSpec
from matplotlib import font_manager

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, balanced_accuracy_score, recall_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_predict

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pf_common as C            # noqa: E402  (SH_COLOR, STAKEHOLDERS, load_buildings)
import measure as M              # noqa: E402  (diagnose -> coverage)
import cake                      # noqa: E402  (load_cfg, far_allowed, far_actual, weakness_score)

OUT = HERE / "out" / "cake_figs"
OUT.mkdir(parents=True, exist_ok=True)

DPI = 160
INK = "#1c1c1c"
SEED = 0

CJK = "Noto Sans CJK JP"
_have_cjk = CJK in {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams.update({
    "font.family": ([CJK] if _have_cjk else []) + ["DejaVu Sans"],
    "axes.unicode_minus": False,
    "axes.linewidth": 0.6,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
})

SITES = ["lujiazui", "nanjingxi", "caoyang", "pengpu", "laoximen", "yuyuan", "dapuqiao", "zhangjiang"]
FAMILY = {"lujiazui": "capital", "nanjingxi": "capital", "caoyang": "danwei", "pengpu": "danwei",
          "laoximen": "lilong", "yuyuan": "lilong", "dapuqiao": "lilong", "zhangjiang": "industry"}
FAM_COLOR = {"capital": "#b5432f", "danwei": "#3f6fa8", "lilong": "#4f8f63", "industry": "#8a6d9c"}
SITE_COLOR = {"lujiazui": "#8f2f1e", "nanjingxi": "#d4735c",
              "caoyang": "#2c5182", "pengpu": "#7ba0cd",
              "laoximen": "#2f6b45", "yuyuan": "#4f8f63", "dapuqiao": "#8fc19f",
              "zhangjiang": "#8a6d9c"}
SH_ORDER = ["resident", "developer", "state", "unknown"]      # drawn largest class first

# EULUC class -> family, and the English label used on the sheets
EU_FAM = {
    "居住用地": "residential", "商务办公用地": "commerce / office", "商业服务用地": "commerce / office",
    "工业用地": "industry", "行政办公用地": "civic / institutional", "教育科研用地": "civic / institutional",
    "医疗卫生用地": "civic / institutional", "体育与文化用地": "civic / institutional",
    "交通场站用地": "civic / institutional", "公园与绿地用地": "park / green", "NA": "unlabelled",
}
EUF_COLOR = {"residential": "#5a9367", "commerce / office": "#c0654a", "industry": "#8a6d9c",
             "civic / institutional": "#4a6fa5", "park / green": "#69a86b", "unlabelled": "#b8b8b8"}
EU_EN = {
    "居住用地": "residential", "商务办公用地": "business office", "商业服务用地": "commercial service",
    "工业用地": "industrial", "行政办公用地": "gov / admin", "教育科研用地": "education / research",
    "医疗卫生用地": "medical", "体育与文化用地": "sport / culture", "交通场站用地": "transport",
    "公园与绿地用地": "park / green", "NA": "unlabelled",
}
FEAT_EN = {
    "log_h": "log height", "log_area": "log footprint area", "log_gfa": "log GFA",
    "slender": "log slenderness h/sqrt(A)", "AGE": "AGE  (weakness age term)",
    "age_known": "age recorded (0/1)", "far_actual": "FAR_actual  (coverage*h/floor_h)",
    "far_allowed": "FAR_allowed  (EULUC lookup)", "GAP": "FAR_GAP", "weakness": "weakness score",
}

PHYS = ["log_h", "log_area", "log_gfa", "slender", "AGE", "age_known", "far_actual"]
REG = ["far_allowed", "GAP", "weakness"]


# --------------------------------------------------------------------- 1  the feature table
def build_table():
    """every building of all eight sites, with exactly the columns cake reads when it maps."""
    cfg = cake.load_cfg()
    yr, ref = cfg["meta"]["year_now"], cfg["meta"]["age_ref"]
    rows = []
    for s in SITES:
        recs = C.load_buildings(s)
        cov = M.diagnose([dict(r) for r in recs], s)["coverage"]
        for r in recs:
            fa = cake.far_allowed(r, cfg)
            fact = cake.far_actual(r, cfg, cov)
            AGE = min(max((yr - r["age"]) / ref, 0.0), 1.0) if r.get("age") else 0.0
            GAP = min(max((fa - fact) / fa, 0.0), 1.0) if fa > 0 else 0.0
            rows.append({
                "site": s, "family": FAMILY[s], "bid": r["bid"], "sh": r["sh"],
                "euluc": r["euluc"] if r["euluc"] else "NA",
                "h": r["h"], "area": r["area"], "coverage": cov,
                "log_h": np.log1p(r["h"]), "log_area": np.log1p(r["area"]),
                "log_gfa": np.log1p(r["area"] * r["h"]),
                "slender": np.log1p(r["h"] / np.sqrt(r["area"])),
                "AGE": AGE, "age_known": float(bool(r.get("age"))), "far_actual": fact,
                "far_allowed": fa, "GAP": GAP,
                "weakness": cake.weakness_score(r, cfg, cov, None),   # missing_age = zero, as configured
            })
    df = pd.DataFrame(rows)
    df["eu_fam"] = df["euluc"].map(EU_FAM).fillna("unlabelled")
    return df


def feature_matrix(df, block="all"):
    cols = list(PHYS)
    if block == "all":
        cols += REG
        F = df[cols].copy()
        for e in EU_LEVELS:
            F["eu:" + e] = (df["euluc"] == e).astype(float)
    else:
        F = df[cols].copy()
    X = StandardScaler().fit_transform(F.values)
    return F.columns.tolist(), X


# --------------------------------------------------------------------- 2  numpy AE / beta-VAE
def _adam(params, grads, state, lr=2e-3, b1=0.9, b2=0.999, eps=1e-8):
    state["t"] += 1
    t = state["t"]
    for i, (p, g) in enumerate(zip(params, grads)):
        state["m"][i] = b1 * state["m"][i] + (1 - b1) * g
        state["v"][i] = b2 * state["v"][i] + (1 - b2) * g ** 2
        p -= lr * (state["m"][i] / (1 - b1 ** t)) / (np.sqrt(state["v"][i] / (1 - b2 ** t)) + eps)


def _init(shapes, rng):
    P = []
    for a, b in shapes:
        P.append(rng.normal(0, np.sqrt(2.0 / a), (a, b)))
        P.append(np.zeros(b))
    return P


def _state(P):
    return {"t": 0, "m": [np.zeros_like(p) for p in P], "v": [np.zeros_like(p) for p in P]}


def train_ae(X, z=2, h1=64, h2=32, epochs=450, batch=512, lr=2e-3, seed=SEED):
    """deterministic autoencoder, tanh MLP, 2D bottleneck. same shape as the sibling project's VAE."""
    rng = np.random.default_rng(seed)
    D = X.shape[1]
    P = _init([(D, h1), (h1, h2), (h2, z), (z, h2), (h2, h1), (h1, D)], rng)
    st = _state(P)
    N = len(X)

    def fwd(x):
        W0, b0, W1, b1_, W2, b2_, W3, b3, W4, b4, W5, b5 = P
        a0 = np.tanh(x @ W0 + b0)
        a1 = np.tanh(a0 @ W1 + b1_)
        Z = a1 @ W2 + b2_
        d0 = np.tanh(Z @ W3 + b3)
        d1 = np.tanh(d0 @ W4 + b4)
        xr = d1 @ W5 + b5
        return a0, a1, Z, d0, d1, xr

    for _ in range(epochs):
        idx = rng.permutation(N)
        for i in range(0, N, batch):
            xb = X[idx[i:i + batch]]
            a0, a1, Z, d0, d1, xr = fwd(xb)
            m = xb.shape[0] * D
            g = 2.0 * (xr - xb) / m                       # dL/dxr
            gW5 = d1.T @ g; gb5 = g.sum(0)
            g = (g @ P[10].T) * (1 - d1 ** 2)
            gW4 = d0.T @ g; gb4 = g.sum(0)
            g = (g @ P[8].T) * (1 - d0 ** 2)
            gW3 = Z.T @ g; gb3 = g.sum(0)
            g = g @ P[6].T                                # dL/dZ
            gW2 = a1.T @ g; gb2 = g.sum(0)
            g = (g @ P[4].T) * (1 - a1 ** 2)
            gW1 = a0.T @ g; gb1 = g.sum(0)
            g = (g @ P[2].T) * (1 - a0 ** 2)
            gW0 = xb.T @ g; gb0 = g.sum(0)
            _adam(P, [gW0, gb0, gW1, gb1, gW2, gb2, gW3, gb3, gW4, gb4, gW5, gb5], st, lr=lr)
    *_, Z, _, _, xr = fwd(X)
    r2 = 1.0 - ((X - xr) ** 2).sum() / ((X - X.mean(0)) ** 2).sum()
    return Z, float(r2)


def train_vae(X, z=2, h1=64, h2=32, epochs=450, batch=512, lr=2e-3, beta=0.05, seed=SEED):
    """beta-VAE, Gaussian latent. beta / lr / architecture follow generative/vae_manifold.py.
    Returns the posterior mean mu (the usual embedding) and the reconstruction R^2 at mu."""
    rng = np.random.default_rng(seed)
    D = X.shape[1]
    P = _init([(D, h1), (h1, h2), (h2, z), (h2, z), (z, h2), (h2, h1), (h1, D)], rng)
    st = _state(P)
    N = len(X)

    def enc(x):
        W0, b0, W1, b1_, Wm, bm, Wl, bl = P[:8]
        a0 = np.tanh(x @ W0 + b0)
        a1 = np.tanh(a0 @ W1 + b1_)
        return a0, a1, a1 @ Wm + bm, a1 @ Wl + bl

    def dec(Z):
        W3, b3, W4, b4, W5, b5 = P[8:]
        d0 = np.tanh(Z @ W3 + b3)
        d1 = np.tanh(d0 @ W4 + b4)
        return d0, d1, d1 @ W5 + b5

    for _ in range(epochs):
        idx = rng.permutation(N)
        for i in range(0, N, batch):
            xb = X[idx[i:i + batch]]
            nb = xb.shape[0]
            a0, a1, mu, lv = enc(xb)
            lv = np.clip(lv, -8.0, 8.0)
            eps = rng.normal(size=mu.shape)
            sig = np.exp(0.5 * lv)
            Z = mu + eps * sig
            d0, d1, xr = dec(Z)
            m = nb * D
            g = 2.0 * (xr - xb) / m
            gW5 = d1.T @ g; gb5 = g.sum(0)
            g = (g @ P[12].T) * (1 - d1 ** 2)
            gW4 = d0.T @ g; gb4 = g.sum(0)
            g = (g @ P[10].T) * (1 - d0 ** 2)
            gW3 = Z.T @ g; gb3 = g.sum(0)
            gZ = g @ P[8].T
            k = nb * z                                    # KL is a mean over elements, as in vae_manifold
            gmu = gZ + beta * mu / k
            glv = gZ * (0.5 * eps * sig) + beta * (-0.5) * (1.0 - np.exp(lv)) / k
            gWm = a1.T @ gmu; gbm = gmu.sum(0)
            gWl = a1.T @ glv; gbl = glv.sum(0)
            g = (gmu @ P[4].T + glv @ P[6].T) * (1 - a1 ** 2)
            gW1 = a0.T @ g; gb1 = g.sum(0)
            g = (g @ P[2].T) * (1 - a0 ** 2)
            gW0 = xb.T @ g; gb0 = g.sum(0)
            _adam(P, [gW0, gb0, gW1, gb1, gWm, gbm, gWl, gbl, gW3, gb3, gW4, gb4, gW5, gb5], st, lr=lr)
    _, _, mu, _ = enc(X)
    _, _, xr = dec(mu)
    r2 = 1.0 - ((X - xr) ** 2).sum() / ((X - X.mean(0)) ** 2).sum()
    return mu, float(r2)


# --------------------------------------------------------------------- 3  the quantitative read
def purity(Z, y, k=10):
    """5-fold cross-validated k-NN class purity in the embedding. Accuracy is dominated by the
    resident majority (59.7%), so balanced accuracy and per-class recall are reported with it."""
    yp = cross_val_predict(KNeighborsClassifier(k), Z, y, cv=5)
    labs = ["state", "developer", "resident", "unknown"]
    rec = recall_score(y, yp, average=None, labels=labs, zero_division=0)
    return {"acc": float((yp == y).mean()), "bal_acc": float(balanced_accuracy_score(y, yp)),
            "recall": {l: float(v) for l, v in zip(labs, rec)}}


def sil(Z, labels, n=6000):
    return float(silhouette_score(Z, labels, sample_size=min(n, len(Z)), random_state=SEED))


# --------------------------------------------------------------------- 4  drawing helpers
def scatter_by(ax, Z, keys, order, colors, s=4.5, alpha=0.5):
    for k in order:
        m = keys == k
        if not m.any():
            continue
        ax.scatter(Z[m, 0], Z[m, 1], s=s, c=colors[k], alpha=alpha, linewidths=0, rasterized=True)


def ellipse(ax, Z, m, color, nsig=2.0):
    """2-sigma covariance ellipse of one class: makes the overlap of the classes readable."""
    P = Z[m]
    if len(P) < 20:
        return
    mu = P.mean(0)
    cov = np.cov(P.T)
    w, v = np.linalg.eigh(cov)
    ang = np.degrees(np.arctan2(v[1, -1], v[0, -1]))
    e = Ellipse(mu, nsig * 2 * np.sqrt(max(w[-1], 1e-9)), nsig * 2 * np.sqrt(max(w[0], 1e-9)),
                angle=ang, fill=False, edgecolor=color, lw=1.5, ls="--", alpha=0.95, zorder=5)
    ax.add_patch(e)
    ax.plot(*mu, marker="o", ms=5, mfc=color, mec="white", mew=1.0, zorder=6)


def bare(ax, xl, yl):
    ax.set_xlabel(xl, fontsize=8, labelpad=2)
    ax.set_ylabel(yl, fontsize=8, labelpad=2)
    ax.tick_params(labelsize=7, length=2)
    for s_ in ax.spines.values():
        s_.set_color("#cccccc")


def foot(fig, txt, y=0.012):
    fig.text(0.045, y, txt, fontsize=7.6, color="#666", va="bottom", linespacing=1.5)


SUPP = "SUPPLEMENTARY  ·  NEXT_RUN_10 Task E  ·  8 sites, %d buildings, real cached data only"


# --------------------------------------------------------------------- E1
def e1(S):
    df, ZA, pca, cols = S["df"], S["Z_all"], S["pca_all"], S["cols_all"]
    evr = pca.explained_variance_ratio_
    fig = plt.figure(figsize=(15.0, 6.7))
    gs = GridSpec(2, 3, width_ratios=[2.35, 0.82, 0.82], height_ratios=[1, 1],
                  left=0.045, right=0.985, top=0.95, bottom=0.085, wspace=0.42, hspace=0.55)
    ax = fig.add_subplot(gs[:, 0])
    y = df["sh"].values
    scatter_by(ax, ZA, y, SH_ORDER, C.SH_COLOR, s=4.5, alpha=0.45)
    for k in SH_ORDER:
        ellipse(ax, ZA, y == k, C.SH_COLOR[k])
    bare(ax, "PC1  (%.1f%% of variance)" % (evr[0] * 100), "PC2  (%.1f%% of variance)" % (evr[1] * 100))
    n = df["sh"].value_counts()
    leg = [Patch(fc=C.SH_COLOR[k], ec="none",
                 label="%s   n=%d  (%.1f%%)" % (k, n.get(k, 0), 100 * n.get(k, 0) / len(df)))
           for k in SH_ORDER]
    leg.append(Patch(fc=C.SH_COLOR["informal"], ec="none", label="informal   n=0  (no signal in this data)"))
    ax.legend(handles=leg, fontsize=8, loc="upper left", frameon=False, handlelength=1.0, borderpad=0.2)
    ax.text(0.985, 0.02, "dashed = 2-sigma ellipse of each class", transform=ax.transAxes,
            fontsize=7.4, color="#777", ha="right")

    # loadings
    for j, pc in enumerate((0, 1)):
        for r, sel in enumerate(("phys", "meta")):
            axl = fig.add_subplot(gs[r, 1 + j])
            keep = [c for c in cols if (c.startswith("eu:") if sel == "meta" else not c.startswith("eu:"))]
            L = pd.Series(pca.components_[pc], index=cols)[keep]
            L = L.reindex(L.abs().sort_values(ascending=False).index)[:9][::-1]
            labels = [EU_EN.get(c[3:], c[3:]) + "  (EULUC)" if c.startswith("eu:") else FEAT_EN.get(c, c)
                      for c in L.index]
            axl.barh(range(len(L)), L.values, color=["#c0654a" if v < 0 else "#4a6fa5" for v in L.values],
                     height=0.68)
            axl.set_yticks(range(len(L)))
            axl.set_yticklabels(labels, fontsize=6.6)
            axl.axvline(0, color="#999", lw=0.6)
            axl.tick_params(axis="x", labelsize=6.4, length=2)
            axl.set_xlim(-0.62, 0.62)
            for s_ in axl.spines.values():
                s_.set_color("#dddddd")
            axl.set_title("PC%d loadings · %s" % (pc + 1, "form / age columns" if sel == "phys" else "land-use one-hot"),
                          fontsize=7.6, color=INK, loc="left", pad=4)

    p = OUT / "E1_pca_stakeholder.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("E1 ->", p)


# --------------------------------------------------------------------- E2
def e2(S):
    df, ZA, pca = S["df"], S["Z_all"], S["pca_all"]
    evr = pca.explained_variance_ratio_
    st = S["stats"]
    fig = plt.figure(figsize=(15.4, 5.0))
    gs = GridSpec(1, 3, left=0.04, right=0.99, top=0.84, bottom=0.11, wspace=0.16)

    ax = fig.add_subplot(gs[0, 0])
    w = df["weakness"].values
    sc = ax.scatter(ZA[:, 0], ZA[:, 1], c=w, s=4.5, cmap="magma_r", alpha=0.62, linewidths=0,
                    vmin=0, vmax=float(np.quantile(w, 0.995)), rasterized=True)
    cb = fig.colorbar(sc, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("weakness = 0.5*AGE + 0.5*FAR_GAP", fontsize=7.4)
    cb.ax.tick_params(labelsize=6.6)
    bare(ax, "PC1 (%.1f%%)" % (evr[0] * 100), "PC2 (%.1f%%)" % (evr[1] * 100))
    ax.set_title("(a) coloured by weakness score",
                 fontsize=9.2, color=INK, loc="left", pad=6, linespacing=1.5)

    ax = fig.add_subplot(gs[0, 1])
    scatter_by(ax, ZA, df["site"].values, SITES, SITE_COLOR, s=4.2, alpha=0.5)
    bare(ax, "PC1 (%.1f%%)" % (evr[0] * 100), "")
    ax.set_title("(b) coloured by site\nsilhouette = %+.3f"
                 % st["all"]["sil_site_2d"], fontsize=9.2, color=INK, loc="left", pad=6, linespacing=1.5)
    ax.legend(handles=[Patch(fc=SITE_COLOR[s], ec="none", label="%s  (%s)" % (s, FAMILY[s])) for s in SITES],
              fontsize=7.2, loc="upper left", frameon=True, framealpha=0.85, edgecolor="none",
              facecolor="white", handlelength=1.0, ncol=1, borderpad=0.3)

    ax = fig.add_subplot(gs[0, 2])
    fams = ["residential", "commerce / office", "civic / institutional", "industry", "park / green", "unlabelled"]
    scatter_by(ax, ZA, df["eu_fam"].values, fams, EUF_COLOR, s=4.2, alpha=0.5)
    bare(ax, "PC1 (%.1f%%)" % (evr[0] * 100), "")
    ax.set_title("(c) coloured by EULUC family\nsilhouette %+.3f in 2-D, %+.3f in full 21-D"
                 % (st["all"]["sil_euf_2d"], st["all"]["sil_euf_full"]),
                 fontsize=9.2, color=INK, loc="left", pad=6, linespacing=1.5)
    nn = df["eu_fam"].value_counts()
    ax.legend(handles=[Patch(fc=EUF_COLOR[f], ec="none", label="%s  n=%d" % (f, nn.get(f, 0))) for f in fams],
              fontsize=7.2, loc="upper left", frameon=True, framealpha=0.85, edgecolor="none",
              facecolor="white", handlelength=1.0, borderpad=0.3)

    p = OUT / "E2_pca_variants.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("E2 ->", p)


# --------------------------------------------------------------------- E3
def e3(S):
    df, st = S["df"], S["stats"]
    y = df["sh"].values
    fig = plt.figure(figsize=(15.4, 5.4))
    gs = GridSpec(1, 4, left=0.035, right=0.99, top=0.82, bottom=0.11, wspace=0.26,
                  width_ratios=[1, 1, 1, 1.12])

    panels = [
        ("AE_all", "(a) autoencoder, 2-D bottleneck\nfull 21-column metadata", S["AE_all"], st["all"]["ae2"], S["r2"]["ae_all"]),
        ("VAE_all", "(b) beta-VAE (beta=0.05), latent mean\nfull 21-column metadata", S["VAE_all"], st["all"]["vae2"], S["r2"]["vae_all"]),
        ("AE_phys", "(c) autoencoder, 2-D bottleneck\nform only: no land-use column", S["AE_phys"], st["phys"]["ae2"], S["r2"]["ae_phys"]),
    ]
    for i, (_k, title, Z, pu, r2) in enumerate(panels):
        ax = fig.add_subplot(gs[0, i])
        scatter_by(ax, Z, y, SH_ORDER, C.SH_COLOR, s=4.0, alpha=0.45)
        for k in SH_ORDER:
            ellipse(ax, Z, y == k, C.SH_COLOR[k])
        bare(ax, "latent 1", "latent 2" if i == 0 else "")
        ax.set_title("%s\nrecon R2 = %.2f · 10-NN purity %.1f%% (balanced %.1f%%)"
                     % (title, r2, 100 * pu["acc"], 100 * pu["bal_acc"]),
                     fontsize=8.8, color=INK, loc="left", pad=6, linespacing=1.5)
        if i == 0:
            ax.legend(handles=[Patch(fc=C.SH_COLOR[k], ec="none", label=k) for k in SH_ORDER],
                      fontsize=7.4, loc="best", frameon=False, handlelength=1.0, borderpad=0.2)

    ax = fig.add_subplot(gs[0, 3])
    spaces = [("PCA 2-D", "pca2"), ("AE 2-D", "ae2"), ("VAE 2-D", "vae2"), ("full-D", "fullD")]
    x = np.arange(len(spaces))
    b1 = [st["all"][k]["bal_acc"] for _, k in spaces]
    b2 = [st["phys"][k]["bal_acc"] for _, k in spaces]
    ax.bar(x - 0.19, b1, 0.36, color="#4a6fa5", label="ALL  (form + land-use)")
    ax.bar(x + 0.19, b2, 0.36, color="#c0654a", label="PHYS (form only)")
    for xi, v in zip(x - 0.19, b1):
        ax.text(xi, v + 0.012, "%.2f" % v, ha="center", fontsize=7.2, color="#33507a")
    for xi, v in zip(x + 0.19, b2):
        ax.text(xi, v + 0.012, "%.2f" % v, ha="center", fontsize=7.2, color="#8f4634")
    ax.axhline(0.25, color="#888", lw=0.9, ls=":")
    ax.text(-0.42, 0.202, "chance (4 classes) = 0.25", fontsize=7.0, color="#555", ha="left",
            bbox=dict(fc="white", ec="none", alpha=0.82, pad=1.5))
    ax.set_xticks(x)
    ax.set_xticklabels([s for s, _ in spaces], fontsize=8)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("10-NN balanced accuracy on stakeholder", fontsize=8)
    ax.tick_params(labelsize=7.4, length=2)
    for s_ in ax.spines.values():
        s_.set_color("#cccccc")
    ax.legend(fontsize=7.6, frameon=False, loc="upper left")
    ax.set_title("(d) balanced accuracy by embedding and feature set\nbalanced across the four classes, 5-fold cross-validated",
                 fontsize=8.8, color=INK, loc="left", pad=6, linespacing=1.5)

    p = OUT / "E3_ae_vae.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("E3 ->", p)


# --------------------------------------------------------------------- driver
EU_LEVELS = []
CACHE = OUT / "_embed_cache"          # trained embeddings, so a re-draw does not re-train


def _cached(name, fn):
    """train once, keep the result. Written temp-then-rename, so an interrupted run cannot
    leave a half-written array behind."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / (name + ".npy")
    j = CACHE / (name + ".json")
    if p.exists() and j.exists():
        return np.load(p), json.load(open(j))["r2"]
    print("   training %s ..." % name, flush=True)
    Z, r2 = fn()
    tmp = CACHE / (name + ".tmp.npy")
    np.save(tmp, Z)
    tmp.replace(p)
    json.dump({"r2": r2, "seed": SEED}, open(j, "w"))
    return Z, r2


def prepare():
    global EU_LEVELS
    df = build_table()
    EU_LEVELS = sorted(df["euluc"].unique())
    y = df["sh"].values
    S = {"df": df, "stats": {}, "r2": {}}

    cols_all, X_all = feature_matrix(df, "all")
    cols_ph, X_ph = feature_matrix(df, "phys")
    S["cols_all"] = cols_all

    pca_all = PCA(n_components=min(10, X_all.shape[1]), random_state=SEED)
    Z_all = pca_all.fit_transform(X_all)[:, :2]
    pca_ph = PCA(n_components=2, random_state=SEED)
    Z_ph = pca_ph.fit_transform(X_ph)
    S["pca_all"], S["Z_all"] = pca_all, Z_all
    S["L1"] = dict(zip(cols_all, pca_all.components_[0]))
    S["L2"] = dict(zip(cols_all, pca_all.components_[1]))

    print("AE / VAE (numpy, seed %d, 450 epochs; cached in %s) ..." % (SEED, CACHE.name), flush=True)
    S["AE_all"], S["r2"]["ae_all"] = _cached("ae_all", lambda: train_ae(X_all))
    S["VAE_all"], S["r2"]["vae_all"] = _cached("vae_all", lambda: train_vae(X_all))
    S["AE_phys"], S["r2"]["ae_phys"] = _cached("ae_phys", lambda: train_ae(X_ph))
    S["VAE_phys"], S["r2"]["vae_phys"] = _cached("vae_phys", lambda: train_vae(X_ph))

    for block, X, Zp, Zae, Zva in (("all", X_all, Z_all, S["AE_all"], S["VAE_all"]),
                                   ("phys", X_ph, Z_ph, S["AE_phys"], S["VAE_phys"])):
        d = {
            "n_features": X.shape[1],
            "pca_evr": [float(v) for v in
                        (pca_all if block == "all" else pca_ph).explained_variance_ratio_[:5]],
            "pca2": purity(Zp, y), "ae2": purity(Zae, y), "vae2": purity(Zva, y),
            "fullD": purity(X, y),
            "sil_sh_2d": sil(Zp, y), "sil_sh_full": sil(X, y),
            "sil_site_2d": sil(Zp, df["site"].values), "sil_site_full": sil(X, df["site"].values),
            "sil_euf_2d": sil(Zp, df["eu_fam"].values), "sil_euf_full": sil(X, df["eu_fam"].values),
            "sil_sh_ae2": sil(Zae, y),
        }
        S["stats"][block] = d

    # how much of the stock has its holder decided by the EULUC column alone
    lk = C.load_lookup()
    S["stats"]["euluc_coverage"] = float(df["euluc"].isin(lk["euluc"].keys()).mean())
    S["stats"]["n"] = int(len(df))
    S["stats"]["prevalence"] = {k: float(v) for k, v in df["sh"].value_counts(normalize=True).items()}
    S["stats"]["sites"] = {s: int((df["site"] == s).sum()) for s in SITES}
    S["stats"]["r2"] = S["r2"]
    S["stats"]["pc1_loadings"] = {k: round(float(v), 3) for k, v in S["L1"].items()}
    S["stats"]["pc2_loadings"] = {k: round(float(v), 3) for k, v in S["L2"].items()}
    S["stats"]["_note"] = ("SUPPLEMENTARY, NEXT_RUN_10 Task E. Real cached buildings only. "
                           "purity = 5-fold cross-validated 10-NN on the embedding.")
    json.dump(S["stats"], open(OUT / "E_embed_stats.json", "w"), indent=1, ensure_ascii=False)
    print("stats ->", OUT / "E_embed_stats.json")
    return S


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    S = prepare()
    if which != "fit":
        for t in (["e1", "e2", "e3"] if which == "all" else [which]):
            {"e1": e1, "e2": e2, "e3": e3}[t](S)
