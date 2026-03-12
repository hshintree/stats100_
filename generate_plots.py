"""
Generate plots for Markov chain T20 simulation. Supports multiple matchups:
  India vs New Zealand, Argentina vs Suriname, Sri Lanka vs Afghanistan.

Usage:
  python generate_plots.py [--matchup "India vs New Zealand"] [--all]
  python generate_plots.py --career --sims 5000 --outdir plots
  python generate_plots.py --span 9 --all   # last 9 months for all matchups

Data: --career = career T20I averages; --span N = last N months.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fetch_batting_stats import fetch_all_lineups
from lineups import MATCHUPS, get_team_lineups, get_matchup
from markov_probabilities import expected_runs_per_ball, stats_to_probabilities
from markov_simulate import build_team_probs, build_transition_matrix, simulate_match

CACHE_DIR = "markov_cache"
CACHE_FILE = os.path.join(CACHE_DIR, "batting_stats.json")
OUTCOME_LABELS = ("0", "1", "2", "4", "6", "out")  # per-ball outcomes


def _span_dates(last_n_months: int) -> tuple[str, str]:
    end = datetime.now()
    start = end - timedelta(days=last_n_months * 30)
    spanmin = start.strftime("%d+%b+%Y").replace(" 0", " ").replace("+0", "+")
    spanmax = end.strftime("%d+%b+%Y").replace(" 0", " ").replace("+0", "+")
    return spanmin, spanmax


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower().strip()).strip("_") or "matchup"


def load_or_fetch_stats(
    use_career: bool,
    last_n_months: int,
    teams_needed: list[str],
) -> dict:
    """Load cache, fetch any missing teams, return full stats dict keyed by team name."""
    all_teams = get_team_lineups()
    cached = {}
    if os.path.isfile(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
        except Exception:
            pass
    to_fetch = [t for t in teams_needed if t not in cached or not cached[t]]
    if to_fetch:
        lineups_to_fetch = {t: all_teams[t] for t in to_fetch}
        if use_career:
            new_stats = fetch_all_lineups(lineups_to_fetch, use_span=False)
        else:
            spanmin, spanmax = _span_dates(last_n_months)
            new_stats = fetch_all_lineups(
                lineups_to_fetch, use_span=True, spanmin=spanmin, spanmax=spanmax
            )
        for team, players in new_stats.items():
            cached[team] = {}
            for name, data in players.items():
                if "_error" in data:
                    cached[team][name] = {"_error": data["_error"]}
                else:
                    cached[team][name] = {k: float(v) for k, v in data.items()}
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cached, f, indent=2)
    return cached


def plot_team_totals_distribution(
    team1_totals: list,
    team2_totals: list,
    team1_name: str,
    team2_name: str,
    outpath: str,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    m1, m2 = np.mean(team1_totals), np.mean(team2_totals)
    s1, s2 = np.std(team1_totals), np.std(team2_totals)
    axes[0].hist(team1_totals, bins=50, color="#0F4C81", alpha=0.75, edgecolor="white", linewidth=0.3)
    axes[0].axvline(m1, color="#E03C31", linewidth=2, label=f"Mean = {m1:.1f}")
    axes[0].set_xlabel("Total runs")
    axes[0].set_ylabel("Number of simulations")
    axes[0].set_title(f"{team1_name} — simulated innings total")
    axes[0].legend()
    axes[0].set_xlim(0, None)
    axes[1].hist(team2_totals, bins=50, color="#002B5C", alpha=0.75, edgecolor="white", linewidth=0.3)
    axes[1].axvline(m2, color="#CC0000", linewidth=2, label=f"Mean = {m2:.1f}")
    axes[1].set_xlabel("Total runs")
    axes[1].set_title(f"{team2_name} — simulated innings total")
    axes[1].legend()
    axes[1].set_xlim(0, None)
    fig.suptitle(
        f"Simulated T20 innings totals\n"
        f"Average expected total: {team1_name} {m1:.1f} (±{s1:.1f})  |  {team2_name} {m2:.1f} (±{s2:.1f})",
        fontsize=11,
    )
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def plot_actual_vs_predicted(
    stats: dict,
    team1_name: str,
    team2_name: str,
    lineup1: list,
    lineup2: list,
    outpath: str,
) -> None:
    def series(team_name: str, lineup: list):
        names, actual, predicted = [], [], []
        for name, _ in lineup:
            s = stats.get(team_name, {}).get(name, {})
            if "_error" in s or not s or s.get("bf", 0) <= 0:
                continue
            runs, bf = s.get("runs", 0), s.get("bf", 1)
            actual.append(runs / bf)
            probs = stats_to_probabilities(s)
            predicted.append(expected_runs_per_ball(probs))
            names.append(name.split()[-1] if " " in name else name)
        return names, actual, predicted

    n1, a1, p1 = series(team1_name, lineup1)
    n2, a2, p2 = series(team2_name, lineup2)
    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=False)
    width = 0.35
    for ax, names, actual, pred, title, c1, c2 in [
        (axes[0], n1, a1, p1, team1_name, "#0F4C81", "#E03C31"),
        (axes[1], n2, a2, p2, team2_name, "#002B5C", "#CC0000"),
    ]:
        x = np.arange(len(names))
        ax.bar(x - width / 2, actual, width, label="Actual runs/ball", color=c1, alpha=0.85)
        ax.bar(x + width / 2, pred, width, label="Model predicted", color=c2, alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha="right")
        ax.set_ylabel("Runs per ball")
        ax.set_title(f"{title} — actual vs model runs per ball")
        ax.legend(loc="upper right", fontsize=8)
        ax.set_ylim(0, None)
    fig.suptitle("Per-player: actual vs Markov model predicted (runs per ball)", fontsize=12)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def plot_win_probability_and_totals(
    team1_totals: list,
    team2_totals: list,
    team1_wins: int,
    team1_name: str,
    team2_name: str,
    n_sims: int,
    outpath: str,
) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    m1, m2 = np.mean(team1_totals), np.mean(team2_totals)
    p1 = team1_wins / n_sims
    ax.hist(team1_totals, bins=45, color="#0F4C81", alpha=0.6, label=f"{team1_name} (mean = {m1:.1f})", density=True)
    ax.hist(team2_totals, bins=45, color="#002B5C", alpha=0.6, label=f"{team2_name} (mean = {m2:.1f})", density=True)
    ax.axvline(m1, color="#0F4C81", linestyle="--", linewidth=1.5)
    ax.axvline(m2, color="#002B5C", linestyle="--", linewidth=1.5)
    ax.set_xlabel("Innings total (runs)")
    ax.set_ylabel("Density")
    ax.set_title(f"Simulated T20 totals (n={n_sims})  —  P({team1_name} wins) = {p1:.1%}")
    ax.legend()
    ax.set_xlim(0, None)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def plot_probability_table(
    stats: dict,
    team1_name: str,
    team2_name: str,
    lineup1: list,
    lineup2: list,
    outpath: str,
) -> None:
    """Table of P(0), P(1), P(2), P(4), P(6), P(out) for each player on both teams."""
    rows, row_labels = [], []
    for team_name, lineup in [(team1_name, lineup1), (team2_name, lineup2)]:
        for name, _ in lineup:
            s = stats.get(team_name, {}).get(name, {})
            probs = stats_to_probabilities(s)
            row = [probs.get(k, 0) for k in OUTCOME_LABELS]
            rows.append(row)
            row_labels.append(f"{name[:20]} ({team_name[:3]})")
    arr = np.array(rows)
    fig, ax = plt.subplots(figsize=(10, max(6, len(rows) * 0.35)))
    im = ax.imshow(arr, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(OUTCOME_LABELS)))
    ax.set_xticklabels([f"P({x})" for x in OUTCOME_LABELS])
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=8)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, f"{arr[i, j]:.2f}", ha="center", va="center", fontsize=7, color="white" if arr[i, j] > 0.5 else "black")
    plt.colorbar(im, ax=ax, label="Probability")
    ax.set_title(f"Per-ball outcome probabilities: {team1_name} & {team2_name}")
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def plot_transition_matrix(
    batter_probs: list,
    team_name: str,
    lineup: list,
    outpath: str,
) -> None:
    """11×11 Markov transition matrix: P(next striker = j | current striker = i)."""
    M = build_transition_matrix(batter_probs)
    labels = [name.split()[-1] if " " in name else name[:10] for name, _ in lineup[:11]]
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(M, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_xticks(range(11))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticks(range(11))
    ax.set_yticklabels(labels)
    ax.set_xlabel("Next striker")
    ax.set_ylabel("Current striker")
    for i in range(11):
        for j in range(11):
            if M[i, j] >= 0.01:
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=7)
    ax.set_title(f"Markov transition matrix: P(next striker | current striker) — {team_name}")
    plt.colorbar(im, ax=ax, label="Probability")
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def run_one_matchup(
    matchup_label: str,
    team1_name: str,
    team2_name: str,
    lineup1: list,
    lineup2: list,
    stats: dict,
    use_career: bool,
    n_sims: int,
    seed: int,
    outdir: str,
) -> None:
    slug = _slug(matchup_label)
    probs1 = build_team_probs(stats.get(team1_name, {}), lineup1)
    probs2 = build_team_probs(stats.get(team2_name, {}), lineup2)
    rng = random.Random(seed)
    t1_totals, t2_totals = [], []
    t1_wins = 0
    for _ in range(n_sims):
        r1, r2, win1 = simulate_match(probs1, probs2, rng)
        t1_totals.append(r1)
        t2_totals.append(r2)
        if win1:
            t1_wins += 1
    m1, m2 = np.mean(t1_totals), np.mean(t2_totals)
    data_src = "career" if use_career else "9month"
    print(f"  {matchup_label} ({data_src}): {team1_name} mean={m1:.1f}, {team2_name} mean={m2:.1f}, P({team1_name} wins)={t1_wins/n_sims:.1%}")

    plot_team_totals_distribution(
        t1_totals, t2_totals, team1_name, team2_name,
        os.path.join(outdir, f"{slug}_simulated_team_totals.png"),
    )
    plot_actual_vs_predicted(
        stats, team1_name, team2_name, lineup1, lineup2,
        os.path.join(outdir, f"{slug}_actual_vs_predicted.png"),
    )
    plot_win_probability_and_totals(
        t1_totals, t2_totals, t1_wins, team1_name, team2_name, n_sims,
        os.path.join(outdir, f"{slug}_win_probability_and_totals.png"),
    )
    plot_probability_table(
        stats, team1_name, team2_name, lineup1, lineup2,
        os.path.join(outdir, f"{slug}_probability_table.png"),
    )
    plot_transition_matrix(probs1, team1_name, lineup1, os.path.join(outdir, f"{slug}_transition_matrix_{_slug(team1_name)}.png"))
    plot_transition_matrix(probs2, team2_name, lineup2, os.path.join(outdir, f"{slug}_transition_matrix_{_slug(team2_name)}.png"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate Markov simulation plots")
    ap.add_argument("--matchup", type=str, default=None, help='e.g. "India vs New Zealand"')
    ap.add_argument("--all", action="store_true", help="Run all matchups")
    ap.add_argument("--career", action="store_true", help="Use career T20I stats")
    ap.add_argument("--span", type=int, default=9, help="Last N months if not --career")
    ap.add_argument("--sims", type=int, default=5000, help="Number of match simulations")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--outdir", type=str, default="plots", help="Output directory")
    args = ap.parse_args()

    use_career = args.career or not args.span
    data_src = "career" if use_career else f"last_{args.span}_months"
    print(f"Data: {data_src}")

    if args.all:
        matchups_to_run = [m[0] for m in MATCHUPS]
    elif args.matchup:
        matchups_to_run = [args.matchup]
        if get_matchup(args.matchup) is None:
            print("Unknown matchup. Choose from:", [m[0] for m in MATCHUPS])
            return
    else:
        matchups_to_run = [MATCHUPS[0][0]]  # default India vs New Zealand

    teams_needed = []
    for label in matchups_to_run:
        m = get_matchup(label)
        if m:
            t1, t2, _, _ = m
            teams_needed.extend([t1, t2])
    teams_needed = list(dict.fromkeys(teams_needed))

    print("Loading/fetching batting stats for:", teams_needed)
    stats = load_or_fetch_stats(use_career=use_career, last_n_months=args.span, teams_needed=teams_needed)
    for t in teams_needed:
        n_ok = sum(1 for p in stats.get(t, {}).values() if p and "_error" not in p)
        print(f"  {t}: {n_ok}/{len(get_team_lineups()[t])} players with stats")

    os.makedirs(args.outdir, exist_ok=True)
    print(f"Running {args.sims} sims per matchup...")
    for label in matchups_to_run:
        m = get_matchup(label)
        if not m:
            continue
        t1_name, t2_name, l1, l2 = m
        run_one_matchup(
            label, t1_name, t2_name, l1, l2,
            stats, use_career, args.sims, args.seed, args.outdir,
        )
    print("Done.")


if __name__ == "__main__":
    main()
