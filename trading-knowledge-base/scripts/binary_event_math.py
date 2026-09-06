#!/usr/bin/env python3
"""Payoff math for binary event contracts (Polymarket/Kalshi-style $0-$1 shares).

A contract bought at price P pays $1 if right and $0 if wrong, so the breakeven
win rate IS the price. This tool makes the consequences explicit: geometric
growth under a given bet fraction, the Kelly-optimal fraction, and how many
consecutive wins a headline "turned $X into $Y" claim actually requires.

Stdlib only, so it runs anywhere.
"""
from __future__ import annotations
import argparse
import math

SECONDS_PER_YEAR = 365 * 24 * 60 * 60


def breakeven_win_rate(price: float) -> float:
    """A $1-payout contract bought at `price` breaks even at win rate == price."""
    return price


def growth_factors(price: float, fraction: float) -> tuple[float, float]:
    """Bankroll multipliers on a win and on a loss when staking `fraction` of it."""
    if not 0 < price < 1:
        raise ValueError("price must be strictly between 0 and 1")
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    return 1 - fraction + fraction / price, 1 - fraction


def expected_log_growth(price: float, fraction: float, win_rate: float) -> float:
    """Expected log growth per trade. Negative means ruin is the destination."""
    win, loss = growth_factors(price, fraction)
    if loss == 0:
        return -math.inf if win_rate < 1 else math.log(win)
    return win_rate * math.log(win) + (1 - win_rate) * math.log(loss)


def breakeven_fraction_win_rate(price: float, fraction: float) -> float:
    """Win rate needed for zero log growth at this price and bet fraction."""
    win, loss = growth_factors(price, fraction)
    lw, ll = math.log(win), math.log(loss)
    return ll / (ll - lw)


def kelly_fraction(price: float, win_rate: float) -> float:
    """Kelly stake. Negative means the bet is -EV and should not be taken."""
    odds = (1 - price) / price
    return (win_rate * odds - (1 - win_rate)) / odds


def wins_for_target(price: float, fraction: float, multiple: float) -> float:
    """Consecutive wins (zero losses) needed to multiply the bankroll by `multiple`."""
    win, _ = growth_factors(price, fraction)
    return math.log(multiple) / math.log(win)


def wins_to_recover_one_loss(price: float, fraction: float) -> float:
    win, loss = growth_factors(price, fraction)
    return -math.log(loss) / math.log(win)


def fair_price_from_move(move_usd: float, spot: float, vol_annual: float, seconds_left: float) -> float:
    """P(move survives) under a driftless lognormal walk: the market's own estimate.

    Answers "the price already moved $M and there are S seconds left" — which is
    exactly the setup that gets sold as an almost-decided outcome.
    """
    sigma = spot * vol_annual * math.sqrt(seconds_left / SECONDS_PER_YEAR)
    if sigma <= 0:
        return 1.0
    return 0.5 * (1 + math.erf((move_usd / sigma) / math.sqrt(2)))


def residual_sigma_usd(spot: float, vol_annual: float, seconds_left: float) -> float:
    return spot * vol_annual * math.sqrt(seconds_left / SECONDS_PER_YEAR)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--price", type=float, required=True, help="contract price paid, 0-1")
    p.add_argument("--fraction", type=float, required=True, help="fraction of bankroll staked per trade")
    p.add_argument("--win-rate", type=float, default=None, help="true win rate (default: fair, i.e. == price)")
    p.add_argument("--target-multiple", type=float, default=None, help="headline claim, e.g. 52 for $250 to $13000")
    p.add_argument("--trades", type=int, default=100, help="horizon for the growth projection")
    p.add_argument("--spot", type=float, default=None, help="underlying price, for the fair-value check")
    p.add_argument("--move-usd", type=float, default=None, help="move already made, for the fair-value check")
    p.add_argument("--vol-annual", type=float, default=0.50, help="annualized vol of the underlying")
    p.add_argument("--seconds-left", type=float, default=120, help="seconds remaining in the round")
    args = p.parse_args()

    price, frac = args.price, args.fraction
    win_rate = args.win_rate if args.win_rate is not None else breakeven_win_rate(price)
    win, loss = growth_factors(price, frac)

    print(f"contract price          : {price:.4f}")
    print(f"breakeven win rate      : {breakeven_win_rate(price):.2%}  (the price IS the hurdle)")
    print(f"assumed true win rate   : {win_rate:.2%}{'  [fair-priced, no edge]' if args.win_rate is None else ''}")
    print(f"stake fraction          : {frac:.2%}")
    print()
    print(f"bankroll on a win       : x{win:.4f}  ({win - 1:+.2%})")
    print(f"bankroll on a loss      : x{loss:.4f}  ({loss - 1:+.2%})")
    print(f"wins to undo one loss   : {wins_to_recover_one_loss(price, frac):.1f}")
    print()

    elg = expected_log_growth(price, frac, win_rate)
    print(f"expected log growth     : {elg:+.5f} per trade")
    print(f"after {args.trades} trades        : x{math.exp(elg * args.trades):.4f} of starting bankroll")
    print(f"win rate for breakeven  : {breakeven_fraction_win_rate(price, frac):.2%} at this stake fraction")
    kf = kelly_fraction(price, win_rate)
    print(f"kelly fraction          : {kf:.2%}" + (f"  (this bet is {frac / kf:.1f}x Kelly)" if kf > 0 else "  (no edge: do not bet)"))

    if args.target_multiple:
        n = wins_for_target(price, frac, args.target_multiple)
        prob = win_rate ** n
        print()
        print(f"to reach x{args.target_multiple:g} with zero losses:")
        print(f"  consecutive wins      : {n:.0f}")
        print(f"  probability           : {prob:.3%}" + (f"  (~1 in {1 / prob:,.0f})" if prob > 0 else ""))

    if args.spot and args.move_usd:
        sig = residual_sigma_usd(args.spot, args.vol_annual, args.seconds_left)
        fair = fair_price_from_move(args.move_usd, args.spot, args.vol_annual, args.seconds_left)
        print()
        print(f"fair-value check ({args.seconds_left:.0f}s left, {args.vol_annual:.0%} annual vol):")
        print(f"  residual 1-sigma      : ${sig:,.0f} of further movement still to come")
        print(f"  move already made     : ${args.move_usd:,.0f}  ({args.move_usd / sig:.2f} sigma)")
        print(f"  fair contract price   : {fair:.4f}")
        print(f"  edge vs price paid    : {fair - price:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
