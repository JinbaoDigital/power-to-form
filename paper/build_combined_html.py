#!/usr/bin/env python3
import base64, os, markdown

ROOT = str(__import__("pathlib").Path(__file__).resolve().parents[1])
FIGDIR = str(__import__("pathlib").Path(__file__).resolve().parent / "figs_web")
MD = os.path.join(ROOT, "paper/manuscript_combined_v1.md")
OUT = os.path.join(ROOT, "paper/manuscript_combined_v1.html")

def datauri(fn):
    with open(os.path.join(FIGDIR, fn), "rb") as f:
        b = base64.b64encode(f.read()).decode()
    return "data:image/jpeg;base64," + b

def figblock(imgs, cap):
    tags = "".join('<img src="%s" alt="%s">' % (datauri(fn), cap) for fn in imgs)
    return '<figure>%s<figcaption>%s</figcaption></figure>' % (tags, cap)

s = open(MD, encoding="utf-8").read()

anchors = [
 ("Stakeholder power is only the first, chosen because it is the parameter most theorized, least computed, and the one most in want of a runnable form.", "F6"),
 ("A minimal, replaceable transform makes that relation legible; a clever one would obscure it.", "F5"),
 ("These two numbers set up the demonstration's central observation.", "F1"),
 ("and that the distinctness is different for each stock.", "F2"),
 ("rather than as an empirical discovery about Shanghai.", "F3"),
 ("without any claim about who ought to control the renewed city.", "F4"),
 ("Height, footprint, vintage and slenderness do not tell you who holds a building.", "E"),
]
for anchor, tag in anchors:
    assert anchor in s, "anchor missing: " + tag
    s = s.replace(anchor, anchor + "\n\n[[FIG:%s]]" % tag, 1)

html_body = markdown.markdown(s, extensions=["tables", "fenced_code", "sane_lists"])

FIGS = {
 "F6": (["F6_parameters.jpg"], "Fig. 1. Parameter families — the parameter-family overview; power is the one family with no operationalised generative method, the empty slot the instrument fills."),
 "F5": (["F5_loop.jpg"], "Fig. 2. The loop — read → map → transform → read back, on Laoximen's real geometry; the transform cell is a swappable lens, with ghost cards for vintage, price, environment, and regulation."),
 "F1": (["F1_atlas.jpg"], "Fig. 3. Site atlas — the eight sites as found: stakeholder-coloured figure-ground, skyline silhouette, nine-axis fingerprint radar, and GFA-holding bar. FAR 1.47–4.28, h_max 132–606 m, resident GFA share 16.5–91.8 %."),
 "F2": (["F2_gallery.jpg"], "Fig. 4. Power-configuration gallery — eight sites (rows) against as-found plus four configurations (columns), same site, same camera. Different inputs of power redistribute holders and heights on a fixed ground plan; a red frame marks a fabric that cannot supply the target."),
 "F3": (["F3_fingerprints.jpg"], "Fig. 5. Cross-case fingerprints — one metric per panel, one line per site; the final panel is the rank-preservation heatmap. A fabric keeps its identity except along the one dimension a configuration grips."),
 "F4": (["F4_reachability_all.jpg"], "Fig. 6. Navigable parameter space — the eight 5×5 reachability grids on one page; unreachable cells washed out. Zhangjiang 0/25 beside Pengpu 20/25. Every unreachable cell fails on the state axis; within the swept window (developer ≤ 0.70, state ≤ 0.40) the developer axis fails in none of the 200 cells."),
 "E":  (["E1_pca_stakeholder.jpg", "E2_pca_variants.jpg", "E3_ae_vae.jpg"], "Fig. 7. The map stage in embedding space — PCA, autoencoder, and β-VAE over 11,397 buildings. With land use in the features the classes separate (≈88–90 %); on morphology alone balanced accuracy collapses to 34.7 % (four-class baseline 25 %). The map is a declarative lookup, not a morphological inference."),
}
FIGS = {k: (v[0], v[1].replace(" — ", ": ")) for k, v in FIGS.items()}
for tag, (imgs, cap) in FIGS.items():
    html_body = html_body.replace("<p>[[FIG:%s]]</p>" % tag, figblock(imgs, cap))
assert "[[FIG:" not in html_body, "unreplaced figure placeholder"

LIGHT = ("--bg:#faf9f6;--fg:#1b1a17;--muted:#6c6b65;--faint:#8f8d86;--rule:#e5e2da;--hair:#efece4;"
         "--accent:#7a2e2e;--card:#f2f0e9;--link:#8a3324;"
         "--sh1:0 1px 2px rgba(35,30,22,.05);--sh2:0 2px 8px rgba(35,30,22,.05),0 16px 38px rgba(35,30,22,.10);"
         "--glass:rgba(250,249,246,.72);--glassbrd:rgba(255,255,255,.65);")
DARK = ("--bg:#141416;--fg:#e8e6e0;--muted:#a29f98;--faint:#78766f;--rule:#29292f;--hair:#212127;"
        "--accent:#d98b74;--card:#1d1d22;--link:#e0a08a;"
        "--sh1:0 1px 2px rgba(0,0,0,.35);--sh2:0 2px 8px rgba(0,0,0,.35),0 18px 44px rgba(0,0,0,.55);"
        "--glass:rgba(20,20,22,.6);--glassbrd:rgba(255,255,255,.09);")

CSS = """
:root{ %s }
@media (prefers-color-scheme:dark){ :root{ %s } }
:root[data-theme=light]{ %s }
:root[data-theme=dark]{ %s }
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%%; scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){ html{scroll-behavior:auto} *{transition:none!important} }
body{ margin:0; background:var(--bg); color:var(--fg);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Songti SC","Source Han Serif SC",serif;
  font-size:18px; line-height:1.64; letter-spacing:-.003em;
  font-optical-sizing:auto; -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility; }
.wrap{ max-width:816px; margin:0 auto; padding:66px 24px 128px; }
h1{ font-size:2.0rem; line-height:1.08; margin:.1em 0 .25em; letter-spacing:-.022em; font-weight:600; }
h2{ font-size:1.34rem; line-height:1.2; margin:2.9em 0 .6em; letter-spacing:-.014em; font-weight:600; }
h2::before{ content:""; display:block; width:2.1rem; height:2px; border-radius:2px;
  background:var(--accent); opacity:.5; margin:0 0 1.05em; }
h3{ font-size:1.07rem; margin:1.95em 0 .4em; letter-spacing:-.006em; font-weight:600; }
h2 + h3, h2 + p{ margin-top:.65em; }
h3 + p{ margin-top:0; }
p{ margin:0 0 1.04em; }
a{ color:var(--link); text-decoration:none; border-bottom:1px solid color-mix(in srgb,var(--link) 30%%,transparent); }
a:hover{ border-bottom-color:var(--link); }
strong{ font-weight:600; }
em{ font-style:italic; }
hr{ display:none; }
.subtitle{ color:var(--muted); font-style:italic; font-size:.9rem; letter-spacing:0; margin:.35em 0 2.4em; line-height:1.55; }
blockquote{ margin:1.7em 0; padding:1em 1.15em; background:var(--card); border-left:2.5px solid var(--accent);
  border-radius:8px; box-shadow:var(--sh1); font-size:.88rem; line-height:1.58; color:var(--fg); letter-spacing:0; }
blockquote p{ margin:0; }
code,pre{ font-family:"SF Mono",ui-monospace,"JetBrains Mono",Menlo,Consolas,monospace; }
code{ font-size:.85em; letter-spacing:0; background:var(--card); padding:.1em .36em; border-radius:5px; }
pre{ background:var(--card); border:1px solid var(--hair); border-radius:10px; padding:15px 17px; overflow-x:auto;
  font-size:.8rem; line-height:1.55; margin:1.4em 0; box-shadow:var(--sh1); }
pre code{ background:none; padding:0; }
.tablewrap{ overflow-x:auto; margin:1.5em 0; border-radius:10px; -webkit-overflow-scrolling:touch; }
table{ border-collapse:collapse; width:100%%; font-size:.78rem; line-height:1.42; letter-spacing:.004em; }
th,td{ text-align:left; padding:8px 11px; border-bottom:1px solid var(--hair); vertical-align:top; white-space:nowrap; }
thead th{ border-top:1.5px solid var(--fg); border-bottom:1.25px solid var(--fg); font-weight:600; letter-spacing:.008em; }
tbody tr:last-child td{ border-bottom:1.5px solid var(--fg); }
td:first-child, th:first-child{ white-space:normal; }
figure{ margin:2.2em 0; }
figure img{ width:100%%; height:auto; display:block; border-radius:10px; background:#fff;
  box-shadow:var(--sh2); margin-bottom:.55em; }
figure img + img{ margin-top:10px; }
figcaption{ font-size:.78rem; line-height:1.55; letter-spacing:.006em; color:var(--muted); padding:0 3px; }
ol,ul{ padding-left:1.4em; margin:0 0 1.15em; }
li{ margin:.32em 0; }
::selection{ background:color-mix(in srgb,var(--accent) 26%%,transparent); }
.topbar{ position:fixed; top:0; left:0; right:0; height:46px; z-index:20;
  display:flex; align-items:center; gap:12px; padding:0 clamp(16px,4vw,44px);
  background:var(--glass); -webkit-backdrop-filter:blur(20px) saturate(180%%); backdrop-filter:blur(20px) saturate(180%%);
  border-top:1px solid var(--glassbrd); box-shadow:var(--sh1);
  transform:translateY(-102%%); opacity:0; transition:transform .4s cubic-bezier(.32,.72,0,1), opacity .3s; }
.topbar.show{ transform:none; opacity:1; }
.topbar-t{ font-size:.78rem; font-weight:600; letter-spacing:.012em; color:var(--muted);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:calc(100%% - 56px); }
.progress{ position:fixed; top:0; left:0; height:2px; width:100%%; z-index:21;
  background:var(--accent); transform:scaleX(0); transform-origin:left; will-change:transform; }
.themebtn{ position:fixed; top:11px; right:clamp(16px,4vw,44px); z-index:22;
  background:var(--glass); color:var(--fg);
  -webkit-backdrop-filter:blur(14px) saturate(160%%); backdrop-filter:blur(14px) saturate(160%%);
  border:1px solid var(--glassbrd); border-radius:999px; width:34px; height:28px; line-height:1;
  font:inherit; font-size:.82rem; cursor:pointer; box-shadow:var(--sh1); }
.themebtn:hover{ color:var(--accent); }
@media(max-width:600px){ body{font-size:16.5px} .wrap{padding:44px 16px 96px} h1{font-size:1.62rem} table{font-size:.7rem} }
@media print{
  .topbar,.progress,.themebtn{ display:none !important }
  html,body{ background:#fff; color:#111; font-size:12.5pt; line-height:2.0; letter-spacing:0; }
  .wrap{ max-width:none; margin:0; padding:0; }
  h1{ font-size:22pt; letter-spacing:-.01em; line-height:1.2 } h2{ font-size:16pt; margin:1.4em 0 .5em; line-height:1.25 }
  h2::before{ display:none } h3{ font-size:13pt; line-height:1.3 }
  h1,h2,h3{ break-after:avoid }
  .subtitle{ font-size:11pt; line-height:1.6 }
  p,li{ orphans:2; widows:2; line-height:2.0 }
  li{ margin:.5em 0 }
  a{ color:#111; border:none }
  figure,table,pre,blockquote{ break-inside:avoid }
  figure img{ box-shadow:none; border:1px solid #ccc }
  figcaption{ font-size:10.5pt; line-height:1.5 }
  blockquote{ box-shadow:none; background:#f4f2ec; font-size:11pt; line-height:1.6 }
  pre{ box-shadow:none; background:#f4f2ec; line-height:1.4 }
  .tablewrap{ overflow:visible }
  table{ font-size:9pt; line-height:1.35 } thead th,tbody tr:last-child td{ border-color:#111 }
}
""" % (LIGHT, DARK, LIGHT, DARK)

JS = """
(function(){
 var btn=document.createElement('button'); btn.className='themebtn'; btn.textContent='◐';
 btn.setAttribute('aria-label','toggle light or dark theme');
 function cur(){var t=document.documentElement.getAttribute('data-theme');
   return t||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');}
 btn.onclick=function(){document.documentElement.setAttribute('data-theme', cur()==='dark'?'light':'dark');};
 document.body.appendChild(btn);
 var bar=document.createElement('div'); bar.className='topbar';
 bar.innerHTML='<span class="topbar-t">Reading the Found City through Stakeholder Power</span>';
 document.body.appendChild(bar);
 var prog=document.createElement('div'); prog.className='progress'; document.body.appendChild(prog);
 var tick=false;
 function upd(){ var h=document.documentElement, max=h.scrollHeight-h.clientHeight, p=max>0?h.scrollTop/max:0;
   prog.style.transform='scaleX('+p.toFixed(4)+')';
   bar.classList.toggle('show', h.scrollTop>140); tick=false; }
 addEventListener('scroll', function(){ if(!tick){ requestAnimationFrame(upd); tick=true; } }, {passive:true});
 document.querySelectorAll('table').forEach(function(t){ if(t.parentElement.classList.contains('tablewrap'))return;
   var w=document.createElement('div'); w.className='tablewrap'; t.parentNode.insertBefore(w,t); w.appendChild(t); });
 upd();
})();
"""

doc = ("<!doctype html><html lang=en><head><meta charset=utf-8>"
 "<meta name=viewport content='width=device-width,initial-scale=1'>"
 "<title>Reading the Found City through Stakeholder Power</title>"
 "<style>%s</style></head><body><div class=wrap>%s</div><script>%s</script></body></html>"
 % (CSS, html_body, JS))

open(OUT, "w", encoding="utf-8").write(doc)
print("wrote", OUT)
print("size: %.2f MB" % (len(doc.encode("utf-8"))/1024/1024))
print("figures embedded:", len(FIGS))
