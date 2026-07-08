"""exp8 — 配方顺序置换(审稿 B3):developer-led 的 3 个变换算子(split/slim/densify)全 6 种顺序
(freeze 恒在首位),量化「顺序效应 vs 基底效应」。
跑:python3 exp8_order_permutation.py     (~10 分钟) 产出:out/exp8_order.csv/.md
"""
import sys, itertools, copy
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
sys.path.insert(0, str(ENGINE))
import pf_common as C
import operators as OP
import measure as M

OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
BASE = OP.load_regimes(ENGINE / "config" / "regimes.yaml")["developer_led"]
freeze, *ops3 = BASE["steps"]                    # [freeze, split, slim, densify]
KEYS = ["far", "coverage", "h_mean", "h_max", "h_cv", "slender", "n", "grain"]

rows = []
for s in SITES:
    base = C.load_buildings(s)
    for perm in itertools.permutations(range(3)):
        spec = {"steps": [copy.deepcopy(freeze)] + [copy.deepcopy(ops3[i]) for i in perm]}
        met = M.diagnose(OP.apply_regime(base, spec), s)
        rows.append({"district": s, "order": "→".join(ops3[i]["op"].replace("split_to_towers","split") for i in perm),
                     **{k: round(met[k], 3) for k in KEYS}})
    print(s, "done")
df = pd.DataFrame(rows)
df.to_csv(OUT / "exp8_order.csv", index=False)

# 顺序效应(同街道跨顺序的极差)vs 基底效应(canonical 顺序跨街道的极差)
canon = "split→slim→densify"
md = ["# exp8 顺序置换(developer-led)— 摘要\n", "## 顺序效应 vs 基底效应(极差比较)\n"]
eff = []
for k in KEYS:
    order_spread = df.groupby("district")[k].agg(lambda x: x.max() - x.min()).median()
    sub = df[df.order == canon]
    substrate_spread = sub[k].max() - sub[k].min()
    eff.append({"metric": k, "median_order_spread": round(order_spread, 3),
                "substrate_spread_canonical": round(substrate_spread, 3),
                "order/substrate": round(order_spread / substrate_spread, 3) if substrate_spread else None})
md += [pd.DataFrame(eff).to_markdown(index=False), "",
       "论文写法:非交换性真实存在(order spread ≠ 0),但顺序效应/基底效应 = 表中比值;",
       "并论证 canonical 顺序编码权力行动的时间序(assemble→verticalize→densify)。", "",
       "## 全表\n", df.to_markdown(index=False)]
(OUT / "exp8_order.md").write_text("\n".join(md), encoding="utf-8")
print("完成 → out/exp8_*")
