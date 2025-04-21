#!/usr/bin/env python3
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
    "desirable difficulties", "cognitive load theory", "learning styles",
]
TOP_N = 10             # number of papers to fetch per topic
OUTPUT_PATH = "input_data/papers_metadata.csv"
RETRY_LIMIT = 3
RETRY_BACKOFF = 2           # seconds to wait before retrying
DELAY_BETWEEN_REQUESTS = 1  # seconds between API calls


# Only these fields will be written, in this order:
DESIRED_FIELDS = [
    "doi",
    "title",
    "published_date",
    "abstract",
    "authors",
    "journal",
    "search_topic",
]

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0"
})

DOI_REGEX = re.compile(r"https?://doi\.org/(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)")

def fetch_url(url, headers=None, method='get', data=None):
    """Fetch a URL with retry/backoff on 5xx or network errors."""
    attempt = 0
    while attempt < RETRY_LIMIT:
        try:
            resp = session.request(method, url, headers=headers, data=data, timeout=10)
            resp.raise_for_status()
            return resp
        except HTTPError as e:
            status = e.response.status_code
            if 500 <= status < 600:
                attempt += 1
                wait = RETRY_BACKOFF ** attempt
                logging.warning("HTTP %s on %s; retry %d/%d after %ds",
                                status, url, attempt, RETRY_LIMIT, wait)
                time.sleep(wait)
                continue
            raise
        except RequestException as e:
            attempt += 1
            wait = RETRY_BACKOFF ** attempt
            logging.warning("Network error on %s: %s; retry %d/%d after %ds",
                            url, e, attempt, RETRY_LIMIT, wait)
            time.sleep(wait)
            continue
    raise RuntimeError(f"Failed to fetch {url} after {RETRY_LIMIT} attempts")

def get_dois_from_scholar(topic, max_results=TOP_N):
    """
    Scrape Google Scholar for `topic`, parse the first `max_results` hits,
    and pull any DOI that appears in the title link.
    """
    qs = requests.utils.quote(topic)
    url = f"https://scholar.google.com/scholar?q={qs}"
    resp = fetch_url(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    dois = []
    # Each result is in a div.gs_r or li.gs_ri depending on HTML version
    results = soup.select("div.gs_r, li.gs_ri")[:max_results]
    for res in results:
        a = res.select_one("h3.gs_rt a")
        if not a or not a.get("href"):
            continue
        m = DOI_REGEX.search(a["href"])
        if m:
            dois.append(m.group(1))
    logging.info(" → Found %d DOIs for '%s'", len(dois), topic)
    return dois

def fetch_crossref_metadata(doi):
    """Get CrossRef metadata for one DOI."""
    url = f"https://api.crossref.org/works/{requests.utils.quote(doi)}"
    resp = fetch_url(url)
    msg = resp.json().get("message", {})
    return msg

def clean_abstract(raw):
    """Strip HTML tags from CrossRef abstract field."""
    if not raw:
        return ""
    return re.sub(r'<[^>]+>', '', unescape(raw)).strip()

def flatten_paper(msg, topic):
    """Extract desired fields from CrossRef 'message' JSON."""
    doi = msg.get("DOI", "")
    title = msg.get("title", [""])[0]
    # issued → date-parts
    date = ""
    if msg.get("issued"):
        parts = msg["issued"].get("date-parts", [])
        if parts and isinstance(parts[0], list):
            y, m, *rest = parts[0] + [1,1]
            date = f"{y:04d}-{m:02d}-{rest[0]:02d}"

    abstract = clean_abstract(msg.get("abstract", ""))
    authors = []
    for a in msg.get("author", []):
        fam = a.get("family", "")
        giv = a.get("given", "")
        authors.append(", ".join(filter(None, [fam, giv])))
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

def chunked_iterable(it, size):
    it = iter(it)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            return
        yield chunk

if __name__ == "__main__":
    all_records = []
    for topic in TOPICS:
        logging.info("Scraping Google Scholar for '%s'…", topic)
        dois = get_dois_from_scholar(topic)
        for doi in dois:
            try:
                msg = fetch_crossref_metadata(doi)
            except Exception as e:
                logging.warning("  ✗ CrossRef fetch failed for %s: %s", doi, e)
                continue
            rec = flatten_paper(msg, topic)
            all_records.append(rec)
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Dedupe on DOI, keep first
    seen = set()
    unique = []
    for r in all_records:
        if r["doi"] and r["doi"] not in seen:
            seen.add(r["doi"])
            unique.append(r)

    logging.info("Total unique papers collected: %d", len(unique))

    # Write CSV
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DESIRED_FIELDS)
        writer.writeheader()
        for r in unique:
            writer.writerow({k: r.get(k, "") for k in DESIRED_FIELDS})

    logging.info("Wrote %d records to %s", len(unique), OUTPUT_PATH)