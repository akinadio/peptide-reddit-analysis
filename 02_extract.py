"""Step 2 — structured extraction with the primary model (GPT-4o-mini, temperature 0, JSON schema).

Records of >=50 characters are prioritised (first-person posts naming a peptide first, then other posts, then
comments; longest first within each tier) up to one million records. One JSON file is cached per record, so the
run is resumable.

    python 02_extract.py               # full run
    python 02_extract.py --limit 100   # smoke test
"""
import argparse, asyncio, csv, json, os, re
from openai import AsyncOpenAI
from dotenv import load_dotenv
from tqdm.asyncio import tqdm
import config as C, prompt as Pm

FIRST_PERSON = re.compile(r"\b(I|i'm|my|me|myself)\b")
NAMED = re.compile(r"\b(bpc[-\s]?157|tb[-\s]?500|thymosin|ipamorelin|cjc[-\s]?1295|sermorelin|tesamorelin|ghk[-\s]?cu|mgf|ghrp[-\s]?6|"
                   r"kpv|aod[-\s]?9604|igf[-\s]?1\s*lr3|semaglutide|tirzepatide|retatrutide|melanotan|pt[-\s]?141|selank|semax|"
                   r"epitalon|hexarelin|hgh|dsip|ss[-\s]?31|cerebrolysin|mots[-\s]?c)\b", re.I)


def tier(r):
    text = f"{r['title']} {r['body']}".strip()
    post, fp, pep, long = r["kind"] == "post", bool(FIRST_PERSON.search(text)), bool(NAMED.search(text)), len(text) >= 150
    order = [(post and fp and pep), (post and fp), (post and pep), (fp and pep), post, fp, pep]
    return next((i + 1 for i, hit in enumerate(order) if long and hit), 8), -len(text)


def select(limit=None):
    csv.field_size_limit(1 << 28)
    rows = [r for r in csv.DictReader(open(C.RAW_CSV, encoding="utf-8"))
            if len(f"{r['title']} {r['body']}".strip()) >= C.MIN_CHARS]
    rows = sorted(rows, key=tier)[:C.TARGET_RECORDS]
    todo = [r for r in rows if not (C.PRIMARY_DIR / f"{r['id']}.json").exists()]
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
