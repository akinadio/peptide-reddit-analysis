"""Shared settings for the pipeline."""
from pathlib import Path

DATA = Path("data")                     # all inputs/outputs live here (git-ignored except samples)
RAW_CSV = DATA / "reddit_peptides_corpus.csv"
PRIMARY_DIR = DATA / "llm_outputs"          # one JSON per record from the primary model
GEMINI_DIR = DATA / "gemini_results"        # Gemini batch results (JSONL)
DB = DATA / "peptides.duckdb"

# Study communities (Reddit names are case-insensitive: r/Biohacking == r/biohacking)
PEPTIDE_SUBS = ["Peptides", "bpc_157", "Peptidesource", "NTNPerformance", "PeptidePathways"]
BIOHACK_SUBS = ["Biohackers", "biohacking", "BodyHackGuide"]
COMMUNITIES = PEPTIDE_SUBS + BIOHACK_SUBS

# Models (three-step extraction)
PRIMARY_MODEL = "gpt-4o-mini"                # step 1: every record (OpenAI, JSON schema)
SECOND_MODEL = "gemini-2.5-flash-lite"       # step 2: every record, independently (Gemini Batch API)
ADJUDICATOR_MODEL = "claude-sonnet-4-6"      # step 3: fields on which steps 1 and 2 disagree (Anthropic Batch API)
CONSENSUS = DATA / "consensus.jsonl"         # final value per field = majority of the three models
CLAUDE_DIR = DATA / "claude_batches"

# Fields compared between models and adjudicated when they disagree (all fields used in the analysis)
COMPARE_FIELDS = ["is_patient_post", "substance_name", "primary_goal", "body_part", "route", "source_type", "provider_type",
                  "reconstitution_solvent", "believed_effective", "would_use_again", "would_recommend", "pain_reduction",
                  "functional_improvement", "peptide_categorization", "health_framing", "evidence_basis_cited", "trust_level",
                  "aware_fda_status", "customs_concern", "vs_traditional_medicine", "peptide_naive_vs_experienced",
                  "reason_for_discontinuation", "sex", "age", "side_effects", "cycle_pattern", "cycle_duration_weeks",
                  "cost_amount", "cost_unit", "specific_vendor_name", "country_obtained"]
TEMPERATURE = 0
MAX_BODY_CHARS = 12_000
MIN_CHARS = 50
TARGET_RECORDS = 1_000_000

# Accounts excluded from analysis
BOT_REGEX = r"(?i)(^AutoModerator$|bot$|-ModTeam$|^\[deleted\]$)"

# Values treated as "not addressed"
NULLS = {"", "null", "unknown", "not_applicable", "not_mentioned", "none", "n/a", "not_stated", "nan", "[]"}
