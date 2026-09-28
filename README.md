# Self-reported use and perception of peptide therapy on Reddit

Code for *Self-Reported Use and Perception of Peptide Therapy: A Cross-Sectional Analysis of Over One Million Online Discussions*.

The pipeline retrieves public posts and comments from eight peptide-focused and biohacking Reddit communities,
extracts 44 structured fields from each record with large language models, and produces every number, table and
figure reported in the paper.

## Three-step extraction

1. **GPT-4o-mini** extracts every record (temperature 0, fixed prompt and JSON schema in `prompt.py`).
2. **Gemini 2.5 Flash-Lite** independently extracts every record with the identical prompt.
3. For fields on which the two disagree, **Claude Sonnet 4.6** acts as a third-model adjudicator; the final value
   of each field is the majority of the three models (fields with no majority keep the first model's value and are flagged).

| Step | Script | What it does |
|---|---|---|
| 1 | `01_scrape.py` | Retrieves posts and comments (Nov 2014 – Jun 2026) from the Arctic Shift Reddit archive |
| 2 | `02_extract.py` | Extraction with GPT-4o-mini |
| 3 | `03_gemini_batch.py` | Independent extraction with Gemini 2.5 Flash-Lite (Batch API) |
| 4 | `04_adjudicate.py` | Compares the two, adjudicates disagreements with Claude Sonnet 4.6 (Batch API), writes the consensus |
| 5 | `05_build_dataset.py` | Keeps the eight communities, flags bot/moderator/deleted accounts, classifies peptides |
| 6 | `06_analyze.py` | All reported statistics, Table 1, Table 2 and figure data → `data/results.json` |
| 7 | `07_figures.py` | Figures 1–3 |

Shared definitions: `config.py` (paths, communities, models, compared fields), `prompt.py` (prompt and schema),
`definitions.py` (peptide categories, adverse-event groups, recodes, value comparison).

## Run

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY
python 01_scrape.py
python 02_extract.py --limit 100     # smoke test, then without --limit
python 03_gemini_batch.py prepare && python 03_gemini_batch.py run
python 04_adjudicate.py estimate     # number of disputed records and cost estimate
python 04_adjudicate.py submit       # then re-run `collect` until all batches are collected
python 04_adjudicate.py collect
python 04_adjudicate.py consensus
python 05_build_dataset.py
python 06_analyze.py
python 07_figures.py
```

## Data

`data/sample_100k.csv` is a random sample of 100,000 records from the retrieved corpus (fixed seed), in the same
format as the full corpus, with account names replaced by anonymous identifiers (one identifier per account;
see `make_sample.py`). The full corpus can be rebuilt with `01_scrape.py`; it is not redistributed in full in line
with Reddit's terms for public content.

## License

MIT
