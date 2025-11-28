"""生成済みデータから baseline/optimal/sensitivity のメトリクスを算出しJSON出力する。"""
from pathlib import Path
import json
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "intermediate"
OUTPUT_PATH = DATA_DIR / "summary_metrics.json"


def main() -> None:
    segment_demand = pd.read_csv(DATA_DIR / "segment_demand.csv")
    allocation_summary = pd.read_csv(DATA_DIR / "allocation_segment_summary.csv")
    allocation_results = pd.read_csv(DATA_DIR / "allocation_results.csv")
    margin_matrix = pd.read_csv(DATA_DIR / "margin_matrix.csv")
    scenario_results = pd.read_csv(DATA_DIR / "scenario_results.csv")

    baseline_total_qty = segment_demand["demand_qty"].sum()
    baseline_segments = (
        segment_demand.assign(share=lambda d: d["demand_qty"] / baseline_total_qty)
        .sort_values("share", ascending=False)
    )

    baseline_total_margin = (margin_matrix["unit_margin"] * margin_matrix["sales_qty"]).sum()

    optimized_total_qty = allocation_results["alloc_qty"].sum()
    optimized_total_margin = allocation_results["alloc_margin"].sum()

    optimized_segments = (
        allocation_summary[["segment", "allocated_qty", "share"]]
        .sort_values("share", ascending=False)
    )

    scenario_sorted = scenario_results.sort_values("total_margin", ascending=False)
    best_scenario = scenario_sorted.iloc[0].to_dict()
    worst_scenario = scenario_sorted.iloc[-1].to_dict()

    summary = {
        "baseline": {
            "total_qty": round(float(baseline_total_qty), 2),
            "total_margin": round(float(baseline_total_margin), 2),
            "top_segments": baseline_segments.head(3).to_dict(orient="records"),
        },
        "optimized": {
            "total_qty": round(float(optimized_total_qty), 2),
            "total_margin": round(float(optimized_total_margin), 2),
            "top_segments": optimized_segments.head(3).to_dict(orient="records"),
        },
        "delta": {
            "qty": round(float(optimized_total_qty - baseline_total_qty), 2),
            "margin": round(float(optimized_total_margin - baseline_total_margin), 2),
        },
        "scenarios": {
            "best": best_scenario,
            "worst": worst_scenario,
        },
    }

    OUTPUT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
