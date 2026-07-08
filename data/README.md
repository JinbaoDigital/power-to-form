# Data — how to obtain the source dataset and rebuild the caches

This repository ships **no raw building geometry** (license). To reproduce the pipeline end to end you
need the compiled Shanghai urban dataset (`上海城市数据集`), then rebuild the five district caches.

## Sources (full provenance in `../paper/DATA_SOURCES.md`)

| Layer | Provider | Access |
|---|---|---|
| Building footprints + height (`①百度/第二版本`) | Baidu Maps Open Platform | https://lbsyun.baidu.com (bulk redistribution restricted) |
| Land use — EULUC-China 2.0 (2022) | Li et al. (2025), Zenodo | https://doi.org/10.5281/zenodo.15180905 · shapefile build https://doi.org/10.5281/zenodo.16794007 (CC BY 4.0) |
| Sub-district (jiedao) boundaries | Tianditu / NGCC | GS(2024)0650, https://cloudcenter.tianditu.gov.cn |
| Building function/year (beta 内测版), AOI | Baidu Maps API | https://lbsyun.baidu.com |
| OSM (Appendix B audits) | OpenStreetMap contributors (ODbL) | Overpass API |

EULUC-China 2.0 and OSM are openly available. The Baidu building/AOI layers and the compiled package
are governed by their providers' terms; obtain them from the provider or the dataset compiler.

## Rebuild the caches

1. Place the source dataset so `engine/pf_common.py` can find it. By default it expects
   `../data_collection/上海城市数据集/`; either match that layout or edit the `SRC`/`AI`/`EU`/`FN`/`AOI`/`JD`
   paths at the top of `engine/pf_common.py`. The building layer is
   `01-建筑轮廓/①百度/第二版本/上海市_百度建筑.shp`.

2. Build the five district caches (writes `engine/data/<slug>/buildings.parquet`):

   ```bash
   cd engine
   python -c "import pf_common as C; \
     [C.build_cache(n,s) for n,s in {'曹杨新村街道':'caoyang','打浦桥街道':'dapuqiao', \
      '老西门街道':'laoximen','陆家嘴街道':'lujiazui','豫园街道':'yuyuan'}.items()]"
   ```

   `build_cache` clips the Baidu footprints to each jiedao polygon, drops non-positive and >632 m
   height outliers, and joins EULUC / function / AOI for the stakeholder cascade.

3. Recompute the frozen results and rerun the experiments:

   ```bash
   cd engine && python recompute_baidu_metrics.py lujiazui   # (repeat per slug) -> results JSON
   cd ../experiments && for e in 1 5 6 8 9; do python exp${e}_*.py; done
   # exp2 (30-90 min) and exp7 (1-2 h) are heavy; exp10/exp10b fetch OSM via Overpass (network).
   ```

Without the licensed data you can still (a) run `python ../reproduce.py --demo` on synthetic data and
(b) verify the shipped results with `python ../reproduce.py --verify`.

## Note on heights

The Baidu height attribute is quantised to ~6 m (storey multiples). This is why the height-distribution
(dip) analysis is **withdrawn** (see `../paper/DATA_SOURCES.md` §9). If you substitute a continuous
per-building height source, the distribution-shape analysis (former §5.4) becomes identifiable again.
