"""Step 3 — independent second extraction of every record with Gemini 2.5 Flash-Lite (Batch API, identical prompt).

Everything is kept in the run folder (config.RUN_DIR), so batches from earlier runs are never reused. Resumable within
a run: state is kept in <run>/gemini_state.json; results are written to <run>/gemini_results/*.jsonl.

    python 03_gemini_batch.py prepare     # one request per record sent to the primary model (skips records already queued)
    python 03_gemini_batch.py run         # submit, poll and download until finished
"""
import csv, json, os, sys, time
from collections import Counter
from datetime import datetime, timezone
from dotenv import load_dotenv
from google import genai
from google.genai import types
import config as C, prompt as Pm

STATE, REQ = C.RUN_DIR / "gemini_state.json", C.RUN_DIR / "gemini_requests"
state = lambda: json.load(open(STATE)) if STATE.exists() else {"chunks": []}
save = lambda s: json.dump(s, open(STATE, "w"), indent=1)


def prepare(chunk=7000):
    """Queues every record sent to the primary model that is not already in a prepared chunk (safe to re-run)."""
    s, buf = state(), []
    queued = {json.loads(l)["key"] for c in s["chunks"] for l in open(c["file"], encoding="utf-8") if l.strip()}
    todo = {p.name.split(".")[0] for p in C.PRIMARY_DIR.iterdir()} - queued   # every record sent to the primary model
    REQ.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(1 << 28)
    def flush():
        path = REQ / f"chunk_{len(s['chunks']):04d}.jsonl"
        path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in buf))
        s["chunks"].append({"file": str(path), "n": len(buf), "status": "prepared"}); buf.clear()
    for r in csv.DictReader(open(C.RAW_CSV, encoding="utf-8")):
        if r["id"] in todo:
            buf.append({"key": r["id"], "request": {
                "system_instruction": {"parts": [{"text": Pm.SYSTEM_PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": Pm.user_message(r, C.MAX_BODY_CHARS)}]}],
                "generation_config": {"temperature": 0, "response_mime_type": "application/json"}}})
            if len(buf) == chunk: flush()
    if buf: flush()
    save(s); print(f"{len(todo):,} new records queued; {len(s['chunks'])} chunks in total")


def run(poll=60, max_active=10):
    load_dotenv(); client = genai.Client(api_key=os.environ["GEMINI_API_KEY"]); C.GEMINI_DIR.mkdir(exist_ok=True)
    s = state()
    while any(c["status"] != "done" for c in s["chunks"]):
        for i, c in enumerate(s["chunks"]):
            if c["status"] == "submitted":
                job = client.batches.get(name=c["job"])
                if job.state.name == "JOB_STATE_SUCCEEDED":
                    out, versions = [], Counter()
                    for line in client.files.download(file=job.dest.file_name).decode().splitlines():
                        o = json.loads(line)
                        versions[(o.get("response") or {}).get("modelVersion") or "not reported"] += 1
                        try:
                            parts = o["response"]["candidates"][0]["content"]["parts"]
                            out.append({"key": o["key"], "data": Pm.parse_json("".join(p.get("text", "") for p in parts))})
                        except Exception:
                            out.append({"key": o["key"], "data": None})
                    (C.GEMINI_DIR / f"chunk_{i:04d}.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in out))
                    c["status"] = "done"
                    prev = C.manifest().get("second_model_versions", {})
                    C.manifest(second_model_versions={m: prev.get(m, 0) + n for m, n in versions.items()},
                               second_last_collected_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
                elif job.state.name in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"):
                    c["status"] = "prepared"
        active = sum(c["status"] == "submitted" for c in s["chunks"])
        for c in s["chunks"]:
            if c["status"] == "prepared" and active < max_active:
                up = client.files.upload(file=c["file"], config=types.UploadFileConfig(mime_type="jsonl"))
                c.update(status="submitted", job=client.batches.create(model=f"models/{C.SECOND_MODEL}", src=up.name).name)
                active += 1
        save(s); print(time.strftime("%H:%M"), {k: sum(c["status"] == k for c in s["chunks"]) for k in ("prepared", "submitted", "done")})
        time.sleep(poll)


if __name__ == "__main__":
    {"prepare": prepare, "run": run}[sys.argv[1]]()
