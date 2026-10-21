#!/usr/bin/env bash
# Publish arXiv reports to GitHub Pages.
# Regenerates all reports from applied scores, then deploys to facero/arxiv-reports.
set -euo pipefail

ARXIV_DIR="$HOME/.openclaw/workspace/arxiv-reader"
SITE_DIR="$HOME/arxiv-reports-site"
export PATH="$PATH:$HOME/.local/bin"

cd "$ARXIV_DIR"

echo "== Finalizing reports =="
~/miniforge3/bin/conda run -n arxiv python3 finalize_all.py

echo "== Deploying to $SITE_DIR =="
cp reports/*.html "$SITE_DIR"/
cd "$SITE_DIR"
if git diff --quiet && git diff --cached --quiet; then
  echo "No changes to deploy."
else
  git add -A
  git -c user.name=facero -c user.email=fabacero@gmail.com commit -q -m "Weekly arXiv report update $(date -u +%F)"
  git push -q origin main
  echo "Pushed."
fi

echo "== Waiting for GitHub Pages build =="
for i in $(seq 1 20); do
  st=$(gh api repos/facero/arxiv-reports/pages/builds/latest --jq '.status' 2>/dev/null || echo unknown)
  echo "  build status: $st"
  [ "$st" = "built" ] && break
  sleep 15
done

code=$(curl -s -o /dev/null -w "%{http_code}" https://facero.github.io/arxiv-reports/)
echo "Site HTTP status: $code"
echo "LIVE: https://facero.github.io/arxiv-reports/"
