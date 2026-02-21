# stats100 — Cricket data scraping & statistics

Scrape ESPNcricinfo Statsguru player tables (batting, bowling, fielding, dismissal summaries, etc.) and save to CSV + Excel. Later: graphs and statistics.

## Setup (Conda)

```bash
conda env create -f environment.yml
conda activate stats100
```

Or with pip only:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python scrape_cricinfo_player.py --player_id 625371 --out_dir data_625371
```

- **`--player_id`** — ESPNcricinfo player ID (e.g. 625371).
- **`--out_dir`** — Output directory for CSVs and Excel workbook (default: `cricinfo_out`).
- **`--sleep`** — Delay between requests in seconds (default: 0.7).

Output: one CSV per table and a single Excel workbook `player_<id>_cricinfo_tables.xlsx` in the output directory.

## If you get blocked (403 / bot protection)

- **Option A:** `pip install cloudscraper` and use `cloudscraper.create_scraper()` instead of `requests.Session()`.
- **Option B:** Use Playwright for headless browser rendering (see comments at bottom of `scrape_cricinfo_player.py`).
