"""Unit tests for the execution core and random baselines."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.backtester import BacktestConfig, simulate
from src.data_loader import LoadedData
from src.random_baseline import (
    derive_seed,
    random_time_and_direction,
    randomize_direction,
)
from src.signals import DIR_BUY, Signal


def _config():
    return BacktestConfig.from_dict(
        {
            "bb_period": 3,
            "bb_deviation": 2.0,
            "rr_values": [2.0],
            "random_seed": 42,
            "use_spread_cost": False,
            "commission_per_trade_R": 0.0,
            "slippage_pips": 0.0,
            "default_spread_pips": {},
            "pip_size": {},
            "sessions": {"Asia": [0, 8], "London": [8, 16], "NewYork": [16, 24]},
            "datetime_column": "datetime",
            "open_column": "open",
            "high_column": "high",
            "low_column": "low",
            "close_column": "close",
            "spread_column": "spread",
        }
    )


def _make(open_, high, low, close, middle):
    """Build a (LoadedData, bands) pair from explicit arrays.

    middle band is supplied directly so 1R distance is fully controlled.
    """
    n = len(open_)
    times = pd.date_range("2020-01-01", periods=n, freq="h")
    df = pd.DataFrame(
        {
            "datetime": times,
            "open": np.array(open_, dtype=float),
            "high": np.array(high, dtype=float),
            "low": np.array(low, dtype=float),
            "close": np.array(close, dtype=float),
        }
    )
    loaded = LoadedData(
        symbol="TEST",
        timeframe="H1",
        df=df,
        has_spread=False,
        source_path=Path("TEST_H1.csv"),
    )
    mid = np.array(middle, dtype=float)
    bands = pd.DataFrame(
        {
            "middle_band": mid,
            "upper_band": mid + 1.0,
            "lower_band": mid - 1.0,
            "band_width": np.full(n, 2.0),
            "band_width_pct": np.full(n, 2.0),
        }
    )
    return loaded, bands


def test_tp_hit_buy():
    # Signal t=0 BUY; entry open[1]=10; middle[0]=9 -> dist 1; rr2 -> tp 12.
    loaded, bands = _make(
        open_=[10, 10, 10, 10],
        high=[10.1, 12.5, 10.1, 10.1],  # bar1 reaches tp=12
        low=[9.9, 9.5, 9.9, 9.9],       # bar1 low 9.5 > sl 9 -> no sl
        close=[10, 10, 10, 10],
        middle=[9, 9, 9, 9],
    )
    trades, skipped, _ = simulate(
        loaded, bands, [Signal(0, DIR_BUY)], 2.0, "M", "ACTUAL", _config(), 1
    )
    assert len(trades) == 1
    t = trades[0]
    assert t["exit_reason"] == "tp"
    assert t["exit_price"] == 12.0
    assert abs(t["gross_result_R"] - 2.0) < 1e-9
    assert t["candle_both_hit"] is False


def test_sl_hit_buy():
    loaded, bands = _make(
        open_=[10, 10, 10, 10],
        high=[10.1, 11.0, 10.1, 10.1],  # tp=12 not reached
        low=[9.9, 8.5, 9.9, 9.9],       # bar1 low 8.5 <= sl 9 -> sl
        close=[10, 10, 10, 10],
        middle=[9, 9, 9, 9],
    )
    trades, _, _ = simulate(
        loaded, bands, [Signal(0, DIR_BUY)], 2.0, "M", "ACTUAL", _config(), 1
    )
    assert len(trades) == 1
    t = trades[0]
    assert t["exit_reason"] == "sl"
    assert t["exit_price"] == 9.0
    assert abs(t["gross_result_R"] - (-1.0)) < 1e-9


def test_same_candle_sl_first():
    # bar1 contains BOTH tp (12) and sl (9). Conservative rule -> SL.
    loaded, bands = _make(
        open_=[10, 10, 10, 10],
        high=[10.1, 12.5, 10.1, 10.1],
        low=[9.9, 8.5, 9.9, 9.9],
        close=[10, 10, 10, 10],
        middle=[9, 9, 9, 9],
    )
    trades, _, _ = simulate(
        loaded, bands, [Signal(0, DIR_BUY)], 2.0, "M", "ACTUAL", _config(), 1
    )
    t = trades[0]
    assert t["exit_reason"] == "sl"
    assert t["candle_both_hit"] is True
    assert abs(t["gross_result_R"] - (-1.0)) < 1e-9


def test_no_lookahead_entry_at_next_open():
    # Signal bar (index 0) has a massive high that WOULD hit tp if we cheated by
    # entering on the signal candle. Entry must be at open[1]; bars 1..3 never
    # reach tp, so the trade is force-closed -> proves bar0 was not used.
    loaded, bands = _make(
        open_=[10, 10, 10, 10],
        high=[1000, 10.5, 10.5, 10.5],  # bar0 huge, but must be ignored
        low=[9.9, 9.5, 9.5, 9.5],
        close=[10, 10, 10, 10.2],
        middle=[9, 9, 9, 9],
    )
    trades, _, _ = simulate(
        loaded, bands, [Signal(0, DIR_BUY)], 2.0, "M", "ACTUAL", _config(), 1
    )
    t = trades[0]
    assert t["entry_time"] == pd.Timestamp("2020-01-01 01:00:00")
    assert t["entry_price"] == 10.0
    assert t["exit_reason"] == "forced_close"
    # forced close at final close 10.2 -> (10.2-10)/1 = 0.2 R
    assert abs(t["gross_result_R"] - 0.2) < 1e-9


def test_no_next_bar_skipped():
    # Signal on the last bar -> no t+1 -> must be skipped, not entered.
    loaded, bands = _make(
        open_=[10, 10, 10, 10],
        high=[10.1, 10.1, 10.1, 10.1],
        low=[9.9, 9.9, 9.9, 9.9],
        close=[10, 10, 10, 10],
        middle=[9, 9, 9, 9],
    )
    trades, skipped, _ = simulate(
        loaded, bands, [Signal(3, DIR_BUY)], 2.0, "M", "ACTUAL", _config(), 1
    )
    assert len(trades) == 0
    assert len(skipped) == 1
    assert skipped[0]["skipped_reason"] == "no_next_bar"


def test_no_overlap_one_position():
    # Two BUY signals at t=0 and t=1. First enters at bar1 and runs to forced
    # close at the end, so the second signal must be skipped as overlapping.
    loaded, bands = _make(
        open_=[10, 10, 10, 10],
        high=[10.1, 10.5, 10.5, 10.5],
        low=[9.9, 9.5, 9.5, 9.5],
        close=[10, 10, 10, 10],
        middle=[9, 9, 9, 9],
    )
    trades, skipped, _ = simulate(
        loaded, bands, [Signal(0, DIR_BUY), Signal(1, DIR_BUY)],
        2.0, "M", "ACTUAL", _config(), 1,
    )
    assert len(trades) == 1
    assert any(s["skipped_reason"] == "overlapping_position" for s in skipped)


def test_random_baseline_reproducible():
    signals = [Signal(i, DIR_BUY) for i in range(10)]
    seed = derive_seed(42, "TEST", "H1", "M", 2.0, "RD")

    a = randomize_direction(signals, seed)
    b = randomize_direction(signals, seed)
    assert [s.direction for s in a] == [s.direction for s in b]
    assert [s.index for s in a] == [s.index for s in b]

    eligible = list(range(50))
    seed2 = derive_seed(42, "TEST", "H1", "M", 2.0, "RT")
    c = random_time_and_direction(8, eligible, seed2)
    d = random_time_and_direction(8, eligible, seed2)
    assert [(s.index, s.direction) for s in c] == [
        (s.index, s.direction) for s in d
    ]
    assert len(c) == 8


def test_derive_seed_stable_and_distinct():
    s1 = derive_seed(42, "EURUSD", "H1", "BB", 2.0, "RD")
    s2 = derive_seed(42, "EURUSD", "H1", "BB", 2.0, "RD")
    s3 = derive_seed(42, "EURUSD", "H1", "BB", 2.0, "RT")
    assert s1 == s2
    assert s1 != s3
