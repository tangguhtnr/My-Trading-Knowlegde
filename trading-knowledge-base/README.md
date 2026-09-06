# Trading Knowledge Base

A GitHub-ready trading research knowledge base distilled from Project AI / Hermes trading work.

This repo is intentionally **not** a signal-selling repo and **not** a live trading bot. It is a disciplined framework for researching, validating, falsifying, and documenting trading edges across XAUUSD, crypto, MT5 EAs, and ML/time-series experiments.

## Bottom line

Most attractive trading claims fail after proper validation. This repo preserves the useful lessons:

- Backtests are hypotheses, not proof.
- Python simulations are the weakest performance evidence unless calibrated against MT5/real fills.
- Beautiful ML metrics are suspicious until walk-forward, non-overlapping, costed OOS validation passes.
- Short-timeframe XAUUSD technical signals are mostly noise after costs.
- The most useful crypto ML findings so far are weak bias filters, not standalone trade engines.
- ETH/BTC relative-value regimes look more promising than standalone price prophecy, but still need exchange-native futures validation.

## Repository structure

```text
.
├── docs/
│   ├── principles.md                 # non-negotiable research principles
│   ├── validation_protocol.md        # truth hierarchy + anti-leakage checklist
│   ├── research_findings.md          # distilled XAU/BTC/ETH findings
│   ├── strategy_scorecard.md         # how to grade strategies
│   ├── mt5_ea_methodology.md         # MT5/EA workflow and caveats
│   ├── viral_claim_teardown.md       # auditing someone else's money claim
│   ├── teardowns/                    # completed teardowns of specific claims
│   └── glossary.md
├── templates/
│   ├── strategy_research_report.md
│   ├── backtest_audit_checklist.md
│   └── viral_claim_teardown.md
├── scripts/
│   ├── validate_ohlcv.py             # audit OHLCV CSV quality
│   ├── cost_sensitivity.py           # cost drag sensitivity tool
│   ├── binary_event_math.py          # payoff math for $0-$1 event contracts
│   └── mean_reversion_backtest.py    # minimal daily MR example
├── examples/
│   └── sample_ohlcv.csv
├── tests/
│   └── test_scripts.py
├── .github/workflows/ci.yml
├── pyproject.toml
└── LICENSE
```

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q

# Audit an OHLCV CSV
python scripts/validate_ohlcv.py examples/sample_ohlcv.csv --time-col time --ohlcv open high low close volume

# Cost sensitivity from returns CSV
python scripts/cost_sensitivity.py examples/sample_ohlcv.csv --return-col close --price-mode close_to_close

# Payoff math for a binary event contract: breakeven, growth, Kelly, streak needed
python scripts/binary_event_math.py --price 0.90 --fraction 0.50 --target-multiple 52
```

## What this repo is good for

1. Creating a research report before touching live capital.
2. Auditing whether a backtest is probably fake/buggy/overfit.
3. Running basic OHLCV integrity checks.
4. Tearing down a viral “make money doing X” claim before it costs you anything
   (see `docs/teardowns/` for a worked example).
5. Teaching an agent or human the required skepticism for trading research.
6. Standardizing future Project AI strategy reviews.

## What this repo refuses to claim

- No guaranteed returns.
- No live-ready strategy included.
- No current market prediction.
- No hidden proprietary alpha.
- No “PF 3+ therefore safe” nonsense.

## Evidence standard

Use this reliability hierarchy:

1. Live trading P&L.
2. Forward demo test with real broker fills.
3. MT5 backtest with 100% real ticks.
4. MT5 mixed tick-quality backtest.
5. TradingView backtest with realistic costs.
6. Python custom backtest calibrated against MT5.
7. Uncalibrated Python research / ML diagnostics.

Higher layer overrides lower layer. If Python says PF 2.3 and MT5 says PF 1.1, Python is wrong until proven otherwise.

## License

MIT. See `LICENSE`.

## Risk warning

Trading is risky. This repo is educational/research infrastructure, not financial advice. Any live deployment requires independent validation, forward testing, broker-specific execution checks, and sane position sizing.
