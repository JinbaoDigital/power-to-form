"""
render.py — 第7步:出图(平面 / 3D 小多图 / N 体制互动切换 / 体制画廊 / index)
=================================================================
站点版 out/sites/<slug>.html  ——「这个地方在 现状 + 4 体制 下」:互动 3D 一键切换 + 静态小多图 + 指标表。
体制版 out/regimes/<regime>.html ——「这种权力在 12 个地方」:12 站 3D 画廊 + 指标表 + 配方。
首页 out/index.html —— 站点版 / 体制版 / 综合报告 / 算子图谱 / 教学 的入口。
自含单档(Three.js 内联),零外链,浅色无雾。
"""
import base64, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pf_common as C
import operators as OP

OUT = C.OUT
WEB = C.ROOT / "web"
STATE_ORDER = ["current", "developer_led", "state_led", "resident_self_build", "shared"]


def state_labels():
    regs = OP.load_regimes()
    lab = {"current": "现状"}
    for k, v in regs.items():
        lab[k] = v.get("label", k)
    return lab


PF_CSS = """
:root{--accent:#0f5e63;--ink:#1a1f22;--muted:#717b80;--line:#e6e9ea;--bg:#f7f8f7;}
*{box-sizing:border-box;}html{scroll-behavior:smooth;}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 "Helvetica Neue","PingFang SC","Microsoft YaHei",system-ui,sans-serif;}
.wrap{max-width:1100px;margin:0 auto;padding:0 22px 90px;}
.nav{max-width:1180px;margin:0 auto;padding:14px 22px 0;font-size:13px;color:var(--muted);}.nav a{color:var(--accent);text-decoration:none;margin-right:12px;}
.cover{max-width:1180px;margin:0 auto;padding:26px 22px 4px;}
.cover .kick{letter-spacing:.16em;text-transform:uppercase;font-size:11px;color:var(--muted);margin:0 0 8px;}
.cover h1{font-size:26px;line-height:1.3;margin:0 0 8px;font-weight:750;}
.cover p.lead{margin:0 0 14px;color:#3a4347;max-width:880px;font-size:15px;}
.hero{max-width:1180px;margin:14px auto 0;padding:0 22px;}
.hero p.lead2{margin:0 0 10px;color:var(--muted);font-size:13.5px;}
#stage{position:relative;width:100%;height:60vh;min-height:430px;border-radius:12px;overflow:hidden;background:#eaeef0;border:1px solid var(--line);}
#cv3d{width:100%;height:100%;display:block;}
.hud{position:absolute;left:14px;top:14px;display:flex;flex-direction:column;gap:9px;max-width:330px;}
.scn{display:flex;flex-wrap:wrap;gap:6px;}
.scn button{font:inherit;font-size:12px;font-weight:600;border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:20px;padding:5px 11px;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.06);}
.scn button.on{background:var(--accent);border-color:var(--accent);color:#fff;}
.hud .card{background:rgba(255,255,255,.93);backdrop-filter:blur(6px);border:1px solid var(--line);border-radius:10px;padding:9px 12px;font-size:12px;box-shadow:0 1px 6px rgba(0,0,0,.08);}
.hud .metric{display:flex;justify-content:space-between;gap:14px;}.hud .metric b{font-variant-numeric:tabular-nums;}
.legend{display:flex;flex-wrap:wrap;gap:7px 11px;margin-top:6px;font-size:11.5px;color:var(--muted);}
.legend i{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:4px;}
.hint3d{position:absolute;right:14px;bottom:12px;font-size:11px;color:#5a6468;background:rgba(255,255,255,.72);padding:2px 7px;border-radius:6px;}
.herofoot{max-width:1180px;margin:0 auto;padding:10px 22px 4px;font-size:12px;color:var(--muted);}
h2{font-size:19px;margin:42px 0 12px;border-bottom:2px solid var(--accent);padding-bottom:7px;}
h2 .num{display:inline-block;background:var(--accent);color:#fff;font-size:12px;font-weight:700;padding:3px 9px;border-radius:4px;margin-right:10px;}
p{margin:0 0 12px;}b{color:#0c4a4e;}code{background:#eaf0f0;color:#0a4448;padding:1px 6px;border-radius:4px;font-size:.88em;}
figure{margin:14px 0 6px;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fff;}
figure img{display:block;width:100%;height:auto;}figcaption{font-size:12px;color:var(--muted);padding:8px 13px;background:#f3f5f5;border-top:1px solid var(--line);}
table{border-collapse:collapse;width:100%;margin:10px 0 16px;font-size:13.5px;}th,td{border:1px solid var(--line);padding:7px 9px;text-align:center;}thead th{background:var(--accent);color:#fff;}tbody tr:nth-child(odd){background:#f5f8f8;}
.teach{background:#eaf4f4;border-left:4px solid var(--accent);padding:10px 15px;border-radius:0 6px 6px 0;font-size:14px;margin:13px 0 0;}
.teach .tag{display:inline-block;background:var(--accent);color:#fff;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:9px;}
.honest{background:#fff;border:1px solid var(--line);border-radius:10px;padding:6px 22px 14px;margin-top:34px;}.honest h2{border-bottom-color:#c0654a;}.honest li{font-size:13.5px;margin:0 0 7px;}
footer{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);text-align:center;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;margin:18px 0;}
.card2{border:1px solid var(--line);border-radius:12px;padding:16px;background:#fff;box-shadow:0 1px 6px rgba(0,0,0,.05);}
.card2 b{font-size:16px;color:var(--accent);}.card2 span{font-size:12.5px;color:#3a4347;display:block;margin:2px 0 8px;}
.card2 a{display:block;font-size:13px;color:var(--accent);text-decoration:none;border:1px solid var(--line);border-radius:8px;padding:6px 10px;margin-top:6px;background:#f5faf9;}
.cap{display:flex;gap:6px;margin-top:2px;}
.cap button{font:inherit;font-size:12px;font-weight:600;border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:20px;padding:4px 10px;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.06);}
.airwrap{max-width:1180px;margin:14px auto 0;padding:0 22px;}
#airender{width:100%;border-radius:12px;border:1px solid var(--line);display:block;background:#eef1f2;}
.aircap{font-size:12.5px;color:var(--muted);margin:7px 0 0;}
"""


# ----------------------------------------------------------------- 3D / 平面 图
def _boxes3d(ax, recs, minx, miny, zmax, center=None):
    xs, ys, dx, dy, dz, cols = [], [], [], [], [], []
    for r in recs:
        b = r["geom"].bounds
        xs.append(b[0] - minx); ys.append(b[1] - miny)
        dx.append(max(b[2] - b[0], 2)); dy.append(max(b[3] - b[1], 2)); dz.append(max(r["h"], 3))
        cols.append(C.SH_COLOR[r["sh"]])
    ax.bar3d(np.array(xs), np.array(ys), np.zeros(len(xs)), np.array(dx), np.array(dy), np.array(dz),
             color=cols, shade=True, edgecolor="none")
    if center:
        ax.plot([center[0] - minx, center[0] - minx], [center[1] - miny, center[1] - miny], [0, zmax],
                c="#d1495b", lw=2.2, alpha=.9)
    ax.view_init(elev=34, azim=-58); ax.set_zlim(0, zmax); ax.set_box_aspect((1, 1, 0.55))
    ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([]); ax.grid(False)
    for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane.pane.set_visible(False)


def _bounds(states):
    allp = [p for recs in states.values() for r in recs for p in C._polys(r["geom"])]
    return min(p.bounds[0] for p in allp), min(p.bounds[1] for p in allp)


def _full_bounds(states):
    allp = [p for recs in states.values() for r in recs for p in C._polys(r["geom"])]
    return (min(p.bounds[0] for p in allp), min(p.bounds[1] for p in allp),
            max(p.bounds[2] for p in allp), max(p.bounds[3] for p in allp))


def mass_field(recs, x0, y0, cell, nx, ny):
    """把每栋的楼面量(footprint面积×高度/层高)撒到网格 → 局部质量场(适用于 footprint 会变的体制)。"""
    g = np.zeros((ny, nx))
    for r in recs:
        c = r["geom"].centroid
        ix = int((c.x - x0) / cell); iy = int((c.y - y0) / cell)
        if 0 <= ix < nx and 0 <= iy < ny:
            g[iy, ix] += r["geom"].area * r["h"] / C.FLOOR_H
    return g


def _smooth(g):
    p = np.pad(g, 1, mode="edge"); s = np.zeros_like(g)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            s += p[dy:dy + g.shape[0], dx:dx + g.shape[1]]
    return s / 9.0


def fig_site_3d(slug, name, states, rows, order, ctr=None):
    import matplotlib.colors as mc, matplotlib.cm as cm
    x0, y0, x1, y1 = _full_bounds(states)
    minx, miny = x0, y0
    zmax = max(max(r["h"] for r in recs) for recs in states.values()) * 1.04
    lab = state_labels()
    # 质量场网格
    cell = max((x1 - x0), (y1 - y0)) / 38.0
    nx = max(int((x1 - x0) / cell) + 1, 1); ny = max(int((y1 - y0) / cell) + 1, 1)
    fields = {k: _smooth(mass_field(states[k], x0, y0, cell, nx, ny)) for k in order}
    deltas = {k: fields[k] - fields["current"] for k in order}
    alld = np.concatenate([np.abs(deltas[k]).ravel() for k in order if k != "current"])
    vlim = max(float(np.percentile(alld[alld > 0], 90)) if (alld > 0).any() else 1.0, 1.0)
    dnorm = mc.TwoSlopeNorm(vmin=-vlim, vcenter=0, vmax=vlim)
    n = len(order)
    fig = plt.figure(figsize=(4.4 * n, 9.4))
    for i, k in enumerate(order):
        ax = fig.add_subplot(2, n, i + 1, projection="3d")
        _boxes3d(ax, states[k], minx, miny, zmax, center=(ctr if k == "state_led" else None))
        ax.set_title("%s\nFAR %.2f·最高%.0f·CV%.2f" % (lab[k], rows[k]["far"], rows[k]["h_max"], rows[k]["h_cv"]), fontsize=10)
        ax2 = fig.add_subplot(2, n, n + i + 1)
        ax2.imshow(deltas[k], origin="lower", extent=[x0, x1, y0, y1], cmap="RdBu_r", norm=dnorm, aspect="equal")
        ax2.set_xticks([]); ax2.set_yticks([])
        ax2.set_title("基线(质量场)" if k == "current" else "vs 现状:质量挪去哪(红增/蓝减)", fontsize=9.5)
    h1 = [Patch(fc=C.SH_COLOR[sh], label=C.SH_LABEL[sh].split("(")[0]) for sh in ("state", "developer", "resident")]
    fig.add_artist(fig.legend(handles=h1, loc="center left", bbox_to_anchor=(0.004, 0.73), fontsize=9, frameon=False, title="上排:持份者"))
    h2 = [Patch(fc=cm.RdBu_r(dnorm(vlim)), label="质量增"), Patch(fc=cm.RdBu_r(dnorm(0)), label="≈不变"), Patch(fc=cm.RdBu_r(dnorm(-vlim)), label="质量减")]
    fig.legend(handles=h2, loc="center left", bbox_to_anchor=(0.004, 0.27), fontsize=9, frameon=False, title="下排:质量场Δ")
    fig.suptitle("%s — 现状 + 4 种权力体制(同视角)\n上=3D 量体(持份者色;★光柱=政府主导的权力重心)· 下=楼面量的空间Δ(权力把质量挪去哪)" % name, fontsize=12.5, fontweight="bold")
    fig.subplots_adjust(left=.06, right=.99, top=.9, bottom=.03, wspace=.04, hspace=.08)
    return C.save_fig(fig, slug + "_3d.png", OUT / "sites")


def fig_site_plan(slug, name, states, order):
    polys = [p for recs in states.values() for r in recs for p in C._polys(r["geom"])]
    minx = min(p.bounds[0] for p in polys); maxx = max(p.bounds[2] for p in polys)
    miny = min(p.bounds[1] for p in polys); maxy = max(p.bounds[3] for p in polys)
    lab = state_labels()
    fig, axs = plt.subplots(1, len(order), figsize=(4.0 * len(order), 4.4))
    for ax, k in zip(axs, order):
        C.plot_footprints(ax, states[k], lambda r: C.SH_COLOR[r["sh"]], lw=0.08)
        ax.set_xlim(minx, maxx); ax.set_ylim(miny, maxy); ax.set_title(lab[k], fontsize=11)
    fig.suptitle("%s — 平面 footprint:每种权力如何重写地块本身" % name, fontsize=13, fontweight="bold")
    fig.subplots_adjust(top=.86, bottom=.02, wspace=.03)
    return C.save_fig(fig, slug + "_plan.png", OUT / "sites")


def fig_regime_gallery(regime, label, by_site, sites, rows_by_site):
    n = len(sites); cols = 4; rws = (n + cols - 1) // cols
    fig = plt.figure(figsize=(4.0 * cols, 4.2 * rws))
    for i, (slug, nm) in enumerate(sites):
        recs = by_site[slug]
        polys = [p for r in recs for p in C._polys(r["geom"])]
        minx = min(p.bounds[0] for p in polys); miny = min(p.bounds[1] for p in polys)
        zmax = max(r["h"] for r in recs) * 1.04
        ax = fig.add_subplot(rws, cols, i + 1, projection="3d")
        _boxes3d(ax, recs, minx, miny, zmax)
        rr = rows_by_site[slug]
        ax.set_title("%s\nFAR%.2f·最高%.0f·CV%.2f" % (nm, rr["far"], rr["h_max"], rr["h_cv"]), fontsize=9)
    fig.suptitle("「%s」在 %d 个上海街道上的形态" % (label, n), fontsize=14, fontweight="bold")
    fig.subplots_adjust(left=.01, right=.99, top=.93, bottom=.02, wspace=.02, hspace=.12)
    return C.save_fig(fig, regime + "_gallery.png", OUT / "regimes")


# ----------------------------------------------------------------- 互动几何 + viewer
def geom_states(states, order, sat=None, sat_extent=None, renders=None):
    allp = [p for recs in states.values() for r in recs for p in C._polys(r["geom"])]
    minx = min(p.bounds[0] for p in allp); miny = min(p.bounds[1] for p in allp)

    def pack(recs):
        out = []
        for r in recs:
            for poly in C._polys(r["geom"]):
                ps = poly.simplify(0.8)
                xy = [[round(x - minx, 1), round(y - miny, 1)] for x, y in list(ps.exterior.coords)[:-1]]
                if len(xy) >= 3:
                    out.append({"p": xy, "sh": r["sh"], "h": round(float(r["h"]), 1)})
        return out
    d = {"colors": C.SH_COLOR, "order": order, "states": {k: pack(states[k]) for k in order}}
    if sat:
        d["sat"] = sat; d["satExtent"] = sat_extent
    if renders:
        d["renders"] = renders
    return json.dumps(d, separators=(",", ":"))


def _site_renders(slug):
    """读 out/sites/renders/<slug>/<state>.jpg(AI 渲染,文件名=state)→ {state: data_uri}。无则空。"""
    import base64
    d = OUT / "sites" / "renders" / slug
    if not d.exists():
        return {}
    out = {}
    for p in sorted(d.glob("*.jpg")):
        out[p.stem] = "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()
    return out


def _site_sat(slug, states):
    allp = [p for recs in states.values() for r in recs for p in C._polys(r["geom"])]
    minx = min(p.bounds[0] for p in allp); miny = min(p.bounds[1] for p in allp)
    maxx = max(p.bounds[2] for p in allp); maxy = max(p.bounds[3] for p in allp)
    try:
        return C.ground_sat(minx, miny, maxx, maxy, OUT / "sites" / (slug + "_sat.jpg"), 2.0)
    except Exception as e:
        print("  卫星底失败", slug, e); return None, None


VIEWER = """
const G=__GEOM__; const COL=G.colors;
let scene,cam,renderer,controls,groups={},cur=G.order[0];
function mk(recs){const grp=new THREE.Group();
  for(const r of recs){const sh=new THREE.Shape();
    r.p.forEach((pt,i)=> i?sh.lineTo(pt[0],pt[1]):sh.moveTo(pt[0],pt[1]));
    const g=new THREE.ExtrudeGeometry(sh,{depth:1,bevelEnabled:false});
    const m=new THREE.MeshLambertMaterial({color:new THREE.Color(COL[r.sh]||"#999")});
    const me=new THREE.Mesh(g,m);me.scale.z=r.h;me.userData={h:r.h};grp.add(me);}
  return grp;}
function init(){const st=document.getElementById("stage"),w=st.clientWidth,h=st.clientHeight;
  scene=new THREE.Scene();cam=new THREE.PerspectiveCamera(50,w/h,1,16000);cam.up.set(0,0,1);
  renderer=new THREE.WebGLRenderer({canvas:document.getElementById("cv3d"),antialias:true,preserveDrawingBuffer:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(w,h);renderer.setClearColor(0xd9e3ea);
  if(THREE.sRGBEncoding!==undefined)renderer.outputEncoding=THREE.sRGBEncoding;
  scene.add(new THREE.HemisphereLight(0xffffff,0xc6d0d3,0.95));scene.add(new THREE.AmbientLight(0xffffff,0.42));
  const dl=new THREE.DirectionalLight(0xffffff,0.68);dl.position.set(0.6,-1,1.4);scene.add(dl);
  let o={minx:1e9,miny:1e9,maxx:-1e9,maxy:-1e9};
  for(const k of G.order)for(const r of G.states[k])for(const p of r.p){o.minx=Math.min(o.minx,p[0]);o.miny=Math.min(o.miny,p[1]);o.maxx=Math.max(o.maxx,p[0]);o.maxy=Math.max(o.maxy,p[1]);}
  const cx=(o.minx+o.maxx)/2,cy=(o.miny+o.maxy)/2,span=Math.max(o.maxx-o.minx,o.maxy-o.miny);
  const root=new THREE.Group();
  if(G.sat){const tx=new THREE.TextureLoader().load(G.sat);if(THREE.sRGBEncoding!==undefined)tx.encoding=THREE.sRGBEncoding;
    const se=G.satExtent,gw=se[2]-se[0],gh=se[3]-se[1];
    const gp=new THREE.Mesh(new THREE.PlaneGeometry(gw,gh),new THREE.MeshBasicMaterial({map:tx}));
    gp.position.set((se[0]+se[2])/2,(se[1]+se[3])/2,-0.3);root.add(gp);
  }else{const gp=new THREE.Mesh(new THREE.PlaneGeometry(span*1.6,span*1.6),new THREE.MeshBasicMaterial({color:0xdfe5e7}));gp.position.set(cx,cy,-0.5);root.add(gp);}
  for(const k of G.order){const grp=mk(G.states[k]);grp.visible=(k===cur);groups[k]=grp;root.add(grp);}
  root.position.set(-cx,-cy,0);scene.add(root);
  cam.position.set(span*0.55,-span*0.72,span*0.6);controls=new THREE.OrbitControls(cam,renderer.domElement);
  controls.target.set(0,0,40);controls.enableDamping=true;controls.dampingFactor=.08;controls.update();
  window.addEventListener("resize",onr);animate();updateAir();}
function onr(){const s=document.getElementById("stage");cam.aspect=s.clientWidth/s.clientHeight;cam.updateProjectionMatrix();renderer.setSize(s.clientWidth,s.clientHeight);}
function animate(){requestAnimationFrame(animate);
  const g=groups[cur];if(g)for(const m of g.children){const t=m.userData.h;if(m.scale.z<t)m.scale.z=Math.min(t,m.scale.z+t*0.09+0.6);}
  controls.update();renderer.render(scene,cam);}
function setState(k){cur=k;for(const kk of G.order)groups[kk].visible=(kk===k);
  for(const m of groups[k].children)m.scale.z=0.01;
  document.querySelectorAll(".scn button").forEach(b=>b.classList.toggle("on",b.dataset.s===k));updateAir();}
function updateAir(){var el=document.getElementById('airender');if(!el||!G.renders)return;var u=G.renders[cur];var wrap=document.getElementById('airwrap');
  if(u){el.src=u;if(wrap)wrap.style.display='';var s=document.getElementById('airstate'),b=document.querySelector('.scn button.on');if(s&&b)s.textContent=b.textContent;}
  else if(wrap){wrap.style.display='none';}}
window.addEventListener("DOMContentLoaded",()=>{init();
  document.querySelectorAll(".scn button").forEach(b=>b.onclick=()=>setState(b.dataset.s));});
let _clay=false;
function _claySet(on){scene.traverse(o=>{if(o.material&&o.material.type==='MeshLambertMaterial'){if(on){if(!o.userData._c)o.userData._c=o.material.color.clone();o.material.color.set(0xccc7c0);}else if(o.userData._c)o.material.color.copy(o.userData._c);}});}
function pfClay(){_clay=!_clay;_claySet(_clay);var b=document.getElementById('claybtn');if(b)b.textContent=_clay?'🎨 分色':'🧱 素模';}
function pfCap(){renderer.render(scene,cam);document.getElementById('cv3d').toBlob(function(bl){var a=document.createElement('a');a.href=URL.createObjectURL(bl);a.download='view_'+cur+'_'+(_clay?'clay':'color')+'.png';a.click();});}
window.addEventListener("DOMContentLoaded",function(){var c=document.getElementById('capbtn');if(c)c.onclick=pfCap;var y=document.getElementById('claybtn');if(y)y.onclick=pfClay;});
"""


def _fig_embed(p, cap):
    b64 = base64.b64encode(p.read_bytes()).decode()
    return '<figure><img src="data:image/png;base64,%s" alt="%s"><figcaption>%s</figcaption></figure>' % (b64, cap, cap)


METRIC_COLS = [("far", "FAR", "%.2f"), ("coverage", "覆盖%", "%.0f%%"), ("h_max", "最高m", "%.0f"),
               ("h_cv", "高度CV", "%.2f"), ("grain", "中位fp", "%.0f"), ("slender", "瘦长比", "%.2f"),
               ("concentration", "重心集中%", "%.0f%%")]


def _mtable(rows, keys, labels, keycol="体制"):
    head = "".join("<th>%s</th>" % c[1] for c in METRIC_COLS)
    body = ""
    for k in keys:
        r = rows[k]
        cells = ""
        for f, _, fmt in METRIC_COLS:
            v = r[f] * 100 if f in ("coverage", "concentration") else r[f]
            cells += "<td>" + (fmt % v) + "</td>"
        body += "<tr><td>%s</td>%s</tr>" % (labels.get(k, k), cells)
    return "<table><thead><tr><th>%s</th>%s</tr></thead><tbody>%s</tbody></table>" % (keycol, head, body)


def site_html(slug, name, family, states, rows, order, ctr):
    lab = state_labels()
    fig3d = fig_site_3d(slug, name, states, rows, order, ctr)
    figpl = fig_site_plan(slug, name, states, order)
    three = (WEB / "three.min.js").read_text(encoding="utf-8")
    orbit = (WEB / "OrbitControls.js").read_text(encoding="utf-8")
    sat, sext = _site_sat(slug, states)
    renders = _site_renders(slug)
    g = geom_states(states, order, sat, sext, renders)
    air = ('<div class="airwrap" id="airwrap"><img id="airender" alt="AI 渲染">'
           '<p class="aircap">AI 渲染(viewer 截图 → img2img)· 切上方情景同步 · 当前:<b id="airstate">现状</b>'
           ' · 教学示意,非真实预测</p></div>') if renders else ""
    scn = "".join('<button data-s="%s"%s>%s</button>' % (k, ' class="on"' if k == order[0] else "", lab[k]) for k in order)
    legend = " ".join('<span><i style="background:%s"></i>%s</span>' % (C.SH_COLOR[s], C.SH_LABEL[s].split("(")[0]) for s in ("state", "developer", "resident"))
    regs = OP.load_regimes()
    recipe = "".join("<li><b>%s</b>:%s</li>" % (v.get("label", k), v.get("desc", "")) for k, v in regs.items())
    html = HTML_SITE
    rep = {"@@TITLE@@": "上海 %s — 4 种权力 × 形态" % name, "@@CSS@@": PF_CSS, "@@NAME@@": name,
           "@@FAMILY@@": family, "@@SCN@@": scn, "@@LEGEND@@": legend,
           "@@MTABLE@@": _mtable(rows, order, lab), "@@RECIPE@@": recipe,
           "@@AIR@@": air,
           "@@FIG3D@@": _fig_embed(fig3d, "上=现状+4体制的3D量体;下=每种权力把楼面量挪去哪的空间Δ(红增/蓝减)"),
           "@@FIGPLAN@@": _fig_embed(figpl, "现状 + 4 体制 的平面 footprint(地块本身怎么变)"),
           "@@THREE@@": three, "@@ORBIT@@": orbit, "@@VIEWER@@": VIEWER.replace("__GEOM__", g)}
    for k, v in rep.items():
        html = html.replace(k, v)
    (OUT / "sites").mkdir(parents=True, exist_ok=True)
    p = OUT / "sites" / (slug + ".html")
    p.write_text(html, encoding="utf-8")
    return p


def regime_html(regime, label, desc, sites, by_site, rows_by_site):
    gal = fig_regime_gallery(regime, label, by_site, sites, rows_by_site)
    rows = {s: rows_by_site[s] for s, _ in sites}
    labels = {s: nm for s, nm in sites}
    html = HTML_REGIME
    rep = {"@@TITLE@@": "「%s」× 12 街道" % label, "@@CSS@@": PF_CSS, "@@LABEL@@": label, "@@DESC@@": desc,
           "@@GALLERY@@": _fig_embed(gal, "「%s」在 12 个街道上的形态(同算子配方)" % label),
           "@@MTABLE@@": _mtable(rows, [s for s, _ in sites], labels, keycol="街道")}
    for k, v in rep.items():
        html = html.replace(k, v)
    (OUT / "regimes").mkdir(parents=True, exist_ok=True)
    p = OUT / "regimes" / (regime + ".html")
    p.write_text(html, encoding="utf-8")
    return p


def index_html(sites, regimes):
    lab = state_labels()
    scards = "".join(
        '<div class="card2"><b>%s</b><span>%s</span><a href="sites/%s.html">看 4 种权力 →</a></div>' % (nm, fam, sl)
        for sl, nm, fam in sites)
    rcards = "".join(
        '<div class="card2"><b>%s</b><span>%s</span><a href="regimes/%s.html">看 12 个街道 →</a></div>' % (regimes[k].get("label", k), regimes[k].get("desc", "")[:40], k)
        for k in STATE_ORDER if k != "current")
    html = HTML_INDEX.replace("@@CSS@@", PF_CSS).replace("@@SCARDS@@", scards).replace("@@RCARDS@@", rcards)
    p = OUT / "index.html"
    p.write_text(html, encoding="utf-8")
    return p


HTML_SITE = """<!DOCTYPE html><html lang="zh-Hans"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>@@TITLE@@</title><style>@@CSS@@</style></head><body>
<div class="nav"><a href="../index.html">← 首页</a> · <a href="../report.html">综合报告</a> · <a href="../atlas.html">算子图谱</a></div>
<div class="cover"><p class="kick">Urban Stakeholder Workshop · power_to_form · @@FAMILY@@</p>
<h1>@@NAME@@ — 同一块地,4 种权力,4 种形态</h1>
<p class="lead">同一套真实 footprint(AI 实测高度)+ 离散权利,施加 4 种<b>权力体制的算子配方</b>:开发商主导(多中心·塔化加密)、政府主导(单中心·向权力重心收拢)、居民自建(细粒·水平)、共享(开放·平权)。下方 3D <b>一键切换</b>现状与 4 体制。这些是<b>教学假设</b>,非真实规划预测。</p></div>
<div class="hero"><div class="inner"><p class="lead2">↓ 互动 3D:按钮切 现状 / 4 体制(footprint 与高度都会变);拖曳旋转、滚轮缩放。</p>
<div id="stage"><canvas id="cv3d"></canvas><div class="hud"><div class="scn">@@SCN@@</div>
<div class="cap"><button id="capbtn">📷 拍照</button><button id="claybtn">🧱 素模</button></div>
<div class="card"><div class="legend">@@LEGEND@@</div></div></div>
<div class="hint3d">拖曳=旋转 · 滚轮=缩放 · 右键=平移</div></div>
<div class="herofoot">同一套真实数据 · 5 个状态内联 · 红光柱(政府主导)=权力重心 · 零 AI、单档离线。</div></div></div>
@@AIR@@
<div class="wrap">
<h2><span class="num">指标</span>4 种权力的形态指纹</h2>
<p>读这张表:<b>开发商</b>=瘦长比↑、覆盖↓、FAR↑;<b>政府/集权</b>=高度CV↑、重心集中%↑、FAR 守恒;<b>居民自建</b>=栋数↑、中位fp↓(细粒)、高度趋平;<b>共享</b>=高度CV↓、覆盖↓、均质中低。</p>
@@MTABLE@@
@@FIG3D@@
@@FIGPLAN@@
<p class="teach"><span class="tag">教什么</span>权力不是只调高度——它能<b>重写地块本身</b>:谁占有(现状权利)、谁拔高(developer)、向哪个重心收拢(state)、细分给谁自建(resident)、释放多少共享地面(shared)。改 <code>config/regimes.yaml</code> 的算子配方 = 亲手做反事实。</p>
<section class="honest"><h2>诚实边界</h2><ul>
<li>这些 regime→形态 是<b>教学假设/约简</b>,不是经验断言或真实规划预测。</li>
<li>简化算子:塔化=缩放、拆板=沿轴切、自建=网格细分、集权=距离衰减;不做退线/日照/产权/参与过程。</li>
<li>权利为<b>用途的离散查表</b>(EULUC→Function→AOI),非产权考证;informal 本数据无信号、恒空;danwei 国家属性在用途数据里看不见。</li>
<li>高度为 AI 实测(极端超高层可能低估);developer/shared 等会改 footprint 与总 GFA,state/集权守恒。</li>
</ul></section>
<footer>power_to_form · 上海 @@NAME@@ · 算子(operators.py)× 配方(regimes.yaml)× 站点 · 教学练习,非真实规划预测</footer></div>
<script>@@THREE@@</script><script>@@ORBIT@@</script><script>@@VIEWER@@</script></body></html>"""

HTML_REGIME = """<!DOCTYPE html><html lang="zh-Hans"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>@@TITLE@@</title><style>@@CSS@@</style></head><body>
<div class="nav"><a href="../index.html">← 首页</a> · <a href="../report.html">综合报告</a></div>
<div class="cover"><p class="kick">Urban Stakeholder Workshop · power_to_form · 体制版</p>
<h1>「@@LABEL@@」在 12 个上海街道上的形态</h1>
<p class="lead">@@DESC@@ 同一套算子配方,跑过资本/单位/里弄/产业 12 个街道——横向看<b>这种权力的形态规律是否稳定</b>。教学假设,非真实规划预测。</p></div>
<div class="wrap">
@@GALLERY@@
<h2><span class="num">指标</span>这种权力在 12 个街道上的指纹</h2>
@@MTABLE@@
<p class="teach"><span class="tag">教什么</span>同一种权力作用在不同肌理(超高层 CBD / 工人新村 / 里弄老城 / 产业园)上,形态指纹是否一致?哪里"吃得动"、哪里被原有肌理抵抗?这正是「权力 × 在地」的对话。</p>
<footer>power_to_form · 体制版 · 教学练习,非真实规划预测</footer></div></body></html>"""

HTML_INDEX = """<!DOCTYPE html><html lang="zh-Hans"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>power_to_form — 权力 × 城市形态</title><style>@@CSS@@</style></head><body>
<div class="cover"><p class="kick">Urban Stakeholder Workshop · power_to_form</p>
<h1>权力 × 城市形态:一套可教、可改的算法</h1>
<p class="lead">真实上海多源数据 → 离散权利 → <b>原子形态算子</b>的<b>配方</b> → 新形态。12 个街道 × 4 种权力体制(开发商主导 / 政府主导集权 / 居民自建 / 共享)。两种看法:<b>站点版</b>(一个地方在 4 种权力下)与<b>体制版</b>(一种权力在 12 个地方)。配方写在 <code>config/regimes.yaml</code>,学生可改。</p>
<p class="lead"><a href="report.html" style="color:#0f5e63;font-weight:700">→ 综合报告(跨 48 格的分析与判断)</a> · <a href="atlas.html" style="color:#0f5e63;font-weight:700">→ 算子图谱(9 个动词的 before/after)</a> · <a href="TEACHING.html" style="color:#0f5e63;font-weight:700">→ 教学指南(7 步)</a></p></div>
<div class="wrap">
<h2><span class="num">体制版</span>一种权力 × 12 个地方</h2><div class="grid">@@RCARDS@@</div>
<h2><span class="num">站点版</span>一个地方 × 4 种权力</h2><div class="grid">@@SCARDS@@</div>
<footer>power_to_form · operators.py × regimes.yaml × 12 sites · 教学练习,非真实规划预测</footer></div></body></html>"""
