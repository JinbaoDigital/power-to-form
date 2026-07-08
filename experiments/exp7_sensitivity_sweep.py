"""exp7 — 参数敏感性 OAT 扫描(审稿 B2):每个关键参数 ×0.7/×1.3,重跑对应体制,
看 Table 3 方向格与 resident 双峰计数是否翻转。
跑:python3 exp7_sensitivity_sweep.py     (数据机建议;~1–2 小时) 产出:out/exp7_sensitivity.csv/.md
"""
import sys, copy, json
from pathlib import Path
import numpy as np
import pandas as pd
import diptest

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
sys.path.insert(0, str(ENGINE))
import pf_common as C
import operators as OP
import measure as M

OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
BASE = OP.load_regimes(ENGINE / "config" / "regimes.yaml")
FACTORS = [0.7, 1.3]

# (体制, step 序号, 参数名, 是否整型)
PARAMS = [
    ("developer_led", 1, "above_m2", False), ("developer_led", 1, "k", True),
    ("developer_led", 2, "ratio", False),    ("developer_led", 3, "far_gain", False),
    ("developer_led", 3, "cap_m", False),
    ("state_led", 0, None, False),           # weight_height: 扰动 state 权重(特判)
    ("state_led", 1, "reach_frac", False),   ("state_led", 1, "cap_m", False),
    ("resident_self_build", 1, "cell_m2", False), ("resident_self_build", 2, "alpha", False),
    ("shared", 0, "ratio", False),           ("shared", 0, "cap_m", False),
    ("shared", 1, "alpha", False),
]

base_recs = {s: C.load_buildings(s) for s in SITES}
cur = {s: M.diagnose(base_recs[s], s) for s in SITES}

def signature_ok(reg, mets):
    """该体制的关键方向签名是否在 5/5 街道成立(只测涌现敏感的格)。"""
    if reg == "developer_led":
        return all(mets[s]["h_cv"] > cur[s]["h_cv"] for s in SITES)          # CV↑ 是涌现格
    if reg == "state_led":
        return all(mets[s]["concentration"] > cur[s]["concentration"] for s in SITES)
    if reg == "resident_self_build":
        return all(mets[s]["n"] > cur[s]["n"] for s in SITES)
    if reg == "shared":
        return all(mets[s]["h_cv"] < cur[s]["h_cv"] for s in SITES)
    return None

rows = []
total = len(PARAMS) * len(FACTORS); done = 0
for reg, si, pname, is_int in PARAMS:
    for f in FACTORS:
        spec = copy.deepcopy(BASE[reg])
        if pname is None:                      # state 权重特判
            spec["steps"][si]["weights"]["state"] *= f
            label = f"weights.state x{f}"
        else:
            v = spec["steps"][si][pname] * f
            spec["steps"][si][pname] = int(round(v)) if is_int else v
            label = f"{pname} x{f}"
        mets, dips = {}, {}
        for s in SITES:
            after = OP.apply_regime(base_recs[s], spec)
            mets[s] = M.diagnose(after, s)
            h = np.array([r["h"] for r in after if r["h"] > 0])
            dips[s] = diptest.diptest(h)[1]
        row = {"regime": reg, "step": si, "param": label,
               "signature_5of5": signature_ok(reg, mets)}
        if reg == "resident_self_build":
            row["dip_bimodal_count"] = sum(p < 0.05 for p in dips.values())
        rows.append(row)
        done += 1
        print(f"[{done}/{total}] {reg} {label} → sig={row['signature_5of5']}", flush=True)

df = pd.DataFrame(rows)
df.to_csv(OUT / "exp7_sensitivity.csv", index=False)
flips = df[df.signature_5of5 == False]  # noqa: E712
md = ["# exp7 参数敏感性(OAT ±30%)— 摘要\n", df.to_markdown(index=False), "",
      f"**翻转的格子:{len(flips)} 个**(空 = 所有涌现签名对 ±30% 扰动稳健)。",
      "论文写法:'each recipe's emergent signature survives ±30% one-at-a-time perturbation of its parameters"
      " except …' 按此表填空。"]
(OUT / "exp7_sensitivity.md").write_text("\n".join(md), encoding="utf-8")
print("完成 → out/exp7_*")
