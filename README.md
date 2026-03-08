# stats100 — Cricket data scraping & statistics

Scrape ESPNcricinfo Statsguru player tables and run a **Markov chain** T20 simulation (India vs New Zealand) to estimate expected runs and P(India wins).

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

## 1. Scraping (single player)

```bash
python scrape_cricinfo_player.py --player_id 625371 --out_dir data_625371
```

- **`--player_id`** — ESPNcricinfo player ID (e.g. 625371).
- **`--out_dir`** — Output directory for CSVs and Excel workbook (default: `cricinfo_out`).
- **`--sleep`** — Delay between requests in seconds (default: 0.7).

Output: one CSV per table and a single Excel workbook `player_<id>_cricinfo_tables.xlsx` in the output directory.

## 2. Markov chain simulation (India vs New Zealand)

The simulation uses the **India vs New Zealand** playing XIs (batting order from your lineup). For each batter it fetches T20I batting stats from [ESPNcricinfo Statsguru](https://stats.espncricinfo.com/ci/engine/player/446507.html?class=3;spanmax1=31+Dec+2026;spanmin1=01+Jan+2026;spanval1=span;template=results;type=batting) and converts them into **per-ball outcome probabilities**: P(4), P(6), P(out), P(1), P(2), P(0). Those drive a Markov chain: each ball is sampled from the current striker’s distribution; on 1/2/3 runs strike rotates; on a wicket the next batter in the order comes in. We simulate full T20 innings (120 balls, 10 wickets) for each team and then compare totals to estimate **P(India wins)**.

**Run:**

```bash
python run_markov_simulation.py --career --sims 10000 --seed 42
```

- **`--career`** — Use career T20I stats (default). Omit and use `--span N` for last N months.
- **`--span N`** — Use stats from last N months (e.g. `--span 9`).
- **`--sims`** — Number of match simulations (default 10000).
- **`--seed`** — Random seed.

Stats are cached in `markov_cache/batting_stats.json` after the first run (when using `--career`).

**Output:** Expected runs for India and New Zealand, and **P(India wins)**.

## If you get blocked (403 / bot protection)

- **Option A:** `pip install cloudscraper` and use `cloudscraper.create_scraper()` instead of `requests.Session()`.
- **Option B:** Use Playwright for headless browser rendering (see comments at bottom of `scrape_cricinfo_player.py`).
