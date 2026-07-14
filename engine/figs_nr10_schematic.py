"""
figs_nr10_schematic.py - NEXT_RUN_10, Task B, the two schematics (F5, F6).

    python3 figs_nr10_schematic.py f5 | f6 | all

F5_loop.png       the tool skeleton: read -> map -> transform -> read-back, closed,
                  grown on a real site (Laoximen, 923 real footprints, EPSG:32651).
                  The transform cell is labelled SWAPPABLE LENS: power is the lens
                  currently installed; four dashed ghost lenses sit in the magazine
                  below it (heritage/age, market/rent gap, environment, regulation).
F6_parameters.png the seven parameter families that shape urban form against the
                  question "has generative design operationalised it?". Six filled
                  rows, one empty cell (power). Vector schematic, no data, no counts.

Reads only what is already on disk:
    out/cake/metrics_cake_all.json                  fingerprints, shares, scenario headlines
    out/cake/ledger_laoximen_capital_deepen_B.csv   per-building h_after under the installed lens
    engine/data/laoximen/buildings.parquet          via pf_common.load_buildings
    engine/config/scenarios.yaml                    via cake.load_cfg (weakness weights)
Writes only into out/cake_figs/.  Nothing under paper/figures/cake, metrics_cake.json
or invariance.csv is touched.  Every number printed on F5 comes from those files;
F6 carries no numbers at all.
"""
import sys
import csv
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pf_common as C          # noqa: E402   load_buildings
import figs_cake as FC         # noqa: E402   plan()
import cake                    # noqa: E402   weakness_score, load_cfg
import measure as M            # noqa: E402   diagnose -> coverage

CAKE = HERE / "out" / "cake"
OUT = HERE / "out" / "cake_figs"
OUT.mkdir(parents=True, exist_ok=True)

DPI = 160

# ------------------------------------------------------------- monochrome ink
# Black-and-white line-art spec (Elsevier artwork guidelines; Conzen /
# Hillier / Habraken monochrome tradition).  This palette is the ONLY ink
# used anywhere in F5 and F6.
BLACK = "#000000"       # text, primary strokes
DARK = "#262626"        # darkest data grey          (holder: state)
MID = "#737373"         # annotations, mid grey      (holder: developer)
LIGHT = "#BFBFBF"       # hairline grey              (holder: resident)
PALE = "#EDEDED"        # background bands / cards only
WHITE = "#ffffff"

# Stroke hierarchy in PRINTED points.  The figures are authored larger than a
# 190 mm full-page print width (F5 18 in ~ 2.4x, F6 15 in ~ 2.0x), so figure
# linewidth = printed pt * scale.  Exactly three levels:
#   primary   1.0-1.2 pt  stage boxes, emphasised borders, table top/bottom rules
#   secondary 0.5-0.75 pt ordinary borders, midrules, arrow shafts, glyph outlines
#   hairline  0.3 pt      row separators, leaders, hatch lines, card outlines
PT_F5, PT_F6 = 2.4, 2.0


def LW(pt, scale):
    """printed-point stroke weight -> figure linewidth."""
    return pt * scale


# dash semantics:  solid = existing / implemented;
#                  dashed = projected / optional / feedback;
#                  dotted = absent / unknown.
DASH = (0, (4, 2))
DOTTED = (0, (1, 2))

# ordinal greyscale for holders, darker = more concentrated control
HOLDER_GREY = {"state": DARK, "developer": MID, "resident": LIGHT,
               "unknown": PALE, "informal": PALE}

SLUG = "laoximen"
LENS_SCEN = "capital_deepen_B"          # developer-led, mode B (grow)
LENS_NAME = "developer-led"

# Arial first (Elsevier), silent fallback down the list; a CJK face is
# appended for 老西门街道 in the READ box and the footer.  font.family as an
# explicit list (not the "sans-serif" alias) enables per-glyph fallback.
_TTF = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
_LATIN = next((f for f in ("Arial", "Helvetica", "DejaVu Sans") if f in _TTF),
              "sans-serif")
_CJK = next((f for f in ("Noto Sans CJK JP", "Hiragino Sans GB", "PingFang HK",
                         "Heiti TC") if f in _TTF), None)
plt.rcParams.update({
    "font.family": [_LATIN] + ([_CJK] if _CJK else []),
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "axes.linewidth": 0.6,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "hatch.linewidth": LW(0.3, PT_F6),  # hairline hatch: the F6 gap cell
    "pdf.fonttype": 42,                 # TrueType in the vector outputs
})

ORDER = ("state", "developer", "resident", "unknown")


def metrics():
    return json.load(open(CAKE / "metrics_cake_all.json", encoding="utf-8"))


def ledger(slug, scen):
    with open(CAKE / ("ledger_%s_%s.csv" % (slug, scen)), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["bid"] = int(r["bid"])
        for k in ("h_before", "h_after", "weakness"):
            r[k] = float(r[k])
    return rows


# ===================================================================== F5
def f5():
    m = metrics()[SLUG]
    cur, sc = m["current"], m[LENS_SCEN]
    site = m["site"]
    recs = C.load_buildings(SLUG)
    cfg = cake.load_cfg()
    cov = M.diagnose(recs, SLUG)["coverage"]
    wk = np.array([cake.weakness_score(r, cfg, cov, None) for r in recs])
    led = ledger(SLUG, LENS_SCEN)
    h_after_by_bid = {r["bid"]: r["h_after"] for r in led}

    h0 = np.array([r["h"] for r in recs])
    h1 = np.array([h_after_by_bid.get(r["bid"], r["h"]) for r in recs])
    hmax = float(max(h0.max(), h1.max()))
    hnorm = mcolors.Normalize(vmin=-8.0, vmax=hmax)     # vmin < 0 keeps the lowest sheds visible
    hcmap = plt.get_cmap("Greys")
    wspan = float(wk.max()) - float(wk.min())
    wnorm = mcolors.Normalize(vmin=float(wk.min()) - 0.18 * wspan,
                              vmax=float(wk.max()))     # padded: min stays visible
    wcmap = plt.get_cmap("Greys")                       # dark = read as weak

    s = PT_F5
    FS_T, FS_H, FS_B = 11.5, 8.6, 7.2   # exactly three sizes: title / header / body

    YTOP = 91.0                       # crop the empty band the removed title used to occupy
    yk = 100.0 / YTOP                 # figure-fraction rescale so insets keep their data-y position
    FW, FH = 18.0, 11.2 * YTOP / 100.0
    fig = plt.figure(figsize=(FW, FH))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100); ax.set_ylim(0, YTOP)
    ax.axis("off")

    def box(x0, x1, y0, y1, title, fc=WHITE, sub=None, emph=False):
        ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                                    boxstyle="round,pad=0.5,rounding_size=1.1",
                                    fc=fc, ec=BLACK, lw=LW(1.0, s), zorder=2))
        if emph:   # double border: outer 1.0 pt + inner 0.5 pt, ~1.5 pt offset
            ax.add_patch(FancyBboxPatch((x0 + 0.28, y0 + 0.42),
                                        (x1 - x0) - 0.56, (y1 - y0) - 0.84,
                                        boxstyle="round,pad=0.5,rounding_size=1.0",
                                        fc="none", ec=BLACK, lw=LW(0.5, s), zorder=2))
        ax.text((x0 + x1) / 2, y1 - 2.4, title, ha="center", va="top", fontsize=FS_T,
                fontweight="bold", color=BLACK, zorder=4)
        if sub:
            ax.text((x0 + x1) / 2, y1 - 6.0, sub, ha="center", va="top", fontsize=FS_B,
                    color=MID, zorder=4, linespacing=1.5)

    def arrow(x0, y0, x1, y1, lw=LW(1.0, PT_F5), color=BLACK, rad=0.0, ls="-", ms=17, z=6):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=ms,
                                     lw=lw, color=color, linestyle=ls,
                                     connectionstyle="arc3,rad=%.2f" % rad, zorder=z))

    def inset(rect, colors):
        a = fig.add_axes(rect, zorder=5)
        FC.plan(a, recs, colors, lw=0.06, ec="white")
        a.patch.set_alpha(0)
        return a

    X = {"read": (2.0, 23.0), "map": (25.5, 47.5), "tf": (50.0, 77.0), "rb": (79.5, 98.0)}
    Y0, Y1 = 38.0, 86.0

    # ---------------------------------------------------------------- 1 READ
    x0, x1 = X["read"]
    box(x0, x1, Y0, Y1, "1  READ",
        sub="the city as found\nfootprints, heights, land use, age, AOI")
    inset([0.035, 0.505 * yk, 0.175, 0.195 * yk], [mcolors.to_hex(hcmap(hnorm(h))) for h in h0])
    ax.text((x0 + x1) / 2, 48.6,
            "%s  %s\nn = %d footprints  |  %.3f km$^2$  |  heights 0-%.0f m (Baidu v2)"
            % (site["name"], SLUG, cur["n"], site["area_km2"], hmax),
            ha="center", va="top", fontsize=FS_B, color=BLACK, zorder=4, linespacing=1.5)
    ax.text((x0 + x1) / 2, 41.8,
            "footprint  |  height  |  EULUC land use (%.0f%%)\nyear layer (%.0f%%)  |  Baidu AOI"
            % (100 * site["euluc_coverage"], 100 * site["age_coverage"]),
            ha="center", va="center", fontsize=FS_B, color=BLACK, zorder=4, linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.4", fc=PALE, ec=LIGHT, lw=LW(0.3, s)))

    # ---------------------------------------------------------------- 2 MAP
    x0, x1 = X["map"]
    box(x0, x1, Y0, Y1, "2  MAP",
        sub="metadata -> a reading of the site\none building = one holder + one weakness")
    ax.text((x0 + x1) / 2, 73.4,
            "cascade:  EULUC land use  ->  Function (year layer)  ->  Baidu AOI  ->  unknown\n"
            "the first source that answers wins.  the table is the model, and it is editable.",
            ha="center", va="center", fontsize=FS_B, color=BLACK, zorder=4, linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.4", fc=PALE, ec=LIGHT, lw=LW(0.3, s)))
    inset([0.262, 0.505 * yk, 0.093, 0.165 * yk], [HOLDER_GREY[r["sh"]] for r in recs])
    inset([0.372, 0.505 * yk, 0.093, 0.165 * yk], [mcolors.to_hex(wcmap(wnorm(w))) for w in wk])
    ax.text(30.85, 48.6,
            "holder\nstate %.0f%%  developer %.0f%%\nresident %.0f%%  of floor volume"
            % (100 * cur["shares_gfa"]["state"], 100 * cur["shares_gfa"]["developer"],
               100 * cur["shares_gfa"]["resident"]),
            ha="center", va="top", fontsize=FS_B, color=BLACK, zorder=4, linespacing=1.5)
    ax.text(41.85, 48.6,
            "weakness = 0.5 AGE + 0.5 FAR-gap\nmin %.2f  median %.2f  max %.2f\ndark = read as weak"
            % (wk.min(), float(np.median(wk)), wk.max()),
            ha="center", va="top", fontsize=FS_B, color=BLACK, zorder=4, linespacing=1.5)
    for k, key in enumerate(ORDER):
        xx = 27.4 + k * 5.3
        ax.add_patch(Rectangle((xx, 39.6), 1.5, 1.2, fc=HOLDER_GREY[key],
                               ec=BLACK, lw=LW(0.3, s), zorder=4))
        ax.text(xx + 1.9, 40.2, key, ha="left", va="center", fontsize=FS_B, color=MID, zorder=4)
    ax.text((x0 + x1) / 2, 38.6, "(darker = more concentrated control)",
            ha="center", va="center", fontsize=FS_B, color=MID, zorder=4)

    # ---------------------------------------------------------------- 3 TRANSFORM
    x0, x1 = X["tf"]
    box(x0, x1, Y0, Y1, "3  TRANSFORM   -   SWAPPABLE LENS",
        fc=PALE, emph=True,
        sub="a lens is a rule for turning the reading into form.")
    ax.add_patch(FancyBboxPatch((x0 + 1.6, 43.4), (x1 - x0) - 3.2, 32.2,
                                boxstyle="round,pad=0.4,rounding_size=0.9",
                                fc=WHITE, ec=BLACK, lw=LW(1.0, s), zorder=3))
    ax.text((x0 + x1) / 2, 74.2, "INSTALLED:  POWER   (engine/cake.py)", ha="center", va="top",
            fontsize=FS_H, color=BLACK, fontweight="bold", zorder=5)
    ax.text(x0 + 3.2, 70.2,
            "set      one number: %s should hold %.0f%% of the floor volume\n"
            "gate    who may take from whom (%s <- resident, pool n = %d)\n"
            "order  weakest first.  the ordering rule IS the politics.\n"
            "build   the new holder sets the height, the footprint never moves\n"
            "           envelope %.0f m, FAR x %.1f, binds on %d"
            % (sc["grow"], 100 * sc["target"], sc["grow"], sc["pool_size"],
               sc["envelope_m"], sc["far_mult"], sc["envelope_bind_n"]),
            ha="left", va="top", fontsize=FS_B, color=BLACK, zorder=5, linespacing=1.8)
    inset([0.532, 0.452 * yk, 0.113, 0.142 * yk], [mcolors.to_hex(hcmap(hnorm(h))) for h in h1])
    ax.text(66.6, 52.4,
            "generated form\nlens = power, %s\n%d of %d buildings rebuilt\nshare reached %.0f%%\n"
            "same greyscale as READ"
            % (LENS_NAME, sc["acquired_n"], cur["n"], 100 * sc["share_reached"]),
            ha="left", va="center", fontsize=FS_B, color=BLACK, zorder=5, linespacing=1.6)
    # ---------------------------------------------------------------- 4 READ-BACK
    x0, x1 = X["rb"]
    box(x0, x1, Y0, Y1, "4  READ-BACK",
        sub="the generated form, measured with the\nsame ruler used on the as-found city")
    fp0, fp1 = cur["fingerprint"], sc["fingerprint"]
    rows = [("FAR", "far", "%.2f"), ("coverage", "coverage", "%.3f"),
            ("mean height", "h_mean", "%.1f m"), ("height CV", "h_cv", "%.2f"),
            ("slenderness", "slender", "%.2f"), ("concentration", "concentration", "%.3f"),
            ("grain", "grain", "%.0f m$^2$")]
    xa, xb, xc = x0 + 2.0, x0 + 11.2, x0 + 15.8
    ax.text(xa, 74.0, "fingerprint", ha="left", va="center", fontsize=FS_B, color=BLACK,
            fontweight="bold", zorder=5)
    ax.text(xb, 74.0, "found", ha="center", va="center", fontsize=FS_B, color=MID, zorder=5)
    ax.text(xc, 74.0, "made", ha="center", va="center", fontsize=FS_B, color=BLACK,
            fontweight="bold", zorder=5)
    ax.plot([xa, x1 - 2.0], [71.6, 71.6], color=BLACK, lw=LW(0.5, s), zorder=5)
    yy = 68.6
    for lab, key, fmt in rows:
        frozen = key in sc["frozen_by_construction"]
        col = MID if frozen else BLACK
        ax.text(xa, yy, lab, ha="left", va="center", fontsize=FS_B, color=col, zorder=5)
        ax.text(xb, yy, fmt % fp0[key], ha="center", va="center", fontsize=FS_B, color=col, zorder=5)
        ax.text(xc, yy, fmt % fp1[key], ha="center", va="center", fontsize=FS_B,
                color=MID if frozen else BLACK, zorder=5,
                fontweight="normal" if frozen else "bold")
        yy -= 3.6
    ax.text((x0 + x1) / 2, 40.6,
            "grey rows are frozen by construction:\nfootprints never move, so coverage,\n"
            "grain and n cannot change.\n\ntotal floor volume %+.1f%%   |   target met: %s"
            % (sc["gfa_change_pct"], "yes" if sc["target_met"] else "no"),
            ha="center", va="center", fontsize=FS_B, color=MID, zorder=5, linespacing=1.6,
            bbox=dict(boxstyle="round,pad=0.4", fc=PALE, ec=LIGHT, lw=LW(0.3, s)))

    # ---------------------------------------------------------------- the loop
    arrow(X["read"][1] + 0.4, 62, X["map"][0] - 0.6, 62)
    arrow(X["map"][1] + 0.4, 62, X["tf"][0] - 0.6, 62)
    arrow(X["tf"][1] + 0.4, 62, X["rb"][0] - 0.6, 62)
    ax.add_patch(FancyArrowPatch((88.7, 86.6), (12.5, 86.6), arrowstyle="-|>", mutation_scale=19,
                                 lw=LW(0.75, s), color=BLACK, linestyle=DASH,
                                 connectionstyle="arc3,rad=0.06", zorder=6))

    # ---------------------------------------------------------------- lens magazine
    ax.add_patch(FancyBboxPatch((2.0, 3.0), 96.0, 27.0, boxstyle="round,pad=0.5,rounding_size=1.1",
                                fc=WHITE, ec=LIGHT, lw=LW(0.5, s), zorder=1))
    ax.text(3.8, 27.4, "Swappable lenses (only power is run here)",
            ha="left", va="center", fontsize=FS_H, color=BLACK, fontweight="bold", zorder=4)

    ghosts = [
        ("POWER  (installed)",
         "reading:  holder + weakness\nrule:  share target, gated take,\nweakest first, rebuild", True),
        ("heritage / age",
         "reading:  age, typology, listing\nrule:  hold the oldest fabric,\nrelease the rest", False),
        ("market / rent gap",
         "reading:  price, rent, yield\nrule:  rebuild where the gap between\nactual and potential is widest", False),
        ("environment",
         "reading:  solar, wind, daylight\nrule:  reshape the massing that\nfails the performance target", False),
        ("regulation",
         "reading:  zoning, FAR, envelope\nrule:  fill the legal envelope,\nnothing else moves", False),
    ]
    gx0, gw, gap = 3.8, 17.6, 1.5
    for i, (name, body, live) in enumerate(ghosts):
        x = gx0 + i * (gw + gap)
        ax.add_patch(FancyBboxPatch((x, 5.0), gw, 13.6, boxstyle="round,pad=0.45,rounding_size=0.9",
                                    fc=WHITE if live else PALE, ec=BLACK if live else MID,
                                    lw=LW(1.2, s) if live else LW(0.5, s),
                                    ls="-" if live else DASH, zorder=3))
        ax.text(x + gw / 2, 16.6, name, ha="center", va="center", fontsize=FS_H,
                color=BLACK if live else MID, fontweight="bold", zorder=4)
        ax.text(x + gw / 2, 10.6, body, ha="center", va="center", fontsize=FS_B,
                color=BLACK if live else MID, zorder=4, linespacing=1.6)

    # the installed lens is carried up into cell 3; the ghosts wait
    arrow(gx0 + gw / 2, 18.8, 54.0, 37.4, lw=LW(0.5, s), color=BLACK, rad=-0.16, ms=13, z=6)
    ax.text(30.0, 32.0, "installed", ha="center", va="center", fontsize=FS_B, color=BLACK,
            style="italic", zorder=6)
    for i in (1, 2, 3, 4):
        x = gx0 + i * (gw + gap) + gw / 2
        tx = 59.0 + (i - 1) * 4.5
        arrow(x, 18.8, tx, 37.4, lw=LW(0.3, s), color=MID, ls=DASH,
              rad=0.10 if x > tx else -0.10, ms=11, z=2)

    # ---------------------------------------------------------------- substrate / audit footer
    ax.text(2.0, 1.2,
            "Substrate: %s (%s), %d real footprints, EPSG:32651, Baidu v2 heights. Numbers read from "
            "out/cake/metrics_cake_all.json, scenario %s (mode B, grow), and out/cake/ledger_%s_%s.csv."
            % (site["name"], SLUG, cur["n"], LENS_SCEN, SLUG, LENS_SCEN),
            ha="left", va="bottom", fontsize=FS_B, color=MID)

    p = OUT / "F5_loop.png"
    fig.savefig(p, dpi=DPI)
    fig.savefig(OUT / "F5_loop.pdf")
    plt.close(fig)
    print("F5 ->", p)
    print("F5 ->", OUT / "F5_loop.pdf")
    print("  site %s: n=%d coverage=%.4f" % (SLUG, cur["n"], cov))
    print("  weakness on stock: min %.4f median %.4f max %.4f" % (wk.min(), float(np.median(wk)), wk.max()))
    print("  fingerprint found:", {k: round(v, 4) for k, v in fp0.items()})
    print("  fingerprint made :", {k: round(v, 4) for k, v in fp1.items()})
    print("  lens %s: target %.2f reached %.4f acquired %d of pool %d dGFA %+.2f%%"
          % (LENS_SCEN, sc["target"], sc["share_reached"], sc["acquired_n"], sc["pool_size"],
             sc["gfa_change_pct"]))


# ===================================================================== F6
FAMILIES = [
    ("Environment",
     "sun, wind, daylight, thermal load",
     "performance-driven massing: solar / daylight / wind optimisation, simulation in the loop",
     True),
    ("Economy",
     "cost, yield, development feasibility",
     "cost and development-yield optimisation; search over developable volume",
     True),
    ("Regulation",
     "zoning, FAR, height envelope, setback",
     "rule-based envelope generation; zoning-compliant massing and code checking",
     True),
    ("Infrastructure",
     "access, street network, transit, service radius",
     "network and accessibility driven layout; street-network and parcel generation",
     True),
    ("Function",
     "programme, land use, mix",
     "programme allocation and land-use mix optimisation; space planning",
     True),
    ("Culture / heritage",
     "typology, morphology, character",
     "shape grammars and typology / morphology learning from existing fabric",
     True),
    ("Power",
     "who holds the floor volume, who may take from whom",
     "",
     False),
]


def f6():
    s = PT_F6
    FS_NAME, FS_B, FS_SM = 10.2, 8.2, 7.2   # exactly three sizes
    fig = plt.figure(figsize=(15.0, 7.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off")

    cx1, cx2, cx3, cx4 = 3.0, 27.0, 74.0, 97.0
    dotx = 78.5
    ax.text(cx1 + 0.5, 93.0, "PARAMETER FAMILY", ha="left", va="center", fontsize=FS_B,
            color=BLACK, fontweight="bold")
    ax.text(cx2 + 0.8, 93.0, "OPERATIONALISED IN GENERATIVE / COMPUTATIONAL DESIGN?", ha="left",
            va="center", fontsize=FS_B, color=BLACK, fontweight="bold")
    ax.text(cx4, 93.0, "STATUS", ha="right", va="center", fontsize=FS_B, color=BLACK,
            fontweight="bold")
    # booktabs: toprule above the header, midrule under it, bottomrule after the
    # last row; hairlines between body rows; no vertical rules, no zebra stripes.
    ax.plot([cx1, cx4], [95.4, 95.4], color=BLACK, lw=LW(1.0, s))
    ax.plot([cx1, cx4], [90.5, 90.5], color=BLACK, lw=LW(0.5, s))

    top, rowh, gap = 87.0, 9.4, 1.5
    for i, (name, shapes, method, done) in enumerate(FAMILIES):
        y1 = top - i * (rowh + gap)
        y0 = y1 - rowh
        yc = (y0 + y1) / 2
        power = not done

        if power:
            ax.add_patch(FancyBboxPatch((cx1 - 0.8, y0 - 0.9), (cx4 - cx1) + 1.9, rowh + 1.8,
                                        boxstyle="round,pad=0.3,rounding_size=0.8",
                                        fc=PALE, ec=BLACK, lw=LW(1.2, s), zorder=1))
        if i < len(FAMILIES) - 2:   # hairline separators between ordinary body rows
            ax.plot([cx1, cx4], [y0 - gap / 2, y0 - gap / 2], color=LIGHT,
                    lw=LW(0.3, s), zorder=1)

        ax.text(cx1 + 0.5, yc + 1.2, name, ha="left", va="center", fontsize=FS_NAME,
                color=BLACK, fontweight="bold" if power else "normal", zorder=3)
        ax.text(cx1 + 0.5, yc - 1.9, shapes, ha="left", va="center", fontsize=FS_SM,
                color=MID, zorder=3)

        if done:
            ax.add_patch(FancyBboxPatch((cx2, y0 + 0.5), (cx3 - cx2) - 1.0, rowh - 1.0,
                                        boxstyle="round,pad=0.25,rounding_size=0.6",
                                        fc=PALE, ec=LIGHT, lw=LW(0.3, s), zorder=2))
            ax.text(cx2 + 1.4, yc, method, ha="left", va="center", fontsize=FS_B,
                    color=BLACK, zorder=3)
            ax.plot([dotx], [yc], marker="o", ms=13, mfc=BLACK, mec=BLACK, zorder=3)
            ax.text(cx4, yc, "operationalised", ha="right", va="center", fontsize=FS_B,
                    color=BLACK, zorder=3)
        else:
            # the gap: hairline '////' hatch fills the empty cell, dashed outline
            ax.add_patch(FancyBboxPatch((cx2, y0 + 0.5), (cx3 - cx2) - 1.0, rowh - 1.0,
                                        boxstyle="round,pad=0.25,rounding_size=0.6",
                                        fc=WHITE, ec=MID, lw=0.0, hatch="////", zorder=2))
            ax.add_patch(FancyBboxPatch((cx2, y0 + 0.5), (cx3 - cx2) - 1.0, rowh - 1.0,
                                        boxstyle="round,pad=0.25,rounding_size=0.6",
                                        fc="none", ec=BLACK, lw=LW(0.5, s), ls=DASH, zorder=2))
            ax.plot([dotx], [yc], marker="o", ms=13, mfc=WHITE, mec=BLACK,
                    mew=LW(0.75, s), zorder=3)
            ax.text(cx4, yc, "not operationalised", ha="right", va="center", fontsize=FS_B,
                    color=BLACK, zorder=3)

    ax.plot([cx1, cx4], [10.0, 10.0], color=BLACK, lw=LW(1.0, s))

    ax.text(3.0, 3.5,
            "Schematic. No counts, no citations and no data are plotted here: the middle column lists method types "
            "and is meant to be read against the review table.",
            ha="left", va="bottom", fontsize=FS_SM, color=MID)

    p = OUT / "F6_parameters.png"
    fig.savefig(p, dpi=DPI)
    fig.savefig(OUT / "F6_parameters.pdf")
    plt.close(fig)
    print("F6 ->", p)
    print("F6 ->", OUT / "F6_parameters.pdf")
    for name, shapes, method, done in FAMILIES:
        print("  %-18s | %-49s | %s" % (name, shapes, method if done else "(EMPTY CELL)"))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("f5", "all"):
        f5()
    if what in ("f6", "all"):
        f6()
