"""
製品ポートフォリオ最適化フレームワーク v6 - Step3: 実現可能性検証

このスクリプトは、目標の実現可能性を検証し、必要に応じて自動調整します。
- A-3改善提案: 自動調整機能（5%削減、最大5イテレーション）
- 拠点別生産能力制約のチェック
- 総販売目標との整合性チェック

作成日: 2025年12月7日
バージョン: 6.0
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Dict, List, Tuple

# 共通ユーティリティのインポート
from optimization_common_v6 import (
    load_config,
    save_csv_with_validation,
    display_dataframe_summary
)


# =============================================================================
# 実現可能性チェック
# =============================================================================

def check_feasibility(
    df: pd.DataFrame,
    config: Dict
) -> Tuple[bool, List[str]]:
    """
    実現可能性をチェックします。

    Parameters
    ----------
    df : pd.DataFrame
        目標計算済みデータ
    config : Dict
        設定ファイルの内容

    Returns
    -------
    Tuple[bool, List[str]]
        (実現可能フラグ, 問題リスト)
    """
    print("\n" + "="*80)
    print("実現可能性チェック")
    print("="*80)

    issues = []

    # 1. セグメント別の奪取可能数量チェック
    print("\n[1/4] セグメント別奪取可能数量チェック")
    for segment_code in df['segment_code'].unique():
        mask = df['segment_code'] == segment_code
        segment_df = df[mask].iloc[0]

        if not segment_df['is_segment_achievable']:
            gap = segment_df['segment_target_volume'] - segment_df['max_achievable_volume']
            issues.append(
                f"セグメント '{segment_code}': 目標数量が奪取可能数量を{gap:,.0f}本超過"
            )
            print(f"  ❌ {segment_code:12s}: "
                  f"目標={segment_df['segment_target_volume']:,.0f}本, "
                  f"最大可能={segment_df['max_achievable_volume']:,.0f}本 "
                  f"(超過={gap:,.0f}本)")
        else:
            print(f"  ✅ {segment_code:12s}: 実現可能")

    # 2. 拠点別生産能力チェック
    print("\n[2/4] 拠点別生産能力チェック")
    plant_capacity = config['plant_capacity']

    for plant_code in df['plant_code'].unique():
        mask = df['plant_code'] == plant_code
        plant_target_volume = df[mask]['target_volume'].sum()
        capacity = plant_capacity[plant_code]
        utilization = (plant_target_volume / capacity * 100) if capacity > 0 else 0

        if plant_target_volume > capacity:
            gap = plant_target_volume - capacity
            issues.append(
                f"拠点 '{plant_code}': 目標数量が生産能力を{gap:,.0f}本超過 (稼働率{utilization:.1f}%)"
            )
            print(f"  ❌ 拠点{plant_code}: "
                  f"目標={plant_target_volume:,.0f}本, "
                  f"能力={capacity:,.0f}本 "
                  f"(超過={gap:,.0f}本, 稼働率={utilization:.1f}%)")
        else:
            print(f"  ✅ 拠点{plant_code}: "
                  f"目標={plant_target_volume:,.0f}本, "
                  f"能力={capacity:,.0f}本 "
                  f"(稼働率={utilization:.1f}%)")

    # 3. 総販売目標チェック
    print("\n[3/4] 総販売目標チェック")
    total_target_volume = df['target_volume'].sum()
    total_sales_target = config['total_sales_target']
    gap = total_target_volume - total_sales_target
    gap_pct = (gap / total_sales_target * 100) if total_sales_target > 0 else 0

    print(f"  目標総販売数量: {total_target_volume:,.0f}本")
    print(f"  総販売目標: {total_sales_target:,.0f}本")
    print(f"  差異: {gap:+,.0f}本 ({gap_pct:+.1f}%)")

    # ±5%以内を許容範囲とする
    if abs(gap_pct) > 5.0:
        if gap < 0:
            issues.append(
                f"総販売目標不足: {abs(gap):,.0f}本 ({abs(gap_pct):.1f}%)"
            )
            print(f"  ❌ 総販売目標を{abs(gap):,.0f}本下回る")
        else:
            issues.append(
                f"総販売目標超過: {gap:,.0f}本 ({gap_pct:.1f}%)"
            )
            print(f"  ❌ 総販売目標を{gap:,.0f}本超過")
    else:
        print(f"  ✅ 総販売目標の±5%以内")

    # 4. 負の目標数量チェック
    print("\n[4/4] 負の目標数量チェック")
    negative_targets = (df['target_volume'] < 0).sum()
    if negative_targets > 0:
        issues.append(f"負の目標数量: {negative_targets}件")
        print(f"  ❌ 負の目標数量が{negative_targets}件存在")
    else:
        print(f"  ✅ すべての目標数量が非負")

    # 結果サマリー
    print("\n" + "-"*80)
    is_feasible = len(issues) == 0
    if is_feasible:
        print("✅ 実現可能性チェック: すべての制約を満たしています")
    else:
        print(f"❌ 実現可能性チェック: {len(issues)}件の問題が見つかりました")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")

    return is_feasible, issues


# =============================================================================
# 自動調整機能（A-3改善提案）
# =============================================================================

def auto_adjust_targets(
    df: pd.DataFrame,
    config: Dict
) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    目標を自動調整します（A-3改善提案）。

    Parameters
    ----------
    df : pd.DataFrame
        目標計算済みデータ
    config : Dict
        設定ファイルの内容

    Returns
    -------
    Tuple[pd.DataFrame, List[Dict]]
        (調整済みデータ, 調整履歴)
    """
    if not config.get('auto_adjustment', {}).get('enabled', False):
        print("\n自動調整機能は無効化されています")
        return df, []

    print("\n" + "="*80)
    print("自動調整機能（A-3改善提案）")
    print("="*80)

    max_iterations = config['auto_adjustment']['max_iterations']
    reduction_rate = config['auto_adjustment']['reduction_rate']

    print(f"最大イテレーション: {max_iterations}回")
    print(f"削減率: {reduction_rate * 100}%")

    adjustment_history = []
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- イテレーション {iteration}/{max_iterations} ---")

        # 実現可能性チェック
        is_feasible, issues = check_feasibility(df, config)

        if is_feasible:
            print(f"\n✅ イテレーション{iteration}で実現可能な目標を達成")
            break

        print(f"\n🔄 調整実施: {len(issues)}件の問題に対処")

        # 調整前の状態を記録
        before_total = df['target_volume'].sum()

        # 問題のあるセグメント・拠点を特定して調整
        adjusted_segments = set()
        adjusted_plants = set()

        # セグメント別の調整
        for segment_code in df['segment_code'].unique():
            mask = df['segment_code'] == segment_code
            segment_df = df[mask].iloc[0]

            if not segment_df['is_segment_achievable']:
                # 目標数量を削減
                current_target = df.loc[mask, 'target_volume']
                adjusted_target = current_target * (1 - reduction_rate)
                df.loc[mask, 'target_volume'] = adjusted_target

                # セグメント目標も更新
                new_segment_target = adjusted_target.sum()
                df.loc[mask, 'segment_target_volume'] = new_segment_target

                # 再チェック
                max_achievable = segment_df['max_achievable_volume']
                is_now_achievable = new_segment_target <= max_achievable
                df.loc[mask, 'is_segment_achievable'] = is_now_achievable

                adjusted_segments.add(segment_code)
                print(f"  📉 {segment_code:12s}: "
                      f"{current_target.sum():,.0f}本 → {new_segment_target:,.0f}本 "
                      f"({-reduction_rate * 100:.0f}%削減)")

        # 拠点別の調整
        plant_capacity = config['plant_capacity']
        for plant_code in df['plant_code'].unique():
            mask = df['plant_code'] == plant_code
            plant_target_volume = df[mask]['target_volume'].sum()
            capacity = plant_capacity[plant_code]

            if plant_target_volume > capacity:
                # 拠点別の目標数量を削減
                current_target = df.loc[mask, 'target_volume']
                adjusted_target = current_target * (1 - reduction_rate)
                df.loc[mask, 'target_volume'] = adjusted_target

                adjusted_plants.add(plant_code)
                print(f"  📉 拠点{plant_code}: "
                      f"{current_target.sum():,.0f}本 → {adjusted_target.sum():,.0f}本 "
                      f"({-reduction_rate * 100:.0f}%削減)")

        # 調整後の状態を記録
        after_total = df['target_volume'].sum()

        adjustment_history.append({
            'iteration': iteration,
            'before_total': before_total,
            'after_total': after_total,
            'reduction': before_total - after_total,
            'adjusted_segments': list(adjusted_segments),
            'adjusted_plants': list(adjusted_plants),
            'issues_count': len(issues)
        })

        print(f"\n  調整サマリー:")
        print(f"    調整前総数量: {before_total:,.0f}本")
        print(f"    調整後総数量: {after_total:,.0f}本")
        print(f"    削減数量: {before_total - after_total:,.0f}本")

    if iteration >= max_iterations and not is_feasible:
        print(f"\n⚠️ 警告: 最大イテレーション{max_iterations}回に達しましたが、実現可能な目標に到達できませんでした")
        print(f"   手動での調整が必要です")

    return df, adjustment_history


# =============================================================================
# サマリーレポート
# =============================================================================

def generate_summary_report(
    df: pd.DataFrame,
    config: Dict,
    adjustment_history: List[Dict],
    output_dir: str
) -> None:
    """
    実現可能性検証のサマリーレポートを生成します。

    Parameters
    ----------
    df : pd.DataFrame
        調整済みデータ
    config : Dict
        設定ファイルの内容
    adjustment_history : List[Dict]
        調整履歴
    output_dir : str
        出力ディレクトリ
    """
    print("\n" + "="*80)
    print("サマリーレポート生成")
    print("="*80)

    report = []

    # 基本統計
    report.append("# 実現可能性検証サマリー（Step3）\n")
    report.append(f"**作成日**: 2025年12月7日\n")
    report.append("\n---\n")

    # 最終的な実現可能性チェック結果
    is_feasible, issues = check_feasibility(df, config)

    report.append("\n## 最終チェック結果\n")
    if is_feasible:
        report.append("✅ **すべての制約を満たしています**\n")
    else:
        report.append(f"❌ **{len(issues)}件の問題が残っています**\n")
        for i, issue in enumerate(issues, 1):
            report.append(f"{i}. {issue}\n")

    # 自動調整履歴
    if adjustment_history:
        report.append("\n## 自動調整履歴（A-3改善提案）\n")
        report.append(f"- **イテレーション回数**: {len(adjustment_history)}回\n")
        report.append(f"- **削減率**: {config['auto_adjustment']['reduction_rate'] * 100}%/回\n")

        report.append("\n| イテレーション | 調整前 | 調整後 | 削減量 | 問題数 |\n")
        report.append("|---------------|--------|--------|--------|--------|\n")

        for hist in adjustment_history:
            report.append(
                f"| {hist['iteration']} | {hist['before_total']:,.0f}本 | "
                f"{hist['after_total']:,.0f}本 | "
                f"{hist['reduction']:,.0f}本 | {hist['issues_count']}件 |\n"
            )

        # 調整されたセグメント・拠点
        all_adjusted_segments = set()
        all_adjusted_plants = set()
        for hist in adjustment_history:
            all_adjusted_segments.update(hist['adjusted_segments'])
            all_adjusted_plants.update(hist['adjusted_plants'])

        if all_adjusted_segments:
            report.append(f"\n**調整されたセグメント**: {', '.join(all_adjusted_segments)}\n")
        if all_adjusted_plants:
            report.append(f"**調整された拠点**: {', '.join(all_adjusted_plants)}\n")

    # 拠点別サマリー
    report.append("\n## 拠点別サマリー\n")
    report.append("| 拠点 | 目標数量 | 生産能力 | 稼働率 | 状態 |\n")
    report.append("|------|----------|----------|--------|------|\n")

    plant_capacity = config['plant_capacity']
    for plant_code in sorted(df['plant_code'].unique()):
        mask = df['plant_code'] == plant_code
        plant_target = df[mask]['target_volume'].sum()
        capacity = plant_capacity[plant_code]
        utilization = (plant_target / capacity * 100) if capacity > 0 else 0
        status = "✅" if plant_target <= capacity else "❌"

        report.append(
            f"| {plant_code} | {plant_target:,.0f}本 | {capacity:,.0f}本 | "
            f"{utilization:.1f}% | {status} |\n"
        )

    # セグメント別サマリー
    report.append("\n## セグメント別サマリー\n")
    report.append("| セグメント | 目標数量 | 最大可能数量 | 実現可能性 |\n")
    report.append("|-----------|----------|-------------|------------|\n")

    segment_summary = df.groupby('segment_code').agg({
        'segment_target_volume': 'first',
        'max_achievable_volume': 'first',
        'is_segment_achievable': 'first'
    }).reset_index()

    for _, row in segment_summary.iterrows():
        status = "✅ 可能" if row['is_segment_achievable'] else "❌ 要調整"
        report.append(
            f"| {row['segment_code']} | {row['segment_target_volume']:,.0f}本 | "
            f"{row['max_achievable_volume']:,.0f}本 | {status} |\n"
        )

    # 総合サマリー
    report.append("\n## 総合サマリー\n")
    total_target = df['target_volume'].sum()
    total_sales_target = config['total_sales_target']
    gap = total_target - total_sales_target
    gap_pct = (gap / total_sales_target * 100) if total_sales_target > 0 else 0

    report.append(f"- **目標総販売数量**: {total_target:,.0f}本\n")
    report.append(f"- **総販売目標**: {total_sales_target:,.0f}本\n")
    report.append(f"- **差異**: {gap:+,.0f}本 ({gap_pct:+.1f}%)\n")

    # レポート保存
    report_path = os.path.join(output_dir, "step3_feasibility_validation_summary.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report)

    print(f"  ✅ サマリーレポート保存: {report_path}")


# =============================================================================
# メイン処理
# =============================================================================

def main():
    """メイン処理"""
    print("="*80)
    print("製品ポートフォリオ最適化フレームワーク v6 - Step3: 実現可能性検証")
    print("="*80)

    # 設定ファイル読み込み
    print("\n[1/4] 設定ファイル読み込み")
    config = load_config()
    print(f"  ✅ バージョン: {config['version']}")
    print(f"  自動調整: {'有効' if config.get('auto_adjustment', {}).get('enabled', False) else '無効'}")

    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    processed_dir = os.path.join(data_dir, "processed")
    reports_dir = os.path.join(script_dir, "..", "reports")

    # Step2の出力データ読み込み
    print("\n[2/4] Step2出力データ読み込み")
    df = pd.read_csv(os.path.join(processed_dir, "target_calculation_data.csv"))
    print(f"  ✅ データ読み込み: {len(df):,}行")

    # 初回実現可能性チェック
    print("\n[3/4] 初回実現可能性チェック")
    is_feasible_initial, issues_initial = check_feasibility(df, config)

    # 自動調整
    print("\n[4/4] 自動調整")
    df_adjusted, adjustment_history = auto_adjust_targets(df, config)

    # 最終チェック
    is_feasible_final, issues_final = check_feasibility(df_adjusted, config)

    # データ保存
    print("\n" + "="*80)
    print("データ保存")
    print("="*80)
    output_path = os.path.join(processed_dir, "feasibility_validated_data.csv")
    save_csv_with_validation(
        df_adjusted,
        output_path,
        schema_name=None
    )

    # サマリーレポート生成
    generate_summary_report(df_adjusted, config, adjustment_history, reports_dir)

    # 最終サマリー
    print("\n" + "="*80)
    print("✅ Step3: 実現可能性検証完了")
    print("="*80)

    if adjustment_history:
        print(f"  自動調整回数: {len(adjustment_history)}回")
        initial_total = adjustment_history[0]['before_total']
        final_total = adjustment_history[-1]['after_total']
        total_reduction = initial_total - final_total
        print(f"  総削減量: {total_reduction:,.0f}本 ({total_reduction / initial_total * 100:.1f}%)")

    print(f"  最終目標総数量: {df_adjusted['target_volume'].sum():,.0f}本")
    print(f"  実現可能性: {'✅ 達成' if is_feasible_final else '❌ 未達成'}")
    print(f"  出力ファイル: {output_path}")


if __name__ == "__main__":
    main()
