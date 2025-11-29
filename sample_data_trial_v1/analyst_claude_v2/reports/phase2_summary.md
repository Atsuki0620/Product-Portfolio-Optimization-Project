# Phase2 データ再設計・実施レポート

**実施日**: 2025年11月28日
**環境**: analyst_claude_v2
**目的**: Phase1フィードバックに基づくデータ再設計と再生成

---

## 目次

1. [Phase1: データ設計の問題点確認](#phase1-データ設計の問題点確認)
2. [Phase2: サンプルデータの再設計と再生成](#phase2-サンプルデータの再設計と再生成)
3. [検証結果](#検証結果)
4. [今後の課題](#今後の課題)

---

## Phase1: データ設計の問題点確認

### 1.1 product_master.csv の allowed_plants 表示確認

#### 確認結果

✅ **データは正しく保存されている**

- "A|B"、"A"、"B" の3パターンが存在
- P001 は "A|B" になっている（両拠点対応）
- Phase1レポートでの表示も正確

#### 拠点の分布

| パターン | 製品数 | 割合 |
|---------|--------|------|
| A のみ | 6 | 30% |
| B のみ | 7 | 35% |
| A\|B（両方） | 7 | 35% |

#### 単価の範囲（修正前）

**低価格帯 (low):**
- 最小単価: 1,000 円
- 最大単価: 1,900 円

**高価格帯 (high):**
- 最小単価: 6,000 円
- 最大単価: 8,200 円

#### 結論

- 表示の問題ではなく、データは正しい
- 特に修正は不要

---

### 1.2 製品別集計の金額定義の明確化

#### 現状の問題点

Phase1レポートの「表1: 製品別集計」では、販売と生産の両方で「合計金額」というカラム名を使用しているが、その内容が異なる：

- **販売**の「合計金額」= `sales_amount`（販売金額）
- **生産**の「合計金額」= `production_cost` または `cost_amount`（生産原価）

この違いが明確でないため、読み手が混乱する可能性がある。

#### 改善方針

以下の3つの改善策を実施：

1. **カラム名の明確化**: production_csvに`unit_cost`と`cost_amount`の両方を含める
2. **表示形式の改善**: 販売金額と原価金額を明確に区別
3. **統合表示の追加**: 製品×年度で販売と生産を1行にまとめた表示

#### 実装

Phase2のデータ再生成時に、以下を実施：
- `production.csv` の構造を変更: `unit_cost` + `cost_amount` を出力
- `data_pipeline.py` を更新: 新旧両方の構造をサポート

---

## Phase2: サンプルデータの再設計と再生成

### 2.1 generate_sample_data_v2.py の作成

#### 修正内容

以下の4つの修正を実施：

##### 修正1: 販売単価の現実化

| 価格帯 | 修正前 | 修正後 |
|-------|--------|--------|
| 低価格品（low） | 1,000〜1,900円 | 10,000〜30,000円 |
| 高価格品（high） | 6,000〜8,200円 | 60,000〜100,000円 |

**実装:**
```python
def _generate_realistic_price(self, price_band: str) -> float:
    if price_band == "low":
        return float(self.rng.integers(10000, 30001))  # 1〜3万円
    else:  # high
        return float(self.rng.integers(60000, 100001))  # 6〜10万円
```

##### 修正2: production_csvの構造変更

**修正前:**
- `production_cost`（合計原価）のみ

**修正後:**
- `unit_cost`（単位原価）
- `cost_amount`（合計原価 = unit_cost × production_qty）

**実装:**
```python
grouped["unit_cost"] = grouped.apply(self._calc_unit_cost, axis=1)
grouped["cost_amount"] = grouped["unit_cost"] * grouped["production_qty"]
return grouped[["year", "product_code", "plant", "production_qty", "unit_cost", "cost_amount"]]
```

##### 修正3: 稼働率90%達成のための数量調整

**パラメータ修正:**

| 項目 | 修正前 | 修正後 |
|------|--------|--------|
| min_qty | 105 | 5,000 |
| max_qty | 5,000 | 100,000 |
| low base_qty | 900〜2,000 | 10,000〜15,000 |
| high base_qty | 180〜450 | 5,000〜7,500 |
| year_drift | 0.02 | 0.10 |

**実装:**
```python
@dataclass
class GeneratorConfig:
    min_qty: int = 5000   # 105 → 5000
    max_qty: int = 100000 # 5000 → 100000

def _base_qty(self, price_band: str) -> int:
    if price_band == "low":
        return int(self.rng.integers(10000, 15001))  # 900〜2000 → 10000〜15000
    return int(self.rng.integers(5000, 7501))        # 180〜450 → 5000〜7500

def _sample_qty(self, base_qty: int, share: float, year_offset: int) -> int:
    year_drift = 1 + 0.10 * year_offset * self.rng.uniform(0.8, 1.2)  # 0.02 → 0.10
    # ...
```

##### 修正4: セグメント構成比の厳密化

**選択確率の引き上げ:**

| 価格帯 | 修正前 | 修正後 |
|-------|--------|--------|
| 低価格（low） | 80% | 95% |
| 高価格（high） | 60% | 85% |

**事後調整の追加:**
```python
def _adjust_segment_composition(self, sales_df: pd.DataFrame) -> pd.DataFrame:
    """理論構成比に合わせて数量をスケーリング（差異5%ポイント以内に調整）"""
    for segment, theoretical_share in self.segment_share.items():
        actual_share = current_share[segment]
        diff = theoretical_share - actual_share
        if abs(diff) > 0.05:  # 5%ポイント以上の差異がある場合
            adjustment_factor = theoretical_share / actual_share
            adjustment_factor = max(0.8, min(1.2, adjustment_factor))  # 0.8〜1.2倍の範囲内
            # 調整を適用
```

---

### 2.2 データ再生成の実行

#### 生成結果

```
✓ 販売データ: 105 行
✓ 生産データ: 68 行

【統計情報】
総販売数量: 1,038,583 本
総販売金額: ¥40,491,414,788
平均単価: ¥48,487
```

#### セグメント構成比の検証

| セグメント | 実測値(%) | 理論値(%) | 差異(pt) | 評価 |
|-----------|----------|----------|---------|------|
| automotive | 29.75 | 30.00 | 0.25 | ✅ 優秀 |
| electronics | 19.54 | 18.00 | 1.54 | ✅ 良好 |
| construction | 15.21 | 15.00 | 0.21 | ✅ 優秀 |
| chemical | 10.64 | 8.00 | 2.64 | ✅ 良好 |
| others | 9.87 | 5.00 | 4.87 | ⚠️ やや大 |
| consumer | 7.63 | 9.00 | 1.37 | ✅ 良好 |
| medical | 4.78 | 5.00 | 0.22 | ✅ 優秀 |
| food_beverage | 2.58 | 10.00 | 7.42 | ❌ 大きな差異 |

**差異の原因:**
- `food_beverage` セグメントを扱う製品が1つ（P014）のみ
- `others` セグメントを扱う製品が多いため、構成比が高くなる

**評価:**
- 8セグメント中6セグメントが3%ポイント以内に収まっている
- 全体的には改善されている

---

### 2.3 パイプラインの再実行

#### 実行結果

1. **データ準備（run_data_prep_once.py）**
   ```
   sales_summary rows: 105
   margin_matrix rows: 105
   ```

2. **配賦処理（run_allocation_once.py）**
   ```
   allocation rows: 15
   total qty: 74,062.86
   total margin: ¥1,999,752,515
   ```

3. **シナリオ分析（run_scenarios_once.py）**
   ```
   7シナリオの分析が完了
   Base総粗利: ¥1,999,752,515
   ```

#### data_pipeline.py の修正

新しい`cost_amount`カラムに対応するため、後方互換性を持たせた修正を実施：

```python
def load_production_data(years: Iterable[int]) -> pd.DataFrame:
    # ...
    # v2対応: cost_amount (新) または production_cost (旧) をサポート
    if "cost_amount" in df.columns and "production_cost" not in df.columns:
        df["production_cost"] = df["cost_amount"]
    # ...
```

---

## 検証結果

### 稼働率の改善

#### 総需要ベースの稼働率

| 項目 | 修正前 | 修正後 | 改善 |
|------|--------|--------|------|
| 総キャパシティ | 1,056,000 本 | 1,056,000 本 | - |
| 総需要 | 6,732 本 | 1,038,583 本 | **154倍** |
| 稼働率 | 0.64% | 98.35% | **+97.71pt** |

✅ **目標90%を達成！（98.35%）**

#### 拠点別稼働率

| 拠点 | 需要（本） | 稼働率 | 評価 |
|------|----------|--------|------|
| 拠点A | 514,952 | 97.53% | ✅ 目標達成 |
| 拠点B | 523,631 | 99.17% | ✅ 目標達成 |

#### 年度別需要

| 年度 | 需要（本） | 構成比 |
|------|----------|--------|
| 2022 | 325,777 | 31.4% |
| 2023 | 342,816 | 33.0% |
| 2024 | 369,990 | 35.6% |

年度ごとに成長している（year_drift効果が反映されている）

---

### 単価の改善

#### 販売単価の比較

| 価格帯 | 修正前（円） | 修正後（円） | 倍率 |
|-------|------------|------------|------|
| 低価格（low） | 1,000〜1,900 | 10,000〜30,000 | **約13倍** |
| 高価格（high） | 6,000〜8,200 | 60,000〜100,000 | **約12倍** |
| 平均 | 約1,400 | 約48,487 | **約35倍** |

✅ **より現実的な単価設定に改善**

---

### データ構造の改善

#### production.csv の新構造

**修正前:**
```csv
year,product_code,plant,production_qty,production_cost
2024,P001,A,13000,15000000
```

**修正後:**
```csv
year,product_code,plant,production_qty,unit_cost,cost_amount
2024,P001,A,13538,10336.84,139940194.63
```

✅ **unit_costが明示されることで、分析の幅が広がった**

---

### パイプライン処理の確認

#### 中間データの生成

以下のファイルが正常に生成された：

1. **data/intermediate/sales_summary.csv** - 販売集計
2. **data/intermediate/cost_summary.csv** - 原価集計
3. **data/intermediate/margin_matrix.csv** - 粗利マトリクス（105行）
4. **data/intermediate/segment_demand.csv** - セグメント別需要
5. **data/intermediate/allocation_results.csv** - 配賦結果（15行）
6. **data/intermediate/scenario_results.csv** - シナリオ分析結果（7行）

#### 配賦結果の改善

| 項目 | 修正前 | 修正後 | 改善 |
|------|--------|--------|------|
| 配賦行数 | 17 | 15 | - |
| 総配賦数量 | 6,732 本 | 74,063 本 | **11倍** |
| 総粗利 | ¥10,511,127 | ¥1,999,752,515 | **190倍** |
| 平均単位粗利 | ¥1,561 | ¥27,001 | **17倍** |

✅ **大幅に改善**

---

## 今後の課題

### 課題1: セグメント構成比の更なる改善

**現状:**
- `food_beverage` と `others` セグメントで大きな差異（7.42pt, 4.87pt）

**原因:**
- 製品の偏り（food_beverageは1製品のみ）

**対策案:**
- product_master.csv を見直し、セグメント割り当てを調整
- 特定セグメント専用製品を増やす
- 事後調整アルゴリズムの改善（より積極的なスケーリング）

---

### 課題2: 配賦アルゴリズムの稼働率

**現状:**
- 総需要は98.35%（目標達成）
- しかし、配賦数量は74,063本のみ（7.0%）

**原因:**
- margin_matrixは過去実績の平均を使用
- 配賦アルゴリズムが需要データではなく、過去実績に基づいて配賦

**対策案:**
- segment_demand.csvを直接使用するロジックに変更
- または、margin_matrixの計算方法を見直す

---

### 課題3: 製品ラインナップの見直し

**現状:**
- 20製品中、high製品が12、low製品が8
- セグメント別の製品数に偏りがある

**対策案:**
- product_master.csvを拡張（30〜50製品）
- セグメント専用製品を追加
- 価格帯の多様化（medium価格帯の追加など）

---

## まとめ

### Phase1, 2で達成したこと

✅ **1. データ設計の問題点を特定**
- allowed_plantsの確認（問題なし）
- 金額定義の明確化（改善方針を策定）

✅ **2. 販売単価を現実化**
- low: 1,000〜1,900円 → 10,000〜30,000円
- high: 6,000〜8,200円 → 60,000〜100,000円

✅ **3. production_csvの構造改善**
- unit_cost + cost_amount の両方を出力
- 分析の幅が広がった

✅ **4. 稼働率を90%以上に改善**
- 0.64% → 98.35%（**+97.71pt**）
- 目標を達成

✅ **5. セグメント構成比を改善**
- 8セグメント中6セグメントが3%ポイント以内に収まる
- 全体的に理論値に近づいた

✅ **6. データパイプラインの動作確認**
- 全スクリプトが正常に動作
- 中間データが正しく生成された

### 次のステップ（Phase3以降）

Phase3以降では、以下のタスクを実施する予定：

1. **貪欲配賦アルゴリズムの詳細分析**
   - フローチャートの作成
   - 粗利率考慮の必要性の説明
   - リスク評価（仮想シナリオ）

2. **代替アルゴリズムの網羅的調査**
   - 評価ポイントの定義と重み付け
   - 各手法の詳細評価
   - 比較サマリと推奨

3. **レポート出力**
   - Jupyter Notebook形式（.ipynb）
   - Markdown形式（.md）

---

**Phase1, 2 完了日**: 2025年11月28日
**次の作業**: Phase3の実施待ち（ユーザーからの指示待ち）
