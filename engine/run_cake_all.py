"""
run_cake_all.py — the same cake engine, run across EIGHT jiedao instead of five.

Why a second runner: run_cake.py and everything it wrote (metrics_cake.json, invariance.csv, the 53
ledgers, the 5 skylines, the 5 reachable grids) is FROZEN. This script never touches those files. It
re-runs the identical engine over a wider case set and writes a parallel, new artefact:

    out/cake/metrics_cake_all.json      all 8 sites, current + 5 scenarios x 2 modes
    out/cake/ledger_<slug>_<key>.csv    ONLY for the 3 new sites
    out/cake/skyline_<slug>.json        ONLY for the 3 new sites (the 5 frozen ones are reused as-is)
    out/cake/reachable_<slug>.json      ONLY for the 3 new sites

The point of the wider set is FORM + FINGERPRINT: what each power configuration does to the built form
of a case, across four morphological families, not who changes hands (a secondary reading, and one the
gate table largely decides anyway; see NEXT_RUN_9_REPORT.md).

  python3 run_cake_all.py corners      current + 4 corners (+ capital_extreme) x modes A/B x 8 sites
  python3 run_cake_all.py grid         5 x 5 developer x state reachable grid, mode grow, 3 new sites
  python3 run_cake_all.py regress      re-run the 5 frozen sites and diff against metrics_cake.json
  python3 run_cake_all.py all
"""
import sys, json, csv
from pathlib import Path
import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pf_common as C
import measure as M
import cake

OUT = HERE / "out" / "cake"; OUT.mkdir(parents=True, exist_ok=True)

# The eight cases, in the order the paper reads them: two capital, two danwei, three old-town, one industry.
SITES_ALL = ["lujiazui", "nanjingxi", "caoyang", "pengpu", "laoximen", "yuyuan", "dapuqiao", "zhangjiang"]
FROZEN = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]      # already in metrics_cake.json
NEW = ["nanjingxi", "pengpu", "zhangjiang"]                              # only these get new artefacts

# The four canonical power configurations. capital_extreme is still run and written, as an extra
# intensity of the developer corner, but it is NOT one of the four corners the figures use.
CORNERS = {
    "developer_led": "capital_deepen",     # developer grows to 0.80 of the floor volume
    "state_led":     "state_civic",        # state grows to 0.30, convertible stock only
    "resident_led":  "resident_retain",    # residents buy back to 0.75
    "shared":        "shared_commons",     # a public trust takes from the TOP, flattened to a platform
}
EXTRA_SCENARIOS = ["capital_extreme"]
SCENARIO_ORDER = list(CORNERS.values()) + EXTRA_SCENARIOS

CFG = cake.load_cfg()
MODES = [("redistribute", "A"), ("grow", "B")]                          # figures use B (grow)
FAMILY = {s["slug"]: s for s in yaml.safe_load(open(HERE / "config" / "sites.yaml", encoding="utf-8"))["sites"]}
METRICS_ALL = OUT / "metrics_cake_all.json"
METRICS_FROZEN = OUT / "metrics_cake.json"


def base(slug):
    recs = C.load_buildings(slug)
    cov = M.diagnose([dict(r) for r in recs], slug)["coverage"]
    return recs, cov


def slim(r):
    return {k: v for k, v in r.items() if k not in ("ledger", "recs")}


def site_block(slug, recs, cov, write_artefacts):
    """current + every scenario x mode for one site. Ledgers/skylines written only if write_artefacts."""
    sh = cake.read_shares(recs)
    fp = M.diagnose([dict(r) for r in recs], slug)
    meta = C.site_meta(slug)
    n = len(recs)
    block = {"current": {
        "shares_gfa": {k: round(v, 4) for k, v in sh["gfa"].items()},
        "shares_count": {k: round(v, 4) for k, v in sh["count"].items()},
        "coverage": round(cov, 4), "n": n,
        "fingerprint": {k: (round(float(v), 4) if isinstance(v, (int, float)) else v) for k, v in fp.items()},
        "V_total_m3": round(sum(cake.gfa(r) for r in recs), 1)}}
    sky = {"current": [[r["bid"], round(r["orig_h"], 2), r["orig_sh"]] for r in recs]}
    for name in SCENARIO_ORDER:
        sc = CFG["scenarios"][name]
        for mode, tag in MODES:
            res = cake.run_scenario(recs, sc, CFG, mode=mode, slug=slug, coverage=cov)
            key = "%s_%s" % (name, tag)
            block[key] = slim(res)
            if write_artefacts:
                with open(OUT / ("ledger_%s_%s.csv" % (slug, key)), "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=["bid", "from_sh", "to_sh", "gfa_before", "gfa_after",
                                                      "h_before", "h_after", "area", "weakness"])
                    w.writeheader()
                    for l in res["ledger"]:
                        w.writerow(l)
            sky[key] = [[r["bid"], round(r["h"], 2), r["sh"]] for r in res["recs"]]
            print("  %-11s %-22s reached %.3f/%.2f  met=%-5s  took %4d  dGFA %+7.1f%%  h_mean %5.1f -> %5.1f"
                  % (slug, key, res["share_reached"], res["target"], res["target_met"], res["acquired_n"],
                     res["gfa_change_pct"], block["current"]["fingerprint"]["h_mean"],
                     res["fingerprint"]["h_mean"]), flush=True)
    if write_artefacts:
        json.dump(sky, open(OUT / ("skyline_%s.json" % slug), "w"))
    # site descriptors the case table needs, so the report never has to re-derive them
    ages = [r["age"] for r in recs if r.get("age")]
    block["site"] = {
        "name": meta["name"], "family": FAMILY[slug]["family"], "area_km2": round(meta["area_km2"], 3),
        "n": n,
        "age_coverage": round(len(ages) / n, 4),
        "age_min": (int(min(ages)) if ages else None), "age_max": (int(max(ages)) if ages else None),
        "age_mean": (round(float(np.mean(ages)), 1) if ages else None),
        "euluc_coverage": round(sum(1 for r in recs if r.get("euluc")) / n, 4),
        "artefacts": ("new" if write_artefacts else "reused from the frozen 5-site run"),
    }
    return block


def corners():
    metrics = {"_meta": {
        "note": "NEW artefact. metrics_cake.json (5 frozen sites) is untouched and remains the reference.",
        "sites": SITES_ALL, "frozen_sites": FROZEN, "new_sites": NEW,
        "corner_map": CORNERS, "extra_scenarios": EXTRA_SCENARIOS,
        "modes": {"A": "redistribute (ownership only, GFA conserved)", "B": "grow (acquired stock rebuilt)"},
        "figures_use_mode": "B",
    }}
    for slug in SITES_ALL:
        recs, cov = base(slug)
        metrics[slug] = site_block(slug, recs, cov, write_artefacts=(slug in NEW))
    json.dump(metrics, open(METRICS_ALL, "w"), ensure_ascii=False, indent=1)
    print("wrote %s (%d sites) + ledgers/skylines for %s" % (METRICS_ALL.name, len(SITES_ALL), ", ".join(NEW)))


def grid(steps=5, sites=None):
    """the reachable space, developer axis x state axis, mode grow. Only the 3 new sites."""
    for slug in (sites or NEW):
        recs, cov = base(slug)
        cur = cake.read_shares(recs)["gfa"]
        devs = np.linspace(cur["developer"], 0.70, steps)
        sts = np.linspace(cur["state"], 0.40, steps)
        cells = []
        for i, d in enumerate(devs):
            for j, s in enumerate(sts):
                r1 = cake.run_scenario(recs, {"grow": "developer", "target": float(d), "rule": "weak_first"},
                                       CFG, mode="grow", slug=slug, coverage=cov)
                r2 = cake.run_scenario(r1["recs"], {"grow": "state", "target": float(s), "rule": "weak_first"},
                                       CFG, mode="grow", slug=slug, coverage=cov)
                cells.append({"i": i, "j": j, "dev_target": round(float(d), 3), "state_target": round(float(s), 3),
                              "shares": r2["shares_gfa"], "fingerprint": r2["fingerprint"],
                              # r2 runs on r1's records, whose orig_h is still the ORIGINAL height, so
                              # r2's gfa_change_pct is already cumulative against the untouched city.
                              # Adding r1's would double-count round one (the NEXT_RUN_9 adversarial pass).
                              "gfa_change_pct": round(r2["gfa_change_pct"], 2),
                              "dev_met": r1["target_met"], "state_met": r2["target_met"],
                              "acquired": r1["acquired_n"] + r2["acquired_n"],
                              "displaced_resident_gfa": round(r1["displacement_gfa"]["resident"], 1),
                              "skyline": [[round(r["h"], 1), r["sh"]] for r in r2["recs"]]})
        json.dump(cells, open(OUT / ("reachable_%s.json" % slug), "w"))
        met = sum(1 for c in cells if c["dev_met"] and c["state_met"])
        print("  %-11s grid %d cells, both targets met in %d, unreachable in %d"
              % (slug, len(cells), met, len(cells) - met), flush=True)


# ------------------------------------------------------------------ regression against the frozen 5
def _leaves(o, path=""):
    """every numeric leaf of a nested dict/list, as (path, value)."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _leaves(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _leaves(v, path + "/%d" % i)
    elif isinstance(o, bool):
        yield path, float(o)
    elif isinstance(o, (int, float)):
        yield path, float(o)


def regress(tol=1e-6):
    """the 5 frozen sites must reproduce metrics_cake.json exactly. Compare every numeric leaf."""
    if not METRICS_FROZEN.exists():
        print("no frozen metrics_cake.json to compare against"); return
    frozen = json.load(open(METRICS_FROZEN, encoding="utf-8"))
    worst, worst_at, checked, missing = 0.0, "", 0, []
    for slug in FROZEN:
        recs, cov = base(slug)
        fresh = site_block(slug, recs, cov, write_artefacts=False)   # writes nothing, by construction
        old = {k: v for k, v in frozen[slug].items() if k != "negotiation"}  # negotiation is run_cake.py's
        fl, nl = dict(_leaves(old)), dict(_leaves(fresh))
        for p, v in fl.items():
            if p not in nl:
                missing.append(slug + p); continue
            checked += 1
            d = abs(nl[p] - v)
            if d > worst:
                worst, worst_at = d, slug + p
        print("  %-11s %d numeric leaves compared" % (slug, len(fl)), flush=True)
    print("\nREGRESSION vs frozen metrics_cake.json")
    print("  leaves compared : %d" % checked)
    print("  keys missing    : %d %s" % (len(missing), missing[:5]))
    print("  max deviation   : %.3e at %s" % (worst, worst_at or "-"))
    print("  verdict         : %s (tol %.0e)" % ("PASS" if (worst <= tol and not missing) else "FAIL", tol))
    return worst


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "all"
    if a in ("regress", "all"): regress()
    if a in ("corners", "all"): corners()
    if a in ("grid", "all"): grid(sites=(sys.argv[2:] or None))
