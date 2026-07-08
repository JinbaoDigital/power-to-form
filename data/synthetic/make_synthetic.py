"""
make_synthetic.py — generate a tiny SYNTHETIC district cache so the engine can run end-to-end
without any licensed data. NOT real Shanghai data; heights are drawn continuously on purpose
(unlike the quantised Baidu source) so every part of the pipeline exercises cleanly.
Writes:  data/synthetic/demo/buildings.parquet  +  data/synthetic/demo/site.yaml
"""
from pathlib import Path
import numpy as np
import geopandas as gpd
import yaml
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
UTM = 32651


def make(seed=7, n=80, outdir=HERE / "demo"):
    rng = np.random.default_rng(seed)
    x0, y0 = 350000.0, 3450000.0      # arbitrary UTM origin (near Shanghai zone 51N)
    span = 900.0
    geoms, hts, shs, eu, fn = [], [], [], [], []
    shares = {"resident": 0.65, "developer": 0.2, "state": 0.12, "unknown": 0.03}
    eul = {"resident": "101", "developer": "201", "state": "501", "unknown": ""}
    fnl = {"resident": "residence", "developer": "office", "state": "public service", "unknown": ""}
    for _ in range(n):
        cx = x0 + rng.uniform(0, span); cy = y0 + rng.uniform(0, span)
        w = rng.uniform(8, 40); d = rng.uniform(8, 40)
        geoms.append(Polygon([(cx, cy), (cx + w, cy), (cx + w, cy + d), (cx, cy + d)]))
        sh = rng.choice(list(shares), p=list(shares.values())); shs.append(sh)
        # continuous heights (lognormal), taller for developer — NOT storey-quantised
        base = {"developer": 3.2, "state": 2.9, "resident": 2.6, "unknown": 2.7}[sh]
        hts.append(float(np.clip(np.exp(rng.normal(base, 0.5)), 3, 300)))
        eu.append(eul[sh]); fn.append(fnl[sh])
    g = gpd.GeoDataFrame({
        "bid": range(n), "height_m": hts, "area_src": [gg.area for gg in geoms],
        "geometry": geoms, "euluc": eu, "function": fn, "age": [None] * n,
        "aoi_type1": [None] * n, "aoi_type2": [None] * n, "aoi_type": [None] * n,
        "stakeholder": shs, "height_source": ["synthetic"] * n,
    }, geometry="geometry", crs=UTM)
    g["area_m2"] = g.geometry.area
    outdir.mkdir(parents=True, exist_ok=True)
    g.to_parquet(outdir / "buildings.parquet")
    bounds = g.to_crs(4326).total_bounds
    yaml.safe_dump({"name": "Synthetic demo district", "slug": "demo",
                    "area_km2": float(span * span / 1e6), "n": int(n),
                    "bounds_lonlat": [float(b) for b in bounds]},
                   open(outdir / "site.yaml", "w", encoding="utf-8"), allow_unicode=True)
    return outdir


if __name__ == "__main__":
    p = make()
    print("wrote synthetic demo cache ->", p)
