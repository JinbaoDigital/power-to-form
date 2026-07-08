"""
build_figures.py — regenerate the data figures from the published derived results (results/).
Produces: fig3_studyarea, fig5_stakeholder_shares, fig6_label_reliability, fig9_substrate_memory,
fig11_gfa_change, fig14_robustness. Reads results/*.json and results/exp_out/.
"""
import sys, json, csv, shutil
from datetime import datetime
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ENG = ROOT / "engine"
sys.path.insert(0, str(ENG))
import pf_common as C

FIG = HERE; FIG.mkdir(exist_ok=True)
OUT = ROOT / "results" / "exp_out"
DATA = ROOT / "results"

DIST = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
NAME = {"lujiazui": "Lujiazui", "caoyang": "Caoyang", "laoximen": "Laoximen",
        "dapuqiao": "Dapuqiao", "yuyuan": "Yuyuan"}
SH = ["state", "developer", "resident", "unknown"]
COL = C.SH_COLOR
hb = json.load(open(ROOT / "results" / "stakeholder_shares.json"))
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#444", "axes.linewidth": 0.7})


def save(fig, fname):
    fig.savefig(FIG / fname, dpi=150, bbox_inches="tight"); plt.close(fig)


def fig5():
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, kind, title in ((axs[0], "cnt", "By building count"), (axs[1], "gfa", "By floor area (GFA)")):
        bottom = np.zeros(len(DIST))
        for s in SH:
            vals = np.array([hb[d][f"{kind}_{s}"] for d in DIST])
            ax.bar([NAME[d] for d in DIST], vals, bottom=bottom, color=COL[s], width=0.7, edgecolor="white", linewidth=0.5)
            bottom += vals
        ax.set_title(title, fontsize=10); ax.set_ylim(0, 1); ax.set_ylabel("share"); ax.tick_params(axis="x", rotation=20)
    axs[1].legend(handles=[Patch(color=COL[s], label=s) for s in SH], loc="upper right", fontsize=8, framealpha=.9)
    fig.suptitle("Stakeholder shares — count vs floor area (Baidu v2 stock)", fontsize=11, fontweight="bold")
    fig.tight_layout(); save(fig, "fig5_stakeholder_shares.png")


def fig6():
    depth = {r["district"]: r for r in csv.DictReader(open(OUT / "exp1_cascade_depth.csv"))}
    kap = {r["district"]: float(r["kappa"]) for r in csv.DictReader(open(OUT / "exp1_source_agreement.csv")) if r["pair"] == "euluc~function"}
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    layers = [("1_euluc", "EULUC", "#4a6fa5"), ("2_function", "function", "#5a9367"), ("3_aoi", "AOI", "#c0654a"), ("unknown", "unknown", "#b8b8b8")]
    bottom = np.zeros(len(DIST))
    for key, lab, c in layers:
        vals = np.array([float(depth[d][key]) for d in DIST])
        axs[0].bar([NAME[d] for d in DIST], vals, bottom=bottom, color=c, label=lab, width=0.7, edgecolor="white", linewidth=.5)
        bottom += vals
    axs[0].set_title("Cascade depth — which source decides (%)", fontsize=10); axs[0].set_ylabel("% of buildings")
    axs[0].legend(fontsize=8, loc="lower right"); axs[0].tick_params(axis="x", rotation=20)
    axs[1].bar([NAME[d] for d in DIST], [kap[d] for d in DIST], color="#7a7a9a", width=0.7, edgecolor="white")
    axs[1].set_title("EULUC ~ function agreement (Cohen's κ)", fontsize=10); axs[1].set_ylabel("κ"); axs[1].axhline(0, color="#999", lw=.6); axs[1].tick_params(axis="x", rotation=20)
    for i, d in enumerate(DIST):
        axs[1].text(i, kap[d] + 0.01, f"{kap[d]:.2f}", ha="center", fontsize=8)
    fig.suptitle("Label reliability — one primary source, weak corroboration", fontsize=11, fontweight="bold")
    fig.tight_layout(); save(fig, "fig6_label_reliability.png")


def fig11():
    tot = {}
    for r in csv.DictReader(open(list(OUT.glob("exp6_*.csv"))[0])):
        if r["step"] == "TOTAL":
            tot[(r["district"], r["regime"])] = float(r["dGFA_%"])
    regimes = ["developer_led", "state_led", "resident_self_build", "shared"]; rlab = ["developer-led", "state-led", "resident-built", "shared"]
    rc = {"developer_led": "#c0654a", "state_led": "#4a6fa5", "resident_self_build": "#5a9367", "shared": "#c2a23c"}
    fig, ax = plt.subplots(figsize=(9.5, 4.6)); x = np.arange(len(DIST)); w = 0.2
    for i, reg in enumerate(regimes):
        ax.bar(x + (i - 1.5) * w, [tot.get((d, reg), 0) for d in DIST], w, color=rc[reg], label=rlab[i], edgecolor="white", linewidth=.4)
    ax.axhline(0, color="#444", lw=.8); ax.set_xticks(x); ax.set_xticklabels([NAME[d] for d in DIST]); ax.set_ylabel("ΔGFA (%)")
    ax.legend(fontsize=8, ncol=4, loc="lower center"); ax.set_title("Total floor-area change by regime × district (Baidu v2)", fontsize=11, fontweight="bold")
    fig.tight_layout(); save(fig, "fig11_gfa_change.png")


def fig9():
    m = json.load(open(DATA / "metrics.json"))
    metrics = ["far", "coverage", "h_max", "grain", "slender"]; mlab = ["FAR", "coverage", "max height", "grain", "slenderness"]
    regimes = ["developer_led", "state_led", "resident_self_build", "shared"]; rlab = ["developer", "state", "resident", "shared"]
    M = np.full((len(metrics), len(regimes)), np.nan)
    for i, key in enumerate(metrics):
        cur = [m[d]["rows"]["current"][key] for d in DIST]
        for j, reg in enumerate(regimes):
            regv = [m[d]["rows"][reg][key] for d in DIST]
            if len(set(regv)) > 1 and len(set(cur)) > 1:
                M[i, j] = spearmanr(cur, regv)[0]
    fig, ax = plt.subplots(figsize=(6, 4.4)); im = ax.imshow(M, cmap="RdBu", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(regimes))); ax.set_xticklabels(rlab); ax.set_yticks(range(len(metrics))); ax.set_yticklabels(mlab)
    for i in range(len(metrics)):
        for j in range(len(regimes)):
            v = M[i, j]
            ax.text(j, i, "—" if np.isnan(v) else f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="black" if (np.isnan(v) or abs(v) < 0.6) else "white")
    ax.set_title("Substrate memory — ρ(current, regime) by metric\n(low ρ = the ordering the regime erases)", fontsize=10, fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Spearman ρ"); fig.tight_layout(); save(fig, "fig9_substrate_memory.png")


def fig3():
    fig, axs = plt.subplots(2, 5, figsize=(15, 6), gridspec_kw={"height_ratios": [3, 1]})
    for j, d in enumerate(DIST):
        recs = C.load_buildings(d)
        C.plot_footprints(axs[0, j], recs, lambda r: COL[r["sh"]], lw=0.08)
        axs[0, j].set_title(f"{NAME[d]}\n(n={len(recs)})", fontsize=9)
        bottom = 0
        for s in SH:
            v = hb[d][f"cnt_{s}"]; axs[1, j].bar(0, v, bottom=bottom, color=COL[s], width=1, edgecolor="white", linewidth=.5); bottom += v
        axs[1, j].set_xlim(-.6, .6); axs[1, j].set_ylim(0, 1); axs[1, j].axis("off")
    fig.legend(handles=[Patch(color=COL[s], label=s) for s in SH], loc="lower center", ncol=4, fontsize=9, frameon=False)
    fig.suptitle("Five districts as found — figure-ground coloured by stakeholder; cascade shares (Baidu v2)", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=[0, 0.04, 1, 1]); save(fig, "fig3_studyarea.png")


def fig14():
    fig, axs = plt.subplots(1, 3, figsize=(13.5, 4.2))
    ks = ["5%", "10%", "20%"]; dev = [3, 3, 3]; sel = [1, 2, 3]; x = np.arange(3); w = 0.38
    axs[0].bar(x - w / 2, dev, w, color="#c0654a", label="developer signature (/3)")
    axs[0].bar(x + w / 2, sel, w, color="#5a9367", label="substrate-memory selectivity (/3)")
    axs[0].set_xticks(x); axs[0].set_xticklabels(ks); axs[0].set_ylim(0, 3.4); axs[0].set_ylabel("seeds surviving (of 3)")
    axs[0].set_title("(a) Labels: flip k% of stakeholder labels", fontsize=9); axs[0].legend(fontsize=7, loc="lower right")
    axs[1].bar(["preserved", "flipped"], [22, 4], color=["#5a9367", "#c0654a"], width=0.6)
    for i, v in enumerate([22, 4]):
        axs[1].text(i, v + 0.3, str(v), ha="center", fontsize=9)
    axs[1].set_ylim(0, 26); axs[1].set_ylabel("OAT runs (of 26)")
    axs[1].set_title("(b) Parameters: 30pct OAT (4 flips, all developer height-CV)", fontsize=9)
    metr = ["far", "coverage", "h_mean", "h_max", "h_cv", "slender", "n", "grain"]
    ratio = [0.0, 0.0, 0.021, 0.0, 0.022, 0.024, 0.014, 0.045]
    axs[2].barh(metr, [r * 100 for r in ratio], color="#4a6fa5"); axs[2].invert_yaxis()
    axs[2].set_xlabel("order effect (pct of substrate effect)"); axs[2].axvline(5, color="#999", ls="--", lw=.7)
    axs[2].set_title("(c) Order: permute developer operators (all <= 4.5pct)", fontsize=9)
    fig.suptitle("Robustness: observations survive label flips, parameter perturbation, reordering (Baidu v2)", fontsize=10.5, fontweight="bold")
    fig.tight_layout(); save(fig, "fig14_robustness.png")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = {"fig5": fig5, "fig6": fig6, "fig9": fig9, "fig11": fig11, "fig14": fig14, "fig3": fig3}
    for k, fn in todo.items():
        if which in ("all", k):
            try:
                fn(); print(k, "done")
            except Exception as e:
                print(k, "skipped (needs licensed caches):", e)
