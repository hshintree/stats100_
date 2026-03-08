"""
Convert career batting stats into per-ball outcome probabilities for a Markov chain.

Cricket rules (T20): each ball can result in 0, 1, 2, 3, 4, 5, 6 runs or a wicket.
We model: P(4), P(6), P(out), P(1), P(2), P(0) with remaining mass for P(3) if needed.
These drive the transition: same batter for 0,4,6; strike rotates for 1,2,3; new batter for out.
"""

from __future__ import annotations

from typing import Dict

# Outcome keys for one ball
OUTCOMES = ("0", "1", "2", "4", "6", "out")


def stats_to_probabilities(stats: Dict[str, float]) -> Dict[str, float]:
    """
    From aggregate stats (runs, bf, fours, sixes, dismissals) compute per-ball probabilities.
    - P(4) = fours / bf,  P(6) = sixes / bf,  P(out) = dismissals / bf.
    - Remaining runs from non-boundary balls: other_runs = runs - 4*fours - 6*sixes.
      Other runs per ball = other_runs / bf. We split this into P(1) and P(2) using a
      heuristic (singles ~2x as likely as doubles in run contribution), and put the rest as P(0).
    """
    if not stats or "_error" in stats:
        return _default_probabilities()
    bf = stats.get("bf") or 0
    if bf <= 0:
        return _default_probabilities()
    runs = stats.get("runs") or 0
    fours = stats.get("fours") or 0
    sixes = stats.get("sixes") or 0
    dismissals = stats.get("dismissals") or 0

    p4 = fours / bf
    p6 = sixes / bf
    p_out = dismissals / bf
    remaining = 1.0 - p4 - p6 - p_out
    if remaining <= 0:
        remaining = 0.0

    other_runs = runs - (4 * fours + 6 * sixes)
    other_runs = max(0, other_runs)
    other_runs_per_ball = other_runs / bf
    # Heuristic: singles contribute ~2/3 of "other" runs, doubles ~1/3 (so P(1)*1 + P(2)*2 = other_runs_per_ball)
    # Set p1 = 0.6 * other_runs_per_ball, p2 = 0.2 * other_runs_per_ball => 0.6 + 0.4 = 1.0 run equiv
    p1 = min(remaining, 0.6 * other_runs_per_ball)
    p2 = min(remaining - p1, 0.2 * other_runs_per_ball)
    p0 = remaining - p1 - p2
    if p0 < 0:
        p0 = 0
        p1 = min(p1, remaining)
        p2 = remaining - p1

    probs = {"0": p0, "1": p1, "2": p2, "4": p4, "6": p6, "out": p_out}
    total = sum(probs.values())
    if total > 1.0:
        scale = 1.0 / total
        probs = {k: v * scale for k, v in probs.items()}
    elif total < 1.0:
        probs["0"] += 1.0 - total
    return probs


def _default_probabilities() -> Dict[str, float]:
    """Fallback for missing stats (e.g. tail-ender): low run rate, moderate out rate."""
    return {
        "0": 0.75,
        "1": 0.08,
        "2": 0.02,
        "4": 0.02,
        "6": 0.01,
        "out": 0.12,
    }
