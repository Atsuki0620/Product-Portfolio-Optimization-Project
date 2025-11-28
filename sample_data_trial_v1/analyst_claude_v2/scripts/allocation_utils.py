"""貪欲配賦アルゴリズムと関連ユーティリティ。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd


@dataclass
class CapacityConfig:
    """拠点キャパシティ設定。"""

    plant_capacity: Dict[str, float]
    capacity_utilization_target: float = 0.9
    demand_scale: float = 1.0

    def initial_capacity(self) -> Dict[str, float]:
        return {
            plant: cap * self.capacity_utilization_target
            for plant, cap in self.plant_capacity.items()
        }


def build_option_table(margin_matrix: pd.DataFrame) -> pd.DataFrame:
    """製品×拠点×セグメントの平均単位粗利と配分上限を算出。"""
    grouped = (
        margin_matrix.groupby(["product_code", "plant", "segment"], as_index=False)
        .agg(
            alloc_cap=("sales_qty", "mean"),
            unit_margin=("unit_margin", "mean"),
            margin_rate=("margin_rate", "mean"),
            avg_price=("avg_price", "mean"),
        )
        .fillna(0)
    )
    grouped = grouped[grouped["unit_margin"] > 0].copy()
    grouped["priority_score"] = grouped["unit_margin"] * grouped["margin_rate"].fillna(0)
    return grouped


def greedy_allocate(
    options: pd.DataFrame,
    segment_demand: pd.DataFrame,
    config: CapacityConfig,
) -> Tuple[pd.DataFrame, Dict[str, float], Dict[str, float]]:
    """単位粗利が高い順に拠点キャパと需要を消化する貪欲配賦。"""
    demand_remaining = {
        row["segment"]: row["demand_qty"] * config.demand_scale for _, row in segment_demand.iterrows()
    }
    plant_remaining = config.initial_capacity()
    records: List[Dict[str, float]] = []

    ordered = options.sort_values(
        ["plant", "priority_score", "margin_rate", "avg_price"], ascending=[True, False, False, False]
    )

    for _, row in ordered.iterrows():
        plant = row["plant"]
        segment = row["segment"]
        if plant not in plant_remaining:
            continue
        demand_cap = demand_remaining.get(segment, 0)
        remaining_cap = plant_remaining.get(plant, 0)
        alloc_cap = min(row["alloc_cap"], demand_cap, remaining_cap)
        if alloc_cap <= 0:
            continue
        records.append(
            {
                "product_code": row["product_code"],
                "plant": plant,
                "segment": segment,
                "alloc_qty": alloc_cap,
                "unit_margin": row["unit_margin"],
                "margin_rate": row["margin_rate"],
                "alloc_margin": alloc_cap * row["unit_margin"],
            }
        )
        plant_remaining[plant] = remaining_cap - alloc_cap
        demand_remaining[segment] = demand_cap - alloc_cap

    allocation_df = pd.DataFrame(records)
    return allocation_df, plant_remaining, demand_remaining


def summarize_allocation(
    allocation_df: pd.DataFrame,
    config: CapacityConfig,
    base_segment_demand: pd.DataFrame,
    plant_remaining: Dict[str, float],
    demand_remaining: Dict[str, float],
) -> Dict[str, pd.DataFrame]:
    """拠点別・セグメント別の結果サマリを返却。"""
    summaries: Dict[str, pd.DataFrame] = {}
    if allocation_df.empty:
        summaries["plant"] = pd.DataFrame()
        summaries["segment"] = pd.DataFrame()
        return summaries

    capacity_limit = {
        plant: cap * config.capacity_utilization_target
        for plant, cap in config.plant_capacity.items()
    }
    plant_summary = (
        allocation_df.groupby("plant", as_index=False)[["alloc_qty", "alloc_margin"]]
        .sum()
        .rename(columns={"alloc_qty": "allocated_qty", "alloc_margin": "allocated_margin"})
    )
    plant_summary["capacity_limit"] = plant_summary["plant"].map(capacity_limit)
    plant_summary["remaining_capacity"] = plant_summary["plant"].map(plant_remaining)
    plant_summary["usage_rate"] = (
        plant_summary["allocated_qty"] / plant_summary["capacity_limit"]
    ).round(3)
    summaries["plant"] = plant_summary

    baseline = base_segment_demand.set_index("segment")["demand_qty"].to_dict()
    segment_summary = (
        allocation_df.groupby("segment", as_index=False)[["alloc_qty", "alloc_margin"]]
        .sum()
        .rename(columns={"alloc_qty": "allocated_qty", "alloc_margin": "allocated_margin"})
    )
    total_qty = segment_summary["allocated_qty"].sum()
    segment_summary["share"] = (segment_summary["allocated_qty"] / total_qty).round(3)
    segment_summary["baseline_qty"] = segment_summary["segment"].map(baseline)
    segment_summary["delta_qty"] = (
        segment_summary["allocated_qty"] - segment_summary["baseline_qty"].fillna(0)
    )
    segment_summary["remaining_demand"] = segment_summary["segment"].map(demand_remaining)
    summaries["segment"] = segment_summary
    return summaries
