# 05_report_outline

## レポート方針
- 本文は日本語で記述し、図表・グラフのラベルのみ英語表記にする。
- sample_data_trial_v1/project_spec.md の要求（概要・背景目的・アウトプット）をすべて1ページで把握できる構成にする。
- 各セクションは以下の6ブロックで構成する。

## セクション構成
1. **Project Overview**
   - 依頼背景（ポートフォリオ最適化の必要性、対象データ範囲）
   - 使用データ（20製品・8セグメント・2拠点・過去3年）
   - ステークホルダー（事業部長、営業/製造チーム）
2. **Data Preparation (Phase1)**
   - 販売/生産データ処理手順の要約
   - グラフ: Flowchart (English labels) to show pipeline (Ingest → Aggregate → Costing → Margin Matrix)
3. **Optimization & Allocation (Phase2-3)**
   - 貪欲配賦アルゴリズムの説明（英語ラベル図：Optimized Segment Mix）
   - 指標: total_qty, total_margin, plant capacity usage
4. **Validation & Execution Feasibility (Phase4 / Step11)**
   - 現状 vs 最適の差分表（日本語本文で解説）
   - チェックリスト（営業/製造/リスク）
5. **Sensitivity Insights (Step12)**
   - グラフ: Scenario Impact on Margin（棒グラフを英語ラベルで）
   - アクション: 価格/コスト/需要変動時の勧告
6. **Next Actions**
   - 本番規模への拡張
   - データ刷新・業務連携計画

## 主要指標と図表
|セクション|図表|英語ラベル例|
|--|--|--|
|Data Preparation|Flowchart|"Data Flow", "Margin Matrix"
|Optimization|Bar chart (segment share)|"Optimized Segment Mix"
|Validation|Table (no図)|—
|Sensitivity|Bar chart|"Scenario Impact on Total Margin"

## 作業メモ
- 図版生成は notebooks/04_reporting.ipynb（新規）で実行予定。
- 1ページレポートは `reports/phase1_summary.md` としてMarkdownで作成し、必要ならPowerPoint化。
