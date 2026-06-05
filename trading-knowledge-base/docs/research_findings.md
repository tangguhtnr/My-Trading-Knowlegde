# Distilled Research Findings

This file summarizes historical Project AI research. It is not live market analysis.

## XAUUSD / Gold

### Edge 3: Upstreak2 + EMA Bull on H1/H60

Rule shape:

- At least 2 consecutive H1 up bars.
- EMA20 > EMA50 > EMA200.
- Close above EMA20.
- Enter long next H1 open.
- Exit after fixed horizon around 60 hours.

Historical synthesis labeled this the most robust XAU candidate because it survived a long sample better than many alternatives. Caveat: exact metrics require re-reading the original report and re-running with current data before publication as performance marketing.

### XAUMaster v2.0: Asian-range breakout

Structural idea:

- Mark Asia range.
- Trade first London breakout.
- Opposite range edge as stop.
- Range filter to skip dead nights/news spikes.
- Max one trade/day.
- Force close at end of day.

Verdict: promising structural hypothesis, not automatically live-ready.

### Harmonic M5 failure

A prior Harmonic M5 system had attractive headline returns, but investigation found severe bugs:

- profitable stop-loss accounting;
- reversed entry cost sign;
- extreme implicit leverage;
- fractal lookahead leakage;
- overlapping trades without capital constraint;
- misleading/truncated data range.

Verdict: rejected. This is the repo’s canonical example of why “huge backtest return” means nothing without audit.

### Short-timeframe oscillator caution

Many M5 oscillator and confluence signals can show raw directional tendencies, but costs and execution usually destroy them. Treat RSI/MACD/Stochastic/BB/Fibonacci/Gann style results as hypotheses only until costed, walk-forward OOS tests pass.

## BTCUSD ML direction

Historical BTCUSD multi-timeframe ML research found weak directional structure:

- Short horizon: mild mean reversion after sharp down candles.
- Multi-day horizon: trend continuation when price is above medium/long moving averages.
- Best OOS AUCs were roughly in the 0.52–0.54 zone.

Verdict: useful as a bias filter, not a standalone entry engine.

## ETH/BTC pair trading

Historical ETH/BTC spread research found:

- Full-period evidence leaned continuation after large relative moves.
- Some recent OOS windows showed short-lookback daily mean-reversion candidates.
- Reversal vs continuation is regime-dependent, not hardcoded.

All-ML edge mining suggested an ETH/BTC relative-value cluster involving:

- ETH medium trend and volatility;
- BTC long-trend state;
- spread momentum;
- ETH/BTC ratio regime;
- funding and exchange-native futures data as required next-stage inputs.

Verdict: research-promising, not live-ready.

## Universal lesson

The strongest finding is methodological: most edges are weak, regime-dependent, and fragile under costs. The correct workflow is to falsify aggressively before risking money.
