"""exp6 — 守恒偏差量化(审稿 A2):逐算子步进,测每步 GFA(=Σ area·h)变化。
回答:声称守恒的算子在 clamp 下的实际偏差是多少(open_ground cap、weight/concentrate 截断、
densify 削顶、split 丢塔)。产出直接改写论文 Table 2 的守恒列 + §5.3 叙述。
跑:python3 exp6_conservation_deviation.py    (~3 分钟) 产出:out/exp6_conservation.csv/.md
"""
import sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
sys.path.insert(0, str(ENGINE))
import pf_common as C
import operators as OP

OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
REGS = OP.load_regimes(ENGINE / "config" / "regimes.yaml")

def gfa(recs):
    return sum(r["geom"].area * r["h"] for r in recs)

def fparea(recs):
    return sum(r["geom"].area for r in recs)

rows = []
for slug in SITES:
    base = C.load_buildings(slug)
    for reg, spec in REGS.items():
        cur = [dict(r) for r in base]
        g0, a0, n0 = gfa(cur), fparea(cur), len(cur)
        for si, step in enumerate(spec["steps"]):
            g_in, a_in, n_in = gfa(cur), fparea(cur), len(cur)
            cur = OP.apply_regime(cur, {"steps": [step]})
            g_out, a_out, n_out = gfa(cur), fparea(cur), len(cur)
            rows.append({"district": slug, "regime": reg, "step": si, "op": step["op"],
                         "dGFA_%": round((g_out/g_in - 1) * 100, 2),
                         "dFootprint_%": round((a_out/a_in - 1) * 100, 2),
                         "dCount": n_out - n_in})
        rows.append({"district": slug, "regime": reg, "step": "TOTAL", "op": "-",
                     "dGFA_%": round((gfa(cur)/g0 - 1) * 100, 2),
                     "dFootprint_%": round((fparea(cur)/a0 - 1) * 100, 2),
                     "dCount": len(cur) - n0})
    print(slug, "done")

df = pd.DataFrame(rows)
df.to_csv(OUT / "exp6_conservation.csv", index=False)
# 按算子汇总「声称守恒」算子的实际偏差
CONSERVING = ["weight_height", "concentrate", "split_to_towers", "slim", "open_ground"]
agg = (df[df.op.isin(CONSERVING)].groupby("op")["dGFA_%"]
       .agg(["min", "median", "max"]).round(2).reset_index())
md = ["# exp6 守恒偏差 — 摘要\n",
      "## 声称守恒的算子:单步 ΔGFA%(跨 街道×出现位置)\n", agg.to_markdown(index=False), "",
      "## 全部逐步记录\n", df.to_markdown(index=False)]
(OUT / "exp6_conservation.md").write_text("\n".join(md), encoding="utf-8")
print("完成 → out/exp6_*"); print(agg.to_string(index=False))
