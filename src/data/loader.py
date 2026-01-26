from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

def load_local_parquet(symbol: str, interval: str, project_root: str | Path) -> pd.DataFrame | None:
    root = Path(project_root)
    p = root / "data" / "processed" / interval / f"{symbol}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    # expected columns: timestamp, open, high, low, close, volume
    df = df.sort_values("timestamp")
    return df

def generate_synthetic_bars(symbol: str, n: int = 400, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed + hash(symbol) % 1000)
    rets = rng.normal(0, 0.01, size=n)
    close = 100 * np.exp(np.cumsum(rets))
    high = close * (1 + rng.uniform(0, 0.01, size=n))
    low = close * (1 - rng.uniform(0, 0.01, size=n))
    open_ = close * (1 + rng.normal(0, 0.002, size=n))
    vol = rng.integers(1_000_000, 5_000_000, size=n)
    ts = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n, freq="B")
    df = pd.DataFrame({
        "timestamp": ts,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": vol
    })
    return df
