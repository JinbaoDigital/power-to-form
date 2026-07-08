"""
rebuild_baidu.py — rebuild the 5-district building caches from the Baidu building footprint layer (with height).
Overrides the source paths to absolute locations so it runs regardless of the SRC relative layout.
Usage:  python3 rebuild_baidu.py <slug>   (or no arg = all five)
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pf_common as C
import geopandas as gpd

import os
BASE = Path(os.environ.get("PTF_SRC", C.SRC))  # set PTF_SRC to your 上海城市数据集 path, or match pf_common.SRC
C.SRC = BASE
C.JD  = BASE / "03-行政区" / "2其他" / "乡镇街道" / "上海市_乡镇边界.shp"
C.AI  = BASE / "01-建筑轮廓" / "①百度" / "第二版本" / "上海市_百度建筑.shp"   # Baidu v2 building footprints + height
C.EU  = BASE / "09-开源土地利用" / "09-开源土地利用" / "开源建设用地分类" / "Data" / "上海市-开源建设用地.shp"
C.FN  = BASE / "01-建筑轮廓" / "③其它" / "上海市_建筑-带年份-内测版.shp"
C.AOI = BASE / "02-POI&AOI" / "2-AOI" / "AOI-baiduapi" / "SHP" / "上海市_AOI.shp"

DISTRICTS = {
    "caoyang":  "曹杨新村街道",
    "dapuqiao": "打浦桥街道",
    "laoximen": "老西门街道",
    "lujiazui": "陆家嘴街道",
    "yuyuan":   "豫园街道",
}

def headline(slug):
    g = gpd.read_parquet(C.DATA / slug / "buildings.parquet")
    g = g.copy(); g["gfa"] = g.geometry.area * g["height_m"]
    cnt = g["stakeholder"].value_counts(normalize=True)
    gfa = g.groupby("stakeholder")["gfa"].sum(); gfa = gfa / gfa.sum()
    row = {"n": int(len(g)), "hmed": round(float(g["height_m"].median()), 1)}
    for k in ["state", "developer", "resident", "unknown"]:
        row[f"cnt_{k}"] = round(float(cnt.get(k, 0)), 3)
        row[f"gfa_{k}"] = round(float(gfa.get(k, 0)), 3)
    return row

def main():
    slugs = [sys.argv[1]] if len(sys.argv) > 1 else list(DISTRICTS)
    out = {}
    for slug in slugs:
        C.build_cache(DISTRICTS[slug], slug)
        out[slug] = headline(slug)
        r = out[slug]
        print(f"{slug:9s} n={r['n']:5d} hmed={r['hmed']:5.1f}  "
              f"cnt(s/d/r/u)={r['cnt_state']:.2f}/{r['cnt_developer']:.2f}/{r['cnt_resident']:.2f}/{r['cnt_unknown']:.2f}  "
              f"gfa={r['gfa_state']:.2f}/{r['gfa_developer']:.2f}/{r['gfa_resident']:.2f}/{r['gfa_unknown']:.2f}")
    jp = C.DATA.parent / "_baidu_headline.json"
    old = json.load(open(jp)) if jp.exists() else {}
    old.update(out); json.dump(old, open(jp, "w"), indent=1)

if __name__ == "__main__":
    main()
