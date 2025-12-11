"""
製品ポートフォリオ最適化フレームワーク v6 - Step1: データ準備

このスクリプトは、サンプルデータを読み込み、最適化に必要な形式に整形します。
- A-6改善提案: Fail-Fast原則によるデータバリデーション
- A-5改善提案: スキーマ検証による品質保証
- 4つ組タプル対応: (product_code, plant_code, segment_code, customer_code)

作成日: 2025年12月7日
バージョン: 6.0
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Dict

# 共通ユーティリティのインポート
from optimization_common_v6 import (
    load_config,
    load_csv_with_validation,
    save_csv_with_validation,
    validate_output_data,
    display_dataframe_summary
)


# =============================================================================
# データ読み込み
# =============================================================================

def load_all_master_data(data_dir: str) -> Dict[str, pd.DataFrame]:
    """
    すべてのマスタデータを読み込みます。

    Parameters
    ----------
    data_dir : str
        データディレクトリのパス

    Returns
    -------
    Dict[str, pd.DataFrame]
        マスタデータの辞書
    """
    print("\n" + "="*80)
    print("マスタデータ読み込み")
    print("="*80)

    master_data = {}

    # 製品マスタ
    print("\n[1/5] 製品マスタ読み込み")
    master_data['product_master'] = load_csv_with_validation(
        os.path.join(data_dir, "master", "product_master.csv"),
        schema_name="product_master"
    )

    # 市場マスタ
    print("\n[2/5] 市場マスタ読み込み")
    master_data['market_master'] = load_csv_with_validation(
        os.path.join(data_dir, "master", "market_master.csv"),
        schema_name="market_master"
    )

    # 競合マスタ
    print("\n[3/5] 競合マスタ読み込み")
    master_data['competitor_master'] = load_csv_with_validation(
        os.path.join(data_dir, "master", "competitor_master.csv"),
        schema_name="competitor_master"
    )

    # セグメントマスタ
    print("\n[4/5] セグメントマスタ読み込み")
    master_data['segment_master'] = load_csv_with_validation(
        os.path.join(data_dir, "master", "segment_master.csv"),
        schema_name="segment_master"
    )

    # 2024年販売実績
    print("\n[5/5] 2024年販売実績読み込み")
    master_data['sales_2024'] = load_csv_with_validation(
        os.path.join(data_dir, "raw", "sales_2024.csv"),
        schema_name="sales_2024"
    )

    return master_data


# =============================================================================
# データマージ
# =============================================================================

def merge_optimization_data(master_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    最適化に必要なデータをマージします。

    Parameters
    ----------
    master_data : Dict[str, pd.DataFrame]
        マスタデータの辞書

    Returns
    -------
    pd.DataFrame
        マージ済みデータ
    """
    print("\n" + "="*80)
    print("データマージ")
    print("="*80)

    # 製品マスタをベースにマージ
    df = master_data['product_master'].copy()
    print(f"ベースデータ: {len(df):,}行（製品マスタ）")

    # 市場マスタをマージ（segment_code基準）
    df = df.merge(
        master_data['market_master'],
        on='segment_code',
        how='left',
        suffixes=('', '_market')
    )
    print(f"  市場マスタマージ後: {len(df):,}行")

    # セグメントマスタをマージ（segment_code基準、strategy_typeは市場マスタ優先）
    segment_master = master_data['segment_master'][['segment_code', 'segment_name']].copy()
    df = df.merge(
        segment_master,
        on='segment_code',
        how='left'
    )
    print(f"  セグメントマスタマージ後: {len(df):,}行")

    # 必要なカラムを整理
    required_columns = [
        # 4つ組タプル（決定変数のキー）
        'product_code',
        'plant_code',
        'segment_code',
        'customer_code',

        # 製品情報
        'product_name',
        'cost_band',

        # 価格・コスト情報（顧客別）
        'unit_price',
        'unit_cost',
        'unit_profit',
        'margin_rate',

        # 現状販売数量
        'sales_volume',

        # 市場情報
        'segment_name',
        'market_size',
        'market_size_after_1y',
        'cagr',
        'current_share',
        'strategy_type'
    ]

    # 欠損カラムのチェック
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"必須カラムが不足しています: {missing_columns}")

    df = df[required_columns]

    # データ検証
    validate_output_data(df, "データマージ結果")

    return df


# =============================================================================
# 統計情報の追加
# =============================================================================

def add_aggregated_statistics(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """
    集計統計情報を追加します。

    Parameters
    ----------
    df : pd.DataFrame
        マージ済みデータ
    config : Dict
        設定ファイルの内容

    Returns
    -------
    pd.DataFrame
        統計情報追加済みデータ
    """
    print("\n" + "="*80)
    print("統計情報の追加")
    print("="*80)

    # 総粗利の計算
    df['total_profit'] = df['unit_profit'] * df['sales_volume']
    print("  ✅ total_profit = unit_profit × sales_volume")

    # 製品×拠点×セグメント別の販売数量合計（顧客をまたいだ集計）
    product_plant_segment_qty = df.groupby(['product_code', 'plant_code', 'segment_code'])['sales_volume'].sum().reset_index()
    product_plant_segment_qty.rename(columns={'sales_volume': 'total_qty_per_pps'}, inplace=True)

    df = df.merge(
        product_plant_segment_qty,
        on=['product_code', 'plant_code', 'segment_code'],
        how='left'
    )
    print(f"  ✅ total_qty_per_pps = 製品×拠点×セグメント別の販売数量合計")

    # セグメント別の総販売数量
    segment_qty = df.groupby('segment_code')['sales_volume'].sum().reset_index()
    segment_qty.rename(columns={'sales_volume': 'segment_total_qty'}, inplace=True)

    df = df.merge(
        segment_qty,
        on='segment_code',
        how='left'
    )
    print(f"  ✅ segment_total_qty = セグメント別の総販売数量")

    # 拠点別の総販売数量
    plant_qty = df.groupby('plant_code')['sales_volume'].sum().reset_index()
    plant_qty.rename(columns={'sales_volume': 'plant_total_qty'}, inplace=True)

    df = df.merge(
        plant_qty,
        on='plant_code',
        how='left'
    )
    print(f"  ✅ plant_total_qty = 拠点別の総販売数量")

    # 全体の総販売数量
    df['total_sales_qty'] = df['sales_volume'].sum()
    print(f"  ✅ total_sales_qty = 全体の総販売数量: {df['total_sales_qty'].iloc[0]:,.0f}本")

    # 拠点生産能力の追加
    plant_capacity = config['plant_capacity']
    df['plant_capacity'] = df['plant_code'].map(plant_capacity)
    print(f"  ✅ plant_capacity = 拠点別の生産能力")
    print(f"      拠点A: {plant_capacity['A']:,}本")
    print(f"      拠点B: {plant_capacity['B']:,}本")

    # 総販売目標の追加
    df['total_sales_target'] = config['total_sales_target']
    print(f"  ✅ total_sales_target = 総販売目標: {config['total_sales_target']:,}本")

    return df


# =============================================================================
# サマリーレポート
# =============================================================================

def generate_summary_report(df: pd.DataFrame, output_dir: str) -> None:
    """
    データ準備のサマリーレポートを生成します。

    Parameters
    ----------
    df : pd.DataFrame
        準備済みデータ
    output_dir : str
        出力ディレクトリ
    """
    print("\n" + "="*80)
    print("サマリーレポート生成")
    print("="*80)

    report = []

    # 基本統計
    report.append("# データ準備サマリー（Step1）\n")
    report.append(f"**作成日**: 2025年12月7日\n")
    report.append(f"**データ行数**: {len(df):,}行\n")
    report.append("\n---\n")

    # 4つ組タプル統計
    report.append("\n## 4つ組タプル統計\n")
    unique_products = df['product_code'].nunique()
    unique_plants = df['plant_code'].nunique()
    unique_segments = df['segment_code'].nunique()
    unique_customers = df['customer_code'].nunique()
    total_combinations = len(df)

    report.append(f"- **製品数**: {unique_products}種類\n")
    report.append(f"- **拠点数**: {unique_plants}拠点\n")
    report.append(f"- **セグメント数**: {unique_segments}セグメント\n")
    report.append(f"- **顧客数**: {unique_customers}社\n")
    report.append(f"- **総組み合わせ数**: {total_combinations:,}通り\n")
    report.append(f"  - 理論上の最大: {unique_products} × {unique_plants} × {unique_segments} × {unique_customers} = {unique_products * unique_plants * unique_segments * unique_customers:,}通り\n")
    report.append(f"  - 実際の組み合わせ: {total_combinations:,}通り ({total_combinations / (unique_products * unique_plants * unique_segments * unique_customers) * 100:.1f}%)\n")

    # 顧客別統計
    report.append("\n## 顧客別統計\n")
    customer_stats = df.groupby('customer_code').agg({
        'sales_volume': 'sum',
        'total_profit': 'sum',
        'segment_code': 'nunique'
    }).reset_index()
    customer_stats.columns = ['customer_code', 'total_sales_volume', 'total_profit', 'segment_count']
    customer_stats = customer_stats.sort_values('total_profit', ascending=False)

    report.append("| 顧客 | 販売数量 | 総粗利 | セグメント数 |\n")
    report.append("|------|----------|--------|-------------|\n")
    for _, row in customer_stats.iterrows():
        report.append(f"| {row['customer_code']} | {row['total_sales_volume']:,.0f}本 | ¥{row['total_profit']:,.0f} | {row['segment_count']}セグメント |\n")

    # セグメント別統計
    report.append("\n## セグメント別統計\n")
    segment_stats = df.groupby(['segment_code', 'strategy_type']).agg({
        'sales_volume': 'sum',
        'total_profit': 'sum',
        'customer_code': 'nunique'
    }).reset_index()
    segment_stats.columns = ['segment_code', 'strategy_type', 'total_sales_volume', 'total_profit', 'customer_count']

    report.append("| セグメント | 戦略 | 販売数量 | 総粗利 | 顧客数 |\n")
    report.append("|-----------|------|----------|--------|--------|\n")
    for _, row in segment_stats.iterrows():
        report.append(f"| {row['segment_code']} | {row['strategy_type']} | {row['total_sales_volume']:,.0f}本 | ¥{row['total_profit']:,.0f} | {row['customer_count']}社 |\n")

    # 拠点別統計
    report.append("\n## 拠点別統計\n")
    plant_stats = df.groupby('plant_code').agg({
        'sales_volume': 'sum',
        'total_profit': 'sum',
        'plant_capacity': 'first'
    }).reset_index()
    plant_stats.columns = ['plant_code', 'total_sales_volume', 'total_profit', 'plant_capacity']
    plant_stats['capacity_utilization'] = plant_stats['total_sales_volume'] / plant_stats['plant_capacity'] * 100

    report.append("| 拠点 | 販売数量 | 総粗利 | 生産能力 | 稼働率 |\n")
    report.append("|------|----------|--------|----------|--------|\n")
    for _, row in plant_stats.iterrows():
        report.append(f"| {row['plant_code']} | {row['total_sales_volume']:,.0f}本 | ¥{row['total_profit']:,.0f} | {row['plant_capacity']:,.0f}本 | {row['capacity_utilization']:.1f}% |\n")

    # レポート保存
    report_path = os.path.join(output_dir, "step1_data_preparation_summary.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report)

    print(f"  ✅ サマリーレポート保存: {report_path}")


# =============================================================================
# メイン処理
# =============================================================================

def main():
    """メイン処理"""
    print("="*80)
    print("製品ポートフォリオ最適化フレームワーク v6 - Step1: データ準備")
    print("="*80)

    # 設定ファイル読み込み
    print("\n[1/5] 設定ファイル読み込み")
    config = load_config()
    print(f"  ✅ バージョン: {config['version']}")

    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    processed_dir = os.path.join(data_dir, "processed")
    reports_dir = os.path.join(script_dir, "..", "reports")
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    # マスタデータ読み込み
    print("\n[2/5] マスタデータ読み込み")
    master_data = load_all_master_data(data_dir)

    # データマージ
    print("\n[3/5] データマージ")
    df = merge_optimization_data(master_data)
    display_dataframe_summary(df, "マージ済みデータ")

    # 統計情報の追加
    print("\n[4/5] 統計情報の追加")
    df = add_aggregated_statistics(df, config)
    display_dataframe_summary(df, "統計情報追加済みデータ")

    # データ保存
    print("\n[5/5] データ保存")
    output_path = os.path.join(processed_dir, "optimization_input_data.csv")
    save_csv_with_validation(
        df,
        output_path,
        schema_name=None  # カスタムスキーマなのでスキーマ検証をスキップ
    )

    # サマリーレポート生成
    generate_summary_report(df, reports_dir)

    print("\n" + "="*80)
    print("✅ Step1: データ準備完了")
    print("="*80)
    print(f"  入力データ: {len(master_data):,}ファイル")
    print(f"  出力データ: {len(df):,}行")
    print(f"  出力ファイル: {output_path}")


if __name__ == "__main__":
    main()
