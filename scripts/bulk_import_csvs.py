import re, sys, asyncio
from pathlib import Path
from loguru import logger
from src.data.csv_importer import import_ohlcvt_csv

# Map Kraken minute-suffixes to human TF labels
TF_MAP = {
    "1": "1m", "5": "5m", "15": "15m", "30": "30m",
    "60": "1h", "240": "4h", "720": "12h", "1440": "1d"
}
PATTERN = re.compile(r"^([A-Z0-9]+)_(\d+)\.csv$", re.IGNORECASE)

def infer(symbol_fn: str):
    m = PATTERN.match(symbol_fn)
    if not m:
        return None
    sym, mins = m.groups()
    tf = TF_MAP.get(mins)
    if not tf:
        return None
    return sym.upper(), tf

def main(root="data/raw", out="data/db"):
    rootp = Path(root)
    files = sorted([p for p in rootp.glob("*.csv")])
    if not files:
        logger.warning(f"No CSVs found under {rootp.resolve()}")
        sys.exit(0)
    ok = 0
    for f in files:
        guess = infer(f.name)
        if not guess:
            logger.warning(f"Skip (unknown pattern): {f.name}")
            continue
        symbol, tf = guess
        try:
            import_ohlcvt_csv(str(f), symbol, tf, out)
            ok += 1
        except Exception as e:
            logger.exception(f"Failed to import {f.name}: {e}")
    logger.info(f"Imported {ok} files into {out}")

if __name__ == "__main__":
    main()