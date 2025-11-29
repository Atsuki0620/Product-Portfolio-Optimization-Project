# データ生成仕様書（2024年版）

## 1. 全体の前提

### 1.1 対象年度
- 対象年：**2024年のみ**
- 全データは年間値（年次数量・金額）で扱い、月別行は持たない

### 1.2 データ粒度
- **行の一意キー**：製品 × 拠点 × セグメント
- year カラムを持ってもよいが、キーには含めない（全行 2024）

### 1.3 製品構成
- **総数**：20製品（P001〜P020）
- **cost_band = 'low'**：12製品
- **cost_band = 'high'**：8製品
- **注意**：price_band という名称は使用せず、原価構造を示すラベルとして cost_band のみ使用

### 1.4 セグメント
以下の4つのセグメントを定義：
- `industrial`（産業用）
- `electronics`（電子機器）
- `oil_gas`（石油・ガス）
- `others`（その他）

### 1.5 拠点
- **拠点A** (plant='A')
- **拠点B** (plant='B')

---

## 2. 年間販売数量と拠点キャパシティ

### 2.1 全社年間販売数量
- **2024年の年間販売数量（全社合計）**：`TOTAL_ANNUAL_SALES_QTY_2024 = 504,000 本`
- **制約**：`sum(sales_qty) = 504,000`

### 2.2 拠点キャパシティ
#### キャパシティ比率
- 拠点A : 拠点B = **25 : 17**
- 全社年間キャパシティ合計：**504,000 本**（販売数量と一致）

#### 拠点別年間キャパシティ
- **plantA_capacity_annual_2024 = 300,000 本**
- **plantB_capacity_annual_2024 = 204,000 本**

#### 制約条件
- `sum(production_qty where plant='A') ≤ 300,000`
- `sum(production_qty where plant='B') ≤ 204,000`
- `sum(production_qty 全体) ≤ 504,000`

#### サンプルデータの方針
- 生産数量と販売数量は基本的に一致させる（在庫・欠品は考慮しない）

---

## 3. セグメント販売比と粗利率

### 3.1 用語定義
- **「需要シェア」ではなく「セグメント販売比」という名称を使用する**

### 3.2 セグメント販売比（合計100%）
| セグメント | 販売比 |
|-----------|--------|
| industrial | 40% |
| electronics | 25% |
| oil_gas | 10% |
| others | 25% |

### 3.3 理論的な年間販売数量（2024年、合計504,000本）
| セグメント | 理論販売数量 |
|-----------|-------------|
| industrial | 201,600 本 |
| electronics | 126,000 本 |
| oil_gas | 50,400 本 |
| others | 126,000 本 |

**実データの調整方針**：
- 各セグメントの `sum(sales_qty)` が上記理論値に対して **±数ポイント以内** に収まるよう、数量を調整する

### 3.4 セグメント別ターゲット粗利率（平均値）
| セグメント | ターゲット粗利率 |
|-----------|-----------------|
| industrial | 10% |
| electronics | 20% |
| oil_gas | 50% |
| others | 20% |

### 3.5 粗利率の定義
```
margin_rate = (unit_price - unit_cost) / unit_price
```

### 3.6 生成ロジック
1. 行ごとに `unit_price` を生成
2. セグメントの `target_margin_rate` に小さな乱数（±数ポイント）を加えて `margin_rate` を決定
3. `margin_rate` から `unit_cost` を逆算：
   ```
   unit_cost = unit_price × (1 - margin_rate)
   ```
4. セグメント単位の平均では、`target_margin_rate` に近づくように調整
5. `cost_band`（low / high）は `margin_rate` の中心値やブレ幅を変えるためのラベルとして利用可能

---

## 4. 単価と cost_band

### 4.1 単価レンジ
- すべての製品で **unit_price ∈ [40,000, 100,000]**

### 4.2 cost_band の役割
- `cost_band = 'low'` / `'high'`
- **単価レンジには影響させず**、原価率の分布（中心やノイズ幅）を変えるためのラベルとして使用

---

## 5. 販売データ（D1: sales_2024.csv）

### 5.1 データ粒度
- **product_code × plant × segment**（2024年）

### 5.2 想定カラム
| カラム名 | データ型 | 説明 |
|---------|---------|------|
| product_code | string | 製品コード（P001〜P020） |
| product_name | string | 製品名 |
| cost_band | enum | 'low' または 'high' |
| plant | enum | 'A' または 'B' |
| segment | enum | 'industrial', 'electronics', 'oil_gas', 'others' |
| sales_qty | int | 年間販売数量 |
| unit_price | int/decimal | 単価（40,000〜100,000） |
| sales_amount | decimal | 売上金額（sales_qty × unit_price） |
| customer_name | string | 顧客名（任意） |
| year | int | 年度（2024）※任意 |

### 5.3 制約条件

#### 全体制約
- `sum(sales_qty) = 504,000`

#### セグメント別制約
- `sum(sales_qty where segment=S)` が、`504,000 × segment_sales_mix[S]` に近づくよう調整

#### 拠点別制約
- `sum(sales_qty where plant='A') ≤ 300,000`
- `sum(sales_qty where plant='B') ≤ 204,000`

---

## 6. 生産データ（D2: production_2024.csv）

### 6.1 データ粒度
- **product_code × plant**（セグメントは合算）

### 6.2 想定カラム
| カラム名 | データ型 | 説明 |
|---------|---------|------|
| product_code | string | 製品コード |
| plant | enum | 'A' または 'B' |
| production_qty | int | 年間生産数量 |
| unit_cost | decimal | 単位原価 |
| cost_amount | decimal | 原価金額（unit_cost × production_qty） |

### 6.3 制約条件

#### 生産数量と販売数量の整合
- `production_qty(product, plant) = sum(sales_qty(product, plant, 全segment))`

#### 拠点キャパシティ制約
- `sum(production_qty where plant='A') ≤ 300,000`
- `sum(production_qty where plant='B') ≤ 204,000`

---

## 7. マスタデータ（D3）

### 7.1 product_master.csv

#### カラム例
| カラム名 | データ型 | 説明 |
|---------|---------|------|
| product_code | string | 製品コード |
| product_name | string | 製品名 |
| cost_band | enum | 'low' または 'high' |
| allowed_plants | string | 許可拠点（"A", "B", "A\|B"） |
| allowed_segments | string | 許可セグメント（例："industrial\|electronics"） |

### 7.2 segment_master.csv

#### カラム例
| カラム名 | データ型 | 説明 |
|---------|---------|------|
| segment_code | string | セグメントコード（industrial, electronics, oil_gas, others） |
| segment_sales_mix | decimal | セグメント販売比（0.40, 0.25, 0.10, 0.25） |
| target_margin_rate | decimal | ターゲット粗利率（0.10, 0.20, 0.50, 0.20） |

### 7.3 拠点キャパシティ（定数）
以下の値をスクリプト内で定義：
- `plantA_capacity_annual_2024 = 300,000`
- `plantB_capacity_annual_2024 = 204,000`
- `total_capacity_annual_2024 = 504,000`

---

## 8. データ生成の実装方針

### 8.1 基本フロー
1. マスタデータ（product_master.csv, segment_master.csv）を読み込む
2. 製品 × 拠点 × セグメントの組み合わせを生成
3. 各行に対して初期数量をランダム生成
4. 以下の制約を満たすようにスケーリング・調整：
   - `sum(sales_qty) = 504,000`
   - セグメント販売比の遵守
   - 拠点キャパシティ制約
5. `unit_price` を [40,000, 100,000] から生成
6. セグメント別 `target_margin_rate` と `cost_band` をもとに `unit_cost` を計算
7. 販売データ（D1）と生産データ（D2）を出力

### 8.2 粗利率の調整
- 各セグメントの平均粗利率が `target_margin_rate` に近づくように、行ごとの `margin_rate` を調整
- `cost_band` によって、粗利率の中心値やノイズ幅を変化させる

### 8.3 出力先
- **販売データ（D1）**：`sample_data_trial_v4/analyst_claude_v4/data/raw/sales_2024.csv`
- **生産データ（D2）**：`sample_data_trial_v4/analyst_claude_v4/data/raw/production_2024.csv`

---

## 9. データ検証の要件

### 9.1 販売データの検証項目
1. **販売数量の合計**
   - `sum(sales_qty) = 504,000` であること

2. **セグメント別販売数量**
   - 各セグメントの `sum(sales_qty)` が、`segment_sales_mix` に基づく理論値 **±3ポイント以内** であること

3. **拠点別販売数量**
   - 拠点A：`sum(sales_qty where plant='A') ≤ 300,000`
   - 拠点B：`sum(sales_qty where plant='B') ≤ 204,000`

### 9.2 生産データの検証項目
1. **生産数量と販売数量の整合**
   - 各 `product × plant` ごとに、`production_qty = sum(sales_qty)` であること

2. **拠点別生産数量**
   - 拠点A：`sum(production_qty where plant='A') ≤ 300,000`
   - 拠点B：`sum(production_qty where plant='B') ≤ 204,000`

### 9.3 粗利率の検証
- セグメント別平均 `margin_rate` が、`target_margin_rate` に対して **±数ポイント程度** の範囲内であること

### 9.4 検証レポート
- コンソール出力で各検証項目の結果（OK / NG）と主要な集計値を表示
- Markdown形式のレポート（`sample_data_trial_v4/analyst_claude_v4/reports/validation_2024_v4.md`）を生成し、検証結果を詳しく記載

---

## 10. 注意事項

1. **過去バージョンの保護**
   - 既存の `sample_data_trial_v1 / v2 / v3` や `analyst_claude_v2 / v3` 配下のコード・ドキュメントは変更しない

2. **データ生成の優先順位**
   - まず 2024年単年仕様（v4）に基づく **正確なサンプルデータ生成と要件チェック** に全力を注ぐ
   - `generate_sample_data_v4.py` と `validate_generated_data_2024_v4.py` によるデータ生成と検証が安定してから、後続フェーズ（最適化・感度分析など）に進める

3. **命名規則の統一**
   - すべての新規ファイルには `v4` または `2024` を含める
   - 例：`generate_sample_data_v4.py`, `validation_2024_v4.md`

---

## 改訂履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2024-XX-XX | 1.0 | 初版作成 |
