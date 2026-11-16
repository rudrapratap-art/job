import requests
from bs4 import BeautifulSoup
import json
import os
import re
import urllib3
from datetime import datetime

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Junk titles to skip
JUNK_TITLES = {
    "skip to content", "home", "about", "contact", "privacy", "disclaimer",
    "terms", "sitemap", "rss feed", "search", "login", "register", "advertise",
    "write for us", "cookie policy", "copyright", "dmca", "career", "team"
}

# Words that indicate this is not a real job title
JUNK_PATTERNS = [
    r"^skip to",
    r"^home$",
    r"^about$",
    r"^contact$",
    r"menu",
    r"search",
    r"facebook|twitter|instagram|telegram|youtube|whatsapp",
]

session = requests.Session()
session.headers.update(HEADERS)


def is_junk_title(text):
    """Check if title is junk/navigation"""
    if not text or len(text) < 10:
        return True
    text_lower = text.lower().strip()
    if text_lower in JUNK_TITLES:
        return True
    for pattern in JUNK_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def clean_title(text, parent_text=""):
    """Clean title by removing parent text artifacts"""
    if not text:
        return ""
    title = text.strip()

    # Remove common artifacts found in govtjobsalert.in titles
    # e.g. "AFCAT 01/2027 Flying, Ground Duty & More284 PostsLast date 11 Dec→"
    # Remove trailing arrows/symbols
    title = re.sub(r"[→➔➣►➤➥]+$", "", title).strip()

    # If parent text contains posts/last_date patterns, try to separate them
    # Look for patterns like "284 PostsLast date 11 Dec" in title
    # Split on known delimiters
    title = re.sub(r"(\d+)\s*Posts(\d+)", r"\1 Posts \2", title)
    title = re.sub(r"(\d+)\s*Last\s*date", r" Last date", title)

    # Remove extra whitespace
    title = re.sub(r"\s+", " ", title).strip()

    # Limit length
    if len(title) > 200:
        title = title[:200] + "..."

    return title


def get_soup(url):
    try:
        response = session.get(url, timeout=15, verify=False)
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def scrape_detail_page(url):
    """Lightweight detail page scraping for key fields only"""
    soup = get_soup(url)
    if not soup:
        return {}

    text = soup.get_text(" ", strip=True)

    posts = ""
    last_date = ""
    qualification = ""
    age_limit = ""

    # Posts
    m = re.search(r"(\d{1,3}(?:,\d{3})*)\s*posts?", text, re.I)
    if m:
        posts = m.group(0).strip()[:50]

    # Last date
    m = re.search(r"(?:Last\s*Date|Closing\s*Date|Apply\s*Before)[:\s]*([^.\n]{0,80})", text, re.I)
    if m:
        last_date = m.group(1).strip()[:80]
    else:
        m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
        if m:
            last_date = m.group(0).strip()[:80]

    # Qualification
    m = re.search(r"(?:Qualification|Educational|Eligibility)[:\s]*([^.\n]{0,150})", text, re.I)
    if m:
        qualification = m.group(1).strip()[:150]

    # Age limit
    m = re.search(r"(?:Age\s*Limit|Age)[:\s]*([^.\n]{0,80})", text, re.I)
    if m:
        age_limit = m.group(1).strip()[:80]

    return {
        "qualification": qualification,
        "age_limit": age_limit,
        "last_date": last_date,
        "posts": posts,
        "salary": "",
        "application_fee": "",
        "selection_process": "",
    }


def scrape_sarkari_result():
    url = "https://www.sarkariresult.com/"
    jobs = []
    soup = get_soup(url)
    if not soup:
        return jobs

    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        if is_junk_title(text):
            continue
        if ("Online Form" in text or "Apply Online" in text or "Result" in text) and len(text) > 15:
            href = a['href']
            full_url = href if href.startswith('http') else f"https://www.sarkariresult.com/{href}"

            detail = scrape_detail_page(full_url)
            clean_t = clean_title(text)

            jobs.append({
                "title": clean_t or text,
                "organization": "Sarkari Result",
                "category": "Latest Job" if "Form" in text else "Result",
                "url": full_url,
                "source": "sarkariresult.com",
                "date_added": datetime.now().strftime("%Y-%m-%d"),
                "qualification": detail.get("qualification", ""),
                "age_limit": detail.get("age_limit", ""),
                "last_date": detail.get("last_date", ""),
                "posts": detail.get("posts", ""),
                "salary": detail.get("salary", ""),
                "application_fee": detail.get("application_fee", ""),
                "selection_process": detail.get("selection_process", ""),
            })
    return jobs


def scrape_govt_jobs_alert():
    url = "https://govtjobsalert.in/"
    jobs = []
    soup = get_soup(url)
    if not soup:
        return jobs

    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        if is_junk_title(text):
            continue
        parent_text = a.parent.get_text(strip=True)
        if ("Last date" in parent_text or "Posts" in parent_text) and len(text) > 10:
            href = a['href']
            full_url = href if href.startswith('http') else f"https://govtjobsalert.in/{href}"

            detail = scrape_detail_page(full_url)
            clean_t = clean_title(text, parent_text)

            jobs.append({
                "title": clean_t or text,
                "organization": "Govt Jobs Alert",
                "category": "Latest Job",
                "url": full_url,
                "source": "govtjobsalert.in",
                "date_added": datetime.now().strftime("%Y-%m-%d"),
                "qualification": detail.get("qualification", ""),
                "age_limit": detail.get("age_limit", ""),
                "last_date": detail.get("last_date", ""),
                "posts": detail.get("posts", ""),
                "salary": detail.get("salary", ""),
                "application_fee": detail.get("application_fee", ""),
                "selection_process": detail.get("selection_process", ""),
            })
    return jobs


def scrape_result_bharat():
    url = "https://www.resultbharat.com/latestjobs_more.html"
    jobs = []
    soup = get_soup(url)
    if not soup:
        return jobs

    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        if is_junk_title(text):
            continue
        href = a['href']
        if len(text) > 15 and "http" in href:
            detail = scrape_detail_page(href)
            clean_t = clean_title(text)

            jobs.append({
                "title": clean_t or text,
                "organization": "Result Bharat",
                "category": "Latest Job",
                "url": href,
                "source": "resultbharat.com",
                "date_added": datetime.now().strftime("%Y-%m-%d"),
                "qualification": detail.get("qualification", ""),
                "age_limit": detail.get("age_limit", ""),
                "last_date": detail.get("last_date", ""),
                "posts": detail.get("posts", ""),
                "salary": detail.get("salary", ""),
                "application_fee": detail.get("application_fee", ""),
                "selection_process": detail.get("selection_process", ""),
            })
    return jobs


def main():
    print("🚀 Starting Job Scraper...")
    all_jobs = []
    all_jobs.extend(scrape_sarkari_result())
    all_jobs.extend(scrape_govt_jobs_alert())
    all_jobs.extend(scrape_result_bharat())

    seen_urls = set()
    unique_jobs = []
    for job in all_jobs:
        if job['url'] not in seen_urls:
            seen_urls.add(job['url'])
            unique_jobs.append(job)

    print(f"✅ Found {len(unique_jobs)} unique jobs.")

    os.makedirs("public", exist_ok=True)
    with open("public/jobs.json", "w", encoding="utf-8") as f:
        json.dump(unique_jobs, f, indent=2, ensure_ascii=False)
    print("💾 Successfully saved to public/jobs.json")


if __name__ == "__main__":
    main()
