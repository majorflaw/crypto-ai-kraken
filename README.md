# Crypto AI Trading (Kraken + Groq)

This repo contains a deterministic crypto trading system with:
- Data ingestion (Kraken CSV OHLCVT → Parquet)
- Live market data (Kraken Spot WS, Kraken **Futures Demo** WS)
- Strategy backtests (EMA crossover + ATR stop)
- Next: 24/7 paper engine, then live execution with risk controls

## Status (2025-09-06)
- [x] Groq API ping
- [x] Kraken Spot public WS ticker test
- [x] Kraken **Futures Demo** WS (ticker + book) with keepalive + reconnect
- [x] OHLC fetcher (Spot REST, 720-candle cap context)
- [x] CSV importer for historical OHLCVT (**single + bulk**)
- [x] Parquet resampler (build 1h/4h/1d from 1m)
- [x] Strategy #1: **EMA crossover + ATR stop** (backtest)
- [ ] **Paper engine** (real-time sim fills on Futures Demo)
- [ ] Live trading + risk controls (min size, max DD circuit breaker, per-trade risk)
- [ ] Docker + 24/7 monitoring
- [ ] Alerts & runbook via Groq

## Keys & Config
Create `.env` from `.env.example`:
```
GROQ_API_KEY=...
# Optional Spot keys (not used yet)
KRAKEN_API_KEY=
KRAKEN_API_SECRET=
# Futures (demo or live) – used later when enabling private endpoints
KRAKEN_FUTURES_API_KEY=
KRAKEN_FUTURES_API_SECRET=
```

## Data Workflow
1. Put Kraken CSVs in `data/raw/` (e.g., `XBTUSD_1.csv`, `ETHUSD_1.csv`).
2. Bulk import to Parquet:
   ```
   python -m scripts.bulk_import_csvs
   ```
3. (Optional) Resample higher TFs from 1m:
   ```
   python -m scripts.resample_parquet --infile data/db/XBTUSD_1m.parquet --symbol XBTUSD --target_tf 1h
   ```

## Live Market Data
- **Futures Demo WS** (safe sandbox):
  ```
  python -m src.app_futures_demo
  ```
- **Instrument discovery**:
  ```
  python -m scripts.list_instruments
  ```

## Backtesting
Run EMA+ATR backtest on any Parquet:
```
python -m scripts.backtest --parquet data/db/XBTUSD_1h.parquet   --fast 20 --slow 50 --atr 14 --atr_mult 2.0 --fee_bps 1.0
```
Outputs: trades, CAGR, Sharpe, max DD, etc.

## Roadmap to Paper Trading
- [ ] Paper engine (simulate orders on Futures Demo prices)
- [ ] Strategy improvements: volatility filter, regime filter, ATR position sizing
- [ ] Parameter sweep + metrics report
- [ ] Risk controls: daily loss limit, kill switch, exposure caps
- [ ] Dockerize + logging/alerts
- [ ] Enable **Futures Demo** private API for test orders
