"""
製品ポートフォリオ最適化フレームワーク v6 - 共通ユーティリティ

このモジュールは、v6フレームワークで使用される共通機能を提供します:
- データスキーマ定義と検証（A-5改善提案）
- Fail-Fast原則によるデータバリデーション（A-6改善提案）
- 設定ファイル読み込み（A-7改善提案）
- 共通ユーティリティ関数

作成日: 2025年12月7日
バージョン: 6.0
"""

import pandas as pd
import yaml
import os
from typing import Dict, List, Any, Optional, Tuple
import sys


# =============================================================================
# データスキーマ定義（A-5: データフォーマットの統一）
# =============================================================================

SCHEMA = {
    "sales_2024": {
        "required_columns": [
            "year",
            "product_code",
            "plant_code",
            "segment_code",
            "customer_code",
            "sales_volume",
            "unit_price",
            "unit_cost",
            "margin_rate"
        ],
        "optional_columns": [
            "product_name",
            "cost_band"
        ],
        "data_types": {
            "year": "int64",
            "product_code": "object",
            "plant_code": "object",
            "segment_code": "object",
            "customer_code": "object",
            "sales_volume": "float64",
            "unit_price": "float64",
            "unit_cost": "float64",
            "margin_rate": "float64"
        },
        "constraints": {
            "sales_volume": {"min": 0, "max": None},
            "unit_price": {"min": 0, "max": None},
            "unit_cost": {"min": 0, "max": None},
            "margin_rate": {"min": 0.0, "max": 1.0}
        }
    },

    "product_master": {
        "required_columns": [
            "product_code",
            "plant_code",
            "segment_code",
            "customer_code",
            "unit_price",
            "unit_cost",
            "unit_profit",
            "margin_rate",
            "sales_volume"
        ],
        "optional_columns": [
            "product_name",
            "cost_band"
        ],
        "data_types": {
            "product_code": "object",
            "plant_code": "object",
            "segment_code": "object",
            "customer_code": "object",
            "unit_price": "float64",
            "unit_cost": "float64",
            "unit_profit": "float64",
            "margin_rate": "float64",
            "sales_volume": "float64"
        },
        "constraints": {
            "unit_price": {"min": 0, "max": None},
            "unit_cost": {"min": 0, "max": None},
            "margin_rate": {"min": 0.0, "max": 1.0},
            "sales_volume": {"min": 0, "max": None}
        },
        "consistency_checks": {
            "unit_profit": "unit_price - unit_cost",
            "margin_rate": "unit_profit / unit_price"
        }
    },

    "market_master": {
        "required_columns": [
            "segment_code",
            "market_size",
            "market_size_after_1y",
            "cagr",
            "current_share",
            "strategy_type"
        ],
        "optional_columns": [],
        "data_types": {
            "segment_code": "object",
            "market_size": "float64",
            "market_size_after_1y": "float64",
            "cagr": "float64",
            "current_share": "float64",
            "strategy_type": "object"
        },
        "constraints": {
            "market_size": {"min": 0, "max": None},
            "market_size_after_1y": {"min": 0, "max": None},
            "cagr": {"min": -1.0, "max": 1.0},
            "current_share": {"min": 0.0, "max": 1.0}
        },
        "enum_values": {
            "segment_code": ["industrial", "electronics", "oil_gas", "others"],
            "strategy_type": ["aggressive_expansion", "maintain", "reduction", "withdrawal"]
        }
    },

    "competitor_master": {
        "required_columns": [
            "segment_code",
            "competitor_code",
            "competitor_share",
            "competitor_strength",
            "acquisition_rate_lower",
            "acquisition_rate_upper"
        ],
        "optional_columns": [],
        "data_types": {
            "segment_code": "object",
            "competitor_code": "object",
            "competitor_share": "float64",
            "competitor_strength": "object",
            "acquisition_rate_lower": "float64",
            "acquisition_rate_upper": "float64"
        },
        "constraints": {
            "competitor_share": {"min": 0.0, "max": 1.0},
            "acquisition_rate_lower": {"min": 0.0, "max": 1.0},
            "acquisition_rate_upper": {"min": 0.0, "max": 1.0}
        },
        "enum_values": {
            "segment_code": ["industrial", "electronics", "oil_gas", "others"],
            "competitor_strength": ["strong", "moderate", "weak"]
        }
    },

    "segment_master": {
        "required_columns": [
            "segment_code",
            "segment_name",
            "strategy_type"
        ],
        "optional_columns": [],
        "data_types": {
            "segment_code": "object",
            "segment_name": "object",
            "strategy_type": "object"
        },
        "constraints": {},
        "enum_values": {
            "segment_code": ["industrial", "electronics", "oil_gas", "others"],
            "strategy_type": ["aggressive_expansion", "maintain", "reduction", "withdrawal"]
        }
    }
}


# =============================================================================
# スキーマ検証関数（A-5: データフォーマットの統一）
# =============================================================================

def validate_dataframe(df: pd.DataFrame, schema_name: str, strict: bool = True) -> Tuple[bool, List[str]]:
    """
    DataFrameがスキーマ定義に準拠しているかを検証します。

    Parameters
    ----------
    df : pd.DataFrame
        検証対象のDataFrame
    schema_name : str
        スキーマ名（"sales_2024", "product_master"など）
    strict : bool, optional
        厳密モード（True: 警告もエラー扱い、False: エラーのみ）

    Returns
    -------
    Tuple[bool, List[str]]
        (検証成功フラグ, エラー/警告メッセージリスト)
    """
    errors = []
    warnings = []

    if schema_name not in SCHEMA:
        errors.append(f"❌ 未定義のスキーマ名: {schema_name}")
        return False, errors

    schema = SCHEMA[schema_name]

    # 1. 必須カラムの存在チェック
    missing_columns = set(schema["required_columns"]) - set(df.columns)
    if missing_columns:
        errors.append(f"❌ 必須カラムが不足: {', '.join(missing_columns)}")

    # 2. 未定義カラムのチェック（警告）
    allowed_columns = set(schema["required_columns"] + schema["optional_columns"])
    extra_columns = set(df.columns) - allowed_columns
    if extra_columns:
        warnings.append(f"⚠️  未定義のカラムが存在: {', '.join(extra_columns)}")

    # 3. データ型チェック
    for col, expected_dtype in schema["data_types"].items():
        if col in df.columns:
            actual_dtype = str(df[col].dtype)
            # float64とint64の互換性を許容
            if expected_dtype == "float64" and actual_dtype in ["int64", "float64"]:
                continue
            if expected_dtype == "int64" and actual_dtype in ["int64", "int32", "int16"]:
                continue
            if expected_dtype == "object" and actual_dtype == "object":
                continue

            if expected_dtype not in actual_dtype:
                errors.append(f"❌ カラム '{col}' のデータ型エラー: 期待={expected_dtype}, 実際={actual_dtype}")

    # 4. 欠損値チェック（必須カラムのみ）
    for col in schema["required_columns"]:
        if col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                errors.append(f"❌ カラム '{col}' に欠損値: {null_count}件")

    # 5. 範囲チェック
    if "constraints" in schema:
        for col, constraint in schema["constraints"].items():
            if col in df.columns:
                if constraint.get("min") is not None:
                    min_violations = (df[col] < constraint["min"]).sum()
                    if min_violations > 0:
                        min_val = df[col].min()
                        errors.append(
                            f"❌ カラム '{col}' の最小値制約違反: {min_violations}件（最小値={min_val}, 制約={constraint['min']}）"
                        )

                if constraint.get("max") is not None:
                    max_violations = (df[col] > constraint["max"]).sum()
                    if max_violations > 0:
                        max_val = df[col].max()
                        errors.append(
                            f"❌ カラム '{col}' の最大値制約違反: {max_violations}件（最大値={max_val}, 制約={constraint['max']}）"
                        )

    # 6. 列挙値チェック
    if "enum_values" in schema:
        for col, allowed_values in schema["enum_values"].items():
            if col in df.columns:
                invalid_values = set(df[col].unique()) - set(allowed_values)
                if invalid_values:
                    errors.append(
                        f"❌ カラム '{col}' に不正な値: {', '.join(map(str, invalid_values))}（許可値: {', '.join(allowed_values)}）"
                    )

    # 7. 整合性チェック
    if "consistency_checks" in schema:
        for check_name, formula in schema["consistency_checks"].items():
            if check_name == "unit_profit" and all(c in df.columns for c in ["unit_price", "unit_cost", "unit_profit"]):
                calculated = df["unit_price"] - df["unit_cost"]
                diff = abs(df["unit_profit"] - calculated)
                violations = (diff > 0.01).sum()  # 誤差±0.01円以内を許容
                if violations > 0:
                    warnings.append(
                        f"⚠️  unit_profit計算式の不一致: {violations}件（許容誤差: ±0.01円）"
                    )

            elif check_name == "margin_rate" and all(c in df.columns for c in ["unit_profit", "unit_price", "margin_rate"]):
                # ゼロ除算を避ける
                non_zero_price = df["unit_price"] > 0
                calculated = df.loc[non_zero_price, "unit_profit"] / df.loc[non_zero_price, "unit_price"]
                actual = df.loc[non_zero_price, "margin_rate"]
                diff = abs(actual - calculated)
                violations = (diff > 0.01).sum()  # 誤差±0.01（1%）以内を許容
                if violations > 0:
                    warnings.append(
                        f"⚠️  margin_rate計算式の不一致: {violations}件（許容誤差: ±0.01）"
                    )

    # 結果の集約
    all_messages = errors + warnings
    is_valid = len(errors) == 0 and (not strict or len(warnings) == 0)

    return is_valid, all_messages


# =============================================================================
# Fail-Fast検証関数（A-6: Fail-Fast原則）
# =============================================================================

def validate_output_data(df: pd.DataFrame, step_name: str, schema_name: Optional[str] = None) -> None:
    """
    処理ステップの出力データを検証し、エラーがあれば即座に停止します（Fail-Fast原則）。

    Parameters
    ----------
    df : pd.DataFrame
        検証対象のDataFrame
    step_name : str
        処理ステップ名（エラーメッセージに使用）
    schema_name : Optional[str], optional
        スキーマ名（指定した場合、スキーマ検証も実施）

    Raises
    ------
    ValueError
        検証エラーが発生した場合
    """
    print(f"\n{'='*80}")
    print(f"📋 データ検証: {step_name}")
    print(f"{'='*80}")

    errors = []

    # 基本チェック
    if df is None:
        errors.append("❌ DataFrameがNoneです")
    elif len(df) == 0:
        errors.append("❌ DataFrameが空です（0行）")

    # スキーマ検証
    if schema_name and df is not None and len(df) > 0:
        is_valid, messages = validate_dataframe(df, schema_name, strict=False)
        if not is_valid:
            errors.extend(messages)
        elif messages:
            # 警告のみの場合は表示して続行
            for msg in messages:
                print(msg)

    # エラーがあれば即座に停止
    if errors:
        print(f"\n❌ {step_name} でエラーが発生しました:")
        for error in errors:
            print(f"  {error}")
        print(f"\n💡 データを修正してから再実行してください。")
        print(f"{'='*80}\n")
        raise ValueError(f"{step_name} の検証に失敗しました")

    print(f"✅ データ検証成功: {len(df):,}行")
    print(f"{'='*80}\n")


# =============================================================================
# 設定ファイル読み込み（A-7: 設定の外部化）
# =============================================================================

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    設定ファイル（config.yaml）を読み込みます。

    Parameters
    ----------
    config_path : str, optional
        設定ファイルのパス（未指定時はデフォルトパスを使用）

    Returns
    -------
    Dict[str, Any]
        設定内容の辞書

    Raises
    ------
    FileNotFoundError
        設定ファイルが見つからない場合
    ValueError
        設定ファイルの形式が不正な場合
    """
    if config_path is None:
        # デフォルトパス: スクリプトと同じディレクトリの ../config/config.yaml
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "..", "config", "config.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 必須キーのチェック
        required_keys = ["version", "plant_capacity", "total_sales_target"]
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ValueError(f"設定ファイルに必須キーが不足: {', '.join(missing_keys)}")

        return config

    except yaml.YAMLError as e:
        raise ValueError(f"設定ファイルの形式エラー: {e}")


# =============================================================================
# データ読み込みユーティリティ
# =============================================================================

def load_csv_with_validation(
    file_path: str,
    schema_name: Optional[str] = None,
    encoding: str = 'utf-8'
) -> pd.DataFrame:
    """
    CSVファイルを読み込み、スキーマ検証を実施します。

    Parameters
    ----------
    file_path : str
        CSVファイルのパス
    schema_name : Optional[str], optional
        スキーマ名（指定した場合、スキーマ検証を実施）
    encoding : str, optional
        文字エンコーディング（デフォルト: utf-8）

    Returns
    -------
    pd.DataFrame
        読み込んだDataFrame

    Raises
    ------
    FileNotFoundError
        ファイルが見つからない場合
    ValueError
        スキーマ検証に失敗した場合
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    try:
        df = pd.read_csv(file_path, encoding=encoding)
    except Exception as e:
        raise ValueError(f"CSVファイルの読み込みエラー: {e}")

    # スキーマ検証
    if schema_name:
        validate_output_data(df, f"CSVファイル読み込み: {os.path.basename(file_path)}", schema_name)

    return df


def save_csv_with_validation(
    df: pd.DataFrame,
    file_path: str,
    schema_name: Optional[str] = None,
    encoding: str = 'utf-8',
    index: bool = False
) -> None:
    """
    DataFrameをCSVファイルに保存し、スキーマ検証を実施します。

    Parameters
    ----------
    df : pd.DataFrame
        保存するDataFrame
    file_path : str
        保存先のファイルパス
    schema_name : Optional[str], optional
        スキーマ名（指定した場合、スキーマ検証を実施）
    encoding : str, optional
        文字エンコーディング（デフォルト: utf-8）
    index : bool, optional
        インデックスを保存するか（デフォルト: False）

    Raises
    ------
    ValueError
        スキーマ検証に失敗した場合
    """
    # スキーマ検証
    if schema_name:
        validate_output_data(df, f"CSVファイル保存: {os.path.basename(file_path)}", schema_name)

    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # CSV保存
    df.to_csv(file_path, encoding=encoding, index=index)
    print(f"✅ ファイル保存完了: {file_path} ({len(df):,}行)")


# =============================================================================
# データサマリー表示
# =============================================================================

def display_dataframe_summary(df: pd.DataFrame, name: str = "DataFrame") -> None:
    """
    DataFrameの概要を表示します。

    Parameters
    ----------
    df : pd.DataFrame
        表示対象のDataFrame
    name : str, optional
        DataFrame名（デフォルト: "DataFrame"）
    """
    print(f"\n{'='*80}")
    print(f"📊 {name} サマリー")
    print(f"{'='*80}")
    print(f"行数: {len(df):,}")
    print(f"列数: {len(df.columns)}")
    print(f"\nカラム一覧:")
    for i, col in enumerate(df.columns, 1):
        dtype = df[col].dtype
        null_count = df[col].isnull().sum()
        null_pct = (null_count / len(df) * 100) if len(df) > 0 else 0
        print(f"  {i:2d}. {col:30s} ({dtype}) - 欠損: {null_count:5d}件 ({null_pct:5.2f}%)")

    print(f"\n先頭5行:")
    print(df.head())
    print(f"{'='*80}\n")


# =============================================================================
# メイン処理（テスト用）
# =============================================================================

if __name__ == "__main__":
    print("="*80)
    print("製品ポートフォリオ最適化フレームワーク v6 - 共通ユーティリティ")
    print("="*80)

    # 設定ファイル読み込みテスト
    try:
        config = load_config()
        print("\n✅ 設定ファイル読み込み成功")
        print(f"  バージョン: {config['version']}")
        print(f"  拠点A生産能力: {config['plant_capacity']['A']:,}本")
        print(f"  拠点B生産能力: {config['plant_capacity']['B']:,}本")
        print(f"  総販売目標: {config['total_sales_target']:,}本")
    except Exception as e:
        print(f"\n❌ 設定ファイル読み込みエラー: {e}")

    # スキーマ定義表示
    print("\n" + "="*80)
    print("定義済みスキーマ:")
    print("="*80)
    for schema_name in SCHEMA.keys():
        required_cols = len(SCHEMA[schema_name]["required_columns"])
        optional_cols = len(SCHEMA[schema_name]["optional_columns"])
        print(f"  - {schema_name:20s}: 必須カラム={required_cols}, オプションカラム={optional_cols}")

    print("\n" + "="*80)
    print("テスト完了")
    print("="*80)
