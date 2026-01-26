from __future__ import annotations
import uuid
from datetime import datetime, timezone

def build_alert(raw: dict, cfg: dict, total_score: float, regime: dict, data_provenance: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "alert_id": str(uuid.uuid4()),
        "created_at_utc": now,
        "universe": cfg["meta"]["universe"],
        "symbol": raw["symbol"],
        "currency": "USD",
        "data_provenance": data_provenance,
        "market_regime": regime,
        "setup": {
            "setup_name": raw["setup_name"],
            "pool": raw["pool"],
            "direction": raw["direction"],
            "action": raw["action"],
            "time_horizon": "SWING",
        },
        "scores": {
            "total": total_score,
            "components": raw["scores"]["components"]
        },
        "evidence": raw.get("evidence", []),
        "trade_plan": raw.get("trade_plan", {}),
        "compliance_notice": "Informational only; not investment advice."
    }
