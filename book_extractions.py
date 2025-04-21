#!/usr/bin/env python3
import requests
import os
import time
import json
import csv
import logging
from itertools import islice
from requests.exceptions import HTTPError, RequestException

# User‑configurable constants
TOPICS = ["business", "finance", "entrepreneur", "management", "accounting", "economics", "project management", "leadership", "strategy", "investment", 
                     "math", "mathematics", "statistics", "calculus", "algebra", "geometry", "probability", "trigonometry", "differential equations", "linear algebra", "discrete math", "topology", "combinatorics", "set theory", "real analysis", "complex analysis", "abstract algebra", "number theory", "graph theory", "logic", "game theory", "measure theory", "mathematical modeling", "stochastic processes", "numerical analysis", "multivariable calculus", "optimization", "vector calculus", "applied mathematics",
                     "computer science", "programming", "software", "coding", "java", "python", "C++", "AI", "artificial intelligence", "web development", "cs50", "technology", "algorithms", "autonomous systems", "systems programming", "cybersecurity", "blockchain", "cloud computing", "machine learning", "deep learning", "neural networks", "operating systems", "computational thinking", "networking", "computer architecture", "embedded systems", "database systems", "theory of computation",
                     "data analytics", "big data", "SQL", "machine learning", "deep learning", "data science", "excel", "r programming", "data", "predictive modeling", "business intelligence", "data mining", "data visualization", "data engineering", "time series analysis", "ETL", "hadoop", "spark",
                     "design", "graphic design", "ux", "ui", "web design", "visual", "animation", "illustration", "motion graphics", "product design", "typography", "brand design", "3D modeling", "video editing", "industrial design", "color theory", "interaction design",
                     "marketing", "advertising", "seo", "branding", "digital marketing", "social media", "consumer behavior", "market research", "public relations", "copywriting", "growth hacking", "email marketing", "content marketing", "performance marketing", "influencer marketing", "affiliate marketing", "event marketing", "guerrilla marketing", "direct marketing", "mobile marketing", "video marketing", "podcast marketing", "community management", "customer relationship management", "lead generation", "conversion rate optimization", "search engine marketing", "pay-per-click advertising", "display advertising", "retargeting",
                     "sales", "negotiation", "persuasion", "customer service", "business development", "sales management", "sales strategy", "sales techniques", "sales training", "sales enablement", "sales operations", "account management", "leadership development", "coaching",
                     "human resources", "recruitment", "talent management", "employee engagement", "performance management", "organizational development", "learning and development", "compensation and benefits", "HR analytics", "HR technology", "workforce planning", "diversity and inclusion", "employee relations", "succession planning", "change management", "HR strategy", "HR compliance", "HR policies and procedures", "HR best practices",
                     "project management", "agile", "scrum", "kanban", "waterfall", "project planning", "project scheduling", "project execution", "project monitoring", "project control", "project risk management", "project quality management", "project scope management", "project cost management", "project resource management", "project communication management", "project stakeholder management", "project procurement management", "project integration management",
                     "leadership", "teamwork", "communication", "emotional intelligence", "conflict resolution", "decision making", "problem solving", "critical thinking", "creativity", "innovation", "strategic thinking", "time management", "negotiation skills", "presentation skills", "interpersonal skills", "networking skills", "influence and persuasion", "mentoring and coaching", "adaptability and flexibility", "resilience and stress management","reinforcement learning", "supervised learning", "unsupervised learning", "natural language processing", "computer vision", "robotics", "data mining", "data visualization", "cloud computing", "internet of things", "edge computing", "quantum computing", "blockchain technology", "cybersecurity"
                     ]
TOP_N = 40            # number of top ISBNs to fetch per topic from Google Books
BATCH_SIZE = 10       # number of ISBNs per batch request to ISBNdb
ISBNDB_API_KEY = os.getenv("ISBNDB_API_KEY")
OUTPUT_PATH = "input_data/books.csv"
RETRY_LIMIT = 5
RETRY_BACKOFF = 2
DELAY_BETWEEN_REQUESTS = 1  # seconds between API calls

# Only these fields will be written, in this order:
DESIRED_FIELDS = [
    "authors",
    "date_published",
    "edition",
    "isbn",
    "isbn10",
    "isbn13",
    "language",
    "pages",
    "publisher",
    "related",
    "search_topic",
    "subjects",
    "synopsis",
    "title",
    "title_long",
]

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
session = requests.Session()


def fetch_url(url, headers=None, method='get', data=None):
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
                logging.warning("HTTP %s on %s; retry %d/%d after %ds", status, url, attempt, RETRY_LIMIT, wait)
                time.sleep(wait)
                continue
            raise
        except RequestException as e:
            attempt += 1
            wait = RETRY_BACKOFF ** attempt
            logging.warning("Network error on %s: %s; retry %d/%d after %ds", url, e, attempt, RETRY_LIMIT, wait)
            time.sleep(wait)
            continue
    raise RuntimeError(f"Failed to fetch {url} after {RETRY_LIMIT} attempts")


def get_isbns_from_google_books(query, max_results=TOP_N):
    url = (
        "https://www.googleapis.com/books/v1/volumes"
        f"?q={requests.utils.quote(query)}"
        f"&maxResults={max_results}"
    )
    resp = fetch_url(url)
    items = resp.json().get("items", [])
    isbns = []
    for item in items:
        ids = item.get("volumeInfo", {}).get("industryIdentifiers", [])
        isbn13 = next((x["identifier"] for x in ids if x["type"] == "ISBN_13"), None)
        isbn10 = next((x["identifier"] for x in ids if x["type"] == "ISBN_10"), None)
        if isbn13:
            isbns.append(isbn13)
        elif isbn10:
            isbns.append(isbn10)
    return isbns


def fetch_books_info_isbndb_batch(isbns_batch):
    url = "https://api2.isbndb.com/books"
    headers = {
        'accept': 'application/json',
        'Authorization': ISBNDB_API_KEY,
        'Content-Type': 'application/json',
    }
    payload = 'isbns=' + ','.join(isbns_batch)
    resp = fetch_url(url, headers=headers, method='post', data=payload)
    return resp.json().get('data', [])


def flatten_book_data(book_data):
    flat = {}
    for k, v in book_data.items():
        flat[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
    return flat


def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            return
        yield chunk


if __name__ == '__main__':
    # 1) Gather all ISBNs and map them to topics
    isbn_topic_map = {}
    for topic in TOPICS:
        logging.info("Searching Google Books for '%s'…", topic)
        isbns = get_isbns_from_google_books(topic)
        logging.info("%d ISBNs for '%s'", len(isbns), topic)
        for isbn in isbns:
            isbn_topic_map.setdefault(isbn, []).append(topic)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Deduplicate ISBNs
    unique_isbns = list(isbn_topic_map.keys())
    logging.info("Total unique ISBNs to fetch: %d", len(unique_isbns))

    # 2) Batch-call ISBNdb
    all_records = []
    for batch in chunked_iterable(unique_isbns, BATCH_SIZE):
        logging.info("Fetching ISBNdb metadata for batch of %d…", len(batch))
        try:
            books = fetch_books_info_isbndb_batch(batch)
        except Exception as e:
            logging.error("Batch fetch failed: %s", e)
            continue
        for book in books:
            isbn_used = book.get('isbn13') or book.get('isbn10')
            topics = isbn_topic_map.get(isbn_used, [])
            rec = flatten_book_data(book)
            rec['search_topic'] = ';'.join(topics)
            all_records.append(rec)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # 3) Write to CSV
    if all_records:
        with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=DESIRED_FIELDS)
            writer.writeheader()
            for rec in all_records:
                row = {k: rec.get(k, "") for k in DESIRED_FIELDS}
                writer.writerow(row)
        logging.info("Wrote %d records to %s", len(all_records), OUTPUT_PATH)
    else:
        logging.info("No data collected.")