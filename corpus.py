"""Corpus loading and the account and duplicate exclusions shared by steps 2, 5 and 8.

Records are ordered chronologically (created_utc, then id). Two exclusions need no model output and are applied
before extraction:
  - records from deleted, AutoModerator, bot and moderator-team accounts (config.BOT_REGEX; empty author = deleted);
  - identical text reposted by the same account (same author, same title + body after lower-casing and collapsing
    whitespace); the earliest copy is kept.
Records dated after the study period (config.STUDY_END_UTC) and outside the eight communities are dropped on load.
"""
import re
import duckdb, pandas as pd
import config as C

_WS = re.compile(r"\s+")
_BOT = re.compile(C.BOT_REGEX)
_CANON = {s.lower(): s for s in C.COMMUNITIES}
COLS = ["id", "subreddit", "kind", "parent_post_id", "author", "created_utc", "title", "body", "permalink"]


def load(path=None):
    """Corpus as a DataFrame of strings (created_utc as int), restricted to the study communities and period."""
    path = str(path or C.RAW_CSV).replace("'", "''")
    df = duckdb.sql(f"select * from read_csv('{path}', all_varchar=true, strict_mode=false)").df()
    df = df[[c for c in COLS if c in df]].fillna("")
    df["created_utc"] = pd.to_numeric(df.created_utc, errors="coerce").fillna(0).astype("int64")
    df["subreddit"] = df.subreddit.str.lower().map(_CANON)
    df = df[df.subreddit.notna() & (df.created_utc < C.STUDY_END_UTC)]
    return df.drop_duplicates("id").sort_values(["created_utc", "id"], kind="stable").reset_index(drop=True)


def flag(df):
    """Adds excluded_account and duplicate (earliest copy of a repeated text by the same account is kept)."""
    df = df.copy()
    df["excluded_account"] = df.author.eq("") | df.author.map(lambda a: bool(_BOT.search(a)))
    key = (df.title + " " + df.body).str.lower().str.replace(_WS, " ", regex=True).str.strip()
    ok = ~df.excluded_account
    df["duplicate"] = False
    df.loc[ok, "duplicate"] = pd.DataFrame({"author": df.author[ok], "text": key[ok]}).duplicated(keep="first").to_numpy()
    return df


def eligible_for_extraction(path=None):
    """Records sent to the models: study communities and period, included accounts, no reposted duplicates."""
    df = flag(load(path))
    return df[~df.excluded_account & ~df.duplicate]
