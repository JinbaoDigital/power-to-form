"""
cake.py — the cake model: read the city's current division of the pie, set a new one, and let the
growing side buy its way there, weakest stock first.

Five steps.
  READ        the cascade (pf_common.assign_all) says who holds each building; the cake is the total
              floor volume V = sum(area * h), and each class holds a share of it.
  SET         the user types one number: the GFA share a class should reach. That is the whole interface.
  REALLOCATE  the growing class acquires buildings from a gated pool, ordered by a weakness score
              (or by value, or at random: the ordering rule IS the politics, so it is editable).
  REBUILD     mode B only, and only the acquired buildings: the new owner changes the height. The
              footprint never moves.
  READ BACK   the same fingerprint as before, plus a ledger of who lost what.

Two modes, run separately, because taking ownership and adding floor area are two different acts:
  A redistribute   ownership changes, no height changes, total GFA conserved
  B grow           ownership changes and acquired buildings are rebuilt to the regulatory envelope

Honesty rules built into the code, not just the prose:
  - if the acquirable pool runs out before the target, the run reports pool_exhausted = True and the
    share actually reached. It never pretends to have met the target.
  - displacement is always measured on orig_h, the height before any rebuild.
  - footprint, orig_h and orig_sh are frozen for the whole run.
  - coverage, grain and n cannot move in this model (footprints are frozen) and are reported as such.
"""
from pathlib import Path
import copy
import random
import yaml
import numpy as np

import pf_common as C
import measure as M

HERE = Path(__file__).resolve().parent
CFG_PATH = HERE / "config" / "scenarios.yaml"
CLASSES = ("state", "developer", "resident")


def load_cfg(path=CFG_PATH):
    return yaml.safe_load(open(path, encoding="utf-8"))


# ------------------------------------------------------------------ 1 READ
def gfa(rec):
    return rec["area"] * rec["h"]


def read_shares(recs):
    """the cake: GFA shares and count shares. unknown is carried but never a player."""
    V = sum(gfa(r) for r in recs) or 1.0
    n = len(recs) or 1
    out = {"V": V, "n": len(recs), "gfa": {}, "count": {}}
    for c in ("state", "developer", "resident", "unknown"):
        out["gfa"][c] = sum(gfa(r) for r in recs if r["sh"] == c) / V
        out["count"][c] = sum(1 for r in recs if r["sh"] == c) / n
    return out


# ------------------------------------------------------------------ 2 weakness
def far_allowed(rec, cfg):
    tbl = cfg["far_allowed"]
    row = tbl.get(rec.get("euluc")) if rec.get("euluc") else None
    return float((row or tbl["_default"])["far"])


def far_actual(rec, cfg, coverage):
    """plot boundaries are not in the data, so district footprint coverage stands in for the plot."""
    return coverage * rec["h"] / cfg["meta"]["floor_h"]


def weakness_score(rec, cfg, coverage, age_median=None):
    w = cfg["weakness"]
    yr = cfg["meta"]["year_now"]
    ref = cfg["meta"]["age_ref"]
    if rec.get("age"):
        AGE = min(max((yr - rec["age"]) / ref, 0.0), 1.0)
    elif w.get("missing_age") == "median" and age_median is not None:
        AGE = age_median
    else:
        AGE = 0.0                      # conservative: claim no weakness rather than invent it
    fa = far_allowed(rec, cfg)
    GAP = min(max((fa - far_actual(rec, cfg, coverage)) / fa, 0.0), 1.0) if fa > 0 else 0.0
    return float(w["w_age"]) * AGE + float(w["w_gap"]) * GAP


# ------------------------------------------------------------------ 4 REBUILD
def rebuild(rec, new_sh, cfg, coverage, envelope, mode_platform=False, far_mult=1.0):
    """the new owner sets the height. footprint frozen. returns the new height."""
    rb = cfg["rebuild"]
    h = rec["h"]
    if new_sh == "developer":
        fa = far_allowed(rec, cfg) * float(far_mult)
        h_target = fa * cfg["meta"]["floor_h"] / max(coverage, 1e-6) * float(rb["kappa"])
        # capital fills the FAR gap up to the envelope. The envelope constrains the UPLIFT, it does not
        # retroactively demolish a building that is already taller than it: max(h, ...) guarantees that.
        return float(max(h, min(h_target, envelope)))
    if new_sh == "state":
        if mode_platform:
            return float(min(h, rb["platform_h"]))             # the commons flattens the top
        lo, hi = rb["civic_band"]
        return float(lo if rec["area"] >= 2000 else hi)        # big footprint -> low civic hall
    if new_sh == "resident":
        return float(min(h, rb["resident_cap"]))
    return h


# ------------------------------------------------------------------ 3 REALLOCATE (weakest first)
def order_pool(pool, rule, cfg, coverage, age_median, seed=0):
    if rule == "value_first":
        return sorted(pool, key=lambda r: (-gfa(r), r["bid"]))
    if rule == "random":
        p = list(pool)
        random.Random(seed).shuffle(p)
        return p
    if rule == "adjacency_first":
        return sorted(pool, key=lambda r: (-r["area"], r["bid"]))
    # weak_first: highest weakness first; ties break on the lowest bid so the order is deterministic
    # and carries no hidden spatial bias.
    return sorted(pool, key=lambda r: (-weakness_score(r, cfg, coverage, age_median), r["bid"]))


def _fingerprint(recs, slug, area_km2):
    """measure.diagnose needs a site area; a synthetic run supplies it directly."""
    if slug is not None:
        return M.diagnose(recs, slug)
    keep = C.site_meta
    C.site_meta = lambda _s=None, a=area_km2: {"area_km2": a}
    try:
        return M.diagnose(recs, "synthetic")
    finally:
        C.site_meta = keep


def run_scenario(recs0, sc, cfg, mode="grow", gamma=None, coverage=None, seed=0,
                 slug=None, area_km2=1.0):
    """one scenario, one mode. returns everything the paper needs, including the failure case."""
    recs = [dict(r) for r in recs0]
    if coverage is None:
        coverage = _fingerprint([dict(r) for r in recs], slug, area_km2)["coverage"]
    gam = cfg["gamma"][gamma or cfg["default_gamma"]]
    envelope = float(gam["height_m"])
    far_mult = float(gam["far_mult"])
    g = sc["grow"]
    target = float(sc["target"])
    rule = sc.get("rule", cfg["weakness"]["rule"])
    platform = sc.get("rebuild_override") == "platform"

    gate = dict(cfg["gates"][g])
    if sc.get("from_override"):
        gate["from"] = sc["from_override"]
    if "euluc_override" in sc:
        gate["euluc_in"] = sc["euluc_override"]

    ages = [r["age"] for r in recs if r.get("age")]
    age_med = None
    if ages:
        a = float(np.median(ages))
        age_med = min(max((cfg["meta"]["year_now"] - a) / cfg["meta"]["age_ref"], 0.0), 1.0)

    # incremental bookkeeping: shares must be recomputed after every acquisition, because in mode B
    # the rebuild changes both the numerator and the denominator.
    V = {c: sum(gfa(r) for r in recs if r["sh"] == c) for c in ("state", "developer", "resident", "unknown")}
    Vt = sum(V.values()) or 1.0

    pool = [r for r in recs
            if r["sh"] in gate["from"]
            and (gate["euluc_in"] is None or r.get("euluc") in gate["euluc_in"])
            and not r["frozen"]]
    pool = order_pool(pool, rule, cfg, coverage, age_med, seed)

    ledger, clipped = [], 0.0
    envelope_bind = 0
    for r in pool:
        if V[g] / Vt >= target:
            break
        src = r["sh"]
        g0 = gfa(r)
        # the weakness that MADE this building a target, measured before the new owner touches it.
        # (Computing it after the rebuild would read the new height and report the building as strong,
        # which silently inverts the whole test.)
        w_at_acquisition = weakness_score(r, cfg, coverage, age_med)
        h_new = r["h"]
        if mode == "grow":
            h_new = rebuild(r, g, cfg, coverage, envelope, platform, far_mult)
            uncapped = rebuild(r, g, cfg, coverage, 1e9, platform, far_mult)
            if uncapped > h_new + 1e-9:                        # the envelope clipped the uplift
                envelope_bind += 1
                clipped += r["area"] * (uncapped - h_new)
        g1 = r["area"] * h_new
        V[src] -= g0
        V[g] += g1
        Vt += (g1 - g0)
        r["sh"] = g
        r["h"] = h_new
        ledger.append({"bid": r["bid"], "from_sh": src, "to_sh": g,
                       "gfa_before": round(r["area"] * r["orig_h"], 2),   # orig_h: displacement is measured before any rebuild
                       "gfa_after": round(g1, 2),
                       "h_before": round(r["orig_h"], 2), "h_after": round(h_new, 2),
                       "area": round(r["area"], 1),
                       "weakness": round(w_at_acquisition, 4)})

    reached = V[g] / Vt
    exhausted = bool(reached < target - 1e-9)

    shares = read_shares(recs)
    fp = _fingerprint([dict(r) for r in recs], slug, area_km2)
    V0 = sum(r["area"] * r["orig_h"] for r in recs0)
    V1 = sum(gfa(r) for r in recs)

    # displacement: floor volume taken FROM each class, measured on orig_h
    disp = {c: sum(l["gfa_before"] for l in ledger if l["from_sh"] == c) for c in CLASSES}
    matrix = {}
    for l in ledger:
        matrix.setdefault(l["from_sh"] + "->" + l["to_sh"], 0.0)
        matrix[l["from_sh"] + "->" + l["to_sh"]] += l["gfa_before"]

    return {
        "grow": g, "target": target, "mode": mode, "rule": rule,
        "gamma": gamma or cfg["default_gamma"], "envelope_m": envelope, "far_mult": far_mult,
        "share_reached": round(reached, 4),
        "target_met": (not exhausted),
        "pool_exhausted": exhausted,
        "pool_size": len(pool),
        "acquired_n": len(ledger),
        "gfa_change_pct": round((V1 / V0 - 1) * 100, 2) if V0 else 0.0,
        "envelope_bind_n": envelope_bind,
        "envelope_clipped_gfa": round(clipped, 1),
        "shares_gfa": {k: round(v, 4) for k, v in shares["gfa"].items()},
        "shares_count": {k: round(v, 4) for k, v in shares["count"].items()},
        "displacement_gfa": {k: round(v, 1) for k, v in disp.items()},
        "displaced_n": {c: sum(1 for l in ledger if l["from_sh"] == c) for c in CLASSES},
        "transfer_matrix": {k: round(v, 1) for k, v in matrix.items()},
        "fingerprint": {k: (round(float(v), 4) if isinstance(v, (int, float)) else v)
                        for k, v in fp.items()},
        "frozen_by_construction": ["coverage", "grain", "n"],   # footprints never move in this model
        "ledger": ledger,
        "recs": recs,
    }
