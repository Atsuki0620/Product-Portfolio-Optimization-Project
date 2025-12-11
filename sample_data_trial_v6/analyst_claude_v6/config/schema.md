# データスキーマ定義書 v6

**作成日**: 2025年12月7日
**バージョン**: 6.0
**改善提案**: A-5（データフォーマットの不統一対策）

---

## 目的

本ドキュメントは、製品ポートフォリオ最適化フレームワークv6で使用されるすべてのデータファイルのカラム名規約を定義します。すべてのCSVファイルおよびデータフレームは、この規約に従う必要があります。

---

## 共通カラム名規約

### 1. 基本情報

| カラム名 | 型 | 説明 | 例 |
|---------|---|------|-----|
| `product_code` | 文字列 | 製品コード | "P001", "P002" |
| `product_name` | 文字列 | 製品名 | "Product_001" |
| `plant_code` | 文字列 | 拠点コード | "A", "B" |
| `segment_code` | 文字列 | セグメントコード | "industrial", "electronics", "oil_gas", "others" |
| `customer_code` | 文字列 | 顧客コード（v6で追加） | "Customer_A", "Customer_B" |
| `year` | 整数 | 年度 | 2024, 2025 |

**注意事項**:
- v5では`plant`, `segment`, `customer_name`が使用されていましたが、v6では統一のため`plant_code`, `segment_code`, `customer_code`に変更
- ただし、データ生成時の互換性のため、一部スクリプトでは`plant`, `segment`も許容

### 2. 数量・金額

| カラム名 | 型 | 単位 | 説明 | 例 |
|---------|---|------|------|-----|
| `sales_volume` | 浮動小数点 | 本 | 販売数量（v5: `sales_qty`から統一） | 1000.0, 2500.5 |
| `unit_price` | 浮動小数点 | 円 | 単価（販売価格） | 50000.0, 75000.0 |
| `unit_cost` | 浮動小数点 | 円 | 単位コスト（製造原価） | 40000.0, 60000.0 |
| `unit_profit` | 浮動小数点 | 円 | 単位粗利（unit_price - unit_cost） | 10000.0, 15000.0 |
| `total_profit` | 浮動小数点 | 円 | 総粗利（unit_profit × sales_volume） | 10000000.0 |
| `margin_rate` | 浮動小数点 | 比率 | 粗利率（unit_profit / unit_price）、0.0〜1.0 | 0.2, 0.3 |

**計算式**:
- `unit_profit = unit_price - unit_cost`
- `total_profit = unit_profit × sales_volume`
- `margin_rate = unit_profit / unit_price`

**注意事項**:
- v6では`sales_qty`を`sales_volume`に統一（Q6-3の回答）
- 金額の単位はすべて「円」
- 数量の単位はすべて「本」

### 3. 市場関連

| カラム名 | 型 | 単位 | 説明 | 例 |
|---------|---|------|------|-----|
| `market_size` | 浮動小数点 | 本 | 現在の市場規模 | 1000000.0 |
| `market_size_after_1y` | 浮動小数点 | 本 | 1年後の市場規模（v5: `market_size_after_3y`から変更） | 1050000.0 |
| `market_share` | 浮動小数点 | 比率 | 市場シェア、0.0〜1.0 | 0.2, 0.15 |
| `current_share` | 浮動小数点 | 比率 | 現状シェア、0.0〜1.0 | 0.2 |
| `target_share_lower` | 浮動小数点 | 比率 | 目標シェア下限、0.0〜1.0 | 0.18 |
| `target_share_upper` | 浮動小数点 | 比率 | 目標シェア上限、0.0〜1.0 | 0.22 |
| `cagr` | 浮動小数点 | 比率 | 年平均成長率、-1.0〜1.0 | 0.05, -0.01 |

**注意事項**:
- v6では1年後の目標に変更したため、`market_size_after_3y` → `market_size_after_1y`
- シェアや率は必ず0.0〜1.0の範囲（パーセンテージではなく比率）

### 4. 戦略関連

| カラム名 | 型 | 説明 | 例 |
|---------|---|------|-----|
| `strategy_type` | 文字列 | 戦略区分 | "aggressive_expansion", "maintain", "reduction", "withdrawal" |
| `strategy_coeff_lower` | 浮動小数点 | 戦略係数下限 | 1.0, 0.95, 0.9, 0.7 |
| `strategy_coeff_upper` | 浮動小数点 | 戦略係数上限 | 1.2, 1.05, 1.0, 0.9 |

**戦略区分の値**:
- `aggressive_expansion`: 積極拡大
- `maintain`: 維持
- `reduction`: 縮小
- `withdrawal`: 撤退

### 5. 競合関連

| カラム名 | 型 | 説明 | 例 |
|---------|---|------|-----|
| `competitor_code` | 文字列 | 競合コード | "CompetitorA", "CompetitorB" |
| `competitor_share` | 浮動小数点 | 競合シェア、0.0〜1.0 | 0.3, 0.25 |
| `competitor_strength` | 文字列 | 競合競争力評価 | "strong", "moderate", "weak" |
| `acquisition_rate_lower` | 浮動小数点 | 奪取可能率下限、0.0〜1.0 | 0.0, 0.007, 0.017 |
| `acquisition_rate_upper` | 浮動小数点 | 奪取可能率上限、0.0〜1.0 | 0.01, 0.017, 0.033 |

---

## ファイル別スキーマ定義

### 1. sales_2024.csv（現状販売データ）

**目的**: 現在の販売実績データ

**必須カラム**:
- `year`: 年度
- `product_code`: 製品コード
- `plant_code`: 拠点コード（v6で追加、v5では`plant`）
- `segment_code`: セグメントコード（v6で追加、v5では`segment`）
- `customer_code`: 顧客コード（v6で追加、v5では`customer_name`）
- `sales_volume`: 販売数量（v6で統一、v5では`sales_qty`）
- `unit_price`: 単価
- `unit_cost`: 単位コスト
- `margin_rate`: 粗利率

**オプションカラム**:
- `product_name`: 製品名
- `cost_band`: コストバンド（例: "low", "high"）

**例**:
```csv
year,product_code,plant_code,segment_code,customer_code,sales_volume,unit_price,unit_cost,margin_rate
2024,P001,A,industrial,Customer_A,2000,60000,53000,0.117
2024,P001,A,industrial,Customer_E,1500,61000,53500,0.123
```

---

### 2. product_master.csv（製品マスタ）

**目的**: 製品×拠点×セグメント×顧客の組み合わせマスタ（v6で顧客追加）

**必須カラム**:
- `product_code`: 製品コード
- `plant_code`: 拠点コード
- `segment_code`: セグメントコード
- `customer_code`: 顧客コード（v6で追加）
- `unit_price`: 単価
- `unit_cost`: 単位コスト
- `unit_profit`: 単位粗利
- `margin_rate`: 粗利率
- `sales_volume`: 販売数量

**オプションカラム**:
- `product_name`: 製品名
- `cost_band`: コストバンド

**例**:
```csv
product_code,plant_code,segment_code,customer_code,unit_price,unit_cost,unit_profit,margin_rate,sales_volume
P001,A,industrial,Customer_A,60000,53000,7000,0.117,2000
P001,A,industrial,Customer_E,61000,53500,7500,0.123,1500
```

---

### 3. market_master.csv（市場マスタ）

**目的**: セグメント別の市場データ

**必須カラム**:
- `segment_code`: セグメントコード
- `market_size`: 現在の市場規模
- `market_size_after_1y`: 1年後の市場規模（v6で変更）
- `cagr`: 年平均成長率
- `current_share`: 現状シェア
- `strategy_type`: 戦略区分

**例**:
```csv
segment_code,market_size,market_size_after_1y,cagr,current_share,strategy_type
industrial,1008000,1007920,-0.01,0.2,withdrawal
electronics,630000,648900,0.03,0.2,maintain
```

---

### 4. competitor_master.csv（競合マスタ）

**目的**: セグメント×競合の組み合わせデータ

**必須カラム**:
- `segment_code`: セグメントコード
- `competitor_code`: 競合コード
- `competitor_share`: 競合シェア
- `competitor_strength`: 競合競争力評価
- `acquisition_rate_lower`: 奪取可能率下限
- `acquisition_rate_upper`: 奪取可能率上限

**例**:
```csv
segment_code,competitor_code,competitor_share,competitor_strength,acquisition_rate_lower,acquisition_rate_upper
industrial,CompetitorA,0.356,strong,0.0,0.01
industrial,CompetitorB,0.178,moderate,0.007,0.017
```

---

### 5. segment_master.csv（セグメントマスタ）

**目的**: セグメントの基本情報

**必須カラム**:
- `segment_code`: セグメントコード
- `segment_name`: セグメント名
- `strategy_type`: 戦略区分

**例**:
```csv
segment_code,segment_name,strategy_type
industrial,Industrial,withdrawal
electronics,Electronics,maintain
oil_gas,Oil & Gas,aggressive_expansion
others,Others,reduction
```

---

## データ型と制約

### 数値型の範囲

| カラム | 最小値 | 最大値 | 備考 |
|--------|-------|-------|------|
| `sales_volume` | 0 | ∞ | 負の値は不可 |
| `unit_price` | 0 | ∞ | 負の値は不可 |
| `unit_cost` | 0 | ∞ | 負の値は不可 |
| `unit_profit` | -∞ | ∞ | 赤字の場合は負も許容 |
| `margin_rate` | 0.0 | 1.0 | 0〜100%を0.0〜1.0で表現 |
| `market_share` | 0.0 | 1.0 | 0〜100%を0.0〜1.0で表現 |
| `cagr` | -1.0 | 1.0 | -100%〜+100%を-1.0〜1.0で表現 |

### 文字列型の許容値

#### `segment_code`
- `industrial`
- `electronics`
- `oil_gas`
- `others`

#### `plant_code`
- `A`
- `B`

#### `strategy_type`
- `aggressive_expansion`
- `maintain`
- `reduction`
- `withdrawal`

#### `competitor_strength`
- `strong`
- `moderate`
- `weak`

---

## バリデーションルール

### 必須チェック

1. **必須カラムの存在**: スキーマで定義された必須カラムがすべて存在すること
2. **データ型**: 数値カラムは数値型、文字列カラムは文字列型であること
3. **欠損値**: 必須カラムに欠損値（NULL, NaN）がないこと

### 範囲チェック

1. **数量・金額**: `sales_volume`, `unit_price`, `unit_cost`は0以上
2. **率**: `margin_rate`, `market_share`, `cagr`などの率は-1.0〜1.0の範囲内
3. **シェア**: `market_share`, `current_share`などのシェアは0.0〜1.0の範囲内

### 整合性チェック

1. **粗利計算**: `unit_profit = unit_price - unit_cost`が成立すること
2. **粗利率計算**: `margin_rate = unit_profit / unit_price`が成立すること（誤差±0.01以内）
3. **市場規模**: `market_size_after_1y = market_size × (1 + cagr)`が成立すること（誤差±1%以内）

---

## 変更履歴

### v6 (2025-12-07)
- **A-5改善提案を反映**: データフォーマット統一
- カラム名統一: `sales_qty` → `sales_volume`
- カラム名統一: `plant` → `plant_code`, `segment` → `segment_code`
- カラム名統一: `customer_name` → `customer_code`
- 期間変更: `market_size_after_3y` → `market_size_after_1y`
- 顧客コード追加: product_masterに`customer_code`を追加

### v5 (2024-12-04)
- 初版作成

---

**以上**
