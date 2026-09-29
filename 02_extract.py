"""Step 2 — structured extraction with the primary model (GPT-4o-mini, temperature 0, JSON schema).

Every record in the study communities and period is extracted, except records from excluded accounts and identical
text reposted by the same account (see corpus.py). There is no cap on the number of records and no prioritisation.

Outputs go to the run folder (config.RUN_DIR, data/runs/<corpus>_<fingerprint>/), one JSON file per record. Outputs
from earlier runs are never reused: a run made with a different model, prompt, schema or setting gets a new folder, and
the pre-run-folder caches (data/llm_outputs etc.) are not read. Within one run the script is resumable: re-running it
after an interruption only sends records that do not yet have an output in this run's folder. Records that fail four
attempts are logged as <id>.err.txt and retried on the next run (use --retry-failed-only to retry only those).

The model version returned by the API for each request (e.g. the dated snapshot behind "gpt-4o-mini") and the dates
of the run are recorded in run_manifest.json for reporting in the Methods.

    python 02_extract.py                 # full run (new run folder unless this exact configuration was started before)
    python 02_extract.py --limit 100     # smoke test
    RUN_TAG=rerun2 python 02_extract.py  # force a separate, fresh run folder even with identical settings
    CORPUS=data/sample_100k.csv python 02_extract.py --limit 100   # smoke test on the public sample
"""
import argparse, asyncio, json, os
from collections import Counter
from datetime import datetime, timezone
from openai import AsyncOpenAI
from dotenv import load_dotenv
from tqdm.asyncio import tqdm
import config as C, prompt as Pm, corpus

MODELS = Counter()          # model version reported by the API -> number of records


def select(limit=None, retry_failed_only=False):
    rows = corpus.eligible_for_extraction().to_dict("records")
    done = {p.stem for p in C.PRIMARY_DIR.glob("*.json")}
    failed = {p.name.split(".")[0] for p in C.PRIMARY_DIR.glob("*.err.txt")}
    todo = [r for r in rows if r["id"] not in done and (not retry_failed_only or r["id"] in failed)]
    print(f"run folder: {C.RUN_DIR}")
    print(f"{len(rows):,} eligible records; {len(done):,} already extracted in this run; {len(todo):,} to send")
    legacy = [d for d in C.LEGACY_DIRS if d.exists() and any(d.iterdir())]
    if legacy:
        print("note: outputs from earlier runs in " + ", ".join(map(str, legacy)) + " are ignored")
    return todo[:limit] if limit else todo


async def extract(client, row, sem):
    err = ""
    async with sem:
        for attempt in range(4):
            try:
                resp = await client.chat.completions.create(
                    model=C.PRIMARY_MODEL, temperature=C.TEMPERATURE,
                    response_format={"type": "json_schema", "json_schema": Pm.SCHEMA},
                    messages=[{"role": "system", "content": Pm.SYSTEM_PROMPT},
                              {"role": "user", "content": Pm.user_message(row, C.MAX_BODY_CHARS)}])
                d = Pm.parse_json(resp.choices[0].message.content)
                (C.PRIMARY_DIR / f"{row['id']}.json").write_text(json.dumps(d, ensure_ascii=False))
                (C.PRIMARY_DIR / f"{row['id']}.err.txt").unlink(missing_ok=True)
                MODELS[resp.model] += 1
                return
            except Exception as e:
                err = str(e)[:300]
                await asyncio.sleep(4 * 2 ** attempt)
        (C.PRIMARY_DIR / f"{row['id']}.err.txt").write_text(err)   # retried on the next run; also sent to Gemini (03)


async def main(limit, concurrency, retry_failed_only):
    load_dotenv(); C.PRIMARY_DIR.mkdir(parents=True, exist_ok=True)
    todo = select(limit, retry_failed_only)
    print(f"{len(todo):,} records to extract with {C.PRIMARY_MODEL}")
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    C.manifest(primary_started_utc=C.manifest().get("primary_started_utc") or started)
    client, sem = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"]), asyncio.Semaphore(concurrency)
    try:
        await tqdm.gather(*(extract(client, r, sem) for r in todo))
    finally:   # record model versions and counts even if the run is interrupted
        prev = C.manifest().get("primary_model_versions", {})
        C.manifest(primary_model_versions={m: prev.get(m, 0) + n for m, n in MODELS.items()},
                   primary_last_run_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   primary_records_extracted=len(list(C.PRIMARY_DIR.glob("*.json"))),
                   primary_records_failed=len(list(C.PRIMARY_DIR.glob("*.err.txt"))))
        print("model versions:", dict(MODELS) or "none this session")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int); ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--retry-failed-only", action="store_true")
    a = ap.parse_args(); asyncio.run(main(a.limit, a.concurrency, a.retry_failed_only))
