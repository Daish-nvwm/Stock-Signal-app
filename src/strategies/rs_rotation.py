from __future__ import annotations
import pandas as pd
from ..scoring.maps import piecewise_score

def evaluate(symbol: str, feat: pd.DataFrame, bench_feat: pd.DataFrame, cfg: dict, score_maps: dict) -> dict | None:
    p = cfg["strategies"]["RS_ROTATION"]["params"]
    last = feat.dropna().iloc[-1]
    bench_last = bench_feat.dropna().iloc[-1]

    # relative strength proxy: 60d return difference
    rs = float(last.get("ret60", 0.0)) - float(bench_last.get("ret60", 0.0))
    # percentile requires cross-sectional ranking; for starter we approximate with mapping on rs itself
    # You will replace this with real percentile ranking across universe.
    # Map: rs >= 0.10 -> high; rs >= 0.05 -> medium; else low.
    if rs >= 0.10:
        rs_pct = 0.95
    elif rs >= 0.05:
        rs_pct = 0.85
    elif rs >= 0.00:
        rs_pct = 0.70
    else:
        rs_pct = 0.50

    rs_score = piecewise_score(rs_pct, score_maps["maps"]["rs_percentile"])

    # trend health
    points = 0
    points += 1 if float(last["close"]) > float(last["ma50"]) else 0
    points += 1 if float(last["ma50"]) > float(last["ma200"]) else 0
    points += 1 if float(last["ma50_slope"]) > 0 else 0
    trend_score = piecewise_score(points, score_maps["maps"]["trend_structure_points"])

    rr = float(p["min_rr"])
    rr_score = piecewise_score(rr, score_maps["maps"]["rr"])

    dollar_vol = float(last["close"]) * float(last["vol20"])
    liq_score = piecewise_score(dollar_vol, score_maps["maps"]["avg_dollar_volume_20d"])

    components = {
        "regime_fit": 90,
        "trend_momo": int(0.6 * rs_score + 0.4 * trend_score),
        "mean_reversion": 0,
        "volume_flow": 50,
        "risk_reward": rr_score,
        "liquidity": liq_score,
        "event_risk_penalty": 0,
    }

    return {
        "symbol": symbol,
        "setup_name": "RS_ROTATION",
        "pool": cfg["strategies"]["RS_ROTATION"]["pool_default"],
        "direction": "LONG",
        "action": "WATCH",  # usually rotation is a watchlist unless price trigger hit
        "scores": {"components": components},
        "evidence": [
            f"RS proxy (ret60 diff vs benchmark): {rs:.3f}",
            f"RS percentile proxy: {rs_pct:.2f}",
            f"Trend health points: {points}/3"
        ],
        "trade_plan": {
            "entry": {"trigger_type": "LIMIT_ENTRY", "entry_zone": [float(last["ma20"]), float(last["ma50"])]},
            "invalidation": {"rule": "CLOSE_BELOW_LEVEL", "price": float(last["ma50"])},
            "stop": {"stop_type": "VOLATILITY_ATR", "atr_multiple": float(p["stop_atr_multiple"])},
            "targets": [{"name": "T1", "rr": rr, "size_pct": 1.0}],
            "position_sizing": {"max_risk_pct_of_equity": cfg["scoring"]["pools"]["CORE"]["max_risk_pct_of_equity"]}
        }
    }
