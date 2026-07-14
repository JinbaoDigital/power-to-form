"""
run_cake.py — run the cake model over the five jiedao and write everything the paper needs.

  python3 run_cake.py corners     current + four corners x modes A/B x five districts
  python3 run_cake.py grid        developer x state reachable-space grid (5 x 5), mode B
  python3 run_cake.py negotiate   three-round negotiation on Caoyang
  python3 run_cake.py invariance  weakness sensitivity + rule ablation
  python3 run_cake.py all

Outputs (engine/out/cake/): metrics_cake.json, ledger_<district>_<scenario>.csv,
skyline_<district>.json, reachable_<district>.json, invariance.csv
"""
import sys, json, csv, copy
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pf_common as C
import measure as M
import cake

OUT = HERE / "out" / "cake"; OUT.mkdir(parents=True, exist_ok=True)
SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
CFG = cake.load_cfg()
MODES = [("redistribute", "A"), ("grow", "B")]


def base(slug):
    recs = C.load_buildings(slug)
    cov = M.diagnose([dict(r) for r in recs], slug)["coverage"]
    return recs, cov


def slim(r):
    d = {k: v for k, v in r.items() if k not in ("ledger", "recs")}
    return d


def corners():
    metrics, skylines = {}, {}
    for slug in SITES:
        recs, cov = base(slug)
        sh = cake.read_shares(recs)
        fp = M.diagnose([dict(r) for r in recs], slug)
        metrics[slug] = {"current": {
            "shares_gfa": {k: round(v, 4) for k, v in sh["gfa"].items()},
            "shares_count": {k: round(v, 4) for k, v in sh["count"].items()},
            "coverage": round(cov, 4), "n": len(recs),
            "fingerprint": {k: (round(float(v), 4) if isinstance(v, (int, float)) else v) for k, v in fp.items()},
            "V_total_m3": round(sum(cake.gfa(r) for r in recs), 1)}}
        sky = {"current": [[r["bid"], round(r["orig_h"], 2), r["orig_sh"]] for r in recs]}
        for name, sc in CFG["scenarios"].items():
            for mode, tag in MODES:
                res = cake.run_scenario(recs, sc, CFG, mode=mode, slug=slug, coverage=cov)
                key = "%s_%s" % (name, tag)
                metrics[slug][key] = slim(res)
                with open(OUT / ("ledger_%s_%s.csv" % (slug, key)), "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=["bid", "from_sh", "to_sh", "gfa_before", "gfa_after",
                                                      "h_before", "h_after", "area", "weakness"])
                    w.writeheader()
                    for l in res["ledger"]:
                        w.writerow(l)
                sky[key] = [[r["bid"], round(r["h"], 2), r["sh"]] for r in res["recs"]]
                print("  %-9s %-22s reached %.3f/%.2f  met=%-5s  took %4d  dGFA %+7.1f%%  disp_res %.2e"
                      % (slug, key, res["share_reached"], res["target"], res["target_met"],
                         res["acquired_n"], res["gfa_change_pct"], res["displacement_gfa"]["resident"]), flush=True)
        json.dump(sky, open(OUT / ("skyline_%s.json" % slug), "w"))
    p = OUT / "metrics_cake.json"
    old = json.load(open(p)) if p.exists() else {}
    for k, v in metrics.items():
        old.setdefault(k, {}).update(v)
    json.dump(old, open(p, "w"), ensure_ascii=False, indent=1)
    print("wrote metrics_cake.json + ledgers + skylines")


def grid(steps=5, only=None):
    for slug in ([only] if only else SITES):
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
                              # Adding r1's would double-count round one (an adversarial check caught
                              # this: it shifted cells by up to 11.4 points and flipped one sign).
                              "gfa_change_pct": round(r2["gfa_change_pct"], 2),
                              "dev_met": r1["target_met"], "state_met": r2["target_met"],
                              "acquired": r1["acquired_n"] + r2["acquired_n"],
                              "displaced_resident_gfa": round(r1["displacement_gfa"]["resident"], 1),
                              "skyline": [[round(r["h"], 1), r["sh"]] for r in r2["recs"]]})
        json.dump(cells, open(OUT / ("reachable_%s.json" % slug), "w"))
        met = sum(1 for c in cells if c["dev_met"] and c["state_met"])
        print("  %-9s grid %d cells, both targets met in %d, unreachable in %d" % (slug, len(cells), met, len(cells) - met), flush=True)


def negotiate():
    slug = "caoyang"
    recs, cov = base(slug)
    rounds = [
        ("v1_state_proposal", {"grow": "state", "target": 0.25, "rule": "weak_first"}, "grow"),
        ("v2_resident_counter", {"grow": "resident", "target": 0.72, "rule": "weak_first"}, "redistribute"),
        ("v3_shared_ground", {"grow": "state", "target": 0.30, "rule": "value_first",
                              "from_override": ["developer"], "euluc_override": None,
                              "rebuild_override": "platform"}, "grow"),
    ]
    # Each round is a COUNTER-PROPOSAL on the same existing fabric, not a further raid on what the
    # previous round left behind. A counter-offer changes the target; it does not stack on top of the
    # offer it rejects. (Run cumulatively, round 1 eats the convertible pool and rounds 2 and 3 have
    # nothing to act on, which says more about the pool than about the negotiation.)
    out, cur = {}, recs
    for name, sc, mode in rounds:
        res = cake.run_scenario(recs, sc, CFG, mode=mode, slug=slug, coverage=cov)
        out[name] = slim(res)
        with open(OUT / ("ledger_%s_%s.csv" % (slug, name)), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["bid", "from_sh", "to_sh", "gfa_before", "gfa_after",
                                              "h_before", "h_after", "area", "weakness"])
            w.writeheader()
            for l in res["ledger"]:
                w.writerow(l)
        cur = res["recs"]
        print("  %-20s reached %.3f/%.2f met=%-5s took %4d dGFA %+6.1f%% shares=%s"
              % (name, res["share_reached"], res["target"], res["target_met"], res["acquired_n"],
                 res["gfa_change_pct"], {k: round(v, 3) for k, v in res["shares_gfa"].items() if k != "unknown"}), flush=True)
    p = OUT / "metrics_cake.json"
    m = json.load(open(p)) if p.exists() else {}
    m.setdefault("caoyang", {})["negotiation"] = out
    json.dump(m, open(p, "w"), ensure_ascii=False, indent=1)


def invariance():
    """the one falsifiable claim: do residents lose first under almost any weighting?"""
    rows = []
    # capital_deepen (0.80), not capital_extreme (0.60): in Lujiazui capital already holds 65.4% of the
    # floor area, so capital_extreme acquires nothing there and would score a vacuous "invariant holds".
    sc = dict(CFG["scenarios"]["capital_deepen"])
    for slug in SITES:
        recs, cov = base(slug)
        for wa, wg in [(1.0, 0.0), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.0, 1.0)]:
            cfg = copy.deepcopy(CFG)
            cfg["weakness"]["w_age"], cfg["weakness"]["w_gap"] = wa, wg
            for miss in ("zero", "median"):
                cfg["weakness"]["missing_age"] = miss
                r = cake.run_scenario(recs, sc, cfg, mode="grow", slug=slug, coverage=cov)
                d = r["displacement_gfa"]
                tot = sum(d.values()) or 1.0
                rows.append(dict(test="sensitivity", district=slug, w_age=wa, w_gap=wg, missing_age=miss,
                                 rule="weak_first", reached=r["share_reached"], met=r["target_met"],
                                 acquired=r["acquired_n"],
                                 resident_loss_share=round(d["resident"] / tot, 4),
                                 resident_loses_most=(d["resident"] >= max(d.values()))))
        # the pool's own weakness distribution, so "did it take the weak ones" can actually be answered
        pool_w = sorted(cake.weakness_score(x, CFG, cov, None) for x in recs if x["sh"] == "resident")
        pool_mean = float(np.mean(pool_w)) if pool_w else float("nan")
        # Two intensities. At a heavy target the growing class consumes almost the whole pool, so the
        # ordering rule has almost nothing left to choose and every rule converges. The rule is a real
        # political choice only when the acquisition is partial, so the light target is the honest test.
        cur_dev = cake.read_shares(recs)["gfa"]["developer"]
        intensities = [("heavy", float(sc["target"])), ("light", round(cur_dev + 0.05, 3))]
        for intensity, tgt in intensities:
          for rule in ("weak_first", "value_first", "random", "adjacency_first"):
            s2 = dict(sc); s2["rule"] = rule; s2["target"] = tgt
            r = cake.run_scenario(recs, s2, CFG, mode="grow", slug=slug, coverage=cov, seed=7)
            d = r["displacement_gfa"]
            tot = sum(d.values()) or 1.0
            med_w = float(np.median([l["weakness"] for l in r["ledger"]])) if r["ledger"] else float("nan")
            rows.append(dict(test="ablation_" + intensity, district=slug, w_age=CFG["weakness"]["w_age"],
                             w_gap=CFG["weakness"]["w_gap"], missing_age="zero", rule=rule,
                             reached=r["share_reached"], met=r["target_met"], acquired=r["acquired_n"],
                             resident_loss_share=round(d["resident"] / tot, 4),
                             resident_loses_most=(d["resident"] >= max(d.values())),
                             median_weakness_taken=round(med_w, 4),
                             mean_weakness_taken=round(float(np.mean([l["weakness"] for l in r["ledger"]])), 4) if r["ledger"] else float("nan"),
                             pool_mean_weakness=round(pool_mean, 4),
                             lift_over_pool=round(float(np.mean([l["weakness"] for l in r["ledger"]])) - pool_mean, 4) if r["ledger"] else float("nan"),
                             pool_taken_frac=round(r["acquired_n"] / max(r["pool_size"], 1), 3)))
            print("  %-9s ablation %-15s took %4d, median weakness of what it took = %.3f"
                  % (slug, rule, r["acquired_n"], med_w), flush=True)
    keys = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with open(OUT / "invariance.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    inv = [r for r in rows if r["test"] == "sensitivity"]
    hold = sum(1 for r in inv if r["resident_loses_most"])
    print("\nINVARIANT: residents lose the most GFA in %d of %d weighting x district runs" % (hold, len(inv)))
    print("resident share of all displaced GFA: min %.3f  max %.3f"
          % (min(r["resident_loss_share"] for r in inv), max(r["resident_loss_share"] for r in inv)))
    for intensity in ("light", "heavy"):
        abl = [r for r in rows if r["test"] == "ablation_" + intensity]
        print("\nDISCRIMINATION of the ordering rule, %s target:" % intensity.upper())
        for rule in ("weak_first", "value_first", "random", "adjacency_first"):
            v = [r["mean_weakness_taken"] for r in abl if r["rule"] == rule and r["acquired"] > 0]
            lf = [r["lift_over_pool"] for r in abl if r["rule"] == rule and r["acquired"] > 0]
            fr = [r["pool_taken_frac"] for r in abl if r["rule"] == rule and r["acquired"] > 0]
            if not v:
                continue
            print("  %-16s weakness taken %.3f | lift over pool %+.3f | took %.0f%% of the pool"
                  % (rule, float(np.nanmean(v)), float(np.nanmean(lf)), 100 * float(np.nanmean(fr))))


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "all"
    if a in ("corners", "all"): corners()
    if a in ("grid", "all"): grid(only=(sys.argv[2] if len(sys.argv) > 2 else None))
    if a in ("negotiate", "all"): negotiate()
    if a in ("invariance", "all"): invariance()
