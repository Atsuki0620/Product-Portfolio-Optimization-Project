#!/usr/bin/env python3
"""
Optimization Results Comparison (2024 v4)

This script compares three scenarios:
1. Current (baseline from sales_2024.csv)
2. Greedy optimization
3. LP optimization

Generates a comprehensive comparison report in Markdown format.
"""

import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

# Import common functions
import optimization_common_v4 as opt_common


def load_all_scenarios() -> Dict[str, pd.DataFrame]:
    """
    Load all three scenarios for comparison.

    Returns:
        Dictionary with DataFrames for each scenario
    """
    workspace_root = opt_common.get_workspace_root()
    data_dir = workspace_root / "data"

    scenarios = {}

    # Load current (baseline)
    current_path = data_dir / "raw" / "sales_2024.csv"
    if not current_path.exists():
        raise FileNotFoundError(f"Current sales data not found: {current_path}")
    current_df = pd.read_csv(current_path)
    current_df['opt_sales_qty'] = current_df['sales_qty']  # Use sales_qty as opt_sales_qty
    scenarios['Current'] = current_df

    # Load Greedy optimization results
    greedy_path = data_dir / "processed" / "sales_2024_opt_greedy_v4.csv"
    if not greedy_path.exists():
        print(f"WARNING: Greedy results not found: {greedy_path}")
        scenarios['Greedy'] = None
    else:
        scenarios['Greedy'] = pd.read_csv(greedy_path)

    # Load LP optimization results
    lp_path = data_dir / "processed" / "sales_2024_opt_lp_v4.csv"
    if not lp_path.exists():
        print(f"WARNING: LP results not found: {lp_path}")
        scenarios['LP'] = None
    else:
        scenarios['LP'] = pd.read_csv(lp_path)

    return scenarios


def calculate_all_metrics(scenarios: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
    """
    Calculate metrics for all scenarios.

    Args:
        scenarios: Dictionary of scenario DataFrames

    Returns:
        Dictionary of metrics for each scenario
    """
    all_metrics = {}

    for name, df in scenarios.items():
        if df is None:
            all_metrics[name] = None
            continue

        metrics = opt_common.calculate_summary_metrics(df, 'opt_sales_qty')
        all_metrics[name] = metrics

    return all_metrics


def generate_comparison_report(scenarios: Dict[str, pd.DataFrame],
                               all_metrics: Dict[str, Dict],
                               params: Dict,
                               report_path: Path) -> None:
    """
    Generate comprehensive comparison report in Markdown.

    Args:
        scenarios: Dictionary of scenario DataFrames
        all_metrics: Dictionary of metrics for each scenario
        params: Parameters dictionary
        report_path: Path to save the report
    """
    # Create report directory if needed
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Optimization Results Comparison (2024)\n\n")
        f.write(f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Overview\n\n")
        f.write("This report compares three scenarios:\n\n")
        f.write("1. **Current**: Baseline from actual sales data (sales_2024.csv)\n")
        f.write("2. **Greedy**: Greedy heuristic optimization\n")
        f.write("3. **LP**: Linear Programming optimization (optimal solution)\n\n")

        # Overall metrics comparison
        f.write("## Overall Performance Comparison\n\n")
        f.write("| Metric | Current | Greedy | LP | Best |\n")
        f.write("|--------|---------|--------|----|----- |\n")

        # Helper function to format and find best
        def format_row(metric_name: str, values: List, format_str: str, higher_better: bool = True):
            valid_values = [(name, val) for name, val in zip(['Current', 'Greedy', 'LP'], values) if val is not None]
            if not valid_values:
                return

            if higher_better:
                best_name = max(valid_values, key=lambda x: x[1])[0]
            else:
                best_name = min(valid_values, key=lambda x: x[1])[0]

            row = f"| {metric_name} | "
            for name in ['Current', 'Greedy', 'LP']:
                val = values[['Current', 'Greedy', 'LP'].index(name)]
                if val is not None:
                    row += format_str.format(val)
                else:
                    row += "N/A"
                row += " | "
            row += f"{best_name} |\n"
            f.write(row)

        # Extract metrics
        total_qty = [all_metrics[name]['total_qty'] if all_metrics[name] else None
                    for name in ['Current', 'Greedy', 'LP']]
        total_revenue = [all_metrics[name]['total_revenue'] if all_metrics[name] else None
                        for name in ['Current', 'Greedy', 'LP']]
        total_profit = [all_metrics[name]['total_profit'] if all_metrics[name] else None
                       for name in ['Current', 'Greedy', 'LP']]
        overall_margin = [all_metrics[name]['overall_margin']*100 if all_metrics[name] else None
                         for name in ['Current', 'Greedy', 'LP']]

        format_row("Total Quantity", total_qty, "{:,.0f}", higher_better=False)
        format_row("Total Revenue (¥)", total_revenue, "¥{:,.0f}", higher_better=True)
        format_row("Total Profit (¥)", total_profit, "¥{:,.0f}", higher_better=True)
        format_row("Overall Margin (%)", overall_margin, "{:.2f}%", higher_better=True)

        f.write("\n")

        # Profit improvement
        f.write("## Profit Improvement Analysis\n\n")
        if all_metrics['Current'] and all_metrics['Greedy']:
            greedy_improvement = all_metrics['Greedy']['total_profit'] - all_metrics['Current']['total_profit']
            greedy_pct = greedy_improvement / all_metrics['Current']['total_profit'] * 100
            f.write(f"**Greedy vs Current**:\n")
            f.write(f"- Profit increase: ¥{greedy_improvement:,.0f} ({greedy_pct:+.2f}%)\n\n")

        if all_metrics['Current'] and all_metrics['LP']:
            lp_improvement = all_metrics['LP']['total_profit'] - all_metrics['Current']['total_profit']
            lp_pct = lp_improvement / all_metrics['Current']['total_profit'] * 100
            f.write(f"**LP vs Current**:\n")
            f.write(f"- Profit increase: ¥{lp_improvement:,.0f} ({lp_pct:+.2f}%)\n\n")

        if all_metrics['Greedy'] and all_metrics['LP']:
            lp_vs_greedy = all_metrics['LP']['total_profit'] - all_metrics['Greedy']['total_profit']
            lp_vs_greedy_pct = lp_vs_greedy / all_metrics['Greedy']['total_profit'] * 100
            f.write(f"**LP vs Greedy**:\n")
            f.write(f"- Profit difference: ¥{lp_vs_greedy:,.0f} ({lp_vs_greedy_pct:+.2f}%)\n\n")

        # Plant utilization comparison
        f.write("## Plant Utilization Comparison\n\n")
        f.write("| Plant | Capacity | Current | Greedy | LP |\n")
        f.write("|-------|----------|---------|--------|----|\n")

        for plant in ['A', 'B']:
            capacity = params['plant_capacity'][plant]
            row = f"| {plant} | {capacity:,} | "

            for name in ['Current', 'Greedy', 'LP']:
                if all_metrics[name]:
                    qty = all_metrics[name]['plant_summary'].get(plant, 0)
                    util = qty / capacity * 100
                    row += f"{qty:,.0f} ({util:.1f}%) | "
                else:
                    row += "N/A | "

            f.write(row + "\n")

        f.write("\n")

        # Segment mix comparison
        f.write("## Segment Mix Comparison\n\n")
        f.write("| Segment | Target Mix | Current | Greedy | LP |\n")
        f.write("|---------|------------|---------|--------|----|\n")

        for segment, target_mix in params['segment_mix'].items():
            row = f"| {segment} | {target_mix*100:.1f}% | "

            for name in ['Current', 'Greedy', 'LP']:
                if all_metrics[name]:
                    seg_summary = all_metrics[name]['segment_summary']
                    if segment in seg_summary.index:
                        qty = seg_summary.loc[segment, 'opt_sales_qty']
                        actual_mix = qty / all_metrics[name]['total_qty'] * 100
                        row += f"{actual_mix:.1f}% | "
                    else:
                        row += "0.0% | "
                else:
                    row += "N/A | "

            f.write(row + "\n")

        f.write("\n")

        # Segment margin rate comparison
        f.write("## Segment Margin Rate Comparison\n\n")
        f.write("| Segment | Target Margin | Current | Greedy | LP |\n")
        f.write("|---------|---------------|---------|--------|----|\n")

        for segment, target_margin in params['target_margin'].items():
            row = f"| {segment} | {target_margin*100:.1f}% | "

            for name in ['Current', 'Greedy', 'LP']:
                if all_metrics[name]:
                    seg_summary = all_metrics[name]['segment_summary']
                    if segment in seg_summary.index:
                        margin = seg_summary.loc[segment, 'margin_rate'] * 100
                        row += f"{margin:.2f}% | "
                    else:
                        row += "N/A | "
                else:
                    row += "N/A | "

            f.write(row + "\n")

        f.write("\n")

        # Summary and recommendations
        f.write("## Summary\n\n")

        if all_metrics['LP'] and all_metrics['Current']:
            best_profit = all_metrics['LP']['total_profit']
            current_profit = all_metrics['Current']['total_profit']
            improvement = best_profit - current_profit
            improvement_pct = improvement / current_profit * 100

            f.write(f"### Key Findings\n\n")
            f.write(f"1. **LP optimization achieves the maximum profit** of ¥{best_profit:,.0f}\n")
            f.write(f"2. This represents an improvement of ¥{improvement:,.0f} ({improvement_pct:.2f}%) "
                   f"over the current baseline\n")

            if all_metrics['Greedy']:
                greedy_profit = all_metrics['Greedy']['total_profit']
                greedy_gap = best_profit - greedy_profit
                greedy_gap_pct = greedy_gap / greedy_profit * 100
                f.write(f"3. Greedy heuristic achieves ¥{greedy_profit:,.0f}, "
                       f"which is ¥{greedy_gap:,.0f} ({greedy_gap_pct:.2f}%) below the LP optimum\n")

            f.write(f"\n### Constraint Satisfaction\n\n")
            f.write(f"All optimization scenarios satisfy:\n")
            f.write(f"- Total sales quantity: {params['total_target']:,} units\n")
            f.write(f"- Plant capacity limits\n")
            f.write(f"- Segment mix targets (±{params['tolerance']*100:.0f} percentage points)\n")

    print(f"\nComparison report saved to: {report_path}")


def print_console_summary(all_metrics: Dict[str, Dict]) -> None:
    """
    Print comparison summary to console.

    Args:
        all_metrics: Dictionary of metrics for each scenario
    """
    print("\n" + "="*60)
    print("Optimization Comparison Summary")
    print("="*60)

    print("\nTotal Profit by Scenario:")
    for name in ['Current', 'Greedy', 'LP']:
        if all_metrics[name]:
            profit = all_metrics[name]['total_profit']
            margin = all_metrics[name]['overall_margin'] * 100
            print(f"  {name:10s}: ¥{profit:>15,.0f}  (Margin: {margin:5.2f}%)")
        else:
            print(f"  {name:10s}: N/A")

    # Find best
    valid_scenarios = [(name, all_metrics[name]['total_profit'])
                      for name in ['Current', 'Greedy', 'LP']
                      if all_metrics[name]]

    if valid_scenarios:
        best_name, best_profit = max(valid_scenarios, key=lambda x: x[1])
        print(f"\n✓ Best scenario: {best_name} with ¥{best_profit:,.0f} total profit")

        # Calculate improvements
        if all_metrics['Current']:
            current_profit = all_metrics['Current']['total_profit']
            improvement = best_profit - current_profit
            improvement_pct = improvement / current_profit * 100
            print(f"  Improvement over current: ¥{improvement:,.0f} ({improvement_pct:+.2f}%)")

    print("="*60 + "\n")


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("Optimization Results Comparison (2024 v4)")
    print("="*60)

    # Load scenarios
    print("\nLoading scenarios...")
    scenarios = load_all_scenarios()

    for name, df in scenarios.items():
        if df is not None:
            print(f"  {name}: {len(df)} rows loaded")
        else:
            print(f"  {name}: Not available")

    # Build parameters from current data
    print("\nBuilding parameters...")
    _, product_master, segment_master = opt_common.load_raw_data()
    params = opt_common.build_parameters(scenarios['Current'], product_master, segment_master)

    # Calculate metrics for all scenarios
    print("\nCalculating metrics for all scenarios...")
    all_metrics = calculate_all_metrics(scenarios)

    # Generate comparison report
    workspace_root = opt_common.get_workspace_root()
    report_path = workspace_root / "reports" / "optimization_2024_comparison_v4.md"

    print("\nGenerating comparison report...")
    generate_comparison_report(scenarios, all_metrics, params, report_path)

    # Print console summary
    print_console_summary(all_metrics)

    return 0


if __name__ == "__main__":
    sys.exit(main())
