# Viral Claim Teardown: "$250 → $13,000" BTC 5-minute Polymarket bot

Protocol: `docs/viral_claim_teardown.md`
Date of teardown: 2026-09-06
Code audited at commit: `1c9aa81ec64cdf62895b155ed64dc8e88c013102` (last commit 2026-04-11)

## Verdict

`SELLER_ECONOMICS`

The bot's advertised mechanism is not in the code, the mechanism that *is* in the code has
negative expected growth at the stated sizing even when it wins as often as advertised, and the
public repository cannot execute a trade because its order-placing engine is not published. The
reliable money in this artifact is the tutorial the post funnels to.

Secondary findings, held separately so they are not lost behind the headline:

- Even taken entirely at face value, the strategy is `REAL_BUT_CAPACITY_CAPPED` — its own
  liquidity assumptions cap it at small size.
- The specific $250 → $13,000 result is `UNPROVEN` and fully consistent with a lucky tail out
  of a large population of people running the same free bot.

## Claim capture

- Source: X post, 2026-09-05 18:27 UTC (link unreachable from the audit environment; text
  supplied by the requester)
- Claim: $250 deposit became "+$13,000" (≈52×), running a free open-source bot the poster did
  not write, cleaned up in "a couple of hours" with an AI coding assistant
- Stated mechanism: wait until ~2 minutes remain in a 5-minute BTC round; confirm BTC has
  already moved $70–$100; buy the side that agrees with the move at $0.80–$0.99; it settles at
  $1. Small opposite hedge if skew reaches ~95/5
- Stated framing: "like buying a lottery ticket when they have practically already announced
  the result"
- Repository: `github.com/Novals83/5min-btc-polymarket` — an OpenClaw skill for Polymarket BTC
  5-minute Up/Down markets, ~387 stars / ~104 forks
- Being sold: nothing directly. The code is free. The post ends by pointing at a tutorial

## Mechanism

**Actual venue:** Polymarket 5-minute BTC Up/Down event markets. Shares trade between $0 and $1
and pay $1 if right, $0 if wrong. Settlement uses a Chainlink price feed at the window close.

**Stated mechanism, in one sentence:** buy near-certain outcomes just before they resolve.

**Actual mechanism in the code, in one sentence:** poll the Polymarket order book and buy
whichever side's best ask is highest, provided it is at or above $0.70.

**Counterparty:** whoever sells you the contract — other traders on the same book, reading the
same Binance tape. Category: *informed directional edge*, the hardest and fastest-decaying row
in the Step 1 table. You are not being paid a risk premium and you are not arbitraging anything.

### The code does not implement the advertised strategy

This is the central finding. Verified by reading the repository:

| Advertised in the post and README | Present in the code? |
|---|---|
| Wait until ~2 minutes left | Partially — `min_entry_seconds_left: 60`, no targeting of the 120s mark |
| **Confirm BTC moved $70–$100** | **No. There is no BTC price feed of any kind** |
| Trade with the move / follow momentum | **No. It cannot see the move** |
| Check market skew / crowd positioning | **No** |
| Micro-hedge at extreme skew (95/5) | **No. `hedge` appears zero times in the code** |
| Position settles at $1 | **No. It exits 20s before close, selling into the bid** |

There is no reference to Binance, Coinbase, Kraken, Chainlink, OHLC data, candles, or any
variable resembling an impulse or momentum filter anywhere in `scripts/`. The bot has no idea
what Bitcoin is doing. The repository's own config file admits it in a footnote:

> "Current 5m runner uses threshold/side-strength logic; impulse filter integration can be
> extended at strategy layer."

The entry rule in full is: if the UP ask ≥ 0.70 or the DOWN ask ≥ 0.70, buy the more expensive
side. "The key is in the timing" describes a filter that was never written.

### The advertised risk controls are not wired up

`config/btc_5m_profiles.yaml` advertises a full risk framework. The runner has its own hardcoded
`PROFILES` dict and never loads that YAML file. Occurrences in `scripts/`:

| Advertised control | Times referenced in code |
|---|---:|
| `skip_if_spread_gt` (spread guard) | 0 |
| `skip_if_top_ask_notional_usd_lt` (liquidity guard) | 0 |
| `daily_max_loss_pct` | 0 |
| `max_trades_per_day` | 0 |
| `risk_per_trade_pct_equity` | 0 |
| `max_notional_usd` | 0 |
| `hedge` (all keys) | 0 |
| `btc_move_usd_min` | 0 |

Worse than absent: the function that places the order actively sets the permissive values.

```python
env.setdefault('PM_MAX_SPREAD', '1')                 # accept any spread up to 100c
env.setdefault('PM_MIN_TOP_ASK_NOTIONAL_USD', '0')   # accept any depth, including none
```

The spread and liquidity guards presented as safety features are overridden to "off" on the
execution path.

### The repository cannot place a trade

`run_open()` shells out to `src/live/pm_live_trade_runner.py` inside
`pm-hl-conservative-plus-repo` — a separate repository that is not published and not included.
The public repo is a config-and-wrapper layer around a private engine. "I grabbed an open source
project and hit run" is not reproducible from what is public.

## Why is it being shared

The code is free and carries no referral code, wallet address, or affiliate link — checked, and
worth stating plainly in the author's favour.

But the post ends with "the bot was created following the tutorial below." The artifact being
monetised is attention and the tutorial funnel, not the trading. This is the Step 2 pattern in
its cleanest form: a strategy that genuinely returned 52× in weeks would be capacity-constrained
and quiet. The one thing here with reliable, drawdown-free revenue is the content.

## Unit economics

A $1-payout contract bought at price P wins $(1−P) and loses $P. **The breakeven win rate is the
price.** There is no arrangement of these contracts in which you buy a near-certain outcome
cheaply — the near-certainty is what you are paying for.

Reproduce all of the following with `scripts/binary_event_math.py`.

### Is the outcome actually "already decided"?

Residual movement in the last 2 minutes, at BTC ≈ $100,000:

| Annualised BTC vol | 1σ still to come | Fair price after a $70 move | after $85 | after $100 |
|---:|---:|---:|---:|---:|
| 30% | $59 | 0.884 | 0.927 | 0.956 |
| 40% | $78 | 0.815 | 0.862 | 0.900 |
| 50% | $98 | 0.764 | 0.808 | 0.847 |
| 60% | $117 | 0.725 | 0.766 | 0.804 |
| 80% | $156 | 0.673 | 0.707 | 0.739 |

At typical BTC volatility the move the bot waits for is **about one standard deviation of the
noise that has not happened yet**. Nothing is decided. The lottery-ticket analogy is backwards:
if the result were announced the contract would trade at $1.00, and the discount from $1.00 is
precisely the market's paid estimate of the reversal it knows can still happen.

The post says it buys between $0.80 and $0.99. Fair value across realistic regimes is roughly
$0.67–$0.90. **Buying at $0.90 after an $85 move at 50% vol is paying $0.90 for $0.81 — a
negative edge of about 9 cents per contract, on every trade.**

### Growth math, assuming the bot wins exactly as often as the price implies

| | Post's version (90¢, 50% of bankroll) | Code's version (70¢, 15% of equity) |
|---|---|---|
| Breakeven win rate | 90.00% | 70.00% |
| Bankroll on a win | ×1.0556 (+5.56%) | ×1.0643 (+6.43%) |
| Bankroll on a loss | ×0.50 (−50%) | ×0.85 (−15%) |
| Wins needed to undo one loss | 12.8 | 2.6 |
| Expected log growth per trade | **−0.02065** | **−0.00514** |
| Bankroll after 100 trades | **12.7% of what you started with** | **59.8%** |
| Win rate needed to break even at this stake | **92.76%** | **72.29%** |

Both are negative. This is the part the equity curve hides: a strategy priced fairly, winning
exactly as often as advertised, still goes to zero at these bet sizes. It is volatility drag —
betting far past Kelly. To make 50% sizing on 90¢ contracts merely break even you need a true
92.76% win rate, i.e. you must beat the market's own estimate by nearly 3 percentage points,
forever. Even granting a genuine 93% hit rate, Kelly says stake 30%, so the advertised 50% is
about 1.7× Kelly — inside the region where ruin is the mathematical destination, not a risk.

### What the headline claim requires

$250 → $13,000 is 52×.

| Scenario | Consecutive wins needed, zero losses | Probability at the implied win rate |
|---|---:|---|
| 90¢ entries, 50% sizing | 73 | ≈ 0.045% (~1 in 2,200) |
| 70¢ entries, 15% sizing (the shipped config) | 63 | ≈ 1 in 6.7 billion |

Any loss along the way makes it strictly worse, because losses must be recovered before progress
resumes. And with ~387 stars, ~104 forks and a viral tutorial, the population running this bot is
plausibly in the thousands. At roughly 1-in-2,200, a handful of spectacular screenshots is not
surprising — **it is the expected output of the population.** The post is selected for being the
tail. The modal outcome, halving and halving again, does not get posted.

### Costs the post omits

- **It never collects the $1.** `exit_before_sec: 20` closes the position 20 seconds before
  settlement, selling into the bid. On a 70¢ entry with 30¢ of upside, crossing a 2–3¢ spread
  gives back 7–10% of the gross profit, on top of the spread already paid on entry.
- **The stop-loss manufactures losses.** `stop_loss_pct_from_entry: 0.25–0.30` exits at roughly
  52–49¢ from a 70¢ entry. In a thin book minutes from expiry, that is hit by noise on positions
  that would have settled at $1, which raises the effective breakeven above the nominal one.
- **Polymarket taker fees** are small at these extreme prices and are not the thing that kills
  this. The pricing and the sizing are.

## Capacity

The config treats **$30 of top-of-book notional** as adequate depth, and the shipped stake is
$5. Whatever the true depth of a 5-minute BTC book, this is a thin market by construction.

"50% of allocation" on a $13,000 account is $6,500 into that book. You would walk the price to
$1.00 against yourself and destroy the very edge you were trying to capture. **The strategy
cannot scale past small size, which the repository's own liquidity assumptions concede.** Even
in the most generous reading, this is a capped side-income, not a compounding machine.

## Adverse selection

Polymarket's 5-minute markets settle on a Chainlink price at the window close, and researchers
have documented spikes in spot orders immediately before settlement followed by rapid reversals —
i.e. an incentive to nudge spot in the final seconds.

The bot enters in the last ~2 minutes, always on the crowded favourite, at 70–99¢, with no
independent price feed and no view of who is on the other side. That is precisely the position a
capitalised actor would want someone else to be holding. In this configuration the bot is not
capturing the edge; it is the exit liquidity.

## Evidence

- **Tier offered: 0.** A narrated result. No trade log, no equity curve, no account history, no
  losing period, no deposit record.
- **The repository contains no backtest, no results file, and no trade history.** Not a single
  number substantiating any win rate.
- Conspicuously absent: how many rounds were traded, how many were lost, the largest drawdown,
  and whether the $13,000 was ever withdrawn.
- Survivorship risk: maximal, per the population arithmetic above.

## Base rate

Relevant population is not "traders" but "people who ran this specific free bot" — thousands, by
the fork and star count. Nothing about being early, clever, or using an AI assistant to tidy the
code changes the payoff structure of a $0.70 contract.

## Red flags observed

- [x] Return with no drawdown, no loss count, no trade log
- [x] Profit only in dollars, never as a return on capital at risk
- [x] Lifestyle/narrative framing used as proof ("minimised the terminal and got on with my day")
- [x] History starts at the win — no mention of any losing run
- [x] Results without a verifiable mechanism — **the stated mechanism is absent from the code**
- [x] Post terminates in a tutorial funnel
- [ ] Funds to a personal wallet — no, funds stay in the user's own Polymarket account
- [ ] Referral link — none found in the repository, stated in fairness

## Operational risk, separate from the strategy

To run this you must supply a `.env` with Polymarket credentials to an execution engine that is
not published, invoked by a wrapper you found on GitHub, in a lineage with ~104 forks. Anything
in that chain that can sign a transaction can drain the account. This repository's own
`SECURITY.md` exists for exactly this class of mistake. Note also that Polymarket enforces
geographic restrictions; check your jurisdiction before assuming access is even permitted.

## What would change the verdict

Concrete and testable:

1. A trade log of 200+ rounds with timestamps, entry prices, and settlement outcomes, showing a
   win rate above the average price paid — the only measurement that establishes an edge exists.
2. The impulse filter actually implemented and shown to raise the win rate above the contract
   price on out-of-sample rounds.
3. Evidence that fills are achievable at size, i.e. depth at the top of book that does not move
   against a meaningful stake.
4. A published, runnable execution engine, so the claim is reproducible by anyone.

Absent all four, the honest description is: a wrapper that buys favourites at above fair value,
sized far past Kelly, whose one visible outcome is the tail of a large sample.

## Final sentence

Rejected as a way to make money; the mechanism described does not exist in the code, and the
mechanism that does exist loses money at the advertised bet size even when it wins as often as
the market says it will.
