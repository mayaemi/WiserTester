import argparse
import os
from .configure import test_mode_type, TestMode


def parse_args():
    """
    Parse command line arguments for running the Wiser Tester program.
    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Run Wiser Tester")
    parser.add_argument("--username", type=str, required=True, help="Username for login")
    parser.add_argument("--password", type=str, required=True, help="Password for login")
    parser.add_argument("--config", type=str, required=True, help="Path to the configuration file")
    parser.add_argument("--mode", type=test_mode_type, choices=list(TestMode), help="Testing mode")
    parser.add_argument("--specific_list", type=str, help="Specific list of input directories")
    parser.add_argument("--expected_output", type=str, default=os.path.join("data", "expectations"), help="Path to expectations")
    parser.add_argument("--no_comparison", action="store_true", help="Don't compare to previous outputs")
    parser.add_argument(
        "--comparison_reports", type=str, default=os.path.join("data", "comparison_reports"), help="Path to comparison reports"
    )
    parser.add_argument("--request_timeout", type=int, default=60, help="Request timeout in seconds")
    parser.add_argument("--exclude_inputs", nargs="+", default=[], help="List of input files to exclude from sending")
    parser.add_argument("--no_preprocessing", action="store_true", help="Don't preprocess outputs")

    return parser.parse_args()
