import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass
class EMAATRParams:
    fast: int = 20
    slow: int = 50
    atr_period: int = 14
    atr_mult: float = 2.0
    fee_bps: float = 1.0  # 1 basis point per side (0.01%)

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    # df columns: time, open, high, low, close, volume
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def generate_signals(df: pd.DataFrame, p: EMAATRParams) -> pd.DataFrame:
    out = df.copy()
    out["ema_fast"] = _ema(out["close"], p.fast)
    out["ema_slow"] = _ema(out["close"], p.slow)
    out["atr"] = _atr(out, p.atr_period)

    # Cross signals (long-only)
    cross_up = (out["ema_fast"] > out["ema_slow"]) & (out["ema_fast"].shift(1) <= out["ema_slow"].shift(1))
    cross_dn = (out["ema_fast"] < out["ema_slow"]) & (out["ema_fast"].shift(1) >= out["ema_slow"].shift(1))
    out["entry_signal"] = cross_up
    out["exit_signal"]  = cross_dn
    return out

def backtest(df: pd.DataFrame, p: EMAATRParams) -> dict:
    """
    Long/flat simulation:
    - Enter on ema cross-up at next bar's open.
    - Exit on ema cross-down OR ATR stop hit; exits at next bar's open or at stop price if stop breached.
    - 1 unit notional; equity in % terms. Fees charged on trade entries/exits: fee_bps.
    """
    data = generate_signals(df, p).copy()
    data = data.dropna().reset_index(drop=True)  # drop warmup

    position = 0  # 0=flat, 1=long
    entry_price = np.nan
    stop_price = np.nan
    fees = p.fee_bps / 10000.0

    trades = []
    rets = []  # per-bar return when in position; fees applied on entry/exit bars

    for i in range(1, len(data)):
        row_prev = data.iloc[i-1]
        row = data.iloc[i]

        # Default: carry no return if flat, otherwise pct change close-close
        r = 0.0
        if position == 1:
            # mark-to-market return
            r = (row["close"] / row_prev["close"]) - 1.0

        # Entry logic (on previous bar signal -> execute at current bar open)
        if position == 0 and row_prev["entry_signal"]:
            position = 1
            entry_price = row["open"]
            stop_price = entry_price - p.atr_mult * row["atr"]
            # apply entry fee (reduce equity)
            r -= fees

        # If in position: update stop dynamically (trailing on ATR below close)
        if position == 1:
            dynamic_stop = row["close"] - p.atr_mult * row["atr"]
            if not np.isnan(dynamic_stop):
                stop_price = max(stop_price, dynamic_stop)

            # Exit conditions (prioritize stop if breached within bar; we approximate w/ close)
            exit_now = False
            # Cross-down exits on next bar open
            if row_prev["exit_signal"]:
                exit_now = True
                exit_price = row["open"]
            # ATR stop: if close below stop -> exit at close (pessimistic)
            if not exit_now and (row["close"] < stop_price):
                exit_now = True
                exit_price = row["close"]

            if exit_now:
                # Adjust last return to reflect exit price vs prev close
                # Replace r with (exit/prev_close - 1)
                r = (exit_price / row_prev["close"]) - 1.0
                r -= fees  # exit fee
                trades.append({
                    "time": row["time"],
                    "entry": float(entry_price),
                    "exit": float(exit_price),
                    "pct": float((exit_price / entry_price) - 1.0)
                })
                position = 0
                entry_price = np.nan
                stop_price = np.nan

        rets.append(r)

    # Equity curve
    ret_series = pd.Series(rets, index=data.index[1:])
    equity = (1.0 + ret_series).cumprod()

    # Metrics
    days = (data["time"].iloc[-1] - data["time"].iloc[0]).total_seconds() / 86400.0
    years = max(days / 365.25, 1e-9)
    cagr = equity.iloc[-1] ** (1/years) - 1.0

    # Sharpe (daily ~sqrt(365)); we approximate from bar returns -> annualize by sqrt(365*bars_per_day)
    r_mean = ret_series.mean()
    r_std = ret_series.std(ddof=1)
    # infer bars per day from median difference
    dt = data["time"].diff().dt.total_seconds().median()
    bars_per_day = 86400.0 / dt if dt and dt > 0 else 1.0
    sharpe = (r_mean / (r_std + 1e-12)) * np.sqrt(365.0 * bars_per_day)

    # Max drawdown
    roll_max = equity.cummax()
    dd = equity / roll_max - 1.0
    max_dd = dd.min()

    # Win rate
    wins = sum(1 for t in trades if t["pct"] > 0)
    wr = wins / max(len(trades), 1)

    summary = {
        "bars": int(len(data)),
        "trades": int(len(trades)),
        "win_rate": float(wr),
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_dd),
        "final_equity": float(equity.iloc[-1]),
        "bars_per_day": float(bars_per_day),
        "params": p.__dict__,
    }
    return {"summary": summary, "equity": equity, "ret_series": ret_series, "trades": trades}