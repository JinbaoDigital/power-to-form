"""
figs_nr10.py — NEXT_RUN_10, Task B: the four cross-case figures (F1..F4).

    python3 figs_nr10.py f1 | f2 | f3 | f4 | all

Reads only what is already on disk:
    out/cake/metrics_cake_all.json    8 sites x (current + 5 scenarios) x modes A/B
    out/cake/reachable_<slug>.json    the 5 x 5 target grid, per site
    out/cake_figs/shot_<slug>_<config>.png       agent-3d Three.js massing screenshots
    out/cake_figs/shot_sky_<slug>_<config>.png   agent-3d Three.js skyline screenshots
    engine/data/<slug>/buildings.parquet         via pf_common.load_buildings

Writes only into out/cake_figs/.  metrics_cake.json, invariance.csv and the frozen
site outputs are never touched.  No 3D is drawn in matplotlib: every massing or
skyline *image* on these sheets is a crop of an agent-3d screenshot.  The 5 x 5
grid thumbnails in F4 are 2D height profiles (one bar per building, placed at its
true easting), which is the same construction figs_cake.fig3 already uses.

Palette and drawing helpers are reused from figs_cake / pf_common.
"""
import sys
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pf_common as C            # noqa: E402  (SH_COLOR, load_buildings)
import figs_cake as FC           # noqa: E402  (plan, scalebar, share_bar, ORDER, INK)

CAKE = HERE / "out" / "cake"
OUT = HERE / "out" / "cake_figs"
OUT.mkdir(parents=True, exist_ok=True)

DPI = 160
INK = FC.INK
ORDER = FC.ORDER
GREY = "#b9b9b9"
FAIL = "#c62828"

# CJK: verified to render with Noto Sans CJK JP in this environment.
CJK = "Noto Sans CJK JP"
_have_cjk = CJK in {f.name for f in matplotlib.font_manager.fontManager.ttflist}
plt.rcParams.update({
    "font.family": ([CJK] if _have_cjk else []) + ["DejaVu Sans"],
    "axes.unicode_minus": False,
    "axes.linewidth": 0.6,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
})

# the four power configurations, mode B (grow), plus the as-found city
CONFIGS = [
    ("current",       "Current",       "current"),
    ("developer-led", "Developer-led", "capital_deepen_B"),
    ("state-led",     "State-led",     "state_civic_B"),
    ("resident-led",  "Resident-led",  "resident_retain_B"),
    ("shared",        "Shared",        "shared_commons_B"),
]
SHOT = [c[0] for c in CONFIGS]          # screenshot filename token
LABEL = [c[1] for c in CONFIGS]
KEY = [c[2] for c in CONFIGS]

SITES = ["lujiazui", "nanjingxi", "caoyang", "pengpu", "laoximen", "yuyuan", "dapuqiao", "zhangjiang"]
FAMILY = {
    "lujiazui": "capital", "nanjingxi": "capital",
    "caoyang": "danwei", "pengpu": "danwei",
    "laoximen": "lilong", "yuyuan": "lilong", "dapuqiao": "lilong",
    "zhangjiang": "industry",
}
FAM_LABEL = {
    "capital": "capital / high-rise CBD",
    "danwei": "danwei workers' village",
    "lilong": "old-town lilong",
    "industry": "industry / tech new town",
}
# English display names for the figures (the site.yaml name is Chinese); slug stays the data id.
EN_NAME = {
    "lujiazui": "Lujiazui", "nanjingxi": "Nanjingxi Rd",
    "caoyang": "Caoyang Xincun", "pengpu": "Pengpu Xincun",
    "laoximen": "Laoximen", "yuyuan": "Yuyuan",
    "dapuqiao": "Dapuqiao", "zhangjiang": "Zhangjiang",
}
FAM_COLOR = {"capital": "#b5432f", "danwei": "#3f6fa8", "lilong": "#4f8f63", "industry": "#8a6d9c"}
FAM_MARK = {0: "o", 1: "s", 2: "^"}     # to separate sites inside one family

METRICS = [
    ("far", "FAR  (floor area ratio)", False),
    ("h_mean", "h_mean  (m)", False),
    ("h_cv", "h_cv  (height dispersion)", False),
    ("slender", "slenderness", False),
    ("concentration", "concentration  (of floor volume)", False),
    ("h_max", "h_max  (m)", False),
    ("coverage", "coverage", True),
    ("grain", "grain  (median footprint, m$^2$)", True),
]
FP9 = ["far", "coverage", "h_mean", "h_max", "h_cv", "grain", "slender", "concentration", "n"]
FP9_LAB = ["FAR", "coverage", "h_mean", "h_max", "h_cv", "grain", "slender", "conc.", "n"]


# ------------------------------------------------------------------ loaders
def M():
    return json.load(open(CAKE / "metrics_cake_all.json", encoding="utf-8"))


def reachable(slug):
    return json.load(open(CAKE / ("reachable_%s.json" % slug), encoding="utf-8"))


def site_title(m, slug):
    s = m[slug]["site"]
    return EN_NAME.get(slug, s["name"]), s["area_km2"], s["n"]


# ------------------------------------------------------------------ screenshots
_crop_cache = {}


def _content_bbox(im, thr=248):
    a = np.asarray(im.convert("RGB"))
    nz = np.where((a < thr).any(axis=2))
    if len(nz[0]) == 0:
        return (0, 0, im.width, im.height)
    return (int(nz[1].min()), int(nz[0].min()), int(nz[1].max()) + 1, int(nz[0].max()) + 1)


def shot(slug, cfg, view="massing", pad=10):
    """agent-3d screenshot, cropped to the UNION content box of all five configs of
    this site+view, so the five images stay pixel-comparable."""
    pre = "shot_sky_" if view == "skyline" else "shot_"
    key = (slug, view)
    if key not in _crop_cache:
        boxes = []
        for c in SHOT:
            p = OUT / ("%s%s_%s.png" % (pre, slug, c))
            if p.exists():
                boxes.append(_content_bbox(Image.open(p)))
        if not boxes:
            _crop_cache[key] = None
        else:
            x0 = max(0, min(b[0] for b in boxes) - pad)
            y0 = max(0, min(b[1] for b in boxes) - pad)
            x1 = max(b[2] for b in boxes) + pad
            y1 = max(b[3] for b in boxes) + pad
            _crop_cache[key] = (x0, y0, x1, y1)
    box = _crop_cache[key]
    p = OUT / ("%s%s_%s.png" % (pre, slug, cfg))
    if not p.exists():
        return None
    im = Image.open(p).convert("RGB")
    if box:
        im = im.crop((box[0], box[1], min(box[2], im.width), min(box[3], im.height)))
    return np.asarray(im)


def imshow(ax, arr):
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    if arr is None:
        ax.text(0.5, 0.5, "screenshot missing", ha="center", va="center", fontsize=8, color=FAIL)
        return
    ax.imshow(arr, interpolation="antialiased")


# ------------------------------------------------------------------ stats
def _rank(v):
    v = np.asarray(v, float)
    order = v.argsort()
    r = np.empty(len(v), float)
    r[order] = np.arange(len(v), dtype=float)
    # average ties
    for u in np.unique(v):
        k = v == u
        if k.sum() > 1:
            r[k] = r[k].mean()
    return r


def spearman(a, b):
    ra, rb = _rank(a), _rank(b)
    if ra.std() == 0 or rb.std() == 0:
        return 1.0
    return float(np.corrcoef(ra, rb)[0, 1])


def legend_holders(fig, loc, ncol=4, fs=8.5, bbox=None):
    fig.legend(handles=[Patch(facecolor=C.SH_COLOR[c], label=FC.NICE[c]) for c in ORDER],
               loc=loc, bbox_to_anchor=bbox, ncol=ncol, fontsize=fs, frameon=False,
               handlelength=1.1, title="holder of the floor volume",
               title_fontsize=fs)


# ===================================================================== F1
def f1():
    """Site atlas: as-found plan + as-found skyline + 9-axis fingerprint radar, per site."""
    m = M()
    recs = {s: C.load_buildings(s) for s in SITES}
    fp = {s: m[s]["current"]["fingerprint"] for s in SITES}
    lo = {k: min(fp[s][k] for s in SITES) for k in FP9}
    hi = {k: max(fp[s][k] for s in SITES) for k in FP9}

    def norm(s):
        return [0.10 + 0.90 * (fp[s][k] - lo[k]) / (hi[k] - lo[k]) if hi[k] > lo[k] else 0.5
                for k in FP9]

    ang = np.linspace(0, 2 * np.pi, len(FP9), endpoint=False)
    ang_c = np.concatenate([ang, ang[:1]])

    nrow = len(SITES)
    RH, HEAD = 2.75, 1.35
    FH = RH * nrow + HEAD
    fig = plt.figure(figsize=(16.4, FH))
    gs = fig.add_gridspec(nrow, 4, width_ratios=[1.0, 1.55, 0.82, 0.62],
                          left=0.035, right=0.985, top=1 - (HEAD - 0.35) / FH,
                          bottom=0.45 / FH, hspace=0.52, wspace=0.05)

    for i, s in enumerate(SITES):
        name, km2, n = site_title(m, s)
        cur = m[s]["current"]
        f = FAMILY[s]

        # --- figure-ground plan, coloured by holder
        a = fig.add_subplot(gs[i, 0])
        r = recs[s]
        b = FC.plan(a, r, [C.SH_COLOR[x["sh"]] for x in r], lw=0.10)
        FC.scalebar(a, b, 200, "200 m")
        a.text(0.0, 1.115, name, transform=a.transAxes, fontsize=11.5,
               color=INK, va="bottom", fontweight="bold")
        a.text(0.0, 1.035, FAM_LABEL[f], transform=a.transAxes, fontsize=8.4,
               color=FAM_COLOR[f], va="bottom", ha="left")
        a.text(0.0, -0.045, "n = %d   %.2f km$^2$   FAR %.2f   coverage %.3f   V = %.1f x 10$^6$ m$^3$"
               % (n, km2, cur["fingerprint"]["far"], cur["coverage"], cur["V_total_m3"] / 1e6),
               transform=a.transAxes, fontsize=7.6, color="#555", va="top")

        # --- as-found skyline (agent-3d screenshot)
        a2 = fig.add_subplot(gs[i, 1])
        imshow(a2, shot(s, "current", "skyline"))
        a2.text(0.005, 1.03, "as-found skyline (Three.js elevation, holder-coloured)",
                transform=a2.transAxes, fontsize=7.8, color="#555", va="bottom")
        a2.text(0.995, 1.03, "h_mean %.1f m   h_max %.0f m   h_cv %.2f"
                % (cur["fingerprint"]["h_mean"], cur["fingerprint"]["h_max"], cur["fingerprint"]["h_cv"]),
                transform=a2.transAxes, fontsize=7.6, color=INK, va="bottom", ha="right")

        # --- 9-axis fingerprint radar (min-max across the 8 cases)
        a3 = fig.add_subplot(gs[i, 2], projection="polar")
        for other in SITES:
            if other == s:
                continue
            v = np.array(norm(other)); v = np.concatenate([v, v[:1]])
            a3.plot(ang_c, v, color="#d8d8d8", lw=0.7, zorder=1)
        v = np.array(norm(s)); v = np.concatenate([v, v[:1]])
        a3.plot(ang_c, v, color=FAM_COLOR[f], lw=1.9, zorder=3)
        a3.fill(ang_c, v, color=FAM_COLOR[f], alpha=0.22, zorder=2)
        a3.set_xticks(ang)
        a3.set_xticklabels(FP9_LAB, fontsize=6.6, color="#444")
        a3.set_yticks([0.25, 0.5, 0.75, 1.0])
        a3.set_yticklabels([])
        a3.set_ylim(0, 1.08)
        a3.grid(color="#e6e6e6", lw=0.5)
        a3.spines["polar"].set_color("#dddddd")
        a3.tick_params(pad=-1)

        # --- holder shares
        a4 = fig.add_subplot(gs[i, 3])
        a4.set_position(a4.get_position())
        sub = a4.inset_axes([0.02, 0.36, 0.96, 0.16])
        FC.share_bar(sub, cur["shares_gfa"], None, fs=6.6)
        a4.axis("off")
        sh = cur["shares_gfa"]
        a4.text(0.02, 0.60, "GFA held by", transform=a4.transAxes, fontsize=7.2, color="#666",
                va="bottom")
        a4.text(0.02, 0.30, "state %.1f%%   developer %.1f%%\nresident %.1f%%   unknown %.1f%%"
                % (sh["state"] * 100, sh["developer"] * 100, sh["resident"] * 100, sh["unknown"] * 100),
                transform=a4.transAxes, fontsize=7.4, color=INK, va="top", linespacing=1.7)

    legend_holders(fig, "upper right", bbox=(0.985, 1 - 0.40 / FH), ncol=4, fs=9)

    p = OUT / "F1_atlas.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("F1 ->", p)
    for s in SITES:
        print("   %-11s far %.3f cov %.3f h_mean %5.1f h_max %5.0f h_cv %.3f grain %6.1f slender %.3f conc %.3f  res %.3f"
              % (s, fp[s]["far"], fp[s]["coverage"], fp[s]["h_mean"], fp[s]["h_max"], fp[s]["h_cv"],
                 fp[s]["grain"], fp[s]["slender"], fp[s]["concentration"],
                 m[s]["current"]["shares_gfa"]["resident"]))


# ===================================================================== F2
def f2(view="massing"):
    """Power-configuration gallery: 8 sites x (current + 4 configurations), from agent-3d shots."""
    m = M()
    nrow, ncol = len(SITES), len(CONFIGS)
    cellw = 3.65 if view == "massing" else 3.9
    cellh = 2.55 if view == "massing" else 1.62
    fig = plt.figure(figsize=(1.85 + cellw * ncol, 1.75 + cellh * nrow))
    top = 1 - 0.55 / fig.get_figheight()
    gs = fig.add_gridspec(nrow, ncol, left=1.78 / fig.get_figwidth(), right=0.995,
                          top=top, bottom=1.15 / fig.get_figheight(),
                          hspace=0.40 if view == "massing" else 0.78, wspace=0.02)

    for i, s in enumerate(SITES):
        name, km2, n = site_title(m, s)
        f = FAMILY[s]
        for j, (cfg, lab, key) in enumerate(CONFIGS):
            ax = fig.add_subplot(gs[i, j])
            imshow(ax, shot(s, cfg, view))
            d = m[s][key]
            fpj = d["fingerprint"]
            if j == 0:
                txt = "FAR %.2f   h_mean %.1f m   h_cv %.2f" % (fpj["far"], fpj["h_mean"], fpj["h_cv"])
                col = "#555"
            else:
                d0 = m[s]["current"]["fingerprint"]
                txt = ("FAR %.2f (%+.0f%%)   h_mean %.1f m   h_cv %.2f   %d buildings rebuilt"
                       % (fpj["far"], 100 * (fpj["far"] / d0["far"] - 1), fpj["h_mean"],
                          fpj["h_cv"], d["acquired_n"]))
                col = "#555"
            def under(s, dy, color, **kw):
                ax.annotate(s, xy=(0.005, 0.0), xycoords="axes fraction",
                            xytext=(0, dy), textcoords="offset points",
                            fontsize=7.4, color=color, va="top", ha="left", **kw)

            under(txt, -6, col)
            if j > 0 and not d["target_met"]:
                under("target not reachable on this fabric: stops at %.3f of %.2f"
                      % (d["share_reached"], d["target"]), -18, FAIL, fontweight="bold")
                ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False,
                                       edgecolor=FAIL, lw=1.6, zorder=6))
            elif j > 0 and d["acquired_n"] == 0:
                under("already past the target: nothing changes", -18, "#7a7a7a", style="italic")
            if i == 0:
                ax.set_title(lab, fontsize=12.5, color=INK, pad=8,
                             fontweight="bold" if j else "normal")
            if j == 0:
                ax.text(-0.018, 0.62, name, transform=ax.transAxes, fontsize=10.5, color=INK,
                        ha="right", va="center", fontweight="bold", rotation=0)
                ax.text(-0.018, 0.42, s, transform=ax.transAxes, fontsize=8.2, color="#777",
                        ha="right", va="center")
                ax.text(-0.018, 0.26, FAM_LABEL[f], transform=ax.transAxes, fontsize=7.4,
                        color=FAM_COLOR[f], ha="right", va="center")

    legend_holders(fig, "lower left", bbox=(1.78 / fig.get_figwidth(), 0.008), ncol=4, fs=9.5)

    p = OUT / ("F2_gallery.png" if view == "massing" else "F2_gallery_skyline.png")
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("F2 (%s) ->" % view, p)
    if view == "massing":
        for s in SITES:
            row = []
            for cfg, lab, key in CONFIGS[1:]:
                d = m[s][key]
                row.append("%s %.3f/%.2f%s" % (lab[:4], d["share_reached"], d["target"],
                                               "" if d["target_met"] else " FAIL"))
            print("   %-11s %s" % (s, " | ".join(row)))


# ===================================================================== F3
def f3():
    """Cross-case fingerprint comparison + rank-preservation (substrate memory)."""
    m = M()
    fam_i = {}
    for s in SITES:
        fam_i[s] = sum(1 for t in SITES[:SITES.index(s)] if FAMILY[t] == FAMILY[s])

    fig = plt.figure(figsize=(20.6, 12.6))
    gs = fig.add_gridspec(3, 3, left=0.044, right=0.775, top=0.945, bottom=0.055,
                          hspace=0.42, wspace=0.22)
    x = np.arange(len(CONFIGS))

    sp = {}     # spearman[metric][config]
    for qi, (met, lab, frozen) in enumerate(METRICS):
        ax = fig.add_subplot(gs[qi // 3, qi % 3])
        base = [m[s]["current"]["fingerprint"][met] for s in SITES]
        sp[met] = [spearman(base, [m[s][k]["fingerprint"][met] for s in SITES]) for k in KEY]

        labs = []
        for s in SITES:
            v = [m[s][k]["fingerprint"][met] for k in KEY]
            col = FAM_COLOR[FAMILY[s]]
            ax.plot(x, v, color=col, lw=1.5, alpha=0.9, zorder=3,
                    marker=FAM_MARK[fam_i[s]], ms=5.0, mew=0.0,
                    ls="-" if fam_i[s] == 0 else ("--" if fam_i[s] == 1 else ":"))
            # hollow the marker where the configuration could not reach its target
            for j, k in enumerate(KEY):
                if j and not m[s][k]["target_met"]:
                    ax.plot([x[j]], [v[j]], marker=FAM_MARK[fam_i[s]], ms=8.5, mfc="white",
                            mec=FAIL, mew=1.6, zorder=4, ls="none")
            labs.append([v[0], s, col])

        # de-overlap the left-hand site labels
        y0, y1 = ax.get_ylim()
        gap = (y1 - y0) * 0.042
        labs.sort(key=lambda t: t[0])
        for q in range(1, len(labs)):
            if labs[q][0] - labs[q - 1][0] < gap:
                labs[q][0] = labs[q - 1][0] + gap
        for yv, s, col in labs:
            ax.text(x[0] - 0.14, yv, s, fontsize=6.8, color=col, ha="right", va="center", zorder=5)

        ax.set_xticks(x)
        ax.set_xticklabels(["current", "dev-led", "state-led", "res-led", "shared"], fontsize=8.2)
        ax.set_xlim(-1.05, len(CONFIGS) - 0.55)
        ax.tick_params(axis="y", labelsize=7.5)
        for sp_ in ("top", "right"):
            ax.spines[sp_].set_visible(False)
        ax.set_title(lab, fontsize=11, color=INK, loc="left", pad=16)
        if frozen:
            ax.text(0.0, 1.015, "frozen by construction (footprints never move)",
                    transform=ax.transAxes, fontsize=7.4, color="#8a8a8a", va="bottom", style="italic")
        else:
            ax.text(0.0, 1.015, "rank kept vs current (Spearman):   " +
                    "   ".join("%s %.2f" % (l, sp[met][j])
                               for j, l in enumerate(["dev", "state", "res", "shared"], start=1)),
                    transform=ax.transAxes, fontsize=7.6, va="bottom",
                    color="#555")
        ax.grid(axis="y", color="#eeeeee", lw=0.6, zorder=0)
        ax.set_axisbelow(True)

    # ---- panel 9: the rank-preservation heatmap
    ax = fig.add_subplot(gs[2, 2])
    mets = [mt for mt, _, fr in METRICS if not fr]
    Z = np.array([[sp[mt][j] for j in range(1, 5)] for mt in mets])
    im = ax.imshow(Z, cmap="RdYlBu", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(4)); ax.set_xticklabels(["dev-led", "state-led", "res-led", "shared"], fontsize=8.5)
    ax.set_yticks(range(len(mets)))
    ax.set_yticklabels([dict((mt, l) for mt, l, _ in METRICS)[mt].split("  ")[0] for mt in mets], fontsize=8.5)
    for a_ in range(Z.shape[0]):
        for b_ in range(Z.shape[1]):
            ax.text(b_, a_, "%.2f" % Z[a_, b_], ha="center", va="center", fontsize=8.6,
                    color="#111" if Z[a_, b_] > 0.45 else "white", fontweight="bold")
    ax.set_title("rank correlation by metric and configuration", fontsize=11, color=INK, loc="left", pad=16)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("1.00 = ordering kept", fontsize=7)
    cb.ax.tick_params(labelsize=7)

    # ---- side rail: family / marker legend
    RX = 0.812
    h = []
    for fam in ["capital", "danwei", "lilong", "industry"]:
        h.append(Line2D([0], [0], color=FAM_COLOR[fam], lw=2.0, label=FAM_LABEL[fam]))
    h.append(Line2D([0], [0], color="white", marker="o", ms=9, mfc="white", mec=FAIL, mew=1.6,
                    label="target not reachable on that fabric"))
    fig.legend(handles=h, loc="upper left", bbox_to_anchor=(RX - 0.003, 0.925), fontsize=8.5,
               frameon=False, handlelength=1.8, labelspacing=0.7,
               title="line colour = case family (not holder)", title_fontsize=8.5)

    p = OUT / "F3_fingerprints.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("F3 ->", p)
    for mt, lab, fr in METRICS:
        print("   %-14s rho vs current: dev %.3f  state %.3f  res %.3f  shared %.3f %s"
              % (mt, sp[mt][1], sp[mt][2], sp[mt][3], sp[mt][4], "(frozen)" if fr else ""))


# ===================================================================== F4
def _profile(ax, cells_sky, recs, hmax, maxbars=260):
    """2D height profile: one bar per building at its true easting, coloured by holder."""
    xs = np.array([r["geom"].centroid.x for r in recs])
    ar = np.array([r["area"] for r in recs])
    o = np.argsort(xs)
    if len(o) > maxbars:
        o = o[np.linspace(0, len(o) - 1, maxbars).round().astype(int)]
    hs = np.array([cells_sky[i][0] for i in o])
    cl = [C.SH_COLOR[cells_sky[i][1]] for i in o]
    wd = np.sqrt(ar[o]) * 1.6
    ax.bar(xs[o], hs, width=wd, color=cl, edgecolor="none", zorder=2)
    ax.set_xlim(xs.min() - 40, xs.max() + 40)
    ax.set_ylim(0, hmax * 1.05)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#d5d5d5"); s.set_linewidth(0.6)


def f4(slugs=("pengpu", "zhangjiang", "lujiazui")):
    m = M()
    for slug in slugs:
        cells = reachable(slug)
        recs = C.load_buildings(slug)
        cur = m[slug]["current"]
        name, km2, n = site_title(m, slug)
        hmax = max(max(h for h, _ in c["skyline"]) for c in cells)
        n_un = sum(1 for c in cells if not (c["dev_met"] and c["state_met"]))

        fig = plt.figure(figsize=(15.6, 15.4))
        gsa = fig.add_gridspec(1, 1, left=0.055, right=0.985, top=0.985, bottom=0.800)
        ax0 = fig.add_subplot(gsa[0])
        imshow(ax0, shot(slug, "current", "skyline"))
        ax0.text(0.004, -0.03, "the fabric as found (Three.js elevation): %s   n = %d   FAR %.2f   "
                               "state %.1f%% / developer %.1f%% / resident %.1f%% of the floor volume"
                 % (name, n, cur["fingerprint"]["far"], cur["shares_gfa"]["state"] * 100,
                    cur["shares_gfa"]["developer"] * 100, cur["shares_gfa"]["resident"] * 100),
                 transform=ax0.transAxes, fontsize=9, color="#444", va="top")

        gs = fig.add_gridspec(5, 5, left=0.075, right=0.985, top=0.760, bottom=0.055,
                              hspace=0.14, wspace=0.06)
        for c in cells:
            i, j = c["i"], c["j"]
            ax = fig.add_subplot(gs[4 - j, i])
            _profile(ax, c["skyline"], recs, hmax)
            ok = c["dev_met"] and c["state_met"]
            if not ok:
                ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="#bcbcbc",
                                       alpha=0.62, zorder=5, edgecolor="none"))
                ax.text(0.5, 0.58, "not reachable\non this fabric", transform=ax.transAxes,
                        ha="center", va="center", fontsize=9.5, color="#2e2e2e",
                        fontweight="bold", zorder=6, linespacing=1.4)
                miss = []
                if not c["dev_met"]:
                    miss.append("developer %.3f" % c["shares"]["developer"])
                if not c["state_met"]:
                    miss.append("state %.3f" % c["shares"]["state"])
                ax.text(0.5, 0.40, "pool exhausted\nstops at %s" % ",  ".join(miss),
                        transform=ax.transAxes, ha="center", va="center", fontsize=6.8,
                        color="#333", zorder=6, linespacing=1.4)
            ax.text(0.03, 0.955, "dev %.0f%% / state %.0f%%"
                    % (c["dev_target"] * 100, c["state_target"] * 100),
                    transform=ax.transAxes, ha="left", va="top", fontsize=7.2, color=INK, zorder=7)
            ax.text(0.03, 0.865, "reached %.0f%% / %.0f%%"
                    % (c["shares"]["developer"] * 100, c["shares"]["state"] * 100),
                    transform=ax.transAxes, ha="left", va="top", fontsize=6.5, color="#555", zorder=7)
            ax.text(0.97, 0.955, "%d rebuilt\nFAR %.2f" % (c["acquired"], c["fingerprint"]["far"]),
                    transform=ax.transAxes, ha="right", va="top", fontsize=6.5, color="#555", zorder=7)
            if j == 0:
                ax.set_xlabel("developer target %.0f%%" % (c["dev_target"] * 100), fontsize=8.6, labelpad=3)
            if i == 0:
                ax.set_ylabel("state target\n%.0f%%" % (c["state_target"] * 100), fontsize=8.6, labelpad=8)
                ax.set_yticks(np.linspace(0, hmax, 4).round(-1))
                ax.tick_params(axis="y", labelsize=6)

        legend_holders(fig, "lower right", bbox=(0.985, 0.004), ncol=4, fs=8.5)
        p = OUT / ("F4_reachable_%s.png" % slug)
        fig.savefig(p, dpi=DPI)
        plt.close(fig)
        print("F4 ->", p, " unreachable %d/%d" % (n_un, len(cells)))

    # ---- the cross-case reachability map: all 8 fabrics, one panel each
    fig = plt.figure(figsize=(16.4, 6.0))
    gs = fig.add_gridspec(2, 4, left=0.045, right=0.985, top=0.86, bottom=0.09,
                          hspace=0.62, wspace=0.30)
    tot = {}
    for q, slug in enumerate(SITES):
        cells = reachable(slug)
        ax = fig.add_subplot(gs[q // 4, q % 4])
        Z = np.zeros((5, 5))
        for c in cells:
            Z[4 - c["j"], c["i"]] = 1.0 if (c["dev_met"] and c["state_met"]) else 0.0
        n_un = int((Z == 0).sum())
        tot[slug] = n_un
        ax.imshow(Z, cmap=matplotlib.colors.ListedColormap(["#bcbcbc", "#eaf2e9"]), vmin=0, vmax=1)
        for c in cells:
            ok = c["dev_met"] and c["state_met"]
            ax.text(c["i"], 4 - c["j"], "ok" if ok else "x", ha="center", va="center",
                    fontsize=7.5, color="#4f8f63" if ok else "#333",
                    fontweight="bold" if not ok else "normal")
        ax.set_xticks(range(5))
        ax.set_xticklabels(["%.0f" % (c["dev_target"] * 100) for c in
                            sorted([c for c in cells if c["j"] == 0], key=lambda c: c["i"])], fontsize=6.6)
        ax.set_yticks(range(5))
        ax.set_yticklabels(["%.0f" % (c["state_target"] * 100) for c in
                            sorted([c for c in cells if c["i"] == 0], key=lambda c: -c["j"])], fontsize=6.6)
        ax.set_xlabel("developer target %", fontsize=7.4, labelpad=1)
        if q % 4 == 0:
            ax.set_ylabel("state target %", fontsize=7.4)
        for s_ in ax.spines.values():
            s_.set_color("#cccccc")
        ax.set_title("%s\n%d of 25 unreachable" % (slug, n_un), fontsize=9,
                     color=FAM_COLOR[FAMILY[slug]], pad=5, loc="left", linespacing=1.5)
    p = OUT / "F4_reachability_all.png"
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("F4b ->", p)
    print("   unreachable per site:", tot)


FN = {"f1": f1, "f2": lambda: (f2("massing"), f2("skyline")), "f3": f3, "f4": f4}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for t in (list(FN) if which == "all" else [which]):
        FN[t]()
