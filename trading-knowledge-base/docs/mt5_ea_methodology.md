# MT5 / EA Methodology

## MT5 is usually stronger evidence than Python

If a Python backtest disagrees with an MT5 backtest for the same EA/period/params, assume Python is wrong until proven otherwise.

## EA-specific checks

- Are model weights in EA identical to trained/exported model?
- Does the EA use closed-bar features (`shift=1`) or forming-bar features (`shift=0`)?
- Does the broker server timezone match the strategy’s session logic?
- Are spreads, commission, swap, and slippage included?
- Are pending orders cancelled during excluded sessions/days?
- Does the EA allow unintended overlapping trades?
- Does SL/TP calculation use correct sign and correct point/pip conversion?
- Are longs and shorts using the right scaler/weights/features?
- Does the Strategy Tester report use real ticks, mixed ticks, or OHLC simulation?

## MT5 report audit

Do not worship the summary table. Reconstruct trades from Deals when possible.

Check:

- gross profit/loss;
- commission/swap;
- spread assumptions;
- order/deal churn;
- loss by hour/day/month;
- loss by parameter set;
- drawdown path;
- whether excluded filters still allowed pending fills.

## Forward test requirement

Backtest success only earns the right to demo forward-test.

Suggested pass criteria:

- 4–12 weeks demo;
- at least 30 trades, preferably 50+;
- PF not collapsing below acceptable threshold;
- drawdown not exceeding 1.5x expected;
- no execution errors;
- trade frequency not collapsing.
