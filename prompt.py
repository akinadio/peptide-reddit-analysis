"""Extraction prompt and JSON schema (identical for every model)."""

FIELDS = {  # field -> JSON type
    "is_patient_post": "boolean", "follow_up_reported": "boolean", "substance_name": "string",
    "substance_stack": "array", "route": "string", "daily_dose_mcg": "number", "cycle_pattern": "string",
    "cycle_duration_weeks": "number", "primary_goal": "string", "specific_indication": "string",
    "body_part": "string", "source_type": "string", "specific_vendor_name": "string",
    "country_obtained": "string", "mentions_lab_testing_COA": "boolean", "reconstitution_solvent": "string",
    "provider_type": "string", "cost_amount": "number", "cost_unit": "string", "cost_currency": "string",
    "pain_reduction": "string", "functional_improvement": "string", "believed_effective": "string",
    "would_use_again": "string", "would_recommend": "string", "side_effects": "array", "age": "integer",
    "sex": "string", "comorbidities": "array", "concurrent_medications": "array", "lab_monitoring": "array",
    "peptide_categorization": "string", "health_framing": "string", "vs_traditional_medicine": "string",
    "trust_level": "string", "evidence_basis_cited": "string", "peptide_naive_vs_experienced": "string",
    "reason_for_discontinuation": "string", "aware_fda_status": "boolean", "customs_concern": "boolean",
    "telemedicine_clinic_involved": "boolean", "mental_health_framing": "array",
    "community_platform_mentioned": "array", "notable_quote": "string",
}

SCHEMA = {"name": "peptide_extraction", "strict": False, "schema": {
    "type": "object", "additionalProperties": False,
    "required": ["is_patient_post", "substance_name", "primary_goal"],
    "properties": {k: ({"type": ["array", "null"], "items": {"type": "string"}} if t == "array" else {"type": [t, "null"]})
                   for k, t in FIELDS.items()}}}

SYSTEM_PROMPT = """You are an expert medical informatics annotator. You read a single post or comment from a Reddit peptide community and extract structured information for a JAMA-scope analysis of patient perception of peptides as health interventions.

Return ONLY a valid JSON object matching the schema. No prose, no markdown — JSON only.

is_patient_post: true if the author is themselves using or has used a peptide. false otherwise.
substance_name: canonical form — BPC-157, TB-500, Thymosin Alpha-1, Ipamorelin, CJC-1295, Sermorelin, Tesamorelin, GHK-Cu, MGF, GHRP-6, KPV, AOD-9604, IGF-1 LR3, Semaglutide, Tirzepatide, Retatrutide, Melanotan I, Melanotan II, PT-141, Selank, Semax, Epitalon, Hexarelin, HGH Frag 176-191, DSIP, 5-Amino-1MQ, SS-31, Cerebrolysin, other.
substance_stack: array of additional peptides used alongside the primary one.
route: oral_capsule, oral_spray, sublingual, subcutaneous, intramuscular, intra_articular, intratendinous, topical, nasal, other.
daily_dose_mcg: dose in micrograms (convert mg ×1000). null if not stated.
cycle_pattern: free text. cycle_duration_weeks: weeks of one cycle.
primary_goal: healing_recovery, performance, aesthetic, weight_loss, cognitive, sleep, sexual, longevity, mood, gut_GI, other.
specific_indication: free text — e.g., "rotator cuff tendinopathy", "perimenopause weight gain", "ulcerative colitis".
body_part: shoulder, knee, hip, elbow, ankle, spine, wrist, hand, foot, tendon, multi_site, skin, systemic, none.
source_type: research_peptide_site, compounding_pharmacy, functional_med_clinic, orthopedic_clinic, regenerative_med_clinic, online_vendor, overseas_clinic, pharmacy, friend, coach, self_compounded, gym, other.
specific_vendor_name: actual vendor or clinic name as written.
country_obtained: country name.
mentions_lab_testing_COA: true if patient mentions COA, lab-tested purity, third-party testing.
reconstitution_solvent: bacteriostatic water / sterile water / saline / other / null.
provider_type: MD_DO, ND_naturopath, DC_chiropractor, PT_physical_therapist, NP_PA, coach_trainer, self, friend, none, other.
cost_amount + cost_unit + cost_currency: paired. Unit one of: per_vial, per_kit, per_5mg, per_10mg, per_15mg, per_mg, per_gram, per_cycle, per_month, per_week, per_dose, per_bottle, per_pen, per_box, total_course, shipping, unknown.
pain_reduction: none / mild / moderate / significant / complete / not_applicable / null.
functional_improvement: yes / partial / no / not_applicable / null.
believed_effective / would_use_again / would_recommend: yes / no / mixed / placebo / null. INFER from indirect language.
side_effects: OPEN array, ANY adverse event mentioned. Use short tokens.
age / sex: integer / 'F' or 'M' — only if author states their own.
comorbidities: OPEN array of patient conditions (T2DM, OA, depression, hypogonadism, etc.)
concurrent_medications: OPEN array of other drugs (TRT, HGH, GLP-1, SSRI, statins, etc.)
lab_monitoring: OPEN array of labs done (CBC, CMP, testosterone, IGF-1, glucose, etc.)
peptide_categorization: supplement / medication / biohack / experimental_therapy / alternative_medicine / performance_enhancer / unknown
health_framing: treating_illness / preventing_illness / health_optimization / aesthetic_enhancement / athletic_performance / longevity / cosmetic / unknown
vs_traditional_medicine: complement / replacement / alternative / didnt_compare / unknown
trust_level: high / moderate / skeptical / experimental / unknown
evidence_basis_cited: published_studies / mechanism_or_biology / community_testimony / personal_experiment / doctor_recommendation / not_mentioned
peptide_naive_vs_experienced: naive / two_to_five_peptides / six_or_more / unknown
reason_for_discontinuation: side_effects / cost / lack_of_effect / completed_cycle / lab_abnormality / doctor_advice / pregnancy_planning / never_stopped / unknown
follow_up_reported: true if this is an update/follow-up post weeks or months after starting.
aware_fda_status: true if patient demonstrates awareness peptide is not FDA-approved for their indication.
customs_concern: true if patient discusses international shipping, customs, legality.
telemedicine_clinic_involved: true if prescribed via online clinic (Hims/Hers, Henry Meds, etc.).
mental_health_framing: OPEN array (anxiety, depression, body_dysmorphia, appearance_pressure, etc.)
community_platform_mentioned: OPEN array (Reddit, Discord, Telegram, Twitter, YouTube, etc.)
notable_quote: at most one short verbatim sentence (<=200 chars). null if nothing standout.

Use null when not addressed. Do NOT guess. Lists: [] only when author explicitly says "none"; otherwise null.
"""

USER_TEMPLATE = "Subreddit: r/{subreddit}\nKind: {kind}\nTitle: {title}\n\nBody:\n{body}\n"


def user_message(row, max_chars=12_000):
    body = (row.get("body") or "").strip()
    if len(body) > max_chars:
        body = body[:max_chars] + "\n...[truncated]"
    return USER_TEMPLATE.format(subreddit=row.get("subreddit", ""), kind=row.get("kind", ""),
                                title=(row.get("title") or "").strip(), body=body)


def parse_json(raw):
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    import json
    d = json.loads(raw)
    if not isinstance(d, dict):
        raise ValueError("model returned non-object JSON")
    return d
