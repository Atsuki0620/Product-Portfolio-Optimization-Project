#!/usr/bin/env python3
"""product_master.csvの詳細確認スクリプト"""
import pandas as pd
from pathlib import Path
from collections import Counter

# パス設定
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
MASTER_DIR = PROJECT_ROOT / "data" / "master"

def main():
    """メイン処理"""
    # product_master.csv を読み込み
    product_master = pd.read_csv(MASTER_DIR / "product_master.csv")

    print("=" * 80)
    print("product_master.csv の詳細確認")
    print("=" * 80)

    # 全体の概要
    print(f"\n総製品数: {len(product_master)}")

    # allowed_plants の分布
    print("\n【allowed_plants の分布】")
    plants_dist = product_master['allowed_plants'].value_counts()
    print(plants_dist)

    # 価格帯別の分布
    print("\n【価格帯別の製品数】")
    price_band_dist = product_master['price_band'].value_counts()
    print(price_band_dist)

    # 価格帯 × allowed_plants のクロス集計
    print("\n【価格帯 × allowed_plants のクロス集計】")
    cross_tab = pd.crosstab(product_master['price_band'], product_master['allowed_plants'])
    print(cross_tab)

    # 各製品の詳細（product_code, price_band, allowed_plants）
    print("\n【全製品の詳細リスト】")
    detail_df = product_master[['product_code', 'product_name', 'price_band', 'allowed_plants', 'allowed_segments']]
    for idx, row in detail_df.iterrows():
        plants = row['allowed_plants']
        segments = row['allowed_segments']
        print(f"{row['product_code']}: {row['product_name']:<30} [{row['price_band']:<4}] Plants={plants:<6} Segments={segments}")

    # allowed_plantsに含まれる拠点の種類を分析
    print("\n【拠点の組み合わせパターン】")
    patterns = {
        'A のみ': 0,
        'B のみ': 0,
        'A|B': 0
    }

    for plants in product_master['allowed_plants']:
        if plants == 'A':
            patterns['A のみ'] += 1
        elif plants == 'B':
            patterns['B のみ'] += 1
        elif plants == 'A|B':
            patterns['A|B'] += 1

    print(f"A のみ: {patterns['A のみ']} 製品")
    print(f"B のみ: {patterns['B のみ']} 製品")
    print(f"A|B (両方): {patterns['A|B']} 製品")

    # 単価の範囲確認
    print("\n【単価の範囲】")
    print(f"低価格帯 (low):")
    low_products = product_master[product_master['price_band'] == 'low']
    print(f"  最小単価: {low_products['unit_price_min'].min():.2f} 円")
    print(f"  最大単価: {low_products['unit_price_max'].max():.2f} 円")
    print(f"  平均最小単価: {low_products['unit_price_min'].mean():.2f} 円")
    print(f"  平均最大単価: {low_products['unit_price_max'].mean():.2f} 円")

    print(f"\n高価格帯 (high):")
    high_products = product_master[product_master['price_band'] == 'high']
    print(f"  最小単価: {high_products['unit_price_min'].min():.2f} 円")
    print(f"  最大単価: {high_products['unit_price_max'].max():.2f} 円")
    print(f"  平均最小単価: {high_products['unit_price_min'].mean():.2f} 円")
    print(f"  平均最大単価: {high_products['unit_price_max'].max():.2f} 円")

if __name__ == '__main__':
    main()
