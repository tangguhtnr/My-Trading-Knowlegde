# Core Principles

## 1. Truth over comfort

If the data says the strategy fails, say it fails. Do not optimize the wording to make failure sound promising.

## 2. Backtest is not reality

A backtest is a controlled historical simulation. It is useful for falsifying weak ideas, not for promising future P&L.

Common degradation sources:

- variable spread;
- slippage;
- missing commission/swap/funding;
- simulated intrabar path;
- broker timezone mismatch;
- partial tick quality;
- lookahead bias;
- overfitting after testing many parameter combinations.

Rule of thumb: real PF can be 10–30% weaker than a decent backtest, and much worse for low-fidelity sims.

## 3. Never claim unverified numbers

Allowed:

> “This MT5 report shows PF 1.28 on this period with this tick quality.”

Not allowed:

> “This should make 10% monthly.”

If the exact combination was not tested, label it as untested.

## 4. Sample size matters

| Trades | Interpretation |
|---:|---|
| < 30 | noise |
| 30–100 | directional clue only |
| 100–500 | useful if robust across periods |
| 500+ | statistically more meaningful, still needs cost/regime checks |

## 5. PF interpretation

| PF | Verdict |
|---:|---|
| < 1.0 | losing |
| 1.0–1.1 | marginal / likely killed by costs |
| 1.1–1.3 | real but thin |
| 1.3–1.6 | solid if robust |
| 1.6–2.5 | strong, verify aggressively |
| > 2.5 | suspicious until proven across regimes and data sources |

## 6. ML outputs are bias filters, not prophecy

For financial direction prediction, AUC around 0.52–0.54 can be real but weak. It is not enough for blind entries unless converted into a costed, non-overlapping, risk-managed trading system.

## 7. Current market facts require live data

Notes in this repo are research memory, not live market state. Prices, funding, liquidity, macro conditions, news, and social sentiment must be checked live before analysis.
