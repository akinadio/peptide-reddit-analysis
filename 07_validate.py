"""Step 7 — validation on the 2,000-record sample (data/validation_sample_ids.csv).

Each sampled record is re-extracted with Gemini 2.5 Flash-Lite and Claude Sonnet 4.6 using the identical prompt.
For each key field the 2-of-3 majority (primary, Gemini, Claude) is the reference; we report the primary model's
accuracy, recall, precision, omissions, commissions and substitutions -> data/validation_metrics.csv.

    python 07_validate.py extract    # run Gemini + Claude on the sample (resumable)
    python 07_validate.py score      # majority vote and metrics
"""
import csv, json, os, sys
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from dotenv import load_dotenv
import config as C, prompt as Pm
from definitions import classify

KEY = ["is_patient_post", "substance_name", "primary_goal", "route", "source_type", "believed_effective",
       "side_effects", "aware_fda_status", "evidence_basis_cited", "provider_type"]
V = C.DATA / "validation"


def extract():
    load_dotenv(); V.mkdir(parents=True, exist_ok=True)
    import anthropic
    from openai import OpenAI
    gem = OpenAI(api_key=os.environ["GEMINI_API_KEY"], base_url="https://generativelanguage.googleapis.com/v1beta/openai")
    cla = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    ids = set(pd.read_csv(C.DATA / "validation_sample_ids.csv", dtype=str).id)
    csv.field_size_limit(1 << 28)
    rows = [r for r in csv.DictReader(open(C.RAW_CSV, encoding="utf-8")) if r["id"] in ids]
    models = {
        "gemini": lambda r: gem.chat.completions.create(model=C.FALLBACK_MODEL, temperature=0, response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": Pm.SYSTEM_PROMPT}, {"role": "user", "content": Pm.user_message(r)}]).choices[0].message.content,
        "claude": lambda r: cla.messages.create(model=C.VALIDATOR_MODEL, max_tokens=2000,
                    system=Pm.SYSTEM_PROMPT + "\n\nJSON schema (return exactly these keys):\n" + json.dumps(Pm.SCHEMA["schema"]),
                    messages=[{"role": "user", "content": Pm.user_message(r)}]).content[0].text}
    for name, call in models.items():
        out = V / f"{name}.jsonl"; done = {json.loads(l)["id"] for l in out.open()} if out.exists() else set()
        def one(r):
            for _ in range(5):
                try: return {"id": r["id"], **Pm.parse_json(call(r))}
                except Exception: pass
        with ThreadPoolExecutor(8) as ex, out.open("a") as f:
            for res in ex.map(one, [r for r in rows if r["id"] not in done]):
                if res: f.write(json.dumps(res, ensure_ascii=False) + "\n"); f.flush()
        print(name, "done")


def norm(field, v):
    v = ("|".join(map(str, v)) if isinstance(v, list) else str(v if v is not None else "")).strip().lower()
    if field != "side_effects": v = v.split("|")[0].strip()
    if v in C.NULLS: return ""
    if field == "substance_name": c = classify(v); return c[1] if isinstance(c, tuple) else v
    if field == "side_effects": return "present"
    return {"yes": "true", "no": "false", "research_peptide_site": "online_vendor", "intranasal": "nasal", "oral": "oral_capsule"}.get(v, v)


def score():
    prim = {p.stem: json.loads(p.read_text()) for p in (C.PRIMARY_DIR / f"{i}.json" for i in
            pd.read_csv(C.DATA / "validation_sample_ids.csv", dtype=str).id) if p.exists()}
    other = {n: {d["id"]: d for d in map(json.loads, (V / f"{n}.jsonl").open())} for n in ("gemini", "claude")}
    ids = sorted(set(prim) & set(other["gemini"]) & set(other["claude"])); rows = []
    for f in KEY:
        t = []
        for i in ids:
            a, b, c = (norm(f, src[i].get(f)) for src in (prim, other["gemini"], other["claude"]))
            ref = a if a in (b, c) else b if b == c else None          # 2-of-3 majority; None = no majority
            if ref is not None:
                t.append((a, ref, "correct" if a == ref else "omission" if not a else "commission" if not ref else "substitution"))
        d = pd.DataFrame(t, columns=["model", "ref", "result"]); ok = d.result.eq("correct")
        rows.append({"field": f, "records_with_majority": len(d), "accuracy": round(ok.mean() * 100, 1),
                     "recall": round((ok & d.ref.ne("")).sum() / max(1, d.ref.ne("").sum()) * 100, 1),
                     "precision": round((ok & d.model.ne("")).sum() / max(1, d.model.ne("").sum()) * 100, 1),
                     **{k: int(d.result.eq(k).sum()) for k in ("omission", "commission", "substitution")}})
    pd.DataFrame(rows).to_csv(C.DATA / "validation_metrics.csv", index=False); print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    {"extract": extract, "score": score}[sys.argv[1]]()
