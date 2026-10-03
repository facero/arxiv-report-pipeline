#!/usr/bin/env python3
"""Apply LLM scores to scored JSONs, build merged July file, regenerate reports."""
import json, glob, os, subprocess, sys

BASE = "/home/facero/.openclaw/workspace/arxiv-reader"
os.chdir(BASE)

# 1. Collect scores from subagent outputs
scores = {}
for f in sorted(glob.glob("scoring/output/*.json")):
    data = json.load(open(f))
    for e in data:
        if not e.get("id"):
            continue
        scores[e["id"]] = {"score": int(e["score"]), "reason": e.get("reason", "")}
print(f"Collected {len(scores)} scored ids from {len(glob.glob('scoring/output/*.json'))} files")

def apply_scores(path):
    ps = json.load(open(path))
    matched = 0
    for p in ps:
        s = scores.get(p.get("id"))
        if s:
            p["score"] = s["score"]
            p["reason"] = s["reason"]
            matched += 1
    json.dump(ps, open(path, "w"), indent=2, ensure_ascii=False)
    print(f"  {path}: {matched}/{len(ps)} scored")
    return ps, matched, len(ps)

total = matched_total = 0
for gp in ["scored/2026-06-23_to_2026-07-08_prefiltered.json",
           "scored/2026-07-09_to_2026-07-31_prefiltered.json",
           "scored/2026-08-01_to_2026-08-31_prefiltered.json",
           "scored/2026-09-01_to_2026-09-30_prefiltered.json",
           "scored/2026-10-01_to_2026-10-03_prefiltered.json"]:
    _, m, t = apply_scores(gp)
    matched_total += m; total += t
print(f"TOTAL scored: {matched_total}/{total}")

if matched_total == 0:
    print("ERROR: no scores applied — aborting before report generation.")
    sys.exit(1)

# 2. Merge the two July windows into one July dataset
merged = {}
for gp in ["scored/2026-06-23_to_2026-07-08_prefiltered.json",
           "scored/2026-07-09_to_2026-07-31_prefiltered.json"]:
    for p in json.load(open(gp)):
        merged[p.get("id") or p.get("title")] = p
july = sorted(merged.values(), key=lambda p: p.get("score", 0), reverse=True)
out = "scored/2026-06-23_to_2026-07-31_merged.json"
json.dump(july, open(out, "w"), indent=2, ensure_ascii=False)
print(f"July merged: {out} ({len(july)} papers)")

# 3. Regenerate reports
concept = open("research_persona.txt").read().strip()
def run(*args):
    subprocess.run(["python3", "generate_report.py", *args], check=True)

run("--month", "2026-07", "--data", out, "--concept", concept)
run("--month", "2026-08", "--data", "scored/2026-08-01_to_2026-08-31_prefiltered.json", "--concept", concept)
run("--month", "2026-09", "--data", "scored/2026-09-01_to_2026-09-30_prefiltered.json", "--concept", concept)
run("--month", "2026-10", "--data", "scored/2026-10-01_to_2026-10-03_prefiltered.json", "--concept", concept)
run("--index", "--concept", concept)
print("Reports + index regenerated.")

# 4. Deploy
subprocess.run(["bash", "-c"], check=False) if False else None
print("Done.")
