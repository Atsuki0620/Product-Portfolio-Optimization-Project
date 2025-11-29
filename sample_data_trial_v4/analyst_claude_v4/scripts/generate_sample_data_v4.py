#!/usr/bin/env python3
"""
2024年データ生成スクリプト (v4)

このスクリプトは、01_data_requirements_2024.md の仕様に沿って、
2024年単年の販売データ（D1）と生産データ（D2）を生成します。
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ===========================
# 定数定義
# ===========================
TOTAL_ANNUAL_SALES_QTY_2024 = 504_000
PLANT_A_CAPACITY = 300_000
PLANT_B_CAPACITY = 204_000
TOTAL_CAPACITY = 504_000

UNIT_PRICE_MIN = 40_000
UNIT_PRICE_MAX = 100_000

YEAR = 2024

# 顧客名サンプル（任意）
CUSTOMER_NAMES = [
    "Customer_A", "Customer_B", "Customer_C", "Customer_D", "Customer_E",
    "Customer_F", "Customer_G", "Customer_H", "Customer_I", "Customer_J"
]


# ===========================
# データ生成関数
# ===========================

def load_master_data(master_dir: Path):
    """マスタデータを読み込む"""
    product_master = pd.read_csv(master_dir / "product_master.csv")
    segment_master = pd.read_csv(master_dir / "segment_master.csv")
    return product_master, segment_master


def generate_sales_data(product_master: pd.DataFrame,
                       segment_master: pd.DataFrame,
                       seed: int = 42) -> pd.DataFrame:
    """販売データ（D1）を生成"""
    np.random.seed(seed)

    plants = ['A', 'B']
    segments = segment_master['segment_code'].tolist()

    # 製品 × 拠点 × セグメントの組み合わせを生成
    rows = []
    for _, product in product_master.iterrows():
        product_code = product['product_code']
        product_name = product['product_name']
        cost_band = product['cost_band']

        for plant in plants:
            for segment in segments:
                rows.append({
                    'product_code': product_code,
                    'product_name': product_name,
                    'cost_band': cost_band,
                    'plant': plant,
                    'segment': segment
                })

    df = pd.DataFrame(rows)

    # 初期数量をランダム生成（後で調整）
    df['sales_qty_raw'] = np.random.randint(100, 5000, size=len(df))

    # セグメント販売比を取得
    segment_mix = segment_master.set_index('segment_code')['segment_sales_mix'].to_dict()

    # ステップ1: 拠点キャパシティを考慮して、拠点別の目標数量を設定
    # 拠点A:B = 300,000:204,000 = 25:17 の比率を維持
    plant_a_target = PLANT_A_CAPACITY
    plant_b_target = PLANT_B_CAPACITY
    # 合計が 504,000 になるように調整（すでに一致しているが、明示的に確認）
    assert plant_a_target + plant_b_target == TOTAL_ANNUAL_SALES_QTY_2024

    # ステップ2: セグメント × 拠点別に数量を配分（セグメント販売比を考慮）
    for segment in segments:
        segment_mask = df['segment'] == segment
        segment_target_qty = TOTAL_ANNUAL_SALES_QTY_2024 * segment_mix[segment]

        # セグメント内の初期数量の合計
        segment_total_raw = df.loc[segment_mask, 'sales_qty_raw'].sum()

        if segment_total_raw > 0:
            # セグメントの目標数量に合わせてスケーリング
            scale_factor = segment_target_qty / segment_total_raw
            df.loc[segment_mask, 'sales_qty'] = (df.loc[segment_mask, 'sales_qty_raw'] * scale_factor).round().astype(int)
        else:
            # 万が一の場合は均等配分
            num_rows = segment_mask.sum()
            if num_rows > 0:
                df.loc[segment_mask, 'sales_qty'] = int(segment_target_qty // num_rows)

    # ステップ3: 拠点キャパシティを厳守するように調整（スケーリング）
    plant_a_current = df[df['plant'] == 'A']['sales_qty'].sum()
    plant_b_current = df[df['plant'] == 'B']['sales_qty'].sum()

    # 拠点Aを目標キャパシティにスケーリング
    if plant_a_current > 0:
        scale_factor_a = PLANT_A_CAPACITY / plant_a_current
        plant_a_mask = df['plant'] == 'A'
        df.loc[plant_a_mask, 'sales_qty'] = (df.loc[plant_a_mask, 'sales_qty'] * scale_factor_a).round().astype(int)

    # 拠点Bを目標キャパシティにスケーリング
    if plant_b_current > 0:
        scale_factor_b = PLANT_B_CAPACITY / plant_b_current
        plant_b_mask = df['plant'] == 'B'
        df.loc[plant_b_mask, 'sales_qty'] = (df.loc[plant_b_mask, 'sales_qty'] * scale_factor_b).round().astype(int)

    # ステップ4: 拠点キャパシティを再確認して微調整
    plant_a_current = int(df[df['plant'] == 'A']['sales_qty'].sum())
    plant_b_current = int(df[df['plant'] == 'B']['sales_qty'].sum())

    # 拠点Bがキャパシティを超えている場合、拠点Aに移動
    if plant_b_current > PLANT_B_CAPACITY:
        excess_b = plant_b_current - PLANT_B_CAPACITY
        plant_b_mask = df['plant'] == 'B'
        plant_b_df = df[plant_b_mask].sort_values('sales_qty', ascending=True)

        for i in range(excess_b):
            idx = plant_b_df.index[i]
            if df.loc[idx, 'sales_qty'] > 1:
                df.loc[idx, 'sales_qty'] -= 1
                plant_b_current -= 1
                # 拠点Aに追加
                plant_a_mask = df['plant'] == 'A'
                plant_a_df = df[plant_a_mask].sort_values('sales_qty', ascending=False)
                add_idx = plant_a_df.index[0]
                df.loc[add_idx, 'sales_qty'] += 1
                plant_a_current += 1

    # 拠点Aがキャパシティを超えている場合、拠点Bに移動
    elif plant_a_current > PLANT_A_CAPACITY:
        excess_a = plant_a_current - PLANT_A_CAPACITY
        plant_a_mask = df['plant'] == 'A'
        plant_a_df = df[plant_a_mask].sort_values('sales_qty', ascending=True)

        for i in range(excess_a):
            idx = plant_a_df.index[i]
            if df.loc[idx, 'sales_qty'] > 1:
                df.loc[idx, 'sales_qty'] -= 1
                plant_a_current -= 1
                # 拠点Bに追加
                plant_b_mask = df['plant'] == 'B'
                plant_b_df = df[plant_b_mask].sort_values('sales_qty', ascending=False)
                add_idx = plant_b_df.index[0]
                df.loc[add_idx, 'sales_qty'] += 1
                plant_b_current += 1

    # ステップ5: 全体の販売数量を TOTAL_ANNUAL_SALES_QTY_2024 に厳密に合わせる
    current_total = int(df['sales_qty'].sum())
    diff = TOTAL_ANNUAL_SALES_QTY_2024 - current_total

    if diff != 0:
        if diff > 0:
            # 拠点Aに追加（キャパシティに余裕がある）
            plant_a_mask = df['plant'] == 'A'
            plant_a_df = df[plant_a_mask].sort_values('sales_qty', ascending=False)
            for i in range(diff):
                idx = plant_a_df.index[i % len(plant_a_df)]
                df.loc[idx, 'sales_qty'] += 1
        else:
            # 削減（拠点Aから）
            plant_a_mask = df['plant'] == 'A'
            plant_a_df = df[plant_a_mask].sort_values('sales_qty', ascending=True)
            for i in range(abs(diff)):
                idx = plant_a_df.index[i % len(plant_a_df)]
                if df.loc[idx, 'sales_qty'] > 1:
                    df.loc[idx, 'sales_qty'] -= 1

    # sales_qty_raw カラムを削除
    df = df.drop(columns=['sales_qty_raw'])

    # unit_price を生成（40,000〜100,000）
    df['unit_price'] = np.random.randint(UNIT_PRICE_MIN, UNIT_PRICE_MAX + 1, size=len(df))

    # セグメント別ターゲット粗利率を取得
    target_margin = segment_master.set_index('segment_code')['target_margin_rate'].to_dict()

    # 粗利率を生成（ターゲット ± 乱数）
    df['margin_rate'] = df['segment'].map(target_margin)

    # cost_band によってノイズ幅を変える
    for idx, row in df.iterrows():
        base_margin = target_margin[row['segment']]

        if row['cost_band'] == 'low':
            # low は粗利率が比較的高め（原価率が低い）
            noise = np.random.uniform(-0.03, 0.05)
        else:  # high
            # high は粗利率が比較的低め（原価率が高い）
            noise = np.random.uniform(-0.05, 0.03)

        margin = base_margin + noise
        # 粗利率は 0〜1 の範囲に制限
        margin = max(0.01, min(0.99, margin))
        df.at[idx, 'margin_rate'] = margin

    # unit_cost を計算
    # margin_rate = (unit_price - unit_cost) / unit_price
    # => unit_cost = unit_price * (1 - margin_rate)
    df['unit_cost'] = (df['unit_price'] * (1 - df['margin_rate'])).round(2)

    # sales_amount を計算
    df['sales_amount'] = df['sales_qty'] * df['unit_price']

    # customer_name をランダムに割り当て
    df['customer_name'] = np.random.choice(CUSTOMER_NAMES, size=len(df))

    # year カラムを追加
    df['year'] = YEAR

    # カラム順序を整理
    df = df[[
        'year', 'product_code', 'product_name', 'cost_band', 'plant', 'segment',
        'sales_qty', 'unit_price', 'sales_amount', 'unit_cost', 'margin_rate', 'customer_name'
    ]]

    return df


def generate_production_data(sales_df: pd.DataFrame) -> pd.DataFrame:
    """生産データ（D2）を生成"""
    # product_code × plant でグループ化して生産数量を集計
    production = sales_df.groupby(['product_code', 'plant']).agg({
        'sales_qty': 'sum',  # 生産数量 = 販売数量の合計
        'unit_cost': 'mean'  # 単位原価は平均値を使用
    }).reset_index()

    production = production.rename(columns={'sales_qty': 'production_qty'})

    # cost_amount を計算
    production['cost_amount'] = (production['production_qty'] * production['unit_cost']).round(2)

    # カラム順序を整理
    production = production[['product_code', 'plant', 'production_qty', 'unit_cost', 'cost_amount']]

    return production


def save_data(sales_df: pd.DataFrame, production_df: pd.DataFrame, output_dir: Path):
    """データを保存"""
    output_dir.mkdir(parents=True, exist_ok=True)

    sales_path = output_dir / "sales_2024.csv"
    production_path = output_dir / "production_2024.csv"

    sales_df.to_csv(sales_path, index=False)
    production_df.to_csv(production_path, index=False)

    print(f"✓ 販売データ（D1）を保存: {sales_path}")
    print(f"✓ 生産データ（D2）を保存: {production_path}")

    # サマリー情報を表示
    print("\n=== データ生成サマリー ===")
    print(f"総販売数量: {sales_df['sales_qty'].sum():,} 本")
    print(f"  - 拠点A: {sales_df[sales_df['plant']=='A']['sales_qty'].sum():,} 本")
    print(f"  - 拠点B: {sales_df[sales_df['plant']=='B']['sales_qty'].sum():,} 本")
    print("\nセグメント別販売数量:")
    for segment in sales_df['segment'].unique():
        qty = sales_df[sales_df['segment']==segment]['sales_qty'].sum()
        pct = qty / sales_df['sales_qty'].sum() * 100
        print(f"  - {segment}: {qty:,} 本 ({pct:.2f}%)")
    print("\n総生産数量:")
    print(f"  - 拠点A: {production_df[production_df['plant']=='A']['production_qty'].sum():,} 本")
    print(f"  - 拠点B: {production_df[production_df['plant']=='B']['production_qty'].sum():,} 本")


# ===========================
# メイン処理
# ===========================

def main():
    parser = argparse.ArgumentParser(
        description="2024年データ生成スクリプト (v4)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="乱数シード（デフォルト: 42）"
    )
    parser.add_argument(
        "--master-dir",
        type=str,
        default=None,
        help="マスタデータディレクトリ（デフォルト: ../data/master）"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="出力ディレクトリ（デフォルト: ../data/raw）"
    )

    args = parser.parse_args()

    # スクリプトのディレクトリを基準にパスを設定
    script_dir = Path(__file__).parent
    master_dir = Path(args.master_dir) if args.master_dir else script_dir.parent / "data" / "master"
    output_dir = Path(args.output_dir) if args.output_dir else script_dir.parent / "data" / "raw"

    print("=== 2024年データ生成スクリプト (v4) ===\n")
    print(f"マスタデータディレクトリ: {master_dir}")
    print(f"出力ディレクトリ: {output_dir}")
    print(f"乱数シード: {args.seed}\n")

    # マスタデータの読み込み
    print("マスタデータを読み込み中...")
    try:
        product_master, segment_master = load_master_data(master_dir)
        print(f"  - 製品マスタ: {len(product_master)} 製品")
        print(f"  - セグメントマスタ: {len(segment_master)} セグメント\n")
    except Exception as e:
        print(f"エラー: マスタデータの読み込みに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    # 販売データの生成
    print("販売データ（D1）を生成中...")
    sales_df = generate_sales_data(product_master, segment_master, seed=args.seed)
    print(f"  - 生成行数: {len(sales_df)} 行\n")

    # 生産データの生成
    print("生産データ（D2）を生成中...")
    production_df = generate_production_data(sales_df)
    print(f"  - 生成行数: {len(production_df)} 行\n")

    # データの保存
    print("データを保存中...")
    save_data(sales_df, production_df, output_dir)

    print("\n完了！")


if __name__ == "__main__":
    main()
