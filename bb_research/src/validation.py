"""Strict data validation.

Philosophy: fail loudly. If the input data is malformed we raise a
``DataValidationError`` with a clear, actionable message instead of silently
dropping rows or guessing. Garbage in must NOT produce a silently-wrong
backtest.
"""

from __future__ import annotations

import pandas as pd


class DataValidationError(Exception):
    """Raised when input OHLC data fails a validation rule."""


def validate_ohlc(
    df: pd.DataFrame,
    symbol: str,
    bb_period: int,
    has_spread: bool,
) -> None:
    """Validate a cleaned OHLC DataFrame.

    Expects columns: datetime, open, high, low, close (and optionally spread).
    Raises ``DataValidationError`` on the first failing rule. Does not mutate.
    """
    required = ["datetime", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataValidationError(
            f"[{symbol}] Missing required columns after mapping: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    n = len(df)
    if n == 0:
        raise DataValidationError(f"[{symbol}] Input data has zero rows.")

    # Enough rows for BB: need at least bb_period rows for the first band value,
    # plus one extra bar so an entry at t+1 is possible.
    if n < bb_period + 1:
        raise DataValidationError(
            f"[{symbol}] Not enough rows for Bollinger Bands: have {n}, "
            f"need at least bb_period + 1 = {bb_period + 1}."
        )

    # Missing OHLC values.
    for col in ["open", "high", "low", "close"]:
        n_na = int(df[col].isna().sum())
        if n_na > 0:
            first_bad = df.index[df[col].isna()][0]
            raise DataValidationError(
                f"[{symbol}] Column '{col}' has {n_na} missing value(s). "
                f"First at row index {first_bad}."
            )

    # Datetime parsed and present.
    if df["datetime"].isna().any():
        raise DataValidationError(
            f"[{symbol}] Some datetime values failed to parse (NaT present)."
        )

    # Duplicate datetimes.
    dup_mask = df["datetime"].duplicated(keep=False)
    if dup_mask.any():
        n_dup = int(dup_mask.sum())
        example = df.loc[dup_mask, "datetime"].iloc[0]
        raise DataValidationError(
            f"[{symbol}] Found {n_dup} duplicate datetime row(s). "
            f"Example duplicate: {example}."
        )

    # Sorted ascending.
    if not df["datetime"].is_monotonic_increasing:
        raise DataValidationError(
            f"[{symbol}] datetime column is not sorted ascending after load. "
            f"This is an internal error - please report."
        )

    # OHLC sanity relationships (vectorised, then report first offender).
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    hi_vs_oc = h < o.combine(c, max)  # high must be >= max(open, close)
    if hi_vs_oc.any():
        idx = df.index[hi_vs_oc][0]
        raise DataValidationError(
            f"[{symbol}] high < max(open, close) at {df.loc[idx, 'datetime']} "
            f"(row {idx}): high={h[idx]}, open={o[idx]}, close={c[idx]}."
        )

    lo_vs_oc = l > o.combine(c, min)  # low must be <= min(open, close)
    if lo_vs_oc.any():
        idx = df.index[lo_vs_oc][0]
        raise DataValidationError(
            f"[{symbol}] low > min(open, close) at {df.loc[idx, 'datetime']} "
            f"(row {idx}): low={l[idx]}, open={o[idx]}, close={c[idx]}."
        )

    hl = h < l  # high must be >= low
    if hl.any():
        idx = df.index[hl][0]
        raise DataValidationError(
            f"[{symbol}] high < low at {df.loc[idx, 'datetime']} (row {idx}): "
            f"high={h[idx]}, low={l[idx]}."
        )

    # Spread (optional) must not be negative.
    if has_spread and "spread" in df.columns:
        neg = df["spread"] < 0
        if neg.any():
            idx = df.index[neg][0]
            raise DataValidationError(
                f"[{symbol}] Negative spread at {df.loc[idx, 'datetime']} "
                f"(row {idx}): spread={df.loc[idx, 'spread']}."
            )
