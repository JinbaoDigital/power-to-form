"""
exp14_render.py — four massing renders for the negotiation-vignette figure (Caoyang).
Same renderer / camera / stakeholder colours as fig8 (render._boxes3d). Outputs
experiments/out/exp14_massing_<step>.png at ~1600 px wide.
"""
import sys, yaml
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pf_common as C, operators as OP, render as R

OUT = ROOT / "experiments" / "out"; OUT.mkdir(parents=True, exist_ok=True)
SLUG, NAME = "caoyang", "Caoyang"
VIG = yaml.safe_load(open(ROOT / "engine" / "config" / "vignette_recipes.yaml", encoding="utf-8"))

recs = C.load_buildings(SLUG)
states = [("current", "current", recs)]
for key in ("vignette_v1_proposal", "vignette_v2_resident_counter", "vignette_v3_shared_ground"):
    states.append((key, VIG[key]["label"], OP.apply_regime(recs, VIG[key])))

# common z-scale across states for comparability
zmax = max(max(r["h"] for r in rc) for _, _, rc in states) * 1.04
polys = [p for r in recs for p in C._polys(r["geom"])]
minx = min(p.bounds[0] for p in polys); miny = min(p.bounds[1] for p in polys)

for key, label, rc in states:
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection="3d")
    R._boxes3d(ax, rc, minx, miny, zmax)
    ax.set_title("%s — %s" % (NAME, label), fontsize=12, fontweight="bold")
    ax.legend(handles=[Patch(fc=C.SH_COLOR[s], label=C.SH_LABEL[s].split("(")[0])
                       for s in ("state", "developer", "resident")],
              loc="upper left", fontsize=9, frameon=False)
    p = OUT / ("exp14_massing_%s.png" % key)
    fig.savefig(p, dpi=200, bbox_inches="tight"); plt.close(fig)
    print("wrote", p.name, "(n=%d)" % len(rc))
