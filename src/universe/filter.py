from __future__ import annotations
import pandas as pd

def passes_universe_filters(feat: pd.DataFrame, cfg: dict) -> bool:
    last = feat.dropna().iloc[-1]
    min_price = float(cfg["universe_filter"]["min_price"])
    min_dv = float(cfg["universe_filter"]["min_avg_dollar_volume_20d"])
    close = float(last["close"])
    # dollar volume: close * avg volume (20d)
    avg_vol20 = float(last["vol20"])
    dollar_vol = close * avg_vol20
    return (close >= min_price) and (dollar_vol >= min_dv)
