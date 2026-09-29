"""Step 8 — extraction validation -> <run>/validation.json (<run> = config.RUN_DIR).

    python 08_validation.py agreement   # model agreement, omissions and adjudication (no API calls)
    python 08_validation.py sample      # draw the manual-review sample -> <run>/manual_review_sample.csv
    python 08_validation.py score       # compare <run>/manual_review_completed.csv with the consensus

agreement: for every compared field, agreement between GPT-4o-mini and Gemini 2.5 Flash-Lite over all records
  extracted by both models (both empty counts as agreement) and over records where at least one model returned a
  value; the share of disagreements that are omissions (one model returned a value, the other none); and, from the
  consensus, how many disputed fields were resolved by majority and how many had no majority.
sample: config.REVIEW_N records drawn at random (seed config.REVIEW_SEED) from the analytic sample. One row per
  record and compared field, with the consensus value; the reviewer fills `reviewer_value` from the original text and
  saves the file as <run>/manual_review_completed.csv. The record ids are also written to <run>/manual_review_ids.csv and
  data/manual_review_ids.csv (committed to the repository).
score: proportion of (record, field) pairs on which the reviewer and the consensus agree, overall and by field.
"""
import json, sys
import duckdb, pandas as pd
import config as C, corpus
from definitions import norm

OUT = C.VALIDATION
update = lambda k, v: OUT.write_text(json.dumps((json.loads(OUT.read_text()) if OUT.exists() else {}) | {k: v}, indent=1))


def agreement():
    prim = {}
    for p in C.PRIMARY_DIR.glob("*.json"):
        try: prim[p.stem] = json.loads(p.read_text())
        except Exception: pass
    gem = {r["key"]: r["data"] for f in sorted(C.GEMINI_DIR.glob("*.jsonl")) for r in map(json.loads, open(f)) if r.get("data")}
    both = prim.keys() & gem.keys()
    per, dis, omit = {}, 0, 0
    for f in C.COMPARE_FIELDS:
        n = agree = n_any = agree_any = 0
        for rid in both:
            a, b = norm(f, prim[rid].get(f)), norm(f, gem[rid].get(f))
            n += 1; agree += a == b
            if a or b:
                n_any += 1; agree_any += a == b
            if a != b:
                dis += 1; omit += (a == "") != (b == "")
        per[f] = {"records": n, "agreement_pct": round(agree / n * 100, 1) if n else None,
                  "records_with_a_value": n_any, "agreement_when_a_value_pct": round(agree_any / n_any * 100, 1) if n_any else None}
    cons = [json.loads(l) for l in open(C.CONSENSUS)]
    res = {"records_extracted_by_both": len(both), "fields": per,
           "agreement_range_pct": [min(v["agreement_pct"] for v in per.values() if v["agreement_pct"] is not None),
                                   max(v["agreement_pct"] for v in per.values() if v["agreement_pct"] is not None)],
           "disagreements": dis, "omission_share_pct": round(omit / dis * 100, 1) if dis else None,
           "fields_without_majority": sum(len(r.get("no_majority", [])) for r in cons)}
    update("model_agreement", res); print(json.dumps({k: v for k, v in res.items() if k != "fields"}, indent=1))


def sample():
    ids = duckdb.connect(str(C.DB), read_only=True).execute("select id from records where analytic").df().id
    pick = ids.sample(n=min(C.REVIEW_N, len(ids)), random_state=C.REVIEW_SEED)
    text = corpus.load().set_index("id").loc[pick.to_numpy(), ["subreddit", "kind", "permalink", "title", "body"]]
    cons = {r["id"]: r for r in map(json.loads, open(C.CONSENSUS)) if r["id"] in set(pick)}
    val = lambda v: "|".join(map(str, v)) if isinstance(v, list) else ("" if v is None else v)
    rows = [{"id": i, **text.loc[i].to_dict(), "field": f, "consensus_value": val(cons.get(i, {}).get(f)), "reviewer_value": ""}
            for i in pick for f in C.COMPARE_FIELDS]
    pd.DataFrame(rows).to_csv(C.RUN_DIR / "manual_review_sample.csv", index=False)
    for d in (C.RUN_DIR, C.DATA): pick.to_frame().to_csv(d / "manual_review_ids.csv", index=False)
    print(f"{len(pick)} records x {len(C.COMPARE_FIELDS)} fields -> {C.RUN_DIR / 'manual_review_sample.csv'}")


def score():
    d = pd.read_csv(C.RUN_DIR / "manual_review_completed.csv", dtype=str, keep_default_na=False)
    d["agree"] = [norm(f, a) == norm(f, b) for f, a, b in zip(d.field, d.consensus_value, d.reviewer_value)]
    res = {"records": int(d.id.nunique()), "pairs": len(d), "agreement_pct": round(d.agree.mean() * 100, 1),
           "by_field_pct": (d.groupby("field").agree.mean() * 100).round(1).to_dict()}
    update("manual_review", res); print(json.dumps({k: v for k, v in res.items() if k != "by_field_pct"}, indent=1))


if __name__ == "__main__":
    {"agreement": agreement, "sample": sample, "score": score}[sys.argv[1]]()
