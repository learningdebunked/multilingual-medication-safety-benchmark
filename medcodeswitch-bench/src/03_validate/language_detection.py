"""
language_detection.py — verify CS ratio and language mix in generated items.

Uses character-level heuristics (Arabic Unicode range) plus simple English
word frequency to estimate language proportions without external libraries.

Output: results/language_detection_report.json
        results/language_detection_sample.csv (25 items per partition)
"""

import os, json, pathlib, csv, unicodedata, re
from collections import defaultdict

os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"]      = "1"

ROOT    = pathlib.Path(__file__).resolve().parents[2]
DATA    = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

PARTITIONS = [
    ("en_base",        DATA / "en_base"        / "en_base_400.jsonl"),
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

# Top-100 Spanish function words and common medical words to detect Spanish
SPANISH_MARKERS = {
    "el","la","los","las","un","una","unos","unas","de","del","al","y","o","en",
    "que","es","son","con","por","para","se","le","les","su","sus","mi","me",
    "paciente","médico","dolor","tratamiento","síntomas","tiene","puede","debe",
    "más","pero","como","también","cuando","si","todo","todos","está","están",
    "fue","era","hay","ser","estar","tener","hacer","no","sí","muy","bien",
    "medicamento","dosis","efectos","secundarios","contraindicado",
}

# Arabic Unicode block: U+0600–U+06FF
def arabic_char_fraction(text: str) -> float:
    """Fraction of characters (excl. spaces) that are Arabic script."""
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    ar = sum(1 for c in chars if '\u0600' <= c <= '\u06FF')
    return ar / len(chars)


def spanish_word_fraction(text: str) -> float:
    """Fraction of whitespace-delimited tokens that match Spanish marker list."""
    tokens = [t.lower().strip('.,;:!?()[]"""\'') for t in text.split()]
    if not tokens:
        return 0.0
    sp = sum(1 for t in tokens if t in SPANISH_MARKERS)
    return sp / len(tokens)


def analyse_item(item: dict, partition: str) -> dict:
    dialogue  = item.get("cs_dialogue", item.get("dialogue", ""))
    cs_ratio  = item.get("cs_ratio", 0.0)
    lang_pair = item.get("language_pair", "en")

    ar_frac = arabic_char_fraction(dialogue)
    es_frac = spanish_word_fraction(dialogue)

    # Detect dominant non-English signal
    if lang_pair == "ar_en":
        detected_cs_signal = ar_frac
        detection_method   = "arabic_char_fraction"
    elif lang_pair == "es_en":
        detected_cs_signal = es_frac
        detection_method   = "spanish_word_fraction"
    else:
        detected_cs_signal = 0.0
        detection_method   = "none"

    # Consistency check: measured cs_ratio (from metadata) vs detected signal
    # Arabic detection (character-based) is more reliable than Spanish (word-list heuristic).
    # We allow 0.35 discrepancy for Latin-script (ES) and 0.25 for Arabic.
    cs_ratio_reported = float(cs_ratio)
    discrepancy       = abs(detected_cs_signal - cs_ratio_reported)
    threshold         = 0.35 if lang_pair == "es_en" else 0.25
    consistent        = discrepancy <= threshold or lang_pair == "en"

    return {
        "item_id"           : item.get("item_id"),
        "partition"         : partition,
        "language_pair"     : lang_pair,
        "cs_ratio_reported" : round(cs_ratio_reported, 4),
        "detected_cs_signal": round(detected_cs_signal, 4),
        "detection_method"  : detection_method,
        "discrepancy"       : round(discrepancy, 4),
        "consistent"        : consistent,
    }


def main():
    report    = {}
    sample_rows = []
    SAMPLE_PER_PART = 25

    for partition, path in PARTITIONS:
        if not path.exists():
            print(f"  SKIP: {path}")
            continue

        items = []
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    items.append(json.loads(line))

        analyses = [analyse_item(it, partition) for it in items]
        consistent_n = sum(1 for a in analyses if a["consistent"])
        mean_signal  = sum(a["detected_cs_signal"] for a in analyses) / len(analyses) if analyses else 0.0
        mean_reported= sum(a["cs_ratio_reported"]  for a in analyses) / len(analyses) if analyses else 0.0

        report[partition] = {
            "n_items"          : len(analyses),
            "consistent_n"     : consistent_n,
            "consistent_pct"   : round(consistent_n / len(analyses) * 100, 1) if analyses else 0.0,
            "mean_cs_ratio_reported" : round(mean_reported, 4),
            "mean_cs_signal_detected": round(mean_signal,   4),
        }

        # Sample rows for CSV
        step = max(1, len(analyses) // SAMPLE_PER_PART)
        for i in range(0, len(analyses), step):
            if len(sample_rows) < (PARTITIONS.index((partition, path)) + 1) * SAMPLE_PER_PART:
                sample_rows.append(analyses[i])

        print(f"  {partition:20s}: n={len(analyses):4d}  consistent={consistent_n}/{len(analyses)}"
              f"  mean_reported={mean_reported:.3f}  mean_detected={mean_signal:.3f}")

    # Write JSON report
    out_json = RESULTS / "language_detection_report.json"
    with open(out_json, "w") as fh:
        json.dump(report, fh, indent=2)

    # Write CSV sample
    out_csv = RESULTS / "language_detection_sample.csv"
    fields  = ["item_id","partition","language_pair","cs_ratio_reported",
               "detected_cs_signal","detection_method","discrepancy","consistent"]
    with open(out_csv, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sample_rows)

    print(f"\n  wrote {out_json}")
    print(f"  wrote {out_csv}")
    print("language_detection.py DONE")


if __name__ == "__main__":
    main()
