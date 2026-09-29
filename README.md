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
| 1 | `01_scrape.py` | Retrieves posts and comments from the Arctic Shift Reddit archive (the study period, Nov 2014 – Jun 2026, is applied in `corpus.py`) |
| 2 | `02_extract.py` | Extraction with GPT-4o-mini |
| 3 | `03_gemini_batch.py` | Independent extraction with Gemini 2.5 Flash-Lite (Batch API) |
| 4 | `04_adjudicate.py` | Compares the two, adjudicates disagreements with Claude Sonnet 4.6 (Batch API), writes the consensus |
| 5 | `05_build_dataset.py` | Classifies peptides, applies the exclusions in order and keeps one record per user → `<run>/flow.json` |
| 6 | `06_analyze.py` | All reported statistics, Table 1, Table 2 and figure data → `<run>/results.json` |
| 7 | `07_figures.py` | Figures 1–3 and Supplementary Figure 1 (record flow) |
| 8 | `08_validation.py` | Model agreement, omissions, adjudication and manual-review agreement → `<run>/validation.json` |

Shared definitions: `config.py` (paths, communities, study period, models, compared fields), `corpus.py` (corpus loading,
account and duplicate exclusions), `prompt.py` (prompt and schema), `definitions.py` (peptide categories, adverse-event
groups, recodes, value comparison).

## Run folders

Every model output and result is written to one run folder, `data/runs/<corpus>_<fingerprint>/` (`<run>` above).
The fingerprint is a hash of the three models, temperature, truncation length, prompt, schema and compared fields, so:

- a run never reuses model outputs from a run made with different settings;
- outputs from before run folders existed (`data/llm_outputs`, `data/gemini_results`, `data/claude_batches`) are never read;
- an interrupted run resumes in its own folder (records already extracted *in that run* are not sent again);
- `RUN_TAG=<name>` forces a separate, fresh run folder even with identical settings;
- the public sample (`CORPUS=data/sample_100k.csv`) gets its own folder and never mixes with the full corpus.

`<run>/run_manifest.json` records the settings, the dates of each step, the model version returned by each API
(e.g. the dated snapshot behind `gpt-4o-mini`), record counts and the record flow, for reporting in the Methods.

## Study population

Records are counted at the first exclusion that applies (Supplementary Figure 1, `<run>/flow.json`):

1. records from deleted, AutoModerator, bot and moderator-team accounts;
2. identical text reposted by the same account (earliest copy kept);
3. records with no extraction output from any model;
4. records not describing the author's own peptide use;
5. records whose named substance is not a peptide;
6. additional records from users with more than one remaining record (the earliest is kept).

Exclusions 1–2 are applied before extraction. The analytic sample has one post or comment per user, so the unit of
analysis is the user. Comments that name no substance inherit the substance of the post they reply to.

## Run

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY
python 01_scrape.py
python 02_extract.py --limit 100     # smoke test, then without --limit (resumes within the same run folder)
python 03_gemini_batch.py prepare && python 03_gemini_batch.py run
python 04_adjudicate.py estimate     # number of disputed records and cost estimate
python 04_adjudicate.py submit       # then re-run `collect` until all batches are collected
python 04_adjudicate.py collect
python 04_adjudicate.py consensus
python 05_build_dataset.py
python 06_analyze.py
python 07_figures.py
python 08_validation.py agreement
python 08_validation.py sample       # then review the records and save <run>/manual_review_completed.csv
python 08_validation.py score
```

To run on the public sample instead of the full corpus, prefix each command with `CORPUS=data/sample_100k.csv`,
e.g. `CORPUS=data/sample_100k.csv python 02_extract.py --limit 100`.

## Data

`data/sample_100k.csv` is a random sample of 100,000 records from the retrieved corpus (fixed seed), in the same
format as the full corpus, with account names replaced by anonymous identifiers (one identifier per account;
see `make_sample.py`). The full corpus can be rebuilt with `01_scrape.py`; it is not redistributed in full in line
with Reddit's terms for public content.

## License

MIT
