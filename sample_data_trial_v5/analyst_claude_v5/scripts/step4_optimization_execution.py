"""
Step 4: 最適化実行

確定した目標シェアを制約条件として、粗利最大化の最適化を実行します。
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import pulp

# 共通モジュールのインポート
from optimization_common_v5 import (
    MASTER_DIR, RAW_DIR, PROCESSED_DIR, REPORTS_DIR,
    PLANT_CAPACITY, TOTAL_SALES_TARGET,
    load_csv_with_validation,
    save_csv_with_backup,
    create_report_header,
    format_percentage,
    format_number
)


class OptimizationExecution:
    """Step 4: 最適化実行クラス"""

    def __init__(self):
        """初期化"""
        self.target_share_final = None
        self.market_master = None
        self.sales_current = None
        self.product_master = None
        self.demand_limits = {}
        self.prob = None
        self.x = {}
        self.optimization_result = None

    def load_data(self) -> bool:
        """
        データを読み込み

        Returns:
            True: 成功、False: 失敗
        """
        print("=" * 80)
        print("Step 4: 最適化実行 - データ読み込み")
        print("=" * 80)

        try:
            # 最終目標シェア読み込み
            print("\n[1/4] 最終目標シェア読み込み...")
            target_path = PROCESSED_DIR / "target_share_final.csv"
            self.target_share_final = load_csv_with_validation(target_path)
            print(f"  ✓ {len(self.target_share_final)}セグメントの最終目標を読み込みました")

            # 市場マスタ読み込み
            print("\n[2/4] 処理済み市場マスタ読み込み...")
            market_path = PROCESSED_DIR / "market_master_processed.csv"
            self.market_master = load_csv_with_validation(market_path)
            print(f"  ✓ {len(self.market_master)}セグメントのデータを読み込みました")

            # 現状販売データ読み込み
            print("\n[3/4] 現状販売データ読み込み...")
            sales_path = RAW_DIR / "sales_2024.csv"
            self.sales_current = load_csv_with_validation(sales_path)
            print(f"  ✓ {len(self.sales_current)}製品のデータを読み込みました")

            # 製品マスタ読み込み
            print("\n[4/4] 製品マスタ読み込み...")
            product_path = MASTER_DIR / "product_master.csv"
            self.product_master = load_csv_with_validation(product_path)
            print(f"  ✓ {len(self.product_master)}製品のデータを読み込みました")

            return True

        except Exception as e:
            print(f"\n✗ エラー: {e}")
            print("  Step 1〜3を先に実行してください。")
            return False

    def calculate_demand_limits(self) -> None:
        """需要上限・下限を算出"""
        print("\n" + "=" * 80)
        print("需要上限・下限の算出")
        print("=" * 80)

        for idx, row in self.target_share_final.iterrows():
            segment = row['segment_code']

            # 3年後市場規模を取得
            market_row = self.market_master[
                self.market_master['segment_code'] == segment
            ].iloc[0]
            market_size_3y = market_row['market_size_after_3y']

            # 需要上限・下限を算出
            demand_min = market_size_3y * row['target_share_lower']
            demand_max = market_size_3y * row['target_share_upper']

            self.demand_limits[segment] = {
                'min': demand_min,
                'max': demand_max,
                'market_size_3y': market_size_3y,
                'target_share_lower': row['target_share_lower'],
                'target_share_upper': row['target_share_upper'],
                'strategy_type': row['strategy_type']
            }

            print(f"\n{segment}:")
            print(f"  3年後市場規模: {format_number(market_size_3y)}本")
            print(f"  目標シェア: {format_percentage(row['target_share_lower'])} 〜 {format_percentage(row['target_share_upper'])}")
            print(f"  需要範囲: {format_number(demand_min)} 〜 {format_number(demand_max)}本")

    def build_lp_model(self) -> None:
        """LPモデルを構築"""
        print("\n" + "=" * 80)
        print("LPモデルの構築")
        print("=" * 80)

        # 問題定義
        self.prob = pulp.LpProblem("ProductPortfolioOptimization_v5", pulp.LpMaximize)

        # 決定変数の定義
        print("\n[1/5] 決定変数の定義...")
        for idx, row in self.product_master.iterrows():
            product_code = row['product_code']
            plant_code = row['plant_code']
            segment_code = row['segment_code']
            var_key = (product_code, plant_code, segment_code)
            self.x[var_key] = pulp.LpVariable(
                f"x_{product_code}_{plant_code}_{segment_code}",
                lowBound=0,
                cat='Continuous'
            )
        print(f"  ✓ {len(self.x)}製品×拠点×セグメント組み合わせの決定変数を定義しました")

        # 目的関数の定義（粗利最大化）
        print("\n[2/5] 目的関数の定義（粗利最大化）...")
        objective = pulp.lpSum([
            row['unit_profit'] * self.x[(row['product_code'], row['plant_code'], row['segment_code'])]
            for idx, row in self.product_master.iterrows()
        ])
        self.prob += objective
        print("  ✓ 目的関数を定義しました")

        # 制約1: 総販売数量制約
        print("\n[3/5] 制約1: 総販売数量制約...")
        self.prob += (
            pulp.lpSum([self.x[p] for p in self.x.keys()]) <= TOTAL_SALES_TARGET,
            "TotalSalesConstraint"
        )
        print(f"  ✓ 総販売数量 ≤ {format_number(TOTAL_SALES_TARGET)}本")

        # 制約2: 拠点キャパシティ制約
        print("\n[4/5] 制約2: 拠点キャパシティ制約...")
        for plant, capacity in PLANT_CAPACITY.items():
            plant_vars = [
                self.x[(row['product_code'], row['plant_code'], row['segment_code'])]
                for idx, row in self.product_master.iterrows()
                if row['plant_code'] == plant
            ]

            self.prob += (
                pulp.lpSum(plant_vars) <= capacity,
                f"PlantCapacity_{plant}"
            )
            print(f"  ✓ Plant {plant} ≤ {format_number(capacity)}本")

        # 制約3: セグメント需要上限制約
        print("\n[5/5] 制約3: セグメント需要制約（上限・下限）...")
        for segment, limits in self.demand_limits.items():
            segment_vars = [
                self.x[(row['product_code'], row['plant_code'], row['segment_code'])]
                for idx, row in self.product_master.iterrows()
                if row['segment_code'] == segment
            ]

            # 需要上限制約
            self.prob += (
                pulp.lpSum(segment_vars) <= limits['max'],
                f"DemandMax_{segment}"
            )

            # 需要下限制約（撤退戦略以外）
            if limits['strategy_type'] != 'withdrawal':
                self.prob += (
                    pulp.lpSum(segment_vars) >= limits['min'],
                    f"DemandMin_{segment}"
                )
                print(f"  ✓ {segment}: {format_number(limits['min'])} 〜 {format_number(limits['max'])}本")
            else:
                print(f"  ✓ {segment}: 上限 {format_number(limits['max'])}本（撤退戦略のため下限なし）")

        print("\n  モデル構築完了:")
        print(f"    - 決定変数: {len(self.x)}個")
        print(f"    - 制約条件: {len(self.prob.constraints)}個")

    def solve_optimization(self) -> bool:
        """最適化を実行

        Returns:
            True: 成功、False: 失敗
        """
        print("\n" + "=" * 80)
        print("最適化の実行")
        print("=" * 80)

        print("\nソルバー実行中...")
        import time
        start_time = time.time()

        # ソルバー実行
        status = self.prob.solve(pulp.PULP_CBC_CMD(msg=0))

        elapsed_time = time.time() - start_time
        print(f"  実行時間: {elapsed_time:.2f}秒")

        # 結果判定
        print(f"\n最適化ステータス: {pulp.LpStatus[status]}")

        if status == pulp.LpStatusOptimal:
            print("✓ 最適解が見つかりました")
            objective_value = pulp.value(self.prob.objective)
            print(f"  最大粗利: {format_number(objective_value)}円")
            return True

        elif status == pulp.LpStatusInfeasible:
            print("✗ 実行不可能（Infeasible）")
            print("  制約条件が厳しすぎるため、実行可能解が存在しません。")
            print("\n推奨対応:")
            print("  1. 目標シェアの範囲を緩和する")
            print("  2. 需要下限制約を削除・緩和する")
            print("  3. Step 3で検証結果を再確認する")
            return False

        elif status == pulp.LpStatusUnbounded:
            print("✗ 非有界（Unbounded）")
            print("  モデルに問題があります。開発者に連絡してください。")
            return False

        else:
            print(f"✗ 不明なステータス: {status}")
            return False

    def extract_results(self) -> None:
        """最適化結果を抽出"""
        print("\n" + "=" * 80)
        print("結果の抽出と整数化")
        print("=" * 80)

        results = []

        for idx, row in self.product_master.iterrows():
            product_code = row['product_code']
            plant_code = row['plant_code']
            segment_code = row['segment_code']
            var_key = (product_code, plant_code, segment_code)
            optimal_value = self.x[var_key].varValue

            # 整数化（四捨五入）
            optimal_int = round(optimal_value)

            results.append({
                'product_code': product_code,
                'segment_code': segment_code,
                'plant_code': plant_code,
                'sales_volume': optimal_int,
                'unit_profit': row['unit_profit'],
                'total_profit': optimal_int * row['unit_profit']
            })

        self.optimization_result = pd.DataFrame(results)

        # 制約充足性の確認
        total_volume = self.optimization_result['sales_volume'].sum()
        print(f"\n総販売数量: {format_number(total_volume)}本")
        print(f"目標: {format_number(TOTAL_SALES_TARGET)}本")

        if abs(total_volume - TOTAL_SALES_TARGET) > 10:
            print(f"⚠ 警告: 整数化により{abs(total_volume - TOTAL_SALES_TARGET)}本の誤差が発生しました")
            # 簡易調整（最も粗利の低い製品で調整）
            diff = int(TOTAL_SALES_TARGET - total_volume)
            if diff != 0:
                # 粗利の低い順にソート
                sorted_products = self.optimization_result.sort_values('unit_profit')
                adjust_product = sorted_products.iloc[0]['product_code']
                self.optimization_result.loc[
                    self.optimization_result['product_code'] == adjust_product,
                    'sales_volume'
                ] += diff
                self.optimization_result['total_profit'] = (
                    self.optimization_result['sales_volume'] *
                    self.optimization_result['unit_profit']
                )
                print(f"  調整完了: {adjust_product}で{diff:+d}本調整")

    def save_optimization_result(self) -> None:
        """最適化結果を保存"""
        print("\n" + "=" * 80)
        print("最適化結果の保存")
        print("=" * 80)

        # CSV保存（v4互換形式）
        output_path = PROCESSED_DIR / "sales_2024_opt_v5.csv"
        save_csv_with_backup(self.optimization_result, output_path, backup=False)

    def run(self) -> bool:
        """
        Step 4を実行

        Returns:
            True: 成功、False: 失敗
        """
        # データ読み込み
        if not self.load_data():
            return False

        # 需要上限・下限の算出
        self.calculate_demand_limits()

        # LPモデル構築
        self.build_lp_model()

        # 最適化実行
        if not self.solve_optimization():
            return False

        # 結果抽出
        self.extract_results()

        # 結果保存
        self.save_optimization_result()

        print("\n" + "=" * 80)
        print("✓ Step 4: 最適化実行が完了しました")
        print("=" * 80)

        # 最終結果表示
        # 現状の総粗利を計算（sales_2024.csvから）
        current_profit = (self.sales_current['sales_qty'] *
                         (self.sales_current['unit_price'] - self.sales_current['unit_cost'])).sum()
        optimized_profit = self.optimization_result['total_profit'].sum()
        improvement = optimized_profit - current_profit
        improvement_rate = (improvement / current_profit) * 100

        print(f"\n【最適化結果サマリー】")
        print(f"  現状総粗利: {format_number(current_profit)}円")
        print(f"  最適化後総粗利: {format_number(optimized_profit)}円")
        improvement_sign = "+" if improvement >= 0 else ""
        print(f"  改善額: {improvement_sign}{format_number(improvement)}円 ({improvement_rate:+.2f}%)")

        return True


def main():
    """メイン関数"""
    optimization = OptimizationExecution()
    success = optimization.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
