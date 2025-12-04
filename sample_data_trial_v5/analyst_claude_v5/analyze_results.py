"""
最適化結果の詳細分析スクリプト
"""

import pandas as pd
import numpy as np
from pathlib import Path

# パス設定
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
MASTER_DIR = DATA_DIR / "master"
PROCESSED_DIR = DATA_DIR / "processed"

# データ読み込み
print("=" * 80)
print("データ読み込み")
print("=" * 80)

# 現状販売データ
sales_current = pd.read_csv(RAW_DIR / "sales_2024.csv")
# 製品×拠点×セグメント単位で集計
current_agg = sales_current.groupby(['product_code', 'plant', 'segment'], as_index=False).agg({
    'sales_qty': 'sum',
    'unit_price': lambda x: np.average(x, weights=sales_current.loc[x.index, 'sales_qty']),
    'unit_cost': lambda x: np.average(x, weights=sales_current.loc[x.index, 'sales_qty'])
})
current_agg['unit_profit'] = current_agg['unit_price'] - current_agg['unit_cost']
current_agg['total_profit'] = current_agg['sales_qty'] * current_agg['unit_profit']
current_agg.rename(columns={'plant': 'plant_code', 'segment': 'segment_code'}, inplace=True)

# 最適化後データ
sales_opt = pd.read_csv(PROCESSED_DIR / "sales_2024_opt_v5.csv")

# 市場マスタ
market_master = pd.read_csv(PROCESSED_DIR / "market_master_processed.csv")

# 目標シェア
target_share = pd.read_csv(PROCESSED_DIR / "target_share_final.csv")

print(f"現状データ: {len(current_agg)} レコード")
print(f"最適化後データ: {len(sales_opt)} レコード")
print(f"市場マスタ: {len(market_master)} セグメント")

# =====================================================================
# セグメント別分析
# =====================================================================
print("\n" + "=" * 80)
print("セグメント別分析")
print("=" * 80)

segment_analysis = []

for segment in ['industrial', 'electronics', 'oil_gas', 'others']:
    # 現状
    current_seg = current_agg[current_agg['segment_code'] == segment]
    current_qty = current_seg['sales_qty'].sum()
    current_profit = current_seg['total_profit'].sum()

    # 最適化後
    opt_seg = sales_opt[sales_opt['segment_code'] == segment]
    opt_qty = opt_seg['sales_volume'].sum()
    opt_profit = opt_seg['total_profit'].sum()

    # 市場情報
    market_info = market_master[market_master['segment_code'] == segment].iloc[0]
    market_size_3y = market_info['market_size_after_3y']
    current_share = market_info['current_share']

    # 目標シェア情報
    target_info = target_share[target_share['segment_code'] == segment].iloc[0]
    strategy = target_info['strategy_type']
    target_lower = target_info['target_share_lower']
    target_upper = target_info['target_share_upper']

    # 最適化後シェア
    opt_share = opt_qty / market_size_3y

    # 変化
    qty_change = opt_qty - current_qty
    qty_change_rate = (qty_change / current_qty * 100) if current_qty > 0 else 0
    profit_change = opt_profit - current_profit
    profit_change_rate = (profit_change / current_profit * 100) if current_profit > 0 else 0

    segment_analysis.append({
        'segment': segment,
        'strategy': strategy,
        'current_qty': current_qty,
        'opt_qty': opt_qty,
        'qty_change': qty_change,
        'qty_change_rate': qty_change_rate,
        'current_share': current_share,
        'opt_share': opt_share,
        'target_lower': target_lower,
        'target_upper': target_upper,
        'current_profit': current_profit,
        'opt_profit': opt_profit,
        'profit_change': profit_change,
        'profit_change_rate': profit_change_rate,
        'market_size_3y': market_size_3y
    })

    print(f"\n【{segment.upper()}】")
    print(f"  戦略区分: {strategy}")
    print(f"  3年後市場規模: {market_size_3y:,.0f}本")
    print(f"  現状販売数量: {current_qty:,.0f}本 (シェア: {current_share:.1%})")
    print(f"  最適化後販売数量: {opt_qty:,.0f}本 (シェア: {opt_share:.1%})")
    print(f"  目標シェア: {target_lower:.1%} 〜 {target_upper:.1%}")
    print(f"  数量変化: {qty_change:+,.0f}本 ({qty_change_rate:+.1f}%)")
    print(f"  現状粗利: {current_profit:,.0f}円")
    print(f"  最適化後粗利: {opt_profit:,.0f}円")
    print(f"  粗利変化: {profit_change:+,.0f}円 ({profit_change_rate:+.1f}%)")

df_segment_analysis = pd.DataFrame(segment_analysis)

# =====================================================================
# 拠点別分析
# =====================================================================
print("\n" + "=" * 80)
print("拠点別分析")
print("=" * 80)

plant_capacity = {'A': 300_000, 'B': 204_000}
plant_analysis = []

for plant in ['A', 'B']:
    # 現状
    current_plant = current_agg[current_agg['plant_code'] == plant]
    current_qty = current_plant['sales_qty'].sum()
    current_profit = current_plant['total_profit'].sum()
    current_utilization = current_qty / plant_capacity[plant]

    # 最適化後
    opt_plant = sales_opt[sales_opt['plant_code'] == plant]
    opt_qty = opt_plant['sales_volume'].sum()
    opt_profit = opt_plant['total_profit'].sum()
    opt_utilization = opt_qty / plant_capacity[plant]

    # セグメント別構成（最適化後）
    segment_composition = opt_plant.groupby('segment_code')['sales_volume'].sum().to_dict()

    plant_analysis.append({
        'plant': plant,
        'capacity': plant_capacity[plant],
        'current_qty': current_qty,
        'opt_qty': opt_qty,
        'current_utilization': current_utilization,
        'opt_utilization': opt_utilization,
        'current_profit': current_profit,
        'opt_profit': opt_profit,
        'segment_composition': segment_composition
    })

    print(f"\n【Plant {plant}】")
    print(f"  キャパシティ: {plant_capacity[plant]:,.0f}本")
    print(f"  現状生産数量: {current_qty:,.0f}本 (稼働率: {current_utilization:.1%})")
    print(f"  最適化後生産数量: {opt_qty:,.0f}本 (稼働率: {opt_utilization:.1%})")
    print(f"  現状粗利: {current_profit:,.0f}円")
    print(f"  最適化後粗利: {opt_profit:,.0f}円")
    print(f"  セグメント別構成（最適化後）:")
    for seg, qty in sorted(segment_composition.items()):
        if qty > 0:
            pct = qty / opt_qty * 100 if opt_qty > 0 else 0
            print(f"    - {seg}: {qty:,.0f}本 ({pct:.1f}%)")

# =====================================================================
# 粗利分析
# =====================================================================
print("\n" + "=" * 80)
print("粗利分析")
print("=" * 80)

# 全体
total_current_profit = current_agg['total_profit'].sum()
total_opt_profit = sales_opt['total_profit'].sum()
total_improvement = total_opt_profit - total_current_profit
total_improvement_rate = (total_improvement / total_current_profit) * 100

print(f"\n現状総粗利: {total_current_profit:,.0f}円")
print(f"最適化後総粗利: {total_opt_profit:,.0f}円")
print(f"改善額: {total_improvement:+,.0f}円 ({total_improvement_rate:+.2f}%)")

# セグメント別粗利貢献度
print(f"\n【セグメント別粗利貢献度】")
for _, row in df_segment_analysis.iterrows():
    current_contrib = row['current_profit'] / total_current_profit * 100
    opt_contrib = row['opt_profit'] / total_opt_profit * 100
    contrib_change = opt_contrib - current_contrib

    print(f"  {row['segment']}:")
    print(f"    現状: {current_contrib:.1f}% ({row['current_profit']:,.0f}円)")
    print(f"    最適化後: {opt_contrib:.1f}% ({row['opt_profit']:,.0f}円)")
    print(f"    変化: {contrib_change:+.1f}%ポイント")

# =====================================================================
# 製品レベル分析（上位10製品）
# =====================================================================
print("\n" + "=" * 80)
print("製品レベル分析（粗利上位10組み合わせ）")
print("=" * 80)

# 最適化後で粗利が高い上位10
top10 = sales_opt[sales_opt['sales_volume'] > 0].nlargest(10, 'total_profit')

for idx, row in top10.iterrows():
    print(f"\n{row['product_code']} (Plant {row['plant_code']}, {row['segment_code']})")
    print(f"  販売数量: {row['sales_volume']:,.0f}本")
    print(f"  単位粗利: {row['unit_profit']:,.2f}円")
    print(f"  総粗利: {row['total_profit']:,.0f}円")

# =====================================================================
# サマリーファイル保存
# =====================================================================
print("\n" + "=" * 80)
print("分析結果の保存")
print("=" * 80)

# セグメント別分析
df_segment_analysis.to_csv(PROCESSED_DIR / "analysis_by_segment.csv", index=False)
print(f"  ✓ セグメント別分析: {PROCESSED_DIR / 'analysis_by_segment.csv'}")

# 拠点別分析
df_plant_analysis = pd.DataFrame(plant_analysis)
# segment_composition列は辞書なので、別途処理
df_plant_analysis_simple = df_plant_analysis.drop('segment_composition', axis=1)
df_plant_analysis_simple.to_csv(PROCESSED_DIR / "analysis_by_plant.csv", index=False)
print(f"  ✓ 拠点別分析: {PROCESSED_DIR / 'analysis_by_plant.csv'}")

# 製品別上位10
top10.to_csv(PROCESSED_DIR / "analysis_top10_products.csv", index=False)
print(f"  ✓ 粗利上位10: {PROCESSED_DIR / 'analysis_top10_products.csv'}")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
