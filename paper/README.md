# paper/ - the manuscript build chain

The **manuscript body is not in this repository**: the paper is under review, and only its build
chain is released, so that a reader can see exactly how the published figures were prepared and
placed.

| Script | What it does |
|---|---|
| `build_combined_figs.py` | resizes the final figure PNGs to web JPGs (width 1500, q85, white-flattened) into `paper/figs_web/` |
| `build_combined_html.py` | inlines those JPGs as data URIs into a single self-contained HTML, and injects the figure captions at fixed sentence anchors in the manuscript text |
| `build_combined_pdf.py` | prints that HTML to PDF |

The three scripts read `paper/manuscript_combined_v1.md` and the figure PNGs from the working tree
of the authoring repository (`engine/out/cake_figs/`). Neither the markdown source nor that output
directory is shipped here, so the chain will not run as-is; it is included as a record of the figure
preparation, not as a runnable target.

The published figures themselves are in [`../figures/`](../figures). The mapping from the pipeline's
internal names to the manuscript's Fig. 1-7:

| Manuscript | Pipeline name | File in `figures/` |
|---|---|---|
| Fig. 1 Parameter families | `F6_parameters.png` | `fig1_parameter_families.png` |
| Fig. 2 The loop | `F5_loop.png` | `fig2_loop.png` |
| Fig. 3 Site atlas | `F1_atlas.png` | `fig3_site_atlas.png` |
| Fig. 4 Configuration gallery | `F2_gallery.png` | `fig4_configuration_gallery.png` |
| Fig. 5 Cross-case fingerprints | `F3_fingerprints.png` | `fig5_fingerprints.png` |
| Fig. 6 Reachability | `F4_reachability_all.png` | `fig6_reachability.png` |
| Fig. 7 Embedding (3 panels) | `E1_pca_stakeholder.png`, `E2_pca_variants.png`, `E3_ae_vae.png` | `fig7a_pca_stakeholder.png`, `fig7b_pca_variants.png`, `fig7c_ae_vae.png` |

The figures carry no in-image titles and no self-numbering: captions live in the manuscript only.
`build_combined_html.py` holds those captions and is therefore the authoritative record of what each
figure is called.
