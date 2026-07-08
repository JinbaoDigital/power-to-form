# Power-to-Form

An exploratory grammar in which configurations of **stakeholder power** become interpretable,
largely floor-area-conserving geometric **operators** on real building stock. Four *regimes*
(developer-led, state-led, resident-built, shared) are replayed across five central-Shanghai
districts and read through a morphological fingerprint. This repository accompanies the paper
(*Frontiers of Architectural Research*).

## Two-layer reproducibility

Following the paper's data-availability statement, this repo releases **derived measurements + code**,
not the raw building geometry (the Baidu source layer is governed by the provider's terms and is
**not** re-hosted). So:

- **Numbers are verifiable now** — the computed results ship in `results/`; `python reproduce.py --verify`
  prints the paper's headline numbers straight from them, with no data download.
- **The pipeline is rerunnable** — obtain the upstream Shanghai dataset (`data/README.md`), rebuild the
  five caches (`engine/rebuild_baidu.py`), then `python reproduce.py --run` recomputes everything and
  redraws the figures. Editing an operator or a recipe and rerunning is how you explore alternatives.
- **No data needed to try the engine** — `python reproduce.py --demo` runs the full operator + measure
  pipeline on a small synthetic district.

```
engine/        pf_common (data contract + stakeholder cascade) · operators · measure · render · atlas
engine/config/ regimes.yaml (the four recipes) · vignette_recipes.yaml · stakeholder_lookup.yaml   <- edit
engine/data/   per-district site.yaml (extent/counts). Building caches are NOT shipped; rebuild them.
experiments/   exp1–exp14 (reliability, conservation, robustness, adversarial labels, negotiation…)
results/       computed outputs the paper's numbers come from (metrics, shape stats, exp_out/)
figures/       build_figures.py (data figures) + build_render_figures.py (3D / embedding)
data/          how to obtain the upstream dataset + a synthetic sample for the offline demo
docs/          REPRODUCIBILITY.md — every claim mapped to the script and output that backs it
notebooks/     pipeline_walkthrough.ipynb — how the pipeline works, cell by cell
```

## Quick start

```bash
pip install -r requirements.txt
python reproduce.py --verify     # headline numbers from results/ (no data needed)
python reproduce.py --demo       # run the engine on a synthetic district (no data needed)
# to rerun on the real districts: rebuild caches (data/README.md), then:
python reproduce.py --run
```

## Change an operator, see a different outcome

Interpretation and power live in **editable tables and small functions**, never in trained weights.
Edit a recipe in `engine/config/regimes.yaml` (e.g. `developer_led`'s `cap_m`) or an operator in
`engine/operators.py`, then re-run: `python reproduce.py --demo` shows the effect immediately on the
synthetic district; on the five real districts, rebuild the caches first (`data/README.md`) and use
`--run`. Describing a new kind of power is a text edit, not a code change.

## Experiments ↔ paper sections

| # | Script | What it backs |
|---|---|---|
| 1 | `exp1_cascade_reliability.py` | §3.5 cascade depth + inter-source κ |
| 2 | `exp2_label_perturbation.py` | §5.5 random label robustness |
| 5 | `exp5_prewar_bound.py` | §3.5 construction-year censoring |
| 6 | `exp6_conservation_deviation.py` | §5.3 conservation-to-clamp |
| 7 | `exp7_sensitivity_sweep.py` | §5.5 ±30% parameter robustness |
| 8 | `exp8_order_permutation.py` | §5.5 operator-order robustness |
| 9 | `exp9_dip_robustness.py` | height-distribution diagnostics |
| 10 / 10b | `exp10_osm_audit.py` / `exp10b_toapayoh.py` | Appendix B OSM sufficiency |
| 12 | `exp12_clustered_flip.py` | §5.5 adversarial clustered label flip |
| 13 | `exp13_transplant_validation.py` | §5.4 caricature-vs-exemplar |
| 14 | `exp14_negotiation_vignette.py` | §6.1 negotiation vignette |

(Experiments read the district caches, so they run after a rebuild; their published outputs are in
`results/exp_out/`.)

## Building stock and heights

Footprints and heights are from the **Baidu Maps building layer**. Heights are a vendor attribute
**quantised to about 6 m** (storey multiples), usable as a coarse conservation currency but not a
continuous per-building height surface.

## Provenance and licensing

Source layers, governed by their providers' terms:

- **Building footprints + height** — Baidu Maps Open Platform (`lbsyun.baidu.com`).
- **Land use** — EULUC-China 2.0 for 2022 (Li et al., 2025; Zenodo [10.5281/zenodo.15180905](https://doi.org/10.5281/zenodo.15180905), CC BY 4.0).
- **Boundaries** — Tianditu / NGCC, review no. GS(2024)0650.
- **OSM audits** — © OpenStreetMap contributors (ODbL).

Code is **MIT** (`LICENSE`). The derived results and figures are released for verification of the
paper; raw source geodata are not included and remain under their providers' terms. Citation: `CITATION.cff`.
