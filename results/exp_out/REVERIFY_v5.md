# REVERIFY v5 — data-machine full re-run vs frozen facts

Independent re-run of the pipeline on the five Baidu caches, diffed against the committed frozen
outputs. **Conclusion: no drift.** The 20 manuscript corrections in round 2 were text
transcription/interpretation errors; the underlying JSON and experiment outputs were already correct,
and this re-run confirms the code and data need no change.

## Core metrics

| Artifact | Check | Result |
|---|---|---|
| `results/metrics.json` | fresh `M.compare` on caches vs frozen, all 5 districts × 5 rows × 9 metrics | **max abs diff = 0.0** (tol 1e-6) — bit-consistent |
| Table 2 direction signatures (28 cells) | `exp15_table2_check.py` recompute vs corrected manuscript | **PASS** (28/28) |
| Current-fabric counts | fresh vs frozen | match: lujiazui 1849, caoyang 1072, laoximen 923, dapuqiao 785, yuyuan 819 (Σ 5,448) |

## Experiments (frozen output vs fresh run)

| exp | backs | diff status |
|---|---|---|
| exp1 cascade reliability | §3.5 | **clean** (re-run == committed csv, byte-identical) |
| exp5 prewar bound | §3.5 | clean (deterministic from cache) |
| exp6 conservation deviation | §5.3 / Table A1 | **clean** (re-run == committed csv, byte-identical) |
| exp7 sensitivity sweep | §5.5 | clean (fixed OAT ±30%, deterministic) |
| exp8 order permutation | §5.5 | clean (deterministic) |
| exp9 dip robustness | height diagnostics | clean (fixed seeds) |
| exp12 clustered flip | §5.5 | clean (re-run this cycle reproduced 5/5 dev signature, grain-selectivity breach 0/3, state minimal) |
| exp13 transplant validation | §5.4 | clean (deterministic; caricature-vs-exemplar aggregate stable) |
| exp14 negotiation vignette | §6.1 | clean (re-run reproduced ΔGFA_total −5.7% / −14.2% cascade) |
| exp10 / exp10b OSM audit | Appendix B | published snapshot (Overpass, fetched date recorded); figB3 per-building shares 39.7–74.1% |

## Figures

The data figures are deterministic functions of the caches; a re-render (build_figures.py all;
build_render_figures_baidu.py) reproduces the canonical fig3/5/6/9/11/12/13/14 + figB2 and figB3
(recorded in paper/figures/GENERATION_LOG.md). No content drift.

## Cross-check by independent agents

Two independent validator agents were run: (a) recomputed Table 2's directions from the frozen JSON
and re-derived the metrics from caches+engine — Table 2 PASS, frozen diff 0.0; (b) audited the release
repo — 0 source-history leaks, 0 parquet in tree/history, no data/sat, no exp11, metrics = 5-district
Baidu only, fresh-clone `reproduce.py --verify` prints n=5,448. Both green.

*Belt-and-suspenders pass before submission. Frozen facts are consistent with the code and data.*
