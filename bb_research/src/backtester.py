"""The execution core: turn signals into trades under strict, conservative rules.

Key correctness rules enforced here (each is the kind of thing that silently
inflates fake backtests if you get it wrong):

  * NO LOOK-AHEAD: a signal on bar ``t`` enters at ``open[t+1]``. We never use
    any information from bar ``t+1`` onwards to decide whether to enter, and we
    never enter on the signal bar's own close.

  * SAME-CANDLE TP/SL -> SL FIRST: with only OHLC data we cannot know the
    intrabar path. If a single candle's range contains both the TP and the SL,
    we conservatively assume the SL was touched first. This avoids the classic
    optimistic bias that makes random strategies look profitable.

  * ONE POSITION AT A TIME: per (symbol, model, rr, baseline) we never hold
    overlapping trades. A new entry may only occur strictly after the previous
    trade's exit bar.

  * FORCED CLOSE: a trade still open at the last bar is closed at that bar's
    close, with exit_reason="forced_close" and its R computed from that price.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .data_loader import LoadedData, resolve_pip_size, resolve_spread_pips
from .random_baseline import BASELINE_ACTUAL
from .sessions import classify_session
from .signals import DIR_BUY, Signal


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
@dataclass
class BacktestConfig:
    """Typed view over config.json with light validation."""

    bb_period: int
    bb_deviation: float
    rr_values: List[float]
    random_seed: int
    use_spread_cost: bool
    commission_per_trade_R: float
    slippage_pips: float
    default_spread_pips: Dict[str, float]
    pip_size: Dict[str, float]
    sessions: Dict[str, List[int]]
    datetime_column: str
    open_column: str
    high_column: str
    low_column: str
    close_column: str
    spread_column: str
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, cfg: dict) -> "BacktestConfig":
        try:
            obj = cls(
                bb_period=int(cfg["bb_period"]),
                bb_deviation=float(cfg["bb_deviation"]),
                rr_values=[float(x) for x in cfg["rr_values"]],
                random_seed=int(cfg["random_seed"]),
                use_spread_cost=bool(cfg.get("use_spread_cost", False)),
                commission_per_trade_R=float(cfg.get("commission_per_trade_R", 0.0)),
                slippage_pips=float(cfg.get("slippage_pips", 0.0)),
                default_spread_pips=dict(cfg.get("default_spread_pips", {})),
                pip_size=dict(cfg.get("pip_size", {})),
                sessions=dict(cfg.get("sessions", {
                    "Asia": [0, 8], "London": [8, 16], "NewYork": [16, 24],
                })),
                datetime_column=cfg.get("datetime_column", "datetime"),
                open_column=cfg.get("open_column", "open"),
                high_column=cfg.get("high_column", "high"),
                low_column=cfg.get("low_column", "low"),
                close_column=cfg.get("close_column", "close"),
                spread_column=cfg.get("spread_column", "spread"),
                raw=dict(cfg),
            )
        except KeyError as exc:
            raise ValueError(f"Missing required config key: {exc}") from exc

        if obj.bb_period <= 1:
            raise ValueError("bb_period must be > 1")
        if obj.bb_deviation <= 0:
            raise ValueError("bb_deviation must be > 0")
        if not obj.rr_values:
            raise ValueError("rr_values must be a non-empty list")
        if any(rr <= 0 for rr in obj.rr_values):
            raise ValueError("all rr_values must be > 0")
        return obj


# --------------------------------------------------------------------------- #
# Trade record (one row of the raw trade log)
# --------------------------------------------------------------------------- #
@dataclass
class Trade:
    trade_id: int
    symbol: str
    timeframe: str
    model: str
    baseline_type: str
    rr: float
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: str
    entry_price: float
    sl_price: float
    tp_price: float
    exit_price: float
    exit_reason: str
    gross_result_R: float
    net_result_R: float
    pnl_pips: float
    duration_bars: int
    duration_minutes: float
    bb_period: int
    bb_deviation: float
    upper_band_signal: float
    middle_band_signal: float
    lower_band_signal: float
    band_width: float
    band_width_pct: float
    close_signal: float
    close_position_vs_band: str
    risk_price_distance: float
    risk_pips: float
    spread_pips: float
    slippage_pips: float
    commission_R: float
    total_cost_R: float
    spread_to_risk_ratio: float
    day_of_week: str
    entry_hour: int
    session: str
    candle_both_hit: bool
    skipped_reason: str = ""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def eligible_entry_indices(bands: pd.DataFrame, n: int) -> np.ndarray:
    """Bars usable as a SIGNAL bar: bands defined AND a t+1 entry bar exists."""
    middle = bands["middle_band"].to_numpy()
    defined = ~np.isnan(middle)
    idx = np.flatnonzero(defined)
    return idx[idx <= n - 2]  # need t+1 <= n-1


def _close_position_vs_band(close_t: float, upper_t: float, lower_t: float) -> str:
    if close_t > upper_t:
        return "above_upper"
    if close_t < lower_t:
        return "below_lower"
    return "inside"


# --------------------------------------------------------------------------- #
# Core simulation
# --------------------------------------------------------------------------- #
def simulate(
    loaded: LoadedData,
    bands: pd.DataFrame,
    signals: Sequence[Signal],
    rr: float,
    model: str,
    baseline_type: str,
    cfg: BacktestConfig,
    trade_id_start: int,
) -> Tuple[List[dict], List[dict], int]:
    """Run one (model, rr, baseline) backtest over a single symbol.

    Returns (executed_trade_dicts, skipped_dicts, next_trade_id).
    """
    df = loaded.df
    symbol = loaded.symbol
    timeframe = loaded.timeframe

    dt = df["datetime"].to_numpy()
    open_ = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()

    middle = bands["middle_band"].to_numpy()
    upper = bands["upper_band"].to_numpy()
    lower = bands["lower_band"].to_numpy()
    bwidth = bands["band_width"].to_numpy()
    bwidth_pct = bands["band_width_pct"].to_numpy()

    spread_arr = df["spread"].to_numpy() if loaded.has_spread else None

    pip_size = resolve_pip_size(symbol, cfg.raw)
    default_spread = resolve_spread_pips(symbol, cfg.raw)

    n = len(df)
    trades: List[dict] = []
    skipped: List[dict] = []
    trade_id = trade_id_start

    # One position at a time: the next entry must be strictly after this index.
    next_available_index = 0

    for sig in signals:
        t = sig.index
        direction = sig.direction

        def log_skip(reason: str) -> None:
            skipped.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "model": model,
                    "baseline_type": baseline_type,
                    "rr": rr,
                    "signal_time": pd.Timestamp(dt[t]) if 0 <= t < n else pd.NaT,
                    "direction": direction,
                    "close_signal": float(close[t]) if 0 <= t < n else np.nan,
                    "upper_band_signal": float(upper[t]) if 0 <= t < n else np.nan,
                    "middle_band_signal": float(middle[t]) if 0 <= t < n else np.nan,
                    "lower_band_signal": float(lower[t]) if 0 <= t < n else np.nan,
                    "skipped_reason": reason,
                }
            )

        entry_idx = t + 1
        # No look-ahead / no entry without a next bar.
        if entry_idx >= n:
            log_skip("no_next_bar")
            continue

        # Bands must be defined at the signal bar (guards random baselines too).
        if np.isnan(middle[t]):
            log_skip("bands_undefined")
            continue

        # One-position-at-a-time: cannot enter while a prior trade is still open.
        if entry_idx < next_available_index:
            log_skip("overlapping_position")
            continue

        entry_price = float(open_[entry_idx])
        middle_t = float(middle[t])
        dist = abs(entry_price - middle_t)  # 1R in price terms
        if dist <= 0:
            log_skip("invalid_risk_distance")
            continue

        is_buy = direction == DIR_BUY
        if is_buy:
            sl_price = entry_price - dist
            tp_price = entry_price + rr * dist
        else:
            sl_price = entry_price + dist
            tp_price = entry_price - rr * dist

        # ---- Scan forward for exit (entry bar inclusive) -------------------- #
        exit_idx = n - 1
        exit_price = float(close[n - 1])
        exit_reason = "forced_close"
        both_hit = False

        for k in range(entry_idx, n):
            hi = high[k]
            lo = low[k]
            if is_buy:
                sl_hit = lo <= sl_price
                tp_hit = hi >= tp_price
            else:
                sl_hit = hi >= sl_price
                tp_hit = lo <= tp_price

            if sl_hit and tp_hit:
                # Conservative: assume SL touched first within the candle.
                exit_idx = k
                exit_price = sl_price
                exit_reason = "sl"
                both_hit = True
                break
            if sl_hit:
                exit_idx = k
                exit_price = sl_price
                exit_reason = "sl"
                break
            if tp_hit:
                exit_idx = k
                exit_price = tp_price
                exit_reason = "tp"
                break

        # ---- Results ------------------------------------------------------- #
        if is_buy:
            gross_R = (exit_price - entry_price) / dist
            pnl_pips = (exit_price - entry_price) / pip_size
        else:
            gross_R = (entry_price - exit_price) / dist
            pnl_pips = (entry_price - exit_price) / pip_size

        risk_pips = dist / pip_size

        # Spread: prefer per-bar data spread (assumed in pips), else config
        # default, else zero. Recorded for transparency regardless of cost mode.
        if spread_arr is not None and not np.isnan(spread_arr[entry_idx]):
            spread_pips = float(spread_arr[entry_idx])
        elif default_spread is not None:
            spread_pips = float(default_spread)
        else:
            spread_pips = 0.0

        slippage_pips = cfg.slippage_pips
        commission_R = cfg.commission_per_trade_R

        if cfg.use_spread_cost:
            # Convert pip-denominated costs to R using this trade's own 1R size.
            total_cost_R = (spread_pips + slippage_pips) / risk_pips + commission_R
        else:
            total_cost_R = 0.0

        net_R = gross_R - total_cost_R
        spread_to_risk_ratio = spread_pips / risk_pips if risk_pips > 0 else np.nan

        entry_time = pd.Timestamp(dt[entry_idx])
        exit_time = pd.Timestamp(dt[exit_idx])
        duration_minutes = (exit_time - entry_time).total_seconds() / 60.0

        trade = Trade(
            trade_id=trade_id,
            symbol=symbol,
            timeframe=timeframe,
            model=model,
            baseline_type=baseline_type,
            rr=rr,
            signal_time=pd.Timestamp(dt[t]),
            entry_time=entry_time,
            exit_time=exit_time,
            direction=direction,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            exit_price=exit_price,
            exit_reason=exit_reason,
            gross_result_R=gross_R,
            net_result_R=net_R,
            pnl_pips=pnl_pips,
            duration_bars=int(exit_idx - entry_idx),
            duration_minutes=duration_minutes,
            bb_period=cfg.bb_period,
            bb_deviation=cfg.bb_deviation,
            upper_band_signal=float(upper[t]),
            middle_band_signal=middle_t,
            lower_band_signal=float(lower[t]),
            band_width=float(bwidth[t]),
            band_width_pct=float(bwidth_pct[t]),
            close_signal=float(close[t]),
            close_position_vs_band=_close_position_vs_band(
                float(close[t]), float(upper[t]), float(lower[t])
            ),
            risk_price_distance=dist,
            risk_pips=risk_pips,
            spread_pips=spread_pips,
            slippage_pips=slippage_pips,
            commission_R=commission_R,
            total_cost_R=total_cost_R,
            spread_to_risk_ratio=spread_to_risk_ratio,
            day_of_week=entry_time.day_name(),
            entry_hour=int(entry_time.hour),
            session=classify_session(int(entry_time.hour), cfg.sessions),
            candle_both_hit=both_hit,
            skipped_reason="",
        )
        trades.append(asdict(trade))
        trade_id += 1

        # Block overlap: next entry must be after this trade's exit bar.
        next_available_index = exit_idx + 1

    return trades, skipped, trade_id
