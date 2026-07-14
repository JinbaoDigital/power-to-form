# FoAR figures — data lineage (provenance)

Complete lineage of every dataset behind the FoAR figures (F1–F6, E1–E3). This is the
authoritative per-figure data record; it reconciles with, and does not replace,
[`FoAR/paper/dataset_provenance.md`](../../../paper/dataset_provenance.md) (the manuscript-level
provenance) and `data_collection/DATA_SOURCES.md` (§9, the 2026-07-08 source decision).

**Zero AI inference.** No stakeholder identity is guessed from morphology. `informal` carries no
signal in this data and is held empty by construction. Every column the figures read is computed
by `pf_common` / `cake` / `measure`; nothing is invented.

---

## 1. Raw sources → the per-site cache

All raw layers are the third-party compilation **上海城市数据集** (`data_collection/上海城市数据集/`,
~61 GB, commercially licensed, **NOT redistributed** with the code). All layers are EPSG:4326;
metric work is done in **EPSG:32651 (UTM 51N)**. Exact shapefile paths as bound in `pf_common.py`:

| Role in the pipeline | File (under `上海城市数据集/`) | Source / licence | Notes |
|----|----|----|----|
| **Site boundary** (jiedao polygon = the extent of each case) | `03-行政区/2其他/乡镇街道/上海市_乡镇边界.shp` | Tianditu / NGCC, **GS(2024)0650** | non-square, variable-size street polygons |
| **Building footprint + height** | `01-建筑轮廓/①百度/第二版本/上海市_百度建筑.shp` | **Baidu Maps building layer, v2** (~873k citywide; 5,448 across the five districts) | height is a **vendor attribute quantised to ~6 m storey multiples, not surveyed**. Selected as the footprint and height source on **2026-07-08** (project decision; DATA_SOURCES §9). |
| **Land use** (discrete primary key of the cascade) | `09-开源土地利用/09-开源土地利用/开源建设用地分类/Data/上海市-开源建设用地.shp` | **EULUC-China 2.0** (2022; Li et al. 2025). Zenodo **10.5281/zenodo.15180905**; shapefile build v3 **10.5281/zenodo.16794007**; **CC BY 4.0** | Gong et al. 2020 demoted to lineage. 90–95 % coverage → unknown 1–6 %. |
| **Function / build-year layer** | `01-建筑轮廓/③其它/上海市_建筑-带年份-内测版.shp` | **beta 内测版** | build-year **right-censored at ≥1984**; feeds `cake`'s age term (E1–E3 physical block; `age_layer_stats.csv`) |
| **AOI** (last cascade fallback) | `02-POI&AOI/2-AOI/AOI-baiduapi/SHP/上海市_AOI.shp` | **Baidu Maps API** | price/structure used only as a discrete tag; raw values never emitted |
| **Satellite basemap** (viewer ground only) | Esri **World Imagery** | figures only, **no tile redistribution** | ground plane under the Three.js viewers → `shot_*.png` |
| **OSM audits** (cross-checks, not a figure input) | Overpass, **2026-07-08** | **ODbL** | context/validation only |

**Cascade (stakeholder assignment)** — `config/stakeholder_lookup.yaml`, applied in
`pf_common.assign_stakeholder`: **EULUC land-use → Function → AOI**, first hit wins,
**one building = one stakeholder** ∈ `{state, developer, resident, informal, unknown}`.
This is a *declared reading of the land-use column*, not a property of geometry — the whole point
E1/E2 visualise. EULUC separates `行政办公 501 → state` from `商务办公 201 → developer` at the
category level, which OSM tags cannot.

**Cache product:** `pf_common.build_cache` clips the Baidu footprints to each jiedao polygon,
joins EULUC / Function / AOI, runs the cascade, and writes one file per site:

```
FoAR/engine/data/<slug>/buildings.parquet   (8 sites, ~1.7 MB total, EPSG:32651)
FoAR/engine/data/<slug>/site.yaml           (name, area, n)
```

Rebuilding the cache requires the raw 上海城市数据集. **The figures need only the parquet cache**,
which is committed — so the figures are reproducible without the licensed raw data.

## 2. Cache → run artefacts → figures

`data/<slug>/buildings.parquet` is consumed by the cake engine to produce the on-disk artefacts
the figure scripts read (see `RUNBOOK.md §2` for the DAG and `MANIFEST.json` for hashes):

- `run_cake_all.py` → `out/cake/metrics_cake_all.json` (fingerprints, shares, scenario headlines
  for 8 sites × current+5 scenarios × modes A/B), `reachable_<slug>.json` (5×5 target grid),
  `ledger_<slug>_<key>.csv`, `skyline_<slug>.json`.
- `aux_csv_nr10.py` → `rule_comparison.csv`, `weakness_dist.csv`, `gamma_bind.csv`,
  `age_layer_stats.csv` (traceability; checked against the frozen `invariance.csv`).
- `cake_viewers.py` → `out/cake_figs/shot_*.png` (80 = 8 sites × 5 configs × 2 views), rendered
  headless with SwiftShader software WebGL (GPU-independent, reproducible).

The **eight case studies** and their families (from `figs_nr10.py`):
`lujiazui, nanjingxi` = capital / high-rise CBD · `caoyang, pengpu` = danwei workers' village ·
`laoximen, yuyuan, dapuqiao` = old-town lilong · `zhangjiang` = industry / tech new town.
The **frozen five** (regression baseline, deviation 0.0): `lujiazui, caoyang, laoximen, dapuqiao, yuyuan`.

## 3. Honest boundaries (carried from the source READMEs)

- **Baidu heights are quantised to ~6 m storeys**, not surveyed → any height-*distribution* claim
  (dip/bimodality) is not identifiable and was **withdrawn** from the manuscript (former Table 3 /
  Fig. 10). The figures here use height as a level, not as a distribution shape, and stand.
- **EULUC is parcel-level and outranks building-level Function**: stray civic buildings inside a
  residential parcel are folded into `resident`.
- **danwei is invisible**: workers' villages were state/work-unit built, but land use = residential
  → counted `resident`; only the morphology remembers the work-unit origin.
- **`informal` has no signal in this data → always empty** (never guessed from form).
- AOI price/structure is a discrete tag only; "whose right" is a forward teaching read, not a title search.
- Release policy: **derived metrics + code only**; the strictest upstream licence governs.

## 4. Citations (short form; full form in `FoAR/paper/dataset_provenance.md` + manuscript refs)

- EULUC-China 2.0 — Li et al. (2025); Zenodo 10.5281/zenodo.15180905, build v3 10.5281/zenodo.16794007 (CC BY 4.0); lineage: Gong et al. (2020).
- Building stock & AOI — Baidu Maps (footprint layer v2; AOI API), redistributed in 上海城市数据集.
- Boundaries — Tianditu / NGCC, GS(2024)0650.
- Basemap — Esri World Imagery (display only).
- OSM — © OpenStreetMap contributors, ODbL (Overpass 2026-07-08).
