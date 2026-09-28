"""Step 5 — build the analysis table (data/peptides.duckdb, table `records`) from the consensus extraction.

Keeps the eight study communities, flags bot/moderator/deleted accounts, marks self-reported use, and assigns each
record a peptide category (comments that name no substance inherit the substance of the post they reply to).

    python 05_build_dataset.py
"""
import json
import duckdb, pandas as pd
import config as C, prompt as Pm
from definitions import classify

flat = lambda d: {k: ("|".join(map(str, d.get(k))) if isinstance(d.get(k), list) else d.get(k)) for k in Pm.FIELDS}


def main():
    ext = pd.DataFrame([{"id": r["id"], **flat(r)} for r in map(json.loads, open(C.CONSENSUS))]).astype({k: "string" for k in Pm.FIELDS})
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
