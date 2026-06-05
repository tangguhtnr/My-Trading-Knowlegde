"""Unit tests for Bollinger Band calculation."""

import numpy as np
import pandas as pd

from src.indicators import bollinger_bands


def test_bollinger_bands_known_values():
    # Simple ramp; sample std (ddof=1) of any 3 consecutive integers is 1.0.
    source = pd.Series([1, 2, 3, 4, 5], dtype=float)
    bands = bollinger_bands(source, period=3, deviation=2.0)

    # First two rows have an incomplete window -> NaN (no back-fill).
    assert np.isnan(bands["middle_band"].iloc[0])
    assert np.isnan(bands["middle_band"].iloc[1])

    # idx 2: window [1,2,3] -> mean 2, std 1 -> upper 4, lower 0.
    assert bands["middle_band"].iloc[2] == 2.0
    assert bands["upper_band"].iloc[2] == 4.0
    assert bands["lower_band"].iloc[2] == 0.0
    assert bands["band_width"].iloc[2] == 4.0

    # idx 4: window [3,4,5] -> mean 4, std 1.
    assert bands["middle_band"].iloc[4] == 4.0
    assert bands["upper_band"].iloc[4] == 6.0
    assert bands["lower_band"].iloc[4] == 2.0


def test_bollinger_band_width_pct():
    source = pd.Series([10, 10, 10, 10], dtype=float)
    bands = bollinger_bands(source, period=3, deviation=2.0)
    # Constant series -> std 0 -> bands collapse onto middle, width 0.
    assert bands["band_width"].iloc[2] == 0.0
    assert bands["band_width_pct"].iloc[2] == 0.0


def test_bollinger_invalid_period():
    source = pd.Series([1, 2, 3], dtype=float)
    try:
        bollinger_bands(source, period=1)
        assert False, "expected ValueError for period <= 1"
    except ValueError:
        pass
