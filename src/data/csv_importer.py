from pathlib import Path
from typing import Optional
import pandas as pd
from loguru import logger

def _standardize_ohlcvt(df: pd.DataFrame) -> pd.DataFrame:
    """
    Accept common Kraken OHLCVT CSV formats and standardize:
    time (UTC), open, high, low, close, volume, trades
    Time is expected in seconds since epoch (int), we convert to UTC datetime.
    """
    cols = {c.lower().strip(): c for c in df.columns}
    # Possible headers from Kraken CSVs: time, open, high, low, close, vwap, volume, trades
    # Some files may name 'trades' as 'count'. We tolerate both.
    rename = {}
    for canonical in ["time", "open", "high", "low", "close", "volume"]:
        if canonical in cols:
            rename[cols[canonical]] = canonical
        elif canonical == "time" and "timestamp" in cols:
            rename[cols["timestamp"]] = "time"
    # trades/count
    if "trades" in cols:
        rename[cols["trades"]] = "trades"
    elif "count" in cols:
        rename[cols["count"]] = "trades"
    # optional vwap
    if "vwap" in cols:
        rename[cols["vwap"]] = "vwap"

    df = df.rename(columns=rename)
    required = ["time", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Found: {df.columns.tolist()}")

    # Convert types
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    float_cols = [c for c in ["open","high","low","close","volume","vwap"] if c in df.columns]
    df[float_cols] = df[float_cols].astype(float)
    if "trades" in df.columns:
        df["trades"] = df["trades"].astype("Int64")
    # Sort and drop duplicates
    df = df.sort_values("time").drop_duplicates(subset=["time"])
    return df[["time","open","high","low","close","volume"] + (["vwap"] if "vwap" in df.columns else []) + (["trades"] if "trades" in df.columns else [])]

def import_ohlcvt_csv(csv_path: str, symbol: str, timeframe: str, out_dir: str = "data/db") -> str:
    """
    Load a Kraken OHLCVT CSV and store as Parquet partitioned by symbol+timeframe.
    Returns the output file path.
    Docs (CSV source): Kraken Support > CSV Data (OHLCVT).  [oai_citation:8‡Kraken Support](https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data?utm_source=chatgpt.com)
    """
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(p)

    # First attempt: autodetect delimiter, assume there IS a header
    df = pd.read_csv(p, sep=None, engine="python")
    try:
        df = _standardize_ohlcvt(df)
    except ValueError:
        # Second attempt: headerless CSV (common for Kraken downloads)
        tmp = pd.read_csv(p, sep=None, engine="python", header=None)
        ncols = tmp.shape[1]
        if ncols == 7:
            # time, open, high, low, close, volume, trades
            tmp.columns = ["time", "open", "high", "low", "close", "volume", "trades"]
        elif ncols == 8:
            # time, open, high, low, close, vwap, volume, trades
            tmp.columns = ["time", "open", "high", "low", "close", "vwap", "volume", "trades"]
        else:
            raise ValueError(
                f"Unexpected column count ({ncols}). "
                "Expected 7 (no VWAP) or 8 (with VWAP). "
                f"First row sample: {tmp.head(1).to_string(index=False)}"
            )
        df = _standardize_ohlcvt(tmp)
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    out_file = out_root / f"{symbol.replace('/','_')}_{timeframe}.parquet"
    df.to_parquet(out_file, index=False)
    logger.info(f"Wrote {len(df):,} rows -> {out_file}")
    return str(out_file)