from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


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
