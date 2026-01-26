from __future__ import annotations
import pandas as pd
from .indicators import sma, atr, rsi, bollinger_z, returns, rolling_max

def compute_daily_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ma20"] = sma(out["close"], 20)
    out["ma50"] = sma(out["close"], 50)
    out["ma200"] = sma(out["close"], 200)
    out["atr14"] = atr(out, 14)
    out["rsi14"] = rsi(out["close"], 14)
    out["z20"] = bollinger_z(out["close"], 20)
    out["ret20"] = returns(out["close"], 20)
    out["ret60"] = returns(out["close"], 60)
    out["high20"] = rolling_max(out["close"], 20)
    out["vol20"] = out["volume"].rolling(20, min_periods=20).mean()
    out["vol_multiple"] = out["volume"] / out["vol20"]
    # simple slope proxy: MA50 today - MA50 20 days ago (normalized by price)
    out["ma50_slope"] = (out["ma50"] - out["ma50"].shift(20)) / out["close"].replace(0, pd.NA)
    return out
