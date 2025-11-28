"""感度分析用シナリオユーティリティ。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd


@dataclass
class Scenario:
    """需要・原価・単価の倍率をまとめたシナリオ。"""

    name: str
    demand_factor: float = 1.0
    unit_cost_factor: float = 1.0
    unit_price_factor: float = 1.0


DEFAULT_SCENARIOS: List[Scenario] = [
    Scenario(name="Base"),
    Scenario(name="DemandPlus10", demand_factor=1.10),
    Scenario(name="DemandMinus10", demand_factor=0.90),
    Scenario(name="CostPlus5", unit_cost_factor=1.05),
    Scenario(name="CostMinus5", unit_cost_factor=0.95),
    Scenario(name="PricePlus5", unit_price_factor=1.05),
    Scenario(name="PriceMinus5", unit_price_factor=0.95),
]


def apply_scenario(
    margin_matrix: pd.DataFrame,
    segment_demand: pd.DataFrame,
    scenario: Scenario,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """指定シナリオを適用した margin_matrix / demand を返却。"""
    mm = margin_matrix.copy()
    mm["avg_price"] = mm["avg_price"] * scenario.unit_price_factor
    if "unit_cost_adj" in mm.columns:
        mm["unit_cost_adj"] = mm["unit_cost_adj"] * scenario.unit_cost_factor
    else:
        mm["unit_cost_adj"] = mm["avg_price"] * scenario.unit_cost_factor * 0.5
    mm["unit_margin"] = mm["avg_price"] - mm["unit_cost_adj"]
    mm["margin_rate"] = mm["unit_margin"] / mm["avg_price"].clip(lower=1e-6)

    demand = segment_demand.copy()
    demand["demand_qty"] = demand["demand_qty"] * scenario.demand_factor
    return mm, demand


def list_default_scenarios() -> List[Scenario]:
    """標準シナリオ一覧を返す。"""
    return DEFAULT_SCENARIOS
