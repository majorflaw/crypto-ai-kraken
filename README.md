
# Crypto AI Trading (Kraken + Groq)

This README replaces the broken one and adds a **Paper Engine v1** checklist so you can get the paper trading loop to actually produce trades/logs for a 1-week test.

> Status as of 2025-09-06 (Europe/Amsterdam): Repo has live market data listeners and a backtestable EMA+ATR strategy. Paper Engine scaffolding starts but doesn't fully drive orders yet.

---

## Quickstart

```bash
# Clone & enter
git clone https://github.com/majorflaw/crypto-ai-kraken.git
cd crypto-ai-kraken

# (Recommended) virtualenv
python3 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .

# Sanity checks from repo
python -m scripts.list_instruments
python -m src.app_futures_demo   # Futures Demo WS (ticker/book) keepalive + reconnect
```

## Backtest (EMA + ATR)

Run against any 1h Parquet (example XBTUSD):

```bash
python -m scripts.backtest --parquet data/db/XBTUSD_1h.parquet \
  --fast 20 --slow 50 --atr 14 --atr_mult 2.0 --fee_bps 1.0
```

Expected: summary with bars, trades, win_rate, CAGR, Sharpe, max_drawdown, final_equity.

---

## Paper Engine v1 – What’s Needed To See Trades

Right now `python -m scripts.run_paper` logs:

```
Starting Paper Engine | products=['PI_XBTUSD', 'PI_ETHUSD'] target_tf=1h
Subscribed to ticker: ['PI_XBTUSD', 'PI_ETHUSD']
```

…and then appears idle. That’s because the loop is **subscribing to real-time prices** but **isn’t yet wiring those prices into a bar aggregator + strategy + order simulator** that emits trades. To go from “idle” to “simulated fills,” we need the following pieces connected:

### 1) Market Data → Bars (TF aggregation)
- Aggregate tick/mini-tick into OHLCV bars for `target_tf` (e.g., 1m → 1h).
- Decide when a bar “closes” (top-of-hour) and trigger strategy evaluation only on bar close to avoid noise.
- Persist bars in `data/rt/PI_XBTUSD_1h.parquet` (rolling) for debuggability.

### 2) Strategy Runner (EMA crossover + ATR stop)
- On each **closed bar**, compute:
  - EMA_fast, EMA_slow → signal: long/flat/short
  - ATR for stop distance and position sizing (risk-based).
- Emit **desired position** (e.g., +1, 0, -1) and **stop/TP levels**.

### 3) Paper Execution (sim fills & PnL)
- Compare desired position vs current position → create simulated market order(s).
- Fill at next available mid-price (or best bid/ask) from the live feed.
- Track:
  - Positions, average price, realized/unrealized PnL
  - Fees via `fee_bps`
  - ATR-based stop: generate exit orders when hit
- Log every order, fill, PnL delta to `logs/paper/…` (CSV/JSONL).

### 4) Risk Controls & Health
- Max daily loss → cut exposure to 0 and pause.
- Kill switch if heartbeat or WS reconnects exceed threshold.
- Exposure caps per product.

### 5) Visibility
- INFO logs on:
  - Bar closes, signals, orders, fills, equity
- Optional: periodic summary every N minutes
- Metrics file `logs/paper/equity_curve.csv` with timestamp, equity

---

## How to Run a 1-Week Paper Test (No Real Money)

1. **Symbols & TF**
   - Start with: `PI_XBTUSD`, `PI_ETHUSD` on `1h` or `15m` to get more activity.

2. **Launch the engine**
   ```bash
   python -m scripts.run_paper --products PI_XBTUSD PI_ETHUSD --tf 1h
   ```

3. **Verify live feed**
   - Within 1–2 minutes you should see periodic heartbeat or price logs.
   - On each bar close (e.g., at hh:00 for 1h TF), expect a “bar closed” log.
   - After wiring strategy: expect “signal=LONG/FLAT/SHORT” logs, then simulated **orders** and **fills**.

4. **Logs to watch**
   - `logs/paper/paper.log` — lifecycle, warnings, errors
   - `logs/paper/orders.csv` — simulated orders
   - `logs/paper/fills.csv` — simulated fills
   - `logs/paper/equity_curve.csv` — equity over time

5. **Daily checks**
   - Confirm engine process is alive and reconnects as needed.
   - Spot check equity curve; verify no runaway leverage or position flips.

6. **End-of-week report**
   - Plot `equity_curve.csv`
   - Compute summary: trades, win_rate, CAGR (annualized), Sharpe, max DD
   - Compare with backtest performance on same params & timeframe.

> Tip: for faster feedback, you can set TF=15m temporarily. Once validated, switch back to 1h for the week-long run.

---

## Troubleshooting “nothing happens”

- **Bar aggregation not running**  
  If the engine only subscribes to `ticker` but never logs “bar closed,” the aggregator isn’t linked. Make sure the live ticks are piped into a resampler and that **bar-close events** trigger the strategy.

- **Strategy not wired**  
  If bars are closing but you see no signals, ensure EMA/ATR are computed and a decision function emits a **desired position**.

- **Orders not simulated**  
  If you see signals but no fills, check the paper execution module creates orders on position changes and fills at the next tick/mid.

- **1h TF waiting**  
  If you start at, say, 13:04, the first bar close is at 14:00. You should see action then. For rapid testing, use 15m first.

- **Logging level**  
  Run with `LOGLEVEL=INFO` (or DEBUG) so you can see bar/strategy/execution messages.

- **Reconnects**  
  Confirm WS keepalive/reconnect logs. If it silently dies, add a heartbeat log every ~30s and a watchdog timer.

---

## Minimal Folder Structure (suggested)

```
crypto-ai-kraken/
├── configs/
│   ├── paper.toml             # products, tf, fees, risk caps
│   └── strategy_ema_atr.toml  # fast, slow, atr, atr_mult, etc.
├── data/
│   ├── db/                    # historical parquet
│   └── rt/                    # rolling live bars
├── logs/
│   ├── paper/                 # paper engine logs, orders, fills, equity
│   └── ws/                    # websocket raw/heartbeat logs (optional)
├── scripts/
│   ├── run_paper.py
│   ├── backtest.py
│   └── list_instruments.py
└── src/
    ├── data/ingest_*.py
    ├── strategy/ema_atr.py
    ├── execution/paper_engine.py
    └── app_futures_demo.py
```

---

## What’s Left To Implement (Paper Engine v1)

- [ ] Tick→bar aggregator emitting **bar_close** events per product/TF
- [ ] EMA/ATR strategy runner returning **desired position** + stop/TP
- [ ] Position & PnL accounting with **sim fills** and **fees**
- [ ] Risk: daily loss limit, exposure caps, kill switch
- [ ] Logging & CSV outputs (orders, fills, equity)
- [ ] CLI flags: `--products`, `--tf`, `--fee-bps`, `--risk-per-trade`
- [ ] Smoke test on TF=15m for a few hours, then 1h for a full week

---

## Commands (macOS) – When Ready

```bash
# Start paper engine
python -m scripts.run_paper --products PI_XBTUSD PI_ETHUSD --tf 1h

# (Optional) faster feedback
python -m scripts.run_paper --products PI_XBTUSD PI_ETHUSD --tf 15m

# Check logs
tail -f logs/paper/paper.log
```

---

## Roadmap

1. Paper Engine v1 (this checklist)
2. Parameter sweep report (grid over fast/slow/atr/atr_mult)
3. Risk controls hardening (daily loss, kill switch)
4. Docker + 24/7 monitoring
5. Futures Demo private API (test orders)
6. Live (small size) with strict risk limits

---

## Changelog

- 2025-09-06: Added Paper Engine v1 checklist and troubleshooting; clarified logs and week-long test steps.
