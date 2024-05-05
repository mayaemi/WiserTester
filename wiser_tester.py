import asyncio
from src.configure import LOGGER, TestMode
from src.exceptions import handle_exceptions
from src.compare import Compare
from src.tester import WiserTester
from src.utils import load_json_file
from src.arg_parser import parse_args
import contextlib


def load_configuration(file_path):
    """Load configuration from a JSON file."""
    return load_json_file(file_path)


@handle_exceptions("An unexpected error occurred", True)
async def run_tests_and_comparison(config, args, tester):
    """Run tests and comparisons based on provided arguments."""
    input_directories = args.input_directories.split(",") if args.input_directories else None
    if args.mode != TestMode.COMPARE_ONLY:
        await tester.start_test(input_directories)
    if not args.no_comparison:
        LOGGER.info("Comparing outputs")
        comparison = Compare(
            config,
            args.expected_output,
            args.comparison_reports,
            input_directories,
        )
        report_paths = comparison.compare_outputs_with_expectations(args.no_preprocessing)
        LOGGER.info(f"Comparison reports: {report_paths}")


async def shutdown(loop, tester):
    """Gracefully shut down asynchronous operations and close the event loop."""
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
    config = load_configuration(args.config)
    tester = WiserTester(args.username, args.password, args.request_timeout, config, args.exclude_inputs)
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(run_tests_and_comparison(config, args, tester))
    except KeyboardInterrupt:
        LOGGER.info("KeyboardInterrupt caught in main")
    finally:
        loop.run_until_complete(shutdown(loop, tester))
        loop.close()
