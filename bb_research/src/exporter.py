"""Excel export of all research outputs.

Produces a single workbook with the raw trade log, the skipped-signal log, the
requested grouped summaries, an equity curve, and a verbatim copy of the config
used (so any result is fully reproducible from the workbook alone).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from .metrics import bandwidth_bucket, build_equity_curve, summarize

# Canonical raw-trade column order (matches the Trade dataclass / spec).
RAW_TRADE_COLUMNS: List[str] = [
    "trade_id", "symbol", "timeframe", "model", "baseline_type", "rr",
    "signal_time", "entry_time", "exit_time", "direction",
    "entry_price", "sl_price", "tp_price", "exit_price", "exit_reason",
    "gross_result_R", "net_result_R", "pnl_pips", "duration_bars",
    "duration_minutes", "bb_period", "bb_deviation",
    "upper_band_signal", "middle_band_signal", "lower_band_signal",
    "band_width", "band_width_pct", "close_signal", "close_position_vs_band",
    "risk_price_distance", "risk_pips", "spread_pips", "slippage_pips",
    "commission_R", "total_cost_R", "spread_to_risk_ratio",
    "day_of_week", "entry_hour", "session", "candle_both_hit", "skipped_reason",
]

SKIPPED_COLUMNS: List[str] = [
    "symbol", "timeframe", "model", "baseline_type", "rr", "signal_time",
    "direction", "close_signal", "upper_band_signal", "middle_band_signal",
    "lower_band_signal", "skipped_reason",
]


def _ordered(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Return df with ``columns`` first (those present), preserving extras."""
    if df.empty:
        return pd.DataFrame(columns=columns)
    present = [c for c in columns if c in df.columns]
    extras = [c for c in df.columns if c not in columns]
    return df[present + extras]


def _config_to_rows(config: dict) -> pd.DataFrame:
    rows = []
    for key, value in config.items():
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = value
        rows.append({"key": key, "value": value_str})
    return pd.DataFrame(rows, columns=["key", "value"])


def export_results(
    trades: pd.DataFrame,
    skipped: pd.DataFrame,
    config: dict,
    output_path: Path,
) -> Path:
    """Write the full results workbook and return its path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw_trades = _ordered(trades, RAW_TRADE_COLUMNS)
    skipped_trades = _ordered(skipped, SKIPPED_COLUMNS)

    # Summaries (all group by model + baseline_type + rr plus their dimension).
    base = ["model", "baseline_type", "rr"]
    summary_overall = summarize(trades, base)
    summary_by_symbol = summarize(trades, ["symbol"] + base)
    summary_by_session = summarize(trades, ["session"] + base)
    summary_by_hour = summarize(trades, ["entry_hour"] + base)
    summary_by_day = summarize(trades, ["day_of_week"] + base)
    summary_by_direction = summarize(trades, ["direction"] + base)

    with_bucket = bandwidth_bucket(trades)
    summary_by_bandwidth = summarize(with_bucket, ["band_width_bucket"] + base)

    equity_curve = build_equity_curve(trades)
    config_used = _config_to_rows(config)

    sheets = {
        "raw_trades": raw_trades,
        "skipped_trades": skipped_trades,
        "summary_overall": summary_overall,
        "summary_by_symbol": summary_by_symbol,
        "summary_by_session": summary_by_session,
        "summary_by_hour": summary_by_hour,
        "summary_by_day": summary_by_day,
        "summary_by_direction": summary_by_direction,
        "summary_by_bandwidth_bucket": summary_by_bandwidth,
        "equity_curve": equity_curve,
        "config_used": config_used,
    }

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            # Excel forbids tz-aware datetimes; our data is tz-naive already,
            # but guard against accidental tz columns.
            safe = df.copy()
            for col in safe.columns:
                if pd.api.types.is_datetime64tz_dtype(safe[col]):
                    safe[col] = safe[col].dt.tz_localize(None)
            safe.to_excel(writer, sheet_name=name[:31], index=False)

    return output_path
