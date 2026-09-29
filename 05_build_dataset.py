"""Step 5 — build the analysis table (<run>/peptides.duckdb, table `records`) and the record flow (<run>/flow.json).

Each retrieved record is assigned a peptide category (comments that name no substance inherit the substance of the
post they reply to) and is then counted at the first exclusion that applies, in this order:
  1. deleted, AutoModerator, bot or moderator-team account;
  2. identical text reposted by the same account (earliest copy kept);
  3. no extraction output from any model;
  4. does not describe the author's own peptide use (is_patient_post not true), e.g. use by someone else or
     informational discussion;
  5. named substance is not a peptide (e.g. MK-677 named first);
  6. additional records from users who still have more than one record (the earliest is kept).
The remaining records form the analytic sample: one record per user, so the unit of analysis is the user.

    python 05_build_dataset.py
"""
import json
import duckdb, pandas as pd
import config as C, prompt as Pm, corpus
from definitions import classify

STEPS = ["excluded_account", "duplicate_text", "no_extraction", "not_own_use", "nonpeptide_substance", "repeat_user"]
flat = lambda d: {k: ("|".join(map(str, d.get(k))) if isinstance(d.get(k), list) else d.get(k)) for k in Pm.FIELDS}


def main():
    df = corpus.flag(corpus.load())
    ext = pd.DataFrame([{"id": r["id"], **flat(r)} for r in map(json.loads, open(C.CONSENSUS))]).astype({k: "string" for k in Pm.FIELDS})
    df = df.merge(ext, on="id", how="left", indicator=True)
    df["has_extraction"] = df.pop("_merge").eq("both")
    df["self_use"] = df.is_patient_post.fillna("").str.lower().eq("true")

    # peptide category; comments naming no peptide inherit the peptide of the post they reply to
    c = df.substance_name.fillna("").map(classify)
    pep = c.map(lambda x: isinstance(x, tuple))
    own = pd.Series(c[pep].to_numpy(), index=df.id[pep])
    inherit = ~pep & df.kind.eq("comment")
    parent = df.loc[inherit, "parent_post_id"].map(own)
    c[inherit] = parent.where(parent.notna(), c[inherit])
    df["category"] = c.map(lambda x: x[0] if isinstance(x, tuple) else None)
    df["peptide"] = c.map(lambda x: x[1] if isinstance(x, tuple) else None)
    df["peptide_class"] = c.map(lambda x: "peptide" if isinstance(x, tuple) else "nonpeptide" if x == "nonpeptide" else "unspecified")
    df["inherited"] = inherit & df.category.notna()

    # exclusions, in order; each record is counted once, at the first step that applies
    reason = pd.Series("", index=df.index, dtype=object)
    for name, hit in [("excluded_account", df.excluded_account), ("duplicate_text", df.duplicate),
                      ("no_extraction", ~df.has_extraction), ("not_own_use", ~df.self_use),
                      ("nonpeptide_substance", df.peptide_class.eq("nonpeptide"))]:
        reason[reason.eq("") & hit] = name
    remaining = reason.eq("")
    kept = df[remaining].drop_duplicates("author", keep="first").index      # df is sorted by time: earliest record per user
    reason[remaining & ~df.index.isin(kept)] = "repeat_user"
    df["exclusion"], df["analytic"] = reason, reason.eq("")

    a = df[df.analytic]
    flow = {"retrieved": len(df), **{s: int(reason.eq(s).sum()) for s in STEPS}, "analysed": len(a),
            "analysed_users": int(a.author.nunique()), "start_utc": int(df.created_utc.min()), "end_utc": int(df.created_utc.max())}
    assert flow["analysed"] == flow["analysed_users"], "analytic sample must contain one record per user"
    assert flow["retrieved"] == flow["analysed"] + sum(flow[s] for s in STEPS)
    C.FLOW.write_text(json.dumps(flow, indent=1)); C.manifest(flow=flow)

    df["yr"] = pd.to_datetime(df.created_utc, unit="s", utc=True).dt.year
    out = df.drop(columns=["title", "body", "permalink"], errors="ignore")
    con = duckdb.connect(str(C.DB)); con.register("out", out)
    con.execute("create or replace table records as select * from out")
    print(json.dumps(flow, indent=1))


if __name__ == "__main__":
    main()
