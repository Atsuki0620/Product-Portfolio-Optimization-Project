#!/usr/bin/env python3
"""
2024年データ検証スクリプト (v4)

このスクリプトは、generate_sample_data_v4.py が生成したデータが
01_data_requirements_2024.md の要件を満たしているか検証し、レポートを出力します。
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


# ===========================
# 定数定義
# ===========================
TOTAL_ANNUAL_SALES_QTY_2024 = 504_000
PLANT_A_CAPACITY = 300_000
PLANT_B_CAPACITY = 204_000

# セグメント販売比（理論値）
SEGMENT_SALES_MIX = {
    'industrial': 0.40,
    'electronics': 0.25,
    'oil_gas': 0.10,
    'others': 0.25
}

# セグメント別ターゲット粗利率
TARGET_MARGIN_RATE = {
    'industrial': 0.10,
    'electronics': 0.20,
    'oil_gas': 0.50,
    'others': 0.20
}

# 許容誤差（パーセントポイント）
SEGMENT_MIX_TOLERANCE = 3.0  # ±3ポイント
MARGIN_RATE_TOLERANCE = 5.0  # ±5ポイント


# ===========================
# 検証関数
# ===========================

class ValidationResult:
    """検証結果を保持するクラス"""
    def __init__(self):
        self.results = []
        self.details = []

    def add(self, check_name: str, passed: bool, message: str, detail: str = ""):
        """検証結果を追加"""
        self.results.append({
            'check': check_name,
            'passed': passed,
            'message': message
        })
        if detail:
            self.details.append(detail)

    def print_summary(self):
        """検証結果サマリーを表示"""
        print("\n" + "=" * 70)
        print("検証結果サマリー")
        print("=" * 70)

        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r['passed'])
        failed_checks = total_checks - passed_checks

        for result in self.results:
            status = "✓ OK" if result['passed'] else "✗ NG"
            print(f"{status:6} | {result['check']:40} | {result['message']}")

        print("=" * 70)
        print(f"合計: {total_checks} 件 | 成功: {passed_checks} 件 | 失敗: {failed_checks} 件")
        print("=" * 70)

        if failed_checks == 0:
            print("\n全ての検証項目が合格しました！")
        else:
            print(f"\n{failed_checks} 件の検証項目が不合格です。詳細を確認してください。")

        return failed_checks == 0

    def get_details(self):
        """詳細情報を取得"""
        return "\n\n".join(self.details)


def load_data(data_dir: Path):
    """データを読み込む"""
    sales_path = data_dir / "sales_2024.csv"
    production_path = data_dir / "production_2024.csv"

    if not sales_path.exists():
        raise FileNotFoundError(f"販売データが見つかりません: {sales_path}")
    if not production_path.exists():
        raise FileNotFoundError(f"生産データが見つかりません: {production_path}")

    sales_df = pd.read_csv(sales_path)
    production_df = pd.read_csv(production_path)

    return sales_df, production_df


def validate_sales_total_qty(sales_df: pd.DataFrame, result: ValidationResult):
    """販売数量の合計を検証"""
    total_qty = sales_df['sales_qty'].sum()
    passed = total_qty == TOTAL_ANNUAL_SALES_QTY_2024

    message = f"{total_qty:,} 本"
    if not passed:
        message += f" (期待値: {TOTAL_ANNUAL_SALES_QTY_2024:,} 本)"

    result.add(
        "販売数量の合計",
        passed,
        message,
        f"### 販売数量の合計\n- 実際: {total_qty:,} 本\n- 期待値: {TOTAL_ANNUAL_SALES_QTY_2024:,} 本\n- 差分: {total_qty - TOTAL_ANNUAL_SALES_QTY_2024:,} 本"
    )


def validate_segment_sales_mix(sales_df: pd.DataFrame, result: ValidationResult):
    """セグメント販売比を検証"""
    total_qty = sales_df['sales_qty'].sum()
    segment_qty = sales_df.groupby('segment')['sales_qty'].sum()

    detail = "### セグメント別販売数量\n\n| セグメント | 実販売数量 | 実販売比 | 理論販売数量 | 理論販売比 | 差分 (pp) | 判定 |\n"
    detail += "|-----------|-----------|---------|-------------|-----------|-----------|------|\n"

    all_passed = True
    for segment, mix in SEGMENT_SALES_MIX.items():
        actual_qty = segment_qty.get(segment, 0)
        actual_mix = actual_qty / total_qty * 100
        theoretical_qty = TOTAL_ANNUAL_SALES_QTY_2024 * mix
        theoretical_mix = mix * 100
        diff_pp = actual_mix - theoretical_mix

        passed = abs(diff_pp) <= SEGMENT_MIX_TOLERANCE

        status = "OK" if passed else "NG"
        detail += f"| {segment:12} | {actual_qty:>9,} | {actual_mix:>6.2f}% | {theoretical_qty:>11,.0f} | {theoretical_mix:>9.2f}% | {diff_pp:>8.2f} | {status} |\n"

        if not passed:
            all_passed = False

    result.add(
        "セグメント販売比",
        all_passed,
        f"±{SEGMENT_MIX_TOLERANCE}pp 以内" if all_passed else f"一部が ±{SEGMENT_MIX_TOLERANCE}pp を超過",
        detail
    )


def validate_plant_capacity(sales_df: pd.DataFrame, result: ValidationResult):
    """拠点キャパシティを検証"""
    plant_qty = sales_df.groupby('plant')['sales_qty'].sum()

    detail = "### 拠点別販売数量\n\n| 拠点 | 販売数量 | キャパシティ | 使用率 | 判定 |\n"
    detail += "|------|---------|------------|--------|------|\n"

    all_passed = True
    for plant, capacity in [('A', PLANT_A_CAPACITY), ('B', PLANT_B_CAPACITY)]:
        qty = plant_qty.get(plant, 0)
        usage_rate = qty / capacity * 100
        passed = qty <= capacity

        status = "OK" if passed else "NG"
        detail += f"| {plant:4} | {qty:>7,} | {capacity:>10,} | {usage_rate:>5.2f}% | {status} |\n"

        if not passed:
            all_passed = False

    result.add(
        "拠点キャパシティ（販売）",
        all_passed,
        "キャパシティ内" if all_passed else "キャパシティ超過",
        detail
    )


def validate_production_consistency(sales_df: pd.DataFrame, production_df: pd.DataFrame, result: ValidationResult):
    """生産数量と販売数量の整合性を検証"""
    # sales_df から product × plant ごとの合計を計算
    sales_grouped = sales_df.groupby(['product_code', 'plant'])['sales_qty'].sum().reset_index()
    sales_grouped = sales_grouped.rename(columns={'sales_qty': 'sales_qty_sum'})

    # production_df とマージ
    merged = production_df.merge(sales_grouped, on=['product_code', 'plant'], how='outer')

    # 差分を計算
    merged['diff'] = merged['production_qty'].fillna(0) - merged['sales_qty_sum'].fillna(0)

    # 差分がある行を抽出
    inconsistent = merged[merged['diff'] != 0]

    passed = len(inconsistent) == 0

    detail = "### 生産数量と販売数量の整合性\n\n"
    if passed:
        detail += "全ての製品×拠点で生産数量 = 販売数量が成立しています。\n"
    else:
        detail += f"**不整合が {len(inconsistent)} 件見つかりました：**\n\n"
        detail += "| 製品コード | 拠点 | 生産数量 | 販売数量 | 差分 |\n"
        detail += "|-----------|------|---------|---------|------|\n"
        for _, row in inconsistent.iterrows():
            detail += f"| {row['product_code']} | {row['plant']} | {row['production_qty']:.0f} | {row['sales_qty_sum']:.0f} | {row['diff']:.0f} |\n"

    result.add(
        "生産数量と販売数量の整合性",
        passed,
        "整合" if passed else f"{len(inconsistent)} 件の不整合",
        detail
    )


def validate_production_capacity(production_df: pd.DataFrame, result: ValidationResult):
    """生産キャパシティを検証"""
    plant_qty = production_df.groupby('plant')['production_qty'].sum()

    detail = "### 拠点別生産数量\n\n| 拠点 | 生産数量 | キャパシティ | 使用率 | 判定 |\n"
    detail += "|------|---------|------------|--------|------|\n"

    all_passed = True
    for plant, capacity in [('A', PLANT_A_CAPACITY), ('B', PLANT_B_CAPACITY)]:
        qty = plant_qty.get(plant, 0)
        usage_rate = qty / capacity * 100
        passed = qty <= capacity

        status = "OK" if passed else "NG"
        detail += f"| {plant:4} | {qty:>7,} | {capacity:>10,} | {usage_rate:>5.2f}% | {status} |\n"

        if not passed:
            all_passed = False

    result.add(
        "拠点キャパシティ（生産）",
        all_passed,
        "キャパシティ内" if all_passed else "キャパシティ超過",
        detail
    )


def validate_margin_rate(sales_df: pd.DataFrame, result: ValidationResult):
    """セグメント別粗利率を検証"""
    # 加重平均粗利率を計算（売上金額でウェイト）
    segment_margin = sales_df.groupby('segment').apply(
        lambda g: (g['margin_rate'] * g['sales_amount']).sum() / g['sales_amount'].sum()
    )

    detail = "### セグメント別粗利率\n\n| セグメント | 実粗利率 | ターゲット粗利率 | 差分 (pp) | 判定 |\n"
    detail += "|-----------|---------|----------------|-----------|------|\n"

    all_passed = True
    for segment, target_margin in TARGET_MARGIN_RATE.items():
        actual_margin = segment_margin.get(segment, 0) * 100
        target = target_margin * 100
        diff_pp = actual_margin - target

        passed = abs(diff_pp) <= MARGIN_RATE_TOLERANCE

        status = "OK" if passed else "NG"
        detail += f"| {segment:12} | {actual_margin:>6.2f}% | {target:>13.2f}% | {diff_pp:>8.2f} | {status} |\n"

        if not passed:
            all_passed = False

    result.add(
        "セグメント別粗利率",
        all_passed,
        f"±{MARGIN_RATE_TOLERANCE}pp 以内" if all_passed else f"一部が ±{MARGIN_RATE_TOLERANCE}pp を超過",
        detail
    )


def generate_markdown_report(sales_df: pd.DataFrame, production_df: pd.DataFrame,
                            result: ValidationResult, output_path: Path):
    """Markdown形式のレポートを生成"""
    report = f"""# データ検証レポート（2024年版 v4）

**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 1. 検証サマリー

"""

    # 検証結果テーブル
    report += "| 検証項目 | 結果 | 詳細 |\n"
    report += "|---------|------|------|\n"

    for r in result.results:
        status = "✓ 合格" if r['passed'] else "✗ 不合格"
        report += f"| {r['check']} | {status} | {r['message']} |\n"

    # 詳細情報
    report += "\n---\n\n## 2. 検証詳細\n\n"
    report += result.get_details()

    # データサマリー
    report += "\n\n---\n\n## 3. データサマリー\n\n"
    report += f"### 販売データ（D1）\n\n"
    report += f"- 総行数: {len(sales_df):,} 行\n"
    report += f"- 総販売数量: {sales_df['sales_qty'].sum():,} 本\n"
    report += f"- 総売上金額: {sales_df['sales_amount'].sum():,.0f} 円\n"
    report += f"- 平均単価: {sales_df['unit_price'].mean():,.0f} 円\n"
    report += f"- 平均粗利率: {(sales_df['margin_rate'] * sales_df['sales_amount']).sum() / sales_df['sales_amount'].sum() * 100:.2f}%\n\n"

    report += f"### 生産データ（D2）\n\n"
    report += f"- 総行数: {len(production_df):,} 行\n"
    report += f"- 総生産数量: {production_df['production_qty'].sum():,} 本\n"
    report += f"- 総原価金額: {production_df['cost_amount'].sum():,.0f} 円\n"
    report += f"- 平均単位原価: {production_df['unit_cost'].mean():,.0f} 円\n"

    # ファイルに保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✓ レポートを保存: {output_path}")


# ===========================
# メイン処理
# ===========================

def main():
    parser = argparse.ArgumentParser(
        description="2024年データ検証スクリプト (v4)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="データディレクトリ（デフォルト: ../data/raw）"
    )
    parser.add_argument(
        "--report-dir",
        type=str,
        default=None,
        help="レポート出力ディレクトリ（デフォルト: ../reports）"
    )

    args = parser.parse_args()

    # スクリプトのディレクトリを基準にパスを設定
    script_dir = Path(__file__).parent
    data_dir = Path(args.data_dir) if args.data_dir else script_dir.parent / "data" / "raw"
    report_dir = Path(args.report_dir) if args.report_dir else script_dir.parent / "reports"

    print("=== 2024年データ検証スクリプト (v4) ===\n")
    print(f"データディレクトリ: {data_dir}")
    print(f"レポート出力ディレクトリ: {report_dir}\n")

    # データの読み込み
    print("データを読み込み中...")
    try:
        sales_df, production_df = load_data(data_dir)
        print(f"  - 販売データ（D1）: {len(sales_df)} 行")
        print(f"  - 生産データ（D2）: {len(production_df)} 行\n")
    except Exception as e:
        print(f"エラー: データの読み込みに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    # 検証実行
    print("検証を実行中...\n")
    result = ValidationResult()

    validate_sales_total_qty(sales_df, result)
    validate_segment_sales_mix(sales_df, result)
    validate_plant_capacity(sales_df, result)
    validate_production_consistency(sales_df, production_df, result)
    validate_production_capacity(production_df, result)
    validate_margin_rate(sales_df, result)

    # 結果表示
    all_passed = result.print_summary()

    # レポート生成
    report_path = report_dir / "validation_2024_v4.md"
    generate_markdown_report(sales_df, production_df, result, report_path)

    # 終了コード
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
