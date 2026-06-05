#!/usr/bin/env python3
"""Audit basic OHLCV CSV integrity."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import pandas as pd


def audit(path: Path, time_col: str, ohlcv: list[str]) -> dict:
    df = pd.read_csv(path)
    missing_cols = [c for c in [time_col, *ohlcv] if c not in df.columns]
    if missing_cols:
        return {"ok": False, "error": "missing_columns", "columns": missing_cols}

    df[time_col] = pd.to_datetime(df[time_col], errors="coerce", utc=False)
    bad_time = int(df[time_col].isna().sum())
    df = df.sort_values(time_col)
    dupes = int(df[time_col].duplicated().sum())

    open_col, high_col, low_col, close_col, volume_col = ohlcv
    numeric = df[[open_col, high_col, low_col, close_col, volume_col]].apply(pd.to_numeric, errors="coerce")
    nan_cells = int(numeric.isna().sum().sum())
    nonpositive_ohlc = int((numeric[[open_col, high_col, low_col, close_col]] <= 0).sum().sum())
    negative_volume = int((numeric[volume_col] < 0).sum())
    high_low_bad = int((numeric[high_col] < numeric[low_col]).sum())
    high_below_body = int((numeric[high_col] < numeric[[open_col, close_col]].max(axis=1)).sum())
    low_above_body = int((numeric[low_col] > numeric[[open_col, close_col]].min(axis=1)).sum())

    deltas = df[time_col].diff().dropna()
    gap_summary = None
    if not deltas.empty:
        mode_delta = deltas.mode().iloc[0]
        large_gaps = deltas[deltas > mode_delta * 1.5]
        gap_summary = {
            "inferred_frequency_seconds": mode_delta.total_seconds(),
            "large_gap_count": int(len(large_gaps)),
            "largest_gap_seconds": float(large_gaps.max().total_seconds()) if len(large_gaps) else 0.0,
        }

    issues = {
        "bad_time": bad_time,
        "duplicate_timestamps": dupes,
        "nan_numeric_cells": nan_cells,
        "nonpositive_ohlc_cells": nonpositive_ohlc,
        "negative_volume_rows": negative_volume,
        "high_below_low_rows": high_low_bad,
        "high_below_open_or_close_rows": high_below_body,
        "low_above_open_or_close_rows": low_above_body,
    }
    ok = all(v == 0 for v in issues.values())
    return {
        "ok": ok,
        "rows": int(len(df)),
        "start": str(df[time_col].min()),
        "end": str(df[time_col].max()),
        "issues": issues,
        "gaps": gap_summary,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--time-col", default="time")
    p.add_argument("--ohlcv", nargs=5, default=["open", "high", "low", "close", "volume"], metavar=("OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"))
    args = p.parse_args()
    result = audit(args.csv, args.time_col, args.ohlcv)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1

if __name__ == "__main__":
    sys.exit(main())
