# Crypto AI Trading (Kraken + Groq)

## Status (2025-09-06)
- [x] Groq API ping
- [x] Kraken **Spot** public WS ticker test
- [x] Kraken **Futures Demo** WS (ticker + book) with keepalive + reconnect
- [x] OHLC fetcher (Spot REST, 720-candle cap for context)
- [x] CSV importer for historical OHLCVT (single + **bulk**)
- [x] Parquet **resampler** (build 1h/4h/1d from 1m)
- [ ] Strategy: **EMA crossover + ATR stop** (backtest)
- [ ] Paper engine (sim fills) on top of Futures Demo
- [ ] Live trading + risk controls
- [ ] Docker + 24/7 monitoring
- [ ] Alerts & runbook via Groq

## Quick Start
```bash
source .venv/bin/activate

# Futures Demo WS (continuous stream)
python -m src.app_futures_demo

# List Futures instruments
python -m scripts.list_instruments

# Import all downloaded Kraken CSVs (e.g., XBTUSD_1.csv, XBTUSD_60.csv...) from data/raw/
python -m scripts.bulk_import_csvs

# Or import single CSV
python -m scripts.import_ohlc_csv --path data/raw/XBTUSD_1.csv --symbol XBTUSD --timeframe 1m --out data/db

# Resample higher TFs from 1m Parquet
python -m scripts.resample_parquet --infile data/db/XBTUSD_1m.parquet --symbol XBTUSD --target_tf 1h