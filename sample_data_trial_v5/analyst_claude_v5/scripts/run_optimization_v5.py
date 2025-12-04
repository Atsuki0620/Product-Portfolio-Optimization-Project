#!/usr/bin/env python3
"""
Product Portfolio Optimization v5 - Integrated Execution Script

This script executes the complete optimization workflow in sequence:
    Step 1: Data Preparation
    Step 2: Target Share Calculation
    Step 3: Feasibility Validation
    Step 4: Optimization Execution

Usage:
    python run_optimization_v5.py                    # Run all steps
    python run_optimization_v5.py --step 2           # Run only Step 2
    python run_optimization_v5.py --from 2 --to 3    # Run Steps 2-3
    python run_optimization_v5.py --yes              # Skip confirmations
    python run_optimization_v5.py --verbose          # Verbose output
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
from datetime import datetime


class OptimizationRunner:
    """Manages the execution of the optimization workflow."""

    STEPS = {
        1: {
            'name': 'Data Preparation',
            'script': 'step1_data_preparation.py',
            'description': 'Load and validate master data'
        },
        2: {
            'name': 'Target Share Calculation',
            'script': 'step2_target_share_calculation.py',
            'description': 'Calculate target market shares with competitive analysis',
            'requires_confirmation': True,
            'confirmation_message': (
                "\n" + "="*70 + "\n"
                "Step 2 completed: Target shares have been calculated.\n"
                "Please review the output files before proceeding to validation.\n"
                "="*70 + "\n"
                "Continue to Step 3 (Feasibility Validation)? [y/n]: "
            )
        },
        3: {
            'name': 'Feasibility Validation',
            'script': 'step3_feasibility_validation.py',
            'description': 'Validate target shares against constraints',
            'requires_confirmation': True,
            'confirmation_message': (
                "\n" + "="*70 + "\n"
                "Step 3 completed: Feasibility validation finished.\n"
                "If there were warnings, please review them carefully.\n"
                "="*70 + "\n"
                "Continue to Step 4 (Optimization Execution)? [y/n]: "
            )
        },
        4: {
            'name': 'Optimization Execution',
            'script': 'step4_optimization_execution.py',
            'description': 'Execute linear programming optimization'
        }
    }

    def __init__(self, scripts_dir: Path, auto_yes: bool = False, verbose: bool = False):
        """
        Initialize the optimization runner.

        Args:
            scripts_dir: Directory containing step scripts
            auto_yes: If True, skip all confirmation prompts
            verbose: If True, show verbose output
        """
        self.scripts_dir = scripts_dir
        self.auto_yes = auto_yes
        self.verbose = verbose
        self.execution_log = []

    def print_header(self, text: str):
        """Print a formatted header."""
        print("\n" + "="*70)
        print(f"  {text}")
        print("="*70 + "\n")

    def print_step_header(self, step_num: int):
        """Print a formatted step header."""
        step_info = self.STEPS[step_num]
        print("\n" + "─"*70)
        print(f"Step {step_num}: {step_info['name']}")
        print(f"Description: {step_info['description']}")
        print("─"*70 + "\n")

    def run_step(self, step_num: int) -> bool:
        """
        Execute a single optimization step.

        Args:
            step_num: Step number (1-4)

        Returns:
            True if step completed successfully, False otherwise
        """
        if step_num not in self.STEPS:
            print(f"Error: Invalid step number {step_num}")
            return False

        step_info = self.STEPS[step_num]
        script_path = self.scripts_dir / step_info['script']

        if not script_path.exists():
            print(f"Error: Script not found: {script_path}")
            return False

        self.print_step_header(step_num)

        # Record start time
        start_time = datetime.now()

        # Execute the step script
        try:
            cmd = [sys.executable, str(script_path)]
            result = subprocess.run(
                cmd,
                cwd=self.scripts_dir.parent,  # Run from analyst_claude_v5 directory
                capture_output=not self.verbose,
                text=True,
                check=False
            )

            # Record execution time
            elapsed = (datetime.now() - start_time).total_seconds()

            if result.returncode == 0:
                print(f"\n✓ Step {step_num} completed successfully ({elapsed:.1f}s)")
                self.execution_log.append({
                    'step': step_num,
                    'status': 'success',
                    'elapsed': elapsed
                })

                # Show captured output if not verbose
                if not self.verbose and result.stdout:
                    print("\nOutput summary:")
                    # Show last few lines of output
                    lines = result.stdout.strip().split('\n')
                    for line in lines[-10:]:
                        print(f"  {line}")

                return True
            else:
                print(f"\n✗ Step {step_num} failed (exit code: {result.returncode})")
                self.execution_log.append({
                    'step': step_num,
                    'status': 'failed',
                    'elapsed': elapsed
                })

                # Show error output
                if result.stderr:
                    print("\nError output:")
                    print(result.stderr)
                if result.stdout:
                    print("\nStandard output:")
                    print(result.stdout)

                self._print_recovery_guidance(step_num)
                return False

        except Exception as e:
            print(f"\n✗ Step {step_num} failed with exception: {e}")
            self.execution_log.append({
                'step': step_num,
                'status': 'error',
                'elapsed': 0
            })
            self._print_recovery_guidance(step_num)
            return False

    def _print_recovery_guidance(self, step_num: int):
        """Print guidance for recovering from a failed step."""
        print("\n" + "─"*70)
        print("Recovery Guidance:")
        print("─"*70)
        print("1. Review the error messages above")
        print("2. Check input data files for the failed step")
        print("3. Verify all dependencies are installed (pandas, numpy, pulp)")
        print(f"4. Try running the step individually:")
        print(f"   python {self.STEPS[step_num]['script']}")
        print("5. Check logs in the output directory for more details")
        print("─"*70 + "\n")

    def get_user_confirmation(self, message: str) -> bool:
        """
        Prompt user for confirmation.

        Args:
            message: Confirmation message to display

        Returns:
            True if user confirms, False otherwise
        """
        if self.auto_yes:
            print(message.replace('[y/n]: ', '[y/n]: y (auto-confirmed)'))
            return True

        while True:
            response = input(message).lower().strip()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'")

    def run_workflow(self, start_step: int = 1, end_step: int = 4) -> bool:
        """
        Execute the complete optimization workflow.

        Args:
            start_step: First step to execute (default: 1)
            end_step: Last step to execute (default: 4)

        Returns:
            True if all steps completed successfully, False otherwise
        """
        self.print_header(f"Product Portfolio Optimization v5 - Steps {start_step}-{end_step}")

        workflow_start = datetime.now()

        for step_num in range(start_step, end_step + 1):
            if step_num not in self.STEPS:
                continue

            # Execute step
            success = self.run_step(step_num)

            if not success:
                print(f"\n✗ Workflow stopped at Step {step_num} due to error")
                self._print_execution_summary()
                return False

            # Check for confirmation requirement
            step_info = self.STEPS[step_num]
            if step_info.get('requires_confirmation') and step_num < end_step:
                if not self.get_user_confirmation(step_info['confirmation_message']):
                    print(f"\nWorkflow stopped by user after Step {step_num}")
                    self._print_execution_summary()
                    return False

        # All steps completed
        workflow_elapsed = (datetime.now() - workflow_start).total_seconds()

        self.print_header("Optimization Workflow Completed Successfully!")
        self._print_execution_summary()
        print(f"Total execution time: {workflow_elapsed:.1f}s\n")

        return True

    def _print_execution_summary(self):
        """Print a summary of executed steps."""
        if not self.execution_log:
            return

        print("\n" + "─"*70)
        print("Execution Summary:")
        print("─"*70)
        for log_entry in self.execution_log:
            step_num = log_entry['step']
            status = log_entry['status']
            elapsed = log_entry['elapsed']
            step_name = self.STEPS[step_num]['name']

            status_symbol = "✓" if status == 'success' else "✗"
            print(f"  {status_symbol} Step {step_num}: {step_name} ({elapsed:.1f}s) - {status}")
        print("─"*70 + "\n")


def main():
    """Main entry point for the optimization runner."""
    parser = argparse.ArgumentParser(
        description='Product Portfolio Optimization v5 - Integrated Execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run all steps (1-4)
  %(prog)s --step 2           # Run only Step 2
  %(prog)s --from 2 --to 3    # Run Steps 2-3
  %(prog)s --yes              # Run all steps, skip confirmations
  %(prog)s --verbose          # Run with verbose output
        """
    )

    parser.add_argument(
        '--step',
        type=int,
        choices=[1, 2, 3, 4],
        help='Run only this specific step'
    )
    parser.add_argument(
        '--from',
        type=int,
        choices=[1, 2, 3, 4],
        dest='from_step',
        help='Start from this step (default: 1)'
    )
    parser.add_argument(
        '--to',
        type=int,
        choices=[1, 2, 3, 4],
        dest='to_step',
        help='End at this step (default: 4)'
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip all confirmation prompts (auto-confirm)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose output from each step'
    )

    args = parser.parse_args()

    # Determine step range
    if args.step:
        start_step = end_step = args.step
    else:
        start_step = args.from_step or 1
        end_step = args.to_step or 4

    # Validate step range
    if start_step > end_step:
        print("Error: Start step must be <= end step")
        return 1

    # Determine script directory
    scripts_dir = Path(__file__).parent

    # Create runner and execute workflow
    runner = OptimizationRunner(
        scripts_dir=scripts_dir,
        auto_yes=args.yes,
        verbose=args.verbose
    )

    success = runner.run_workflow(start_step, end_step)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
