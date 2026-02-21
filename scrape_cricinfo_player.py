"""
scrape_cricinfo_player.py

Scrapes "relevant" ESPNcricinfo Statsguru player tables (batting, bowling, fielding, dismissal summaries, etc.)
for a given player_id and saves everything to CSV + a single Excel workbook.

Example URL you gave (fielding dismissal summary):
https://stats.espncricinfo.com/ci/engine/player/625371.html?class=3;template=results;type=fielding;view=dismissal_summary

USAGE
-----
python scrape_cricinfo_player.py --player_id 625371 --out_dir data_625371

Dependencies
------------
pip install requests pandas lxml beautifulsoup4 openpyxl tqdm

Notes
-----
- ESPNcricinfo pages usually contain HTML tables; we use pandas.read_html for reliability.
- If you get blocked (403 / bot protection), see the "If you get blocked" section at bottom.
"""

from __future__ import annotations

import argparse
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


BASE = "https://stats.espncricinfo.com/ci/engine/player/{player_id}.html"
DEFAULT_HEADERS = {
    # Spoof a normal browser UA; this often avoids trivial blocking.
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}


@dataclass(frozen=True)
class QuerySpec:
    type: str                      # batting | bowling | fielding | ...
    view: Optional[str] = None      # e.g., dismissal_summary
    cls: Optional[int] = None       # "class" in querystring (format)
    extra_params: Optional[Dict[str, str]] = None


def make_url(player_id: int, spec: QuerySpec) -> str:
    # ESPN Statsguru expects class first when present (e.g. class=3;template=results;type=fielding;view=...).
    params: List[Tuple[str, str]] = []
    if spec.cls is not None:
        params.append(("class", str(spec.cls)))
    params.append(("template", "results"))
    params.append(("type", spec.type))
    if spec.view:
        params.append(("view", spec.view))
    if spec.extra_params:
        params.extend(spec.extra_params.items())

    # Statsguru uses semicolon-separated query params.
    qp = ";".join([f"{k}={v}" for k, v in params])
    return BASE.format(player_id=player_id) + "?" + qp


def safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s.strip())
    return s[:180] if len(s) > 180 else s


def fetch_html(session: requests.Session, url: str, sleep_s: float = 0.7) -> str:
    r = session.get(url, headers=DEFAULT_HEADERS, timeout=30)
    # Light rate limit to be polite.
    time.sleep(sleep_s)

    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} for {url}\nFirst 300 chars:\n{r.text[:300]}")
    return r.text


def extract_page_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else "cricinfo_page"
    # ESPN titles can be long; keep it shortish.
    return title


def read_tables_from_html(html: str) -> List[pd.DataFrame]:
    # Strip DOCTYPE so lxml does not try to load external DTD (avoids Errno 2).
    html = re.sub(r"<!DOCTYPE[^>]*>", "", html, count=1, flags=re.IGNORECASE | re.DOTALL)
    # read_html can sometimes return empty list if tables not found.
    dfs = pd.read_html(html)
    cleaned = []
    for df in dfs:
        # Drop completely empty columns
        df = df.dropna(axis=1, how="all")
        # Drop completely empty rows
        df = df.dropna(axis=0, how="all")
        if df.shape[0] == 0 or df.shape[1] == 0:
            continue
        cleaned.append(df)
    return cleaned


def normalize_tables(
    dfs: List[pd.DataFrame],
    meta: Dict[str, str],
) -> List[pd.DataFrame]:
    out = []
    for i, df in enumerate(dfs, start=1):
        df2 = df.copy()
        # Attach metadata columns
        for k, v in meta.items():
            df2.insert(0, k, v)
        df2.insert(0, "_table_index", i)
        out.append(df2)
    return out


def save_tables(
    tables: List[pd.DataFrame],
    out_dir: str,
    base_name: str,
) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    saved = []
    for i, df in enumerate(tables, start=1):
        fn = safe_filename(f"{base_name}__table{i}.csv")
        path = os.path.join(out_dir, fn)
        df.to_csv(path, index=False)
        saved.append(path)
    return saved


def write_excel_book(
    all_tables: Dict[str, List[pd.DataFrame]],
    excel_path: str,
) -> None:
    # Excel sheet name limit is 31 chars.
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for key, dfs in all_tables.items():
            # If multiple tables per key, split into multiple sheets.
            for i, df in enumerate(dfs, start=1):
                sheet = safe_filename(key)[:25]
                if len(dfs) > 1:
                    sheet = f"{sheet}_{i}"
                sheet = sheet[:31]
                df.to_excel(writer, sheet_name=sheet, index=False)


def build_default_specs() -> List[QuerySpec]:
    """
    ESPN uses `class` to represent match format in Statsguru.

    Common mapping (not guaranteed for every view):
      1: Tests
      2: ODIs
      3: T20Is
      4: First-class (sometimes)
      5: List A
      6: T20 (all T20s)
      9: ??? (varies)
      10: ??? (varies)

    Instead of assuming, we try a reasonable set of class values.
    """
    classes_to_try = [1, 2, 3, 4, 5, 6]  # broad coverage

    specs: List[QuerySpec] = []

    # Core "results" tables
    for c in classes_to_try:
        specs.extend(
            [
                QuerySpec(type="batting", cls=c, view="innings"),
                QuerySpec(type="batting", cls=c, view="results"),
                QuerySpec(type="bowling", cls=c, view="innings"),
                QuerySpec(type="bowling", cls=c, view="results"),
                QuerySpec(type="fielding", cls=c, view="results"),
                # Your provided view:
                QuerySpec(type="fielding", cls=c, view="dismissal_summary"),
            ]
        )

    # Career aggregates / overall summaries (often with view=innings or view=results is enough)
    # Some pages also support view=match, view=career, etc. We'll try a few "common" ones without failing the whole run.
    extra_views = ["career", "match", "series"]
    for c in classes_to_try:
        for v in extra_views:
            specs.append(QuerySpec(type="batting", cls=c, view=v))
            specs.append(QuerySpec(type="bowling", cls=c, view=v))
            specs.append(QuerySpec(type="fielding", cls=c, view=v))

    # De-duplicate
    uniq = []
    seen = set()
    for sp in specs:
        key = (sp.type, sp.view, sp.cls, tuple(sorted((sp.extra_params or {}).items())))
        if key not in seen:
            seen.add(key)
            uniq.append(sp)
    return uniq


def main(player_id: int, out_dir: str, sleep_s: float) -> None:
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    session = requests.Session()

    specs = build_default_specs()
    print(f"Player ID: {player_id}")
    print(f"Total query specs to try: {len(specs)}")
    print(f"Output dir: {out_dir}")

    all_tables: Dict[str, List[pd.DataFrame]] = {}
    failures: List[Tuple[str, str]] = []

    for spec in tqdm(specs, desc="Fetching tables"):
        url = make_url(player_id, spec)
        key = f"type={spec.type}__view={spec.view or 'none'}__class={spec.cls or 'none'}"
        try:
            html = fetch_html(session, url, sleep_s=sleep_s)
            title = extract_page_title(html)
            dfs = read_tables_from_html(html)
            if not dfs:
                # No tables is common for unsupported combos; don't treat as fatal.
                continue

            meta = {
                "_url": url,
                "_title": title,
                "_type": spec.type,
                "_view": spec.view or "",
                "_class": str(spec.cls) if spec.cls is not None else "",
            }
            dfs2 = normalize_tables(dfs, meta)
            all_tables[key] = dfs2

            # Save CSVs per key
            save_tables(dfs2, out_dir=out_dir, base_name=key)

        except Exception as e:
            failures.append((url, str(e)))
            continue

    # Write one combined Excel workbook too
    if all_tables:
        excel_path = os.path.join(out_dir, f"player_{player_id}_cricinfo_tables.xlsx")
        write_excel_book(all_tables, excel_path)
        print(f"\nWrote Excel workbook: {excel_path}")

    # Summarize
    print(f"\nSaved {sum(len(v) for v in all_tables.values())} tables across {len(all_tables)} pages.")
    if failures:
        print(f"\n{len(failures)} requests failed (often due to unsupported view/class combos).")
        # Print a few helpful failures
        for url, msg in failures[:8]:
            print(f"- FAIL: {url}\n  {msg.splitlines()[0]}")
        fail_log = os.path.join(out_dir, "failures.txt")
        with open(fail_log, "w", encoding="utf-8") as f:
            for url, msg in failures:
                f.write(url + "\n" + msg + "\n" + ("-" * 80) + "\n")
        print(f"Full failure log: {fail_log}")

    print("\nDone.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--player_id", type=int, required=True, help="ESPNcricinfo player id (e.g., 625371)")
    ap.add_argument("--out_dir", type=str, default="cricinfo_out", help="Output directory")
    ap.add_argument("--sleep", type=float, default=0.7, help="Delay between requests (seconds)")
    args = ap.parse_args()

    main(player_id=args.player_id, out_dir=args.out_dir, sleep_s=args.sleep)

"""
If you get blocked (403 / bot protection):

Option A (often works): add cloudscraper
    pip install cloudscraper
    then replace requests.Session() with cloudscraper.create_scraper()

Option B (heavyweight): use Playwright to render + dump HTML:
    pip install playwright
    playwright install
Then fetch page HTML via a headless browser and pass to pandas.read_html.

If you want, paste your exact error (status code + first few lines) and I'll give you the
least-painful unblock path for your setup.
"""
