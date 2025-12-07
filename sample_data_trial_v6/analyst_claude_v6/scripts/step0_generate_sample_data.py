"""
製品ポートフォリオ最適化フレームワーク v6 - サンプルデータ生成

v6の改善提案を反映したサンプルデータを生成します:
- 代理店モデル（60%単一セグメント、40%複数セグメント）
- 4つ組タプル（製品×拠点×セグメント×顧客）
- 顧客別価格設定（±5-10%変動）
- 1年後の目標設定（market_size_after_1y）
- 1年間の奪取可能率（3年率を3で割る）

作成日: 2025年12月7日
バージョン: 6.0
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Dict, List, Tuple
import random

# 共通ユーティリティのインポート
from optimization_common_v6 import (
    load_config,
    save_csv_with_validation,
    display_dataframe_summary
)


# =============================================================================
# 定数定義
# =============================================================================

# 顧客セグメントマッピング（実装計画書のQ6-3より）
CUSTOMER_SEGMENT_MAPPING = {
    'Customer_A': ['industrial'],                           # 単一セグメント
    'Customer_B': ['electronics'],                          # 単一セグメント
    'Customer_C': ['oil_gas'],                             # 単一セグメント
    'Customer_D': ['others'],                              # 単一セグメント
    'Customer_E': ['industrial'],                           # 単一セグメント
    'Customer_F': ['electronics'],                          # 単一セグメント
    'Customer_G': ['industrial', 'electronics'],            # 2セグメント
    'Customer_H': ['oil_gas', 'others'],                   # 2セグメント
    'Customer_I': ['electronics', 'oil_gas'],              # 2セグメント
    'Customer_J': ['industrial', 'electronics', 'oil_gas'], # 3セグメント
}

# セグメント別市場データ（実装計画書のQ2-1, Q4-1より）
SEGMENT_DATA = {
    'industrial': {
        'segment_name': 'Industrial',
        'market_size': 1_008_000,
        'cagr': -0.01,  # -1%
        'current_share': 0.20,
        'strategy_type': 'withdrawal'
    },
    'electronics': {
        'segment_name': 'Electronics',
        'market_size': 630_000,
        'cagr': 0.03,  # +3%
        'current_share': 0.20,
        'strategy_type': 'maintain'
    },
    'oil_gas': {
        'segment_name': 'Oil & Gas',
        'market_size': 756_000,
        'cagr': 0.05,  # +5%
        'current_share': 0.20,
        'strategy_type': 'aggressive_expansion'
    },
    'others': {
        'segment_name': 'Others',
        'market_size': 126_000,
        'cagr': -0.02,  # -2%
        'current_share': 0.20,
        'strategy_type': 'reduction'
    }
}

# 競合データ（実装計画書のQ4-2, Q7より）
COMPETITOR_DATA = {
    'industrial': [
        {'competitor_code': 'CompetitorA', 'competitor_share': 0.356, 'competitor_strength': 'strong'},
        {'competitor_code': 'CompetitorB', 'competitor_share': 0.178, 'competitor_strength': 'moderate'},
        {'competitor_code': 'CompetitorC', 'competitor_share': 0.089, 'competitor_strength': 'weak'},
        {'competitor_code': 'CompetitorD', 'competitor_share': 0.178, 'competitor_strength': 'moderate'}
    ],
    'electronics': [
        {'competitor_code': 'CompetitorA', 'competitor_share': 0.400, 'competitor_strength': 'strong'},
        {'competitor_code': 'CompetitorB', 'competitor_share': 0.200, 'competitor_strength': 'moderate'},
        {'competitor_code': 'CompetitorC', 'competitor_share': 0.100, 'competitor_strength': 'weak'},
        {'competitor_code': 'CompetitorD', 'competitor_share': 0.100, 'competitor_strength': 'weak'}
    ],
    'oil_gas': [
        {'competitor_code': 'CompetitorA', 'competitor_share': 0.300, 'competitor_strength': 'strong'},
        {'competitor_code': 'CompetitorB', 'competitor_share': 0.250, 'competitor_strength': 'moderate'},
        {'competitor_code': 'CompetitorC', 'competitor_share': 0.150, 'competitor_strength': 'weak'},
        {'competitor_code': 'CompetitorD', 'competitor_share': 0.100, 'competitor_strength': 'weak'}
    ],
    'others': [
        {'competitor_code': 'CompetitorA', 'competitor_share': 0.350, 'competitor_strength': 'strong'},
        {'competitor_code': 'CompetitorB', 'competitor_share': 0.200, 'competitor_strength': 'moderate'},
        {'competitor_code': 'CompetitorC', 'competitor_share': 0.150, 'competitor_strength': 'weak'},
        {'competitor_code': 'CompetitorD', 'competitor_share': 0.100, 'competitor_strength': 'weak'}
    ]
}

# 1年間の奪取可能率（実装計画書のQ7より、3年率を3で割る）
ACQUISITION_RATES = {
    'strong': {'lower': 0.000, 'upper': 0.010},    # 3年: 0-3% → 1年: 0-1%
    'moderate': {'lower': 0.007, 'upper': 0.017},  # 3年: 2-5% → 1年: 0.7-1.7%
    'weak': {'lower': 0.017, 'upper': 0.033}       # 3年: 5-10% → 1年: 1.7-3.3%
}


# =============================================================================
# データ生成関数
# =============================================================================

def generate_base_product_data(config: Dict) -> pd.DataFrame:
    """
    製品×拠点×セグメントの基本データを生成します。

    Parameters
    ----------
    config : Dict
        設定ファイルの内容

    Returns
    -------
    pd.DataFrame
        基本データ（160行: 20製品 × 2拠点 × 4セグメント）
    """
    products = [f"P{str(i).zfill(3)}" for i in range(1, 21)]  # P001~P020
    plants = ['A', 'B']
    segments = ['industrial', 'electronics', 'oil_gas', 'others']

    data = []
    np.random.seed(42)  # 再現性のためシード固定

    for product_code in products:
        # 製品番号から特性を決定（一貫性のため）
        product_num = int(product_code[1:])

        # コストバンド（低コスト: P001-P010, 高コスト: P011-P020）
        cost_band = 'low' if product_num <= 10 else 'high'
        base_cost = 50000 if cost_band == 'low' else 80000

        for plant_code in plants:
            for segment_code in segments:
                # 拠点別のコスト調整（拠点Aは-5%、拠点Bは+5%）
                plant_cost_multiplier = 0.95 if plant_code == 'A' else 1.05

                # セグメント別の価格調整
                segment_price_multipliers = {
                    'industrial': 1.0,
                    'electronics': 1.2,
                    'oil_gas': 1.3,
                    'others': 0.9
                }
                segment_multiplier = segment_price_multipliers[segment_code]

                # 基本単価とコストを計算
                base_unit_cost = base_cost * plant_cost_multiplier
                base_unit_price = base_unit_cost * 1.2 * segment_multiplier  # 基本粗利率20%

                # ランダム変動（±3%）
                cost_variation = np.random.uniform(0.97, 1.03)
                price_variation = np.random.uniform(0.97, 1.03)

                unit_cost = round(base_unit_cost * cost_variation, 2)
                unit_price = round(base_unit_price * price_variation, 2)
                unit_profit = round(unit_price - unit_cost, 2)
                margin_rate = round(unit_profit / unit_price, 3)

                # 基本販売数量（拠点・セグメントによって異なる）
                base_qty = np.random.randint(1000, 5000)

                data.append({
                    'product_code': product_code,
                    'product_name': f'Product_{product_code[1:]}',
                    'cost_band': cost_band,
                    'plant_code': plant_code,
                    'segment_code': segment_code,
                    'base_unit_cost': unit_cost,
                    'base_unit_price': unit_price,
                    'base_unit_profit': unit_profit,
                    'base_margin_rate': margin_rate,
                    'base_sales_volume': base_qty
                })

    return pd.DataFrame(data)


def generate_product_master_with_customers(
    base_data: pd.DataFrame,
    config: Dict
) -> pd.DataFrame:
    """
    代理店モデルを適用し、4つ組タプルの製品マスタを生成します。

    Parameters
    ----------
    base_data : pd.DataFrame
        基本データ（製品×拠点×セグメント）
    config : Dict
        設定ファイルの内容

    Returns
    -------
    pd.DataFrame
        製品マスタ（製品×拠点×セグメント×顧客）
    """
    data = []
    np.random.seed(42)

    for idx, row in base_data.iterrows():
        product_code = row['product_code']
        plant_code = row['plant_code']
        segment_code = row['segment_code']

        # このセグメントで取引可能な顧客を取得
        available_customers = [
            customer for customer, segments in CUSTOMER_SEGMENT_MAPPING.items()
            if segment_code in segments
        ]

        # ランダムに1-3顧客を選択
        min_customers = config['distributor_model']['customers_per_combination']['min']
        max_customers = config['distributor_model']['customers_per_combination']['max']
        num_customers = np.random.randint(min_customers, min(max_customers + 1, len(available_customers) + 1))
        selected_customers = np.random.choice(available_customers, size=num_customers, replace=False)

        for customer_code in selected_customers:
            # 顧客別の価格・コスト変動（±5-10%）
            price_multiplier = np.random.uniform(
                config['distributor_model']['price_variation']['min_multiplier'],
                config['distributor_model']['price_variation']['max_multiplier']
            )
            cost_multiplier = np.random.uniform(
                config['distributor_model']['cost_variation']['min_multiplier'],
                config['distributor_model']['cost_variation']['max_multiplier']
            )

            unit_cost = round(row['base_unit_cost'] * cost_multiplier, 2)
            unit_price = round(row['base_unit_price'] * price_multiplier, 2)

            # 負の粗利を防ぐため、unit_price < unit_costの場合は価格を調整
            min_margin_rate = 0.05  # 最低5%の粗利率を確保
            if unit_price < unit_cost * (1 + min_margin_rate):
                unit_price = round(unit_cost * (1 + min_margin_rate), 2)

            unit_profit = round(unit_price - unit_cost, 2)
            margin_rate = round(unit_profit / unit_price, 3) if unit_price > 0 else 0.0

            # 販売数量の配分（選択された顧客数で分割）
            sales_volume = round(row['base_sales_volume'] / num_customers)

            data.append({
                'product_code': product_code,
                'product_name': row['product_name'],
                'cost_band': row['cost_band'],
                'plant_code': plant_code,
                'segment_code': segment_code,
                'customer_code': customer_code,
                'unit_cost': unit_cost,
                'unit_price': unit_price,
                'unit_profit': unit_profit,
                'margin_rate': margin_rate,
                'sales_volume': sales_volume
            })

    return pd.DataFrame(data)


def generate_sales_2024(product_master: pd.DataFrame) -> pd.DataFrame:
    """
    2024年販売実績データを生成します。

    Parameters
    ----------
    product_master : pd.DataFrame
        製品マスタ

    Returns
    -------
    pd.DataFrame
        2024年販売実績データ
    """
    sales_data = product_master.copy()
    sales_data.insert(0, 'year', 2024)

    # カラムの順序を調整
    columns = [
        'year',
        'product_code',
        'product_name',
        'cost_band',
        'plant_code',
        'segment_code',
        'customer_code',
        'sales_volume',
        'unit_price',
        'unit_cost',
        'margin_rate'
    ]

    return sales_data[columns]


def generate_market_master() -> pd.DataFrame:
    """
    市場マスタを生成します（1年後の予測）。

    Returns
    -------
    pd.DataFrame
        市場マスタ
    """
    data = []

    for segment_code, segment_info in SEGMENT_DATA.items():
        market_size = segment_info['market_size']
        cagr = segment_info['cagr']
        market_size_after_1y = round(market_size * (1 + cagr))

        data.append({
            'segment_code': segment_code,
            'market_size': market_size,
            'market_size_after_1y': market_size_after_1y,
            'cagr': cagr,
            'current_share': segment_info['current_share'],
            'strategy_type': segment_info['strategy_type']
        })

    return pd.DataFrame(data)


def generate_competitor_master() -> pd.DataFrame:
    """
    競合マスタを生成します（1年間の奪取可能率）。

    Returns
    -------
    pd.DataFrame
        競合マスタ
    """
    data = []

    for segment_code, competitors in COMPETITOR_DATA.items():
        for comp in competitors:
            strength = comp['competitor_strength']
            acquisition_rate = ACQUISITION_RATES[strength]

            data.append({
                'segment_code': segment_code,
                'competitor_code': comp['competitor_code'],
                'competitor_share': comp['competitor_share'],
                'competitor_strength': strength,
                'acquisition_rate_lower': acquisition_rate['lower'],
                'acquisition_rate_upper': acquisition_rate['upper']
            })

    return pd.DataFrame(data)


def generate_segment_master() -> pd.DataFrame:
    """
    セグメントマスタを生成します。

    Returns
    -------
    pd.DataFrame
        セグメントマスタ
    """
    data = []

    for segment_code, segment_info in SEGMENT_DATA.items():
        data.append({
            'segment_code': segment_code,
            'segment_name': segment_info['segment_name'],
            'strategy_type': segment_info['strategy_type']
        })

    return pd.DataFrame(data)


# =============================================================================
# メイン処理
# =============================================================================

def main():
    """メイン処理"""
    print("="*80)
    print("製品ポートフォリオ最適化フレームワーク v6 - サンプルデータ生成")
    print("="*80)

    # 設定ファイル読み込み
    print("\n[1/6] 設定ファイル読み込み")
    config = load_config()
    print(f"  ✅ バージョン: {config['version']}")

    # 出力ディレクトリ
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_data_dir = os.path.join(script_dir, "..", "data", "raw")
    master_data_dir = os.path.join(script_dir, "..", "data", "master")
    os.makedirs(raw_data_dir, exist_ok=True)
    os.makedirs(master_data_dir, exist_ok=True)

    # 基本データ生成
    print("\n[2/6] 基本データ生成（製品×拠点×セグメント）")
    base_data = generate_base_product_data(config)
    print(f"  ✅ 基本パターン数: {len(base_data):,}行")

    # 製品マスタ生成（代理店モデル適用）
    print("\n[3/6] 製品マスタ生成（代理店モデル適用）")
    product_master = generate_product_master_with_customers(base_data, config)
    display_dataframe_summary(product_master, "製品マスタ")

    # 顧客セグメント分布の確認
    print("\n  📊 顧客セグメント分布:")
    for customer, segments in CUSTOMER_SEGMENT_MAPPING.items():
        segment_count = len(segments)
        category = "単一セグメント" if segment_count == 1 else f"{segment_count}セグメント"
        print(f"    {customer:12s}: {', '.join(segments):40s} ({category})")

    total_customers = len(CUSTOMER_SEGMENT_MAPPING)
    single_segment = sum(1 for segs in CUSTOMER_SEGMENT_MAPPING.values() if len(segs) == 1)
    multi_segment = total_customers - single_segment
    print(f"\n  単一セグメント顧客: {single_segment}/{total_customers} ({single_segment/total_customers*100:.1f}%)")
    print(f"  複数セグメント顧客: {multi_segment}/{total_customers} ({multi_segment/total_customers*100:.1f}%)")

    # 2024年販売実績データ生成
    print("\n[4/6] 2024年販売実績データ生成")
    sales_2024 = generate_sales_2024(product_master)
    display_dataframe_summary(sales_2024, "2024年販売実績")

    # 市場マスタ生成
    print("\n[5/6] 市場マスタ生成")
    market_master = generate_market_master()
    display_dataframe_summary(market_master, "市場マスタ")

    # 競合マスタ生成
    print("\n[6/6] 競合マスタ生成")
    competitor_master = generate_competitor_master()
    display_dataframe_summary(competitor_master, "競合マスタ")

    # セグメントマスタ生成
    print("\n[7/7] セグメントマスタ生成")
    segment_master = generate_segment_master()
    display_dataframe_summary(segment_master, "セグメントマスタ")

    # ファイル保存
    print("\n" + "="*80)
    print("ファイル保存")
    print("="*80)

    save_csv_with_validation(
        sales_2024,
        os.path.join(raw_data_dir, "sales_2024.csv"),
        schema_name="sales_2024"
    )

    save_csv_with_validation(
        product_master,
        os.path.join(master_data_dir, "product_master.csv"),
        schema_name="product_master"
    )

    save_csv_with_validation(
        market_master,
        os.path.join(master_data_dir, "market_master.csv"),
        schema_name="market_master"
    )

    save_csv_with_validation(
        competitor_master,
        os.path.join(master_data_dir, "competitor_master.csv"),
        schema_name="competitor_master"
    )

    save_csv_with_validation(
        segment_master,
        os.path.join(master_data_dir, "segment_master.csv"),
        schema_name="segment_master"
    )

    # 生成統計サマリー
    print("\n" + "="*80)
    print("生成統計サマリー")
    print("="*80)
    print(f"製品×拠点×セグメント組み合わせ: {len(base_data):,}通り")
    print(f"製品×拠点×セグメント×顧客組み合わせ: {len(product_master):,}通り")
    print(f"セグメント数: {len(market_master)}種類")
    print(f"競合企業数: {len(competitor_master)}エントリ")
    print(f"\n代理店モデル:")
    print(f"  単一セグメント顧客: {single_segment}名 ({single_segment/total_customers*100:.1f}%)")
    print(f"  複数セグメント顧客: {multi_segment}名 ({multi_segment/total_customers*100:.1f}%)")

    print("\n" + "="*80)
    print("✅ データ生成完了")
    print("="*80)


if __name__ == "__main__":
    main()
