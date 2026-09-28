"""Step 4 — adjudication and consensus.

For each record, the primary (GPT-4o-mini) and second (Gemini 2.5 Flash-Lite) extractions are compared field by field.
Fields that disagree are sent to Claude Sonnet 4.6 (Anthropic Message Batches API; the instructions are prompt-cached
and only the disputed fields are requested). The final value of each field is the majority of the three models;
fields on which all three disagree keep the primary value and are flagged.

    python 04_adjudicate.py estimate    # count disputed records and estimate cost (no API calls)
    python 04_adjudicate.py submit      # send disputed records to Claude in batches of 20,000
    python 04_adjudicate.py collect     # download finished batches (re-run until all are collected)
    python 04_adjudicate.py consensus   # write data/consensus.jsonl
"""
import csv, json, os, sys
import anthropic
from dotenv import load_dotenv
import config as C, prompt as Pm
from definitions import norm

BATCHES = C.CLAUDE_DIR / "batches.json"


def load(source):
    if source == "primary":
        out = {}
        for p in C.PRIMARY_DIR.glob("*.json"):
            try: out[p.stem] = json.loads(p.read_text())
            except Exception: pass
        return out
    rows = (json.loads(l) for f in sorted(C.GEMINI_DIR.glob("*.jsonl")) for l in f.read_text().splitlines() if l.strip())
    return {r["key"]: r["data"] or {} for r in rows}


def disputes():
    prim, gem = load("primary"), load("gemini")
    for rid in prim.keys() | gem.keys():
        a, b = prim.get(rid) or {}, gem.get(rid) or {}
        fields = [f for f in C.COMPARE_FIELDS if norm(f, a.get(f)) != norm(f, b.get(f))]
        yield rid, a, b, fields


def estimate():
    n = k = 0
    for _, _, _, f in disputes():
        n += 1; k += bool(f)
    # Sonnet batch prices (USD per million tokens; check current pricing): input 1.50, cached input 0.15, output 7.50
    cost = k * (400 * 1.50 + 2200 * 0.15 + 90 * 7.50) / 1e6
    print(f"{n:,} records; {k:,} ({k / n:.1%}) have at least one disputed field; estimated Claude cost ≈ ${cost:,.0f}")


def submit(batch_size=20_000):          # Anthropic limit: 100,000 requests or 256 MB per batch
    load_dotenv(); client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]); C.CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    done = json.loads(BATCHES.read_text()) if BATCHES.exists() else []
    sent = {i for b in done for i in b["ids"]}
    csv.field_size_limit(1 << 28)
    text = {r["id"]: r for r in csv.DictReader(open(C.RAW_CSV, encoding="utf-8"))}
    system = [{"type": "text", "cache_control": {"type": "ephemeral"},
               "text": Pm.SYSTEM_PROMPT + "\nJSON schema:\n" + json.dumps(Pm.SCHEMA["schema"])}]
    reqs = [{"custom_id": rid, "params": {"model": C.ADJUDICATOR_MODEL, "max_tokens": 600, "system": system, "messages": [{"role": "user",
             "content": Pm.user_message(text[rid], C.MAX_BODY_CHARS) + "\nReturn a JSON object with only these keys: " + ", ".join(f)}]}}
            for rid, _, _, f in disputes() if f and rid not in sent and rid in text]
    for i in range(0, len(reqs), batch_size):
        chunk = reqs[i:i + batch_size]
        b = client.messages.batches.create(requests=chunk)
        done.append({"id": b.id, "ids": [r["custom_id"] for r in chunk], "collected": False})
        BATCHES.write_text(json.dumps(done)); print("submitted", b.id, len(chunk))


def collect():
    load_dotenv(); client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    done = json.loads(BATCHES.read_text())
    for b in done:
        if b["collected"] or client.messages.batches.retrieve(b["id"]).processing_status != "ended": continue
        with open(C.CLAUDE_DIR / f"{b['id']}.jsonl", "w") as f:
            for r in client.messages.batches.results(b["id"]):
                try: data = Pm.parse_json(r.result.message.content[0].text) if r.result.type == "succeeded" else None
                except Exception: data = None
                f.write(json.dumps({"id": r.custom_id, "data": data}, ensure_ascii=False) + "\n")
        b["collected"] = True; BATCHES.write_text(json.dumps(done)); print("collected", b["id"])
    print(sum(b["collected"] for b in done), "of", len(done), "batches collected")


def consensus():
    claude = {r["id"]: r["data"] or {} for f in C.CLAUDE_DIR.glob("msgbatch_*.jsonl") for r in map(json.loads, open(f))}
    stats = {"records": 0, "adjudicated_fields": 0, "no_majority_fields": 0}
    with open(C.CONSENSUS, "w") as out:
        for rid, a, b, fields in disputes():
            final, c, flagged = dict(a or b), claude.get(rid, {}), []
            for f in fields:
                va, vb, vc = norm(f, a.get(f)), norm(f, b.get(f)), norm(f, c.get(f))
                if va == vc: final[f] = a.get(f)          # primary + Claude agree
                elif vb == vc: final[f] = b.get(f)        # Gemini + Claude agree
                else: final[f] = a.get(f); flagged.append(f)   # no majority: keep primary, flag
            stats["records"] += 1; stats["adjudicated_fields"] += len(fields); stats["no_majority_fields"] += len(flagged)
            out.write(json.dumps({"id": rid, "no_majority": flagged, **final}, ensure_ascii=False) + "\n")
    print(stats)


if __name__ == "__main__":
    {"estimate": estimate, "submit": submit, "collect": collect, "consensus": consensus}[sys.argv[1]]()
