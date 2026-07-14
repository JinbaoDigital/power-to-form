# Frozen E-series embeddings (canonical)

These 8 files are the **canonical, frozen** trained embeddings behind the supplementary
latent-space figures **E1–E3** and their stats file `out/cake_figs/E_embed_stats.json`.

- Producer: `FoAR/engine/figs_nr10_embed.py` (`_cached()` in the `all` driver).
- Training: numpy AE/VAE, **seed 0**, 450 epochs.
- **numpy version at capture: `2.0.2`** (embeddings are numpy-version-sensitive; pin this to reproduce bit-for-bit).
- Live (regenerable) location: `FoAR/engine/out/cake_figs/_embed_cache/` — this path is **git-ignored**
  (`.gitignore` line: `engine/out/cake_figs/_embed_cache/`), so it does NOT travel with the repo.
  This tracked copy is the durable one.

Each `<name>.npy` is a trained 2-D embedding array; the paired `<name>.json` holds `{"r2", "seed"}`.
`_cached()` returns early (loads, does **not** retrain) whenever both the `.npy` and `.json` exist,
which is what makes E1–E3 bit-reproducible once these are restored.

## What the numbers derive from

The balanced-accuracy figures reported in E1–E3 / `E_embed_stats.json` (the `"all"` feature set,
5-fold cross-validated 10-NN purity on the embedding) come directly from these arrays:

| view    | balanced accuracy | source in E_embed_stats.json |
|---------|-------------------|------------------------------|
| PCA-2D  | **57.2 %**        | `all.pca2.bal_acc`  = 0.5720907023642345 |
| AE-2D   | **88.8 %**        | `all.ae2.bal_acc`   = 0.8884726455700068 |
| VAE-2D  | **90.4 %**        | `all.vae2.bal_acc`  = 0.9044345480251382 |
| full-D  | **88.5 %**        | `all.fullD.bal_acc` = 0.8849834640296838 |

(PCA-2D and full-D do not use the cached AE/VAE arrays, but they are recomputed in the same
deterministic run; freezing the AE/VAE cache is what pins the AE-2D and VAE-2D rows and keeps
`E_embed_stats.json` byte-identical across re-runs.)

Verified bit-stable on 2026-07-14: re-running `python3 figs_nr10_embed.py all` loaded from cache
(no retrain) and left `E_embed_stats.json` sha256 unchanged
(`a23c27f5c0929a0e905a0bbbc4dafd8899f8a837429f0df76d51118a7dd1ad21`).

## sha256 of the frozen files

```
baeaaafb747088430bf4d3cf9998d5ca176b2f3788f6f68b7d0fcf0adab7b2a0  ae_all.npy
eccb5c0a2d69a942707a3ef64f7d2b5845fdea802c3086de05384c067dafbfa0  ae_phys.npy
7726d91703fe418de8a4789cc025475784cebff2f228c657f4e86aebf2dacff4  vae_all.npy
d6c5fde89d39e40fd43e1cae2f03832891dd19f76b52ebe924130e1cc41d228f  vae_phys.npy
9b883ddbb0e5d7c17cf91eaf3d011740e6184b72f82f0d570067b4342b44604d  ae_all.json
98664dbbf766b6c8fdac8282ef9349c7635cb023ef039899162042a84e5b057e  ae_phys.json
08d07d717b71893c85459bf376d39993201099d300cea56e2070b86d3f3fd8e5  vae_all.json
c149599be01c7e998ce5a0fff230119439389a6c8fe33d2aa9687ea2aa757377  vae_phys.json
```

## Restore before re-running the figures

From the engine root (`FoAR/engine/`):

```bash
mkdir -p out/cake_figs/_embed_cache
cp audit/foar_figures/embed_cache_frozen/*.npy \
   audit/foar_figures/embed_cache_frozen/*.json \
   out/cake_figs/_embed_cache/
python3 figs_nr10_embed.py all   # loads the cache, does NOT retrain; regenerates E1–E3 + E_embed_stats.json
```

Optional integrity check after restoring:

```bash
shasum -a 256 out/cake_figs/_embed_cache/*.npy out/cake_figs/_embed_cache/*.json
# must match the hashes listed above
```
