#!/usr/bin/env python3
"""
Generate HTML report from scored papers JSON.
"""
import argparse, json, os, re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

def generate_monthly_report(papers, month, concept=""):
    """Generate a single monthly HTML report with scored papers."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

    try:
        dt = datetime.strptime(month, "%Y-%m")
        month_name = dt.strftime("%B %Y")
    except:
        month_name = month

    rows = ""
    for i, p in enumerate(papers, 1):
        score = p.get("score", 0)
        bar_pct = min(int(score), 100)
        bar_color = "#27ae60" if score >= 70 else "#f39c12" if score >= 40 else "#e74c3c"
        title = p.get("title", "No title")
        summary = p.get("summary", "")
        short_summary = (summary[:200] + "...") if len(summary) > 200 else summary
        authors = ", ".join(p.get("authors", []))
        link = p.get("link", "#")
        arxiv_id = p.get("id", "")
        categories = ", ".join(p.get("categories", []))
        reason = p.get("reason", "")

        card_id = arxiv_id or f"idx-{i}"
        rows += f"""
        <div class="paper-card" data-id="{card_id}">
            <div class="paper-header">
                <span class="rank">#{i}</span>
                <div class="score-bar" style="width: {bar_pct}%; background: {bar_color};"></div>
                <span class="score">{score}/100</span>
            </div>
            <div class="paper-title"><a href="{link}" target="_blank">{title}</a></div>
            <div class="paper-meta">
                <span>📝 {authors}</span>
                {f'<span>🏷️ {categories}</span>' if categories else ''}
                {f'<span>🔗 {arxiv_id}</span>' if arxiv_id else ''}
            </div>
            <div class="paper-abstract">{short_summary}</div>
            {f'<div class="paper-reason"><strong>Why relevant:</strong> {reason}</div>' if reason else ''}
            <div class="card-actions">
                <button class="save-btn" onclick="savePaper('{card_id}', `{title.replace('`', "'")}`, '{link}')">📖 Save to Reading List</button>
                <button class="hide-btn" data-id="{card_id}" title="Hide this paper">✕ Hide</button>
            </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArXiv Papers - {month_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0f0f23;
            color: #e0e0e0;
            padding: 20px;
            max-width: 1000px;
            margin: 0 auto;
        }}
        h1 {{ color: #fff; font-size: 1.8em; margin-bottom: 5px; }}
        .subtitle {{ color: #8899aa; margin-bottom: 20px; }}
        .header-bar {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 20px; flex-wrap: wrap; gap: 10px;
        }}
        .stats {{
            display: flex; gap: 15px; flex-wrap: wrap;
        }}
        .stat {{
            background: #1a1a3e; padding: 10px 18px; border-radius: 8px;
            border: 1px solid #2a2a5e;
        }}
        .stat .num {{ font-size: 1.4em; font-weight: bold; color: #5dade2; }}
        .stat .label {{ font-size: 0.8em; color: #8899aa; }}
        .concept {{ 
            background: #1a1a3e; padding: 15px 20px; border-radius: 8px;
            border-left: 4px solid #5dade2; margin-bottom: 20px;
            font-size: 0.95em; line-height: 1.5;
        }}
        .paper-card {{
            background: #1a1a3e; border-radius: 10px; padding: 18px 20px;
            margin-bottom: 14px; border: 1px solid #2a2a5e;
            transition: transform 0.15s, box-shadow 0.15s;
        }}
        .paper-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(93, 173, 226, 0.15);
        }}
        .paper-header {{
            display: flex; align-items: center; gap: 12px; margin-bottom: 10px;
        }}
        .rank {{ font-weight: bold; font-size: 1.1em; color: #5dade2; min-width: 32px; }}
        .score-bar {{
            height: 8px; border-radius: 4px; flex: 1; max-width: 200px;
            transition: width 0.3s;
        }}
        .score {{ font-weight: bold; font-size: 0.9em; color: #5dade2; min-width: 45px; text-align: right; }}
        .paper-title {{ font-size: 1.05em; font-weight: 600; margin-bottom: 6px; }}
        .paper-title a {{ color: #85c1e9; text-decoration: none; }}
        .paper-title a:hover {{ text-decoration: underline; }}
        .paper-meta {{ font-size: 0.8em; color: #8899aa; margin-bottom: 8px; display: flex; gap: 12px; flex-wrap: wrap; }}
        .paper-abstract {{ font-size: 0.85em; color: #b0b8c8; line-height: 1.5; margin-bottom: 8px; }}
        .paper-reason {{ font-size: 0.85em; color: #82e0aa; padding: 8px 12px; background: #0d3b1e; border-radius: 6px; margin-bottom: 10px; }}
        .save-btn {{
            background: transparent; border: 1px solid #5dade2; color: #85c1e9;
            padding: 5px 14px; border-radius: 5px; cursor: pointer;
            font-size: 0.8em; transition: all 0.2s;
        }}
        .save-btn:hover {{ background: #5dade2; color: #0f0f23; }}
        .nav {{ margin-bottom: 20px; }}
        .nav a {{ color: #85c1e9; text-decoration: none; }}
        .nav a:hover {{ text-decoration: underline; }}
        .chart-container {{ background: #1a1a3e; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #2a2a5e; }}
        .card-actions {{ display: flex; gap: 10px; margin-top: 4px; }}
        .save-hint {{ background: #12203a; border: 1px solid #2a2a5e; border-left: 4px solid #27ae60; border-radius: 8px; padding: 10px 14px; margin-bottom: 18px; font-size: 0.85em; color: #a9c3d6; line-height: 1.5; }}
        .hide-btn {{
            background: transparent; border: 1px solid #6c3483; color: #a569bd;
            padding: 5px 12px; border-radius: 5px; cursor: pointer;
            font-size: 0.8em; transition: all 0.2s;
        }}
        .hide-btn:hover {{ background: #6c3483; color: white; }}
        .hidden-card {{ display: none !important; }}
        #hideBar {{
            position: sticky; top: 8px; z-index: 100;
            display: none; align-items: center; justify-content: space-between;
            background: #2a1a5e; border: 1px solid #6c3483; border-radius: 8px;
            padding: 10px 16px; margin-bottom: 16px; gap: 10px; flex-wrap: wrap;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }}
        #hideBarText {{ color: #c39bd3; font-size: 0.9em; }}
        .bar-btn {{
            background: transparent; border: 1px solid #a569bd; color: #c39bd3;
            padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.85em;
            transition: all 0.2s;
        }}
        .bar-btn:hover {{ background: #6c3483; color: white; }}
    </style>
</head>
<body>
    <div class="nav"><a href="index.html">← Archive</a></div>

    <div id="hideBar">
        <span id="hideBarText"></span>
        <div style="display:flex; gap:8px;">
            <button id="undoHideBtn" class="bar-btn" title="Restore the last hidden paper">↩️ Undo</button>
            <button id="restoreAllBtn" class="bar-btn">Restore all</button>
        </div>
    </div>

    <div class="header-bar">
        <div>
            <h1>📄 {month_name}</h1>
            <div class="subtitle">High Energy Astrophysics - Scored by Minime</div>
        </div>
        <button onclick="window.open('reading_list.html', '_arxiv_reading_list')" style="background:#6c3483; color:white; border:none; padding:10px 18px; border-radius:8px; cursor:pointer; font-size:0.9em;">📖 Reading List</button>
    </div>

    <div class="save-hint">💡 <strong>Save to Reading List</strong> opens a prefilled GitHub issue — press <strong>Submit</strong> there and it syncs to all your devices. Close the issue to remove it.</div>

    <div class="stats">
        <div class="stat"><div class="num">{len(papers)}</div><div class="label">Papers Scored</div></div>
        <div class="stat"><div class="num">{sum(1 for p in papers if p.get('score', 0) >= 70)}</div><div class="label">High Relevance (≥70)</div></div>
        <div class="stat"><div class="num">{sum(1 for p in papers if 40 <= p.get('score', 0) < 70)}</div><div class="label">Medium (40-69)</div></div>
        <div class="stat"><div class="num">{sum(1 for p in papers if p.get('score', 0) < 40)}</div><div class="label">Low (&lt;40)</div></div>
    </div>

    {f'<div class="concept"><strong>🎯 Research Persona:</strong> {concept}</div>' if concept else ''}

    <div class="chart-container">
        <canvas id="scoreChart"></canvas>
    </div>

    <div id="papers">
        {rows}
    </div>

    <script>
        const scores = {json.dumps([p.get("score", 0) for p in papers])};
        new Chart(document.getElementById('scoreChart'), {{
            type: 'bar',
            data: {{
                labels: scores.map((_, i) => '#' + (i+1)),
                datasets: [{{
                    label: 'Relevance Score',
                    data: scores,
                    backgroundColor: scores.map(s => s >= 70 ? '#27ae60' : s >= 40 ? '#f39c12' : '#e74c3c'),
                    borderRadius: 3
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true, max: 100, grid: {{ color: '#2a2a5e' }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});

        // Save to a permanent, cross-device reading list backed by GitHub Issues.
        function savePaper(id, title, link) {{
            const repo = 'facero/arxiv-reports';
            const today = new Date().toISOString().split('T')[0];
            const body = '**Paper:** ' + title + '\\n\\n**arXiv:** ' + link +
                         '\\n\\n**ID:** ' + id + '\\n\\n_Saved ' + today + ' from the arXiv report site._';
            const url = 'https://github.com/' + repo + '/issues/new'
                + '?title=' + encodeURIComponent(title)
                + '&body=' + encodeURIComponent(body)
                + '&labels=reading-list';
            window.open(url, '_blank');
        }}

        /* ---- Hide papers (no database, just localStorage) ---- */
        const HIDE_KEY = 'arxivHidden';
        let hidden = JSON.parse(localStorage.getItem(HIDE_KEY) || '[]');
        let lastHiddenId = null;
        const hideBar = document.getElementById('hideBar');
        const hideBarText = document.getElementById('hideBarText');
        const restoreAllBtn = document.getElementById('restoreAllBtn');

        function getCard(id) {{
            const cards = document.querySelectorAll('.paper-card');
            for (const c of cards) if (c.dataset.id === id) return c;
            return null;
        }}

        function refreshHideBar(msg) {{
            if (!hideBar) return;
            hideBarText.textContent = msg || (hidden.length ? `🗑️ ${{hidden.length}} hidden paper(s) on this browser` : '');
            restoreAllBtn.textContent = `Restore all (${{hidden.length}})`;
            hideBar.style.display = (hidden.length > 0 || msg) ? 'flex' : 'none';
        }}

        function hidePaper(id) {{
            if (!id || hidden.includes(id)) return;
            hidden.push(id);
            localStorage.setItem(HIDE_KEY, JSON.stringify(hidden));
            const card = getCard(id);
            if (card) card.classList.add('hidden-card');
            lastHiddenId = id;
            refreshHideBar('🗑️ Paper hidden');
        }}

        document.addEventListener('click', e => {{
            const btn = e.target.closest('.hide-btn');
            if (btn) hidePaper(btn.dataset.id);
        }});

        document.getElementById('undoHideBtn').addEventListener('click', () => {{
            if (!lastHiddenId) return;
            hidden = hidden.filter(id => id !== lastHiddenId);
            localStorage.setItem(HIDE_KEY, JSON.stringify(hidden));
            const card = getCard(lastHiddenId);
            if (card) card.classList.remove('hidden-card');
            lastHiddenId = null;
            if (hidden.length) refreshHideBar('↩️ Paper restored');
            else {{ hideBar.style.display = 'none'; }}
        }});

        restoreAllBtn.addEventListener('click', () => {{
            hidden.forEach(id => {{
                const card = getCard(id);
                if (card) card.classList.remove('hidden-card');
            }});
            hidden = [];
            lastHiddenId = null;
            localStorage.removeItem(HIDE_KEY);
            hideBar.style.display = 'none';
        }});

        // Apply previously hidden papers on load
        hidden.forEach(id => {{
            const card = getCard(id);
            if (card) card.classList.add('hidden-card');
        }});
        if (hidden.length) refreshHideBar();
    </script>
</body>
</html>"""
    out = os.path.join(REPORTS_DIR, f"{month}.html")
    with open(out, "w") as f:
        f.write(html)
    log(f"Report saved: {out}")

def generate_index(papers_by_month, concept=""):
    """Generate the archive index page."""
    os.makedirs(REPORTS_DIR, exist_ok=True)

    total_papers = sum(len(ps) for ps in papers_by_month.values())
    months_sorted = sorted(papers_by_month.keys(), reverse=True)

    month_grid = ""
    for m in months_sorted:
        ps = papers_by_month[m]
        try:
            mn = datetime.strptime(m, "%Y-%m").strftime("%B %Y")
        except:
            mn = m
        high = sum(1 for p in ps if p.get("score", 0) >= 70)
        month_grid += f"""
        <div class="month-item">
            <div class="month-title">📅 {mn}</div>
            <div class="month-stats">
                <span>📊 {len(ps)} papers</span>
                <span>✅ {high} high relevance</span>
            </div>
            <a href="{m}.html" class="view-btn">View →</a>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArXiv Paper Archive</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #1a1a3e 0%, #0f0f23 100%);
            min-height: 100vh; padding: 30px;
        }}
        .container {{
            max-width: 1000px; margin: 0 auto; background: rgba(26, 26, 62, 0.9);
            border-radius: 12px; padding: 30px; border: 1px solid #2a2a5e;
        }}
        h1 {{ color: #fff; text-align: center; font-size: 2.2em; }}
        .subtitle {{ text-align: center; color: #8899aa; margin-bottom: 25px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px; }}
        .stat-card {{ background: linear-gradient(135deg, #2a1a5e, #1a2a5e); color: white; padding: 18px; border-radius: 10px; text-align: center; }}
        .stat-card .number {{ font-size: 2.2em; font-weight: bold; }}
        .stat-card .label {{ font-size: 0.85em; opacity: 0.8; }}
        .concept {{ background: #1a1a3e; padding: 15px; border-radius: 8px; border-left: 4px solid #5dade2; margin-bottom: 20px; font-size: 0.9em; color: #b0b8c8; }}
        .month-list {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }}
        .month-item {{ background: #1a1a3e; border: 1px solid #2a2a5e; border-radius: 8px; padding: 15px; transition: all 0.2s; }}
        .month-item:hover {{ border-color: #5dade2; transform: translateY(-3px); }}
        .month-title {{ font-size: 1em; font-weight: 600; color: #e0e0e0; margin-bottom: 8px; }}
        .month-stats {{ color: #8899aa; font-size: 0.8em; margin-bottom: 12px; }}
        .month-stats span {{ display: block; }}
        .view-btn {{ background: #5dade2; color: #0f0f23; display: block; text-align: center; padding: 7px; border-radius: 5px; text-decoration: none; font-weight: 600; font-size: 0.85em; }}
        .chart-container {{ background: #1a1a3e; padding: 20px; border-radius: 10px; border: 1px solid #2a2a5e; }}
        .top-btn {{ background: #6c3483; color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-size: 0.95em; display: inline-block; text-decoration: none; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 ArXiv Paper Archive</h1>
        <div class="subtitle">High Energy Astrophysics - Scored by Minime 🤖</div>
        <div style="text-align:center; margin-bottom: 20px;">
            <button onclick="window.open('reading_list.html', '_arxiv_reading_list')" class="top-btn">📖 Reading List (<span id="rlCount">0</span>)</button>
        </div>
        <div class="stats-grid">
            <div class="stat-card"><div class="number">{len(months_sorted)}</div><div class="label">Months</div></div>
            <div class="stat-card"><div class="number">{total_papers}</div><div class="label">Papers Scored</div></div>
            <div class="stat-card"><div class="number">{total_papers // max(len(months_sorted), 1)}</div><div class="label">Avg/Month</div></div>
        </div>
        {f'<div class="concept"><strong>🎯 Research Persona:</strong> {concept}</div>' if concept else ''}
        <div class="month-list" id="monthList">{month_grid}</div>
        <div class="chart-container"><canvas id="trendChart"></canvas></div>
    </div>
    <script>
        const labels = {json.dumps([datetime.strptime(m, "%Y-%m").strftime("%b %Y") if len(m) == 7 else m for m in reversed(months_sorted)])};
        const data = {json.dumps([len(papers_by_month[m]) for m in reversed(months_sorted)])};
        new Chart(document.getElementById('trendChart'), {{
            type: 'line',
            data: {{ labels, datasets: [{{ label: 'Papers/Month', data, borderColor: '#5dade2', backgroundColor: 'rgba(93,173,226,0.1)', tension: 0.4, fill: true }}] }},
            options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: true, grid: {{ color: '#2a2a5e' }} }}, x: {{ grid: {{ display: false }} }} }} }}
        }});
        function openRL() {{ window.open('reading_list.html', '_arxiv_reading_list'); }}
        // Reading list count comes from open GitHub issues labelled 'reading-list'
        document.addEventListener('DOMContentLoaded', () => {{
            fetch('https://api.github.com/repos/facero/arxiv-reports/issues?state=open&labels=reading-list&per_page=100&_=' + Date.now(), {{ cache: 'no-store' }})
                .then(r => r.ok ? r.json() : [])
                .then(items => {{
                    document.getElementById('rlCount').textContent = items.filter(i => !i.pull_request).length;
                }})
                .catch(() => {{}});
        }});
    </script>
</body>
</html>"""
    out = os.path.join(REPORTS_DIR, "index.html")
    with open(out, "w") as f:
        f.write(html)
    log(f"Index saved: {out}")

def generate_reading_list():
    """Generate the reading list page (backed by GitHub Issues, no localStorage)."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArXiv Reading List</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', sans-serif; background: #0f0f23; color: #e0e0e0; padding: 20px; max-width: 800px; margin: 0 auto; }
        h1 { color: #fff; margin-bottom: 6px; }
        .subtitle { color: #8899aa; font-size: 0.85em; margin-bottom: 18px; }
        .paper { background: #1a1a3e; border: 1px solid #2a2a5e; border-radius: 8px; padding: 12px 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; gap: 10px; }
        .paper a.title { color: #85c1e9; text-decoration: none; flex: 1; }
        .paper a.title:hover { text-decoration: underline; }
        .paper .date { color: #8899aa; font-size: 0.8em; white-space: nowrap; }
        .done-btn { background: transparent; border: 1px solid #27ae60; color: #82e0aa; padding: 4px 10px; border-radius: 4px; font-size: 0.8em; text-decoration: none; white-space: nowrap; }
        .done-btn:hover { background: #27ae60; color: white; }
        .gh-btn { background: transparent; border: 1px solid #8899aa; color: #b0b8c8; padding: 8px 16px; border-radius: 5px; font-size: 0.85em; margin-bottom: 10px; text-decoration: none; display: inline-block; }
        .gh-btn:hover { border-color: #5dade2; color: #85c1e9; }
        .empty { color: #8899aa; text-align: center; padding: 40px; }
        .hint { color: #6c7a8a; font-size: 0.8em; margin-bottom: 15px; }
        .nav a { color: #85c1e9; text-decoration: none; display: inline-block; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="nav"><a href="index.html">← Archive</a></div>
    <h1>📖 Reading List</h1>
    <div class="subtitle">Backed by GitHub Issues — synced across all your devices</div>
    <a class="gh-btn" id="ghLink" href="#" target="_blank">🔗 Open on GitHub</a>
    <div class="hint">Tap “✓ Done” to open the paper’s issue — close it there to remove it from this list.</div>
    <div id="list"><div class="empty">Loading…</div></div>
    <script>
        const REPO = 'facero/arxiv-reports';
        const API = 'https://api.github.com/repos/' + REPO + '/issues?state=open&labels=reading-list&per_page=100';
        document.getElementById('ghLink').href = 'https://github.com/' + REPO + '/issues?q=label%3Areading-list';
        function paperUrl(body) {
            const m = /(https?:\\/\\/arxiv\\.org\\/abs\\/[^\\s)]+)/.exec(body || '');
            return m ? m[1] : null;
        }
        async function render() {
            const container = document.getElementById('list');
            try {
                const r = await fetch(API + '&_=' + Date.now(), { headers: { 'Accept': 'application/vnd.github+json' }, cache: 'no-store' });
                if (!r.ok) throw new Error('HTTP ' + r.status);
                const items = (await r.json()).filter(i => !i.pull_request);
                if (!items.length) {
                    container.innerHTML = '<div class="empty">Nothing saved yet.<br>Open a monthly report and click “📖 Save to Reading List”.</div>';
                    return;
                }
                container.innerHTML = items.map(i => {
                    const url = paperUrl(i.body) || i.html_url;
                    const d = (i.created_at || '').slice(0, 10);
                    return '<div class="paper">'
                        + '<span class="date">' + d + '</span>'
                        + '<a class="title" href="' + url + '" target="_blank">' + i.title + '</a>'
                        + '<a class="done-btn" href="' + i.html_url + '" target="_blank" title="Open on GitHub to close">✓ Done</a>'
                        + '</div>';
                }).join('');
            } catch (e) {
                container.innerHTML = '<div class="empty">Could not load the list from GitHub (' + e.message + ').<br>'
                    + '<a style="color:#85c1e9" href="https://github.com/' + REPO + '/issues?q=label%3Areading-list" target="_blank">Open it on GitHub</a>.</div>';
            }
        }
        render();
    </script>
</body>
</html>"""
    out = os.path.join(REPORTS_DIR, "reading_list.html")
    with open(out, "w") as f:
        f.write(html)
    log(f"Reading list saved: {out}")

def log(msg):
    print(msg, flush=True)
    with open(os.path.join(BASE_DIR, "scraper.log"), "a") as f:
        f.write(msg + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", help="YYYY-MM format")
    parser.add_argument("--data", help="Path to scored JSON file")
    parser.add_argument("--index", action="store_true", help="Regenerate index from all scored files")
    parser.add_argument("--concept", default="", help="Research persona text")
    args = parser.parse_args()

    if args.index:
        # Gather all scored papers
        papers_dir = os.path.join(BASE_DIR, "scored")
        all_papers = {}
        if os.path.exists(papers_dir):
            for fname in sorted(os.listdir(papers_dir)):
                if fname.endswith(".json"):
                    # Extract YYYY-MM from filename. Prefer the END month of a
                    # date range (e.g. 2026-06-23_to_2026-07-08 -> 2026-07),
                    # falling back to the leading YYYY-MM.
                    stem = fname[:-5]
                    mtch = re.match(r"(\d{4}-\d{2})-\d{2}_to_(\d{4}-\d{2})-\d{2}", stem)
                    m = mtch.group(2) if mtch else (stem[:7] if len(stem) >= 7 and stem[4] == '-' else stem)
                    with open(os.path.join(papers_dir, fname)) as f:
                        papers = json.load(f)
                    # Merge into the month bucket, de-duplicating by arXiv id
                    bucket = all_papers.setdefault(m, [])
                    seen = {p.get("id") or p.get("title") for p in bucket}
                    for p in papers:
                        key = p.get("id") or p.get("title")
                        if key not in seen:
                            bucket.append(p)
                            seen.add(key)
            # Highest score first within each month
            for m in all_papers:
                all_papers[m].sort(key=lambda p: p.get("score", p.get("embedding_score", 0)), reverse=True)
        if all_papers:
            generate_index(all_papers, args.concept)
        generate_reading_list()
    elif args.month and args.data:
        with open(args.data) as f:
            papers = json.load(f)
        generate_monthly_report(papers, args.month, args.concept)
        generate_reading_list()
    else:
        print("Usage: generate_report.py --month YYYY-MM --data scored.json [--index] [--concept '...']")
