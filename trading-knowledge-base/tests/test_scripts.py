from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
sys.path.insert(0, str(ROOT / "scripts"))


def run(*args):
    return subprocess.run([PY, *args], cwd=ROOT, text=True, capture_output=True, check=False)


def test_validate_ohlcv_sample_passes():
    r = run("scripts/validate_ohlcv.py", "examples/sample_ohlcv.csv")
    assert r.returncode == 0, r.stdout + r.stderr
    assert '"ok": true' in r.stdout


def test_cost_sensitivity_runs():
    r = run("scripts/cost_sensitivity.py", "examples/sample_ohlcv.csv", "--return-col", "close", "--price-mode", "close_to_close")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "cost_bps" in r.stdout
    assert "30" in r.stdout


def test_mean_reversion_runs():
    r = run("scripts/mean_reversion_backtest.py", "examples/sample_ohlcv.csv")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "trades:" in r.stdout


def test_binary_event_math_runs():
    r = run("scripts/binary_event_math.py", "--price", "0.90", "--fraction", "0.50", "--target-multiple", "52")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "breakeven win rate      : 90.00%" in r.stdout
    assert "consecutive wins" in r.stdout


def test_binary_event_math_fair_price_is_breakeven():
    """A fair-priced contract has zero edge, so Kelly must be zero."""
    from binary_event_math import kelly_fraction, breakeven_win_rate

    for price in (0.55, 0.70, 0.90, 0.99):
        assert abs(kelly_fraction(price, breakeven_win_rate(price))) < 1e-12


def test_binary_event_math_overbetting_is_negative_even_when_fair():
    """Staking half the bankroll on a fairly priced 90c contract still loses."""
    from binary_event_math import expected_log_growth

    assert expected_log_growth(0.90, 0.50, 0.90) < 0
    assert expected_log_growth(0.70, 0.15, 0.70) < 0


def test_binary_event_math_kelly_caps_the_stake():
    """With a real 3-point edge over a 90c price, Kelly is well under the 50% the pitch uses."""
    from binary_event_math import kelly_fraction

    assert 0 < kelly_fraction(0.90, 0.93) < 0.35


def test_binary_event_math_residual_noise_swamps_the_signal():
    """A $85 move with 2 minutes left is about one sigma, not a decided outcome."""
    from binary_event_math import fair_price_from_move, residual_sigma_usd

    sigma = residual_sigma_usd(100_000, 0.50, 120)
    assert 80 < sigma < 120
    assert fair_price_from_move(85, 100_000, 0.50, 120) < 0.85
