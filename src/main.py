from __future__ import annotations
import argparse
from pathlib import Path

from .common.config_loader import load_config, load_score_maps
from .data.loader import generate_synthetic_bars, load_local_parquet
from .features.feature_set import compute_daily_features
from .regime.classifier import classify_regime
from .universe.filter import passes_universe_filters
from .strategies import trend_breakout, rs_rotation
from .scoring.scorer import total_score
from .alerts.builder import build_alert
from .alerts.storage import save_alerts_jsonl

DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META"]
BENCH = "SPY"

def run_demo(project_root: Path):
    cfg = load_config(project_root)
    maps = load_score_maps(project_root)

    # Generate synthetic benchmark + symbols
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

        # Strategy 1: Trend breakout
        if regime_res.regime in cfg["strategies"]["TREND_BREAKOUT"]["allowed_regimes"]:
            raw = trend_breakout.evaluate(sym, feat, cfg, maps)
            if raw:
                tscore = total_score(raw["scores"]["components"], cfg["scoring"]["weights_global"])
                alerts.append(build_alert(raw, cfg, tscore, regime, data_provenance={"vendor":"synthetic","feed":"demo","bar_interval":"1d"}))

        # Strategy 2: RS rotation (watchlist)
        if regime_res.regime in cfg["strategies"]["RS_ROTATION"]["allowed_regimes"]:
            raw = rs_rotation.evaluate(sym, feat, bench_feat, cfg, maps)
            if raw:
                tscore = total_score(raw["scores"]["components"], cfg["scoring"]["weights_global"])
                alerts.append(build_alert(raw, cfg, tscore, regime, data_provenance={"vendor":"synthetic","feed":"demo","bar_interval":"1d"}))

    # Apply CORE gate and rank
    core_min = cfg["scoring"]["pools"]["CORE"]["min_total"]
    alerts = [a for a in alerts if a["scores"]["total"] >= core_min]
    alerts = sorted(alerts, key=lambda x: x["scores"]["total"], reverse=True)[:cfg["scoring"]["pools"]["CORE"]["max_alerts_per_run"]]

    out = project_root / "data" / "processed" / "alerts_demo.jsonl"
    save_alerts_jsonl(alerts, out)
    print(f"Regime: {regime_res.regime} | Alerts saved to: {out}")
    for a in alerts:
        print(f"- {a['symbol']} {a['setup']['setup_name']} score={a['scores']['total']} action={a['setup']['action']}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Run demo with synthetic data.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    if args.demo:
        run_demo(project_root)
    else:
        print("Starter kit: implement real data loading in src/data/loader.py and add a run mode here.")

if __name__ == "__main__":
    main()
