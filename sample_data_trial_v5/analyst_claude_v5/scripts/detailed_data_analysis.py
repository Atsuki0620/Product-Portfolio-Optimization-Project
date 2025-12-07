#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
詳細データ分析スクリプト
- 顧客別セグメント分布分析（代理店モデルの検証）
- セグメント×顧客×製品×拠点の全パターン粗利分析とパレート図作成
- 拠点別セグメント粗利構造の詳細分析
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# パス設定
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_MASTER_DIR = BASE_DIR / "data" / "master"
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "detailed_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    """データ読み込み"""
    print("=" * 80)
    print("データ読み込み中...")
    print("=" * 80)

    sales_df = pd.read_csv(DATA_RAW_DIR / "sales_2024.csv")
    product_master = pd.read_csv(DATA_MASTER_DIR / "product_master.csv")

    print(f"\n販売データ: {len(sales_df)} 行")
    print(f"製品マスタ: {len(product_master)} 行")

    return sales_df, product_master


def analyze_customer_segment_distribution(sales_df):
    """
    分析1: 顧客別セグメント分布分析（代理店モデルの検証）

    目的:
    - 各顧客が何セグメントの製品を購入しているかを集計
    - 1セグメントのみ、2セグメント、3セグメント以上の顧客の割合を確認
    - 代理店モデル（約1/3の顧客が2-3セグメント）を検証
    """
    print("\n" + "=" * 80)
    print("分析1: 顧客別セグメント分布分析（代理店モデルの検証）")
    print("=" * 80)

    # 顧客×セグメントの組み合わせを抽出
    customer_segment = sales_df.groupby(['customer_name', 'segment']).agg({
        'sales_qty': 'sum',
        'sales_amount': 'sum'
    }).reset_index()

    # 各顧客が購入しているセグメント数を集計
    customer_segment_count = customer_segment.groupby('customer_name')['segment'].count().reset_index()
    customer_segment_count.columns = ['customer_name', 'num_segments']

    # セグメント数別の顧客数と割合
    segment_distribution = customer_segment_count.groupby('num_segments').size().reset_index()
    segment_distribution.columns = ['num_segments', 'num_customers']
    segment_distribution['percentage'] = segment_distribution['num_customers'] / segment_distribution['num_customers'].sum() * 100

    print("\n【セグメント数別顧客分布】")
    print(segment_distribution.to_string(index=False))

    # 統計サマリー
    total_customers = len(customer_segment_count)
    customers_1seg = segment_distribution[segment_distribution['num_segments'] == 1]['num_customers'].sum()
    customers_2seg = segment_distribution[segment_distribution['num_segments'] == 2]['num_customers'].sum() if 2 in segment_distribution['num_segments'].values else 0
    customers_3seg = segment_distribution[segment_distribution['num_segments'] == 3]['num_customers'].sum() if 3 in segment_distribution['num_segments'].values else 0
    customers_4seg = segment_distribution[segment_distribution['num_segments'] == 4]['num_customers'].sum() if 4 in segment_distribution['num_segments'].values else 0
    customers_multi_seg = customers_2seg + customers_3seg + customers_4seg

    print(f"\n【統計サマリー】")
    print(f"総顧客数: {total_customers}")
    print(f"1セグメントのみの顧客: {customers_1seg} ({customers_1seg/total_customers*100:.1f}%)")
    print(f"2セグメントの顧客: {customers_2seg} ({customers_2seg/total_customers*100:.1f}%)")
    print(f"3セグメントの顧客: {customers_3seg} ({customers_3seg/total_customers*100:.1f}%)")
    print(f"4セグメントの顧客: {customers_4seg} ({customers_4seg/total_customers*100:.1f}%)")
    print(f"複数セグメント(2-4)の顧客: {customers_multi_seg} ({customers_multi_seg/total_customers*100:.1f}%)")

    print(f"\n【代理店モデルの検証結果】")
    if customers_multi_seg / total_customers >= 0.2 and customers_multi_seg / total_customers <= 0.5:
        print(f"✓ 複数セグメント顧客の割合: {customers_multi_seg/total_customers*100:.1f}%")
        print(f"  期待範囲（20-40%）に近い値です。代理店モデルと整合的です。")
    else:
        print(f"✗ 複数セグメント顧客の割合: {customers_multi_seg/total_customers*100:.1f}%")
        print(f"  期待範囲（20-40%）から外れています。")
        print(f"  → サンプルデータの修正が必要です。")

    # 顧客別詳細リスト（複数セグメント顧客）
    multi_segment_customers = customer_segment_count[customer_segment_count['num_segments'] >= 2].copy()
    multi_segment_customers = multi_segment_customers.sort_values('num_segments', ascending=False)

    print(f"\n【複数セグメント顧客の詳細リスト】")
    for _, row in multi_segment_customers.iterrows():
        customer = row['customer_name']
        num_segs = row['num_segments']
        segments = customer_segment[customer_segment['customer_name'] == customer]['segment'].tolist()
        print(f"  {customer}: {num_segs}セグメント ({', '.join(segments)})")

    # CSV出力
    customer_segment_count.to_csv(OUTPUT_DIR / "customer_segment_count.csv", index=False)
    segment_distribution.to_csv(OUTPUT_DIR / "segment_distribution.csv", index=False)

    return customer_segment_count, segment_distribution


def analyze_pattern_profit_pareto(sales_df):
    """
    分析2: セグメント×顧客×製品×拠点の全パターン粗利分析とパレート図作成

    目的:
    - 全ての組み合わせパターンを抽出
    - パターンごとの粗利金額を計算
    - パレート図を作成して上位80%の粗利を占めるパターンを特定
    """
    print("\n" + "=" * 80)
    print("分析2: セグメント×顧客×製品×拠点の全パターン粗利分析")
    print("=" * 80)

    # 粗利計算
    sales_df['unit_profit'] = sales_df['unit_price'] - sales_df['unit_cost']
    sales_df['total_profit'] = sales_df['unit_profit'] * sales_df['sales_qty']

    # パターン別集計
    pattern_profit = sales_df.groupby(['segment', 'customer_name', 'product_code', 'plant']).agg({
        'sales_qty': 'sum',
        'total_profit': 'sum',
        'unit_profit': 'mean',
        'margin_rate': 'mean'
    }).reset_index()

    pattern_profit = pattern_profit.sort_values('total_profit', ascending=False).reset_index(drop=True)

    # 累積粗利計算
    total_profit = pattern_profit['total_profit'].sum()
    pattern_profit['profit_contribution'] = pattern_profit['total_profit'] / total_profit * 100
    pattern_profit['cumulative_profit'] = pattern_profit['total_profit'].cumsum()
    pattern_profit['cumulative_percentage'] = pattern_profit['cumulative_profit'] / total_profit * 100

    print(f"\n【パターン数】")
    print(f"総パターン数: {len(pattern_profit)}")
    print(f"総粗利: {total_profit:,.0f} 円")

    # 上位パターン分析
    top_10 = pattern_profit.head(10).copy()
    top_80_percent = pattern_profit[pattern_profit['cumulative_percentage'] <= 80].copy()

    print(f"\n【上位10パターン】")
    print(top_10[['segment', 'customer_name', 'product_code', 'plant', 'total_profit', 'profit_contribution', 'cumulative_percentage']].to_string(index=True))

    print(f"\n【パレート分析結果】")
    print(f"上位80%の粗利を占めるパターン数: {len(top_80_percent)} / {len(pattern_profit)} ({len(top_80_percent)/len(pattern_profit)*100:.1f}%)")
    print(f"上位10パターンの粗利貢献度: {top_10['profit_contribution'].sum():.1f}%")
    print(f"上位20パターンの粗利貢献度: {pattern_profit.head(20)['profit_contribution'].sum():.1f}%")
    print(f"上位50パターンの粗利貢献度: {pattern_profit.head(50)['profit_contribution'].sum():.1f}%")

    # パレート図作成
    fig, ax1 = plt.subplots(figsize=(14, 6))

    # 棒グラフ（粗利貢献度）
    x_pos = np.arange(min(50, len(pattern_profit)))
    ax1.bar(x_pos, pattern_profit.head(50)['profit_contribution'], color='skyblue', alpha=0.7)
    ax1.set_xlabel('Pattern Rank (Top 50)', fontsize=12)
    ax1.set_ylabel('Profit Contribution (%)', fontsize=12, color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.set_title('Pareto Chart: Segment x Customer x Product x Plant Patterns', fontsize=14, fontweight='bold')

    # 折れ線グラフ（累積粗利率）
    ax2 = ax1.twinx()
    ax2.plot(x_pos, pattern_profit.head(50)['cumulative_percentage'], color='red', marker='o', linewidth=2, markersize=3)
    ax2.set_ylabel('Cumulative Profit (%)', fontsize=12, color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    ax2.axhline(y=80, color='green', linestyle='--', linewidth=1.5, label='80% Line')
    ax2.legend(loc='lower right')
    ax2.set_ylim(0, 105)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "pareto_chart_patterns.png", dpi=300, bbox_inches='tight')
    print(f"\nパレート図を保存: {OUTPUT_DIR / 'pareto_chart_patterns.png'}")

    # CSV出力
    pattern_profit.to_csv(OUTPUT_DIR / "pattern_profit_analysis.csv", index=False)

    return pattern_profit


def analyze_plant_segment_profit_structure(sales_df):
    """
    分析3: 拠点別セグメント粗利構造の詳細分析

    目的:
    - 各拠点における4セグメントの粗利貢献度を詳細に分析
    - 「拠点A=Electronics/Industrial専門」という構造を検証
    """
    print("\n" + "=" * 80)
    print("分析3: 拠点別セグメント粗利構造の詳細分析")
    print("=" * 80)

    # 粗利計算
    sales_df['unit_profit'] = sales_df['unit_price'] - sales_df['unit_cost']
    sales_df['total_profit'] = sales_df['unit_profit'] * sales_df['sales_qty']

    # 拠点×セグメント別集計
    plant_segment = sales_df.groupby(['plant', 'segment']).agg({
        'sales_qty': 'sum',
        'total_profit': 'sum',
        'margin_rate': 'mean'
    }).reset_index()

    # 拠点別合計
    plant_total = sales_df.groupby('plant').agg({
        'sales_qty': 'sum',
        'total_profit': 'sum'
    }).reset_index()
    plant_total.columns = ['plant', 'total_sales_qty_plant', 'total_profit_plant']

    # 拠点別セグメント粗利貢献度
    plant_segment = plant_segment.merge(plant_total, on='plant')
    plant_segment['profit_contribution'] = plant_segment['total_profit'] / plant_segment['total_profit_plant'] * 100
    plant_segment['qty_share'] = plant_segment['sales_qty'] / plant_segment['total_sales_qty_plant'] * 100

    print("\n【拠点別セグメント粗利構造】")
    for plant in ['A', 'B']:
        plant_data = plant_segment[plant_segment['plant'] == plant].copy()
        plant_data = plant_data.sort_values('total_profit', ascending=False)

        print(f"\n--- Plant {plant} ---")
        print(f"総粗利: {plant_data['total_profit_plant'].iloc[0]:,.0f} 円")
        print(f"総販売数量: {plant_data['total_sales_qty_plant'].iloc[0]:,.0f} 本")
        print(f"\nセグメント別内訳:")
        for _, row in plant_data.iterrows():
            print(f"  {row['segment']:15s}: 粗利 {row['total_profit']:>12,.0f} 円 ({row['profit_contribution']:>5.1f}%), "
                  f"数量 {row['sales_qty']:>8,.0f} 本 ({row['qty_share']:>5.1f}%), 粗利率 {row['margin_rate']:>5.1%}")

    # ヒートマップ作成（拠点×セグメント粗利貢献度）
    pivot_profit = plant_segment.pivot(index='plant', columns='segment', values='profit_contribution')

    fig, ax = plt.subplots(figsize=(10, 4))
    sns.heatmap(pivot_profit, annot=True, fmt='.1f', cmap='YlOrRd', cbar_kws={'label': 'Profit Contribution (%)'}, ax=ax)
    ax.set_title('Plant x Segment: Profit Contribution (%)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Segment', fontsize=12)
    ax.set_ylabel('Plant', fontsize=12)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "plant_segment_heatmap.png", dpi=300, bbox_inches='tight')
    print(f"\nヒートマップを保存: {OUTPUT_DIR / 'plant_segment_heatmap.png'}")

    # 検証結果
    print(f"\n【拠点特化の検証結果】")
    plant_a_data = plant_segment[plant_segment['plant'] == 'A'].copy()
    plant_b_data = plant_segment[plant_segment['plant'] == 'B'].copy()

    plant_a_electronics = plant_a_data[plant_a_data['segment'] == 'electronics']['profit_contribution'].values[0] if len(plant_a_data[plant_a_data['segment'] == 'electronics']) > 0 else 0
    plant_a_industrial = plant_a_data[plant_a_data['segment'] == 'industrial']['profit_contribution'].values[0] if len(plant_a_data[plant_a_data['segment'] == 'industrial']) > 0 else 0
    plant_a_ei_total = plant_a_electronics + plant_a_industrial

    plant_b_oil_gas = plant_b_data[plant_b_data['segment'] == 'oil_gas']['profit_contribution'].values[0] if len(plant_b_data[plant_b_data['segment'] == 'oil_gas']) > 0 else 0
    plant_b_others = plant_b_data[plant_b_data['segment'] == 'others']['profit_contribution'].values[0] if len(plant_b_data[plant_b_data['segment'] == 'others']) > 0 else 0
    plant_b_oo_total = plant_b_oil_gas + plant_b_others

    print(f"Plant A:")
    print(f"  Electronics + Industrial の粗利貢献度: {plant_a_ei_total:.1f}%")
    if plant_a_ei_total >= 70:
        print(f"  ✓ Electronics/Industrial 専門拠点として機能している（70%以上）")
    else:
        print(f"  ✗ Electronics/Industrial 専門拠点としては弱い（70%未満）")

    print(f"\nPlant B:")
    print(f"  Oil & Gas + Others の粗利貢献度: {plant_b_oo_total:.1f}%")
    if plant_b_oo_total >= 70:
        print(f"  ✓ Oil & Gas/Others 専門拠点として機能している（70%以上）")
    else:
        print(f"  ✗ Oil & Gas/Others 専門拠点としては弱い（70%未満）")

    # CSV出力
    plant_segment.to_csv(OUTPUT_DIR / "plant_segment_structure.csv", index=False)

    return plant_segment


def main():
    """メイン実行関数"""
    print("\n" + "=" * 80)
    print("詳細データ分析スクリプト実行開始")
    print("=" * 80)

    # データ読み込み
    sales_df, product_master = load_data()

    # 分析1: 顧客別セグメント分布分析
    customer_segment_count, segment_distribution = analyze_customer_segment_distribution(sales_df)

    # 分析2: パターン別粗利分析とパレート図
    pattern_profit = analyze_pattern_profit_pareto(sales_df)

    # 分析3: 拠点別セグメント粗利構造分析
    plant_segment = analyze_plant_segment_profit_structure(sales_df)

    print("\n" + "=" * 80)
    print("すべての分析が完了しました")
    print(f"結果ファイルは以下のディレクトリに保存されています:")
    print(f"  {OUTPUT_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()
