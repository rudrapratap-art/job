# Naukri Radar

Files:
- index.html: website (qualification, umar, category se jobs filter karta hai)
- jobs.json: jobs ka data (abhi haath se bhari 16 entries, 1 Nov 2026)
- scraper.py + requirements.txt: jobs.json apne aap banane wali script
- manual.json (optional): haath se likhi entries, scraper inhe jobs.json mein jod deta hai

Local test (file:// se fetch nahi chalta, isliye server chalao):
    python3 -m http.server 8000
    browser mein http://localhost:8000 kholo

Scraper:
    pip install -r requirements.txt
    scraper.py kholo, SOURCES mein sites ke selectors daalo
    python scraper.py

Hosting: GitHub Pages ya Netlify par index.html aur jobs.json daalo.
jobs.json roz update karne ke liye scraper ko GitHub Actions ya cron par chalao.

Roz auto-update (GitHub Actions):
- Folder ko GitHub repo mein daalo, .github/workflows/scrape.yml ke saath.
- Repo Settings > Actions > General > Workflow permissions: "Read and write" chuno.
- Actions tab se "Update jobs.json" ko ek baar Run workflow karke test karo.
- Render par Static Site isi repo se jodo. Har commit par site apne aap redeploy hogi.
