"""
verify_cake_nr10.py — recompute NEXT_RUN_10's headline numbers from the artefacts themselves.
Companion to verify_cake.py (which covers the frozen five). Exits non-zero if anything fails to reconcile.

Covers: the eight case studies, the four power configurations, the frozen-five regression,
the reachability grids, the envelope (gamma) finding, and the four aux CSVs of Task C.
"""
import json, csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "cake"
FIGS = HERE / "out" / "cake_figs"

SITES = ["lujiazui", "nanjingxi", "caoyang", "pengpu", "laoximen", "yuyuan", "dapuqiao", "zhangjiang"]
FROZEN = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
CORNERS = {"developer-led": "capital_deepen_B", "state-led": "state_civic_B",
           "resident-led": "resident_retain_B", "shared": "shared_commons_B"}
fail = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fail.append(msg)


A = json.load(open(OUT / "metrics_cake_all.json", encoding="utf-8"))
F = json.load(open(OUT / "metrics_cake.json", encoding="utf-8"))

print("\neight case studies, as found (engine/out/cake/metrics_cake_all.json):\n")
print("%-11s%7s%9s%9s%9s%8s%8s" % ("site", "n", "state", "developer", "resident", "far", "cover"))
for s in SITES:
    c = A[s]["current"]
    sh, fp = c["shares_gfa"], c["fingerprint"]
    print("%-11s%7d%9.3f%9.3f%9.3f%8.2f%8.3f"
          % (s, c["n"], sh["state"], sh["developer"], sh["resident"], fp["far"], fp["coverage"]))

print("\nfour power configurations, mode B (grow):\n")
print("%-11s%-14s%9s%7s%9s%9s" % ("site", "configuration", "reached", "met", "dGFA%", "rebuilt"))
for s in SITES:
    for label, key in CORNERS.items():
        v = A[s][key]
        print("%-11s%-14s%9.3f%7s%9.1f%9d"
              % (s, label, v["share_reached"], v["target_met"], v["gfa_change_pct"], v["acquired_n"]))

# 1. frozen-five regression: every numeric leaf of metrics_cake.json must be reproduced
print("\n1. frozen-five regression (metrics_cake_all.json vs frozen metrics_cake.json)")
dev, leaves = 0.0, 0


def walk(a, b, path=""):
    global dev, leaves
    if isinstance(a, dict):
        for k in a:
            if k in b:
                walk(a[k], b[k], path + "/" + k)
    elif isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)):
        leaves += 1
        dev = max(dev, abs(float(a) - float(b)))


for s in FROZEN:
    walk(F[s], A[s], s)
check(dev == 0.0, "%d numeric leaves reproduced, max deviation %.3e (must be 0)" % (leaves, dev))

# 2. the cross-case inversion: capital blocked at zhangjiang, the state blocked at pengpu
print("\n2. the cross-case inversion (the run's main morphological finding)")
zj, pp = A["zhangjiang"], A["pengpu"]
check(not zj["capital_deepen_B"]["target_met"] and abs(zj["capital_deepen_B"]["share_reached"] - 0.774) < 0.002,
      "zhangjiang: developer-led falls short at %.3f of 0.80" % zj["capital_deepen_B"]["share_reached"])
check(zj["state_civic_B"]["target_met"], "zhangjiang: state-led meets its target")
check(not pp["state_civic_B"]["target_met"] and abs(pp["state_civic_B"]["share_reached"] - 0.063) < 0.002,
      "pengpu: state-led reaches only %.3f of 0.30" % pp["state_civic_B"]["share_reached"])
check(pp["resident_retain_B"]["acquired_n"] == 0 and abs(pp["current"]["shares_gfa"]["resident"] - 0.918) < 0.002,
      "pengpu: residents already hold %.3f of the floor volume, resident-led rebuilds nothing"
      % pp["current"]["shares_gfa"]["resident"])
check(sum(1 for s in SITES if not A[s]["capital_deepen_B"]["target_met"]) == 1,
      "zhangjiang is the only site where developer-led fails")

# 3. reachability grids: every unreachable cell is a state-side failure
print("\n3. reachability grids (reachable_<slug>.json)")
unreach = {}
for s in SITES:
    p = OUT / ("reachable_%s.json" % s)
    if not p.exists():
        fail.append("missing reachable_%s.json" % s)
        continue
    cells = json.load(open(p))
    bad = [c for c in cells if not (c["dev_met"] and c["state_met"])]
    unreach[s] = (len(bad), len(cells))
    check(all(not c["state_met"] for c in bad),
          "%-11s %2d/%d cells unreachable, all of them state-side" % (s, len(bad), len(cells)))
check(unreach.get("pengpu", (0, 0))[0] == 20 and unreach.get("zhangjiang", (1, 0))[0] == 0,
      "pengpu 20/25 unreachable (worst), zhangjiang 0/25 (best)")

# 4. the envelope does not bite at base gamma
print("\n4. the regulatory envelope at base gamma (the negative finding)")
binds = [(s, k) for s in SITES for k, v in A[s].items()
         if isinstance(v, dict) and v.get("envelope_bind_n", 0) != 0]
check(not binds, "envelope_bind_n = 0 in every site x configuration x mode (%d runs)"
      % sum(1 for s in SITES for k, v in A[s].items() if isinstance(v, dict) and "envelope_bind_n" in v))
g = list(csv.DictReader(open(OUT / "gamma_bind.csv", encoding="utf-8")))
base = [r for r in g if r["row_type"] == "gamma_setting" and r["gamma"] == "base"
        and r["configuration"] == "developer_led"]
check(len(base) == 8, "gamma_bind.csv carries the base setting for all %d sites" % len(base))
hs = [float(r["rebuild_target_h_max"]) for r in base]
check(max(hs) < 60.0, "highest developer rebuild target %.2f m stays under the 60 m envelope, "
                      "headroom %.2f m, so the envelope is inert by arithmetic and not by policy"
                      % (max(hs), 60.0 - max(hs)))
strict = [r for r in g if r["row_type"] == "gamma_setting" and r["gamma"] == "strict"]
check(sum(1 for r in strict if int(r["envelope_bind_n"]) > 0) > 0,
      "the dial is not inert in general: at strict gamma (30 m) it binds on %d of %d runs"
      % (sum(1 for r in strict if int(r["envelope_bind_n"]) > 0), len(strict)))

# 5. Task C aux CSVs exist and reconcile on the rule ordering
print("\n5. task C aux csv (traceability)")
for name, rows_min in [("rule_comparison.csv", 32), ("weakness_dist.csv", 40),
                       ("gamma_bind.csv", 32), ("age_layer_stats.csv", 8)]:
    p = OUT / name
    n = len(list(csv.DictReader(open(p, encoding="utf-8")))) if p.exists() else 0
    check(n >= rows_min, "%-22s %3d rows" % (name, n))
rc = list(csv.DictReader(open(OUT / "rule_comparison.csv", encoding="utf-8")))
lift = {}
for r in rc:
    k = r["rule"]
    lift.setdefault(k, []).append(float(r["lift_over_pool"]))
mean = {k: sum(v) / len(v) for k, v in lift.items()}
check(mean["weak_first"] > 0.15 > mean["random"] > mean["value_first"],
      "weak_first lifts the weakness of what it takes (+%.3f) while random (%+.3f) and "
      "value_first (%+.3f) do not" % (mean["weak_first"], mean["random"], mean["value_first"]))

# 6. figures and viewers are on disk
print("\n6. figures, viewers and screenshots (engine/out/cake_figs/)")
want = ["F1_atlas.png", "F2_gallery.png", "F3_fingerprints.png", "F4_reachability_all.png",
        "F5_loop.png", "F6_parameters.png", "E1_pca_stakeholder.png", "viewers_index.html"]
for w in want:
    check((FIGS / w).exists() and (FIGS / w).stat().st_size > 20000, "%-24s present" % w)
shots = list(FIGS.glob("shot_*.png"))
viewers = list(FIGS.glob("viewer_*.html"))
check(len(viewers) == 8, "%d interactive viewers (one per case study)" % len(viewers))
check(len(shots) == 80, "%d headless screenshots (8 sites x 5 configurations x 2 views)" % len(shots))

print("\n%s  %d checks failed" % ("FAILED" if fail else "ALL PASS", len(fail)))
sys.exit(1 if fail else 0)