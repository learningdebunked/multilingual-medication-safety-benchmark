"""
filter_rxsafebench.py — Sample 200 contraindication + 200 drug-interaction
scenarios from RxSafeBench to form the 400-item English base set.

Selection criteria (Stage 4 spec §3.1):
  - Seed = 42
  - Quality score > 3.5 (if available) — prefer higher quality items
  - Drug-name preservation: med_true and med_false must be non-empty
  - Indication must be non-empty
  - Dialogue must be > 200 characters
  - Stratified across indications (no single indication > 10 items)
"""

import os, sys, json, random, pathlib

os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"]      = "1"

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parents[2]  # medcodeswitch-bench/
RAW  = ROOT / "data" / "raw" / "rxsafebench"
OUT  = ROOT / "data" / "en_base"
SRC  = ROOT / "src" / "01_build_dataset"

sys.path.insert(0, str(SRC))
from schema import BenchmarkItem, Category, LanguagePair, CSType

SEED              = 42
N_TARGET          = 200          # per category
MAX_PER_INDICATION = 10
MIN_DIALOGUE_LEN  = 200
MIN_QUALITY_SCORE = 3.5

random.seed(SEED)


def load_flat(path: pathlib.Path, category_key: str) -> list[dict]:
    """Flatten nested RxSafeBench structure to a list of scenario dicts."""
    with open(path) as f:
        data = json.load(f)
    flat = []
    for entry in data:
        indication = entry.get("indication", "").strip()
        for scenario in entry.get(category_key, []):
            scenario["_indication"] = indication
            flat.append(scenario)
    return flat


def quality_filter(scenarios: list[dict]) -> list[dict]:
    """Remove items that fail basic quality checks."""
    kept = []
    for s in scenarios:
        if not s.get("med_true", "").strip():
            continue
        if not s.get("med_false", "").strip():
            continue
        if not s.get("_indication", "").strip():
            continue
        dialogue = s.get("dialogue", "")
        if len(dialogue) < MIN_DIALOGUE_LEN:
            continue
        score = s.get("score", None)
        if score is not None:
            try:
                if float(score) < MIN_QUALITY_SCORE:
                    continue
            except (ValueError, TypeError):
                pass
        kept.append(s)
    return kept


def stratified_sample(scenarios: list[dict], n: int, rng: random.Random) -> list[dict]:
    """
    Sample n items with stratification by indication:
    no single indication may contribute more than MAX_PER_INDICATION items.
    Shuffle first so that within-indication selection is random.
    """
    shuffled = scenarios.copy()
    rng.shuffle(shuffled)
    indication_counts: dict[str, int] = {}
    selected = []
    for s in shuffled:
        ind = s["_indication"]
        if indication_counts.get(ind, 0) >= MAX_PER_INDICATION:
            continue
        selected.append(s)
        indication_counts[ind] = indication_counts.get(ind, 0) + 1
        if len(selected) >= n:
            break
    return selected


def to_benchmark_item(s: dict, category: Category, idx: int) -> BenchmarkItem:
    prefix = "CONTRA" if category == Category.CONTRAINDICATION else "INTER"
    item_id = f"{prefix}-{idx:03d}"

    # Safety detail: contradiction uses 'notice'; interaction uses 'interacton' (sic)
    safety_detail = (
        s.get("notice", "")
        or str(s.get("interacton", {}).get("name", "")) if isinstance(s.get("interacton"), dict)
        else str(s.get("interacton", ""))
    ).strip()

    # Interaction key may be 'med_not_related'
    distractor = s.get("med_not_related", "").strip()

    score = None
    try:
        score = float(s.get("score", None))
    except (TypeError, ValueError):
        pass

    struct_score = None
    try:
        struct_score = float(s.get("structure_score", None))
    except (TypeError, ValueError):
        pass

    return BenchmarkItem(
        item_id        = item_id,
        category       = category,
        indication     = s["_indication"],
        med_true       = s["med_true"].strip(),
        med_false      = s["med_false"].strip(),
        med_distractor = distractor,
        safety_detail  = safety_detail or "see-dialogue",
        dialogue       = s["dialogue"].strip(),
        language_pair  = LanguagePair.EN,
        cs_type        = CSType.NONE,
        cs_ratio       = 0.0,
        source         = "rxsafebench",
        synthetic      = False,
        quality_score  = score,
        structure_score= struct_score,
        seed           = SEED,
    )


def main():
    rng = random.Random(SEED)

    # ── Load and flatten ──────────────────────────────────────────────────
    print("Loading RxSafeBench_Contradiction.json ...")
    contra_raw = load_flat(RAW / "RxSafeBench_Contradiction.json", "Contradiction")
    print(f"  Raw contradiction scenarios: {len(contra_raw)}")

    print("Loading RxSafeBench_Interaction.json ...")
    inter_raw = load_flat(RAW / "RxSafeBench_Interaction.json", "interaction")
    print(f"  Raw interaction scenarios:   {len(inter_raw)}")

    # ── Quality filter ────────────────────────────────────────────────────
    contra_filt = quality_filter(contra_raw)
    inter_filt  = quality_filter(inter_raw)
    print(f"\nAfter quality filter → contraindication: {len(contra_filt)}, interaction: {len(inter_filt)}")

    # ── Stratified sampling ───────────────────────────────────────────────
    contra_sel = stratified_sample(contra_filt, N_TARGET, rng)
    inter_sel  = stratified_sample(inter_filt,  N_TARGET, rng)
    print(f"Sampled → contraindication: {len(contra_sel)}, interaction: {len(inter_sel)}")

    if len(contra_sel) < N_TARGET or len(inter_sel) < N_TARGET:
        print(f"WARNING: could not reach {N_TARGET} per category — lowering caps or relaxing filters may help")

    # ── Convert to BenchmarkItem ──────────────────────────────────────────
    items: list[BenchmarkItem] = []
    for i, s in enumerate(contra_sel, start=1):
        items.append(to_benchmark_item(s, Category.CONTRAINDICATION, i))
    for i, s in enumerate(inter_sel, start=1):
        items.append(to_benchmark_item(s, Category.DRUG_INTERACTION, i))

    print(f"\nTotal benchmark items: {len(items)}")

    # ── Validation checks ─────────────────────────────────────────────────
    ids = [it.item_id for it in items]
    assert len(set(ids)) == len(ids), "Duplicate item_ids detected!"

    # Drug-name preservation check
    preservation_fails = 0
    for it in items:
        if not it.med_true or not it.med_false:
            preservation_fails += 1
    print(f"Drug-name preservation failures: {preservation_fails}")
    threshold = 0.95
    preservation_rate = 1.0 - preservation_fails / len(items)
    print(f"Drug-name preservation rate: {preservation_rate:.3f} (threshold: {threshold})")
    assert preservation_rate >= threshold, f"Preservation rate {preservation_rate:.3f} < {threshold}"

    # Indication diversity
    from collections import Counter
    ind_counts = Counter(it.indication for it in items)
    max_ind = max(ind_counts.values())
    print(f"Max items per indication: {max_ind} (cap: {MAX_PER_INDICATION})")
    assert max_ind <= MAX_PER_INDICATION, "Stratification cap violated"

    # ── Save ──────────────────────────────────────────────────────────────
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "en_base_400.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(it.model_dump_json() + "\n")
    print(f"\nSaved: {out_path}  ({len(items)} items)")

    # Summary stats
    cat_counts = Counter(it.category for it in items)
    print("\nCategory breakdown:")
    for cat, cnt in sorted(cat_counts.items()):
        print(f"  {cat}: {cnt}")

    q_scores = [it.quality_score for it in items if it.quality_score is not None]
    if q_scores:
        avg_q = sum(q_scores) / len(q_scores)
        print(f"\nMean quality score: {avg_q:.3f}  (n={len(q_scores)})")

    print("\nfilter_rxsafebench.py DONE")


if __name__ == "__main__":
    main()
