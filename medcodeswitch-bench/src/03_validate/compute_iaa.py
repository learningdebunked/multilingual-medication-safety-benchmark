"""
compute_iaa.py — Simulate inter-annotator agreement on validation_sample_100.csv.

Since we use automated judge scoring (no human annotators in sandbox), we simulate
IAA by treating run_43 vs run_44 as two independent "annotators" for MODEL-001
on the 100-item validation sample.

Computes:
  - Cohen's kappa for binary (score_0_1)
  - Percent agreement
  - Krippendorff's alpha (ordinal, score_partial in {0, 0.5, 0.75, 1.0})

Output: results/iaa_report.json
"""

import os, json, csv, pathlib, math

os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"]      = "1"

ROOT           = pathlib.Path(__file__).resolve().parents[2]
DATA_VAL       = ROOT / "data" / "validation" / "validation_sample_100.csv"
OUTPUTS_JUDGED = ROOT / "outputs_judged"
RESULTS        = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def load_validation_ids() -> list[str]:
    ids = []
    with open(DATA_VAL) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ids.append(row["item_id"])
    return ids


def load_judged_for_model(model_id: str, seed: int, val_ids: set[str]) -> dict[str, dict]:
    """Return {item_id: judged_dict} for items in val_ids, from given model+seed."""
    records = {}
    # en_base only for IAA (ground-truth items without CS noise)
    judged_path = OUTPUTS_JUDGED / "en_base" / model_id / f"run_{seed}.jsonl"
    if not judged_path.exists():
        raise FileNotFoundError(judged_path)
    with open(judged_path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r["item_id"] in val_ids:
                records[r["item_id"]] = r
    return records


def cohen_kappa(labels_a: list[int], labels_b: list[int]) -> float:
    """Compute Cohen's kappa for binary labels."""
    n = len(labels_a)
    assert n == len(labels_b) and n > 0

    p_agree = sum(a == b for a, b in zip(labels_a, labels_b)) / n

    # Expected agreement
    p_a1 = sum(labels_a) / n
    p_b1 = sum(labels_b) / n
    p_e  = p_a1 * p_b1 + (1 - p_a1) * (1 - p_b1)

    if p_e == 1.0:
        return 1.0
    return (p_agree - p_e) / (1 - p_e)


def krippendorff_alpha_ordinal(data: list[list[float]]) -> float:
    """
    Krippendorff's alpha for ordinal data.
    data: list of [annotator1_score, annotator2_score] per item.
    Uses ordinal difference metric: d(v,w) = (sum(n_k, k=v..w-1))^2
    For a simplified 4-level ordinal {0, 0.5, 0.75, 1.0}
    we map to integers {0, 1, 2, 3} and use squared differences.
    """
    # Map partial scores to ordinal integers
    score_map = {0.0: 0, 0.5: 1, 0.75: 2, 1.0: 3}
    coded = []
    for pair in data:
        coded.append([score_map.get(pair[0], 0), score_map.get(pair[1], 0)])

    n_items = len(coded)
    n_ann   = 2  # two annotators

    # Observed disagreement D_o
    do_sum = 0.0
    for pair in coded:
        do_sum += (pair[0] - pair[1]) ** 2
    D_o = do_sum / n_items

    # Expected disagreement D_e (all values pooled)
    all_vals = [v for pair in coded for v in pair]
    n_total = len(all_vals)
    D_e = 0.0
    for i in range(n_total):
        for j in range(n_total):
            if i != j:
                D_e += (all_vals[i] - all_vals[j]) ** 2
    D_e /= (n_total * (n_total - 1))

    if D_e == 0:
        return 1.0
    return 1.0 - D_o / D_e


def main():
    val_ids  = load_validation_ids()
    val_set  = set(val_ids)

    # Use MODEL-001 (GPT-4o) as primary annotator; compare run_43 vs run_44
    ann1 = load_judged_for_model("MODEL-001", 43, val_set)
    ann2 = load_judged_for_model("MODEL-001", 44, val_set)

    # Intersection of available items
    common_ids = sorted(set(ann1) & set(ann2))
    n = len(common_ids)
    print(f"IAA computed on {n} overlapping items from validation sample.")

    labels_a = [int(ann1[i]["score_0_1"])    for i in common_ids]
    labels_b = [int(ann2[i]["score_0_1"])    for i in common_ids]
    partial_a = [ann1[i]["score_partial"]    for i in common_ids]
    partial_b = [ann2[i]["score_partial"]    for i in common_ids]

    kappa    = cohen_kappa(labels_a, labels_b)
    p_agree  = sum(a == b for a, b in zip(labels_a, labels_b)) / n if n else 0.0
    k_alpha  = krippendorff_alpha_ordinal(list(zip(partial_a, partial_b)))

    iaa_threshold = 0.75   # from external_values.yaml: iaa_kappa_threshold

    result = {
        "n_items"            : n,
        "model_used"         : "MODEL-001",
        "runs_compared"      : [43, 44],
        "annotation_basis"   : "run_as_annotator_simulation",
        "percent_agreement"  : round(p_agree,  4),
        "cohen_kappa"        : round(kappa,    4),
        "krippendorff_alpha" : round(k_alpha,  4),
        "kappa_threshold"    : iaa_threshold,
        "kappa_pass"         : kappa >= iaa_threshold,
        "simulation"         : True,
        "note": (
            "IAA simulated: two independent runs of the same model treated as annotators. "
            "Real human annotation would be required for camera-ready paper."
        ),
    }

    out_path = RESULTS / "iaa_report.json"
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2)

    print(f"  Cohen's kappa : {kappa:.4f}  (threshold {iaa_threshold}) → {'PASS' if result['kappa_pass'] else 'FAIL'}")
    print(f"  % agreement   : {p_agree:.4f}")
    print(f"  Krippendorff α: {k_alpha:.4f}")
    print(f"  wrote {out_path}")
    print("compute_iaa.py DONE")


if __name__ == "__main__":
    main()
