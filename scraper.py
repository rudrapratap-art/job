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
import hashlib
import json
import os
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib import robotparser

import requests
from bs4 import BeautifulSoup, NavigableString

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
    # Listing pages jahan har job ek link hai: "link_regex" se href chuno, "title_regex" (optional)
    # se anchor text filter karo. Ye HTML classes par nirbhar nahi hai.
    {"name": "SarkariResult", "type": "html", "sector": "govt",
     "url": "https://www.sarkariresult.com/latestjob/",
     "link_regex": r"/20(?:26|27)/"},
    {"name": "ResultBharat", "type": "html", "sector": "govt",
     "url": "https://www.resultbharat.com/latestjobs_more.html",
     "link_regex": r"resultbharat\.com/[^?#]+\.html$",
     "title_regex": r"online form|recruitment|vacanc|\bposts?\b"},
    # {"name": "Example RSS", "type": "rss", "sector": "govt",
    #  "url": "https://example.com/feed/"},
    # {"name": "Example HTML list", "type": "html", "sector": "govt",
    #  "url": "https://example.com/latest-jobs",
    #  "item": "table.jobs tr",          # TODO: apni site ke hisaab se
    #  "title": "td.title a",            # TODO
    #  "link": "td.title a"},            # TODO
]

# (level, shabd-pattern [case-insensitive], short-form pattern [case-sensitive])
QUAL_PATTERNS = [
    (4, r"post[\s-]?graduat|master'?s|masters", r"\bM\.Sc\b|\bM\.Com\b|\bM\.A\b|\bMBA\b|\bM\.Tech\b|\bMSc\b|\bMCA\b"),
    (3, r"graduat|bachelor|degree|engineering", r"\bB\.E\b|\bB\.Tech\b|\bBTech\b|\bB\.Sc\b|\bBSc\b|\bB\.Com\b|\bBCA\b|\bB\.A\b|\bB\.Ed\b"),
    (2, r"\b12th\b|intermediate|higher secondary|\+2\b", r"\bHSC\b"),
    (1, r"\b10th\b|matric|high school", r"\bSSLC\b"),
]
TITLE_JOB_RE = re.compile(r"online form|recruitment|vacanc|\bposts?\b|bharti|apply", re.I)
TITLE_SKIP_RE = re.compile(r"result|admit card|answer key|syllabus|certificate|download|admission|cut[\s-]?off|score\s?card|city|exam date|counselling|\bjee|\bneet|\bcuet|\bnta\b", re.I)
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
    """Apply karne ki last date. Fee / exam / correction wali dates chhod dete hain.
    'Apply' wale label ko pehle chunte hain."""
    best = None
    pat = r"(last date[^\n:]{0,40}|closing date|apply (?:on or )?before|last day)[^0-9]{0,25}([0-9][^\n]{0,30})"
    for m in re.finditer(pat, text, re.I):
        before = text[max(0, m.start() - 25): m.start()].lower()
        label = m.group(1).lower()
        if re.search(r"fee|exam|correction|admit|result|payment", before + label):
            continue
        dt = parse_date(m.group(2))
        if not dt:
            continue
        if "apply" in label:
            return dt
        best = best or dt
    return best


def find_qual(text: str):
    """Sirf 'Qualification' / 'Eligibility' ke baad ki 250 characters dekho (poore page ka menu nahi).
    Alag-alag level mile (alag posts, ya page par idhar-udhar ka text) to None, "check karo" ke liye."""
    levels = set()
    for m in re.finditer(r"qualification|eligibility", text, re.I):
        window = text[m.end(): m.end() + 250]
        for level, words, short in QUAL_PATTERNS:
            if re.search(words, window, re.I) or re.search(short, window):
                levels.add(level)
    return levels.pop() if len(levels) == 1 else None   # ek se zyada level mile to andaaza mat lagao


def find_age(text: str):
    """Umar ki range tabhi lo jab poore page par sirf EK range mile (aur wo sahi lage).
    Alag posts ki alag limit ho to galat filter se behtar hai ki khaali chhodo."""
    ranges = set()
    for m in re.finditer(r"(\d{2}(?:\.\d)?)\s*(?:-|\u2013|to)\s*(\d{2}(?:\.\d)?)\s*years", text, re.I):
        ranges.add((float(m.group(1)), float(m.group(2))))
    if len(ranges) != 1:
        return None, None
    lo, hi = ranges.pop()
    if 14 <= lo <= 27 and lo < hi <= 45:
        return lo, hi
    return None, None


def find_posts(text: str):
    m = re.search(r"([\d,]{1,7})\s*(?:posts?|vacancies|vacancy)", text, re.I)
    return f"{m.group(1)} posts" if m else ""


def _build_basic(source, title, link, text):
    last = find_last_date(text)
    min_age, max_age = find_age(text)
    return {
        "title": title.strip(),
        "org": source["name"],
        "sector": source.get("sector", "govt"),
        "kind": "live" if last else "hiring",   # date na mile to "Hiring / Check karo" dikhao
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


def build_job(source, title, link, text):
    title = re.sub(r"\s*\|\s*(?:last date|post date).*$", "", title, flags=re.I)
    job = _build_basic(source, title, link, text)
    return enrich(job, text) if GEMINI_KEY else job


def page_text(html: str) -> str:
    """Page ka text. Table ki har row ek line banti hai ("Post | Qualification | Age"),
    taaki row-column ka mel na toote. Andar table wali bahari rows chhod di jaati hain."""
    soup = BeautifulSoup(html, "html.parser")
    for tr in soup.find_all("tr"):
        if tr.find("table"):
            continue
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        cells = [c for c in cells if c]
        if cells:
            tr.replace_with(NavigableString(" | ".join(cells) + "\n"))
    return soup.get_text("\n")


def detail_text(link: str) -> str:
    r = get(link)
    return page_text(r.text) if r else ""


# ---------------------------------------------------------------- Gemini
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")   # gemini_test.py se pata karo tumhari key par kaunsa chalta hai
LLM_DELAY = float(os.environ.get("LLM_DELAY", "6"))                  # free tier ki rate limit ke liye
LLM_CACHE = Path("llm_cache.json")
DEBUG_LLM = bool(os.environ.get("DEBUG_LLM"))
MAX_LLM_CHARS = 20000
GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "60"))

SCHEMA = {
    "type": "object",
    "properties": {
        "isJobRecruitment": {"type": "boolean"},
        "organisation": {"type": "string"},
        "lastDate": {"type": "string"},
        "totalPosts": {"type": "integer"},
        "postList": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "qual": {"type": "integer"},
                    "minAge": {"type": "number"},
                    "maxAge": {"type": "number"},
                    "experienceYears": {"type": "number"},
                },
                "required": ["name", "qual", "minAge", "maxAge", "experienceYears"],
            },
        },
    },
    "required": ["isJobRecruitment", "organisation", "lastDate", "totalPosts", "postList"],
}

PROMPT = """You read an Indian job notification web page and extract eligibility facts.
Use ONLY what the page explicitly states. If a value is not stated, use 0 (numbers) or "" (strings). Never guess.

Fields:
- isJobRecruitment: false if the page is an exam result, admit card, answer key, syllabus, college admission or entrance exam. true only for job / apprenticeship recruitment.
- organisation: the recruiting body.
- lastDate: last date to APPLY (not fee payment, correction, or exam date), as YYYY-MM-DD, or "".
- totalPosts: total vacancies, or 0.
- postList: one entry per distinct post. If one notification covers categories with DIFFERENT education requirements (for example trade/ITI apprentices, diploma apprentices and graduate apprentices), write a SEPARATE entry for each category. Never merge posts with different requirements into one entry.
  - name: post name.
  - qual: minimum education for that post: 1 = 10th pass, 2 = 12th pass / ITI / diploma, 3 = bachelor's degree (including engineering, MBBS, B.Ed), 4 = master's degree or higher, 0 = not stated.
  - minAge, maxAge: age limits for the General/Unreserved category only (not reserved-category relaxations), or 0.
  - experienceYears: minimum years of experience required for that post, including years of service required in a lower post (for example '12 years as PGT' means 12), or 0.

Page title: {title}

Page text:
{text}
"""


def _find_json(x):
    """API response ka shape kuch bhi ho, usme se hamara JSON dhoondo."""
    if isinstance(x, dict):
        if "postList" in x and "lastDate" in x:
            return x
        for v in x.values():
            r = _find_json(v)
            if r:
                return r
    elif isinstance(x, list):
        for v in x:
            r = _find_json(v)
            if r:
                return r
    elif isinstance(x, str):
        try:
            d = json.loads(x)
        except ValueError:
            return None
        return _find_json(d) if isinstance(d, (dict, list)) else None
    return None


def _call_gemini(prompt: str):
    """Pehle generateContent, na chale to naya Interactions API."""
    headers = {"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"}
    base = "https://generativelanguage.googleapis.com/v1beta"
    attempts = [
        (f"{base}/models/{GEMINI_MODEL}:generateContent", {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": SCHEMA}}),
        (f"{base}/interactions", {
            "model": GEMINI_MODEL, "input": prompt,
            "response_format": {"type": "text", "mime_type": "application/json", "schema": SCHEMA}}),
    ]
    for url, body in attempts:
        for _ in range(3):
            try:
                r = requests.post(url, headers=headers, json=body, timeout=GEMINI_TIMEOUT)
            except Exception as e:
                print(f"  gemini network error: {type(e).__name__}")
                return None
            if r.status_code == 429:
                print("  gemini rate limit, 30 second ruk raha hu")
                time.sleep(30)
                continue
            if r.status_code >= 400:
                print(f"  gemini {r.status_code} ({url.rsplit('/', 1)[-1]}): {r.text[:200]}")
                break
            data = _find_json(r.json())
            if DEBUG_LLM or not data:
                print("  gemini raw:", r.text[:600])
            if data:
                return data
            break
    return None


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def enrich(job, text):
    """Gemini se padhkar job ki posts, last date, qualification, umar bharo. Job na ho to None."""
    cache = json.loads(LLM_CACHE.read_text(encoding="utf-8")) if LLM_CACHE.exists() else {}
    key = hashlib.sha1((PROMPT + text[:MAX_LLM_CHARS]).encode("utf-8")).hexdigest()
    data = cache.get(key)
    if data is None:
        prompt = PROMPT.replace("{title}", job["title"]).replace("{text}", text[:MAX_LLM_CHARS])
        data = _call_gemini(prompt)
        time.sleep(LLM_DELAY)
        if data is None:
            return job                      # Gemini fail: regex wala (kam bharose ka) result rakho
        cache[key] = data
        LLM_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    if not data.get("isJobRecruitment", True):
        return None
    posts = []
    for po in data.get("postList", []):
        q = int(po.get("qual") or 0)
        posts.append({"name": (po.get("name") or "").strip(),
                      "qual": q if 1 <= q <= 4 else None,
                      "minAge": _num(po.get("minAge")), "maxAge": _num(po.get("maxAge")),
                      "exp": _num(po.get("experienceYears")) or 0})
    last = data.get("lastDate") or ""
    if re.fullmatch(r"20\d\d-\d\d-\d\d", last):
        job["last"] = last
    job["postList"] = posts
    for k in ("qual", "minAge", "maxGen"):
        job[k] = None                       # ab har post ki apni limit hai
    job["kind"] = "live" if job.get("last") else "hiring"
    if data.get("organisation"):
        job["org"] = data["organisation"]
    if data.get("totalPosts"):
        job["posts"] = f"{data['totalPosts']:,} posts"
    job["note"] = "Gemini se padha gaya. Official notification se verify karo."
    job["status"] = "AI-extracted"
    return job


# ---------------------------------------------------------------- sources
def scrape_rss(source):
    import feedparser  # sirf RSS source ke liye zaruri
    feed = feedparser.parse(source["url"])
    for e in feed.entries[:MAX_ITEMS_PER_SOURCE]:
        text = BeautifulSoup(e.get("summary", ""), "html.parser").get_text("\n")
        link = e.get("link", "")
        if FETCH_DETAIL_PAGES and link:
            text += "\n" + detail_text(link)
        yield build_job(source, e.get("title", ""), link, text)


def scrape_links(source, soup):
    """Listing page par har job ek link hota hai: href aur anchor text se pehchano."""
    href_re = re.compile(source["link_regex"])
    title_re = re.compile(source["title_regex"], re.I) if source.get("title_regex") else None
    seen, n = set(), 0
    for a in soup.find_all("a", href=True):
        link = urljoin(source["url"], a["href"]).split("#")[0]
        title = a.get_text(" ", strip=True)
        if link in seen or len(title) < 12 or not href_re.search(link):
            continue
        if title_re and not title_re.search(title):
            continue
        if TITLE_SKIP_RE.search(title) or not TITLE_JOB_RE.search(title):
            continue
        seen.add(link)
        text = title
        if FETCH_DETAIL_PAGES:
            text += "\n" + detail_text(link)
        yield build_job(source, title, link, text)
        n += 1
        if n >= MAX_ITEMS_PER_SOURCE:
            break


def scrape_html(source):
    r = get(source["url"])
    if not r:
        return
    soup = BeautifulSoup(r.text, "html.parser")
    if "link_regex" in source:
        yield from scrape_links(source, soup)
        return
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


def dedupe(jobs):
    """Ek hi job do sites par ho to ek rakho. Pehchan: organisation ke pehle 2 shabd + last date + posts ki ginti.
    Jis entry mein zyada posts ki detail ho, wahi rakho."""
    out, index = [], {}
    for j in jobs:
        org = " ".join(re.findall(r"[a-z]+", (j.get("org") or "").lower())[:2])
        if not (j.get("last") and j.get("posts") and org):
            out.append(j)
            continue
        key = (org, j["last"], j["posts"])
        if key in index:
            k = index[key]
            if len(j.get("postList", [])) > len(out[k].get("postList", [])):
                out[k] = j
            continue
        index[key] = len(out)
        out.append(j)
    return out


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
            if not job or job["link"] in seen or not job["title"]:
                continue
            seen.add(job["link"])
            jobs.append(job)
    today = date.today().isoformat()
    jobs = [j for j in jobs if not j.get("last") or j["last"] >= today]
    jobs = dedupe(jobs)
    for i, j in enumerate(jobs, 1):
        j["id"] = i
    OUTPUT.write_text(json.dumps({"updated": datetime.now().isoformat(timespec="minutes"), "jobs": jobs},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(jobs)} jobs {OUTPUT} mein likhi. Gemini: " + ("chalu" if GEMINI_KEY else "band (GEMINI_API_KEY set nahi)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
