from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

def save_alerts_jsonl(alerts: list[dict], out_path: str | Path) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for a in alerts:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    return p
