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

# Models
PRIMARY_MODEL = "gpt-4o-mini"                # OpenAI, temperature 0, JSON-schema output
FALLBACK_MODEL = "gemini-2.5-flash-lite"     # records without usable primary output (Batch API)
VALIDATOR_MODEL = "claude-sonnet-4-6"        # validation only
TEMPERATURE = 0
MAX_BODY_CHARS = 12_000
MIN_CHARS = 50
TARGET_RECORDS = 1_000_000

# Accounts excluded from analysis
BOT_REGEX = r"(?i)(^AutoModerator$|bot$|-ModTeam$|^\[deleted\]$)"

# Values treated as "not addressed"
NULLS = {"", "null", "unknown", "not_applicable", "not_mentioned", "none", "n/a", "not_stated", "nan", "[]"}
