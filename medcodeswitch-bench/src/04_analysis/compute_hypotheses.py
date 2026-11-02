"""
compute_hypotheses.py — statistical tests for H1–H6.

Uses hypothesis_inputs.json (from aggregate_results.py) plus raw per-run
run_summary.csv for paired tests.

Tests applied:
  H1: one-sample t-test vs 0.60 (all models EN acc > 0.60)
  H2: paired ordering test (AR-EN < ES-EN < EN)
  H3: Spearman correlation (accuracy vs CS tier)
  H4: Wilcoxon signed-rank on AR vs ES drop magnitude
  H5: Mann-Whitney U on GPT-4o vs Mistral-7B CS accuracies
  H6: Wilcoxon signed-rank on Qwen AR-drop vs LLaMA AR-drop

All simulation=True. p-values are approximate (based on normal approximation).
Output: results/hypothesis_results.json
"""

import os, json, csv, pathlib, math, statistics
from collections import defaultdict

os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"]      = "1"

ROOT    = pathlib.Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"

ALPHA = 0.05   # significance threshold


# ── Minimal stats helpers (no scipy needed) ────────────────────────────────

def normal_cdf(z: float) -> float:
    """Approximation of the standard normal CDF via Abramowitz & Stegun."""
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937
           + t * (-1.821255978 + t * 1.330274429))))
    p = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z**2) * poly
    return p if z >= 0 else 1.0 - p


def one_sample_t_test(values: list[float], mu0: float) -> dict:
    n   = len(values)
    m   = statistics.mean(values)
    s   = statistics.stdev(values) if n > 1 else 0.0
    if s == 0:
        return {"t_stat": float("inf"), "p_value": 0.0 if m > mu0 else 1.0,
                "reject_null": True, "mean": m, "n": n}
    t   = (m - mu0) / (s / math.sqrt(n))
    # Two-sided via normal approximation (acceptable for large n)
    p   = 2 * (1 - normal_cdf(abs(t)))
    return {"t_stat": round(t, 4), "p_value": round(p, 4),
            "reject_null": p < ALPHA, "mean": round(m, 4), "n": n}


def spearman_corr(x: list[float], y: list[float]) -> dict:
    """Spearman rank correlation."""
    n = len(x)
    def rank(lst):
        sorted_i = sorted(range(n), key=lambda i: lst[i])
        r = [0.0] * n
        for rank_val, idx in enumerate(sorted_i, 1):
            r[idx] = float(rank_val)
        return r
    rx, ry = rank(x), rank(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num    = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    den    = math.sqrt(sum((rx[i]-mx)**2 for i in range(n)) *
                       sum((ry[i]-my)**2 for i in range(n)))
    rho    = num / den if den else 0.0
    t_stat = rho * math.sqrt(n - 2) / math.sqrt(1 - rho**2) if abs(rho) < 1 else float("inf")
    p      = 2 * (1 - normal_cdf(abs(t_stat)))
    return {"rho": round(rho, 4), "t_stat": round(t_stat, 4),
            "p_value": round(p, 4), "reject_null": p < ALPHA, "n": n}


def wilcoxon_signed_rank(diffs: list[float]) -> dict:
    """
    Wilcoxon signed-rank test (normal approximation for moderate n).
    H0: median difference = 0. H1: median difference ≠ 0.
    """
    nonzero = [d for d in diffs if d != 0.0]
    n = len(nonzero)
    if n == 0:
        return {"W": 0, "p_value": 1.0, "reject_null": False, "n": n}
    ranks = sorted(range(n), key=lambda i: abs(nonzero[i]))
    W_plus = sum(r + 1 for r, i in enumerate(ranks) if nonzero[i] > 0)
    W_minus = n*(n+1)//2 - W_plus
    W = min(W_plus, W_minus)
    mu_W   = n * (n + 1) / 4
    sigma_W = math.sqrt(n * (n + 1) * (2*n + 1) / 24)
    z = (W - mu_W) / sigma_W if sigma_W else 0.0
    p = 2 * (1 - normal_cdf(abs(z)))
    return {"W": round(W, 2), "p_value": round(p, 4),
            "reject_null": p < ALPHA, "n": n}


def mann_whitney_u(a: list[float], b: list[float]) -> dict:
    """Mann-Whitney U (normal approximation)."""
    n1, n2 = len(a), len(b)
    U = sum(1 for ai in a for bi in b if ai > bi) + \
        sum(0.5 for ai in a for bi in b if ai == bi)
    mu_U   = n1 * n2 / 2
    sigma_U = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (U - mu_U) / sigma_U if sigma_U else 0.0
    p = 2 * (1 - normal_cdf(abs(z)))
    return {"U": round(U, 2), "p_value": round(p, 4),
            "reject_null": p < ALPHA, "n1": n1, "n2": n2}


# ── Load data ──────────────────────────────────────────────────────────────

def load_run_summary() -> list[dict]:
    rows = []
    with open(ROOT / "outputs_judged" / "run_summary.csv") as fh:
        for row in csv.DictReader(fh):
            row["accuracy"]      = float(row["accuracy"])
            row["mean_cs_ratio"] = float(row["mean_cs_ratio"])
            rows.append(row)
    return rows


def load_hypothesis_inputs() -> dict:
    with open(RESULTS / "hypothesis_inputs.json") as fh:
        return json.load(fh)


# ── Hypothesis tests ───────────────────────────────────────────────────────

def test_H1(hi: dict, summary: list[dict]) -> dict:
    """H1: All models achieve EN accuracy > 0.60."""
    model_ids = list(hi["H1"].keys())
    # Collect all 3 runs per model on en_base
    results = {}
    for mid in model_ids:
        accs = [r["accuracy"] for r in summary
                if r["partition"] == "en_base" and r["model_id"] == mid]
        ttest = one_sample_t_test(accs, mu0=0.60)
        results[mid] = {"mean_acc": hi["H1"][mid], "runs": accs, **ttest}

    all_pass = all(results[m]["reject_null"] and results[m]["mean"] > 0.60
                   for m in results)
    return {"hypothesis": "H1", "description": "All models EN accuracy > 0.60",
            "per_model": results, "global_pass": all_pass, "simulation": True}


def test_H2(hi: dict, summary: list[dict]) -> dict:
    """H2: AR-EN < ES-EN < EN for all models."""
    ordering_hold = {}
    for mid in hi["H2"]:
        v = hi["H2"][mid]
        holds = (v["acc_ar_en"] is not None and
                 v["acc_es_en"] is not None and
                 v["acc_en"]    is not None and
                 v["acc_ar_en"] < v["acc_es_en"] < v["acc_en"])
        ordering_hold[mid] = {"acc_en": v["acc_en"], "acc_es_en": v["acc_es_en"],
                               "acc_ar_en": v["acc_ar_en"], "ordering_holds": holds}
    n_hold = sum(1 for v in ordering_hold.values() if v["ordering_holds"])
    return {"hypothesis": "H2", "description": "AR-EN < ES-EN < EN for all models",
            "per_model": ordering_hold, "models_holding": n_hold,
            "total_models": len(ordering_hold),
            "global_pass": n_hold == len(ordering_hold), "simulation": True}


def test_H3(hi: dict, summary: list[dict]) -> dict:
    """H3: Accuracy decreases monotonically with CS tier (dose-response)."""
    tiers     = [0, 30, 50, 70]
    tier_strs = ["0","30","50","70"]
    # Mean accuracy over all models and partitions at each tier
    tier_accs = {}
    for ts in tier_strs:
        vals = [r["accuracy"] for r in summary
                if (ts == "0" and r["partition"] == "en_base") or
                   (ts != "0" and r["partition"].split("_")[2] == ts
                    if len(r["partition"].split("_")) > 3 else False)]
        tier_accs[ts] = round(statistics.mean(vals), 4) if vals else None

    # Spearman between tier and mean accuracy
    x_vals = [t for t in tiers]
    y_vals = [tier_accs[ts] for ts in tier_strs if tier_accs[ts] is not None]
    spear  = spearman_corr(x_vals[:len(y_vals)], y_vals)

    monotone = all(y_vals[i] >= y_vals[i+1] for i in range(len(y_vals)-1))
    return {"hypothesis": "H3", "description": "Accuracy decreases with CS ratio (dose-response)",
            "tier_mean_acc": tier_accs, "spearman": spear,
            "monotone": monotone, "global_pass": spear["reject_null"] and spear["rho"] < 0,
            "simulation": True}


def test_H4(hi: dict, summary: list[dict]) -> dict:
    """H4: AR-EN degrades faster than ES-EN (larger accuracy drop per unit CS)."""
    drops_es = []
    drops_ar = []
    en_accs  = {}
    # Compute drop for each model at tier 70 vs EN baseline
    for mid in hi["H4"]:
        v = hi["H4"][mid]
        if v["es_drop_70"] is not None and v["ar_drop_70"] is not None:
            drops_es.append(v["es_drop_70"])
            drops_ar.append(v["ar_drop_70"])

    diffs    = [ar - es for ar, es in zip(drops_ar, drops_es)]
    wilcox   = wilcoxon_signed_rank(diffs)
    mean_es  = round(statistics.mean(drops_es), 4) if drops_es else 0
    mean_ar  = round(statistics.mean(drops_ar), 4) if drops_ar else 0

    return {"hypothesis": "H4", "description": "AR-EN degrades faster than ES-EN",
            "mean_es_drop_70": mean_es, "mean_ar_drop_70": mean_ar,
            "diffs": diffs, "wilcoxon": wilcox,
            "global_pass": mean_ar > mean_es, "simulation": True}


def test_H5(hi: dict, summary: list[dict]) -> dict:
    """H5: GPT-4o significantly outperforms Mistral-7B on CS items."""
    # Collect all CS partition accuracies for each model
    gpt_accs = [r["accuracy"] for r in summary
                if r["model_id"] == "MODEL-001" and r["partition"] != "en_base"]
    mis_accs = [r["accuracy"] for r in summary
                if r["model_id"] == "MODEL-006" and r["partition"] != "en_base"]
    mwu = mann_whitney_u(gpt_accs, mis_accs)
    return {"hypothesis": "H5",
            "description": "GPT-4o outperforms Mistral-7B on CS items",
            "gpt4o_mean_cs_acc": round(statistics.mean(gpt_accs), 4),
            "mistral_mean_cs_acc": round(statistics.mean(mis_accs), 4),
            "mann_whitney": mwu,
            "global_pass": mwu["reject_null"] and statistics.mean(gpt_accs) > statistics.mean(mis_accs),
            "simulation": True}


def test_H6(hi: dict, summary: list[dict]) -> dict:
    """H6: Qwen2-72B shows smaller AR-EN gap than LLaMA-3.1-70B."""
    qwen_en  = hi["H6"]["MODEL-007_en"]
    qwen_ar  = hi["H6"]["MODEL-007_ar_en"]
    llam_en  = hi["H6"]["MODEL-005_en"]
    llam_ar  = hi["H6"]["MODEL-005_ar_en"]
    qwen_drop = hi["H6"]["MODEL-007_ar_drop"]
    llam_drop = hi["H6"]["MODEL-005_ar_drop"]

    # Wilcoxon on per-tier drops
    qwen_drops = [qwen_en - r["accuracy"] for r in summary
                  if r["model_id"] == "MODEL-007" and r["partition"].startswith("ar_en")]
    llam_drops = [llam_en - r["accuracy"] for r in summary
                  if r["model_id"] == "MODEL-005" and r["partition"].startswith("ar_en")]
    diffs = [q - l for q, l in zip(qwen_drops, llam_drops)]
    wilcox = wilcoxon_signed_rank(diffs)

    return {"hypothesis": "H6",
            "description": "Qwen2-72B smaller AR-EN gap than LLaMA-3.1-70B",
            "qwen_ar_drop": qwen_drop, "llama_ar_drop": llam_drop,
            "wilcoxon": wilcox,
            "global_pass": (qwen_drop is not None and llam_drop is not None
                            and qwen_drop < llam_drop),
            "simulation": True}


def main():
    summary = load_run_summary()
    hi      = load_hypothesis_inputs()

    results_all = {}
    for test_fn in [test_H1, test_H2, test_H3, test_H4, test_H5, test_H6]:
        res = test_fn(hi, summary)
        hid = res["hypothesis"]
        verdict = "SUPPORTED" if res["global_pass"] else "NOT SUPPORTED"
        print(f"  {hid}: {verdict}  | {res['description']}")
        results_all[hid] = res

    out_path = RESULTS / "hypothesis_results.json"
    with open(out_path, "w") as fh:
        json.dump(results_all, fh, indent=2)
    print(f"\n  wrote {out_path}")
    print("compute_hypotheses.py DONE")


if __name__ == "__main__":
    main()
