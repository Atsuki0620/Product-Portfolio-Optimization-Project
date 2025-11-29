"""sample_data_trial_v1 analyst_codex データ処理パイプライン.

project_spec.md に基づき、販売・生産・マスタデータの読み込みと集計を
行うための共通関数群を提供する。各関数は notebooks から import して
再利用する想定。
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA_DIR / "raw"
MASTER_DIR = DATA_DIR / "master"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"


def _concat_csv(paths: Iterable[Path]) -> pd.DataFrame:
    """複数CSVを結合し、空の場合は空DataFrameを返す。"""
    frames: List[pd.DataFrame] = []
    for path in paths:
        if path.exists():
            frames.append(pd.read_csv(path))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_sales_data(years: Iterable[int]) -> pd.DataFrame:
    """D1: 販売実績データを年度ごとに読み込み、単一DataFrameに連結する。"""
    files = [RAW_DIR / f"sales_{year}.csv" for year in years]
    df = _concat_csv(files)
    required_cols = {"year", "product_code", "plant", "segment", "sales_qty", "sales_amount"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"販売実績に必要な列が不足: {missing}")
    return df


def load_production_data(years: Iterable[int]) -> pd.DataFrame:
    """D2: 生産実績データを読み込み、単位原価算出に利用する。"""
    files = [RAW_DIR / f"production_{year}.csv" for year in years]
    df = _concat_csv(files)

    # v2対応: cost_amount (新) または production_cost (旧) をサポート
    if "cost_amount" in df.columns and "production_cost" not in df.columns:
        df["production_cost"] = df["cost_amount"]

    required_cols = {"year", "product_code", "plant", "production_qty", "production_cost"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"生産実績に必要な列が不足: {missing}")
    return df


def load_product_master() -> pd.DataFrame:
    """製品マスタを読込。価格帯や許容セグメントを保持。"""
    path = MASTER_DIR / "product_master.csv"
    if not path.exists():
        raise FileNotFoundError("product_master.csv が存在しません")
    return pd.read_csv(path)


def summarize_sales(df_sales: pd.DataFrame) -> pd.DataFrame:
    """年度×製品×拠点×セグメント単位で数量・金額を集計し平均単価を算出。"""
    grouped = (
        df_sales
        .groupby(["year", "product_code", "plant", "segment"], as_index=False)
        .agg({"sales_qty": "sum", "sales_amount": "sum"})
    )
    grouped["avg_price"] = grouped["sales_amount"] / grouped["sales_qty"].clip(lower=1)
    return grouped


def summarize_cost(df_prod: pd.DataFrame) -> pd.DataFrame:
    """年度×製品×拠点で単位原価を計算し、3年平均を求める。"""
    df = df_prod.copy()
    df["unit_cost"] = df["production_cost"] / df["production_qty"].clip(lower=1)
    mean_df = (
        df.groupby(["product_code", "plant"], as_index=False)["unit_cost"]
        .mean()
        .rename(columns={"unit_cost": "unit_cost_avg"})
    )
    return mean_df


def build_margin_matrix(
    sales_summary: pd.DataFrame,
    cost_summary: pd.DataFrame,
    plant_uplift: Dict[str, float] | None = None,
) -> pd.DataFrame:
    """販売と原価サマリを結合し、単位粗利と粗利率を付与する。"""
    uplift = plant_uplift or {"A": 0.0, "B": 0.05}
    merged = sales_summary.merge(cost_summary, on=["product_code", "plant"], how="left")
    merged["unit_cost_adj"] = merged.apply(
        lambda row: row["unit_cost_avg"] * (1 + uplift.get(row["plant"], 0.0)), axis=1
    )
    merged["unit_margin"] = merged["avg_price"] - merged["unit_cost_adj"]
    merged["margin_rate"] = merged["unit_margin"] / merged["avg_price"]
    return merged


def derive_segment_demand(sales_summary: pd.DataFrame) -> pd.DataFrame:
    """セグメント別需要・受注可能数量（過去3年平均）を算出。"""
    demand = (
        sales_summary.groupby(["segment"], as_index=False)["sales_qty"]
        .mean()
        .rename(columns={"sales_qty": "demand_qty"})
    )
    total = demand["demand_qty"].sum()
    demand["demand_share"] = demand["demand_qty"] / total if total else 0
    return demand


def ensure_directories() -> None:
    """データ出力用ディレクトリを事前に作成する。"""
    for path in (DATA_DIR, RAW_DIR, MASTER_DIR, INTERMEDIATE_DIR):
        path.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    # 単体実行時は存在確認のみ行う
    ensure_directories()
    print("データディレクトリを確認しました:", DATA_DIR)
