from __future__ import annotations
import pandas as pd
from ..scoring.maps import piecewise_score

def evaluate(symbol: str, feat: pd.DataFrame, cfg: dict, score_maps: dict) -> dict | None:
    p = cfg["strategies"]["TREND_BREAKOUT"]["params"]
    last = feat.dropna().iloc[-1]

    # simple breakout condition: close >= 20d high (using high20 as rolling max of close in this starter)
    breakout = float(last["close"]) >= float(last["high20"])
    if not breakout and bool(p["require_close_confirm"]):
        return None

    vol_mult = float(last.get("vol_multiple", 0.0))
    vol_score = piecewise_score(vol_mult, score_maps["maps"]["volume_multiple"])

    # trend structure points (0-4)
    points = 0
    points += 1 if float(last["close"]) > float(last["ma50"]) else 0
    points += 1 if float(last["ma50"]) > float(last["ma200"]) else 0
    points += 1 if float(last["ma50_slope"]) > 0 else 0
    points += 1 if breakout else 0
    trend_score = piecewise_score(points, score_maps["maps"]["trend_structure_points"])

    # risk-reward proxy: require min_rr in config; score mapping uses rr
    rr = float(p["min_rr"])
    rr_score = piecewise_score(rr, score_maps["maps"]["rr"])

    # liquidity: based on dollar volume proxy
    dollar_vol = float(last["close"]) * float(last["vol20"])
    liq_score = piecewise_score(dollar_vol, score_maps["maps"]["avg_dollar_volume_20d"])

    # assemble
    components = {
        "regime_fit": 90,  # strategy allowed only in TREND; treat as high
        "trend_momo": trend_score,
        "mean_reversion": 0,
        "volume_flow": vol_score,
        "risk_reward": rr_score,
        "liquidity": liq_score,
        "event_risk_penalty": 0,
    }

    return {
        "symbol": symbol,
        "setup_name": "TREND_BREAKOUT",
        "pool": cfg["strategies"]["TREND_BREAKOUT"]["pool_default"],
        "direction": "LONG",
        "action": "BUY",
        "scores": {"components": components},
        "evidence": [
            f"Breakout condition met (close>=20D high proxy)",
            f"Volume multiple: {vol_mult:.2f}",
            f"Trend structure points: {points}/4"
        ],
        "trade_plan": {
            "entry": {"trigger_type": "CLOSE_CONFIRM", "trigger_price": float(last["close"])},
            "invalidation": {"rule": "CLOSE_BELOW_LEVEL", "price": float(last["high20"])},
            "stop": {"stop_type": "VOLATILITY_ATR", "atr_multiple": float(p["stop_atr_multiple"])},
            "targets": [{"name": "T1", "rr": float(t["rr"]), "size_pct": float(t["size_pct"])} for t in p["targets"]],
            "position_sizing": {"max_risk_pct_of_equity": cfg["scoring"]["pools"]["CORE"]["max_risk_pct_of_equity"]}
        }
    }
