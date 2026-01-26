from __future__ import annotations
from dataclasses import dataclass
import pandas as pd

@dataclass
class RegimeResult:
    regime: str
    reasons: list[str]

def classify_regime(bench_feat: pd.DataFrame, vix_last: float | None = None) -> RegimeResult:
    # use last available row
    last = bench_feat.dropna().iloc[-1]
    reasons = []
    close = float(last["close"])
    ma50 = float(last["ma50"])
    ma200 = float(last["ma200"])
    # Simple TREND / RISK_OFF decision; RANGE will be determined later via ADX proxy (not implemented)
    close_above_ma200 = close > ma200
    ma50_above_ma200 = ma50 > ma200

    if close_above_ma200 and ma50_above_ma200:
        reasons += ["benchmark_close_above_ma200", "benchmark_ma50_above_ma200"]
        if vix_last is not None and vix_last >= 30:
            return RegimeResult("HIGH_VOL", reasons + ["vix_ge_30"])
        return RegimeResult("TREND", reasons)

    if not close_above_ma200:
        reasons += ["benchmark_close_below_ma200"]
        if vix_last is not None and vix_last >= 30:
            return RegimeResult("HIGH_VOL", reasons + ["vix_ge_30"])
        return RegimeResult("RISK_OFF", reasons)

    # fallback
    return RegimeResult("RANGE", ["fallback_range"])
