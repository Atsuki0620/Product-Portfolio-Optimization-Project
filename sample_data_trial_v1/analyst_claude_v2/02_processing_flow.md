# 02_processing_flow

## Phase1: 過去データ整備
1. **販売集計** (`sales_summary`)
   - 入力: D1.
   - 処理: 年度×製品×拠点×セグメントで `sales_qty`, `sales_amount` を集計し、`avg_price = sales_amount / sales_qty` を計算。
   - 検証: 集計数量合計と元データの差分が 1 本以内か確認。
2. **原価整備** (`cost_summary`)
   - 入力: D2.
   - 処理: 年度×製品×拠点で `unit_cost = production_cost / production_qty` を算出し、3年平均を `unit_cost_avg` として保持。
   - 拠点Bの追加コストを反映するため、`unit_cost_adj = unit_cost_avg * (1 + plant_cost_uplift)`。
3. **粗利計算** (`margin_matrix`)
   - 結合: `sales_summary` と `cost_summary` を製品×拠点で結合し、`unit_margin = avg_price - unit_cost_adj`、`margin_rate = unit_margin / avg_price` を計算。
   - フィルタ: `unit_margin > 0` のみ残し、値が負の組み合わせは実装段階で警告ログを出力。
4. **需要・受注可能数推計**
   - `demand_segment = mean(sales_qty)` をセグメント別に計算。
   - `alloc_cap_product_segment = mean(sales_qty)` を製品×セグメント単位の上限制約として保存。

## Phase2: 組み合わせランク付け
1. **スコア算出**
   - テーブル: `option_rank`（製品×拠点×セグメント）。
   - 指標: `unit_margin`, `margin_rate`, `avg_price`, 過去販売実績の有無フラグ `has_history`。
   - ソートキー: `unit_margin` 降順 → `margin_rate` 降順。
2. **利用可能性チェック**
   - `allowed_plants`, `allowed_segments` を用い、不可な組み合わせを除外。
   - 過去3年実績 `has_history=0` でも、仕様上許可されている場合は別タグ `new_combo` として残し、後段で優先度を下げる。

## Phase3: 最適配分アルゴリズム
1. **拠点別残キャパ初期化**
   - `remaining_capacity[A] = 528000 * capacity_utilization_target`、`remaining_capacity[B] = 528000 * capacity_utilization_target`。
   - 初期ターゲットは現状 90% (=475,200) をベースにし、改善案で 100% フル稼働も比較する。
2. **貪欲割当ロジック**
   - 疑似コード:
     ```python
     for plant in ['A', 'B']:
         for row in option_rank_sorted:
             if row.plant != plant:
                 continue
             alloc_cap = min(row.alloc_cap_product_segment,
                             demand_segment[row.segment],
                             remaining_capacity[plant])
             if alloc_cap <= 0:
                 continue
             assign(row, alloc_cap)
             remaining_capacity[plant] -= alloc_cap
             demand_segment[row.segment] -= alloc_cap
     ```
   - `assign` 関数では `allocated_qty`, `allocated_margin = alloc_cap * unit_margin` を記録する。
3. **結果集計**
   - 拠点別粗利: `total_margin_by_plant`。
   - セグメント別構成比: `allocated_qty_segment / sum(allocated_qty)`。
   - 現状対比用に、過去平均構成比を別テーブル `current_mix` で保持し、差分 `delta_mix`, `delta_margin` を算出。

## ロギング・検証
- 各フェーズ完了時に `logs/phaseX_summary.json` を生成し、合計数量・粗利・キャパ残を記録予定。
- エラー条件: 残キャパ < 0、需要残 > 0 でキャパ未使用等を警告。
- notebooks ではチェックセルを作成し、`assert abs(original_qty - aggregated_qty) <= 1` などの簡易テストを入れる。
