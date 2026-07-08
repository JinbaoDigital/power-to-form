"""exp1 — 级联信度:深度分布 + 源间一致性(离线,读 engine/data 缓存)。
产出(experiments/out/):
  exp1_cascade_depth.csv    每街道:由第几跳(EULUC/function/AOI/unknown)决定的建筑占比
  exp1_source_agreement.csv 两两源(在同时有判定的子集上)的一致率 + Cohen's kappa
  exp1_summary.md           论文 §3.5 可直接引用的摘要
跑:python3 exp1_cascade_reliability.py     (~1 分钟)
"""
import sys, yaml
from pathlib import Path
import pandas as pd
import geopandas as gpd

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
sys.path.insert(0, str(ENGINE))
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)

SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
LK = yaml.safe_load(open(ENGINE / "config" / "stakeholder_lookup.yaml", encoding="utf-8"))


def by_euluc(v):
    return LK["euluc"].get(v) if isinstance(v, str) else None

def by_function(v):
    return LK["function"].get(v) if isinstance(v, str) else None

def by_aoi(row):
    """AOI 关键词匹配(与 pf_common.assign_stakeholder 同逻辑:aoi 字段拼接后找关键词)。"""
    txt = " ".join(str(row.get(c, "")) for c in ("aoi_type1", "aoi_type2", "aoi_type") if pd.notna(row.get(c)))
    if not txt.strip():
        return None
    for kw, sh in LK["aoi_contains"].items():
        if kw in txt:
            return sh
    return None


def kappa(a, b):
    """Cohen's kappa(手写,免 sklearn 依赖)。a,b 等长列表。"""
    cats = sorted(set(a) | set(b)); n = len(a)
    if n == 0: return float("nan"), 0
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan"), n


depth_rows, agree_rows = [], []
for slug in SITES:
    g = gpd.read_parquet(ENGINE / "data" / slug / "buildings.parquet")
    n = len(g)
    e = g["euluc"].map(lambda v: by_euluc(v))
    f = g["function"].map(lambda v: by_function(v))
    a = g.apply(by_aoi, axis=1)
    # 级联深度(第一个命中即定,与 pf_common cascade 顺序一致:euluc→function→aoi)
    decided_by = pd.Series("unknown", index=g.index)
    decided_by[a.notna()] = "3_aoi"
    decided_by[f.notna()] = "2_function"
    decided_by[e.notna()] = "1_euluc"
    dist = decided_by.value_counts(normalize=True)
    depth_rows.append({"district": slug, "n": n,
                       **{k: round(float(dist.get(k, 0)) * 100, 1) for k in ["1_euluc", "2_function", "3_aoi", "unknown"]}})
    # 源间一致性(两两,在双方都有判定的建筑上)
    for (n1, s1), (n2, s2) in [(("euluc", e), ("function", f)), (("euluc", e), ("aoi", a)), (("function", f), ("aoi", a))]:
        m = s1.notna() & s2.notna()
        aa, bb = list(s1[m]), list(s2[m])
        k, cnt = kappa(aa, bb)
        agr = sum(1 for x, y in zip(aa, bb) if x == y) / cnt * 100 if cnt else float("nan")
        agree_rows.append({"district": slug, "pair": f"{n1}~{n2}", "n_overlap": cnt,
                           "overlap_pct": round(cnt / n * 100, 1),
                           "agreement_pct": round(agr, 1) if cnt else None,
                           "kappa": round(k, 3) if cnt else None})
    print(slug, "done")

pd.DataFrame(depth_rows).to_csv(OUT / "exp1_cascade_depth.csv", index=False)
pd.DataFrame(agree_rows).to_csv(OUT / "exp1_source_agreement.csv", index=False)

# 汇总 md
dd = pd.DataFrame(depth_rows); ag = pd.DataFrame(agree_rows)
pool = ag.groupby("pair").apply(lambda x: pd.Series({
    "n": int(x.n_overlap.sum()),
    "agree_w": round((x.agreement_pct * x.n_overlap).sum() / x.n_overlap.sum(), 1)})).reset_index()
md = ["# exp1 级联信度 — 摘要\n",
      "## 级联深度(各街道由第几跳决定,%)\n", dd.to_markdown(index=False), "",
      "## 源间一致性(两两,重叠子集)\n", ag.to_markdown(index=False), "",
      "## 加权合并(跨街道)\n", pool.to_markdown(index=False), "",
      "写进论文 §3.5:深度分布回答「多源是不是单源+补丁」;κ 回答「独立证据对归属的同意度」。"]
(OUT / "exp1_summary.md").write_text("\n".join(md), encoding="utf-8")
print("完成 → out/exp1_*")
