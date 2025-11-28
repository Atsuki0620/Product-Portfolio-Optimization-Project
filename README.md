# Product-Portfolio-Optimization-Project

製品ポートフォリオの最適化による粗利最大化を実現するデータ分析プロジェクト。

## プロジェクト概要

### 背景・目的
- **依頼者**: 事業部長
- **課題**: どのセグメント（業界区分）に注力すべきか不明確
- **目的**: 粗利を最大化するための生産製品構成比率を分析し、最適解を導出
- **分析期間**: 過去3年分の実績データ（2022-2024年）

### 分析規模
- **現在（サンプル段階）**: 20製品 × 8セグメント × 2拠点
- **最終目標**: 200製品規模への拡張

### 主要成果物
- 20製品×8セグメント×2拠点のサンプルデータ分析完了
- 貪欲配賦アルゴリズムと感度分析の実装
- 最適化手法の確立と本番適用準備完了

## ワークスペース構成

### analyst_codex/ - オリジナル作業領域
初期の分析作業とドキュメントを保持。**変更しないオリジナル版**として保存されています。

### analyst_claude/ - Claude Code改善版（推奨）
Claude Codeによる改善版の作業領域。以下の改善が含まれます：
- ドキュメントの正規化（パッチ形式から完全なMarkdownへ変換）
- レポートの詳細化（phase1_summary.md: 99行 → 942行に拡充）
- 実行可能性の確保（独立して動作可能）

**詳細は** [`sample_data_trial_v1/analyst_claude/README.md`](sample_data_trial_v1/analyst_claude/README.md) **を参照してください。**

## クイックスタート

### 1. 環境構築

#### 前提条件
- Python 3.11以上
- Git
- 約500MBの空きディスク容量

#### セットアップ手順

```bash
# リポジトリのクローン
git clone <repository-url>
cd Product-Portfolio-Optimization-Project

# 仮想環境の作成（推奨）
python -m venv .venv

# 仮想環境の有効化
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

#### requirements.txt に含まれるパッケージ
- `numpy>=1.24` - 数値計算
- `pandas>=2.2` - データ処理
- `pyarrow>=15.0` - Parquet形式サポート
- `matplotlib>=3.8` - 可視化
- `jupyterlab>=4.1` - 対話的分析

### 2. サンプルデータでの動作確認（analyst_claude/を使用）

```bash
# データ準備
cd sample_data_trial_v1/analyst_claude
python scripts/run_data_prep_once.py

# 最適配分の実行
python scripts/run_allocation_once.py

# 感度分析の実行
python scripts/run_scenarios_once.py

# Jupyter Labでの分析
jupyter lab
```

### 3. 仮想環境の終了

```bash
deactivate
```

## ディレクトリ構造

```
Product-Portfolio-Optimization-Project/
├── README.md                          # 本ファイル
├── AGENTS.md                          # 作業方針
├── requirements.txt                   # 依存パッケージ
├── analyst_codex/                     # 分析作業領域（予備）
└── sample_data_trial_v1/              # サンプルデータトライアル
    ├── project_spec.md                # プロジェクト仕様書
    ├── analyst_codex/                 # オリジナル作業ディレクトリ
    │   └── （元の分析内容、変更しない）
    └── analyst_claude/                # Claude Code改善版（推奨）
        ├── README.md                  # analyst_claude ガイド
        ├── data/                      # データディレクトリ
        │   ├── raw/                   # 販売・生産実績（2022-2024）
        │   ├── master/                # 製品・セグメントマスタ
        │   └── intermediate/          # 集計・最適化結果
        ├── scripts/                   # 自動化スクリプト
        │   ├── README.md              # スクリプトガイド（257行、正規化版）
        │   ├── generate_sample_data.py
        │   ├── data_pipeline.py
        │   ├── allocation_utils.py
        │   ├── sensitivity_utils.py
        │   ├── run_data_prep_once.py
        │   ├── run_allocation_once.py
        │   ├── run_scenarios_once.py
        │   └── summarize_metrics.py
        ├── notebooks/                 # Jupyter分析ノート
        │   ├── 01_data_prep.ipynb
        │   ├── 02_allocation.ipynb
        │   ├── 03_sensitivity.ipynb
        │   └── 04_reporting.ipynb
        ├── reports/                   # 成果物
        │   ├── phase1_summary.md      # 詳細分析レポート（942行、完全版）
        │   └── img_*.png              # 可視化図表
        └── ドキュメント群/
            ├── 00_setup_notes.md
            ├── 01_data_requirements.md
            ├── 02_processing_flow.md
            ├── 03_validation_and_outputs.md（267行、正規化版）
            ├── 04_sample_data_blueprint.md
            └── 05_report_outline.md
```

## ドキュメント

### プロジェクト仕様
- [プロジェクト仕様書](sample_data_trial_v1/project_spec.md) - プロジェクト全体の要件定義

### analyst_claude/ の主要ドキュメント（推奨）
1. [analyst_claude ガイド](sample_data_trial_v1/analyst_claude/README.md) - 改善版の概要
2. [Phase1詳細レポート](sample_data_trial_v1/analyst_claude/reports/phase1_summary.md) - 初回トライアルの詳細分析結果（942行、完全版）
3. [検証・成果物定義](sample_data_trial_v1/analyst_claude/03_validation_and_outputs.md) - Phase4検証フレームワーク（267行、正規化版）
4. [スクリプトガイド](sample_data_trial_v1/analyst_claude/scripts/README.md) - 全スクリプトの詳細ドキュメント（257行、正規化版）

### analyst_codex/ の元ドキュメント
- [元の分析手順](sample_data_trial_v1/analyst_codex/README.md) - オリジナル版

## 運用ルール

### 作業方針
- **analyst_codex/**: オリジナルの作業内容を保持（変更しない）
- **analyst_claude/**: Claude Codeによる改善作業（変更可能）
- 各担当者は自分専用のサブフォルダ配下で作業してください（例: `analyst_a/`）
- コードやドキュメントの追加・修正は日本語で記載してください
- リポジトリ直下のファイルを編集する場合は、内容を最小限に留め、他担当者の領域に影響を与えないようにしてください
- テストや実行コマンドを行った場合は、結果を記録してください

詳細は [AGENTS.md](AGENTS.md) を参照してください。

## 分析の概要

### 8つのセグメント（業界区分）
1. 自動車業界 (30%) - 主力セグメント
2. 電機・電子業界 (18%) - 高粗利
3. 建設・インフラ業界 (15%) - 低粗利・大量
4. 医療・ヘルスケア業界 (5%) - 高粗利・小規模
5. 食品・飲料業界 (10%) - 中粗利
6. 化学・素材業界 (8%) - 低粗利
7. 一般消費財業界 (9%) - 低粗利
8. その他産業 (5%) - ニッチ

### 生産体制
- **拠点A（国内）**: 年間528,000本、原価基準
- **拠点B（海外）**: 年間528,000本、原価+5%高
- **現状稼働率**: 90%

### 分析手法
1. **データ整備**: 販売・生産・マスタデータの統合と検証
2. **粗利計算**: 製品×拠点×セグメント単位での粗利算出
3. **貪欲配賦**: 単位粗利が高い順に最適配分
4. **感度分析**: 需要±10%、原価±5%、価格±5%のシナリオ評価

## 主な分析結果

### サンプルデータでの発見
- 年間需要: 6,732本（拠点能力の0.7%）
- 総粗利: 10.5百万円
- 価格変動が最大の影響要因（±5%で粗利±11.5%）
- キャパシティ余剰が大きく、本番データでは制約が顕在化する見込み

### 推奨アクション
1. 価格改定戦略（医療・電機セグメント +5〜7%）
2. 拠点Bコスト削減（-3%目標）
3. 高粗利セグメントの営業パイプライン拡大

## 次のステップ

### 短期（3ヶ月以内）
- 本番データ（200製品）の抽出とパイプライン構築
- 計算パフォーマンスの検証
- 営業/製造ワークショップの開催

### 中期（6ヶ月以内）
- 価格改定プロジェクト（期待効果: +0.97M）
- 拠点Bコスト削減プロジェクト（期待効果: +0.41M）
- レポーティング自動化

### 長期（12ヶ月以内）
- 需要予測モデルの高度化（時系列分析、機械学習）
- リアルタイム最適化システムの構築

## トラブルシューティング

### よくある問題

**Q: JupyterLabが起動しない**
```bash
# バージョン確認
jupyter lab --version

# 再インストール
pip uninstall jupyterlab
pip install jupyterlab>=4.1
```

**Q: データファイルが見つからない**
```bash
# サンプルデータの生成
cd sample_data_trial_v1/analyst_claude
python scripts/generate_sample_data.py
```

**Q: Python 3.13で動作確認済みですか？**
- はい、Python 3.13.5での動作を確認しています（analyst_codex/setup_log.md参照）

## ライセンス・貢献

このプロジェクトは社内利用を想定しています。外部への公開・配布は事業部長の承認が必要です。

## 連絡先

- プロジェクトオーナー: 事業部長
- 技術担当: データ分析チーム
- 質問・提案: 各担当者のサブフォルダ内でissue管理

---

**最終更新**: 2025年11月28日
**バージョン**: 3.0（analyst_claude版追加）
