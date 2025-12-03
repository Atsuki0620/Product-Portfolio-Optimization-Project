"""
製品ポートフォリオ最適化フレームワーク v5 共通モジュール

このモジュールは、v5最適化フレームワークで使用される共通定数と
ユーティリティ関数を提供します。
"""

from pathlib import Path
from typing import Dict, Any
import pandas as pd

# =============================================================================
# パス定義
# =============================================================================

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent

# データディレクトリ
DATA_DIR = PROJECT_ROOT / "data"
MASTER_DIR = DATA_DIR / "master"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# レポートディレクトリ
REPORTS_DIR = PROJECT_ROOT / "reports"

# =============================================================================
# 定数定義
# =============================================================================

# 奪取可能率パラメータ（競争力評価別）
ACQUISITION_RATE = {
    'strong': {'lower': 0.00, 'upper': 0.03},
    'moderate': {'lower': 0.02, 'upper': 0.05},
    'weak': {'lower': 0.05, 'upper': 0.10}
}

# 戦略区分別係数
STRATEGY_COEFFICIENTS = {
    'aggressive_expansion': {'lower': 1.0, 'upper': 1.5},
    'maintain': {'lower': 0.9, 'upper': 1.1},
    'reduction': {'lower': 0.5, 'upper': 1.0},
    'withdrawal': {'lower': 0.0, 'upper': 0.7}
}

# 拠点キャパシティ（本数）
PLANT_CAPACITY = {
    'A': 300_000,
    'B': 204_000
}

# 総キャパシティ
TOTAL_CAPACITY = sum(PLANT_CAPACITY.values())  # 504,000

# 総販売数量目標
TOTAL_SALES_TARGET = 504_000

# 3年計画の年数
PLANNING_YEARS = 3

# =============================================================================
# ユーティリティ関数
# =============================================================================

def calculate_market_size_after_3y(current_size: float, cagr: float) -> float:
    """
    3年後の市場規模を計算

    Args:
        current_size: 現在の市場規模
        cagr: 年平均成長率（例: 0.03 = 3%）

    Returns:
        3年後の市場規模
    """
    return current_size * ((1 + cagr) ** PLANNING_YEARS)


def calculate_current_sales_volume(market_size: float, share: float) -> float:
    """
    現在の販売数量を計算

    Args:
        market_size: 市場規模
        share: 市場シェア（例: 0.20 = 20%）

    Returns:
        販売数量
    """
    return market_size * share


def validate_share_sum(shares: Dict[str, float], segment_code: str, tolerance: float = 0.01) -> bool:
    """
    シェア合計が100%になるかを検証

    Args:
        shares: シェアの辞書 {'our_company': 0.20, 'competitor_a': 0.30, ...}
        segment_code: セグメントコード（エラーメッセージ用）
        tolerance: 許容誤差（デフォルト: 1%）

    Returns:
        True: 合計が100%±tolerance、False: それ以外
    """
    total = sum(shares.values())
    if abs(total - 1.0) > tolerance:
        print(f"警告: {segment_code}のシェア合計が{total*100:.2f}%です（100%±{tolerance*100}%の範囲外）")
        return False
    return True


def get_acquisition_rate(competitive_position: str, bound: str = 'upper') -> float:
    """
    奪取可能率を取得

    Args:
        competitive_position: 競争力評価（'strong', 'moderate', 'weak'）
        bound: 'lower'または'upper'

    Returns:
        奪取可能率

    Raises:
        ValueError: 不正な競争力評価またはbound指定
    """
    if competitive_position not in ACQUISITION_RATE:
        raise ValueError(f"不正な競争力評価: {competitive_position}")
    if bound not in ['lower', 'upper']:
        raise ValueError(f"boundは'lower'または'upper'を指定してください: {bound}")

    return ACQUISITION_RATE[competitive_position][bound]


def get_strategy_coefficient(strategy_type: str, bound: str = 'upper') -> float:
    """
    戦略係数を取得

    Args:
        strategy_type: 戦略区分（'aggressive_expansion', 'maintain', 'reduction', 'withdrawal'）
        bound: 'lower'または'upper'

    Returns:
        戦略係数

    Raises:
        ValueError: 不正な戦略区分またはbound指定
    """
    if strategy_type not in STRATEGY_COEFFICIENTS:
        raise ValueError(f"不正な戦略区分: {strategy_type}")
    if bound not in ['lower', 'upper']:
        raise ValueError(f"boundは'lower'または'upper'を指定してください: {bound}")

    return STRATEGY_COEFFICIENTS[strategy_type][bound]


def load_csv_with_validation(file_path: Path, required_columns: list = None) -> pd.DataFrame:
    """
    CSVファイルを読み込み、必須カラムの存在を検証

    Args:
        file_path: CSVファイルパス
        required_columns: 必須カラムのリスト（Noneの場合は検証なし）

    Returns:
        DataFrame

    Raises:
        FileNotFoundError: ファイルが存在しない
        ValueError: 必須カラムが不足している
    """
    if not file_path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    df = pd.read_csv(file_path)

    if required_columns:
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"必須カラムが不足しています: {missing_columns}")

    return df


def save_csv_with_backup(df: pd.DataFrame, file_path: Path, backup: bool = True) -> None:
    """
    DataFrameをCSVとして保存（既存ファイルがある場合はバックアップ）

    Args:
        df: 保存するDataFrame
        file_path: 保存先パス
        backup: Trueの場合、既存ファイルを.bakとしてバックアップ
    """
    if backup and file_path.exists():
        backup_path = file_path.with_suffix('.csv.bak')
        file_path.rename(backup_path)
        print(f"既存ファイルをバックアップ: {backup_path}")

    df.to_csv(file_path, index=False, encoding='utf-8-sig')
    print(f"ファイルを保存: {file_path}")


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    浮動小数点数をパーセンテージ文字列に変換

    Args:
        value: 数値（例: 0.25 = 25%）
        decimals: 小数点以下の桁数

    Returns:
        パーセンテージ文字列（例: "25.0%"）
    """
    return f"{value * 100:.{decimals}f}%"


def format_number(value: float, decimals: int = 0) -> str:
    """
    数値をカンマ区切りの文字列に変換

    Args:
        value: 数値
        decimals: 小数点以下の桁数

    Returns:
        カンマ区切りの文字列（例: "1,000,000"）
    """
    return f"{value:,.{decimals}f}"


def create_report_header(title: str, step: str, date: str = None) -> str:
    """
    Markdownレポートのヘッダーを生成

    Args:
        title: レポートタイトル
        step: ステップ名（例: "Step 1"）
        date: 日付（Noneの場合は自動設定）

    Returns:
        Markdownヘッダー文字列
    """
    if date is None:
        from datetime import datetime
        date = datetime.now().strftime('%Y年%m月%d日')

    header = f"""# {title}

**ステップ**: {step}
**実行日**: {date}

---

"""
    return header


# =============================================================================
# バリデーション関数
# =============================================================================

def validate_positive_number(value: float, name: str) -> None:
    """
    正の数値であることを検証

    Args:
        value: 検証する値
        name: 値の名前（エラーメッセージ用）

    Raises:
        ValueError: 値が正でない場合
    """
    if value <= 0:
        raise ValueError(f"{name}は正の数値である必要があります: {value}")


def validate_share_range(share: float, name: str) -> None:
    """
    シェアが0〜1の範囲内であることを検証

    Args:
        share: 検証するシェア値
        name: 値の名前（エラーメッセージ用）

    Raises:
        ValueError: シェアが範囲外の場合
    """
    if not (0 <= share <= 1):
        raise ValueError(f"{name}は0〜1の範囲である必要があります: {share}")


def validate_strategy_type(strategy_type: str) -> None:
    """
    戦略区分が有効であることを検証

    Args:
        strategy_type: 検証する戦略区分

    Raises:
        ValueError: 戦略区分が不正な場合
    """
    if strategy_type not in STRATEGY_COEFFICIENTS:
        valid_types = list(STRATEGY_COEFFICIENTS.keys())
        raise ValueError(f"不正な戦略区分: {strategy_type}. 有効な値: {valid_types}")


def validate_competitive_position(competitive_position: str) -> None:
    """
    競争力評価が有効であることを検証

    Args:
        competitive_position: 検証する競争力評価

    Raises:
        ValueError: 競争力評価が不正な場合
    """
    if competitive_position not in ACQUISITION_RATE:
        valid_positions = list(ACQUISITION_RATE.keys())
        raise ValueError(f"不正な競争力評価: {competitive_position}. 有効な値: {valid_positions}")


# =============================================================================
# デバッグ用関数
# =============================================================================

def print_constants() -> None:
    """定数情報を表示（デバッグ用）"""
    print("=" * 80)
    print("製品ポートフォリオ最適化フレームワーク v5 定数情報")
    print("=" * 80)
    print(f"\n【拠点キャパシティ】")
    for plant, capacity in PLANT_CAPACITY.items():
        print(f"  Plant {plant}: {format_number(capacity)}本")
    print(f"  合計: {format_number(TOTAL_CAPACITY)}本")

    print(f"\n【総販売数量目標】")
    print(f"  {format_number(TOTAL_SALES_TARGET)}本")

    print(f"\n【奪取可能率パラメータ】")
    for position, rates in ACQUISITION_RATE.items():
        print(f"  {position}: {format_percentage(rates['lower'])} 〜 {format_percentage(rates['upper'])}")

    print(f"\n【戦略係数】")
    for strategy, coefs in STRATEGY_COEFFICIENTS.items():
        print(f"  {strategy}: {coefs['lower']:.1f} 〜 {coefs['upper']:.1f}")

    print("=" * 80)


if __name__ == "__main__":
    # モジュールを直接実行した場合、定数情報を表示
    print_constants()
