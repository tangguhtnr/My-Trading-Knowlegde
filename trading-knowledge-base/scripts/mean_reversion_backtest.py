#!/usr/bin/env python3
"""Minimal daily mean-reversion research template.

This is deliberately simple. It is not a live strategy.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def metrics(r: pd.Series, periods: int = 252) -> dict:
    r = r.dropna()
    equity = np.exp(r.cumsum())
    dd = equity / equity.cummax() - 1
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    gross_profit = float(r[r > 0].sum())
    gross_loss = float(-r[r < 0].sum())
    return {
        "trades": int(len(r)),
        "win_rate": wins / max(wins + losses, 1),
        "profit_factor_logret": gross_profit / gross_loss if gross_loss else float("inf"),
        "total_log_return": float(r.sum()),
        "sharpe": float(r.mean() / r.std(ddof=1) * np.sqrt(periods)) if len(r) > 2 and r.std(ddof=1) else float("nan"),
        "max_drawdown": float(dd.min()),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--time-col", default="time")
    p.add_argument("--close-col", default="close")
    p.add_argument("--cost-bps", type=float, default=0.0)
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    df[args.time_col] = pd.to_datetime(df[args.time_col])
    df = df.sort_values(args.time_col)
    close = pd.to_numeric(df[args.close_col], errors="coerce")
    log_ret = np.log(close / close.shift(1))

    # Mean reversion: bet against previous bar direction.
    prev_dir = np.sign(log_ret.shift(1)).replace(0, np.nan).ffill()
    signal = -prev_dir
    trade_ret = signal * log_ret - args.cost_bps / 10000.0
    out = metrics(trade_ret.dropna())
    for k, v in out.items():
        print(f"{k}: {v}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
