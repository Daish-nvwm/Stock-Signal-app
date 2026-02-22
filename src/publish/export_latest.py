from __future__ import annotations
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input alerts JSONL path")
    ap.add_argument("--output", required=True, help="Output latest.json path")
    ap.add_argument("--max", type=int, default=20, help="Max alerts to publish")
    ap.add_argument("--report", default=None, help="Optional run_report.json to include for diagnostics")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    alerts = read_jsonl(in_path)

<<<<<<< HEAD
    alerts = sorted(alerts, key=lambda a: a.get("scores", {}).get("total", 0), reverse=True)
    alerts = alerts[: args.max]
=======
    alerts = sorted(alerts, key=lambda a: a.get("scores", {}).get("total", 0), reverse=True)[: args.max]
>>>>>>> 8faa76d (Finnhub run + publish report)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "alerts": alerts,
    }

    if args.report:
        rp = Path(args.report)
        if rp.exists():
            try:
                payload["report"] = json.loads(rp.read_text(encoding="utf-8"))
            except Exception:
                payload["report"] = {"error": "failed_to_parse_report"}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
