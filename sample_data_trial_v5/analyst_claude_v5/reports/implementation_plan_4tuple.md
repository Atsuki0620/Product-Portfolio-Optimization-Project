# 4つ組タプル実装計画書

**作成日**: 2025年12月7日

---

## Q4の補足説明

### 質問4の意図

**質問**: 最適化で何を決定したいのか？

最適化モデルでは、「何を決定変数とするか」によって、モデルの複雑さと表現力が変わります。この質問は、以下の2つのアプローチのどちらを採用するかを確認するものでした。

#### アプローチA: 顧客レベルで直接販売数量を決定

**決定変数**: `x[製品, 拠点, セグメント, 顧客] = 販売数量`

**例**:
```
x[P001, A, industrial, Customer_A] = 1000本
x[P001, A, industrial, Customer_D] = 2000本
x[P001, A, electronics, Customer_B] = 1500本
```

**特徴**:
- 各顧客に対して、個別に販売数量を決定
- 顧客別の価格・コストを直接反映できる
- モデルはシンプル（1段階の最適化）

#### アプローチB: 生産数量と顧客配分を分ける2段階最適化

**決定変数1**: `y[製品, 拠点, セグメント] = 生産数量`
**決定変数2**: `z[製品, 拠点, セグメント, 顧客] = 配分数量`

**制約**: `Σ z[製品, 拠点, セグメント, 顧客] = y[製品, 拠点, セグメント]`

**例**:
```
# まず生産数量を決定
y[P001, A, industrial] = 3000本

# 次に顧客配分を決定
z[P001, A, industrial, Customer_A] = 1000本
z[P001, A, industrial, Customer_D] = 2000本
合計 = 3000本
```

**特徴**:
- 生産計画と販売配分を分離
- より複雑だが、生産制約と販売制約を分けて考えられる
- 2段階の最適化が必要

### ご回答に基づく判断

ご回答内容から判断すると：
- 顧客別に異なる価格で販売（個別価格交渉）
- 顧客レベルでの販売数量を直接最適化したい

→ **アプローチA（顧客レベルで直接販売数量を決定）が適切**と判断します。

---

## 実装計画

ご回答に基づき、以下の実装計画を提案します。

### 回答のまとめ

| 質問 | 回答 | 実装への影響 |
|------|------|------------|
| Q1-1 | はい | 同じ製品×拠点×セグメントで複数顧客に異なる価格 |
| Q1-2 | B（個別価格交渉） | 顧客×製品ごとに価格を個別設定 |
| Q2-1 | いいえ | 全組み合わせは不要 |
| Q2-2 | 代理店モデル反映 | 20-40%の顧客が2-3セグメント |
| Q3 | C（将来の拡張性） | 顧客・製品追加が容易な構造 |
| Q4 | - | アプローチA（顧客レベルで直接決定） |

### 採用する実装アプローチ

**選択肢1の改良版: 代理店モデルに基づくproduct_master拡張**

**理由**:
1. 将来の拡張性を重視（Q3: C）
2. 個別価格交渉に対応（Q1-2: B）
3. 代理店モデルを反映（Q2-2）
4. データ構造がシンプルで理解しやすい

**データ量**:
- 全組み合わせ（1,600行）ではなく、**実際の取引組み合わせのみ**（推定300-500行）

---

## 実装ステップ

### ステップ1: サンプルデータの修正（代理店モデルの反映）

#### 1-1. 顧客セグメント分布の再設計

**現状**: 全10顧客が4セグメント全てで取引（100%）

**修正後**: 代理店モデルを反映

| 顧客タイプ | セグメント数 | 顧客数 | 割合 | 具体例 |
|----------|------------|--------|------|--------|
| 単一セグメント顧客 | 1 | 6 | 60% | Customer_A: industrial のみ |
| 代理店（小規模） | 2 | 3 | 30% | Customer_G: industrial + electronics |
| 代理店（大規模） | 3 | 1 | 10% | Customer_J: industrial + electronics + oil_gas |

**顧客セグメントマッピング案**:

```python
customer_segment_mapping = {
    # 単一セグメント顧客（60%）
    'Customer_A': ['industrial'],
    'Customer_B': ['electronics'],
    'Customer_C': ['oil_gas'],
    'Customer_D': ['others'],
    'Customer_E': ['industrial'],
    'Customer_F': ['electronics'],

    # 代理店（2セグメント、30%）
    'Customer_G': ['industrial', 'electronics'],
    'Customer_H': ['oil_gas', 'others'],
    'Customer_I': ['electronics', 'oil_gas'],

    # 代理店（3セグメント、10%）
    'Customer_J': ['industrial', 'electronics', 'oil_gas'],
}
```

**結果**:
- 単一セグメント顧客: 6 / 10 = 60%
- 複数セグメント顧客: 4 / 10 = 40%（うち3セグメント1社、2セグメント3社）

#### 1-2. sales_2024.csvの再生成

**方針**:
1. 上記の顧客セグメントマッピングに基づき、取引を再割り当て
2. 顧客×製品ごとに個別価格を設定
3. 同じ製品×拠点×セグメントでも、顧客によって価格が異なるケースを作成

**データ構造（例）**:

```csv
year,product_code,product_name,cost_band,plant,segment,customer_name,sales_qty,unit_price,unit_cost,margin_rate
2024,P001,Product_001,low,A,industrial,Customer_A,2000,60000,53000,0.117
2024,P001,Product_001,low,A,industrial,Customer_E,1500,61000,53500,0.123
2024,P001,Product_001,low,A,industrial,Customer_G,1000,59000,52800,0.105
2024,P001,Product_001,low,A,electronics,Customer_B,3000,68000,53000,0.221
2024,P001,Product_001,low,A,electronics,Customer_F,2000,67500,53200,0.212
2024,P001,Product_001,low,A,electronics,Customer_G,1500,67000,53100,0.208
```

**ポイント**:
- P001_A_industrialを3顧客（A, E, G）に販売（価格はそれぞれ異なる）
- P001_A_electronicsを3顧客（B, F, G）に販売

**総パターン数の見積もり**:
- 単一セグメント顧客: 6顧客 × 20製品 × 2拠点 × 1セグメント = 240パターン
- 2セグメント顧客: 3顧客 × 20製品 × 2拠点 × 2セグメント = 240パターン
- 3セグメント顧客: 1顧客 × 20製品 × 2拠点 × 3セグメント = 120パターン
- **合計: 約600パターン**（ただし、実際には全製品を全顧客が購入するわけではないので、300-400パターン程度）

---

### ステップ2: product_master.csvの拡張

#### 2-1. 顧客コードの追加

**現在の構造**:
```csv
product_code,product_name,cost_band,plant_code,segment_code,unit_cost,unit_price,unit_profit,margin_rate,sales_qty
```

**新しい構造**:
```csv
product_code,product_name,cost_band,plant_code,segment_code,customer_code,unit_cost,unit_price,unit_profit,margin_rate,sales_qty
```

#### 2-2. データの生成方法

**方法1: sales_2024.csvから直接生成**

修正後のsales_2024.csvをそのまま利用：

```python
product_master = sales_df[[
    'product_code', 'product_name', 'cost_band', 'plant', 'segment',
    'customer_name', 'unit_cost', 'unit_price', 'margin_rate', 'sales_qty'
]].copy()
product_master.columns = [
    'product_code', 'product_name', 'cost_band', 'plant_code', 'segment_code',
    'customer_code', 'unit_cost', 'unit_price', 'margin_rate', 'sales_qty'
]
product_master['unit_profit'] = product_master['unit_price'] - product_master['unit_cost']
```

**メリット**:
- シンプル
- 実績データと完全に一致

**デメリット**:
- 将来の新規組み合わせを追加しにくい

**方法2: 顧客別価格ルールを定義して生成**

基準価格に、顧客別の価格係数を適用：

```python
# 基準価格（製品×拠点×セグメント）
base_prices = {...}

# 顧客別価格係数
customer_price_multiplier = {
    'Customer_A': 0.98,   # 2%割引
    'Customer_B': 1.00,   # 標準価格
    'Customer_C': 0.95,   # 5%割引
    ...
}

# 顧客別価格生成
for (product, plant, segment) in base_prices:
    for customer in customer_segment_mapping:
        if segment in customer_segment_mapping[customer]:
            unit_price = base_prices[(product, plant, segment)] * customer_price_multiplier[customer]
            ...
```

**メリット**:
- 将来の拡張が容易
- 価格ルールが明示的

**デメリット**:
- 価格係数の設定が必要

**推奨**: まず**方法1**でsales_2024.csvから生成し、後で必要に応じて**方法2**に拡張

---

### ステップ3: 最適化コードの修正

#### 3-1. 決定変数定義の変更

**現在（step4_optimization_execution.py:131）**:

```python
for idx, row in self.product_master.iterrows():
    product_code = row['product_code']
    plant_code = row['plant_code']
    segment_code = row['segment_code']
    var_key = (product_code, plant_code, segment_code)  # 3つ組
    self.x[var_key] = pulp.LpVariable(
        f"x_{product_code}_{plant_code}_{segment_code}",
        lowBound=0,
        cat='Continuous'
    )
```

**修正後**:

```python
for idx, row in self.product_master.iterrows():
    product_code = row['product_code']
    plant_code = row['plant_code']
    segment_code = row['segment_code']
    customer_code = row['customer_code']  # 追加
    var_key = (product_code, plant_code, segment_code, customer_code)  # 4つ組
    self.x[var_key] = pulp.LpVariable(
        f"x_{product_code}_{plant_code}_{segment_code}_{customer_code}",
        lowBound=0,
        cat='Continuous'
    )
```

#### 3-2. 目的関数の変更

**現在**:

```python
objective = pulp.lpSum([
    row['unit_profit'] * self.x[(row['product_code'], row['plant_code'], row['segment_code'])]
    for idx, row in self.product_master.iterrows()
])
```

**修正後**:

```python
objective = pulp.lpSum([
    row['unit_profit'] * self.x[(row['product_code'], row['plant_code'], row['segment_code'], row['customer_code'])]
    for idx, row in self.product_master.iterrows()
])
```

#### 3-3. 制約条件の変更

**拠点キャパシティ制約（変更なし）**:

```python
for plant, capacity in PLANT_CAPACITY.items():
    plant_vars = [
        self.x[(row['product_code'], row['plant_code'], row['segment_code'], row['customer_code'])]
        for idx, row in self.product_master.iterrows()
        if row['plant_code'] == plant
    ]
    self.prob += (pulp.lpSum(plant_vars) <= capacity, f"PlantCapacity_{plant}")
```

**セグメント需要制約（顧客集計が必要）**:

```python
for segment, limits in self.demand_limits.items():
    segment_vars = [
        self.x[(row['product_code'], row['plant_code'], row['segment_code'], row['customer_code'])]
        for idx, row in self.product_master.iterrows()
        if row['segment_code'] == segment
    ]
    # 上限制約
    self.prob += (pulp.lpSum(segment_vars) <= limits['max'], f"DemandMax_{segment}")

    # 下限制約（撤退戦略以外）
    if limits['strategy_type'] != 'withdrawal':
        self.prob += (pulp.lpSum(segment_vars) >= limits['min'], f"DemandMin_{segment}")
```

**顧客別制約（必要に応じて追加）**:

```python
# 例: 特定顧客への販売数量上限
MAX_SALES_PER_CUSTOMER = {
    'Customer_A': 50000,
    'Customer_B': 40000,
    ...
}

for customer, max_qty in MAX_SALES_PER_CUSTOMER.items():
    customer_vars = [
        self.x[(row['product_code'], row['plant_code'], row['segment_code'], row['customer_code'])]
        for idx, row in self.product_master.iterrows()
        if row['customer_code'] == customer
    ]
    self.prob += (pulp.lpSum(customer_vars) <= max_qty, f"CustomerMax_{customer}")
```

---

## 実装スケジュール

### フェーズ1: サンプルデータ修正（優先度: 最高）

**作業内容**:
1. 顧客セグメントマッピング定義
2. sales_2024.csv再生成スクリプト作成
3. 代理店モデルの検証（分析1の再実行）

**成果物**:
- `scripts/regenerate_sales_data_with_distributor_model.py`
- 修正後の`data/raw/sales_2024.csv`

**所要時間**: 2-3時間

### フェーズ2: product_master拡張（優先度: 高）

**作業内容**:
1. product_master生成スクリプト修正
2. 顧客コード追加
3. データ整合性チェック

**成果物**:
- 修正後の`data/master/product_master.csv`
- `scripts/generate_product_master_v6.py`

**所要時間**: 1-2時間

### フェーズ3: 最適化コード修正（優先度: 高）

**作業内容**:
1. 決定変数定義を4つ組に変更
2. 目的関数・制約条件の修正
3. 結果出力フォーマット調整

**成果物**:
- 修正後の`scripts/step4_optimization_execution.py`
- テスト実行結果

**所要時間**: 2-3時間

### フェーズ4: 検証とドキュメント更新（優先度: 中）

**作業内容**:
1. 最適化の実行と結果検証
2. レポート更新
3. 詳細分析の再実行

**成果物**:
- 更新されたレポート
- 検証結果ドキュメント

**所要時間**: 1-2時間

**総所要時間**: 6-10時間

---

## リスクと対策

### リスク1: データ量増加によるパフォーマンス低下

**リスク内容**:
- product_masterが160行 → 300-600行に増加
- 最適化の計算時間が増える可能性

**対策**:
- CBCソルバーは数千変数まで高速に処理可能（現在0.02秒）
- 600変数程度なら問題なし（推定1秒以内）
- 必要に応じて、より高速なソルバー（Gurobi, CPLEX）への切り替えも可能

### リスク2: 代理店モデルの妥当性

**リスク内容**:
- 提案した顧客セグメント分布が実態と異なる可能性

**対策**:
- まず提案した分布でサンプルデータを生成
- 分析結果を確認して、必要に応じて調整
- 顧客セグメントマッピングは設定ファイル化して、容易に変更可能に

### リスク3: 価格設定の複雑さ

**リスク内容**:
- 顧客×製品ごとの個別価格設定が複雑

**対策**:
- フェーズ1では、現在のsales_2024.csvの価格に小幅な変動を加える
- 将来的に、より詳細な価格ルールを追加可能な構造にする

---

## 次のステップ

以下の順序で実装を進めます：

1. **ステップ1-1: 顧客セグメントマッピング定義とsales_2024.csv再生成スクリプト作成**
   - 提案した顧客セグメント分布で良いか確認
   - スクリプト作成と実行

2. **ステップ1-2: 代理店モデルの検証**
   - 詳細分析スクリプトを再実行
   - 20-40%の範囲内になっているか確認

3. **ステップ2: product_master.csv拡張**
   - 顧客コード追加
   - 整合性チェック

4. **ステップ3: 最適化コード修正**
   - 決定変数を4つ組に変更
   - テスト実行

ステップ1から開始してよろしいでしょうか？

---

**以上**
