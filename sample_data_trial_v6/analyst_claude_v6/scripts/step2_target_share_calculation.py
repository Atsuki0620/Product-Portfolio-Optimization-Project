"""
製品ポートフォリオ最適化フレームワーク v6 - Step2: 目標シェア計算

このスクリプトは、セグメント別の戦略に基づいて目標シェアと目標販売数量を計算します。
- 1年間の目標設定（v5の3年から変更）
- 新戦略係数の適用（現実的な値に修正）
- 競合からの奪取可能数量の計算

作成日: 2025年12月7日
バージョン: 6.0
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Dict, Tuple

# 共通ユーティリティのインポート
from optimization_common_v6 import (
    load_config,
    load_csv_with_validation,
    save_csv_with_validation,
    validate_output_data,
    display_dataframe_summary
)


# =============================================================================
# 目標シェア計算
# =============================================================================

def calculate_target_share(
    df: pd.DataFrame,
    config: Dict
) -> pd.DataFrame:
    """
    戦略タイプに基づいて目標シェアを計算します。

    Parameters
    ----------
    df : pd.DataFrame
        入力データ
    config : Dict
        設定ファイルの内容

    Returns
    -------
    pd.DataFrame
        目標シェア追加済みデータ
    """
    print("\n" + "="*80)
    print("目標シェア計算")
    print("="*80)

    strategy_coefficients = config['strategy_coefficients']

    # セグメント別に目標シェアを計算
    df['target_share'] = 0.0

    for strategy_type, coeffs in strategy_coefficients.items():
        mask = df['strategy_type'] == strategy_type

        # ランダムに係数範囲内の値を選択（セグメント単位で統一）
        np.random.seed(42)
        for segment_code in df[mask]['segment_code'].unique():
            segment_mask = mask & (df['segment_code'] == segment_code)
            coefficient = np.random.uniform(coeffs['lower'], coeffs['upper'])
            target_share = df.loc[segment_mask, 'current_share'] * coefficient

            # シェアは0-1の範囲に制限
            target_share = np.clip(target_share, 0.0, 1.0)

            df.loc[segment_mask, 'target_share'] = target_share

            print(f"  {segment_code:12s} ({strategy_type:20s}): "
                  f"現在シェア={df.loc[segment_mask, 'current_share'].iloc[0]:.3f} → "
                  f"目標シェア={target_share.iloc[0]:.3f} (係数={coefficient:.3f})")

    return df


# =============================================================================
# 競合からの奪取可能数量計算
# =============================================================================

def calculate_acquisition_potential(
    df: pd.DataFrame,
    competitor_master: pd.DataFrame,
    config: Dict
) -> pd.DataFrame:
    """
    競合からの奪取可能数量を計算します。

    Parameters
    ----------
    df : pd.DataFrame
        目標シェア計算済みデータ
    competitor_master : pd.DataFrame
        競合マスタ
    config : Dict
        設定ファイルの内容

    Returns
    -------
    pd.DataFrame
        奪取可能数量追加済みデータ
    """
    print("\n" + "="*80)
    print("競合からの奪取可能数量計算")
    print("="*80)

    # セグメント別の奪取可能数量を計算
    acquisition_by_segment = []

    for segment_code in df['segment_code'].unique():
        segment_df = df[df['segment_code'] == segment_code].iloc[0]
        market_size_after_1y = segment_df['market_size_after_1y']

        # このセグメントの競合データを取得
        competitors = competitor_master[competitor_master['segment_code'] == segment_code]

        total_acquisition = 0.0

        for _, comp in competitors.iterrows():
            competitor_volume = market_size_after_1y * comp['competitor_share']

            # 奪取可能率の中央値を使用
            acquisition_rate = (comp['acquisition_rate_lower'] + comp['acquisition_rate_upper']) / 2

            acquisition_volume = competitor_volume * acquisition_rate
            total_acquisition += acquisition_volume

            print(f"  {segment_code:12s} - {comp['competitor_code']:12s} "
                  f"({comp['competitor_strength']:8s}): "
                  f"シェア={comp['competitor_share']:.3f}, "
                  f"奪取率={acquisition_rate:.4f}, "
                  f"奪取数量={acquisition_volume:,.0f}本")

        acquisition_by_segment.append({
            'segment_code': segment_code,
            'total_acquisition_potential': total_acquisition
        })

    # DataFrameに変換してマージ
    acquisition_df = pd.DataFrame(acquisition_by_segment)
    df = df.merge(acquisition_df, on='segment_code', how='left')

    print(f"\n  セグメント別奪取可能数量合計:")
    for _, row in acquisition_df.iterrows():
        print(f"    {row['segment_code']:12s}: {row['total_acquisition_potential']:,.0f}本")

    return df


# =============================================================================
# 目標販売数量計算
# =============================================================================

def calculate_target_volume(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    目標販売数量を計算します。

    Parameters
    ----------
    df : pd.DataFrame
        奪取可能数量計算済みデータ

    Returns
    -------
    pd.DataFrame
        目標販売数量追加済みデータ
    """
    print("\n" + "="*80)
    print("目標販売数量計算")
    print("="*80)

    # セグメント別の目標販売数量を計算
    for segment_code in df['segment_code'].unique():
        mask = df['segment_code'] == segment_code
        segment_df = df[mask].iloc[0]

        market_size_after_1y = segment_df['market_size_after_1y']
        target_share = segment_df['target_share']
        total_acquisition_potential = segment_df['total_acquisition_potential']

        # 目標販売数量 = 1年後市場規模 × 目標シェア
        segment_target_volume = market_size_after_1y * target_share

        # 奪取を考慮した実現可能な目標数量
        # （現状シェア分 + 奪取可能数量の範囲内）
        current_volume = market_size_after_1y * segment_df['current_share']
        max_achievable_volume = current_volume + total_acquisition_potential

        # 実現可能性チェック
        if segment_target_volume > max_achievable_volume:
            print(f"  ⚠️  {segment_code:12s}: 目標数量が奪取可能数量を超過")
            print(f"      目標={segment_target_volume:,.0f}本, 最大可能={max_achievable_volume:,.0f}本")
            achievable_flag = False
        else:
            achievable_flag = True

        df.loc[mask, 'segment_target_volume'] = segment_target_volume
        df.loc[mask, 'max_achievable_volume'] = max_achievable_volume
        df.loc[mask, 'is_segment_achievable'] = achievable_flag

        print(f"  {segment_code:12s}: "
              f"現状={segment_df['current_share']:.3f} → 目標={target_share:.3f}, "
              f"目標数量={segment_target_volume:,.0f}本 "
              f"({'✅ 実現可能' if achievable_flag else '❌ 要調整'})")

    # 製品×拠点×セグメント×顧客レベルの目標数量を配分
    # （セグメント目標数量を現状比で配分）
    df['target_volume'] = 0.0

    for segment_code in df['segment_code'].unique():
        mask = df['segment_code'] == segment_code
        segment_df = df[mask]

        segment_current_total = segment_df['sales_volume'].sum()
        segment_target_total = segment_df['segment_target_volume'].iloc[0]

        if segment_current_total > 0:
            # 現状比で配分
            allocation_ratio = segment_target_total / segment_current_total
            df.loc[mask, 'target_volume'] = df.loc[mask, 'sales_volume'] * allocation_ratio
        else:
            # 現状数量が0の場合は均等配分
            df.loc[mask, 'target_volume'] = segment_target_total / len(segment_df)

    return df


# =============================================================================
# サマリーレポート
# =============================================================================

def generate_summary_report(df: pd.DataFrame, output_dir: str) -> None:
    """
    目標シェア計算のサマリーレポートを生成します。

    Parameters
    ----------
    df : pd.DataFrame
        計算済みデータ
    output_dir : str
        出力ディレクトリ
    """
    print("\n" + "="*80)
    print("サマリーレポート生成")
    print("="*80)

    report = []

    # 基本統計
    report.append("# 目標シェア計算サマリー（Step2）\n")
    report.append(f"**作成日**: 2025年12月7日\n")
    report.append("\n---\n")

    # セグメント別目標
    report.append("\n## セグメント別目標シェアと販売数量\n")
    report.append("| セグメント | 戦略 | 現状シェア | 目標シェア | 現状数量 | 目標数量 | 増減 | 実現可能性 |\n")
    report.append("|-----------|------|-----------|-----------|----------|----------|------|------------|\n")

    segment_summary = df.groupby(['segment_code', 'strategy_type']).agg({
        'current_share': 'first',
        'target_share': 'first',
        'sales_volume': 'sum',
        'segment_target_volume': 'first',
        'is_segment_achievable': 'first'
    }).reset_index()

    for _, row in segment_summary.iterrows():
        change = row['segment_target_volume'] - row['sales_volume']
        change_pct = (change / row['sales_volume'] * 100) if row['sales_volume'] > 0 else 0
        achievable = "✅ 可能" if row['is_segment_achievable'] else "❌ 要調整"

        report.append(
            f"| {row['segment_code']} | {row['strategy_type']} | "
            f"{row['current_share']:.3f} | {row['target_share']:.3f} | "
            f"{row['sales_volume']:,.0f}本 | {row['segment_target_volume']:,.0f}本 | "
            f"{change:+,.0f}本 ({change_pct:+.1f}%) | {achievable} |\n"
        )

    # 総合計
    report.append("\n## 全体サマリー\n")
    total_current = df['sales_volume'].sum()
    total_target = df['target_volume'].sum()
    total_change = total_target - total_current
    total_change_pct = (total_change / total_current * 100) if total_current > 0 else 0

    report.append(f"- **現状総販売数量**: {total_current:,.0f}本\n")
    report.append(f"- **目標総販売数量**: {total_target:,.0f}本\n")
    report.append(f"- **増減**: {total_change:+,.0f}本 ({total_change_pct:+.1f}%)\n")

    # 総販売目標との比較
    total_sales_target = df['total_sales_target'].iloc[0]
    gap_to_target = total_sales_target - total_target

    report.append(f"\n- **総販売目標**: {total_sales_target:,.0f}本\n")
    report.append(f"- **目標との差**: {gap_to_target:+,.0f}本\n")

    if abs(gap_to_target) > 1000:
        if gap_to_target > 0:
            report.append(f"- ⚠️ **警告**: 目標に{gap_to_target:,.0f}本不足。追加施策が必要です。\n")
        else:
            report.append(f"- ✅ **状況**: 目標を{abs(gap_to_target):,.0f}本超過。問題ありません。\n")

    # 戦略別統計
    report.append("\n## 戦略別統計\n")
    strategy_summary = df.groupby('strategy_type').agg({
        'sales_volume': 'sum',
        'target_volume': 'sum'
    }).reset_index()

    report.append("| 戦略 | 現状数量 | 目標数量 | 増減 |\n")
    report.append("|------|----------|----------|------|\n")

    for _, row in strategy_summary.iterrows():
        change = row['target_volume'] - row['sales_volume']
        change_pct = (change / row['sales_volume'] * 100) if row['sales_volume'] > 0 else 0

        report.append(
            f"| {row['strategy_type']} | {row['sales_volume']:,.0f}本 | "
            f"{row['target_volume']:,.0f}本 | {change:+,.0f}本 ({change_pct:+.1f}%) |\n"
        )

    # レポート保存
    report_path = os.path.join(output_dir, "step2_target_share_summary.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report)

    print(f"  ✅ サマリーレポート保存: {report_path}")


# =============================================================================
# メイン処理
# =============================================================================

def main():
    """メイン処理"""
    print("="*80)
    print("製品ポートフォリオ最適化フレームワーク v6 - Step2: 目標シェア計算")
    print("="*80)

    # 設定ファイル読み込み
    print("\n[1/6] 設定ファイル読み込み")
    config = load_config()
    print(f"  ✅ バージョン: {config['version']}")

    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    processed_dir = os.path.join(data_dir, "processed")
    reports_dir = os.path.join(script_dir, "..", "reports")

    # Step1の出力データ読み込み
    print("\n[2/6] Step1出力データ読み込み")
    df = pd.read_csv(os.path.join(processed_dir, "optimization_input_data.csv"))
    display_dataframe_summary(df, "Step1出力データ")

    # 競合マスタ読み込み
    print("\n[3/6] 競合マスタ読み込み")
    competitor_master = load_csv_with_validation(
        os.path.join(data_dir, "master", "competitor_master.csv"),
        schema_name="competitor_master"
    )

    # 目標シェア計算
    print("\n[4/6] 目標シェア計算")
    df = calculate_target_share(df, config)

    # 競合からの奪取可能数量計算
    print("\n[5/6] 奪取可能数量計算")
    df = calculate_acquisition_potential(df, competitor_master, config)

    # 目標販売数量計算
    print("\n[6/6] 目標販売数量計算")
    df = calculate_target_volume(df)

    # データ保存
    print("\n" + "="*80)
    print("データ保存")
    print("="*80)
    output_path = os.path.join(processed_dir, "target_calculation_data.csv")
    save_csv_with_validation(
        df,
        output_path,
        schema_name=None
    )

    # サマリーレポート生成
    generate_summary_report(df, reports_dir)

    # 最終サマリー
    print("\n" + "="*80)
    print("✅ Step2: 目標シェア計算完了")
    print("="*80)
    total_current = df['sales_volume'].sum()
    total_target = df['target_volume'].sum()
    print(f"  現状総販売数量: {total_current:,.0f}本")
    print(f"  目標総販売数量: {total_target:,.0f}本")
    print(f"  増減: {total_target - total_current:+,.0f}本 ({(total_target - total_current) / total_current * 100:+.1f}%)")
    print(f"  出力ファイル: {output_path}")


if __name__ == "__main__":
    main()
