"""Shared settings for the pipeline."""
import os
from datetime import datetime, timezone
from pathlib import Path

DATA = Path("data")                     # all inputs/outputs live here (git-ignored except samples)
# Corpus written by 01_scrape.py. Set CORPUS=data/sample_100k.csv to run the pipeline on the public sample.
RAW_CSV = Path(os.environ.get("CORPUS", DATA / "reddit_peptides_corpus.csv"))
PRIMARY_DIR = DATA / "llm_outputs"          # one JSON per record from the primary model
GEMINI_DIR = DATA / "gemini_results"        # Gemini batch results (JSONL)
DB = DATA / "peptides.duckdb"
FLOW = DATA / "flow.json"                   # record flow (Supplementary Figure 1), written by 05_build_dataset.py

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

# Accounts excluded from analysis (deleted accounts, AutoModerator, bots, moderator teams)
BOT_REGEX = r"(?i)(^AutoModerator$|bot$|-ModTeam$|^\[deleted\]$)"

# Manual review of the extraction (08_validation.py)
REVIEW_N, REVIEW_SEED = 500, 2026

# Values treated as "not addressed"
NULLS = {"", "null", "unknown", "not_applicable", "not_mentioned", "none", "n/a", "not_stated", "nan", "[]"}
