"""
JARVIS Lead Scraper Template
============================
This script is launched by the JARVIS executor as an autonomous agent subprocess.
It reads its identity (JOB_ID, CALLBACK_URL) from environment variables injected
by the executor — you do NOT need to modify those lines.

To customise a scrape, the AI modifies the CONFIG dict below before running.

Usage (manual):
    python lead_scraper_template.py

Dependencies (install once):
    pip install requests beautifulsoup4 duckduckgo-search
"""

# ── Identity injected by JARVIS executor ────────────────────────────────────
import os as _os
JARVIS_JOB_ID = _os.environ.get("JARVIS_JOB_ID", "manual-run")
JARVIS_CALLBACK_URL = _os.environ.get(
    "JARVIS_CALLBACK_URL",
    f"http://127.0.0.1:8000/api/jobs/{JARVIS_JOB_ID}/complete",
)

# ── Configuration (AI modifies this section) ────────────────────────────────
CONFIG = {
    # Search query — be specific for best results
    "QUERY": "SaaS founders site:linkedin.com",

    # Maximum number of leads to collect
    "MAX_RESULTS": 30,

    # Output CSV path (workspace-relative, used in the callback)
    "OUTPUT_FILE": "backend/scripts/output/leads.csv",

    # Optional: SerpAPI key for higher-quality results.
    # Leave empty ("") to use the free DuckDuckGo backend.
    "SERPAPI_KEY": _os.environ.get("SERPAPI_KEY", ""),
}

# ── Standard library imports (always available) ──────────────────────────────
import csv
import json
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ── Third-party imports (graceful fail with clear message) ──────────────────
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[JARVIS] FATAL: Missing dependencies. Run: pip install requests beautifulsoup4")
    sys.exit(1)

try:
    from duckduckgo_search import DDGS
    _HAS_DDGS = True
except ImportError:
    _HAS_DDGS = False
    print("[JARVIS] WARNING: duckduckgo-search not installed. Install with: pip install duckduckgo-search")
    print("[JARVIS] Falling back to basic scraping mode.")


# ============================================================================
# Callback — always fires, even if scraping crashes
# ============================================================================

def _send_callback(output_path: str, row_count: int) -> None:
    """POST job completion signal to JARVIS backend."""
    payload = json.dumps({
        "output_path": output_path,
        "row_count": row_count,
    }).encode("utf-8")
    req = urllib.request.Request(
        JARVIS_CALLBACK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[JARVIS] Callback sent → {resp.status} {JARVIS_CALLBACK_URL}")
    except Exception as cb_err:
        # Callback failure must NEVER crash the script
        print(f"[JARVIS] WARNING: Callback failed ({cb_err}). Job output still written to disk.")


# ============================================================================
# Extraction helpers
# ============================================================================

def _extract_page_leads(url: str, session: requests.Session) -> list[dict]:
    """Attempt to extract lead info from a single URL."""
    try:
        resp = session.get(url, timeout=10, allow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [skip] {url} — {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Try to extract structured data ──────────────────────────────────────
    leads = []

    # Heuristic: look for name-like headings + surrounding context
    # Works reasonably on LinkedIn public profiles, about pages, directories
    name_candidates = (
        soup.find_all("h1") +
        soup.find_all("h2") +
        soup.find_all(class_=lambda c: c and any(
            kw in c.lower() for kw in ["name", "profile", "person", "founder", "ceo"]
        ))
    )

    # Grab visible text near each candidate
    parsed = urlparse(url)
    domain = f"{parsed.scheme}://{parsed.netloc}"

    # Try to find email addresses in page text
    import re
    page_text = soup.get_text(" ", strip=True)
    emails = list(set(re.findall(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", page_text
    )))

    # Basic title / company extraction from meta or headings
    title = ""
    company = ""

    og_title = soup.find("meta", property="og:title")
    if og_title:
        title = og_title.get("content", "")

    og_site = soup.find("meta", property="og:site_name")
    if og_site:
        company = og_site.get("content", "")

    # Try page <title> as fallback
    if not title and soup.title:
        title = soup.title.string or ""

    # Clean up
    name = ""
    if name_candidates:
        name = name_candidates[0].get_text(strip=True)[:80]

    # Only include if we got at least a name or title
    if name or title:
        is_linkedin = "linkedin.com" in url
        leads.append({
            "name": name[:80],
            "company": company[:80],
            "title": title[:120],
            "email": emails[0] if emails else "",
            "linkedin_url": url if is_linkedin else "",
            "website": "" if is_linkedin else domain,
            "source_url": url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })

    return leads


# ============================================================================
# Search backends
# ============================================================================

def _search_duckduckgo(query: str, max_results: int) -> list[str]:
    """Return a list of URLs via DuckDuckGo search."""
    if not _HAS_DDGS:
        return []
    urls = []
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=max_results):
                href = result.get("href") or result.get("link") or ""
                if href:
                    urls.append(href)
                if len(urls) >= max_results:
                    break
    except Exception as e:
        print(f"[JARVIS] DuckDuckGo search error: {e}")
    return urls


def _search_serpapi(query: str, max_results: int, api_key: str) -> list[str]:
    """Return URLs via SerpAPI (requires a valid key)."""
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={
                "q": query,
                "num": min(max_results, 100),
                "api_key": api_key,
                "engine": "google",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [r.get("link", "") for r in data.get("organic_results", []) if r.get("link")]
    except Exception as e:
        print(f"[JARVIS] SerpAPI error: {e}")
        return []


# ============================================================================
# Main scraping logic
# ============================================================================

def run_scraper() -> list[dict]:
    query = CONFIG["QUERY"]
    max_results = int(CONFIG["MAX_RESULTS"])
    serpapi_key = CONFIG.get("SERPAPI_KEY", "")

    print(f"[JARVIS] Starting lead scrape — query: '{query}' | max: {max_results}")

    # ── Step 1: Collect URLs ─────────────────────────────────────────────────
    if serpapi_key:
        print("[JARVIS] Using SerpAPI backend...")
        urls = _search_serpapi(query, max_results, serpapi_key)
    elif _HAS_DDGS:
        print("[JARVIS] Using DuckDuckGo backend...")
        urls = _search_duckduckgo(query, max_results)
    else:
        print("[JARVIS] ERROR: No search backend available. Install duckduckgo-search or provide SERPAPI_KEY.")
        return []

    print(f"[JARVIS] Found {len(urls)} URLs to scrape.")

    # ── Step 2: Scrape each URL ──────────────────────────────────────────────
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    })

    all_leads = []
    for i, url in enumerate(urls[:max_results], 1):
        print(f"[JARVIS] [{i}/{len(urls)}] Scraping: {url}")
        leads = _extract_page_leads(url, session)
        all_leads.extend(leads)
        time.sleep(0.5)  # polite delay

    # Deduplicate by source_url
    seen = set()
    unique_leads = []
    for lead in all_leads:
        key = lead.get("source_url", "")
        if key not in seen:
            seen.add(key)
            unique_leads.append(lead)

    print(f"[JARVIS] Scraped {len(unique_leads)} unique leads.")
    return unique_leads


# ============================================================================
# CSV writer
# ============================================================================

def write_csv(leads: list[dict], output_rel_path: str) -> str:
    """Write leads to CSV and return the workspace-relative path."""
    # Resolve from the script's own location back to workspace root
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent.parent  # backend/scripts/ → workspace root
    output_path = workspace_root / output_rel_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["name", "company", "title", "email", "linkedin_url", "website", "source_url", "scraped_at"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow({k: lead.get(k, "") for k in fieldnames})

    print(f"[JARVIS] CSV written to: {output_path} ({len(leads)} rows)")
    return output_rel_path  # return workspace-relative for the callback


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    output_rel = CONFIG["OUTPUT_FILE"]
    leads = []

    try:
        leads = run_scraper()
    except Exception:
        print("[JARVIS] SCRAPER ERROR:")
        traceback.print_exc()
    finally:
        # Always write whatever was collected (even if empty on crash)
        try:
            if leads:
                output_rel = write_csv(leads, output_rel)
            else:
                # Write an empty CSV so the AI still has a file to read
                output_rel = write_csv([], output_rel)
        except Exception as write_err:
            print(f"[JARVIS] CSV write failed: {write_err}")

        # Always call the callback — the executor is polling for this signal
        _send_callback(output_rel, len(leads))
