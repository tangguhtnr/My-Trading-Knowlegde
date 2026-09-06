# Viral Money-Claim Teardown

`validation_protocol.md` audits **your own** backtest, where you have the data and the code.

This document audits **someone else's claim** — a viral X thread, a YouTube video, a Telegram
pitch, a "how I make $500/day" reel — where you have no data, no code, and no incentive
alignment with the person making the claim.

The question is never "does their screenshot look real?". It is:

> Where does the money physically come from, who pays it, and does that survive contact with costs?

## Step 0 — Capture before analysing

Record these before forming an opinion. Links get deleted; memory reconstructs claims charitably.

| Field | Why it matters |
|---|---|
| URL + archived copy / screenshot | The claim must be quotable verbatim later |
| Author handle, account age, follower count | New account + huge numbers = manufactured credibility |
| The exact numeric claim | "$500/day", "10% monthly", "90% win rate" — pin the number down |
| Required capital, stated or implied | Most claims omit this on purpose |
| What is being sold or linked | Course, Discord, signal group, referral/IB link, prop-firm affiliate, token, bot subscription |
| Who could verify it besides the claimant | If nobody, the evidence tier is 0 |

Rule: a claim that only the claimant can verify is not evidence. It is marketing copy.

## Step 1 — The counterparty test

Every dollar you make is a dollar someone else loses or pays. **Name that someone.** If you
cannot name them, you do not understand the mechanism, and you cannot size it.

| Mechanism | Who actually pays you | Sustainable? |
|---|---|---|
| Market making / liquidity provision | Impatient takers crossing the spread | Yes, if you manage inventory and are fast enough |
| Arbitrage (cross-venue, triangular, basis) | Slower participants, fragmented venues | Yes, but hard capacity and latency limits |
| Risk premium (carry, funding, basis, vol selling) | Hedgers and leveraged longs paying to transfer risk | Yes — you are paid for a real risk that eventually hits |
| Informed directional edge | Other speculators | Sometimes; hardest category, decays fastest |
| Fees from other participants | **You and people like you** | Yes for the seller. No for the buyer |
| New deposits paying old depositors | Later victims | No. This is a Ponzi |
| Token emission / points farming | Issuer treasury and future token buyers | Temporary and dilutive; ends by design |

If the honest answer lands in the last three rows, the person telling you about it is not
sharing an edge. **You are the edge.**

## Step 2 — The "why are they telling me" test

Genuine edge is capacity-constrained. Every person you add consumes it. So ask what the seller
gains by adding you.

Legitimate answers exist: the strategy genuinely does not scale-compete (long-horizon
investing), the person is brand-building for a fund or a job, the research is public/academic,
or teaching is an honest second business openly labelled as such.

Illegitimate answer, and by far the most common: **selling has a better risk-adjusted return
than trading**, because the trading edge is thin, unproven, or absent. Course revenue has no
drawdown.

Quick arithmetic to run on any "$X/day on $Y capital" pitch:

- Convert to daily % of capital.
- Compound it over ~252 trading days.
- 1%/day compounds to roughly **+1100% per year**.

Any claim implying that, sustained, is a claim to have beaten every fund in recorded history —
while selling it for the price of a dinner.

## Step 3 — Unit economics before belief

Fill in real numbers. The headline dies here more often than anywhere else.

```text
net edge = gross edge per trade
         − spread
         − commission
         − slippage
         − funding / swap / borrow
         − withdrawal + FX + platform fees
         − tax

income   = net edge × trades per period × capital deployed
capped by: capacity, liquidity, exchange limits, and your own drawdown tolerance
```

Then answer three questions the pitch will not:

1. **What capital does the headline number actually require?** Work backwards from the claim.
2. **What drawdown does the strategy imply?** A number without a drawdown is half a claim.
3. **What happens at 10× the capital?** If the edge dies, the income is bounded — that is a
   side hustle with a ceiling, not a career.

Run `scripts/cost_sensitivity.py` on any return series you are given. Breakeven cost is more
informative than the headline profit factor.

## Step 4 — Evidence tiers for social claims

| Tier | Evidence | Weight |
|---:|---|---|
| 0 | Screenshot or screen recording of a P&L number | None. Trivially faked, demo accounts, cherry-picked |
| 1 | "Verified" badge on a site the claimant pays | Near none |
| 2 | Read-only broker/exchange link (MyFxBook, FXBlue, read-only API key) | Weak-moderate; check deposits, hidden accounts, start date |
| 3 | Full trade history including losing periods, balance curve, and deposit/withdrawal log | Moderate |
| 4 | You reproduce the mechanism yourself on demo with realistic fills | Strong |
| 5 | You run it live with small real money | Decisive |

The survivorship funnel is the reason tier 0 is worthless: run 100 accounts, or post 100
signals, and you will always own one screenshot that looks like genius.

## Step 5 — Check the base rate before the anecdote

An individual success story is only meaningful against the population it came from.

- **Retail CFD / FX:** regulator-mandated disclosures across EU/UK brokers consistently report
  that roughly **74–89% of retail accounts lose money** over a rolling 12-month window. This is
  audited, standardised, and published by the brokers themselves.
- **Prop-firm challenges:** published pass rates cluster around **5–14%**, the share of challenge
  buyers who ever receive a payout is materially smaller again, and traders still withdrawing
  after six months are commonly estimated at **1–3%** of participants. Note the business model:
  challenge fees are revenue, and failure is the modal outcome.

A claim can still be true inside those tails. But a low base rate means the burden of proof sits
at tier 3+, not at "he posted a screenshot".

## Step 6 — Category map

| Pitch | Real mechanism | Money actually flows | Typical verdict |
|---|---|---|---|
| VIP signal group / Discord | Subscription business | Members → seller | `SELLER_ECONOMICS` |
| Course / mentorship | Education business | Students → seller | `SELLER_ECONOMICS` |
| Affiliate / IB "just refer people" | Rebate on referrals' spread and volume | Your recruits' trading costs → you | `SELLER_ECONOMICS` |
| Copy trading leader | Performance fee + per-lot rebate | Copiers → leader; rebates reward overtrading | `SELLER_ECONOMICS` |
| Prop-firm "get funded" | Challenge-fee business with a real payout tail | Failed challenges fund the model | `REAL_BUT_CAPACITY_CAPPED` at best |
| Grid / martingale EA for sale | Software sales; equity curve looks perfect until one gap | Buyers → seller; market → your account, once | `REJECTED` in most forms |
| Funding-rate / cash-and-carry basis | Genuine risk premium | Leveraged longs → you | `REAL_RISK_PREMIUM`; watch depeg, exchange, and liquidation risk |
| Cross-exchange / triangular arb | Genuine but latency- and capacity-bound | Slower flow → you | `REAL_BUT_INACCESSIBLE` for most retail |
| MEV / sniping | Genuine, adversarial, specialist-dominated | Other transactors → you | `REAL_BUT_INACCESSIBLE` |
| Airdrop / points farming | Incentive emissions | Issuer treasury and later buyers → you | `REAL_BUT_CAPACITY_CAPPED`, backward-looking, sybil-filtered |
| Option "income" selling | Selling insurance | Premium buyers → you, until the tail | `REAL_RISK_PREMIUM`, misrepresented as safe |
| Guaranteed daily % "AI bot" / managed account | None | New depositors → old depositors | `SCAM` |

## Step 7 — Red flags

- A return figure with no drawdown, no capital base, and no time period.
- Win rate quoted without average win/loss.
- Profit shown in currency, never in % of capital.
- "Risk-free", "guaranteed", "passive", "no losses" attached to a market activity.
- Urgency: limited seats, price rising tonight, closing the group.
- The proof is a lifestyle, not a track record.
- Deposits go to a personal wallet, an unregulated entity, or an unnamed "partner broker".
- Withdrawals require a new deposit, a fee, or "unlocking" the account.
- The only account history shown starts after the drawdown.
- Referral link is the primary call to action.
- Claim contains no mechanism at all — only results.
- Cannot answer "who is on the other side of this trade?" in one sentence.

## Step 8 — Verdicts

Every teardown ends with exactly one label:

- `SCAM` — mechanism requires new depositors, or the stated mechanism does not exist.
- `SELLER_ECONOMICS` — activity is real, but the reliable money goes to the seller, not the practitioner.
- `REAL_BUT_INACCESSIBLE` — genuine edge requiring capital, latency, licence, or desk you do not have.
- `REAL_BUT_CAPACITY_CAPPED` — works at small size; income has a hard ceiling.
- `REAL_RISK_PREMIUM` — genuine and repeatable; you are paid to hold a risk that will eventually hit. Sizing decides survival.
- `UNPROVEN` — plausible mechanism, insufficient evidence; requires your own tier-4/5 test.
- `INSUFFICIENT_INFO` — not enough disclosed to judge. Do not act.

## Minimum bar before any money moves

1. Mechanism stated in one sentence, including the counterparty.
2. Unit economics survive realistic costs (Step 3).
3. Evidence tier 3 or higher, or your own tier-4 reproduction.
4. Worst-case loss defined and affordable — assume total loss of deployed capital.
5. Position sized so being wrong is boring.

Fail any one of these and the correct action is to do nothing. Doing nothing has a known,
bounded cost.
