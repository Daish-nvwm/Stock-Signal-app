from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def load_local_parquet(symbol: str, interval: str, project_root: str | Path) -> pd.DataFrame:
    """
    Load local parquet file for real (non-demo) runs.

    Convention:
      {project_root}/data/raw/{symbol}_{interval}.parquet

    Expected columns (at least):
      timestamp, open, high, low, close, volume

    If your parquet uses different column names, map them in this function.
    """
    root = Path(project_root)
    path = root / "data" / "raw" / f"{symbol}_{interval}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"Local parquet not found: {path}\n"
            "Provide the file under data/raw/ OR run demo mode."
        )

    df = pd.read_parquet(path)

    # Optional: enforce common schema/order
    expected = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Parquet missing columns: {missing}. Columns found: {list(df.columns)}")

    return df


def generate_synthetic_bars(symbol: str, n: int = 520, seed: int = 1) -> pd.DataFrame:
    """
    Generate synthetic OHLCV bars with consistent lengths for demo/testing.
    Output columns: timestamp, open, high, low, close, volume
    """
    rng = np.random.default_rng(seed)

    ts = pd.date_range(
        end=pd.Timestamp.utcnow().normalize(),
        periods=n,
        freq="B",
        tz="UTC",
    )

    rets = rng.normal(loc=0.0004, scale=0.02, size=n)
    close = 100.0 * np.exp(np.cumsum(rets))

    open_ = close * (1.0 + rng.normal(0, 0.002, size=n))
    spread = np.abs(rng.normal(0.0, 0.006, size=n))
    high = np.maximum(open_, close) * (1.0 + spread)
    low = np.minimum(open_, close) * (1.0 - spread)

    volume = rng.integers(low=800_000, high=3_500_000, size=n, dtype=np.int64)

    # --- safety: align lengths (prevents pandas ValueError) ---
    lens = {
        "ts": len(ts),
        "open": len(open_),
        "high": len(high),
        "low": len(low),
        "close": len(close),
        "volume": len(volume),
    }
    m = min(lens.values())
    if len(set(lens.values())) != 1:
        print(f"[WARN] synthetic bars length mismatch: {lens} -> trunc to {m}")

    ts = ts[:m]
    open_ = open_[:m]
    high = high[:m]
    low = low[:m]
    close = close[:m]
    volume = volume[:m]

    df = pd.DataFrame(
        {
            "timestamp": ts,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "symbol": [symbol] * m,
        }
    )
    return df