"""
Step 1: データ準備

市場マスタと競合マスタを整備し、導出値を算出します。
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# 共通モジュールのインポート
from optimization_common_v5 import (
    MASTER_DIR, PROCESSED_DIR, REPORTS_DIR,
    calculate_market_size_after_3y,
    calculate_current_sales_volume,
    validate_share_sum,
    load_csv_with_validation,
    save_csv_with_backup,
    create_report_header,
    format_percentage,
    format_number,
    validate_positive_number,
    validate_share_range,
    validate_strategy_type,
    validate_competitive_position
)


class DataPreparation:
    """Step 1: データ準備クラス"""

    def __init__(self):
        """初期化"""
        self.market_master = None
        self.competitor_master = None
        self.validation_errors = []
        self.validation_warnings = []

    def load_masters(self) -> bool:
        """
        マスタファイルを読み込み

        Returns:
            True: 成功、False: 失敗
        """
        print("=" * 80)
        print("Step 1: データ準備 - マスタファイル読み込み")
        print("=" * 80)

        try:
            # 市場マスタ読み込み
            print("\n[1/2] 市場マスタ読み込み...")
            market_path = MASTER_DIR / "market_master.csv"
            required_columns = ['segment_code', 'current_market_size', 'market_cagr',
                              'current_share', 'strategy_type']
            self.market_master = load_csv_with_validation(market_path, required_columns)
            print(f"  ✓ {len(self.market_master)}セグメントのデータを読み込みました")

            # 競合マスタ読み込み
            print("\n[2/2] 競合マスタ読み込み...")
            competitor_path = MASTER_DIR / "competitor_master.csv"
            required_columns = ['competitor_code', 'competitor_name', 'segment_code',
                              'current_share', 'competitive_position']
            self.competitor_master = load_csv_with_validation(competitor_path, required_columns)
            print(f"  ✓ {len(self.competitor_master)}件の競合データを読み込みました")

            return True

        except Exception as e:
            print(f"\n✗ エラー: {e}")
            return False

    def validate_data_integrity(self) -> bool:
        """
        データ整合性チェック

        Returns:
            True: 整合性OK、False: エラーあり
        """
        print("\n" + "=" * 80)
        print("データ整合性チェック")
        print("=" * 80)

        has_error = False

        # 市場マスタの検証
        print("\n[市場マスタの検証]")
        for idx, row in self.market_master.iterrows():
            segment = row['segment_code']

            # 正の数値チェック
            try:
                validate_positive_number(row['current_market_size'], f"{segment}の市場規模")
            except ValueError as e:
                self.validation_errors.append(str(e))
                has_error = True

            # シェア範囲チェック
            try:
                validate_share_range(row['current_share'], f"{segment}の自社シェア")
            except ValueError as e:
                self.validation_errors.append(str(e))
                has_error = True

            # 戦略区分チェック
            try:
                validate_strategy_type(row['strategy_type'])
            except ValueError as e:
                self.validation_errors.append(str(e))
                has_error = True

            # CAGR範囲チェック（-50%〜+50%の範囲を想定）
            if not (-0.5 <= row['market_cagr'] <= 0.5):
                msg = f"{segment}のCAGR {row['market_cagr']*100:.1f}%が想定範囲外です"
                self.validation_warnings.append(msg)

        if not has_error:
            print("  ✓ 市場マスタの検証: OK")

        # 競合マスタの検証
        print("\n[競合マスタの検証]")
        for idx, row in self.competitor_master.iterrows():
            competitor = row['competitor_code']
            segment = row['segment_code']

            # シェア範囲チェック
            try:
                validate_share_range(row['current_share'], f"{competitor}の{segment}シェア")
            except ValueError as e:
                self.validation_errors.append(str(e))
                has_error = True

            # 競争力評価チェック
            try:
                validate_competitive_position(row['competitive_position'])
            except ValueError as e:
                self.validation_errors.append(str(e))
                has_error = True

        if not has_error:
            print("  ✓ 競合マスタの検証: OK")

        # シェア合計チェック
        print("\n[セグメント別シェア合計チェック]")
        for segment in self.market_master['segment_code']:
            # 自社シェア
            our_share = self.market_master[
                self.market_master['segment_code'] == segment
            ]['current_share'].values[0]

            # 競合シェア合計
            competitor_shares = self.competitor_master[
                self.competitor_master['segment_code'] == segment
            ]['current_share'].sum()

            total_share = our_share + competitor_shares

            # 合計が100%±1%の範囲内かチェック
            if abs(total_share - 1.0) > 0.01:
                msg = f"{segment}: シェア合計 = {format_percentage(total_share)} (100%から乖離)"
                self.validation_errors.append(msg)
                has_error = True
            else:
                print(f"  ✓ {segment}: シェア合計 = {format_percentage(total_share, 2)}")

        # エラー・警告の表示
        if self.validation_errors:
            print("\n" + "!" * 80)
            print("検証エラー:")
            for error in self.validation_errors:
                print(f"  ✗ {error}")
            print("!" * 80)

        if self.validation_warnings:
            print("\n" + "-" * 80)
            print("警告:")
            for warning in self.validation_warnings:
                print(f"  ⚠ {warning}")
            print("-" * 80)

        return not has_error

    def calculate_derived_values(self) -> None:
        """導出値を算出"""
        print("\n" + "=" * 80)
        print("導出値の算出")
        print("=" * 80)

        # 市場マスタに導出値を追加
        print("\n[1/2] 3年後市場規模の算出...")
        self.market_master['market_size_after_3y'] = self.market_master.apply(
            lambda row: calculate_market_size_after_3y(
                row['current_market_size'],
                row['market_cagr']
            ),
            axis=1
        )

        # 自社の現在販売数量も算出
        self.market_master['current_sales_volume'] = self.market_master.apply(
            lambda row: calculate_current_sales_volume(
                row['current_market_size'],
                row['current_share']
            ),
            axis=1
        )

        # 結果を表示
        for idx, row in self.market_master.iterrows():
            segment = row['segment_code']
            current = row['current_market_size']
            after_3y = row['market_size_after_3y']
            cagr = row['market_cagr']
            change = ((after_3y - current) / current) * 100

            print(f"  {segment}:")
            print(f"    現在市場規模: {format_number(current)}本")
            print(f"    3年後市場規模: {format_number(after_3y)}本 (CAGR: {format_percentage(cagr)}, 変化: {change:+.1f}%)")
            print(f"    自社販売数量: {format_number(row['current_sales_volume'])}本 (シェア: {format_percentage(row['current_share'])})")

        # 競合マスタに導出値を追加
        print("\n[2/2] 競合の現在販売数量の算出...")
        # 各セグメントの市場規模を取得
        segment_market_size = self.market_master.set_index('segment_code')['current_market_size'].to_dict()

        self.competitor_master['current_sales_volume'] = self.competitor_master.apply(
            lambda row: calculate_current_sales_volume(
                segment_market_size[row['segment_code']],
                row['current_share']
            ),
            axis=1
        )

        print(f"  ✓ {len(self.competitor_master)}件の競合販売数量を算出しました")

    def save_processed_masters(self) -> None:
        """処理済みマスタを保存"""
        print("\n" + "=" * 80)
        print("処理済みマスタの保存")
        print("=" * 80)

        # ディレクトリが存在しない場合は作成
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

        # 市場マスタ保存
        market_output = PROCESSED_DIR / "market_master_processed.csv"
        save_csv_with_backup(self.market_master, market_output, backup=False)

        # 競合マスタ保存
        competitor_output = PROCESSED_DIR / "competitor_master_processed.csv"
        save_csv_with_backup(self.competitor_master, competitor_output, backup=False)

    def generate_validation_report(self) -> None:
        """検証レポートを生成"""
        print("\n" + "=" * 80)
        print("検証レポートの生成")
        print("=" * 80)

        # ディレクトリが存在しない場合は作成
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        report_path = REPORTS_DIR / "step1_validation_report.md"

        # レポート作成
        report = create_report_header(
            "Step 1: データ準備 検証レポート",
            "Step 1: Data Preparation"
        )

        # 概要
        report += "## 1. 概要\n\n"
        report += "市場マスタと競合マスタを整備し、最適化に必要な導出値を算出しました。\n\n"

        # マスタ情報
        report += "## 2. マスタ情報\n\n"
        report += f"- **市場マスタ**: {len(self.market_master)}セグメント\n"
        report += f"- **競合マスタ**: {len(self.competitor_master)}件（"
        report += f"{len(self.competitor_master['competitor_code'].unique())}社）\n\n"

        # セグメント別市場規模
        report += "## 3. セグメント別市場規模\n\n"
        report += "| セグメント | 現在市場規模 | CAGR | 3年後市場規模 | 変化率 |\n"
        report += "|-----------|-------------|------|--------------|-------|\n"

        for idx, row in self.market_master.iterrows():
            segment = row['segment_code']
            current = row['current_market_size']
            after_3y = row['market_size_after_3y']
            cagr = row['market_cagr']
            change = ((after_3y - current) / current) * 100

            report += f"| {segment} | {format_number(current)} | "
            report += f"{format_percentage(cagr)} | {format_number(after_3y)} | "
            report += f"{change:+.1f}% |\n"

        # セグメント別自社シェアと戦略
        report += "\n## 4. セグメント別自社シェアと戦略\n\n"
        report += "| セグメント | 自社シェア | 自社販売数量 | 戦略区分 |\n"
        report += "|-----------|-----------|-------------|----------|\n"

        for idx, row in self.market_master.iterrows():
            segment = row['segment_code']
            share = row['current_share']
            volume = row['current_sales_volume']
            strategy = row['strategy_type']

            report += f"| {segment} | {format_percentage(share)} | "
            report += f"{format_number(volume)} | {strategy} |\n"

        # セグメント別競合状況
        report += "\n## 5. セグメント別競合状況\n\n"

        for segment in self.market_master['segment_code']:
            report += f"### {segment}\n\n"
            report += "| 競合 | シェア | 販売数量 | 競争力評価 |\n"
            report += "|------|-------|---------|------------|\n"

            competitors = self.competitor_master[
                self.competitor_master['segment_code'] == segment
            ].sort_values('current_share', ascending=False)

            for idx, comp in competitors.iterrows():
                report += f"| {comp['competitor_name']} | "
                report += f"{format_percentage(comp['current_share'])} | "
                report += f"{format_number(comp['current_sales_volume'])} | "
                report += f"{comp['competitive_position']} |\n"

            # 合計
            total_share = competitors['current_share'].sum()
            our_share = self.market_master[
                self.market_master['segment_code'] == segment
            ]['current_share'].values[0]

            report += f"\n**合計**: 競合シェア = {format_percentage(total_share)}, "
            report += f"自社シェア = {format_percentage(our_share)}, "
            report += f"合計 = {format_percentage(total_share + our_share)}\n\n"

        # 検証結果
        report += "## 6. 検証結果\n\n"

        if not self.validation_errors and not self.validation_warnings:
            report += "✓ すべての検証をパスしました。\n\n"
        else:
            if self.validation_errors:
                report += "### エラー\n\n"
                for error in self.validation_errors:
                    report += f"- ✗ {error}\n"
                report += "\n"

            if self.validation_warnings:
                report += "### 警告\n\n"
                for warning in self.validation_warnings:
                    report += f"- ⚠ {warning}\n"
                report += "\n"

        # 出力ファイル
        report += "## 7. 出力ファイル\n\n"
        report += "- `data/processed/market_master_processed.csv`: 処理済み市場マスタ\n"
        report += "- `data/processed/competitor_master_processed.csv`: 処理済み競合マスタ\n\n"

        # 次のステップ
        report += "## 8. 次のステップ\n\n"
        report += "Step 2（目標シェア初期算出）に進んでください。\n\n"
        report += "```bash\n"
        report += "python scripts/step2_target_share_calculation.py\n"
        report += "```\n"

        # ファイルに保存
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"  ✓ レポートを保存: {report_path}")

    def run(self) -> bool:
        """
        Step 1を実行

        Returns:
            True: 成功、False: 失敗
        """
        # マスタ読み込み
        if not self.load_masters():
            return False

        # データ整合性チェック
        if not self.validate_data_integrity():
            print("\n✗ データ整合性チェックでエラーが検出されました。")
            print("  マスタファイルを修正してから再実行してください。")
            return False

        # 導出値算出
        self.calculate_derived_values()

        # 処理済みマスタ保存
        self.save_processed_masters()

        # レポート生成
        self.generate_validation_report()

        print("\n" + "=" * 80)
        print("✓ Step 1: データ準備が完了しました")
        print("=" * 80)
        return True


def main():
    """メイン関数"""
    preparation = DataPreparation()
    success = preparation.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
