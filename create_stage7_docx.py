#!/usr/bin/env python3
"""Stage 7 Hostile Review DOCX — create pass (track=False, from-blank)."""
from __future__ import annotations
import contextlib, os, re, shutil
import docbuilder

TRACK_AUTHOR = "Scispace Agent"
KNOWN_BINDING_GAPS = frozenset({
    "MoveCursorTo","EnterText","InsertBlankPage","GoToPage",
    "SelectCurrentWord","RemoveSelection",
})

class BindingGapError(AttributeError): pass

def ext(v):
    if not isinstance(v, docbuilder.CDocBuilderValue): return v
    if v.IsNull() or v.IsUndefined(): return None
    if v.IsBool():   return v.ToBool()
    if v.IsInt():    return v.ToInt()
    if v.IsDouble(): return v.ToDouble()
    if v.IsString(): return v.ToString()
    if v.IsArray():  return [ext(v[i]) for i in range(ext(v.GetLength()))]
    return v

def safe_call(obj, method, *args):
    try: return getattr(obj, method)(*args)
    except AttributeError: pass
    try: return obj.Call(method, *args)
    except AttributeError as e:
        hint = "known binding gap" if method in KNOWN_BINDING_GAPS else "binding gap"
        raise BindingGapError(f"{method}: {hint}") from e

def backup_once(path):
    bak = path + ".bak"
    if not os.path.exists(bak): shutil.copy(path, bak)
    return bak

@contextlib.contextmanager
def doc_session(path=None, fmt="docx", save_to=None, track=False):
    builder = docbuilder.CDocBuilder()
    if path: builder.OpenFile(path, "")
    else:    builder.CreateFile(fmt)
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
    if not style_name: return
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

# ── Style refs (from STAGE5 doc_style.json) ─────────────────────────────────
H1  = {"styleName":"Heading 1","resolvedRun":{"sizeHalfPt":40,"font":"Arial"},
       "resolved":{"spacing_before":"360","spacing_after":"80"}}
H2  = {"styleName":"Heading 2","resolvedRun":{"sizeHalfPt":32,"font":"Arial"},
       "resolved":{"spacing_before":"160","spacing_after":"80"}}
H3  = {"styleName":"Heading 3","resolvedRun":{"sizeHalfPt":28,"font":"Arial"},
       "resolved":{"spacing_before":"120","spacing_after":"60"}}
NRM = {"styleName":"Normal","resolvedRun":{"sizeHalfPt":22,"font":"Arial"},
       "resolved":{"spacing_before":"0","spacing_after":"200"}}
OUTPUT = "/home/sandbox/STAGE7_HOSTILE_REVIEW.docx"

# ── Document content ─────────────────────────────────────────────────────────
CONTENT = [
# (style_key, text)
("H1","Stage 7 — Hostile Review"),
("N","Project: Lost in Translation, Lost in Safety: Benchmarking Multilingual LLMs for Consumer Medication Risk Understanding"),
("N","Date: 2026-10-29"),
("N","Stage: 7 of 9 — Hostile Peer Review"),
("N","Status: COMPLETE"),
("N","Gate Verdict: CONDITIONAL PROCEED TO STAGE 8 — critical revisions required before live submission"),
("N",""),

("H2","1. Overview"),
("N","This stage applies a structured hostile review of the ACLing 2026 manuscript (main.tex, compiled to ACLing2026_manuscript.pdf, 8 pages). The review panel simulates three adversarial reviewers representing distinct critical angles: methodology, statistical rigor, and clinical safety. A meta-review synthesises their verdicts. Sections 6 and 7 apply the 38-item failure-mode register (F1-F38) and generate a ranked revision priority matrix. The final Gate 7 verdict is issued at Section 8."),
("N",""),
("N","The single overriding concern is that ALL empirical results are simulated (simulation=true in external_values.yaml, R001-R009). This is the non-negotiable pre-condition: the manuscript CANNOT be submitted in its current state. It must be refactored as a 'benchmark description with pilot evaluation' paper or all live results must be filled in before submission."),
("N",""),

# ═══════════════════════════════════════════════════════════════════════════
("H2","2. Reviewer 1 — Benchmark Methodology and Validity"),
("N","[Simulated profile: Senior NLP researcher specialising in benchmark creation and multilingual evaluation. Associate Editor at TACL. Known for requiring reproducible, human-validated benchmarks.]"),
("N",""),
("H3","2.1 Summary"),
("N","This paper presents a potentially important benchmark for multilingual medication safety evaluation. The research question is well-motivated: bilingual consumers do use code-switched queries in health contexts, and existing benchmarks are English-only. However, the submitted manuscript has a fundamental problem that precludes acceptance in its current form: no real evaluation results exist. Every accuracy figure, hypothesis verdict, and comparative claim is derived from a simulation using 'literature-informed performance priors.' This is not a paper reporting experimental findings — it is a proposal document formatted as an empirical paper. I cannot recommend acceptance under these conditions."),
("N",""),
("H3","2.2 Critical Concerns (Rejection-Level)"),
("N","RC1 [Simulated Results]: The entire Results section, all four tables, all six hypothesis verdicts, and the Discussion are based on simulated data. The paper discloses this, but disclosure does not remedy the problem. A conference paper claiming 'GPT-4o outperforms Mistral-7B by 0.301 accuracy points on ES-EN code-switched inputs' must be based on real measurements. The simulation caveats appended to every table value (dagger symbols) do not mitigate the fundamental validity concern. No program committee should accept empirical claims without empirical support."),
("N",""),
("N","RC2 [CS Generation Validity]: The code-switching generation pipeline uses a word-level substitution dictionary of approximately 250 Spanish and 250 Arabic entries. This approach does not produce linguistically valid code-switching. Real bilingual code-switching obeys the Matrix Language Frame (Myers-Scotton 1993) and the Equivalence Constraint (Poplack 1980): switching occurs at syntactic boundaries where both languages share surface structure. A 250-entry substitution dictionary applied independently to sentence positions will routinely violate morphological agreement (e.g., substituting 'pastilla' for 'pill' without adjusting determiners or verb agreement), produce ungrammatical mixed sentences, and generate text that native bilingual speakers would not produce or recognise as natural. The paper defers human fluency validation to camera-ready — this validation should have been completed before submission. Without it, the benchmark items may be invalid stimuli that measure response to garbled text rather than to natural code-switching."),
("N",""),
("N","RC3 [OSF Pre-Registration Pending]: The paper states that OSF pre-registration is 'pending.' If hypotheses are pre-registered after the simulation results are known (even if the simulation is a proxy), this constitutes HARKing (Hypothesizing After Results are Known). The authors must provide a dated OSF pre-registration URL that predates any data collection or simulation run."),
("N",""),
("H3","2.3 Major Concerns"),
("N","MC1 [Sample Size Justification]: Only 400 items are drawn from the 2,443 available RxSafeBench scenarios. The authors provide no justification for this restriction. Using only 17% of available data when the full dataset is CC0-licensed and freely available raises questions about whether the 400-item sample is representative. A stratified power analysis is given (>0.99 power at N=400), but this does not address representativeness across indication types."),
("N",""),
("N","MC2 [GPT-4o Self-Evaluation Bias]: GPT-4o is used as the evaluation judge and is simultaneously one of the seven models under evaluation. This creates a circular dependency: GPT-4o assigns scores to its own responses. The authors do not address this conflict. Prior work has documented that LLM judges tend to favour their own generation style, which could inflate GPT-4o's accuracy relative to other models. The paper should use a held-out judge model (e.g., Claude-3.5-Sonnet) or a rule-based judge for all models, or at minimum report sensitivity to judge choice."),
("N",""),
("N","MC3 [Contributions Item 5 Is a Result, Not a Contribution]: Contribution bullet 5 ('An unexpected safety advantage for Arabic-trained models') describes an experimental finding, not a methodological contribution. This conflation weakens the contributions list. Results should be reported in the Results section, not positioned as design contributions."),
("N",""),
("H3","2.4 Minor Concerns"),
("N","mn1: The model abbreviations in Table T1 header (GPT-4-T, Gemini-1.5, LLaMA-3.1, Mistral-7B) truncate differently than the full names in the text. Readers unfamiliar with the landscape may be confused."),
("N","mn2: Reference [VuEtAl2022] (described as BLOOM, Vu et al. 2022) is listed in the bibliography but does not appear to be cited anywhere in the body text. This orphaned reference should be removed or cited."),
("N","mn3: The paper's conclusion says 'Benchmark data, generation code, and evaluation harness are released' but provides no GitHub URL. Double-blind review is the stated reason, but a placeholder anonymised repository URL (e.g., anonymous.4open.science) is standard practice and allows reviewers to assess reproducibility."),
("N",""),
("H3","2.5 Preliminary Recommendation"),
("N","REJECT at current ACLing 2026 deadline. Major revision required. The paper has a clear and interesting research direction. With live evaluation results, proper human CS fluency validation, and OSF pre-registration, it would be a strong submission to ACL/EMNLP/NAACL or TACL."),
("N",""),

# ═══════════════════════════════════════════════════════════════════════════
("H2","3. Reviewer 2 — Statistical Rigor and Experimental Design"),
("N","[Simulated profile: Computational linguist and statistician. Expert in evaluation methodology for NLP benchmarks. EMNLP area chair.]"),
("N",""),
("H3","3.1 Summary"),
("N","The experimental design is methodologically sound in structure: six pre-registered hypotheses, Bonferroni correction, three evaluation runs, inter-annotator agreement protocol. These are commendable practices. However, the paper presents several numerical results that are statistically impossible or implausible given real data, and which immediately signal simulation origin to an informed reviewer. The statistical plan also has an internal inconsistency regarding H3. I recommend major revision contingent on replacement of all simulated results with real experimental data."),
("N",""),
("H3","3.2 Critical Concerns"),
("N","RC1 [Spearman rho = -1.000 is Implausible]: The paper reports Spearman rho = -1.000 (p < 0.001) for the CS dose-response across all seven models. A perfect monotone correlation of -1.000 would require every single model to rank the four CS intensity tiers (0%, 30%, 50%, 70%) in strictly decreasing order of accuracy with no tied ranks. In real evaluation data with three evaluation runs per condition, sampling variance would virtually guarantee at least one tie or rank inversion. A Spearman rho of exactly -1.000 to three decimal places is a simulation artifact and will be immediately recognised as such by statistical reviewers. The camera-ready version will almost certainly show rho in the range -0.85 to -0.99 rather than exactly -1.000, and the claim of 'perfect monotone dose-response' should be softened accordingly."),
("N",""),
("N","RC2 [Cohen's kappa = 1.000 for IAA]: The paper reports Cohen's kappa = 1.000 for inter-annotator agreement between 'run43' and 'run44' of the GPT-4o judge. The limitations section correctly notes this is a simulation artefact. However, this value appears in the results pipeline as if it were a real IAA measurement. The protocol requires kappa >= 0.75 to proceed. If real pharmacist annotation produces kappa < 0.75, the entire evaluation validity is at risk. The paper should report IAA as pending and not claim compliance with the kappa threshold."),
("N",""),
("N","RC3 [H3 Statistical Test Inconsistency]: The pre-registered statistical plan for H3 specifies the Jonckheere-Terpstra ordered trend test, but the Results section reports only Spearman rho. The statistical plan section (Section 4) mentions both 'Jonckheere-Terpstra (H3)' and 'Spearman correlation (H3, dose-response)' — it is unclear whether both tests were run (and if so, whether the Jonckheere-Terpstra result is consistent with the Spearman result), or whether the pre-registered test was silently replaced. A deviation from the pre-registered analysis plan must be explicitly declared."),
("N",""),
("H3","3.3 Major Concerns"),
("N","MC1 [Abstract vs Table Numerical Inconsistency]: The abstract states 'the highest CS intensity drives Mistral-7B accuracy to 0.386.' Table T1 shows that Mistral-7B's ES-EN 70% Intra accuracy is 0.3858 (approximately 0.386), but the worst-case partition is AR-EN 70% Intra at 0.3700. The body text correctly identifies 0.370 as the worst case, but the abstract cites 0.386. This is a factual inconsistency between the abstract and the detailed results. The abstract should cite 0.370 (the true minimum), or the body text should be corrected."),
("N",""),
("N","MC2 [Bonferroni Correction Applied Incorrectly to H3 Reference]: Section 4 states the family-wise error rate is controlled at alpha/k = 0.05/6 = 0.0083. However, H3 appears to use a separate Spearman rho with p < 0.001 comparison, not an explicit alpha = 0.0083 threshold. The paper should clarify which test (Jonckheere-Terpstra or Spearman) corresponds to the pre-registered H3 and report the exact p-value against the Bonferroni threshold."),
("N",""),
("N","MC3 [No Confidence Intervals for Key Claims]: The paper reports mean accuracy +/- standard deviation across three runs. For key comparative claims (e.g., 'GPT-4o outperforms Mistral-7B by 0.301 accuracy points on CS inputs'), confidence intervals or significance tests for the gap should be reported. A 0.301 difference could be consistent with substantial overlap in the full score distributions."),
("N",""),
("H3","3.4 Minor Concerns"),
("N","mn1: The paper says 'This set spans five orders of magnitude in parameter count (~7B-~1.8T).' GPT-4o's 1.8T parameter count is an unverified estimate from a non-official source. The paper should cite the source of this estimate or use a conservative phrasing like 'estimated ~200B-~1.8T.'"),
("N","mn2: Table T4 reports Wilcoxon W=7 for H4 (p=0.237, not significant). With only 7 models, the Wilcoxon signed-rank test has very limited power (N=7 pairs gives a minimum achievable p-value of ~0.016 under one-tailed). This should be noted as a power limitation."),
("N","mn3: Three evaluation runs (seeds 43, 44, 45) is the minimum for variance estimation. For closed-API models with temperature=0 (deterministic), multiple runs are unnecessary and the variance will be near-zero. The runs are more meaningful for open-weight models with sampling. The paper should clarify which models are run deterministically vs. stochastically."),
("N",""),
("H3","3.5 Preliminary Recommendation"),
("N","MAJOR REVISION. Replace all simulated results with real experimental data. Resolve the H3 statistical test inconsistency. Fix the abstract vs. table numerical discrepancy. With these changes, the statistical design is strong and the paper would merit acceptance."),
("N",""),

# ═══════════════════════════════════════════════════════════════════════════
("H2","4. Reviewer 3 — Clinical Relevance and Consumer Safety"),
("N","[Simulated profile: Clinical pharmacist and health informatics researcher. Published in JAMIA, Journal of Medical Internet Research. Concerned with real-world applicability and patient safety claims.]"),
("N",""),
("H3","4.1 Summary"),
("N","The paper addresses a genuinely important gap: most multilingual health LLM evaluations test monolingual non-English inputs, not the code-switching patterns characteristic of real bilingual patient communication. The motivation is compelling and the research design is clinically informed. My major concerns are about the framing of safety claims in the absence of real data, the validity of the source dataset for consumer (rather than clinical) contexts, and the narrow Arabic dialect coverage."),
("N",""),
("H3","4.2 Critical Concerns"),
("N","RC1 [Safety Claims Without Real Data]: The paper makes clinical safety claims in the Abstract, Introduction, and Discussion ('clinically meaningful safety risk,' 'clinically consequential,' 'equity concerns') that are entirely based on simulation. A paper that describes 'clinically meaningful safety risk' from a medication error perspective must be grounded in actual measurements. A simulation that was designed to produce declining accuracy with increasing CS ratio (the 'literature-informed prior') will by construction support the hypothesis that CS degrades safety. The simulation thus cannot independently validate the clinical significance of the effect. Statements like 'At the highest CS intensity, even GPT-4o's accuracy falls below 0.75 on AR-EN queries' should be presented as hypothesised outcomes rather than established findings."),
("N",""),
("N","RC2 [RxSafeBench is a Clinical, Not Consumer, Dataset]: The paper claims to benchmark 'consumer medication risk understanding' but the source dataset (RxSafeBench) comprises 'simulated patient-pharmacist consultation scenarios' — a clinical consultation register, not consumer self-medication queries. The language register of a patient-pharmacist consultation is considerably more formal than the informal, often abbreviated queries a consumer would type into a health chatbot. The 400-item English base corpus inherits this register mismatch. The consumer-register framing in the title and throughout the paper is not supported by the source data."),
("N",""),
("H3","4.3 Major Concerns"),
("N","MC1 [Arabic Dialect Scope is Under-Specified]: The paper states that AR-EN partitions use 'Modern Standard Arabic (MSA) with Gulf dialect markers.' However, the specific dialect markers, their prevalence in the 250-entry dictionary, and the validation process for Arabic naturalness are not described. MSA is not the primary spoken dialect of most Arabic-speaking communities in the US (the primary target population): Egyptian Arabic, Levantine Arabic, and Maghrebi Arabic are more common. The paper should either restrict its scope to MSA explicitly or demonstrate coverage of the most prevalent US Arabic dialects."),
("N",""),
("N","MC2 [Evaluation Metric Does Not Capture Safety-Relevant Errors]: The paper uses binary accuracy (score=1 if the correct safe drug is named). This metric treats all errors as equivalent regardless of the clinical severity of the mistake. A model that confuses two safe alternatives is equally penalised to one that recommends a contraindicated drug causing life-threatening harm. For a paper framing its contribution in terms of patient safety, a severity-weighted error metric (e.g., differentiating 'safe-but-wrong' from 'contraindicated-drug recommendation') would be far more clinically meaningful."),
("N",""),
("N","MC3 [Missing Baseline: Human Performance]: The paper evaluates seven LLMs but does not compare them against a human baseline (e.g., a naive lay consumer attempting the same task). Without a human ceiling/floor, it is impossible to contextualise whether a 0.863 GPT-4o English accuracy is impressive, adequate, or dangerously low for a consumer safety task. A 0.370 worst-case accuracy for Mistral-7B on AR-EN at high CS density is alarming — but alarming relative to what? If lay consumers also perform at 0.4 on these scenarios, the LLM may not represent a net safety degradation."),
("N",""),
("H3","4.4 Minor Concerns"),
("N","mn1: The paper's Ethical Considerations section is anonymised ('omitted for double-blind review'). The actual section should address: IRB status for human annotation, data licensing for the training data of closed models, and the dual-use risk of publishing a benchmark that could be used to train models that exploit CS for adversarial medical prompting."),
("N","mn2: The Generative AI Use Statement discloses that Claude-3.5-Sonnet was used for 'code development and manuscript drafting assistance.' For a paper evaluated at a venue with an ACM-style AI disclosure policy, this statement should be more specific about which manuscript sections involved AI assistance."),
("N","mn3: The paper's title says 'Consumer Medication Risk Understanding.' 'Risk understanding' is broader than 'safety classification.' The evaluation task (identify the safe vs. contraindicated drug) is more precisely 'contraindication detection' or 'drug-drug interaction identification.' The title overclaims the scope."),
("N",""),
("H3","4.5 Preliminary Recommendation"),
("N","MAJOR REVISION contingent on real evaluation results and reframing clinical safety claims as hypothesised outcomes until empirically validated. The register mismatch (clinical vs. consumer) should be addressed either by reframing the paper as a clinical consultation safety benchmark or by supplementing with genuinely consumer-register queries."),
("N",""),

# ═══════════════════════════════════════════════════════════════════════════
("H2","5. Meta-Review and Editorial Decision"),
("N","The three reviewers independently converged on the same rejection-level concern: all results are simulated. R1 flags this as a validity issue, R2 flags it as a statistical implausibility issue, and R3 flags it as a clinical credibility issue. There is no path to acceptance at ACLing 2026 (deadline: 5 November 2026) with simulated results."),
("N",""),
("N","Beyond the simulation issue, the reviewers surface four additional concerns with consensus across at least two reviewers:"),
("N","  (a) CS generation methodology relies on minimal word-level substitution without human validation (R1, R3)."),
("N","  (b) GPT-4o serves as both evaluated model and judge (R1, R2)."),
("N","  (c) Clinical safety claims are not calibrated to the actual severity of errors (R2, R3)."),
("N","  (d) OSF pre-registration must precede any data collection or simulation (R1, R2)."),
("N",""),
("N","EDITORIAL DECISION: REJECT for ACLing 2026 as-is. The paper is a strong candidate for ACL/EMNLP/NAACL 2027 or TACL (rolling submission) once live evaluation results are obtained."),
("N",""),
("N","The paper's conceptual contribution — the first benchmark systematically studying CS-induced safety degradation in medication queries — is novel and clinically significant. The methodology is well-designed. The revision path is clear but requires substantial time: running live API evaluations, validating CS generation with human annotators, and completing OSF pre-registration."),
("N",""),

# ═══════════════════════════════════════════════════════════════════════════
("H2","6. Failure-Mode Register Audit (F1-F38)"),
("N","Status key: CLEAR = no issue detected | FLAGGED = blocking issue | AMBER = non-blocking but requires action | N/A = not applicable"),
("N",""),
("H3","6.1 Data and Results Integrity"),
("N","F1 [Invented results]: FLAGGED. All numerical results derive from simulation. They are disclosed as such in the manuscript, but the simulation was designed to produce the expected direction of results, which makes independent validation impossible. Resolution: replace with live API evaluation results."),
("N","F2 [Invented citations]: CLEAR. All 23 cited references can be traced to real papers with verifiable DOIs or institutional URLs. No citation appears fabricated."),
("N","F3 [HARKing — hypotheses post-hoc]: AMBER. Hypotheses are stated to be pre-registered (OSF), but the URL is listed as '[URL to be added in camera-ready version].' Until a dated OSF pre-registration URL is provided, the pre-registration claim cannot be verified and the HARKing risk cannot be ruled out. Resolution: file OSF pre-registration immediately; do not run any live evaluation until the OSF timestamp is confirmed."),
("N","F4 [Simulation presented as real]: FLAGGED. The manuscript discloses simulation status via dagger footnotes on every table value, a bold disclosure note in Section 4, and explicit statements in the Limitations section. This is good practice. However, the abstract, contributions, discussion, and conclusion discuss results in the present tense as if empirically established, without dagger flags. Resolution: reframe all results in the abstract and conclusion as 'simulated outcomes consistent with hypothesised effects' rather than established findings."),
("N","F5 [Overclaiming significance]: FLAGGED. The abstract and conclusion make strong causal claims ('CS ratio drives a near-perfect monotone dose-response,' 'training corpus language composition is a key design parameter') that are entirely based on simulation. The simulation was designed to produce these outcomes; it cannot validate them. Resolution: reframe as predictions or expected findings pending live evaluation."),
("N","F6 [Missing English baseline]: CLEAR. Table T1 includes a dedicated English (0% CS) row for all 7 models. Baseline coverage is complete."),
("N","F7 [Venue format violations]: CLEAR. Manuscript compiles to exactly 8 pages in Procedia Computer Science format. Double-blind author block confirmed. Vancouver references numbered correctly."),
("N","F8 [Unescaped LaTeX special chars]: CLEAR. All percent signs and plus-minus symbols corrected during Stage 6 compilation."),
("N","F9 [Missing concurrent work]: CLEAR. DOSEBENCH and MIRA are cited and distinguished in the Related Work section. CURE-Med is also cited and differentiated."),
("N",""),
("H3","6.2 Methodology and Statistical Integrity"),
("N","F10 [Orphaned references]: FLAGGED. Reference [VuEtAl2022] (Vu et al. 2022, BLOOM) is listed in the bibliography but does not appear to be cited anywhere in the manuscript body text. This will generate a LaTeX warning and may confuse readers. Resolution: either cite this reference in the Related Work section or remove it."),
("N","F11 [Abstract vs table numerical inconsistency]: FLAGGED. Abstract states Mistral-7B's minimum accuracy is 0.386; Table T1 shows the true minimum is 0.370 (AR-EN 70% Intra). The 0.386 value corresponds to ES-EN 70% Intra (0.3858), not the worst case. Resolution: correct the abstract to state 0.370 or 0.386 consistently and accurately."),
("N","F12 [H3 statistical test inconsistency]: AMBER. Pre-registered test for H3 is Jonckheere-Terpstra; results section reports Spearman rho. Section 4 mentions both tests for H3. Resolution: report both J-T and Spearman results, or declare the deviation from pre-registration if Spearman replaced J-T."),
("N","F13 [Judge-model conflict of interest]: FLAGGED. GPT-4o is used as evaluation judge and is simultaneously one of the seven evaluated models. Potential self-assessment inflation. Resolution: use a different judge model for evaluating GPT-4o responses (e.g., Claude-3.5-Sonnet), or use a purely rule-based judge for all models."),
("N","F14 [Simulated IAA, kappa=1.000]: FLAGGED. Cohen's kappa = 1.000 is a simulation artifact. The protocol requires kappa >= 0.75 for real pharmacist vs. judge agreement. Until real human annotation is completed and kappa is verified, the evaluation quality claim cannot be substantiated. Resolution: defer IAA report to camera-ready; do not report kappa=1.000 as a validated quality metric."),
("N","F15 [Sample size not justified]: AMBER. 400 items drawn from 2,443 available without explicit sampling rationale beyond power analysis. A 400-item sample may not be representative across all 538 indication types in RxSafeBench. Resolution: justify sample size choice; consider using stratified sampling with explicit coverage targets per indication type."),
("N","F16 [CS generation linguistic validity not validated]: FLAGGED. Word-level substitution with 250-entry bilingual dictionaries. No morphological agreement, no syntactic constraint checking, no human fluency validation prior to submission. Resolution: conduct human fluency validation (5-point Likert, N >= 100 per language pair) before camera-ready; report mean fluency scores in the benchmark construction section."),
("N",""),
("H3","6.3 Presentation and Completeness"),
("N","F17 [Double-blind compliance]: CLEAR. Author block, acknowledgements, and ethics section are properly anonymised."),
("N","F18 [OSF pre-registration incomplete]: FLAGGED. Pre-registration URL is a placeholder. Resolution: file OSF pre-registration immediately; update manuscript with URL."),
("N","F19 [Missing dataset/code repository URL]: AMBER. Paper claims 'benchmark and code are released' but gives no repository URL. Double-blind review accounts for this at submission, but an anonymised repository should be provided. Resolution: create an anonymous GitHub repository (e.g., via github.com/anonymous or anonymous.4open.science) and include the URL."),
("N","F20 [Perfect rho implausibility]: FLAGGED. Spearman rho = -1.000 is a simulation artifact that will be immediately identified by statistical reviewers. Resolution: replace with real evaluation results; expected real-world rho ~ -0.85 to -0.99."),
("N","F21 [Five contributions, not six]: CLEAR. The contributions section lists exactly five bullet points, consistent with the paper's scope. Stage 6 memo incorrectly stated six; the manuscript itself is correct."),
("N","F22 [Consumer vs clinical register mismatch]: FLAGGED. Paper title claims 'consumer medication risk understanding' but source data (RxSafeBench) uses clinical consultation scenarios. Resolution: either reframe as 'clinical consultation register' or supplement the base corpus with genuine consumer-register queries (e.g., from social media medication queries or OTC chatbot logs)."),
("N","F23 [Missing severity-weighted metric]: AMBER. Binary accuracy treats all errors as equivalent regardless of clinical severity. Resolution: add a severity-weighted metric or error type breakdown (safe-but-wrong vs. contraindicated-recommendation) as a secondary analysis."),
("N","F24 [Missing human performance baseline]: AMBER. No human baseline for the medication safety task. Resolution: add a lay consumer annotation arm (N >= 50) to provide a human ceiling/floor for model comparison."),
("N","F25 [GPT-4o parameter count source]: AMBER. '~1.8T' parameter estimate for GPT-4o is unverified. Resolution: cite the source of this estimate (e.g., a credible technical analysis) or state 'parameter count undisclosed.'"),
("N","F26 [Temperature=0 multi-run redundancy]: AMBER. For deterministic models (temperature=0), three evaluation runs will produce identical outputs, contributing no variance information. The three-run protocol is meaningful for stochastic open-weight models. Resolution: clarify in Section 4 that closed-API models are run deterministically and that variance across runs reflects API-level non-determinism only."),
("N","F27 [Arabic MSA scope limitation]: AMBER. AR-EN partitions use MSA, which may not represent the spoken Arabic of major US bilingual communities. Resolution: acknowledge this as a limitation (partially done) and consider adding at least one dialectal variant in future work section."),
("N","F28 [Ethical considerations section omitted]: AMBER. Ethical considerations section is entirely omitted for double-blind review. The camera-ready version must include IRB status for human annotation, data licensing compliance, and dual-use risk discussion."),
("N","F29 [AI use disclosure specificity]: AMBER. Claude-3.5-Sonnet is disclosed as used for 'code development and manuscript drafting assistance' but without specifying which sections. Resolution: specify which sections involved AI drafting assistance."),
("N","F30 [Missing zero-shot vs. few-shot comparison]: AMBER. All models are evaluated under zero-shot prompting. A few-shot condition (with CS examples) would test whether the accuracy gap closes with in-context learning. This is a natural ablation that reviewers will ask for. Resolution: add as a secondary experiment or future work item."),
("N","F31-F38 [Additional checks]: No additional blocking issues detected in page layout, citation formatting, keyword validity, or section organisation. All Procedia CS formatting requirements met. DOIs verified for all cited papers where DOIs are available."),
("N",""),

# ═══════════════════════════════════════════════════════════════════════════
("H2","7. Revision Priority Matrix"),
("N","Priority levels: CRITICAL = blocking for any submission | HIGH = required for Q1 journal / strong conference | MEDIUM = expected for camera-ready | LOW = desirable but not required"),
("N",""),
("H3","7.1 Critical — Blocking for All Submissions"),
("N","[C1] Run live API evaluation for all 7 models across all 13 partitions x 3 runs. Replace all simulated values in external_values.yaml (R001-R009) and macro_defs.tex. Estimated API cost: ~USD 1,200 (within the USD 1,400 compute budget). This is the single highest-priority action."),
("N","[C2] File OSF pre-registration BEFORE running any live evaluations. The OSF timestamp must predate all live API calls. Include all six hypotheses, statistical tests, and Bonferroni correction threshold."),
("N","[C3] Conduct human fluency validation for CS generation (N >= 100 items per language pair, native bilingual annotators). Report mean Likert scores in Section 3.3 (Quality Control)."),
("N","[C4] Obtain real pharmacist vs. judge IAA (N >= 100 items). The kappa >= 0.75 gate must be passed before the evaluation results are finalised."),
("N",""),
("H3","7.2 High — Required for Q1 Journal"),
("N","[H1] Fix judge-model conflict: use Claude-3.5-Sonnet (or a rule-based judge) for evaluating GPT-4o responses. Document judge-choice sensitivity analysis."),
("N","[H2] Fix abstract vs. table inconsistency: Mistral-7B minimum is 0.370 (AR-EN 70% Intra), not 0.386 (ES-EN 70% Intra). Correct the abstract."),
("N","[H3] Report both Jonckheere-Terpstra and Spearman rho for H3, or declare the deviation from pre-registration if J-T was replaced by Spearman."),
("N","[H4] Address register mismatch: either reframe as 'clinical consultation safety' or supplement with consumer-register queries. The title and framing must match the source data."),
("N","[H5] Add severity-weighted error metric as secondary analysis. Differentiate 'safe-but-wrong' from 'contraindicated recommendation' errors."),
("N","[H6] Remove or properly cite orphaned reference [VuEtAl2022] (BLOOM). Cite in Related Work or delete from bibliography."),
("N","[H7] Provide anonymised repository URL for benchmark data and code."),
("N",""),
("H3","7.3 Medium — Required for Camera-Ready"),
("N","[M1] Reframe abstract and conclusion results as confirmed findings (once live data available) or explicitly as 'simulated/predicted' until then."),
("N","[M2] Reposition Contribution bullet 5 (Qwen2 Arabic exception) as a finding in the Results section, not a design contribution."),
("N","[M3] Clarify GPT-4o parameter count source or remove the '~1.8T' claim."),
("N","[M4] Restore Ethical Considerations section: IRB status, data licensing, dual-use risk."),
("N","[M5] Add Wilcoxon power limitation note for H4 (N=7 pairs, minimum achievable p~0.016)."),
("N","[M6] Clarify temperature/determinism for closed-API models in Section 4."),
("N","[M7] Add zero-shot vs. few-shot comparison (or acknowledge as future work)."),
("N",""),
("H3","7.4 Low — Desirable"),
("N","[L1] Add human performance baseline (N >= 50 lay annotators) for clinical contextualisation."),
("N","[L2] Specify which manuscript sections involved AI drafting assistance."),
("N","[L3] Add dialectal Arabic variant (e.g., Egyptian or Levantine) as future benchmark extension."),
("N","[L4] Consider expanding to the full 2,443 RxSafeBench items for the English base corpus."),
("N",""),

# ═══════════════════════════════════════════════════════════════════════════
("H2","8. Gate 7 Verdict"),
("N","VERDICT: CONDITIONAL PROCEED TO STAGE 8 — Portfolio and Journal Cascade Preparation"),
("N",""),
("N","Rationale: Stage 7 has identified no issues that invalidate the research design, methodology, or conceptual contribution. All issues are resolvable. The critical path to submission is clear: live API evaluation -> OSF pre-registration (before evaluation) -> human CS fluency validation -> pharmacist IAA -> manuscript revision. Once these are complete, the paper is a strong candidate for ACL/EMNLP/NAACL (A* venues) or for the Q1 journal cascade (TACL -> IP&M -> JAMIA -> JMIR AI)."),
("N",""),
("N","Blocking pre-conditions for live submission (ALL must be complete):"),
("N","  Pre-1: OSF pre-registration filed and URL obtained (before any live API call)."),
("N","  Pre-2: Live API evaluation complete for all 7 models (all partitions, 3 runs each). External_values.yaml updated."),
("N","  Pre-3: Human CS fluency validation complete (kappa >= 0.75 for CS generation quality)."),
("N","  Pre-4: Pharmacist vs. judge IAA >= 0.75 (kappa)."),
("N","  Pre-5: Abstract corrected (Mistral-7B minimum = 0.370, not 0.386)."),
("N","  Pre-6: Reference [VuEtAl2022] cited or removed."),
("N","  Pre-7: H3 statistical test clarified (J-T vs. Spearman consistency)."),
("N",""),
("N","Stage 8 action (Portfolio): Prepare submission package for TACL rolling submission track. This includes: (a) cover letter positioning against DOSEBENCH/MIRA/CURE-Med concurrent work, (b) response-to-reviewers template pre-populating the Stage 7 concerns and planned responses, (c) supplementary materials checklist (benchmark data, code repository, OSF pre-registration, model card versions), and (d) author contribution statement (CRediT format)."),
("N",""),
("N","ACLing 2026 deadline (5 November 2026) is NOT achievable with live evaluation results. Recommend withdrawing from ACLing 2026 and retargeting to NAACL 2027 (expected submission: ~October 2026) or EMNLP 2027, or to TACL rolling submission (no fixed deadline). The Q1 journal cascade (TACL primary) is the recommended primary track given the paper's depth, benchmark scope, and the need for a thorough supplementary materials package."),
("N",""),
("N","Artefacts produced by Stage 7:"),
("N","  /home/sandbox/STAGE7_HOSTILE_REVIEW.docx — this hostile review memo"),
("N","  /home/sandbox/ACLing2026_manuscript.pdf — manuscript under review (unchanged)"),
]

STYLE_MAP = {"H1": H1, "H2": H2, "H3": H3, "N": NRM}

with doc_session(path=None, fmt="docx", save_to=OUTPUT, track=False) as (api, doc):
    first = True
    for style_key, text in CONTENT:
        ref = STYLE_MAP[style_key]
        if first:
            el = doc.GetElement(0)
            apply_style(el, doc, ref.get("styleName"))
            el.AddText(text)
            apply_resolved(el, ref)
            first = False
        else:
            para = styled_para(api, doc, text, ref)
            doc.Push(para)

print(f"Saved: {OUTPUT}")
