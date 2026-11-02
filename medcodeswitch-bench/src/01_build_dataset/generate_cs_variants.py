"""
generate_cs_variants.py — Programmatic code-switching variant generation.

Since SwitchLingua requires the GPT-4o API (unavailable in sandbox), this module
generates synthetic code-switched variants using word-level substitution
from curated bilingual dictionaries. All outputs are marked synthetic=true.

CS ratios: 0.30, 0.50, 0.70
CS types : intra (within-sentence mixing), inter (sentence-level alternation)
Languages: ES-EN, AR-EN
"""

import os, sys, re, json, random, pathlib
from collections import defaultdict

os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"]      = "1"

ROOT    = pathlib.Path(__file__).resolve().parents[2]
EN_BASE = ROOT / "data" / "en_base" / "en_base_400.jsonl"
CS_OUT  = ROOT / "data"
SRC     = ROOT / "src" / "01_build_dataset"
sys.path.insert(0, str(SRC))
from schema import BenchmarkItem, Category, LanguagePair, CSType

SEED_CS = 42

# ── Bilingual substitution dictionaries ──────────────────────────────────────
# Expanded ~250-word dictionary for ES-EN (covers function words, verbs, medical)

ES_DICT = {
    # Greetings
    "hello":"hola","hi":"hola","thank":"gracias","thanks":"gracias",
    "please":"por favor","yes":"si","okay":"bien","ok":"ok",
    "sure":"claro","sorry":"lo siento","good":"bueno","well":"bien",
    "right":"correcto","really":"realmente","very":"muy","quite":"bastante",
    "just":"solo","also":"tambien","too":"tambien","maybe":"quizas",
    "probably":"probablemente",
    # Pronouns / determiners
    "i":"yo","you":"usted","the":"el","a":"un","an":"un",
    "my":"mi","your":"su","this":"este","that":"ese","these":"estos",
    "those":"esos","it":"eso","we":"nosotros","they":"ellos",
    "our":"nuestro","their":"su","some":"algunos","any":"cualquier",
    "all":"todo","other":"otro","each":"cada","every":"cada","both":"ambos",
    # Prepositions / conjunctions
    "in":"en","on":"sobre","at":"en","for":"para","with":"con",
    "about":"sobre","from":"de","after":"despues","before":"antes",
    "during":"durante","between":"entre","through":"a traves",
    "without":"sin","since":"desde","until":"hasta","because":"porque",
    "but":"pero","and":"y","or":"o","if":"si","when":"cuando",
    "where":"donde","how":"como","what":"que","which":"cual",
    "while":"mientras","although":"aunque","however":"sin embargo",
    "therefore":"por lo tanto","so":"asi que",
    # Verbs
    "have":"tengo","has":"tiene","had":"tenia","having":"teniendo",
    "feel":"siento","feels":"siente","felt":"sentia","feeling":"sintiendo",
    "experiencing":"experimentando","experience":"experimentar",
    "take":"tomar","taking":"tomando","taken":"tomado",
    "understand":"entiendo","know":"se","think":"creo",
    "need":"necesito","needs":"necesita","want":"quiero","wanted":"queria",
    "try":"intentar","tried":"intente","see":"ver","seen":"visto",
    "come":"venir","came":"vine","go":"ir","going":"yendo",
    "start":"comenzar","started":"comence","stop":"detener",
    "continue":"continuar","recommend":"recomendar",
    "prescribe":"recetar","prescribed":"recetado",
    "manage":"manejar","managing":"manejando",
    "monitor":"monitorear","monitoring":"monitoreando",
    "check":"verificar","checked":"verificado",
    "avoid":"evitar","avoiding":"evitando",
    "reduce":"reducir","improve":"mejorar","improving":"mejorando",
    "diagnose":"diagnosticar","diagnosed":"diagnosticado",
    "treat":"tratar","treated":"tratado",
    "tell":"decir","told":"dijo","ask":"preguntar","asked":"pregunto",
    "help":"ayudar","helping":"ayudando","control":"controlar",
    # Medical / body
    "pain":"dolor","doctor":"medico","patient":"paciente",
    "medication":"medicamento","medicine":"medicina",
    "blood":"sangre","heart":"corazon","symptoms":"sintomas",
    "symptom":"sintoma","diagnosis":"diagnostico","treatment":"tratamiento",
    "prescription":"receta","hospital":"hospital","appointment":"cita",
    "condition":"condicion","disease":"enfermedad","health":"salud",
    "diabetes":"diabetes","pressure":"presion","kidney":"rinon",
    "liver":"higado","stomach":"estomago","headache":"dolor de cabeza",
    "fatigue":"fatiga","weakness":"debilidad","numbness":"entumecimiento",
    "tingling":"hormigueo","swelling":"hinchazon","rash":"sarpullido",
    "nausea":"nauseas","vomiting":"vomitos","diarrhea":"diarrea",
    "fever":"fiebre","cough":"tos","breathe":"respirar",
    "breathing":"respiracion","infection":"infeccion",
    "inflammation":"inflamacion","cholesterol":"colesterol",
    "thyroid":"tiroides","allergic":"alergico","allergy":"alergia",
    "dosage":"dosis","pregnant":"embarazada","pregnancy":"embarazo",
    "weeks":"semanas","months":"meses","years":"anos","days":"dias",
    "body":"cuerpo","weight":"peso","test":"prueba","tests":"pruebas",
    "results":"resultados","levels":"niveles","dose":"dosis",
    "drug":"farmaco","drugs":"farmacos","risk":"riesgo","risks":"riesgos",
    "benefit":"beneficio","benefits":"beneficios","history":"historial",
    "family":"familia","age":"edad","diet":"dieta","exercise":"ejercicio",
    "sleep":"sueno","stress":"estres","side":"efecto","effects":"secundarios",
    # Descriptors
    "severe":"severo","mild":"leve","chronic":"cronico","acute":"agudo",
    "normal":"normal","high":"alto","low":"bajo","recent":"reciente",
    "important":"importante","necessary":"necesario","worried":"preocupado",
    "concerned":"preocupado","significant":"significativo","serious":"serio",
    "major":"mayor","minor":"menor","regular":"regular","daily":"diario",
    "current":"actual","previous":"previo","new":"nuevo","first":"primero",
    "second":"segundo","last":"ultimo","long":"largo","short":"corto",
    "different":"diferente","similar":"similar","better":"mejor",
    "worse":"peor","possible":"posible","certain":"cierto",
    "effective":"efectivo","common":"comun","rare":"raro",
}

# AR-EN: ~250-word Arabic dictionary
AR_DICT = {
    # Greetings
    "hello":"\u0645\u0631\u062d\u0628\u0627","hi":"\u0623\u0647\u0644\u0627",
    "thank":"\u0634\u0643\u0631\u0627","thanks":"\u0634\u0643\u0631\u0627\u064b",
    "please":"\u0645\u0646 \u0641\u0636\u0644\u0643","yes":"\u0646\u0639\u0645",
    "no":"\u0644\u0627","okay":"\u062d\u0633\u0646\u0627","ok":"\u062d\u0633\u0646\u0627",
    "sure":"\u0628\u0627\u0644\u062a\u0623\u0643\u064a\u062f",
    "sorry":"\u0622\u0633\u0641","good":"\u062c\u064a\u062f","well":"\u062d\u0633\u0646\u0627",
    "really":"\u062d\u0642\u0627\u064b","very":"\u062c\u062f\u0627\u064b",
    "just":"\u0641\u0642\u0637","also":"\u0623\u064a\u0636\u0627\u064b",
    "too":"\u0623\u064a\u0636\u0627\u064b","maybe":"\u0631\u0628\u0645\u0627",
    "probably":"\u0639\u0644\u0649 \u0627\u0644\u0623\u0631\u062c\u062d",
    # Pronouns / determiners
    "i":"\u0623\u0646\u0627","you":"\u0623\u0646\u062a",
    "my":"\u0645\u062a\u0627\u0639\u064a","your":"\u0645\u062a\u0627\u0639\u0643",
    "this":"\u0647\u0630\u0627","that":"\u0630\u0644\u0643",
    "we":"\u0646\u062d\u0646","they":"\u0647\u0645",
    "some":"\u0628\u0639\u0636","all":"\u0643\u0644",
    "other":"\u0622\u062e\u0631","each":"\u0643\u0644",
    # Prepositions / conjunctions
    "in":"\u0641\u064a","on":"\u0639\u0644\u0649","at":"\u0639\u0646\u062f",
    "for":"\u0644\u0640","with":"\u0645\u0639","about":"\u062d\u0648\u0644",
    "from":"\u0645\u0646","after":"\u0628\u0639\u062f","before":"\u0642\u0628\u0644",
    "during":"\u062e\u0644\u0627\u0644","between":"\u0628\u064a\u0646",
    "without":"\u0628\u062f\u0648\u0646","since":"\u0645\u0646\u0630",
    "until":"\u062d\u062a\u0649","because":"\u0644\u0623\u0646",
    "but":"\u0644\u0643\u0646","and":"\u0648","or":"\u0623\u0648",
    "if":"\u0625\u0630\u0627","when":"\u0639\u0646\u062f\u0645\u0627",
    "where":"\u0623\u064a\u0646","how":"\u0643\u064a\u0641",
    "what":"\u0645\u0627\u0630\u0627","while":"\u0628\u064a\u0646\u0645\u0627",
    "however":"\u0648\u0644\u0643\u0646","so":"\u0644\u0630\u0644\u0643",
    # Verbs
    "have":"\u0644\u062f\u064a","has":"\u0644\u062f\u064a\u0647",
    "having":"\u0623\u0639\u0627\u0646\u064a","feel":"\u0623\u0634\u0639\u0631",
    "feeling":"\u0623\u0634\u0639\u0631","experiencing":"\u0623\u0639\u0627\u0646\u064a",
    "take":"\u0622\u062e\u0630","taking":"\u0622\u062e\u0630",
    "understand":"\u0623\u0641\u0647\u0645","know":"\u0623\u0639\u0631\u0641",
    "think":"\u0623\u0639\u062a\u0642\u062f","need":"\u0623\u062d\u062a\u0627\u062c",
    "want":"\u0623\u0631\u064a\u062f","see":"\u0623\u0631\u0649",
    "come":"\u062a\u0639\u0627\u0644","go":"\u0627\u0630\u0647\u0628",
    "start":"\u0627\u0628\u062f\u0623","stop":"\u062a\u0648\u0642\u0641",
    "recommend":"\u0623\u0648\u0635\u064a","prescribe":"\u0635\u0641",
    "prescribed":"\u0648\u0635\u0641","monitor":"\u0631\u0627\u0642\u0628",
    "check":"\u062a\u062d\u0642\u0642","avoid":"\u062a\u062c\u0646\u0628",
    "improve":"\u062a\u062d\u0633\u064a\u0646","diagnose":"\u0634\u062e\u0635",
    "diagnosed":"\u062a\u0645 \u062a\u0634\u062e\u064a\u0635",
    "treat":"\u0639\u0644\u0627\u062c","tell":"\u0623\u062e\u0628\u0631",
    "help":"\u0645\u0633\u0627\u0639\u062f\u0629","control":"\u062a\u062d\u0643\u0645",
    # Medical / body
    "pain":"\u0623\u0644\u0645","doctor":"\u062f\u0643\u062a\u0648\u0631",
    "patient":"\u0645\u0631\u064a\u0636","medication":"\u062f\u0648\u0627\u0621",
    "medicine":"\u062f\u0648\u0627\u0621","blood":"\u062f\u0645",
    "heart":"\u0642\u0644\u0628","symptoms":"\u0623\u0639\u0631\u0627\u0636",
    "symptom":"\u0639\u0631\u0636","diagnosis":"\u062a\u0634\u062e\u064a\u0635",
    "treatment":"\u0639\u0644\u0627\u062c","prescription":"\u0648\u0635\u0641\u0629 \u0637\u0628\u064a\u0629",
    "hospital":"\u0645\u0633\u062a\u0634\u0641\u0649","appointment":"\u0645\u0648\u0639\u062f",
    "condition":"\u062d\u0627\u0644\u0629","disease":"\u0645\u0631\u0636",
    "health":"\u0635\u062d\u0629","diabetes":"\u0633\u0643\u0631\u064a",
    "pressure":"\u0636\u063a\u0637","kidney":"\u0643\u0644\u064a\u0629",
    "liver":"\u0643\u0628\u062f","stomach":"\u0645\u0639\u062f\u0629",
    "headache":"\u0635\u062f\u0627\u0639","fatigue":"\u0625\u0631\u0647\u0627\u0642",
    "weakness":"\u0636\u0639\u0641","numbness":"\u062e\u062f\u0631",
    "tingling":"\u0648\u062e\u0632","swelling":"\u062a\u0648\u0631\u0645",
    "rash":"\u0637\u0641\u062d \u062c\u0644\u062f\u064a","nausea":"\u063a\u062b\u064a\u0627\u0646",
    "vomiting":"\u0642\u064a\u0621","diarrhea":"\u0625\u0633\u0647\u0627\u0644",
    "fever":"\u062d\u0645\u0649","cough":"\u0633\u0639\u0627\u0644",
    "breathe":"\u062a\u0646\u0641\u0633","breathing":"\u062a\u0646\u0641\u0633",
    "infection":"\u0639\u062f\u0648\u0649","inflammation":"\u0627\u0644\u062a\u0647\u0627\u0628",
    "cholesterol":"\u0643\u0648\u0644\u064a\u0633\u062a\u0631\u0648\u0644",
    "thyroid":"\u0627\u0644\u063a\u062f\u0629 \u0627\u0644\u062f\u0631\u0642\u064a\u0629",
    "allergic":"\u062d\u0633\u0627\u0633","allergy":"\u062d\u0633\u0627\u0633\u064a\u0629",
    "dosage":"\u062c\u0631\u0639\u0629","pregnant":"\u062d\u0627\u0645\u0644",
    "pregnancy":"\u062d\u0645\u0644","weeks":"\u0623\u0633\u0627\u0628\u064a\u0639",
    "months":"\u0623\u0634\u0647\u0631","years":"\u0633\u0646\u0648\u0627\u062a",
    "days":"\u0623\u064a\u0627\u0645","body":"\u062c\u0633\u0645",
    "weight":"\u0648\u0632\u0646","test":"\u0641\u062d\u0635","tests":"\u0641\u062d\u0648\u0635",
    "results":"\u0646\u062a\u0627\u0626\u062c","levels":"\u0645\u0633\u062a\u0648\u064a\u0627\u062a",
    "dose":"\u062c\u0631\u0639\u0629","drug":"\u062f\u0648\u0627\u0621",
    "risk":"\u062e\u0637\u0631","risks":"\u0645\u062e\u0627\u0637\u0631",
    "benefit":"\u0641\u0627\u0626\u062f\u0629","history":"\u062a\u0627\u0631\u064a\u062e",
    "family":"\u0639\u0627\u0626\u0644\u0629","age":"\u0639\u0645\u0631",
    "diet":"\u0646\u0638\u0627\u0645 \u063a\u0630\u0627\u0626\u064a","exercise":"\u062a\u0645\u0631\u064a\u0646",
    "sleep":"\u0646\u0648\u0645","stress":"\u062a\u0648\u062a\u0631",
    # Descriptors
    "severe":"\u0634\u062f\u064a\u062f","mild":"\u062e\u0641\u064a\u0641",
    "chronic":"\u0645\u0632\u0645\u0646","acute":"\u062d\u0627\u062f",
    "normal":"\u0637\u0628\u064a\u0639\u064a","high":"\u0645\u0631\u062a\u0641\u0639",
    "low":"\u0645\u0646\u062e\u0641\u0636","recent":"\u062d\u062f\u064a\u062b",
    "important":"\u0645\u0647\u0645","worried":"\u0642\u0644\u0642",
    "concerned":"\u0642\u0644\u0642","significant":"\u0643\u0628\u064a\u0631",
    "serious":"\u062e\u0637\u064a\u0631","major":"\u0631\u0626\u064a\u0633\u064a",
    "regular":"\u0645\u0646\u062a\u0638\u0645","daily":"\u064a\u0648\u0645\u064a",
    "current":"\u062d\u0627\u0644\u064a","previous":"\u0633\u0627\u0628\u0642",
    "new":"\u062c\u062f\u064a\u062f","first":"\u0623\u0648\u0644",
    "last":"\u0623\u062e\u064a\u0631","long":"\u0637\u0648\u064a\u0644",
    "short":"\u0642\u0635\u064a\u0631","better":"\u0623\u0641\u0636\u0644",
    "worse":"\u0623\u0633\u0648\u0623","possible":"\u0645\u0645\u0643\u0646",
    "effective":"\u0641\u0639\u0627\u0644","common":"\u0634\u0627\u0626\u0639",
    "rare":"\u0646\u0627\u062f\u0631",
}

# ── Tokenizer / detokenizer ───────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"(\w[\w'-]*|\s+|[^\w\s])")

def tokenize(text):
    return _TOKEN_RE.findall(text)

def detokenize(tokens):
    return "".join(tokens)

def word_lower(token):
    return token.lower().rstrip(".,;:!?\"'")

def build_protected_set(item):
    protected = set()
    for name in [item.med_true, item.med_false, item.med_distractor, item.indication]:
        for part in name.lower().split():
            protected.add(part.strip(".,;:!?\"'"))
    return protected

# ── CS generation ─────────────────────────────────────────────────────────────

def apply_intra_cs(tokens, bilingual_dict, protected, target_ratio, rng):
    word_indices = [
        i for i, t in enumerate(tokens)
        if t.strip() and re.match(r"\w", t) and word_lower(t) not in protected
    ]
    rng.shuffle(word_indices)
    total_words = len(word_indices)
    n_target = max(1, int(total_words * target_ratio))
    substituted = tokens.copy()
    n_substituted = 0
    for i in word_indices:
        if n_substituted >= n_target:
            break
        key = word_lower(tokens[i])
        if key in bilingual_dict:
            repl = bilingual_dict[key]
            if tokens[i][0].isupper() and repl and not repl[0].isdigit():
                repl = repl[0].upper() + repl[1:]
            substituted[i] = repl
            n_substituted += 1
    actual_ratio = n_substituted / max(1, total_words)
    return substituted, actual_ratio

def apply_inter_cs(text, bilingual_dict, protected, target_ratio, rng):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out_sentences = []
    total_tokens = 0
    cs_tokens = 0
    for sent in sentences:
        toks = tokenize(sent)
        word_count = sum(1 for t in toks if t.strip() and re.match(r"\w", t))
        total_tokens += word_count
        if rng.random() < target_ratio:
            cs_toks, _ = apply_intra_cs(toks, bilingual_dict, protected, 0.9, rng)
            n_sub = sum(
                1 for i, t in enumerate(toks)
                if t.strip() and re.match(r"\w", t) and cs_toks[i] != t
            )
            cs_tokens += n_sub
            out_sentences.append(detokenize(cs_toks))
        else:
            out_sentences.append(sent)
    actual_ratio = cs_tokens / max(1, total_tokens)
    return " ".join(out_sentences), actual_ratio

# ── Main ──────────────────────────────────────────────────────────────────────

CS_CONFIGS = [
    (LanguagePair.ES_EN, 0.30, CSType.INTRA, "es_en/30_intra"),
    (LanguagePair.ES_EN, 0.30, CSType.INTER, "es_en/30_inter"),
    (LanguagePair.ES_EN, 0.50, CSType.INTRA, "es_en/50_intra"),
    (LanguagePair.ES_EN, 0.50, CSType.INTER, "es_en/50_inter"),
    (LanguagePair.ES_EN, 0.70, CSType.INTRA, "es_en/70_intra"),
    (LanguagePair.ES_EN, 0.70, CSType.INTER, "es_en/70_inter"),
    (LanguagePair.AR_EN, 0.30, CSType.INTRA, "ar_en/30_intra"),
    (LanguagePair.AR_EN, 0.30, CSType.INTER, "ar_en/30_inter"),
    (LanguagePair.AR_EN, 0.50, CSType.INTRA, "ar_en/50_intra"),
    (LanguagePair.AR_EN, 0.50, CSType.INTER, "ar_en/50_inter"),
    (LanguagePair.AR_EN, 0.70, CSType.INTRA, "ar_en/70_intra"),
    (LanguagePair.AR_EN, 0.70, CSType.INTER, "ar_en/70_inter"),
]

def main():
    rng = random.Random(SEED_CS)
    base_items = []
    with open(EN_BASE) as f:
        for line in f:
            base_items.append(BenchmarkItem.model_validate_json(line.strip()))
    print(f"Loaded {len(base_items)} base EN items")

    total_written = 0
    actual_ratios = defaultdict(list)

    for lang_pair, target_ratio, cs_type, outdir in CS_CONFIGS:
        out_path = CS_OUT / outdir
        out_path.mkdir(parents=True, exist_ok=True)
        out_file = out_path / "cs_variants.jsonl"
        bilingual_dict = ES_DICT if lang_pair == LanguagePair.ES_EN else AR_DICT

        written = 0
        with open(out_file, "w", encoding="utf-8") as f_out:
            for item in base_items:
                protected = build_protected_set(item)
                tokens = tokenize(item.dialogue)

                if cs_type == CSType.INTRA:
                    cs_tokens, actual = apply_intra_cs(
                        tokens, bilingual_dict, protected, target_ratio, rng)
                    cs_dialogue = detokenize(cs_tokens)
                else:
                    cs_dialogue, actual = apply_inter_cs(
                        item.dialogue, bilingual_dict, protected, target_ratio, rng)
                    if actual == 0.0:
                        cs_tokens2, actual = apply_intra_cs(
                            tokenize(item.dialogue), bilingual_dict, protected,
                            min(0.10, target_ratio), rng)
                        cs_dialogue = detokenize(cs_tokens2)
                    actual = max(actual, 0.001)

                lang_code = "ES" if lang_pair == LanguagePair.ES_EN else "AR"
                ratio_code = str(int(target_ratio * 100))
                type_code  = "I" if cs_type == CSType.INTRA else "X"
                new_id = f"{item.item_id}-{lang_code}CS{ratio_code}{type_code}"

                cs_item = BenchmarkItem(
                    item_id        = new_id,
                    category       = item.category,
                    indication     = item.indication,
                    med_true       = item.med_true,
                    med_false      = item.med_false,
                    med_distractor = item.med_distractor,
                    safety_detail  = item.safety_detail,
                    dialogue       = cs_dialogue,
                    language_pair  = lang_pair,
                    cs_type        = cs_type,
                    cs_ratio       = round(actual, 3),
                    source         = "rxsafebench+programmatic_cs",
                    synthetic      = True,
                    quality_score  = item.quality_score,
                    structure_score= item.structure_score,
                    seed           = SEED_CS,
                )
                f_out.write(cs_item.model_dump_json() + "\n")
                actual_ratios[outdir].append(actual)
                written += 1

        total_written += written
        mean_actual = sum(actual_ratios[outdir]) / len(actual_ratios[outdir])
        print(f"  {outdir:20s}: {written} items  mean_cs_ratio={mean_actual:.3f}  (target={target_ratio})")

    print(f"\nTotal CS variants written: {total_written}")
    print("generate_cs_variants.py DONE")

if __name__ == "__main__":
    main()
