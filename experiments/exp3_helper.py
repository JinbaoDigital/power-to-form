"""exp3 辅助:每街道列最高10栋+最大5栋的 级联标签+质心坐标(WGS84),供地图比对。"""
import sys
from pathlib import Path
import geopandas as gpd
HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"
for slug in ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]:
    g = gpd.read_parquet(ENGINE / "data" / slug / "buildings.parquet").to_crs(32651)
    g["lon"] = g.geometry.centroid.to_crs(4326).x.round(5)
    g["lat"] = g.geometry.centroid.to_crs(4326).y.round(5)
    g["area"] = g.geometry.area.round(0)
    print(f"\n===== {slug} — 最高 10 栋 =====")
    print(g.nlargest(10, "height_m")[["bid","height_m","area","stakeholder","lon","lat"]].to_string(index=False))
    print(f"----- {slug} — 最大 footprint 5 栋 -----")
    print(g.nlargest(5, "area")[["bid","height_m","area","stakeholder","lon","lat"]].to_string(index=False))
