from __future__ import annotations
from typing import Any

def piecewise_score(value: float, rules: list[dict[str, Any]]) -> int:
    for r in rules:
        if "lte" in r and value <= float(r["lte"]):
            return int(r["score"])
        if "lt" in r and value < float(r["lt"]):
            return int(r["score"])
        if "gte" in r and value >= float(r["gte"]):
            return int(r["score"])
        if "gt" in r and value > float(r["gt"]):
            return int(r["score"])
    return 0
