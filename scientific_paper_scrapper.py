import requests
import os
import time
import csv
import logging
import re
from itertools import islice
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError, RequestException
from html import unescape

# — User‑configurable constants —
TOPICS = [
    "spaced practice", "retrieval practice", "interleaved practice",
    "desirable difficulties", "cognitive load theory", "learning styles"
]
TOP_N = 400             # results per topic
OUTPUT_PATH = "input_data/papers_metadata.csv"
RETRY_LIMIT = 5
RETRY_BACKOFF = 2
DELAY_BETWEEN_REQUESTS = 1  # seconds between HTTP calls

# Fields to write, in order:
DESIRED_FIELDS = [
    "doi", "title", "published_date", "abstract", "authors", "journal", "search_topic"
]

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64)"
})

DOI_REGEX = re.compile(r"https?://doi\.org/(10\.\d{4,9}/\S+)")

def fetch_url(url, **kw):
    attempt = 0
    while attempt < RETRY_LIMIT:
        try:
            resp = session.get(url, timeout=10, **kw)
            resp.raise_for_status()
            return resp
        except HTTPError as e:
            if 500 <= e.response.status_code < 600:
                attempt += 1
                time.sleep(RETRY_BACKOFF ** attempt)
                continue
            raise
        except RequestException:
            attempt += 1
            time.sleep(RETRY_BACKOFF ** attempt)
    raise RuntimeError(f"Failed to fetch {url}")

def search_doi_by_title(title):
    """CrossRef title‐search fallback."""
    q = requests.utils.quote(f'title:"{title}"')
    url = f"https://api.crossref.org/works?query.title={q}&rows=1"
    try:
        resp = fetch_url(url)
        items = resp.json().get("message", {}).get("items", [])
        if items:
            return items[0].get("DOI")
    except Exception:
        pass
    return None

def get_dois_from_scholar(topic, max_results=TOP_N):
    """Scrape Scholar, extract DOIs or else lookup by title."""
    url = f"https://scholar.google.com/scholar?q={requests.utils.quote(topic)}"
    resp = fetch_url(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    results = soup.select("div.gs_r, li.gs_ri")[:max_results]

    dois = []
    for res in results:
        # 1) try DOI in the <a href>
        link = res.select_one("h3.gs_rt a")
        if link and link.get("href"):
            m = DOI_REGEX.search(link["href"])
            if m:
                dois.append(m.group(1))
                continue

        # 2) fallback: extract title text, search CrossRef
        title_tag = link or res.select_one("h3.gs_rt")
        if title_tag:
            title = title_tag.get_text(strip=True)
            doi = search_doi_by_title(title)
            if doi:
                logging.info("  ↳ Fallback DOI for '%s': %s", title, doi)
                dois.append(doi)

        time.sleep(DELAY_BETWEEN_REQUESTS)
    logging.info(" → Found %d DOIs for '%s'", len(dois), topic)
    return dois

def fetch_crossref(doi):
    url = f"https://api.crossref.org/works/{requests.utils.quote(doi)}"
    resp = fetch_url(url)
    return resp.json().get("message", {})

def clean_abstract(raw):
    if not raw:
        return ""
    text = unescape(raw)
    return re.sub(r"<[^>]+>", "", text).strip()

def flatten(msg, topic):
    doi = msg.get("DOI", "")
    title = msg.get("title", [""])[0]
    date = ""
    if msg.get("issued"):
        dp = msg["issued"].get("date-parts", [])
        if dp and dp[0]:
            y, m, *rest = dp[0] + [1,1]
            date = f"{y:04d}-{m:02d}-{rest[0]:02d}"
    abstract = clean_abstract(msg.get("abstract", ""))
    authors = []
    for a in msg.get("author", []):
        fam, giv = a.get("family",""), a.get("given","")
        authors.append(", ".join(filter(None,[fam,giv])))
    journal = msg.get("container-title", [""])[0]
    return {
        "doi": doi,
        "title": title,
        "published_date": date,
        "abstract": abstract,
        "authors": "; ".join(authors),
        "journal": journal,
        "search_topic": topic
    }

if __name__ == "__main__":
    records = []
    for topic in TOPICS:
        logging.info("Scraping Google Scholar for '%s'…", topic)
        for doi in get_dois_from_scholar(topic):
            try:
                msg = fetch_crossref(doi)
                records.append(flatten(msg, topic))
            except Exception as e:
                logging.warning("  ✗ failed DOI %s: %s", doi, e)
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Dedupe
    seen = set()
    unique = []
    for r in records:
        if r["doi"] and r["doi"] not in seen:
            seen.add(r["doi"])
            unique.append(r)

    logging.info("Total unique papers: %d", len(unique))

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DESIRED_FIELDS)
        writer.writeheader()
        for r in unique:
            writer.writerow({k: r.get(k,"") for k in DESIRED_FIELDS})

    logging.info("Wrote %d records to %s", len(unique), OUTPUT_PATH)
