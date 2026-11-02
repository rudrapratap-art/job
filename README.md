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

Gemini se eligibility padhwana (zaruri, warna umar/qualification bharose layak nahi):
- Local: export GEMINI_API_KEY="apni_key"   (Termux mein bhi chalta hai), phir python scraper.py
- Model ka naam badalna ho: export GEMINI_MODEL="naam"   (default gemini-3.8-flash)
- Pehli baar chhote scale par chalao: scraper.py mein MAX_ITEMS_PER_SOURCE = 10 karo
- Galti dhoondhni ho: export DEBUG_LLM=1 (API ka raw jawab dikhata hai)
- Free tier ki limit lage to LLM_DELAY badhao: export LLM_DELAY=12
- llm_cache.json: jo jobs ek baar padh li, unhe dobara Gemini ko nahi bhejta
- GitHub Actions ke liye: repo Settings > Secrets and variables > Actions > New secret, naam GEMINI_API_KEY
- API key kabhi code ya repo mein mat likho.
