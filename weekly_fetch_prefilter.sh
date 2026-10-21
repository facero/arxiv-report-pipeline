#!/usr/bin/env bash
# Fetch new arXiv papers since the last run and pre-filter them.
# Prints the window and the prefiltered file path; then the caller must LLM-score it.
set -euo pipefail

ARXIV_DIR="$HOME/.openclaw/workspace/arxiv-reader"
cd "$ARXIV_DIR"

PY=~/miniforge3/bin/conda
WIN=$("$PY" run -n arxiv python3 - <<'EOF'
import glob, os, re, datetime
files = glob.glob("papers/*.json")
ends = []
for f in files:
    m = re.search(r"_to_(\d{4})-(\d{2})-(\d{2})\.json$", f)
    if not m:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", os.path.basename(f))
    if m:
        ends.append(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
if not ends:
    print("")
else:
    last = max(ends)
    start = last + datetime.timedelta(days=1)
    today = datetime.date.today()
    if start > today:
        print("")
    else:
        print(f"{start.isoformat()}|{today.isoformat()}")
EOF
)

if [ -z "$WIN" ]; then
  echo "NOTHING_TO_DO: already up to date."
  exit 0
fi

START="${WIN%%|*}"
TODAY="${WIN##*|}"
echo "Window: $START -> $TODAY"

"$PY" run -n arxiv python3 fetch_arxiv.py --since "$START"

PAPERS="papers/${START}_to_${TODAY}.json"
if [ ! -f "$PAPERS" ]; then
  # fetch may have branded the file with its own end date
  PAPERS=$(ls -t papers/*.json | head -1)
fi
echo "Papers file: $PAPERS"

NAME="$(basename "$PAPERS" .json)"
OUT="scored/${NAME}_prefiltered.json"
./run_filter.sh --input "$PAPERS" --output "$OUT" --top 0.25

cp "$OUT" "scoring/input/${NAME}_new.json"
echo "SCORE_INPUT: scoring/input/${NAME}_new.json"
echo "SCORE_OUTPUT_NEXT_RUN: scoring/output/${NAME}_new.json  (write scores here)"
echo "PREFILTERED: $OUT"
