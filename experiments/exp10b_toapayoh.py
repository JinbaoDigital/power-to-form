# -*- coding: utf-8 -*-
"""exp10b — 大巴窑(Toa Payoh)OSM 复审:试点场地的 2026 实测重跑(附录 B.1)。
与 exp10 同一 tag 查表(试点风格,含 informal)。边界:OSM Toa Payoh 行政区 area;
失败则退回 bbox (1.3220,103.8330,1.3480,103.8650)。
跑:python3 exp10b_toapayoh.py fetch → assemble
产出:out/exp10_toapayoh.csv/.md + out/osm_raw/toapayoh.json
"""
import sys, json, time, urllib.request, urllib.parse
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"; CKPT = OUT / "osm_raw"; CKPT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))
from exp10_osm_audit import classify, has_height  # 同一查表

MIRRORS = ["https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]

Q_AREA = ('[out:json][timeout:25];area["name"="Toa Payoh"]["boundary"="administrative"]->.a;'
          '(way["building"](area.a);relation["building"](area.a););out tags;')
Q_BBOX = ('[out:json][timeout:25];(way["building"](1.3220,103.8330,1.3480,103.8650);'
          'relation["building"](1.3220,103.8330,1.3480,103.8650););out tags;')

def fetch():
    for q, label in ((Q_AREA, "area"), (Q_BBOX, "bbox")):
        for attempt in range(2):
            url = MIRRORS[attempt % len(MIRRORS)]
            try:
                req = urllib.request.Request(url,
                    data=urllib.parse.urlencode({"data": q}).encode(),
                    headers={"User-Agent": "FoAR-research/1.0 (academic; jinbao@arch.nycu.edu.tw)",
                             "Content-Type": "application/x-www-form-urlencoded"})
                els = json.loads(urllib.request.urlopen(req, timeout=18).read())["elements"]
                if els:
                    json.dump({"boundary": label, "elements": els}, open(CKPT / "toapayoh.json", "w"))
                    print(f"toapayoh fetched ({label})", len(els)); return
            except Exception as e:
                print(f"  retry ({label}/{url.split('/')[2]}): {type(e).__name__}", flush=True)
                time.sleep(2)
    raise RuntimeError("all attempts failed")

def assemble():
    d = json.load(open(CKPT / "toapayoh.json"))
    tags = [e.get("tags", {}) for e in d["elements"]]
    n = len(tags)
    cls = [classify(t) for t in tags]
    shares = {c: round(cls.count(c) / n * 100, 1) for c in ("state", "developer", "resident", "informal", "unknown")}
    row = {"site": "toapayoh_2026", "boundary": d["boundary"], "n_osm": n,
           "height_signal_pct": round(sum(has_height(t) for t in tags) / n * 100, 1),
           "classifiable_pct": round(sum(c != "unknown" for c in cls) / n * 100, 1),
           **{f"share_{k}": v for k, v in shares.items}} if False else {
           "site": "toapayoh_2026", "boundary": d["boundary"], "n_osm": n,
           "height_signal_pct": round(sum(has_height(t) for t in tags) / n * 100, 1),
           "classifiable_pct": round(sum(c != "unknown" for c in cls) / n * 100, 1),
           "share_state": shares["state"], "share_developer": shares["developer"],
           "share_resident": shares["resident"], "share_informal": shares["informal"],
           "share_unknown": shares["unknown"]}
    df = pd.DataFrame([row])
    df.to_csv(OUT / "exp10_toapayoh.csv", index=False)
    md = ["# exp10b Toa Payoh 2026 复审\n", df.to_markdown(index=False), "",
          "试点存档值(as run):n=1,163;unknown 36%;informal 3%;高度多缺失/层数估算。",
          f"复审:Overpass API,{time.strftime('%Y-%m-%d')};边界={d['boundary']}。"]
    (OUT / "exp10_toapayoh.md").write_text("\n".join(md), encoding="utf-8")
    print(df.to_string(index=False))

if __name__ == "__main__":
    fetch() if sys.argv[1] == "fetch" else assemble()
