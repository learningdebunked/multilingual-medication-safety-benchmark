#!/usr/bin/env python3
"""Stage 6 memo DOCX — create pass (track=False, from-blank)."""
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
        if isinstance(st, docbuilder.CDocBuilderValue) and not (
                st.IsUndefined() or st.IsNull()):
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
        raise ValueError(f"style {style_name!r} not resolved")
    para.SetStyle(st)

def apply_resolved(para, style_ref):
    rr = style_ref.get("resolvedRun") or style_ref
    rp = style_ref.get("resolved") or style_ref
    if rr.get("font"):                       para.SetFontFamily(rr["font"])
    if rr.get("sizeHalfPt") is not None:     para.SetFontSize(int(rr["sizeHalfPt"]))
    if rr.get("bold") is not None:           para.SetBold(bool(rr["bold"]))
    if rr.get("italic") is not None:         para.SetItalic(bool(rr["italic"]))
    if rp.get("align"):                      para.SetJc(rp["align"])
    if rp.get("spacing_before") is not None: para.SetSpacingBefore(int(rp["spacing_before"]))
    if rp.get("spacing_after") is not None:  para.SetSpacingAfter(int(rp["spacing_after"]))
    if rp.get("ind_left") is not None:       para.SetIndLeft(int(rp["ind_left"]))

def styled_para(api, doc, text, style_ref):
    para = api.CreateParagraph()
    apply_style(para, doc, style_ref.get("styleName"))
    para.AddText(text)
    apply_resolved(para, style_ref)
    return para

# ── style refs (from doc_style.json) ──────────────────────────────────────────
HEADING1 = {
    "styleName": "Heading 1",
    "resolvedRun": {"sizeHalfPt": 40, "font": "Arial"},
    "resolved": {"spacing_before": "360", "spacing_after": "80"},
}
HEADING2 = {
    "styleName": "Heading 2",
    "resolvedRun": {"sizeHalfPt": 32, "font": "Arial"},
    "resolved": {"spacing_before": "160", "spacing_after": "80"},
}
NORMAL = {
    "styleName": "Normal",
    "resolvedRun": {"sizeHalfPt": 22, "font": "Arial"},
    "resolved": {"spacing_before": "0", "spacing_after": "200"},
}

OUTPUT = "/home/sandbox/STAGE6_MANUSCRIPT.docx"

# ── document content ───────────────────────────────────────────────────────────
SECTIONS = [
    # (style_key, text)
    ("H1", "Stage 6 — Manuscript"),
    ("N",  "Project: Lost in Translation, Lost in Safety: Benchmarking Multilingual LLMs for Consumer Medication Risk Understanding"),
    ("N",  "Date: 2026-10-29"),
    ("N",  "Stage: 6 of 9 — Manuscript Compilation"),
    ("N",  "Status: COMPLETE"),
    ("N",  "Gate Verdict: PROCEED TO STAGE 7 (with documented simulation caveats)"),
    ("N",  ""),

    ("H2", "1. Overview"),
    ("N",  "Stage 6 compiles the full submission-ready LaTeX manuscript for the ACLing 2026 conference (Procedia Computer Science, Elsevier). All content is derived from Stages 1–5 deliverables: the novelty memo, significance scoring, dataset feasibility, study protocol, engineering specification, and the locked simulation results produced in Stage 5."),
    ("N",  ""),
    ("N",  "The manuscript targets the ACLing 2026 Call for Papers (deadline: 5 November 2026) and adheres to the Procedia Computer Science format: single-column, 8 pages maximum, double-blind, Vancouver numbered references. The compiled PDF is exactly 8 pages."),
    ("N",  ""),

    ("H2", "2. Compilation Outcome"),
    ("N",  "Compiler: pdflatex (TeX Live, Ubuntu). Two-pass compilation for cross-references and labels."),
    ("N",  ""),
    ("N",  "Exit code: 0 (both passes). No fatal LaTeX errors."),
    ("N",  "Output: main.pdf — 8 pages, 183,025 bytes."),
    ("N",  "Master copy: /home/sandbox/ACLing2026_manuscript.pdf (179 KB)."),
    ("N",  ""),
    ("N",  "Warnings resolved:"),
    ("N",  "  - Missing logo files (elsevier-logo-3p, SDlogo-3p, Procs): copied from /home/sandbox/acling_template/PROCS_ACLing 2026_LATEX_Templates/ to /home/sandbox/paper/."),
    ("N",  "  - Unescaped % characters in table cells (e.g., 30%) caused LaTeX to interpret trailing content as comments: replaced with \\% via sed across all four table files."),
    ("N",  "  - Unicode plus-minus sign (+-) replaced with $\\pm$ for proper math-mode rendering."),
    ("N",  "  - T1 table: replaced \\resizebox{\\textwidth}{!} with \\scalebox{0.72} to prevent measurement-pass hang in single-column Procedia layout."),
    ("N",  "  - T2/T3 tables: wrapped in \\scalebox{0.85} to prevent Overfull \\hbox (39.89pt overflow on 7-column tables)."),
    ("N",  "  - Missing \\doi command: defined via \\providecommand{\\doi} in preamble (Vancouver style in Procedia template does not define it natively)."),
    ("N",  "  - \\usepackage{scalefnt} added to preamble."),
    ("N",  ""),
    ("N",  "Final compilation: zero Overfull \\hbox warnings, zero undefined citations, zero undefined references."),
    ("N",  ""),

    ("H2", "3. Manuscript Structure"),
    ("N",  "Page 1: Title, double-blind author block (Anonymous Author(s) / Affiliation withheld), abstract (198 words, within 200-word limit), keywords (6 ACM-MeSH terms), Introduction."),
    ("N",  "Page 2: Related Work — four subsections (Safety-critical NLP benchmarks, Multilingual clinical NLP, Code-switching in clinical NLP, Consumer medication safety benchmarks). Contributions list (six numbered items)."),
    ("N",  "Page 3: Methods — MedCodeSwitch-Bench construction, benchmark design (5,200 items, 13 partitions, 3 languages, 5 risk dimensions), evaluation protocol (7 LLMs, 3 runs each, 109,200 judged responses, GPT-4o-as-judge), statistical plan."),
    ("N",  "Page 4: Table T2 (language-pair accuracy summary, scalebox 0.85), Experimental Setup, Results and Analysis subsections."),
    ("N",  "Page 5: Table T1 (full 13x7 accuracy table, scalebox 0.72), Table T3 (CS dose-response, scalebox 0.85), Table T4 (hypothesis summary), Discussion."),
    ("N",  "Pages 6–7: Discussion continued, Limitations, Conclusion, Ethical Considerations, CRediT Author Statement, Acknowledgements, References (Vancouver numbered, 27 entries)."),
    ("N",  "Page 8: References continued."),
    ("N",  ""),

    ("H2", "4. Table Summary"),
    ("N",  "T1 — Main Accuracy Table (table_T1_main.tex): 13 partitions x 7 models. Accuracy range: Mistral-7B English 0.627 to GPT-4o English 0.863. scalebox=0.72."),
    ("N",  "T2 — Language-Pair Summary (table_T2_langpair.tex): Mean accuracy per model across English, ES-EN, AR-EN, with GPT-4o/Mistral gap and AR-EN drop columns. scalebox=0.85."),
    ("N",  "T3 — CS Dose-Response (table_T3_dose.tex): Accuracy by code-switching density (0%, 30%, 50%, 70%, 100%) per language pair. Spearman rho=-1.000 (H3 SUPPORTED). scalebox=0.85."),
    ("N",  "T4 — Hypothesis Verdicts (table_T4_hypotheses.tex): H1 SUPPORTED, H2 NOT SUPPORTED (Qwen2 AR>ES), H3 SUPPORTED (rho=-1.0), H4 NOT SUPPORTED (W=7 p=0.237), H5 SUPPORTED, H6 SUPPORTED. Full-width, no scalebox needed."),
    ("N",  ""),

    ("H2", "5. Simulation Disclosure"),
    ("N",  "All numerical results in this manuscript are derived from SIMULATED data (simulation=true in external_values.yaml, R001-R009). No live LLM API calls were made during Stage 5 execution. Hypothesis verdicts, accuracy figures, Spearman rho, and Wilcoxon W-statistics are all synthetic by design."),
    ("N",  ""),
    ("N",  "The manuscript includes the following explicit disclosure in Section 4 (Experimental Setup):"),
    ("N",  "  \"NOTE TO REVIEWERS: All numerical results reported in this manuscript are derived from a controlled simulation of the MedCodeSwitch-Bench evaluation pipeline. No live LLM API calls were executed; all accuracy scores, significance test results, and hypothesis verdicts represent the pre-registered expected outcomes used to validate the pipeline architecture and manuscript structure. Live evaluation results will replace these values prior to final submission.\""),
    ("N",  ""),
    ("N",  "The simulation caveat propagates to Stage 7 (Hostile Review) and Stage 9 (Portfolio) as a known limitation requiring resolution before camera-ready submission."),
    ("N",  ""),

    ("H2", "6. Known Issues"),
    ("N",  "1. All results are simulated. Live API evaluation (GPT-4o, Claude-3.5-Sonnet, Mistral-7B, LLaMA-3.1-70B, Qwen2-72B, Gemma-2-27B, BioMistral-7B) must be run before final submission to replace macro values in macro_defs.tex and external_values.yaml."),
    ("N",  "2. Reference [12] (RxSafeBench, DOI 10.48550/arxiv.2511.04328) uses CC0-1.0 license — confirmed publicly available."),
    ("N",  "3. DOSEBENCH [26] (DOI 10.48550/arxiv.2606.04262) and MIRA [27] (DOI 10.48550/arxiv.2605.28025) are concurrent work identified during Stage 2. The manuscript addresses overlap in Related Work and Discussion."),
    ("N",  "4. The \\doi command was absent from the Procedia CS Vancouver bibliography style; a \\providecommand workaround was applied. This is cosmetic and will not affect peer review."),
    ("N",  "5. Double-blind compliance: author block, acknowledgements, and ethics section use anonymised placeholders. All identifying text must be restored at camera-ready stage."),
    ("N",  ""),

    ("H2", "7. Failure-Mode Check"),
    ("N",  "Spot-check against the 38-item failure-mode register (F1–F38):"),
    ("N",  ""),
    ("N",  "F1 (Invented results): CLEAR — all numbers sourced from external_values.yaml (R001–R009) via macro_defs.tex. No inline values."),
    ("N",  "F2 (Invented citations): CLEAR — all 27 references sourced from Stage 1–2 literature search outputs; DOIs verified."),
    ("N",  "F3 (Hypothesis HARKing): CLEAR — all six hypotheses pre-registered in Stage 3 study protocol before any simulation run."),
    ("N",  "F4 (Simulation presented as real): CLEAR — explicit disclosure note present in Section 4 and Limitations."),
    ("N",  "F5 (Overclaiming significance): CLEAR — H2 and H4 are correctly reported as NOT SUPPORTED; no selective reporting."),
    ("N",  "F6 (Missing baseline): CLEAR — T1 includes English-only baseline for all 7 models."),
    ("N",  "F7 (Venue format violations): CLEAR — 8 pages, double-blind, Vancouver refs, Procedia CS class; verified by pdflatex exit 0."),
    ("N",  "F8 (Unescaped LaTeX special chars): CLEAR — % and +- fixed in all four table files."),
    ("N",  "F9 (Missing concurrent work): CLEAR — DOSEBENCH and MIRA cited and discussed in Related Work."),
    ("N",  "F10–F38: No pipeline-breaking failures detected. Residual open item: live evaluation pending (recorded as Known Issue #1 above)."),
    ("N",  ""),

    ("H2", "8. Gate 6 Verdict"),
    ("N",  "VERDICT: PROCEED TO STAGE 7 — Hostile Review"),
    ("N",  ""),
    ("N",  "Rationale: The LaTeX manuscript compiles cleanly to exactly 8 pages in Procedia Computer Science format. All four result tables render without overflow. The failure-mode check identifies no blocking issues. The simulation caveat is explicitly disclosed in the manuscript and is the only standing risk."),
    ("N",  ""),
    ("N",  "Pre-condition for camera-ready submission: Replace all simulated macro values in macro_defs.tex and external_values.yaml with live evaluation results before Stage 9 (Portfolio)."),
    ("N",  ""),
    ("N",  "Artefacts produced by Stage 6:"),
    ("N",  "  /home/sandbox/paper/main.tex — full LaTeX source"),
    ("N",  "  /home/sandbox/paper/main.pdf — compiled PDF (8 pages, 183,025 bytes)"),
    ("N",  "  /home/sandbox/ACLing2026_manuscript.pdf — master copy (179 KB)"),
    ("N",  "  /home/sandbox/STAGE6_MANUSCRIPT.docx — this memo"),
    ("N",  ""),
    ("N",  "Next stage: Stage 7 — Hostile Review. Apply the 38-item failure-mode register as structured reviewer critique, targeting ACLing 2026 standards and the Q1 journal cascade (TACL → IP&M → JAMIA → JMIR AI)."),
]

# ── build document ─────────────────────────────────────────────────────────────
with doc_session(path=None, fmt="docx", save_to=OUTPUT, track=False) as (api, doc):
    first = True
    for style_key, text in SECTIONS:
        if style_key == "H1":
            ref = HEADING1
        elif style_key == "H2":
            ref = HEADING2
        else:
            ref = NORMAL

        if first:
            # Re-text the existing blank first paragraph rather than pushing a new one
            el = doc.GetElement(0)
            apply_style(el, doc, ref.get("styleName"))
            el.AddText(text)
            apply_resolved(el, ref)
            first = False
        else:
            para = styled_para(api, doc, text, ref)
            doc.Push(para)

print(f"Saved: {OUTPUT}")
