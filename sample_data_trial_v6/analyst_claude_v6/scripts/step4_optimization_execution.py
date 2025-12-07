"""
製品ポートフォリオ最適化フレームワーク v6 - Step4: 最適化実行

このスクリプトは、線形計画法による製品ポートフォリオ最適化を実行します。
- 4つ組タプル決定変数: (product_code, plant_code, segment_code, customer_code)
- A-4改善提案: 診断機能（制約チェックと具体的な提案）
- PuLPによる線形計画法実装

作成日: 2025年12月7日
バージョン: 6.0
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Dict, List, Tuple
from pulp import *

# 共通ユーティリティのインポート
from optimization_common_v6 import (
    load_config,
    save_csv_with_validation,
    display_dataframe_summary
)


# =============================================================================
# 診断機能（A-4改善提案）
# =============================================================================

def diagnose_constraints(
    df: pd.DataFrame,
    config: Dict
) -> Dict[str, any]:
    """
    最適化実行前に制約を診断します（A-4改善提案）。

    Parameters
    ----------
    df : pd.DataFrame
        検証済みデータ
    config : Dict
        設定ファイルの内容

    Returns
    -------
    Dict[str, any]
        診断結果
    """
    if not config.get('diagnostics', {}).get('enabled', False):
        print("\n診断機能は無効化されています")
        return {}

    print("\n" + "="*80)
    print("最適化前診断（A-4改善提案）")
    print("="*80)

    diagnostics = {
        'feasibility_score': 0.0,
        'warnings': [],
        'suggestions': [],
        'constraint_analysis': {}
    }

    # 1. 拠点別生産能力の余裕度
    print("\n[1/5] 拠点別生産能力の余裕度分析")
    plant_capacity = config['plant_capacity']
    plant_analysis = []

    for plant_code in sorted(df['plant_code'].unique()):
        mask = df['plant_code'] == plant_code
        current_volume = df[mask]['sales_volume'].sum()
        target_volume = df[mask]['target_volume'].sum()
        capacity = plant_capacity[plant_code]

        current_util = (current_volume / capacity * 100) if capacity > 0 else 0
        target_util = (target_volume / capacity * 100) if capacity > 0 else 0
        margin = capacity - target_volume

        plant_analysis.append({
            'plant_code': plant_code,
            'capacity': capacity,
            'current_volume': current_volume,
            'target_volume': target_volume,
            'current_utilization': current_util,
            'target_utilization': target_util,
            'margin': margin,
            'margin_pct': (margin / capacity * 100) if capacity > 0 else 0
        })

        print(f"  拠点{plant_code}:")
        print(f"    生産能力: {capacity:,.0f}本")
        print(f"    現状数量: {current_volume:,.0f}本 (稼働率 {current_util:.1f}%)")
        print(f"    目標数量: {target_volume:,.0f}本 (稼働率 {target_util:.1f}%)")
        print(f"    余裕: {margin:+,.0f}本 ({margin / capacity * 100:+.1f}%)")

        if margin < 0:
            diagnostics['warnings'].append(
                f"拠点{plant_code}が生産能力を{abs(margin):,.0f}本超過"
            )
            diagnostics['suggestions'].append(
                f"拠点{plant_code}の製品を他拠点に振り分けるか、目標を削減してください"
            )
        elif margin < capacity * 0.1:
            diagnostics['warnings'].append(
                f"拠点{plant_code}の余裕が{margin / capacity * 100:.1f}%と少ない"
            )

    diagnostics['constraint_analysis']['plant_capacity'] = plant_analysis

    # 2. セグメント別の目標実現可能性
    print("\n[2/5] セグメント別目標実現可能性")
    segment_analysis = []

    for segment_code in sorted(df['segment_code'].unique()):
        mask = df['segment_code'] == segment_code
        segment_df = df[mask].iloc[0]

        target_volume = segment_df['segment_target_volume']
        max_achievable = segment_df['max_achievable_volume']
        gap = max_achievable - target_volume
        feasibility_ratio = (target_volume / max_achievable) if max_achievable > 0 else 0

        segment_analysis.append({
            'segment_code': segment_code,
            'target_volume': target_volume,
            'max_achievable': max_achievable,
            'gap': gap,
            'feasibility_ratio': feasibility_ratio
        })

        print(f"  {segment_code}:")
        print(f"    目標数量: {target_volume:,.0f}本")
        print(f"    最大可能: {max_achievable:,.0f}本")
        print(f"    余裕: {gap:+,.0f}本 (実現可能率 {feasibility_ratio * 100:.1f}%)")

        if gap < 0:
            diagnostics['warnings'].append(
                f"セグメント{segment_code}が最大可能数量を{abs(gap):,.0f}本超過"
            )
            diagnostics['suggestions'].append(
                f"セグメント{segment_code}の戦略係数を下げるか、競合奪取率を見直してください"
            )

    diagnostics['constraint_analysis']['segment_feasibility'] = segment_analysis

    # 3. 製品×拠点の組み合わせ分析
    print("\n[3/5] 製品×拠点組み合わせ分析")
    product_plant_combos = df.groupby(['product_code', 'plant_code']).size().reset_index(name='count')
    total_products = df['product_code'].nunique()
    single_plant_products = product_plant_combos[product_plant_combos['count'] > 0].groupby('product_code').size()
    dual_plant_products = (single_plant_products == 2).sum()

    print(f"  総製品数: {total_products}")
    print(f"  両拠点生産製品: {dual_plant_products} ({dual_plant_products / total_products * 100:.1f}%)")
    print(f"  単一拠点生産製品: {total_products - dual_plant_products} ({(total_products - dual_plant_products) / total_products * 100:.1f}%)")

    # 4. 粗利率の分布分析
    print("\n[4/5] 粗利率分布分析")
    margin_stats = df['margin_rate'].describe()
    print(f"  平均粗利率: {margin_stats['mean'] * 100:.1f}%")
    print(f"  中央値粗利率: {margin_stats['50%'] * 100:.1f}%")
    print(f"  最小粗利率: {margin_stats['min'] * 100:.1f}%")
    print(f"  最大粗利率: {margin_stats['max'] * 100:.1f}%")

    low_margin_count = (df['margin_rate'] < 0.1).sum()
    if low_margin_count > 0:
        diagnostics['warnings'].append(
            f"{low_margin_count}件の組み合わせで粗利率が10%未満"
        )
        diagnostics['suggestions'].append(
            f"低粗利率製品の価格見直しまたは製造中止を検討してください"
        )

    # 5. 総合実現可能性スコア
    print("\n[5/5] 総合実現可能性スコア")

    # スコア計算（0-100点）
    score = 100.0

    # 拠点能力制約違反: -20点/件
    plant_violations = sum(1 for p in plant_analysis if p['margin'] < 0)
    score -= plant_violations * 20

    # セグメント制約違反: -15点/件
    segment_violations = sum(1 for s in segment_analysis if s['gap'] < 0)
    score -= segment_violations * 15

    # 拠点余裕不足（<10%）: -10点/件
    low_margin_plants = sum(1 for p in plant_analysis if 0 <= p['margin_pct'] < 10)
    score -= low_margin_plants * 10

    # 低粗利率製品: -5点（10%超の場合）
    if low_margin_count / len(df) > 0.1:
        score -= 5

    score = max(0, score)  # 最低0点

    diagnostics['feasibility_score'] = score

    print(f"\n  📊 総合実現可能性スコア: {score:.0f}/100点")

    if score >= 80:
        print(f"  ✅ 優良: 最適化の実行に問題ありません")
    elif score >= 60:
        print(f"  ⚠️  注意: 一部の制約に問題がありますが、最適化可能です")
    else:
        print(f"  ❌ 要改善: 多くの制約違反があります。データを見直してください")

    # サマリー
    print(f"\n  警告件数: {len(diagnostics['warnings'])}件")
    print(f"  提案件数: {len(diagnostics['suggestions'])}件")

    if diagnostics['suggestions']:
        print(f"\n  💡 改善提案:")
        for i, suggestion in enumerate(diagnostics['suggestions'], 1):
            print(f"    {i}. {suggestion}")

    return diagnostics


# =============================================================================
# 最適化モデル構築
# =============================================================================

def build_optimization_model(
    df: pd.DataFrame,
    config: Dict
) -> Tuple[LpProblem, Dict]:
    """
    最適化モデルを構築します。

    Parameters
    ----------
    df : pd.DataFrame
        検証済みデータ
    config : Dict
        設定ファイルの内容

    Returns
    -------
    Tuple[LpProblem, Dict]
        (最適化モデル, 決定変数辞書)
    """
    print("\n" + "="*80)
    print("最適化モデル構築")
    print("="*80)

    # 最適化問題の作成（目的: 総粗利最大化）
    model = LpProblem("Portfolio_Optimization_v6", LpMaximize)

    # 決定変数: 製品×拠点×セグメント×顧客ごとの販売数量
    # 4つ組タプル (product_code, plant_code, segment_code, customer_code)
    decision_vars = {}

    print(f"\n[1/4] 決定変数の作成")
    for idx, row in df.iterrows():
        var_name = f"x_{row['product_code']}_{row['plant_code']}_{row['segment_code']}_{row['customer_code']}"
        decision_vars[idx] = LpVariable(
            var_name,
            lowBound=0,
            cat='Continuous'
        )

    print(f"  ✅ 決定変数数: {len(decision_vars):,}個")
    print(f"      4つ組タプル: (product_code, plant_code, segment_code, customer_code)")

    # 目的関数: 総粗利最大化
    print(f"\n[2/4] 目的関数の設定")
    objective = lpSum([
        decision_vars[idx] * row['unit_profit']
        for idx, row in df.iterrows()
    ])
    model += objective
    print(f"  ✅ 目的関数: 総粗利最大化 = Σ(販売数量 × 単位粗利)")

    # 制約条件
    print(f"\n[3/4] 制約条件の追加")
    constraint_count = 0

    # 制約1: 拠点別生産能力制約
    plant_capacity = config['plant_capacity']
    for plant_code in df['plant_code'].unique():
        mask = df['plant_code'] == plant_code
        indices = df[mask].index

        model += (
            lpSum([decision_vars[idx] for idx in indices]) <= plant_capacity[plant_code],
            f"PlantCapacity_{plant_code}"
        )
        constraint_count += 1

    print(f"  ✅ 拠点別生産能力制約: {len(df['plant_code'].unique())}件")

    # 制約2: セグメント別目標数量制約（範囲制約: 目標±10%）
    for segment_code in df['segment_code'].unique():
        mask = df['segment_code'] == segment_code
        indices = df[mask].index
        segment_target = df[mask]['segment_target_volume'].iloc[0]

        # 下限: 目標の90%
        model += (
            lpSum([decision_vars[idx] for idx in indices]) >= segment_target * 0.9,
            f"SegmentMin_{segment_code}"
        )

        # 上限: 最大可能数量
        max_achievable = df[mask]['max_achievable_volume'].iloc[0]
        model += (
            lpSum([decision_vars[idx] for idx in indices]) <= max_achievable,
            f"SegmentMax_{segment_code}"
        )

        constraint_count += 2

    print(f"  ✅ セグメント別目標数量制約: {len(df['segment_code'].unique()) * 2}件 (下限+上限)")

    # 制約3: 総販売目標制約（±10%の範囲）
    total_sales_target = config['total_sales_target']
    model += (
        lpSum([decision_vars[idx] for idx in df.index]) >= total_sales_target * 0.9,
        "TotalSalesMin"
    )
    model += (
        lpSum([decision_vars[idx] for idx in df.index]) <= total_sales_target * 1.1,
        "TotalSalesMax"
    )
    constraint_count += 2

    print(f"  ✅ 総販売目標制約: 2件 (下限+上限)")

    print(f"\n[4/4] モデル構築完了")
    print(f"  総制約数: {constraint_count}件")

    return model, decision_vars


# =============================================================================
# 最適化実行
# =============================================================================

def solve_optimization(
    model: LpProblem,
    decision_vars: Dict,
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    最適化を実行し、結果をDataFrameに格納します。

    Parameters
    ----------
    model : LpProblem
        最適化モデル
    decision_vars : Dict
        決定変数辞書
    df : pd.DataFrame
        入力データ

    Returns
    -------
    pd.DataFrame
        最適化結果
    """
    print("\n" + "="*80)
    print("最適化実行")
    print("="*80)

    # ソルバーの実行
    print(f"\nソルバー実行中...")
    solver = PULP_CBC_CMD(msg=1, timeLimit=300)  # 5分のタイムリミット
    status = model.solve(solver)

    # 結果の確認
    print(f"\n最適化ステータス: {LpStatus[status]}")

    if status != LpStatusOptimal:
        print(f"⚠️ 警告: 最適解が見つかりませんでした")
        if status == LpStatusInfeasible:
            print(f"  制約が矛盾しています。制約条件を緩和してください")
        elif status == LpStatusUnbounded:
            print(f"  問題が非有界です。制約条件を追加してください")
        return df

    # 結果の取得
    print(f"\n結果の抽出中...")
    optimized_volumes = []
    for idx in df.index:
        optimized_volumes.append(decision_vars[idx].varValue if decision_vars[idx].varValue else 0.0)

    df['optimized_volume'] = optimized_volumes
    df['optimized_profit'] = df['optimized_volume'] * df['unit_profit']

    # 最適化前後の比較
    df['volume_change'] = df['optimized_volume'] - df['target_volume']
    df['volume_change_pct'] = (df['volume_change'] / df['target_volume'] * 100).replace([np.inf, -np.inf], 0)
    df['profit_change'] = df['optimized_profit'] - df['total_profit']

    # サマリー
    print(f"\n" + "="*80)
    print(f"最適化結果サマリー")
    print(f"="*80)

    total_optimized_volume = df['optimized_volume'].sum()
    total_optimized_profit = df['optimized_profit'].sum()
    total_current_profit = df['total_profit'].sum()
    profit_improvement = total_optimized_profit - total_current_profit
    profit_improvement_pct = (profit_improvement / total_current_profit * 100) if total_current_profit > 0 else 0

    print(f"\n販売数量:")
    print(f"  現状: {df['sales_volume'].sum():,.0f}本")
    print(f"  目標: {df['target_volume'].sum():,.0f}本")
    print(f"  最適化: {total_optimized_volume:,.0f}本")

    print(f"\n総粗利:")
    print(f"  現状: ¥{total_current_profit:,.0f}")
    print(f"  最適化: ¥{total_optimized_profit:,.0f}")
    print(f"  改善: ¥{profit_improvement:+,.0f} ({profit_improvement_pct:+.1f}%)")

    # 拠点別サマリー
    print(f"\n拠点別最適化結果:")
    for plant_code in sorted(df['plant_code'].unique()):
        mask = df['plant_code'] == plant_code
        plant_volume = df[mask]['optimized_volume'].sum()
        plant_profit = df[mask]['optimized_profit'].sum()
        print(f"  拠点{plant_code}: {plant_volume:,.0f}本, 粗利¥{plant_profit:,.0f}")

    # セグメント別サマリー
    print(f"\nセグメント別最適化結果:")
    for segment_code in sorted(df['segment_code'].unique()):
        mask = df['segment_code'] == segment_code
        segment_volume = df[mask]['optimized_volume'].sum()
        segment_profit = df[mask]['optimized_profit'].sum()
        print(f"  {segment_code}: {segment_volume:,.0f}本, 粗利¥{segment_profit:,.0f}")

    return df


# =============================================================================
# 最適化レポート生成
# =============================================================================

def generate_optimization_report(
    df: pd.DataFrame,
    diagnostics: Dict,
    config: Dict,
    output_dir: str
) -> None:
    """
    最適化結果の詳細レポートを生成します。

    Parameters
    ----------
    df : pd.DataFrame
        最適化結果
    diagnostics : Dict
        診断結果
    config : Dict
        設定ファイルの内容
    output_dir : str
        出力ディレクトリ
    """
    print("\n" + "="*80)
    print("最適化レポート生成")
    print("="*80)

    report = []

    # ヘッダー
    report.append("# 製品ポートフォリオ最適化レポート v6\n")
    report.append(f"**作成日**: 2025年12月7日\n")
    report.append("\n---\n")

    # エグゼクティブサマリー
    report.append("\n## エグゼクティブサマリー\n")

    total_current_profit = df['total_profit'].sum()
    total_optimized_profit = df['optimized_profit'].sum()
    profit_improvement = total_optimized_profit - total_current_profit
    profit_improvement_pct = (profit_improvement / total_current_profit * 100) if total_current_profit > 0 else 0

    total_current_volume = df['sales_volume'].sum()
    total_optimized_volume = df['optimized_volume'].sum()
    volume_change = total_optimized_volume - total_current_volume

    report.append(f"- **総粗利改善**: ¥{profit_improvement:+,.0f} ({profit_improvement_pct:+.1f}%)\n")
    report.append(f"- **現状総粗利**: ¥{total_current_profit:,.0f}\n")
    report.append(f"- **最適化後総粗利**: ¥{total_optimized_profit:,.0f}\n")
    report.append(f"- **総販売数量**: {total_current_volume:,.0f}本 → {total_optimized_volume:,.0f}本 ({volume_change:+,.0f}本)\n")

    # 診断結果
    if diagnostics:
        report.append(f"\n## 最適化前診断結果（A-4改善提案）\n")
        report.append(f"- **実現可能性スコア**: {diagnostics['feasibility_score']:.0f}/100点\n")
        report.append(f"- **警告件数**: {len(diagnostics['warnings'])}件\n")
        report.append(f"- **改善提案**: {len(diagnostics['suggestions'])}件\n")

        if diagnostics['suggestions']:
            report.append(f"\n### 改善提案\n")
            for i, suggestion in enumerate(diagnostics['suggestions'], 1):
                report.append(f"{i}. {suggestion}\n")

    # 拠点別詳細
    report.append(f"\n## 拠点別最適化結果\n")
    report.append("| 拠点 | 現状数量 | 最適化数量 | 増減 | 現状粗利 | 最適化粗利 | 粗利改善 | 稼働率 |\n")
    report.append("|------|----------|-----------|------|----------|-----------|----------|--------|\n")

    plant_capacity = config['plant_capacity']
    for plant_code in sorted(df['plant_code'].unique()):
        mask = df['plant_code'] == plant_code
        current_vol = df[mask]['sales_volume'].sum()
        opt_vol = df[mask]['optimized_volume'].sum()
        vol_change = opt_vol - current_vol

        current_profit = df[mask]['total_profit'].sum()
        opt_profit = df[mask]['optimized_profit'].sum()
        profit_change = opt_profit - current_profit

        capacity = plant_capacity[plant_code]
        utilization = (opt_vol / capacity * 100) if capacity > 0 else 0

        report.append(
            f"| {plant_code} | {current_vol:,.0f}本 | {opt_vol:,.0f}本 | "
            f"{vol_change:+,.0f}本 | ¥{current_profit:,.0f} | ¥{opt_profit:,.0f} | "
            f"¥{profit_change:+,.0f} | {utilization:.1f}% |\n"
        )

    # セグメント別詳細
    report.append(f"\n## セグメント別最適化結果\n")
    report.append("| セグメント | 戦略 | 現状数量 | 最適化数量 | 目標数量 | 達成率 | 現状粗利 | 最適化粗利 |\n")
    report.append("|-----------|------|----------|-----------|----------|--------|----------|------------|\n")

    for segment_code in sorted(df['segment_code'].unique()):
        mask = df['segment_code'] == segment_code
        segment_df = df[mask]

        strategy = segment_df['strategy_type'].iloc[0]
        current_vol = segment_df['sales_volume'].sum()
        opt_vol = segment_df['optimized_volume'].sum()
        target_vol = segment_df['segment_target_volume'].iloc[0]
        achievement = (opt_vol / target_vol * 100) if target_vol > 0 else 0

        current_profit = segment_df['total_profit'].sum()
        opt_profit = segment_df['optimized_profit'].sum()

        report.append(
            f"| {segment_code} | {strategy} | {current_vol:,.0f}本 | "
            f"{opt_vol:,.0f}本 | {target_vol:,.0f}本 | {achievement:.1f}% | "
            f"¥{current_profit:,.0f} | ¥{opt_profit:,.0f} |\n"
        )

    # トップ10改善製品
    report.append(f"\n## トップ10粗利改善製品\n")
    top_improvements = df.nlargest(10, 'profit_change')[
        ['product_code', 'plant_code', 'segment_code', 'customer_code',
         'sales_volume', 'optimized_volume', 'volume_change',
         'total_profit', 'optimized_profit', 'profit_change']
    ]

    report.append("| 製品 | 拠点 | セグメント | 顧客 | 現状数量 | 最適化数量 | 粗利改善 |\n")
    report.append("|------|------|-----------|------|----------|-----------|----------|\n")

    for _, row in top_improvements.iterrows():
        report.append(
            f"| {row['product_code']} | {row['plant_code']} | {row['segment_code']} | "
            f"{row['customer_code']} | {row['sales_volume']:,.0f}本 | "
            f"{row['optimized_volume']:,.0f}本 | ¥{row['profit_change']:+,.0f} |\n"
        )

    # レポート保存
    report_path = os.path.join(output_dir, "portfolio_optimization_v6_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report)

    print(f"  ✅ 最適化レポート保存: {report_path}")


# =============================================================================
# メイン処理
# =============================================================================

def main():
    """メイン処理"""
    print("="*80)
    print("製品ポートフォリオ最適化フレームワーク v6 - Step4: 最適化実行")
    print("="*80)

    # 設定ファイル読み込み
    print("\n[1/6] 設定ファイル読み込み")
    config = load_config()
    print(f"  ✅ バージョン: {config['version']}")
    print(f"  診断機能: {'有効' if config.get('diagnostics', {}).get('enabled', False) else '無効'}")

    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    processed_dir = os.path.join(data_dir, "processed")
    reports_dir = os.path.join(script_dir, "..", "reports")

    # Step3の出力データ読み込み
    print("\n[2/6] Step3出力データ読み込み")
    df = pd.read_csv(os.path.join(processed_dir, "feasibility_validated_data.csv"))
    display_dataframe_summary(df, "Step3出力データ")

    # 診断
    print("\n[3/6] 最適化前診断")
    diagnostics = diagnose_constraints(df, config)

    # 最適化モデル構築
    print("\n[4/6] 最適化モデル構築")
    model, decision_vars = build_optimization_model(df, config)

    # 最適化実行
    print("\n[5/6] 最適化実行")
    df_optimized = solve_optimization(model, decision_vars, df)

    # データ保存
    print("\n[6/6] データ保存")
    output_path = os.path.join(processed_dir, "optimization_result.csv")
    save_csv_with_validation(
        df_optimized,
        output_path,
        schema_name=None
    )

    # 最適化レポート生成
    generate_optimization_report(df_optimized, diagnostics, config, reports_dir)

    # 最終サマリー
    print("\n" + "="*80)
    print("✅ Step4: 最適化実行完了")
    print("="*80)

    total_profit_improvement = df_optimized['optimized_profit'].sum() - df_optimized['total_profit'].sum()
    improvement_pct = (total_profit_improvement / df_optimized['total_profit'].sum() * 100)

    print(f"  総粗利改善: ¥{total_profit_improvement:+,.0f} ({improvement_pct:+.1f}%)")
    print(f"  出力ファイル: {output_path}")
    print(f"  レポート: {os.path.join(reports_dir, 'portfolio_optimization_v6_report.md')}")


if __name__ == "__main__":
    main()
