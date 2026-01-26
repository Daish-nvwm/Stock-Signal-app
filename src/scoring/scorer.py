from __future__ import annotations

def total_score(components: dict, weights: dict) -> float:
    s = 0.0
    s += components.get("regime_fit", 0) * weights.get("regime_fit", 0)
    s += components.get("trend_momo", 0) * weights.get("trend_momo", 0)
    s += components.get("mean_reversion", 0) * weights.get("mean_reversion", 0)
    s += components.get("volume_flow", 0) * weights.get("volume_flow", 0)
    s += components.get("risk_reward", 0) * weights.get("risk_reward", 0)
    s += components.get("liquidity", 0) * weights.get("liquidity", 0)
    # penalty is negative or 0; add directly
    s += components.get("event_risk_penalty", 0)
    return round(float(s), 2)
