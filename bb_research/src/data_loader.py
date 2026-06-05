"""Input data loading and normalisation.

Supports CSV and XLSX. One file = one (symbol, timeframe). Symbol and timeframe
are inferred from the file name using the convention:

    SYMBOL_TIMEFRAME.ext        e.g.  EURUSD_H1.csv, GBPJPY_M15.xlsx

If the stem has only one token, timeframe is set to ``"NA"``.

Column names are mapped via the config (datetime_column, open_column, ...), so
your raw files can use any header names as long as you map them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from .validation import DataValidationError, validate_ohlc


@dataclass
class LoadedData:
    """A validated, normalised price series ready for backtesting."""

    symbol: str
    timeframe: str
    df: pd.DataFrame  # columns: datetime, open, high, low, close, [spread]
    has_spread: bool
    source_path: Path


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def parse_symbol_timeframe(path: Path) -> tuple[str, str]:
    """Infer (symbol, timeframe) from a file name like ``EURUSD_H1.csv``."""
    stem = path.stem
    parts = stem.split("_")
    if len(parts) >= 2:
        return parts[0].upper(), parts[1].upper()
    return stem.upper(), "NA"


def _read_raw(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise DataValidationError(
        f"Unsupported file extension '{path.suffix}' for {path.name}. "
        f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
    )


def load_file(path: Path, config: dict) -> LoadedData:
    """Load, map, parse, sort and validate a single data file.

    Raises DataValidationError on any structural problem. Does NOT silently
    repair data.
    """
    path = Path(path)
    if not path.exists():
        raise DataValidationError(f"Input file does not exist: {path}")

    symbol, timeframe = parse_symbol_timeframe(path)
    raw = _read_raw(path)

    if raw.shape[0] == 0:
        raise DataValidationError(f"[{symbol}] File {path.name} contains no rows.")

    # Resolve configured column names.
    dt_col = config.get("datetime_column", "datetime")
    o_col = config.get("open_column", "open")
    h_col = config.get("high_column", "high")
    l_col = config.get("low_column", "low")
    c_col = config.get("close_column", "close")
    spread_col = config.get("spread_column", "spread")

    rename_map = {
        dt_col: "datetime",
        o_col: "open",
        h_col: "high",
        l_col: "low",
        c_col: "close",
    }
    missing_src = [src for src in rename_map if src not in raw.columns]
    if missing_src:
        raise DataValidationError(
            f"[{symbol}] {path.name}: configured columns not found: {missing_src}. "
            f"File has columns: {list(raw.columns)}. "
            f"Update the *_column mappings in config.json."
        )

    has_spread = spread_col in raw.columns
    keep = list(rename_map.keys())
    if has_spread:
        keep.append(spread_col)
        rename_map[spread_col] = "spread"

    df = raw[keep].rename(columns=rename_map).copy()

    # Parse datetime strictly. Anything unparseable becomes NaT and is caught
    # by validation (we do not coerce-then-ignore).
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

    # Coerce numeric OHLC; non-numeric -> NaN -> caught by validation.
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if has_spread:
        df["spread"] = pd.to_numeric(df["spread"], errors="coerce")

    # Sort ascending by datetime and reset to a clean RangeIndex so positional
    # indexing in the backtester maps 1:1 to bar number.
    df = df.sort_values("datetime", kind="mergesort").reset_index(drop=True)

    validate_ohlc(df, symbol, int(config.get("bb_period", 20)), has_spread)

    return LoadedData(
        symbol=symbol,
        timeframe=timeframe,
        df=df,
        has_spread=has_spread,
        source_path=path,
    )


def discover_input_files(input_dir: Path) -> list[Path]:
    """Return supported data files in ``input_dir``, sorted for determinism."""
    input_dir = Path(input_dir)
    if not input_dir.exists():
        raise DataValidationError(f"Input directory does not exist: {input_dir}")
    files = [
        p
        for p in sorted(input_dir.iterdir())
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        and not p.name.startswith("~$")  # skip Excel lock files
    ]
    return files


def resolve_pip_size(symbol: str, config: dict) -> float:
    """Resolve pip size for a symbol.

    Order: explicit config override -> JPY heuristic (0.01) -> default 0.0001.
    """
    pip_map = config.get("pip_size", {})
    if symbol in pip_map:
        return float(pip_map[symbol])
    # Heuristic fallback for symbols not listed in config.
    if "JPY" in symbol.upper():
        return 0.01
    return 0.0001


def resolve_spread_pips(symbol: str, config: dict) -> Optional[float]:
    """Resolve the default spread (in pips) for a symbol, if configured."""
    spread_map = config.get("default_spread_pips", {})
    if symbol in spread_map:
        return float(spread_map[symbol])
    return None
