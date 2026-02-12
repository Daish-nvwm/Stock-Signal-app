from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path
from datetime import datetime, timezone

from .common.config_loader import load_config, load_score_maps
from .data.loader import generate_synthetic_bars, load_local_parquet
from .data.finnhub_client import fetch_stock_candles, fetch_quote
from .features.feature_set import compute_daily_features
from .regime.classifier import classify_regime
from .universe.filter import passes_universe_filters
from .strategies import trend_breakout, rs_rotation
from .scoring.scorer import total_score
from .alerts.builder import build_alert
from .alerts.storage import save_alerts_jsonl

DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META"]
BENCH = "SPY"


def _read_watchlist(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Watchlist not found: {path}")
    syms: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip().upper()
        if not s or s.startswith("#"):
            continue
        syms.append(s)

    # de-dup preserving order
    seen = set()
    out = []
    for s in syms:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _lookback_days_for_interval(cfg: dict, interval: str) -> int:
    for b in cfg.get("data", {}).get("bars", []):
        if str(b.get("interval")) == interval:
            return int(b.get("lookback_days", 520))
    return int(cfg.get("data", {}).get("min_history_days", 260))


def run_demo(project_root: Path):
    cfg = load_config(project_root)
    maps = load_score_maps(project_root)

    bench_df = generate_synthetic_bars(BENCH, n=520, seed=1)
    bench_feat = compute_daily_features(bench_df)

    regime_res = classify_regime(bench_feat, vix_last=None)
    regime = {"regime": regime_res.regime, "benchmark": BENCH, "regime_reason": regime_res.reasons}

    alerts = []
    for sym in DEFAULT_SYMBOLS:
        df = generate_synthetic_bars(sym, n=520, seed=3)
        feat = compute_daily_features(df)

        if not passes_universe_filters(feat, cfg):
            continue

        if regime_res.regime in cfg["strategies"]["TREND_BREAKOUT"]["allowed_regimes"]:
            raw = trend_breakout.evaluate(sym, feat, cfg, maps)
            if raw:
                tscore = total_score(raw["scores"]["components"], cfg["scoring"]["weights_global"])
                alerts.append(build_alert(raw, cfg, tscore, regime, data_provenance={"vendor":"synthetic","feed":"demo","bar_interval":"1d"}))

        if regime_res.regime in cfg["strategies"]["RS_ROTATION"]["allowed_regimes"]:
            raw = rs_rotation.evaluate(sym, feat, bench_feat, cfg, maps)
            if raw:
                tscore = total_score(raw["scores"]["components"], cfg["scoring"]["weights_global"])
                alerts.append(build_alert(raw, cfg, tscore, regime, data_provenance={"vendor":"synthetic","feed":"demo","bar_interval":"1d"}))

    core_min = cfg["scoring"]["pools"]["CORE"]["min_total"]
    alerts = [a for a in alerts if a["scores"]["total"] >= core_min]
    alerts = sorted(alerts, key=lambda x: x["scores"]["total"], reverse=True)[:cfg["scoring"]["pools"]["CORE"]["max_alerts_per_run"]]

    out = project_root / "data" / "processed" / "alerts_demo.jsonl"
    save_alerts_jsonl(alerts, out)
    print(f"Regime: {regime_res.regime} | Alerts saved to: {out}")


def run_finnhub(
    project_root: Path,
    interval: str,
    watchlist_path: Path,
    max_symbols: int | None = None,
    sleep_s: float = 1.05,
):
    """Real run using Finnhub REST API."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FINNHUB_API_KEY is not set.\n"
            "- Local: export FINNHUB_API_KEY='...'\n"
            "- GitHub Actions: add Repo Settings -> Secrets -> Actions -> FINNHUB_API_KEY"
        )

    cfg = load_config(project_root)
    maps = load_score_maps(project_root)
    lookback_days = _lookback_days_for_interval(cfg, interval)

    symbols = _read_watchlist(watchlist_path)
    if max_symbols is not None:
        symbols = symbols[:max_symbols]

    report = {
        "meta": {
            "run_ts_utc": datetime.now(timezone.utc).isoformat(),
            "vendor": "finnhub",
            "bar_interval": interval,
            "lookback_days": lookback_days,
            "benchmark": BENCH,
        },
        "universe": {"requested": len(symbols), "loaded": 0},
        "stats": {"scanned": 0, "passed_filters": 0, "alerts_raw": 0, "alerts_final": 0, "errors": 0, "skipped": 0},
        "skipped_items": [],
        "errors": [],
    }

    # Benchmark (SPY)
    bench_df = fetch_stock_candles(BENCH, interval=interval, lookback_days=lookback_days, api_key=api_key)
    time.sleep(sleep_s)
    if bench_df.empty:
        raise RuntimeError("Finnhub returned no benchmark data for SPY. Check API key / plan / symbol.")
    bench_feat = compute_daily_features(bench_df)

    # Optional VIX quote for vol guard (best-effort)
    vix_last = None
    try:
        vix_q = fetch_quote("VIX", api_key=api_key)
        time.sleep(sleep_s)
        if isinstance(vix_q, dict) and vix_q.get("c") is not None:
            vix_last = float(vix_q["c"])
    except Exception:
        vix_last = None

    regime_res = classify_regime(bench_feat, vix_last=vix_last)
    regime = {"regime": regime_res.regime, "benchmark": BENCH, "regime_reason": regime_res.reasons}

    alerts: list[dict] = []
    for sym in symbols:
        report["universe"]["loaded"] += 1
        try:
            df = fetch_stock_candles(sym, interval=interval, lookback_days=lookback_days, api_key=api_key)
            time.sleep(sleep_s)

            if df.empty:
                report["stats"]["skipped"] += 1
                report["skipped_items"].append({"symbol": sym, "reason": "no_data"})
                continue

            feat = compute_daily_features(df)
            report["stats"]["scanned"] += 1

            # Min history guard
            if len(feat.dropna()) < int(cfg["data"]["min_history_days"]):
                report["stats"]["skipped"] += 1
                report["skipped_items"].append({"symbol": sym, "reason": "insufficient_history"})
                continue

            if not passes_universe_filters(feat, cfg):
                report["stats"]["skipped"] += 1
                report["skipped_items"].append({"symbol": sym, "reason": "universe_filter"})
                continue

            report["stats"]["passed_filters"] += 1

            if regime_res.regime in cfg["strategies"]["TREND_BREAKOUT"]["allowed_regimes"]:
                raw = trend_breakout.evaluate(sym, feat, cfg, maps)
                if raw:
                    tscore = total_score(raw["scores"]["components"], cfg["scoring"]["weights_global"])
                    alerts.append(
                        build_alert(
                            raw,
                            cfg,
                            tscore,
                            regime,
                            data_provenance={"vendor": "finnhub", "feed": "rest", "bar_interval": interval},
                        )
                    )

            if regime_res.regime in cfg["strategies"]["RS_ROTATION"]["allowed_regimes"]:
                raw = rs_rotation.evaluate(sym, feat, bench_feat, cfg, maps)
                if raw:
                    tscore = total_score(raw["scores"]["components"], cfg["scoring"]["weights_global"])
                    alerts.append(
                        build_alert(
                            raw,
                            cfg,
                            tscore,
                            regime,
                            data_provenance={"vendor": "finnhub", "feed": "rest", "bar_interval": interval},
                        )
                    )

        except Exception as e:
            report["stats"]["errors"] += 1
            report["errors"].append({"symbol": sym, "stage": "scan", "message": str(e)})

    report["stats"]["alerts_raw"] = len(alerts)

    core_min = cfg["scoring"]["pools"]["CORE"]["min_total"]
    alerts = [a for a in alerts if a["scores"]["total"] >= core_min]
    alerts = sorted(alerts, key=lambda x: x["scores"]["total"], reverse=True)[: cfg["scoring"]["pools"]["CORE"]["max_alerts_per_run"]]
    report["stats"]["alerts_final"] = len(alerts)

    out_alerts = project_root / "data" / "processed" / "alerts.jsonl"
    out_report = project_root / "data" / "processed" / "run_report.json"
    save_alerts_jsonl(alerts, out_alerts)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Regime: {regime_res.regime} (vix={vix_last})")
    print(f"Alerts saved to: {out_alerts} | Report saved to: {out_report}")
    print(
        f"Universe={report['universe']['requested']} "
        f"scanned={report['stats']['scanned']} "
        f"passed_filters={report['stats']['passed_filters']} "
        f"alerts_final={report['stats']['alerts_final']} "
        f"errors={report['stats']['errors']}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Run demo with synthetic data.")
    parser.add_argument("--finnhub", action="store_true", help="Run using Finnhub REST API.")
    parser.add_argument("--interval", default="1d", help="Bar interval: 1d, 60m, 30m, ...")
    parser.add_argument("--watchlist", default="config/watchlist.txt", help="Path to watchlist file")
    parser.add_argument("--max-symbols", type=int, default=None, help="Optional cap to avoid rate limits")
    parser.add_argument("--sleep-s", type=float, default=1.05, help="Sleep between Finnhub API calls (free tier: ~1.05s)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    if args.demo:
        run_demo(project_root)
    elif args.finnhub:
        wl = (project_root / args.watchlist).resolve() if not Path(args.watchlist).is_absolute() else Path(args.watchlist)
        run_finnhub(
            project_root,
            interval=str(args.interval),
            watchlist_path=wl,
            max_symbols=args.max_symbols,
            sleep_s=float(args.sleep_s),
        )
    else:
        print("Starter kit: run demo (--demo) or Finnhub (--finnhub).")


if __name__ == "__main__":
    main()
