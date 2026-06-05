"""CLI entry point for the Bollinger Bands research engine.

Usage:
    python run_backtest.py --config config.json
    python run_backtest.py --config config.json \
        --input-dir data/input \
        --output data/output/bb_raw_backtest_results.xlsx

For every data file in the input directory, and for every (model, RR) pair, this
runs the actual BB strategy plus both random baselines, then writes one Excel
workbook with raw trades, skipped signals, and all summaries.

It does NOT pick winners, optimise parameters, or hide losing combinations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

import pandas as pd

from src.backtester import BacktestConfig, eligible_entry_indices, simulate
from src.data_loader import discover_input_files, load_file
from src.exporter import export_results
from src.indicators import bollinger_bands
from src.random_baseline import (
    BASELINE_ACTUAL,
    BASELINE_RANDOM_DIRECTION,
    BASELINE_RANDOM_TIME_DIRECTION,
    derive_seed,
    random_time_and_direction,
    randomize_direction,
)
from src.signals import (
    MODEL_BREAKOUT,
    MODEL_MEAN_REVERSION,
    generate_signals,
)
from src.validation import DataValidationError

MODELS = [MODEL_MEAN_REVERSION, MODEL_BREAKOUT]


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bollinger Bands research backtester (BB vs random baseline)."
    )
    parser.add_argument(
        "--config", required=True, help="Path to config.json"
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Directory of input data files (default: data/input next to config).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output xlsx path (default: data/output/bb_raw_backtest_results.xlsx).",
    )
    return parser.parse_args(argv)


def load_config(path: Path) -> dict:
    if not path.exists():
        raise DataValidationError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def run(config_path: Path, input_dir: Path, output_path: Path) -> Path:
    raw_config = load_config(config_path)
    cfg = BacktestConfig.from_dict(raw_config)

    files = discover_input_files(input_dir)
    if not files:
        raise DataValidationError(
            f"No input data files (.csv/.xlsx) found in {input_dir}. "
            f"Place one file per symbol/timeframe, e.g. EURUSD_H1.csv."
        )

    all_trades: List[dict] = []
    all_skipped: List[dict] = []
    trade_id = 1

    for path in files:
        loaded = load_file(path, raw_config)  # validates or raises
        bands = bollinger_bands(
            loaded.df["close"], cfg.bb_period, cfg.bb_deviation
        )
        n = len(loaded.df)
        eligible = eligible_entry_indices(bands, n)

        print(
            f"[{loaded.symbol} {loaded.timeframe}] rows={n} "
            f"eligible_bars={len(eligible)}"
        )

        for model in MODELS:
            signals = generate_signals(loaded.df, bands, model)
            n_signals = len(signals)

            for rr in cfg.rr_values:
                # 1) Actual BB strategy.
                t, s, trade_id = simulate(
                    loaded, bands, signals, rr, model,
                    BASELINE_ACTUAL, cfg, trade_id,
                )
                all_trades.extend(t)
                all_skipped.extend(s)

                # 2) Random DIRECTION on the same BB timestamps.
                seed_rd = derive_seed(
                    cfg.random_seed, loaded.symbol, loaded.timeframe,
                    model, rr, BASELINE_RANDOM_DIRECTION,
                )
                rd_signals = randomize_direction(signals, seed_rd)
                t, s, trade_id = simulate(
                    loaded, bands, rd_signals, rr, model,
                    BASELINE_RANDOM_DIRECTION, cfg, trade_id,
                )
                all_trades.extend(t)
                all_skipped.extend(s)

                # 3) Random TIME + DIRECTION, same number of signals as BB.
                seed_rt = derive_seed(
                    cfg.random_seed, loaded.symbol, loaded.timeframe,
                    model, rr, BASELINE_RANDOM_TIME_DIRECTION,
                )
                rt_signals = random_time_and_direction(
                    n_signals, eligible, seed_rt
                )
                t, s, trade_id = simulate(
                    loaded, bands, rt_signals, rr, model,
                    BASELINE_RANDOM_TIME_DIRECTION, cfg, trade_id,
                )
                all_trades.extend(t)
                all_skipped.extend(s)

    trades_df = pd.DataFrame(all_trades)
    skipped_df = pd.DataFrame(all_skipped)

    out = export_results(trades_df, skipped_df, raw_config, output_path)
    print(
        f"\nDone. Executed trades: {len(trades_df)} | "
        f"Skipped signals: {len(skipped_df)}"
    )
    print(f"Results workbook: {out}")
    return out


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    config_path = Path(args.config)
    base_dir = config_path.resolve().parent

    input_dir = (
        Path(args.input_dir)
        if args.input_dir
        else base_dir / "data" / "input"
    )
    output_path = (
        Path(args.output)
        if args.output
        else base_dir / "data" / "output" / "bb_raw_backtest_results.xlsx"
    )

    try:
        run(config_path, input_dir, output_path)
    except DataValidationError as exc:
        print(f"\nDATA ERROR: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"\nCONFIG ERROR: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
