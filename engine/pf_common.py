"""
pf_common.py — power_to_form 的契约层(数据接入 + 离散权利 + 通用工具)
=================================================================
这是「可教框架」的地基。整条教学流水线 7 步:
  1 选地   subdistrict(name)         街道多边形(非方形、变大小)
  2 裁切   build_cache / load_buildings  百度建筑高度 footprint 裁到街道
  3 权利   assign_all(级联查表)        一栋 = 一个 stakeholder(EULUC→Function→AOI)
  4 配方   regimes.yaml               选一个权力体制(= 原子算子的配方)   ← operators.py
  5 施加   apply_regime               按序施加算子 → 新形态               ← operators.py
  6 量测   measure.py                 FAR/覆盖/CV/重心集中度/瘦长/细粒
  7 出图   render.py                  平面 / 3D / 互动 HTML

本层负责 1–3 + 通用工具(颜色、挤体、绘图)。零 AI、零语意转换;informal 无信号、恒空。
数据:../data_collection/上海城市数据集/(全 EPSG:4326,度量用 32651)。
"""
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import yaml
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import triangulate
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
for _f in ("Arial Unicode MS", "PingFang SC", "Heiti TC", "Hiragino Sans GB"):
    try:
        matplotlib.rcParams["font.sans-serif"] = [_f]; matplotlib.rcParams["axes.unicode_minus"] = False; break
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "data_collection" / "上海城市数据集"
JD = SRC / "03-行政区" / "2其他" / "乡镇街道" / "上海市_乡镇边界.shp"
AI = SRC / "01-建筑轮廓" / "①百度" / "第二版本" / "上海市_百度建筑.shp"  # Baidu Maps building footprints v2, with per-building height (project decision 2026-07-08)
EU = SRC / "09-开源土地利用" / "09-开源土地利用" / "开源建设用地分类" / "Data" / "上海市-开源建设用地.shp"
FN = SRC / "01-建筑轮廓" / "③其它" / "上海市_建筑-带年份-内测版.shp"
AOI = SRC / "02-POI&AOI" / "2-AOI" / "AOI-baiduapi" / "SHP" / "上海市_AOI.shp"
CONFIG = ROOT / "config"
LOOKUP_PATH = CONFIG / "stakeholder_lookup.yaml"
DATA = ROOT / "data"
OUT = ROOT / "out"
UTM = 32651
FLOOR_H = 3.5

STAKEHOLDERS = ["state", "developer", "resident", "informal", "unknown"]
SH_LABEL = {"state": "政府/公共", "developer": "开发商/资本", "resident": "居民",
            "informal": "非正式(本数据无信号)", "unknown": "未标"}
SH_COLOR = {"state": "#4a6fa5", "developer": "#c0654a", "resident": "#5a9367",
            "informal": "#c2a23c", "unknown": "#b8b8b8"}


# --------------------------------------------------------- 3 离散权利(级联查表)
def load_lookup(path=LOOKUP_PATH):
    return yaml.safe_load(open(path, encoding="utf-8"))


def _t(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "") else s


def assign_stakeholder(row, lk):
    for src in lk["cascade"]:
        if src == "euluc":
            m = lk["euluc"].get(_t(row.get("euluc")))
            if m:
                return m
        elif src == "function":
            m = lk["function"].get(_t(row.get("function")))
            if m and m != "unknown":
                return m
        elif src == "aoi":
            for field in ("aoi_type2", "aoi_type1", "aoi_type"):
                v = _t(row.get(field))
                if v:
                    for kw, sh in lk["aoi_contains"].items():
                        if kw in v:
                            return sh
    return lk.get("default", "unknown")


def assign_all(df, lookup=None):
    lookup = lookup or load_lookup()
    df = df.copy()
    df["stakeholder"] = df.apply(lambda r: assign_stakeholder(r, lookup), axis=1)
    return df


# --------------------------------------------------------- 1+2 选地 + 裁切 + 多源 join
def subdistrict(name):
    jd = gpd.read_file(JD)
    row = jd[jd["name"].fillna("") == name]
    if len(row) == 0:
        row = jd[jd["name"].fillna("").str.contains(name)]
    if len(row) == 0:
        raise ValueError("找不到街道:%s" % name)
    row = row.iloc[[0]].to_crs(4326)
    return row, row.geometry.iloc[0]


def _join(cent, path, bb, cols_map):
    try:
        src = gpd.read_file(path, bbox=bb)
    except Exception:
        return pd.DataFrame({"bid": []})
    have = {k: v for k, v in cols_map.items() if k in src.columns}
    if not have:
        return pd.DataFrame({"bid": []})
    src = src[list(have) + ["geometry"]].rename(columns=have)
    src = src[src.geometry.notna()]
    j = gpd.sjoin(cent[["bid", "geometry"]], src.to_crs(4326), predicate="within", how="left")
    j = j.dropna(subset=list(have.values()), how="all").drop_duplicates("bid")
    return j[["bid"] + list(have.values())]


def build_cache(name, slug):
    """街道多边形裁 AI-带高度 footprint + 多源 join → data/<slug>/buildings.parquet(几何 32651)。"""
    row, poly = subdistrict(name)
    bb = poly.bounds
    area_km2 = float(row.to_crs(UTM).area.iloc[0] / 1e6)
    ai = gpd.read_file(AI, bbox=bb)
    ai = gpd.clip(ai, poly)
    ai = ai[ai.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    ai = ai.rename(columns={"Height": "height_m", "height": "height_m", "Area": "area_src", "area": "area_src"})
    ai["height_m"] = pd.to_numeric(ai["height_m"], errors="coerce")
    # Baidu heights: drop non-positive and gross outliers (>632 m = above Shanghai Tower are errors, e.g. 762 m)
    ai = ai[(ai["height_m"] > 0) & (ai["height_m"] <= 632)].reset_index(drop=True)
    ai["bid"] = range(len(ai))
    ai = ai.set_crs(4326, allow_override=True)
    cent = ai[["bid", "geometry"]].copy()
    cent["geometry"] = ai.geometry.representative_point()
    cent = gpd.GeoDataFrame(cent, geometry="geometry", crs=4326)
    eu = _join(cent, EU, bb, {"class2": "euluc"})
    fn = _join(cent, FN, bb, {"Function": "function", "Age": "age"})
    aoi = _join(cent, AOI, bb, {"type1": "aoi_type1", "type2": "aoi_type2", "type": "aoi_type",
                                "结构": "aoi_struct", "价格": "aoi_price", "时间": "aoi_year"})
    out = ai.drop(columns=[c for c in ai.columns if c not in ("bid", "height_m", "area_src", "geometry")])
    for part in (eu, fn, aoi):
        if len(part):
            out = out.merge(part, on="bid", how="left")
    out = gpd.GeoDataFrame(out, geometry="geometry", crs=4326).to_crs(UTM)
    out["area_m2"] = out.geometry.area
    out["height_source"] = "baidu_v2"
    out = assign_all(out)
    d = DATA / slug
    d.mkdir(parents=True, exist_ok=True)
    out.to_parquet(d / "buildings.parquet")
    yaml.safe_dump({"name": name, "slug": slug, "area_km2": area_km2, "n": len(out),
                    "bounds_lonlat": list(poly.bounds)},
                   open(d / "site.yaml", "w", encoding="utf-8"), allow_unicode=True)
    return out


def load_buildings(slug):
    """读缓存 → records 列表(operators 与 cake.py 的共同工作单位)。几何 32651。

    附加字段(cake.py 的分蛋糕模型需要;对旧的 operators/measure 惰性,只多几个 key,
    几何/高度/stakeholder 一字不动,故 metrics_baidu_5districts.json 不受影响,已回归验证):
      bid              缓存内稳定编号(动迁账清单用)
      orig_h, orig_sh  冻结的初始高度与初始持有者(算动迁必须用初始值)
      age              建造/登记年,右删失于 1984,覆盖 48-66%,缺失为 None
      euluc            EULUC-China 2.0 用地类(FAR 门槛查表)
      area             footprint 面积 m^2(cake 模型里 footprint 永久冻结)
    """
    gdf = gpd.read_parquet(DATA / slug / "buildings.parquet")
    if "stakeholder" not in gdf.columns:
        gdf = assign_all(gdf)
    has = set(gdf.columns)
    recs = []
    for i, (_, r) in enumerate(gdf.iterrows()):
        h = float(r["height_m"])
        age = None
        if "age" in has:
            try:
                a = float(r["age"])
                age = int(a) if a == a and a > 0 else None
            except (TypeError, ValueError):
                age = None
        eu = r["euluc"] if "euluc" in has else None
        recs.append({"geom": r.geometry, "h": h, "sh": r["stakeholder"], "frozen": False,
                     "bid": int(r["bid"]) if "bid" in has else i,
                     "orig_h": h, "orig_sh": r["stakeholder"], "age": age,
                     "euluc": eu if isinstance(eu, str) else None,
                     "area": float(r["area_m2"]) if "area_m2" in has else float(r.geometry.area)})
    return recs


def site_meta(slug):
    return yaml.safe_load(open(DATA / slug / "site.yaml", encoding="utf-8"))


# --------------------------------------------------------- 通用工具
def _polys(geom):
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return []


def gfa(recs):
    return sum(r["geom"].area * r["h"] for r in recs)


def plot_footprints(ax, recs, color_for, lw=0.12):
    for r in recs:
        col = color_for(r)
        for p in _polys(r["geom"]):
            xs, ys = p.exterior.xy
            ax.fill(xs, ys, facecolor=col, edgecolor="white", linewidth=lw)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])


def save_fig(fig, name, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / name
    fig.savefig(p, dpi=120, bbox_inches="tight"); plt.close(fig)
    return p


def ground_sat(minx, miny, maxx, maxy, cache_png, factor=2.0):
    """抓比 patch 宽 factor× 的真实卫星图(Esri),贴 viewer 地面用 → 体块坐在真实上海上(灭孤岛)。
    返回 (data_uri_jpeg, local_extent[lx0,ly0,lx1,ly1])。local 坐标 = 相对 (minx,miny),与 footprint 同系。"""
    import json as _json, base64, contextily as ctx, pyproj
    from PIL import Image
    cache_png = Path(cache_png); meta_p = cache_png.with_suffix(".json")
    if cache_png.exists() and meta_p.exists():
        ext = _json.load(open(meta_p))
        return "data:image/jpeg;base64," + base64.b64encode(cache_png.read_bytes()).decode(), ext
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    hw, hh = (maxx - minx) / 2 * factor, (maxy - miny) / 2 * factor
    to4326 = pyproj.Transformer.from_crs(UTM, 4326, always_xy=True).transform
    corners = [to4326(cx - hw, cy - hh), to4326(cx + hw, cy - hh), to4326(cx - hw, cy + hh), to4326(cx + hw, cy + hh)]
    lons = [p[0] for p in corners]; lats = [p[1] for p in corners]
    span = max(2 * hw, 2 * hh); zoom = 16 if span < 2500 else (15 if span < 6500 else 14)
    img, ext = ctx.bounds2img(min(lons), min(lats), max(lons), max(lats), ll=True,
                              source=ctx.providers.Esri.WorldImagery, zoom=zoom)
    from3857 = pyproj.Transformer.from_crs(3857, UTM, always_xy=True).transform
    ux0, uy0 = from3857(ext[0], ext[2]); ux1, uy1 = from3857(ext[1], ext[3])
    local = [ux0 - minx, uy0 - miny, ux1 - minx, uy1 - miny]
    arr = img[:, :, :3] if (getattr(img, "ndim", 0) == 3 and img.shape[2] >= 3) else img
    cache_png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(cache_png, "JPEG", quality=82)
    _json.dump(local, open(meta_p, "w"))
    return "data:image/jpeg;base64," + base64.b64encode(cache_png.read_bytes()).decode(), local


def extrude_obj(recs, origin=None):
    polys_all = [p for r in recs for p in _polys(r["geom"])]
    if origin is None:
        minx = min(p.bounds[0] for p in polys_all); miny = min(p.bounds[1] for p in polys_all)
        origin = (minx, miny)
    ox, oy = origin
    V, F = [], []

    def addv(x, y, z):
        V.append((x - ox, y - oy, z)); return len(V)
    for r in recs:
        h = float(r["h"])
        for poly in _polys(r["geom"]):
            ring = list(poly.exterior.coords)
            if len(ring) > 1 and ring[0] == ring[-1]:
                ring = ring[:-1]
            n = len(ring)
            if n < 3:
                continue
            bb = len(V)
            for (x, y) in ring:
                addv(x, y, 0.0)
            bt = len(V)
            for (x, y) in ring:
                addv(x, y, h)
            for i in range(n):
                j = (i + 1) % n
                F.append((bb + i + 1, bb + j + 1, bt + j + 1)); F.append((bb + i + 1, bt + j + 1, bt + i + 1))
            for tri in triangulate(poly):
                if not poly.contains(tri.representative_point()):
                    continue
                tc = list(tri.exterior.coords)[:3]
                a = addv(tc[0][0], tc[0][1], h); b = addv(tc[1][0], tc[1][1], h); c = addv(tc[2][0], tc[2][1], h)
                F.append((a, b, c))
    lines = ["# power_to_form extruded (meters)"]
    for (x, y, z) in V:
        lines.append("v %.3f %.3f %.3f" % (x, y, z))
    for f in F:
        lines.append("f %d %d %d" % f)
    return "\n".join(lines) + "\n", len(V), len(F)
