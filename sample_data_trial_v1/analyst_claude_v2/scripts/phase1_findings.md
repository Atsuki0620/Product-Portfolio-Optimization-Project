# Phase1: データ設計の問題点確認と修正方針

## 1.1 product_master.csv の allowed_plants 表示確認

### 確認結果

product_master.csv を読み込み、allowed_plants カラムの実際の値を確認しました。

**データ構造確認:**
- ✅ データは正しく保存されている
- ✅ "A|B"、"A"、"B" の3パターンが存在
- ✅ P001 は "A|B" になっている（両拠点対応）

**拠点の分布:**

| パターン | 製品数 | 割合 |
|---------|--------|------|
| A のみ | 6 | 30% |
| B のみ | 7 | 35% |
| A\|B（両方） | 7 | 35% |

**価格帯 × 拠点のクロス集計:**

|  | A のみ | B のみ | A\|B |
|---------|--------|--------|------|
| low | 2 | 2 | 4 |
| high | 4 | 5 | 3 |

### 詳細リスト

| 製品コード | 製品名 | 価格帯 | 拠点 | セグメント |
|-----------|--------|--------|------|-----------|
| P001 | アクセルハウジング | low | A\|B | automotive\|construction\|consumer |
| P002 | 断熱コンポジット | low | A | construction\|chemical\|others |
| P003 | 配線ハーネス | low | B | automotive\|electronics |
| P004 | 燃料制御バルブ | low | A\|B | automotive\|chemical |
| P005 | 標準ギアセット | low | A | automotive\|construction |
| P006 | 汎用シール材 | low | B | construction\|consumer\|others |
| P007 | セーフティボルト | low | A\|B | automotive\|electronics |
| P008 | 耐熱パッキン | low | A\|B | chemical\|others |
| P009 | 医療用マイクロポンプ | high | B | medical |
| P010 | 精密レーザーモジュール | high | A | electronics |
| P011 | 骨再生プレート | high | B | medical |
| P012 | 高速通信用モジュール | high | A\|B | electronics |
| P013 | スペシャルコーティング材 | high | A | chemical\|others |
| P014 | 食品向け滅菌バルブ | high | B | food_beverage |
| P015 | ヘビーデューティアクチュエータ | high | A\|B | construction\|automotive |
| P016 | 医療用センシングチップ | high | B | medical |
| P017 | 化学反応制御ユニット | high | A | chemical |
| P018 | クリーンルームコントローラ | high | A | electronics |
| P019 | スマート家電基板 | high | B | consumer\|electronics |
| P020 | 多目的ロボット関節 | high | A\|B | automotive\|construction\|electronics |

### 単価の範囲

**低価格帯 (low):**
- 最小単価: 1,000 円
- 最大単価: 1,900 円
- 平均最小単価: 1,219 円
- 平均最大単価: 1,556 円

**高価格帯 (high):**
- 最小単価: 6,000 円
- 最大単価: 8,200 円
- 平均最小単価: 6,475 円
- 平均最大単価: 7,242 円

### 結論

- **表示の問題ではなく、データは正しく保存されている**
- Phase1レポートでの表示も正確
- 特に修正は不要

---

## 1.2 製品別集計の金額定義の明確化

### 現状の問題点

Phase1レポートの「表1: 製品別集計」では、販売と生産の両方で「合計金額」というカラム名を使用しているが、その内容が異なる：

- **販売**の「合計金額」= `sales_amount`（販売金額）
- **生産**の「合計金額」= `production_cost`（生産原価）

この違いが明確でないため、読み手が混乱する可能性がある。

### 現在のコード実装

`scripts/analyze_for_report.py` の `aggregate_by_product()` 関数:

```python
# 販売集計
sales_agg = sales.groupby(['product_code', 'year']).agg({
    'sales_qty': 'sum',
    'sales_amount': 'sum'  # 販売金額
}).reset_index()
sales_agg['type'] = '販売'
sales_agg = sales_agg.rename(columns={'sales_qty': 'qty', 'sales_amount': 'amount'})

# 生産集計
prod_agg = production.groupby(['product_code', 'year']).agg({
    'production_qty': 'sum',
    'production_cost': 'sum'  # 生産原価
}).reset_index()
prod_agg['type'] = '生産'
prod_agg = prod_agg.rename(columns={'production_qty': 'qty', 'production_cost': 'amount'})
```

両方とも `amount` という同じカラム名にリネームされているため、表示時に区別がつかない。

### 改善方針

以下の3つの改善策を実施する：

#### 方針1: カラム名の明確化

販売と生産で異なるカラム名を使用する：

- 販売: `sales_amount`（販売金額）
- 生産: `cost_amount`（原価金額）

#### 方針2: 表示形式の改善

Markdownテーブルで以下の形式を採用：

**改善前:**
| 製品コード | 年度 | 区分 | 合計数量(本) | 合計金額(¥) | 合計金額($) |

**改善後:**
| 製品コード | 年度 | 区分 | 数量(本) | 販売金額(¥) | 原価金額(¥) | 粗利(¥) | 販売金額($) | 原価金額($) | 粗利($) |

※ 販売行は販売金額のみ、生産行は原価金額のみを表示（該当しない列は空欄）

#### 方針3: 統合表示の追加

製品×年度で販売と生産を1行にまとめた統合表示も追加：

| 製品コード | 年度 | 販売数量 | 生産数量 | 販売金額(¥) | 原価金額(¥) | 粗利(¥) | 粗利率(%) |

### 実装計画

Phase2のデータ再生成時に、以下を実施：

1. `production.csv` のカラム構造を変更
   - 現状: `production_cost`（合計原価）のみ
   - 変更後: `unit_cost`（単位原価）と `cost_amount`（合計原価）の両方を含む

2. `analyze_for_report.py` を改善版に更新
   - 明確なカラム名を使用
   - 統合表示機能を追加

3. レポート生成スクリプトを更新
   - 改善されたテーブル形式を採用

---

## Phase1のまとめ

### 確認結果

1. **allowed_plants の確認**: ✅ データは正しく、修正不要
2. **金額定義の確認**: ✅ 問題点を特定、改善方針を策定

### 次のステップ（Phase2）

- generate_sample_data_v2.py の作成
  - production_csv の構造変更（unit_cost と cost_amount を追加）
  - 単価の現実化（low: 10,000-30,000円、high: 60,000-100,000円）
  - 稼働率90%達成のための数量調整
  - セグメント構成比の厳密化
