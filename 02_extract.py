"""Step 2 — structured extraction with the primary model (GPT-4o-mini, temperature 0, JSON schema).

Every record in the study communities and period is extracted, except records from excluded accounts and identical
text reposted by the same account (see corpus.py). One JSON file is cached per record, so the run is resumable and
records extracted in earlier runs are not sent again.

    python 02_extract.py               # full run
    python 02_extract.py --limit 100   # smoke test
    CORPUS=data/sample_100k.csv python 02_extract.py --limit 100   # smoke test on the public sample
"""
import argparse, asyncio, json, os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from tqdm.asyncio import tqdm
import config as C, prompt as Pm, corpus


def select(limit=None):
    rows = corpus.eligible_for_extraction().to_dict("records")
    todo = [r for r in rows if not (C.PRIMARY_DIR / f"{r['id']}.json").exists()]
    print(f"{len(rows):,} eligible records; {len(rows) - len(todo):,} already extracted")
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
                return
            except Exception as e:
                err = str(e)[:300]
                await asyncio.sleep(4 * 2 ** attempt)
        (C.PRIMARY_DIR / f"{row['id']}.err.txt").write_text(err)   # picked up by 03_gemini_batch.py


async def main(limit, concurrency):
    load_dotenv(); C.PRIMARY_DIR.mkdir(parents=True, exist_ok=True)
    todo = select(limit)
    print(f"{len(todo):,} records to extract with {C.PRIMARY_MODEL}")
    client, sem = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"]), asyncio.Semaphore(concurrency)
    await tqdm.gather(*(extract(client, r, sem) for r in todo))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int); ap.add_argument("--concurrency", type=int, default=16)
    a = ap.parse_args(); asyncio.run(main(a.limit, a.concurrency))
