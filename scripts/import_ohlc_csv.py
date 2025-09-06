import argparse
from src.data.csv_importer import import_ohlcvt_csv

def main():
    ap = argparse.ArgumentParser(description="Import Kraken OHLCVT CSV to Parquet")
    ap.add_argument("--path", required=True, help="Path to downloaded CSV")
    ap.add_argument("--symbol", required=True, help="Symbol label to store, e.g. XBTUSD or BTC/USDT")
    ap.add_argument("--timeframe", required=True, help="e.g. 1m,5m,15m,1h,4h,1d")
    ap.add_argument("--out", default="data/db", help="Output dir (default: data/db)")
    args = ap.parse_args()

    out = import_ohlcvt_csv(args.path, args.symbol, args.timeframe, args.out)
    print(out)

if __name__ == "__main__":
    main()