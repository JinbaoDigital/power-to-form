# Reproducibility map — claim → script → output

Every quantitative claim in the manuscript, mapped to the script that produces it and the artifact that
backs it. Numbers reflect the **Baidu-v2** building stock (see `../paper/DATA_SOURCES.md` §9).

Legend: **[frozen]** = re-derivable here from `results/` (no licensed data); **[data]** = needs the
licensed source dataset + rebuilt caches (`../data/README.md`); **[net]** = needs network (Overpass).

| Manuscript | Claim | Script | Output / how to check |
|---|---|---|---|
| §3.3, Table 1 | 5 districts as found — n, FAR, coverage, h_mean/max, CV, slenderness (citywide 1.37M→873k; 5-district 9,504→5,448) | `engine/pf_common.build_cache` → `engine/measure.diagnose` | `results/metrics_baidu_5districts.json`; `reproduce.py --verify` **[frozen]** |
| §3.4 | Stakeholder shares 62–81% resident, 9–24% developer, 8–12% state, 1–3% unknown; Lujiazui 63%/28% (resident) vs 24%/65% (developer) count/GFA | `engine/pf_common.assign_all` | `results/stakeholder_shares.json`; `reproduce.py --verify`; `figures/fig5` **[frozen]** |
| §3.5 | Cascade depth (EULUC 93.5–97.7%), inter-source κ 0.02–0.39 | `experiments/exp1_cascade_reliability.py` | `results/exp_out/exp1_*`; `figures/fig6` **[data]** |
| §3.5 | Construction-year layer right-censored (all ≥1984), pre-war invisible | `experiments/exp5_prewar_bound.py` | `results/exp_out/exp5_prewar_bound.md` **[data]** |
| §5.1, Table 2 | Direction-consistent regime signatures (developer-led FAR↑ cov↓ slender↑ 5/5) | `engine/operators.apply_regime` + `measure.compare` | `results/metrics_baidu_5districts.json` **[frozen]** |
| §5.2 | Substrate memory — ρ(current, regime); grain under resident-built ρ=−0.10; state-led max-height ordering erased | `engine/measure` + Spearman ρ | `figures/fig9`; `figures/build_figures.py fig9` **[frozen]** |
| §5.3, Table A1 | Conservation to clamp — developer +28–65%, state-led −10 to +1% (concentrate leak), resident −56 to −79%, shared −15 to −49% | `experiments/exp6_conservation_deviation.py` | `results/exp_out/exp6_*`; `figures/fig11` **[data]** |
| §5.4 | **WITHDRAWN** — dip finds all 5 current fabrics "bimodal" (D=0.07–0.17, p<0.001); this is the 6 m height quantisation, not a result | `experiments/exp9_dip_robustness.py` | `results/exp_out/exp9_*`; `results/dist_shape_stats.json`; `reproduce.py --verify` **[frozen]** |
| §5.6 | Robustness — survives 20% label flips (3/3), ±30% OAT (22/26), operator reordering (≤4.5% of substrate) | `exp2_label_perturbation.py`, `exp7_sensitivity_sweep.py`, `exp8_order_permutation.py` | `results/exp_out/exp2_*`, `exp7_*`, `exp8_*`; `figures/fig14` **[data]** (exp2/exp7 heavy) |
| Appendix B | OSM sufficiency — footprint coverage 42–86% of Baidu stock; height signal 1–43% (levels only); 31–73% untagged | `exp10_osm_audit.py`, `exp10b_toapayoh.py` | `results/exp_out/` (rerun) **[data][net]** |

## Fastest checks (no licensed data)

```bash
python reproduce.py --verify     # Table 1 / §3.4 / §5.4 numbers straight from results/
python reproduce.py --demo       # operators + measure run end-to-end on synthetic data
```

## Full re-derivation (with the licensed dataset)

See `../data/README.md`: rebuild the five caches, then run `engine/recompute_baidu_metrics.py` and
`experiments/exp*.py`. The heavy experiments (exp2 ~30–90 min, exp7 ~1–2 h) and the OSM audits
(exp10/exp10b, network) are the only slow steps.

## Provenance

Building footprints and heights are from the Baidu Maps building layer; land use from EULUC-China 2.0
(2022, Li et al. 2025); sub-district boundaries from Tianditu; OpenStreetMap is used only for the
sufficiency audits (Appendix B). Full source list, licences and access notes are in `../README.md`.
