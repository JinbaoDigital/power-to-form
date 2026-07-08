#!/usr/bin/env python3
"""
reproduce.py - one entry point for Power-to-Form.

  python reproduce.py --verify    print the headline numbers from results/*.json
  python reproduce.py --run        recompute from rebuilt caches (see data/README.md), then redraw figures
                                    (edit engine/operators.py or engine/config/regimes.yaml first,
                                     then run this to SEE your changes in the numbers and figures)
  python reproduce.py --demo       run the engine on a synthetic district (no caches needed)

This repo ships the DERIVED results (results/) + code, not the raw geometry caches (Baidu ToS).
Individual experiments also run directly, e.g.  python experiments/exp1_cascade_reliability.py
"""
import sys, json, argparse, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENG = ROOT / "engine"
RES = ROOT / "results"
sys.path.insert(0, str(ENG))
DIST = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]


def _shares(recs):
    area = [r["geom"].area for r in recs]
    gfa = [a * r["h"] for a, r in zip(area, recs)]
    tc, tg = len(recs), (sum(gfa) or 1.0)
    out = {"n": tc}
    for k in ("state", "developer", "resident", "unknown"):
        out["cnt_" + k] = round(sum(1 for r in recs if r["sh"] == k) / max(tc, 1), 3)
        out["gfa_" + k] = round(sum(g for g, r in zip(gfa, recs) if r["sh"] == k) / tg, 3)
    return out


def run():
    import numpy as np
    from scipy.stats import skew, kurtosis
    import diptest
    import pf_common as C, operators as OP, measure as M
    missing = [d for d in DIST if not (ENG / "data" / d / "buildings.parquet").exists()]
    if missing:
        print("Building caches are not distributed (raw Baidu-derived geometry is not re-hosted).")
        print("This repo ships the DERIVED results (results/) + code. To recompute from scratch:")
        print("  1. obtain the upstream Shanghai dataset (see data/README.md),")
        print("  2. rebuild the caches:  cd engine && python rebuild_baidu.py")
        print("  3. re-run this.  For a no-data check of the published numbers:  python reproduce.py --verify")
        return
    reg = OP.load_regimes()
    metrics, hbs, dss, shares = {}, {}, {}, {}
    for slug in DIST:
        recs = C.load_buildings(slug)
        after = {n: OP.apply_regime(recs, rc) for n, rc in reg.items()}
        rows, _ = M.compare(recs, after, slug)
        metrics[slug] = {"name": C.site_meta(slug)["name"], "source": "engine/data cache", "rows": rows}
        hbs[slug] = {"current": [r["h"] for r in recs]}
        for n, a in after.items():
            hbs[slug][n] = [r["h"] for r in a]

        def ss(h):
            h = np.asarray([x for x in h if x > 0], float)
            d, p = diptest.diptest(h)
            return {"n": int(len(h)), "skew": float(skew(h)), "kurt": float(kurtosis(h)),
                    "cv": float(h.std() / h.mean()), "dip": float(d), "dip_p": float(p)}
        dss[slug] = {k: ss(v) for k, v in hbs[slug].items()}
        shares[slug] = _shares(recs)
        print("  %s: n=%d far=%.2f resident cnt/gfa=%.2f/%.2f" %
              (slug, len(recs), rows["current"]["far"], shares[slug]["cnt_resident"], shares[slug]["gfa_resident"]))
    json.dump(metrics, open(RES / "metrics.json", "w"), ensure_ascii=False, indent=1)
    json.dump(hbs, open(RES / "heights_by_state.json", "w"))
    json.dump(dss, open(RES / "dist_shape_stats.json", "w"))
    json.dump(shares, open(RES / "stakeholder_shares.json", "w"), indent=1)
    print("results/ updated. Redrawing figures...")
    subprocess.run([sys.executable, str(ROOT / "figures" / "build_figures.py"), "all"], check=False)
    print("Done. Edit engine/operators.py or engine/config/regimes.yaml and rerun to explore.")


def demo():
    import pf_common as C, operators as OP, measure as M
    sys.path.insert(0, str(ROOT / "data" / "synthetic"))
    import make_synthetic
    C.DATA = ROOT / "data" / "synthetic"
    if not (C.DATA / "demo" / "buildings.parquet").exists():
        make_synthetic.make(outdir=C.DATA / "demo")
    recs = C.load_buildings("demo")
    reg = OP.load_regimes()
    after = {n: OP.apply_regime(recs, rc) for n, rc in reg.items()}
    rows, _ = M.compare(recs, after, "demo")
    print("\nSynthetic demo, %d buildings, engine ran end to end.\n" % len(recs))
    keys = ["n", "far", "coverage", "h_mean", "h_cv", "grain", "slender"]
    print("state           " + "".join("%9s" % k for k in keys))
    for name, r in rows.items():
        print(("%-15s" % name) + "".join("%9.2f" % r[k] for k in keys))


def verify():
    m = json.load(open(RES / "metrics.json"))
    sh = json.load(open(RES / "stakeholder_shares.json"))
    print("\nFive districts as found (from results/):\n")
    print("%-10s%6s%7s%7s   cnt s/d/r/u          gfa s/d/r/u" % ("district", "n", "FAR", "cov"))
    tot = 0
    for d in DIST:
        c = m[d]["rows"]["current"]; s = sh[d]; tot += c["n"]
        cnt = "/".join("%.2f" % s["cnt_" + k] for k in ("state", "developer", "resident", "unknown"))
        gfa = "/".join("%.2f" % s["gfa_" + k] for k in ("state", "developer", "resident", "unknown"))
        print("%-10s%6d%7.2f%7.3f   %s   %s" % (d, c["n"], c["far"], c["coverage"], cnt, gfa))
    print("%-10s%6d\n(see docs/REPRODUCIBILITY.md for the claim -> script -> output map)" % ("TOTAL", tot))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true", help="recompute from caches + redraw figures")
    ap.add_argument("--verify", action="store_true", help="print headline numbers from results/")
    ap.add_argument("--demo", action="store_true", help="run engine on synthetic data")
    a = ap.parse_args()
    if a.run:
        run()
    elif a.verify:
        verify()
    elif a.demo:
        demo()
    else:
        ap.print_help()
