import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

@dataclass
class Bar:
    time: datetime  # start time of bar (UTC)
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0  # we don't have true volume from ticker; left as 0.0

def floor_to_minute(ts_ms: int, minutes: int = 1) -> datetime:
    sec = ts_ms // 1000
    # align to minute boundary
    bucket = (sec // (60 * minutes)) * (60 * minutes)
    return datetime.fromtimestamp(bucket, tz=timezone.utc)

class BarBuilder:
    """
    Builds OHLC bars from tick prices (e.g., ticker markPrice/last).
    Base timeframe = 1m by default.
    """
    def __init__(self, minutes: int = 1):
        self.minutes = minutes
        self._bars: Dict[str, Bar] = {}       # symbol -> current building bar
        self._last_closed: Dict[str, Bar] = {}  # last closed bar per symbol

    def on_tick(self, symbol: str, ts_ms: int, price: float) -> Optional[Bar]:
        """
        Add a tick; if a bar closes, return the CLOSED bar; else return None.
        """
        if not (isinstance(price, (int, float)) and math.isfinite(price)):
            return None
        bucket = floor_to_minute(ts_ms, self.minutes)
        cur = self._bars.get(symbol)

        # New bar starts
        if cur is None or cur.time != bucket:
            # Close previous bar if exists
            if cur is not None:
                self._last_closed[symbol] = cur
            # Start new bar
            newbar = Bar(time=bucket, open=price, high=price, low=price, close=price, volume=0.0)
            self._bars[symbol] = newbar
            # If we closed a bar, return it
            if cur is not None and cur.time != bucket:
                return cur
            return None

        # Update existing bar
        cur.high = max(cur.high, price)
        cur.low = min(cur.low, price)
        cur.close = price
        return None

    def force_close_all(self) -> Dict[str, Bar]:
        """Force close current bars (used during shutdown)."""
        closed = {}
        for sym, bar in list(self._bars.items()):
            closed[sym] = bar
            self._last_closed[sym] = bar
            del self._bars[sym]
        return closed