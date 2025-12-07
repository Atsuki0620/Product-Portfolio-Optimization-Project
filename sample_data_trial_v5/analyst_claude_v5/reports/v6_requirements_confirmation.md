# v6実装要件の整理と不明点確認

**作成日**: 2025年12月7日

---

## 要件の整理

ご指示いただいた要件を以下のように整理しました。実装開始前に不明点を確認させてください。

---

## 1. 作業環境

### ✅ 理解した内容

- **新規作業フォルダ**: `Product-Portfolio-Optimization-Project/sample_data_trial_v6/analyst_claude_v6`を新規作成
- **既存フォルダは変更しない**: v4, v5は一切変更しない
- **以降の作業はv6内でのみ実施**

### ❓ 確認事項

**Q1-1**: v6フォルダの初期構成は、v5からコピーして修正する形でよろしいでしょうか？
- [ ] A. v5をコピーして修正
- [ ] B. v5を参考に、ゼロから作成
- [ ] C. その他（具体的に: ________________）

---

## 2. 市場規模の期間変更

### ✅ 理解した内容

- **変更前**: 3年後の市場規模（market_size_after_3y）
- **変更後**: 1年後の市場規模（market_size_after_1y）
- **理由**: 3年後の最適化は複雑すぎる

### ✅ 影響範囲の理解

1. **market_master.csv**:
   - カラム名: `market_size_after_3y` → `market_size_after_1y`
   - 計算式: `market_size_current * (1 + cagr)^3` → `market_size_current * (1 + cagr)^1`

2. **レポート・ドキュメント**:
   - 「3年後の目標状態」→「1年後の目標状態」に変更

3. **競合分析・戦略区分**:
   - 1年後を想定した競合シェア・戦略目標に変更

### ❓ 確認事項

**Q2-1**: 現状のCAGR（年平均成長率）は、そのまま使用してよろしいでしょうか？
- [ ] A. そのまま使用
- [ ] B. 1年後に合わせて調整（具体的に: ________________）

**Q2-2**: 競合分析の「奪取可能シェア」も1年後を想定した値に変更しますか？
- [ ] A. 変更する（1年で奪取可能なシェアに縮小）
- [ ] B. そのまま使用（3年分の奪取可能シェアを1年で達成する積極的な目標）

---

## 3. 代理店モデルの反映

### ✅ 理解した内容

**顧客セグメント分布**:

| 顧客タイプ | セグメント数 | 顧客数 | 割合 |
|----------|------------|--------|------|
| 単一セグメント顧客 | 1 | 6 | 60% |
| 代理店（小規模） | 2 | 3 | 30% |
| 代理店（大規模） | 3 | 1 | 10% |

**具体的なマッピング**:
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

**結果**: 複数セグメント顧客 = 4/10 = 40% ✓

### ✅ データ生成方針の理解

1. **sales_2024.csv**:
   - 上記マッピングに基づき、顧客×製品×拠点×セグメントの組み合わせを生成
   - 同じ製品×拠点×セグメントでも、顧客によって価格が異なる

2. **データ量**:
   - 全組み合わせ（1,600行）ではなく、実際の取引組み合わせのみ（推定300-500行）

### ❓ 確認事項

**Q3-1**: 顧客別の価格差はどのように設定しますか？
- [ ] A. ランダムに±5-10%の変動を加える
- [ ] B. 顧客ランクを定義して、一律の割引率を適用
- [ ] C. v5のsales_2024.csvの価格をベースに、顧客ごとに微調整
- [ ] D. その他（具体的に: ________________）

**Q3-2**: 各製品×拠点×セグメントに対して、何顧客まで割り当てますか？
- [ ] A. 該当するすべての顧客（例: P001_A_industrialに対して、Customer_A, E, G, Jの4顧客）
- [ ] B. ランダムに1-3顧客を割り当て
- [ ] C. その他（具体的に: ________________）

---

## 4. product_master.csv拡張

### ✅ 理解した内容

- **顧客コードを追加**: `customer_code`カラムを追加
- **粒度変更**: 製品×拠点×セグメント（160行） → 製品×拠点×セグメント×顧客（300-500行）

### ✅ 構造の理解

```csv
product_code,plant_code,segment_code,customer_code,unit_cost,unit_price,unit_profit,...
P001,A,industrial,Customer_A,53000,60000,7000,...
P001,A,industrial,Customer_E,53500,61000,7500,...
P001,A,industrial,Customer_G,52800,59000,6200,...
```

### ❓ 確認事項

**Q4-1**: product_masterの生成方法はどちらがよろしいでしょうか？
- [ ] A. sales_2024.csvから直接生成（実績データのみ）
- [ ] B. 基準価格×顧客係数で全組み合わせを生成（将来の拡張性重視）

---

## 5. 戦略係数の見直し

### ✅ 理解した内容

- **現状の問題**: aggressive_expansion: 1.0-1.5は増やしすぎ
- **修正案**: aggressive_expansion: 1.0-1.2（事業部長のビジネス感覚）
- **管理方法**: パラメータは別ファイル管理（config.yaml）

### ❓ 確認事項

**Q5-1**: 他の戦略係数も見直しますか？

| 戦略区分 | 現状（v5） | 提案（v6） | 確認 |
|---------|----------|----------|------|
| aggressive_expansion | 下限1.0 / 上限1.5 | 下限1.0 / 上限1.2 | ✓ 明示的 |
| maintain | 下限0.9 / 上限1.1 | 下限0.9 / 上限1.1 | ？ |
| reduction | 下限0.5 / 上限1.0 | 下限0.5 / 上限1.0 | ？ |
| withdrawal | 下限0.0 / 上限0.7 | 下限0.0 / 上限0.7 | ？ |

事業部長のビジネス感覚で、他の戦略係数も調整しますか？
- [ ] A. aggressive_expansionのみ修正
- [ ] B. 全戦略係数を見直す（具体的な値を提示してください）
- [ ] C. その他

**Q5-2**: 戦略係数の根拠（コメント）はどの程度詳細に記載しますか？
- [ ] A. 簡潔に（例: "事業部長のビジネス感覚に基づく"）
- [ ] B. 詳細に（例: "過去3年のシェア変動実績より、年間20%の拡大は現実的ではない"）

---

## 6. 改善提案の実装範囲

### ✅ 理解した内容

以下の5項目を確実に実装：

| 項目 | 提案内容 | 実装難易度 | 期待効果 |
|------|---------|----------|---------|
| **A-3** | 自動調整機能（段階的な目標引き下げループ） | 中程度（2週間） | 手動調整の手間削減 |
| **A-4** | 最適化失敗時の診断機能（制約充足度チェック） | 中程度（2週間） | デバッグ時間短縮 |
| **A-5** | データフォーマットの不統一対策（スキーマ標準化） | 容易（1週間） | バグ削減、保守性向上 |
| **A-6** | エラー伝播の問題対策（Fail-Fast原則） | 容易（1週間） | エラー早期発見 |
| **A-7** | 設定管理の不統一対策（config.yaml外部化） | 容易（1週間） | パラメータ変更容易 |

### ✅ A-3の実装内容（自動調整機能）

```python
def auto_adjust_targets(target_share, market_data, capacity, max_iterations=5):
    """
    目標シェアを段階的に調整し、実行可能な目標を探索する。
    """
    for i in range(max_iterations):
        is_feasible, message = check_feasibility(target_share, market_data, capacity)

        if is_feasible:
            print(f"✓ 反復 {i}: 実行可能な目標を発見")
            return target_share, True

        print(f"✗ 反復 {i}: 実行不可能 - {message}")
        print(f"  目標シェアを5%引き下げます")

        # 全セグメントの目標を5%引き下げ
        for segment in target_share:
            target_share[segment]['lower'] *= 0.95
            target_share[segment]['upper'] *= 0.95

    print(f"✗ {max_iterations}回の反復でも実行可能な目標が見つかりませんでした")
    return target_share, False
```

### ✅ A-4の実装内容（診断機能）

```python
def diagnose_constraints(target_share, market_data, capacity):
    """
    最適化実行前に制約の充足可能性を診断する。
    """
    total_capacity = sum(capacity.values())
    total_demand_lower = 0

    for segment, targets in target_share.items():
        market_size = market_data[segment]['market_size_after_1y']  # ←1年後に変更
        demand_lower = market_size * targets['lower']
        total_demand_lower += demand_lower

    # チェック1: 総需要下限 vs 総キャパシティ
    if total_demand_lower > total_capacity:
        shortage = total_demand_lower - total_capacity
        issues.append({
            'constraint': '総キャパシティ制約',
            'problem': f'需要下限 {total_demand_lower:,.0f}本 > キャパシティ {total_capacity:,.0f}本',
            'suggestion': f'キャパシティを {shortage:,.0f}本増やすか、目標シェアを {shortage/total_demand_lower*100:.1f}%下げてください'
        })
```

### ✅ A-5の実装内容（スキーマ標準化）

**schema.md**を作成し、以下のカラム名規約を定義：

- `product_code`: 製品コード
- `plant_code`: 拠点コード
- `segment_code`: セグメントコード
- `customer_code`: 顧客コード（新規追加）
- `sales_volume`: 販売数量（`sales_qty`から統一）
- `unit_price`, `unit_cost`, `unit_profit`, `total_profit`

### ✅ A-6の実装内容（Fail-Fast原則）

各ステップの最後にバリデーション関数を追加：

```python
def validate_market_forecast(market_df):
    """
    市場予測データの品質チェック。
    """
    errors = []

    # チェック1: 市場規模が正の値か
    if (market_df['market_size_after_1y'] <= 0).any():
        errors.append("市場規模が0以下のレコードがあります")

    # チェック2: シェアが0〜1の範囲か
    if ((market_df['current_share'] < 0) | (market_df['current_share'] > 1)).any():
        errors.append("現状シェアが0〜1の範囲外です")

    # チェック3: 欠損値がないか
    if market_df.isnull().any().any():
        errors.append("欠損値が存在します")

    if errors:
        raise ValueError("Step 1の出力データに問題があります。")

    print("✓ データ検証: すべてのチェックに合格しました")
```

### ✅ A-7の実装内容（設定ファイル外部化）

**config.yaml**を作成：

```yaml
version: "1.0"

# 拠点キャパシティ（単位: 本）
plant_capacity:
  A: 300000
  B: 204000

# 市場予測
market_forecast:
  target_period: 1  # 年数（1年後の目標）

# 戦略係数（事業部長のビジネス感覚に基づく）
strategy_coefficients:
  aggressive_expansion:
    lower: 1.0
    upper: 1.2  # 従来1.5 → 1.2に修正（年間20%拡大は非現実的）
  maintain:
    lower: 0.9
    upper: 1.1
  reduction:
    lower: 0.5
    upper: 1.0
  withdrawal:
    lower: 0.0
    upper: 0.7
```

### ❓ 確認事項

**Q6-1**: A-3の自動調整機能で、「5%ずつ引き下げ」は適切ですか？
- [ ] A. 5%で問題なし
- [ ] B. もっと小刻みに（例: 2-3%）
- [ ] C. もっと大胆に（例: 10%）

**Q6-2**: A-3の自動調整で、「最大5回反復」は適切ですか？
- [ ] A. 5回で問題なし
- [ ] B. もっと多く（例: 10回）
- [ ] C. もっと少なく（例: 3回）

**Q6-3**: A-5のカラム名統一で、`sales_qty` → `sales_volume`への変更でよろしいでしょうか？
- [ ] A. `sales_volume`に統一
- [ ] B. `sales_qty`のまま（他を合わせる）
- [ ] C. その他（具体的に: ________________）

---

## 7. 実装の優先順位

### ✅ 理解した内容

以下の順序で実装：

1. **基盤整備**:
   - v6フォルダ作成
   - A-7: config.yaml作成
   - A-5: schema.md作成

2. **データ準備**:
   - 代理店モデルに基づくsales_2024.csv再生成
   - product_master.csv拡張（顧客コード追加）

3. **最適化コード修正**:
   - 決定変数を4つ組に変更
   - A-3: 自動調整機能追加
   - A-4: 診断機能追加
   - A-6: Fail-Fast原則導入

4. **検証**:
   - 最適化実行
   - 結果検証
   - レポート作成

### ❓ 確認事項

**Q7-1**: 上記の優先順位でよろしいでしょうか？
- [ ] A. 問題なし
- [ ] B. 変更希望（具体的に: ________________）

---

## 8. 矛盾点のチェック

### ✅ 確認した矛盾点

以下の点について確認しましたが、矛盾はありませんでした：

1. **代理店モデルと4つ組タプル**:
   - 代理店モデル → 顧客×セグメントの組み合わせを限定
   - 4つ組タプル → 製品×拠点×セグメント×顧客で決定変数定義
   - → 両立可能（該当する組み合わせのみ定義）

2. **1年後の目標と戦略係数**:
   - 1年後の目標 → 短期的な目標設定
   - 戦略係数の引き下げ（1.5→1.2） → より現実的な目標
   - → 両立可能（むしろ整合的）

3. **自動調整機能と診断機能**:
   - 自動調整 → 実行不可能な目標を段階的に引き下げ
   - 診断機能 → 事前に問題を検出して警告
   - → 両立可能（診断→自動調整の順で実行）

---

## まとめ: 確認が必要な質問一覧

以下の質問にご回答いただければ、実装計画を確定し、作業を開始いたします。

### 必須の質問

- **Q1-1**: v6の初期構成（v5からコピー or ゼロから作成）
- **Q3-1**: 顧客別価格差の設定方法
- **Q5-1**: 他の戦略係数も見直すか

### 重要な質問

- **Q2-1**: CAGRの使用方法
- **Q2-2**: 奪取可能シェアの期間調整
- **Q3-2**: 各製品×拠点×セグメントに割り当てる顧客数
- **Q4-1**: product_masterの生成方法

### その他の質問

- **Q5-2**: 戦略係数の根拠コメントの詳細度
- **Q6-1**: 自動調整の引き下げ幅（5%）
- **Q6-2**: 自動調整の最大反復回数（5回）
- **Q6-3**: カラム名統一（sales_volume）
- **Q7-1**: 実装の優先順位

---

**以上**
