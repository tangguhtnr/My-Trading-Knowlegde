"""Trading-session classification based on the entry hour.

The session boundaries are configurable (see ``config.json -> sessions``). The
default mirrors a simple, broker-server-time view of the FX day:

    Asia:    00:00-07:59
    London:  08:00-15:59
    NewYork: 16:00-23:59

IMPORTANT: sessions are derived from whatever timezone the input data is stored
in. We do NOT convert timezones here. The label is only as meaningful as the
timezone of the source data, so document the timezone of your data accordingly.
"""

from __future__ import annotations

from typing import Dict, List


def classify_session(hour: int, sessions: Dict[str, List[int]]) -> str:
    """Map an integer hour [0, 23] to a session label.

    ``sessions`` maps a label to ``[start_hour, end_hour)`` (end exclusive).
    Returns the first matching label, or ``"Unknown"`` if no range matches.
    """
    for label, bounds in sessions.items():
        start, end = bounds[0], bounds[1]
        if start <= hour < end:
            return label
    return "Unknown"
