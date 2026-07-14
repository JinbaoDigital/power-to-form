#!/usr/bin/env python3
"""
reproduce.py - one entry point for the auditable parametric instrument.

  python reproduce.py --verify   recompute and reconcile EVERY number in the paper from the
                                 frozen derived artefacts in engine/out/ (no licensed data needed).
                                 Exits non-zero if any check fails.
  python reproduce.py --run      recompute the artefacts from the per-site caches. The caches are
                                 Baidu-derived geometry and are NOT redistributed; see README.md.
  python reproduce.py --demo     run the v5 engine on a synthetic district (delegates to the
                                 archived 5-district package; no data needed).

This repo ships DERIVED measurements + code, never raw geometry. --verify reads only
JSON/CSV artefacts: it hard-codes the EXPECTED value published in the paper, RECOMPUTES the
actual value from the artefacts, prints both, and compares. See VALIDATION.md.
"""
import sys, json, csv, math, argparse, hashlib, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENG = ROOT / "engine"
OUT = ENG / "out" / "cake"
FIGS = ENG / "out" / "cake_figs"
AUDIT = ENG / "audit" / "foar_figures"
ARCHIVE = ROOT / "archive_v5_5district"

SITES = ["lujiazui", "nanjingxi", "caoyang", "pengpu", "laoximen", "yuyuan", "dapuqiao", "zhangjiang"]
FROZEN5 = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
CORNERS = {"developer-led": "capital_deepen_B", "state-led": "state_civic_B",
           "resident-led": "resident_retain_B", "shared": "shared_commons_B"}

_fails, _checks = [], [0]


def chk(ok, label, expected, actual, note=""):
    """Print expected vs recomputed and record pass/fail."""
    _checks[0] += 1
    print("  %-5s %-46s expected %-22s recomputed %-22s%s"
          % ("ok" if ok else "FAIL", label, expected, actual, ("  " + note) if note else ""))
    if not ok:
        _fails.append(label)
    return ok


def close(a, b, tol):
    return abs(float(a) - float(b)) <= tol


# ---------------------------------------------------------------- rank correlation (no scipy)
def _ranks(v):
    idx = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[idx[j + 1]] == v[idx[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0            # average rank for ties
        for k in range(i, j + 1):
            r[idx[k]] = avg
        i = j + 1
    return r


def spearman(x, y):
    """Spearman rho = Pearson on average ranks. Implemented here so the audit needs no scipy."""
    rx, ry = _ranks(x), _ranks(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx and dy else float("nan")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


# =================================================================== verify
def verify():
    if not (OUT / "metrics_cake_all.json").exists():
        sys.exit("engine/out/cake/metrics_cake_all.json is missing - is this a complete checkout?")
    A = json.load(open(OUT / "metrics_cake_all.json", encoding="utf-8"))
    F = json.load(open(OUT / "metrics_cake.json", encoding="utf-8"))
    E = json.load(open(FIGS / "E_embed_stats.json", encoding="utf-8"))
    G = list(csv.DictReader(open(OUT / "gamma_bind.csv", encoding="utf-8")))

    print("\nReading the Found City through Stakeholder Power - audit of the published numbers")
    print("source: engine/out/cake/*.json|csv, engine/out/cake_figs/E_embed_stats.json (derived, frozen)")
    print("method: the EXPECTED value is the number printed in the paper; the RECOMPUTED value is")
    print("        derived from the artefacts on every run. Nothing below prints itself.")

    # -------------------------------------------------- 0. release guard
    print("\n0. release guard (no raw geometry may be present)")
    parquet = sorted(p for p in ROOT.rglob("*.parquet") if ".git" not in p.parts)
    chk(len(parquet) == 0, "buildings.parquet / any parquet in tree", "0 files", "%d files" % len(parquet))

    # -------------------------------------------------- 1. Table 1
    print("\n1. Table 1 - the eight sites as found (metrics_cake_all.json)")
    T1 = {  # expected, verbatim from Table 1 of the manuscript
        # site: (n, area_km2, state, developer, resident, far, coverage, h_mean, h_max)
        "lujiazui":   (1849,  6.89, .068, .654, .275, 3.26, 0.179, 41.1, 606),
        "nanjingxi":  (999,   1.62, .044, .580, .362, 4.19, 0.357, 32.6, 456),
        "caoyang":    (1072,  2.08, .111, .207, .681, 3.18, 0.276, 34.4, 228),
        "pengpu":     (1821,  3.28, .046, .034, .918, 3.22, 0.285, 37.0, 132),
        "laoximen":   (923,   1.21, .143, .264, .589, 3.72, 0.370, 27.3, 198),
        "yuyuan":     (819,   1.20, .125, .363, .509, 2.99, 0.362, 22.0, 192),
        "dapuqiao":   (785,   1.59, .159, .356, .483, 4.28, 0.318, 39.5, 312),
        "zhangjiang": (3129, 18.30, .250, .581, .165, 1.47, 0.180, 23.8, 240),
    }
    print("    %-11s%7s%8s%23s%7s%8s%8s%7s" % ("site", "n", "km2", "state/dev/resident GFA",
                                               "FAR", "cover", "h_mean", "h_max"))
    for s in SITES:
        c = A[s]["current"]
        fp, sh, meta = c["fingerprint"], c["shares_gfa"], A[s]["site"]
        got = (c["n"], round(meta["area_km2"], 2), round(sh["state"], 3), round(sh["developer"], 3),
               round(sh["resident"], 3), round(fp["far"], 2), round(fp["coverage"], 3),
               round(fp["h_mean"], 1), int(fp["h_max"]))
        print("    %-11s%7d%8.2f%23s%7.2f%8.3f%8.1f%7d"
              % (s, got[0], got[1], "%.3f / %.3f / %.3f" % got[2:5], got[5], got[6], got[7], got[8]))
        chk(got == T1[s], "Table 1 row: %s" % s, str(T1[s]), str(got))
    n_tot = sum(A[s]["current"]["n"] for s in SITES)
    chk(len(SITES) == 8, "site count", "8", str(len(SITES)))
    chk(n_tot == 11397, "total buildings n", "11,397", "{:,}".format(n_tot))

    # -------------------------------------------------- 2. invariants + frozen regression
    print("\n2. by-construction invariants and the frozen-five regression")
    dev, leaves = [0.0], [0]

    def walk(a, b):
        if isinstance(a, dict):
            for k in a:
                if k in b:
                    walk(a[k], b[k])
        elif isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)):
            leaves[0] += 1
            dev[0] = max(dev[0], abs(float(a) - float(b)))

    for s in FROZEN5:
        walk(F[s], A[s])
    chk(dev[0] == 0.0 and leaves[0] == 1748, "frozen-five regression (5 sites, every leaf)",
        "0.000e+00 over 1748 leaves", "%.3e over %d leaves" % (dev[0], leaves[0]))
    modeA = [v["gfa_change_pct"] for s in SITES for k, v in A[s].items()
             if isinstance(v, dict) and k.endswith("_A")]
    chk(len(modeA) == 40 and max(abs(x) for x in modeA) == 0.0,
        "mode A (redistribute) volume conservation", "0.00% over 40 runs",
        "%.2f%% over %d runs" % (max(abs(x) for x in modeA), len(modeA)))
    cov_ok = all(A[s][k]["fingerprint"]["coverage"] == A[s]["current"]["fingerprint"]["coverage"]
                 and A[s][k]["fingerprint"]["grain"] == A[s]["current"]["fingerprint"]["grain"]
                 and A[s][k]["fingerprint"]["n"] == A[s]["current"]["fingerprint"]["n"]
                 for s in SITES for k in A[s] if k not in ("current", "site"))
    chk(cov_ok, "coverage / grain / n frozen in every run", "identical to as-found",
        "identical" if cov_ok else "DRIFT")

    # -------------------------------------------------- 3. failure anchors
    print("\n3. the two failure anchors (the demonstration's central observation)")
    zj, pp = A["zhangjiang"], A["pengpu"]
    r = zj["capital_deepen_B"]
    chk(not r["target_met"] and close(r["share_reached"], 0.774, 0.001),
        "zhangjiang developer-led falls short", "0.774 of 0.80 (unmet)",
        "%.3f of %.2f (%s)" % (r["share_reached"], r["target"], "unmet" if not r["target_met"] else "MET"))
    nfail = [s for s in SITES if not A[s]["capital_deepen_B"]["target_met"]]
    chk(nfail == ["zhangjiang"], "the only developer-led failure of the 8", "['zhangjiang']", str(nfail))
    r = pp["state_civic_B"]
    chk(not r["target_met"] and close(r["share_reached"], 0.063, 0.001),
        "pengpu state-led falls short", "0.063 of 0.30 (unmet)",
        "%.3f of %.2f (%s)" % (r["share_reached"], r["target"], "unmet" if not r["target_met"] else "MET"))
    chk(pp["resident_retain_B"]["acquired_n"] == 0, "pengpu resident-led rebuilds nothing",
        "0 buildings", "%d buildings" % pp["resident_retain_B"]["acquired_n"],
        "residents already hold %.3f of the GFA" % pp["current"]["shares_gfa"]["resident"])

    # -------------------------------------------------- 4. reachability
    print("\n4. morphological reachability (reachable_<slug>.json, 5x5 target grid per site)")
    EXP_UNREACH = {"zhangjiang": 0, "nanjingxi": 5, "dapuqiao": 5, "lujiazui": 9,
                   "caoyang": 15, "yuyuan": 15, "laoximen": 18, "pengpu": 20}
    tot_bad = tot_cells = tot_state = tot_dev = 0
    for s in SITES:
        cells = json.load(open(OUT / ("reachable_%s.json" % s), encoding="utf-8"))
        bad = [c for c in cells if not (c["dev_met"] and c["state_met"])]
        tot_bad += len(bad)
        tot_cells += len(cells)
        tot_state += sum(1 for c in bad if not c["state_met"])
        tot_dev += sum(1 for c in cells if not c["dev_met"])
        chk(len(bad) == EXP_UNREACH[s] and len(cells) == 25, "unreachable cells: %s" % s,
            "%d of 25" % EXP_UNREACH[s], "%d of %d" % (len(bad), len(cells)))
    chk(tot_bad == 87 and tot_cells == 200, "unreachable cells, all sites", "87 of 200",
        "%d of %d" % (tot_bad, tot_cells))
    chk(tot_state == tot_bad, "every unreachable cell fails on the state axis",
        "87 of 87", "%d of %d" % (tot_state, tot_bad))
    chk(tot_dev == 0, "cells failing on the developer axis", "0 of 200", "%d of 200" % tot_dev)

    # -------------------------------------------------- 5. the regulatory envelope (gamma)
    print("\n5. the regulatory envelope (gamma): inert at base, live at strict")
    runs = [(s, k) for s in SITES for k, v in A[s].items()
            if isinstance(v, dict) and "envelope_bind_n" in v]
    binds = [(s, k) for s, k in runs if A[s][k]["envelope_bind_n"] != 0]
    chk(len(runs) == 80 and len(binds) == 0, "base gamma (60 m): runs where the envelope binds",
        "0 of 80 runs", "%d of %d runs" % (len(binds), len(runs)))
    base = [r for r in G if r["row_type"] == "gamma_setting" and r["gamma"] == "base"
            and r["configuration"] == "developer_led"]
    hmax = max(float(r["rebuild_target_h_max"]) for r in base)
    chk(len(base) == 8 and hmax < 60.0, "base gamma: highest developer rebuild target",
        "< 60.0 m (inert by arithmetic)", "%.2f m (headroom %.2f m)" % (hmax, 60.0 - hmax))
    strict = [r for r in G if r["row_type"] == "gamma_setting" and r["gamma"] == "strict"]
    sbind = [r for r in strict if int(r["envelope_bind_n"]) > 0]
    clipped = sum(float(r["envelope_clipped_gfa"]) for r in strict)
    chk(len(strict) == 32 and len(sbind) == 3, "strict gamma (30 m): runs where it binds",
        "3 of 32 runs", "%d of %d runs" % (len(sbind), len(strict)))
    chk(close(clipped, 6.0e6, 0.1e6), "strict gamma: volume removed by the envelope",
        "about 6.0e+06 m3", "%.3e m3" % clipped)

    # -------------------------------------------------- 6. rank preservation
    print("\n6. fingerprint rank preservation across the 8 sites (Spearman rho, current -> configured)")
    EXP_RHO = [("far", "developer-led", 1.00), ("concentration", "state-led", 0.33),
               ("h_cv", "shared", 0.50), ("slender", "state-led", 1.00), ("slender", "shared", 1.00)]
    for axis, cfg, exp in EXP_RHO:
        cur = [A[s]["current"]["fingerprint"][axis] for s in SITES]
        new = [A[s][CORNERS[cfg]]["fingerprint"][axis] for s in SITES]
        rho = spearman(cur, new)
        chk(close(rho, exp, 0.005), "rho %-14s under %-13s" % (axis, cfg), "%.2f" % exp, "%.4f" % rho)

    # -------------------------------------------------- 7. embedding (E-series)
    print("\n7. embedding of the 11,397 buildings (frozen E_embed_stats.json; balanced accuracy)")
    print("    frozen cache: numpy AE / beta-VAE, seed 0, 450 epochs, numpy 2.0.2, in")
    print("    engine/audit/foar_figures/embed_cache_frozen/. This audit reconciles against the")
    print("    FROZEN stats file (tolerance 0.05 pp), so a numpy bump cannot fail it spuriously.")
    print("    A LIVE retrain is looser: the AE drifts about 0.4 pp across numpy versions")
    print("    (88.47 measured on numpy 2.2.6 against the frozen 88.85 on numpy 2.0.2).")
    chk(E["n"] == 11397, "buildings embedded", "11,397", "{:,}".format(E["n"]))
    for label, path, exp in [("PCA-2D  (21 features)", ("all", "pca2"), 57.2),
                             ("AE-2D   (21 features)", ("all", "ae2"), 88.8),
                             ("VAE-2D  (21 features)", ("all", "vae2"), 90.4),
                             ("full-D  (21 features)", ("all", "fullD"), 88.5),
                             ("full-D  (form only, 7)", ("phys", "fullD"), 34.7)]:
        got = E[path[0]][path[1]]["bal_acc"] * 100.0
        chk(close(round(got, 1), exp, 0.05), "balanced accuracy: %s" % label, "%.1f %%" % exp,
            "%.2f %%" % got)
    rec = E["phys"]["fullD"]["recall"]["state"]
    chk(close(round(rec, 2), 0.07, 0.005), "form-only recall of the state class", "0.07", "%.4f" % rec)

    # -------------------------------------------------- 8. hash manifest
    print("\n8. hash manifest (engine/audit/foar_figures/MANIFEST.json)")
    M = json.load(open(AUDIT / "MANIFEST.json", encoding="utf-8"))
    pinned = {}
    pinned.update({"audit/foar_figures/scripts_snapshot/" + k: v
                   for k, v in M["scripts_snapshot"]["sha256"].items()})
    pinned.update({k: v for k, v in M["helpers"].items() if not k.startswith("$")})
    pinned.update({k: v for k, v in M["configs"].items()})
    pinned.update({k: v for k, v in M["frozen_data_inputs"].items() if not k.startswith("$")})
    pinned.update({e["path"]: e["sha256"] for e in M["embed_cache_frozen"] if "path" in e})
    KNOWN_DELTA = {  # release policy: two comment lines about the upstream source layer were removed
        "pf_common.py": ("15be82d27e7d1a842b20f54e6eb601e5395f29e9277eba9ed3add0ca36edd2f3",
                         "2 comment lines scrubbed for release; code identical - see VALIDATION.md")}
    bad, delta, missing = [], [], []
    for rel, want in sorted(pinned.items()):
        p = ENG / rel
        if not p.exists():
            missing.append(rel)
            continue
        got = sha256(p)
        if got == want:
            continue
        if rel in KNOWN_DELTA and got == KNOWN_DELTA[rel][0]:
            delta.append(rel)
        else:
            bad.append("%s: %s != %s" % (rel, got[:8], want[:8]))
    present = len(pinned) - len(missing)
    chk(not bad, "pinned artefacts reconciling with MANIFEST", "0 unexplained mismatches",
        "%d unexplained (%d exact + %d known delta of %d present)"
        % (len(bad), present - len(delta) - len(bad), len(delta), present),
        "" if not bad else "; ".join(bad))
    for rel in delta:
        print("  note  %-46s known release delta: %s" % (rel, KNOWN_DELTA[rel][1]))
    if missing:
        # absent by design: raw geometry and the 80 screenshots are not redistributed (see README)
        print("  note  %d pinned paths absent from the release, by design: %s"
              % (len(missing), ", ".join(missing)))
    snap = sha256(AUDIT / "scripts_snapshot" / "figs_nr10_schematic.py")
    live = sha256(ENG / "figs_nr10_schematic.py")
    chk(snap == live, "scripts_snapshot pins the published figure scripts",
        "snapshot == engine copy", "%s == %s" % (snap[:8], live[:8]))

    # -------------------------------------------------- 9. figures
    print("\n9. the published figures (figures/)")
    figs = sorted((ROOT / "figures").glob("fig*.png"))
    chk(len(figs) == 9 and all(f.stat().st_size > 20000 for f in figs),
        "Fig. 1-7 PNGs on disk (Fig. 7 has 3 panels)", "9 files > 20 KB", "%d files" % len(figs))

    print("\n%s   %d checks, %d failed" % ("ALL PASS" if not _fails else "FAILED",
                                           _checks[0], len(_fails)))
    if _fails:
        for f in _fails:
            print("  failed: %s" % f)
    print("see VALIDATION.md for the three validation layers and the figure -> script -> input map")
    return 1 if _fails else 0


# =================================================================== run / demo
def run():
    missing = [s for s in SITES if not (ENG / "data" / s / "buildings.parquet").exists()]
    if missing:
        print("The per-site building caches are NOT distributed: they are Baidu-derived geometry")
        print("(footprints + heights) and re-hosting them is not permitted. This repo ships the")
        print("DERIVED measurements (engine/out/) + the code that produced them.")
        print("")
        print("To recompute from scratch you need the licensed upstream Shanghai dataset; every")
        print("layer and its licence is listed in engine/audit/foar_figures/PROVENANCE.md.")
        print("With the caches rebuilt (pf_common.build_cache, one call per site in config/sites.yaml):")
        print("  cd engine")
        print("  python run_cake_all.py all    # metrics_cake_all.json, reachable_*, ledgers, skylines")
        print("  python aux_csv_nr10.py        # the four traceability CSVs")
        print("  python figs_nr10.py all && python figs_nr10_schematic.py all")
        print("  python figs_nr10_embed.py all # restore audit/foar_figures/embed_cache_frozen/ first")
        print("  python verify_cake_nr10.py    # the 34 pinned checks")
        print("")
        print("Without the upstream data every published number is still fully checkable:")
        print("  python reproduce.py --verify")
        return 0
    print("caches present; recomputing the eight-site run...")
    return subprocess.call([sys.executable, str(ENG / "run_cake_all.py"), "all"], cwd=str(ENG))


def demo():
    p = ARCHIVE / "reproduce.py"
    if not p.exists():
        sys.exit("archived demo not found: %s" % p)
    print("the synthetic-district demo belongs to the archived 5-district generation; delegating to")
    print("  %s --demo\n" % p)
    return subprocess.call([sys.executable, str(p), "--demo"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="reconcile every published number from engine/out/")
    ap.add_argument("--run", action="store_true", help="recompute the artefacts (needs the licensed caches)")
    ap.add_argument("--demo", action="store_true", help="run the engine on a synthetic district")
    a = ap.parse_args()
    if a.verify:
        sys.exit(verify())
    elif a.run:
        sys.exit(run())
    elif a.demo:
        sys.exit(demo())
    else:
        ap.print_help()
