import argparse, json, pandas as pd
from loguru import logger
from src.strategies.ema_atr import EMAATRParams, backtest

def main():
    ap = argparse.ArgumentParser(description="EMA crossover + ATR stop backtest")
    ap.add_argument("--parquet", required=True, help="Path to {SYMBOL}_{TF}.parquet")
    ap.add_argument("--fast", type=int, default=20)
    ap.add_argument("--slow", type=int, default=50)
    ap.add_argument("--atr", type=int, default=14)
    ap.add_argument("--atr_mult", type=float, default=2.0)
    ap.add_argument("--fee_bps", type=float, default=1.0)
    args = ap.parse_args()

    df = pd.read_parquet(args.parquet)
    # ensure datetime
    if df["time"].dtype != "datetime64[ns, UTC]":
        df["time"] = pd.to_datetime(df["time"], utc=True)

    p = EMAATRParams(
        fast=args.fast,
        slow=args.slow,
        atr_period=args.atr,
        atr_mult=args.atr_mult,
        fee_bps=args.fee_bps,
    )
    res = backtest(df, p)
    logger.info("Summary:\n" + json.dumps(res["summary"], indent=2))
    # Show last 5 trades
    last_trades = res["trades"][-5:]
    if last_trades:
        # Convert any pandas/NumPy types for JSON (notably Timestamp)
        def _to_jsonable(t):
            t = dict(t)
            if "time" in t:
                # ensure ISO 8601 string
                t["time"] = pd.Timestamp(t["time"]).isoformat()
            return t
        safe_trades = [_to_jsonable(t) for t in last_trades]
        logger.info("Last trades:\n" + json.dumps(safe_trades, indent=2))
    else:
        logger.info("No trades triggered with these parameters.")

if __name__ == "__main__":
    main()