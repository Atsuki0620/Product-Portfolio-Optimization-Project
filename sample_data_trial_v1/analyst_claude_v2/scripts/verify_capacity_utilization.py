#!/usr/bin/env python3
"""稼働率の検証スクリプト"""
import pandas as pd
from pathlib import Path

# パス設定
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# キャパシティ設定
TOTAL_CAPACITY = 1_056_000  # 拠点A: 528,000 + 拠点B: 528,000
TARGET_UTILIZATION = 0.9

def main():
    # 全年度の販売データを読み込み
    sales_dfs = []
    for year in [2022, 2023, 2024]:
        df = pd.read_csv(RAW_DIR / f'sales_{year}.csv')
        sales_dfs.append(df)

    sales = pd.concat(sales_dfs, ignore_index=True)

    # 総需要を計算
    total_demand = sales['sales_qty'].sum()

    # 稼働率を計算
    utilization_rate = total_demand / TOTAL_CAPACITY

    print("=" * 80)
    print("稼働率検証")
    print("=" * 80)
    print(f"\n総キャパシティ: {TOTAL_CAPACITY:,} 本")
    print(f"総需要: {total_demand:,} 本")
    print(f"\n現在の稼働率: {utilization_rate:.2%}")
    print(f"目標稼働率: {TARGET_UTILIZATION:.0%}")

    if utilization_rate < TARGET_UTILIZATION:
        shortage = int(TOTAL_CAPACITY * TARGET_UTILIZATION - total_demand)
        print(f"\n⚠️  目標未達: {shortage:,} 本不足")
        print(f"    不足率: {(TARGET_UTILIZATION - utilization_rate):.2%}")
    elif utilization_rate > TARGET_UTILIZATION:
        excess = int(total_demand - TOTAL_CAPACITY * TARGET_UTILIZATION)
        print(f"\n✓ 目標超過: {excess:,} 本超過")
        print(f"    超過率: {(utilization_rate - TARGET_UTILIZATION):.2%}")
    else:
        print(f"\n✓ 目標達成")

    # 年度別の需要
    print("\n【年度別需要】")
    yearly_demand = sales.groupby('year')['sales_qty'].sum()
    for year, demand in yearly_demand.items():
        print(f"{year}: {demand:,} 本 ({demand/total_demand:.1%})")

    # 拠点別の需要
    print("\n【拠点別需要】")
    plant_demand = sales.groupby('plant')['sales_qty'].sum()
    for plant, demand in plant_demand.items():
        plant_capacity = TOTAL_CAPACITY / 2
        plant_util = demand / plant_capacity
        print(f"拠点{plant}: {demand:,} 本 (稼働率: {plant_util:.2%})")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
