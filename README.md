# Self-reported use and perception of peptide therapy on Reddit

Code for *Self-Reported Use and Perception of Peptide Therapy: A Cross-Sectional Analysis of Over One Million Online Discussions*.

The pipeline retrieves public posts and comments from eight peptide-focused and biohacking Reddit communities,
extracts 44 structured fields from each record with a large language model, and produces every number,
table and figure reported in the paper.

| Step | Script | What it does |
|---|---|---|
| 1 | `01_scrape.py` | Retrieves posts and comments (Nov 2014 – Jun 2026) from the Arctic Shift Reddit archive |
| 2 | `02_extract.py` | Structured extraction with **GPT-4o-mini** (temperature 0, fixed prompt and JSON schema in `prompt.py`) |
| 3 | `03_gemini_batch.py` | Gemini 2.5 Flash-Lite (Batch API) for records without usable primary output |
| 4 | `04_build_dataset.py` | Merges outputs, keeps the eight communities, flags bot/moderator/deleted accounts, classifies peptides |
| 5 | `05_analyze.py` | All reported statistics, Table 1, Table 2 and figure data → `data/results.json` |
| 6 | `06_figures.py` | Figures 1–3 |
| 7 | `07_validate.py` | Validation on 2,000 records: Gemini 2.5 Flash-Lite and Claude Sonnet 4.6, 2-of-3 majority vote |

Shared definitions: `config.py` (paths, communities, models), `prompt.py` (prompt and schema),
`definitions.py` (peptide categories, adverse-event groups, recodes).

## Run

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY
python 01_scrape.py
python 02_extract.py --limit 100     # smoke test, then without --limit
python 03_gemini_batch.py prepare && python 03_gemini_batch.py run
python 04_build_dataset.py
python 05_analyze.py
python 06_figures.py
python 07_validate.py extract && python 07_validate.py score
```

## Data

`data/sample_100k.csv` is a random sample of 100,000 records from the retrieved corpus (fixed seed), in the same
format as the full corpus, with account names replaced by anonymous identifiers (one identifier per account).
`data/validation_sample_ids.csv` lists the 2,000 records used for validation. The full corpus can be rebuilt with
`01_scrape.py`; it is not redistributed in full in line with Reddit's terms for public content.

## License

MIT
