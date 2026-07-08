"""exp4 — 人工分层抽验图卡(信度协议第4步)。
make:每街道分层抽样(默认每类15栋,不足取全),出图卡 PNG(卫星裁片+高亮footprint+形态属性,
      不显示标签)+ rater 评分表 CSV ×2 + 密封答案 CSV。
score:两位评审填完 rater CSV 后,算评审员间 kappa + 各自与级联的一致率。
跑:python3 exp4_audit_sheets.py make
    python3 exp4_audit_sheets.py score
"""
import sys, json, random
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
DATA = HERE.parent / "data"
OUT = HERE / "out" / "audit"; OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ENGINE))
import pf_common as C

SITES = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
PER_CLASS = 15
CLASSES = ["state", "developer", "resident", "unknown"]

def kappa(a, b):
    cats = sorted(set(a) | set(b)); n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((list(a).count(c)/n) * (list(b).count(c)/n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")

def make():
    rng = random.Random(42)
    key_rows = []
    cid = 0
    for slug in SITES:
        g = gpd.read_parquet(ENGINE / "data" / slug / "buildings.parquet").to_crs(32651)
        sat = np.asarray(Image.open(DATA / "sat" / f"{slug}.jpg"))
        ext = json.load(open(DATA / "sat" / f"{slug}.json"))
        Hh, Ww = sat.shape[:2]; x0, y0, x1, y1 = ext
        px = lambda x: (x - x0) / (x1 - x0) * Ww
        py = lambda y: (y1 - y) / (y1 - y0) * Hh
        for cls in CLASSES:
            sub = g[g["stakeholder"] == cls]
            take = sub.sample(min(PER_CLASS, len(sub)), random_state=rng.randint(0, 9999))
            for _, r in take.iterrows():
                cid += 1
                c = r.geometry.centroid
                R = 140                                    # 米,裁片半径
                fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=120)
                ax.imshow(sat, extent=(x0, x1, y0, y1), origin="upper")
                xs, ys = r.geometry.exterior.xy if r.geometry.geom_type == "Polygon" else (None, None)
                if xs is not None:
                    ax.plot(xs, ys, color="#ff2d2d", lw=1.6)
                ax.set_xlim(c.x - R, c.x + R); ax.set_ylim(c.y - R, c.y + R)
                ax.set_title(f"#{cid:03d}  {slug}   area {r.geometry.area:.0f} m² · h {r['height_m']:.0f} m",
                             fontsize=9)
                ax.axis("off")
                fig.savefig(OUT / f"card_{cid:03d}.png", bbox_inches="tight")
                plt.close(fig)
                key_rows.append({"card": cid, "district": slug, "bid": int(r["bid"]),
                                 "cascade_label": cls})
        print(slug, "done")
    key = pd.DataFrame(key_rows)
    key.to_csv(OUT / "ANSWER_KEY_do_not_open.csv", index=False)
    blank = key[["card", "district"]].copy()
    blank["your_label(state/developer/resident/unknown)"] = ""
    blank.to_csv(OUT / "rater_A.csv", index=False)
    blank.to_csv(OUT / "rater_B.csv", index=False)
    print(f"图卡 {len(key)} 张 → out/audit/;评审填 rater_A/B.csv(别看 ANSWER_KEY)")

def score():
    key = pd.read_csv(OUT / "ANSWER_KEY_do_not_open.csv")
    col = "your_label(state/developer/resident/unknown)"
    A = pd.read_csv(OUT / "rater_A.csv")[col].str.strip().tolist()
    B = pd.read_csv(OUT / "rater_B.csv")[col].str.strip().tolist()
    G = key["cascade_label"].tolist()
    print(f"评审员间一致率 {sum(a==b for a,b in zip(A,B))/len(A)*100:.1f}%  κ={kappa(A,B):.3f}")
    for name, R in [("A", A), ("B", B)]:
        print(f"评审{name} vs 级联:一致率 {sum(r==g for r,g in zip(R,G))/len(G)*100:.1f}%  κ={kappa(R,G):.3f}")

if __name__ == "__main__":
    (score if "score" in sys.argv else make)()
