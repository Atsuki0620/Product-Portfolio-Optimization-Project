"""販売・生産データを読み込み、中間集計をCSV/Parquetで書き出す単発スクリプト。"""
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(SCRIPT_DIR))

from data_pipeline import (  # noqa: E402
    ensure_directories,
    load_sales_data,
    load_production_data,
    summarize_sales,
    summarize_cost,
    build_margin_matrix,
    derive_segment_demand,
)


YEARS = [2022, 2023, 2024]
OUTPUT_DIR = PROJECT_ROOT / "data" / "intermediate"


def main() -> None:
    ensure_directories()
    sales_df = load_sales_data(YEARS)
    production_df = load_production_data(YEARS)

    sales_summary = summarize_sales(sales_df)
    cost_summary = summarize_cost(production_df)
    margin_matrix = build_margin_matrix(sales_summary, cost_summary)
    segment_demand = derive_segment_demand(sales_summary)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_outputs("sales_summary", sales_summary)
    _write_outputs("cost_summary", cost_summary)
    _write_outputs("margin_matrix", margin_matrix)
    _write_outputs("segment_demand", segment_demand)

    print("sales_summary rows:", len(sales_summary))
    print("margin_matrix rows:", len(margin_matrix))


def _write_outputs(name: str, df) -> None:
    """ParquetとCSVの双方に保存するユーティリティ。"""
    parquet_path = OUTPUT_DIR / f"{name}.parquet"
    csv_path = OUTPUT_DIR / f"{name}.csv"
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)


if __name__ == "__main__":
    main()
