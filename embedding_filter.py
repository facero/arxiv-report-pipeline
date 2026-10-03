#!/usr/bin/env python3
"""
Embedding-based pre-filter for arXiv papers.

Reads fetched papers JSON, computes TF-IDF similarity against the research
persona, and outputs only the top fraction for LLM scoring.

Requires scikit-learn in the arxiv conda env.

Usage:
  # In the arxiv conda env:
  conda run -n arxiv python3 embedding_filter.py \
      --input papers/2026-06-01_to_2026-06-22.json \
      --output scored/2026-06-01_to_2026-06-22_prefiltered.json \
      --top 0.25
"""
import argparse, json, os, sys

# Friendly error if running outside the conda env
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    print("ERROR: scikit-learn or numpy not found. Run from the arxiv conda env:")
    print("  conda run -n arxiv python3 embedding_filter.py ...")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def log(msg):
    print(msg, flush=True)
    with open(os.path.join(BASE_DIR, "scraper.log"), "a") as f:
        f.write(msg + "\n")

def load_persona():
    path = os.path.join(BASE_DIR, "research_persona.txt")
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return ""

def build_texts(papers, persona):
    """Build combined text for each paper (title + abstract)."""
    texts = []
    for p in papers:
        title = p.get("title", "")
        summary = p.get("summary", "")
        texts.append(f"{title} {summary}")
    return texts

def compute_similarities(texts, query):
    """
    Compute cosine similarity between each text and the query using TF-IDF.
    Returns a numpy array of similarity scores (0-1).
    """
    all_texts = texts + [query]
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=10000,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.85,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    # Last row is the query
    paper_vectors = tfidf_matrix[:-1]
    query_vector = tfidf_matrix[-1]
    sims = cosine_similarity(paper_vectors, query_vector).flatten()
    return sims

def main():
    parser = argparse.ArgumentParser(description="TF-IDF pre-filter for arXiv papers")
    parser.add_argument("--input", required=True, help="Input papers JSON (from fetch_arxiv.py)")
    parser.add_argument("--output", required=True, help="Output JSON with top fraction only")
    parser.add_argument("--top", type=float, default=0.25, help="Top fraction to keep (default: 0.25)")
    args = parser.parse_args()

    if not 0 < args.top <= 1:
        log(f"Invalid --top value: {args.top}. Must be between 0 and 1.")
        sys.exit(1)

    with open(args.input) as f:
        papers = json.load(f)
    log(f"Loaded {len(papers)} papers from {args.input}")

    persona = load_persona()
    if not persona:
        log("WARNING: research_persona.txt not found, using generic query.")
        persona = "gamma-ray astronomy high energy astrophysics supernova remnants pulsars"
    log(f"Research persona ({len(persona)} chars)")

    texts = build_texts(papers, persona)
    log(f"Computing TF-IDF similarities for {len(texts)} papers...")
    sims = compute_similarities(texts, persona)

    indices = np.argsort(sims)[::-1]
    sorted_sims = sims[indices]

    keep = max(1, int(len(papers) * args.top))
    top_indices = indices[:keep]

    log(f"Similarity range: {sims.min():.4f} – {sims.max():.4f}")
    log(f"Keeping top {keep}/{len(papers)} ({args.top*100:.0f}%)")

    kept_papers = []
    min_score = sorted_sims[keep - 1] if keep <= len(sorted_sims) else 0
    for idx in top_indices:
        p = papers[idx]
        p["embedding_score"] = round(float(sims[idx]) * 100, 1)
        kept_papers.append(p)

    kept_papers.sort(key=lambda p: p.get("embedding_score", 0), reverse=True)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(kept_papers, f, indent=2, ensure_ascii=False)

    log(f"Saved {len(kept_papers)} pre-filtered papers to {args.output}")
    log(f"   Threshold: embedding_score >= {min_score*100:.1f}")

    top5 = kept_papers[:5]
    log(f"   Top 5 by embedding:")
    for i, p in enumerate(top5, 1):
        log(f"   {i}. [{p.get('embedding_score', 0)}] {p.get('title', '')[:80]}")

if __name__ == "__main__":
    main()
