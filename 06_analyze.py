"""Step 5 — all numbers reported in the Results, Table 1, Table 2 and the figures -> data/results.json.

Analysis population: records from included accounts that describe the author's own peptide use, excluding records
whose named substance is not a peptide. Each field's denominator is the records that addressed it.

    python 05_analyze.py
"""
import json, math, re
from collections import Counter
import duckdb, pandas as pd
import config as C
from definitions import RECODE, ae_groups, frequency, CONTINUOUS

con = duckdb.connect(str(C.DB), read_only=True)
allrec = con.execute("select * exclude (notable_quote) from records").df()
clean = allrec[~allrec.excluded_account]
X = clean[clean.self_use & (clean.peptide_class != "nonpeptide")].copy()
first = lambda s: s.fillna("").str.lower().str.split("|").str[0].str.strip()


def dist(field, df=X):
    v = first(df[field]); v = v[~v.isin(C.NULLS)].map(RECODE.get(field, lambda x: x)).dropna()
    n = int(len(v)); c = v.value_counts()
    return {"n": n, "pct": (c / n * 100).round(1).to_dict(), "count": c.to_dict()}


def numeric(field, lo, hi, df=X):
    v = pd.to_numeric(df[field], errors="coerce"); v = v[(v >= lo) & (v <= hi)]
    return {"n": int(len(v)), "median": float(v.median()), "q1": float(v.quantile(.25)), "q3": float(v.quantile(.75))}


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round((c - h) * 100, 2), round((c + h) * 100, 2)


R = {}
# ---- cohort and flow
R["flow"] = {"records": len(allrec), "excluded_account_records": int(allrec.excluded_account.sum()),
             "excluded_accounts": int(allrec[allrec.excluded_account].author.nunique()), "analysed": len(clean),
             "unique_accounts": int(clean.author.nunique()), "self_use": int(clean.self_use.sum()),
             "peptide_named": int((clean.self_use & (clean.peptide_class == "peptide")).sum()),
             "no_peptide_named": int((clean.self_use & (clean.peptide_class == "unspecified")).sum())}
R["annual_records"] = clean.groupby("yr").size().to_dict()
R["age"], R["sex"] = numeric("age", 13, 95), dist("sex")
# ---- categorical fields
R["fields"] = {f: dist(f) for f in RECODE if f in X}
R["cost_per_vial_usd"] = numeric("cost_amount", 1, 5000, X[first(X.cost_unit).eq("per_vial") &
                                  first(X.cost_currency).isin(["", "usd", "$", "us$", "dollars", "null"])])
R["cycle_weeks"] = numeric("cycle_duration_weeks", 0.5, 104)
w = pd.to_numeric(X.cycle_duration_weeks, errors="coerce"); hw = w.between(0.5, 104)
cont = X.cycle_pattern.fillna("").str.lower().str.contains(CONTINUOUS); nc = int((hw | cont).sum())
R["cycle_extra"] = {"n": nc, "pct_4wk": round((hw & (w == 4)).sum() / nc * 100, 1), "pct_8wk": round((hw & (w == 8)).sum() / nc * 100, 1),
                    "pct_continuous": round((cont & ~hw).sum() / nc * 100, 1)}
fq = X.cycle_pattern.map(frequency).dropna()
R["dosing_frequency"] = {"n": int(len(fq)), "pct": (fq.value_counts(normalize=True) * 100).round(1).to_dict()}
sol = X.reconstitution_solvent.fillna("").str.lower(); sol = sol[~sol.isin(C.NULLS)]
R["nonpharmaceutical_water"] = {"n": int(len(sol)), "k": int(sol.str.contains(r"\btap\b|distilled|spring|bottled|filtered|boiled|purified|reverse osmosis").sum())}
vend = X.specific_vendor_name.fillna("").str.lower().str.strip(); vend = vend[~vend.isin(C.NULLS | {"other"})]
R["vendor"] = {"n": int(len(vend)), "peptide_sciences": int((vend.str.contains(r"peptide ?sciences?|peptidesciences") | (vend == "ps")).sum())}
# ---- adverse events
has = X.side_effects.fillna("").str.strip().str.lower().map(lambda s: s not in C.NULLS)
groups = X.loc[has, "side_effects"].map(ae_groups)
cnt = Counter(g for gs in groups for g in gs); n_ae = int(has.sum())
R["adverse_events"] = {"n": n_ae, "groups": [{"group": g, "records": k, "pct": round(k / n_ae * 100, 2), "ci95": wilson(k, n_ae)}
                                            for g, k in cnt.most_common() if g != "Other / unclassified"]}
# ---- Table 1 (by category)
P = X[X.peptide_class == "peptide"]; N = len(P); t1 = []
for cat, g in P.groupby("category"):
    route = first(g.route).map(RECODE["route"]); route = route[~route.isin(C.NULLS | {"other"})]
    fr = g.cycle_pattern.map(frequency).dropna()
    ae = g.loc[g.side_effects.fillna("").str.strip().str.lower().map(lambda s: s not in C.NULLS), "side_effects"].map(ae_groups)
    aec = Counter(x for gs in ae for x in gs if x != "Other / unclassified")
    top = lambda s: (s.value_counts().index[0], round(s.value_counts().iloc[0] / len(s) * 100)) if len(s) else None
    t1.append({"category": cat, "records": len(g), "pct": round(len(g) / N * 100, 1),
               "peptides": [(p, k, round(k / N * 100, 1)) for p, k in g.peptide.value_counts().head(5).items()],
               "route": top(route), "frequency": top(fr),
               "complication": (aec.most_common(1)[0][0], round(aec.most_common(1)[0][1] / len(ae) * 100)) if len(ae) else None})
R["table1"] = sorted(t1, key=lambda r: -r["records"])
# ---- Figure 2 (satisfaction by category)
FIG2 = {"GLP-1/GIP receptor agonists": P.category.str.startswith("GLP-1"), "Tissue-repair and skin peptides": P.category.eq("Tissue-repair and skin peptides"),
        "Growth-hormone axis peptides": P.category.str.startswith("Growth-hormone")}
FIG2["Other peptides"] = ~(FIG2["GLP-1/GIP receptor agonists"] | FIG2["Tissue-repair and skin peptides"] | FIG2["Growth-hormone axis peptides"])
R["figure2"] = {f: {g: dist(f, P[m]) for g, m in FIG2.items()} for f in ("believed_effective", "would_use_again", "would_recommend")}

C.DATA.joinpath("results.json").write_text(json.dumps(R, indent=1, default=str))
print(json.dumps(R["flow"], indent=1))
