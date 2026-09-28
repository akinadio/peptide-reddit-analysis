"""Step 1 — retrieve posts and comments from the study communities via the Arctic Shift archive.

Peptide-dedicated communities are kept in full; in biohacking communities a post (and its comments) is kept
only if the thread mentions a peptide. Resumable: re-running continues after the newest post already saved.

    python 01_scrape.py
"""
import csv, re, time
from collections import defaultdict
import requests
import config as C

API = "https://arctic-shift.photon-reddit.com/api"
COLS = ["id", "subreddit", "kind", "parent_post_id", "author", "created_utc", "title", "body", "score", "num_comments", "permalink"]
PEPTIDE_RE = re.compile(r"\b(peptides?|bpc[-\s]?157|tb[-\s]?500|thymosin|ipamorelin|cjc[-\s]?1295|sermorelin|tesamorelin|ghk(-cu)?|"
                        r"mgf|ghrp[-\s]?6|kpv|aod[-\s]?9604|igf[-\s]?1\s*lr3|semaglutide|tirzepatide|retatrutide|mounjaro|ozempic|"
                        r"wegovy|selank|semax|pt[-\s]?141|melanotan|epit?halon|hexarelin|hgh\s*frag|research\s*peptide)\b", re.I)


def get(path, **params):
    params = {k: v for k, v in params.items() if v} | {"meta-app": "peptide-research"}
    for attempt in range(8):
        try:
            r = requests.get(API + path, params=params, timeout=60)
        except requests.RequestException:
            time.sleep(15); continue
        if r.status_code in (429, 422) or r.status_code >= 500:
            time.sleep(45 * (1 + attempt / 2)); continue
        return r.json().get("data") or [] if r.ok else []
    return []


def paged(path, key, value, after=None):
    seen = set()
    while True:
        rows = get(path, **{key: value}, limit=100, sort="asc", after=after)
        new = [x for x in rows if x.get("id") not in seen]
        yield from new
        seen |= {x["id"] for x in new}
        nxt = max((int(x.get("created_utc") or 0) for x in rows), default=0)
        if len(rows) < 100 or not nxt or (after and nxt <= after):
            return
        after = nxt
        time.sleep(3)


def row(x, kind, sub, parent=""):
    return {"id": x["id"], "subreddit": sub, "kind": kind, "parent_post_id": parent, "author": x.get("author") or "",
            "created_utc": int(x.get("created_utc") or 0), "title": (x.get("title") or "").strip(),
            "body": (x.get("selftext") if kind == "post" else x.get("body") or "").strip(),
            "score": x.get("score") or 0, "num_comments": x.get("num_comments") or 0,
            "permalink": "https://reddit.com" + x["permalink"] if x.get("permalink") else ""}


def main():
    C.DATA.mkdir(exist_ok=True)
    seen, last = set(), defaultdict(int)
    if C.RAW_CSV.exists():
        csv.field_size_limit(1 << 28)
        for r in csv.DictReader(open(C.RAW_CSV, encoding="utf-8")):
            seen.add(r["id"])
            if r["kind"] == "post": last[r["subreddit"]] = max(last[r["subreddit"]], int(r["created_utc"] or 0))
    new_file = not C.RAW_CSV.exists()
    with open(C.RAW_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS)
        if new_file: w.writeheader()
        for sub in C.COMMUNITIES:
            for p in paged("/posts/search", "subreddit", sub, after=last[sub] or None):
                if p["id"] in seen: continue
                comments = list(paged("/comments/search", "link_id", f"t3_{p['id']}"))
                thread = " ".join([p.get("title") or "", p.get("selftext") or ""] + [c.get("body") or "" for c in comments])
                if sub in C.BIOHACK_SUBS and not PEPTIDE_RE.search(thread):
                    continue
                w.writerow(row(p, "post", sub)); seen.add(p["id"])
                for c in comments:
                    if c["id"] not in seen and (c.get("body") or "") not in ("[deleted]", "[removed]"):
                        w.writerow(row(c, "comment", sub, p["id"])); seen.add(c["id"])
                f.flush()
            print(f"r/{sub} done ({len(seen):,} records total)")


if __name__ == "__main__":
    main()
