"""Shared settings for the pipeline."""
import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

DATA = Path("data")                     # all inputs/outputs live here (git-ignored except samples)
# Corpus written by 01_scrape.py. Set CORPUS=data/sample_100k.csv to run the pipeline on the public sample.
RAW_CSV = Path(os.environ.get("CORPUS", DATA / "reddit_peptides_corpus.csv"))

# Study communities (Reddit names are case-insensitive: r/Biohacking == r/biohacking)
PEPTIDE_SUBS = ["Peptides", "bpc_157", "Peptidesource", "NTNPerformance", "PeptidePathways"]
BIOHACK_SUBS = ["Biohackers", "biohacking", "BodyHackGuide"]
COMMUNITIES = PEPTIDE_SUBS + BIOHACK_SUBS

# Study period: everything retrieved up to 30 June 2026 (UTC); later records are ignored
STUDY_END_UTC = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp())

# Models (three-step extraction)
PRIMARY_MODEL = "gpt-4o-mini"                # step 1: every record (OpenAI, JSON schema)
SECOND_MODEL = "gemini-2.5-flash-lite"       # step 2: every record, independently (Gemini Batch API)
ADJUDICATOR_MODEL = "claude-sonnet-4-6"      # step 3: fields on which steps 1 and 2 disagree (Anthropic Batch API)

# Fields compared between models and adjudicated when they disagree (all fields used in the analysis)
COMPARE_FIELDS = ["is_patient_post", "substance_name", "primary_goal", "body_part", "route", "source_type", "provider_type",
                  "reconstitution_solvent", "believed_effective", "would_use_again", "would_recommend", "pain_reduction",
                  "functional_improvement", "peptide_categorization", "health_framing", "evidence_basis_cited", "trust_level",
                  "aware_fda_status", "customs_concern", "vs_traditional_medicine", "peptide_naive_vs_experienced",
                  "reason_for_discontinuation", "sex", "age", "side_effects", "cycle_pattern", "cycle_duration_weeks",
                  "cost_amount", "cost_unit", "specific_vendor_name", "country_obtained"]
TEMPERATURE = 0
MAX_BODY_CHARS = 12_000

# ---------------------------------------------------------------- extraction run
# Every model output and every result is written to one run folder, data/runs/<corpus>_<fingerprint>/. The fingerprint
# is a hash of the models, settings, prompt and schema, so no output is ever reused from a run made with different
# settings, and outputs from before run folders existed (data/llm_outputs, data/gemini_results, data/claude_batches)
# are never read. An interrupted run resumes in its own folder. RUN_TAG=<name> forces a new, separate run folder.
def _fingerprint():
    import prompt as Pm
    spec = json.dumps({"models": [PRIMARY_MODEL, SECOND_MODEL, ADJUDICATOR_MODEL], "temperature": TEMPERATURE,
                       "max_body_chars": MAX_BODY_CHARS, "system_prompt": Pm.SYSTEM_PROMPT, "user_template": Pm.USER_TEMPLATE,
                       "schema": Pm.SCHEMA, "compare_fields": COMPARE_FIELDS}, sort_keys=True)
    return hashlib.sha256(spec.encode()).hexdigest()[:10]


RUN_ID = f"{RAW_CSV.stem}_{os.environ.get('RUN_TAG') or _fingerprint()}"
RUN_DIR = DATA / "runs" / RUN_ID
PRIMARY_DIR = RUN_DIR / "llm_outputs"        # one JSON per record from the primary model
GEMINI_DIR = RUN_DIR / "gemini_results"      # Gemini batch results (JSONL)
CLAUDE_DIR = RUN_DIR / "claude_batches"      # Claude adjudication batches
CONSENSUS = RUN_DIR / "consensus.jsonl"      # final value per field = majority of the three models
DB = RUN_DIR / "peptides.duckdb"
FLOW = RUN_DIR / "flow.json"                 # record flow (Supplementary Figure 1), written by 05_build_dataset.py
RESULTS = RUN_DIR / "results.json"
VALIDATION = RUN_DIR / "validation.json"
FIGURES = RUN_DIR / "figures"
MANIFEST = RUN_DIR / "run_manifest.json"     # settings, model versions returned by each API, record counts, dates
LEGACY_DIRS = [DATA / "llm_outputs", DATA / "gemini_results", DATA / "claude_batches"]


def manifest(**updates):
    """Reads the run manifest and merges `updates` into it (lists and dicts are merged, other values replaced)."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    m = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {
        "run_id": RUN_ID, "corpus": str(RAW_CSV), "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "models_requested": {"primary": PRIMARY_MODEL, "second": SECOND_MODEL, "adjudicator": ADJUDICATOR_MODEL},
        "temperature": TEMPERATURE, "max_body_chars": MAX_BODY_CHARS}
    for k, v in updates.items():
        if isinstance(v, list) and isinstance(m.get(k), list): m[k] = sorted(set(m[k]) | set(v))
        elif isinstance(v, dict) and isinstance(m.get(k), dict): m[k] = m[k] | v
        else: m[k] = v
    MANIFEST.write_text(json.dumps(m, indent=1))
    return m

# Accounts excluded from analysis (deleted accounts, AutoModerator, bots, moderator teams)
BOT_REGEX = r"(?i)(^AutoModerator$|bot$|-ModTeam$|^\[deleted\]$)"

# Manual review of the extraction (08_validation.py)
REVIEW_N, REVIEW_SEED = 500, 2026

# Values treated as "not addressed"
NULLS = {"", "null", "unknown", "not_applicable", "not_mentioned", "none", "n/a", "not_stated", "nan", "[]"}
