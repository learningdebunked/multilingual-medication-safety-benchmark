"""
generate_tables.py — produce LaTeX and CSV result tables for the manuscript.

Tables produced:
  T1: Main accuracy table (partitions × models)       → results/table_T1_main.tex + .csv
  T2: Language-pair summary (EN / ES-EN / AR-EN)      → results/table_T2_langpair.tex + .csv
  T3: CS dose-response (tiers 0/30/50/70)             → results/table_T3_dose.tex + .csv
  T4: Hypothesis test summary                          → results/table_T4_hypotheses.tex + .csv
  macro_defs.tex: LaTeX macros for all key numbers    → results/macro_defs.tex
"""

import os, json, csv, pathlib, statistics

os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"]      = "1"

ROOT    = pathlib.Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"

MODEL_LABELS = {
    "MODEL-001": "GPT-4o",
    "MODEL-002": "Claude-3.5",
    "MODEL-003": "GPT-4-T",
    "MODEL-004": "Gemini-1.5",
    "MODEL-007": "Qwen2-72B",
    "MODEL-005": "LLaMA-3.1",
    "MODEL-006": "Mistral-7B",
}
MODEL_ORDER = ["MODEL-001","MODEL-002","MODEL-003","MODEL-004",
               "MODEL-007","MODEL-005","MODEL-006"]

PARTITION_LABELS = {
    "en_base"      : "EN",
    "es_en_30_intra": "ES-EN 30% Intra",
    "es_en_30_inter": "ES-EN 30% Inter",
    "es_en_50_intra": "ES-EN 50% Intra",
    "es_en_50_inter": "ES-EN 50% Inter",
    "es_en_70_intra": "ES-EN 70% Intra",
    "es_en_70_inter": "ES-EN 70% Inter",
    "ar_en_30_intra": "AR-EN 30% Intra",
    "ar_en_30_inter": "AR-EN 30% Inter",
    "ar_en_50_intra": "AR-EN 50% Intra",
    "ar_en_50_inter": "AR-EN 50% Inter",
    "ar_en_70_intra": "AR-EN 70% Intra",
    "ar_en_70_inter": "AR-EN 70% Inter",
}

HYPOTHESIS_DESC = {
    "H1": "All models EN accuracy > 60\\%",
    "H2": "Language ordering: AR-EN $<$ ES-EN $<$ EN",
    "H3": "Dose-response: accuracy $\\downarrow$ with CS ratio",
    "H4": "AR-EN degrades faster than ES-EN",
    "H5": "GPT-4o significantly outperforms Mistral-7B (CS)",
    "H6": "Qwen2-72B smaller AR-EN gap (multilingual training)",
}


def load_csv(path) -> list[dict]:
    with open(path) as fh:
        return list(csv.DictReader(fh))


def load_json(path) -> dict:
    with open(path) as fh:
        return json.load(fh)


def bold_if_max(value_str: str, row_vals: list[str]) -> str:
    """Bold the maximum value in a row (LaTeX)."""
    try:
        nums = []
        for v in row_vals:
            try:
                nums.append(float(v.split("±")[0]))
            except:
                nums.append(-999.0)
        my_num = float(value_str.split("±")[0])
        if my_num == max(nums):
            return f"\\textbf{{{value_str}}}"
    except:
        pass
    return value_str


# ── T1: Main accuracy table ────────────────────────────────────────────────

def make_T1(part_rows: list[dict]):
    col_headers = " & ".join(MODEL_LABELS[m] for m in MODEL_ORDER)
    lines = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\caption{Accuracy (mean$\\pm$std, 3 runs) across 13 benchmark partitions and 7 LLMs. "
        "\\textbf{Bold} = best per row. All results simulation=True (sandbox constraints).}",
        "\\label{tab:main_results}",
        "\\resizebox{\\textwidth}{!}{%",
        f"\\begin{{tabular}}{{l{'r'*len(MODEL_ORDER)}}}",
        "\\toprule",
        f"Partition & {col_headers} \\\\",
        "\\midrule",
    ]

    prev_lang = None
    for row in part_rows:
        part  = row["partition"]
        label = PARTITION_LABELS.get(part, part)
        lang  = row.get("language_pair", "")

        if lang != prev_lang and prev_lang is not None:
            lines.append("\\midrule")
        prev_lang = lang

        vals = [row.get(m, "NA") for m in MODEL_ORDER]
        numeric_vals = [v.split("±")[0] if "±" in v else v for v in vals]
        bolded = [bold_if_max(v, numeric_vals) if v != "NA" else "NA"
                  for v in vals]
        row_str = " & ".join(bolded)
        lines.append(f"{label} & {row_str} \\\\")

    lines += [
        "\\bottomrule",
        "\\end{tabular}}",
        "\\end{table*}",
    ]
    return "\n".join(lines)


# ── T2: Language-pair summary ──────────────────────────────────────────────

def make_T2(langpair_rows: list[dict]):
    col_headers = " & ".join(MODEL_LABELS[m] for m in MODEL_ORDER)
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Mean accuracy by language pair, averaged over CS tiers.}",
        "\\label{tab:langpair}",
        f"\\begin{{tabular}}{{l{'r'*len(MODEL_ORDER)}}}",
        "\\toprule",
        f"Language Pair & {col_headers} \\\\",
        "\\midrule",
    ]
    lang_labels = {"en": "English (EN)", "es_en": "Spanish-EN (ES-EN)", "ar_en": "Arabic-EN (AR-EN)"}
    for row in langpair_rows:
        lang  = row["language_pair"]
        label = lang_labels.get(lang, lang)
        vals  = [str(row.get(m, "NA")) for m in MODEL_ORDER]
        lines.append(f"{label} & {' & '.join(vals)} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines)


# ── T3: CS dose-response ───────────────────────────────────────────────────

def make_T3(dose_rows: list[dict]):
    col_headers = " & ".join(MODEL_LABELS[m] for m in MODEL_ORDER)
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Accuracy by CS ratio tier, averaged over ES-EN and AR-EN.}",
        "\\label{tab:dose_response}",
        f"\\begin{{tabular}}{{c{'r'*len(MODEL_ORDER)}}}",
        "\\toprule",
        f"CS Tier (\\%) & {col_headers} \\\\",
        "\\midrule",
    ]
    tier_labels = {"0":"0 (EN baseline)","30":"30","50":"50","70":"70"}
    for row in dose_rows:
        tier  = row["cs_tier"]
        label = tier_labels.get(tier, tier)
        vals  = [str(row.get(m, "NA")) for m in MODEL_ORDER]
        lines.append(f"{label} & {' & '.join(vals)} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines)


# ── T4: Hypothesis summary ─────────────────────────────────────────────────

def make_T4(hyp: dict):
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Hypothesis test summary. All results simulation=True.}",
        "\\label{tab:hypotheses}",
        "\\begin{tabular}{clcl}",
        "\\toprule",
        "ID & Description & Verdict & Key Statistic \\\\",
        "\\midrule",
    ]
    for hid in ["H1","H2","H3","H4","H5","H6"]:
        h     = hyp[hid]
        desc  = HYPOTHESIS_DESC.get(hid, hid)
        verdict = "\\textcolor{green!50!black}{Supported}" if h["global_pass"] \
                  else "\\textcolor{red!60!black}{Not Supported}"
        # Key stat
        if hid == "H1":
            min_acc = min(v["mean_acc"] for v in h["per_model"].values() if v["mean_acc"])
            stat = f"min EN acc = {min_acc:.3f}"
        elif hid == "H2":
            stat = f"{h['models_holding']}/{h['total_models']} models"
        elif hid == "H3":
            stat = f"$\\rho={h['spearman']['rho']:.3f}$, $p={h['spearman']['p_value']:.4f}$"
        elif hid == "H4":
            stat = f"W={h['wilcoxon']['W']}, $p={h['wilcoxon']['p_value']:.4f}$"
        elif hid == "H5":
            stat = f"U={h['mann_whitney']['U']:.0f}, $p={h['mann_whitney']['p_value']:.4f}$"
        elif hid == "H6":
            stat = f"$\\Delta$AR-drop: Qwen={h['qwen_ar_drop']:.3f}, LLaMA={h['llama_ar_drop']:.3f}"
        else:
            stat = ""
        lines.append(f"{hid} & {desc} & {verdict} & {stat} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines)


# ── Macro definitions ──────────────────────────────────────────────────────

def make_macros(hyp: dict, langpair_rows: list[dict], dose_rows: list[dict]) -> str:
    macros = []

    def mac(name, value, comment=""):
        safe = str(value).replace("%","\\%")
        return f"\\newcommand{{\\{name}}}{{{safe}}} % {comment}"

    # H1
    macros.append(mac("GptFourOEnAcc",
        f"{hyp['H1']['per_model']['MODEL-001']['mean_acc']:.3f}", "GPT-4o EN accuracy"))
    macros.append(mac("MistralEnAcc",
        f"{hyp['H1']['per_model']['MODEL-006']['mean_acc']:.3f}", "Mistral-7B EN accuracy"))

    # H2 — language pair means for MODEL-001
    gpt_row = {r["language_pair"]: r for r in langpair_rows}
    macros.append(mac("GptFourOEsEnAcc",
        f"{gpt_row['es_en']['MODEL-001']}", "GPT-4o ES-EN mean accuracy"))
    macros.append(mac("GptFourOArEnAcc",
        f"{gpt_row['ar_en']['MODEL-001']}", "GPT-4o AR-EN mean accuracy"))

    # H3 — Spearman
    macros.append(mac("HThreeRho",
        f"{hyp['H3']['spearman']['rho']:.3f}", "Spearman rho CS dose-response"))
    macros.append(mac("HThreeP",
        f"{hyp['H3']['spearman']['p_value']:.4f}", "Spearman p-value"))

    # H5 — GPT vs Mistral gap
    gpt_cs = float(gpt_row["es_en"]["MODEL-001"]) if "es_en" in gpt_row else 0
    mis_cs = float(gpt_row["es_en"]["MODEL-006"]) if "es_en" in gpt_row else 0
    macros.append(mac("GptMistralCsGap",
        f"{gpt_cs - mis_cs:.3f}", "GPT-4o minus Mistral-7B ES-EN accuracy gap"))

    # H6 — Qwen vs LLaMA AR drop
    macros.append(mac("QwenArDrop",
        f"{hyp['H6']['qwen_ar_drop']:.3f}", "Qwen2-72B AR-EN accuracy drop"))
    macros.append(mac("LlamaArDrop",
        f"{hyp['H6']['llama_ar_drop']:.3f}", "LLaMA-3.1-70B AR-EN accuracy drop"))

    # Dataset size macros
    macros.append(mac("NItemsTotal",   "5{,}200", "Total benchmark items"))
    macros.append(mac("NItemsBase",    "400",     "EN base items"))
    macros.append(mac("NPartitions",   "13",      "Benchmark partitions"))
    macros.append(mac("NModels",       "7",       "Evaluated LLMs"))
    macros.append(mac("NRuns",         "3",       "Evaluation runs per model/partition"))

    header = (
        "% macro_defs.tex — auto-generated by generate_tables.py\n"
        "% All simulation=True. Do NOT edit manually.\n"
        "% Include with: \\input{macro_defs}\n\n"
    )
    return header + "\n".join(macros)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    part_rows    = load_csv(RESULTS / "table_accuracy_by_partition.csv")
    langpair_rows= load_csv(RESULTS / "table_by_language_pair.csv")
    dose_rows    = load_csv(RESULTS / "table_cs_dose_response.csv")
    hyp          = load_json(RESULTS / "hypothesis_results.json")

    # T1
    t1_tex = make_T1(part_rows)
    (RESULTS / "table_T1_main.tex").write_text(t1_tex)
    print(f"  wrote table_T1_main.tex")

    # T2
    t2_tex = make_T2(langpair_rows)
    (RESULTS / "table_T2_langpair.tex").write_text(t2_tex)
    print(f"  wrote table_T2_langpair.tex")

    # T3
    t3_tex = make_T3(dose_rows)
    (RESULTS / "table_T3_dose.tex").write_text(t3_tex)
    print(f"  wrote table_T3_dose.tex")

    # T4
    t4_tex = make_T4(hyp)
    (RESULTS / "table_T4_hypotheses.tex").write_text(t4_tex)
    print(f"  wrote table_T4_hypotheses.tex")

    # Macros
    macros = make_macros(hyp, langpair_rows, dose_rows)
    (RESULTS / "macro_defs.tex").write_text(macros)
    print(f"  wrote macro_defs.tex")

    print("\ngenerate_tables.py DONE")


if __name__ == "__main__":
    main()
