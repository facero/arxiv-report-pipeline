#!/usr/bin/env python3
"""Finalize an arXiv run: apply LLM scores from scoring/output/*.json to every
scored/*_prefiltered.json, then regenerate all monthly reports + the archive index.

Usage: python3 finalize_all.py [--no-index]
"""
import argparse, glob, json, os, re, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
SCORED = "scored"

def end_month(fname):
    stem = fname[:-5]
    m = re.match(r"(\d{4}-\d{2})-\d{2}_to_(\d{4}-\d{2})-\d{2}", stem)
    if m:
        return m.group(2)
    return stem[:7] if len(stem) >= 7 and stem[4] == "-" else stem

# 1. Collect all scores
scores = {}
nfiles = 0
for f in sorted(glob.glob("scoring/output/*.json")):
    nfiles += 1
    try:
        data = json.load(open(f))
    except Exception as e:
        print(f"  WARN: cannot read {f}: {e}")
        continue
    for e in data:
        if e.get("id") and e.get("score") is not None:
            scores[e["id"]] = {"score": int(e["score"]), "reason": e.get("reason", "")}
print(f"Collected {len(scores)} scored ids from {nfiles} files")
if not scores:
    print("ERROR: no scores found — aborting.")
    sys.exit(1)

# 2. Apply scores to every prefiltered file
applied = {}
for gp in sorted(glob.glob(f"{SCORED}/*_prefiltered.json")):
    ps = json.load(open(gp))
    matched = 0
    for p in ps:
        s = scores.get(p.get("id"))
        if s:
            p["score"] = s["score"]
            p["reason"] = s["reason"]
            matched += 1
    json.dump(ps, open(gp, "w"), indent=2, ensure_ascii=False)
    applied[gp] = (matched, len(ps))
    print(f"  {gp}: {matched}/{len(ps)} scored")

# 3. Build month buckets from all scored/*.json (dedup by id). Skip *merged* files
#    when a non-merged source for the same month exists — dedup makes it moot, but
#    we include everything and let dedup handle it.
buckets = {}
for fname in sorted(os.listdir(SCORED)):
    if not fname.endswith(".json"):
        continue
    m = end_month(fname)
    papers = json.load(open(os.path.join(SCORED, fname)))
    bucket = buckets.setdefault(m, [])
    seen = {p.get("id") or p.get("title") for p in bucket}
    for p in papers:
        key = p.get("id") or p.get("title")
        if key not in seen:
            bucket.append(p)
            seen.add(key)

for m in buckets:
    buckets[m].sort(key=lambda p: p.get("score", p.get("embedding_score", 0)), reverse=True)
    print(f"  month {m}: {len(buckets[m])} papers")

# 4. Regenerate each monthly report
concept = open("research_persona.txt").read().strip()
for m, papers in sorted(buckets.items()):
    # write a temp data file so generate_report can read it (it expects --data)
    tmp = os.path.join(SCORED, f".tmp_{m}.json")
    json.dump(papers, open(tmp, "w"), indent=2, ensure_ascii=False)
    subprocess.run(["python3", "generate_report.py", "--month", m, "--data", tmp,
                    "--concept", concept], check=True)
    os.remove(tmp)

if "--no-index" not in sys.argv:
    subprocess.run(["python3", "generate_report.py", "--index", "--concept", concept], check=True)

print("All monthly reports + index regenerated.")
