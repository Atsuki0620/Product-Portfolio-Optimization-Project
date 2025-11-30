#!/usr/bin/env python3
"""
Portfolio Optimization CLI (2024 v4)

Main entry point for running portfolio optimization.
Supports three methods:
- greedy: Greedy heuristic optimization
- lp: Linear Programming optimization (requires pulp)
- compare: Compare all optimization results

Usage:
    python run_optimization_2024_v4.py --method greedy
    python run_optimization_2024_v4.py --method lp
    python run_optimization_2024_v4.py --method compare
"""

import argparse
import sys
from pathlib import Path

# Import optimization modules
import optimize_portfolio_greedy_2024_v4 as greedy_opt
import optimize_portfolio_lp_2024_v4 as lp_opt
import compare_optimization_2024_v4 as compare


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Portfolio Optimization Tool (2024 v4)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Run Greedy optimization:
    %(prog)s --method greedy

  Run LP optimization:
    %(prog)s --method lp

  Compare all results:
    %(prog)s --method compare
        """
    )

    parser.add_argument(
        '--method',
        type=str,
        required=True,
        choices=['greedy', 'lp', 'compare'],
        help='Optimization method to run (greedy, lp, or compare)'
    )

    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_args()

    print("="*70)
    print("Portfolio Optimization Tool (2024 v4)")
    print("="*70)
    print(f"Method: {args.method}")
    print("="*70)

    try:
        if args.method == 'greedy':
            print("\nRunning Greedy optimization...")
            return_code = greedy_opt.main()

        elif args.method == 'lp':
            print("\nRunning LP optimization...")
            return_code = lp_opt.main()

        elif args.method == 'compare':
            print("\nRunning comparison analysis...")
            return_code = compare.main()

        else:
            print(f"ERROR: Unknown method '{args.method}'")
            return 1

        if return_code == 0:
            print("\n" + "="*70)
            print(f"✓ {args.method.upper()} completed successfully")
            print("="*70 + "\n")
        else:
            print("\n" + "="*70)
            print(f"✗ {args.method.upper()} completed with errors")
            print("="*70 + "\n")

        return return_code

    except Exception as e:
        print(f"\n{'='*70}")
        print(f"✗ ERROR: {str(e)}")
        print(f"{'='*70}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
