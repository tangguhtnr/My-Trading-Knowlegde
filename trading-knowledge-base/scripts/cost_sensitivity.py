#!/usr/bin/env python3
"""Simple cost sensitivity for return streams or close-to-close price series."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def sharpe(x: pd.Series, periods: int = 252) -> float:
    x = x.dropna()
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * np.sqrt(periods))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--return-col", required=True, help="return column, or close column if --price-mode close_to_close")
    p.add_argument("--price-mode", choices=["returns", "close_to_close"], default="returns")
    p.add_argument("--periods", type=int, default=252)
    p.add_argument("--costs-bps", nargs="*", type=float, default=[0,1,2,3,4,5,10,15,30])
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    s = pd.to_numeric(df[args.return_col], errors="coerce")
    if args.price_mode == "close_to_close":
        ret = np.log(s / s.shift(1)).dropna()
    else:
        ret = s.dropna()

    print("cost_bps,mean_return,sharpe,total_log_return")
    for c in args.costs_bps:
        adjusted = ret - c / 10000.0
        print(f"{c:g},{adjusted.mean():.10f},{sharpe(adjusted,args.periods):.6f},{adjusted.sum():.10f}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
