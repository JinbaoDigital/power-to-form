"""
exp15_table2_check.py — machine check of Table 2 (regime direction signatures).

Recomputes, from the frozen results/metrics.json, the direction each of 7 metrics moves
under each of the 4 regimes across the 5 districts (n/5 up / down / unchanged), and asserts it against
the manuscript's corrected Table 2. Turns the review panel's hand-caught errors into a regression test:
any future numeric drift fails here instead of relying on human proofreading.
Run:  python3 exp15_table2_check.py   ->  out/exp15_table2_check.md ; exit 0 if all cells match.
"""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
M = json.load(open(ROOT / "results" / "metrics.json"))
DIST = list(M)
REGIMES = ["developer_led", "state_led", "resident_self_build", "shared"]
# display label -> json key
METRICS = [("FAR", "far"), ("Cov", "coverage"), ("MeanH", "h_mean"), ("HCV", "h_cv"),
           ("Slender", "slender"), ("Count", "n"), ("Conc", "concentration")]
EPS = 1e-9

# expected dominant direction + count, from the corrected manuscript (Table 2 + §5.1 concentration)
# tuple = (symbol, n) where symbol in {"up","down","flat"}; flat means unchanged in all 5
EXPECT = {
    "developer_led":       {"FAR": ("up", 5), "Cov": ("down", 5), "MeanH": ("up", 5), "HCV": ("down", 5), "Slender": ("up", 5), "Count": ("up", 5), "Conc": ("down", 4)},
    "state_led":           {"FAR": ("down", 3), "Cov": ("flat", 5), "MeanH": ("down", 5), "HCV": ("up", 5), "Slender": ("down", 5), "Count": ("flat", 5), "Conc": ("up", 5)},
    "resident_self_build": {"FAR": ("down", 5), "Cov": ("down", 5), "MeanH": ("down", 5), "HCV": ("down", 5), "Slender": ("up", 5), "Count": ("up", 5), "Conc": ("down", 3)},
    "shared":              {"FAR": ("down", 5), "Cov": ("down", 5), "MeanH": ("up", 4), "HCV": ("down", 5), "Slender": ("up", 5), "Count": ("flat", 5), "Conc": ("down", 4)},
}


def counts(reg, key):
    up = dn = fl = 0
    for d in DIST:
        cur = M[d]["rows"]["current"][key]
        val = M[d]["rows"][reg][key]
        if abs(val - cur) <= EPS:
            fl += 1
        elif val > cur:
            up += 1
        else:
            dn += 1
    return up, dn, fl


def dominant(up, dn, fl):
    if fl == len(DIST):
        return ("flat", fl)
    return ("up", up) if up >= dn else ("down", dn)


SYM = {"up": "↑", "down": "↓", "flat": "·"}
rows_md = ["# exp15 — Table 2 machine check (regime direction signatures)\n",
           "Recomputed from results/metrics.json; compared to the corrected manuscript Table 2.\n",
           "| metric | " + " | ".join(r.replace("_led", "").replace("_self_build", "-built") for r in REGIMES) + " |",
           "|---|" + "---|" * len(REGIMES)]
all_ok = True
mismatches = []
for lab, key in METRICS:
    cells = []
    for reg in REGIMES:
        up, dn, fl = counts(reg, key)
        dsym, dn_count = dominant(up, dn, fl)
        exp_sym, exp_n = EXPECT[reg][lab]
        ok = (dsym == exp_sym and dn_count == exp_n)
        if not ok:
            all_ok = False
            mismatches.append(f"{reg}.{lab}: got {SYM[dsym]}{dn_count} (up{up}/dn{dn}/·{fl}), expected {SYM[exp_sym]}{exp_n}")
        mark = "" if ok else " ✗"
        cells.append(f"{SYM[dsym]}{dn_count}{mark}")
    rows_md.append(f"| {lab} | " + " | ".join(cells) + " |")

rows_md.append("")
rows_md.append(("**PASS** — all 28 cells match the corrected manuscript Table 2." if all_ok
                else "**FAIL** — mismatches:\n- " + "\n- ".join(mismatches)))
(OUT / "exp15_table2_check.md").write_text("\n".join(rows_md), encoding="utf-8")
print("\n".join(rows_md))
sys.exit(0 if all_ok else 1)
