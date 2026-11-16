import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

session = requests.Session()
session.headers.update(HEADERS)


def get_soup(url):
    try:
        response = session.get(url, timeout=15, verify=False)
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def scrape_sarkari_result():
    url = "https://www.sarkariresult.com/"
    jobs = []
    soup = get_soup(url)
    if not soup:
        return jobs

    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        if ("Online Form" in text or "Apply Online" in text or "Result" in text) and len(text) > 15:
            href = a['href']
            full_url = href if href.startswith('http') else f"https://www.sarkariresult.com/{href}"

            detail = scrape_detail_page(full_url)

            jobs.append({
                "title": text,
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
        parent_text = a.parent.get_text(strip=True)
        if ("Last date" in parent_text or "Posts" in parent_text) and len(text) > 10:
            href = a['href']
            full_url = href if href.startswith('http') else f"https://govtjobsalert.in/{href}"

            detail = scrape_detail_page(full_url)

            jobs.append({
                "title": text,
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
        href = a['href']
        if len(text) > 15 and "http" in href:
            detail = scrape_detail_page(href)

            jobs.append({
                "title": text,
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


def scrape_detail_page(url):
    soup = get_soup(url)
    if not soup:
        return {}

    text = soup.get_text(" ", strip=True)

    qualification = ""
    age_limit = ""
    last_date = ""
    posts = ""
    salary = ""
    application_fee = ""
    selection_process = ""

    qual_patterns = [
        r"(?:Qualification|Educational|Eligibility)[:\s]*([^.]{0,200})",
        r"(?:10th|12th|Graduation|B\.Tech|B\.E|M\.Tech|MBA|MCA|B\.Sc|M\.Sc|B\.Com|M\.Com|B\.A|M\.A)[^.]{0,100}",
    ]
    for pattern in qual_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            qualification = m.group(0).strip()[:200]
            break

    age_patterns = [
        r"(?:Age|Age Limit)[:\s]*([^.]{0,100})",
        r"(?:18|20|21|25|30|35|40)\s*(?:to|[-–])\s*(\d{1,2})\s*years",
    ]
    for pattern in age_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            age_limit = m.group(0).strip()[:100]
            break

    date_patterns = [
        r"(?:Last Date|Closing Date|Apply Before)[:\s]*([^.]{0,100})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ]
    for pattern in date_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            last_date = m.group(0).strip()[:100]
            break

    posts_patterns = [
        r"(?:Posts|Vacancies|Total Posts)[:\s]*([^.]{0,100})",
        r"(\d{1,3}(?:,\d{3})*)\s*posts?",
    ]
    for pattern in posts_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            posts = m.group(0).strip()[:100]
            break

    salary_patterns = [
        r"(?:Salary|Pay Scale|Salary Band)[:\s]*([^.]{0,150})",
        r"(?:₹|Rs\.?)\s*[\d,]+(?:\s*[-–]\s*[\d,]+)?",
    ]
    for pattern in salary_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            salary = m.group(0).strip()[:150]
            break

    fee_patterns = [
        r"(?:Application Fee|Exam Fee)[:\s]*([^.]{0,100})",
    ]
    for pattern in fee_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            application_fee = m.group(0).strip()[:100]
            break

    sel_patterns = [
        r"(?:Selection Process|Selection)[:\s]*([^.]{0,200})",
    ]
    for pattern in sel_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            selection_process = m.group(0).strip()[:200]
            break

    return {
        "qualification": qualification,
        "age_limit": age_limit,
        "last_date": last_date,
        "posts": posts,
        "salary": salary,
        "application_fee": application_fee,
        "selection_process": selection_process,
    }


def main():
    print("🚀 Starting Deep Job Scraper...")
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

    print(f"✅ Found {len(unique_jobs)} unique jobs with details.")

    os.makedirs("public", exist_ok=True)
    with open("public/jobs.json", "w", encoding="utf-8") as f:
        json.dump(unique_jobs, f, indent=2, ensure_ascii=False)
    print("💾 Successfully saved to public/jobs.json")


if __name__ == "__main__":
    main()
