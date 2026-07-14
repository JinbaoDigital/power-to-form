#!/usr/bin/env python3
"""Resize final cake_figs PNGs -> web JPGs (width 1500, q85, white-flattened) for the HTML build."""
import os
from PIL import Image

SRC = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "engine" / "out" / "cake_figs")
DST = str(__import__("pathlib").Path(__file__).resolve().parent / "figs_web")
os.makedirs(DST, exist_ok=True)

FILES = [
    "F1_atlas.png", "F2_gallery.png", "F2_gallery_skyline.png", "F3_fingerprints.png",
    "F4_reachability_all.png", "F5_loop.png", "F6_parameters.png",
    "E1_pca_stakeholder.png", "E2_pca_variants.png", "E3_ae_vae.png",
]
W = 1500

for fn in FILES:
    src = os.path.join(SRC, fn)
    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    if im.width > W:
        h = round(im.height * W / im.width)
        im = im.resize((W, h), Image.LANCZOS)
    out = os.path.join(DST, os.path.splitext(fn)[0] + ".jpg")
    im.save(out, "JPEG", quality=85, optimize=True, progressive=True)
    print("%-26s %s -> %.0fKB" % (os.path.basename(out), im.size, os.path.getsize(out) / 1024))
print("done ->", DST)
