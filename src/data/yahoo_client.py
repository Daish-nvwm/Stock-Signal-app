from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pandas as pd
import yfinance as yf


def fetch_stock_candles_yahoo(
    symbol: str,
    interval: str,
    lookback_days: int,
    now_utc: datetime | None = None,
) -> pd.DataFrame:
    """
    Fetch OHLCV candles from Yahoo Finance via yfinance.

    Returns DataFrame with columns:
      timestamp (UTC), open, high, low, close, volume, symbol
    """
    if interval.lower() not in ("1d", "d", "day", "daily"):
        raise ValueError("Yahoo fallback currently supports daily only (1d).")

    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    start = (now_utc - timedelta(days=int(lookback_days * 1.2) + 5)).date().isoformat()
    end = (now_utc + timedelta(days=1)).date().isoformat()

    df = yf.download(
        tickers=symbol,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    # yfinance columns: Open High Low Close Adj Close Volume
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    out = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(df.index, utc=True),
            "open": df["open"].values,
            "high": df["high"].values,
            "low": df["low"].values,
            "close": df["close"].values,
            "volume": df.get("volume", pd.Series([None] * len(df))).values,
            "symbol": [symbol] * len(df),
        }
    )

    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return out