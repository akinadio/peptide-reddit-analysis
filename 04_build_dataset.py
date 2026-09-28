"""Step 4 — build the analysis table (data/peptides.duckdb, table `records`).

Primary-model output is used for every record; Gemini output is used where the primary model returned nothing usable.
Keeps the eight study communities, flags bot/moderator/deleted accounts, marks self-reported use, and assigns each
record a peptide category (comments that name no substance inherit the substance of the post they reply to).

    python 04_build_dataset.py
"""
import json
from concurrent.futures import ThreadPoolExecutor
import duckdb, pandas as pd
import config as C, prompt as Pm
from definitions import classify

flat = lambda d: {k: ("|".join(map(str, d.get(k))) if isinstance(d.get(k), list) else d.get(k)) for k in Pm.FIELDS}


def load_primary():
    def read(p):
        try: d = json.loads(p.read_text()); return (p.stem, d) if d else None
        except Exception: return None
    with ThreadPoolExecutor(32) as ex:
        hits = [h for h in ex.map(read, C.PRIMARY_DIR.glob("*.json"), chunksize=2000) if h]
    return pd.DataFrame([{"id": i, "source": "primary", **flat(d)} for i, d in hits])


def load_gemini():
    rows = [json.loads(l) for f in sorted(C.GEMINI_DIR.glob("*.jsonl")) for l in f.read_text().splitlines() if l.strip()]
    return pd.DataFrame([{"id": r["key"], "source": "gemini", **flat(r["data"])} for r in rows if r.get("data")])


def main():
    prim, gem = load_primary(), load_gemini()
    ext = pd.concat([prim, gem[~gem.id.isin(prim.id)]], ignore_index=True).astype({k: "string" for k in Pm.FIELDS})
    con = duckdb.connect(str(C.DB)); con.register("ext", ext)
    subs = ", ".join(f"'{s.lower()}'" for s in C.COMMUNITIES)
    canon = " ".join(f"when '{s.lower()}' then '{s}'" for s in C.COMMUNITIES)
    con.execute(f"""
        create or replace table records as
        select r.id, case lower(r.subreddit) {canon} end as subreddit, r.kind, r.parent_post_id, r.author,
               to_timestamp(r.created_utc::double) as ts, year(to_timestamp(r.created_utc::double)) as yr,
               regexp_matches(r.author, '{C.BOT_REGEX}') as excluded_account,
               lower(e.is_patient_post) = 'true' as self_use, e.* exclude (id)
        from read_csv('{C.RAW_CSV}', all_varchar=true, strict_mode=false) r join ext e on e.id = r.id
        where lower(r.subreddit) in ({subs})""")
    # peptide category, with parent-post inheritance for comments naming no peptide
    d = con.execute("select id, kind, parent_post_id, substance_name from records").df()
    d["c"] = d.substance_name.map(classify)
    pep = d.c.map(lambda c: isinstance(c, tuple))
    own = d[pep].set_index("id").c
    inherit = ~pep & (d.kind == "comment")
    d.loc[inherit, "c"] = d.loc[inherit, "parent_post_id"].map(own).where(lambda s: s.notna(), d.loc[inherit, "c"])
    d["category"] = d.c.map(lambda c: c[0] if isinstance(c, tuple) else None)
    d["peptide"] = d.c.map(lambda c: c[1] if isinstance(c, tuple) else None)
    d["peptide_class"] = d.c.map(lambda c: "peptide" if isinstance(c, tuple) else "nonpeptide" if c == "nonpeptide" else "unspecified")
    d["inherited"] = inherit & d.category.notna()
    con.register("cls", d[["id", "category", "peptide", "peptide_class", "inherited"]])
    con.execute("create or replace table records as select * from records join cls using (id)")
    print(con.execute("""select count(*) records, sum(excluded_account::int) excluded,
                         sum((self_use and not excluded_account)::int) self_use,
                         sum((self_use and not excluded_account and peptide_class='peptide')::int) peptide_named from records""").df())


if __name__ == "__main__":
    main()
