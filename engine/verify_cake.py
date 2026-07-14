"""
verify_cake.py — recompute the headline numbers of metrics_cake.json from the artefacts themselves.
Wired into reproduce.py --verify. Exits non-zero if anything fails to reconcile.
"""
import json, csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "cake"
SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
M = json.load(open(OUT / "metrics_cake.json", encoding="utf-8"))
fail = []

print("\ncake model, five jiedao (from engine/out/cake/):\n")
print("%-10s%9s%9s%9s%9s" % ("district", "n", "state", "developer", "resident"))
for s in SITES:
    c = M[s]["current"]["shares_gfa"]
    print("%-10s%9d%9.3f%9.3f%9.3f" % (s, M[s]["current"]["n"], c["state"], c["developer"], c["resident"]))

print("\n%-10s%-20s%9s%8s%9s%12s" % ("district", "scenario", "reached", "met", "dGFA%", "resid.disp"))
for s in SITES:
    for k, v in M[s].items():
        if k in ("current", "negotiation"):
            continue
        print("%-10s%-20s%9.3f%8s%9.1f%12.2e"
              % (s, k, v["share_reached"], v["target_met"], v["gfa_change_pct"], v["displacement_gfa"]["resident"]))
        # a mode-A run must conserve the cake
        if k.endswith("_A") and abs(v["gfa_change_pct"]) > 1e-6:
            fail.append("%s %s: mode A changed total GFA by %.4f%%" % (s, k, v["gfa_change_pct"]))
        # a run may never claim success without reaching its target
        if v["target_met"] and v["share_reached"] < v["target"] - 1e-9:
            fail.append("%s %s: claims target_met but reached %.4f < %.4f" % (s, k, v["share_reached"], v["target"]))
        if v["pool_exhausted"] and v["target_met"]:
            fail.append("%s %s: pool exhausted AND target met" % (s, k))
        # the ledger must reconcile with the reported displacement
        p = OUT / ("ledger_%s_%s.csv" % (s, k))
        if p.exists():
            rows = list(csv.DictReader(open(p, encoding="utf-8")))
            if len(rows) != v["acquired_n"]:
                fail.append("%s %s: ledger has %d rows, acquired_n = %d" % (s, k, len(rows), v["acquired_n"]))
            for cls in ("state", "developer", "resident"):
                tot = sum(float(r["gfa_before"]) for r in rows if r["from_sh"] == cls)
                if abs(tot - v["displacement_gfa"][cls]) > 1.0:
                    fail.append("%s %s: ledger %s displacement %.1f != reported %.1f"
                                % (s, k, cls, tot, v["displacement_gfa"][cls]))
            for r in rows:
                # area and h_before are stored rounded, so compare with a relative tolerance:
                # a 0.05 m2 rounding on a 100 m building is already 5 m3.
                lhs, rhs = float(r["gfa_before"]), float(r["area"]) * float(r["h_before"])
                if abs(lhs - rhs) > max(5.0, 0.002 * max(lhs, rhs)):
                    fail.append("%s %s bid %s: gfa_before %.1f != area x h_before %.1f" % (s, k, r["bid"], lhs, rhs))
                    break

print("\n" + ("cake verification: PASS (%d scenarios reconcile)" % sum(len(M[s]) - 1 for s in SITES)
              if not fail else "cake verification: FAIL\n  " + "\n  ".join(fail[:12])))
sys.exit(0 if not fail else 1)
