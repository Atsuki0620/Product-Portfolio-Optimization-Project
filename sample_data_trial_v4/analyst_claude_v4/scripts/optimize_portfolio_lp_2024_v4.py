#!/usr/bin/env python3
"""
Linear Programming Portfolio Optimization (2024 v4)

This script formulates and solves a Linear Programming (LP) problem to optimize
the product portfolio, maximizing total profit while satisfying all constraints.

Requirements:
- pulp library (install with: pip install pulp)
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

try:
    import pulp
except ImportError:
    print("ERROR: pulp library is required for LP optimization.")
    print("Please install it with: pip install pulp")
    sys.exit(1)

# Import common functions
import optimization_common_v4 as opt_common


def build_lp_model(sales_df: pd.DataFrame, params: Dict) -> Tuple[pulp.LpProblem, Dict]:
    """
    Build Linear Programming model for portfolio optimization.

    Objective:
        Maximize total profit = sum(unit_profit[p,pl,s] * x[p,pl,s])

    Decision Variables:
        x[p, pl, s] >= 0  (continuous)

    Constraints:
        1. Total sales: sum(x[p,pl,s]) = 504,000
        2. Plant capacity:
           - sum(x[p,'A',s]) <= 300,000
           - sum(x[p,'B',s]) <= 204,000
        3. Segment mix (for each segment s):
           - 504,000 * (target_mix[s] - 0.03) <= sum(x[p,pl,s]) <= 504,000 * (target_mix[s] + 0.03)
        4. Demand upper bound:
           - 0 <= x[p,pl,s] <= demand_max[p,pl,s]

    Args:
        sales_df: Sales data DataFrame
        params: Parameters dictionary

    Returns:
        Tuple of (LP problem, decision variables dict)
    """
    print("\n" + "="*60)
    print("Building Linear Programming Model")
    print("="*60)

    # Create LP problem (maximization)
    prob = pulp.LpProblem("Portfolio_Optimization", pulp.LpMaximize)

    # Create decision variables
    x_vars = {}
    for _, row in sales_df.iterrows():
        key = (row['product_code'], row['plant'], row['segment'])
        demand_max = row['sales_qty'] * 2.0  # Allow up to 2x current demand

        # Create variable with bounds
        x_vars[key] = pulp.LpVariable(
            name=f"x_{key[0]}_{key[1]}_{key[2]}",
            lowBound=0,
            upBound=demand_max,
            cat='Continuous'
        )

    print(f"Created {len(x_vars)} decision variables")

    # Objective function: Maximize total profit
    objective_terms = []
    for _, row in sales_df.iterrows():
        key = (row['product_code'], row['plant'], row['segment'])
        unit_profit = row['unit_price'] * row['margin_rate']
        objective_terms.append(unit_profit * x_vars[key])

    prob += pulp.lpSum(objective_terms), "Total_Profit"
    print("Objective function: Maximize total profit")

    # Constraint 1: Total sales quantity
    total_target = params['total_target']
    prob += (
        pulp.lpSum([x_vars[key] for key in x_vars.keys()]) == total_target,
        "Total_Sales_Quantity"
    )
    print(f"Constraint: Total sales = {total_target:,}")

    # Constraint 2: Plant capacity
    for plant in ['A', 'B']:
        plant_vars = [x_vars[key] for key in x_vars.keys() if key[1] == plant]
        capacity = params['plant_capacity'][plant]
        prob += (
            pulp.lpSum(plant_vars) <= capacity,
            f"Plant_{plant}_Capacity"
        )
        print(f"Constraint: Plant {plant} <= {capacity:,}")

    # Constraint 3: Segment mix bounds
    for segment, target_mix in params['segment_mix'].items():
        segment_vars = [x_vars[key] for key in x_vars.keys() if key[2] == segment]

        lower_bound = total_target * (target_mix - params['tolerance'])
        upper_bound = total_target * (target_mix + params['tolerance'])

        prob += (
            pulp.lpSum(segment_vars) >= lower_bound,
            f"Segment_{segment}_Lower"
        )
        prob += (
            pulp.lpSum(segment_vars) <= upper_bound,
            f"Segment_{segment}_Upper"
        )
        print(f"Constraint: Segment {segment}: {lower_bound:,.0f} to {upper_bound:,.0f}")

    print(f"\nTotal constraints: {len(prob.constraints)}")

    return prob, x_vars


def solve_lp_model(prob: pulp.LpProblem, x_vars: Dict) -> Dict:
    """
    Solve the LP model and extract results.

    Args:
        prob: LP problem
        x_vars: Decision variables dictionary

    Returns:
        Dictionary with solution values
    """
    print("\n" + "="*60)
    print("Solving Linear Programming Model")
    print("="*60)

    # Solve the problem
    print("\nInvoking LP solver...")
    solver = pulp.PULP_CBC_CMD(msg=1)  # Use CBC solver with output
    prob.solve(solver)

    # Check solution status
    status = pulp.LpStatus[prob.status]
    print(f"\nSolver status: {status}")

    if status != 'Optimal':
        print(f"WARNING: Solution is not optimal!")
        if status == 'Infeasible':
            print("The problem is infeasible - constraints cannot be satisfied simultaneously.")
        elif status == 'Unbounded':
            print("The problem is unbounded - objective can increase indefinitely.")
        else:
            print(f"Unexpected status: {status}")
        return None

    # Extract solution
    print(f"Optimal objective value: ¥{pulp.value(prob.objective):,.0f}")

    solution = {}
    for key, var in x_vars.items():
        solution[key] = var.varValue

    return solution


def apply_lp_solution(sales_df: pd.DataFrame, solution: Dict) -> pd.DataFrame:
    """
    Apply LP solution to sales DataFrame.

    Args:
        sales_df: Original sales DataFrame
        solution: Solution dictionary from solve_lp_model

    Returns:
        DataFrame with opt_sales_qty column
    """
    result_df = sales_df.copy()
    result_df['opt_sales_qty'] = 0.0

    for idx, row in result_df.iterrows():
        key = (row['product_code'], row['plant'], row['segment'])
        if key in solution:
            result_df.at[idx, 'opt_sales_qty'] = solution[key]

    # Round to integers for practical purposes
    result_df['opt_sales_qty'] = result_df['opt_sales_qty'].round(0).astype(int)

    return result_df


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
    print("Linear Programming Portfolio Optimization (2024 v4)")
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

    # Build LP model
    prob, x_vars = build_lp_model(sales_df, params)

    # Solve LP model
    solution = solve_lp_model(prob, x_vars)

    if solution is None:
        print("\nERROR: Could not find optimal solution")
        return 1

    # Apply solution
    print("\nApplying solution to data...")
    opt_df = apply_lp_solution(sales_df, solution)

    # Validate results
    opt_common.validate_sales_constraints(opt_df, params, "LP")

    # Save results
    workspace_root = opt_common.get_workspace_root()
    output_path = workspace_root / "data" / "processed" / "sales_2024_opt_lp_v4.csv"
    save_optimization_results(opt_df, output_path)

    # Generate report
    report_path = workspace_root / "reports" / "optimization_2024_lp_v4.md"
    print(f"\nGenerating Markdown report...")
    opt_common.generate_markdown_report(opt_df, params, "LP", report_path)

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
