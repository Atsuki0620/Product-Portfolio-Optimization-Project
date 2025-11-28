# scripts ディレクトリガイド

## 目的
自動化された分析スクリプト群を配置し、データ準備・最適配分・感度分析を再現可能な形で実行する。notebooks/ での手作業検証を経た処理を、定型バッチ処理として実装する。

## ディレクトリの役割
- **notebooks/**: 対話的分析・仮説検証・可視化（一度限りの試行錯誤）
- **scripts/**: 自動化・定型処理・再現性確保（本番運用・CI/CD統合可能）

**推奨ワークフロー**:
1. notebooks/ で手法を検証・確立
2. 確定した処理を scripts/ にモジュール化して実装
3. 本番実行・定期実行は scripts/ を使用

## スクリプト一覧

### データ生成
- **`generate_sample_data.py`**: サンプルデータ（販売・生産・マスタ）を生成
  - 入力: なし（設定はスクリプト内で定義）
  - 出力: `data/raw/sales_*.csv`, `production_*.csv`, `data/master/*.csv`
  - 実行: `python scripts/generate_sample_data.py`
  - 用途: 初回セットアップ、データリセット

### データ処理パイプライン
- **`data_pipeline.py`**: データ読み込み・集計・粗利計算の共通関数群
  - 主要関数:
    - `load_sales_data()`: 販売実績の読み込み
    - `load_production_data()`: 生産実績の読み込み
    - `load_product_master()`: 製品マスタの読み込み
    - `summarize_sales()`: 販売データの集計
    - `summarize_cost()`: 原価計算
    - `derive_segment_demand()`: セグメント別需要算出
  - 用途: 他のスクリプトやnotebooksから import して利用

### データ準備
- **`run_data_prep_once.py`**: Phase1のデータ整備を一括実行
  - 入力: `data/raw/sales_*.csv`, `production_*.csv`, `data/master/*.csv`
  - 出力: `data/intermediate/sales_summary.csv`, `cost_summary.csv`, `margin_matrix.csv`, `segment_demand.csv`
  - 実行: `python scripts/run_data_prep_once.py`
  - 処理内容:
    1. 販売・生産データの読み込み
    2. 製品×拠点×セグメント単位での集計
    3. 単位原価・粗利の算出
    4. セグメント別需要の導出

### 最適配分
- **`run_allocation_once.py`**: Phase2-3の貪欲配賦を実行
  - 入力: `data/intermediate/margin_matrix.csv`, `segment_demand.csv`
  - 出力: `data/intermediate/allocation_results.csv`, `allocation_plant_summary.csv`, `allocation_segment_summary.csv`
  - 実行: `python scripts/run_allocation_once.py`
  - 処理内容:
    1. 製品×拠点×セグメント候補テーブルの構築
    2. 優先度スコア（単位粗利×粗利率）の算出
    3. 貪欲配賦アルゴリズムの実行
    4. 拠点別・セグメント別サマリの作成

- **`allocation_utils.py`**: 貪欲配賦アルゴリズムとサマリ関数を提供
  - 主要クラス:
    - `CapacityConfig`: 拠点キャパシティ設定
  - 主要関数:
    - `build_option_table()`: 候補テーブルの構築
    - `greedy_allocate()`: 貪欲配賦の実行
    - `summarize_by_plant()`: 拠点別サマリ作成
    - `summarize_by_segment()`: セグメント別サマリ作成
  - 用途: `run_allocation_once.py` や notebooks から import

### 感度分析
- **`run_scenarios_once.py`**: Phase4の感度分析を一括実行
  - 入力: `data/intermediate/margin_matrix.csv`, `segment_demand.csv`
  - 出力: `data/intermediate/scenario_results.csv`
  - 実行: `python scripts/run_scenarios_once.py`
  - シナリオ: Base, DemandPlus10, DemandMinus10, CostPlus5, CostMinus5, PricePlus5, PriceMinus5
  - 処理内容:
    1. 各シナリオのパラメータ適用
    2. シナリオ別の貪欲配賦実行
    3. 総粗利・平均単位粗利の集計
    4. ベースラインとの比較

- **`sensitivity_utils.py`**: 需要・原価・単価シナリオを適用する補助関数群
  - 主要関数:
    - `apply_demand_scenario()`: 需要変動シナリオの適用
    - `apply_cost_scenario()`: 原価変動シナリオの適用
    - `apply_price_scenario()`: 単価変動シナリオの適用
    - `run_scenario()`: シナリオ実行のラッパー関数
  - 用途: `run_scenarios_once.py` や notebooks から import

### 指標集計
- **`summarize_metrics.py`**: 分析結果を集約してJSONサマリを作成
  - 入力: `data/intermediate/allocation_*.csv`, `scenario_results.csv`, `segment_demand.csv`
  - 出力: `data/intermediate/summary_metrics.json`
  - 実行: `python scripts/summarize_metrics.py`
  - 集計内容:
    - ベースライン（現状）の総数量・総粗利・上位セグメント
    - 最適化後の総数量・総粗利・上位セグメント
    - 差分（数量・粗利）
    - 感度分析の最良・最悪シナリオ

## 実行順序

### 初回セットアップ
```bash
# 1. サンプルデータ生成
python scripts/generate_sample_data.py

# 2. データ準備
python scripts/run_data_prep_once.py

# 3. 最適配分
python scripts/run_allocation_once.py

# 4. 感度分析
python scripts/run_scenarios_once.py

# 5. 指標集計
python scripts/summarize_metrics.py
```

### 定期更新（本番運用時）
```bash
# 月次更新の想定
# 1. 最新データの配置（販売・生産実績を data/raw/ に追加）
# 2. データ準備の再実行
python scripts/run_data_prep_once.py

# 3. 最適配分の再実行
python scripts/run_allocation_once.py

# 4. 感度分析の再実行
python scripts/run_scenarios_once.py

# 5. 指標集計の再実行
python scripts/summarize_metrics.py
```

## ファイル命名規則

### 入力データ
- 販売実績: `data/raw/sales_YYYY.csv` (YYYYは年度)
- 生産実績: `data/raw/production_YYYY.csv`
- 製品マスタ: `data/master/product_master.csv`
- セグメントマスタ: `data/master/segment_master.csv`

### 中間データ
- `data/intermediate/*.csv`: CSV形式（可読性優先）
- `data/intermediate/*.parquet`: Parquet形式（処理速度・容量優先）

### 成果物
- `data/intermediate/scenario_results.csv`: 感度分析結果
- `data/intermediate/summary_metrics.json`: 主要指標サマリ
- `reports/*.png`: 可視化図表

## 処理時間の目安（20製品規模）

| スクリプト | 実行時間 | 備考 |
|-----------|---------|------|
| `generate_sample_data.py` | 0.5秒 | サンプルデータ生成 |
| `run_data_prep_once.py` | 0.3秒 | 90行の集計 |
| `run_allocation_once.py` | 0.2秒 | 16パターンの配分 |
| `run_scenarios_once.py` | 1.4秒 | 7シナリオの実行 |
| `summarize_metrics.py` | 0.1秒 | JSON出力 |
| **合計** | **約2.5秒** | - |

**本番データ想定（200製品規模）**:
- データ準備: 約3秒
- 最適配分: 約5秒
- 感度分析: 約30秒（7シナリオ）
- **合計**: 約40秒（並列化なし）

## ログとエラーハンドリング

### ログ出力先
- 標準出力: 処理の進捗状況
- `logs/*.log`: 詳細なデバッグ情報（将来実装予定）

### エラー発生時の対応
1. **FileNotFoundError**: データファイルが見つからない
   - 対応: `generate_sample_data.py` を実行してデータを生成

2. **ValueError**: 必須カラムが不足
   - 対応: データファイルのスキーマを確認（`01_data_requirements.md` 参照）

3. **MemoryError**: メモリ不足
   - 対応: Parquet形式の使用、データの分割処理

## 開発ガイドライン

### 新規スクリプトの追加
1. notebooks/ で動作確認済みのコードをベースにする
2. `if __name__ == "__main__":` ブロックで実行部分を分離
3. 関数はモジュールとして import 可能にする
4. docstring を日本語で記載
5. 型ヒントを付与（Python 3.11+）

### コーディング規約
- **命名規則**: snake_case（関数・変数）、PascalCase（クラス）
- **インポート順**: 標準ライブラリ → サードパーティ → ローカルモジュール
- **コメント**: 日本語で記載
- **エラーハンドリング**: 明示的な例外処理を実装

### テスト
- notebooks/ で手動テスト実施
- 将来的には pytest による自動テストを導入予定

## 依存関係

### 必須パッケージ
```
numpy>=1.24
pandas>=2.2
pyarrow>=15.0
```

### オプションパッケージ
```
matplotlib>=3.8  # 可視化（notebooks で使用）
jupyterlab>=4.1  # 対話的分析（notebooks で使用）
```

## トラブルシューティング

### よくある問題

**Q: `ModuleNotFoundError: No module named 'data_pipeline'`**
```bash
# scriptsディレクトリから実行している場合
cd ..  # analyst_claude/ に移動
python scripts/run_data_prep_once.py

# または PYTHONPATH を設定
export PYTHONPATH=/path/to/analyst_claude:$PYTHONPATH
```

**Q: データが更新されない**
```bash
# 中間ファイルを削除して再生成
rm -rf data/intermediate/*.csv
python scripts/run_data_prep_once.py
python scripts/run_allocation_once.py
```

**Q: 本番データで処理が遅い**
- Parquet形式の使用を検討
- データの並列処理を実装
- メモリ使用量の最適化（chunk処理）

## 関連ドキュメント
- [データ要件定義](../01_data_requirements.md)
- [処理フロー設計](../02_processing_flow.md)
- [検証・成果物定義](../03_validation_and_outputs.md)
- [Notebooksガイド](../notebooks/README.md)

---

**作成日**: 2025年11月27日
**最終更新**: 2025年11月28日（analyst_claude版、正規化）
**メンテナンス**: Claude Code
