"""exp5 — 直管公房误标上界:老城厢 resident 标签中战前(<1949)建筑占比。
用地=居住 → resident 只反映使用,不反映控制;上海老城厢大量里弄为市管公房(state 控制)。
战前建成且被标 resident 的份额 = 该误标方向的可估上界。
跑:python3 exp5_prewar_bound.py    (秒级) 产出:out/exp5_prewar_bound.csv/.md
"""
import sys, re
from pathlib import Path
import pandas as pd
import geopandas as gpd

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]

def parse_year(v):
    if pd.isna(v): return None
    m = re.search(r"(18|19|20)\d{2}", str(v))
    return int(m.group()) if m else None

rows = []
for slug in SITES:
    g = gpd.read_parquet(ENGINE / "data" / slug / "buildings.parquet")
    g["year"] = g["age"].map(parse_year)
    res = g[g["stakeholder"] == "resident"]
    cov_all = g["year"].notna().mean() * 100
    cov_res = res["year"].notna().mean() * 100
    resy = res[res["year"].notna()]
    pre49 = (resy["year"] < 1949).mean() * 100 if len(resy) else float("nan")
    ymin = int(g["year"].min()) if g["year"].notna().any() else None
    rows.append({"district": slug, "n": len(g), "n_resident": len(res),
                 "year_coverage_all_%": round(cov_all, 1),
                 "year_coverage_resident_%": round(cov_res, 1),
                 "year_min": ymin,
                 "resident_pre1949_%_of_dated": round(pre49, 1) if pre49 == pre49 else None})
    print(slug, "done")
df = pd.DataFrame(rows)
df.to_csv(OUT / "exp5_prewar_bound.csv", index=False)
censored = df["year_min"].min() >= 1949 if df["year_min"].notna().any() else True
md = ["# exp5 战前上界 — 摘要\n", df.to_markdown(index=False), ""]
if censored:
    md += [f"**结论:年份源右删失(全部年份 ≥ {int(df['year_min'].min())},疑为登记/普查年而非建成年),**",
           "**战前建筑完全不可见 → 此源无法约束直管公房误标。**",
           "论文写法:如实报告该源的删失,公房误标只能定性声明 + 依赖 exp3/exp4 人工点检在老城厢的针对性核查。"]
else:
    md += ["解释:resident 标签中「有年份且 <1949」的份额,是老城厢直管公房方向误标的可估上界",
           "(战前里弄多为公房;并非全部,故为上界而非点估计)。年份覆盖率低时须一并报告覆盖率。"]
(OUT / "exp5_prewar_bound.md").write_text("\n".join(md), encoding="utf-8")
print("完成 → out/exp5_*")
