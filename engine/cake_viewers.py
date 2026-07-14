"""
cake_viewers.py — Task D: interactive Three.js viewers + headless screenshots from the SAME scene.

    python3 cake_viewers.py build     # viewer_<slug>.html x 8   (+ satellite ground, + _lib)
    python3 cake_viewers.py shots     # shot_<slug>_<cfg>.png + shot_sky_<slug>_<cfg>.png, from those same viewers
    python3 cake_viewers.py index     # viewers_index.html (thumbnails from the shots)
    python3 cake_viewers.py all

Screenshots need a browser. On this sandbox:
    pip install playwright --break-system-packages && playwright install chromium
    # chrome ships without libXdamage here; unpack it once into /tmp/xlibs:
    mkdir -p /tmp/xlibs && cd /tmp/xlibs && apt-get download libxdamage1 && dpkg-deb -x libxdamage1_*.deb .
cmd_shots picks /tmp/xlibs up automatically via LD_LIBRARY_PATH. Rendering is SwiftShader (software
WebGL), so the PNGs are reproducible on any machine, with or without a GPU.

One tool, many case studies: input different power -> different form grows.
Configurations are named by FORM, never by who was taken:
    current | developer-led | state-led | resident-led | shared

Everything on screen is read from files already on disk:
    out/cake/skyline_<slug>.json        per-scenario [bid, height_m, holder]
    out/cake/metrics_cake_all.json      fingerprints + gfa shares per scenario
    data/<slug>/buildings.parquet       footprints (EPSG:32651), via pf_common.load_buildings

Footprints are frozen by the cake model, so one geometry payload serves all five
configurations; only height and holder change. Non-destructive: writes only under
out/cake_figs/.
"""
import base64
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pf_common as C  # noqa: E402

CAKE = HERE / "out" / "cake"
FIGS = HERE / "out" / "cake_figs"
SHOTS = FIGS / "shots"
LIB = FIGS / "_lib"
SATD = FIGS / "sat"

# corner mapping (NEXT_RUN_10): figures use mode B = grow
CONFIGS = [
    ("current", "current", "Current"),
    ("developer_led", "capital_deepen_B", "Developer-led"),
    ("state_led", "state_civic_B", "State-led"),
    ("resident_led", "resident_retain_B", "Resident-led"),
    ("shared", "shared_commons_B", "Shared"),
]
ORDER = [c[0] for c in CONFIGS]
LABEL = {c[0]: c[2] for c in CONFIGS}
SCEN = {c[0]: c[1] for c in CONFIGS}

SH_IDX = ["state", "developer", "resident", "informal", "unknown"]
SH_EN = {"state": "state", "developer": "developer", "resident": "resident",
         "informal": "informal", "unknown": "unknown"}

SITES = ["lujiazui", "nanjingxi", "caoyang", "pengpu", "laoximen", "yuyuan", "dapuqiao", "zhangjiang"]

FAMILY_EN = {
    "lujiazui": "capital / supertall CBD",
    "nanjingxi": "capital / commercial spine",
    "caoyang": "danwei / workers' village",
    "pengpu": "danwei / workers' village",
    "laoximen": "old town / lilong shikumen",
    "yuyuan": "old town / lilong",
    "dapuqiao": "old town / lilong + Tianzifang",
    "zhangjiang": "industry / tech new town",
}

THREE_URL = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
ORBIT_URL = "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"

SAT_FACTOR = 2.0  # must stay <= 3 (20 hangs the viewer)

# Disk-cache the Esri tiles so a big site (zhangjiang needs ~56 tiles) can be fetched over
# several runs instead of one long one. pf_common.ground_sat is reused unchanged; this only
# switches on contextily's own tile cache.
try:
    import contextily as _ctx
    (FIGS / "_tilecache").mkdir(parents=True, exist_ok=True)
    _ctx.set_cache_dir(str(FIGS / "_tilecache"))
except Exception as _e:  # pragma: no cover
    print("  ! tile cache off:", _e)


# ------------------------------------------------------------------ libs
def libs():
    """three.js + OrbitControls, cached under out/cake_figs/_lib/ so the build is repeatable offline."""
    import urllib.request
    LIB.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, url in (("three.min.js", THREE_URL), ("OrbitControls.js", ORBIT_URL)):
        p = LIB / name
        if not p.exists():
            with urllib.request.urlopen(url, timeout=60) as r:
                p.write_bytes(r.read())
        out[name] = p.read_text(encoding="utf-8")
    return out["three.min.js"], out["OrbitControls.js"]


# ------------------------------------------------------------------ data
def load_site(slug):
    """-> (payload dict for JS, sat_status str)"""
    recs = C.load_buildings(slug)
    sky = json.load(open(CAKE / ("skyline_%s.json" % slug), encoding="utf-8"))
    allm = json.load(open(CAKE / "metrics_cake_all.json", encoding="utf-8"))
    meta = allm[slug]["site"]

    # bid -> index
    bids = [r["bid"] for r in recs]
    pos = {b: i for i, b in enumerate(bids)}
    n = len(recs)

    polys = [p for r in recs for p in C._polys(r["geom"])]
    minx = min(p.bounds[0] for p in polys); miny = min(p.bounds[1] for p in polys)
    maxx = max(p.bounds[2] for p in polys); maxy = max(p.bounds[3] for p in polys)

    # footprint parts: [bid_index, [[x,y],...]] in local metres
    parts = []
    for r in recs:
        i = pos[r["bid"]]
        for poly in C._polys(r["geom"]):
            ps = poly.simplify(0.8)
            xy = [[round(x - minx, 1), round(y - miny, 1)] for x, y in list(ps.exterior.coords)[:-1]]
            if len(xy) >= 3:
                parts.append([i, xy])

    # per-config height + holder arrays, aligned to bid index
    H, S, missing = {}, {}, {}
    for cfg in ORDER:
        key = SCEN[cfg]
        rows = sky.get(key)
        if rows is None:
            raise KeyError("%s: skyline has no scenario %s" % (slug, key))
        h = [0.0] * n
        s = [SH_IDX.index("unknown")] * n
        seen = 0
        for bid, ht, holder in rows:
            i = pos.get(int(bid))
            if i is None:
                continue
            h[i] = round(float(ht), 1)
            s[i] = SH_IDX.index(holder) if holder in SH_IDX else SH_IDX.index("unknown")
            seen += 1
        H[cfg] = h; S[cfg] = s; missing[cfg] = n - seen
    if any(missing.values()):
        print("   ! skyline/parquet bid mismatch:", missing)

    # metrics per config, straight from metrics_cake_all.json
    met = {}
    for cfg in ORDER:
        d = allm[slug].get(SCEN[cfg], {})
        fp = d.get("fingerprint", {})
        met[cfg] = {
            "far": fp.get("far"), "h_max": fp.get("h_max"), "h_cv": fp.get("h_cv"),
            "coverage": fp.get("coverage"), "h_mean": fp.get("h_mean"), "n": fp.get("n"),
            "shares": d.get("shares_gfa", {}),
            "gfa_change_pct": d.get("gfa_change_pct"),
        }

    # satellite ground plane (real Esri imagery), via the existing pf_common pipeline
    SATD.mkdir(parents=True, exist_ok=True)
    sat, sext, status = None, None, ""
    if os.environ.get("NO_SAT"):
        status = "satellite off (NO_SAT) -> neutral ground plane"
    else:
        try:
            sat, sext = C.ground_sat(minx, miny, maxx, maxy, SATD / (slug + ".jpg"), SAT_FACTOR)
            status = "esri ok (factor %.1f)" % SAT_FACTOR
        except Exception as e:
            status = "FAILED (%s) -> neutral ground plane" % type(e).__name__
            print("   ! satellite failed for %s: %r" % (slug, e))

    hmax = max(max(H[c]) for c in ORDER)
    span = max(maxx - minx, maxy - miny)
    d = {
        "slug": slug, "name": meta["name"], "family": FAMILY_EN.get(slug, meta.get("family", "")),
        "familyZh": meta.get("family", ""), "areaKm2": meta.get("area_km2"), "nBld": n,
        "colors": C.SH_COLOR, "shIdx": SH_IDX, "shEn": SH_EN,
        "order": ORDER, "labels": LABEL, "scen": SCEN,
        "parts": parts, "H": H, "S": S, "metrics": met,
        "sat": sat, "satExtent": sext,
        "box": {"w": round(maxx - minx, 1), "h": round(maxy - miny, 1),
                "span": round(span, 1), "hmax": round(hmax, 1)},
    }
    return d, status


# ------------------------------------------------------------------ viewer JS
VIEWER_JS = r"""
const G = __GEOM__;
const COL = G.colors, SH = G.shIdx;
let scene, cam, renderer, controls, meshes = [], mats = {}, cur = G.order[0], view = "oblique";
let SHOT = new URLSearchParams(location.search).has("shot");
let CAM = {};   // camera presets, identical for every configuration of this site

// az/el/fov/target are fixed per view; the distance is FITTED to the site's building box so
// the frame is tight at any aspect ratio. Identical for all five configurations of a site
// (footprints are frozen and the box uses the tallest configuration), so the five PNGs of a
// site are directly comparable and match what the viewer shows.
const VIEWS = {
  oblique: {az: -55, el: 30, fov: 40, tzf: 0.28, margin: 1.05},
  skyline: {az: -90, el: 4.5, fov: 16, tzf: 0.50, margin: 1.03}
};

function fitCam(v) {
  const p = VIEWS[v], b = G.box;
  const hmax = Math.max(b.hmax, 20);
  const az = p.az * Math.PI / 180, el = p.el * Math.PI / 180;
  const dir = new THREE.Vector3(Math.cos(el) * Math.cos(az), Math.cos(el) * Math.sin(az), Math.sin(el));
  const view = dir.clone().negate();
  const right = new THREE.Vector3().crossVectors(view, new THREE.Vector3(0, 0, 1)).normalize();
  const upv = new THREE.Vector3().crossVectors(right, view).normalize();
  const tz = hmax * p.tzf;
  const vt = Math.tan(p.fov * Math.PI / 360), ht = vt * cam.aspect;
  const cx = b.w / 2, cy = b.h / 2;
  let D = 0;
  for (const sx of [0, b.w]) for (const sy of [0, b.h]) for (const sz of [0, hmax]) {
    const c = new THREE.Vector3(sx - cx, sy - cy, sz - tz);
    const x = c.dot(right), y = c.dot(upv), z = c.dot(dir);
    D = Math.max(D, z + Math.abs(x) / ht, z + Math.abs(y) / vt);
  }
  D *= p.margin;
  return {pos: [dir.x * D, dir.y * D, dir.z * D], target: [0, 0, tz], fov: p.fov,
          azDeg: p.az, elDeg: p.el, dist: Math.round(D), fovDeg: p.fov};
}

function build() {
  const mkMat = (sh) => new THREE.MeshLambertMaterial(
    {color: new THREE.Color(COL[sh] || "#b8b8b8").convertSRGBToLinear()});
  for (const sh of SH) mats[sh] = mkMat(sh);
  const grp = new THREE.Group();
  for (const [bi, ring] of G.parts) {
    const shape = new THREE.Shape();
    ring.forEach((pt, i) => i ? shape.lineTo(pt[0], pt[1]) : shape.moveTo(pt[0], pt[1]));
    const geo = new THREE.ExtrudeGeometry(shape, {depth: 1, bevelEnabled: false});
    const me = new THREE.Mesh(geo, mats[SH[G.S[cur][bi]]]);
    me.userData = {bi: bi};
    me.scale.z = 0.01;
    grp.add(me); meshes.push(me);
  }
  return grp;
}

function applyConfig(k, snap) {
  cur = k;
  const H = G.H[k], S = G.S[k];
  for (const m of meshes) {
    const bi = m.userData.bi;
    m.material = mats[SH[S[bi]]];
    m.userData.h = Math.max(H[bi], 0.5);
    m.scale.z = snap ? m.userData.h : 0.01;
  }
  document.querySelectorAll(".scn button").forEach(b => b.classList.toggle("on", b.dataset.s === k));
  updateHUD();
}

function setView(v) {
  view = v;
  const p = CAM[v] = fitCam(v);
  cam.fov = p.fov; cam.updateProjectionMatrix();
  cam.position.set(p.pos[0], p.pos[1], p.pos[2]);
  if (controls) { controls.target.set(p.target[0], p.target[1], p.target[2]); controls.update(); }
  else cam.lookAt(p.target[0], p.target[1], p.target[2]);
  document.querySelectorAll(".vw button").forEach(b => b.classList.toggle("on", b.dataset.v === v));
}

function fmt(x, d) { return (x === null || x === undefined) ? "--" : Number(x).toFixed(d); }

function updateHUD() {
  const el = document.getElementById("mx"); if (!el) return;
  const m = G.metrics[cur], s = m.shares || {};
  const bar = ["state", "developer", "resident"].map(k =>
    '<span style="display:inline-block;height:8px;width:' + ((s[k] || 0) * 100).toFixed(1) +
    '%;background:' + COL[k] + '"></span>').join("");
  el.innerHTML =
    '<div class="metric"><span>FAR</span><b>' + fmt(m.far, 2) + '</b></div>' +
    '<div class="metric"><span>tallest</span><b>' + fmt(m.h_max, 0) + ' m</b></div>' +
    '<div class="metric"><span>height CV</span><b>' + fmt(m.h_cv, 2) + '</b></div>' +
    '<div class="metric"><span>coverage</span><b>' + fmt((m.coverage || 0) * 100, 0) + '%</b></div>' +
    '<div class="bar">' + bar + '</div>' +
    '<div class="shl">GFA held: state ' + fmt((s.state || 0) * 100, 0) + '% · developer ' +
    fmt((s.developer || 0) * 100, 0) + '% · resident ' + fmt((s.resident || 0) * 100, 0) + '%</div>';
}

function init() {
  const st = document.getElementById("stage");
  const w = st.clientWidth, h = st.clientHeight;
  scene = new THREE.Scene();
  cam = new THREE.PerspectiveCamera(42, w / h, 1, 60000); cam.up.set(0, 0, 1);
  renderer = new THREE.WebGLRenderer({canvas: document.getElementById("cv3d"), antialias: true,
                                      preserveDrawingBuffer: true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(w, h);
  renderer.setClearColor(SHOT ? 0xffffff : 0xd9e3ea);   // white sky for the paper PNGs
  if (THREE.sRGBEncoding !== undefined) renderer.outputEncoding = THREE.sRGBEncoding;
  scene.add(new THREE.HemisphereLight(0xffffff, 0xb9c4c8, 0.38));
  scene.add(new THREE.AmbientLight(0xffffff, 0.16));
  const dl = new THREE.DirectionalLight(0xffffff, 0.66); dl.position.set(0.6, -1, 1.4); scene.add(dl);

  const b = G.box, cx = b.w / 2, cy = b.h / 2;
  const root = new THREE.Group();
  window.__satReady = !G.sat;
  if (G.sat) {
    const tx = new THREE.TextureLoader().load(G.sat, () => { window.__satReady = true; });
    if (THREE.sRGBEncoding !== undefined) tx.encoding = THREE.sRGBEncoding;
    const se = G.satExtent, gw = se[2] - se[0], gh = se[3] - se[1];
    const gp = new THREE.Mesh(new THREE.PlaneGeometry(gw, gh),
                              new THREE.MeshBasicMaterial({map: tx}));
    gp.position.set((se[0] + se[2]) / 2, (se[1] + se[3]) / 2, -0.3);
    root.add(gp);
  } else {
    const gp = new THREE.Mesh(new THREE.PlaneGeometry(b.span * 2.2, b.span * 2.2),
                              new THREE.MeshBasicMaterial({color: 0xdfe5e7}));
    gp.position.set(cx, cy, -0.5); root.add(gp);
  }
  root.add(build());
  root.position.set(-cx, -cy, 0);
  scene.add(root);

  controls = new THREE.OrbitControls(cam, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.08;
  setView("oblique");
  applyConfig(cur, SHOT);           // in shot mode buildings start at full height
  window.addEventListener("resize", onResize);
  animate();
  window.__ready = true;
}

function onResize() {
  const s = document.getElementById("stage");
  cam.aspect = s.clientWidth / s.clientHeight; cam.updateProjectionMatrix();
  renderer.setSize(s.clientWidth, s.clientHeight);
  setView(view);
}

function animate() {
  requestAnimationFrame(animate);
  if (!SHOT) for (const m of meshes) {
    const t = m.userData.h || 1;
    if (m.scale.z < t) m.scale.z = Math.min(t, m.scale.z + t * 0.09 + 0.6);
  }
  controls.update();
  renderer.render(scene, cam);
}

// ---- headless screenshot API (same scene, same camera, no second renderer)
window.PF = {
  setConfig: (k) => { applyConfig(k, true); renderer.render(scene, cam); },
  setView: (v) => { setView(v); renderer.render(scene, cam); },
  camera: () => { const p = CAM[view]; return {view: view, azimuth_deg: p.azDeg, elevation_deg: p.elDeg,
                  distance_m: p.dist, fov_deg: p.fovDeg, target_local: p.target, up: "z"}; },
  ready: () => !!(window.__ready && window.__satReady),
  render: () => renderer.render(scene, cam)
};

window.addEventListener("DOMContentLoaded", () => {
  if (SHOT) document.body.classList.add("shotmode");
  init();
  document.querySelectorAll(".scn button").forEach(b => b.onclick = () => applyConfig(b.dataset.s, false));
  document.querySelectorAll(".vw button").forEach(b => b.onclick = () => setView(b.dataset.v));
  const c = document.getElementById("capbtn");
  if (c) c.onclick = () => {
    renderer.render(scene, cam);
    document.getElementById("cv3d").toBlob(bl => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(bl);
      a.download = G.slug + "_" + cur + "_" + view + ".png"; a.click();
    });
  };
});
"""

CSS = """
:root{--accent:#0f5e63;--ink:#1a1f22;--muted:#717b80;--line:#e6e9ea;--bg:#f7f8f7;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.65 "Helvetica Neue","PingFang SC",system-ui,sans-serif;}
.wrap{max-width:1180px;margin:0 auto;padding:20px 22px 40px;}
.kick{letter-spacing:.16em;text-transform:uppercase;font-size:11px;color:var(--muted);margin:0 0 6px;}
h1{font-size:24px;line-height:1.3;margin:0 0 6px;font-weight:750;}
h1 small{font-weight:500;color:var(--muted);font-size:15px;}
p.lead{margin:0 0 14px;color:#3a4347;max-width:900px;font-size:14.5px;}
#stage{position:relative;width:100%;height:66vh;min-height:460px;border-radius:12px;overflow:hidden;
background:#d9e3ea;border:1px solid var(--line);}
#cv3d{width:100%;height:100%;display:block;}
.hud{position:absolute;left:14px;top:14px;display:flex;flex-direction:column;gap:8px;max-width:330px;}
.scn,.vw,.cap{display:flex;flex-wrap:wrap;gap:6px;}
.scn button,.vw button,.cap button{font:inherit;font-size:12px;font-weight:600;border:1px solid var(--line);
background:#fff;color:var(--ink);border-radius:20px;padding:5px 11px;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.06);}
.scn button.on,.vw button.on{background:var(--accent);border-color:var(--accent);color:#fff;}
.vw button.on{background:#334a52;border-color:#334a52;}
.card{background:rgba(255,255,255,.93);backdrop-filter:blur(6px);border:1px solid var(--line);
border-radius:10px;padding:9px 12px;font-size:12px;box-shadow:0 1px 6px rgba(0,0,0,.08);}
.metric{display:flex;justify-content:space-between;gap:14px;}.metric b{font-variant-numeric:tabular-nums;}
.bar{margin:7px 0 4px;height:8px;background:#eceeef;border-radius:4px;overflow:hidden;font-size:0;}
.shl{font-size:10.5px;color:var(--muted);line-height:1.4;}
.legend{display:flex;flex-wrap:wrap;gap:6px 11px;margin-top:2px;font-size:11.5px;color:var(--muted);}
.legend i{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:4px;}
.hint{position:absolute;right:14px;bottom:12px;font-size:11px;color:#5a6468;
background:rgba(255,255,255,.72);padding:2px 7px;border-radius:6px;}
.foot{font-size:12px;color:var(--muted);margin-top:10px;}
table{border-collapse:collapse;width:100%;margin:18px 0 6px;font-size:13px;}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:center;}
thead th{background:var(--accent);color:#fff;}tbody tr:nth-child(odd){background:#f4f7f7;}
tbody td:first-child{text-align:left;font-weight:600;}
body.shotmode{background:#fff;}
body.shotmode .wrap{max-width:none;margin:0;padding:0;}
body.shotmode .hud,body.shotmode .hint,body.shotmode .kick,body.shotmode h1,
body.shotmode p.lead,body.shotmode table,body.shotmode .foot{display:none!important;}
body.shotmode #stage{width:100vw;height:100vh;min-height:0;border:0;border-radius:0;background:#fff;}
"""

HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>@@TITLE@@</title>
<style>@@CSS@@</style></head><body>
<div class="wrap">
<p class="kick">power_to_form · parametric case study · @@FAMILY@@</p>
<h1>@@NAME@@ <small>— input a different power, a different form grows</small></h1>
<p class="lead">One street, one engine, five configurations. Footprints are the real Baidu building outlines of
@@NAME@@ (@@N@@ buildings, @@AREA@@ km²); heights and holders are the engine's output for each power
configuration. Massing is coloured by <b>who holds the floor area</b>. Drag to orbit, scroll to zoom,
right-drag to pan. <b>Oblique</b> / <b>Skyline</b> reproduce the two camera views used in the paper figures.</p>
<div id="stage"><canvas id="cv3d"></canvas>
<div class="hud">
  <div class="scn">@@SCN@@</div>
  <div class="vw"><button data-v="oblique" class="on">Oblique</button><button data-v="skyline">Skyline</button></div>
  <div class="cap"><button id="capbtn">Save PNG</button></div>
  <div class="card" id="mx"></div>
  <div class="card"><div class="legend">@@LEGEND@@</div></div>
</div>
<div class="hint">drag = orbit · scroll = zoom · right-drag = pan</div></div>
<p class="foot">Ground: @@SATNOTE@@ · geometry EPSG:32651 · configurations are engine outputs (grow mode),
teaching instrument, not a planning forecast.</p>
@@TABLE@@
</div>
<script>@@THREE@@</script><script>@@ORBIT@@</script><script>@@VIEWER@@</script></body></html>"""


def metrics_table(d):
    rows = ""
    for cfg in ORDER:
        m = d["metrics"][cfg]; s = m["shares"] or {}
        f = lambda v, k=2: "--" if v is None else ("%.*f" % (k, v))
        rows += ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s%%</td>"
                 "<td>%.0f%%</td><td>%.0f%%</td><td>%.0f%%</td></tr>") % (
            LABEL[cfg], f(m["far"]), f(m["h_max"], 0), f(m["h_cv"]),
            f((m["coverage"] or 0) * 100, 0),
            (s.get("state", 0)) * 100, (s.get("developer", 0)) * 100, (s.get("resident", 0)) * 100)
    return ("<table><thead><tr><th>configuration</th><th>FAR</th><th>tallest (m)</th><th>height CV</th>"
            "<th>coverage</th><th>state GFA</th><th>developer GFA</th><th>resident GFA</th></tr></thead>"
            "<tbody>%s</tbody></table>") % rows


def build_viewer(slug, three, orbit):
    d, sat_status = load_site(slug)
    scn = "".join('<button data-s="%s"%s>%s</button>' % (c, ' class="on"' if c == ORDER[0] else "", LABEL[c])
                  for c in ORDER)
    legend = " ".join('<span><i style="background:%s"></i>%s</span>' % (C.SH_COLOR[s], SH_EN[s])
                      for s in ("state", "developer", "resident", "unknown"))
    satnote = ("real Esri satellite imagery of this street" if d["sat"]
               else "NEUTRAL PLANE (satellite fetch failed for this site)")
    geom = json.dumps(d, separators=(",", ":"))
    html = HTML
    for k, v in {
        "@@TITLE@@": "%s — five power configurations" % d["name"],
        "@@CSS@@": CSS, "@@NAME@@": d["name"], "@@FAMILY@@": d["family"],
        "@@N@@": str(d["nBld"]), "@@AREA@@": "%.2f" % (d["areaKm2"] or 0),
        "@@SCN@@": scn, "@@LEGEND@@": legend, "@@SATNOTE@@": satnote,
        "@@TABLE@@": metrics_table(d),
        "@@THREE@@": three, "@@ORBIT@@": orbit,
        "@@VIEWER@@": VIEWER_JS.replace("__GEOM__", geom),
    }.items():
        html = html.replace(k, v)
    FIGS.mkdir(parents=True, exist_ok=True)
    p = FIGS / ("viewer_%s.html" % slug)
    p.write_text(html, encoding="utf-8")
    return p, d, sat_status


def cmd_build(only=None, force=False):
    """Incremental: sites whose viewer already exists are skipped unless force."""
    three, orbit = libs()
    sp = FIGS / "_build_status.json"
    status = json.load(open(sp)) if sp.exists() else {}
    todo = only or SITES
    for slug in todo:
        if not force and (FIGS / ("viewer_%s.html" % slug)).exists() and slug in status:
            print("  %-11s skip (exists)" % slug); continue
        p, d, st = build_viewer(slug, three, orbit)
        mb = p.stat().st_size / 1e6
        status[slug] = {"sat": st, "html": str(p), "mb": round(mb, 2),
                        "n": d["nBld"], "span_m": d["box"]["span"], "hmax_m": d["box"]["hmax"]}
        print("  %-11s %5.1f MB  n=%-5d span=%-6.0fm  sat: %s" % (slug, mb, d["nBld"], d["box"]["span"], st), flush=True)
        json.dump(status, open(sp, "w"), indent=1)
    return status


# ------------------------------------------------------------------ shots
SHOT_W, SHOT_H = 1600, 1000          # oblique massing   -> shot_<slug>_<config>.png
SKY_W, SKY_H = 1800, 620             # low-angle skyline -> shot_sky_<slug>_<config>.png


def cmd_shots(only=None, views=None):
    import os
    from playwright.sync_api import sync_playwright
    # sandbox only: chrome needs libXdamage.so.1, unpacked from the distro .deb into /tmp/xlibs
    _xl = "/tmp/xlibs/usr/lib/x86_64-linux-gnu"
    if os.path.isdir(_xl):
        os.environ["LD_LIBRARY_PATH"] = _xl + ":" + os.environ.get("LD_LIBRARY_PATH", "")
    FIGS.mkdir(parents=True, exist_ok=True)
    mp = FIGS / "shots_manifest.json"
    prev = json.load(open(mp)) if mp.exists() else None
    manifest = {"generator": "engine/cake_viewers.py (Three.js r128, headless Chromium via Playwright)",
                "note": "PNGs are captured from the same Three.js scene as viewer_<slug>.html "
                        "(?shot=1 hides the UI chrome). No second 3D pipeline is used.",
                "mode": "B (grow)", "corner_map": {c: SCEN[c] for c in ORDER},
                "views": {"massing": "oblique, %dx%d px" % (SHOT_W, SHOT_H),
                          "skyline": "near-orthographic elevation, %dx%d px" % (SKY_W, SKY_H)},
                "shots": []}
    todo = only or SITES
    vsel = views or ["massing", "skyline"]
    if prev:  # keep shots we are not re-rendering in this chunk
        manifest["shots"] = [s for s in prev.get("shots", [])
                             if not (s["site"] in todo and s["view"] in vsel)]
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chromium", args=[
            "--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader", "--disable-dev-shm-usage"])
        for slug in todo:
            url = (FIGS / ("viewer_%s.html" % slug)).as_uri() + "?shot=1"
            for view, (w, h) in (("massing", (SHOT_W, SHOT_H)), ("skyline", (SKY_W, SKY_H))):
                if view not in vsel:
                    continue
                page = br.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
                page.goto(url, wait_until="load", timeout=120000)
                page.wait_for_function("window.PF && window.PF.ready()", timeout=120000)
                page.evaluate("window.PF.setView('%s')" % ("oblique" if view == "massing" else "skyline"))
                cam = page.evaluate("window.PF.camera()")
                for cfg in ORDER:
                    page.evaluate("window.PF.setConfig('%s')" % cfg)
                    page.wait_for_timeout(260)
                    page.evaluate("window.PF.render()")
                    stem = ("shot_%s_%s" % (slug, cfg.replace("_", "-")) if view == "massing"
                            else "shot_sky_%s_%s" % (slug, cfg.replace("_", "-")))
                    out = FIGS / (stem + ".png")
                    page.locator("#cv3d").screenshot(path=str(out))
                    manifest["shots"].append({
                        "file": out.name, "site": slug, "config": cfg,
                        "config_label": LABEL[cfg], "scenario_key": SCEN[cfg], "view": view,
                        "width_px": w, "height_px": h, "camera": cam})
                    print("   %s" % out.name, flush=True)
                page.close()
                manifest["shots"].sort(key=lambda s: (SITES.index(s["site"]), s["view"], s["config"]))
                json.dump(manifest, open(mp, "w"), indent=1)
        br.close()
    json.dump(manifest, open(mp, "w"), indent=1)
    print("  -> %d PNGs, MANIFEST.json" % len(manifest["shots"]))
    return manifest


# ------------------------------------------------------------------ index
def thumb(p, width=460):
    from PIL import Image
    im = Image.open(p).convert("RGB")
    im.thumbnail((width, width), Image.LANCZOS)
    import io
    b = io.BytesIO(); im.save(b, "JPEG", quality=78)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


ONE_LINER = {
    "lujiazui": "supertall CBD: capital already holds the skyline; more capital only sharpens it.",
    "nanjingxi": "commercial spine: dense mid-rise fabric that every power can still reshape.",
    "caoyang": "workers' village: even slab rows, low CV; power shows up as who rebuilds them.",
    "pengpu": "workers' village at scale: the same slab logic across 3.3 km².",
    "laoximen": "lilong shikumen: fine grain, low and flat; the corner configurations diverge hardest here.",
    "yuyuan": "old-town lilong beside the garden: tight grain, tourist edge.",
    "dapuqiao": "lilong + Tianzifang: fine grain with a creative-economy overlay.",
    "zhangjiang": "tech new town: 18.3 km² of low-coverage campus, the loosest cake of the eight.",
}

INDEX_HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>power_to_form — eight streets, five power configurations</title><style>@@CSS@@
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;margin:20px 0;}
.card2{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:#fff;
box-shadow:0 1px 6px rgba(0,0,0,.05);display:flex;flex-direction:column;}
.card2 img{display:block;width:100%;height:auto;background:#d9e3ea;}
.card2 .bd{padding:12px 14px 14px;}
.card2 b{font-size:16px;color:var(--accent);}
.card2 .fam{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin:2px 0 6px;}
.card2 .one{font-size:13px;color:#3a4347;margin:0 0 10px;min-height:38px;}
.card2 a{display:block;text-align:center;font-size:13px;font-weight:600;color:#fff;background:var(--accent);
text-decoration:none;border-radius:8px;padding:7px 10px;}
.card2 .st{font-size:11px;color:var(--muted);margin-top:7px;}
</style></head><body>
<div class="wrap">
<p class="kick">Urban Stakeholder Workshop · power_to_form · interactive viewers</p>
<h1>Eight Shanghai streets. One engine. Five power configurations each.</h1>
<p class="lead">Every viewer below is the same tool with a different street loaded: real Baidu footprints on real
satellite imagery, massing coloured by who holds the floor area. Switch between
<b>current</b>, <b>developer-led</b>, <b>state-led</b>, <b>resident-led</b> and <b>shared</b> and watch a
different form grow out of the same ground. Thumbnails show the current state; each viewer opens by
double-click, no server needed.</p>
<div class="grid">@@CARDS@@</div>
<p class="foot">Corner mapping: developer-led = capital_deepen · state-led = state_civic ·
resident-led = resident_retain · shared = shared_commons, all in grow mode (B).
Static figures in the paper are screenshots of these exact scenes (shot_&lt;site&gt;_&lt;config&gt;.png).</p>
</div></body></html>"""


def cmd_index(status=None):
    status = status or json.load(open(FIGS / "_build_status.json"))
    allm = json.load(open(CAKE / "metrics_cake_all.json", encoding="utf-8"))
    cards = ""
    for slug in SITES:
        st = status.get(slug, {})
        tp = FIGS / ("shot_%s_current.png" % slug)
        img = thumb(tp) if tp.exists() else ""
        meta = allm[slug]["site"]
        sat_ok = st.get("sat", "").startswith("esri")
        cards += ('<div class="card2">%s<div class="bd"><b>%s</b>'
                  '<div class="fam">%s · %.2f km² · %d buildings</div>'
                  '<p class="one">%s</p>'
                  '<a href="viewer_%s.html">open viewer</a>'
                  '<div class="st">ground: %s</div></div></div>') % (
            ('<img src="%s" alt="%s current">' % (img, slug)) if img else "",
            meta["name"], FAMILY_EN.get(slug, ""), meta.get("area_km2", 0), meta.get("n", 0),
            ONE_LINER.get(slug, ""), slug,
            "real satellite" if sat_ok else "neutral plane (satellite unavailable)")
    html = INDEX_HTML.replace("@@CSS@@", CSS).replace("@@CARDS@@", cards)
    p = FIGS / "viewers_index.html"
    p.write_text(html, encoding="utf-8")
    print("  -> %s" % p)
    return p


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    args = sys.argv[2:]
    force = "--force" in args
    only = [a for a in args if a in SITES] or None
    if cmd in ("build", "all"):
        print("[build viewers]", flush=True); cmd_build(only, force)
    if cmd in ("shots", "all"):
        views = [v for v in ("massing", "skyline") if ("--" + v) in args] or None
        print("[shots]", flush=True); cmd_shots(only, views)
    if cmd in ("index", "all"):
        print("[index]", flush=True); cmd_index()
