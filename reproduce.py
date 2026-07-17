#!/usr/bin/env python3
"""
reproduce.py - one entry point for the auditable parametric instrument.

  python reproduce.py --verify   recompute and reconcile the published numbers from the frozen
                                 derived artefacts in engine/out/ (no licensed data needed).
                                 72 checks; exits non-zero if any of them fails. VALIDATION.md
                                 lists what is checked and what ships unchecked.
  python reproduce.py --run      recompute the artefacts from the per-site caches. The caches are
                                 Baidu-derived geometry and are NOT redistributed; see README.md.

This repo ships DERIVED measurements + code, never raw geometry. --verify reads only
JSON/CSV/PNG artefacts: it hard-codes the EXPECTED value published in the paper, RECOMPUTES the
actual value from the artefacts, prints both, and compares. It does NOT re-check every cell of
every shipped file; VALIDATION.md names the 72 checks and the columns left unchecked.
"""
import sys, json, csv, math, argparse, hashlib, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENG = ROOT / "engine"
OUT = ENG / "out" / "cake"
FIGS = ENG / "out" / "cake_figs"
AUDIT = ENG / "audit" / "foar_figures"

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
    print("scope:  72 named checks. VALIDATION.md lists them, and names the columns of the shipped")
    print("        artefacts that no verifier opens. This is not a cell-by-cell re-read of the tree.")

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
    shr = [(s, k, sum(v["shares_gfa"].values())) for s in SITES for k, v in A[s].items()
           if isinstance(v, dict) and "shares_gfa" in v]
    dmax = max(abs(t - 1.0) for _, _, t in shr)
    chk(len(shr) == 88 and dmax <= 5e-4, "one building, one holder: shares sum to 1 per site",
        "1.000 +/- 5e-04 in every run", "max |sum - 1| = %.3e over %d runs" % (dmax, len(shr)),
        "the residual is 4 dp rounding of the four shares, not leakage")

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
    pinned = {}   # every sha256 in the manifest whose file is shipped; path relative to engine/
    pinned.update({k: v["sha256"] for k, v in M["scripts"].items()})
    pinned.update({"audit/foar_figures/scripts_snapshot/" + k: v
                   for k, v in M["scripts_snapshot"]["sha256"].items()})
    pinned.update({k: v for k, v in M["helpers"].items() if not k.startswith("$")})
    pinned.update({k: v["sha256"] for k, v in M["upstream_producers"].items()
                   if not k.startswith("$")})
    pinned.update({k: v for k, v in M["configs"].items()})
    pinned.update({k: v for k, v in M["frozen_data_inputs"].items() if not k.startswith("$")})
    pinned.update({e["path"]: e["sha256"] for e in M["embed_cache_frozen"] if "path" in e})
    pinned[M["verification"]["script"]] = M["verification"]["sha256"]
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
    chk(not missing, "every pinned path is present in the release", "0 absent",
        "%d absent of %d pinned" % (len(missing), len(pinned)),
        "" if not missing else "; ".join(missing))
    chk(not bad, "pinned artefacts reconciling with MANIFEST", "0 unexplained mismatches",
        "%d unexplained (%d exact + %d known delta of %d pinned)"
        % (len(bad), present - len(delta) - len(bad), len(delta), len(pinned)),
        "" if not bad else "; ".join(bad))
    for rel in delta:
        print("  note  %-46s known release delta: %s" % (rel, KNOWN_DELTA[rel][1]))
    for fs in ("figs_nr10.py", "figs_nr10_embed.py", "figs_nr10_schematic.py"):
        snap = sha256(AUDIT / "scripts_snapshot" / fs)
        live = sha256(ENG / fs)
        chk(snap == live, "snapshot == engine copy: %s" % fs, "byte-identical",
            "%s == %s" % (snap[:8], live[:8]))

    # -------------------------------------------------- 9. figures
    print("\n9. the published figures (figures/)")
    figs = sorted((ROOT / "figures").glob("fig*.png"))
    chk(len(figs) == 9 and all(f.stat().st_size > 20000 for f in figs),
        "Fig. 1-7 PNGs on disk (Fig. 7 has 3 panels)", "9 files > 20 KB", "%d files" % len(figs))
    fpin = {k: v["sha256"] for k, v in M["published_figures"].items() if not k.startswith("$")}
    fbad = [rel for rel, want in sorted(fpin.items())
            if not (ROOT / rel).exists() or sha256(ROOT / rel) != want]
    chk(len(fpin) == 9 and not fbad, "the nine PNGs reconcile with MANIFEST.published_figures",
        "9 of 9 sha256 exact", "%d of %d exact" % (len(fpin) - len(fbad), len(fpin)),
        "" if not fbad else "; ".join(fbad))

    # -------------------------------------------------- 10. ledgers, skylines, traceability CSVs
    print("\n10. the shipped artefacts the audit used to leave unopened")
    print("    (83 ledger_*.csv, 8 skyline_*.json, invariance / rule_comparison / weakness_dist /")
    print("     age_layer_stats .csv - recomputed here, not merely shipped)")
    led = sorted(OUT.glob("ledger_*.csv"))
    chk(len(led) == 83, "per-building ledgers shipped", "83 files", "%d files" % len(led))
    lrows = {p.name: sum(1 for _ in open(p, encoding="utf-8")) - 1 for p in led}
    mism, npair = [], 0
    for s in SITES:
        for k, v in A[s].items():
            if isinstance(v, dict) and "acquired_n" in v:
                npair += 1
                if lrows.get("ledger_%s_%s.csv" % (s, k)) != v["acquired_n"]:
                    mism.append("%s_%s" % (s, k))
    chk(npair == 80 and not mism, "ledger rows == acquired_n in every scenario run",
        "80 runs, 0 mismatches", "%d runs, %d mismatches" % (npair, len(mism)),
        "" if not mism else ", ".join(mism))
    ppl = lrows["ledger_pengpu_resident_retain_B.csv"]
    chk(ppl == 0 and pp["resident_retain_B"]["acquired_n"] == 0,
        "pengpu resident-led ledger: nothing is taken", "0 rows (acquired_n = 0)",
        "%d rows (acquired_n = %d)" % (ppl, pp["resident_retain_B"]["acquired_n"]))
    sky_n, sky_bad = 0, set()
    HOLDERS = {"state", "developer", "resident", "unknown"}
    for s in SITES:
        cur = json.load(open(OUT / ("skyline_%s.json" % s), encoding="utf-8"))["current"]
        sky_n += len(cur)
        if int(max(r[1] for r in cur)) != int(A[s]["current"]["fingerprint"]["h_max"]):
            sky_bad.add(s)
        if set(r[2] for r in cur) - HOLDERS:
            sky_bad.add(s)
    chk(sky_n == 11397, "skyline_<slug>.json: buildings carried, 8 sites", "11,397",
        "{:,}".format(sky_n))
    chk(not sky_bad, "skyline h_max == Table 1 h_max; holders in the 4 declared classes",
        "8 of 8 sites agree", "%d of 8 agree" % (8 - len(sky_bad)))

    RC = list(csv.DictReader(open(OUT / "rule_comparison.csv", encoding="utf-8")))
    lift = {}
    for r in RC:
        lift.setdefault(r["rule"], []).append(float(r["lift_over_pool"]))
    mlift = {k: sum(v) / len(v) for k, v in lift.items()}
    chk(len(RC) == 32 and sorted(lift) == ["adjacency_first", "random", "value_first", "weak_first"]
        and all(len(v) == 8 for v in lift.values()),
        "rule_comparison.csv: 4 ordering rules x 8 sites", "32 rows", "%d rows" % len(RC))
    for rule, exp in [("weak_first", 0.214), ("random", -0.002), ("value_first", -0.155),
                      ("adjacency_first", -0.031)]:
        chk(close(round(mlift[rule], 3), exp, 0.0005), "mean weakness lift over pool: %-15s" % rule,
            "%+.3f" % exp, "%+.4f" % mlift[rule])
    chk(mlift["weak_first"] > mlift["random"] > mlift["adjacency_first"] > mlift["value_first"],
        "weak_first takes the weakest, the other three rules do not",
        "weak > random > adjacency > value", " > ".join(
            k for k in sorted(mlift, key=lambda x: -mlift[x])))

    WD = list(csv.DictReader(open(OUT / "weakness_dist.csv", encoding="utf-8")))
    wpool = [r for r in WD if r["pool"] == "acquirable_pool_developer"]
    ties = [float(r["tie_share_exact"]) for r in wpool]
    chk(len(WD) == 48 and len(wpool) == 8, "weakness_dist.csv: 6 pools x 8 sites", "48 rows",
        "%d rows (%d pool rows)" % (len(WD), len(wpool)))
    chk(min(ties) >= 0.88 and max(ties) <= 0.995, "weakness ties inside the acquirable pool",
        "88-99 % of the pool tied", "%.1f-%.1f %%" % (100 * min(ties), 100 * max(ties)),
        "the weakness score is coarse: order, not a ruler")

    AL = list(csv.DictReader(open(OUT / "age_layer_stats.csv", encoding="utf-8")))
    cov = [float(r["age_coverage"]) for r in AL]
    cens = sorted(set(r["censor_year"] for r in AL))
    chk(len(AL) == 16 and cens == ["1984"], "age_layer_stats.csv: 2 pools x 8 sites, right-censored",
        "16 rows, censor 1984", "%d rows, censor %s" % (len(AL), "/".join(cens)))
    chk(min(cov) >= 0.48 and max(cov) <= 0.71, "construction-year coverage over the 16 pools",
        "0.48-0.71 of buildings dated", "%.4f-%.4f" % (min(cov), max(cov)))

    IV = list(csv.DictReader(open(OUT / "invariance.csv", encoding="utf-8")))
    sens = [r for r in IV if r["test"] == "sensitivity"]
    abl = [r for r in IV if r["test"].startswith("ablation")]
    chk(len(IV) == 90 and len(sens) == 50 and len(abl) == 40,
        "invariance.csv: sensitivity + ablation rows", "90 rows (50 + 40)",
        "%d rows (%d + %d)" % (len(IV), len(sens), len(abl)))
    smet = [r for r in sens if r["met"] == "True" and float(r["reached"]) >= 0.7999]
    chk(len(smet) == 50 == len(sens),
        "developer target met under every weakness weighting", "50 of 50 runs (reached >= 0.80)",
        "%d of %d runs" % (len(smet), len(sens)),
        "5 districts x (w_age, w_gap) in 5 splits x missing_age in {zero, median}")
    loss = [float(r["resident_loss_share"]) for r in sens]
    chk(min(loss) == 1.0 and max(loss) == 1.0, "residents bear the whole loss, every weighting",
        "1.000 in 50 of 50", "%.3f-%.3f in %d runs" % (min(loss), max(loss), len(loss)))
    cells = {}
    for r in abl:
        cells.setdefault((r["test"], r["district"]), {})[r["rule"]] = float(r["lift_over_pool"])
    won = [k for k, v in cells.items() if max(v, key=lambda x: v[x]) == "weak_first"]
    chk(len(cells) == 10 and len(won) == 10, "weak_first leads the ablation in every cell",
        "10 of 10 (5 districts x 2 intensities)", "%d of %d" % (len(won), len(cells)))

    print("\n%s   %d checks, %d failed" % ("ALL PASS" if not _fails else "FAILED",
                                           _checks[0], len(_fails)))
    if _fails:
        for f in _fails:
            print("  failed: %s" % f)
    print("see VALIDATION.md for the three validation layers and the figure -> script -> input map")
    return 1 if _fails else 0


# =================================================================== run
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
        print("Without the upstream data the published numbers are still checkable:")
        print("  python reproduce.py --verify    # 72 checks; VALIDATION.md lists them one by one")
        return 0
    print("caches present; recomputing the eight-site run...")
    return subprocess.call([sys.executable, str(ENG / "run_cake_all.py"), "all"], cwd=str(ENG))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true",
                    help="recompute the published numbers from engine/out/ (72 checks)")
    ap.add_argument("--run", action="store_true", help="recompute the artefacts (needs the licensed caches)")
    a = ap.parse_args()
    if a.verify:
        sys.exit(verify())
    elif a.run:
        sys.exit(run())
    else:
        ap.print_help()
