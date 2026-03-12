# stats100 — Cricket data scraping & statistics

Scrape ESPNcricinfo Statsguru player tables and run a **Markov chain** T20 simulation for multiple matchups (India vs New Zealand, Argentina vs Suriname, Sri Lanka vs Afghanistan) to estimate expected runs and win probabilities.

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

## 2. Markov chain simulation

The simulation uses playing XIs (batting order in `lineups.py`) and fetches T20I batting stats from [ESPNcricinfo Statsguru](https://stats.espncricinfo.com/ci/engine/player/446507.html?class=3;template=results;type=batting). You can use **career** T20I averages or **last 9 months** (or any `--span N` months). Stats are converted into per-ball outcome probabilities P(0), P(1), P(2), P(4), P(6), P(out); those drive the chain (strike rotation on 1/2/3, next batter on wicket). We simulate full T20 innings (120 balls, 10 wickets) per team and compare totals for win probability.

**Run (India vs New Zealand only):**

```bash
python run_markov_simulation.py --career --sims 10000 --seed 42
```

- **`--career`** — Use career T20I stats (default). Otherwise use **`--span N`** for last N months (e.g. `--span 9`).
- **`--sims`** — Number of match simulations.
- **`--seed`** — Random seed.

Stats are cached in `markov_cache/batting_stats.json` per team.

**Output:** Expected runs for each team and P(team1 wins).

## 3. Matchups and plots

**Matchups** (defined in `lineups.py`): **India vs New Zealand**, **Argentina vs Suriname**, **Sri Lanka vs Afghanistan**. Lineups use ESPNcricinfo player IDs; unknown IDs use default probabilities.

**Generate plots** (optionally for one matchup or all):

```bash
# One matchup, career data
python generate_plots.py --matchup "India vs New Zealand" --career --sims 5000 --outdir plots

# Last 9 months for a matchup
python generate_plots.py --matchup "Sri Lanka vs Afghanistan" --span 9 --sims 5000 --outdir plots

# All three matchups, career data
python generate_plots.py --all --career --sims 5000 --outdir plots
```

- **`--matchup "X vs Y"`** — Run only that matchup (default: India vs New Zealand).
- **`--all`** — Run India vs NZ, Argentina vs Suriname, Sri Lanka vs Afghanistan.
- **`--career`** — Career T20I averages. **`--span N`** — Last N months (e.g. 9).
- **`--sims`** — Simulations per matchup.
- **`--outdir`** — Output directory (default `plots`).

**Output files** (per matchup, with slugged names e.g. `india_vs_new_zealand_*`):

- **`*_simulated_team_totals.png`** — Histograms of simulated innings totals and average expected total for each team.
- **`*_actual_vs_predicted.png`** — Per player: actual runs/ball (from stats) vs model-predicted runs/ball.
- **`*_win_probability_and_totals.png`** — Density of both teams’ totals and P(team1 wins).
- **`*_probability_table.png`** — **Table of probabilities**: each player (both teams) × P(0), P(1), P(2), P(4), P(6), P(out).
- **`*_transition_matrix_<team>.png`** — **Markov transition matrix** (11×11): P(next striker = j | current striker = i) for that team’s batting order.

Requires `matplotlib`. Data source (career vs 9-month) is printed when the script runs.

## If you get blocked (403 / bot protection)

- **Option A:** `pip install cloudscraper` and use `cloudscraper.create_scraper()` instead of `requests.Session()`.
- **Option B:** Use Playwright for headless browser rendering (see comments at bottom of `scrape_cricinfo_player.py`).
