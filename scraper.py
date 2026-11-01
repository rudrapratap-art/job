#!/usr/bin/env python3
"""Naukri Radar scraper.

Har source se job listings leta hai, detail page padhta hai, qualification / umar /
last date / posts nikalta hai, aur jobs.json likhta hai (Naukri Radar site ka format).

Chalane ka tarika:
    pip install -r requirements.txt
    python scraper.py

IMPORTANT: SOURCES mein jo selectors hain wo placeholder hain. Har site ka HTML alag hota hai.
Site kholo, Inspect karo, aur CSS selectors apne hisaab se badlo. Pehle chhote test ke liye
MAX_ITEMS_PER_SOURCE kam rakho.
"""
import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib import robotparser

import feedparser
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------- config
USER_AGENT = "NaukriRadarBot/0.1 (personal project; contact: you@example.com)"
DELAY_SECONDS = 2.0            # har request ke beech ruko
MAX_ITEMS_PER_SOURCE = 30
FETCH_DETAIL_PAGES = True      # True: har job ka page khol kar details nikalo
OUTPUT = Path("jobs.json")
MANUAL = Path("manual.json")   # haath se daali hui entries (optional), isi format mein

# type "rss": sirf url chahiye.
# type "html": item (har job ka block), title, link selectors chahiye.
SOURCES = [
    # {"name": "Example RSS", "type": "rss", "sector": "govt",
    #  "url": "https://example.com/feed/"},
    # {"name": "Example HTML list", "type": "html", "sector": "govt",
    #  "url": "https://example.com/latest-jobs",
    #  "item": "table.jobs tr",          # TODO: apni site ke hisaab se
    #  "title": "td.title a",            # TODO
    #  "link": "td.title a"},            # TODO
]

QUAL_PATTERNS = [  # upar se neeche, sabse ooncha pehle
    (4, r"post[\s-]?graduat|master'?s|\bm\.?sc\b|\bm\.?a\b|\bm\.?com\b|\bmba\b|\bm\.?tech\b"),
    (3, r"graduat|bachelor|\bb\.?e\b|\bb\.?tech\b|\bb\.?sc\b|\bb\.?com\b|\bb\.?a\b|degree"),
    (2, r"12th|\+2|intermediate|higher secondary|\bhsc\b"),
    (1, r"10th|matric|\bssc\b exam passed|secondary school"),
]
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}

# ---------------------------------------------------------------- http
session = requests.Session()
session.headers["User-Agent"] = USER_AGENT
_robots = {}


def allowed(url: str) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = robotparser.RobotFileParser()
        rp.set_url(base + "/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        _robots[base] = rp
    rp = _robots[base]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def get(url: str):
    if not allowed(url):
        print(f"  robots.txt allow nahi karta, skip: {url}")
        return None
    try:
        r = session.get(url, timeout=20)
        r.raise_for_status()
        time.sleep(DELAY_SECONDS)
        return r
    except Exception as e:
        print(f"  fetch fail {url}: {e}")
        return None


# ---------------------------------------------------------------- extraction
def parse_date(text: str):
    """Pehli last-date jaisi date. Returns ISO string ya None."""
    t = text.lower()
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](20\d{2})", t)
    if m:
        d, mo, y = map(int, m.groups())
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3,9})[,\s]+(20\d{2})", t)
    if m and m.group(2) in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1))).isoformat()
        except ValueError:
            pass
    return None


def find_last_date(text: str):
    m = re.search(r"(last date|closing date|apply (?:on or )?before|last day)[^0-9]{0,40}([0-9][^\n]{0,30})", text, re.I)
    return parse_date(m.group(2)) if m else None


def find_qual(text: str):
    t = text.lower()
    for level, pat in QUAL_PATTERNS:
        if re.search(pat, t):
            return level
    return None


def find_age(text: str):
    m = re.search(r"(\d{2}(?:\.\d)?)\s*(?:-|–|to)\s*(\d{2}(?:\.\d)?)\s*years", text, re.I)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def find_posts(text: str):
    m = re.search(r"([\d,]{1,7})\s*(?:posts|vacancies|vacancy)", text, re.I)
    return f"{m.group(1)} posts" if m else ""


def build_job(source, title, link, text):
    last = find_last_date(text)
    min_age, max_age = find_age(text)
    return {
        "title": title.strip(),
        "org": source["name"],
        "sector": source.get("sector", "govt"),
        "kind": "live" if last else "awaited",
        "when": None if last else "Date check karo",
        "posts": find_posts(text),
        "qual": find_qual(text),
        "minAge": min_age,
        "maxGen": max_age,
        "relax": source.get("sector", "govt") == "govt",
        "open": None,
        "last": last,
        "note": "Auto-scraped. Official notification se verify karo.",
        "status": "Auto-scraped",
        "link": link,
        "src": urlparse(link).netloc,
    }


def detail_text(link: str) -> str:
    r = get(link)
    return BeautifulSoup(r.text, "html.parser").get_text("\n") if r else ""


# ---------------------------------------------------------------- sources
def scrape_rss(source):
    feed = feedparser.parse(source["url"])
    for e in feed.entries[:MAX_ITEMS_PER_SOURCE]:
        text = BeautifulSoup(e.get("summary", ""), "html.parser").get_text("\n")
        link = e.get("link", "")
        if FETCH_DETAIL_PAGES and link:
            text += "\n" + detail_text(link)
        yield build_job(source, e.get("title", ""), link, text)


def scrape_html(source):
    r = get(source["url"])
    if not r:
        return
    soup = BeautifulSoup(r.text, "html.parser")
    for item in soup.select(source["item"])[:MAX_ITEMS_PER_SOURCE]:
        t = item.select_one(source["title"])
        a = item.select_one(source["link"])
        if not t or not a or not a.get("href"):
            continue
        link = urljoin(source["url"], a["href"])
        text = item.get_text("\n")
        if FETCH_DETAIL_PAGES:
            text += "\n" + detail_text(link)
        yield build_job(source, t.get_text(" ", strip=True), link, text)


# ---------------------------------------------------------------- main
def main():
    if not SOURCES:
        print("SOURCES khaali hai. scraper.py kholo aur kam se kam ek source daalo.")
        return 1
    jobs, seen = [], set()
    if MANUAL.exists():
        for j in json.loads(MANUAL.read_text(encoding="utf-8")):
            jobs.append(j)
            seen.add(j.get("link"))
    for s in SOURCES:
        print(f"Scraping {s['name']} ...")
        fn = scrape_rss if s["type"] == "rss" else scrape_html
        for job in fn(s):
            if job["link"] in seen or not job["title"]:
                continue
            seen.add(job["link"])
            jobs.append(job)
    today = date.today().isoformat()
    jobs = [j for j in jobs if not j.get("last") or j["last"] >= today]
    for i, j in enumerate(jobs, 1):
        j["id"] = i
    OUTPUT.write_text(json.dumps({"updated": datetime.now().isoformat(timespec="minutes"), "jobs": jobs},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(jobs)} jobs {OUTPUT} mein likhi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
