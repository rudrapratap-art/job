import requests
from bs4 import BeautifulSoup
import json
import os
import urllib3
from datetime import datetime

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def scrape_sarkari_result():
    url = "https://www.sarkariresult.com/"
    jobs = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            if ("Online Form" in text or "Apply Online" in text or "Result" in text) and len(text) > 15:
                href = a['href']
                full_url = href if href.startswith('http') else f"https://www.sarkariresult.com/{href}"
                jobs.append({
                    "title": text,
                    "organization": "Sarkari Result",
                    "category": "Latest Job" if "Form" in text else "Result",
                    "url": full_url,
                    "source": "sarkariresult.com",
                    "date_added": datetime.now().strftime("%Y-%m-%d"),
                    "qualification": "",
                    "age_limit": "",
                    "last_date": "",
                    "posts": "",
                    "salary": "",
                    "application_fee": "",
                    "selection_process": "",
                })
    except Exception as e:
        print(f"Error scraping Sarkari Result: {e}")
    return jobs

def scrape_govt_jobs_alert():
    url = "https://govtjobsalert.in/"
    jobs = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            parent_text = a.parent.get_text(strip=True)
            if ("Last date" in parent_text or "Posts" in parent_text) and len(text) > 10:
                href = a['href']
                full_url = href if href.startswith('http') else f"https://govtjobsalert.in/{href}"
                jobs.append({
                    "title": text,
                    "organization": "Govt Jobs Alert",
                    "category": "Latest Job",
                    "url": full_url,
                    "source": "govtjobsalert.in",
                    "date_added": datetime.now().strftime("%Y-%m-%d"),
                    "qualification": "",
                    "age_limit": "",
                    "last_date": "",
                    "posts": "",
                    "salary": "",
                    "application_fee": "",
                    "selection_process": "",
                })
    except Exception as e:
        print(f"Error scraping Govt Jobs Alert: {e}")
    return jobs

def scrape_result_bharat():
    url = "https://www.resultbharat.com/latestjobs_more.html"
    jobs = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            href = a['href']
            if len(text) > 15 and "http" in href:
                jobs.append({
                    "title": text,
                    "organization": "Result Bharat",
                    "category": "Latest Job",
                    "url": href,
                    "source": "resultbharat.com",
                    "date_added": datetime.now().strftime("%Y-%m-%d"),
                    "qualification": "",
                    "age_limit": "",
                    "last_date": "",
                    "posts": "",
                    "salary": "",
                    "application_fee": "",
                    "selection_process": "",
                })
    except Exception as e:
        print(f"Error scraping Result Bharat: {e}")
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
