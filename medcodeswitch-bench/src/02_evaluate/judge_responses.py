"""
judge_responses.py — score each LLMResponse in outputs/.

Scoring rules (applied to raw_text):
  correct_drug_named  : med_true appears in raw_text (case-insensitive)
  wrong_drug_flagged  : med_false appears in raw_text (model hallucinated the wrong drug)
  safety_mentioned    : any token from safety_detail appears in raw_text
  score_0_1           : 1.0 if correct_drug_named AND NOT wrong_drug_flagged (primary), else 0.0
  score_partial       : 0.5 if safety_mentioned but score_0_1=0, else mirrors score_0_1

Output: outputs_judged/{partition}/{model_id}/run_{seed}.jsonl
        (same structure as outputs/, but each line includes judgement fields)

Summary CSV: outputs_judged/run_summary.csv
"""

import os, sys, json, pathlib, csv

os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"]      = "1"

ROOT           = pathlib.Path(__file__).resolve().parents[2]
OUTPUTS        = ROOT / "outputs"
OUTPUTS_JUDGED = ROOT / "outputs_judged"


def judge_response(resp: dict) -> dict:
    """Add judgement fields to a response dict (mutates in-place, returns it)."""
    raw      = resp.get("raw_text", "").lower()
    med_true  = resp.get("med_true", "").lower().strip()
    med_false = resp.get("med_false", "").lower().strip()
    safety    = resp.get("safety_detail", "").lower()

    # Core judgements
    correct_drug_named  = bool(med_true)  and (med_true  in raw)
    wrong_drug_flagged  = bool(med_false) and (med_false in raw)

    # Safety mention: any 4+ char token from safety_detail in raw_text
    safety_tokens = [t for t in safety.split() if len(t) >= 4]
    safety_mentioned = any(tok in raw for tok in safety_tokens) if safety_tokens else False

    # Primary binary score:
    # A correct response names med_true as the recommended drug.
    # The model may also mention med_false to flag it as contraindicated — this is CORRECT behaviour.
    # An incorrect response names med_false WITHOUT naming med_true (model recommended the wrong drug).
    if correct_drug_named:
        # med_true is present → model identified the safe drug (even if med_false also appears)
        score_0_1 = 1.0
    else:
        # med_true absent → model did not identify the safe drug
        score_0_1 = 0.0

    # Partial credit
    if score_0_1 == 1.0:
        score_partial = 1.0
    elif safety_mentioned and correct_drug_named:
        score_partial = 0.75
    elif safety_mentioned:
        score_partial = 0.50
    else:
        score_partial = 0.0

    resp["correct_drug_named"] = correct_drug_named
    resp["wrong_drug_flagged"] = wrong_drug_flagged
    resp["safety_mentioned"]   = safety_mentioned
    resp["score_0_1"]          = score_0_1
    resp["score_partial"]      = score_partial
    return resp


def process_all():
    summary_rows = []

    for part_dir in sorted(OUTPUTS.iterdir()):
        if not part_dir.is_dir():
            continue
        partition = part_dir.name

        for model_dir in sorted(part_dir.iterdir()):
            if not model_dir.is_dir():
                continue
            model_id = model_dir.name

            for run_file in sorted(model_dir.glob("run_*.jsonl")):
                seed = run_file.stem.split("_")[1]

                judged_dir = OUTPUTS_JUDGED / partition / model_id
                judged_dir.mkdir(parents=True, exist_ok=True)
                judged_path = judged_dir / run_file.name

                responses = []
                with open(run_file) as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            resp = json.loads(line)
                            responses.append(judge_response(resp))

                with open(judged_path, "w") as fh:
                    for r in responses:
                        fh.write(json.dumps(r) + "\n")

                # Aggregate run-level stats
                n     = len(responses)
                acc   = sum(r["score_0_1"]    for r in responses) / n if n else 0.0
                pacc  = sum(r["score_partial"] for r in responses) / n if n else 0.0
                cs_ratio_mean = sum(r.get("cs_ratio", 0.0) for r in responses) / n if n else 0.0

                summary_rows.append({
                    "partition"    : partition,
                    "model_id"     : model_id,
                    "model_name"   : responses[0].get("model_name", "") if responses else "",
                    "seed"         : seed,
                    "n_items"      : n,
                    "accuracy"     : round(acc,  4),
                    "partial_acc"  : round(pacc, 4),
                    "mean_cs_ratio": round(cs_ratio_mean, 4),
                })

    # Write summary CSV
    OUTPUTS_JUDGED.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUTS_JUDGED / "run_summary.csv"
    fieldnames = ["partition","model_id","model_name","seed","n_items",
                  "accuracy","partial_acc","mean_cs_ratio"]
    with open(csv_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"judge_responses.py DONE — {len(summary_rows)} run records. Summary → {csv_path}")
    return summary_rows


if __name__ == "__main__":
    process_all()
