# main file
import argparse
import asyncio
from src.configure import LOGGER, test_mode_type, TestMode
from src.exceptions import handle_exceptions
from src.compare import Compare
from src.tester import WiserTester
from src.utils import load_json_file
from argparse import ArgumentParser
import contextlib


def parse_args():
    """
    The function `parse_args()` is used to parse command line arguments for running the Wiser Tester
    program.
    :return: The function `parse_args()` returns the parsed command-line arguments as an
    `argparse.Namespace` object.
    """
    parser = argparse.ArgumentParser(description="Run Wiser Tester")
    parser.add_argument("--username", type=str, required=True, help="Username for login")
    parser.add_argument("--password", type=str, required=True, help="Password for login")
    parser.add_argument("--config", type=str, required=True, help="Path to the configuration file")

    parser.add_argument("--mode", type=test_mode_type, choices=list(TestMode), help="Testing mode")
    parser.add_argument("--specific_list", type=str, help="specific list of input directories")
    parser.add_argument("--expected_output", type=str, default="data/expectations", help="path to expectations")
    parser.add_argument("--no_comparison", action="store_true", help="Don't Compare to previous outputs")
    parser.add_argument("--comparison_reports", type=str, default="data/comparison_reports", help="path to comparison reports")
    parser.add_argument("--request_timeout", type=int, default=60, help="request timeout in seconds")
    parser.add_argument("--exclude_inputs", nargs="+", default=[], help="List of input files to exclude from sending")
    parser.add_argument("--no_preprocessing", action="store_true", help="Don't preprocess outputs")

    return parser.parse_args()


@handle_exceptions("An unexpected error occurred", True)
async def main(config, args, tester):
    try:
        if args.mode != TestMode.COMPARE_ONLY:
            await tester.start_test(args.specific_list.split(",") if args.mode == TestMode.SPECIFIC else None)
        if not args.no_comparison:
            LOGGER.info("Comparing outputs")
            # comparison = Compare(config["outputs_dir"], args.expected_output, args.comparison_reports, config["ignore_paths"])
            comparison = Compare(config, args.expected_output, args.comparison_reports)
            report_paths = comparison.compare_outputs_with_expectations(args.no_preprocessing)
            LOGGER.info(f"Comparison reports: {report_paths}")
    except KeyboardInterrupt:
        LOGGER.warning("Interrupted during main execution.")


async def shutdown(loop, tester):
    """Graceful shutdown."""
    LOGGER.info("Closing client sessions...")
    await tester.close()

    LOGGER.info("Cancelling outstanding tasks...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    for task in tasks:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    loop.stop()
    LOGGER.info("Shutdown complete.")


if __name__ == "__main__":
    args = parse_args()
    config = load_json_file(args.config)
    tester = WiserTester(args.username, args.password, args.request_timeout, config, args.exclude_inputs)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(config, args, tester))
    except KeyboardInterrupt:
        LOGGER.info("KeyboardInterrupt caught in main")
    finally:
        loop.run_until_complete(shutdown(loop, tester))
        loop.close()
