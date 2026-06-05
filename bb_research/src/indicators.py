"""Technical indicators used by the research engine.

Only Bollinger Bands are needed. The implementation is intentionally simple and
fully vectorised so it is easy to audit for look-ahead bias: every band value at
index ``t`` is computed using a trailing window that ends at ``t`` (inclusive),
i.e. it only ever uses data from ``t`` and earlier candles.
"""

from __future__ import annotations

import pandas as pd


def bollinger_bands(
    source: pd.Series,
    period: int = 20,
    deviation: float = 2.0,
) -> pd.DataFrame:
    """Compute Bollinger Bands on ``source`` (typically the close price).

    Returns a DataFrame indexed exactly like ``source`` with columns:
        middle_band, upper_band, lower_band, band_width, band_width_pct

    Notes on correctness:
      * The rolling mean / std use ``min_periods=period`` so the first
        ``period - 1`` rows are NaN. We never back-fill them; callers must skip
        bars where bands are NaN. This prevents using an incomplete window.
      * Standard deviation uses the *sample* std (``ddof=1``), which is the
        convention used by most charting platforms (MetaTrader, TradingView).
    """
    if period <= 1:
        raise ValueError(f"bb_period must be > 1, got {period}")

    middle = source.rolling(window=period, min_periods=period).mean()
    std = source.rolling(window=period, min_periods=period).std(ddof=1)

    upper = middle + deviation * std
    lower = middle - deviation * std
    band_width = upper - lower
    # band_width_pct expresses the band width relative to the middle band so it
    # is comparable across pairs with very different price levels (e.g. EURUSD
    # ~1.10 vs USDJPY ~150). Expressed as a percentage.
    band_width_pct = (band_width / middle) * 100.0

    return pd.DataFrame(
        {
            "middle_band": middle,
            "upper_band": upper,
            "lower_band": lower,
            "band_width": band_width,
            "band_width_pct": band_width_pct,
        }
    )
