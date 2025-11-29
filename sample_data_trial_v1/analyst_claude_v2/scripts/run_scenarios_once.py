"""標準シナリオを一括実行し、scenario_results.csvを出力する。"""
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "intermediate"
sys.path.append(str(SCRIPT_DIR))

from allocation_utils import (  # noqa: E402
    CapacityConfig,
    build_option_table,
    greedy_allocate,
)
from sensitivity_utils import list_default_scenarios, apply_scenario  # noqa: E402

import pandas as pd


def main() -> None:
    margin_matrix = pd.read_parquet(DATA_DIR / "margin_matrix.parquet")
    segment_demand = pd.read_parquet(DATA_DIR / "segment_demand.parquet")
    scenarios = list_default_scenarios()
    config = CapacityConfig({"A": 528000, "B": 528000}, capacity_utilization_target=0.9)

    records = []
    for scenario in scenarios:
        mm, demand = apply_scenario(margin_matrix, segment_demand, scenario)
        options = build_option_table(mm)
        allocation_df, _, _ = greedy_allocate(options, demand, config)
        total_margin = allocation_df["alloc_margin"].sum() if not allocation_df.empty else 0
        total_qty = allocation_df["alloc_qty"].sum() if not allocation_df.empty else 0
        avg_margin = total_margin / total_qty if total_qty else 0
        records.append(
            {
                "scenario": scenario.name,
                "allocated_qty": round(total_qty, 2),
                "total_margin": round(total_margin, 2),
                "avg_unit_margin": round(avg_margin, 4),
            }
        )

    df = pd.DataFrame(records)
    df.to_csv(DATA_DIR / "scenario_results.csv", index=False)
    print(df)


if __name__ == "__main__":
    main()
