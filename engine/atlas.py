"""
atlas.py — 算子图谱:9 个原子动词各自的 before/after(教学核心)
=================================================================
学生先学"动词"再学"配方"。这页把每个算子单独施加在同一个样本上,看它到底改了什么:
  footprint 类(plan 最清楚):slim 塔化 / split 拆板 / infill 自建细分 / open_ground 释放地面
  height 类(3D 最清楚)   :weight_height 权重重分配 / concentrate 向重心收拢 / densify 加密 / level 平权
  freeze 锁定(无视觉变化,文字说明)
产出 out/atlas.html。
"""
import base64, warnings
warnings.filterwarnings("ignore")
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Point
import pf_common as C, operators as OP, render as R

OUT = C.OUT
SAMPLE = ("caoyang", "曹杨新村街道")

DEMOS = [
    ("slim", "塔化", "footprint 向形心缩到 ratio,高度 /ratio 补偿(单栋 GFA 守恒)→ 更细更高。", "plan",
     lambda r: OP.slim(r, ["resident", "developer"], 0.4)),
    ("split_to_towers", "拆板成塔", "大 footprint 沿 OBB 长轴拆成 k 块(高度不变 → GFA 守恒)。", "plan",
     lambda r: OP.split_to_towers(r, ["resident", "developer"], 600, 3)),
    ("infill", "居民自建", "把大 footprint 细分成自建小单元(细粒、低层、有机)。", "plan",
     lambda r: OP.infill(r, ["resident", "developer"], 120, 6, 21, 0.35)),
    ("open_ground", "释放地面", "缩私有 footprint 释放共享地面,高度补偿(GFA 守恒,不激进塔化)。", "plan",
     lambda r: OP.open_ground(r, ["resident", "developer"], 0.55, 200)),
    ("weight_height", "权重重分配高度", "按 stakeholder 权重重分配高度(此例:developer↑、其余↓,总 GFA 守恒)。", "3d",
     lambda r: OP.weight_height(r, {"developer": 1.8, "resident": 0.8, "state": 0.9, "unknown": 0.9}, "conserve")),
    ("concentrate", "向权力重心收拢", "高度按到权力重心(政府/公共质心)的距离收拢(守恒)→ 中央锥峰。", "3d",
     lambda r: OP.concentrate(r, "state_centroid", 0.18, 2.0, 600)),
    ("densify", "加密", "抬高度 = 加 GFA(footprint 不变)。", "3d",
     lambda r: OP.densify(r, ["resident", "developer"], 1.8, 480)),
    ("level", "平权/趋同", "目标楼高度向参考值(此例中位数)靠拢 → 均质。", "3d",
     lambda r: OP.level(r, ["resident", "developer", "state"], "median", 0.85)),
]


def _pair(before, after, kind, title):
    if kind == "plan":
        polys = [p for recs in (before, after) for r in recs for p in C._polys(r["geom"])]
        minx = min(p.bounds[0] for p in polys); maxx = max(p.bounds[2] for p in polys)
        miny = min(p.bounds[1] for p in polys); maxy = max(p.bounds[3] for p in polys)
        fig, axs = plt.subplots(1, 2, figsize=(11, 5.4))
        for ax, recs, t in ((axs[0], before, "before"), (axs[1], after, "after")):
            C.plot_footprints(ax, recs, lambda r: C.SH_COLOR[r["sh"]], lw=0.1)
            ax.set_xlim(minx, maxx); ax.set_ylim(miny, maxy); ax.set_title(t, fontsize=11)
    else:
        polys = [p for recs in (before, after) for r in recs for p in C._polys(r["geom"])]
        minx = min(p.bounds[0] for p in polys); miny = min(p.bounds[1] for p in polys)
        zmax = max(max(r["h"] for r in before), max(r["h"] for r in after)) * 1.04
        fig = plt.figure(figsize=(11, 5.2))
        for i, (recs, t) in enumerate(((before, "before"), (after, "after"))):
            ax = fig.add_subplot(1, 2, i + 1, projection="3d")
            R._boxes3d(ax, recs, minx, miny, zmax)
            ax.set_title(t, fontsize=11)
    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.subplots_adjust(top=.88, wspace=.04)
    return fig


def crop(recs, radius=320):
    cx = np.mean([r["geom"].centroid.x for r in recs]); cy = np.mean([r["geom"].centroid.y for r in recs])
    c = Point(cx, cy)
    return [r for r in recs if r["geom"].centroid.distance(c) <= radius]


def main():
    slug, name = SAMPLE
    if not (C.DATA / slug / "buildings.parquet").exists():
        C.build_cache(name, slug)
    before = crop(C.load_buildings(slug))
    figs = []
    for op, label, desc, kind, fn in DEMOS:
        after = fn([dict(r) for r in before])
        fig = _pair(before, after, kind, "%s — %s(%s 视图)" % (op, label, "平面" if kind == "plan" else "3D"))
        p = C.save_fig(fig, "atlas_%s.png" % op, OUT)
        b64 = base64.b64encode(p.read_bytes()).decode()
        figs.append((op, label, desc,
                     '<figure><img src="data:image/png;base64,%s"><figcaption>%s — %s</figcaption></figure>' % (b64, op, desc)))
    blocks = "".join("<h3><code>%s</code> %s</h3><p>%s</p>%s" % (op, label, desc, img) for op, label, desc, img in figs)
    html = """<!DOCTYPE html><html lang="zh-Hans"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>算子图谱 — power_to_form</title><style>%s</style></head><body>
<div class="nav"><a href="index.html">← 首页</a></div>
<div class="cover"><p class="kick">power_to_form · 算子图谱</p>
<h1>9 个原子动词:权力对城市形态能做什么</h1>
<p class="lead">每个算子单独施加在同一个样本(%s 中心一片)上,看它到底改了什么。<b>权力体制 = 这些动词的配方</b>(见 <code>config/regimes.yaml</code>)。<code>freeze</code> 无视觉变化:把某些 stakeholder(如 state/遗产)标记为冻结,后续算子都跳过——"谁被保护、谁可被改写"本身就是权力。</p></div>
<div class="wrap">%s
<p class="teach"><span class="tag">教什么</span>先认这 9 个动词,再读 4 个体制的配方:开发商=split→slim→densify;政府=weight_height→concentrate;居民自建=infill→level;共享=open_ground→level。改配方 = 造你自己的权力体制。</p>
<footer>power_to_form · 算子图谱 · 教学练习</footer></div></body></html>""" % (R.PF_CSS, name, blocks)
    (OUT).mkdir(parents=True, exist_ok=True)
    (OUT / "atlas.html").write_text(html, encoding="utf-8")
    print("写了 out/atlas.html(%d 个算子)" % len(figs))


if __name__ == "__main__":
    main()
