"""Public 100,000-record sample of the retrieved corpus -> data/sample_100k.csv.

Rows are drawn at random (seed 2026). Account names are replaced by an anonymous identifier derived with a keyed
hash (HMAC-SHA256, secret key not published), so each account keeps one consistent identifier but cannot be
recovered by hashing known usernames. Deleted accounts stay "[deleted]".

    SAMPLE_KEY=<any secret> python make_sample.py
"""
import hashlib, hmac, os
import pandas as pd
import config as C

key = os.environ["SAMPLE_KEY"].encode()
anon = lambda a: a if a in ("", "[deleted]") else "u_" + hmac.new(key, a.encode(), hashlib.sha256).hexdigest()[:16]
df = pd.read_csv(C.RAW_CSV, dtype=str, keep_default_na=False, engine="python", on_bad_lines="skip")
s = df.sample(n=100_000, random_state=2026).sort_values(["subreddit", "created_utc"])
s["author"] = s.author.map(anon)
s.drop(columns=[c for c in ("sub_kind",) if c in s]).to_csv(C.DATA / "sample_100k.csv", index=False)
print(len(s), "rows;", s.author.nunique(), "unique accounts")
