# BB Research Engine — Bollinger Bands vs Random Baseline

A clean, reproducible Python backtesting **research** engine whose only job is to
generate **raw trade-level data** so you can later analyse *where* profit/loss
comes from (by pair, session, hour, day, direction, RR, volatility regime, and
Bollinger Band condition).

> This is a **research tool, not a finished strategy.** It does not optimise, it
> does not pick winners, and it does not hide losses. Bad results are valid
> results.

---

## 1. What this project tests

The central question:

> **"Does Bollinger Bands provide a better distribution of trade outcomes than
> random entry, after realistic execution rules, on large-sample data?"**

To answer it, the engine runs three things side by side under *identical*
execution rules:

1. **Pure BB Mean Reversion** — fade the bands.
2. **Pure BB Breakout** — follow the bands.
3. **Random baselines** — the control group (see §7).

If BB cannot beat random, BB has no demonstrated edge. Total net profit alone is
meaningless without this comparison.

---

## 2. How to place data files

Put one file per **symbol + timeframe** in `data/input/`. Name files using the
convention:

```
SYMBOL_TIMEFRAME.ext      e.g.  EURUSD_H1.csv   GBPJPY_M15.xlsx
```

The symbol and timeframe are parsed from the file name. Any symbol file you drop
in is processed — the engine is not limited to the configured pair list.

Pre-configured pairs (spreads/pip sizes in `config.json`):
`EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD, EURJPY, GBPJPY, EURGBP, AUDJPY`.

---

## 3. Required data format

CSV or XLSX. Required columns (names are configurable via `*_column` keys):

| column     | required | notes                          |
|------------|----------|--------------------------------|
| datetime   | yes      | parseable timestamp            |
| open       | yes      |                                |
| high       | yes      |                                |
| low        | yes      |                                |
| close      | yes      |                                |
| volume     | no       | ignored if present             |
| spread     | no       | assumed in **pips**; else uses `default_spread_pips` |

**Timezone note:** sessions/hours are derived from whatever timezone your data
is stored in. The engine does **not** convert timezones. Label your data's
timezone so session analysis is meaningful.

Validation is strict and **fails loudly** (no silent row-dropping). It checks:
no duplicate datetimes, no missing OHLC, `high >= max(open, close)`,
`low <= min(open, close)`, `high >= low`, ascending datetime, enough rows for
BB, and non-negative spread. On failure it raises a clear `DataValidationError`.

---

## 4. How to run

```bash
pip install -r requirements.txt

# Default: reads data/input, writes data/output/bb_raw_backtest_results.xlsx
python run_backtest.py --config config.json

# Explicit paths
python run_backtest.py --config config.json \
    --input-dir data/input \
    --output data/output/bb_raw_backtest_results.xlsx
```

Run the tests:

```bash
python -m pytest
```

---

## 5. Output sheets

One workbook: `data/output/bb_raw_backtest_results.xlsx`.

| sheet | meaning |
|-------|---------|
| `raw_trades` | every executed trade, one row, full detail (the primary deliverable) |
| `skipped_trades` | every signal that did **not** become a trade, with a reason (`no_next_bar`, `bands_undefined`, `overlapping_position`, `invalid_risk_distance`) |
| `summary_overall` | grouped by model × baseline × RR |
| `summary_by_symbol` | + symbol |
| `summary_by_session` | + session |
| `summary_by_hour` | + entry hour |
| `summary_by_day` | + day of week |
| `summary_by_direction` | + BUY/SELL |
| `summary_by_bandwidth_bucket` | `band_width_pct` bucketed into quantiles `very_low … very_high` (volatility regime) |
| `equity_curve` | per symbol/model/baseline/RR: cumulative R and drawdown |
| `config_used` | verbatim config for full reproducibility |

Each summary reports: trades, wins, losses, winrate, **breakeven_winrate**
(`1/(1+RR)`), gross_net_R, total_net_R, avg/median net R, expectancy_R,
profit_factor, payoff_ratio, max_drawdown_R, average_duration_minutes,
best/worst trade R.

`baseline_type` values: `ACTUAL` (the real BB strategy),
`RANDOM_DIRECTION_ON_BB_TIMESTAMPS`, `RANDOM_TIME_AND_DIRECTION`.

---

## 6. Conservative same-candle TP/SL assumption

With OHLC data we cannot know the intrabar path. **If a single candle's range
contains both the take-profit and the stop-loss, the engine assumes the SL was
hit first** (`exit_reason = "sl"`, `candle_both_hit = True`).

This is deliberately pessimistic. The optimistic alternative (assume TP first)
makes even random strategies look profitable — the single most common way
backtests lie. Other anti-bias rules enforced:

- **No look-ahead:** a signal on candle `t` enters at `open[t+1]`. The signal
  candle's own high/low is never used to fill the entry trade.
- **No repainting:** band values use only a trailing window ending at `t`.
- **One position at a time** per symbol/model/RR/baseline (no overlap).
- **Forced close** at the last bar's close if a trade never hits TP/SL.

---

## 7. Why the random baseline is included

A strategy that makes money is not proof of edge — markets drift, and *any*
entry can look good on the right sample. The baselines isolate two claims:

- **`RANDOM_DIRECTION_ON_BB_TIMESTAMPS`** — same bars BB fired on, coin-toss
  direction. Tests whether BB picks the right **direction**.
- **`RANDOM_TIME_AND_DIRECTION`** — same *number* of trades, random eligible
  bars and direction. Tests whether BB picks the right **time**.

All randomness is seeded (`random_seed` in config) and the per-run seed is
derived from `(seed, symbol, timeframe, model, rr, variant)`, so results are
**byte-for-byte reproducible** regardless of file processing order.

---

## 8. Warning about overfitting / data mining

> **A profitable subset is NOT proof of edge.** With 2 models × 4 RRs × many
> pairs × sessions × hours × days, *some* combination will look great by pure
> chance. This engine intentionally reports **all** combinations, including
> losing ones, and never auto-selects the best.

A result is only interesting if it (a) beats the random baseline, (b) survives
out-of-sample testing, and (c) holds up under multiple-comparison scrutiny.

---

## 9. Next research steps

1. **Out-of-sample validation** — split data; confirm edge holds on unseen data.
2. **Walk-forward testing** — rolling train/test windows.
3. **Monte Carlo reshuffling** — reshuffle trade order / resample to get a
   confidence interval on drawdown and expectancy.
4. **Forward / demo testing** — paper-trade live before risking capital.
5. **Spread/slippage sensitivity** — re-run with `use_spread_cost: true` and
   sweep spread/slippage to find the break-even cost level.

---

## Configuration reference (`config.json`)

| key | meaning |
|-----|---------|
| `bb_period`, `bb_deviation` | Bollinger Band settings (default 20, 2.0) |
| `rr_values` | reward:risk multiples to test (default 1.6, 1.7, 1.9, 2.0) |
| `random_seed` | base seed for reproducible baselines |
| `use_spread_cost` | if `false`, `net_result_R = gross_result_R` |
| `commission_per_trade_R`, `slippage_pips` | extra costs (only applied when cost mode on) |
| `default_spread_pips` | per-symbol fallback spread (pips) |
| `pip_size` | per-symbol pip size; JPY pairs default 0.01, others 0.0001 |
| `sessions` | label → `[start_hour, end_hour)` |
| `*_column` | map your file's column names to the engine's |

### Risk model (both models, given a direction)

`1R = |entry_price − middle_band[t]|`. For a BUY: `SL = entry − 1R`,
`TP = entry + RR × 1R` (mirror for SELL). If `1R <= 0` the trade is skipped and
logged.

### Cost model

`risk_pips = 1R / pip_size`. When `use_spread_cost` is on:
`total_cost_R = (spread_pips + slippage_pips) / risk_pips + commission_R`, and
`net_result_R = gross_result_R − total_cost_R`. Cost columns are always recorded
for transparency even when cost mode is off.
