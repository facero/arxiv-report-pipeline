# arxiv-report-pipeline

An automated pipeline that fetches, filters, scores **and publishes** a personalised
arXiv digest for high-energy astrophysics — then serves it as a static website on
GitHub Pages.

Built for a research profile focused on **supernova remnants, pulsar wind nebulae,
Galactic PeVatrons** and their non-thermal emission (Fermi-LAT, HESS, CTA/LST-1),
with X-ray analysis (XMM-Newton, NuSTAR, Chandra) and multi-wavelength follow-up.

**Live site:** https://facero.github.io/arxiv-reports/

---

## Pipeline overview

```
arXiv catchup pages ──► fetch_arxiv.py ──► papers/*.json
        │                                     (keyword filter applied)
        ▼
embedding_filter.py  (TF-IDF vs. research_persona.txt, top 25%) ──► scored/*_prefiltered.json
        │
        ▼
LLM scoring pass  (score 0-100 + "why relevant") ──► scored data gains score/reason
        │
        ▼
generate_report.py ──► reports/YYYY-MM.html, index.html, reading_list.html
        │
        ▼
git push ──► GitHub Pages  ──►  arxiv-reports site
```

1. **`fetch_arxiv.py`** — walks the arXiv `astro-ph.HE` catch-up pages day by day
   (new + cross-listed submissions only), pulls abstracts/titles/authors via the
   arXiv API, and drops anything matching `ignored-keywords.txt`.
2. **`embedding_filter.py`** — computes TF-IDF cosine similarity of each paper
   (title + abstract) against `research_persona.txt` and keeps the top fraction
   (default 25%) for scoring.
3. **LLM scoring** — each pre-filtered paper is scored `0-100` for relevance to the
   persona, plus a one-line *"why relevant"* note. Output is a
   `{"id", "score", "reason"}` array (see `finalize_run.py`, `scoring/`).
4. **`generate_report.py`** — builds a monthly HTML report per month, an archive
   `index.html`, and the `reading_list.html` page.
5. **Publish** — copy `reports/*.html` into the `arxiv-reports` Pages repo and push.

---

## Files

| File | Purpose |
|------|---------|
| `fetch_arxiv.py` | Harvest paper IDs from arXiv catch-up pages + abstracts from the API |
| `embedding_filter.py` | TF-IDF relevance pre-filter against the research persona |
| `generate_report.py` | Build monthly reports, archive index and reading-list page |
| `finalize_run.py` | Apply LLM scores to the scored JSONs, merge month windows, regenerate reports |
| `run_filter.sh` | Wrapper to run `embedding_filter.py` inside the `arxiv` conda env |
| `ignored-keywords.txt` | Title keywords to exclude (cosmology, GRB, AGN, …) |
| `research_persona.txt` | The research profile used for relevance filtering |

Generated data (`papers/`, `scored/`, `reports/`, `scoring/`, logs) is **not** tracked
(see `.gitignore`).

---

## Requirements

- Python 3
- A conda env named `arxiv` with: `requests`, `beautifulsoup4`, `numpy`, `scikit-learn`
  (see `requirements.txt`)
- `git` + access to the Pages repo for publishing

```bash
conda create -n arxiv python=3.11 requests beautifulsoup4 numpy scikit-learn -y
```

---

## Usage

**1. Fetch papers** for a date window:

```bash
conda run -n arxiv --no-capture-output python3 fetch_arxiv.py --since 2026-07-09 --days 23
#  → papers/2026-07-09_to_2026-07-31.json
```

**2. Pre-filter** to the top 25% by relevance:

```bash
./run_filter.sh --input papers/2026-07-09_to_2026-07-31.json \
                --output scored/2026-07-09_to_2026-07-31_prefiltered.json --top 0.25
```

**3. Score** the pre-filtered papers (LLM pass) and apply the scores:

```bash
python3 finalize_run.py     # applies scoring/output/*.json, merges months, rebuilds reports
```

**4. Generate reports** manually (single month / archive index):

```bash
CONCEPT="$(cat research_persona.txt)"
python3 generate_report.py --month 2026-07 --data scored/2026-06-23_to_2026-07-31_merged.json --concept "$CONCEPT"
python3 generate_report.py --index --concept "$CONCEPT"
```

**5. Publish** to GitHub Pages:

```bash
cp reports/*.html ~/arxiv-reports-site/
cd ~/arxiv-reports-site && git add -A && git commit -m "Update reports" && git push
```

---

## Site features

- **Monthly reports** — each paper card shows the relevance score, abstract,
  authors/categories and a *"why relevant"* note.
- **✕ Hide** — dismiss papers you don't care about; hidden ids are kept in the
  browser's `localStorage` (per-browser, no server) with an Undo + Restore-all bar.
- **📖 Reading List** — permanent and **cross-device**, backed by GitHub Issues
  (label `reading-list`) on the Pages repo. Clicking *Save* opens a prefilled issue;
  press Submit to store it. The list page reads open issues from GitHub's public API.

---

## Notes / gotchas

- The `/100` score and the *"why relevant"* text come from the separate LLM pass —
  not from the fetch/filter scripts. Running only steps 1-2 yields unscored pages.
- arXiv is rate-limited politely (`time.sleep` between requests); a multi-month
  backfill takes a few minutes.
- GitHub Pages builds can take a minute or two; a stale page usually just needs a
  re-check or an empty commit to nudge the build.
