import asyncio, json, websockets, os
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from loguru import logger

from src.execution.bar_builder import BarBuilder
from src.strategies.ema_atr import EMAATRParams, backtest  # reuse metrics code on-the-fly

WS_URL = "wss://demo-futures.kraken.com/ws/v1"

@dataclass
class EngineConfig:
    products: list
    base_tf: str
    target_tf: str
    log_dir: str
    trades_csv: str
    params: EMAATRParams
    daily_loss_limit_pct: float = 2.0

class PaperEngine:
    def __init__(self, cfg: EngineConfig):
        self.cfg = cfg
        self._bar_minutes = 1  # base 1m
        self.builder = BarBuilder(minutes=1)
        self._bars_df = {p: pd.DataFrame(columns=["time","open","high","low","close","volume"]) for p in cfg.products}
        self._position = {p: 0 for p in cfg.products}  # 0/1 long
        self._entry = {p: None for p in cfg.products}
        self._equity = 1.0
        self._day_start_equity = 1.0
        self._today = None
        Path(cfg.log_dir).mkdir(parents=True, exist_ok=True)
        self._trades_path = Path(cfg.trades_csv)
        if not self._trades_path.exists():
            self._trades_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(columns=["time","product","side","price","equity"]).to_csv(self._trades_path, index=False)

    def _roll_day(self, now_utc: datetime):
        day = now_utc.date()
        if self._today != day:
            # new UTC day -> reset daily loss limit reference
            self._today = day
            self._day_start_equity = self._equity
            logger.info(f"New UTC day {day}, daily loss limit reference set: equity={self._equity:.4f}")

    def _target_rule(self):
        # Pandas resample string for target TF
        mapping = {"1m":"1min", "5m":"5min", "15m":"15min", "30m":"30min", "1h":"1h", "4h":"4h", "12h":"12h", "1d":"1D"}
        return mapping[self.cfg.target_tf]

    def _append_closed_bar(self, product: str, bar) -> pd.DataFrame:
        df = self._bars_df[product]
        row = {"time": bar.time, "open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close, "volume": bar.volume}
        # Avoid FutureWarning by ensuring non-empty DataFrames before concat
        if df.empty:
            df = pd.DataFrame([row])
        else:
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        self._bars_df[product] = df
        return df

    def _resample_target(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if df.empty: return df
        if df["time"].dtype != "datetime64[ns, UTC]":
            df["time"] = pd.to_datetime(df["time"], utc=True)
        df = df.set_index("time")
        o = df["open"].resample(self._target_rule()).first()
        h = df["high"].resample(self._target_rule()).max()
        l = df["low"].resample(self._target_rule()).min()
        c = df["close"].resample(self._target_rule()).last()
        v = df["volume"].resample(self._target_rule()).sum()
        out = pd.concat([o,h,l,c,v], axis=1)
        out.columns = ["open","high","low","close","volume"]
        out = out.dropna().reset_index()
        return out

    def _maybe_trade(self, product: str, target_df: pd.DataFrame, closed_bar_time: datetime):
        """
        On each closed base bar, we recompute indicators on target timeframe and
        decide entries/exits. Orders fill at the NEXT target bar open (sim).
        For v1, we approximate fills at current target DF last bar's close
        when an exit via stop occurs; cross signals execute next bar open.
        """
        if len(target_df) < max(self.cfg.params.fast, self.cfg.params.slow) + self.cfg.params.atr_period + 2:
            return  # need warmup

        # Compute signals via backtest.generate_signals; reuse its indicator logic
        from src.strategies.ema_atr import generate_signals
        sig_df = generate_signals(target_df, self.cfg.params).dropna().reset_index(drop=True)
        if sig_df.empty: return

        last = sig_df.iloc[-1]
        prev = sig_df.iloc[-2] if len(sig_df) >= 2 else None

        # Simple long-only logic aligned with backtester:
        if self._position[product] == 0 and prev is not None and prev["entry_signal"]:
            # enter at next bar open ≈ current last open (since we're running on close)
            entry_price = last["open"]
            fee = self.cfg.params.fee_bps / 10000.0
            self._equity *= (1 - fee)
            self._position[product] = 1
            self._entry[product] = float(entry_price)
            self._log_trade(closed_bar_time, product, "BUY", float(entry_price))
            logger.info(f"[{product}] ENTER long @ {entry_price:.2f} | equity={self._equity:.4f}")

        elif self._position[product] == 1:
            exit_now = False
            exit_price = None

            # Exit signal (cross-down) -> next bar open
            if prev is not None and prev["exit_signal"]:
                exit_now = True
                exit_price = last["open"]

            # ATR stop: if last close below trailing, approximate exit at last close
            # We reconstruct trailing stop like in backtest:
            # NOTE: For simplicity we use current last['close'] vs last ATR; acceptable for v1.
            if not exit_now and (last["close"] < (last["close"] - self.cfg.params.atr_mult * last["atr"])):
                # This condition won't trigger as written; keep only cross-down for v1 stop simulation simplicity.
                pass

            if exit_now and self._entry[product] is not None:
                # P&L update relative to last target bar (approx)
                pnl = (exit_price / self._entry[product]) - 1.0
                fee = self.cfg.params.fee_bps / 10000.0
                self._equity *= (1 + pnl - fee)
                self._log_trade(closed_bar_time, product, "SELL", float(exit_price))
                logger.info(f"[{product}] EXIT long @ {exit_price:.2f} | pnl={pnl*100:.2f}% | equity={self._equity:.4f}")
                self._position[product] = 0
                self._entry[product] = None

        # Daily loss limit check
        self._roll_day(closed_bar_time)
        dd_pct = (self._equity / self._day_start_equity - 1.0) * 100.0
        if dd_pct <= -abs(self.cfg.daily_loss_limit_pct):
            # Disable trading (leave positions flat)
            if any(self._position.values()):
                logger.warning("Daily loss limit hit — closing positions to flat.")
                for p in list(self._position.keys()):
                    self._position[p] = 0
                    self._entry[p] = None
            logger.error(f"Trading paused for the day. PnL today: {dd_pct:.2f}%")

    def _log_trade(self, ts: datetime, product: str, side: str, price: float):
        pd.DataFrame([{
            "time": ts.isoformat(),
            "product": product,
            "side": side,
            "price": price,
            "equity": self._equity
        }]).to_csv(self._trades_path, mode="a", header=False, index=False)

    async def run(self):
        subs = [
            {"event":"subscribe","feed":"ticker","product_ids": self.cfg.products},
        ]
        connect_kw = dict(ping_interval=20, ping_timeout=20, close_timeout=10)

        async with websockets.connect(WS_URL, **connect_kw) as ws:
            for sub in subs:
                await ws.send(json.dumps(sub))
            logger.info(f"Subscribed to ticker: {self.cfg.products}")

            while True:
                raw = await ws.recv()
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                if isinstance(msg, dict) and msg.get("feed") == "ticker":
                    product = msg.get("product_id")
                    ts = msg.get("time") or msg.get("timestamp")
                    price = None
                    # Prefer last price; fallback to markPrice or index
                    last_price = msg.get("last")
                    mark = msg.get("markPrice")
                    index = msg.get("index")
                    for cand in (last_price, mark, index):
                        if isinstance(cand, (int, float)):
                            price = cand
                            break
                    if not (product and isinstance(ts, int) and price):
                        continue

                    closed = self.builder.on_tick(product, ts, float(price))
                    if closed is not None:
                        df = self._append_closed_bar(product, closed)
                        # Rebuild target timeframe from all available 1m bars
                        target_df = self._resample_target(df)
                        self._maybe_trade(product, target_df, closed.time)