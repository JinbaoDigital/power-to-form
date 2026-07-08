"""exp13 — 漫画与现实的距离:developer 配方移植到其余四街道后,逐维对照真实陆家嘴现状。

不是验证(配方是漫画,§6.5),是仪器的边界刻画,回答三个问题:
  Q1 方向:配方在各维度上把街道推向陆家嘴的那一侧吗?(toward-side agreement)
  Q2 力度:推过头多少?(overshoot ratio = 实际位移 / 到范例的位移;>1 过冲)
  Q3 结构:哪些维度反向?反向处 = 纯资本漫画与「国家+资本联合体」真实产物的形态分歧
          (预期:grain 反向——真实陆家嘴是裙楼粗粒,漫画拆塔是细粒)。

离线:只读 data/metrics.json,秒级。
产出:out/exp13_transplant.csv + exp13_summary.md
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
MJ = json.load(open(HERE.parent / "data" / "metrics.json"))

METRICS = ["far", "coverage", "h_mean", "h_max", "h_cv", "grain", "slender", "concentration"]
SITES = ["caoyang", "laoximen", "dapuqiao", "yuyuan"]
EXEMPLAR = "lujiazui"
LJ = MJ[EXEMPLAR]["rows"]["current"]

rows = []
for s in SITES:
    b = MJ[s]["rows"]["current"]; a = MJ[s]["rows"]["developer_led"]
    for m in METRICS:
        target, before, after = LJ[m], b[m], a[m]
        need = target - before          # 到范例还差多少
        move = after - before           # 配方实际推了多少
        if abs(move) < 1e-9:
            verdict, overshoot = "static", None
        elif need * move > 0:
            overshoot = move / need
            verdict = "toward" if overshoot <= 1 else "overshoot"
        else:
            verdict, overshoot = "away", None
        closer = abs(after - target) < abs(before - target)
        rows.append({"district": s, "metric": m,
                     "exemplar": round(target, 3), "before": round(before, 3),
                     "after": round(after, 3), "verdict": verdict,
                     "overshoot_ratio": round(overshoot, 2) if overshoot else "",
                     "ends_closer": closer})

with open(OUT / "exp13_transplant.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

# ---- 汇总
by_m = {m: [r for r in rows if r["metric"] == m] for m in METRICS}
lines = ["# exp13 漫画与现实的距离 — developer 配方 vs 真实陆家嘴(现状)\n",
         "| metric | LJZ 现状 | 4 街道判定(toward/overshoot/away) | ends closer |",
         "|---|---|---|---|"]
for m in METRICS:
    rs = by_m[m]
    v = ", ".join(f"{r['district'][:3]}:{r['verdict']}" for r in rs)
    c = sum(r["ends_closer"] for r in rs)
    lines.append(f"| {m} | {LJ[m]:.2f} | {v} | {c}/4 |")
n_toward = sum(1 for r in rows if r["verdict"] in ("toward", "overshoot"))
n_closer = sum(1 for r in rows if r["ends_closer"])
lines += [
    "",
    f"推向范例一侧(含过冲):{n_toward}/{len(rows)};终点更近:{n_closer}/{len(rows)}。",
    "",
    "读法:配方在陆家嘴真正「开发商化」的维度(coverage、h_max)上把街道拉近范例(4/4);",
    "在强度维(h_mean、slender)上以漫画化力度冲过头(参数未按范例标定,§6.5);",
    "grain 的行为与范例无关:配方一律细粒化(拆塔),而真实陆家嘴以裙楼大 footprint 为主,",
    "两街道远离、两街道以数十倍过冲越过。这个缺口不是仪器失误,而是范例本身是",
    "国家+资本联合体的产物(§5.5),纯 developer 漫画不应、也确实没有复现它。",
]
(OUT / "exp13_summary.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
