# -*- coding: utf-8 -*-
"""exp10 — OSM 充分性审计:同样五个街道,OSM 能支撑本文法吗?(附录 B 素材)
对每个街道:Overpass 拉取 building 要素(街道多边形内),统计
  n_osm            OSM footprint 数(way+relation)
  height_pct       有可用高度信号(height 或 building:levels)的比例
  class_pct        经 Toa-Payoh 式 tag 查表可判 stakeholder 的比例
并与本文数据集(engine/data 缓存 + exp1)对比:n_ds、高度=100%(实测)、unknown 2–6%。
跑:python3 exp10_osm_audit.py <slug>   (逐街道,礼貌限速)  → 全部跑完后 assemble
产出:out/exp10_osm_audit.csv/.md
注意:边界用 03-行政区 乡镇边界(非 AI 数据);OSM 数据来自 Overpass API,可复现。
"""
import sys, json, time, urllib.request, urllib.parse
from pathlib import Path
import pandas as pd
import geopandas as gpd
import yaml

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
CKPT = OUT / "osm_raw"; CKPT.mkdir(exist_ok=True)
JD = HERE.parent.parent / "data_collection" / "上海城市数据集" / "03-行政区" / "2其他" / "乡镇街道" / "上海市_乡镇边界.shp"

SITES = {"lujiazui": "陆家嘴街道", "caoyang": "曹杨新村街道", "laoximen": "老西门街道",
         "dapuqiao": "打浦桥街道", "yuyuan": "豫园街道"}

# Toa-Payoh 式 tag→stakeholder 查表(顺序敏感;与 §3.1 试点同精神)
def classify(tags):
    b = tags.get("building", "")
    if tags.get("amenity") in ("school", "university", "college", "hospital", "clinic",
                               "townhall", "police", "fire_station", "library", "community_centre",
                               "place_of_worship", "kindergarten") or \
       b in ("school", "university", "hospital", "civic", "government", "public", "train_station", "transportation"):
        return "state"
    if tags.get("office") or tags.get("shop") or b in ("commercial", "office", "retail", "hotel",
                                                       "industrial", "warehouse", "supermarket"):
        return "developer"
    if b in ("residential", "apartments", "house", "dormitory", "terrace", "semidetached_house", "detached"):
        return "resident"
    if b in ("garage", "garages", "shed", "hut", "construction", "roof"):
        return "informal"
    return "unknown"

def has_height(tags):
    return ("height" in tags) or ("building:levels" in tags)

def fetch(slug):
    jd = gpd.read_file(JD)
    poly = jd[jd["name"].str.contains(SITES[slug].replace("街道", ""))].geometry.iloc[0]
    simp = poly.simplify(0.0008)
    if simp.geom_type == "MultiPolygon":
        simp = max(simp.geoms, key=lambda g: g.area)
    coords = " ".join(f"{y:.5f} {x:.5f}" for x, y in simp.exterior.coords)
    q = f'[out:json][timeout:25];(way["building"](poly:"{coords}");relation["building"](poly:"{coords}"););out tags;'
    MIRRORS = ["https://overpass-api.de/api/interpreter",
               "https://overpass.kumi.systems/api/interpreter",
               "https://overpass.private.coffee/api/interpreter"]
    els = None
    for attempt in range(2):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            req = urllib.request.Request(url,
                data=urllib.parse.urlencode({"data": q}).encode(),
                headers={"User-Agent": "FoAR-research/1.0 (academic; jinbao@arch.nycu.edu.tw)",
                         "Content-Type": "application/x-www-form-urlencoded"})
            r = urllib.request.urlopen(req, timeout=18)
            els = json.loads(r.read())["elements"]
            break
        except Exception as e:
            print(f"  retry ({url.split('/')[2]}): {type(e).__name__}", flush=True)
            time.sleep(2)
    if els is None:
        raise RuntimeError(f"all mirrors failed for {slug}")
    json.dump(els, open(CKPT / f"{slug}.json", "w"))
    print(slug, "fetched", len(els))

def assemble():
    d1 = pd.read_csv(OUT / "exp1_cascade_depth.csv").set_index("district")
    rows = []
    for slug in SITES:
        els = json.load(open(CKPT / f"{slug}.json"))
        tags = [e.get("tags", {}) for e in els]
        n = len(tags)
        meta = yaml.safe_load(open(ENGINE / "data" / slug / "site.yaml", encoding="utf-8"))
        cls = [classify(t) for t in tags]
        rows.append({
            "district": slug,
            "n_osm": n,
            "n_dataset": meta["n"],
            "osm_coverage_pct": round(n / meta["n"] * 100, 1),
            "osm_height_signal_pct": round(sum(has_height(t) for t in tags) / n * 100, 1) if n else 0.0,
            "osm_classifiable_pct": round(sum(c != "unknown" for c in cls) / n * 100, 1) if n else 0.0,
            "osm_unknown_pct": round(sum(c == "unknown" for c in cls) / n * 100, 1) if n else 100.0,
            "dataset_height_pct": 100.0,
            "dataset_unknown_pct": d1.loc[slug, "unknown"],
        })
        print(slug, rows[-1])
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "exp10_osm_audit.csv", index=False)
    md = ["# exp10 OSM \u5145\u5206\u6027\u5ba1\u8ba1 \u2014 \u6458\u8981\uff08\u9644\u5f55 B\uff09\n",
          df.to_markdown(index=False), "",
          "\u8bfb\u6cd5\uff1a\u4e09\u4e2a\u95e8\u69db\u4efb\u4f55\u4e00\u4e2a\u4e0d\u8fc7\uff0c\u672c\u6587\u6cd5\u5c31\u8dd1\u4e0d\u8d77\u6765\u2014\u2014",
          "\uff081\uff09footprint \u8986\u76d6\uff08OSM/\u6570\u636e\u96c6\uff09\uff1b\uff082\uff09\u9ad8\u5ea6\u4fe1\u53f7\uff08\u5b88\u6052\u7b97\u672f\u7684\u8d27\u5e01\uff09\uff1b\uff083\uff09\u53ef\u5224 stakeholder \u6bd4\u4f8b\u3002",
          "OSM \u6293\u53d6\u65f6\u95f4\uff1a" + time.strftime("%Y-%m-%d") + "\uff1bOverpass API\uff1b\u8fb9\u754c=\u4e61\u9547\u8857\u9053\u591a\u8fb9\u5f62\uff08\u7b80\u5316 0.0008\u00b0\uff09\u3002"]
    (OUT / "exp10_osm_audit.md").write_text("\n".join(md), encoding="utf-8")
    print("done -> out/exp10_osm_audit.*")

if __name__ == "__main__":
    a = sys.argv[1]
    assemble() if a == "assemble" else fetch(a)
