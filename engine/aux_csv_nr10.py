"""
aux_csv_nr10.py — traceability CSVs for NEXT_RUN_10.

Every diagnostic the last report stated in prose but kept in no file. Four CSVs, all NEW files,
written next to the frozen artefacts and touching none of them:

    out/cake/rule_comparison.csv   ordering-rule ablation at the LIGHT target, all 8 sites
    out/cake/weakness_dist.csv     the weakness distribution itself (and its ties), per site x pool
    out/cake/gamma_bind.csv        does the regulatory envelope bind? site x configuration x gamma
    out/cake/age_layer_stats.csv   age coverage, right-censoring at 1984, and who carries the score

Nothing here re-runs or re-writes metrics_cake.json, metrics_cake_all.json, invariance.csv, the
ledgers, the skylines or the reachable grids. rule_comparison.csv is CHECKED against the frozen
invariance.csv for the five frozen sites: if the engine had drifted, the check prints a deviation.

  python3 aux_csv_nr10.py            all four
  python3 aux_csv_nr10.py rules|dist|gamma|age
"""
import sys, csv, copy, json
from pathlib import Path
from collections import Counter
import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pf_common as C
import measure as M
import cake

OUT = HERE / "out" / "cake"; OUT.mkdir(parents=True, exist_ok=True)
SITES_ALL = ["lujiazui", "nanjingxi", "caoyang", "pengpu", "laoximen", "yuyuan", "dapuqiao", "zhangjiang"]
FROZEN5 = ["lujiazui", "caoyang", "laoximen", "dapuqiao", "yuyuan"]
CFG = cake.load_cfg()
FAMILY = {s["slug"]: s["family"] for s in yaml.safe_load(open(HERE / "config" / "sites.yaml", encoding="utf-8"))["sites"]}

# the four power configurations, in the paper's language
CORNERS = [("developer_led", "capital_deepen"),
           ("state_led", "state_civic"),
           ("resident_led", "resident_retain"),
           ("shared", "shared_commons")]
RULES = ["weak_first", "random", "adjacency_first", "value_first"]
CENSOR_YEAR = 1984          # the age layer's lower bound: everything older is recorded as 1984
SEED = 7                    # same seed run_cake.invariance() uses, so the frozen 5 must reproduce


def base(slug):
    recs = C.load_buildings(slug)
    cov = M.diagnose([dict(r) for r in recs], slug)["coverage"]
    return recs, cov


def gate_pool(recs, grow):
    """exactly the pool cake.run_scenario builds for a growing class (no scenario overrides)."""
    gate = CFG["gates"][grow]
    return [r for r in recs
            if r["sh"] in gate["from"]
            and (gate["euluc_in"] is None or r.get("euluc") in gate["euluc_in"])
            and not r["frozen"]]


def wscore(recs, cov):
    """weakness at the config default (w_age .5, w_gap .5, missing_age zero -> age_median unused)."""
    return [cake.weakness_score(r, CFG, cov, None) for r in recs]


def _q(v, p):
    return float(np.percentile(v, p)) if len(v) else float("nan")


def write(name, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    p = OUT / name
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("wrote %s (%d rows)" % (p, len(rows)))
    return p


# ------------------------------------------------------------------ 1 rule_comparison.csv
def rules():
    """The honest test of the ordering rule: the LIGHT target (current developer share + 0.05), where
    the pool is far from exhausted and the rule still has a choice. At the heavy target (0.80) capital
    eats nearly the whole pool and every rule converges on the same set, which tests nothing."""
    rows = []
    for slug in SITES_ALL:
        recs, cov = base(slug)
        cur_dev = cake.read_shares(recs)["gfa"]["developer"]
        target = round(cur_dev + 0.05, 3)
        pool = gate_pool(recs, "developer")
        pool_w = wscore(pool, cov)
        pool_mean = float(np.mean(pool_w)) if pool_w else float("nan")
        for rule in RULES:
            sc = dict(CFG["scenarios"]["capital_deepen"])
            sc["rule"] = rule
            sc["target"] = target
            r = cake.run_scenario(recs, sc, CFG, mode="grow", slug=slug, coverage=cov, seed=SEED)
            w = [l["weakness"] for l in r["ledger"]]
            d = r["displacement_gfa"]
            tot = sum(d.values()) or 1.0
            rows.append(dict(
                site=slug, family=FAMILY[slug], mode="B_grow", scenario="capital_deepen",
                intensity="light", current_dev_share=round(cur_dev, 4), target=target,
                rule=rule,
                acquired_n=r["acquired_n"], pool_size=r["pool_size"],
                pool_taken_frac=round(r["acquired_n"] / max(r["pool_size"], 1), 4),
                mean_weakness_taken=(round(float(np.mean(w)), 4) if w else ""),
                median_weakness_taken=(round(float(np.median(w)), 4) if w else ""),
                sd_weakness_taken=(round(float(np.std(w)), 4) if w else ""),
                min_weakness_taken=(round(float(np.min(w)), 4) if w else ""),
                max_weakness_taken=(round(float(np.max(w)), 4) if w else ""),
                pool_mean_weakness=round(pool_mean, 4),
                lift_over_pool=(round(float(np.mean(w)) - pool_mean, 4) if w else ""),
                share_reached=r["share_reached"], target_met=r["target_met"],
                pool_exhausted=r["pool_exhausted"],
                resident_loss_share=round(d["resident"] / tot, 4),
                displaced_resident_gfa=round(d["resident"], 1),
                gfa_change_pct=r["gfa_change_pct"],
                envelope_bind_n=r["envelope_bind_n"]))
            print("  %-11s %-16s took %4d/%4d  mean w %.3f  lift %+.3f"
                  % (slug, rule, r["acquired_n"], r["pool_size"],
                     float(np.mean(w)) if w else float("nan"),
                     (float(np.mean(w)) - pool_mean) if w else float("nan")), flush=True)
    p = write("rule_comparison.csv", rows)

    # --- cross-check against the FROZEN invariance.csv (read only) -----------------------------
    inv = OUT / "invariance.csv"
    if inv.exists():
        old = [r for r in csv.DictReader(open(inv, encoding="utf-8")) if r["test"] == "ablation_light"]
        worst, worst_at, n = 0.0, "", 0
        for o in old:
            m = [r for r in rows if r["site"] == o["district"] and r["rule"] == o["rule"]]
            if not m:
                continue
            new = m[0]
            for kn, ko in (("mean_weakness_taken", "mean_weakness_taken"),
                           ("pool_mean_weakness", "pool_mean_weakness"),
                           ("lift_over_pool", "lift_over_pool"),
                           ("pool_taken_frac", "pool_taken_frac"),
                           ("acquired_n", "acquired"), ("share_reached", "reached")):
                # invariance.csv rounds each field to its own number of decimals (pool_taken_frac to 3,
                # the rest to 4). Round the fresh value to the SAME decimals before differencing, or the
                # comparison reports a rounding artefact as engine drift.
                s = str(o[ko])
                dp = len(s.split(".")[1]) if "." in s else 0
                try:
                    dv = abs(round(float(new[kn]), dp) - float(s))
                except (ValueError, TypeError):
                    continue
                n += 1
                if dv > worst:
                    worst, worst_at = dv, "%s/%s/%s" % (o["district"], o["rule"], kn)
        print("\nCHECK vs frozen invariance.csv (ablation_light, 5 frozen sites): %d values, "
              "max deviation %.2e at %s" % (n, worst, worst_at or "-"))
        print("  verdict: %s" % ("MATCH (engine reproduces the frozen run exactly)"
                                 if worst <= 1e-9 else "DRIFT"))

    # headline
    print("\nDISCRIMINATION at the light target, 8 sites:")
    for rule in RULES:
        sub = [r for r in rows if r["rule"] == rule and r["acquired_n"] > 0]
        print("  %-16s mean weakness taken %.3f | lift %+.3f | took %.1f%% of the pool | n=%d sites"
              % (rule,
                 float(np.mean([r["mean_weakness_taken"] for r in sub])),
                 float(np.mean([r["lift_over_pool"] for r in sub])),
                 100 * float(np.mean([r["pool_taken_frac"] for r in sub])), len(sub)))
    return p


# ------------------------------------------------------------------ 2 weakness_dist.csv
def _tie_stats(v, dp=None):
    """how tied is this distribution? A tie-heavy score makes 'weakest first' an arbitrary order."""
    x = [round(a, dp) for a in v] if dp is not None else list(v)
    c = Counter(x)
    n = len(x) or 1
    tied_n = sum(k for k in c.values() if k >= 2)
    top_val, top_n = (c.most_common(1)[0] if c else (float("nan"), 0))
    return {"n_distinct": len(c), "distinct_frac": round(len(c) / n, 4),
            "tie_share": round(tied_n / n, 4),
            "modal_value": round(float(top_val), 4), "modal_n": top_n,
            "modal_frac": round(top_n / n, 4)}


def dist():
    """The distribution the ordering rule sorts on. If it is tie-heavy, 'weak first' is partly a
    coin-flip, and the tie-break (lowest bid) is doing work the politics is supposed to do."""
    rows = []
    for slug in SITES_ALL:
        recs, cov = base(slug)
        groups = [("all", recs),
                  ("acquirable_pool_developer", gate_pool(recs, "developer")),
                  ("state", [r for r in recs if r["sh"] == "state"]),
                  ("developer", [r for r in recs if r["sh"] == "developer"]),
                  ("resident", [r for r in recs if r["sh"] == "resident"]),
                  ("unknown", [r for r in recs if r["sh"] == "unknown"])]
        for gname, g in groups:
            if not g:
                continue
            v = np.array(wscore(g, cov))
            t_ex = _tie_stats(v.tolist(), None)          # exact float ties: what the sort actually sees
            t_4 = _tie_stats(v.tolist(), 4)              # ties at the 4dp the ledger reports
            rows.append(dict(
                site=slug, family=FAMILY[slug], pool=gname, n=len(g),
                w_age=CFG["weakness"]["w_age"], w_gap=CFG["weakness"]["w_gap"],
                missing_age=CFG["weakness"]["missing_age"], coverage=round(cov, 4),
                min=round(float(v.min()), 4), q1=round(_q(v, 25), 4), median=round(_q(v, 50), 4),
                q3=round(_q(v, 75), 4), max=round(float(v.max()), 4),
                mean=round(float(v.mean()), 4), sd=round(float(v.std()), 4),
                iqr=round(_q(v, 75) - _q(v, 25), 4),
                n_distinct_exact=t_ex["n_distinct"], distinct_frac_exact=t_ex["distinct_frac"],
                tie_share_exact=t_ex["tie_share"],
                n_distinct_4dp=t_4["n_distinct"], distinct_frac_4dp=t_4["distinct_frac"],
                tie_share_4dp=t_4["tie_share"],
                modal_value_4dp=t_4["modal_value"], modal_n_4dp=t_4["modal_n"],
                modal_frac_4dp=t_4["modal_frac"],
                share_at_zero=round(float((v <= 1e-12).mean()), 4),
                share_no_far_gap=round(float(np.mean([
                    cake.far_actual(r, CFG, cov) >= cake.far_allowed(r, CFG) for r in g])), 4)))
            print("  %-11s %-26s n=%5d  mean %.3f sd %.3f  distinct %4d (%.1f%%)  tied %.1f%%"
                  % (slug, gname, len(g), v.mean(), v.std(), t_4["n_distinct"],
                     100 * t_4["distinct_frac"], 100 * t_4["tie_share"]), flush=True)
    return write("weakness_dist.csv", rows)


# ------------------------------------------------------------------ 3 gamma_bind.csv
def _uncapped_targets(recs, ledger, cov, far_mult, platform=False):
    """the height the new owner WOULD have built, ignoring the envelope, for every acquired building.
    Same call cake.run_scenario makes with envelope = 1e9, so the two agree by construction."""
    by_bid = {r["bid"]: r for r in recs}
    out = []
    for l in ledger:
        r = by_bid[l["bid"]]
        u = cake.rebuild(dict(r, h=l["h_before"]), l["to_sh"], CFG, cov, 1e9,
                         mode_platform=platform, far_mult=far_mult)
        out.append((l["h_before"], u, r["area"]))
    return out


def gamma():
    """Does the regulatory envelope actually bite? The gate lets capital take residential stock only
    (FAR 2.5), and the rebuild target is FAR * floor_h / coverage, so on the real coverages the target
    lands far below the 60 m base envelope. The other three configurations rebuild DOWNWARD (civic
    band, resident cap, platform), so the envelope cannot bind on them by construction. This CSV says
    so with numbers, and sweeps the envelope down to find where it would start to bite."""
    rows = []
    for slug in SITES_ALL:
        recs, cov = base(slug)
        # the canonical residential rebuild target, the number that decides the whole question
        h_res = 2.5 * CFG["meta"]["floor_h"] / cov * CFG["rebuild"]["kappa"]      # 居住用地 FAR 2.5
        h_def = CFG["far_allowed"]["_default"]["far"] * CFG["meta"]["floor_h"] / cov * CFG["rebuild"]["kappa"]
        for cname, sname in CORNERS:
            sc = CFG["scenarios"][sname]
            plat = (sc.get("rebuild_override") == "platform")
            for gname in ("strict", "base", "permissive", "none"):
                gam = CFG["gamma"][gname]
                r = cake.run_scenario(recs, sc, CFG, mode="grow", gamma=gname, slug=slug,
                                      coverage=cov, seed=SEED)
                tg = _uncapped_targets(recs, r["ledger"], cov, float(gam["far_mult"]), plat)
                up = [(h0, u, a) for h0, u, a in tg if u > h0 + 1e-9]     # buildings that gain height
                utg = [u for _, u, _ in up]
                V_after = sum(l["gfa_after"] for l in r["ledger"])
                rows.append(dict(
                    site=slug, family=FAMILY[slug], configuration=cname, scenario=sname,
                    mode="B_grow", row_type="gamma_setting", gamma=gname,
                    far_mult=gam["far_mult"], envelope_m=gam["height_m"],
                    coverage=round(cov, 4),
                    rebuild_direction=("up" if cname == "developer_led" else "down"),
                    acquired_n=r["acquired_n"],
                    n_with_uplift=len(up),
                    envelope_bind_n=r["envelope_bind_n"],
                    envelope_bind_frac=round(r["envelope_bind_n"] / max(r["acquired_n"], 1), 4),
                    envelope_clipped_gfa=r["envelope_clipped_gfa"],
                    clipped_frac_of_acquired_gfa=round(r["envelope_clipped_gfa"] / V_after, 4) if V_after else 0.0,
                    rebuild_target_h_min=(round(min(utg), 2) if utg else ""),
                    rebuild_target_h_median=(round(float(np.median(utg)), 2) if utg else ""),
                    rebuild_target_h_max=(round(max(utg), 2) if utg else ""),
                    h_target_residential_far2p5=round(h_res * float(gam["far_mult"]), 2),
                    h_target_default_far3p0=round(h_def * float(gam["far_mult"]), 2),
                    headroom_m=(round(float(gam["height_m"]) - max(utg), 2) if utg else ""),
                    envelope_first_bites_below_m=(round(max(utg), 2) if utg else ""),
                    envelope_bites_all_below_m=(round(min(utg), 2) if utg else ""),
                    share_reached=r["share_reached"], target_met=r["target_met"],
                    gfa_change_pct=r["gfa_change_pct"]))
            print("  %-11s %-14s base: bind %d / acq %d, clipped %.0f m3"
                  % (slug, cname, rows[-3]["envelope_bind_n"], rows[-3]["acquired_n"],
                     rows[-3]["envelope_clipped_gfa"]), flush=True)

        # --- height-only sweep, developer_led (the only configuration that builds UPWARD) --------
        for hm in (20, 25, 30, 35, 40, 45, 50, 55, 60, 80, 120):
            cfg2 = copy.deepcopy(CFG)
            cfg2["gamma"]["sweep"] = {"far_mult": 1.0, "height_m": float(hm)}
            r = cake.run_scenario(recs, CFG["scenarios"]["capital_deepen"], cfg2, mode="grow",
                                  gamma="sweep", slug=slug, coverage=cov, seed=SEED)
            tg = _uncapped_targets(recs, r["ledger"], cov, 1.0)
            up = [(h0, u, a) for h0, u, a in tg if u > h0 + 1e-9]
            utg = [u for _, u, _ in up]
            V_after = sum(l["gfa_after"] for l in r["ledger"])
            rows.append(dict(
                site=slug, family=FAMILY[slug], configuration="developer_led", scenario="capital_deepen",
                mode="B_grow", row_type="height_sweep", gamma="sweep_h%d" % hm,
                far_mult=1.0, envelope_m=float(hm), coverage=round(cov, 4), rebuild_direction="up",
                acquired_n=r["acquired_n"], n_with_uplift=len(up),
                envelope_bind_n=r["envelope_bind_n"],
                envelope_bind_frac=round(r["envelope_bind_n"] / max(r["acquired_n"], 1), 4),
                envelope_clipped_gfa=r["envelope_clipped_gfa"],
                clipped_frac_of_acquired_gfa=round(r["envelope_clipped_gfa"] / V_after, 4) if V_after else 0.0,
                rebuild_target_h_min=(round(min(utg), 2) if utg else ""),
                rebuild_target_h_median=(round(float(np.median(utg)), 2) if utg else ""),
                rebuild_target_h_max=(round(max(utg), 2) if utg else ""),
                h_target_residential_far2p5=round(h_res, 2),
                h_target_default_far3p0=round(h_def, 2),
                headroom_m=(round(hm - max(utg), 2) if utg else ""),
                envelope_first_bites_below_m=(round(max(utg), 2) if utg else ""),
                envelope_bites_all_below_m=(round(min(utg), 2) if utg else ""),
                share_reached=r["share_reached"], target_met=r["target_met"],
                gfa_change_pct=r["gfa_change_pct"]))
    p = write("gamma_bind.csv", rows)
    b = [r for r in rows if r["row_type"] == "gamma_setting" and r["gamma"] == "base"]
    print("\nBASE GAMMA (60 m, far_mult 1.0), 8 sites x 4 configurations, mode B:")
    print("  rows                    : %d" % len(b))
    print("  rows with bind_n > 0    : %d" % sum(1 for r in b if r["envelope_bind_n"] > 0))
    print("  total clipped floor vol : %.1f m3" % sum(r["envelope_clipped_gfa"] for r in b))
    dv = [r for r in b if r["configuration"] == "developer_led"]
    print("  developer_led rebuild target height, across the 8 sites: %.1f to %.1f m (envelope 60 m)"
          % (min(r["rebuild_target_h_min"] for r in dv), max(r["rebuild_target_h_max"] for r in dv)))
    sw = [r for r in rows if r["row_type"] == "height_sweep"]
    print("\nHEIGHT SWEEP, developer_led: envelope at which the first building is clipped, per site")
    for slug in SITES_ALL:
        s = [r for r in sw if r["site"] == slug]
        bite = [r for r in s if r["envelope_bind_n"] > 0]
        first = max((r["envelope_m"] for r in bite), default=None)
        print("  %-11s target h %.1f-%.1f m | first clip at envelope <= %s m | at 30 m: %d/%d clipped"
              % (slug, s[0]["rebuild_target_h_min"], s[0]["rebuild_target_h_max"],
                 ("%.0f" % first if first else "never in sweep"),
                 [r for r in s if r["envelope_m"] == 30][0]["envelope_bind_n"],
                 s[0]["acquired_n"]))
    return p


# ------------------------------------------------------------------ 4 age_layer_stats.csv
def _spearman(a, b):
    if len(a) < 3:
        return float("nan")
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def age():
    """How much of the weakness score is age actually carrying? The age layer stops at 1984 (no dated
    building is older) and covers only half to two thirds of the stock; where it is missing the score
    sets AGE = 0, so the FAR gap carries the ordering alone. And where it is PRESENT it is mostly a
    single value: the censored mass sits at 1985, not at the 1984 floor. Both facts are in the CSV."""
    rows = []
    yr = CFG["meta"]["year_now"]; ref = CFG["meta"]["age_ref"]
    wa, wg = float(CFG["weakness"]["w_age"]), float(CFG["weakness"]["w_gap"])
    for slug in SITES_ALL:
        recs, cov = base(slug)
        for gname, g in (("all", recs), ("acquirable_pool_developer", gate_pool(recs, "developer"))):
            if not g:
                continue
            ages = [r["age"] for r in g if r.get("age")]
            n = len(g)
            cnt = Counter(ages)
            mode_y, mode_n = (cnt.most_common(1)[0] if cnt else ("", 0))
            AGE = np.array([min(max((yr - r["age"]) / ref, 0.0), 1.0) if r.get("age") else 0.0 for r in g])
            GAP = np.array([
                min(max((cake.far_allowed(r, CFG) - cake.far_actual(r, CFG, cov)) / cake.far_allowed(r, CFG), 0.0), 1.0)
                if cake.far_allowed(r, CFG) > 0 else 0.0 for r in g])
            W = wa * AGE + wg * GAP
            a_term = wa * AGE
            g_term = wg * GAP
            rows.append(dict(
                site=slug, family=FAMILY[slug], pool=gname, n=n,
                n_with_age=len(ages), age_coverage=round(len(ages) / n, 4),
                censor_year=CENSOR_YEAR,
                n_at_censor=sum(1 for a in ages if a <= CENSOR_YEAR),
                share_at_censor_of_dated=(round(sum(1 for a in ages if a <= CENSOR_YEAR) / len(ages), 4) if ages else ""),
                share_at_censor_of_all=round(sum(1 for a in ages if a <= CENSOR_YEAR) / n, 4),
                # the real mass point: the layer's floor is 1984, but the pile-up sits at 1985
                year_mode=(int(mode_y) if ages else ""), n_at_mode=mode_n,
                share_at_mode_of_dated=(round(mode_n / len(ages), 4) if ages else ""),
                share_at_mode_of_all=round(mode_n / n, 4),
                share_le_1985_of_dated=(round(sum(1 for a in ages if a <= 1985) / len(ages), 4) if ages else ""),
                age_term_at_mode=(round(wa * min(max((yr - mode_y) / ref, 0.0), 1.0), 4) if ages else ""),
                year_min=(int(min(ages)) if ages else ""), year_max=(int(max(ages)) if ages else ""),
                year_mean=(round(float(np.mean(ages)), 2) if ages else ""),
                year_sd=(round(float(np.std(ages)), 2) if ages else ""),
                year_sd_sample=(round(float(np.std(ages, ddof=1)), 2) if len(ages) > 1 else ""),
                year_median=(round(float(np.median(ages)), 1) if ages else ""),
                year_iqr=(round(_q(ages, 75) - _q(ages, 25), 2) if ages else ""),
                n_distinct_years=len(set(ages)),
                mean_AGE_norm=round(float(AGE.mean()), 4),
                mean_GAP_norm=round(float(GAP.mean()), 4),
                mean_weakness=round(float(W.mean()), 4),
                mean_age_component=round(float(a_term.mean()), 4),
                mean_gap_component=round(float(g_term.mean()), 4),
                gap_share_of_weakness=round(float(g_term.mean() / W.mean()), 4) if W.mean() else "",
                age_share_of_weakness=round(float(a_term.mean() / W.mean()), 4) if W.mean() else "",
                share_with_zero_age_term=round(float((AGE <= 1e-12).mean()), 4),
                spearman_w_vs_gap=round(_spearman(W, GAP), 4),
                spearman_w_vs_age=round(_spearman(W, AGE), 4)))
            if gname == "all":
                r0 = rows[-1]
                print("  %-11s age cov %.3f  mean %s sd %-5s  floor %s  mode %s = %.1f%% of dated  at 1984 %.3f  gap carries %.1f%% of the score"
                      % (slug, r0["age_coverage"], r0["year_mean"], r0["year_sd"], r0["year_min"],
                         r0["year_mode"], 100 * float(r0["share_at_mode_of_dated"]),
                         float(r0["share_at_censor_of_dated"]),
                         100 * float(r0["gap_share_of_weakness"])), flush=True)
    p = write("age_layer_stats.csv", rows)
    lx = [r for r in rows if r["site"] == "laoximen" and r["pool"] == "all"][0]
    print("\nLAOXIMEN check (the paper claims mean 1985.2, sd 0.67): mean %s, sd %s (population), %s (sample), coverage %s, %d distinct years"
          % (lx["year_mean"], lx["year_sd"], lx["year_sd_sample"], lx["age_coverage"], lx["n_distinct_years"]))
    print("\nCENSORING, as measured: the age layer's floor is 1984, but the mass sits at 1985.")
    for r in [x for x in rows if x["pool"] == "all"]:
        print("  %-11s mode %s: %5.1f%% of dated (%5.1f%% of all) | at the 1984 floor: %4.1f%% of dated | age term at the mode = %s"
              % (r["site"], r["year_mode"], 100 * float(r["share_at_mode_of_dated"]),
                 100 * float(r["share_at_mode_of_all"]), 100 * float(r["share_at_censor_of_dated"]),
                 r["age_term_at_mode"]))
    return p


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "all"
    if a in ("rules", "all"):
        print("\n=== 1 rule_comparison.csv ==="); rules()
    if a in ("dist", "all"):
        print("\n=== 2 weakness_dist.csv ==="); dist()
    if a in ("gamma", "all"):
        print("\n=== 3 gamma_bind.csv ==="); gamma()
    if a in ("age", "all"):
        print("\n=== 4 age_layer_stats.csv ==="); age()
