#!/usr/bin/env python3
"""
Fetch arXiv papers since a given date using the arXiv catchup page.
Usage:
  python fetch_arxiv.py --since 2026-06-01          # Single day onward
  python fetch_arxiv.py --since 2026-06-01 --days 7  # One week
  python fetch_arxiv.py --since 2026-06-01          # Default: up to today
  python fetch_arxiv.py                               # Default: last 7 days
"""
import argparse, json, os, re, time, sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAPERS_DIR = os.path.join(BASE_DIR, "papers")
CATCHUP_URL = "https://arxiv.org/catchup/astro-ph.HE"
API_URL = "http://export.arxiv.org/api/query"

def log(msg):
    print(msg, flush=True)
    with open(os.path.join(BASE_DIR, "scraper.log"), "a") as f:
        f.write(msg + "\n")

def load_ignored_keywords(filepath):
    path = os.path.join(BASE_DIR, filepath)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [line.strip().lower() for line in f if line.strip()]

def filter_by_keywords(papers, ignored):
    if not ignored:
        return papers
    kept, excluded = [], 0
    for p in papers:
        if any(kw in p["title"].lower() for kw in ignored):
            excluded += 1
        else:
            kept.append(p)
    log(f"Keyword filter: {excluded} excluded, {len(kept)} remaining.")
    return kept

def fetch_ids_from_catchup(start_date, days=None):
    """
    Walk the catchup page day-by-day from start_date, extracting arXiv IDs.
    Only collects new submissions and cross-listings (skip replacements).
    """
    current = start_date
    end_date = datetime.utcnow().date()
    if days is not None:
        end_date = min(end_date, start_date + timedelta(days=days - 1))

    all_ids = []
    page_num = 1
    max_days = (end_date - start_date).days + 1
    day_count = 0

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        url = f"{CATCHUP_URL}/{date_str}?abs=False&page={page_num}"
        log(f"Fetching catchup: {url}")
        
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            log(f"  Failed to fetch {date_str}: {e}")
            current += timedelta(days=1)
            page_num = 1
            day_count += 1
            continue

        soup = BeautifulSoup(resp.content, "html.parser")

        # Catchup page structure (all in document order):
        #   <h3>New submissions...</h3> <dl>...</dl>
        #   <h3>Cross submissions...</h3> <dl>...</dl>
        #   <h3>Replacement submissions...</h3> <dl>...</dl>
        # Collect IDs from the first two <dl>s (new + cross), skip replacements.
        
        # Walk h3/dl in document order to pair them
        current_section = "unknown"
        ids_this_day = set()
        
        for tag in soup.find_all(["h3", "dl"]):
            if tag.name == "h3":
                txt = tag.get_text().strip().lower()
                if 'new submissions' in txt:
                    current_section = 'new'
                elif 'cross' in txt:
                    current_section = 'cross'
                elif 'replacement' in txt:
                    current_section = 'replacements'
            elif tag.name == "dl" and current_section in ("new", "cross"):
                for dt in tag.find_all("dt"):
                    a = dt.find("a", href=re.compile(r"/abs/\d{4}\.\d{4,}"))
                    if a:
                        href = a["href"]
                        rid = re.sub(r'.*/abs/', '', href)
                        rid = re.sub(r'v\d+$', '', rid)
                        ids_this_day.add(rid)

        count = len(ids_this_day)
        if count > 0:
            log(f"  {count} new/cross papers found on {date_str}")
            all_ids.extend(ids_this_day)
        else:
            log(f"  No papers on {date_str}")

        # Check for "Continue to the next day" link
        continue_link = soup.find("a", href=re.compile(r"/catchup/.*" + current.strftime("%Y-%m-%d") + r"\?abs=False&page=2"))
        if continue_link:
            page_num = 2
            # Keep same day, next page
            continue
        else:
            current += timedelta(days=1)
            page_num = 1
            day_count += 1

        # Rate limiting - be nice
        time.sleep(1)

    # Deduplicate
    all_ids = list(set(all_ids))
    log(f"\nTotal unique IDs collected: {len(all_ids)}")
    return all_ids

def fetch_abstracts_from_api(ids, batch_size=100):
    """Fetch abstracts + titles via arXiv API."""
    papers = []
    namespaces = {"atom": "http://www.w3.org/2005/Atom"}

    for i in range(0, len(ids), batch_size):
        batch = ids[i:i+batch_size]
        api_url = f"{API_URL}?id_list={','.join(batch)}&start=0&max_results={len(batch)}"
        log(f"  API batch {i//batch_size + 1}/{(len(ids)+batch_size-1)//batch_size} ({len(batch)} ids)...")
        try:
            resp = requests.get(api_url, timeout=60)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            for entry in root.findall("atom:entry", namespaces):
                # Title
                title_el = entry.find("atom:title", namespaces)
                title = "".join(title_el.itertext()).strip() if title_el is not None else ""
                # Summary
                summary_el = entry.find("atom:summary", namespaces)
                summary = " ".join(summary_el.itertext()).strip() if summary_el is not None else ""
                # Authors (first 5)
                authors = []
                for auth_el in entry.findall("atom:author/atom:name", namespaces):
                    if len(authors) < 5:
                        authors.append(auth_el.text)
                # arXiv ID
                id_url = entry.find("atom:id", namespaces)
                arxiv_id = ""
                if id_url is not None:
                    arxiv_id = id_url.text.split("/abs/")[-1]
                    arxiv_id = re.sub(r'v\d+$', '', arxiv_id)
                # Link
                link = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""
                # Categories
                cats = []
                for cat in entry.findall("atom:category", namespaces):
                    cats.append(cat.attrib.get("term", ""))
                # Published date
                published_el = entry.find("atom:published", namespaces)
                published = published_el.text if published_el is not None else ""

                papers.append({
                    "id": arxiv_id,
                    "title": title,
                    "summary": summary,
                    "authors": authors,
                    "link": link,
                    "categories": cats,
                    "published": published
                })
        except ET.ParseError as e:
            log(f"  XML parse error in batch: {e}")
        except Exception as e:
            log(f"  Batch error: {e}")
        time.sleep(0.5)  # Be nice to arXiv API

    log(f"Fetched {len(papers)} papers with abstracts via API.")
    return papers

def main():
    parser = argparse.ArgumentParser(description="Fetch arXiv papers since a date using catchup page")
    parser.add_argument("--since", help="Start date YYYY-MM-DD (default: 7 days ago)")
    parser.add_argument("--days", type=int, help="Number of days to fetch (default: all up to today)")
    parser.add_argument("--output", help="Output filename (without path)")
    args = parser.parse_args()

    # Determine start date
    if args.since:
        try:
            start_date = datetime.strptime(args.since, "%Y-%m-%d").date()
        except ValueError:
            log(f"Invalid date format: {args.since}. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        start_date = datetime.utcnow().date() - timedelta(days=7)

    log(f"Fetching arXiv papers since {start_date}" +
        (f" for {args.days} days" if args.days else " up to today"))

    os.makedirs(PAPERS_DIR, exist_ok=True)

    # 1. Fetch paper IDs from catchup pages
    ids = fetch_ids_from_catchup(start_date, args.days)
    if not ids:
        log("No paper IDs found. Exiting.")
        return

    # 2. Fetch abstracts via API
    papers = fetch_abstracts_from_api(ids)

    # 3. Load and apply keyword filter
    ignored = load_ignored_keywords("ignored-keywords.txt")
    papers = filter_by_keywords(papers, ignored)

    # 4. Determine output filename
    end_date = datetime.utcnow().date()
    if args.days:
        end_date = min(end_date, start_date + timedelta(days=args.days - 1))
    
    if args.output:
        out_name = args.output
    else:
        out_name = f"{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.json"
    
    out_path = os.path.join(PAPERS_DIR, out_name)
    with open(out_path, "w") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    log(f"\n✅ Saved {len(papers)} papers to {out_path}")

if __name__ == "__main__":
    main()
