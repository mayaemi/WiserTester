import argparse
import os


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
    parser.add_argument("--input_dir", type=str, help="Location of input dirs")
    parser.add_argument("--output_dir", type=str, help="Location of test output")
    parser.add_argument("--expected_dir", type=str, help="Location of expectations")
    parser.add_argument("--specific_inputs", nargs="+", help="List of specific input files to test")
    parser.add_argument("--compare_only", action="store_true", help="Only run comparison")
    parser.add_argument("--no_comparison", action="store_true", help="Don't compare to previous outputs")
    parser.add_argument(
        "--comparison_reports", type=str, default=os.path.join("data", "comparison_reports"), help="Path to comparison reports"
    )
    parser.add_argument("--request_timeout", type=int, default=60, help="Request timeout in seconds")
    parser.add_argument("--exclude_inputs", nargs="+", default=[], help="List of input files to exclude from testing")
    parser.add_argument("--no_preprocessing", action="store_true", help="Don't preprocess outputs before comparison")

    return parser.parse_args()
