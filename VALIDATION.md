# Validation

How the published numbers of *Reading the Found City through Stakeholder Power: An Auditable
Parametric Instrument* are checked, and what a reviewer can re-run from this repository alone.

One command reconciles them against the frozen derived artefacts:

```bash
python reproduce.py --verify      # 72 checks; exits non-zero if any of them fails
```

It hard-codes only the **expected** value (the number as printed in the paper), **recomputes** the
actual value from `engine/out/`, prints both side by side, and compares. No published number is a
constant that prints itself.

**What that does and does not mean.** `--verify` runs **72 named checks**, listed in full below. It
is not a cell-by-cell re-reading of every shipped file, and this document does not claim it is: the
section [What ships unchecked](#what-ships-unchecked) says exactly which columns of which artefacts
no verifier opens. Every number that appears in the manuscript - Table 1, the anchors, the grids,
the envelope, the ranks, the embedding - is in the 72.

Validation stands on three layers.

---

## Layer 1 - by-construction invariants

These hold by the design of the instrument, not by luck, and the audit re-asserts them so that a
change to an operator cannot silently break them.

| Invariant | Where it is enforced | Recomputed value |
|---|---|---|
| Footprints are frozen: **coverage**, **grain** and **n** are identical in every run | `cake.py` never moves or adds a footprint; only height and holder change | identical to as-found in all 8 sites x 10 runs |
| **Mode A (redistribute)** conserves floor volume exactly | mode A transfers holding without changing GFA | `gfa_change_pct = 0.00 %` across **40 runs** (8 sites x 5 scenarios) |
| One building has exactly one holder | `pf_common.assign_stakeholder`, first hit wins over EULUC -> Function -> AOI | shares sum to 1: **max \|sum - 1\| = 1.0e-04** over the 88 runs (as-found + configured), the residual being the 4 dp rounding of the four shares; `--verify` asserts a 5e-4 tolerance |
| The regulatory envelope is a dial, not a constant | `gamma` in `config/scenarios.yaml` | binds in **0 of 80** runs at base (60 m); in **3 of 32** at strict (30 m), removing **6.036e+06 m3** |

Mode B (grow) deliberately does **not** conserve volume: that is the point of a growth
configuration, and the ledgers record every cubic metre it adds or removes.

## Layer 2 - frozen regression

The five-site run of the earlier paper (`engine/out/cake/metrics_cake.json`) is a **frozen
reference**. The eight-site run must reproduce it exactly, or the extension changed the answer for
the sites it inherited.

- `reproduce.py --verify` walks every numeric leaf of the frozen file against the eight-site file:
  **1748 leaves, max deviation 0.000e+00**.
- The pinned verifier `engine/verify_cake_nr10.py` (sha256 `87aa724d...`, recorded in
  `MANIFEST.json`) carries **34 checks**: the frozen-five regression, the cross-case inversion, the
  eight reachability grids, the envelope finding, the four traceability CSVs, and the presence of
  the figures, the eight interactive viewers and the 80 screenshots on disk.

  Run raw in **this** repository it reports **24 pass, 10 fail** and exits 1, and that is by design,
  not a defect. The 10 failures are its last section, which asserts that the rendered figures, the
  eight interactive viewers and the 80 Three.js screenshots exist in `engine/out/cake_figs/`. Those
  artefacts are **not redistributed** (they inline per-building footprint coordinates and Esri
  satellite imagery; see the README). All 34 pass in the full working tree, where the licensed
  caches and the rendered viewers are present.

  So the reviewer runs it through the release-side wrapper, which re-hashes the pinned script
  against `MANIFEST.json`, runs it **unmodified**, and counts those 10 as **skipped**:

  ```bash
  python audit_release.py     # ALL PASS  24 pass, 10 skipped, 0 failed   -> exit 0
  make audit                  # the same, after reproduce.py --verify     -> exit 0
  make audit-raw              # the pinned script raw: 24 ok, 10 FAIL     -> exit 1, by design
  ```

  `verify_cake_nr10.py` is pinned by sha256 and is never edited: the wrapper is what adapts, so the
  audit chain stays intact. The two verifiers overlap but neither contains the other:
  `verify_cake_nr10.py` checks the four aux-CSV row counts and the weak_first lift, and until this
  pass `--verify` did not; `--verify` adds Table 1, the Spearman ranks, the embedding statistics,
  the hash manifest and the figure hashes on top. As of this release **`--verify` also recomputes
  the aux CSVs, the ledgers and the skylines** (section 10 of its output), so nothing the pinned
  verifier checks in the release is outside `--verify`.

## Layer 3 - hash manifest and the frozen embedding cache

`engine/audit/foar_figures/MANIFEST.json` pins the sha256 of every script, config and derived
artefact behind the published figures. `reproduce.py --verify` re-hashes **all 42 pinned paths**
(the three figure scripts and their snapshot copies, the five helpers, the three upstream producers,
the pinned verifier, the five configs, the 14 frozen data inputs, the eight embedding-cache files)
and reconciles them, and **a pinned path that is absent is a failure**, not a printed note. Every
one of the 42 is shipped; nothing pinned is missing. The **nine published PNGs** are pinned too, in
the new `published_figures` section, and re-hashed: they are no longer merely counted.

**One deliberate delta.** `engine/pf_common.py` here is `15be82d2...`, while the manifest pins the
audited copy `a37637e2...`. The two files differ in **two comment lines only** (a note on the
history of the upstream footprint layer, removed under the release policy); the code is identical
otherwise. The audit prints this as a named exception rather than hiding it. Nothing that produces a
number depends on those two lines.

**Snapshot integrity.** `audit/foar_figures/scripts_snapshot/` holds the three figure scripts as
published. On 2026-07-14 the snapshot of `figs_nr10_schematic.py` (and its manifest hash) was found
to be one commit stale: it pinned the pre-restyle script `c0ad6595...` while the published Fig. 1
and Fig. 2 are the monochrome line-art versions. It was re-pinned to `45b0fbe2...`; the superseded
hash is retained in `MANIFEST.json` for traceability. `--verify` now asserts, one check per script,
that the snapshot and the engine copy of **all three** figure scripts (`figs_nr10.py`,
`figs_nr10_embed.py`, `figs_nr10_schematic.py`) are byte-identical, and that each matches its
manifest pin.

**Frozen embeddings.** The E-series (Fig. 7) depends on a numpy autoencoder and beta-VAE. The
canonical trained cache (seed 0, 450 epochs, numpy 2.0.2) is tracked in
`engine/audit/foar_figures/embed_cache_frozen/` (4 `.npy` + 4 `.json`, each hashed in the manifest).
`figs_nr10_embed.py` loads it and does **not** retrain, so the figures are bit-reproducible.

Honest caveats on the embedding, both measured rather than assumed:

- Re-running the E-series against the frozen cache leaves `E_embed_stats.json` byte-identical on one
  machine, but across **BLAS builds** the file can differ at the **1e-15 level** on the PCA
  explained-variance-ratio and silhouette leaves (last-bit floating-point reduction order). All four
  headline balanced accuracies (**PCA-2D 57.2, AE-2D 88.8, VAE-2D 90.4, full-D 88.5**) are **exactly
  equal** across those runs, because they are counts of correct classifications, not sums of floats.
- A **live retrain** (deleting the cache) is a different matter: the AE drifts by about **0.4 pp**
  across numpy versions (**88.47** measured on numpy 2.2.6 against the frozen **88.85** on numpy
  2.0.2). The audit therefore reconciles against the **frozen stats file**, so a numpy bump cannot
  fail it spuriously; if you retrain, expect the AE-2D number to move within roughly +/- 0.5 pp and
  treat that as the reproducibility tolerance of a retrain, not of the paper.

---

## What `--verify` reconciles (72 checks)

| # | Group | Numbers checked |
|---|---|---|
| 1 | Release guard | zero `.parquet` anywhere in the tree |
| 10 | Table 1 | 8 rows x (n, area_km2, state/developer/resident GFA share, FAR, coverage, h_mean, h_max); 8 sites; **n = 11,397** |
| 4 | Invariants | frozen-five 1748 leaves at 0.000e+00; mode A 0.00 % over 40 runs; coverage/grain/n frozen; shares sum to 1 (max dev **1.0e-04** over 88 runs) |
| 4 | Failure anchors | Zhangjiang developer-led **0.774 of 0.80**, the only developer-led failure; Pengpu state-led **0.063 of 0.30**; Pengpu resident-led rebuilds **0 buildings** |
| 11 | Reachability | **87 of 200** cells unreachable, **all 87** state-side, **0** developer-side; per site zhangjiang 0, nanjingxi 5, dapuqiao 5, lujiazui 9, caoyang 15, yuyuan 15, laoximen 18, pengpu 20 (of 25) |
| 4 | Envelope | base (60 m) binds in **0 of 80**, highest rebuild target 58.56 m; strict (30 m) binds in **3 of 32**, removes **6.036e+06 m3** |
| 5 | Rank preservation | Spearman rho: FAR under developer-led **1.00**; concentration under state-led **0.33**; h_cv under shared **0.50**; slenderness under state-led and shared **1.00** |
| 7 | Embedding | PCA-2D **57.2**, AE-2D **88.8**, VAE-2D **90.4**, full-D **88.5**, form-only full-D **34.7** with state recall **0.07**; n = 11,397 |
| 5 | Hashes | all **42** pinned artefacts re-hashed, an absent one is a failure; snapshot == engine copy for **all three** figure scripts |
| 2 | Figures | the nine PNGs of Fig. 1-7 present **and sha256-pinned** (`published_figures`) |
| 5 | Ledgers + skylines | 83 `ledger_*.csv` shipped; **ledger rows == `acquired_n` in all 80 scenario runs**; Pengpu resident-led ledger **0 rows** against its `acquired_n = 0`; the 8 `skyline_*.json` carry **11,397** buildings, their `h_max` equals Table 1's, their holders are the four declared classes |
| 6 | Ordering rule | `rule_comparison.csv` 32 rows; mean weakness lift over the pool recomputed per rule: weak_first **+0.214**, random **-0.002**, adjacency_first **-0.031**, value_first **-0.155**, and weak_first leads |
| 2 | Weakness ties | `weakness_dist.csv` 48 rows; inside the developer-acquirable pool **88.1 % to 99.3 %** of buildings are tied on weakness (the score is an order, not a ruler) |
| 2 | Age layer | `age_layer_stats.csv` 16 rows, right-censored at **1984**; construction-year coverage **0.48 to 0.71** across the 16 pools |
| 4 | Invariance | `invariance.csv` 90 rows (50 sensitivity + 40 ablation); the developer target is met in **50 of 50** weightings, residents bear **1.000** of the loss in all 50, and weak_first leads the lift in **10 of 10** ablation cells |

Spearman is computed inside `reproduce.py` from average ranks (a dozen lines) rather than by
importing scipy, so the audit runs on a bare Python and adds no dependency.

<a name="what-ships-unchecked"></a>

## What ships unchecked

Stated so that no one has to discover it. These artefacts are in the release, and a reviewer can
read them, but no verifier reconciles them cell by cell:

| Artefact | Machine-checked | Not machine-checked |
|---|---|---|
| `ledger_*.csv` (83 files, 26,016 rows) | file count; **row count against `acquired_n`** for the 80 scenario runs | the per-row columns (`bid`, holder before/after, `gfa_before/after`, `h_before/after`, `area`, `weakness`); the 3 vignette ledgers (`caoyang_v1/v2/v3`) have no `acquired_n` to check against |
| `skyline_*.json` (8 files) | building count (11,397), `h_max` vs Table 1, the holder vocabulary | the per-building heights of the 5 configured states |
| `rule_comparison.csv` | 32 rows, the mean lift of each of the 4 rules | the other 20 columns (pool sizes, weakness quartiles, displaced GFA) |
| `weakness_dist.csv` | 48 rows, the tie share inside the acquirable pool | quartiles, modal value, zero share, the 5 non-pool pools |
| `age_layer_stats.csv` | 16 rows, censor year, age coverage | the 27 other columns (year moments, weakness decomposition, the two Spearman columns) |
| `invariance.csv` | 90 rows; target met, resident loss share, ablation ordering | `acquired`, the weakness moments, `pool_taken_frac` |
| `gamma_bind.csv` | the base/strict envelope rows used by the envelope checks | the permissive and none rows, and the per-run clipping columns |
| `E_embed_stats.json` | n = 11,397, the five balanced accuracies, the state recall | the PCA explained-variance and silhouette leaves (they drift at 1e-15 across BLAS builds; see above) |
| the nine PNGs | sha256 against `MANIFEST.published_figures` | nothing re-renders them here: Fig. 3, 4, 6, 7 need the licensed caches and the screenshots |
| `paper/` build chain | - | not run by the audit; the manuscript body is not in this repository |

---

## Reviewer's recomputation path (figure -> script -> input -> command)

Flattened from `engine/audit/foar_figures/RUNBOOK.md` and renumbered to the manuscript's Fig. 1-7.
Commands are run from `engine/`. "Release?" says whether the figure can be rebuilt from **this**
repository alone, or needs the licensed caches that are not redistributed.

| Fig. | (was) | Script - fn | Command | Inputs | Release? |
|---|---|---|---|---|---|
| **1** Parameter families | F6 | `figs_nr10_schematic.py f6()` | `python figs_nr10_schematic.py f6` | none (pure schematic) | **yes** |
| **2** The loop | F5 | `figs_nr10_schematic.py f5()` | `python figs_nr10_schematic.py f5` | `out/cake/metrics_cake_all.json`; `out/cake/ledger_laoximen_capital_deepen_B.csv`; `config/scenarios.yaml`; `data/laoximen/buildings.parquet` | no (needs the cache) |
| **3** Site atlas | F1 | `figs_nr10.py f1()` | `python figs_nr10.py f1` | `metrics_cake_all.json`; `data/<slug>/buildings.parquet` (x8); `out/cake_figs/shot_sky_<slug>_current.png` (x8) | no (cache + screenshots) |
| **4** Configuration gallery | F2 | `figs_nr10.py f2()` | `python figs_nr10.py f2` | `metrics_cake_all.json`; `shot_<slug>_<cfg>.png` + `shot_sky_<slug>_<cfg>.png` (80) | no (screenshots) |
| **5** Cross-case fingerprints | F3 | `figs_nr10.py f3()` | `python figs_nr10.py f3` | `metrics_cake_all.json` **only** (Spearman computed in-script) | **yes** |
| **6** Reachability | F4 | `figs_nr10.py f4()` | `python figs_nr10.py f4` | `out/cake/reachable_<slug>.json` (x8); `metrics_cake_all.json`; `data/<slug>/buildings.parquet`; `shot_sky_<slug>_current.png` | no (cache + screenshots) |
| **7** Embedding (3 panels) | E1-E3 | `figs_nr10_embed.py e1/e2/e3()` | `python figs_nr10_embed.py all` | `data/<slug>/buildings.parquet` (x8); `config/stakeholder_lookup.yaml`; `config/scenarios.yaml`; the frozen cache in `audit/foar_figures/embed_cache_frozen/` | no (cache); its **statistics** ship in `out/cake_figs/E_embed_stats.json` and are audited |

Upstream of the figures (needs the licensed dataset; see `engine/audit/foar_figures/PROVENANCE.md`):

```bash
cd engine
python run_cake_all.py all     # -> out/cake/metrics_cake_all.json, reachable_*.json, ledger_*, skyline_*
python aux_csv_nr10.py         # -> rule_comparison / weakness_dist / gamma_bind / age_layer_stats .csv
python cake_viewers.py all     # -> viewer_<slug>.html + 80 screenshots (headless chromium)
```

The artefacts those three commands produce are **already shipped** in `engine/out/` (except the
viewers and the screenshots), which is why the numbers can be audited without the data. Restore the
frozen embedding cache before rebuilding Fig. 7:

```bash
mkdir -p engine/out/cake_figs/_embed_cache
cp engine/audit/foar_figures/embed_cache_frozen/*.npy \
   engine/audit/foar_figures/embed_cache_frozen/*.json engine/out/cake_figs/_embed_cache/
cd engine && python figs_nr10_embed.py all      # loads the cache, does not retrain
```
