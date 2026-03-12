"""
Run the cricket Markov chain: fetch T20I batting stats for India vs NZ lineups,
derive per-ball probabilities, simulate many matches, and report expected runs and P(India wins).

Usage:
  python run_markov_simulation.py [--career] [--span 9] [--sims 10000] [--seed 42]
  --career: use career stats (default). Otherwise use last N months with --span.
  --span N: use stats from last N months (only if not --career).
  --sims: number of match simulations (default 10000).
  --seed: random seed for reproducibility.
"""

from __future__ import annotations

import argparse
import random

from lineups import INDIA_LINEUP, NEW_ZEALAND_LINEUP

from generate_plots import load_or_fetch_stats
from markov_simulate import build_team_probs, simulate_match, simulate_innings_with_tracking


def main() -> None:
    ap = argparse.ArgumentParser(description="Markov chain India vs NZ T20 simulation")
    ap.add_argument("--career", action="store_true", help="Use career T20I stats (default)")
    ap.add_argument("--span", type=int, default=9, help="Last N months if not --career")
    ap.add_argument("--sims", type=int, default=10_000, help="Number of match simulations")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    args = ap.parse_args()

    use_career = args.career or not args.span
    print("Loading lineups (India vs New Zealand, batting order from provided lineup)...")
    print("  India:", [n for n, _ in INDIA_LINEUP])
    print("  New Zealand:", [n for n, _ in NEW_ZEALAND_LINEUP])

    print("\nFetching T20I batting stats from ESPNcricinfo...")
    stats = load_or_fetch_stats(
        use_career=use_career,
        last_n_months=args.span,
        teams_needed=["India", "New Zealand"],
    )
    for team, players in stats.items():
        ok = sum(1 for p in players.values() if p and "_error" not in p)
        print(f"  {team}: {ok}/{len(players)} players with stats")

    india_probs = build_team_probs(stats.get("India", {}), INDIA_LINEUP)
    nz_probs = build_team_probs(stats.get("New Zealand", {}), NEW_ZEALAND_LINEUP)

    rng = random.Random(args.seed)
    india_totals = []
    nz_totals = []
    india_wins = 0
    n_sims = args.sims
    for _ in range(n_sims):
        ind_runs, nz_runs, ind_wins = simulate_match(india_probs, nz_probs, rng)
        india_totals.append(ind_runs)
        nz_totals.append(nz_runs)
        if ind_wins:
            india_wins += 1

    ind_mean = sum(india_totals) / n_sims
    nz_mean = sum(nz_totals) / n_sims
    p_india_wins = india_wins / n_sims

    print("\n--- Results (India bats first, then New Zealand) ---")
    print(f"  Simulated matches: {n_sims}")
    print(f"  India   expected runs (mean): {ind_mean:.1f}")
    print(f"  NZ      expected runs (mean): {nz_mean:.1f}")
    print(f"  P(India wins): {p_india_wins:.2%}")

    # Average runs per dismissal: use a fresh RNG and run many innings so middle/lower order get dismissals too
    n_innings_tracking = max(n_sims, 20_000)  # run at least 20k innings so we see 4+ wickets often
    print("\n--- Average runs per dismissal (over all simulated innings) ---")
    print(f"  (Running {n_innings_tracking} innings per team so middle/lower order get enough dismissals.)")
    rng_tracking = random.Random(args.seed + 1)
    for team_name, lineup, probs in [
        ("India", INDIA_LINEUP, india_probs),
        ("New Zealand", NEW_ZEALAND_LINEUP, nz_probs),
    ]:
        n_batters = len(probs)
        sum_runs = [0] * n_batters
        sum_outs = [0] * n_batters
        for _ in range(n_innings_tracking):
            _, br, bb, bo = simulate_innings_with_tracking(probs, rng_tracking)
            for i in range(n_batters):
                sum_runs[i] += br[i]
                sum_outs[i] += bo[i]
        total_dismissals = sum(sum_outs)
        wkts_per_inn = total_dismissals / n_innings_tracking
        print(f"\n  {team_name} (n={n_innings_tracking} innings, total dismissals={total_dismissals}, ~{wkts_per_inn:.1f} wkts/innings):")
        for i, (name, _) in enumerate(lineup):
            if i >= n_batters:
                break
            runs, outs = sum_runs[i], sum_outs[i]
            avg = runs / outs if outs > 0 else None
            val = f"{avg:.1f}" if avg is not None else "— (no dismissal)"
            print(f"    {name:25}  {val}")
    print("\nDone.")


if __name__ == "__main__":
    main()
