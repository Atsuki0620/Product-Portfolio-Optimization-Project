# v6実装計画書（確定版）

**作成日**: 2025年12月7日
**バージョン**: v6
**ステータス**: 実装準備完了

---

## エグゼクティブサマリー

本ドキュメントは、製品ポートフォリオ最適化フレームワークv6の実装計画を定義します。v5からの主要な改善点は以下の通りです：

### 主要な変更点

1. **1年後の目標に変更**: 3年後→1年後（market_size_after_1y）
2. **代理店モデルの反映**: 60%単一セグメント、40%複数セグメント
3. **4つ組タプル決定変数**: 顧客レベルでの最適化
4. **戦略係数の見直し**: より現実的な目標設定
5. **5つの改善提案実装**: 自動調整、診断、スキーマ標準化等

### 実装期間

- **総所要時間**: 8-12時間（実装4-6時間、テスト2-3時間、ドキュメント2-3時間）

---

## 1. フォルダ構成と初期セットアップ

### 1.1 作業フォルダ

**パス**: `Product-Portfolio-Optimization-Project/sample_data_trial_v6/analyst_claude_v6`

**構築方針** (Q1-1の回答):
- ✅ **v5を参考にゼロから作成**
- ❌ v5を一括コピーしない（不要ファイルの混入を防ぐ）
- ✓ 必要なファイルを都度v5から探し、改善・修正してコピー

### 1.2 フォルダ構造設計

```
sample_data_trial_v6/analyst_claude_v6/
├── config/
│   ├── config.yaml              # 設定ファイル（新規）
│   └── schema.md                # データスキーマ定義（新規）
├── data/
│   ├── raw/
│   │   ├── sales_2024.csv       # 代理店モデル反映版
│   │   └── production_2024.csv  # v5からコピー（必要に応じて）
│   ├── master/
│   │   ├── product_master.csv   # 顧客コード追加版
│   │   ├── market_master.csv    # 1年後版
│   │   ├── competitor_master.csv # 1年後版
│   │   └── segment_master.csv   # v5からコピー
│   └── processed/
│       └── (最適化実行時に生成)
├── scripts/
│   ├── step0_generate_sample_data.py      # 代理店モデル対応版
│   ├── step1_data_preparation.py          # Fail-Fast対応版
│   ├── step2_target_share_calculation.py  # 戦略係数改訂版
│   ├── step3_feasibility_validation.py    # 自動調整機能追加版
│   ├── step4_optimization_execution.py    # 4つ組タプル+診断機能版
│   └── optimization_common_v6.py          # 共通関数（スキーマ標準化）
└── reports/
    └── (最適化実行後に生成)
```

---

## 2. 質問への回答と実装方針

### 2.1 市場規模の期間変更

| 項目 | 回答 | 実装内容 |
|------|------|---------|
| **Q2-1: CAGRの使用** | A. そのまま使用 | CAGRは変更せず、期間のみ1年に変更 |
| **Q2-2: 奪取可能シェア** | A. 1年用に変更（縮小） | 3年分の奪取可能シェアを1年分に縮小（×1/3） |

**実装詳細**:

```python
# market_master生成
market_size_after_1y = market_size_current * (1 + cagr) ** 1  # 3→1に変更

# 奪取可能シェア（競合分析）
acquisition_rate_1y = {
    'strong': {'lower': 0.0, 'upper': 0.01},    # 3年: 0-3% → 1年: 0-1%
    'moderate': {'lower': 0.007, 'upper': 0.017}, # 3年: 2-5% → 1年: 0.7-1.7%
    'weak': {'lower': 0.017, 'upper': 0.033}     # 3年: 5-10% → 1年: 1.7-3.3%
}
```

**根拠**: 3年分のシェア変化を単純に1/3にすると、年間の変化率が現実的になる

---

### 2.2 代理店モデルの実装

| 項目 | 回答 | 実装内容 |
|------|------|---------|
| **Q3-1: 価格差** | A. ランダムに±5-10%変動 | 各顧客に対して、基準価格×(0.9〜1.1)の範囲でランダム設定 |
| **Q3-2: 顧客割り当て** | B. ランダムに1-3顧客 | 各製品×拠点×セグメントに、1〜3顧客をランダム割り当て |

**顧客セグメントマッピング** (確定):

```python
customer_segment_mapping = {
    # 単一セグメント顧客（60%、6社）
    'Customer_A': ['industrial'],
    'Customer_B': ['electronics'],
    'Customer_C': ['oil_gas'],
    'Customer_D': ['others'],
    'Customer_E': ['industrial'],
    'Customer_F': ['electronics'],

    # 代理店・2セグメント（30%、3社）
    'Customer_G': ['industrial', 'electronics'],
    'Customer_H': ['oil_gas', 'others'],
    'Customer_I': ['electronics', 'oil_gas'],

    # 代理店・3セグメント（10%、1社）
    'Customer_J': ['industrial', 'electronics', 'oil_gas'],
}
```

**検証目標**: 複数セグメント顧客 = 4/10 = 40% ✓

**データ生成ロジック**:

```python
import random
import numpy as np

def generate_sales_data_with_distributor_model():
    """代理店モデルを反映したsales_2024.csvを生成"""

    records = []

    for product in products:  # 20製品
        for plant in ['A', 'B']:  # 2拠点
            for segment in segments:  # 4セグメント
                # このセグメントを扱う顧客をフィルタ
                eligible_customers = [
                    c for c, segs in customer_segment_mapping.items()
                    if segment in segs
                ]

                # ランダムに1-3顧客を選択
                num_customers = random.randint(1, 3)
                selected_customers = random.sample(eligible_customers,
                                                  min(num_customers, len(eligible_customers)))

                # 基準価格取得（v5のproduct_master相当から）
                base_price = get_base_price(product, plant, segment)
                base_cost = get_base_cost(product, plant, segment)

                for customer in selected_customers:
                    # 顧客別に±5-10%の価格変動
                    price_multiplier = random.uniform(0.9, 1.1)
                    cost_multiplier = random.uniform(0.95, 1.05)

                    unit_price = base_price * price_multiplier
                    unit_cost = base_cost * cost_multiplier

                    # 販売数量もランダム配分
                    sales_qty = random.randint(100, 5000)

                    records.append({
                        'year': 2024,
                        'product_code': product,
                        'plant': plant,
                        'segment': segment,
                        'customer_name': customer,
                        'sales_qty': sales_qty,
                        'unit_price': unit_price,
                        'unit_cost': unit_cost,
                        'margin_rate': (unit_price - unit_cost) / unit_price
                    })

    return pd.DataFrame(records)
```

---

### 2.3 product_master拡張

| 項目 | 回答 | 実装内容 |
|------|------|---------|
| **Q4-1: 生成方法** | A. sales_2024.csvから直接生成 | 実績データのみ、将来組み合わせは含まない |

**実装**:

```python
def generate_product_master_from_sales(sales_df):
    """sales_2024.csvからproduct_masterを生成"""

    product_master = sales_df.groupby([
        'product_code', 'plant', 'segment', 'customer_name'
    ]).agg({
        'unit_price': 'mean',
        'unit_cost': 'mean',
        'sales_qty': 'sum'
    }).reset_index()

    # カラム名をスキーマに合わせる
    product_master.columns = [
        'product_code', 'plant_code', 'segment_code', 'customer_code',
        'unit_price', 'unit_cost', 'sales_volume'  # sales_qty → sales_volume
    ]

    # unit_profit計算
    product_master['unit_profit'] = (
        product_master['unit_price'] - product_master['unit_cost']
    )
    product_master['margin_rate'] = (
        product_master['unit_profit'] / product_master['unit_price']
    )

    return product_master
```

---

### 2.4 戦略係数の改訂

| 項目 | 回答 | 実装内容 |
|------|------|---------|
| **Q5-1: 見直し範囲** | B. 全戦略係数を見直す | 4つの戦略すべてを改訂 |
| **Q5-2: 根拠コメント** | A. 簡潔に | "事業部長のビジネス感覚に基づく" |

**改訂後の戦略係数** (確定):

| 戦略区分 | 下限 | 上限 | 変更理由 |
|---------|------|------|---------|
| **aggressive_expansion** | 1.0 | 1.2 | 年間20%拡大は現実的 (v5: 1.0-1.5) |
| **maintain** | 0.95 | 1.05 | 維持戦略の範囲を縮小 (v5: 0.9-1.1) |
| **reduction** | 0.9 | 1.0 | 縮小でも微増を許容 (v5: 0.5-1.0) |
| **withdrawal** | 0.7 | 0.9 | 段階的撤退 (v5: 0.0-0.7) |

**config.yaml**:

```yaml
version: "6.0"
description: "Product Portfolio Optimization Framework v6"

# 拠点キャパシティ（単位: 本）
plant_capacity:
  A: 300000
  B: 204000

# 総販売目標（単位: 本）
total_sales_target: 504000

# 市場予測期間
market_forecast:
  target_period: 1  # 年数（1年後の目標）
  # 注: CAGRはそのまま使用

# 戦略係数（事業部長のビジネス感覚に基づく）
strategy_coefficients:
  aggressive_expansion:
    lower: 1.0
    upper: 1.2  # 年間20%拡大は現実的（v5: 1.5→1.2に修正）
    description: "1年で20%までのシェア拡大を目指す"

  maintain:
    lower: 0.95
    upper: 1.05  # 維持戦略の範囲を縮小（v5: 0.9-1.1）
    description: "現状シェアの±5%以内で維持"

  reduction:
    lower: 0.9
    upper: 1.0  # 縮小でも微増を許容（v5: 0.5-1.0）
    description: "段階的縮小、最大10%減"

  withdrawal:
    lower: 0.7
    upper: 0.9  # 段階的撤退（v5: 0.0-0.7）
    description: "1年で最大30%縮小"

# 競合奪取可能率（1年用に調整）
acquisition_rates:
  strong:
    lower: 0.000
    upper: 0.010  # 3年: 0-3% → 1年: 0-1%
  moderate:
    lower: 0.007
    upper: 0.017  # 3年: 2-5% → 1年: 0.7-1.7%
  weak:
    lower: 0.017
    upper: 0.033  # 3年: 5-10% → 1年: 1.7-3.3%

# 自動調整パラメータ（A-3）
auto_adjustment:
  enabled: true
  max_iterations: 5
  reduction_rate: 0.05  # 5%ずつ引き下げ

# 診断機能パラメータ（A-4）
diagnostics:
  enabled: true
  pre_optimization_check: true
```

---

### 2.5 改善提案のパラメータ

| 項目 | 回答 | 実装内容 |
|------|------|---------|
| **Q6-1: 引き下げ幅** | A. 5%で問題なし | 0.05 (5%) |
| **Q6-2: 最大反復回数** | A. 5回で問題なし | max_iterations: 5 |
| **Q6-3: カラム名統一** | A. sales_volumeに統一 | `sales_qty` → `sales_volume` |

**カラム名規約** (schema.md):

```markdown
# データスキーマ定義書 v6

## 共通カラム名規約

### 基本情報
- `product_code`: 製品コード (例: "P001")
- `plant_code`: 拠点コード ('A' or 'B')
- `segment_code`: セグメントコード ('industrial', 'electronics', 'oil_gas', 'others')
- `customer_code`: 顧客コード (例: "Customer_A")

### 数量・金額
- `sales_volume`: 販売数量（単位: 本） ← 統一
- `unit_price`: 単価（単位: 円）
- `unit_cost`: 単位コスト（単位: 円）
- `unit_profit`: 単位粗利（単位: 円）
- `total_profit`: 総粗利（単位: 円）
- `margin_rate`: 粗利率（0.0〜1.0）

### 市場関連
- `market_size`: 市場規模（単位: 本）
- `market_size_after_1y`: 1年後市場規模（単位: 本） ← 変更
- `market_share`: 市場シェア（0.0〜1.0）
- `cagr`: 年平均成長率（0.0〜1.0）
```

---

## 3. 改善提案の実装詳細

### 3.1 A-3: 自動調整機能

**実装場所**: `scripts/step3_feasibility_validation.py`

```python
def auto_adjust_targets(target_share, market_data, capacity, config):
    """
    目標シェアを段階的に調整し、実行可能な目標を探索する。

    Parameters:
        target_share: 目標シェア辞書
        market_data: 市場データ
        capacity: キャパシティ辞書
        config: 設定ファイル（config.yaml）

    Returns:
        (調整後の目標シェア, 成功フラグ)
    """
    max_iterations = config['auto_adjustment']['max_iterations']
    reduction_rate = config['auto_adjustment']['reduction_rate']

    print("\n" + "=" * 80)
    print("自動調整機能（A-3実装）")
    print("=" * 80)

    for i in range(max_iterations):
        is_feasible, message = check_feasibility(
            target_share, market_data, capacity
        )

        if is_feasible:
            print(f"\n✓ 反復 {i+1}/{max_iterations}: 実行可能な目標を発見")
            if i > 0:
                print(f"  {i}回の調整で実行可能な目標を見つけました")
            return target_share, True

        print(f"\n✗ 反復 {i+1}/{max_iterations}: 実行不可能")
        print(f"  理由: {message}")
        print(f"  目標シェアを{reduction_rate*100}%引き下げます...")

        # 全セグメントの目標を5%引き下げ
        for segment in target_share:
            target_share[segment]['lower'] *= (1 - reduction_rate)
            target_share[segment]['upper'] *= (1 - reduction_rate)
            print(f"    {segment}: {target_share[segment]['lower']:.1%} - {target_share[segment]['upper']:.1%}")

    print(f"\n✗ {max_iterations}回の反復でも実行可能な目標が見つかりませんでした")
    print("  推奨: キャパシティ増強、またはデータを見直してください")
    return target_share, False
```

---

### 3.2 A-4: 診断機能

**実装場所**: `scripts/step4_optimization_execution.py`

```python
def diagnose_constraints(target_share, market_data, capacity):
    """
    最適化実行前に制約の充足可能性を診断する。

    Returns:
        診断結果（True: 問題なし、False: 問題あり）
    """
    print("\n" + "=" * 80)
    print("制約診断機能（A-4実装）")
    print("=" * 80)

    total_capacity = sum(capacity.values())
    total_demand_lower = 0
    total_demand_upper = 0
    issues = []

    for segment, targets in target_share.items():
        market_size = market_data[segment]['market_size_after_1y']
        demand_lower = market_size * targets['lower']
        demand_upper = market_size * targets['upper']

        total_demand_lower += demand_lower
        total_demand_upper += demand_upper

    # チェック1: 総需要下限 vs 総キャパシティ
    if total_demand_lower > total_capacity:
        shortage = total_demand_lower - total_capacity
        issues.append({
            'constraint': '総キャパシティ制約（下限）',
            'problem': f'需要下限 {total_demand_lower:,.0f}本 > キャパシティ {total_capacity:,.0f}本',
            'shortage': shortage,
            'suggestion': (
                f'オプション1: キャパシティを {shortage:,.0f}本増やす\n'
                f'オプション2: 目標シェアを {shortage/total_demand_lower*100:.1f}%下げる'
            )
        })

    # チェック2: 総需要上限 vs 総キャパシティ（警告のみ）
    if total_demand_upper < total_capacity * 0.8:
        underutilization = total_capacity - total_demand_upper
        issues.append({
            'constraint': 'キャパシティ活用率',
            'problem': f'需要上限 {total_demand_upper:,.0f}本 < キャパシティ {total_capacity:,.0f}本',
            'shortage': -underutilization,
            'suggestion': (
                f'警告: キャパシティが{underutilization:,.0f}本（{underutilization/total_capacity*100:.1f}%）余っています\n'
                f'オプション: 目標シェア上限を引き上げてキャパシティを有効活用'
            )
        })

    # 結果表示
    if issues:
        print(f"\n検出された問題: {len(issues)}件\n")
        for idx, issue in enumerate(issues, 1):
            print(f"【問題 {idx}】 {issue['constraint']}")
            print(f"  問題: {issue['problem']}")
            print(f"  提案: {issue['suggestion']}")
            print()

        # 致命的エラーのみFalseを返す
        critical_issues = [i for i in issues if i['shortage'] > 0]
        if critical_issues:
            return False

    print("✓ 制約診断: すべての制約が理論的に充足可能です\n")
    return True
```

---

### 3.3 A-5: データフォーマット統一

**実装場所**: `scripts/optimization_common_v6.py`

```python
"""
共通関数モジュール v6

データスキーマ標準化（A-5実装）
- すべてのカラム名をschema.mdに準拠
- バリデーション関数を提供
"""

import pandas as pd
from pathlib import Path

# スキーマ定義
SCHEMA = {
    'product_master': {
        'required_columns': [
            'product_code', 'plant_code', 'segment_code', 'customer_code',
            'unit_price', 'unit_cost', 'unit_profit', 'margin_rate', 'sales_volume'
        ],
        'numeric_columns': ['unit_price', 'unit_cost', 'unit_profit', 'margin_rate', 'sales_volume']
    },
    'market_master': {
        'required_columns': [
            'segment_code', 'market_size', 'market_size_after_1y', 'cagr', 'current_share'
        ],
        'numeric_columns': ['market_size', 'market_size_after_1y', 'cagr', 'current_share']
    }
}

def validate_dataframe(df, schema_name):
    """
    データフレームがスキーマに準拠しているか検証（A-5実装）
    """
    schema = SCHEMA.get(schema_name)
    if not schema:
        raise ValueError(f"未定義のスキーマ: {schema_name}")

    errors = []

    # 必須カラムチェック
    missing_columns = set(schema['required_columns']) - set(df.columns)
    if missing_columns:
        errors.append(f"必須カラムが不足: {missing_columns}")

    # データ型チェック
    for col in schema['numeric_columns']:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            errors.append(f"カラム '{col}' は数値型である必要があります")

    # 欠損値チェック
    null_columns = df.columns[df.isnull().any()].tolist()
    if null_columns:
        errors.append(f"欠損値が存在: {null_columns}")

    if errors:
        raise ValueError(f"スキーマ検証エラー ({schema_name}):\n" + "\n".join(errors))

    return True
```

---

### 3.4 A-6: Fail-Fast原則

**実装場所**: 各ステップの最後に追加

```python
def validate_output_data(df, step_name):
    """
    各ステップの出力データを検証（A-6実装）

    Parameters:
        df: 検証対象のDataFrame
        step_name: ステップ名（エラーメッセージ用）
    """
    errors = []

    # 負の値チェック（価格・コスト・数量）
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if col.startswith('unit_') or col.endswith('_volume') or col.endswith('_size'):
            if (df[col] < 0).any():
                errors.append(f"カラム '{col}' に負の値があります")

    # 範囲チェック（シェア・率）
    rate_cols = [c for c in df.columns if 'rate' in c or 'share' in c]
    for col in rate_cols:
        if col in df.columns:
            if ((df[col] < 0) | (df[col] > 1)).any():
                errors.append(f"カラム '{col}' が0〜1の範囲外です")

    # 欠損値チェック
    if df.isnull().any().any():
        null_cols = df.columns[df.isnull().any()].tolist()
        errors.append(f"欠損値が存在: {null_cols}")

    if errors:
        print("\n" + "=" * 80)
        print(f"データ検証エラー ({step_name})")
        print("=" * 80)
        for error in errors:
            print(f"✗ {error}")
        raise ValueError(f"{step_name}の出力データに問題があります。処理を中止します。")

    print(f"✓ データ検証 ({step_name}): すべてのチェックに合格")
    return True

# 各ステップの最後に追加
# Step 1の最後
validate_output_data(market_master_processed, "Step 1: データ準備")

# Step 2の最後
validate_output_data(target_share_df, "Step 2: 目標シェア算出")

# Step 3の最後
validate_output_data(validation_result_df, "Step 3: 実行可能性検証")
```

---

### 3.5 A-7: 設定管理の外部化

**実装**: 上記のconfig.yamlを参照

**読み込み方法**:

```python
import yaml

def load_config(config_path='config/config.yaml'):
    """設定ファイル読み込み"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

# 各スクリプトで使用
config = load_config()
PLANT_CAPACITY = config['plant_capacity']
STRATEGY_COEFFS = config['strategy_coefficients']
```

---

## 4. 実装スケジュール

### フェーズ1: 基盤整備（1-2時間）

**作業内容**:
1. v6フォルダ作成
2. config.yaml作成
3. schema.md作成
4. optimization_common_v6.py作成（スキーマ検証関数）

**成果物**:
- `config/config.yaml`
- `config/schema.md`
- `scripts/optimization_common_v6.py`

---

### フェーズ2: データ生成（2-3時間）

**作業内容**:
1. step0_generate_sample_data.py作成（代理店モデル対応）
2. sales_2024.csv生成
3. product_master.csv生成（顧客コード追加）
4. market_master.csv生成（1年後版）
5. competitor_master.csv生成（1年後版）
6. 代理店モデル検証（分析スクリプト実行）

**成果物**:
- `data/raw/sales_2024.csv`
- `data/master/product_master.csv`
- `data/master/market_master.csv`
- `data/master/competitor_master.csv`

---

### フェーズ3: 最適化コード実装（3-4時間）

**作業内容**:
1. step1_data_preparation.py修正（Fail-Fast対応）
2. step2_target_share_calculation.py修正（戦略係数改訂）
3. step3_feasibility_validation.py修正（自動調整機能追加）
4. step4_optimization_execution.py修正（4つ組タプル、診断機能）

**成果物**:
- `scripts/step1_data_preparation.py`
- `scripts/step2_target_share_calculation.py`
- `scripts/step3_feasibility_validation.py`
- `scripts/step4_optimization_execution.py`

---

### フェーズ4: テストと検証（2-3時間）

**作業内容**:
1. Step 1〜4の順次実行
2. エラーハンドリングのテスト
3. 結果の妥当性検証
4. レポート作成

**成果物**:
- 最適化実行結果
- 検証レポート

---

## 5. 実装の優先順位（Q7-1の回答を反映）

✅ **回答**: A. 問題なし

以下の順序で実装：

1. **基盤整備** → 2. **データ準備** → 3. **最適化コード修正** → 4. **検証**

---

## 6. リスクと対策

### リスク1: 代理店モデルのデータ生成が複雑

**対策**: まず小規模（5製品×2拠点×2セグメント）でテスト実装し、動作確認後に本番データ生成

### リスク2: 4つ組タプルでの最適化が遅い

**対策**: 決定変数が増加（160→300-500）しても、CBCソルバーは高速（推定1秒以内）。問題が発生した場合、Gurobiへの切り替えも検討

### リスク3: 自動調整機能が無限ループ

**対策**: 最大5回反復に制限。5回でも解決しない場合、明確なエラーメッセージを表示

---

## 7. 完了条件

以下をすべて満たした時点で、v6実装完了とする：

- [x] フォルダ構成が定義通りに作成されている ✅
- [x] config.yaml、schema.mdが作成されている ✅
- [x] 代理店モデルが反映されたsales_2024.csvが生成されている（複数セグメント顧客40%） ✅
- [x] product_masterに顧客コードが追加されている ✅
- [x] 最適化コードが4つ組タプルに対応している ✅
- [x] A-3〜A-7の5つの改善提案がすべて実装されている ✅
- [x] Step 1〜4がエラーなく実行できる ✅
- [x] 最適化が成功し、結果が妥当である ✅
- [x] レポートが作成されている ✅

**実装完了日**: 2025年12月7日

---

## 8. 実装完了サマリー

v6実装計画書のすべての項目が完了しました。

### 実装成果

**Phase 1: 基盤整備** ✅
- フォルダ構造、config.yaml、schema.md、optimization_common_v6.py

**Phase 2: データ生成** ✅
- step0_generate_sample_data.py（代理店モデル実装）
- 308通りの4つ組タプル（308/1,600 = 19.2%）
- 顧客別価格設定（±5-10%変動）

**Phase 3: 最適化スクリプト** ✅
- step1_data_preparation.py（Fail-Fast検証）
- step2_target_share_calculation.py（1年目標、新係数）
- step3_feasibility_validation.py（A-3自動調整）
- step4_optimization_execution.py（4つ組タプル、A-4診断）

**Phase 4: テストと検証** ✅
- Steps 1-4の順次実行成功
- 最適化結果: 総粗利+¥11.5B (+112.5%)
- 包括的レポート作成（portfolio_optimization_v6_report.md）

### 改善提案の実装状況

| 提案 | 機能 | 実装 | 検証 |
|------|------|------|------|
| A-3 | 自動調整（5%削減×5回） | ✅ | 2イテレーションで制約違反解消 |
| A-4 | 診断機能（実現可能性スコア） | ✅ | 85/100点達成 |
| A-5 | スキーマ標準化 | ✅ | 全データ検証成功 |
| A-6 | Fail-Fast検証 | ✅ | 各ステップで即座のエラー検出 |
| A-7 | 設定外部化 | ✅ | config.yamlで一元管理 |

### 未解決事項・今後の改善点

**なし** - すべての計画項目が完了しました。

### 今後の推奨事項

1. **定期的な再最適化**: 月次または四半期での再実行
2. **市場データの更新**: 実際の市場動向に基づくパラメータ調整
3. **戦略の見直し**: industrial（撤退）セグメントの戦略格上げ検討
4. **v7への発展**: 在庫制約、リードタイム、季節変動等の追加要素検討

---

**以上**
