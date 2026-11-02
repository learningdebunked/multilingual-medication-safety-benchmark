"""
run_evaluation.py — iterate all 13 partitions × 7 models × 3 runs.

Outputs: outputs/{partition_name}/{model_id}/run_{seed}.jsonl
Each line = one LLMResponse dict (simulation=True).

Seeds from external_values.yaml: base_eval=42 (runs: 43, 44, 45).
"""

import os, sys, json, pathlib, time

os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"]      = "1"

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT    = pathlib.Path(__file__).resolve().parents[2]
DATA    = ROOT / "data"
OUTPUTS = ROOT / "outputs"
SRC_EVA = pathlib.Path(__file__).parent
sys.path.insert(0, str(SRC_EVA))

from model_clients import SimulationClient, MODELS

# ── Partition registry ─────────────────────────────────────────────────────
PARTITIONS = [
    ("en_base",      DATA / "en_base"        / "en_base_400.jsonl"),
    ("es_en_30_intra", DATA / "es_en" / "30_intra" / "cs_variants.jsonl"),
    ("es_en_30_inter", DATA / "es_en" / "30_inter" / "cs_variants.jsonl"),
    ("es_en_50_intra", DATA / "es_en" / "50_intra" / "cs_variants.jsonl"),
    ("es_en_50_inter", DATA / "es_en" / "50_inter" / "cs_variants.jsonl"),
    ("es_en_70_intra", DATA / "es_en" / "70_intra" / "cs_variants.jsonl"),
    ("es_en_70_inter", DATA / "es_en" / "70_inter" / "cs_variants.jsonl"),
    ("ar_en_30_intra", DATA / "ar_en" / "30_intra" / "cs_variants.jsonl"),
    ("ar_en_30_inter", DATA / "ar_en" / "30_inter" / "cs_variants.jsonl"),
    ("ar_en_50_intra", DATA / "ar_en" / "50_intra" / "cs_variants.jsonl"),
    ("ar_en_50_inter", DATA / "ar_en" / "50_inter" / "cs_variants.jsonl"),
    ("ar_en_70_intra", DATA / "ar_en" / "70_intra" / "cs_variants.jsonl"),
    ("ar_en_70_inter", DATA / "ar_en" / "70_inter" / "cs_variants.jsonl"),
]

RUN_SEEDS = [43, 44, 45]   # 3 runs per model/partition


def load_partition(path: pathlib.Path) -> list[dict]:
    items = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def run_partition(partition_name: str, items: list[dict], model_id: str, seed: int) -> list[dict]:
    client = SimulationClient(model_id, seed=seed)
    responses = []
    for item in items:
        resp = client.generate(item, run_id=seed)
        # Attach ground-truth fields needed by judge
        resp["med_true"]      = item["med_true"]
        resp["med_false"]     = item["med_false"]
        resp["safety_detail"] = item.get("safety_detail", "")
        resp["category"]      = item.get("category", "")
        resp["language_pair"] = item.get("language_pair", "en")
        resp["cs_ratio"]      = item.get("cs_ratio", 0.0)
        resp["cs_type"]       = item.get("cs_type", "none")
        resp["partition"]     = partition_name
        responses.append(resp)
    return responses


def main():
    total_batches = len(PARTITIONS) * len(MODELS) * len(RUN_SEEDS)
    done = 0
    t0 = time.time()

    for part_name, part_path in PARTITIONS:
        if not part_path.exists():
            print(f"  SKIP (missing): {part_path}", flush=True)
            continue

        items = load_partition(part_path)

        for model_id in MODELS:
            model_name = MODELS[model_id].model_name
            for seed in RUN_SEEDS:
                out_dir = OUTPUTS / part_name / model_id
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"run_{seed}.jsonl"

                if out_path.exists():
                    done += 1
                    continue  # skip re-runs (idempotent)

                responses = run_partition(part_name, items, model_id, seed)

                with open(out_path, "w") as fh:
                    for r in responses:
                        fh.write(json.dumps(r) + "\n")

                done += 1
                elapsed = time.time() - t0
                print(
                    f"  [{done:3d}/{total_batches}] {part_name:20s} {model_id} run_{seed}"
                    f"  → {len(responses)} items  ({elapsed:.1f}s)",
                    flush=True,
                )

    print(f"\nrun_evaluation.py DONE — {done}/{total_batches} batches. Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
