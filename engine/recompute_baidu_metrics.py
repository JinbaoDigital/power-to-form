"""
recompute_baidu_metrics.py — regenerate the study's frozen 5-district metrics from the
Baidu-v2 caches: heights_by_state.json, dist_shape_stats.json, and a study-consistent
metrics_baidu_5districts.json (current + 4 regimes). Run per slug to stay within limits.
Usage: python3 recompute_baidu_metrics.py <slug>
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from scipy.stats import skew, kurtosis
import diptest
import pf_common as C, operators as OP, measure as M

DATA = C.DATA
DIST = ["caoyang", "dapuqiao", "laoximen", "lujiazui", "yuyuan"]

def shape_stats(h):
    h = np.asarray([x for x in h if x > 0], float)
    d, p = diptest.diptest(h)
    return {"n": int(len(h)), "skew": float(skew(h)), "kurt": float(kurtosis(h)),
            "cv": float(h.std() / h.mean()), "dip": float(d), "dip_p": float(p)}

def upd(path, slug, val):
    obj = json.load(open(path)) if Path(path).exists() else {}
    obj[slug] = val
    json.dump(obj, open(path, "w"), ensure_ascii=False)

def run(slug):
    recs = C.load_buildings(slug)
    regimes = OP.load_regimes()
    after = {name: OP.apply_regime(recs, rec) for name, rec in regimes.items()}
    # 1) heights_by_state
    hbs = {"current": [r["h"] for r in recs]}
    for name, ar in after.items():
        hbs[name] = [r["h"] for r in ar]
    upd(DATA / "heights_by_state.json", slug, hbs)
    # 2) dist_shape_stats
    dss = {k: shape_stats(v) for k, v in hbs.items()}
    upd(DATA / "dist_shape_stats.json", slug, dss)
    # 3) study-consistent regime metrics (FAR/coverage/grain/slender/concentration)
    rows, _ = M.compare(recs, after, slug)
    upd(DATA / "metrics_baidu_5districts.json", slug,
        {"name": C.site_meta(slug)["name"], "source": "baidu_v2", "rows": rows})
    print(f"{slug}: current n={dss['current']['n']} dip={dss['current']['dip']:.4f} "
          f"p={dss['current']['dip_p']:.3f} | far={rows['current']['far']:.2f} "
          f"cov={rows['current']['coverage']:.2f} hcv={rows['current']['h_cv']:.2f}")

if __name__ == "__main__":
    run(sys.argv[1])
