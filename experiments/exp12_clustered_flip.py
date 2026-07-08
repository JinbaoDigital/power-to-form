"""exp12 — 聚类对抗性标签扰动(模拟审稿 X1):随机翻转(exp2)看不见方向性、
空间成块的误标。已知误差方向:老城厢直管公房被 EULUC-居住 → resident,实为市管公房(state)。

对抗设定:在 laoximen、yuyuan 两个老城街道,把 resident 标签**空间连片地**翻成 state
(种子建筑 + 质心距离最近的 resident 邻居,直到达到目标份额 f ∈ {30%, 60%}),
重跑四体制,检查三类结论是否存活:
  (a) developer 方向签名(far↑ coverage↓ slender↑)5/5;
  (b) 基底记忆选择性(grain:ρ_resident 显著低于 ρ_developer);
  (c) state-led 守恒(|ΔGFA| 仍为四体制中最小)。
未修改街道的结果取冻结 json(标签翻转不改变几何,现状指标不变)。

跑:python3 exp12_clustered_flip.py     (2 份额 × 3 种子 × 2 街道 × 4 体制 = 48 次变换,约几分钟)
产出:out/exp12_clustered.json + exp12_summary.md
"""
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
sys.path.insert(0, str(ENGINE))
import pf_common as C
import operators as OP
import measure as M

OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
MJ = json.load(open(HERE.parent / "data" / "metrics.json"))
SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
TARGETS = ["laoximen", "yuyuan"]          # 老城厢:已知误标方向所在
REGS = OP.load_regimes(ENGINE / "config" / "regimes.yaml")
RNAMES = ["developer_led", "state_led", "resident_self_build", "shared"]
FRACS = [0.30, 0.60]
SEEDS = [0, 1, 2]


def clustered_flip(recs, frac, seed):
    """resident → state,空间连片:随机 resident 种子 + 质心最近邻扩张到 frac。"""
    out = [dict(r) for r in recs]
    res_idx = [i for i, r in enumerate(out) if r["sh"] == "resident"]
    k = int(len(res_idx) * frac)
    rng = random.Random(seed)
    s = out[rng.choice(res_idx)]["geom"].centroid
    ranked = sorted(res_idx, key=lambda i: math.hypot(
        out[i]["geom"].centroid.x - s.x, out[i]["geom"].centroid.y - s.y))
    for i in ranked[:k]:
        out[i]["sh"] = "state"
    return out


def spearman(a, b):
    rk = lambda v: [sorted(range(len(v)), key=lambda i: v[i]).index(i) for i in range(len(v))]
    x, y = rk(a), rk(b); n = len(a)
    return 1 - 6 * sum((p - q) ** 2 for p, q in zip(x, y)) / (n * (n * n - 1))


base = {s: C.load_buildings(s) for s in TARGETS}
cur = {s: MJ[s]["rows"]["current"] for s in SITES}
frozen = {s: MJ[s]["rows"] for s in SITES}          # 未修改街道直接引用

results = []
total = len(FRACS) * len(SEEDS) * len(TARGETS) * len(RNAMES); done = 0
for f in FRACS:
    for seed in SEEDS:
        world = {s: dict(frozen[s]) for s in SITES}  # 先抄冻结,再覆写被修改街道
        for slug in TARGETS:
            pert = clustered_flip(base[slug], f, seed * 100 + len(slug))
            for reg in RNAMES:
                after = OP.apply_regime([dict(r) for r in pert], REGS[reg])
                world[slug][reg] = M.diagnose(after, slug)
                done += 1
                print(f"[{done}/{total}] f={f} seed={seed} {slug} {reg}", flush=True)
        # ---- 三类结论
        sig = all(world[s]["developer_led"]["far"] > cur[s]["far"] and
                  world[s]["developer_led"]["coverage"] < cur[s]["coverage"] and
                  world[s]["developer_led"]["slender"] > cur[s]["slender"] for s in SITES)
        g0 = [cur[s]["grain"] for s in SITES]
        rho_res = spearman(g0, [world[s]["resident_self_build"]["grain"] for s in SITES])
        rho_dev = spearman(g0, [world[s]["developer_led"]["grain"] for s in SITES])
        dev_abs = {r: max(abs(world[s][r]["far"] / cur[s]["far"] - 1) for s in SITES) for r in RNAMES}
        state_min = dev_abs["state_led"] == min(dev_abs.values())
        results.append({"frac": f, "seed": seed, "dev_signature_5of5": sig,
                        "rho_resident": round(rho_res, 3), "rho_developer": round(rho_dev, 3),
                        "selectivity": rho_res < 0.5 < rho_dev,
                        "state_maxdev_pct": round(dev_abs["state_led"] * 100, 1),
                        "state_is_min_deviation": state_min})

json.dump(results, open(OUT / "exp12_clustered.json", "w"), indent=1)
lines = ["# exp12 聚类对抗性翻转(resident→state,老西门+豫园连片)— 摘要\n",
         "| f | seed | dev 签名 5/5 | ρ_res | ρ_dev | 选择性存活 | state 最大偏差% | state 仍最小偏差 |",
         "|---|---|---|---|---|---|---|---|"]
for r in results:
    lines.append(f"| {int(r['frac']*100)}% | {r['seed']} | {r['dev_signature_5of5']} | "
                 f"{r['rho_resident']} | {r['rho_developer']} | {r['selectivity']} | "
                 f"{r['state_maxdev_pct']} | {r['state_is_min_deviation']} |")
for f in FRACS:
    rs = [r for r in results if r["frac"] == f]
    lines.append(f"\nf={int(f*100)}%:签名存活 {sum(r['dev_signature_5of5'] for r in rs)}/{len(rs)},"
                 f"选择性存活 {sum(r['selectivity'] for r in rs)}/{len(rs)},"
                 f"state 最小偏差 {sum(r['state_is_min_deviation'] for r in rs)}/{len(rs)}")
lines.append("\n读法:这是**对抗性**扰动——按已知误标方向(直管公房)、空间连片地翻;"
             "比 exp2 的随机翻转更狠。存活/失守都如实进 §5.5(labels 轴升级为 random + adversarial)。")
(OUT / "exp12_summary.md").write_text("\n".join(lines), encoding="utf-8")
print("完成 → out/exp12_*")
