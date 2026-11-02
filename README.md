# Lost in Translation, Lost in Safety
## Benchmarking Multilingual LLMs for Consumer Medication Risk Understanding

[![TACL Submission](https://img.shields.io/badge/Target%20Journal-TACL%20(SJR%20Q1)-blue)](https://transacl.org)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Simulation Results](https://img.shields.io/badge/Results-Simulation%20Only-orange)](config/external_values.yaml)

> **Status:** Pre-submission manuscript. All numerical results are simulation placeholders
> (`simulation=true` in `config/external_values.yaml`). Replace with live API results
> before submission — see `TACL_SUBMISSION_CHECKLIST.docx` for the full action list.

---

## Overview

This repository contains the full research codebase, manuscript, and pipeline deliverables
for a benchmark study evaluating how well large language models (LLMs) comprehend
consumer-facing medication safety information when prompts are written in code-switched
language (English–Spanish and English–Arabic at multiple intra-word and inter-word ratios).

**Target:** *Transactions of the Association for Computational Linguistics* (TACL), rolling submission.

---

## Repository Structure

```
.
├── paper/                        # LaTeX manuscript files
│   ├── main_tacl.tex             # TACL-formatted manuscript (primary submission file)
│   ├── main_tacl.pdf             # Compiled TACL PDF (7 pages, A4)
│   ├── main.tex                  # Original elsarticle draft (do not overwrite)
│   ├── tacl_refs.bib             # 22-entry BibTeX bibliography
│   ├── tacl2021v1.sty            # TACL 2021 style file
│   ├── acl_natbib.bst            # TACL bibliography style
│   ├── macro_defs.tex            # LaTeX macros tied to result IDs R001–R009
│   ├── table_T1_main.tex         # Main results table (13 partitions × 7 models)
│   ├── table_T2_langpair.tex     # Language-pair summary table
│   ├── table_T3_dose.tex         # Dose-response table
│   └── table_T4_hypotheses.tex   # Hypothesis test summary table
│
├── medcodeswitch-bench/          # Benchmark dataset and evaluation harness
│   ├── src/                      # Source code (build, evaluate, validate, analyse)
│   ├── data/                     # Benchmark data (EN base + ES-EN + AR-EN partitions)
│   │   ├── en_base/              # 400 English base items
│   │   ├── es_en/                # ES-EN code-switched variants (30/50/70% × intra/inter)
│   │   ├── ar_en/                # AR-EN code-switched variants (30/50/70% × intra/inter)
│   │   └── raw/                  # Raw source data (RxSafeBench)
│   ├── configs/                  # Evaluation configuration files
│   ├── results/                  # Aggregated results (simulation)
│   ├── tests/                    # Unit tests
│   └── vendor/                   # Third-party dependencies
│
├── config/
│   └── external_values.yaml      # Single source of truth: R001–R009 (simulation=true)
│
├── STAGE1_NOVELTY_MEMO.docx      # Pipeline Stage 1: Novelty assessment
├── STAGE1B_SIGNIFICANCE_JOURNALS.docx  # Stage 1B: Journal targeting
├── STAGE2_DATASET_FEASIBILITY.docx     # Stage 2: Dataset feasibility
├── STAGE3_STUDY_PROTOCOL.docx    # Stage 3: Hypotheses, metrics, statistical plan
├── STAGE4_ENGINEERING_SPEC.docx  # Stage 4: Engineering specification
├── STAGE5_BUILD_AND_RUN.docx     # Stage 5: Build and run plan
├── STAGE6_MANUSCRIPT.docx        # Stage 6: Manuscript draft
├── STAGE7_HOSTILE_REVIEW.docx    # Stage 7: Hostile peer review
├── STAGE8_PORTFOLIO.docx         # Stage 8: Submission portfolio
├── STAGE9_FINAL_RETROSPECTIVE.docx  # Stage 9: Final retrospective
├── TACL_SUBMISSION_CHECKLIST.docx   # Pre-submission checklist (C1–C7)
│
└── create_tacl_checklist.py      # Script that generates TACL_SUBMISSION_CHECKLIST.docx
```

---

## Benchmark: MedCodeSwitch-Bench

**5,200 items** across **13 partitions**:

| Partition | Code-switch ratio | Direction |
|-----------|-------------------|-----------|
| `en_base` | 0% (English only) | — |
| `es_en_30_intra` / `es_en_30_inter` | 30% | ES→EN intra-word / inter-word |
| `es_en_50_intra` / `es_en_50_inter` | 50% | ES→EN intra-word / inter-word |
| `es_en_70_intra` / `es_en_70_inter` | 70% | ES→EN intra-word / inter-word |
| `ar_en_30_intra` / `ar_en_30_inter` | 30% | AR→EN intra-word / inter-word |
| `ar_en_50_intra` / `ar_en_50_inter` | 50% | AR→EN intra-word / inter-word |
| `ar_en_70_intra` / `ar_en_70_inter` | 70% | AR→EN intra-word / inter-word |

**Source:** RxSafeBench (`10.48550/arxiv.2511.04328`) — 400 EN base items on drug interactions
and contraindications, extended via the DOSEBENCH (`10.48550/arxiv.2606.04262`) protocol.

---

## Evaluated Models

| Model | Parameter count | Access |
|-------|-----------------|--------|
| GPT-4o (`gpt-4o-2024-11-20`) | — | OpenAI API |
| Claude-3.5-Sonnet (`claude-3-5-sonnet-20241022`) | — | Anthropic API |
| GPT-4-Turbo (`gpt-4-turbo-2024-04-09`) | — | OpenAI API |
| Gemini-1.5-Pro (`gemini-1.5-pro-002`) | — | Google AI API |
| Qwen2-72B-Instruct | 72B | Alibaba Cloud / HF |
| LLaMA-3.1-70B-Instruct | 70B | Meta AI / HF |
| Mistral-7B-Instruct-v0.3 | 7B | Mistral AI / HF |

---

## Key Hypotheses

| ID | Hypothesis | Verdict (simulation) |
|----|-----------|----------------------|
| H1 | Accuracy degrades monotonically with CS ratio | SUPPORTED |
| H2 | AR-EN degrades more than ES-EN | NOT SUPPORTED (Qwen2 reversal) |
| H3 | Negative correlation: model size vs. accuracy drop | SUPPORTED (ρ = −1.0, simulation) |
| H4 | AR-EN intra-word > inter-word accuracy drop | NOT SUPPORTED (W=7, p=0.237) |
| H5 | GPT-4o outperforms all models at all CS ratios | SUPPORTED |
| H6 | Mistral-7B shows the largest accuracy drop | SUPPORTED |

> ⚠️  H3 ρ = −1.0 is a simulation artifact. Re-run with live data before reporting.

---

## Reproducing the Evaluation

### Prerequisites

```bash
pip install openai anthropic google-generativeai transformers datasets
```

### Run pipeline

```bash
# 1. Build code-switched variants (requires en_base/en_base_400.jsonl)
python medcodeswitch-bench/src/01_build_dataset/build_cs_variants.py

# 2. Run LLM evaluation (set API keys first — see configs/)
python medcodeswitch-bench/src/02_evaluate/run_evaluation.py --config configs/eval_config.yaml

# 3. LLM-as-judge scoring
python medcodeswitch-bench/src/02_evaluate/run_judge.py

# 4. Validate outputs
python medcodeswitch-bench/src/03_validate/validate_outputs.py

# 5. Statistical analysis
python medcodeswitch-bench/src/04_analysis/run_analysis.py

# 6. Update external_values.yaml with live results, then recompile
cd paper && pdflatex main_tacl.tex && bibtex main_tacl && pdflatex main_tacl.tex && pdflatex main_tacl.tex
```

---

## Compiling the Manuscript

```bash
cd paper
pdflatex main_tacl.tex
bibtex main_tacl
pdflatex main_tacl.tex
pdflatex main_tacl.tex
# Output: main_tacl.pdf (TACL-formatted, ~7 pages)
```

---

## Pre-submission Checklist

See `TACL_SUBMISSION_CHECKLIST.docx` for the full C1–C7 action list. Critical blockers before submission:

- **C1**: Replace simulation results with live LLM API runs (~USD 300); update `config/external_values.yaml`
- **C3**: Update Section 4.2 — LLM judge: GPT-4o → Claude-3.5-Sonnet
- **C4**: OSF pre-registration (before data collection)
- **C5**: Human fluency validation (n ≥ 30 bilingual raters, ICC/Krippendorff's α)
- **C7**: Re-run H3 with Jonckheere–Terpstra test after live results

---

## Citation

If you use this benchmark or codebase, please cite:

```bibtex
@article{PoreddyEtAl2026medcodeswitch,
  title     = {Lost in Translation, Lost in Safety: Benchmarking Multilingual {LLM}s
               for Consumer Medication Risk Understanding},
  author    = {Poreddy, Kapil Kumar Reddy and others},
  journal   = {Transactions of the Association for Computational Linguistics},
  year      = {2026},
  note      = {Under review}
}
```

---

## License

- **Code:** MIT License
- **Data:** CC BY 4.0 (derived from RxSafeBench under CC BY 4.0)
- **Manuscript:** © The Authors — all rights reserved until publication

---

## Acknowledgements

Built using the SciSpace AI-assisted research pipeline (9-stage protocol). All numerical results
are simulation placeholders pending live API runs. See `config/external_values.yaml`.
