"""
Markov chain simulation for T20 cricket.

State: (striker_ix, non_striker_ix, runs, wickets, balls).
- striker_ix, non_striker_ix: indices into the batting lineup (0..10).
- Cricket rules: 0, 4, 6 keep same striker; 1, 2, 3 rotate strike; wicket → new batter at striker.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Set, Tuple

from markov_probabilities import OUTCOMES, stats_to_probabilities

MAX_BALLS = 120
MAX_WICKETS = 10


def sample_outcome(probs: Dict[str, float], rng: random.Random) -> str:
    """Sample one ball outcome from outcome probabilities."""
    r = rng.random()
    cum = 0.0
    for k in OUTCOMES:
        cum += probs.get(k, 0)
        if r <= cum:
            return k
    return "0"


def runs_from_outcome(outcome: str) -> int:
    if outcome == "out":
        return 0
    return int(outcome)


def next_batter_index(at_crease: Tuple[int, int], dismissed: Optional[Set[int]] = None) -> int:
    """Lowest lineup index not at the crease and not yet dismissed (next in batting order)."""
    unavailable = set(at_crease) | (dismissed or set())
    for i in range(11):
        if i not in unavailable:
            return i
    return 10  # fallback


def simulate_one_ball(
    striker_ix: int,
    non_striker_ix: int,
    batter_probs: List[Dict[str, float]],
    rng: random.Random,
    dismissed: Optional[Set[int]] = None,
) -> Tuple[int, int, int, int, str]:
    """
    Simulate one ball. Returns (new_striker_ix, new_non_striker_ix, runs, wicket, outcome).
    On wicket: new batter (next in order who hasn't batted yet) comes in at striker.
    dismissed: set of batter indices already out this innings (caller must add striker after).
    """
    probs = batter_probs[striker_ix]
    outcome = sample_outcome(probs, rng)
    runs = runs_from_outcome(outcome)

    if outcome == "out":
        # Next batter = next in order not at crease and not already dismissed
        next_batter = next_batter_index(
            (striker_ix, non_striker_ix), (dismissed or set()) | {striker_ix}
        )
        return (next_batter, non_striker_ix, 0, 1, outcome)

    if outcome in ("1", "2", "3"):
        return (non_striker_ix, striker_ix, runs, 0, outcome)
    return (striker_ix, non_striker_ix, runs, 0, outcome)


def simulate_innings(
    batter_probs: List[Dict[str, float]],
    rng: random.Random,
    max_balls: int = MAX_BALLS,
    max_wickets: int = MAX_WICKETS,
) -> int:
    """
    Simulate a full T20 innings. Returns total runs scored.
    batter_probs[i] = outcome probabilities for player at position i in the batting order.
    """
    striker, non_striker = 0, 1
    dismissed: Set[int] = set()
    total_runs = 0
    wickets = 0
    balls = 0

    while balls < max_balls and wickets < max_wickets:
        new_striker, new_non_striker, runs, wicket, _ = simulate_one_ball(
            striker, non_striker, batter_probs, rng, dismissed
        )
        total_runs += runs
        if wicket:
            dismissed.add(striker)
        wickets += wicket
        balls += 1
        striker, non_striker = new_striker, new_non_striker
    return total_runs


def simulate_innings_with_tracking(
    batter_probs: List[Dict[str, float]],
    rng: random.Random,
    max_balls: int = MAX_BALLS,
    max_wickets: int = MAX_WICKETS,
) -> Tuple[int, List[int], List[int], List[int]]:
    """
    Simulate a full T20 innings and return (total_runs, batter_runs, batter_balls, batter_outs).
    batter_outs[i] = 1 if player i was dismissed this innings, else 0.
    """
    n_batters = len(batter_probs)
    batter_runs = [0] * n_batters
    batter_balls = [0] * n_batters
    batter_outs = [0] * n_batters
    striker, non_striker = 0, 1
    dismissed: Set[int] = set()
    total_runs = 0
    wickets = 0
    balls = 0

    while balls < max_balls and wickets < max_wickets:
        new_striker, new_non_striker, runs, wicket, _ = simulate_one_ball(
            striker, non_striker, batter_probs, rng, dismissed
        )
        total_runs += runs
        batter_runs[striker] += runs
        batter_balls[striker] += 1
        if wicket:
            batter_outs[striker] = 1
            dismissed.add(striker)
        wickets += wicket
        balls += 1
        striker, non_striker = new_striker, new_non_striker
    return (total_runs, batter_runs, batter_balls, batter_outs)


def simulate_match(
    india_probs: List[Dict[str, float]],
    nz_probs: List[Dict[str, float]],
    rng: random.Random,
) -> Tuple[int, int, bool]:
    """
    Simulate India vs NZ: India bats first, then NZ chases.
    Returns (india_total, nz_total, india_wins).
    """
    india_total = simulate_innings(india_probs, rng)
    nz_total = simulate_innings(nz_probs, rng)
    return (india_total, nz_total, india_total > nz_total)


def build_team_probs(
    team_stats: Dict[str, Dict],
    batting_order: List[Tuple[str, int]],
) -> List[Dict[str, float]]:
    """
    Build list of per-ball probability dicts in batting order.
    team_stats = { "Sanju Samson": { "runs": ..., "bf": ..., ... }, ... }
    batting_order = [ ("Sanju Samson", 425943), ... ]
    """
    from markov_probabilities import stats_to_probabilities
    probs_list = []
    for name, _ in batting_order:
        stats = team_stats.get(name, {})
        probs_list.append(stats_to_probabilities(stats))
    return probs_list
