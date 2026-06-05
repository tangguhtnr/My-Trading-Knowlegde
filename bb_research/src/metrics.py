"""Trade-level metrics and grouped summaries.

All metrics are computed on ``net_result_R`` (the column the user ultimately
cares about). Nothing here selects a "best" anything - every requested grouping
is reported in full, winners and losers alike.
"""

from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd


def max_drawdown_R(net_series: pd.Series) -> float:
    """Max drawdown (positive number) of the cumulative net-R equity curve.

    Assumes ``net_series`` is already in chronological order.
    """
    if net_series.empty:
        return 0.0
    cum = net_series.cumsum()
    running_max = cum.cummax()
    drawdown = running_max - cum  # >= 0
    return float(drawdown.max())


def breakeven_winrate(rr: float) -> float:
    """Winrate needed to break even at a given reward:risk (ignoring costs)."""
    return 1.0 / (1.0 + rr) if rr > 0 else np.nan


def _group_metrics(g: pd.DataFrame) -> pd.Series:
    """Compute the metric block for one already-sorted group of trades."""
    net = g["net_result_R"]
    gross = g["gross_result_R"]

    wins_mask = net > 0
    losses_mask = net < 0
    n = len(g)
    n_wins = int(wins_mask.sum())
    n_losses = int(losses_mask.sum())

    profits = net[wins_mask].sum()
    losses_sum = net[losses_mask].sum()  # negative or 0

    if losses_sum < 0:
        profit_factor = float(profits / abs(losses_sum))
    elif profits > 0:
        profit_factor = np.inf  # winners but zero losers
    else:
        profit_factor = np.nan  # no decisive trades

    avg_win = float(net[wins_mask].mean()) if n_wins > 0 else np.nan
    avg_loss = float(net[losses_mask].mean()) if n_losses > 0 else np.nan
    if n_wins > 0 and n_losses > 0 and avg_loss != 0:
        payoff_ratio = float(avg_win / abs(avg_loss))
    else:
        payoff_ratio = np.nan

    return pd.Series(
        {
            "trades": n,
            "wins": n_wins,
            "losses": n_losses,
            "winrate": (n_wins / n) if n > 0 else np.nan,
            "gross_net_R": float(gross.sum()),
            "total_net_R": float(net.sum()),
            "avg_net_R": float(net.mean()) if n > 0 else np.nan,
            "median_net_R": float(net.median()) if n > 0 else np.nan,
            "expectancy_R": float(net.mean()) if n > 0 else np.nan,
            "profit_factor": profit_factor,
            "payoff_ratio": payoff_ratio,
            "max_drawdown_R": max_drawdown_R(net),
            "average_duration_minutes": float(g["duration_minutes"].mean())
            if n > 0
            else np.nan,
            "best_trade_R": float(net.max()) if n > 0 else np.nan,
            "worst_trade_R": float(net.min()) if n > 0 else np.nan,
        }
    )


def summarize(trades: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
    """Group ``trades`` by ``group_cols`` and compute the metric block.

    Trades within each group are sorted by entry_time first so drawdown and any
    order-dependent metric are chronologically correct.
    """
    if trades.empty:
        return pd.DataFrame(columns=group_cols)

    ordered = trades.sort_values("entry_time", kind="mergesort")
    grouped = ordered.groupby(group_cols, dropna=False, sort=True)
    try:
        # pandas >= 2.2: exclude grouping columns from the per-group frame.
        summary = grouped.apply(_group_metrics, include_groups=False).reset_index()
    except TypeError:
        # Older pandas has no include_groups kwarg; group keys are simply
        # present in the frame, which _group_metrics ignores.
        summary = grouped.apply(_group_metrics).reset_index()
    # rr is one of the group keys in every summary, so breakeven winrate is best
    # computed here from the restored rr column (it is dropped inside the apply).
    if "rr" in summary.columns:
        summary.insert(
            summary.columns.get_loc("winrate") + 1,
            "breakeven_winrate",
            summary["rr"].apply(breakeven_winrate),
        )
    return summary


def build_equity_curve(trades: pd.DataFrame) -> pd.DataFrame:
    """Per (symbol, model, baseline_type, rr) cumulative net-R curve."""
    if trades.empty:
        return pd.DataFrame(
            columns=[
                "trade_number", "symbol", "model", "baseline_type", "rr",
                "entry_time", "net_result_R", "cumulative_R", "drawdown_R",
            ]
        )

    group_cols = ["symbol", "model", "baseline_type", "rr"]
    rows = []
    ordered = trades.sort_values(["symbol", "model", "baseline_type", "rr", "entry_time"],
                                 kind="mergesort")
    for _, g in ordered.groupby(group_cols, dropna=False, sort=True):
        cum = g["net_result_R"].cumsum()
        running_max = cum.cummax()
        drawdown = running_max - cum
        block = pd.DataFrame(
            {
                "trade_number": np.arange(1, len(g) + 1),
                "symbol": g["symbol"].to_numpy(),
                "model": g["model"].to_numpy(),
                "baseline_type": g["baseline_type"].to_numpy(),
                "rr": g["rr"].to_numpy(),
                "entry_time": g["entry_time"].to_numpy(),
                "net_result_R": g["net_result_R"].to_numpy(),
                "cumulative_R": cum.to_numpy(),
                "drawdown_R": drawdown.to_numpy(),
            }
        )
        rows.append(block)
    return pd.concat(rows, ignore_index=True)


def bandwidth_bucket(trades: pd.DataFrame) -> pd.DataFrame:
    """Add a quantile bucket of band_width_pct to a COPY of ``trades``.

    Buckets: very_low, low, medium, high, very_high. Falls back gracefully when
    there are too few distinct values to form 5 quantiles.
    """
    out = trades.copy()
    if out.empty:
        out["band_width_bucket"] = pd.Series(dtype="object")
        return out

    labels = ["very_low", "low", "medium", "high", "very_high"]
    try:
        out["band_width_bucket"] = pd.qcut(
            out["band_width_pct"], q=5, labels=labels, duplicates="drop"
        )
        # If duplicates collapsed bins, qcut returns fewer categories; cast to
        # string so the summary still groups cleanly.
        out["band_width_bucket"] = out["band_width_bucket"].astype("object")
    except (ValueError, IndexError):
        # Not enough distinct values for any quantiles -> single bucket.
        out["band_width_bucket"] = "all"
    out["band_width_bucket"] = out["band_width_bucket"].fillna("undefined")
    return out
