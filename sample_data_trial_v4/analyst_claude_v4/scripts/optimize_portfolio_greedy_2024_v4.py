#!/usr/bin/env python3
"""
Greedy Portfolio Optimization (2024 v4)

This script implements a greedy heuristic approach to optimize the product portfolio.
The algorithm prioritizes combinations with higher unit profit while satisfying constraints.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# Import common functions
import optimization_common_v4 as opt_common


def run_greedy_optimization(sales_df: pd.DataFrame, params: Dict) -> pd.DataFrame:
    """
    Execute greedy optimization algorithm.

    Algorithm approach (two-phase):
    Phase 1: Meet segment lower bounds with highest profit items per segment
    Phase 2: Fill remaining capacity with highest profit items respecting all constraints

    Args:
        sales_df: Sales data DataFrame
        params: Parameters dictionary from optimization_common_v4

    Returns:
        DataFrame with optimized sales quantities
    """
    print("\n" + "="*60)
    print("Greedy Optimization Algorithm (Two-Phase)")
    print("="*60)

    # Create working DataFrame with unit profit
    work_df = sales_df.copy()
    work_df['unit_profit'] = work_df['unit_price'] * work_df['margin_rate']
    work_df['opt_sales_qty'] = 0.0

    # Tracking variables
    total_allocated = 0.0
    plant_allocated = {'A': 0.0, 'B': 0.0}
    segment_allocated = {seg: 0.0 for seg in params['segment_mix'].keys()}

    # Target quantities for segments
    total_target = params['total_target']
    segment_targets = {seg: total_target * mix for seg, mix in params['segment_mix'].items()}
    segment_lower = {seg: total_target * (mix - params['tolerance'])
                    for seg, mix in params['segment_mix'].items()}
    segment_upper = {seg: total_target * (mix + params['tolerance'])
                    for seg, mix in params['segment_mix'].items()}

    print(f"\nPhase 1: Meeting segment lower bounds...")
    print(f"Segment targets: {segment_targets}")

    # Phase 1: Ensure each segment meets its lower bound
    for segment in params['segment_mix'].keys():
        target_qty = segment_targets[segment]

        # Get all rows for this segment, sorted by unit profit
        segment_rows = work_df[work_df['segment'] == segment].copy()
        segment_rows = segment_rows.sort_values('unit_profit', ascending=False)

        allocated_for_segment = 0.0

        for idx, row in segment_rows.iterrows():
            if allocated_for_segment >= target_qty:
                break

            plant = row['plant']
            max_demand = row['sales_qty'] * 2.0

            # Calculate how much we can allocate
            remaining_total = total_target - total_allocated
            remaining_plant = params['plant_capacity'][plant] - plant_allocated[plant]
            needed_for_segment = target_qty - allocated_for_segment

            allocate_qty = min(max_demand, remaining_total, remaining_plant, needed_for_segment)

            if allocate_qty > 0.5:
                work_df.at[idx, 'opt_sales_qty'] = allocate_qty
                total_allocated += allocate_qty
                plant_allocated[plant] += allocate_qty
                segment_allocated[segment] += allocate_qty
                allocated_for_segment += allocate_qty

        print(f"  {segment}: allocated {allocated_for_segment:,.0f} / target {target_qty:,.0f}")

    print(f"\nAfter Phase 1: {total_allocated:,.0f} / {total_target:,.0f} allocated")

    # Phase 2: Fill remaining capacity with highest profit items
    remaining = total_target - total_allocated

    if remaining > 0.5:
        print(f"\nPhase 2: Filling remaining {remaining:,.0f} units with highest profit items...")

        # Sort all rows by unit profit
        sorted_df = work_df.sort_values('unit_profit', ascending=False)

        for idx, row in sorted_df.iterrows():
            if remaining < 0.5:
                break

            plant = row['plant']
            segment = row['segment']
            current_qty = work_df.at[idx, 'opt_sales_qty']
            max_demand = row['sales_qty'] * 2.0

            # Calculate how much more we can allocate
            can_add_demand = max_demand - current_qty
            can_add_plant = params['plant_capacity'][plant] - plant_allocated[plant]
            can_add_segment = segment_upper[segment] - segment_allocated[segment]

            can_add = min(can_add_demand, can_add_plant, can_add_segment, remaining)

            if can_add > 0.5:
                work_df.at[idx, 'opt_sales_qty'] += can_add
                total_allocated += can_add
                plant_allocated[plant] += can_add
                segment_allocated[segment] += can_add
                remaining -= can_add

    # Round to integers
    work_df['opt_sales_qty'] = work_df['opt_sales_qty'].round(0).astype(int)

    # Recalculate totals after rounding
    final_total = work_df['opt_sales_qty'].sum()

    # Fine-tune to exact target if needed
    diff = total_target - final_total

    if abs(diff) > 0:
        # Add or subtract from the combination with highest quantity
        max_idx = work_df['opt_sales_qty'].idxmax()
        work_df.at[max_idx, 'opt_sales_qty'] += int(diff)

    print(f"\nFinal total: {work_df['opt_sales_qty'].sum():,.0f}")

    # Sort back to original order (by product_code, plant, segment)
    work_df = work_df.sort_values(['product_code', 'plant', 'segment']).reset_index(drop=True)

    return work_df


def save_optimization_results(opt_df: pd.DataFrame, output_path: Path) -> None:
    """
    Save optimization results to CSV.

    Args:
        opt_df: DataFrame with optimization results
        output_path: Path to save CSV file
    """
    # Calculate delta
    opt_df['delta_sales_qty'] = opt_df['opt_sales_qty'] - opt_df['sales_qty']

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    opt_df.to_csv(output_path, index=False)
    print(f"\nOptimization results saved to: {output_path}")

    # Print summary
    print(f"\nResults summary:")
    print(f"  Total rows: {len(opt_df)}")
    print(f"  Original total qty: {opt_df['sales_qty'].sum():,.0f}")
    print(f"  Optimized total qty: {opt_df['opt_sales_qty'].sum():,.0f}")
    print(f"  Rows with changes: {(opt_df['delta_sales_qty'] != 0).sum()}")
    print(f"  Max increase: {opt_df['delta_sales_qty'].max():,.0f}")
    print(f"  Max decrease: {opt_df['delta_sales_qty'].min():,.0f}")


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("Greedy Portfolio Optimization (2024 v4)")
    print("="*60)

    # Load data
    print("\nLoading data...")
    sales_df, product_master, segment_master = opt_common.load_raw_data()
    print(f"Loaded {len(sales_df)} sales records")

    # Build parameters
    print("\nBuilding optimization parameters...")
    params = opt_common.build_parameters(sales_df, product_master, segment_master)
    print(f"Total target: {params['total_target']:,}")
    print(f"Plant capacities: A={params['plant_capacity']['A']:,}, B={params['plant_capacity']['B']:,}")
    print(f"Segment mix targets: {params['segment_mix']}")

    # Run greedy optimization
    print("\nExecuting greedy optimization...")
    opt_df = run_greedy_optimization(sales_df, params)

    # Validate results
    opt_common.validate_sales_constraints(opt_df, params, "Greedy")

    # Save results
    workspace_root = opt_common.get_workspace_root()
    output_path = workspace_root / "data" / "processed" / "sales_2024_opt_greedy_v4.csv"
    save_optimization_results(opt_df, output_path)

    # Generate report
    report_path = workspace_root / "reports" / "optimization_2024_greedy_v4.md"
    print(f"\nGenerating Markdown report...")
    opt_common.generate_markdown_report(opt_df, params, "Greedy", report_path)

    # Calculate and display final metrics
    metrics = opt_common.calculate_summary_metrics(opt_df, 'opt_sales_qty')
    print(f"\n" + "="*60)
    print("Final Optimization Metrics")
    print("="*60)
    print(f"Total Profit: ¥{metrics['total_profit']:,.0f}")
    print(f"Overall Margin Rate: {metrics['overall_margin']*100:.2f}%")
    print(f"Total Revenue: ¥{metrics['total_revenue']:,.0f}")
    print("="*60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
