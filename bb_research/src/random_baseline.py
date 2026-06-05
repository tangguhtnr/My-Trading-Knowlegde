"""Random baselines.

The whole point of this research engine is to compare Bollinger Band signals
against random entries under *identical* execution rules. If BB cannot beat
random, BB has no demonstrated edge. Two baselines isolate two different claims:

  RANDOM_DIRECTION_ON_BB_TIMESTAMPS
      Keep the exact bars BB fired on, but flip the direction to a coin toss.
      Tests the claim: "BB picks the right DIRECTION."

  RANDOM_TIME_AND_DIRECTION
      Pick the same NUMBER of trades, but at random eligible bars and random
      direction. Tests the claim: "BB picks the right TIME (and direction)."

All randomness is seeded so a run is byte-for-byte reproducible. The seed is
derived deterministically from the base seed plus the (symbol, timeframe, model,
rr, variant) tuple, so results do not depend on the order files are processed.
"""

from __future__ import annotations

import hashlib
from typing import List, Sequence

import numpy as np

from .signals import DIR_BUY, DIR_SELL, Signal

BASELINE_ACTUAL = "ACTUAL"
BASELINE_RANDOM_DIRECTION = "RANDOM_DIRECTION_ON_BB_TIMESTAMPS"
BASELINE_RANDOM_TIME_DIRECTION = "RANDOM_TIME_AND_DIRECTION"


def derive_seed(base_seed: int, *parts: object) -> int:
    """Deterministically derive a 32-bit seed from a base seed + context parts.

    Uses SHA-256 (stable across processes, unlike Python's builtin ``hash``).
    """
    key = "|".join([str(base_seed)] + [str(p) for p in parts])
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest, 16) % (2**32)


def _random_directions(rng: np.random.Generator, n: int) -> List[str]:
    picks = rng.integers(0, 2, size=n)
    return [DIR_BUY if p == 0 else DIR_SELL for p in picks]


def randomize_direction(signals: Sequence[Signal], seed: int) -> List[Signal]:
    """Keep BB signal bars, randomise BUY/SELL with a seeded RNG."""
    rng = np.random.default_rng(seed)
    dirs = _random_directions(rng, len(signals))
    return [Signal(index=s.index, direction=d) for s, d in zip(signals, dirs)]


def random_time_and_direction(
    n_trades: int,
    eligible_indices: Sequence[int],
    seed: int,
) -> List[Signal]:
    """Pick ``n_trades`` random eligible bars with random direction.

    ``eligible_indices`` must already be filtered to bars that have defined
    bands and a valid ``t+1`` entry bar. Sampling is without replacement when
    there are enough eligible bars, otherwise with replacement (and we warn via
    the returned count being honoured rather than silently truncated).
    """
    rng = np.random.default_rng(seed)
    eligible = np.asarray(eligible_indices, dtype=int)
    if n_trades <= 0 or eligible.size == 0:
        return []

    replace = n_trades > eligible.size
    chosen = rng.choice(eligible, size=n_trades, replace=replace)
    chosen.sort()  # chronological order for sane one-position-at-a-time handling
    dirs = _random_directions(rng, n_trades)
    return [Signal(index=int(i), direction=d) for i, d in zip(chosen, dirs)]
