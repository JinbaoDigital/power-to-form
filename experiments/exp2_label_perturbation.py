"""exp2 — 标签扰动稳健性:随机翻转 k% 标签,重跑四体制,看结论存活情况。
把主张从「标签是对的」换成「结论对标签误差稳健」(后者可证)。
检查三类结论:(a) Table 3 方向签名;(b) 基底记忆 ρ(grain/resident、h_max/state 的塌缩);(c) Table 4 dip 双峰计数。
跑:python3 exp2_label_perturbation.py        默认 K=[5,10,20]%,SEEDS=3 → 5街道×4体制×3k×3seed=180 次变换
    数据机上可调大 SEEDS。预计 30–90 分钟。
产出:out/exp2_perturbation.json + exp2_summary.md
"""
import sys, json, random
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
sys.path.insert(0, str(ENGINE))
import pf_common as C
import operators as OP
import measure as M
import diptest

OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
REGS = OP.load_regimes(ENGINE / "config" / "regimes.yaml")
RNAMES = ["developer_led", "state_led", "resident_self_build", "shared"]
KS = [0.05, 0.10, 0.20]
SEEDS = [0, 1, 2]
CLASSES = ["state", "developer", "resident", "unknown"]

def flip(recs, k, seed):
    rng = random.Random(seed)
    out = [dict(r) for r in recs]
    idx = rng.sample(range(len(out)), int(len(out) * k))
    for i in idx:
        cur = out[i]["sh"]
        out[i]["sh"] = rng.choice([c for c in CLASSES if c != cur])
    return out

def spearman(a, b):
    def rank(v):
        s = sorted(range(len(v)), key=lambda i: v[i]); r = [0]*len(v)
        for p, i in enumerate(s): r[i] = p
        return r
    ra, rb = rank(a), rank(b); n = len(a)
    return 1 - 6*sum((x-y)**2 for x, y in zip(ra, rb))/(n*(n*n-1))

base = {s: C.load_buildings(s) for s in SITES}
cur_metrics = {s: M.diagnose(base[s], s) for s in SITES}

results = []
total = len(KS)*len(SEEDS)*len(SITES)*len(RNAMES); done = 0
for k in KS:
    for seed in SEEDS:
        run = {"k": k, "seed": seed, "metrics": {}, "dip_p": {}}
        for slug in SITES:
            pert = flip(base[slug], k, seed*1000+hash(slug) % 997)
            run["metrics"][slug] = {}
            run["dip_p"][slug] = {}
            for reg in RNAMES:
                after = OP.apply_regime(pert, REGS[reg])
                run["metrics"][slug][reg] = M.diagnose(after, slug)
                h = np.array([r["h"] for r in after if r["h"] > 0])
                run["dip_p"][slug][reg] = float(diptest.diptest(h)[1])
                done += 1
                print(f"[{done}/{total}] k={k} seed={seed} {slug} {reg}", flush=True)
        results.append(run)

json.dump({"runs": results, "current": cur_metrics}, open(OUT / "exp2_perturbation.json", "w"), default=float)

# ---- 汇总:三类结论的存活率
md = ["# exp2 标签扰动稳健性 — 摘要\n"]
for k in KS:
    runs = [r for r in results if r["k"] == k]
    # (a) developer 方向签名 5/5?(far↑ cov↓ slender↑)
    sig_ok = 0
    for r in runs:
        ok = all(r["metrics"][s]["developer_led"]["far"] > cur_metrics[s]["far"] and
                 r["metrics"][s]["developer_led"]["coverage"] < cur_metrics[s]["coverage"] and
                 r["metrics"][s]["developer_led"]["slender"] > cur_metrics[s]["slender"] for s in SITES)
        sig_ok += ok
    # (b) 基底记忆选择性:grain/resident ρ 仍显著低于 grain/developer ρ?
    mem_ok = 0
    for r in runs:
        cur_g = [cur_metrics[s]["grain"] for s in SITES]
        rho_res = spearman(cur_g, [r["metrics"][s]["resident_self_build"]["grain"] for s in SITES])
        rho_dev = spearman(cur_g, [r["metrics"][s]["developer_led"]["grain"] for s in SITES])
        mem_ok += (rho_res < 0.5 and rho_dev > 0.8)
    # (c) resident 双峰 5/5?
    dip_ok = sum(all(r["dip_p"][s]["resident_self_build"] < 0.05 for s in SITES) for r in runs)
    md.append(f"## k = {int(k*100)}%({len(runs)} seeds)\n"
              f"- developer 方向签名(far↑cov↓slender↑ 于 5/5)存活:{sig_ok}/{len(runs)}\n"
              f"- 基底记忆选择性(grain: ρ_resident<0.5 且 ρ_developer>0.8)存活:{mem_ok}/{len(runs)}\n"
              f"- resident-built 双峰 5/5(dip p<0.05)存活:{dip_ok}/{len(runs)}\n")
(OUT / "exp2_summary.md").write_text("\n".join(md), encoding="utf-8")
print("完成 → out/exp2_*")
