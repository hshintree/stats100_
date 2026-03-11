"""
Generate plots for the Markov chain India vs NZ simulation:
1. Distribution of simulated team totals (India & NZ) with average expected runs.
2. Per-player comparison: actual career runs/ball vs model-predicted runs/ball.

Usage:
  python generate_plots.py [--career] [--sims 5000] [--seed 42] [--outdir plots]
  Uses cached batting stats if available (same as run_markov_simulation.py).
"""

from __future__ import annotations

import argparse
import json
import os
import random
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")  # no display required
import matplotlib.pyplot as plt
import numpy as np

from fetch_batting_stats import fetch_all_lineups
from lineups import INDIA_LINEUP, NEW_ZEALAND_LINEUP, get_team_lineups
from markov_probabilities import expected_runs_per_ball, stats_to_probabilities
from markov_simulate import build_team_probs, simulate_match

CACHE_DIR = "markov_cache"
CACHE_FILE = os.path.join(CACHE_DIR, "batting_stats.json")


def _span_dates(last_n_months: int) -> tuple[str, str]:
    end = datetime.now()
    start = end - timedelta(days=last_n_months * 30)
    spanmin = start.strftime("%d+%b+%Y").replace(" 0", " ").replace("+0", "+")
    spanmax = end.strftime("%d+%b+%Y").replace(" 0", " ").replace("+0", "+")
    return spanmin, spanmax


def load_or_fetch_stats(use_career: bool, last_n_months: int) -> dict:
    lineups = get_team_lineups()
    if use_career and os.path.isfile(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached:
                    return cached
        except Exception:
            pass
    if use_career:
        stats = fetch_all_lineups(lineups, use_span=False)
    else:
        spanmin, spanmax = _span_dates(last_n_months)
        stats = fetch_all_lineups(lineups, use_span=True, spanmin=spanmin, spanmax=spanmax)
    os.makedirs(CACHE_DIR, exist_ok=True)
    out = {}
    for team, players in stats.items():
        out[team] = {}
        for name, data in players.items():
            if "_error" in data:
                out[team][name] = {"_error": data["_error"]}
            else:
                out[team][name] = {k: float(v) for k, v in data.items()}
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    return out


def plot_team_totals_distribution(
    india_totals: list,
    nz_totals: list,
    outpath: str,
) -> None:
    """Histogram of simulated innings totals with mean lines and annotations."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    ind_mean = np.mean(india_totals)
    nz_mean = np.mean(nz_totals)
    ind_std = np.std(india_totals)
    nz_std = np.std(nz_totals)

    axes[0].hist(india_totals, bins=50, color="#0F4C81", alpha=0.75, edgecolor="white", linewidth=0.3)
    axes[0].axvline(ind_mean, color="#E03C31", linewidth=2, label=f"Mean = {ind_mean:.1f}")
    axes[0].set_xlabel("Total runs")
    axes[0].set_ylabel("Number of simulations")
    axes[0].set_title("India — simulated innings total")
    axes[0].legend()
    axes[0].set_xlim(0, None)

    axes[1].hist(nz_totals, bins=50, color="#002B5C", alpha=0.75, edgecolor="white", linewidth=0.3)
    axes[1].axvline(nz_mean, color="#CC0000", linewidth=2, label=f"Mean = {nz_mean:.1f}")
    axes[1].set_xlabel("Total runs")
    axes[1].set_title("New Zealand — simulated innings total")
    axes[1].legend()
    axes[1].set_xlim(0, None)

    fig.suptitle(
        f"Simulated T20 innings totals (Markov chain)\n"
        f"Average expected total: India {ind_mean:.1f} (±{ind_std:.1f})  |  NZ {nz_mean:.1f} (±{nz_std:.1f})",
        fontsize=11,
    )
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def plot_actual_vs_predicted_runs_per_ball(
    stats: dict,
    india_lineup: list,
    nz_lineup: list,
    outpath: str,
) -> None:
    """
    For each player: actual runs/ball (from career stats) vs model predicted runs/ball.
    """
    def series_for_team(team_name: str, lineup: list) -> tuple[list, list, list, list]:
        names, actual, predicted = [], [], []
        for name, _ in lineup:
            s = stats.get(team_name, {}).get(name, {})
            if "_error" in s or not s or s.get("bf", 0) <= 0:
                continue
            runs, bf = s.get("runs", 0), s.get("bf", 1)
            actual_rpb = runs / bf
            probs = stats_to_probabilities(s)
            pred_rpb = expected_runs_per_ball(probs)
            names.append(name.split()[-1] if " " in name else name)  # surname for space
            actual.append(actual_rpb)
            predicted.append(pred_rpb)
        return names, actual, predicted

    ind_names, ind_actual, ind_pred = series_for_team("India", india_lineup)
    nz_names, nz_actual, nz_pred = series_for_team("New Zealand", nz_lineup)

    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=False)
    x = np.arange(max(len(ind_names), len(nz_names)))
    width = 0.35

    # India
    ax = axes[0]
    n = len(ind_names)
    ax.bar(x[:n] - width / 2, ind_actual, width, label="Actual (career runs/ball)", color="#0F4C81", alpha=0.85)
    ax.bar(x[:n] + width / 2, ind_pred, width, label="Model predicted runs/ball", color="#E03C31", alpha=0.85)
    ax.set_xticks(x[:n])
    ax.set_xticklabels(ind_names, rotation=45, ha="right")
    ax.set_ylabel("Runs per ball")
    ax.set_title("India — actual vs model runs per ball (T20I career)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_ylim(0, None)
    ax.axhline(np.mean(ind_actual), color="#0F4C81", linestyle="--", alpha=0.5, linewidth=0.8)
    ax.axhline(np.mean(ind_pred), color="#E03C31", linestyle="--", alpha=0.5, linewidth=0.8)

    # New Zealand
    ax = axes[1]
    n = len(nz_names)
    ax.bar(x[:n] - width / 2, nz_actual, width, label="Actual (career runs/ball)", color="#002B5C", alpha=0.85)
    ax.bar(x[:n] + width / 2, nz_pred, width, label="Model predicted runs/ball", color="#CC0000", alpha=0.85)
    ax.set_xticks(x[:n])
    ax.set_xticklabels(nz_names, rotation=45, ha="right")
    ax.set_ylabel("Runs per ball")
    ax.set_title("New Zealand — actual vs model runs per ball (T20I career)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_ylim(0, None)
    ax.axhline(np.mean(nz_actual), color="#002B5C", linestyle="--", alpha=0.5, linewidth=0.8)
    ax.axhline(np.mean(nz_pred), color="#CC0000", linestyle="--", alpha=0.5, linewidth=0.8)

    fig.suptitle("Per-player: career actual vs Markov model predicted (runs per ball)", fontsize=12)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def plot_win_probability_and_totals(
    india_totals: list,
    nz_totals: list,
    india_wins: int,
    n_sims: int,
    outpath: str,
) -> None:
    """Single figure: histograms of both teams' totals + P(India wins) in title."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ind_mean, nz_mean = np.mean(india_totals), np.mean(nz_totals)
    p_india = india_wins / n_sims

    ax.hist(india_totals, bins=45, color="#0F4C81", alpha=0.6, label=f"India (mean = {ind_mean:.1f})", density=True)
    ax.hist(nz_totals, bins=45, color="#002B5C", alpha=0.6, label=f"New Zealand (mean = {nz_mean:.1f})", density=True)
    ax.axvline(ind_mean, color="#0F4C81", linestyle="--", linewidth=1.5)
    ax.axvline(nz_mean, color="#002B5C", linestyle="--", linewidth=1.5)
    ax.set_xlabel("Innings total (runs)")
    ax.set_ylabel("Density")
    ax.set_title(f"Simulated T20 totals (n={n_sims})  —  P(India wins) = {p_india:.1%}")
    ax.legend()
    ax.set_xlim(0, None)
    plt.tight_layout()
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {outpath}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate Markov simulation plots")
    ap.add_argument("--career", action="store_true", help="Use career T20I stats")
    ap.add_argument("--span", type=int, default=9, help="Last N months if not --career")
    ap.add_argument("--sims", type=int, default=5000, help="Number of match simulations")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--outdir", type=str, default="plots", help="Output directory for figures")
    args = ap.parse_args()

    use_career = args.career or not args.span
    os.makedirs(args.outdir, exist_ok=True)

    print("Loading/fetching batting stats...")
    stats = load_or_fetch_stats(use_career=use_career, last_n_months=args.span)
    india_probs = build_team_probs(stats.get("India", {}), INDIA_LINEUP)
    nz_probs = build_team_probs(stats.get("New Zealand", {}), NEW_ZEALAND_LINEUP)

    print(f"Running {args.sims} match simulations...")
    rng = random.Random(args.seed)
    india_totals, nz_totals = [], []
    india_wins = 0
    for _ in range(args.sims):
        ind_r, nz_r, ind_win = simulate_match(india_probs, nz_probs, rng)
        india_totals.append(ind_r)
        nz_totals.append(nz_r)
        if ind_win:
            india_wins += 1

    ind_mean = np.mean(india_totals)
    nz_mean = np.mean(nz_totals)
    print(f"India   average expected total: {ind_mean:.1f}")
    print(f"NZ      average expected total: {nz_mean:.1f}")
    print(f"P(India wins): {india_wins / args.sims:.1%}")

    plot_team_totals_distribution(
        india_totals,
        nz_totals,
        os.path.join(args.outdir, "simulated_team_totals.png"),
    )
    plot_actual_vs_predicted_runs_per_ball(
        stats,
        INDIA_LINEUP,
        NEW_ZEALAND_LINEUP,
        os.path.join(args.outdir, "actual_vs_predicted_runs_per_ball.png"),
    )
    plot_win_probability_and_totals(
        india_totals,
        nz_totals,
        india_wins,
        args.sims,
        os.path.join(args.outdir, "win_probability_and_totals.png"),
    )
    print("Done.")


if __name__ == "__main__":
    main()
