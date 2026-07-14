"""
figs_cake.py — the four cake-model figures for the paper.

    python3 figs_cake.py fig1 | fig2 | fig3 | fig4 | all

Every number on every figure is read from files already on disk:
    out/cake/metrics_cake.json          shares, fingerprints, ledger headlines, transfer matrices
    out/cake/ledger_<d>_<s>.csv         the named buildings: bid, from, to, gfa, h, area, weakness
    out/cake/skyline_<d>.json           [[bid, h, holder], ...] per scenario
    out/cake/reachable_<d>.json         the 5 x 5 target grid
    engine/data/<d>/buildings.parquet   via pf_common.load_buildings (geometry, EPSG:32651)
Nothing is invented here. If a value is not in those files it is not on the figure.
"""
import sys
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as MPolygon
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pf_common as C          # noqa: E402
import measure as M            # noqa: E402
import cake                    # noqa: E402

ROOT = HERE.parent
CAKE = HERE / "out" / "cake"
FIGS = ROOT / "paper" / "figures" / "cake"
FIGS.mkdir(parents=True, exist_ok=True)

DPI = 160
SLUG = "caoyang"
SCEN = "capital_extreme_B"
RED = "#d1281e"                # the colour of being taken
PALE = "#e2e2e0"               # untouched stock
INK = "#1c1c1c"

ORDER = ("state", "developer", "resident", "unknown")
NICE = {"state": "state", "developer": "developer", "resident": "resident", "unknown": "unknown"}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.linewidth": 0.6,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
})


# --------------------------------------------------------------------- loaders
def metrics():
    return json.load(open(CAKE / "metrics_cake.json", encoding="utf-8"))


def ledger(slug, scen):
    with open(CAKE / ("ledger_%s_%s.csv" % (slug, scen)), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("gfa_before", "gfa_after", "h_before", "h_after", "area", "weakness"):
            r[k] = float(r[k])
        r["bid"] = int(r["bid"])
    return rows


def skyline(slug):
    return json.load(open(CAKE / ("skyline_%s.json" % slug), encoding="utf-8"))


def reachable(slug):
    return json.load(open(CAKE / ("reachable_%s.json" % slug), encoding="utf-8"))


def buildings(slug=SLUG):
    return C.load_buildings(slug)


# --------------------------------------------------------------------- drawing helpers
def _patches(recs):
    """one matplotlib polygon per footprint ring, in record order."""
    out, idx = [], []
    for k, r in enumerate(recs):
        for p in C._polys(r["geom"]):
            out.append(MPolygon(np.asarray(p.exterior.coords), closed=True))
            idx.append(k)
    return out, np.asarray(idx)


def plan(ax, recs, colors, lw=0.15, ec="white", zorder=2, alpha=1.0):
    """recs plotted as filled footprints; colors is a list parallel to recs."""
    polys, idx = _patches(recs)
    pc = PatchCollection(polys, facecolors=[colors[i] for i in idx], edgecolors=ec,
                         linewidths=lw, zorder=zorder, alpha=alpha)
    ax.add_collection(pc)
    xs = [r["geom"].bounds for r in recs]
    minx = min(b[0] for b in xs); miny = min(b[1] for b in xs)
    maxx = max(b[2] for b in xs); maxy = max(b[3] for b in xs)
    pad = 0.02 * max(maxx - minx, maxy - miny)
    ax.set_xlim(minx - pad, maxx + pad); ax.set_ylim(miny - pad, maxy + pad)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    return (minx, miny, maxx, maxy)


def scalebar(ax, bounds, metres=200, label="200 m"):
    minx, miny, maxx, maxy = bounds
    x0 = minx + 0.06 * (maxx - minx)
    y0 = miny + 0.045 * (maxy - miny)
    ax.plot([x0, x0 + metres], [y0, y0], color=INK, lw=1.6, solid_capstyle="butt", zorder=8)
    ax.text(x0 + metres / 2, y0 + 0.012 * (maxy - miny), label, ha="center", va="bottom",
            fontsize=6.5, color=INK, zorder=8)


def share_bar(ax, shares, label=None, fs=7.5, show=0.045):
    left = 0.0
    for c in ORDER:
        v = float(shares.get(c, 0.0))
        if v <= 0:
            continue
        ax.barh(0, v, left=left, height=0.75, color=C.SH_COLOR[c], edgecolor="white", linewidth=0.8)
        if v >= show:
            ax.text(left + v / 2, 0, "%.0f%%" % (v * 100), ha="center", va="center",
                    fontsize=fs, color="white", fontweight="bold")
        left += v
    ax.set_xlim(0, 1); ax.set_ylim(-0.5, 0.5)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    if label:
        ax.set_title(label, fontsize=8, color=INK, pad=4, loc="left")


def legend_sh(ax, classes=ORDER, fs=7, loc="upper right", extra=None):
    from matplotlib.patches import Patch
    h = [Patch(facecolor=C.SH_COLOR[c], edgecolor="white", label=NICE[c]) for c in classes]
    if extra:
        h += extra
    ax.legend(handles=h, loc=loc, fontsize=fs, frameon=False, handlelength=1.1,
              handleheight=0.9, borderpad=0.2, labelspacing=0.35)


# ===================================================================== FIG 1
def fig1():
    m = metrics()[SLUG]
    cur, sc = m["current"], m[SCEN]
    led = ledger(SLUG, SCEN)
    taken = {r["bid"] for r in led}
    recs = buildings()
    sky = skyline(SLUG)

    disp_res = sc["displacement_gfa"]["resident"]
    V0 = cur["V_total_m3"]

    fig = plt.figure(figsize=(16.5, 7.4))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 0.20], hspace=0.10, wspace=0.06,
                          left=0.02, right=0.98, top=0.88, bottom=0.10)

    # ---- LEFT: the city as it is -----------------------------------------
    a1 = fig.add_subplot(gs[0, 0])
    cols = [C.SH_COLOR[r["sh"]] for r in recs]
    b = plan(a1, recs, cols)
    scalebar(a1, b)
    a1.set_title("1  READ  -  who holds the cake now\n"
                 "Caoyang, %d buildings, floor volume V = %.2f x 10$^6$ m$^3$" % (cur["n"], V0 / 1e6),
                 fontsize=10, loc="left", color=INK, pad=9)
    legend_sh(a1)
    s1 = fig.add_subplot(gs[1, 0])
    share_bar(s1, cur["shares_gfa"], "current GFA shares  (developer %.1f%%)" % (cur["shares_gfa"]["developer"] * 100))

    # ---- MIDDLE: the target, and the buildings it names --------------------
    a2 = fig.add_subplot(gs[0, 1])
    cols2 = [RED if r["bid"] in taken else PALE for r in recs]
    b = plan(a2, recs, cols2, lw=0.12, ec="white")
    scalebar(a2, b)
    a2.set_title("2  SET + REALLOCATE  -  the tool names the buildings\n"
                 "developer share -> 0.60: %d buildings acquired, weakest first"
                 % sc["acquired_n"], fontsize=10, loc="left", color=INK, pad=9)
    from matplotlib.patches import Patch
    a2.legend(handles=[Patch(facecolor=RED, edgecolor="white",
                             label="acquired by developer (n = %d)" % sc["acquired_n"]),
                       Patch(facecolor=PALE, edgecolor="white", label="untouched")],
              loc="upper right", fontsize=7.5, frameon=True, framealpha=0.9, edgecolor="none",
              handlelength=1.1, borderpad=0.4)
    a2.text(0.015, 0.985, "pool = %d resident buildings\n(gate: developer may take from resident)\n"
                          "ordered by weakness\n= 0.5*AGE + 0.5*FAR-gap\npool exhausted: %s"
            % (sc["pool_size"], "yes" if sc["pool_exhausted"] else "no"),
            transform=a2.transAxes, fontsize=6.8, color="#555", va="top", linespacing=1.4,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.85))

    s2 = fig.add_subplot(gs[1, 1])
    d0 = cur["shares_gfa"]["developer"]
    s2.barh(0, 1.0, height=0.55, color="#ededed", edgecolor="none")
    s2.barh(0, d0, height=0.55, color=C.SH_COLOR["developer"], edgecolor="none")
    s2.plot([sc["target"], sc["target"]], [-0.42, 0.42], color=RED, lw=1.6, ls="--")
    s2.annotate("", xy=(sc["target"], 0), xytext=(d0, 0),
                arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.8, shrinkA=0, shrinkB=0))
    s2.text(d0 - 0.01, -0.5, "now %.1f%%" % (d0 * 100), ha="right", va="top", fontsize=8,
            color=C.SH_COLOR["developer"], fontweight="bold")
    s2.text(sc["target"] + 0.01, -0.5, "target %.0f%%" % (sc["target"] * 100), ha="left", va="top",
            fontsize=8, color=RED, fontweight="bold")
    s2.set_xlim(0, 1); s2.set_ylim(-1.0, 0.5)
    s2.set_xticks([]); s2.set_yticks([])
    for s in s2.spines.values():
        s.set_visible(False)
    s2.set_title("SET: developer share of the cake  (scenario capital_extreme)", fontsize=8, loc="left")

    # ---- RIGHT: the resulting skyline -------------------------------------
    a3 = fig.add_subplot(gs[0, 2])
    xy = {r["bid"]: (r["geom"].centroid.x, r["geom"].centroid.y, r["area"]) for r in recs}
    now = {b_: h for b_, h, _ in sky["current"]}
    after = sky[SCEN]
    after = sorted(after, key=lambda t: -xy[t[0]][1])          # far buildings drawn first
    xs = np.array([xy[t[0]][0] for t in after])
    hs = np.array([t[1] for t in after])
    h0 = np.array([now[t[0]] for t in after])
    wd = np.sqrt(np.array([xy[t[0]][2] for t in after])) * 0.9
    ch = [C.SH_COLOR[t[2]] for t in after]
    a3.bar(xs, h0, width=wd, color="#d9d9d9", edgecolor="none", zorder=1)     # the city before
    a3.bar(xs, hs, width=wd, color=ch, edgecolor="white", linewidth=0.12, zorder=2, alpha=0.95)
    a3.set_xlim(xs.min() - 60, xs.max() + 60)
    a3.set_ylim(0, max(hs.max(), h0.max()) * 1.42)
    a3.set_xticks([])
    a3.set_ylabel("height (m)", fontsize=8)
    a3.tick_params(axis="y", labelsize=7)
    for s in ("top", "right", "bottom"):
        a3.spines[s].set_visible(False)
    a3.set_title("3  REBUILD + READ BACK  -  footprints frozen, only heights move\n"
                 "skyline after capital_extreme (mode B); grey = the city before",
                 fontsize=10, loc="left", color=INK, pad=9)
    a3.text(0.985, 0.985,
            "%d buildings taken\n"
            "%.2f x 10$^6$ m$^3$ resident floor volume transferred (%.1f%% of V)\n"
            "total GFA %+.1f%%   |   envelope binds on %d\n"
            "developer share reached %.1f%%  (target %.0f%%, met: %s)"
            % (sc["acquired_n"], disp_res / 1e6, 100 * disp_res / V0, sc["gfa_change_pct"],
               sc["envelope_bind_n"], sc["share_reached"] * 100, sc["target"] * 100,
               "yes" if sc["target_met"] else "NO"),
            transform=a3.transAxes, ha="right", va="top", fontsize=8, color=INK,
            bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#cccccc", lw=0.6))
    s3 = fig.add_subplot(gs[1, 2])
    share_bar(s3, sc["shares_gfa"], "GFA shares after  (developer %.1f%%)" % (sc["shares_gfa"]["developer"] * 100))

    fig.suptitle("The cake game: the city's floor volume, who holds it, and what it costs to change that",
                 fontsize=13, x=0.02, ha="left", y=0.975, color=INK)
    p = FIGS / "fig1_cake_game.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("fig1 ->", p)
    print("  current shares_gfa:", cur["shares_gfa"], " V=%.1f m3" % V0)
    print("  after   shares_gfa:", sc["shares_gfa"])
    print("  acquired_n=%d  ledger rows=%d  displacement_gfa.resident=%.1f  gfa_change=%+.2f%%"
          % (sc["acquired_n"], len(led), disp_res, sc["gfa_change_pct"]))


# ===================================================================== FIG 2
def fig2():
    m = metrics()[SLUG]
    cur, sc = m["current"], m[SCEN]
    recs = buildings()
    cfg = cake.load_cfg()
    cov = M.diagnose(recs, SLUG)["coverage"]
    wk = np.array([cake.weakness_score(r, cfg, cov, None) for r in recs])

    fig = plt.figure(figsize=(16.5, 8.6))

    # substrate: the real plan, faint, behind everything
    axbg = fig.add_axes([0.0, 0.0, 1.0, 1.0], zorder=0)
    plan(axbg, recs, ["#9aa0a6"] * len(recs), lw=0.1, ec="white", alpha=0.13)
    axbg.set_frame_on(False); axbg.patch.set_alpha(0)

    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0], zorder=1)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off"); ax.patch.set_alpha(0)

    def box(x0, x1, y0, y1, title, body, fc="white", ec="#4a4a4a", lw=1.0, tfs=10, bfs=7.6,
            heavy=False, ls="-"):
        ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                                    boxstyle="round,pad=0.6,rounding_size=1.2",
                                    fc=fc, ec=ec, lw=lw, ls=ls, zorder=3, alpha=0.97))
        ax.text((x0 + x1) / 2, y1 - 3.0, title, ha="center", va="top", fontsize=tfs,
                fontweight="bold" if heavy else "normal", color=INK, zorder=4)
        if body:
            ax.text((x0 + x1) / 2, y1 - 7.5, body, ha="center", va="top", fontsize=bfs,
                    color="#333", zorder=4, linespacing=1.5)

    def arrow(x0, y0, x1, y1, lw=1.8, color="#4a4a4a", rad=0.0, ls="-"):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1),
                                     arrowstyle="-|>", mutation_scale=16, lw=lw, color=color,
                                     linestyle=ls, connectionstyle="arc3,rad=%.2f" % rad, zorder=5))

    # 1 READ
    fp0 = cur["fingerprint"]
    box(2, 17.5, 46, 84, "1  READ",
        "cascade (OSM + Baidu AOI + EULUC)\nassigns every building a holder\n\n"
        "cake  V = sum(area x h)\n= %.2f x 10$^6$ m$^3$\n\n"
        "shares of V\nstate %.1f%%   developer %.1f%%\nresident %.1f%%   unknown %.1f%%"
        % (cur["V_total_m3"] / 1e6, cur["shares_gfa"]["state"] * 100,
           cur["shares_gfa"]["developer"] * 100, cur["shares_gfa"]["resident"] * 100,
           cur["shares_gfa"]["unknown"] * 100))
    ax.text(9.75, 52.5, "fingerprint (9 numbers)\nfar %.2f | h_mean %.1f m | cov %.3f\ngrain %.0f m$^2$ | conc %.3f"
            % (fp0["far"], fp0["h_mean"], fp0["coverage"], fp0["grain"], fp0["concentration"]),
            ha="center", va="center", fontsize=7, color=C.SH_COLOR["state"], zorder=4,
            bbox=dict(boxstyle="round,pad=0.35", fc="#eef2f8", ec=C.SH_COLOR["state"], lw=0.7))

    # 2 SET
    box(21, 34.5, 52, 84, "2  SET",
        "the whole interface is\none number\n\n"
        '"developer should hold\n60%% of the floor area"\n\n'
        "target = %.2f\ngrowing class = %s\nrule = %s"
        % (sc["target"], sc["grow"], sc["rule"]))

    # 3 REALLOCATE — the political core, given the weight
    box(38, 66, 20, 90, "3  REALLOCATE   <- the political core",
        "the growing class acquires from a gated pool,\n"
        "ordered by a weakness score.  the ordering rule IS the politics.\n"
        "weakness = 0.5*AGE + 0.5*FAR-gap   (old and under-built stock first)",
        fc="#fff6f4", ec=RED, lw=2.2, tfs=12, bfs=8, heavy=True)
    axw = fig.add_axes([0.415, 0.28, 0.20, 0.44], zorder=6)
    norm = mcolors.Normalize(vmin=float(wk.min()), vmax=float(wk.max()))
    cmap = plt.get_cmap("inferno_r")
    plan(axw, recs, [mcolors.to_hex(cmap(norm(w))) for w in wk], lw=0.08, ec="white")
    axw.patch.set_alpha(0)
    axw.set_title("weakness score on the real stock\n(gate: developer may take from resident, n = %d)"
                  % sc["pool_size"], fontsize=7.5, color=INK, pad=3)
    cax = fig.add_axes([0.628, 0.30, 0.008, 0.28], zorder=6)
    cb = fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
    cb.set_label("weakness (taken first ->)", fontsize=6.5)
    cb.ax.tick_params(labelsize=6)
    ax.text(52, 24.5, "gate + ordering are editable; pool exhaustion is reported, never hidden",
            ha="center", va="center", fontsize=7.5, color=RED, zorder=6, style="italic")

    # ghost box: future work
    ax.add_patch(FancyBboxPatch((38, 4), 28, 12, boxstyle="round,pad=0.6,rounding_size=1.2",
                                fc="none", ec="#9a9a9a", lw=1.4, ls=(0, (5, 4)), zorder=3))
    ax.text(52, 12.6, "learned reallocation  (future work)", ha="center", va="center",
            fontsize=9, color="#7a7a7a", zorder=4, style="italic")
    ax.text(52, 7.6, "a learned policy could replace the hand-written ordering rule;\n"
                     "the ruler at both ends would not change",
            ha="center", va="center", fontsize=7, color="#8a8a8a", zorder=4)
    arrow(52, 16.5, 52, 19.5, lw=1.2, color="#9a9a9a", ls=(0, (4, 3)))

    # 4 REBUILD
    box(70, 82.5, 52, 84, "4  REBUILD",
        "mode B only, and only on\nthe acquired buildings.\n\n"
        "the new owner sets the height;\nthe footprint never moves.\n\n"
        "envelope gamma = %.0f m,\nFAR x %.1f\nbinds on %d buildings"
        % (sc["envelope_m"], sc["far_mult"], sc["envelope_bind_n"]))
    ax.text(76.25, 47.5, "mode A (redistribute) skips this box:\nownership moves, V is conserved",
            ha="center", va="center", fontsize=6.8, color="#666", zorder=4, style="italic")

    # 5 READ BACK
    fp1 = sc["fingerprint"]
    box(86, 98, 46, 84, "5  READ BACK",
        "the SAME fingerprint,\nplus the ledger\n\n"
        "%d buildings named\n%.2f x 10$^6$ m$^3$ taken\nfrom residents\n\ntotal GFA %+.1f%%\ntarget met: %s"
        % (sc["acquired_n"], sc["displacement_gfa"]["resident"] / 1e6,
           sc["gfa_change_pct"], "yes" if sc["target_met"] else "no"))
    ax.text(92, 52.5, "fingerprint (same 9)\nfar %.2f | h_mean %.1f m | cov %.3f\ngrain %.0f m$^2$ | conc %.3f"
            % (fp1["far"], fp1["h_mean"], fp1["coverage"], fp1["grain"], fp1["concentration"]),
            ha="center", va="center", fontsize=7, color=C.SH_COLOR["state"], zorder=4,
            bbox=dict(boxstyle="round,pad=0.35", fc="#eef2f8", ec=C.SH_COLOR["state"], lw=0.7))

    arrow(17.8, 68, 20.8, 68)
    arrow(34.8, 68, 37.8, 68)
    arrow(66.2, 68, 69.8, 68)
    arrow(82.8, 68, 85.8, 68)

    # the loop: same ruler at both ends
    ax.add_patch(FancyArrowPatch((92, 84.6), (9.75, 84.6), arrowstyle="-|>", mutation_scale=18,
                                 lw=1.6, color=C.SH_COLOR["state"],
                                 connectionstyle="arc3,rad=0.05", zorder=5))
    ax.text(51, 98.0, "ONE RULER, BOTH ENDS  -  the fingerprint that reads the city is the fingerprint that reads the result",
            ha="center", va="center", fontsize=10.5, color=C.SH_COLOR["state"], fontweight="bold", zorder=6)
    ax.text(51, 94.6, "coverage, grain and n are frozen by construction (footprints never move); "
                      "far, h_mean, h_cv, slenderness and concentration are free to move",
            ha="center", va="center", fontsize=7.5, color="#555", zorder=6)
    ax.text(2, 1.5, "substrate: the real Caoyang footprints (n = %d, EPSG:32651). "
                    "Values shown are read from out/cake/metrics_cake.json, scenario %s."
            % (len(recs), SCEN), ha="left", va="bottom", fontsize=6.8, color="#8a8a8a", zorder=6)

    p = FIGS / "fig2_one_ruler.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("fig2 ->", p)
    print("  fingerprint current:", {k: round(v, 4) for k, v in fp0.items()})
    print("  fingerprint after  :", {k: round(v, 4) for k, v in fp1.items()})
    print("  weakness on stock: min %.4f  median %.4f  max %.4f (coverage %.4f)"
          % (wk.min(), float(np.median(wk)), wk.max(), cov))


# ===================================================================== FIG 3
def fig3(maxbars=300):
    cells = reachable(SLUG)
    cur = metrics()[SLUG]["current"]
    devs = sorted({c["dev_target"] for c in cells})
    sts = sorted({c["state_target"] for c in cells})
    hmax = max(max(h for h, _ in c["skyline"]) for c in cells)

    fig = plt.figure(figsize=(14.5, 13.2))
    gs = fig.add_gridspec(5, 5, left=0.085, right=0.985, top=0.885, bottom=0.075,
                          hspace=0.16, wspace=0.09)

    n_unreach = 0
    for c in cells:
        i, j = c["i"], c["j"]                      # i -> dev target, j -> state target
        ax = fig.add_subplot(gs[4 - j, i])         # state target increases upward
        sk = c["skyline"]
        if len(sk) > maxbars:
            idx = np.linspace(0, len(sk) - 1, maxbars).round().astype(int)
            sk = [sk[k] for k in idx]
        hs = np.array([s[0] for s in sk])
        cols = [C.SH_COLOR[s[1]] for s in sk]
        ax.bar(np.arange(len(sk)), hs, width=1.0, color=cols, edgecolor="none")
        ax.set_xlim(-1, len(sk))
        ax.set_ylim(0, hmax * 1.05)
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color("#cfcfcf"); s.set_linewidth(0.6)
        ok = c["dev_met"] and c["state_met"]
        if not ok:
            n_unreach += 1
            ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="#b9b9b9",
                                   alpha=0.55, zorder=5, edgecolor="none"))
            miss = []
            if not c["dev_met"]:
                miss.append("developer")
            if not c["state_met"]:
                miss.append("state")
            ax.text(0.5, 0.56, "unreachable", transform=ax.transAxes, ha="center", va="center",
                    fontsize=11, color="#3b3b3b", fontweight="bold", zorder=6)
            ax.text(0.5, 0.43, "pool exhausted\n(%s target not met)" % " + ".join(miss),
                    transform=ax.transAxes, ha="center", va="center", fontsize=7,
                    color="#3b3b3b", zorder=6)
        ax.text(0.03, 0.95, "dev %.0f%% / state %.0f%%" % (c["dev_target"] * 100, c["state_target"] * 100),
                transform=ax.transAxes, ha="left", va="top", fontsize=7, color=INK, zorder=7)
        ax.text(0.03, 0.855, "reached  %.0f%% / %.0f%%"
                % (c["shares"]["developer"] * 100, c["shares"]["state"] * 100),
                transform=ax.transAxes, ha="left", va="top", fontsize=6.6,
                color="#444" if ok else "#222", zorder=7)
        ax.text(0.97, 0.95, "%d taken\ndGFA %+.1f%%" % (c["acquired"], c["gfa_change_pct"]),
                transform=ax.transAxes, ha="right", va="top", fontsize=6.6, color="#444", zorder=7)
        if j == 0:
            ax.set_xlabel("developer target %.0f%%" % (c["dev_target"] * 100), fontsize=8.5, labelpad=3)
        if i == 0:
            ax.set_ylabel("state target\n%.0f%%" % (c["state_target"] * 100), fontsize=8.5, labelpad=6)
            ax.set_yticks([0, 60, 120, 180, 240])
            ax.tick_params(axis="y", labelsize=6)

    fig.suptitle("The possibility space is an array of skylines", fontsize=14, x=0.085, ha="left", y=0.965, color=INK)
    fig.text(0.085, 0.925,
             "Caoyang, 5 x 5 targets (developer share ->, state share up). Each cell: one thin bar per building "
             "(subsampled to %d of %d), coloured by holder after the run.\n"
             "Both passes are mode B (grow): the developer target is run first, then the state takes from the "
             "developer. Grey cells are honest failures - the gated pool ran out before the target was reached "
             "(%d of %d cells)." % (maxbars, len(cells[0]["skyline"]), n_unreach, len(cells)),
             fontsize=8.6, color="#444", va="top")
    fig.text(0.085, 0.028,
             "cell (0,0) = the district as it is: developer %.1f%%, state %.1f%% of the floor volume, nothing acquired."
             % (cur["shares_gfa"]["developer"] * 100, cur["shares_gfa"]["state"] * 100),
             fontsize=8, color="#666")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor=C.SH_COLOR[c], label=NICE[c]) for c in ORDER],
               loc="lower right", bbox_to_anchor=(0.985, 0.015), ncol=4, fontsize=8.5,
               frameon=False, handlelength=1.1)

    p = FIGS / "fig3_possibility_space.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("fig3 ->", p)
    print("  dev targets:", devs)
    print("  state targets:", sts)
    print("  unreachable cells: %d / %d" % (n_unreach, len(cells)))
    for c in cells:
        print("   i=%d j=%d dev %.3f st %.3f -> dev %.4f st %.4f  met %s/%s  acq %4d  dGFA %+6.2f%%"
              % (c["i"], c["j"], c["dev_target"], c["state_target"], c["shares"]["developer"],
                 c["shares"]["state"], c["dev_met"], c["state_met"], c["acquired"], c["gfa_change_pct"]))


# ===================================================================== FIG 4
def fig4():
    m = metrics()[SLUG]
    cur, sc = m["current"], m[SCEN]
    led = ledger(SLUG, SCEN)
    recs = buildings()
    cfg = cake.load_cfg()
    cov = M.diagnose(recs, SLUG)["coverage"]

    by_bid = {r["bid"]: r for r in led}
    flows = sorted(sc["transfer_matrix"].items(), key=lambda kv: -kv[1])
    flow_n = {}
    for r in led:
        k = r["from_sh"] + "->" + r["to_sh"]
        flow_n[k] = flow_n.get(k, 0) + 1

    fig = plt.figure(figsize=(13.6, 10.4))
    ax = fig.add_axes([0.02, 0.05, 0.72, 0.86])

    cols, edges, lws = [], [], []
    for r in recs:
        l = by_bid.get(r["bid"])
        if l is None:
            cols.append(PALE); edges.append("white"); lws.append(0.12)
        else:
            cols.append(C.SH_COLOR[l["to_sh"]])          # fill = who took it
            edges.append(C.SH_COLOR[l["from_sh"]])       # outline = who lost it
            lws.append(0.7)
    polys, idx = _patches(recs)
    pc = PatchCollection(polys, facecolors=[cols[i] for i in idx],
                         edgecolors=[edges[i] for i in idx],
                         linewidths=[lws[i] for i in idx], zorder=2)
    ax.add_collection(pc)
    bb = [r["geom"].bounds for r in recs]
    minx = min(b[0] for b in bb); miny = min(b[1] for b in bb)
    maxx = max(b[2] for b in bb); maxy = max(b[3] for b in bb)
    pad = 0.02 * max(maxx - minx, maxy - miny)
    ax.set_xlim(minx - pad, maxx + pad); ax.set_ylim(miny - pad, maxy + pad)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    scalebar(ax, (minx, miny, maxx, maxy))

    ax.set_title("Displacement is visible: every building that changed hands, and who lost it\n"
                 "Caoyang | capital_extreme, mode B (grow) | fill = who took it, outline = who lost it",
                 fontsize=12, loc="left", color=INK, pad=8)

    # ---- the ledger, as text -------------------------------------------
    tx = fig.add_axes([0.755, 0.42, 0.235, 0.49]); tx.axis("off")
    y = 1.0
    tx.text(0, y, "THE LEDGER", fontsize=11, fontweight="bold", color=INK, va="top")
    y -= 0.055
    tx.text(0, y, "who lost what, measured on the height\nbefore any rebuild (orig_h)",
            fontsize=7.5, color="#666", va="top")
    y -= 0.085
    V0 = cur["V_total_m3"]
    for k, v in flows:
        src, dst = k.split("->")
        tx.add_patch(Rectangle((0.0, y - 0.035), 0.06, 0.028, transform=tx.transAxes,
                               facecolor=C.SH_COLOR[dst], edgecolor=C.SH_COLOR[src], linewidth=1.6,
                               clip_on=False))
        tx.text(0.09, y - 0.021, "%s  ->  %s" % (NICE[src], NICE[dst]), fontsize=10.5,
                color=INK, va="center", fontweight="bold")
        y -= 0.075
        tx.text(0.09, y, "%s buildings\n%.2f x 10$^6$ m$^3$ of floor volume\n= %.1f%% of the district's cake"
                % (flow_n[k], v / 1e6, 100 * v / V0), fontsize=9, color="#333", va="top", linespacing=1.6)
        y -= 0.135
    y -= 0.02
    tx.text(0, y, "nothing was taken from the state or the\ndeveloper in this run: the gate only lets\n"
                  "capital take from residents.", fontsize=7.6, color="#666", va="top", linespacing=1.5)
    y -= 0.10
    tx.text(0, y, "total floor volume  %+.1f%%\nshare reached  %.1f%%  (target %.0f%%)\n"
                  "pool  %d of %d taken   |   exhausted: %s"
            % (sc["gfa_change_pct"], sc["share_reached"] * 100, sc["target"] * 100,
               sc["acquired_n"], sc["pool_size"], "yes" if sc["pool_exhausted"] else "no"),
            fontsize=8.5, color=INK, va="top", linespacing=1.6)

    # ---- inset: weakness of what was taken vs what was left --------------
    hx = fig.add_axes([0.775, 0.10, 0.20, 0.22])
    w_taken = np.array([r["weakness"] for r in led])
    pool_from = {k.split("->")[0] for k in sc["transfer_matrix"]}
    w_left = np.array([cake.weakness_score(r, cfg, cov, None) for r in recs
                       if r["orig_sh"] in pool_from and r["bid"] not in by_bid])
    bins = np.linspace(0, max(w_taken.max(), w_left.max()) * 1.02, 26)
    hx.hist(w_left, bins=bins, color="#9a9a9a", alpha=0.85, label="left alone (n = %d)" % len(w_left))
    hx.hist(w_taken, bins=bins, color=RED, alpha=0.80, label="taken (n = %d)" % len(w_taken))
    hx.axvline(np.median(w_left), color="#5a5a5a", lw=1.2, ls="--")
    hx.axvline(np.median(w_taken), color=RED, lw=1.2, ls="--")
    hx.set_xlabel("weakness score  (0.5*AGE + 0.5*FAR-gap)", fontsize=7)
    hx.set_ylabel("buildings", fontsize=7)
    hx.tick_params(labelsize=6.5)
    for s in ("top", "right"):
        hx.spines[s].set_visible(False)
    hx.legend(fontsize=6.5, frameon=False, loc="upper left")
    hx.set_title("weak first, and the data says so:\nmedian weakness taken %.3f vs left %.3f"
                 % (np.median(w_taken), np.median(w_left)), fontsize=7.5, color=INK, pad=4)

    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=C.SH_COLOR["developer"], edgecolor=C.SH_COLOR["resident"],
                             linewidth=1.6, label="taken by developer, from resident"),
                       Patch(facecolor=PALE, edgecolor="white", label="not acquired")],
              loc="upper right", fontsize=8, frameon=False, handlelength=1.4, borderpad=0.3)

    p = FIGS / "fig4_displacement.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("fig4 ->", p)
    print("  transfer_matrix:", sc["transfer_matrix"], " counts:", flow_n)
    print("  V_total_m3 = %.1f  -> flow is %.2f%% of the cake" % (V0, 100 * flows[0][1] / V0))
    print("  weakness taken:  n=%d median=%.4f mean=%.4f min=%.4f max=%.4f"
          % (len(w_taken), np.median(w_taken), w_taken.mean(), w_taken.min(), w_taken.max()))
    print("  weakness left:   n=%d median=%.4f mean=%.4f min=%.4f max=%.4f"
          % (len(w_left), np.median(w_left), w_left.mean(), w_left.min(), w_left.max()))


FIGS_FN = {"fig1": fig1, "fig2": fig2, "fig3": fig3, "fig4": fig4}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = list(FIGS_FN) if which == "all" else [which]
    for t in todo:
        FIGS_FN[t]()
