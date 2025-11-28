"""margin_matrix/segment_demand を読み込み、配賦結果をエクスポートするユーティリティ。"""
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
    summarize_allocation,
)


def main() -> None:
    margin_matrix = _read_parquet("margin_matrix.parquet")
    segment_demand = _read_parquet("segment_demand.parquet")
    options = build_option_table(margin_matrix)
    config = CapacityConfig({"A": 528000, "B": 528000}, capacity_utilization_target=0.9)

    allocation_df, plant_remaining, demand_remaining = greedy_allocate(
        options, segment_demand, config
    )
    summaries = summarize_allocation(
        allocation_df, config, segment_demand, plant_remaining, demand_remaining
    )

    output_dir = DATA_DIR
    allocation_df.to_parquet(output_dir / "allocation_results.parquet", index=False)
    summaries["plant"].to_parquet(output_dir / "allocation_plant_summary.parquet", index=False)
    summaries["segment"].to_parquet(output_dir / "allocation_segment_summary.parquet", index=False)

    allocation_df.to_csv(output_dir / "allocation_results.csv", index=False)
    summaries["plant"].to_csv(output_dir / "allocation_plant_summary.csv", index=False)
    summaries["segment"].to_csv(output_dir / "allocation_segment_summary.csv", index=False)

    total_margin = allocation_df["alloc_margin"].sum()
    total_qty = allocation_df["alloc_qty"].sum()
    print(f"allocation rows: {len(allocation_df)}")
    print(f"total qty: {total_qty}")
    print(f"total margin: {total_margin:.2f}")


def _read_parquet(name: str):
    import pandas as pd

    return pd.read_parquet(DATA_DIR / name)


if __name__ == "__main__":
    main()
