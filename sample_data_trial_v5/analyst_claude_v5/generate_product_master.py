"""
製品マスタ生成スクリプト
sales_2024.csvから製品×拠点×セグメントの組み合わせごとに集計して
新しいproduct_master.csvを生成する
"""

import pandas as pd
import numpy as np
from pathlib import Path

# パス設定
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
MASTER_DIR = DATA_DIR / "master"

# 入力ファイル
SALES_FILE = RAW_DIR / "sales_2024.csv"
PRODUCT_MASTER_OLD = MASTER_DIR / "product_master.csv"

# 出力ファイル
PRODUCT_MASTER_NEW = MASTER_DIR / "product_master.csv"
PRODUCT_MASTER_BACKUP = MASTER_DIR / "product_master_backup.csv"

def main():
    print("=" * 80)
    print("製品マスタ生成スクリプト")
    print("=" * 80)

    # 1. 既存のproduct_master.csvをバックアップ
    print("\n[1] 既存のproduct_master.csvをバックアップ...")
    if PRODUCT_MASTER_OLD.exists():
        import shutil
        shutil.copy(PRODUCT_MASTER_OLD, PRODUCT_MASTER_BACKUP)
        print(f"  ✓ バックアップ完了: {PRODUCT_MASTER_BACKUP}")
    else:
        print(f"  ! 既存ファイルが存在しません: {PRODUCT_MASTER_OLD}")

    # 2. sales_2024.csvを読み込み
    print("\n[2] sales_2024.csvを読み込み...")
    df_sales = pd.read_csv(SALES_FILE)
    print(f"  ✓ 読み込み完了: {len(df_sales)} レコード")
    print(f"  カラム: {list(df_sales.columns)}")

    # 3. 製品×拠点×セグメント単位で集計
    print("\n[3] 製品×拠点×セグメント単位で集計...")

    # グループ化して集計
    group_cols = ['product_code', 'product_name', 'cost_band', 'plant', 'segment']

    # 各グループごとに計算
    agg_dict = {
        'sales_qty': 'sum',  # 販売数量の合計
        'unit_price': lambda x: np.average(x, weights=df_sales.loc[x.index, 'sales_qty']),  # 加重平均
        'unit_cost': lambda x: np.average(x, weights=df_sales.loc[x.index, 'sales_qty']),   # 加重平均
        'margin_rate': lambda x: np.average(x, weights=df_sales.loc[x.index, 'sales_qty'])  # 加重平均
    }

    df_agg = df_sales.groupby(group_cols, as_index=False).agg(agg_dict)

    # unit_profit を計算
    df_agg['unit_profit'] = df_agg['unit_price'] - df_agg['unit_cost']

    # カラム名を整理
    df_agg.rename(columns={
        'plant': 'plant_code',
        'segment': 'segment_code'
    }, inplace=True)

    # 必要なカラムのみ選択し、順序を整理
    output_cols = [
        'product_code',
        'product_name',
        'cost_band',
        'plant_code',
        'segment_code',
        'unit_cost',
        'unit_price',
        'unit_profit',
        'margin_rate',
        'sales_qty'
    ]

    df_product_master = df_agg[output_cols].copy()

    print(f"  ✓ 集計完了: {len(df_product_master)} 製品×拠点×セグメント組み合わせ")

    # 4. データ整合性チェック
    print("\n[4] データ整合性チェック...")

    # 4-1. 欠損値チェック
    null_counts = df_product_master.isnull().sum()
    if null_counts.sum() > 0:
        print("  ⚠ 欠損値が見つかりました:")
        for col, count in null_counts[null_counts > 0].items():
            print(f"    - {col}: {count} 件")
    else:
        print("  ✓ 欠損値なし")

    # 4-2. 数値の妥当性チェック
    print("\n  数値カラムの統計:")
    numeric_cols = ['unit_cost', 'unit_price', 'unit_profit', 'margin_rate', 'sales_qty']
    stats = df_product_master[numeric_cols].describe()
    print(stats.to_string())

    # 4-3. 負の値チェック
    for col in ['unit_cost', 'unit_price', 'sales_qty']:
        negative_count = (df_product_master[col] < 0).sum()
        if negative_count > 0:
            print(f"  ⚠ {col} に負の値: {negative_count} 件")

    # 4-4. unit_profit の整合性チェック
    df_product_master['profit_check'] = df_product_master['unit_price'] - df_product_master['unit_cost']
    profit_diff = (df_product_master['unit_profit'] - df_product_master['profit_check']).abs()
    if profit_diff.max() > 0.01:
        print(f"  ⚠ unit_profit の計算に誤差: 最大差分 {profit_diff.max():.2f}")
    else:
        print("  ✓ unit_profit の計算正常")
    df_product_master.drop('profit_check', axis=1, inplace=True)

    # 4-5. セグメントと拠点の分布
    print("\n  セグメント別レコード数:")
    print(df_product_master['segment_code'].value_counts().to_string())

    print("\n  拠点別レコード数:")
    print(df_product_master['plant_code'].value_counts().to_string())

    # 5. 新しいproduct_master.csvを保存
    print("\n[5] 新しいproduct_master.csvを保存...")
    df_product_master.to_csv(PRODUCT_MASTER_NEW, index=False)
    print(f"  ✓ 保存完了: {PRODUCT_MASTER_NEW}")
    print(f"  レコード数: {len(df_product_master)}")
    print(f"  カラム数: {len(df_product_master.columns)}")

    # 6. サマリー
    print("\n" + "=" * 80)
    print("処理完了")
    print("=" * 80)
    print(f"入力ファイル: {SALES_FILE}")
    print(f"出力ファイル: {PRODUCT_MASTER_NEW}")
    print(f"バックアップ: {PRODUCT_MASTER_BACKUP}")
    print(f"\n生成されたレコード数: {len(df_product_master)}")
    print(f"製品数: {df_product_master['product_code'].nunique()}")
    print(f"拠点数: {df_product_master['plant_code'].nunique()}")
    print(f"セグメント数: {df_product_master['segment_code'].nunique()}")
    print("=" * 80)

if __name__ == "__main__":
    main()
