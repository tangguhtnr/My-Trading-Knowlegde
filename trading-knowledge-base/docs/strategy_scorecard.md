# Strategy Scorecard

Use this to classify a strategy without emotional bias.

## Verdict labels

- `REJECTED`: fails after bug/cost/leakage audit.
- `RESEARCH_ONLY`: interesting pattern, not executable yet.
- `BIAS_FILTER`: weak directional value, not standalone trading engine.
- `DEMO_TEST`: passed enough backtesting to justify forward demo.
- `LIVE_SMALL`: passed forward demo and can be tested with tiny size.
- `LIVE_SCALE_CANDIDATE`: passed live-small sample; scale gradually.

## Scorecard

| Category | Questions | Pass standard |
|---|---|---|
| Data quality | gaps, duplicates, timezone, OHLC validity | audited and documented |
| Leakage | closed bars, HTF shift, no future pivots | no known leakage |
| Costs | spread, commission, slippage, funding | survives realistic + stress costs |
| Robustness | multiple regimes/years | not dependent on one cherry-picked period |
| Sample size | enough trades? | preferably 200+ for claims |
| OOS | chronological validation | positive after costs |
| Execution | order type, fill timing, broker constraints | model matches platform behavior |
| Risk | DD, exposure, leverage, liquidation | survivable under stress |

## Red flags

- PF > 2.5 on a single instrument with small sample.
- Strategy only works in one year.
- Many parameters optimized on full sample.
- No cost sensitivity.
- Uses fractals/pivots without confirmation-delay modeling.
- Uses current HTF candle as if completed.
- Overlapping horizon labels called “backtest”.
- Win rate advertised without avg win/loss.
- Tiny stop loss below realistic spread/slippage.
- Python result contradicts MT5 result but Python is treated as truth.

## Required final sentence

Every strategy review must end with one of:

- “Rejected.”
- “Research-only.”
- “Bias filter only.”
- “Demo forward-test candidate.”
- “Small-live candidate after demo pass.”
