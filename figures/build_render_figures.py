"""
build_render_figures_baidu.py — regenerate the render/embedding figures on the Baidu-v2 caches
Produces, versioned under figures/_versions/<ts>_baidu_v2/ and to canonical
paper/figures/:  fig7 (PCA embedding) · fig8 (regime gallery 3D) · fig12 (skylines) · fig13
(transplant 3D) · figB2 (OSM thresholds).  fig4/figB3 need Esri tiles / OSM geometry (see notes).
Usage: python3 build_render_figures_baidu.py [fig7|fig8|fig12|fig13|figB2|all]
"""
import sys, json, shutil, pickle
from datetime import datetime
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
HERE = Path(__file__).resolve().parent
ENG = HERE.parent / "engine"; sys.path.insert(0, str(ENG))
import pf_common as C, operators as OP, measure as M, render as R

FIG = HERE
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN = FIG / "_versions" / f"{TS}_baidu_v2"; RUN.mkdir(parents=True, exist_ok=True)
DIST = [("lujiazui", "Lujiazui"), ("caoyang", "Caoyang"), ("laoximen", "Laoximen"),
        ("dapuqiao", "Dapuqiao"), ("yuyuan", "Yuyuan")]
ORDER = ["current", "developer_led", "state_led", "resident_self_build", "shared"]
SLAB = {"current": "current", "developer_led": "developer-led", "state_led": "state-led",
        "resident_self_build": "resident-built", "shared": "shared"}
COL = C.SH_COLOR
REG = OP.load_regimes()
STATES_PKL = Path('/tmp/ptf_states.pkl')
_manifest = []

def save(fig, fname):
    fig.savefig(RUN / fname, dpi=140, bbox_inches="tight")
    fig.savefig(FIG / fname, dpi=140, bbox_inches="tight")
    plt.close(fig); _manifest.append(fname)

# ---- shared: build states + rows per district ----
def build(only=None):
    S = pickle.load(open(STATES_PKL, "rb")) if STATES_PKL.exists() else {}
    names = dict(DIST)
    todo = [only] if only else [d[0] for d in DIST]
    for slug in todo:
        if slug in S:
            continue
        recs = C.load_buildings(slug)
        aft = {n: OP.apply_regime(recs, rc) for n, rc in REG.items()}
        rows, ctr = M.compare(recs, aft, slug)
        S[slug] = {"name": names[slug], "states": {"current": recs, **aft}, "rows": rows, "ctr": ctr}
        pickle.dump(S, open(STATES_PKL, "wb"))
        print("  prepped", slug)
    return S

def _box(ax, recs, title, cap=1400):
    if len(recs) > cap:
        idx = np.random.default_rng(0).choice(len(recs), cap, replace=False)
        recs = [recs[i] for i in idx]
    polys = [p for r in recs for p in C._polys(r["geom"])]
    minx = min(p.bounds[0] for p in polys); miny = min(p.bounds[1] for p in polys)
    zmax = max(r["h"] for r in recs) * 1.04
    R._boxes3d(ax, recs, minx, miny, zmax)
    ax.set_title(title, fontsize=8)

def fig8(S):
    regs = ["developer_led", "state_led", "resident_self_build", "shared"]
    fig = plt.figure(figsize=(4.0 * 5, 3.6 * 4))
    for ri, reg in enumerate(regs):
        for ci, (slug, nm) in enumerate(DIST):
            ax = fig.add_subplot(4, 5, ri * 5 + ci + 1, projection="3d")
            _box(ax, S[slug]["states"][reg], f"{SLAB[reg]} · {nm}", cap=500)
    fig.suptitle("Fig. 8  One recipe, five substrates: four regimes replayed across the five districts (3D massing)", fontsize=13, fontweight="bold")
    fig.subplots_adjust(left=.01, right=.99, top=.95, bottom=.01, wspace=.03, hspace=.12)
    save(fig, "fig8_regime_gallery.png")

def fig13(S):
    fig = plt.figure(figsize=(4.0 * 5, 3.8 * 2))
    for ci, (slug, nm) in enumerate(DIST):
        ax = fig.add_subplot(2, 5, ci + 1, projection="3d"); _box(ax, S[slug]["states"]["current"], f"current · {nm}")
        ax2 = fig.add_subplot(2, 5, 5 + ci + 1, projection="3d"); _box(ax2, S[slug]["states"]["developer_led"], f"developer-led · {nm}")
    fig.suptitle("Fig. 12  Transplanting the Lujiazui playbook: current (top) and developer-led (bottom) for all five districts", fontsize=13, fontweight="bold")
    fig.subplots_adjust(left=.01, right=.99, top=.93, bottom=.01, wspace=.03, hspace=.1)
    save(fig, "fig13_lujiazui_transplant.png")

def fig12(S):
    fig, axs = plt.subplots(5, 5, figsize=(16, 12), sharey=True)
    for ri, (slug, nm) in enumerate(DIST):
        for ci, st in enumerate(ORDER):
            ax = axs[ri, ci]; recs = S[slug]["states"][st]
            xs = np.array([r["geom"].centroid.x for r in recs]); hs = np.array([r["h"] for r in recs])
            cols = [COL[r["sh"]] for r in recs]
            xr = (xs - xs.min()) / (np.ptp(xs) + 1e-9)
            ax.vlines(xr, 0, hs, colors=cols, linewidth=0.5)
            ax.set_xticks([]); ax.set_ylim(0, 320); ax.set_xlim(-0.02, 1.02)
            if ri == 0: ax.set_title(SLAB[st], fontsize=10)
            if ci == 0: ax.set_ylabel(nm, fontsize=10)
    fig.suptitle("Fig. 11  Speculative skylines: five substrates × five states (one bar per building, stakeholder colours)", fontsize=13, fontweight="bold")
    fig.legend(handles=[Patch(color=COL[s], label=s) for s in ("state", "developer", "resident", "unknown")], loc="lower center", ncol=4, fontsize=9, frameon=False)
    fig.tight_layout(rect=[0, 0.03, 1, 0.97]); save(fig, "fig12_speculative_skylines.png")

def figB2():
    # Baidu Table B3 (recomputed): coverage / height-signal / classifiable per district; cascade unknown line
    B3 = {"Lujiazui": (73.9, 6.9, 69.4, 0.8), "Caoyang": (67.2, 1.8, 41.9, 0.7),
          "Laoximen": (41.9, 42.9, 55.3, 2.2), "Dapuqiao": (86.1, 1.2, 45.0, 2.0), "Yuyuan": (62.1, 37.5, 26.7, 1.2)}
    names = list(B3); x = np.arange(len(names)); w = 0.26
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.bar(x - w, [B3[n][0] for n in names], w, color="#4a6fa5", label="footprint coverage")
    ax.bar(x, [B3[n][1] for n in names], w, color="#c0654a", label="height / storey signal")
    ax.bar(x + w, [B3[n][2] for n in names], w, color="#5a9367", label="tag-classifiable")
    ax.plot(x, [B3[n][3] for n in names], "k--o", ms=4, label="cascade unknown (for comparison)")
    ax.axhline(50, color="#999", lw=.6)
    ax.set_xticks(x); ax.set_xticklabels(names); ax.set_ylabel("% of the Baidu stock"); ax.set_ylim(0, 100)
    ax.legend(fontsize=8, ncol=2); ax.set_title("Fig. B2  Why not OSM: the grammar's three entry thresholds over the five districts (Baidu stock)", fontsize=11, fontweight="bold")
    fig.tight_layout(); save(fig, "figB2_osm_audit.png")

def fig7():
    # PCA (numpy SVD) embedding of all buildings by 5 form descriptors, coloured by stakeholder
    X, sh = [], []
    for slug, nm in DIST:
        for r in C.load_buildings(slug):
            g = r["geom"]; A = g.area; P = g.length
            mrr = g.minimum_rotated_rectangle
            xs, ys = mrr.exterior.xy
            e = [((xs[i+1]-xs[i])**2 + (ys[i+1]-ys[i])**2) ** .5 for i in range(4)]
            elong = (max(e[0], e[1]) / (min(e[0], e[1]) + 1e-9))
            X.append([r["h"], np.log(A + 1), 4 * np.pi * A / (P * P + 1e-9), elong, np.log(P + 1)])
            sh.append(r["sh"])
    X = np.array(X); sh = np.array(sh)
    Xz = (X - X.mean(0)) / (X.std(0) + 1e-9)
    U, s, Vt = np.linalg.svd(Xz - Xz.mean(0), full_matrices=False)
    var = (s ** 2) / (s ** 2).sum(); pc = (Xz @ Vt[:2].T)
    fig, ax = plt.subplots(figsize=(7, 6))
    for cls in ("resident", "developer", "state", "unknown"):
        m = sh == cls
        ax.scatter(pc[m, 0], pc[m, 1], s=4, alpha=.35, c=COL[cls], label=cls, linewidths=0)
    ax.set_xlabel(f"PC1 ({var[0]*100:.0f}% var)"); ax.set_ylabel(f"PC2 ({var[1]*100:.0f}% var)")
    ax.legend(markerscale=3, fontsize=9)
    ax.set_title(f"Fig. 7  Form-stakeholder embedding: all {len(X):,} buildings by five descriptors\n(PCA; first two components {var[:2].sum()*100:.0f}% of variance). Association, not identification.", fontsize=10, fontweight="bold")
    fig.tight_layout(); save(fig, "fig7_embedding.png")
    print(f"  fig7: n={len(X)}  PC1={var[0]*100:.1f}%  PC2={var[1]*100:.1f}%  PC1+2={var[:2].sum()*100:.1f}%")

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which == "prep":
        build(sys.argv[2] if len(sys.argv) > 2 else None); sys.exit(0)
    need_states = which in ("all", "fig8", "fig12", "fig13")
    S = build() if need_states else None
    if which in ("all", "fig7"): fig7()
    if which in ("all", "figB2"): figB2()
    if which in ("all", "fig8"): fig8(S)
    if which in ("all", "fig13"): fig13(S)
    if which in ("all", "fig12"): fig12(S)
    if _manifest:
        with open(FIG / "GENERATION_LOG.md", "a", encoding="utf-8") as lg:
            lg.write(f"\n## {TS} — baidu_v2 (render/embedding)\nRun `_versions/{TS}_baidu_v2/`: {', '.join(_manifest)}. "
                     f"fig7 PCA via numpy SVD (no torch); 3D via render._boxes3d (no satellite context).\n")
        print("wrote", ", ".join(_manifest), "-> version", RUN.name)
