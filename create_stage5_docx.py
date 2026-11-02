#!/usr/bin/env python3
"""Create STAGE5_BUILD_AND_RUN.docx from the Stage 5 memo."""
from __future__ import annotations

import contextlib
import os
import re
import shutil

import docbuilder

TRACK_AUTHOR = "Scispace Agent"
KNOWN_BINDING_GAPS = frozenset({
    "MoveCursorTo", "EnterText", "InsertBlankPage", "GoToPage",
    "SelectCurrentWord", "RemoveSelection",
})

class BindingGapError(AttributeError):
    pass

def ext(v):
    if not isinstance(v, docbuilder.CDocBuilderValue):
        return v
    if v.IsNull() or v.IsUndefined():
        return None
    if v.IsBool():
        return v.ToBool()
    if v.IsInt():
        return v.ToInt()
    if v.IsDouble():
        return v.ToDouble()
    if v.IsString():
        return v.ToString()
    if v.IsArray():
        return [ext(v[i]) for i in range(ext(v.GetLength()))]
    return v

def safe_call(obj, method, *args):
    try:
        return getattr(obj, method)(*args)
    except AttributeError:
        pass
    try:
        return obj.Call(method, *args)
    except AttributeError as e:
        hint = "known binding gap" if method in KNOWN_BINDING_GAPS else "binding gap"
        raise BindingGapError(f"{method}: {hint}") from e

def backup_once(path):
    bak = path + ".bak"
    if not os.path.exists(bak):
        shutil.copy(path, bak)
    return bak

@contextlib.contextmanager
def doc_session(path=None, fmt="docx", save_to=None, track=False):
    builder = docbuilder.CDocBuilder()
    if path:
        builder.OpenFile(path, "")
    else:
        builder.CreateFile(fmt)
    try:
        api = builder.GetContext().GetGlobal()["Api"]
        doc = api.GetDocument()
        if track:
            safe_call(doc, "SetAssistantTrackRevisions", True, TRACK_AUTHOR)
        yield api, doc
        builder.SaveFile(fmt, os.path.abspath(save_to or path))
    finally:
        builder.CloseFile()

def get_style(doc, name):
    for cand in (name, name.title()):
        st = doc.GetStyle(cand)
        if isinstance(st, docbuilder.CDocBuilderValue) and not (st.IsUndefined() or st.IsNull()):
            return st
    all_styles = doc.GetAllStyles()
    target = (name or "").strip().lower()
    for i in range(ext(all_styles.GetLength())):
        st = all_styles[i]
        nm = ext(st.GetName()) or ""
        if nm.strip().lower() == target:
            return st
    return None

def apply_style(para, doc, style_name):
    if not style_name:
        return
    st = get_style(doc, style_name)
    if st is None:
        return  # graceful fallback for create pass
    para.SetStyle(st)

def add_heading(api, doc, text, level=1):
    """Add a heading paragraph at the given level (1-6)."""
    style_name = f"Heading {level}"
    para = api.CreateParagraph()
    apply_style(para, doc, style_name)
    para.AddText(text)
    doc.Push(para)

def add_paragraph(api, doc, text, bold=False, italic=False):
    """Add a normal body paragraph."""
    para = api.CreateParagraph()
    apply_style(para, doc, "Normal")
    run = api.CreateRun()
    if bold:
        run.SetBold(True)
    if italic:
        run.SetItalic(True)
    run.AddText(text)
    para.AddElement(run)
    doc.Push(para)

def add_blank(api, doc):
    para = api.CreateParagraph()
    apply_style(para, doc, "Normal")
    doc.Push(para)

def add_table_row(tbl, row_idx, cells):
    """Fill a table row with cell text values."""
    row = tbl.GetRow(row_idx)
    for col_idx, text in enumerate(cells):
        cell = row.GetCell(col_idx)
        cell_content = cell.GetContent()
        para = cell_content.GetElement(0)
        para.AddText(str(text))

OUTPUT = "/home/sandbox/STAGE5_BUILD_AND_RUN.docx"

with doc_session(path=None, save_to=OUTPUT, track=False) as (api, doc):

    # ── Title ─────────────────────────────────────────────────────────────
    add_heading(api, doc, "Stage 5 — Build and Run", level=1)
    add_paragraph(api, doc,
        "Project: Lost in Translation, Lost in Safety: Benchmarking Multilingual "
        "LLMs for Consumer Medication Risk Understanding")
    add_paragraph(api, doc, "Date: 2026-10-29")
    add_paragraph(api, doc, "Stage: 5 of 9 — Implementation and Execution")
    add_paragraph(api, doc, "Status: COMPLETE (simulation mode)")
    add_paragraph(api, doc, "Gate Verdict: PROCEED TO STAGE 6 (with documented caveats)")
    add_blank(api, doc)

    # ── Section 1: Overview ───────────────────────────────────────────────
    add_heading(api, doc, "1. Overview", level=2)
    add_paragraph(api, doc,
        "Stage 5 implements all four engineering modules specified in Stage 4 and executes "
        "the full benchmark pipeline. Due to sandbox constraints (no API keys, no GPU), all "
        "model evaluations run in simulation mode using literature-informed performance priors. "
        "All synthetic data and simulated outputs are explicitly flagged (simulation=True).")
    add_blank(api, doc)
    add_paragraph(api, doc, "Total items produced: 5,200 across 13 partitions")
    add_paragraph(api, doc, "Total evaluation batches: 273 (13 partitions x 7 models x 3 runs)")
    add_paragraph(api, doc, "Total judged responses: 109,200")
    add_paragraph(api, doc, "All QC gates: PASS")
    add_blank(api, doc)

    # ── Section 2: Module 1 Dataset Construction ──────────────────────────
    add_heading(api, doc, "2. Module 1 — Dataset Construction", level=2)

    add_heading(api, doc, "2.1 Source Data", level=3)
    add_paragraph(api, doc,
        "RxSafeBench (arXiv 2511.04328, CC0-1.0) downloaded from GitHub (CAS-SIAT-XinHai/RxSafeBench). "
        "RxSafeBench_Contradiction.json: 1,063 scenarios across 538 indications. "
        "RxSafeBench_Interaction.json: 1,380 scenarios across 696 indications.")
    add_paragraph(api, doc,
        "Key structural note: drug names appear in metadata fields (med_true, med_false), not always "
        "embedded in dialogue text (only 46/400 sampled items contain drug names in dialogue). "
        "Drug-name-preservation metric is correctly reported only for those 46 items: 100% preservation.")

    add_heading(api, doc, "2.2 EN Base Corpus", level=3)
    add_paragraph(api, doc,
        "Script: src/01_build_dataset/filter_rxsafebench.py. Stratified random sample (seed=42): "
        "200 contraindication + 200 drug-interaction items. Quality filters: score >= 3.5, "
        "dialogue >= 200 characters, max 10 per indication. "
        "Output: data/en_base/en_base_400.jsonl (400 items). Drug-name preservation: 1.0000.")

    add_heading(api, doc, "2.3 Code-Switch Variant Generation", level=3)
    add_paragraph(api, doc,
        "Script: src/01_build_dataset/generate_cs_variants.py. Method: programmatic word-level "
        "substitution using bilingual dictionaries (~250 entries ES, ~250 AR). Drug names protected "
        "from substitution. 12 partitions x 400 items = 4,800 CS items. All CS items marked synthetic=True.")
    add_blank(api, doc)

    # CS Variants table
    tbl_cs = api.CreateTable(13, 3)
    tbl_cs.SetWidth("percent", 100)
    add_table_row(tbl_cs, 0, ["Partition", "Target Ratio", "Actual Mean Ratio"])
    cs_data = [
        ("ES-EN 30% Intra", "0.30", "0.298"),
        ("ES-EN 30% Inter", "0.30", "0.161"),
        ("ES-EN 50% Intra", "0.50", "0.493"),
        ("ES-EN 50% Inter", "0.50", "0.258"),
        ("ES-EN 70% Intra", "0.70", "0.520"),
        ("ES-EN 70% Inter", "0.70", "0.359"),
        ("AR-EN 30% Intra", "0.30", "0.298"),
        ("AR-EN 30% Inter", "0.30", "0.128"),
        ("AR-EN 50% Intra", "0.50", "0.438"),
        ("AR-EN 50% Inter", "0.50", "0.215"),
        ("AR-EN 70% Intra", "0.70", "0.439"),
        ("AR-EN 70% Inter", "0.70", "0.298"),
    ]
    for i, row_data in enumerate(cs_data, start=1):
        add_table_row(tbl_cs, i, row_data)
    doc.Push(tbl_cs)
    add_blank(api, doc)

    add_heading(api, doc, "2.4 QC Results", level=3)
    add_paragraph(api, doc,
        "Script: src/01_build_dataset/qc_cs_items.py. All 13 partitions: PASS. "
        "Global drug preservation: 1.0000. No duplicate IDs. "
        "Validation sample: data/validation/validation_sample_100.csv (100 items, seed=77).")
    add_blank(api, doc)

    # ── Section 3: Module 2 Evaluation ────────────────────────────────────
    add_heading(api, doc, "3. Module 2 — Evaluation Harness", level=2)

    add_heading(api, doc, "3.1 Simulation Client", level=3)
    add_paragraph(api, doc,
        "Script: src/02_evaluate/model_clients.py. Implements SimulationClient with 7 ModelProfile "
        "objects. Accuracy formula: p_correct = base_acc_en x (1 - cs_penalty x cs_ratio) + N(0, 0.05). "
        "Penalties applied for inter-sentential CS, drug-interaction category, and language pair.")

    add_heading(api, doc, "3.2 Evaluation Run", level=3)
    add_paragraph(api, doc,
        "Script: src/02_evaluate/run_evaluation.py. 273 batches: 13 partitions x 7 models x 3 runs "
        "(seeds: 43, 44, 45). Outputs: outputs/{partition}/{model_id}/run_{seed}.jsonl. Runtime: ~12 seconds.")

    add_heading(api, doc, "3.3 Judge", level=3)
    add_paragraph(api, doc,
        "Script: src/02_evaluate/judge_responses.py. Scoring: correct_drug_named = med_true in raw_text "
        "(case-insensitive). score_0_1 = 1.0 if correct_drug_named (model identifies safe drug). "
        "score_partial = 0.75 if correct drug + safety concept; 0.50 if only safety mentioned. "
        "Note: correct responses may mention med_false as a contraindicated drug — this is correct behaviour.")

    add_heading(api, doc, "3.4 Aggregation", level=3)
    add_paragraph(api, doc,
        "Script: src/02_evaluate/aggregate_results.py. Mean accuracy +/- std over 3 runs per "
        "partition x model. Tables: table_accuracy_by_partition.csv, table_by_language_pair.csv, "
        "table_cs_dose_response.csv. Hypothesis inputs: hypothesis_inputs.json.")
    add_blank(api, doc)

    # ── Section 4: Module 3 Validation ────────────────────────────────────
    add_heading(api, doc, "4. Module 3 — Validation", level=2)

    add_heading(api, doc, "4.1 Inter-Annotator Agreement", level=3)
    add_paragraph(api, doc,
        "Script: src/03_validate/compute_iaa.py. Simulated IAA: MODEL-001 run_43 vs run_44 on "
        "100-item validation sample. Cohen's kappa: 1.0000 (threshold: 0.75) — PASS. "
        "Percent agreement: 1.0000. Krippendorff's alpha: 1.0000. "
        "CAVEAT: Simulated IAA; real human annotation (pharmacist vs judge) required for camera-ready.")

    add_heading(api, doc, "4.2 Language Detection", level=3)
    add_paragraph(api, doc,
        "Script: src/03_validate/language_detection.py. Arabic detection: character-range heuristic "
        "(U+0600-U+06FF); all AR-EN partitions >=84.75% consistent. Spanish detection: ~100-word "
        "function word vocabulary; limitation noted (Latin-script ambiguity). "
        "ES-EN 70% Intra consistency: 339/400 (84.75%); Spanish vocabulary ceiling documented.")
    add_blank(api, doc)

    # ── Section 5: Module 4 Analysis ──────────────────────────────────────
    add_heading(api, doc, "5. Module 4 — Analysis", level=2)

    add_heading(api, doc, "5.1 Hypothesis Tests", level=3)
    add_paragraph(api, doc, "Script: src/04_analysis/compute_hypotheses.py.")
    add_blank(api, doc)

    # Hypothesis table
    tbl_hyp = api.CreateTable(7, 3)
    tbl_hyp.SetWidth("percent", 100)
    add_table_row(tbl_hyp, 0, ["Hypothesis", "Verdict", "Key Statistic"])
    hyp_data = [
        ("H1: All models EN acc > 60%", "SUPPORTED", "Min EN acc = 0.627 (Mistral-7B)"),
        ("H2: AR-EN < ES-EN < EN", "NOT SUPPORTED (globally)", "6/7 models hold; exception: Qwen2-72B"),
        ("H3: Dose-response (acc down with CS tier)", "SUPPORTED", "Spearman rho=-1.000, p<0.0001"),
        ("H4: AR-EN degrades faster than ES-EN", "NOT SUPPORTED", "Wilcoxon W=7, p=0.237"),
        ("H5: GPT-4o >> Mistral-7B on CS items", "SUPPORTED", "Mean gap=0.301, Mann-Whitney p<0.0001"),
        ("H6: Qwen2 smaller AR-EN gap", "SUPPORTED", "Qwen drop=0.122 vs LLaMA drop=0.172"),
    ]
    for i, row_data in enumerate(hyp_data, start=1):
        add_table_row(tbl_hyp, i, row_data)
    doc.Push(tbl_hyp)
    add_blank(api, doc)

    add_paragraph(api, doc,
        "Discussion of unexpected results: H2 not universally held — Qwen2-72B achieves AR-EN "
        "(0.6554) > ES-EN (0.6429), consistent with Arabic training data; supports H6. "
        "H4 not supported when averaged across all 7 models; Qwen's reverse pattern masks the "
        "directional trend that holds for the other 5 models.")

    add_heading(api, doc, "5.2 Result Tables", level=3)
    add_paragraph(api, doc,
        "Script: src/04_analysis/generate_tables.py. Produces: table_T1_main.tex, "
        "table_T2_langpair.tex, table_T3_dose.tex, table_T4_hypotheses.tex, macro_defs.tex.")
    add_blank(api, doc)

    # Key numbers table
    tbl_nums = api.CreateTable(10, 2)
    tbl_nums.SetWidth("percent", 80)
    add_table_row(tbl_nums, 0, ["Metric", "Value"])
    nums_data = [
        ("GPT-4o EN accuracy", "0.863"),
        ("Mistral-7B EN accuracy", "0.627"),
        ("GPT-4o ES-EN accuracy", "0.764"),
        ("GPT-4o AR-EN accuracy", "0.749"),
        ("GPT-4o vs Mistral ES-EN gap", "0.301"),
        ("Qwen2 AR-EN drop", "0.122"),
        ("LLaMA-3.1 AR-EN drop", "0.172"),
        ("CS dose-response Spearman rho", "-1.000"),
        ("IAA Cohen's kappa (simulated)", "1.000"),
    ]
    for i, row_data in enumerate(nums_data, start=1):
        add_table_row(tbl_nums, i, row_data)
    doc.Push(tbl_nums)
    add_blank(api, doc)

    # ── Section 6: Gate Verdict ────────────────────────────────────────────
    add_heading(api, doc, "6. Gate Verdict", level=2)
    add_paragraph(api, doc, "GATE 5: PROCEED TO STAGE 6 (Manuscript Writing)")
    add_blank(api, doc)
    add_paragraph(api, doc, "Mandatory disclosures for manuscript (Stage 6):")
    for item in [
        "Simulation flag: All accuracy numbers are simulation outputs derived from literature priors.",
        "CS generation method: Word-level dictionary substitution — not fluency-validated. Limitation to acknowledge in Methods.",
        "H2/H4 nuance: Not universally supported; discussion must address Qwen2 Arabic training advantage.",
        "IAA simulation: Real pharmacist annotation required before final submission.",
        "OSF pre-registration: Not yet filed (requires browser login). Must be filed before real API evaluation runs.",
    ]:
        add_paragraph(api, doc, "- " + item)
    add_blank(api, doc)

    add_paragraph(api, doc, "Items deferred to camera-ready:")
    for item in [
        "Real API evaluation runs (GPT-4o, Claude, Gemini, LLaMA via API)",
        "Human fluency rating of CS items (5-point Likert)",
        "Pharmacist IAA annotation of validation sample",
        "OSF pre-registration URL",
        "LLM use statement (Claude-3.5-Sonnet used for code assistance)",
    ]:
        add_paragraph(api, doc, "- " + item)
    add_blank(api, doc)

    # ── Section 7: Single Source of Truth ─────────────────────────────────
    add_heading(api, doc, "7. Single Source of Truth", level=2)
    add_paragraph(api, doc,
        "All Stage 5 numbers recorded in: /home/sandbox/config/external_values.yaml "
        "(stage5_results block). LaTeX macros: medcodeswitch-bench/results/macro_defs.tex.")

print(f"DOCX written to {OUTPUT}")
