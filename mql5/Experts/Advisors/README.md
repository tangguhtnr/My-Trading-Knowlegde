# BB_DualModel_EA (MQL5)

One Expert Advisor implementing **both** pure Bollinger Band models, selectable
by input. It is the live/Strategy-Tester counterpart of the Python research
engine in [`../../../bb_research`](../../../bb_research), and enforces the same
correctness rules so live trading matches the research.

## Install

Copy `BB_DualModel_EA.mq5` into your MetaTrader 5 Experts folder, e.g.:

```
C:\Users\Tangguh\AppData\Roaming\MetaQuotes\Terminal\<ID>\MQL5\Experts\Advisors\
```

Then in MetaEditor press **Compile** (F7) → it appears in the Navigator under
Expert Advisors. Drag it onto a chart.

> The folder layout in this repo (`mql5/Experts/Advisors/`) mirrors the MT5
> path on purpose, so you can copy the file straight across.

## Models (input `InpMode`)

| Mode | BUY when | SELL when |
|------|----------|-----------|
| `BB_MEAN_REVERSION` | `close[closed_bar] < lower_band` | `close[closed_bar] > upper_band` |
| `BB_BREAKOUT`       | `close[closed_bar] > upper_band` | `close[closed_bar] < lower_band` |

## Rules it shares with the backtester

- **No look-ahead** — signal is read from the just-closed bar (shift 1); entry
  is taken on the open of the new bar (shift 0). The forming bar is never used.
- **Risk model** — `1R = |entry_open - middle_band|`. BUY: `SL = entry - 1R`,
  `TP = entry + RR*1R`. SELL is the mirror. Trades with `1R <= 0` are skipped.
- **One position at a time** per (symbol, magic).

## Key inputs

| input | meaning |
|-------|---------|
| `InpMode` | which model to run |
| `InpBBPeriod`, `InpBBDeviation` | Bollinger settings (default 20 / 2.0) |
| `InpRR` | reward:risk, TP as a multiple of 1R |
| `InpLotMode` | `LOT_FIXED` or `LOT_RISK_PERCENT` |
| `InpFixedLots` / `InpRiskPercent` | lot size source |
| `InpMagic`, `InpMaxSpreadPts`, `InpSlippagePts` | execution controls |

## Backtesting note

To reproduce the engine's **conservative same-candle TP/SL = SL-first**
assumption, run the Strategy Tester with **"Every tick based on real ticks"**.
Bar/OHLC modelling can resolve a same-candle TP+SL optimistically and inflate
results — the same bias the Python engine deliberately avoids.

> Research caveat (unchanged): a profitable backtest is **not** proof of edge
> until it beats the random baseline and survives out-of-sample / forward tests.
