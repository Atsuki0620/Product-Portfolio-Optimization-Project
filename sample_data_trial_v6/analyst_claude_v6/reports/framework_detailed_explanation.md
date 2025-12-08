# 製品ポートフォリオ最適化フレームワーク v6 - 詳細解説レポート

**作成日**: 2025年12月7日
**対象読者**: 初見の方、フレームワークの仕組みを理解したい方

---

## このレポートについて

本レポートは、製品ポートフォリオ最適化フレームワークv6の**仕組みと計算過程**を、具体的な数値を使って詳しく解説します。結果だけでなく、**なぜその数値になったのか**を理解できるよう設計されています。

---

## 目次

1. [フレームワーク全体像](#フレームワーク全体像)
2. [前提条件と基本データ](#前提条件と基本データ)
3. [Step1: データ準備](#step1-データ準備)
4. [Step2: 目標シェア計算（詳細）](#step2-目標シェア計算詳細)
5. [Step3: 実現可能性検証（詳細）](#step3-実現可能性検証詳細)
6. [Step4: 最適化実行](#step4-最適化実行)
7. [用語集](#用語集)

---

## フレームワーク全体像

### 何を最適化するのか？

**目的**: 製品の生産・販売計画を最適化し、**総粗利を最大化**する

**決定すること**:
- どの製品を
- どの拠点で生産し
- どのセグメント（市場）の
- どの顧客に
- 何本販売するか

これを「**4つ組タプル**」と呼びます：（製品, 拠点, セグメント, 顧客）

### 制約条件

最適化には以下の制約があります：

1. **拠点別生産能力**: 各拠点には生産できる上限がある
   - 拠点A: 300,000本まで
   - 拠点B: 204,000本まで

2. **市場からの奪取可能数量**: 競合から奪える数量には限界がある

3. **総販売目標**: 会社全体で504,000本の販売を目指す

### 4つのステップ

```
【Step1: データ準備】
    ↓
  現状のデータを整理
  - 308通りの組み合わせ（製品×拠点×セグメント×顧客）
  - 現状販売数量: 482,259本
    ↓
【Step2: 目標シェア計算】
    ↓
  戦略に基づいて1年後の目標を計算
  - 積極拡大: シェアを1.0-1.2倍に
  - 維持: シェアを0.95-1.05倍に
  - 縮小: シェアを0.9-1.0倍に
  - 撤退: シェアを0.7-0.9倍に
    ↓
  ⚠️ 問題発見: oil_gasが奪取可能数量を超過
    ↓
【Step3: 実現可能性検証】
    ↓
  制約を満たすか確認し、違反があれば自動調整
  - oil_gas: 5%削減（170,652本 → 162,120本）
  - 拠点B: 5%削減（216,127本 → 201,729本）
    ↓
【Step4: 最適化実行】
    ↓
  線形計画法で総粗利を最大化
  - 結果: 総粗利 +112.5% (¥10.3B → ¥21.8B)
  - 総販売数量: 504,000本（目標達成）
```

---

## 前提条件と基本データ

### 市場セグメント（4種類）

**データソース**: `data/master/market_master.csv`

| 列名 | 説明 | 型 |
|------|------|-----|
| segment_code | セグメントコード | 文字列 |
| market_size | 現在の市場規模 | 数値（本） |
| market_size_after_1y | 1年後の市場規模 | 数値（本） |
| cagr | 年平均成長率 | 数値（小数） |
| current_share | 現状シェア | 数値（小数） |
| strategy_type | 戦略タイプ | 文字列 |

**データ内容**:

| セグメント | 市場規模 | 1年後市場規模 | CAGR | 現状シェア | 戦略 |
|-----------|---------|-------------|------|-----------|------|
| industrial | 1,008,000本 | 997,920本 | -1% | 20% | 撤退 |
| electronics | 630,000本 | 648,900本 | +3% | 20% | 維持 |
| **oil_gas** | **756,000本** | **793,800本** | **+5%** | **20%** | **積極拡大** |
| others | 126,000本 | 123,480本 | -2% | 20% | 縮小 |

**計算式**（1年後市場規模）:
```
market_size_after_1y = market_size × (1 + cagr)
```

**計算例**（oil_gas）:
```
market_size_after_1y = 756,000 × (1 + 0.05) = 793,800本
```

### 拠点別生産能力

**データソース**:
- 生産能力: `config/config.yaml` の `plant_capacity`
- 現状生産数量: `data/processed/optimization_input_data.csv` の `sales_volume` を `plant_code` でグループ化して合計

**列名**（config.yaml）:
```yaml
plant_capacity:
  A: 300000  # 拠点Aの生産能力（本）
  B: 204000  # 拠点Bの生産能力（本）
```

**計算式**（現状稼働率）:
```
現状稼働率 = (現状生産数量 / 生産能力) × 100
```

**データ内容**:

| 拠点 | 生産能力 | 現状生産数量 | 現状稼働率 |
|------|---------|------------|-----------|
| A | 300,000本 | 256,536本 | 85.5% |
| B | 204,000本 | 225,723本 | **110.6%** ⚠️ |

**計算例**（拠点B）:
```
現状稼働率 = (225,723 / 204,000) × 100 = 110.6%
```

**問題**: 拠点Bが既に生産能力を超過している（110.6%）

### 顧客分布（代理店モデル）

**データソース**: `scripts/step0_generate_sample_data.py` の顧客マッピング定義
- 顧客セグメント対応: `customer_segment_map` 変数（lines 113-124）
- 製品マスターへの反映: `data/master/product_master.csv` の `customer_code` 列

**列名**（product_master.csv内の関連列）:
```
customer_code: 顧客コード（Customer_A〜Customer_J）
segment_code: セグメントコード（顧客が取引可能なセグメント）
```

**顧客セグメントマッピング**:
| 顧客 | 取引セグメント | 分類 |
|------|---------------|------|
| Customer_A | industrial | 単一セグメント |
| Customer_B | electronics | 単一セグメント |
| Customer_C | oil_gas | 単一セグメント |
| Customer_D | others | 単一セグメント |
| Customer_E | industrial | 単一セグメント |
| Customer_F | electronics | 単一セグメント |
| Customer_G | industrial, electronics | 2セグメント |
| Customer_H | oil_gas, others | 2セグメント |
| Customer_I | electronics, oil_gas | 2セグメント |
| Customer_J | industrial, electronics, oil_gas | 3セグメント |

- 単一セグメント顧客: 6社（60%）
- 複数セグメント顧客: 4社（40%）

**計算式**（組み合わせ総数）:
```
総組み合わせ数 = Σ(各顧客の取引可能セグメント数 × 製品数 × 拠点数)
```

---

## Step1: データ準備

**データソース**:
- **入力ファイル**:
  - `data/master/product_master.csv` - 製品マスター（308行の4つ組データ）
  - `data/master/market_master.csv` - 市場マスター（4セグメント）
  - `data/master/competitor_master.csv` - 競合マスター（16行）
  - `data/master/segment_master.csv` - セグメント戦略マスター（4行）
- **出力ファイル**:
  - `data/processed/optimization_input_data.csv` - 最適化用統合データ（308行）
- **実行スクリプト**: `scripts/step1_data_preparation.py`

**主要な列名**（optimization_input_data.csv）:
```
# 基本キー（4つ組）
product_code, plant_code, segment_code, customer_code

# 価格・コスト情報
unit_price: 単価（円）
unit_cost: 単位原価（円）
unit_profit: 単位粗利（円）
margin_rate: 粗利率（小数）

# 販売情報
sales_volume: 現状販売数量（本）

# 市場情報（market_master.csvから結合）
market_size: 現在の市場規模（本）
market_size_after_1y: 1年後の市場規模（本）
cagr: 年平均成長率（小数）
current_share: 現状シェア（小数）
strategy_type: 戦略タイプ（文字列）

# 統計情報（集約計算）
total_sales_qty_segment: セグメント別総販売数量（本）
total_profit_segment: セグメント別総粗利（円）
total_sales_qty_plant: 拠点別総販売数量（本）
total_profit_plant: 拠点別総粗利（円）
```

**データ結合ロジック**:
```python
# step1_data_preparation.py (lines 28-35)
merged = product_master
    .merge(market_master, on='segment_code', how='left')
    .merge(competitor_master.groupby('segment_code').agg(...), on='segment_code', how='left')
    .merge(segment_master, on='segment_code', how='left')
```

### 4つ組タプルとは？

従来のv5では「製品×拠点×セグメント」の3つ組（160通り）でしたが、v6では**顧客レベルの価格差**を考慮するため4つ組に拡張しました。

**例**: 同じ製品P001でも、顧客によって価格が異なる

| 製品 | 拠点 | セグメント | 顧客 | 単価 | 単位粗利 |
|-----|------|-----------|------|------|---------|
| P001 | A | oil_gas | Customer_C | ¥65,595 | ¥16,871 |
| P001 | A | oil_gas | Customer_H | ¥68,280 | ¥23,665 |
| P001 | A | oil_gas | Customer_J | ¥73,843 | ¥27,870 |

→ 同じ製品・拠点・セグメントでも、顧客Jの方が高粗利

### データ統計

- **総組み合わせ数**: 308通り
  - 理論値: 20製品 × 2拠点 × 4セグメント × 10顧客 = 1,600通り
  - 実際: 308通り（19.2%）
  - **理由**: 各顧客は特定セグメントでのみ取引（代理店モデル）

---

## Step2: 目標シェア計算（詳細）

**データソース**:
- **入力ファイル**:
  - `data/processed/optimization_input_data.csv` - Step1の出力データ（308行）
  - `config/config.yaml` - 戦略係数設定（`strategy_coefficients`）
  - `data/master/competitor_master.csv` - 競合情報（16行）
- **出力ファイル**:
  - `data/processed/target_calculation_data.csv` - 目標計算済みデータ（308行）
- **実行スクリプト**: `scripts/step2_target_share_calculation.py`

**config.yamlの関連設定**:
```yaml
strategy_coefficients:
  aggressive_expansion:  # 積極拡大
    lower: 1.0
    upper: 1.2
  maintain:  # 維持
    lower: 0.95
    upper: 1.05
  reduction:  # 縮小
    lower: 0.9
    upper: 1.0
  withdrawal:  # 撤退
    lower: 0.7
    upper: 0.9

acquisition_rates:  # 競合奪取率（1年）
  strong:
    lower: 0.0
    upper: 0.01
  moderate:
    lower: 0.007
    upper: 0.017
  weak:
    lower: 0.017
    upper: 0.033
```

**追加される列名**（target_calculation_data.csv）:
```
# 目標計算関連
strategy_coefficient: 戦略係数（実際に適用された値）
target_share: 目標シェア（小数）
target_volume: 目標販売数量（本）

# 奪取可能数量計算
competitor_share_total: 競合シェア合計（小数）
acquisition_potential: 奪取可能数量（本）
max_achievable_volume: 最大可能数量（本）

# 実現可能性判定
is_achievable: 実現可能性フラグ（True/False）
excess_volume: 超過数量（本、負の場合は余裕あり）
```

**計算式**:
```python
# 1. 目標シェア計算
strategy_coefficient = random.uniform(lower, upper)  # 戦略に応じた係数
target_share = current_share × strategy_coefficient

# 2. 目標販売数量計算
target_volume = market_size_after_1y × target_share

# 3. 奪取可能数量計算（セグメント別）
for each competitor in segment:
    acquisition = market_size_after_1y × competitor_share × acquisition_rate
acquisition_potential = sum(all acquisitions)

# 4. 最大可能数量計算
current_volume = market_size_after_1y × current_share
max_achievable_volume = current_volume + acquisition_potential

# 5. 実現可能性判定
excess_volume = target_volume - max_achievable_volume
is_achievable = (excess_volume <= 0)
```

### 計算の流れ（oil_gasセグメントの例）

#### ステップ2-1: 戦略係数の適用

**入力データ**:
- 現状シェア: 0.200（20%）
- 戦略: 積極拡大
- 戦略係数範囲: 1.0〜1.2

**計算**:
1. ランダムに係数を選択（シード固定）: **1.075**
2. 目標シェア = 0.200 × 1.075 = **0.215**（21.5%）

#### ステップ2-2: 目標販売数量の計算

**計算**:
- 1年後市場規模: 793,800本
- 目標販売数量 = 793,800 × 0.215 = **170,667本**
  - ※実際は小数点処理により170,652本

#### ステップ2-3: 奪取可能数量の計算

**競合シェア**（oil_gasセグメント）:

| 競合 | シェア | 強度 | 1年奪取率 | 計算 |
|------|-------|------|---------|------|
| CompetitorA | 30.0% | strong | 0.5% | 793,800 × 0.30 × 0.005 = 1,191本 |
| CompetitorB | 25.0% | moderate | 1.2% | 793,800 × 0.25 × 0.012 = 2,381本 |
| CompetitorC | 15.0% | weak | 2.5% | 793,800 × 0.15 × 0.025 = 2,977本 |
| CompetitorD | 10.0% | weak | 2.5% | 793,800 × 0.10 × 0.025 = 1,984本 |

**合計奪取可能数量** = 1,191 + 2,381 + 2,977 + 1,984 = **8,533本**

#### ステップ2-4: 最大可能数量の計算

**計算**:
1. 現状数量 = 793,800 × 0.200 = **158,760本**
2. 最大可能数量 = 現状数量 + 奪取可能数量
   = 158,760 + 8,533 = **167,293本**

#### ステップ2-5: 実現可能性チェック

**判定**:
- 目標販売数量: **170,652本**
- 最大可能数量: **167,293本**
- **超過量**: 170,652 - 167,293 = **3,359本** ❌

→ **「要調整」と判定される理由はここ！**

### 全セグメントの計算結果まとめ

| セグメント | 現状数量 | 目標数量 | 奪取可能 | 最大可能 | 超過量 | 判定 |
|-----------|---------|---------|---------|---------|--------|------|
| industrial | 201,552本 | 154,659本 | 8,260本 | 209,812本 | - | ✅ 可能 |
| electronics | 129,780本 | 128,152本 | 6,100本 | 135,880本 | - | ✅ 可能 |
| **oil_gas** | **158,760本** | **170,652本** | **8,533本** | **167,293本** | **+3,359本** | ❌ **要調整** |
| others | 24,696本 | 23,151本 | 1,284本 | 25,980本 | - | ✅ 可能 |

**oil_gasだけが要調整になる理由**:
- 積極拡大戦略（係数1.075）により目標が高すぎる
- 競合から奪える数量（8,533本）では足りない
- 3,359本不足している

---

## Step3: 実現可能性検証（詳細）

**データソース**:
- **入力ファイル**:
  - `data/processed/target_calculation_data.csv` - Step2の出力データ（308行）
  - `config/config.yaml` - 自動調整設定（`auto_adjustment`）と生産能力（`plant_capacity`）
- **出力ファイル**:
  - `data/processed/feasibility_validated_data.csv` - 検証済みデータ（308行）
- **実行スクリプト**: `scripts/step3_feasibility_validation.py`

**config.yamlの関連設定**:
```yaml
auto_adjustment:
  max_iterations: 5  # 最大調整回数
  reduction_rate: 0.05  # 削減率（5%）

plant_capacity:
  A: 300000  # 拠点A生産能力（本）
  B: 204000  # 拠点B生産能力（本）
```

**追加される列名**（feasibility_validated_data.csv）:
```
# 調整履歴
adjustment_iterations: 調整回数（整数）
adjusted_target_volume: 調整後目標数量（本）
adjustment_reason: 調整理由（文字列）

# 検証結果
segment_feasibility: セグメント別実現可能性（True/False）
plant_feasibility: 拠点別実現可能性（True/False）
final_feasibility_score: 最終実現可能性スコア（0-100点）
```

**調整アルゴリズム**:
```python
# step3_feasibility_validation.py
for iteration in range(1, max_iterations + 1):
    # セグメント別制約チェック
    for segment in segments:
        if target_volume > max_achievable_volume:
            # 5%削減
            adjusted_target = target_volume × (1 - reduction_rate)

    # 拠点別制約チェック
    for plant in plants:
        plant_total = sum(targets for plant)
        if plant_total > plant_capacity:
            # 該当拠点の製品を5%削減
            adjusted_target = target_volume × (1 - reduction_rate)

    # 変更がなければ終了
    if no_changes:
        break
```

**実現可能性スコア計算式**:
```python
# step3_feasibility_validation.py (lines 180-185)
score = 100
if segment_violations > 0:
    score -= (segment_violations / total_segments) × 30
if plant_violations > 0:
    score -= (plant_violations / total_plants) × 30
if total_target < total_goal:
    score -= abs(shortage_rate) × 40
```

### 初回診断で検出された3つの問題

#### 問題1: oil_gasセグメントの超過（3,359本）

**詳細**:
- 目標数量: 170,652本
- 最大可能数量: 167,293本
- **超過**: 3,359本

**原因**: Step2で説明した通り、奪取可能数量の限界

#### 問題2: 拠点Bの生産能力超過（12,127本）

**計算の流れ**:

1. **Step2終了時点の拠点別目標数量**:

各セグメントの目標を拠点別に配分すると：

| セグメント | 拠点A目標 | 拠点B目標 | 合計目標 |
|-----------|----------|----------|---------|
| industrial | 82,385本 | 72,274本 | 154,659本 |
| electronics | 68,303本 | 59,849本 | 128,152本 |
| oil_gas | 90,940本 | 79,712本 | 170,652本 |
| others | 12,339本 | 10,812本 | 23,151本 |
| **合計** | **253,967本** | **222,647本** | **476,614本** |

※実際のコードでは現状比で配分するため、上記は概算

2. **拠点Bの問題**:
- 拠点B生産能力: **204,000本**
- 拠点B目標数量: **216,127本**（実際の計算値）
- **超過**: 216,127 - 204,000 = **12,127本** ❌

**なぜ超過？**:
- oil_gasセグメントが積極拡大（+48,111本）
- これを拠点A/Bで分担するが、拠点Bの現状稼働率が既に高い（110.6%）
- 目標がさらに増えて能力超過

#### 問題3: 総販売目標不足（27,385本）

**計算**:
- 総販売目標: 504,000本
- Step2の目標合計: 476,615本
- **不足**: 504,000 - 476,615 = **27,385本**（5.4%）

**原因**:
- withdrawal（撤退）戦略: industrial が-22.5%（係数0.775）
- reduction（縮小）戦略: others が-80.7%（係数0.937）
- これらの縮小が、oil_gas/electronicsの拡大を上回る

### 自動調整機能（A-3）の動作

#### イテレーション1: 5%削減

**調整対象**:
1. **oil_gasセグメント**（奪取可能数量超過）
   - 調整前: 170,652本
   - 調整後: 170,652 × 0.95 = **162,120本**
   - 削減: 8,532本

2. **拠点B**（生産能力超過）
   - 調整前: 216,127本
   - 調整後: 216,127 × 0.95 = **205,321本**
   - 削減: 10,806本

**調整後の状態**:

| 制約 | 調整前 | 調整後 | 状態 |
|------|-------|-------|------|
| oil_gas奪取可能数量 | 170,652本 > 167,293本 | 162,120本 < 167,293本 | ✅ 解決 |
| 拠点B生産能力 | 216,127本 > 204,000本 | 205,321本 > 204,000本 | ⚠️ まだ超過 |

**拠点B再計算**（実際のコードの動作）:

拠点Bの製品を5%削減すると、その分が全体から減るため：
- 調整後の拠点B: 約201,729本（実測値）
- 拠点B生産能力: 204,000本
- **201,729本 < 204,000本** → ✅ **解決**

#### イテレーション2〜5: 変化なし

**理由**:
- セグメント別と拠点別の制約は解決済み
- 残るのは「総販売目標不足」のみ
- これは削減では解決できない（削減すると逆効果）
- → 調整量 = 0本

### 最終状態

| 制約 | 状態 | 詳細 |
|------|------|------|
| セグメント別奪取可能数量 | ✅ すべて可能 | 4セグメント全て範囲内 |
| 拠点別生産能力 | ✅ すべて可能 | 拠点A: 85.2%, 拠点B: 98.9% |
| 総販売目標 | ⚠️ 9.2%不足 | 457,465本 vs 504,000本 |

**総販売目標不足の理由**:
- withdrawal/reduction戦略による構造的な縮小
- 削減では解決不可（削減すると目標からさらに遠ざかる）
- → **Step4の最適化で解決**（後述）

---

## Step4: 最適化実行

**データソース**:
- **入力ファイル**:
  - `data/processed/feasibility_validated_data.csv` - Step3の検証済みデータ（308行）
  - `config/config.yaml` - 診断設定（`diagnostics`）と総販売目標（`total_sales_target`）
- **出力ファイル**:
  - `data/processed/optimization_result.csv` - 最適化結果（308行）
- **実行スクリプト**: `scripts/step4_optimization_execution.py`

**config.yamlの関連設定**:
```yaml
total_sales_target: 504000  # 総販売目標（本）

diagnostics:
  enabled: true
  include_feasibility_score: true
  score_threshold: 70  # スコアが70点未満で警告
```

**optimization_result.csvの列名**:
```
# 基本キー（4つ組）
product_code, plant_code, segment_code, customer_code

# 最適化結果
optimized_volume: 最適化後販売数量（本）
optimized_profit: 最適化後粗利（円）

# 元データからの変化
volume_change: 数量変化（本）
volume_change_rate: 数量変化率（小数）
profit_change: 粗利変化（円）
profit_change_rate: 粗利変化率（小数）

# その他メタデータ
solver_status: ソルバーステータス（Optimal/Infeasible等）
solve_time: 求解時間（秒）
```

**最適化モデル定義**:
```python
# step4_optimization_execution.py (lines 45-85)

# 決定変数: x_i = 各4つ組の販売数量（308個）
x = {key: LpVariable(f"x_{key}", lowBound=0) for key in all_combinations}

# 目的関数: 総粗利を最大化
problem += lpSum([x[key] × unit_profit[key] for key in all_combinations])

# 制約1: 拠点別生産能力制約（2個）
for plant in ['A', 'B']:
    problem += (
        lpSum([x[key] for key in combinations where plant_code == plant])
        <= plant_capacity[plant]
    )

# 制約2: セグメント別目標制約（8個 = 4セグメント × 上下限）
for segment in segments:
    lower_bound = target_volume[segment] × 0.9
    upper_bound = max_achievable_volume[segment]
    problem += (
        lower_bound
        <= lpSum([x[key] for key in combinations where segment_code == segment])
        <= upper_bound
    )

# 制約3: 総販売目標制約（2個）
total_target = config['total_sales_target']
problem += lpSum([x[key] for key in all_combinations]) >= total_target × 0.9
problem += lpSum([x[key] for key in all_combinations]) <= total_target × 1.1
```

**診断機能（A-4）**:
```python
# step4_optimization_execution.py (lines 110-130)

# 事前診断スコア計算
diagnostic_result = {
    'feasibility_score': calculate_feasibility_score(),
    'constraint_violations': check_all_constraints(),
    'risk_factors': identify_risk_factors(),
    'recommendations': generate_recommendations()
}

# スコアが閾値未満の場合、警告を表示
if diagnostic_result['feasibility_score'] < score_threshold:
    print(f"警告: 実現可能性スコア {score}点 - 最適化が失敗する可能性")
```

### 最適化モデルの構造

#### 決定変数（308個）

各4つ組タプル（製品, 拠点, セグメント, 顧客）の販売数量 `x_i`

**例**:
- `x_P011_A_oil_gas_Customer_H` = P011を拠点Aで生産し、oil_gasセグメントのCustomer_Hに販売する数量

#### 目的関数（最大化）

```
総粗利 = Σ(販売数量 × 単位粗利)
      = x_P011_A_oil_gas_Customer_H × 56,701円 + ...（308項）
```

#### 制約条件（12個）

**1. 拠点別生産能力制約（2個）**

```
拠点Aの総生産数量 ≤ 300,000本
拠点Bの総生産数量 ≤ 204,000本
```

**2. セグメント別目標数量制約（8個 = 4セグメント × 2）**

各セグメントについて：
```
目標の90% ≤ セグメント総販売数量 ≤ 最大可能数量
```

**例**（oil_gas）:
```
162,120 × 0.9 = 145,908本 ≤ oil_gas総販売数量 ≤ 167,293本
```

**3. 総販売目標制約（2個）**

```
504,000 × 0.9 = 453,600本 ≤ 総販売数量 ≤ 504,000 × 1.1 = 554,400本
```

### 最適化の実行結果

#### ソルバーの動作

- **ソルバー**: PuLP CBC（線形計画法）
- **実行時間**: 0.012秒
- **ステータス**: Optimal（最適解発見）

#### 最適解

**総販売数量**: 504,000本（上限制約ぎりぎり）
**総粗利**: ¥21,785,572,115

**拠点別配分**:
| 拠点 | 最適化数量 | 生産能力 | 稼働率 |
|------|-----------|---------|--------|
| A | 300,000本 | 300,000本 | **100.0%** |
| B | 204,000本 | 204,000本 | **100.0%** |

→ **両拠点ともフル稼働**

**セグメント別配分**:
| セグメント | 最適化数量 | 目標数量 | 達成率 |
|-----------|-----------|---------|--------|
| oil_gas | 167,293本 | 162,120本 | 103.2% |
| electronics | 135,880本 | 128,152本 | 106.0% |
| industrial | 179,991本 | 154,659本 | 116.4% |
| others | 20,836本 | 23,151本 | 90.0% |

**合計**: 504,000本 ✅

#### なぜ総販売目標を達成できたか？

Step3で不足していた46,535本を、最適化が以下で解決：

1. **拠点Aの余裕を活用**:
   - Step3時点: 255,736本（稼働率85.2%）
   - 最適化後: 300,000本（稼働率100%）
   - **+44,264本**

2. **高粗利セグメントに集中**:
   - industrial（撤退戦略）でも高粗利製品を発見
   - P016×industrial×Customer_A: 粗利+¥5.4B
   - 戦略を無視して粗利最大化

3. **others（縮小）を最小化**:
   - 目標23,151本に対し20,836本（90%）
   - 低粗利セグメントを削減して余力確保

### 重要な発見

**industrial（撤退戦略）の矛盾**:
- 戦略: 撤退（シェア-22.5%）
- 最適化結果: +52.0%増加、粗利+¥3.9B
- **原因**: P016×顧客Aが超高粗利（単位粗利¥29,854）
- **推奨**: 戦略を「維持」または「縮小」に変更

---

## 最適化の核心メカニズム

### なぜ粗利が112.5%も改善したのか？

**答え**: 最適化が以下を同時に実現したから

1. **両拠点をフル稼働**（504,000本生産）
   - 現状: 482,259本（稼働率95.7%）
   - 最適化: 504,000本（稼働率100%）
   - **+21,741本**

2. **高粗利製品に集中**
   - P011（単位粗利¥56,701）: 1,980本 → 164,120本
   - P017（単位粗利¥46,730）: 790本 → 135,880本
   - P016（単位粗利¥29,854）: 1,279本 → 179,991本

3. **低粗利製品を削減**
   - 粗利率<10%の製品を0本に設定
   - 29件の低粗利組み合わせを削減

### 単純化した例

**現状の配分**（仮想例）:
```
低粗利製品: 100本 × ¥1,000 = ¥100,000
高粗利製品: 100本 × ¥50,000 = ¥5,000,000
合計: 200本、¥5,100,000
```

**最適化後**:
```
低粗利製品: 0本 × ¥1,000 = ¥0
高粗利製品: 200本 × ¥50,000 = ¥10,000,000
合計: 200本、¥10,000,000 (+96%改善)
```

→ 同じ生産量でも、配分を変えるだけで粗利が倍増

---

## 用語集

### 4つ組タプル
（製品, 拠点, セグメント, 顧客）の組み合わせ。v6の決定変数の単位。

### CAGR（年平均成長率）
Compound Annual Growth Rateの略。市場が年間何%成長するかを示す。

### 奪取可能数量
競合から奪い取れる最大の販売数量。競合の強度によって異なる。

### 実現可能性スコア
最適化実行前に、制約を満たせる可能性を0-100点で評価したもの。

### Fail-Fast検証
エラーを早期に検出し、即座に処理を停止する原則。

### 線形計画法
制約条件の下で目的関数を最大化（または最小化）する数学的手法。

---

## まとめ

### Step2で分かったこと

- oil_gasは積極拡大戦略により目標が高すぎた
- 奪取可能数量（8,533本）では目標（170,652本）に3,359本不足
- 拠点Bは既に能力超過で、さらに12,127本の超過

### Step3で解決したこと

- 自動調整（5%削減）でoil_gasと拠点Bの問題を解決
- 総販売目標不足は残存（削減では解決不可）

### Step4で達成したこと

- 両拠点フル稼働で総販売目標504,000本を達成
- 高粗利製品に集中配分で粗利+112.5%
- industrial（撤退）戦略の矛盾を発見

### 推奨事項

1. **industrial戦略の見直し**: 撤退→維持/縮小へ
2. **oil_gas強化**: 生産能力増強の検討
3. **低粗利製品の整理**: 価格改定または製造中止
4. **拠点Aの活用**: 余裕があるので増産可能

---

**このレポートで疑問が解決しましたか？**

さらに詳しい説明が必要な箇所があれば、お気軽にお尋ねください。
