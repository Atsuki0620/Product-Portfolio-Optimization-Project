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
    min_qty: int = 105
    max_qty: int = 5000


class SampleDataGenerator:
    """project_spec に沿った擬似データを生成するクラス。"""

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
        records: List[Dict] = []
        base_year = min(self.config.years)
        for _, prod in self.products.iterrows():
            allowed_segments = prod["allowed_segments_list"]
            allowed_plants = prod["allowed_plants_list"]
            selected_segments = self._choose_segments(allowed_segments, prod["price_band"])
            base_qty = self._base_qty(prod["price_band"])
            for segment in selected_segments:
                share = self.segment_share.get(segment, 0.08)
                for year in self.config.years:
                    qty = self._sample_qty(base_qty, share, year - base_year)
                    plant = self._choose_plant(allowed_plants)
                    price = self.rng.uniform(prod["unit_price_min"], prod["unit_price_max"])
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
        return pd.DataFrame(records)

    def _choose_segments(self, segments: List[str], price_band: str) -> List[str]:
        prob = 0.8 if price_band == "low" else 0.6
        selected = [seg for seg in segments if self.rng.random() < prob]
        if not selected:
            selected = [self.rng.choice(segments)]
        return selected

    def _base_qty(self, price_band: str) -> int:
        if price_band == "low":
            return int(self.rng.integers(900, 2000))
        return int(self.rng.integers(180, 450))

    def _sample_qty(self, base_qty: int, share: float, year_offset: int) -> int:
        noise = self.rng.uniform(0.7, 1.3)
        segment_factor = 0.7 + share * 1.6
        year_drift = 1 + 0.02 * year_offset * self.rng.uniform(0.8, 1.2)
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

    def generate_production(self, sales_df: pd.DataFrame) -> pd.DataFrame:
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
        grouped["production_cost"] = grouped["unit_cost"] * grouped["production_qty"]
        return grouped[["year", "product_code", "plant", "production_qty", "production_cost"]]

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
    parser = argparse.ArgumentParser(description="サンプルデータ生成スクリプト")
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
    sales = generator.generate_sales()
    production = generator.generate_production(sales)
    generator.write_sales_files(sales)
    generator.write_production_files(production)
    print(f"販売データ: {len(sales)} 行、 生産データ: {len(production)} 行を生成しました。")


if __name__ == "__main__":
    main()
