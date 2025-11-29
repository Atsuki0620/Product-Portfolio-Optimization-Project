#!/usr/bin/env python3
"""レポート作成用の分析スクリプト"""
import json
from pathlib import Path
import pandas as pd
import numpy as np

# パス設定
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
MASTER_DIR = DATA_DIR / "master"

# 為替レート（$1 = 150円）
USD_RATE = 150

def load_all_data():
    """全データファイルを読み込み"""
    data = {}

    # 中間データ
    data['scenario_results'] = pd.read_csv(INTERMEDIATE_DIR / 'scenario_results.csv')
    data['allocation_results'] = pd.read_csv(INTERMEDIATE_DIR / 'allocation_results.csv')
    data['segment_demand'] = pd.read_csv(INTERMEDIATE_DIR / 'segment_demand.csv')

    # Raw データ（全年度）
    sales_dfs = []
    production_dfs = []
    for year in [2022, 2023, 2024]:
        sales_df = pd.read_csv(RAW_DIR / f'sales_{year}.csv')
        sales_df['year'] = year
        sales_dfs.append(sales_df)

        prod_df = pd.read_csv(RAW_DIR / f'production_{year}.csv')
        prod_df['year'] = year
        production_dfs.append(prod_df)

    data['sales'] = pd.concat(sales_dfs, ignore_index=True)
    data['production'] = pd.concat(production_dfs, ignore_index=True)

    # マスタデータ
    data['product_master'] = pd.read_csv(MASTER_DIR / 'product_master.csv')
    data['segment_master'] = pd.read_csv(MASTER_DIR / 'segment_master.csv')

    return data

def analyze_utilization_rate(data):
    """稼働率分析"""
    # キャパシティ設定（run_allocation_once.pyから）
    total_capacity = 528000 * 2  # 拠点A + 拠点B

    # 総需要を計算
    total_demand = data['segment_demand']['demand_qty'].sum()

    # 現在の稼働率
    current_utilization = total_demand / total_capacity

    # 90%稼働率達成に必要な需要量
    target_demand = total_capacity * 0.9

    # 製品数
    num_products = len(data['product_master'])

    # 製品あたり平均必要販売数量
    avg_qty_per_product = target_demand / num_products

    return {
        'total_capacity': int(total_capacity),
        'total_demand': int(total_demand),
        'current_utilization_rate': round(current_utilization, 6),
        'current_utilization_pct': round(current_utilization * 100, 4),
        'target_demand_for_90pct': int(target_demand),
        'demand_gap': int(target_demand - total_demand),
        'num_products': num_products,
        'avg_qty_per_product_current': int(total_demand / num_products),
        'avg_qty_per_product_target': int(avg_qty_per_product)
    }

def analyze_profit_drivers(data):
    """利益ドライバー分析"""
    scenario_df = data['scenario_results']

    # ベースラインを特定
    baseline = scenario_df[scenario_df['scenario'] == 'Base'].iloc[0]
    baseline_margin = baseline['total_margin']

    # 各シナリオの影響を計算
    drivers = []
    for _, row in scenario_df.iterrows():
        if row['scenario'] == 'Base':
            continue

        impact = row['total_margin'] - baseline_margin
        impact_pct = (impact / baseline_margin * 100) if baseline_margin != 0 else 0

        drivers.append({
            'scenario': row['scenario'],
            'total_margin': round(row['total_margin'], 2),
            'impact_amount': round(impact, 2),
            'impact_pct': round(impact_pct, 4),
            'allocated_qty': round(row['allocated_qty'], 2)
        })

    # 影響度でソート
    drivers_sorted = sorted(drivers, key=lambda x: abs(x['impact_pct']), reverse=True)

    return {
        'baseline_margin': round(baseline_margin, 2),
        'baseline_qty': round(baseline['allocated_qty'], 2),
        'drivers': drivers_sorted
    }

def aggregate_by_product(data):
    """製品別集計"""
    sales = data['sales']
    production = data['production']

    # 販売集計
    sales_agg = sales.groupby(['product_code', 'year']).agg({
        'sales_qty': 'sum',
        'sales_amount': 'sum'
    }).reset_index()
    sales_agg['type'] = '販売'
    sales_agg = sales_agg.rename(columns={'sales_qty': 'qty', 'sales_amount': 'amount'})

    # 生産集計
    prod_agg = production.groupby(['product_code', 'year']).agg({
        'production_qty': 'sum',
        'production_cost': 'sum'
    }).reset_index()
    prod_agg['type'] = '生産'
    prod_agg = prod_agg.rename(columns={'production_qty': 'qty', 'production_cost': 'amount'})

    # 統合
    combined = pd.concat([sales_agg, prod_agg], ignore_index=True)
    combined['amount_usd'] = combined['amount'] / USD_RATE

    return combined.to_dict('records')

def aggregate_by_plant(data):
    """拠点別集計"""
    sales = data['sales']
    production = data['production']

    # 販売集計
    sales_agg = sales.groupby(['plant', 'year']).agg({
        'sales_qty': 'sum',
        'sales_amount': 'sum'
    }).reset_index()
    sales_agg['type'] = '販売'
    sales_agg = sales_agg.rename(columns={'sales_qty': 'qty', 'sales_amount': 'amount'})

    # 生産集計
    prod_agg = production.groupby(['plant', 'year']).agg({
        'production_qty': 'sum',
        'production_cost': 'sum'
    }).reset_index()
    prod_agg['type'] = '生産'
    prod_agg = prod_agg.rename(columns={'production_qty': 'qty', 'production_cost': 'amount'})

    # 統合
    combined = pd.concat([sales_agg, prod_agg], ignore_index=True)
    combined['amount_usd'] = combined['amount'] / USD_RATE

    return combined.to_dict('records')

def aggregate_by_segment(data):
    """セグメント別集計（販売のみ）"""
    sales = data['sales']

    # 販売集計
    sales_agg = sales.groupby(['segment', 'year']).agg({
        'sales_qty': 'sum',
        'sales_amount': 'sum'
    }).reset_index()
    sales_agg['type'] = '販売'
    sales_agg = sales_agg.rename(columns={'sales_qty': 'qty', 'sales_amount': 'amount'})
    sales_agg['amount_usd'] = sales_agg['amount'] / USD_RATE

    return sales_agg.to_dict('records')

def get_data_samples(data):
    """各データファイルのサンプル（先頭5行）"""
    samples = {}

    # Raw データ
    for year in [2022, 2023, 2024]:
        sales_df = pd.read_csv(RAW_DIR / f'sales_{year}.csv')
        production_df = pd.read_csv(RAW_DIR / f'production_{year}.csv')

        # 金額をUSDに変換
        sales_sample = sales_df.head(5).copy()
        sales_sample['sales_amount_usd'] = sales_sample['sales_amount'] / USD_RATE
        sales_sample['unit_price_usd'] = sales_sample['unit_price'] / USD_RATE

        production_sample = production_df.head(5).copy()
        production_sample['production_cost_usd'] = production_sample['production_cost'] / USD_RATE

        samples[f'sales_{year}'] = sales_sample.to_dict('records')
        samples[f'production_{year}'] = production_sample.to_dict('records')

    # マスタデータ
    product_master = pd.read_csv(MASTER_DIR / 'product_master.csv')
    product_sample = product_master.head(5).copy()
    product_sample['unit_price_min_usd'] = product_sample['unit_price_min'] / USD_RATE
    product_sample['unit_price_max_usd'] = product_sample['unit_price_max'] / USD_RATE
    samples['product_master'] = product_sample.to_dict('records')

    segment_master = pd.read_csv(MASTER_DIR / 'segment_master.csv')
    samples['segment_master'] = segment_master.head(5).to_dict('records')

    return samples

def analyze_segment_share(data):
    """セグメント構成比の検証"""
    segment_master = data['segment_master']
    sales = data['sales']

    # 理論値（マスタから）
    theoretical = segment_master.set_index('segment_code')['demand_share'].to_dict()

    # 実測値（販売データから）
    total_sales = sales['sales_qty'].sum()
    actual = sales.groupby('segment')['sales_qty'].sum() / total_sales

    comparison = []
    for segment in theoretical.keys():
        theo_val = theoretical.get(segment, 0) * 100
        actual_val = actual.get(segment, 0) * 100
        diff = actual_val - theo_val

        comparison.append({
            'segment': segment,
            'theoretical_pct': round(theo_val, 2),
            'actual_pct': round(actual_val, 2),
            'diff_pt': round(diff, 2)
        })

    return comparison

def main():
    """メイン処理"""
    print("データ読み込み中...")
    data = load_all_data()

    print("分析実行中...")
    results = {
        'utilization': analyze_utilization_rate(data),
        'profit_drivers': analyze_profit_drivers(data),
        'aggregates': {
            'by_product': aggregate_by_product(data),
            'by_plant': aggregate_by_plant(data),
            'by_segment': aggregate_by_segment(data)
        },
        'samples': get_data_samples(data),
        'segment_share_comparison': analyze_segment_share(data)
    }

    # 結果を保存
    output_path = INTERMEDIATE_DIR / 'report_analysis.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"分析完了: {output_path}")
    print(f"\n稼働率: {results['utilization']['current_utilization_pct']:.4f}%")
    print(f"需要ギャップ: {results['utilization']['demand_gap']:,} 本")

if __name__ == '__main__':
    main()
