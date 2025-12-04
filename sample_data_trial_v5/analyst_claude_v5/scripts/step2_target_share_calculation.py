"""
Step 2: 目標シェア初期算出

戦略区分から目標シェアの初期値を機械的に算出し、
競合分析結果と合わせてユーザーに提示します。
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# 共通モジュールのインポート
from optimization_common_v5 import (
    PROCESSED_DIR, REPORTS_DIR,
    ACQUISITION_RATE, STRATEGY_COEFFICIENTS,
    get_acquisition_rate,
    get_strategy_coefficient,
    load_csv_with_validation,
    save_csv_with_backup,
    create_report_header,
    format_percentage,
    format_number
)


class TargetShareCalculation:
    """Step 2: 目標シェア初期算出クラス"""

    def __init__(self):
        """初期化"""
        self.market_master = None
        self.competitor_master = None
        self.target_share_initial = None
        self.competitive_analysis = None

    def load_processed_data(self) -> bool:
        """
        処理済みデータを読み込み

        Returns:
            True: 成功、False: 失敗
        """
        print("=" * 80)
        print("Step 2: 目標シェア初期算出 - データ読み込み")
        print("=" * 80)

        try:
            # 市場マスタ読み込み
            print("\n[1/2] 処理済み市場マスタ読み込み...")
            market_path = PROCESSED_DIR / "market_master_processed.csv"
            self.market_master = load_csv_with_validation(market_path)
            print(f"  ✓ {len(self.market_master)}セグメントのデータを読み込みました")

            # 競合マスタ読み込み
            print("\n[2/2] 処理済み競合マスタ読み込み...")
            competitor_path = PROCESSED_DIR / "competitor_master_processed.csv"
            self.competitor_master = load_csv_with_validation(competitor_path)
            print(f"  ✓ {len(self.competitor_master)}件の競合データを読み込みました")

            return True

        except Exception as e:
            print(f"\n✗ エラー: {e}")
            print("  Step 1を先に実行してください。")
            return False

    def calculate_initial_target_share(self) -> None:
        """戦略区分から目標シェア初期値を算出"""
        print("\n" + "=" * 80)
        print("戦略区分から目標シェア初期値を算出")
        print("=" * 80)

        results = []

        for idx, row in self.market_master.iterrows():
            segment = row['segment_code']
            current_share = row['current_share']
            strategy_type = row['strategy_type']

            # 戦略係数を取得
            coef_lower = get_strategy_coefficient(strategy_type, 'lower')
            coef_upper = get_strategy_coefficient(strategy_type, 'upper')

            # 目標シェアを算出
            target_share_lower = current_share * coef_lower
            target_share_upper = current_share * coef_upper

            # 結果を格納
            result = {
                'segment_code': segment,
                'current_share': current_share,
                'strategy_type': strategy_type,
                'target_share_lower': target_share_lower,
                'target_share_upper': target_share_upper
            }
            results.append(result)

            # 表示
            print(f"\n{segment}:")
            print(f"  現状シェア: {format_percentage(current_share)}")
            print(f"  戦略区分: {strategy_type}")
            print(f"  戦略係数: {coef_lower:.1f} 〜 {coef_upper:.1f}")
            print(f"  目標シェア初期値: {format_percentage(target_share_lower)} 〜 {format_percentage(target_share_upper)}")

        self.target_share_initial = pd.DataFrame(results)

    def perform_competitive_analysis(self) -> None:
        """競合分析による到達可能シェア上限を算出"""
        print("\n" + "=" * 80)
        print("競合分析による到達可能シェア上限を算出")
        print("=" * 80)

        results = []

        for segment in self.market_master['segment_code']:
            print(f"\n【{segment}】")

            # 自社の現状シェア
            current_share = self.market_master[
                self.market_master['segment_code'] == segment
            ]['current_share'].values[0]

            # セグメント内の競合を取得
            competitors = self.competitor_master[
                self.competitor_master['segment_code'] == segment
            ].copy()

            # 各競合から奪取可能なシェアを計算
            acquirable_shares_lower = []
            acquirable_shares_upper = []

            print("\n  競合別奪取可能シェア:")
            print("  " + "-" * 70)

            for idx, comp in competitors.iterrows():
                comp_name = comp['competitor_name']
                comp_share = comp['current_share']
                comp_position = comp['competitive_position']

                # 奪取可能率を取得
                acq_rate_lower = get_acquisition_rate(comp_position, 'lower')
                acq_rate_upper = get_acquisition_rate(comp_position, 'upper')

                # 奪取可能シェアを計算
                # min(奪取可能率, 競合の実際のシェア)
                acquirable_lower = min(acq_rate_lower, comp_share)
                acquirable_upper = min(acq_rate_upper, comp_share)

                acquirable_shares_lower.append(acquirable_lower)
                acquirable_shares_upper.append(acquirable_upper)

                print(f"  {comp_name:10s} | シェア: {format_percentage(comp_share):6s} | "
                      f"評価: {comp_position:8s} | "
                      f"奪取可能: {format_percentage(acquirable_lower)} 〜 {format_percentage(acquirable_upper)}")

            # 到達可能シェアを算出
            total_acquirable_lower = sum(acquirable_shares_lower)
            total_acquirable_upper = sum(acquirable_shares_upper)

            achievable_share_lower = current_share + total_acquirable_lower
            achievable_share_upper = current_share + total_acquirable_upper

            print("  " + "-" * 70)
            print(f"  奪取可能シェア合計: {format_percentage(total_acquirable_lower)} 〜 {format_percentage(total_acquirable_upper)}")
            print(f"  到達可能シェア: {format_percentage(achievable_share_lower)} 〜 {format_percentage(achievable_share_upper)}")

            # 目標シェアと比較
            target_row = self.target_share_initial[
                self.target_share_initial['segment_code'] == segment
            ].iloc[0]

            target_lower = target_row['target_share_lower']
            target_upper = target_row['target_share_upper']

            print(f"\n  目標シェア初期値: {format_percentage(target_lower)} 〜 {format_percentage(target_upper)}")

            # 警告判定
            warning = ""
            if target_upper > achievable_share_upper:
                warning = "⚠ 目標上限が到達可能上限を超過"
            elif target_upper > achievable_share_upper * 0.9:
                warning = "⚠ 目標達成の難易度が高い"

            if warning:
                print(f"  {warning}")

            # 結果を格納
            result = {
                'segment_code': segment,
                'current_share': current_share,
                'total_acquirable_lower': total_acquirable_lower,
                'total_acquirable_upper': total_acquirable_upper,
                'achievable_share_lower': achievable_share_lower,
                'achievable_share_upper': achievable_share_upper,
                'warning': warning
            }
            results.append(result)

        self.competitive_analysis = pd.DataFrame(results)

    def save_results(self) -> None:
        """結果を保存"""
        print("\n" + "=" * 80)
        print("結果の保存")
        print("=" * 80)

        # 目標シェア初期値を保存
        target_output = PROCESSED_DIR / "target_share_initial.csv"
        save_csv_with_backup(self.target_share_initial, target_output, backup=False)

        # 競合分析結果を保存
        analysis_output = PROCESSED_DIR / "competitive_analysis.csv"
        save_csv_with_backup(self.competitive_analysis, analysis_output, backup=False)

    def run(self) -> bool:
        """
        Step 2を実行

        Returns:
            True: 成功、False: 失敗
        """
        # データ読み込み
        if not self.load_processed_data():
            return False

        # 目標シェア初期値算出
        self.calculate_initial_target_share()

        # 競合分析
        self.perform_competitive_analysis()

        # 結果保存
        self.save_results()

        print("\n" + "=" * 80)
        print("✓ Step 2: 目標シェア初期算出が完了しました")
        print("=" * 80)
        print("\n必要に応じて目標シェアを修正してください。")
        print(f"修正ファイル: {PROCESSED_DIR / 'target_share_initial.csv'}")
        return True


def main():
    """メイン関数"""
    calculation = TargetShareCalculation()
    success = calculation.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
