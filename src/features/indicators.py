from __future__ import annotations
import numpy as np
import pandas as pd

def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()

def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    # Wilder's smoothing (EMA with alpha=1/n)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_down = down.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    tr = true_range(df["high"], df["low"], df["close"])
    # Wilder's ATR
    return tr.ewm(alpha=1/n, adjust=False).mean()

def bollinger_z(close: pd.Series, n: int = 20) -> pd.Series:
    ma = close.rolling(n, min_periods=n).mean()
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    z = (close - ma) / sd.replace(0, np.nan)
    return z

def returns(close: pd.Series, n: int) -> pd.Series:
    return close.pct_change(n)

def rolling_max(close: pd.Series, n: int) -> pd.Series:
    return close.rolling(n, min_periods=n).max()

def rolling_min(close: pd.Series, n: int) -> pd.Series:
    return close.rolling(n, min_periods=n).min()
