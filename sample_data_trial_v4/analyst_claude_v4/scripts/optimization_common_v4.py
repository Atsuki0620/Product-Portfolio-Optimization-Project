#!/usr/bin/env python3
"""
Optimization Common Module (v4)

Provides shared preprocessing functions for optimization scripts:
- load_raw_data(): Load sales and master data
- build_parameters(): Build optimization parameters
- validate_sales_constraints(): Validate optimization results
"""

import os
import sys
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd


# Constants
TOTAL_ANNUAL_SALES_QTY_2024 = 504_000
PLANT_A_CAPACITY = 300_000
PLANT_B_CAPACITY = 204_000
SEGMENT_MIX_TOLERANCE = 0.03  # ±3 percentage points


def get_workspace_root() -> Path:
    """Get the workspace root directory."""
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent
    return workspace_root


def load_raw_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load raw sales data and master data.

    Returns:
        Tuple containing:
        - sales_df: Sales data DataFrame
        - product_master: Product master DataFrame
        - segment_master: Segment master DataFrame
    """
    workspace_root = get_workspace_root()
    data_dir = workspace_root / "data"

    # Load sales data
    sales_path = data_dir / "raw" / "sales_2024.csv"
    if not sales_path.exists():
        raise FileNotFoundError(f"Sales data not found: {sales_path}")
    sales_df = pd.read_csv(sales_path)

    # Load master data
    product_master_path = data_dir / "master" / "product_master.csv"
    segment_master_path = data_dir / "master" / "segment_master.csv"

    if not product_master_path.exists():
        raise FileNotFoundError(f"Product master not found: {product_master_path}")
    if not segment_master_path.exists():
        raise FileNotFoundError(f"Segment master not found: {segment_master_path}")

    product_master = pd.read_csv(product_master_path)
    segment_master = pd.read_csv(segment_master_path)

    return sales_df, product_master, segment_master


def build_parameters(sales_df: pd.DataFrame,
                     product_master: pd.DataFrame,
                     segment_master: pd.DataFrame) -> Dict:
    """
    Build optimization parameters from raw data.

    Args:
        sales_df: Sales data DataFrame
        product_master: Product master DataFrame
        segment_master: Segment master DataFrame

    Returns:
        Dictionary containing optimization parameters:
        - total_target: Total sales quantity target (504,000)
        - plant_capacity: Dict with plant capacity limits
        - segment_mix: Dict with target segment sales mix
        - target_margin: Dict with target margin rates by segment
        - demand_max: Dict with maximum demand by (product, plant, segment)
        - unit_profit: Dict with unit profit by (product, plant, segment)
        - combinations: List of all (product, plant, segment) combinations
    """
    # Calculate unit profit for each row
    sales_df['unit_profit'] = sales_df['unit_price'] * sales_df['margin_rate']

    # Build segment mix dictionary
    segment_mix = {}
    target_margin = {}
    for _, row in segment_master.iterrows():
        segment_mix[row['segment_code']] = row['segment_sales_mix']
        target_margin[row['segment_code']] = row['target_margin_rate']

    # Build demand_max and unit_profit dictionaries
    demand_max = {}
    unit_profit = {}
    combinations = []

    for _, row in sales_df.iterrows():
        key = (row['product_code'], row['plant'], row['segment'])
        combinations.append(key)

        # Use current sales_qty as demand_max (can be adjusted if needed)
        # For optimization, we allow up to 2x current demand as upper bound
        demand_max[key] = row['sales_qty'] * 2.0
        unit_profit[key] = row['unit_profit']

    # Build parameters dictionary
    params = {
        'total_target': TOTAL_ANNUAL_SALES_QTY_2024,
        'plant_capacity': {
            'A': PLANT_A_CAPACITY,
            'B': PLANT_B_CAPACITY
        },
        'segment_mix': segment_mix,
        'target_margin': target_margin,
        'demand_max': demand_max,
        'unit_profit': unit_profit,
        'combinations': combinations,
        'tolerance': SEGMENT_MIX_TOLERANCE
    }

    return params


def validate_sales_constraints(opt_df: pd.DataFrame,
                               params: Dict,
                               method_name: str = "Optimization") -> bool:
    """
    Validate optimization results against constraints.

    Args:
        opt_df: DataFrame with optimization results (must have 'opt_sales_qty' column)
        params: Parameters dictionary from build_parameters()
        method_name: Name of optimization method for reporting

    Returns:
        True if all constraints are satisfied, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"{method_name} Result Validation")
    print(f"{'='*60}")

    all_valid = True

    # Total sales quantity
    total_qty = opt_df['opt_sales_qty'].sum()
    target_qty = params['total_target']
    total_valid = abs(total_qty - target_qty) < 1.0

    print(f"\nTotal Sales Quantity:")
    print(f"  Target: {target_qty:,.0f}")
    print(f"  Actual: {total_qty:,.0f}")
    print(f"  Status: {'✓ OK' if total_valid else '✗ NG'}")
    all_valid = all_valid and total_valid

    # Plant capacity
    print(f"\nPlant Capacity:")
    for plant in ['A', 'B']:
        plant_qty = opt_df[opt_df['plant'] == plant]['opt_sales_qty'].sum()
        capacity = params['plant_capacity'][plant]
        plant_valid = plant_qty <= capacity + 1.0  # Allow small tolerance

        print(f"  Plant {plant}:")
        print(f"    Capacity: {capacity:,.0f}")
        print(f"    Actual:   {plant_qty:,.0f}")
        print(f"    Usage:    {plant_qty/capacity*100:.1f}%")
        print(f"    Status:   {'✓ OK' if plant_valid else '✗ NG'}")
        all_valid = all_valid and plant_valid

    # Segment sales mix
    print(f"\nSegment Sales Mix:")
    for segment, target_mix in params['segment_mix'].items():
        segment_qty = opt_df[opt_df['segment'] == segment]['opt_sales_qty'].sum()
        actual_mix = segment_qty / total_qty if total_qty > 0 else 0
        lower_bound = target_mix - params['tolerance']
        upper_bound = target_mix + params['tolerance']
        segment_valid = lower_bound <= actual_mix <= upper_bound

        print(f"  {segment}:")
        print(f"    Target:  {target_mix*100:.1f}% (±3pp)")
        print(f"    Actual:  {actual_mix*100:.1f}%")
        print(f"    Qty:     {segment_qty:,.0f}")
        print(f"    Status:  {'✓ OK' if segment_valid else '✗ NG'}")
        all_valid = all_valid and segment_valid

    # Summary
    print(f"\n{'='*60}")
    print(f"Overall: {'✓ All constraints satisfied' if all_valid else '✗ Some constraints violated'}")
    print(f"{'='*60}\n")

    return all_valid


def calculate_summary_metrics(df: pd.DataFrame, qty_col: str = 'sales_qty') -> Dict:
    """
    Calculate summary metrics for a given quantity column.

    Args:
        df: DataFrame with sales data
        qty_col: Column name for quantity (default: 'sales_qty')

    Returns:
        Dictionary with summary metrics
    """
    # Calculate totals
    total_qty = df[qty_col].sum()
    df['revenue'] = df[qty_col] * df['unit_price']
    df['cost'] = df[qty_col] * df['unit_cost']
    df['profit'] = df['revenue'] - df['cost']

    total_revenue = df['revenue'].sum()
    total_cost = df['cost'].sum()
    total_profit = df['profit'].sum()
    overall_margin = total_profit / total_revenue if total_revenue > 0 else 0

    # Plant breakdown
    plant_summary = df.groupby('plant')[qty_col].sum().to_dict()

    # Segment breakdown
    segment_summary = df.groupby('segment').agg({
        qty_col: 'sum',
        'revenue': 'sum',
        'profit': 'sum'
    })
    segment_summary['margin_rate'] = segment_summary['profit'] / segment_summary['revenue']

    metrics = {
        'total_qty': total_qty,
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'overall_margin': overall_margin,
        'plant_summary': plant_summary,
        'segment_summary': segment_summary
    }

    return metrics


def generate_markdown_report(opt_df: pd.DataFrame,
                            params: Dict,
                            method_name: str,
                            report_path: Path) -> None:
    """
    Generate a Markdown report for optimization results.

    Args:
        opt_df: DataFrame with optimization results
        params: Parameters dictionary
        method_name: Name of optimization method
        report_path: Path to save the report
    """
    metrics = calculate_summary_metrics(opt_df, 'opt_sales_qty')

    # Create report directory if needed
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# {method_name} Optimization Report (2024)\n\n")
        f.write(f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Overall summary
        f.write("## Overall Summary\n\n")
        f.write(f"- **Total Sales Quantity**: {metrics['total_qty']:,.0f} units\n")
        f.write(f"- **Total Revenue**: ¥{metrics['total_revenue']:,.0f}\n")
        f.write(f"- **Total Cost**: ¥{metrics['total_cost']:,.0f}\n")
        f.write(f"- **Total Profit**: ¥{metrics['total_profit']:,.0f}\n")
        f.write(f"- **Overall Margin Rate**: {metrics['overall_margin']*100:.2f}%\n\n")

        # Plant summary
        f.write("## Plant Summary\n\n")
        f.write("| Plant | Sales Quantity | Composition | Capacity | Utilization |\n")
        f.write("|-------|----------------|-------------|----------|-------------|\n")
        for plant in ['A', 'B']:
            qty = metrics['plant_summary'].get(plant, 0)
            composition = qty / metrics['total_qty'] * 100 if metrics['total_qty'] > 0 else 0
            capacity = params['plant_capacity'][plant]
            utilization = qty / capacity * 100 if capacity > 0 else 0
            f.write(f"| {plant} | {qty:,.0f} | {composition:.1f}% | {capacity:,.0f} | {utilization:.1f}% |\n")
        f.write("\n")

        # Segment summary
        f.write("## Segment Summary\n\n")
        f.write("| Segment | Sales Quantity | Composition | Target Mix | Revenue | Profit | Margin Rate | Target Margin |\n")
        f.write("|---------|----------------|-------------|------------|---------|--------|-------------|---------------|\n")

        seg_summary = metrics['segment_summary']
        for segment in params['segment_mix'].keys():
            if segment in seg_summary.index:
                row = seg_summary.loc[segment]
                qty = row['opt_sales_qty']
                composition = qty / metrics['total_qty'] * 100 if metrics['total_qty'] > 0 else 0
                target_mix = params['segment_mix'][segment] * 100
                revenue = row['revenue']
                profit = row['profit']
                margin = row['margin_rate'] * 100
                target_margin = params['target_margin'][segment] * 100

                f.write(f"| {segment} | {qty:,.0f} | {composition:.1f}% | {target_mix:.1f}% | "
                       f"¥{revenue:,.0f} | ¥{profit:,.0f} | {margin:.2f}% | {target_margin:.1f}% |\n")

        f.write("\n")

        # Constraints check
        f.write("## Constraint Validation\n\n")
        f.write("### Total Sales Quantity\n")
        f.write(f"- Target: {params['total_target']:,.0f}\n")
        f.write(f"- Actual: {metrics['total_qty']:,.0f}\n")
        f.write(f"- Difference: {metrics['total_qty'] - params['total_target']:,.0f}\n\n")

        f.write("### Segment Mix Compliance\n")
        for segment, target_mix in params['segment_mix'].items():
            if segment in seg_summary.index:
                qty = seg_summary.loc[segment, 'opt_sales_qty']
                actual_mix = qty / metrics['total_qty'] if metrics['total_qty'] > 0 else 0
                diff = (actual_mix - target_mix) * 100
                f.write(f"- **{segment}**: Target {target_mix*100:.1f}%, "
                       f"Actual {actual_mix*100:.1f}% (Diff: {diff:+.1f}pp)\n")

    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    # Test the module
    print("Loading data...")
    sales_df, product_master, segment_master = load_raw_data()

    print(f"Sales data: {len(sales_df)} rows")
    print(f"Products: {len(product_master)}")
    print(f"Segments: {len(segment_master)}")

    print("\nBuilding parameters...")
    params = build_parameters(sales_df, product_master, segment_master)

    print(f"Total target: {params['total_target']:,}")
    print(f"Plant capacities: {params['plant_capacity']}")
    print(f"Segment mix: {params['segment_mix']}")
    print(f"Combinations: {len(params['combinations'])}")

    print("\nValidating current sales data...")
    # Test validation with current sales_qty as opt_sales_qty
    test_df = sales_df.copy()
    test_df['opt_sales_qty'] = test_df['sales_qty']
    validate_sales_constraints(test_df, params, "Current Sales")
