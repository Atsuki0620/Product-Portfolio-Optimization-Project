#!/usr/bin/env python3
"""
サンプルデータ生成スクリプト v2
Phase2の要件に基づき、以下の修正を実施：
1. 販売単価の現実化（low: 10,000-30,000円、high: 60,000-100,000円）
2. production_csvの構造変更（unit_costとcost_amountを追加）
3. 稼働率90%達成のための数量調整
4. セグメント構成比の厳密化
"""
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
MASTER_DIR = DATA_DIR / "master"


@dataclass
class GeneratorConfig:
    years: List[int]
    seed: int = 42
    min_qty: int = 5000  # 修正3: 105 → 5000
    max_qty: int = 100000  # 修正3: 5000 → 100000


class SampleDataGenerator:
    """project_spec に沿った擬似データを生成するクラス（v2改善版）"""

    def __init__(self, config: GeneratorConfig) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self.products = self._load_products()
        self.segments = self._load_segments()
        self.segment_share = dict(
            zip(self.segments["segment_code"], self.segments["demand_share"])
        )

    def _load_products(self) -> pd.DataFrame:
        path = MASTER_DIR / "product_master.csv"
        if not path.exists():
            raise FileNotFoundError("product_master.csv が存在しません")
        df = pd.read_csv(path)
        df["allowed_plants_list"] = df["allowed_plants"].str.split("|").apply(
            lambda items: [item.strip() for item in items]
        )
        df["allowed_segments_list"] = df["allowed_segments"].str.split("|").apply(
            lambda items: [item.strip() for item in items]
        )
        return df

    def _load_segments(self) -> pd.DataFrame:
        path = MASTER_DIR / "segment_master.csv"
        if not path.exists():
            raise FileNotFoundError("segment_master.csv が存在しません")
        return pd.read_csv(path)

    def generate_sales(self) -> pd.DataFrame:
        """販売データを生成（セグメント構成比の厳密化対応）"""
        records: List[Dict] = []
        base_year = min(self.config.years)

        # 製品ごとの総需要を先に決定
        product_total_demands = {}
        for _, prod in self.products.iterrows():
            base_qty = self._base_qty(prod["price_band"])
            # 製品ごとの総需要を計算（年度とセグメントの期待値）
            avg_year_factor = 1 + 0.10 * (len(self.config.years) - 1) / 2
            num_segments = len(prod["allowed_segments_list"])
            expected_total = base_qty * avg_year_factor * num_segments * len(self.config.years)
            product_total_demands[prod["product_code"]] = expected_total

        for _, prod in self.products.iterrows():
            allowed_segments = prod["allowed_segments_list"]
            allowed_plants = prod["allowed_plants_list"]

            # 修正4: セグメント選択確率の引き上げ（95% / 85%）
            selected_segments = self._choose_segments(allowed_segments, prod["price_band"])

            base_qty = self._base_qty(prod["price_band"])

            for segment in selected_segments:
                share = self.segment_share.get(segment, 0.08)
                for year in self.config.years:
                    qty = self._sample_qty(base_qty, share, year - base_year)
                    plant = self._choose_plant(allowed_plants)

                    # 修正1: 販売単価の現実化
                    price = self._generate_realistic_price(prod["price_band"])

                    records.append(
                        {
                            "year": year,
                            "product_code": prod["product_code"],
                            "plant": plant,
                            "segment": segment,
                            "sales_qty": int(qty),
                            "sales_amount": round(qty * price, 2),
                            "unit_price": round(price, 2),
                            "customer_name": f"{segment.upper()}-C{self.rng.integers(1, 6)}",
                        }
                    )

        sales_df = pd.DataFrame(records)

        # 修正4: セグメント構成比の事後調整
        sales_df = self._adjust_segment_composition(sales_df)

        return sales_df

    def _generate_realistic_price(self, price_band: str) -> float:
        """
        修正1: 販売単価の現実化
        - 低価格品（low）: 10,000〜30,000円
        - 高価格品（high）: 60,000〜100,000円
        """
        if price_band == "low":
            return float(self.rng.integers(10000, 30001))
        else:  # high
            return float(self.rng.integers(60000, 100001))

    def _choose_segments(self, segments: List[str], price_band: str) -> List[str]:
        """
        修正4: セグメント選択確率の引き上げ
        - 低価格: 95%（従来80%）
        - 高価格: 85%（従来60%）
        """
        prob = 0.95 if price_band == "low" else 0.85
        selected = [seg for seg in segments if self.rng.random() < prob]
        if not selected:
            selected = [self.rng.choice(segments)]
        return selected

    def _base_qty(self, price_band: str) -> int:
        """
        修正3: ベース数量の調整（90%稼働率達成のため）
        - 低価格: 10,000〜15,000（従来900〜2,000）
        - 高価格: 5,000〜7,500（従来180〜450）
        """
        if price_band == "low":
            return int(self.rng.integers(10000, 15001))
        return int(self.rng.integers(5000, 7501))

    def _sample_qty(self, base_qty: int, share: float, year_offset: int) -> int:
        """
        修正3: 年度成長率の強化
        - year_drift: 0.10（従来0.02）
        """
        noise = self.rng.uniform(0.7, 1.3)
        segment_factor = 0.7 + share * 1.6
        year_drift = 1 + 0.10 * year_offset * self.rng.uniform(0.8, 1.2)  # 0.02 → 0.10
        qty = base_qty * segment_factor * noise * year_drift
        qty = max(self.config.min_qty, min(self.config.max_qty, qty))
        return int(round(qty))

    def _choose_plant(self, plants: List[str]) -> str:
        if len(plants) == 1:
            return plants[0]
        if set(plants) == {"A", "B"}:
            weights = np.array([0.55 if plant == "A" else 0.45 for plant in plants])
            weights = weights / weights.sum()
            return str(self.rng.choice(plants, p=weights))
        return str(self.rng.choice(plants))

    def _adjust_segment_composition(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """
        修正4: セグメント構成比の事後調整
        理論構成比（segment_master.csv）に合わせて数量をスケーリング
        目標: 差異を5%ポイント以内に収める
        """
        total_qty = sales_df['sales_qty'].sum()

        # 現在のセグメント別構成比
        current_share = sales_df.groupby('segment')['sales_qty'].sum() / total_qty

        # 理論構成比との差異を計算
        adjustments = {}
        for segment, theoretical_share in self.segment_share.items():
            if segment in current_share.index:
                actual_share = current_share[segment]
                # 調整係数を計算（差異が大きい場合のみ調整）
                diff = theoretical_share - actual_share
                if abs(diff) > 0.05:  # 5%ポイント以上の差異がある場合
                    adjustment_factor = theoretical_share / actual_share
                    # 極端な調整を避ける（0.8〜1.2倍の範囲内）
                    adjustment_factor = max(0.8, min(1.2, adjustment_factor))
                    adjustments[segment] = adjustment_factor
                else:
                    adjustments[segment] = 1.0
            else:
                adjustments[segment] = 1.0

        # 調整を適用
        for segment, factor in adjustments.items():
            mask = sales_df['segment'] == segment
            sales_df.loc[mask, 'sales_qty'] = (sales_df.loc[mask, 'sales_qty'] * factor).round().astype(int)
            sales_df.loc[mask, 'sales_amount'] = (sales_df.loc[mask, 'sales_qty'] * sales_df.loc[mask, 'unit_price']).round(2)

        return sales_df

    def generate_production(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """
        修正2: production_csvの構造変更
        - unit_cost と cost_amount の両方を出力
        """
        grouped = (
            sales_df.groupby(
                ["year", "product_code", "plant"], as_index=False
            )[["sales_qty", "sales_amount"]]
            .sum()
        )
        grouped["avg_price"] = grouped["sales_amount"] / grouped["sales_qty"].clip(lower=1)
        grouped = grouped.merge(
            self.products[["product_code", "price_band"]], on="product_code", how="left"
        )
        qty_multiplier = self.rng.uniform(1.00, 1.05, size=len(grouped))
        grouped["production_qty"] = (grouped["sales_qty"] * qty_multiplier).round().astype(int)
        grouped["unit_cost"] = grouped.apply(self._calc_unit_cost, axis=1)

        # 修正2: cost_amount を追加（production_cost から改名）
        grouped["cost_amount"] = grouped["unit_cost"] * grouped["production_qty"]

        # 修正2: unit_cost と cost_amount の両方を出力
        return grouped[["year", "product_code", "plant", "production_qty", "unit_cost", "cost_amount"]]

    def _calc_unit_cost(self, row: pd.Series) -> float:
        if row["price_band"] == "low":
            ratio = self.rng.uniform(0.45, 0.60)
        else:
            ratio = self.rng.uniform(0.50, 0.65)
        if row["plant"] == "B":
            ratio *= 1.05
        return float(row["avg_price"] * ratio)

    def write_sales_files(self, sales_df: pd.DataFrame) -> None:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        for year in self.config.years:
            path = RAW_DIR / f"sales_{year}.csv"
            sales_df[sales_df["year"] == year].to_csv(path, index=False)

    def write_production_files(self, prod_df: pd.DataFrame) -> None:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        for year in self.config.years:
            path = RAW_DIR / f"production_{year}.csv"
            prod_df[prod_df["year"] == year].to_csv(path, index=False)


def parse_args() -> GeneratorConfig:
    parser = argparse.ArgumentParser(description="サンプルデータ生成スクリプト v2")
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=[2022, 2023, 2024],
        help="生成対象の年度リスト",
    )
    parser.add_argument("--seed", type=int, default=42, help="乱数シード")
    args = parser.parse_args()
    return GeneratorConfig(years=args.years, seed=args.seed)


def main() -> None:
    config = parse_args()
    generator = SampleDataGenerator(config)

    print("=" * 80)
    print("サンプルデータ生成 v2")
    print("=" * 80)
    print("\n【修正内容】")
    print("1. 販売単価の現実化: low=10,000-30,000円、high=60,000-100,000円")
    print("2. production_csvの構造変更: unit_cost + cost_amount を出力")
    print("3. 稼働率90%達成: min_qty=5,000、max_qty=100,000、base_qty大幅引き上げ")
    print("4. セグメント構成比の厳密化: 選択確率95%/85%、事後調整実施")
    print()

    print("販売データを生成中...")
    sales = generator.generate_sales()

    print("生産データを生成中...")
    production = generator.generate_production(sales)

    print("ファイルに書き出し中...")
    generator.write_sales_files(sales)
    generator.write_production_files(production)

    print(f"\n✓ 販売データ: {len(sales):,} 行")
    print(f"✓ 生産データ: {len(production):,} 行")

    # 統計情報を表示
    print("\n【統計情報】")
    print(f"総販売数量: {sales['sales_qty'].sum():,} 本")
    print(f"総販売金額: ¥{sales['sales_amount'].sum():,.2f}")
    print(f"平均単価: ¥{sales['unit_price'].mean():,.2f}")

    # セグメント構成比を表示
    print("\n【セグメント構成比】")
    total_qty = sales['sales_qty'].sum()
    segment_stats = sales.groupby('segment')['sales_qty'].sum().sort_values(ascending=False)
    for segment, qty in segment_stats.items():
        share = qty / total_qty
        theoretical = generator.segment_share.get(segment, 0)
        diff = abs(share - theoretical) * 100
        print(f"{segment:20s}: {share*100:5.2f}% (理論値: {theoretical*100:5.2f}%, 差異: {diff:4.2f}pt)")

    print("\n" + "=" * 80)
    print("生成完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
