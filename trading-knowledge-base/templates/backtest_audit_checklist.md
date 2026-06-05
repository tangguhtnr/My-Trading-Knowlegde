# Backtest Audit Checklist

## Data

- [ ] Source identified.
- [ ] Date range verified from actual timestamps, not filename.
- [ ] Timezone known.
- [ ] Duplicates checked.
- [ ] Missing bars/gaps checked.
- [ ] Nonpositive OHLC checked.
- [ ] Volume semantics understood.

## Strategy logic

- [ ] Signal uses only available information.
- [ ] HTF features shifted to completed bars.
- [ ] Entry/exit timing matches platform.
- [ ] No accidental overlapping trades.
- [ ] SL/TP sign and units verified.
- [ ] Position sizing and leverage bounded.

## Costs and execution

- [ ] Spread included.
- [ ] Commission included.
- [ ] Slippage included.
- [ ] Funding/swap included if relevant.
- [ ] Stress cost grid tested.

## Statistics

- [ ] Chronological split.
- [ ] OOS period not used for tuning.
- [ ] Enough trades.
- [ ] Multiple regimes tested.
- [ ] Multiple testing correction considered.
- [ ] Drawdown path inspected.

## Final classification

- [ ] Rejected.
- [ ] Research-only.
- [ ] Bias filter only.
- [ ] Demo forward-test candidate.
- [ ] Small-live candidate after demo pass.
