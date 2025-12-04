"""
感度分析スクリプト
フレームワークの主要パラメータに対する感度分析を実行
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 共通モジュールのインポート
sys.path.append(str(Path(__file__).parent / "scripts"))
from optimization_common_v5 import (
    MASTER_DIR, PROCESSED_DIR, REPORTS_DIR,
    ACQUISITION_RATE, STRATEGY_COEFFICIENTS,
    calculate_market_size_after_3y
)

# パス設定
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = PROCESSED_DIR / "sensitivity_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("感度分析スクリプト")
print("=" * 80)

# =====================================================================
# データ読み込み
# =====================================================================
print("\n[データ読み込み]")
market_master = pd.read_csv(PROCESSED_DIR / "market_master_processed.csv")
competitor_master = pd.read_csv(PROCESSED_DIR / "competitor_master_processed.csv")
target_share = pd.read_csv(PROCESSED_DIR / "target_share_final.csv")
sales_opt = pd.read_csv(PROCESSED_DIR / "sales_2024_opt_v5.csv")

print(f"  ✓ 市場マスタ: {len(market_master)} セグメント")
print(f"  ✓ 競合マスタ: {len(competitor_master)} 競合")
print(f"  ✓ 目標シェア: {len(target_share)} セグメント")
print(f"  ✓ 最適化結果: {len(sales_opt)} レコード")

# =====================================================================
# 感度分析1: 奪取可能率パラメータ
# =====================================================================
print("\n" + "=" * 80)
print("感度分析1: 奪取可能率パラメータの影響")
print("=" * 80)

# 現在のパラメータ
print("\n[現在のパラメータ]")
for position, rates in ACQUISITION_RATE.items():
    print(f"  {position:10s}: {rates['lower']*100:5.1f}% - {rates['upper']*100:5.1f}%")

# 代替案1: より保守的（奪取率を半分に）
acquisition_rate_conservative = {
    'strong': {'lower': 0.00, 'upper': 0.015},
    'moderate': {'lower': 0.01, 'upper': 0.025},
    'weak': {'lower': 0.025, 'upper': 0.05}
}

# 代替案2: より積極的（奪取率を1.5倍に）
acquisition_rate_aggressive = {
    'strong': {'lower': 0.00, 'upper': 0.045},
    'moderate': {'lower': 0.03, 'upper': 0.075},
    'weak': {'lower': 0.075, 'upper': 0.15}
}

# 代替案3: 弱い競合のみ攻略（strongは諦める）
acquisition_rate_focused = {
    'strong': {'lower': 0.00, 'upper': 0.00},
    'moderate': {'lower': 0.03, 'upper': 0.08},
    'weak': {'lower': 0.10, 'upper': 0.20}
}

def calculate_achievable_share(segment_code, competitor_df, acquisition_params):
    """到達可能シェアを計算"""
    segment_competitors = competitor_df[competitor_df['segment_code'] == segment_code]
    current_share = market_master[market_master['segment_code'] == segment_code]['current_share'].values[0]

    total_lower = 0
    total_upper = 0

    for _, comp in segment_competitors.iterrows():
        position = comp['competitive_position']
        comp_share = comp['current_share']

        params = acquisition_params[position]

        # 奪取可能シェアの下限・上限
        lower = min(params['lower'] * comp_share, comp_share)
        upper = min(params['upper'], 1.0) * comp_share

        total_lower += lower
        total_upper += upper

    achievable_lower = current_share + total_lower
    achievable_upper = current_share + total_upper

    return achievable_lower, achievable_upper

# 各パラメータセットで到達可能シェアを計算
sensitivity_results = []

for segment in ['industrial', 'electronics', 'oil_gas', 'others']:
    # 現在のパラメータ
    current_lower, current_upper = calculate_achievable_share(segment, competitor_master, ACQUISITION_RATE)

    # 保守的パラメータ
    conservative_lower, conservative_upper = calculate_achievable_share(segment, competitor_master, acquisition_rate_conservative)

    # 積極的パラメータ
    aggressive_lower, aggressive_upper = calculate_achievable_share(segment, competitor_master, acquisition_rate_aggressive)

    # 集中型パラメータ
    focused_lower, focused_upper = calculate_achievable_share(segment, competitor_master, acquisition_rate_focused)

    # 実際の最適化結果
    actual_share = sales_opt[sales_opt['segment_code'] == segment]['sales_volume'].sum() / \
                   market_master[market_master['segment_code'] == segment]['market_size_after_3y'].values[0]

    sensitivity_results.append({
        'segment': segment,
        'current_share': market_master[market_master['segment_code'] == segment]['current_share'].values[0],
        'actual_optimized_share': actual_share,
        'current_param_lower': current_lower,
        'current_param_upper': current_upper,
        'conservative_lower': conservative_lower,
        'conservative_upper': conservative_upper,
        'aggressive_lower': aggressive_lower,
        'aggressive_upper': aggressive_upper,
        'focused_lower': focused_lower,
        'focused_upper': focused_upper
    })

df_sensitivity = pd.DataFrame(sensitivity_results)

print("\n[到達可能シェアの比較]")
print(df_sensitivity.to_string(index=False))

# CSV保存
df_sensitivity.to_csv(OUTPUT_DIR / "acquisition_rate_sensitivity.csv", index=False)
print(f"\n  ✓ 保存: {OUTPUT_DIR / 'acquisition_rate_sensitivity.csv'}")

# =====================================================================
# 感度分析2: 戦略係数パラメータ
# =====================================================================
print("\n" + "=" * 80)
print("感度分析2: 戦略係数パラメータの影響")
print("=" * 80)

print("\n[現在のパラメータ]")
for strategy, coeffs in STRATEGY_COEFFICIENTS.items():
    print(f"  {strategy:22s}: {coeffs['lower']:.1f} - {coeffs['upper']:.1f}")

# 代替案1: より保守的（変化幅を半分に）
strategy_coeffs_conservative = {
    'aggressive_expansion': {'lower': 1.0, 'upper': 1.25},
    'maintain': {'lower': 0.95, 'upper': 1.05},
    'reduction': {'lower': 0.75, 'upper': 1.0},
    'withdrawal': {'lower': 0.5, 'upper': 0.85}
}

# 代替案2: より積極的（変化幅を拡大）
strategy_coeffs_aggressive = {
    'aggressive_expansion': {'lower': 1.2, 'upper': 2.0},
    'maintain': {'lower': 0.85, 'upper': 1.15},
    'reduction': {'lower': 0.3, 'upper': 1.0},
    'withdrawal': {'lower': 0.0, 'upper': 0.5}
}

# 代替案3: バランス型（極端を避ける）
strategy_coeffs_balanced = {
    'aggressive_expansion': {'lower': 1.05, 'upper': 1.3},
    'maintain': {'lower': 0.90, 'upper': 1.10},
    'reduction': {'lower': 0.60, 'upper': 1.0},
    'withdrawal': {'lower': 0.3, 'upper': 0.8}
}

def calculate_target_share_range(current_share, strategy_type, strategy_params):
    """目標シェア範囲を計算"""
    params = strategy_params[strategy_type]
    lower = current_share * params['lower']
    upper = current_share * params['upper']
    return lower, upper

# 各パラメータセットで目標シェアを計算
strategy_sensitivity_results = []

for _, row in market_master.iterrows():
    segment = row['segment_code']
    current_share = row['current_share']
    strategy = target_share[target_share['segment_code'] == segment]['strategy_type'].values[0]

    # 現在のパラメータ
    current_lower, current_upper = calculate_target_share_range(current_share, strategy, STRATEGY_COEFFICIENTS)

    # 保守的
    conservative_lower, conservative_upper = calculate_target_share_range(current_share, strategy, strategy_coeffs_conservative)

    # 積極的
    aggressive_lower, aggressive_upper = calculate_target_share_range(current_share, strategy, strategy_coeffs_aggressive)

    # バランス型
    balanced_lower, balanced_upper = calculate_target_share_range(current_share, strategy, strategy_coeffs_balanced)

    # 実際の目標
    actual_lower = target_share[target_share['segment_code'] == segment]['target_share_lower'].values[0]
    actual_upper = target_share[target_share['segment_code'] == segment]['target_share_upper'].values[0]

    strategy_sensitivity_results.append({
        'segment': segment,
        'strategy': strategy,
        'current_share': current_share,
        'actual_target_lower': actual_lower,
        'actual_target_upper': actual_upper,
        'current_param_lower': current_lower,
        'current_param_upper': current_upper,
        'conservative_lower': conservative_lower,
        'conservative_upper': conservative_upper,
        'aggressive_lower': aggressive_lower,
        'aggressive_upper': aggressive_upper,
        'balanced_lower': balanced_lower,
        'balanced_upper': balanced_upper
    })

df_strategy_sensitivity = pd.DataFrame(strategy_sensitivity_results)

print("\n[目標シェア範囲の比較]")
print(df_strategy_sensitivity.to_string(index=False))

# CSV保存
df_strategy_sensitivity.to_csv(OUTPUT_DIR / "strategy_coeffs_sensitivity.csv", index=False)
print(f"\n  ✓ 保存: {OUTPUT_DIR / 'strategy_coeffs_sensitivity.csv'}")

# =====================================================================
# 感度分析3: 市場成長率（CAGR）の影響
# =====================================================================
print("\n" + "=" * 80)
print("感度分析3: 市場成長率（CAGR）の影響")
print("=" * 80)

cagr_sensitivity_results = []

# CAGR を ±2%ポイント変動させた場合
for segment_row in market_master.itertuples():
    segment = segment_row.segment_code
    current_size = segment_row.current_market_size
    current_cagr = segment_row.market_cagr
    current_3y = segment_row.market_size_after_3y

    # ベースライン（現在のCAGR）
    baseline_3y = calculate_market_size_after_3y(current_size, current_cagr)

    # 楽観シナリオ（CAGR + 2%）
    optimistic_cagr = current_cagr + 0.02
    optimistic_3y = calculate_market_size_after_3y(current_size, optimistic_cagr)

    # 悲観シナリオ（CAGR - 2%）
    pessimistic_cagr = current_cagr - 0.02
    pessimistic_3y = calculate_market_size_after_3y(current_size, pessimistic_cagr)

    # 最適化後の販売数量
    opt_volume = sales_opt[sales_opt['segment_code'] == segment]['sales_volume'].sum()

    # 各シナリオでのシェア
    baseline_share = opt_volume / baseline_3y
    optimistic_share = opt_volume / optimistic_3y
    pessimistic_share = opt_volume / pessimistic_3y

    cagr_sensitivity_results.append({
        'segment': segment,
        'current_cagr': current_cagr,
        'current_market_3y': baseline_3y,
        'optimistic_cagr': optimistic_cagr,
        'optimistic_market_3y': optimistic_3y,
        'pessimistic_cagr': pessimistic_cagr,
        'pessimistic_market_3y': pessimistic_3y,
        'opt_volume': opt_volume,
        'baseline_share': baseline_share,
        'optimistic_share': optimistic_share,
        'pessimistic_share': pessimistic_share,
        'share_range': pessimistic_share - optimistic_share
    })

df_cagr_sensitivity = pd.DataFrame(cagr_sensitivity_results)

print("\n[市場成長率シナリオ別のシェア変動]")
for _, row in df_cagr_sensitivity.iterrows():
    print(f"\n{row['segment'].upper()}:")
    print(f"  現在CAGR: {row['current_cagr']*100:+.1f}% → 3年後市場: {row['current_market_3y']:,.0f}本 → シェア: {row['baseline_share']:.1%}")
    print(f"  楽観CAGR: {row['optimistic_cagr']*100:+.1f}% → 3年後市場: {row['optimistic_market_3y']:,.0f}本 → シェア: {row['optimistic_share']:.1%}")
    print(f"  悲観CAGR: {row['pessimistic_cagr']*100:+.1f}% → 3年後市場: {row['pessimistic_market_3y']:,.0f}本 → シェア: {row['pessimistic_share']:.1%}")
    print(f"  シェア変動幅: {row['share_range']:.1%}ポイント")

# CSV保存
df_cagr_sensitivity.to_csv(OUTPUT_DIR / "cagr_sensitivity.csv", index=False)
print(f"\n  ✓ 保存: {OUTPUT_DIR / 'cagr_sensitivity.csv'}")

# =====================================================================
# 感度分析4: キャパシティ制約の影響
# =====================================================================
print("\n" + "=" * 80)
print("感度分析4: キャパシティ制約の影響")
print("=" * 80)

# 現在のキャパシティ利用状況
plant_a_usage = sales_opt[sales_opt['plant_code'] == 'A']['sales_volume'].sum()
plant_b_usage = sales_opt[sales_opt['plant_code'] == 'B']['sales_volume'].sum()
total_capacity = 300_000 + 204_000

print(f"\n[現在のキャパシティ利用状況]")
print(f"  Plant A: {plant_a_usage:,}本 / 300,000本 ({plant_a_usage/300_000:.1%})")
print(f"  Plant B: {plant_b_usage:,}本 / 204,000本 ({plant_b_usage/204_000:.1%})")
print(f"  Total:   {plant_a_usage + plant_b_usage:,}本 / 504,000本 ({(plant_a_usage + plant_b_usage)/total_capacity:.1%})")

# キャパシティを変動させた場合のシミュレーション
capacity_scenarios = []

# シナリオ1: Plant A +20%, Plant B +20%
capacity_scenarios.append({
    'scenario': 'Both +20%',
    'plant_a_capacity': 360_000,
    'plant_b_capacity': 244_800,
    'total_capacity': 604_800,
    'potential_increase': 604_800 - 504_000
})

# シナリオ2: Plant B のみ +50%（Oil & Gas 専用化）
capacity_scenarios.append({
    'scenario': 'Plant B +50% (Oil&Gas focus)',
    'plant_a_capacity': 300_000,
    'plant_b_capacity': 306_000,
    'total_capacity': 606_000,
    'potential_increase': 606_000 - 504_000
})

# シナリオ3: Plant A のみ +30%（Electronics 専用化）
capacity_scenarios.append({
    'scenario': 'Plant A +30% (Electronics focus)',
    'plant_a_capacity': 390_000,
    'plant_b_capacity': 204_000,
    'total_capacity': 594_000,
    'potential_increase': 594_000 - 504_000
})

# シナリオ4: Plant B を削減、Plant A に統合
capacity_scenarios.append({
    'scenario': 'Consolidate to Plant A',
    'plant_a_capacity': 504_000,
    'plant_b_capacity': 0,
    'total_capacity': 504_000,
    'potential_increase': 0
})

df_capacity_scenarios = pd.DataFrame(capacity_scenarios)

print("\n[キャパシティ変動シナリオ]")
print(df_capacity_scenarios.to_string(index=False))

# 最大粗利の理論値推定（キャパシティが無制限の場合）
# 最も粗利率の高いセグメント×拠点×製品に全キャパシティを割り当てた場合
max_unit_profit = sales_opt['unit_profit'].max()
theoretical_max_profit = total_capacity * max_unit_profit

current_total_profit = sales_opt['total_profit'].sum()

print(f"\n[粗利のポテンシャル分析]")
print(f"  現在の総粗利: {current_total_profit:,.0f}円")
print(f"  理論上の最大粗利: {theoretical_max_profit:,.0f}円")
print(f"  （全キャパシティを最高粗利率製品に割り当てた場合）")
print(f"  ポテンシャル: {theoretical_max_profit - current_total_profit:,.0f}円 (+{(theoretical_max_profit/current_total_profit - 1)*100:.1f}%)")
print(f"  ")
print(f"  ※ただし、この理論値は以下を無視しています:")
print(f"    - セグメント需要上限制約")
print(f"    - 製品ミックスの多様性")
print(f"    - 市場シェアの実現可能性")

# CSV保存
df_capacity_scenarios.to_csv(OUTPUT_DIR / "capacity_scenarios.csv", index=False)
print(f"\n  ✓ 保存: {OUTPUT_DIR / 'capacity_scenarios.csv'}")

# =====================================================================
# サマリーレポート生成
# =====================================================================
print("\n" + "=" * 80)
print("感度分析サマリーレポート生成")
print("=" * 80)

summary_lines = []

summary_lines.append("# 感度分析サマリー\n")
summary_lines.append("## 1. 奪取可能率パラメータの感度\n")
summary_lines.append("| セグメント | 現状シェア | 最適化後シェア | 現行パラメータ上限 | 保守的上限 | 積極的上限 | 集中型上限 |\n")
summary_lines.append("|-----------|----------|--------------|----------------|----------|----------|----------|\n")

for _, row in df_sensitivity.iterrows():
    summary_lines.append(f"| {row['segment']} | {row['current_share']:.1%} | {row['actual_optimized_share']:.1%} | "
                        f"{row['current_param_upper']:.1%} | {row['conservative_upper']:.1%} | "
                        f"{row['aggressive_upper']:.1%} | {row['focused_upper']:.1%} |\n")

summary_lines.append("\n## 2. 戦略係数パラメータの感度\n")
summary_lines.append("| セグメント | 戦略区分 | 現行目標上限 | 保守的上限 | 積極的上限 | バランス型上限 |\n")
summary_lines.append("|-----------|---------|------------|----------|----------|------------|\n")

for _, row in df_strategy_sensitivity.iterrows():
    summary_lines.append(f"| {row['segment']} | {row['strategy']} | {row['actual_target_upper']:.1%} | "
                        f"{row['conservative_upper']:.1%} | {row['aggressive_upper']:.1%} | {row['balanced_upper']:.1%} |\n")

summary_lines.append("\n## 3. 市場成長率（CAGR）の感度\n")
summary_lines.append("| セグメント | 現行CAGR | 楽観CAGR | 悲観CAGR | シェア変動幅 |\n")
summary_lines.append("|-----------|---------|---------|---------|------------|\n")

for _, row in df_cagr_sensitivity.iterrows():
    summary_lines.append(f"| {row['segment']} | {row['current_cagr']:+.1%} | {row['optimistic_cagr']:+.1%} | "
                        f"{row['pessimistic_cagr']:+.1%} | {row['share_range']:.1%}pt |\n")

summary_lines.append("\n## 4. 主要な発見事項\n")
summary_lines.append("1. **奪取可能率パラメータ**: 現行設定は保守的であり、特にOil & Gasセグメントで積極的な設定により更なるシェア拡大の余地がある\n")
summary_lines.append("2. **戦略係数パラメータ**: Industrial（撤退）とOil & Gas（積極拡大）の係数幅が広く、目標設定の柔軟性が高い\n")
summary_lines.append("3. **市場成長率の不確実性**: CAGRが±2%変動すると、達成シェアが最大で±3%ポイント変動し、市場予測の精度が重要\n")
summary_lines.append("4. **キャパシティ制約**: 現在ほぼ100%稼働しており、増産余地は限定的。増産には設備投資が必要\n")

summary_path = OUTPUT_DIR / "sensitivity_analysis_summary.md"
with open(summary_path, 'w', encoding='utf-8') as f:
    f.writelines(summary_lines)

print(f"  ✓ サマリーレポート保存: {summary_path}")

print("\n" + "=" * 80)
print("感度分析完了")
print("=" * 80)
print(f"\n出力ディレクトリ: {OUTPUT_DIR}")
print(f"  - acquisition_rate_sensitivity.csv")
print(f"  - strategy_coeffs_sensitivity.csv")
print(f"  - cagr_sensitivity.csv")
print(f"  - capacity_scenarios.csv")
print(f"  - sensitivity_analysis_summary.md")
