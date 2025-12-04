# 製品ポートフォリオ最適化フレームワーク v5 データ仕様書

**バージョン**: 1.0
**作成日**: 2025年12月3日
**対象ディレクトリ**: `sample_data_trial_v5/analyst_claude_v5/`

---

## 1. 概要

本文書は、製品ポートフォリオ最適化フレームワーク v5 で使用するデータファイルの仕様を定義します。v5では、市場シェアベースの最適化を実現するため、市場マスタと競合マスタが新規追加されています。

---

## 2. データディレクトリ構成

```
data/
├── master/          # マスタデータ
│   ├── product_master.csv       # 製品マスタ（v4から継続）
│   ├── segment_master.csv       # セグメントマスタ（v4から継続）
│   ├── market_master.csv        # 市場マスタ（v5新規）
│   └── competitor_master.csv    # 競合マスタ（v5新規）
├── raw/             # 生データ
│   ├── sales_2024.csv           # 販売データ（v4から継続）
│   └── production_2024.csv      # 生産データ（v4から継続）
└── processed/       # 処理済みデータ
    ├── market_master_processed.csv
    ├── competitor_master_processed.csv
    ├── target_share_initial.csv
    ├── competitive_analysis.csv
    ├── target_share_final.csv
    └── sales_2024_opt_v5.csv
```

---

## 3. マスタデータ仕様

### 3.1 製品マスタ（product_master.csv）

**説明**: 製品の基本情報を管理（v4から変更なし）

| カラム名 | データ型 | 説明 | 例 |
|---------|---------|------|-----|
| product_code | string | 製品コード | P001 |
| product_name | string | 製品名 | 高圧ホース A-100 |
| segment_code | string | セグメントコード | industrial |
| plant_code | string | 製造拠点コード | A |
| unit_cost | decimal | 単位原価（円） | 1500.00 |
| unit_price | decimal | 単位価格（円） | 2000.00 |
| unit_profit | decimal | 単位粗利（円） | 500.00 |

**データ件数**: 24製品（4セグメント × 2拠点 × 3製品）

---

### 3.2 セグメントマスタ（segment_master.csv）

**説明**: セグメント別の販売構成比と目標粗利率を管理（v4から継続、役割が変化）

| カラム名 | データ型 | 説明 | 例 |
|---------|---------|------|-----|
| segment_code | string | セグメントコード | industrial |
| segment_sales_mix | decimal | セグメント販売構成比（%） | 0.40 |
| target_margin_rate | decimal | ターゲット粗利率（%） | 0.25 |

**v4からの変更点**:
- `segment_sales_mix`はv5では参考値として使用（制約条件には使用しない）
- 市場シェアベースの制約に置き換えられる

**データ件数**: 4セグメント

---

### 3.3 市場マスタ（market_master.csv）【v5新規】

**説明**: セグメント別の市場規模、成長率、自社シェア、戦略区分を管理

| カラム名 | データ型 | 必須 | 説明 | 例 |
|---------|---------|------|------|-----|
| segment_code | string | ✓ | セグメントコード | industrial |
| current_market_size | integer | ✓ | 現在の市場規模（本数） | 1008000 |
| market_cagr | decimal | ✓ | 市場の年平均成長率（CAGR） | -0.01 |
| current_share | decimal | ✓ | 現状の自社シェア（%） | 0.20 |
| strategy_type | enum | ✓ | 戦略区分 | withdrawal |

**戦略区分（strategy_type）の値**:

| 値 | 説明 | 目標シェア係数 |
|----|------|--------------|
| aggressive_expansion | 積極拡大 | 1.0 〜 1.5 |
| maintain | 維持 | 0.9 〜 1.1 |
| reduction | 縮小 | 0.5 〜 1.0 |
| withdrawal | 撤退 | 0.0 〜 0.7 |

**導出値**（Step 1で算出）:
- `market_size_after_3y`: 3年後市場規模 = `current_market_size × (1 + market_cagr)^3`
- `current_sales_volume`: 自社販売数量 = `current_market_size × current_share`

**データ件数**: 4セグメント

**サンプルデータ**:

```csv
segment_code,current_market_size,market_cagr,current_share,strategy_type
industrial,1008000,-0.01,0.20,withdrawal
electronics,630000,0.03,0.20,maintain
oil_gas,336000,0.05,0.15,aggressive_expansion
others,840000,0.007,0.15,reduction
```

---

### 3.4 競合マスタ（competitor_master.csv）【v5新規】

**説明**: 競合他社のセグメント別シェアと競争力評価を管理

| カラム名 | データ型 | 必須 | 説明 | 例 |
|---------|---------|------|------|-----|
| competitor_code | string | ✓ | 競合コード | COMP_A |
| competitor_name | string | ✓ | 競合名 | 競合A |
| segment_code | string | ✓ | セグメントコード | industrial |
| current_share | decimal | ✓ | 現状シェア（%） | 0.356 |
| competitive_position | enum | ✓ | 競争力評価 | strong |

**競争力評価（competitive_position）の値**:

| 値 | 説明 | 奪取可能率 |
|----|------|----------|
| strong | 強い（技術・営業・ブランドで優位） | 0% 〜 3% |
| moderate | 中程度（同等の競争力） | 2% 〜 5% |
| weak | 弱い（競争力が劣る） | 5% 〜 10% |

**導出値**（Step 1で算出）:
- `current_sales_volume`: 競合販売数量 = `市場規模 × current_share`

**データ件数**: 17件（競合5社×4セグメント、ただしセグメントによって参入していない競合あり）

**サンプルデータ（一部）**:

```csv
competitor_code,competitor_name,segment_code,current_share,competitive_position
COMP_A,競合A,industrial,0.356,strong
COMP_B,競合B,industrial,0.178,moderate
COMP_C,競合C,industrial,0.151,weak
COMP_D,競合D,industrial,0.044,strong
COMP_E,競合E,industrial,0.071,strong
```

**整合性制約**:
- 各セグメントで自社シェア + 全競合シェアの合計 = 100%（±1%の誤差を許容）

---

## 4. 生データ仕様

### 4.1 販売データ（sales_2024.csv）

**説明**: 製品別・拠点別の現状販売実績（v4から変更なし）

| カラム名 | データ型 | 説明 | 例 |
|---------|---------|------|-----|
| product_code | string | 製品コード | P001 |
| segment_code | string | セグメントコード | industrial |
| plant_code | string | 製造拠点コード | A |
| sales_volume | integer | 販売数量（本） | 30000 |
| unit_profit | decimal | 単位粗利（円） | 500.00 |
| total_profit | decimal | 粗利合計（円） | 15000000.00 |

**データ件数**: 24件（製品数と同じ）

**合計販売数量**: 504,000本（総キャパシティと一致）

---

### 4.2 生産データ（production_2024.csv）

**説明**: 拠点別の生産能力情報（v4から変更なし）

| カラム名 | データ型 | 説明 | 例 |
|---------|---------|------|-----|
| plant_code | string | 製造拠点コード | A |
| plant_name | string | 拠点名 | 東京工場 |
| capacity | integer | 生産能力（本/年） | 300000 |
| current_production | integer | 現状生産数量（本） | 300000 |
| utilization_rate | decimal | 稼働率（%） | 1.00 |

**データ件数**: 2拠点

**総キャパシティ**: 504,000本（300,000 + 204,000）

---

## 5. 処理済みデータ仕様

### 5.1 処理済み市場マスタ（market_master_processed.csv）

**説明**: 市場マスタに導出値を追加したもの（Step 1出力）

**追加カラム**:
- `market_size_after_3y`: 3年後市場規模
- `current_sales_volume`: 自社現在販売数量

---

### 5.2 処理済み競合マスタ（competitor_master_processed.csv）

**説明**: 競合マスタに導出値を追加したもの（Step 1出力）

**追加カラム**:
- `current_sales_volume`: 競合現在販売数量

---

### 5.3 目標シェア初期値（target_share_initial.csv）

**説明**: 戦略区分から算出した目標シェアの初期値（Step 2出力）

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| segment_code | string | セグメントコード |
| current_share | decimal | 現状シェア |
| strategy_type | string | 戦略区分 |
| target_share_lower | decimal | 目標シェア下限 |
| target_share_upper | decimal | 目標シェア上限 |

**ユーザー修正**: このファイルはユーザーが修正可能

---

### 5.4 競合分析結果（competitive_analysis.csv）

**説明**: セグメント別の競合分析結果（Step 2出力）

| カラム名 | データ型 | 説明 |
|---------|---------|------|
| segment_code | string | セグメントコード |
| current_share | decimal | 現状シェア |
| total_acquirable_lower | decimal | 奪取可能シェア合計（下限） |
| total_acquirable_upper | decimal | 奪取可能シェア合計（上限） |
| achievable_share_lower | decimal | 到達可能シェア（下限） |
| achievable_share_upper | decimal | 到達可能シェア（上限） |
| warning | string | 警告メッセージ |

---

### 5.5 最終目標シェア（target_share_final.csv）

**説明**: 検証を通過した最終的な目標シェア（Step 3出力）

**構造**: `target_share_initial.csv`と同じ

---

### 5.6 最適化結果（sales_2024_opt_v5.csv）

**説明**: 最適化後の販売計画（Step 4出力）

**構造**: `sales_2024.csv`と同じ形式（v4との互換性のため）

---

## 6. データ検証ルール

### 6.1 必須検証項目

1. **正の数値チェック**: 市場規模、販売数量、キャパシティは正の数値
2. **シェア範囲チェック**: シェアは0〜1の範囲内
3. **シェア合計チェック**: 各セグメントで自社+競合シェア合計=100%（±1%許容）
4. **戦略区分チェック**: strategy_typeが定義された値のいずれか
5. **競争力評価チェック**: competitive_positionが定義された値のいずれか
6. **CAGR範囲チェック**: market_cagrが-50%〜+50%の範囲内（警告）

### 6.2 整合性検証

1. **セグメントコード一致**: 全マスタでsegment_codeが一致
2. **拠点コード一致**: 製品マスタと生産データでplant_codeが一致
3. **キャパシティ整合**: 総販売数量 ≤ 総キャパシティ

---

## 7. データ更新手順

### 7.1 市場環境変化時

1. `market_master.csv`の`market_cagr`を更新
2. Step 1を再実行して`market_size_after_3y`を再計算

### 7.2 競合状況変化時

1. `competitor_master.csv`の`current_share`または`competitive_position`を更新
2. シェア合計が100%になるよう調整
3. Step 1から再実行

### 7.3 戦略変更時

1. `market_master.csv`の`strategy_type`を変更
2. Step 2から再実行して目標シェアを再算出

---

## 8. v4からの移行

### 8.1 継続使用するファイル

- `product_master.csv`
- `segment_master.csv`
- `sales_2024.csv`
- `production_2024.csv`

→ v4から**そのままコピー**して使用

### 8.2 新規作成が必要なファイル

- `market_master.csv`
- `competitor_master.csv`

→ 市場調査データから作成

### 8.3 互換性

- 最適化結果（`sales_2024_opt_v5.csv`）はv4と同じカラム構成
- v4の結果と直接比較可能

---

## 9. 注意事項

### 9.1 データ精度

- 市場規模データは外部調査機関のデータを推奨
- 競合シェアは推定値でも可（合計100%の制約を満たすこと）
- CAGRは過去3年の実績ベースを推奨

### 9.2 機密情報

- 競合の詳細情報（企業名等）は匿名化を検討
- 単価・原価情報は社外秘として取り扱い

### 9.3 更新頻度

- 市場マスタ: 四半期ごとに見直し推奨
- 競合マスタ: 半期ごとに見直し推奨
- 販売データ: 毎月更新

---

## 改訂履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2025-12-03 | 1.0 | 初版作成 |
