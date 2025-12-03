"""
Step 3: 実現可能性検証

暫定目標シェアが現実的に達成可能かを3つの観点から検証します。
- 検証A: 生産能力検証
- 検証B: 競争環境検証
- 検証C: 戦略整合性検証
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# 共通モジュールのインポート
from optimization_common_v5 import (
    PROCESSED_DIR, REPORTS_DIR,
    PLANT_CAPACITY, TOTAL_CAPACITY,
    load_csv_with_validation,
    save_csv_with_backup,
    create_report_header,
    format_percentage,
    format_number
)


class FeasibilityValidation:
    """Step 3: 実現可能性検証クラス"""

    def __init__(self):
        """初期化"""
        self.target_share = None
        self.market_master = None
        self.competitive_analysis = None
        self.validation_results = []
        self.has_errors = False
        self.has_warnings = False

    def load_data(self) -> bool:
        """
        データを読み込み

        Returns:
            True: 成功、False: 失敗
        """
        print("=" * 80)
        print("Step 3: 実現可能性検証 - データ読み込み")
        print("=" * 80)

        try:
            # 目標シェア読み込み
            print("\n[1/3] 目標シェア読み込み...")
            target_path = PROCESSED_DIR / "target_share_initial.csv"
            self.target_share = load_csv_with_validation(target_path)
            print(f"  ✓ {len(self.target_share)}セグメントの目標シェアを読み込みました")

            # 市場マスタ読み込み
            print("\n[2/3] 処理済み市場マスタ読み込み...")
            market_path = PROCESSED_DIR / "market_master_processed.csv"
            self.market_master = load_csv_with_validation(market_path)
            print(f"  ✓ {len(self.market_master)}セグメントのデータを読み込みました")

            # 競合分析結果読み込み
            print("\n[3/3] 競合分析結果読み込み...")
            analysis_path = PROCESSED_DIR / "competitive_analysis.csv"
            self.competitive_analysis = load_csv_with_validation(analysis_path)
            print(f"  ✓ {len(self.competitive_analysis)}セグメントの分析結果を読み込みました")

            return True

        except Exception as e:
            print(f"\n✗ エラー: {e}")
            print("  Step 1とStep 2を先に実行してください。")
            return False

    def validation_a_capacity(self) -> None:
        """検証A: 生産能力検証"""
        print("\n" + "=" * 80)
        print("検証A: 生産能力検証")
        print("=" * 80)

        # セグメント別の目標販売数量を算出
        segment_volumes = []

        for idx, row in self.target_share.iterrows():
            segment = row['segment_code']

            # 市場規模（3年後）を取得
            market_row = self.market_master[
                self.market_master['segment_code'] == segment
            ].iloc[0]
            market_size_3y = market_row['market_size_after_3y']

            # 目標販売数量を算出
            volume_lower = market_size_3y * row['target_share_lower']
            volume_upper = market_size_3y * row['target_share_upper']

            segment_volumes.append({
                'segment_code': segment,
                'volume_lower': volume_lower,
                'volume_upper': volume_upper
            })

            print(f"\n{segment}:")
            print(f"  3年後市場規模: {format_number(market_size_3y)}本")
            print(f"  目標シェア: {format_percentage(row['target_share_lower'])} 〜 {format_percentage(row['target_share_upper'])}")
            print(f"  目標販売数量: {format_number(volume_lower)} 〜 {format_number(volume_upper)}本")

        # 総販売数量を算出
        total_lower = sum([v['volume_lower'] for v in segment_volumes])
        total_upper = sum([v['volume_upper'] for v in segment_volumes])

        print("\n" + "-" * 80)
        print(f"総販売数量（下限）: {format_number(total_lower)}本")
        print(f"総販売数量（上限）: {format_number(total_upper)}本")
        print(f"総キャパシティ: {format_number(TOTAL_CAPACITY)}本")

        # 判定
        validation_a_status = "OK"
        validation_a_message = ""
        validation_a_suggestion = ""

        if total_lower > TOTAL_CAPACITY:
            validation_a_status = "ERROR"
            excess = total_lower - TOTAL_CAPACITY
            validation_a_message = f"目標下限の合計がキャパシティを{format_number(excess)}本超過しています"
            validation_a_suggestion = "各セグメントの目標シェア下限を引き下げる必要があります"
            self.has_errors = True
            print(f"\n✗ エラー: {validation_a_message}")
            print(f"  修正必須: {validation_a_suggestion}")

        elif total_upper > TOTAL_CAPACITY:
            validation_a_status = "WARNING"
            excess = total_upper - TOTAL_CAPACITY
            validation_a_message = f"目標上限の合計がキャパシティを{format_number(excess)}本超過しています"
            validation_a_suggestion = "上限達成は困難です。目標シェア上限の引き下げを検討してください"
            self.has_warnings = True
            print(f"\n⚠ 警告: {validation_a_message}")
            print(f"  推奨: {validation_a_suggestion}")

        else:
            validation_a_message = "生産能力の範囲内です"
            margin_lower = TOTAL_CAPACITY - total_lower
            margin_upper = TOTAL_CAPACITY - total_upper
            print(f"\n✓ OK: {validation_a_message}")
            print(f"  余裕（下限）: {format_number(margin_lower)}本")
            print(f"  余裕（上限）: {format_number(margin_upper)}本")

        # 検証結果を記録
        self.validation_results.append({
            'validation_type': 'A_Capacity',
            'segment_code': 'ALL',
            'status': validation_a_status,
            'message': validation_a_message,
            'suggestion': validation_a_suggestion,
            'total_lower': total_lower,
            'total_upper': total_upper,
            'capacity': TOTAL_CAPACITY
        })

    def validation_b_competitive(self) -> None:
        """検証B: 競争環境検証"""
        print("\n" + "=" * 80)
        print("検証B: 競争環境検証")
        print("=" * 80)

        for idx, row in self.target_share.iterrows():
            segment = row['segment_code']
            target_lower = row['target_share_lower']
            target_upper = row['target_share_upper']

            # 競合分析結果を取得
            analysis_row = self.competitive_analysis[
                self.competitive_analysis['segment_code'] == segment
            ].iloc[0]

            achievable_lower = analysis_row['achievable_share_lower']
            achievable_upper = analysis_row['achievable_share_upper']

            print(f"\n【{segment}】")
            print(f"  目標シェア上限: {format_percentage(target_upper)}")
            print(f"  到達可能上限: {format_percentage(achievable_upper)}")

            # 判定
            status = "OK"
            message = ""
            suggestion = ""

            if target_upper > achievable_upper:
                status = "ERROR"
                excess = target_upper - achievable_upper
                message = f"目標上限が到達可能上限を{format_percentage(excess)}超過"
                suggestion = f"目標上限を{format_percentage(achievable_upper)}以下に引き下げてください"
                self.has_errors = True
                print(f"  ✗ エラー: {message}")
                print(f"    修正必須: {suggestion}")

            elif target_upper > achievable_upper * 0.9:
                status = "WARNING"
                message = "目標上限が到達可能上限の90%を超過（達成難易度が高い）"
                suggestion = f"より保守的な目標（{format_percentage(achievable_upper * 0.85)}程度）を推奨"
                self.has_warnings = True
                print(f"  ⚠ 警告: {message}")
                print(f"    推奨: {suggestion}")

            else:
                margin = achievable_upper - target_upper
                message = f"到達可能な範囲内（余裕: {format_percentage(margin)}）"
                print(f"  ✓ OK: {message}")

            # 検証結果を記録
            self.validation_results.append({
                'validation_type': 'B_Competitive',
                'segment_code': segment,
                'status': status,
                'message': message,
                'suggestion': suggestion,
                'target_upper': target_upper,
                'achievable_upper': achievable_upper
            })

    def validation_c_strategic(self) -> None:
        """検証C: 戦略整合性検証"""
        print("\n" + "=" * 80)
        print("検証C: 戦略整合性検証")
        print("=" * 80)

        for idx, row in self.target_share.iterrows():
            segment = row['segment_code']
            current_share = row['current_share']
            target_lower = row['target_share_lower']
            target_upper = row['target_share_upper']
            strategy = row['strategy_type']

            print(f"\n【{segment}】")
            print(f"  戦略区分: {strategy}")
            print(f"  現状シェア: {format_percentage(current_share)}")
            print(f"  目標シェア: {format_percentage(target_lower)} 〜 {format_percentage(target_upper)}")

            # 判定
            status = "OK"
            message = ""
            suggestion = ""

            # aggressive_expansion（積極拡大）
            if strategy == 'aggressive_expansion':
                if target_upper < current_share:
                    status = "ERROR"
                    message = "積極拡大戦略なのに目標上限がシェア減少"
                    suggestion = f"目標上限を現状シェア（{format_percentage(current_share)}）以上に設定してください"
                    self.has_errors = True
                    print(f"  ✗ エラー: {message}")
                elif target_upper < current_share * 1.1:
                    status = "WARNING"
                    message = "積極拡大戦略なのにシェア増加が小幅"
                    suggestion = f"より積極的な目標（{format_percentage(current_share * 1.2)}程度）を推奨"
                    self.has_warnings = True
                    print(f"  ⚠ 警告: {message}")
                else:
                    message = "拡大戦略と整合しています"
                    print(f"  ✓ OK: {message}")

            # maintain（維持）
            elif strategy == 'maintain':
                if target_upper > current_share * 1.2 or target_lower < current_share * 0.8:
                    status = "WARNING"
                    message = "維持戦略なのに大幅な増減"
                    suggestion = f"現状シェアの±10%程度（{format_percentage(current_share * 0.9)}〜{format_percentage(current_share * 1.1)}）を推奨"
                    self.has_warnings = True
                    print(f"  ⚠ 警告: {message}")
                else:
                    message = "維持戦略と整合しています"
                    print(f"  ✓ OK: {message}")

            # reduction（縮小）
            elif strategy == 'reduction':
                if target_lower > current_share:
                    status = "WARNING"
                    message = "縮小戦略なのに目標下限がシェア維持以上"
                    suggestion = f"目標下限を現状シェア（{format_percentage(current_share)}）未満に設定することを推奨"
                    self.has_warnings = True
                    print(f"  ⚠ 警告: {message}")
                else:
                    message = "縮小戦略と整合しています"
                    print(f"  ✓ OK: {message}")

            # withdrawal（撤退）
            elif strategy == 'withdrawal':
                if target_lower > current_share:
                    status = "ERROR"
                    message = "撤退戦略なのに目標下限がシェア増加"
                    suggestion = f"目標下限を現状シェア（{format_percentage(current_share)}）以下に設定してください"
                    self.has_errors = True
                    print(f"  ✗ エラー: {message}")
                else:
                    message = "撤退戦略と整合しています"
                    print(f"  ✓ OK: {message}")

            # 検証結果を記録
            self.validation_results.append({
                'validation_type': 'C_Strategic',
                'segment_code': segment,
                'status': status,
                'message': message,
                'suggestion': suggestion,
                'strategy_type': strategy,
                'current_share': current_share,
                'target_lower': target_lower,
                'target_upper': target_upper
            })

    def save_validation_results(self) -> None:
        """検証結果を保存"""
        print("\n" + "=" * 80)
        print("検証結果の保存")
        print("=" * 80)

        # 検証結果をDataFrameに変換
        results_df = pd.DataFrame(self.validation_results)

        # CSV保存
        output_path = PROCESSED_DIR / "validation_result.csv"
        save_csv_with_backup(results_df, output_path, backup=False)

    def save_target_share_final(self) -> None:
        """最終目標シェアを保存"""
        if self.has_errors:
            print("\n検証エラーがあるため、最終目標シェアは保存されません。")
            return

        print("\n最終目標シェアの保存...")
        output_path = PROCESSED_DIR / "target_share_final.csv"
        save_csv_with_backup(self.target_share, output_path, backup=False)

    def generate_validation_report(self) -> None:
        """検証レポートを生成"""
        print("\n" + "=" * 80)
        print("検証レポートの生成")
        print("=" * 80)

        # ディレクトリが存在しない場合は作成
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        report_path = REPORTS_DIR / "step3_validation_report.md"

        # レポート作成
        report = create_report_header(
            "Step 3: 実現可能性検証レポート",
            "Step 3: Feasibility Validation"
        )

        # 概要
        report += "## 1. 概要\n\n"
        report += "目標シェアの実現可能性を3つの観点から検証しました。\n\n"

        # 検証結果サマリー
        report += "## 2. 検証結果サマリー\n\n"

        error_count = sum(1 for r in self.validation_results if r['status'] == 'ERROR')
        warning_count = sum(1 for r in self.validation_results if r['status'] == 'WARNING')
        ok_count = sum(1 for r in self.validation_results if r['status'] == 'OK')

        if self.has_errors:
            report += f"**総合判定**: ✗ エラーあり（修正が必要です）\n\n"
        elif self.has_warnings:
            report += f"**総合判定**: ⚠ 警告あり（確認を推奨します）\n\n"
        else:
            report += f"**総合判定**: ✓ すべての検証をパスしました\n\n"

        report += f"- エラー: {error_count}件\n"
        report += f"- 警告: {warning_count}件\n"
        report += f"- OK: {ok_count}件\n\n"

        # 検証A: 生産能力検証
        report += "## 3. 検証A: 生産能力検証\n\n"

        capacity_results = [r for r in self.validation_results if r['validation_type'] == 'A_Capacity']
        if capacity_results:
            result = capacity_results[0]
            report += f"**判定**: {result['status']}\n\n"
            report += f"- 目標販売数量（下限）: {format_number(result['total_lower'])}本\n"
            report += f"- 目標販売数量（上限）: {format_number(result['total_upper'])}本\n"
            report += f"- 総キャパシティ: {format_number(result['capacity'])}本\n\n"
            report += f"**メッセージ**: {result['message']}\n\n"
            if result['suggestion']:
                report += f"**推奨対応**: {result['suggestion']}\n\n"

        # 検証B: 競争環境検証
        report += "## 4. 検証B: 競争環境検証\n\n"

        competitive_results = [r for r in self.validation_results if r['validation_type'] == 'B_Competitive']
        report += "| セグメント | 目標上限 | 到達可能上限 | 判定 | メッセージ |\n"
        report += "|-----------|---------|------------|------|------------|\n"

        for result in competitive_results:
            status_icon = "✓" if result['status'] == 'OK' else ("⚠" if result['status'] == 'WARNING' else "✗")
            report += f"| {result['segment_code']} | "
            report += f"{format_percentage(result['target_upper'])} | "
            report += f"{format_percentage(result['achievable_upper'])} | "
            report += f"{status_icon} | {result['message']} |\n"

        report += "\n"

        # エラー・警告詳細
        errors_warnings = [r for r in competitive_results if r['status'] in ['ERROR', 'WARNING']]
        if errors_warnings:
            report += "### 修正推奨\n\n"
            for result in errors_warnings:
                report += f"**{result['segment_code']}**: {result['suggestion']}\n\n"

        # 検証C: 戦略整合性検証
        report += "## 5. 検証C: 戦略整合性検証\n\n"

        strategic_results = [r for r in self.validation_results if r['validation_type'] == 'C_Strategic']
        report += "| セグメント | 戦略区分 | 現状シェア | 目標範囲 | 判定 | メッセージ |\n"
        report += "|-----------|---------|-----------|---------|------|------------|\n"

        for result in strategic_results:
            status_icon = "✓" if result['status'] == 'OK' else ("⚠" if result['status'] == 'WARNING' else "✗")
            target_range = f"{format_percentage(result['target_lower'])} 〜 {format_percentage(result['target_upper'])}"
            report += f"| {result['segment_code']} | "
            report += f"{result['strategy_type']} | "
            report += f"{format_percentage(result['current_share'])} | "
            report += f"{target_range} | "
            report += f"{status_icon} | {result['message']} |\n"

        report += "\n"

        # エラー・警告詳細
        errors_warnings = [r for r in strategic_results if r['status'] in ['ERROR', 'WARNING']]
        if errors_warnings:
            report += "### 修正推奨\n\n"
            for result in errors_warnings:
                report += f"**{result['segment_code']}**: {result['suggestion']}\n\n"

        # 次のアクション
        report += "## 6. 次のアクション\n\n"

        if self.has_errors:
            report += "### エラーが検出されました\n\n"
            report += "以下の手順で修正してください：\n\n"
            report += "1. `data/processed/target_share_initial.csv`を開く\n"
            report += "2. 上記の推奨対応に従って`target_share_lower`と`target_share_upper`を修正\n"
            report += "3. Step 3を再実行\n\n"
            report += "```bash\n"
            report += "python scripts/step3_feasibility_validation.py\n"
            report += "```\n\n"

        elif self.has_warnings:
            report += "### 警告が検出されました\n\n"
            report += "推奨対応を確認の上、以下のいずれかを選択してください：\n\n"
            report += "**選択肢1**: 目標を修正する\n"
            report += "1. `data/processed/target_share_initial.csv`を修正\n"
            report += "2. Step 3を再実行\n\n"
            report += "**選択肢2**: このまま続行する\n"
            report += "1. Step 4（最適化実行）に進む\n\n"
            report += "```bash\n"
            report += "python scripts/step4_optimization_execution.py\n"
            report += "```\n\n"

        else:
            report += "### すべての検証をパスしました\n\n"
            report += "Step 4（最適化実行）に進んでください。\n\n"
            report += "```bash\n"
            report += "python scripts/step4_optimization_execution.py\n"
            report += "```\n\n"

        # 出力ファイル
        report += "## 7. 出力ファイル\n\n"
        report += "- `data/processed/validation_result.csv`: 検証結果詳細\n"
        if not self.has_errors:
            report += "- `data/processed/target_share_final.csv`: 最終目標シェア\n"
        report += "\n"

        # ファイルに保存
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"  ✓ レポートを保存: {report_path}")

    def run(self) -> bool:
        """
        Step 3を実行

        Returns:
            True: 成功（エラーなしまたは警告のみ）、False: 失敗（エラーあり）
        """
        # データ読み込み
        if not self.load_data():
            return False

        # 検証A: 生産能力検証
        self.validation_a_capacity()

        # 検証B: 競争環境検証
        self.validation_b_competitive()

        # 検証C: 戦略整合性検証
        self.validation_c_strategic()

        # 検証結果保存
        self.save_validation_results()

        # 最終目標シェア保存
        self.save_target_share_final()

        # レポート生成
        self.generate_validation_report()

        # 結果表示
        print("\n" + "=" * 80)
        if self.has_errors:
            print("✗ Step 3: 検証エラーが検出されました")
            print("=" * 80)
            print("\n目標シェアを修正してから再実行してください。")
            print(f"詳細: {REPORTS_DIR / 'step3_validation_report.md'}")
            return False
        elif self.has_warnings:
            print("⚠ Step 3: 検証で警告が検出されました")
            print("=" * 80)
            print("\nレポートを確認してください。このまま続行も可能です。")
            print(f"詳細: {REPORTS_DIR / 'step3_validation_report.md'}")
            return True
        else:
            print("✓ Step 3: すべての検証をパスしました")
            print("=" * 80)
            print("\nStep 4（最適化実行）に進んでください。")
            return True


def main():
    """メイン関数"""
    validation = FeasibilityValidation()
    success = validation.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
