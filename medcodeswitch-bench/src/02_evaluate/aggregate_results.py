"""
aggregate_results.py — aggregate 3 runs per model × partition into final tables.

Reads: outputs_judged/run_summary.csv
Writes:
  results/table_accuracy_by_partition.csv   — mean ± std accuracy
  results/table_by_language_pair.csv        — aggregated by language family
  results/table_cs_dose_response.csv        — accuracy vs CS ratio tier
  results/hypothesis_inputs.json            — raw numbers for compute_hypotheses.py
"""

import os, json, pathlib, csv, statistics
from collections import defaultdict

os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"]      = "1"

ROOT           = pathlib.Path(__file__).resolve().parents[2]
OUTPUTS_JUDGED = ROOT / "outputs_judged"
RESULTS        = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def load_summary() -> list[dict]:
    csv_path = OUTPUTS_JUDGED / "run_summary.csv"
    rows = []
    with open(csv_path) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row["accuracy"]      = float(row["accuracy"])
            row["partial_acc"]   = float(row["partial_acc"])
            row["n_items"]       = int(row["n_items"])
            row["mean_cs_ratio"] = float(row["mean_cs_ratio"])
            rows.append(row)
    return rows


def partition_to_attrs(partition: str) -> dict:
    """Parse partition name → {language_pair, cs_tier, cs_type}."""
    if partition == "en_base":
        return {"language_pair": "en", "cs_tier": "0", "cs_type": "none"}
    parts = partition.split("_")
    # e.g. es_en_30_intra → language_pair=es_en, cs_tier=30, cs_type=intra
    lang  = parts[0] + "_" + parts[1]   # es_en / ar_en
    tier  = parts[2]                     # 30 / 50 / 70
    ctype = parts[3]                     # intra / inter
    return {"language_pair": lang, "cs_tier": tier, "cs_type": ctype}


def aggregate_runs(rows: list[dict]) -> dict:
    """
    Group rows by (partition, model_id), average accuracy over 3 seeds.
    Returns {(partition, model_id): {mean_acc, std_acc, mean_partial, n_runs, ...}}
    """
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["partition"], r["model_id"])].append(r)

    agg = {}
    for key, rlist in grouped.items():
        accs = [r["accuracy"] for r in rlist]
        pacc = [r["partial_acc"] for r in rlist]
        agg[key] = {
            "partition"   : rlist[0]["partition"],
            "model_id"    : rlist[0]["model_id"],
            "model_name"  : rlist[0]["model_name"],
            "n_runs"      : len(accs),
            "mean_acc"    : round(statistics.mean(accs), 4),
            "std_acc"     : round(statistics.stdev(accs) if len(accs) > 1 else 0.0, 4),
            "mean_partial": round(statistics.mean(pacc), 4),
            "mean_cs_ratio": round(statistics.mean(r["mean_cs_ratio"] for r in rlist), 4),
            **partition_to_attrs(rlist[0]["partition"]),
        }
    return agg


def write_table_accuracy_by_partition(agg: dict, model_order: list[str]):
    """Wide table: rows=partitions, cols=models."""
    partitions = sorted({v["partition"] for v in agg.values()})
    fieldnames = ["partition","language_pair","cs_tier","cs_type","mean_cs_ratio"] + model_order
    rows_out = []
    for part in partitions:
        attrs = partition_to_attrs(part)
        row = {
            "partition"    : part,
            "language_pair": attrs["language_pair"],
            "cs_tier"      : attrs["cs_tier"],
            "cs_type"      : attrs["cs_type"],
            "mean_cs_ratio": "",
        }
        for mid in model_order:
            key = (part, mid)
            if key in agg:
                v = agg[key]
                row["mean_cs_ratio"] = v["mean_cs_ratio"]
                row[mid] = f"{v['mean_acc']:.4f}±{v['std_acc']:.4f}"
            else:
                row[mid] = "NA"
        rows_out.append(row)

    out = RESULTS / "table_accuracy_by_partition.csv"
    with open(out, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"  wrote {out}")


def write_table_by_language_pair(agg: dict, model_order: list[str]):
    """Group by language_pair (en / es_en / ar_en), average across tiers."""
    from collections import defaultdict as dd
    grouped = dd(lambda: dd(list))
    for v in agg.values():
        grouped[v["language_pair"]][v["model_id"]].append(v["mean_acc"])

    rows_out = []
    for lang in ["en", "es_en", "ar_en"]:
        if lang not in grouped:
            continue
        row = {"language_pair": lang}
        for mid in model_order:
            accs = grouped[lang].get(mid, [])
            row[mid] = round(statistics.mean(accs), 4) if accs else "NA"
        rows_out.append(row)

    out = RESULTS / "table_by_language_pair.csv"
    fieldnames = ["language_pair"] + model_order
    with open(out, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"  wrote {out}")


def write_table_cs_dose_response(agg: dict, model_order: list[str]):
    """Accuracy vs CS tier (0/30/50/70), averaged across intra+inter and ES+AR."""
    from collections import defaultdict as dd
    grouped = dd(lambda: dd(list))
    for v in agg.values():
        grouped[v["cs_tier"]][v["model_id"]].append(v["mean_acc"])

    rows_out = []
    for tier in ["0", "30", "50", "70"]:
        row = {"cs_tier": tier}
        for mid in model_order:
            accs = grouped[tier].get(mid, [])
            row[mid] = round(statistics.mean(accs), 4) if accs else "NA"
        rows_out.append(row)

    out = RESULTS / "table_cs_dose_response.csv"
    fieldnames = ["cs_tier"] + model_order
    with open(out, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"  wrote {out}")


def build_hypothesis_inputs(agg: dict, model_order: list[str]) -> dict:
    """
    Pre-compute the raw numbers needed for compute_hypotheses.py.
    Returns a dict structured by hypothesis.
    """
    hi = {}

    def mean_acc(language_pair=None, cs_tier=None, cs_type=None, model_id=None):
        vals = [
            v["mean_acc"] for v in agg.values()
            if (language_pair is None or v["language_pair"] == language_pair)
            and (cs_tier      is None or v["cs_tier"]       == cs_tier)
            and (cs_type      is None or v["cs_type"]       == cs_type)
            and (model_id     is None or v["model_id"]      == model_id)
        ]
        return round(statistics.mean(vals), 4) if vals else None

    def run_accs(partition, model_id, rows_raw):
        """Return list of per-run accuracies for a (partition, model_id) pair."""
        return [r["accuracy"] for r in rows_raw
                if r["partition"] == partition and r["model_id"] == model_id]

    # H1: EN accuracy > 0.60 for all models
    hi["H1"] = {
        mid: mean_acc(language_pair="en", model_id=mid)
        for mid in model_order
    }

    # H2: AR-EN < ES-EN < EN (per model)
    hi["H2"] = {
        mid: {
            "acc_en"   : mean_acc(language_pair="en",    model_id=mid),
            "acc_es_en": mean_acc(language_pair="es_en", model_id=mid),
            "acc_ar_en": mean_acc(language_pair="ar_en", model_id=mid),
        }
        for mid in model_order
    }

    # H3: dose-response — accuracy decreases as CS tier increases
    hi["H3"] = {
        tier: mean_acc(cs_tier=tier)
        for tier in ["0", "30", "50", "70"]
    }

    # H4: AR-EN degrades faster than ES-EN (compare slope)
    hi["H4"] = {}
    for mid in model_order:
        es_accs = [mean_acc(language_pair="es_en", cs_tier=t, model_id=mid)
                   for t in ["30", "50", "70"]]
        ar_accs = [mean_acc(language_pair="ar_en", cs_tier=t, model_id=mid)
                   for t in ["30", "50", "70"]]
        en_acc  = mean_acc(language_pair="en", model_id=mid)
        hi["H4"][mid] = {
            "en_acc"    : en_acc,
            "es_accs"   : es_accs,
            "ar_accs"   : ar_accs,
            # drop = (en_acc - mean_cs_acc) for tier 70
            "es_drop_70": round(en_acc - es_accs[2], 4) if en_acc and es_accs[2] else None,
            "ar_drop_70": round(en_acc - ar_accs[2], 4) if en_acc and ar_accs[2] else None,
        }

    # H5: GPT-4o vs Mistral-7B on CS items
    hi["H5"] = {
        "MODEL-001": mean_acc(language_pair="es_en", model_id="MODEL-001"),
        "MODEL-006": mean_acc(language_pair="es_en", model_id="MODEL-006"),
        "MODEL-001_ar": mean_acc(language_pair="ar_en", model_id="MODEL-001"),
        "MODEL-006_ar": mean_acc(language_pair="ar_en", model_id="MODEL-006"),
    }

    # H6: Qwen2-72B shows smaller AR-EN gap (trained on Arabic)
    hi["H6"] = {
        "MODEL-007_en"   : mean_acc(language_pair="en",    model_id="MODEL-007"),
        "MODEL-007_ar_en": mean_acc(language_pair="ar_en", model_id="MODEL-007"),
        "MODEL-005_en"   : mean_acc(language_pair="en",    model_id="MODEL-005"),
        "MODEL-005_ar_en": mean_acc(language_pair="ar_en", model_id="MODEL-005"),
        "MODEL-007_ar_drop": None,  # filled below
        "MODEL-005_ar_drop": None,
    }
    q007 = hi["H6"]["MODEL-007_en"]
    q007a = hi["H6"]["MODEL-007_ar_en"]
    l005 = hi["H6"]["MODEL-005_en"]
    l005a = hi["H6"]["MODEL-005_ar_en"]
    if q007 and q007a:
        hi["H6"]["MODEL-007_ar_drop"] = round(q007 - q007a, 4)
    if l005 and l005a:
        hi["H6"]["MODEL-005_ar_drop"] = round(l005 - l005a, 4)

    return hi


def main():
    rows = load_summary()
    agg  = aggregate_runs(rows)

    # Canonical model order (by base_acc desc)
    model_order = [
        "MODEL-001","MODEL-002","MODEL-003","MODEL-004",
        "MODEL-007","MODEL-005","MODEL-006"
    ]

    print("Aggregating results...")
    write_table_accuracy_by_partition(agg, model_order)
    write_table_by_language_pair(agg, model_order)
    write_table_cs_dose_response(agg, model_order)

    hi = build_hypothesis_inputs(agg, model_order)
    hyp_path = RESULTS / "hypothesis_inputs.json"
    with open(hyp_path, "w") as fh:
        json.dump(hi, fh, indent=2)
    print(f"  wrote {hyp_path}")

    print("\naggregate_results.py DONE")


if __name__ == "__main__":
    main()
