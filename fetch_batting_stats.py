"""
Fetch T20I batting stats from ESPNcricinfo Statsguru for each player in the lineups.
Used to derive per-ball probabilities (P(4), P(6), P(out), P(1), P(2), P(0)) for the Markov chain.

Uses optional date span: e.g. last 9 months via spanmin1/spanmax1/spanval1=span.
Example: https://stats.espncricinfo.com/ci/engine/player/446507.html?class=3;spanmax1=31+Dec+2026;spanmin1=01+Jan+2026;spanval1=span;template=results;type=batting
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from scrape_cricinfo_player import (
    BASE,
    DEFAULT_HEADERS,
    QuerySpec,
    make_url,
)


def fetch_html(session: requests.Session, url: str, sleep_s: float = 0.5) -> str:
    r = session.get(url, headers=DEFAULT_HEADERS, timeout=30)
    time.sleep(sleep_s)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} for {url}")
    return r.text


def _normalize_col(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _parse_number(val: Any) -> float:
    if val is None or (isinstance(val, float) and (val != val)):  # NaN
        return 0.0
    s = str(val).strip().replace("*", "").replace(",", "")
    if not s or s in ("-", "–"):
        return 0.0
    try:
        return float(re.sub(r"[^0-9.]", "", s) or 0)
    except ValueError:
        return 0.0


def parse_career_averages_from_html(html: str) -> Optional[Dict[str, float]]:
    """
    Find the 'Career averages' table in the Statsguru batting page and extract the first data row.
    Column order: (empty/Span), Mat, Inns, NO, Runs, HS, Ave, BF, SR, 100, 50, 0, 4s, 6s, (Profile link).
    Returns dict with keys: runs, bf, fours, sixes, inns, no, dismissals.
    """
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table", class_="engineTable"):
        cap = table.find("caption")
        if cap and "Career averages" not in cap.get_text():
            continue
        thead = table.find("thead")
        tbody = table.find("tbody")
        if not tbody:
            continue
        rows = tbody.find_all("tr", class_="data1")
        if not rows:
            rows = tbody.find_all("tr")
        for tr in rows:
            cells = tr.find_all("td")
            if len(cells) < 15:
                continue
            # ESPN Career averages row: 0=label, 1=Span, 2=Mat, 3=Inns, 4=NO, 5=Runs, 6=HS, 7=Ave, 8=BF, 9=SR, 10=100, 11=50, 12=0, 13=4s, 14=6s
            try:
                inns = _parse_number(cells[3].get_text())
                no = _parse_number(cells[4].get_text())
                runs = _parse_number(cells[5].get_text())
                bf = _parse_number(cells[8].get_text())
                fours = _parse_number(cells[13].get_text())
                sixes = _parse_number(cells[14].get_text())
            except (IndexError, AttributeError):
                continue
            if bf <= 0:
                continue
            return {
                "runs": runs,
                "bf": bf,
                "fours": fours,
                "sixes": sixes,
                "inns": inns,
                "no": no,
                "dismissals": max(0, inns - no),
            }
    return None


def fetch_batting_stats_for_player(
    session: requests.Session,
    player_id: int,
    use_span: bool = False,
    spanmin: str = "01+Jan+2025",
    spanmax: str = "31+Dec+2026",
    sleep_s: float = 0.5,
) -> Optional[Dict[str, float]]:
    """
    Fetch T20I (class=3) batting results page and parse career-style averages.
    If use_span=True, pass spanmin/spanmax for date filter (e.g. last 9 months).
    """
    extra = {}
    if use_span:
        extra = {"spanval1": "span", "spanmin1": spanmin, "spanmax1": spanmax}
    spec = QuerySpec(type="batting", cls=3, view=None, extra_params=extra if extra else None)
    url = make_url(player_id, spec)
    html = fetch_html(session, url, sleep_s=sleep_s)
    return parse_career_averages_from_html(html)


def fetch_all_lineups(
    lineups: Dict[str, List[Tuple[str, int]]],
    use_span: bool = False,
    spanmin: str = "01+Jan+2025",
    spanmax: str = "31+Dec+2026",
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Fetch batting stats for every player in each team.
    Returns { "India": { "Sanju Samson": {...}, ... }, "New Zealand": { ... } }
    """
    session = requests.Session()
    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for team, players in lineups.items():
        out[team] = {}
        for name, pid in players:
            try:
                stats = fetch_batting_stats_for_player(
                    session, pid, use_span=use_span, spanmin=spanmin, spanmax=spanmax
                )
                if stats:
                    out[team][name] = stats
                else:
                    out[team][name] = {}  # no data
            except Exception as e:
                out[team][name] = {"_error": str(e)}
    return out
