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

    def generate_presentation_report(self) -> None:
        """ユーザー確認用レポートを生成"""
        print("\n" + "=" * 80)
        print("ユーザー確認用レポートの生成")
        print("=" * 80)

        report_path = REPORTS_DIR / "step2_presentation_report.md"

        # レポート作成
        report = create_report_header(
            "Step 2: 目標シェア初期算出 確認レポート",
            "Step 2: Target Share Calculation"
        )

        # 概要
        report += "## 1. 概要\n\n"
        report += "戦略区分から目標シェアの初期値を機械的に算出し、競合分析による到達可能性を評価しました。\n"
        report += "以下の結果をご確認いただき、必要に応じて目標シェアを修正してください。\n\n"

        # 目標シェア算出ロジック
        report += "## 2. 目標シェア算出ロジック\n\n"
        report += "### 戦略区分別係数\n\n"
        report += "| 戦略区分 | 下限係数 | 上限係数 | 説明 |\n"
        report += "|---------|---------|---------|------|\n"

        for strategy, coef in STRATEGY_COEFFICIENTS.items():
            report += f"| {strategy} | {coef['lower']:.1f} | {coef['upper']:.1f} | "
            if strategy == 'aggressive_expansion':
                report += "シェア拡大を目指す |\n"
            elif strategy == 'maintain':
                report += "現状維持 |\n"
            elif strategy == 'reduction':
                report += "段階的な縮小 |\n"
            elif strategy == 'withdrawal':
                report += "撤退方向へ |\n"

        report += "\n### 奪取可能率パラメータ\n\n"
        report += "| 競争力評価 | 下限 | 上限 | 説明 |\n"
        report += "|-----------|------|------|------|\n"

        for position, rate in ACQUISITION_RATE.items():
            report += f"| {position} | {format_percentage(rate['lower'])} | {format_percentage(rate['upper'])} | "
            if position == 'strong':
                report += "強い競合からはシェア奪取困難 |\n"
            elif position == 'moderate':
                report += "中程度の競合から一定のシェア奪取可能 |\n"
            elif position == 'weak':
                report += "弱い競合から積極的なシェア奪取可能 |\n"

        # セグメント別結果
        report += "\n## 3. セグメント別結果\n\n"

        for segment in self.market_master['segment_code']:
            report += f"### {segment}\n\n"

            # 市場情報
            market_row = self.market_master[
                self.market_master['segment_code'] == segment
            ].iloc[0]

            report += "#### 市場情報\n\n"
            report += f"- **現状市場規模**: {format_number(market_row['current_market_size'])}本\n"
            report += f"- **3年後市場規模**: {format_number(market_row['market_size_after_3y'])}本\n"
            report += f"- **市場CAGR**: {format_percentage(market_row['market_cagr'])}\n"
            report += f"- **現状自社シェア**: {format_percentage(market_row['current_share'])}\n"
            report += f"- **戦略区分**: {market_row['strategy_type']}\n\n"

            # 目標シェア初期値
            target_row = self.target_share_initial[
                self.target_share_initial['segment_code'] == segment
            ].iloc[0]

            report += "#### 目標シェア初期値\n\n"
            report += f"- **下限**: {format_percentage(target_row['target_share_lower'])}\n"
            report += f"- **上限**: {format_percentage(target_row['target_share_upper'])}\n\n"

            # 競合分析結果
            analysis_row = self.competitive_analysis[
                self.competitive_analysis['segment_code'] == segment
            ].iloc[0]

            report += "#### 競合分析結果\n\n"
            report += f"- **奪取可能シェア合計**: "
            report += f"{format_percentage(analysis_row['total_acquirable_lower'])} 〜 "
            report += f"{format_percentage(analysis_row['total_acquirable_upper'])}\n"
            report += f"- **到達可能シェア上限**: "
            report += f"{format_percentage(analysis_row['achievable_share_lower'])} 〜 "
            report += f"{format_percentage(analysis_row['achievable_share_upper'])}\n\n"

            # 競合詳細
            report += "#### 競合詳細\n\n"
            report += "| 競合 | シェア | 評価 | 奪取可能率 |\n"
            report += "|------|-------|------|----------|\n"

            competitors = self.competitor_master[
                self.competitor_master['segment_code'] == segment
            ].sort_values('current_share', ascending=False)

            for idx, comp in competitors.iterrows():
                comp_position = comp['competitive_position']
                acq_lower = get_acquisition_rate(comp_position, 'lower')
                acq_upper = get_acquisition_rate(comp_position, 'upper')

                report += f"| {comp['competitor_name']} | "
                report += f"{format_percentage(comp['current_share'])} | "
                report += f"{comp_position} | "
                report += f"{format_percentage(acq_lower)} 〜 {format_percentage(acq_upper)} |\n"

            # 評価
            report += "\n#### 評価\n\n"
            if analysis_row['warning']:
                report += f"⚠ **{analysis_row['warning']}**\n\n"
            else:
                report += "✓ 目標シェアは到達可能な範囲内です。\n\n"

        # サマリー
        report += "## 4. サマリー\n\n"
        report += "| セグメント | 現状シェア | 目標シェア（下限〜上限） | 到達可能上限 | 状態 |\n"
        report += "|-----------|-----------|---------------------|------------|------|\n"

        for segment in self.market_master['segment_code']:
            market_row = self.market_master[
                self.market_master['segment_code'] == segment
            ].iloc[0]
            target_row = self.target_share_initial[
                self.target_share_initial['segment_code'] == segment
            ].iloc[0]
            analysis_row = self.competitive_analysis[
                self.competitive_analysis['segment_code'] == segment
            ].iloc[0]

            status = "⚠" if analysis_row['warning'] else "✓"

            report += f"| {segment} | "
            report += f"{format_percentage(market_row['current_share'])} | "
            report += f"{format_percentage(target_row['target_share_lower'])} 〜 "
            report += f"{format_percentage(target_row['target_share_upper'])} | "
            report += f"{format_percentage(analysis_row['achievable_share_upper'])} | "
            report += f"{status} |\n"

        # 次のステップ
        report += "\n## 5. 次のステップ\n\n"
        report += "### 修正が不要な場合\n\n"
        report += "Step 3（実現可能性検証）に進んでください。\n\n"
        report += "```bash\n"
        report += "python scripts/step3_feasibility_validation.py\n"
        report += "```\n\n"

        report += "### 修正が必要な場合\n\n"
        report += "`data/processed/target_share_initial.csv`を編集し、"
        report += "`target_share_lower`と`target_share_upper`を修正してください。\n"
        report += "修正後、Step 3に進んでください。\n\n"

        # 注意事項
        report += "## 6. 注意事項\n\n"
        report += "- 目標シェア上限が到達可能上限を大きく超える場合、最適化が実行不可能になる可能性があります。\n"
        report += "- 戦略区分との整合性を確認してください（例: 撤退戦略なのにシェア増加など）。\n"
        report += "- 市場規模の成長率（CAGR）も考慮して、現実的な目標を設定してください。\n"

        # ファイルに保存
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"  ✓ レポートを保存: {report_path}")

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

        # レポート生成
        self.generate_presentation_report()

        print("\n" + "=" * 80)
        print("✓ Step 2: 目標シェア初期算出が完了しました")
        print("=" * 80)
        print("\nレポートを確認し、必要に応じて目標シェアを修正してください。")
        print(f"レポート: {REPORTS_DIR / 'step2_presentation_report.md'}")
        print(f"修正ファイル: {PROCESSED_DIR / 'target_share_initial.csv'}")
        return True


def main():
    """メイン関数"""
    calculation = TargetShareCalculation()
    success = calculation.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
