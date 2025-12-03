# 製品ポートフォリオ最適化フレームワーク v5 最適化仕様書

**バージョン**: 1.0
**作成日**: 2025年12月3日
**対象ディレクトリ**: `sample_data_trial_v5/analyst_claude_v5/`

---

## 1. 概要

本文書は、製品ポートフォリオ最適化フレームワーク v5 の最適化ロジックと実行手順を定義します。v5では、市場シェアベースの制約を導入し、競合分析と戦略的方向性を反映した最適化を実現します。

---

## 2. v4からの主要変更点

### 2.1 最適化アプローチの変更

| 観点 | v4 | v5 |
|------|----|----|
| **制約の基盤** | 内部制約のみ | 市場シェアベース制約 |
| **需要上限** | 現状×2.0（固定倍率） | 到達可能シェアから算出 |
| **戦略反映** | なし | 戦略区分による差別化 |
| **検証プロセス** | 事後検証のみ | 事前4ステップ検証 |
| **時間軸** | 単年 | 3年計画ベース |

### 2.2 制約条件の変更

**v4の制約**:
1. 総販売数量 = 504,000
2. 拠点キャパシティ制約
3. セグメント構成比制約（±3%）
4. 需要上限制約（現状×2.0）

**v5の制約**:
1. 総販売数量 = 504,000（維持）
2. 拠点キャパシティ制約（維持）
3. **市場シェアベース需要上限制約**（新規）
4. **戦略整合性制約**（新規）

---

## 3. 最適化モデル

### 3.1 目的関数

**粗利最大化**（v4と同じ）

```
max Σ(unit_profit[i] × x[i])
```

ここで:
- `x[i]`: 製品iの販売数量（決定変数）
- `unit_profit[i]`: 製品iの単位粗利

### 3.2 制約条件

#### 制約1: 総販売数量制約

```
Σx[i] = 504,000
```

全製品の販売数量合計が総キャパシティと一致

#### 制約2: 拠点キャパシティ制約

```
Σx[i] ≤ capacity[p]  (for each plant p)
```

- Plant A: ≤ 300,000本
- Plant B: ≤ 204,000本

#### 制約3: 市場シェアベース需要上限制約【v5新規】

```
Σx[i] ≤ demand_max[s]  (for each segment s)
```

ここで:

```
demand_max[s] = market_size_after_3y[s] × target_share_upper[s]
```

- `market_size_after_3y[s]`: セグメントsの3年後市場規模
- `target_share_upper[s]`: セグメントsの目標シェア上限（Step 3で確定）

**v4との違い**:
- v4: `demand_max = 現状販売数量 × 2.0`（市場無視）
- v5: `demand_max = 3年後市場規模 × 目標シェア`（市場・競合を考慮）

#### 制約4: 需要下限制約【v5新規・オプション】

```
Σx[i] ≥ demand_min[s]  (for each segment s)
```

ここで:

```
demand_min[s] = market_size_after_3y[s] × target_share_lower[s]
```

撤退戦略以外のセグメントで、シェアの急激な減少を防ぐ

### 3.3 非負制約

```
x[i] ≥ 0  (for all i)
```

---

## 4. 最適化実行プロセス

v5では、最適化実行前に3つのステップを踏む段階的なプロセスを採用します。

### 4.1 全体フロー

```
Step 1: データ準備
  ↓
Step 2: 目標シェア初期算出
  ↓
Step 3: 実現可能性検証
  ↓
Step 4: 最適化実行
```

### 4.2 各ステップの詳細

#### Step 1: データ準備

**目的**: 最適化に必要なマスタデータを整備

**入力**:
- `market_master.csv`: 市場マスタ
- `competitor_master.csv`: 競合マスタ

**処理**:
1. `market_size_after_3y`の算出
   ```
   market_size_after_3y = current_market_size × (1 + market_cagr)^3
   ```

2. `current_sales_volume`の算出
   ```
   current_sales_volume = market_size × current_share
   ```

3. データ整合性チェック
   - シェア合計が100%であることを確認
   - 欠損値・異常値のチェック

**出力**:
- `market_master_processed.csv`: 処理済み市場マスタ
- `competitor_master_processed.csv`: 処理済み競合マスタ
- `step1_validation_report.md`: 検証レポート

**実行コマンド**:
```bash
python scripts/step1_data_preparation.py
```

---

#### Step 2: 目標シェア初期算出

**目的**: 戦略区分から目標シェアを算出し、競合分析で妥当性を評価

**入力**:
- `market_master_processed.csv`: Step 1の出力
- `competitor_master_processed.csv`: Step 1の出力

**処理**:

1. **戦略区分から目標シェア初期値を算出**

   | 戦略区分 | 下限係数 | 上限係数 |
   |---------|---------|---------|
   | aggressive_expansion | 1.0 | 1.5 |
   | maintain | 0.9 | 1.1 |
   | reduction | 0.5 | 1.0 |
   | withdrawal | 0.0 | 0.7 |

   ```
   target_share_lower = current_share × 下限係数
   target_share_upper = current_share × 上限係数
   ```

2. **競合分析による到達可能シェアの算出**

   各競合から奪取可能なシェアを算出:

   | 競争力評価 | 奪取可能率（下限） | 奪取可能率（上限） |
   |-----------|------------------|------------------|
   | strong | 0% | 3% |
   | moderate | 2% | 5% |
   | weak | 5% | 10% |

   ```
   奪取可能シェア = min(奪取可能率, 競合の実際のシェア)
   到達可能シェア = 現状シェア + Σ奪取可能シェア
   ```

3. **警告判定**
   - 目標上限 > 到達可能上限 → エラー
   - 目標上限 > 到達可能上限 × 0.9 → 警告

**出力**:
- `target_share_initial.csv`: 目標シェア初期値
- `competitive_analysis.csv`: 競合分析結果
- `step2_presentation_report.md`: ユーザー確認用レポート

**ユーザー操作**:
- レポートを確認
- 必要に応じて`target_share_initial.csv`を修正

**実行コマンド**:
```bash
python scripts/step2_target_share_calculation.py
```

---

#### Step 3: 実現可能性検証

**目的**: 目標シェアが実現可能かを3つの観点から検証

**入力**:
- `target_share_initial.csv`: Step 2の出力（または修正版）
- `market_master_processed.csv`: Step 1の出力
- `competitive_analysis.csv`: Step 2の出力

**処理**:

1. **検証A: 生産能力検証**
   ```
   目標販売数量合計 = Σ(market_size_after_3y × target_share_upper)

   if 目標販売数量下限合計 > total_capacity:
       → エラー: 修正必須
   elif 目標販売数量上限合計 > total_capacity:
       → 警告: 上限達成困難
   else:
       → OK
   ```

2. **検証B: 競争環境検証**
   ```
   for each segment:
       if target_share_upper > achievable_share_upper:
           → エラー: 到達不可能
       elif target_share_upper > achievable_share_upper × 0.9:
           → 警告: 達成困難
       else:
           → OK
   ```

3. **検証C: 戦略整合性検証**
   ```
   if strategy_type == 'aggressive_expansion' and target_share_upper < current_share:
       → エラー: 戦略と方向性が不整合
   if strategy_type == 'withdrawal' and target_share_lower > current_share:
       → エラー: 戦略と方向性が不整合
   ...
   ```

**出力**:
- `validation_result.csv`: 検証結果詳細
- `step3_validation_report.md`: 検証レポート
- `target_share_final.csv`: 検証通過後の最終目標シェア

**エラー時の対応**:
- 具体的な修正範囲を提示
- ユーザーが`target_share_initial.csv`を修正
- Step 3を再実行

**実行コマンド**:
```bash
python scripts/step3_feasibility_validation.py
```

---

#### Step 4: 最適化実行

**目的**: 確定した目標シェアを制約として、粗利最大化の最適化を実行

**入力**:
- `target_share_final.csv`: Step 3の出力
- `sales_2024.csv`: 現状販売データ
- `market_master_processed.csv`: Step 1の出力

**処理**:

1. **需要上限・下限の算出**
   ```
   demand_max[s] = market_size_after_3y[s] × target_share_upper[s]
   demand_min[s] = market_size_after_3y[s] × target_share_lower[s]
   ```

2. **LPモデルの構築**
   - 目的関数: 粗利最大化
   - 制約条件: 前述の制約1〜4

3. **最適化実行**（PuLP使用）
   ```python
   import pulp

   prob = pulp.LpProblem("ProductPortfolioOptimization", pulp.LpMaximize)
   # 目的関数と制約条件を設定
   prob.solve()
   ```

4. **結果の整数化・検証**

**出力**:
- `sales_2024_opt_v5.csv`: 最適化結果
- `optimization_report_v5.md`: 最適化レポート
- `comparison_v4_v5.md`: v4比較レポート

**実行コマンド**:
```bash
python scripts/step4_optimization_execution.py
```

---

## 5. パラメータ設定

### 5.1 定数（optimization_common_v5.py）

```python
# 奪取可能率パラメータ
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

# 拠点キャパシティ
PLANT_CAPACITY = {'A': 300_000, 'B': 204_000}

# 総販売数量目標
TOTAL_SALES_TARGET = 504_000

# 3年計画の年数
PLANNING_YEARS = 3
```

### 5.2 パラメータ調整方法

パラメータを変更する場合:

1. `scripts/optimization_common_v5.py`を編集
2. 該当の定数を変更
3. Step 2から再実行

**例: 奪取可能率を保守的に設定**
```python
ACQUISITION_RATE = {
    'strong': {'lower': 0.00, 'upper': 0.02},  # 3% → 2%
    'moderate': {'lower': 0.01, 'upper': 0.03},  # 2-5% → 1-3%
    'weak': {'lower': 0.03, 'upper': 0.07}  # 5-10% → 3-7%
}
```

---

## 6. 実行例

### 6.1 全ステップ実行（Phase 2以降で実装予定）

```bash
# 統合実行スクリプト（Phase 3で実装）
python scripts/run_optimization_v5.py
```

### 6.2 個別ステップ実行（Phase 1で実装済み）

```bash
# Step 1: データ準備
python scripts/step1_data_preparation.py

# Step 2: 目標シェア初期算出
python scripts/step2_target_share_calculation.py

# 必要に応じてtarget_share_initial.csvを修正

# Step 3: 実現可能性検証（Phase 2で実装）
python scripts/step3_feasibility_validation.py

# エラーがあればtarget_share_initial.csvを修正してStep 3を再実行

# Step 4: 最適化実行（Phase 2で実装）
python scripts/step4_optimization_execution.py
```

---

## 7. 期待される効果

### 7.1 v4からの改善

| 観点 | v4の課題 | v5での改善 |
|------|---------|-----------|
| 市場現実性 | 内部制約のみで市場を無視 | 市場規模・競合を考慮 |
| 戦略反映 | 全セグメント同一扱い | 戦略区分で差別化 |
| 検証プロセス | 事後検証のみ | 事前段階的検証 |
| 意思決定支援 | 結果提示のみ | 対話的プロセス |

### 7.2 ビジネス価値

1. **現実的な目標設定**: 競合分析に基づく達成可能なシェアの明確化
2. **戦略との整合性**: 事業戦略と数値目標の一致
3. **リスク可視化**: 目標達成の難易度を定量評価
4. **意思決定支援**: 段階的検証による計画精緻化

---

## 8. 注意事項

### 8.1 最適化の前提

- 市場規模データの精度が結果に大きく影響
- 競合分析は定性的評価を含むため、保守的な設定を推奨
- 3年計画を前提とするが、毎年見直しが必要

### 8.2 実務適用時の考慮点

1. **段階的な目標設定**: 3年後の目標を一気に達成するのではなく、年次計画に分解
2. **リスクバッファ**: 到達可能上限の80-90%を目標とする保守的アプローチも検討
3. **継続的モニタリング**: 四半期ごとに実績と目標を比較し、必要に応じて再最適化

### 8.3 既知の制限事項

1. **競合の反応は考慮外**: 自社のシェア拡大に対する競合の対抗策は考慮していない
2. **価格変動は考慮外**: 単価・原価が固定と仮定
3. **新規参入は考慮外**: 新しい競合の参入は想定していない

---

## 9. トラブルシューティング

### 9.1 最適化が実行不可能（Infeasible）の場合

**原因**:
- 目標シェアの制約が厳しすぎる
- キャパシティ不足

**対処**:
1. Step 3の検証結果を再確認
2. `target_share_upper`を緩和
3. セグメント別の需要下限制約を削除・緩和

### 9.2 最適解が現状と大きく乖離する場合

**原因**:
- 目標シェアの上限・下限の幅が広すぎる
- 粗利差が大きいセグメントに集中

**対処**:
1. 目標シェアの範囲を狭める
2. 需要下限制約を強化
3. セグメント構成比の制約追加を検討（ただしv5の思想とトレードオフ）

### 9.3 検証エラーが解消できない場合

**原因**:
- 戦略目標とキャパシティが矛盾

**対処**:
1. 戦略区分を見直し
2. キャパシティ拡張を検討
3. 総販売数量目標を下方修正

---

## 10. Phase 2以降の実装予定

### 10.1 Phase 2（次回実装）

- Step 3: 実現可能性検証スクリプト
- Step 4: 最適化実行スクリプト

### 10.2 Phase 3（最終回実装）

- 統合実行スクリプト（`run_optimization_v5.py`）
- v4比較機能
- 詳細レポート生成機能

---

## 改訂履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2025-12-03 | 1.0 | 初版作成（Phase 1実装完了） |
