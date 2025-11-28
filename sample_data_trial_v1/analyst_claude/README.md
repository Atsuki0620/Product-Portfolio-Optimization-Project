# analyst_claude ワークスペース

このディレクトリは Claude Code による分析作業用の専用ワークスペースです。

## 目的
- Claude Code による自動化・改善作業を集約
- `analyst_codex/` の元の状態を保持しながら、並行して改善版を開発
- モジュール・パス・ドキュメントを整備し、独立して実行可能な環境を構築

## analyst_codex との違い
- **analyst_codex**: オリジナルの作業内容（変更しない）
- **analyst_claude**: Claude Code による改善版（このディレクトリ）

## ディレクトリ構造

```
analyst_claude/
├── README.md                     # 本ファイル
├── 00_setup_notes.md             # セットアップメモ
├── 01_data_requirements.md       # データ要件定義
├── 02_processing_flow.md         # 処理フロー設計
├── 03_validation_and_outputs.md  # 検証・成果物定義（正規化版）
├── 04_sample_data_blueprint.md   # サンプルデータ仕様
├── 05_report_outline.md          # レポート構成
├── data/                         # データディレクトリ
│   ├── raw/                      # 販売・生産実績
│   ├── master/                   # 製品・セグメントマスタ
│   └── intermediate/             # 集計・最適化結果
├── scripts/                      # 自動化スクリプト
│   ├── README.md                 # スクリプトガイド（正規化版）
│   ├── generate_sample_data.py
│   ├── data_pipeline.py
│   ├── allocation_utils.py
│   ├── sensitivity_utils.py
│   ├── run_data_prep_once.py
│   ├── run_allocation_once.py
│   ├── run_scenarios_once.py
│   └── summarize_metrics.py
├── notebooks/                    # Jupyter分析ノート
│   ├── 01_data_prep.ipynb
│   ├── 02_allocation.ipynb
│   ├── 03_sensitivity.ipynb
│   └── 04_reporting.ipynb
└── reports/                      # 成果物
    ├── phase1_summary.md         # Phase1詳細レポート（942行完全版）
    └── img_*.png                 # 可視化図表
```

## 主な改善点

### 1. ドキュメントの正規化
- **03_validation_and_outputs.md**: パッチ形式から完全なMarkdownに変換（267行）
- **scripts/README.md**: パッチ形式から完全なMarkdownに変換（257行）

### 2. レポートの詳細化
- **reports/phase1_summary.md**: 99行から942行に拡充（9.5倍）
  - エグゼクティブサマリー追加
  - データ整備プロセスの詳細化
  - 粗利マトリクスの統計分析
  - 貪欲配賦アルゴリズムの完全定式化
  - 感度分析の深掘り
  - 実務展開ロードマップ

### 3. 実行可能性の確保
- モジュールパスの修正（必要に応じて）
- すべてのスクリプトが `analyst_claude/` 配下で実行可能

## クイックスタート

### 1. 環境構築
```bash
# プロジェクトルートで実行
cd sample_data_trial_v1/analyst_claude
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r ../../requirements.txt
```

### 2. サンプルデータ生成と分析実行
```bash
# データ生成
python scripts/generate_sample_data.py

# データ準備
python scripts/run_data_prep_once.py

# 最適配分
python scripts/run_allocation_once.py

# 感度分析
python scripts/run_scenarios_once.py

# 指標集計
python scripts/summarize_metrics.py
```

### 3. Jupyter Labでの分析
```bash
jupyter lab
# notebooks/01_data_prep.ipynb から順に実行
```

## 主要成果物へのリンク

- [Phase1詳細レポート](reports/phase1_summary.md) - 初回トライアルの完全版分析結果
- [検証・成果物定義](03_validation_and_outputs.md) - Phase4検証フレームワーク
- [スクリプトガイド](scripts/README.md) - 全スクリプトの詳細ドキュメント

## 注意事項
- このディレクトリの変更は `analyst_codex/` に影響しません
- 本番適用時は `analyst_codex/` と比較検証を行ってください
- データファイル（`data/` 配下）は共通ですが、モジュールパスが異なる場合があります

---

**作成日**: 2025年11月28日
**管理者**: Claude Code
**元ディレクトリ**: sample_data_trial_v1/analyst_codex/
