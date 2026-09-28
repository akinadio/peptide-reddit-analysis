"""Peptide categories (Table 1), adverse-event groups (Figure 3) and field recodes used in the analysis."""
import re

# ---------------------------------------------------------------- peptide categories
CATEGORIES = {
    "GLP-1/GIP receptor agonists and amylin analogues": {
        "Retatrutide": r"retatrutide|retarutide|\breta\b|\bret\b", "Tirzepatide": r"tirzepatide|tirzepitide|trizepatide|\btirz\b|\btriz\b|mounjaro|zepbound",
        "Semaglutide": r"semaglutide|\bsema\b|ozempic|wegovy|rybelsus", "Cagrilintide": r"cagrilintide|\bcagri\b|\bcag\b",
        "Liraglutide": r"liraglutide|saxenda|victoza", "Other incretin agonist": r"survodutide|mazdutide|orforglipron|\bglp[\s-]?1\b|glp1|glucagon"},
    "Tissue-repair and skin peptides": {
        "BPC-157": r"bpc|pentadeca|\bpda\b", "TB-500 / thymosin β4": r"tb[\s_-]?500|tb[\s-]?4\b|thymosin[\s-]?beta", "GHK-Cu": r"ghk|copper[\s_]?peptide",
        "BPC-157/TB-500/GHK-Cu blends": r"klow|glow|wolverine", "Cosmetic peptides (AHK-Cu, SNAP-8)": r"ahk|snap[\s-]?8|argireline|matrixyl|leuphasyl"},
    "Growth-hormone axis peptides and secretagogues": {
        "CJC-1295 / mod GRF 1-29": r"cjc|mod[\s-]?grf|modgrf|\bghrh\b|\bdac\b", "Ipamorelin": r"ipamorelin|\bipa\b", "Tesamorelin": r"tesamorelin",
        "Sermorelin": r"sermorelin|semorelin", "GHRP-2/-6 / hexarelin": r"ghrp|hexarelin", "HGH (somatropin)": r"\bhgh\b|growth[\s_]?hormone|\bgh\b|somatropin|genotropin|norditropin",
        "IGF-1 LR3 / MGF": r"igf|\bmgf\b", "HGH fragment 176-191 / AOD-9604": r"frag|aod[\s-]?9604", "Follistatin": r"follistatin|sarcotropin"},
    "Melanocortin peptides": {"Melanotan I/II": r"melanotan|\bmt[\s-]?(2|ii|1|i)\b", "PT-141 (bremelanotide)": r"pt[\s-]?141|bremelanotide"},
    "Mitochondrial, longevity and bioregulator peptides": {
        "MOTS-c": r"mots|mot[\s-]?c|motc", "SS-31": r"ss[\s-]?31|elamipretide", "Epitalon": r"epitalon|epithalon", "Humanin": r"humanin",
        "FOXO4-DRI": r"foxo|fox04", "GDF11": r"gdf[\s-]?11",
        "Short peptide bioregulators": r"cartalax|testagen|bronchogen|prostamax|visoluten|sigumir|vilon|ovagen|chonluten|vesugen|cardiogen|livagen|pancragen|crystagen|bioregulator|khavinson"},
    "Nootropic and neuroactive peptides": {
        "Semax": r"semax", "Selank": r"selank", "DSIP": r"dsip", "Cerebrolysin / cortexin": r"cerebrolysin|cortexin", "Dihexa": r"dihexa",
        "Other neuroactive peptides": r"\bp21\b|adamax|pinealon|mif[\s-]?1|pe[\s-]?22|dermorphin|nsi[\s-]?189"},
    "Immunomodulatory and anti-inflammatory peptides": {
        "Thymosin α1 / thymic peptides": r"thymosin[\s-]?alpha|\bta[\s-]?1\b|thymalin|thymulin|thymogen", "KPV": r"\bkpv\b", "LL-37": r"ll[\s-]?37",
        "ARA-290": r"ara[\s-]?290|^ara$", "VIP": r"\bvip\b", "Other immunomodulatory / gut peptides": r"glp[\s-]?2|larazotide|pnc[\s-]?27"},
    "Reproductive and endocrine peptides": {
        "hCG / hMG": r"\bhcg\b|\bhmg\b|pregnyl|novarel", "Kisspeptin": r"kisspeptin", "Gonadorelin / triptorelin": r"gonadorelin|triptorelin", "Oxytocin": r"oxytocin"},
    "Metabolic and fat-loss peptides": {"Adipotide": r"adipotide"},
}
_PATTERNS = [(cat, name, re.compile(rx)) for cat, d in CATEGORIES.items() for name, rx in d.items()]
_UNSPEC = re.compile(r"^(unknown|null|none|other|n/a|na|nan|multiple|unspecified( peptide)?|peptides?|retail|ps|various|stack|bac|bac water|bacteriostatic[ _]water|bacteriostatic)$")
_SPLIT = re.compile(r"\s*(?:,|\||/|;|\+|\band\b|&|\bwith\b)\s*")


_SMALL_MOLECULE = re.compile(r"mk[\s-]?677|ibutamoren|^mk$|\bnad\b|nad\+|\bnmn\b|\bnr\b|nicotinamide|5[\s-]?amino|1mq|slu[\s-]?pp|tesofensine|lipo[\s-]?c")


def classify(substance):
    """(category, peptide) for the first recognisable peptide named; 'nonpeptide' if only non-peptide substances are named
    (or a small molecule sold alongside peptides, e.g. MK-677, is named first); None if no substance is named."""
    named_other = False
    for tok in (t.strip().strip(".").lower() for t in _SPLIT.split(substance or "") if t.strip()):
        if _UNSPEC.match(tok): continue
        hit = next(((c, n) for c, n, rx in _PATTERNS if rx.search(tok)), None)
        if hit: return hit
        if _SMALL_MOLECULE.search(tok): return "nonpeptide"
        named_other = True
    return "nonpeptide" if named_other else None


# ---------------------------------------------------------------- adverse-event groups (first match wins)
AE_GROUPS = [
    ("Injection-site reaction", r"injection site|site (reaction|pain|redness|swelling)|redness|itch|sting|welt|bump|lump|swelling|burning|burn\b|soreness|irritation|inflammation|\bpip\b|knot|bruis"),
    ("Fatigue / lethargy", r"fatigue|tired|lethargy|exhaust|low energy|drowsi|groggi|malaise|weakness|sluggish"),
    ("Nausea", r"nausea|nauseous|queasy"), ("Vomiting", r"vomit|throw(ing)? up"),
    ("Anxiety / restlessness", r"anxiety|anxious|panic|restless|agitat|jitter|nervous"),
    ("Anhedonia / emotional blunting", r"anhedonia|emotional(ly)? (flat|blunt)|numb|apathy|flat affect"),
    ("Mood change", r"depress|low mood|mood crash|mood swing|crash|irritab|anger|rage|mood"),
    ("Sleep disturbance / vivid dreams", r"insomnia|sleep|vivid dream|nightmare|dream"),
    ("Headache", r"headache|migraine|head rush|head pressure"), ("Flushing", r"flush"),
    ("Water retention / bloating", r"water retention|water weight|bloat|edema|oedema|puffy|swollen"),
    ("Increased hunger / cravings", r"hunger|hungry|increased appetite|appetite increase|craving"),
    ("Decreased appetite", r"appetite (loss|suppress|decrease|reduc)|loss of appetite|no appetite|decreased appetite|reduced appetite|suppressed appetite|food aversion"),
    ("Constipation", r"constipat"), ("Diarrhoea", r"diarr|loose stool"),
    ("Other gastrointestinal", r"reflux|heartburn|gerd|burp|eructation|indigestion|gas\b|stomach|abdominal|cramp|gi (upset|issues)|upset stomach"),
    ("Dizziness", r"dizz|lighthead|vertigo|faint"), ("Palpitations / increased heart rate", r"heart|palpit|tachy|racing"),
    ("Blood pressure change", r"blood pressure|hypertens|hypotens"),
    ("Hyperpigmentation", r"hyperpigment|dark(er|ening)? (spot|skin|mole)|mole|freckle|\btan|pigment"), ("Skin tags", r"skin tag"),
    ("Carpal-tunnel-like symptoms", r"carpal|numb (hand|finger)|tingl|paresthesia|paraesthesia|pins and needles"),
    ("Hair loss", r"hair loss|shedding|hair thin|alopecia"), ("Skin eruption", r"acne|breakout|rash|hives|urticaria|dermatitis|skin sensitiv|dry skin"),
    ("Allergic / histamine reaction", r"allerg|histamine|anaphyla"), ("Sexual / endocrine effect", r"libido|erection|erectile|sexual|arousal|gyneco"),
    ("Blood glucose change", r"blood sugar|hypoglyc|hyperglyc|glucose|insulin resist"), ("Joint pain", r"joint pain|arthralgia|joint"),
    ("Muscle loss / muscle pain", r"muscle (loss|wast)|sarcopenia|muscle cramp|muscle pain|myalgia"), ("Weight change", r"weight gain|weight loss|rebound"),
    ("Temperature dysregulation / flu-like symptoms", r"sweat|hot flash|chills|fever|flu|warmth|temperature|night sweat"),
    ("Cognitive effects", r"brain fog|cognitive|memory|confus|concentrat"), ("Sensory (tinnitus, visual)", r"tinnitus|vision|blurry|eye"),
    ("Dry mouth / dehydration", r"dry mouth|thirst|dehydrat"), ("Withdrawal / dependence", r"withdrawal|dependen|addict|tolerance|crash after"),
    ("Infection", r"infection|abscess|cellulitis"), ("Respiratory / chest tightness", r"shortness of breath|breath|chest tight"), ("Pain", r"pain"),
]
_AE = [(g, re.compile(rx)) for g, rx in AE_GROUPS]


def ae_groups(side_effects):
    """Distinct adverse-event groups mentioned in a '|'-separated side-effect string."""
    out = []
    for tok in (side_effects or "").lower().split("|"):
        tok = tok.strip().replace("_", " ")
        if tok and tok not in ("null", "none", "unknown"):
            g = next((g for g, rx in _AE if rx.search(tok)), "Other / unclassified")
            if g not in out: out.append(g)
    return out


# ---------------------------------------------------------------- dosing frequency (from free-text cycle pattern)
FREQUENCY = [("5 days on / 2 days off", r"5 ?(days? )?on.{0,4}2 ?(days? )?off|5/2|weekdays"),
             ("Twice daily", r"twice (a |per )?day|2x ?(/|per |a )?day|2x daily|\bbid\b|am and pm|morning and (night|evening)"),
             ("Every other day", r"every other day|\beod\b|alternate days|every 2 days"),
             ("Twice weekly", r"twice (a |per )?week|2x ?(/|per |a )?week|twice weekly|biweekly"),
             ("Weekly", r"weekly|once a week|per week|/week|1x ?(/|per |a )?week|every week|every 7 days"),
             ("Daily", r"daily|every day|once a day|\bed\b|/day|per day|nightly|each day|\bqd\b|every night|before bed|each morning")]
_FQ = [(n, re.compile(rx)) for n, rx in FREQUENCY]
frequency = lambda s: next((n for n, rx in _FQ if rx.search((s or "").lower())), None)
CONTINUOUS = re.compile(r"continu|ongoing|indefinite|no break|year[- ]round|no cycl|non[- ]?stop|without (a )?break|no off")

# ---------------------------------------------------------------- categorical recodes (value -> reported category; None = not addressed)
def _keep(*vals, **alias):
    return lambda v: alias.get(v, v if v in vals else None)

RECODE = {
    "sex": lambda v: {"m": "M", "male": "M", "man": "M", "men": "M", "f": "F", "female": "F", "woman": "F", "women": "F"}.get(v),
    "route": lambda v: {"intranasal": "nasal", "injection": "other", "oral": "oral_capsule"}.get(v, v),
    "source_type": lambda v: {"research_peptide_site": "online_vendor", "self": "self_compounded", "gym": "friend"}.get(v, v),
    "believed_effective": _keep("yes", "no", "mixed", "placebo"),
    "would_use_again": _keep("yes", "no", "mixed"), "would_recommend": _keep("yes", "no", "mixed"),
    "pain_reduction": _keep("mild", "moderate", "significant", "complete"),
    "functional_improvement": _keep("yes", "partial", "no"),
    "peptide_categorization": _keep("supplement", "medication", "experimental_therapy", "alternative_medicine", "performance_enhancer",
                                    "aesthetic_enhancement", biohack="biohacking_tool", aesthetic="aesthetic_enhancement", cosmetic="aesthetic_enhancement"),
    "evidence_basis_cited": _keep("published_studies", "mechanism_or_biology", "community_testimony", "personal_experiment", "doctor_recommendation",
                                  research="published_studies", clinical_trials="published_studies", studies="published_studies"),
    "trust_level": _keep("high", "moderate", "skeptical", "experimental"),
    "health_framing": _keep("treating_illness", "preventing_illness", "health_optimization", "aesthetic_enhancement", "athletic_performance", "longevity",
                            "weight_loss", "mental_health", "sexual", "sleep", "cognitive", performance="athletic_performance", cosmetic="aesthetic_enhancement"),
    "provider_type": _keep("md_do", "nd_naturopath", "dc_chiropractor", "pt_physical_therapist", "np_pa", "coach_trainer", "self", "friend", "other",
                           doctor="md_do", physician="md_do", md="md_do", do="md_do", clinic="other", functional_med_clinic="other"),
    "reason_for_discontinuation": _keep("side_effects", "cost", "lack_of_effect", "completed_cycle", "lab_abnormality", "doctor_advice",
                                        "pregnancy_planning", "never_stopped", "scam", "allergic_reaction", not_effective="lack_of_effect"),
    "vs_traditional_medicine": _keep("complement", "replacement", "alternative", "didnt_compare", alternative_medicine="alternative"),
    "peptide_naive_vs_experienced": _keep("naive", "two_to_five_peptides", "six_or_more", experienced="two_to_five_peptides"),
    "primary_goal": _keep("healing_recovery", "performance", "aesthetic", "weight_loss", "cognitive", "sleep", "sexual", "longevity", "mood",
                          "gut_gi", "other", "health_optimization", "mental_health"),
    "body_part": lambda v: v,
    "reconstitution_solvent": lambda v: ("bacteriostatic_water" if "bacteriostatic" in v or v == "bac water" or "bac " in v else
                                         "sterile_water" if "sterile water" in v else "saline" if "saline" in v or "sodium chloride" in v else "other"),
    "aware_fda_status": lambda v: {"true": "referenced", "false": "not_referenced"}.get(v),
    "customs_concern": lambda v: {"true": "yes", "false": "no"}.get(v),
    "country_obtained": lambda v: ("United States" if v in {"usa", "us", "united states", "united states of america", "america", "u.s.", "u.s.a."} else
                                   "United Kingdom" if v in {"uk", "united kingdom", "england", "britain", "great britain", "scotland", "wales"} else
                                   None if v in {"overseas", "abroad", "international", "not specified", "domestic"} else v),
}
