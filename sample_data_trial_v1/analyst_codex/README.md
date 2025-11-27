*** Begin Patch
*** Update File: sample_data_trial_v1\analyst_codex\README.md
@@
 - `02_processing_flow.md`: Phase1?3 におけるデータ整形と最適化処理フロー設計。
 - `03_validation_and_outputs.md`: Phase4/8 の検証方針・感度分析・成果物テンプレ。
 - `notebooks/` (予定): 実装用 Jupyter Notebook もしくはスクリプトを配置予定。
+- `scripts/`: `run_data_prep_once.py`, `run_allocation_once.py`, `run_scenarios_once.py` など自動実行用スクリプト郡。
@@
-2. notebooks ディレクトリを作成し、データ準備ノート (`01_data_prep.ipynb` など) を順次追加する。
-3. 粗利最大化ロジックと貪欲配賦アルゴリズムを Python で実装し、検証結果を 03 ドキュメントに反映する。
+2. notebooks ディレクトリを作成し、データ準備ノート (`01_data_prep.ipynb` など) を順次追加する。
+3. 粗利最大化ロジックと貪欲配賦アルゴリズムを Python で実装し、`scripts/run_allocation_once.py` / `scripts/run_scenarios_once.py` で成果物CSVを自動生成、検証結果を 03 ドキュメントに反映する。
*** End Patch
