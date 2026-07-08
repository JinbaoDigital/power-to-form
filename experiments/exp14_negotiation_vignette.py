"""exp14 — 谈判 vignette:把 §6.1「谈判即编辑配方」做成一次可量测的演示(曹杨)。

三步配方序列(engine/config/vignette_recipes.yaml):
  v1 政府初案(= 发布版 state_led)
  v2 居民反对后:freeze(resident) + 塔降尺度(cap 600→150)+ resident 权重回 1.0
  v3 共享方加入:v2 + open_ground(state/developer, ratio 0.4)
每步输出 fingerprint + 按 stakeholder 类分组的 GFA;步间 diff = 谈判记录。

跑:python3 exp14_negotiation_vignette.py     (3 次体制施加,~1 分钟)
产出:out/exp14_vignette.json + exp14_summary.md
figure(数据机):用 fig8 同款渲染器出三步 massing(同机位)→ out/exp14_massing_v{1,2,3}.png,
组版由 JZ 机器在重写阶段完成。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
sys.path.insert(0, str(ENGINE))
import pf_common as C
import operators as OP
import measure as M

OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
SLUG = "caoyang"
RECIPES = OP.load_regimes(ENGINE / "config" / "vignette_recipes.yaml")
ORDER = ["vignette_v1_proposal", "vignette_v2_resident_counter", "vignette_v3_shared_ground"]
CLASSES = ["state", "developer", "resident", "unknown"]


def gfa_by_class(recs):
    out = {c: 0.0 for c in CLASSES}
    for r in recs:
        out[r["sh"]] += r["geom"].area * r["h"] / C.FLOOR_H
    return out


base = C.load_buildings(SLUG)
ctr = M.ref_center(base)
cur_m = M.diagnose(base, SLUG, ctr)
cur_g = gfa_by_class(base)

steps = {"current": {"metrics": cur_m, "gfa_by_class": cur_g}}
for name in ORDER:
    after = OP.apply_regime([dict(r) for r in base], RECIPES[name])
    steps[name] = {"metrics": M.diagnose(after, SLUG, ctr), "gfa_by_class": gfa_by_class(after)}
    print(name, "done", flush=True)

json.dump(steps, open(OUT / "exp14_vignette.json", "w"), indent=1, default=float)

# ---- 谈判记录表
KEY = ["far", "coverage", "h_max", "grain", "slender"]
lines = ["# exp14 谈判 vignette(曹杨,state × resident × shared)— 摘要\n",
         "| step | " + " | ".join(KEY) + " | ΔGFA_res % | ΔGFA_state % | ΔGFA_total % |",
         "|---|" + "---|" * (len(KEY) + 3)]
for name in ["current"] + ORDER:
    m, g = steps[name]["metrics"], steps[name]["gfa_by_class"]
    dres = (g["resident"] / cur_g["resident"] - 1) * 100
    dsta = (g["state"] / cur_g["state"] - 1) * 100
    dtot = (sum(g.values()) / sum(cur_g.values()) - 1) * 100
    lines.append(f"| {name} | " + " | ".join(f"{m[k]:.2f}" for k in KEY) +
                 f" | {dres:+.1f} | {dsta:+.1f} | {dtot:+.1f} |")
lines += ["",
          "谈判记录读法(与实测一致):v1 初案以守恒重分配削走居民 GFA 的三分之一强,换取",
          "政府类 +321% 与 600 m 塔;v2 冻结居民(ΔGFA_res=0)后,让步的成本显形——cap 150 在",
          "未冻结类上咬合,总 GFA −5.7%(h_max 228 为既存被冻结建筑,新塔止步于 150);",
          "v3 在 150 m 限高协议下再要共享地面,高度补偿被同一 cap 拦截,总量再付至 −14.2%,",
          "coverage 0.28→0.23。约束互锁的代价由配方 diff 逐步晒出:每一行都是一次可量测的让步。"]
(OUT / "exp14_summary.md").write_text("\n".join(lines), encoding="utf-8")
print("完成 → out/exp14_*")
