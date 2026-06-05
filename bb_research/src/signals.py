"""Signal generation for the two pure Bollinger Band models.

A ``Signal`` is just "at bar index ``t``, go in direction ``d``". The actual
entry happens at ``open[t+1]`` inside the backtester - signals never carry an
entry price, which keeps the no-look-ahead rule centralised in one place.

Models:
  BB_MEAN_REVERSION
      close[t] < lower_band[t]  -> BUY   (price stretched below, expect revert up)
      close[t] > upper_band[t]  -> SELL  (price stretched above, expect revert down)

  BB_BREAKOUT
      close[t] > upper_band[t]  -> BUY   (price breaking up, expect continuation)
      close[t] < lower_band[t]  -> SELL  (price breaking down, expect continuation)

Note the two models are exact mirror images in direction for the same band
condition - that is intentional and is precisely what we want to compare.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

MODEL_MEAN_REVERSION = "BB_MEAN_REVERSION"
MODEL_BREAKOUT = "BB_BREAKOUT"

DIR_BUY = "BUY"
DIR_SELL = "SELL"


@dataclass(frozen=True)
class Signal:
    """A trade trigger at bar ``index`` (positional) in direction ``direction``."""

    index: int          # positional bar index t of the signal candle
    direction: str      # "BUY" or "SELL"


def generate_signals(
    df: pd.DataFrame,
    bands: pd.DataFrame,
    model: str,
) -> List[Signal]:
    """Generate signals for the given model.

    Only bars where the bands are defined (not NaN) can produce a signal. The
    very last bar can still produce a signal here; the backtester is responsible
    for discarding it if there is no ``t+1`` bar to enter on.
    """
    close = df["close"].to_numpy()
    upper = bands["upper_band"].to_numpy()
    lower = bands["lower_band"].to_numpy()

    valid = ~np.isnan(upper) & ~np.isnan(lower)

    above_upper = valid & (close > upper)
    below_lower = valid & (close < lower)

    if model == MODEL_MEAN_REVERSION:
        buy_mask = below_lower
        sell_mask = above_upper
    elif model == MODEL_BREAKOUT:
        buy_mask = above_upper
        sell_mask = below_lower
    else:
        raise ValueError(f"Unknown model: {model}")

    signals: List[Signal] = []
    buy_idx = np.flatnonzero(buy_mask)
    sell_idx = np.flatnonzero(sell_mask)
    for i in buy_idx:
        signals.append(Signal(index=int(i), direction=DIR_BUY))
    for i in sell_idx:
        signals.append(Signal(index=int(i), direction=DIR_SELL))

    # Sort by bar index so trades are processed in chronological order. A given
    # bar cannot be both above upper and below lower, so there are no ties.
    signals.sort(key=lambda s: s.index)
    return signals
