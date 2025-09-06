# src/data/ohlc_rest.py  (honor 720-candle constraint + CSV import hook)
import httpx, pandas as pd, time
from loguru import logger

BASE = "https://api.kraken.com/0/public/OHLC"

INTERVALS = {
    "1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440
}

async def fetch_ohlc(pair="XBTUSDT", tf="1h"):
    """Fetch up to 720 most recent candles from Kraken OHLC."""
    interval = INTERVALS[tf]
    params = {"pair": pair, "interval": interval}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(BASE, params=params)
        r.raise_for_status()
        data = r.json()["result"]
        sym_key = next(k for k in data.keys() if k not in ("last",))
        rows = data[sym_key]
        # Kraken returns: [time,open,high,low,close,vwap,volume,count]
        df = pd.DataFrame(rows, columns=["time","open","high","low","close","vwap","volume","count"])
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.astype({"open":float,"high":float,"low":float,"close":float,"vwap":float,"volume":float,"count":int})
        logger.info(f"Fetched {len(df)} candles; note API caps at 720 most recent.")
        return df