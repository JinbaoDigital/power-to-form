# FoAR figures — audit & re-compute runbook

Audit record for the figures of the FoAR *power-to-form* manuscript
(**F1–F6** main, **E1–E3** supplementary), from the **NEXT_RUN_10 ("cake")** run:
8 jiedao × (current + 5 scenarios) × modes A/B.

- **This folder:** `FoAR/engine/audit/foar_figures/` — a record, not a working copy.
- **Engine root (where you run everything):** `FoAR/engine/` = `../../` from here.
- Companion files: [`MANIFEST.json`](MANIFEST.json) (machine-readable figure→script→inputs→output),
  [`PROVENANCE.md`](PROVENANCE.md) (data lineage, sources, licences, DOIs).

> **Why this lives here and not in `power_to_form/`:** `power_to_form/` is the clean,
> teachable framework package (9 operators + regimes-as-recipes + 7-step pipeline); it is
> deliberately paper-agnostic and is **not** a git repo. This figure pipeline is a
> *paper-specific, run-specific* build that lives entirely inside `FoAR/engine/` (its scripts,
> its `out/cake/` + `out/cake_figs/` artefacts, its `data/<slug>/` cache, its verifier) and is
> version-controlled with the manuscript in `FoAR/`. An "audit + re-compute" record belongs
> next to the pipeline it audits and inside the same versioned tree — so it sits in the engine,
> beside `FoAR/paper/dataset_provenance.md`, not in the teaching package. See the report that
> created this folder for the full reasoning.

---

## 0. TL;DR re-compute

```bash
cd FoAR/engine

# (only if out/cake and out/cake_figs are missing — otherwise skip to figures)
python3 run_cake_all.py all      # metrics_cake_all.json, reachable_<slug>.json, ledgers, skylines
python3 aux_csv_nr10.py          # rule_comparison / weakness_dist / gamma_bind / age_layer_stats .csv
python3 cake_viewers.py all      # viewer_<slug>.html + 80 shot_*.png (needs headless chromium)

# the figures (read-only over the artefacts above)
python3 figs_nr10.py all         # F1 F2 F3 F4  -> out/cake_figs/F1..F4*.png
python3 figs_nr10_schematic.py all   # F5 F6      -> out/cake_figs/F5_loop.png, F6_parameters.png
python3 figs_nr10_embed.py all       # E1 E2 E3   -> out/cake_figs/E1..E3*.png (+E_embed_stats.json)

# verify
python3 verify_cake_nr10.py      # 34 checks, exit 0 on all-pass; frozen-five deviation must be 0.0
```

All three figure scripts also accept a single figure token, e.g. `python3 figs_nr10.py f3`.
The figure scripts **only read** files already on disk and **only write** into `out/cake_figs/`;
they never touch `metrics_cake.json`, `invariance.csv` or the frozen-five site outputs.

---

## 1. Figure → script → inputs → output

Paths are relative to the **engine root** (`FoAR/engine/`). `<slug>` ∈
`lujiazui, nanjingxi, caoyang, pengpu, laoximen, yuyuan, dapuqiao, zhangjiang`.
`<cfg>` ∈ `current, developer-led, state-led, resident-led, shared`.

| Fig | Script · fn | Command | Reads | Writes |
|----|----|----|----|----|
| **F1** Site atlas (plan + skyline + 9-axis radar) | `figs_nr10.py · f1()` | `figs_nr10.py f1` | `out/cake/metrics_cake_all.json`; `data/<slug>/buildings.parquet` (×8, figure-ground); `out/cake_figs/shot_sky_<slug>_current.png` (×8) | `out/cake_figs/F1_atlas.png` |
| **F2** Gallery: 8 sites × 5 configs | `figs_nr10.py · f2()` | `figs_nr10.py f2` | `metrics_cake_all.json`; `shot_<slug>_<cfg>.png` + `shot_sky_<slug>_<cfg>.png` (8×5 each) | `F2_gallery.png`, `F2_gallery_skyline.png` |
| **F3** Fingerprints + Spearman rank-preservation | `figs_nr10.py · f3()` | `figs_nr10.py f3` | `metrics_cake_all.json` **only** (Spearman computed in-script) | `F3_fingerprints.png` |
| **F4** Reachability 5×5 grids + cross-case map | `figs_nr10.py · f4()` | `figs_nr10.py f4` | `out/cake/reachable_<slug>.json`; `data/<slug>/buildings.parquet` (true easting); `metrics_cake_all.json`; `shot_sky_<slug>_current.png` | `F4_reachable_{pengpu,zhangjiang,lujiazui}.png`, `F4_reachability_all.png` |
| **F5** Tool loop (read→map→transform→read-back, swappable lens) | `figs_nr10_schematic.py · f5()` | `figs_nr10_schematic.py f5` | `metrics_cake_all.json`; `out/cake/ledger_laoximen_capital_deepen_B.csv`; `data/laoximen/buildings.parquet`; `config/scenarios.yaml` | `F5_loop.png` |
| **F6** Seven parameter families vs generative operationalisation | `figs_nr10_schematic.py · f6()` | `figs_nr10_schematic.py f6` | **none** — pure schematic, no data/counts/citations | `F6_parameters.png` |
| **E1** PCA of the 21-col vector, coloured by stakeholder | `figs_nr10_embed.py · e1()` | `figs_nr10_embed.py e1` | `data/<slug>/buildings.parquet` (all 8, `build_table`); `config/stakeholder_lookup.yaml`; `config/scenarios.yaml`; features via `cake` + `measure` | `E1_pca_stakeholder.png`, `E_embed_stats.json` |
| **E2** Same PCA, three colourings | `figs_nr10_embed.py · e2()` | `figs_nr10_embed.py e2` | (same table as E1) | `E2_pca_variants.png` |
| **E3** AE + β-VAE vs PCA, recoverability | `figs_nr10_embed.py · e3()` | `figs_nr10_embed.py e3` | (same table as E1); numpy AE + β-VAE (β=0.05, SEED=0), cache `out/cake_figs/_embed_cache/` | `E3_ae_vae.png` |

Shared modules imported by all three figure scripts (a change here changes the figures):
`figs_cake.py` (plan/scalebar/share_bar, palette, `ORDER/INK/NICE/RED`),
`pf_common.py` (`SH_COLOR`, `load_buildings`, `STAKEHOLDERS`),
`cake.py` (`far_allowed/far_actual/weakness_score/load_cfg`),
`measure.py` (`diagnose → coverage`), `operators.py`.

## 2. Build DAG (what produces the figure inputs)

```
上海城市数据集 (raw, NOT distributed — see PROVENANCE.md)
   │  pf_common.build_cache / load_buildings   (clip to jiedao, join EULUC/Function/AOI, cascade)
   ▼
data/<slug>/buildings.parquet        ← 8 sites (footprints+height+holder, EPSG:32651)
   │
   ├─ run_cake_all.py  ─▶ out/cake/metrics_cake_all.json, reachable_<slug>.json, ledger_*, skyline_*
   ├─ aux_csv_nr10.py  ─▶ out/cake/{rule_comparison,weakness_dist,gamma_bind,age_layer_stats}.csv
   └─ cake_viewers.py  ─▶ out/cake_figs/viewer_<slug>.html + shot_*.png (80 = 8×5×2, headless chromium)
                                   │
                                   ▼
         figs_nr10.py · figs_nr10_schematic.py · figs_nr10_embed.py
                                   ▼
         out/cake_figs/F1..F6*.png, E1..E3*.png   ──▶  verify_cake_nr10.py (34 checks)
```

`run_cake.py` + `verify_cake.py` are the **FROZEN five** baseline; the `*_all` / `*_nr10`
runners extend to eight sites and are written to never touch the frozen files. The frozen-five
regression inside `verify_cake_nr10.py` is what guarantees the extension did not drift
(**max deviation 0.0** over every numeric leaf).

## 3. Verification

```bash
cd FoAR/engine && python3 verify_cake_nr10.py     # exit 0 = all 34 pass
```

The 34 checks: frozen-five regression (deviation 0.0) · cross-case inversion (zhangjiang
developer-led 0.774/0.80, pengpu state-led 0.063/0.30, zhangjiang the sole developer-led
failure) · reachability grids (every unreachable cell state-side; pengpu 20/25 worst,
zhangjiang 0/25 best) · envelope inert at base γ / binds at strict γ=30 m · aux-CSV row counts
and `weak_first` lift · figures/viewers/screenshots present on disk (F1–F6 + E1 >20 KB,
8 viewers, 80 shots). `verify_cake.py` is the frozen-five-only companion.

---

## 4. ⚠️ SCRIPT SYNC DONE (2026-07-14) — copy the three edited scripts in later

At capture time (**2026-07-13**) the three figure scripts were being **edited concurrently by
other agents** (a de-editorialization pass). `figs_nr10_schematic.py` in fact **changed under
observation** during this session (`b1ac40e5… → 00c69bc1…`, and F5/F6 regenerated at 23:39).
They were therefore **NOT copied into this folder** — a copy now would freeze a transient state.

**Next step (do this after the de-editorialization edits land):** copy the three scripts into
`FoAR/engine/audit/foar_figures/scripts_snapshot/` and record their new sha256 here, so the
published-figure version is pinned and diffable against the snapshot below.

Snapshot sha256 at capture (the baseline to diff against):

| script | sha256 (first capture) | mtime | status |
|----|----|----|----|
| `figs_nr10.py` | `89092ae59f1907dea2ac59f93f9f277d5327ec41e140a6ad7ff3d043ca3e6839` | 2026-07-13T03:27:37 | SYNC PENDING — **already drifted** (see below) |
| `figs_nr10_schematic.py` | `00c69bc1a7ae65331dd9f5fa4e49256f78dd33775cddf3e3a133e4b98b88dd69` | 2026-07-13T23:39:01 | SYNC PENDING — **already drifted** (see below) |
| `figs_nr10_embed.py` | `b58d26e0fc5f986fe90fe3f750339931dd09a50e1afc847768e76941a4474a78` | 2026-07-13T02:37:38 | SYNC PENDING (stable so far) |

**Churn observed within this session.** Re-hashing ~6 minutes after first capture (2026-07-13 ~23:45)
already showed two of the three moving again:

| script | first capture | re-hash @23:45 | moving? |
|----|----|----|----|
| `figs_nr10.py` | `89092ae5…` | `ee252dd8c54335c99c7b7ff11d50ec8e4c02aff8e212f8bf4c6e57c61811dba0` | yes |
| `figs_nr10_schematic.py` | `00c69bc1…` | `c6960d4961e156927a94400b275402cccbe796ec0cc11d42ef1d660a61c5bc48` | yes |
| `figs_nr10_embed.py` | `b58d26e0…` | `b58d26e0…` | no (stable) |

The de-editorialization pass is **still in flight** — do not treat any single hash above as final.
When copying into `scripts_snapshot/`, re-hash fresh at that moment and record *those* values.

To re-hash before syncing:

```bash
cd FoAR/engine
shasum -a 256 figs_nr10.py figs_nr10_schematic.py figs_nr10_embed.py
# if a hash differs from the table above, the de-editorialization landed — safe to snapshot:
mkdir -p audit/foar_figures/scripts_snapshot
cp figs_nr10.py figs_nr10_schematic.py figs_nr10_embed.py audit/foar_figures/scripts_snapshot/
shasum -a 256 audit/foar_figures/scripts_snapshot/*.py   # then paste into MANIFEST.json + this table
```

Helper modules (`figs_cake.py`, `pf_common.py`, `cake.py`, `measure.py`, `operators.py`) were
stable at capture; their hashes are pinned in `MANIFEST.json → helpers` and can be snapshotted
in the same step if a fully self-contained copy is wanted.

## E-series frozen embeddings

The supplementary latent-space figures **E1–E3** (and their `out/cake_figs/E_embed_stats.json`)
depend on trained numpy AE/VAE embeddings that `figs_nr10_embed.py` caches in
`out/cake_figs/_embed_cache/`. **That live cache path is git-ignored**
(`.gitignore: engine/out/cake_figs/_embed_cache/`), so it does NOT survive a clean checkout —
which is exactly why the E-series had been drifting whenever the cache was absent and the AE/VAE
retrained.

To make E1–E3 bit-reproducible and audit-durable, the canonical cache (**seed 0, 450 epochs,
numpy 2.0.2**) is now frozen under a **tracked** folder:

- **`embed_cache_frozen/`** — 4 `.npy` + 4 `.json` (`ae_all`, `vae_all`, `ae_phys`, `vae_phys`),
  their sha256, and a `README.md`. The 8 files + hashes are also recorded in
  `MANIFEST.json → embed_cache_frozen`.

Verified bit-stable on **2026-07-14**: with the cache present, `python3 figs_nr10_embed.py all`
loads from `_embed_cache/` (the `_cached()` early-return; no retrain) and leaves
`E_embed_stats.json` byte-identical
(sha256 `a23c27f5c0929a0e905a0bbbc4dafd8899f8a837429f0df76d51118a7dd1ad21`). Balanced-accuracy
rows hold: **PCA-2D 57.2 / AE-2D 88.8 / VAE-2D 90.4 / full-D 88.5**.

Restore the frozen cache before re-running the E-series (from the engine root):

```bash
mkdir -p out/cake_figs/_embed_cache
cp audit/foar_figures/embed_cache_frozen/*.npy \
   audit/foar_figures/embed_cache_frozen/*.json \
   out/cake_figs/_embed_cache/
python3 figs_nr10_embed.py all   # loads cache, does NOT retrain
```


> **Script sync completed 2026-07-14.** Final de-editorialized, title-less versions of the three figure scripts are snapshotted in `scripts_snapshot/`; sha256 recorded in `MANIFEST.json` under `scripts_snapshot`. The in-figure titles/tags were removed entirely (captions live only in the manuscript, figures numbered Fig. 1-7 there).
