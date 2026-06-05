# Validation Protocol

## Truth hierarchy

1. Live trading P&L.
2. Forward demo test.
3. MT5 100% real tick backtest.
4. MT5 mixed tick-quality backtest.
5. MT5 1-minute OHLC mode.
6. TradingView backtest.
7. Python custom backtest.
8. ML diagnostics without executable trade simulation.

Higher layer beats lower layer.

## Required checks before saying “edge”

- Data range is explicit.
- Data source is explicit.
- Timezone is explicit.
- Duplicate timestamps checked.
- Missing bars/gaps checked.
- Nonpositive OHLC checked.
- Spread/commission/slippage/funding included where relevant.
- Train/test split is chronological.
- Higher timeframe features are shifted to avoid leakage.
- Signals use closed bars unless current-bar logic is intentional and executable.
- Parameter selection is separated from OOS evaluation.
- Non-overlapping trade logic is used for overlapping horizons.
- Results are stress-tested across regimes.
- Multiple-testing correction considered when many candidates are tested.

## Anti-leakage rules

### Closed-bar rule

Use `shift=1` for indicator features in live/EA contexts unless the strategy genuinely executes on forming-bar data.

### Higher timeframe rule

When joining D1 features into H4/H1/M15 rows, only use the previous completed D1 bar. Same-day final D1 OHLC leaks future information.

### Walk-forward rule

Never random-split time series. Use chronological train/validation/test or rolling walk-forward.

### Drop-NaN rule

Compute features first, then drop NaNs, then align signals and returns. Do not compute signals on a shortened frame and slice with indices from the original frame.

## Cost sensitivity

Every strategy must be tested across cost assumptions.

Example grid:

```text
0 bps, 1 bps, 2 bps, 3 bps, 4 bps, 5 bps, 10 bps, 15 bps, 30 bps
```

The breakeven cost is often more important than headline PF.

## Minimum report fields

- Instrument / symbol.
- Broker / exchange / data vendor.
- Timeframe.
- Date range.
- Number of trades.
- Win rate.
- Profit factor.
- Average win/loss.
- Max drawdown.
- Cost model.
- Slippage model.
- Tick quality / data quality.
- In-sample vs out-of-sample split.
- Known caveats.
- Final verdict: live-ready / demo-only / research-only / rejected.
