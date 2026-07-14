# Reading the Found City through Stakeholder Power

### An Auditable Parametric Instrument - audit and validation package

A deterministic instrument that reads a real building stock, maps each building to the stakeholder
who holds it through a declared lookup, transforms the stock under one configuration of power, and
reads the result back with the same ruler. No trained weights: identical inputs yield an identical
city, and every rule is an editable table or a small function. Eight central and peri-urban Shanghai
sub-districts, **11,397 buildings**, four power configurations, one shared fingerprint.

This repository is the **audit and validation package** for the manuscript: **derived measurements +
the code that produced them**. It is not a data release.

```bash
pip install -r requirements.txt
python reproduce.py --verify     # reconcile EVERY number in the paper, 48 checks, no data needed
```

`--verify` hard-codes only the *expected* value (the number as printed in the paper), *recomputes*
the actual value from the frozen artefacts in `engine/out/`, prints both, and exits non-zero if any
of them disagree. See [`VALIDATION.md`](VALIDATION.md) for the three validation layers and the
reviewer's figure-by-figure recomputation path.

---

## What this repo carries

```
reproduce.py            --verify (audit every number) - --run (needs the licensed caches) - --demo
VALIDATION.md           the three validation layers + figure -> script -> input -> command table
engine/                 the instrument
  cake.py                 the transform: acquisition, weakness ordering, rebuild, the gamma envelope
  pf_common.py            data contract: the EULUC -> Function -> AOI cascade, one holder per building
  measure.py, figs_cake.py, operators.py       the ruler and the shared drawing helpers
  run_cake.py, run_cake_all.py                 the 5-site (frozen) and 8-site runners
  aux_csv_nr10.py                              the four traceability CSVs
  verify_cake_nr10.py                          the 34 pinned checks
  figs_nr10.py, figs_nr10_schematic.py, figs_nr10_embed.py    the three figure scripts
  cake_viewers.py                              builds the interactive viewers (outputs not shipped, below)
  config/                 scenarios - regimes - sites - stakeholder_lookup - vignette_recipes  <- edit these
  data/<slug>/site.yaml   name, slug, area_km2, n for the eight sites (no geometry, no bounding box)
  out/cake/               THE FROZEN DERIVED ARTEFACTS the paper's numbers come from:
                          metrics_cake_all.json (8 sites x current + 5 scenarios x modes A/B),
                          metrics_cake.json (the frozen five), reachable_<slug>.json (8 x 5x5 grid),
                          ledger_*.csv (83: bid, holder before/after, gfa, height, area, weakness),
                          skyline_<slug>.json (bid, height, holder), invariance.csv,
                          rule_comparison / weakness_dist / gamma_bind / age_layer_stats .csv
  out/cake_figs/          E_embed_stats.json (the embedding statistics behind Fig. 7)
  audit/foar_figures/     RUNBOOK.md - PROVENANCE.md - MANIFEST.json (sha256 of every pinned artefact)
                          scripts_snapshot/ (the three figure scripts, pinned to the published versions)
                          embed_cache_frozen/ (the frozen AE / beta-VAE latent coordinates)
figures/                  the nine PNGs of the published Fig. 1-7
paper/                    the manuscript build chain (the manuscript body is NOT here, see below)
archive_v5_5district/     the previous generation, kept whole (see "Two generations")
```

Every artefact above is a **derived measurement**: metrics, fingerprints, shares, ledgers, skylines,
reachability grids, embedding statistics, latent coordinates. None of them contains a coordinate, a
footprint or an image tile.

## What this repo deliberately does not carry, and why

| Not here | Why |
|---|---|
| `engine/data/<slug>/buildings.parquet` (the per-site caches) | Baidu-derived building geometry. Footprints and heights are governed by the provider's terms and are not re-hosted, in this tree or anywhere in its git history. |
| Bounding boxes in `site.yaml` | Removed from the eight current sites; only name, slug, area and count remain. |
| `viewer_<slug>.html` (the eight interactive Three.js views) | Each viewer inlines the **per-building footprint coordinates** into its JavaScript. Shipping them would ship the geometry through the back door. |
| The 80 Three.js screenshots (`shot_*.png`) | Their ground plane is **Esri World Imagery**; redistributing them redistributes satellite tiles. |
| The manuscript body | The paper is under review; only its build chain is here (`paper/`). |

Consequences, stated plainly: **Fig. 1 and Fig. 5 can be rebuilt from this repository alone**; the
other figures crop the viewers' screenshots or read the caches, so they can only be rebuilt in the
full working tree, with the licensed upstream data. The published PNGs of all seven are in
`figures/`. The **numbers** behind all seven are auditable here, which is the point of the package:
`reproduce.py --verify` recomputes them from the derived artefacts.

Cache building (`pf_common.build_cache`) is kept in the code because it documents the provenance of
every column, but it reads the licensed upstream Shanghai compilation and is therefore **not
reproducible from this repository**. Nothing in the verification path reads it, or any parquet:
`reproduce.py --verify` opens only JSON and CSV, and its first check asserts that no `.parquet` file
exists anywhere in the tree.

## Two generations, two papers

This repository has been through one previous release, and nothing from it was deleted.

| Generation | Where | Paper |
|---|---|---|
| **v5, five districts** (Lujiazui, Caoyang, Laoximen, Dapuqiao, Yuyuan; four regimes as operator recipes; exp1-exp15; the old Fig. 3-14) | `archive_v5_5district/` - self-contained, still runs: `python archive_v5_5district/reproduce.py --verify` | *Power-to-Form: a stakeholder-power shape grammar* (the earlier five-district submission) |
| **current, eight sites** (adds Nanjingxi, Pengpu, Zhangjiang; the cake transform, reachability, the gamma envelope, the E-series embedding; Fig. 1-7) | the repository root | **Reading the Found City through Stakeholder Power: An Auditable Parametric Instrument** |

The two generations share a substrate but not a run: the five sites the new run inherits are held to
the old numbers by a **frozen regression** (1748 numeric leaves, deviation 0.000e+00), so the
extension provably did not move the earlier paper's results. `archive_v5_5district/` keeps its own
engine, experiments, results and figures, so both papers remain reproducible from one checkout.

## The reviewer's path

```bash
python reproduce.py --verify              # 1. every published number, recomputed (48 checks)
cd engine && python verify_cake_nr10.py   # 2. the 34 pinned checks (24 run here; see VALIDATION.md)
```

Then read [`VALIDATION.md`](VALIDATION.md) for the figure -> script -> input -> command table, and
`engine/audit/foar_figures/PROVENANCE.md` for the lineage of every column the instrument reads.

To change what power means, edit `engine/config/scenarios.yaml` (targets, weakness weights, the gamma
envelope) or `engine/config/stakeholder_lookup.yaml` (the land-use -> holder cascade) and re-run. A
new kind of power is a text edit, not a code change. Re-running on the eight real sites needs the
caches; `python reproduce.py --demo` runs the engine end to end on a synthetic district with no data
at all.

## Provenance and licensing

Source layers behind the derived measurements, each governed by its provider's terms
(full lineage in `engine/audit/foar_figures/PROVENANCE.md`):

- **Building footprints + height** - Baidu Maps building layer v2 (`lbsyun.baidu.com`). Heights are a
  vendor attribute quantised to about 6 m storey multiples, not a survey; we read them at storey
  resolution and comparatively.
- **Land use** - EULUC-China 2.0 for 2022 (Li et al., 2025; Zenodo
  [10.5281/zenodo.15180905](https://doi.org/10.5281/zenodo.15180905), CC BY 4.0).
- **Construction year** - a beta year layer, right-censored at 1984.
- **Boundaries** - Tianditu / NGCC, review no. GS(2024)0650.
- **Satellite basemap** (in the viewers only, which are not shipped) - Esri World Imagery.

Code is **MIT** (`LICENSE`). The derived results and figures are released for verification of the
paper; the raw source geodata are not included and remain under their providers' terms. The frozen
embedding cache in `engine/audit/foar_figures/embed_cache_frozen/` holds **derived latent
coordinates** (2-D AE / beta-VAE outputs), not geometry, but its upstream lineage runs back to those
same licensed layers through the feature table. Citation: `CITATION.cff`.
