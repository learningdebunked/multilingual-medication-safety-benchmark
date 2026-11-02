#!/usr/bin/env python3
"""Create TACL_SUBMISSION_CHECKLIST.docx from blank."""
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


OUTPUT = "/home/sandbox/TACL_SUBMISSION_CHECKLIST.docx"


def push_heading(api, doc, text, level=1):
    para = api.CreateParagraph()
    para.AddText(text)
    st = doc.GetStyle(f"Heading {level}")
    if isinstance(st, docbuilder.CDocBuilderValue) and not (st.IsNull() or st.IsUndefined()):
        para.SetStyle(st)
    doc.Push(para)
    return para


def push_body(api, doc, text, bold=False, italic=False, color=None, indent=0):
    para = api.CreateParagraph()
    run = para.AddText(text)
    if bold:
        run.SetBold(True)
    if italic:
        run.SetItalic(True)
    if color:
        run.SetColor(color[0], color[1], color[2], False)
    if indent:
        para.SetIndLeft(indent)
    doc.Push(para)
    return para


def push_bullets(api, doc, items, checked_set=None):
    """Push a fresh bullet list for the given items.
    checked_set: set of item texts that are already done."""
    num = doc.CreateNumbering("bullet")
    lvl = num.GetLevel(0)
    checked_set = checked_set or set()
    for text in items:
        marker = "✅  " if text in checked_set else "☐  "
        para = api.CreateParagraph()
        para.AddText(marker + text)
        para.SetNumbering(lvl)
        doc.Push(para)


def set_cell(cell, text, bold=False, bg=None, fs=20):
    content = cell.GetContent()
    para = content.GetElement(0)
    run = para.AddText(text)
    run.SetFontSize(fs)
    if bold:
        run.SetBold(True)
    if bg:
        cell.SetShd("clear", bg[0], bg[1], bg[2])
    return para


HDR_BG = (68, 114, 196)
GREEN   = (0, 176, 80)
ORANGE  = (255, 192, 0)
RED_TXT = (192, 0, 0)
ORG_TXT = (192, 80, 0)
GRN_TXT = (0, 128, 0)


with doc_session(path=None, save_to=OUTPUT) as (api, doc):

    # ── TITLE ────────────────────────────────────────────────────────────────
    title = doc.GetElement(0)
    title.AddText("TACL Submission Checklist")
    tst = doc.GetStyle("Title")
    if isinstance(tst, docbuilder.CDocBuilderValue) and not (tst.IsNull() or tst.IsUndefined()):
        title.SetStyle(tst)
    title.SetJc("center")

    sub = api.CreateParagraph()
    r = sub.AddText(
        '"Lost in Translation, Lost in Safety: '
        'Benchmarking Multilingual LLMs for Consumer Medication Risk Understanding"'
    )
    r.SetItalic(True)
    r.SetFontSize(22)
    sub.SetJc("center")
    doc.Push(sub)

    jl = api.CreateParagraph()
    jr = jl.AddText(
        "Target: Transactions of the Association for Computational Linguistics (TACL) "
        "— Rolling Submission, SJR Q1"
    )
    jr.SetFontSize(20)
    jl.SetJc("center")
    doc.Push(jl)

    sl = api.CreateParagraph()
    sr = sl.AddText("Manuscript: main_tacl.pdf — 7 pages, A4, TACL-formatted, 0 LaTeX errors ✅")
    sr.SetFontSize(20)
    sr.SetColor(GRN_TXT[0], GRN_TXT[1], GRN_TXT[2], False)
    sl.SetJc("center")
    doc.Push(sl)

    doc.Push(api.CreateParagraph())

    # ── PART 1 — CRITICAL BLOCKERS ───────────────────────────────────────────
    push_heading(api, doc, "Part 1: Critical Pre-Submission Actions (Blockers)", 1)

    # C1
    push_heading(api, doc, "C1 — Replace Simulation Results with Live Experimental Data", 2)
    push_body(api, doc,
        "Priority: CRITICAL BLOCKER | All 9 result macros (R001–R009) are simulation=true. "
        "The paper cannot be submitted until live API results replace them.",
        bold=True, color=RED_TXT)
    push_bullets(api, doc, [
        "Run all 7 LLMs against all 5,200 benchmark items across 13 partitions (3 runs each)",
        "Estimated API cost: ~USD 300 (GPT-4o, Claude-3.5-Sonnet, GPT-4-Turbo, Gemini-1.5-Pro are most expensive)",
        "Update config/external_values.yaml: change all simulation: true → simulation: false; replace R001–R009",
        "Recompile all four result tables (table_T1_main.tex through table_T4_hypotheses.tex) with updated macros",
        "Re-run all six statistical tests (Wilcoxon, Friedman, Spearman/Jonckheere-Terpstra, McNemar × 2)",
        "Recompile main_tacl.pdf after all values verified",
    ])

    # C3
    push_heading(api, doc, "C3 — Correct LLM Judge Designation", 2)
    push_body(api, doc,
        "Priority: HIGH | Section 4.2 currently names GPT-4o as judge; the designated judge is Claude-3.5-Sonnet.",
        bold=True, color=ORG_TXT)
    push_bullets(api, doc, [
        "Update Section 4.2 in main_tacl.tex: change judge from GPT-4o to Claude-3.5-Sonnet (claude-3-5-sonnet-20241022)",
        "Update any other methodology text that references the judge model by name",
        "Review the AI Use Statement — update if it names the judge model",
        "Recompile and verify the change appears correctly in the PDF",
    ])

    # C4
    push_heading(api, doc, "C4 — Insert Real OSF Pre-Registration URL", 2)
    push_body(api, doc,
        "Priority: HIGH | tacl_refs.bib OSF2026 entry contains a placeholder note instead of a real DOI/URL.",
        bold=True, color=ORG_TXT)
    push_bullets(api, doc, [
        "Pre-register the study on OSF (https://osf.io) BEFORE beginning live data collection",
        "Record the OSF pre-registration DOI/URL assigned at registration",
        "Update tacl_refs.bib: replace placeholder note in OSF2026 entry with the real DOI",
        "Update any in-text reference to the pre-registration URL in Section 3 or Data Availability",
        "Recompile and confirm the citation resolves correctly",
    ])

    # C5
    push_heading(api, doc, "C5 — Human Fluency Validation", 2)
    push_body(api, doc,
        "Priority: HIGH | Longest-lead item (~2–4 weeks). Required for methodological credibility with TACL reviewers.",
        bold=True, color=ORG_TXT)
    push_bullets(api, doc, [
        "Recruit >= 30 bilingual raters per language pair (Spanish-English, Arabic-English)",
        "Design 5-point Likert scale fluency rating instrument for code-switched prompts",
        "Administer annotation task (recommend Prolific or comparable crowdsourcing platform)",
        "Calculate inter-rater reliability: Krippendorff's alpha or intraclass correlation coefficient (ICC)",
        "Add reliability scores to Section 3.3 (Dataset Construction) or a new Appendix section",
        "Update main_tacl.tex with human validation results before submission",
    ])

    # C7
    push_heading(api, doc, "C7 — Re-run H3 with Jonckheere-Terpstra Test", 2)
    push_body(api, doc,
        "Priority: HIGH | Simulation artifact: Spearman rho = -1.000 will not be credible to reviewers.",
        bold=True, color=ORG_TXT)
    push_bullets(api, doc, [
        "After C1: re-run H3 using the Jonckheere-Terpstra test (ordered alternative to Kruskal-Wallis)",
        "Replace rho = -1.000 with the live J-T test statistic and p-value",
        "Update \\HThreeRho macro in macro_defs.tex with the live value",
        "Update H3 verdict text in Section 5.3 and Table T4 (Hypothesis Test Summary)",
        "Revise H3 discussion in Section 6 to reflect the actual test outcome",
    ])

    # ── PART 2 — NON-BLOCKING ────────────────────────────────────────────────
    push_heading(api, doc, "Part 2: Non-Blocking Pre-Submission Actions", 1)

    push_heading(api, doc, "C2 — Abstract Accuracy Value [COMPLETE]", 2)
    push_body(api, doc,
        "✅  Corrected: 0.386 → 0.370 (Mistral-7B worst-case AR-EN 70% Intra accuracy). No further action required.",
        color=GRN_TXT)

    push_heading(api, doc, "C6 — Unused BibTeX Entry (VuEtAl2022)", 2)
    push_body(api, doc,
        "Priority: LOW | Decision required. VuEtAl2022 exists in tacl_refs.bib but is not cited in main_tacl.tex.")
    push_bullets(api, doc, [
        "OPTION A: Cite VuEtAl2022 — add to Section 2 Related Work with a sentence on Vietnamese medication NLP",
        "OPTION B: Remove VuEtAl2022 from tacl_refs.bib entirely (BibTeX only warns for uncited entries, does not error)",
        "Decision: choose one option and implement before submission",
    ])

    # ── PART 3 — BIBTEX CLEANUP ──────────────────────────────────────────────
    push_heading(api, doc, "Part 3: BibTeX / References Clean-Up", 1)
    push_body(api, doc,
        "TACL prohibits 'et al.' abbreviations in the reference list. "
        "The 11 entries below currently use shortened author lists and must be expanded "
        "to full author lists before camera-ready (strongly recommended before submission):")
    push_bullets(api, doc, [
        "Zhao2025 — expand to full author list",
        "Wu2025 — expand to full author list",
        "Li2024 — expand to full author list",
        "Xu2026 — expand to full author list",
        "Wang2023 — expand to full author list",
        "Alghamdi2024 — expand to full author list",
        "Onyame2026 — expand to full author list",
        "SwitchLingua2025 — expand to full author list",
        "OpenAI2024 — expand to full author list (or use standard tech-report format)",
        "Meta2024 — expand to full author list (or use standard tech-report format)",
        "Sun2022 — expand to full author list",
    ])

    # ── PART 4 — PDF PROPERTIES ──────────────────────────────────────────────
    push_heading(api, doc, "Part 4: PDF & Document Properties", 1)

    push_heading(api, doc, "Remove Author Metadata from PDF [Anonymity Requirement]", 2)
    push_bullets(api, doc, [
        "Check metadata: pdfinfo main_tacl.pdf | grep -i author",
        "If names present: exiftool -Author=\"\" -Creator=\"\" -Producer=\"\" main_tacl.pdf",
        "Re-verify: pdfinfo main_tacl.pdf | grep -i author (must return empty)",
        "Check title, subject, and keywords fields for identifying information",
    ])

    push_heading(api, doc, "Add Keywords for TACL Submission Portal", 2)
    push_body(api, doc, "Enter 5–10 keywords in the 'Comments to Editor' field at submission. Suggested:")
    push_body(api, doc,
        "multilingual NLP, medication safety, code-switching, large language models, benchmarking, "
        "patient safety, health literacy, low-resource languages, LLM evaluation, consumer health informatics",
        italic=True, indent=720)
    push_bullets(api, doc, [
        "Enter keywords in the TACL submission portal 'Comments to Editor' field before submitting",
    ])

    # ── PART 5 — FORMATTING VERIFICATION TABLE ───────────────────────────────
    push_heading(api, doc, "Part 5: Formatting Verification (TACL Requirements)", 1)

    fmt_tbl = api.CreateTable(1, 3)
    fmt_tbl.SetWidth("percent", 100)
    fmt_tbl.SetTableBorderAll("single", 4, 0, 180, 180, 180)

    hrow = fmt_tbl.GetRow(0)
    hrow.SetTableHeader(True)
    set_cell(hrow.GetCell(0), "Requirement", bold=True, bg=HDR_BG)
    set_cell(hrow.GetCell(1), "Status",      bold=True, bg=HDR_BG)
    set_cell(hrow.GetCell(2), "Notes",        bold=True, bg=HDR_BG)

    fmt_rows = [
        ("Anonymous submission mode (\\usepackage[]{})",       "PASS",   "Correct for pre-submission; switch to acceptedWithA on camera-ready"),
        ("Line numbers in both margins",                        "PASS",   "Verified pages 1-7"),
        ("Two-column layout",                                   "PASS",   "TACL standard format"),
        ("A4 paper (595.3 x 841.9 pt)",                        "PASS",   "Verified in compile log"),
        ("natbib: \\citet{} / \\citep{}",                      "PASS",   "All citations converted from \\cite{}"),
        ("Full-width tables (table* environment)",              "PASS",   "All four result tables fixed (T1-T4)"),
        ("Zero overfull hbox errors",                           "PASS",   "Verified in final pdflatex log"),
        ("Zero undefined citations",                            "PASS",   "22/22 tacl_refs.bib entries resolved"),
        ("TACL header: Confidential TACL submission",           "PASS",   "Verified page 1"),
        ("Abstract word count <= 250 words",                    "VERIFY", "Manually count or use texcount on abstract"),
        ("Page limit <= 8 pages (excl. references)",            "VERIFY", "Currently 7 pages — re-check after C1 live results"),
        ("ACL Anthology reference format",                      "PASS",   "acl_natbib.bst used throughout"),
        ("No author names in PDF (anonymous mode active)",      "PASS",   "Anonymous TACL submission placeholder set"),
    ]

    for req, status, notes in fmt_rows:
        row = fmt_tbl.AddRow()
        bg_status = GREEN if status == "PASS" else ORANGE
        set_cell(row.GetCell(0), req)
        set_cell(row.GetCell(1), status, bold=True, bg=bg_status)
        set_cell(row.GetCell(2), notes)

    doc.Push(fmt_tbl)

    # ── PART 6 — CAMERA-READY ────────────────────────────────────────────────
    push_heading(api, doc, "Part 6: Camera-Ready Actions (Post-Acceptance Only)", 1)
    push_body(api, doc,
        "Do NOT perform these steps before acceptance — they de-anonymize the manuscript.",
        italic=True, color=RED_TXT)
    push_bullets(api, doc, [
        "Change \\usepackage[]{tacl2021v1} to \\usepackage[acceptedWithA]{tacl2021v1} in main_tacl.tex",
        "Line numbers are automatically removed by acceptedWithA mode — verify after recompile",
        "Insert real author names, affiliations, email addresses (replace Anonymous placeholder)",
        "Add funding acknowledgements, IRB approval number, and grant numbers to Acknowledgements section",
        "Expand all 11 [EXPAND] BibTeX entries to full author lists (see Part 3)",
        "Final proofread against TACL camera-ready instructions at https://transacl.org/",
        "Confirm PDF title matches the accepted manuscript title exactly",
    ])

    # ── PART 7 — TIMELINE TABLE ──────────────────────────────────────────────
    push_heading(api, doc, "Part 7: Estimated Pre-Submission Timeline", 1)

    tl_tbl = api.CreateTable(1, 4)
    tl_tbl.SetWidth("percent", 100)
    tl_tbl.SetTableBorderAll("single", 4, 0, 180, 180, 180)

    thr = tl_tbl.GetRow(0)
    thr.SetTableHeader(True)
    for i, hdr in enumerate(["Action", "Effort", "Dependency", "Parallelize?"]):
        set_cell(thr.GetCell(i), hdr, bold=True, bg=HDR_BG)

    tl_rows = [
        ("C4: OSF pre-registration",                    "1–2 hours",  "Must precede data collection", "Yes — do first"),
        ("C1: Live API runs (7 models x 5,200 items)",  "2–3 days",   "Budget approval",              "No — sequential"),
        ("C3: Update judge designation",                "30 min",     "None",                          "Yes — with C4, C6"),
        ("C5: Human validation (30+ raters)",           "2–4 weeks",  "None",                          "Yes — start immediately"),
        ("C7: Jonckheere-Terpstra re-run",              "1–2 hours",  "C1 must be complete",           "No"),
        ("C6: Cite or remove VuEtAl2022",               "30 min",     "None",                          "Yes"),
        ("Part 3: BibTeX expansion (11 entries)",       "2–4 hours",  "None",                          "Yes"),
        ("Part 4: PDF metadata clean-up",               "15 min",     "None",                          "Yes"),
        ("Final recompile and verify",                  "1 hour",     "C1, C3, C4, C7 complete",       "No — last step"),
        ("TOTAL (critical path, dominated by C5)",      "~3–4 weeks", "Start C5 immediately",          ""),
    ]
    for row_data in tl_rows:
        row = tl_tbl.AddRow()
        for i, txt in enumerate(row_data):
            set_cell(row.GetCell(i), txt)

    doc.Push(tl_tbl)

    # ── FINAL WARNING ────────────────────────────────────────────────────────
    doc.Push(api.CreateParagraph())
    warn = api.CreateParagraph()
    wr = warn.AddText(
        "IMPORTANT: All simulation results carry simulation=true in config/external_values.yaml. "
        "The manuscript must not be submitted until C1 is complete and all macros (R001–R009) "
        "are updated with live experimental results."
    )
    wr.SetBold(True)
    wr.SetColor(RED_TXT[0], RED_TXT[1], RED_TXT[2], False)
    warn.SetJc("both")
    doc.Push(warn)

print("Done:", OUTPUT)
