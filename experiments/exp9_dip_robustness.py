"""exp9 — dip 检验稳健性(审稿 A3):原始 vs 对数高度、效应量 D、多重比较校正、层高离散化敏感性。
跑:python3 exp9_dip_robustness.py    (~2 分钟) 产出:out/exp9_dip_robustness.csv/.md
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import diptest

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
sys.path.insert(0, str(ENGINE))
import pf_common as C
import operators as OP

OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
REGS = OP.load_regimes(ENGINE / "config" / "regimes.yaml")
STATES = ["current", "developer_led", "state_led", "resident_self_build", "shared"]

rows = []
for slug in SITES:
    base = C.load_buildings(slug)
    states = {"current": base}
    for r in STATES[1:]:
        states[r] = OP.apply_regime(base, REGS[r])
    for sname, recs in states.items():
        h = np.array([r["h"] for r in recs if r["h"] > 0])
        d_raw, p_raw = diptest.diptest(h)
        d_log, p_log = diptest.diptest(np.log10(h))
        h3 = np.round(h / 3.0) * 3.0                      # 层高 3m 离散化
        d_dis, p_dis = diptest.diptest(h3)
        rows.append({"district": slug, "state": sname, "n": len(h),
                     "D_raw": round(d_raw, 4), "p_raw": round(p_raw, 4),
                     "D_log": round(d_log, 4), "p_log": round(p_log, 4),
                     "D_disc3m": round(d_dis, 4), "p_disc3m": round(p_dis, 4)})
    print(slug, "done")
df = pd.DataFrame(rows)

# Holm 校正(在 25 个原始检验上;log 同样处理)
def holm(ps):
    order = np.argsort(ps); m = len(ps); adj = np.empty(m)
    mx = 0
    for rank, i in enumerate(order):
        mx = max(mx, (m - rank) * ps[i]); adj[i] = min(1.0, mx)
    return adj
df["p_raw_holm"] = holm(df["p_raw"].values).round(4)
df["p_log_holm"] = holm(df["p_log"].values).round(4)
df.to_csv(OUT / "exp9_dip_robustness.csv", index=False)

cnt = lambda col: df[df[col] < 0.05].groupby("state").size().reindex(STATES).fillna(0).astype(int)
summ = pd.DataFrame({"raw_p<.05": cnt("p_raw"), "raw_holm<.05": cnt("p_raw_holm"),
                     "log_p<.05": cnt("p_log"), "log_holm<.05": cnt("p_log_holm"),
                     "disc3m_p<.05": cnt("p_disc3m")})
md = ["# exp9 dip 稳健性 — 摘要\n",
      "## 每状态双峰显著计数(/5 街道),不同变换与校正下\n", summ.to_markdown(), "",
      "结论写法:报告 D 与 p;声明检验所用变换;Holm 校正后仍存活的格子才进正文强调。",
      "", "## 全表\n", df.to_markdown(index=False)]
(OUT / "exp9_dip_robustness.md").write_text("\n".join(md), encoding="utf-8")
print("完成 → out/exp9_*"); print(summ.to_string())
