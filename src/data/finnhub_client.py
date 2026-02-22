from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time
from typing import Any

import pandas as pd
import requests


FINNHUB_BASE = "https://finnhub.io/api/v1"


@dataclass(frozen=True)
class FinnhubError(Exception):
    message: str
    status_code: int | None = None
    payload: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"FinnhubError(status={self.status_code}): {self.message}"


def _to_unix_seconds(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def interval_to_resolution(interval: str) -> str:
    interval = interval.strip().lower()
    if interval in ("1d", "d", "day", "daily"):
        return "D"
    if interval in ("60m", "60", "1h", "hour", "hourly"):
        return "60"
    if interval in ("30m", "30"):
        return "30"
    if interval in ("15m", "15"):
        return "15"
    if interval in ("5m", "5"):
        return "5"
    if interval in ("1m", "1"):
        return "1"
    raise ValueError(f"Unsupported interval: {interval}")


def _request_json(
    url: str,
    params: dict[str, Any],
    api_key: str,
    timeout_s: int = 25,
    max_retries: int = 4,
) -> dict[str, Any]:
    """
    Finnhub request with clear debugging:
    - Uses token query param (robust in CI).
    - Prints status/text via raised FinnhubError payload.
    """
    api_key = (api_key or "").strip()
    if not api_key:
        raise FinnhubError("missing FINNHUB_API_KEY")

    p = dict(params)
    p["token"] = api_key

    last_err: Exception | None = None

    for i in range(max_retries):
        try:
            r = requests.get(url, params=p, timeout=timeout_s)

            # retryable transient
            if r.status_code in (429, 500, 502, 503, 504):
                last_err = FinnhubError(
                    "transient http error",
                    status_code=r.status_code,
                    payload={"text": r.text[:300]},
                )
                time.sleep(min(10, 2 ** i))
                continue

            # auth errors -> fail fast
            if r.status_code in (401, 403):
                raise FinnhubError(
                    "auth error (check API key / plan)",
                    status_code=r.status_code,
                    payload={"text": r.text[:300]},
                )

            # other 4xx -> show details
            if r.status_code >= 400:
                raise FinnhubError(
                    "http error",
                    status_code=r.status_code,
                    payload={"text": r.text[:300]},
                )

            return r.json()

        except FinnhubError as e:
            last_err = e
            if e.status_code in (401, 403):
                raise
            time.sleep(min(10, 2 ** i))

        except requests.exceptions.RequestException as e:
            last_err = e
            time.sleep(min(10, 2 ** i))

    raise FinnhubError("request failed after retries", payload={"error": str(last_err)})


def fetch_stock_candles(
    symbol: str,
    interval: str,
    lookback_days: int,
    api_key: str,
    now_utc: datetime | None = None,
) -> pd.DataFrame:
    """
    Finnhub /stock/candle -> DataFrame:
    timestamp (UTC), open, high, low, close, volume, symbol
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    start = now_utc - timedelta(days=int(lookback_days * 1.2) + 5)
    params = {
        "symbol": symbol,
        "resolution": interval_to_resolution(interval),
        "from": _to_unix_seconds(start),
        "to": _to_unix_seconds(now_utc),
    }
    url = f"{FINNHUB_BASE}/stock/candle"
    j = _request_json(url, params=params, api_key=api_key)

    if j.get("s") != "ok":
        return pd.DataFrame()

    if not j.get("t"):
        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(j["t"], unit="s", utc=True),
            "open": j.get("o", []),
            "high": j.get("h", []),
            "low": j.get("l", []),
            "close": j.get("c", []),
            "volume": j.get("v", []),
            "symbol": [symbol] * len(j["t"]),
        }
    )

    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df


def fetch_quote(symbol: str, api_key: str) -> dict[str, Any]:
    url = f"{FINNHUB_BASE}/quote"
    params = {"symbol": symbol}
    return _request_json(url, params=params, api_key=api_key)