import asyncio
from datetime import datetime
import json
import os
import re
import sys
from functools import wraps
from pathlib import Path
import socketio
import httpx
import logging
import argparse
from deepdiff import DeepDiff, Delta

# Configuration and Constants
CONFIG = {
    "LOGIN_URL": "/login",
    "LOGIN_JSON_HEADERS": {"Accept": "application/json", "Content-Type": "application/json"},
    "LOG_FORMAT": "%(asctime)s | %(levelname)s | %(message)s",
    "LOG_FILE": "logs/testlog.log",
}


# Setup logging
def setup_logging():
    if not os.path.isdir("logs"):
        os.mkdir("logs")

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(CONFIG["LOG_FORMAT"])

    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler(CONFIG["LOG_FILE"])]
    for handler in handlers:
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


LOGGER = setup_logging()


# Error Handling Decorator
def handle_exceptions(log_message, should_raise=True):
    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    LOGGER.error(f"{log_message}: {e}")
                    if should_raise:
                        raise

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    LOGGER.error(f"{log_message}: {e}")
                    if should_raise:
                        raise

            return sync_wrapper

    return decorator


# Utility Functions
@handle_exceptions("Error loading/saving JSON file")
def load_json_file(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


@handle_exceptions("Failed to save JSON file")
def save_json_file(data, file_path):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=2)
        return True


# Authentication
@handle_exceptions("Login failed", True)
async def login(username, password, server_path):
    """
    Logs into the application using provided credentials.
    Returns: HTTPX response object and cookies after successful login.
    """
    url = f"{server_path}{CONFIG['LOGIN_URL']}"
    data = {"username": username, "password": password}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=CONFIG["LOGIN_JSON_HEADERS"])
        response.raise_for_status()
        return response, response.cookies


def handle_cookies(response_cookies):
    """Extracts and formats required cookies from the HTTPX response."""
    access_token_cookie = response_cookies.get("access_token_cookie")
    csrf_token = response_cookies.get("csrf_access_token")

    if not all([access_token_cookie, csrf_token]):
        LOGGER.error("Error: Missing required cookies")
        raise ValueError("Missing required cookies")

    cookies_str = f"access_token_cookie={access_token_cookie}; csrf_access_token={csrf_token}"
    return cookies_str, access_token_cookie, csrf_token


class Compare:
    def __init__(self, outputs_path, expectations_path, reports_path, ignore_paths=None):
        self.outputs_path = outputs_path
        self.expectations_path = expectations_path
        self.reports_path = reports_path
        self.report_paths = []
        self.ignore_paths = ignore_paths if ignore_paths is not None else []

        LOGGER.info(f"Excluding paths: {self.ignore_paths}")

    @handle_exceptions("Comparison error", False)
    def compare_outputs_with_expectations(self):
        """Compare the output files with expected outputs stored in a specified directory."""
        LOGGER.info("Comparing outputs to expectations")
        for output_folder in os.listdir(self.outputs_path):
            expectation_folder_path = os.path.join(self.expectations_path, output_folder)
            if os.path.isdir(expectation_folder_path):
                output_folder_path = os.path.join(self.outputs_path, output_folder)
                self.compare_folder_outputs(output_folder_path, expectation_folder_path)
        return self.generate_summary_report()

    @handle_exceptions("Directory comparison error", False)
    def compare_folder_outputs(self, output_folder_path, expectation_folder_path):
        """Compare outputs in a specific folder with their expected counterparts."""
        LOGGER.info(f"Comparing results for {os.path.basename(output_folder_path)}")
        # Iterate through output files in the folder
        for output_file in os.listdir(output_folder_path):
            input_file_name, _ = os.path.splitext(output_file)
            expected_file_name = f"{input_file_name}.json"
            expected_file_path = os.path.join(expectation_folder_path, expected_file_name)
            output_file_path = os.path.join(output_folder_path, output_file)
            new_report_path = os.path.join(self.reports_path, os.path.basename(output_folder_path))

            if not os.path.isdir(new_report_path):
                os.mkdir(new_report_path)
                LOGGER.info(f"Created directory {new_report_path}")

            # Compare the output file with the expected file
            if os.path.exists(expected_file_path):
                self.compare_and_save_report(input_file_name, output_file_path, expected_file_path, new_report_path)
            else:
                LOGGER.warning(f"No expectation file found for {input_file_name}")

    @handle_exceptions("Unexpected error reading files", False)
    def compare_and_save_report(self, input_file_name, output_file_path, expected_file_path, report_path):
        """Compare an output file with its expected counterpart and save the report."""
        output_data = load_json_file(output_file_path).get("data")
        expected_data = load_json_file(expected_file_path).get("data")

        if output_data and expected_data:  # Ensure data was successfully loaded
            report = {
                "timestamp": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                "request_id": output_data.get("requestId", "N/A"),
                "output_file": output_file_path,
                "expected_output_file": expected_file_path,
            }
            exclude_regex = [re.compile(path) for path in self.ignore_paths]

            diff = DeepDiff(
                output_data,
                expected_data,
                ignore_order=True,
                report_repetition=True,
                exclude_regex_paths=exclude_regex,
                cutoff_intersection_for_pairs=1,
                get_deep_distance=True,
            )
            if diff:
                delta = Delta(diff, bidirectional=True)
                flat_dicts = delta.to_flat_dicts()
                report["diff"] = flat_dicts
                file_name = f"{input_file_name}_comparison.json"
                output_path = os.path.join(report_path, file_name)
                save_json_file(report, output_path)
                self.report_paths.append(output_path)
                LOGGER.info(f"Comparison report generated for {input_file_name}")
            else:
                LOGGER.info(f"No difference found in output for {input_file_name}")

    @handle_exceptions("Failed to generate summary report", False)
    def generate_summary_report(self):
        """Generate a summary report of all comparisons."""
        summary = {"total_comparisons": len(self.report_paths), "differences": []}

        for report_path in self.report_paths:
            report_data = load_json_file(report_path)
            if "diff" in report_data:
                summary["differences"].append(
                    {
                        "request_id": report_data.get("request_id", "N/A"),
                        "output_file": report_data["output_file"],
                        "expected_output_file": report_data["expected_output_file"],
                        "diff": report_data["diff"],
                    }
                )
        summary_report_path = os.path.join(self.reports_path, "comparison_summary.json")
        save_json_file(summary, summary_report_path)
        LOGGER.info(f"Summary report generated at {summary_report_path}")
        return summary_report_path


class WiserTester:

    def __init__(self, username, password, request_timeout, config):
        """
        Initializes the WiserTester instance.
        Args:
            username (str): Username for login.
            password (str): Password for login.
            request_timeout (int): Timeout for waiting on reports.
            config: Config file dictionary
        """
        self.socket = socketio.AsyncClient()
        self.http_client = httpx.AsyncClient()
        self.username = username
        self.password = password
        self.host = config["host"]
        self.origin = config["origin"]
        self.inputs_dir = config["inputs_dir"]
        self.outputs_dir = config["outputs_dir"]

        self.server_path = f"http://{self.host}/"
        self.request_timeout = request_timeout  # seconds
        self.config = config
        self.s_id, self.cookies = None, None
        self.current_input_dir, self.current_output_dir = None, None
        self.request_to_input_map = {}  # dictionary to map request IDs to input file names
        self.request_to_input_dir_map = {}  # Map request IDs to input directories
        self.request_mapping_event = asyncio.Event()
        self.report_event = asyncio.Event()
        self.request_id_lock = asyncio.Lock()  # Lock for synchronizing request ID mapping
        self.client_lock = asyncio.Lock()
        self.pending_requests = set()

        # Define event handlers for the socket events
        self._define_event_handlers()

    async def start_test(self, specific_inputs=None):
        """
        Starts the testing process. Tests either all inputs or a specific list of inputs.
        Args:
            specific_inputs (list, optional): A list of specific inputs to be tested. If None, all inputs will be tested.
        """
        # Perform login and store cookies
        _, self.cookies = await login(self.username, self.password, self.server_path)
        LOGGER.info(f"Logged in and obtained cookies {self.cookies}")

        await self.connect_to_server()

        await self.test_inputs(specific_inputs)

        await self.socket.wait()

    def _define_event_handlers(self):
        """Define event handlers for socket events."""

        @self.socket.event
        async def connect():
            LOGGER.info("Socket connected")

        @self.socket.event
        async def disconnect():
            LOGGER.info("Socket disconnected")

        @self.socket.event
        async def report_ready(data):
            await self._handle_report_ready(data)

        @self.socket.event
        async def error(data):
            await self._handle_error(data)

    async def _handle_report_ready(self, data):
        """Handle incoming report readiness."""
        await self.request_mapping_event.wait()
        self.request_mapping_event.clear()
        await self.process_report(data)

    async def _handle_error(self, data):
        """Handle errors reported by the server."""
        error_msg = data.get("error")
        report_id = data.get("id")
        if report_id:
            async with self.client_lock:
                LOGGER.error(f"Error for ID {report_id}: {error_msg}")

    @handle_exceptions("Socket connection failed.", True)
    async def connect_to_server(self):
        """Establishes connection to the server."""
        await self.socket.connect(self.server_path, wait_timeout=10)
        self.s_id = self.socket.get_sid()
        LOGGER.info(f"sid: {self.s_id}")

    # Request handling methods

    def prepare_request_data(self, json_request_path):
        """prepares the requests data, returns json request and headers."""
        json_request = load_json_file(json_request_path)
        cookies_str, access_token_cookie_value, csrf_access_token_value = handle_cookies(self.cookies)
        req_headers = self.config["request_headers"]
        req_headers["Cookie"] = f"{cookies_str}"
        req_headers["Host"] = f"{self.host}"
        req_headers["Origin"] = f"{self.origin}"
        req_headers["Referer"] = f"{self.origin}/"
        req_headers["S_ID"] = f"{self.s_id}"
        req_headers["X-CSRF-TOKEN"] = f"{csrf_access_token_value}"
        req_headers["Cookie"] = f"{cookies_str}"
        return json_request, req_headers

    async def send_request(self, json_request, headers, json_request_path):
        """sends request using http post, returns request_id, response object."""
        response = await self.http_client.post(f"{self.server_path}report", json=json_request, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        request_id = response_json.get("id")  # Assuming the response contains the request ID
        if request_id:
            input_file_name = Path(json_request_path).stem
            async with self.request_id_lock:
                self.request_to_input_map[request_id] = input_file_name
                self.request_to_input_dir_map[request_id] = self.current_input_dir
                self.request_mapping_event.set()  # Signal that mapping is complete
            LOGGER.info(f"request: {request_id}, input file name {input_file_name}")
            return request_id, response
        else:
            LOGGER.error("No request ID found in response")
            return None, None

    @handle_exceptions("Request failed", False)
    async def send_request_get_response(self, json_request_path):
        """
        Sends a request to the server using the data in the specified JSON file.
        Returns:
            tuple: A tuple containing the request ID and the server's response object.
        """
        self.report_event.clear()  # Reset the event for the next report
        json_request, headers = self.prepare_request_data(json_request_path)

        request_id, response = await self.send_request(json_request, headers, json_request_path)
        return request_id, response

    # Report handling methods

    async def process_report(self, data):
        """Process incoming reports, either in order or handling late reports."""
        report_id = data.get("id")
        if not report_id:
            LOGGER.error("Report ID missing in data")
            return

        report_data = json.loads(data.get("data"))
        LOGGER.info(f"Report received for ID {report_id}")

        if report_id in self.pending_requests:
            self.pending_requests.remove(report_id)

        if report_id in self.request_to_input_map:
            input_dir = self.request_to_input_dir_map.get(report_id)

            if input_dir == self.current_input_dir:
                await self.save_output({"data": report_data, "id": report_id}, self.current_output_dir)
                self.report_event.set()

            else:
                await self.handle_late_report(report_id, report_data)
        else:
            LOGGER.error(f"Report ID {report_id} not found in request mapping")

    async def handle_late_report(self, report_id, data):
        inp_dir = self.request_to_input_dir_map.get(report_id)
        input_folder = os.path.basename(inp_dir)
        path = os.path.join(self.outputs_path, input_folder)
        LOGGER.warning(f"Late report received for ID {report_id} which should be in {inp_dir}")
        await self.save_output({"data": data, "id": report_id}, path)

    async def wait_for_report(self, request_id):
        try:
            await asyncio.wait_for(self.report_event.wait(), timeout=self.request_timeout)
        except asyncio.TimeoutError:
            input_file_name = self.request_to_input_map.get(request_id, "unknown")
            LOGGER.warning(f"Timeout occurred for request ID {request_id}, input file: {input_file_name}")

    @handle_exceptions("An error occurred while waiting for all reports", False)
    async def wait_for_all_reports(self, timeout=120):
        """
        Waits for all reports to be processed or until the timeout is reached.
        Args:
            timeout (int): The maximum time to wait for all reports, in seconds.
        """
        if self.pending_requests:
            LOGGER.info("Waiting for all reports to be completed...")
            await asyncio.wait([self.wait_for_report(request_id) for request_id in self.pending_requests], timeout=timeout)
            LOGGER.info("All reports have been completed.")
        else:
            LOGGER.info("No pending reports to wait for.")

    # Testing methods

    async def test_inputs(self, inputs_list=None):
        """
        Tests inputs in the input directory, either all or a specific list.
        Args:
            inputs_list (list, optional): A list of specific inputs to be tested. If None, all inputs will be tested.
        """
        if inputs_list is None:  # If inputs_list is not provided, test all inputs
            LOGGER.info("Started testing all inputs")
            directories = [os.path.join(self.input_path, rec) for rec in os.listdir(self.input_path)]
        else:  # If inputs_list is provided, test only those inputs
            LOGGER.info(f"Started testing inputs {inputs_list}")
            directories = [os.path.join(self.input_path, rec) for rec in inputs_list]

        for rec_dir in directories:
            await self.test_input(rec_dir)
            await asyncio.sleep(1)  # pause between processing

        await self.wait_for_all_reports()
        await self.close()

    @handle_exceptions("An error occurred during testing of specific input", False)
    async def test_input(self, inp_dir):
        """
        Tests an input directory.
        Args:
            inp_dir (str): The directory containing an input to be tested.
        """
        LOGGER.info(f"testing {inp_dir}")
        self.current_input_dir = inp_dir
        self.current_output_dir = await self.make_output_dir()
        LOGGER.info(f"made directory {self.current_output_dir}")
        lst = os.listdir(inp_dir)
        lst.sort()
        LOGGER.info(lst)
        for filename in lst:
            file_path = os.path.join(inp_dir, filename)
            if file_path.endswith(".json"):
                await self.process_request_file(file_path)
        LOGGER.info(f"all requests completed for {inp_dir}")

    async def process_request_file(self, file_path):
        LOGGER.info(f"sending request for file: {file_path}")
        request_id, _ = await self.send_request_get_response(file_path)
        if request_id:
            self.pending_requests.add(request_id)
            await self.wait_for_report(request_id)

    # Utilities
    async def make_output_dir(self):
        input_folder = os.path.basename(self.current_input_dir)
        path = os.path.join(self.outputs_path, input_folder)
        if not os.path.isdir(path):
            os.mkdir(path)
            LOGGER.info(f"created dir {path}")
        return path

    async def save_output(self, output_data, output_dir):
        """
        Saves the test output to a JSON file, naming it with the request ID and a timestamp.
        Returns:
            str: The path to the saved output file.
        """
        try:
            input_file_name = self.request_to_input_map.get(output_data["id"], "unknown")
            file_name = f"{input_file_name}.json"
            output_path = os.path.join(output_dir, file_name)
            saved = save_json_file(output_data, output_path)
            if saved:
                LOGGER.info(f"saved report {output_path}")
            return output_path
        except Exception as e:
            LOGGER.error(f"Failed to save output for request ID {output_data['id']}: {e}")

    # Cleanup methods

    async def close(self):
        """Closes the WebSocket connection and HTTP client they are open."""
        if self.socket:
            await self.socket.disconnect()

        if self.http_client:
            await self.http_client.aclose()
            LOGGER.info("HTTP client closed.")


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

    parser.add_argument("--mode", type=str, choices=["all", "specific"], default="all", help="Testing mode: 'all' or 'specific'")
    parser.add_argument("--specific_list", type=str, help="specific list of input directories")
    parser.add_argument("--expected_output", type=str, default="data/expectations", help="path to expectations")
    parser.add_argument(
        "--compare", type=str, choices=["yes", "no"], default="yes", help="Compare to previous outputs: 'yes' or 'no'"
    )
    parser.add_argument("--comparison_reports", type=str, default="data/comparison_reports", help="path to comparison reports")
    parser.add_argument("--request_timeout", type=int, default=60, help="request timeout in seconds")

    return parser.parse_args()


@handle_exceptions("An unexpected error occurred", False)
async def main():
    args = parse_args()

    # Load the configuration file
    config = load_json_file(args.config)
    LOGGER.info("loaded config file ")
    tester = WiserTester(args.username, args.password, args.request_timeout, config)

    await tester.start_test(args.specific_list.split(",") if args.mode == "specific" else None)
    if args.compare == "yes":
        LOGGER.info("Comparing outputs")
        comparison = Compare(args.output, args.expected_output, args.comparison_reports, config["ignore_paths"])
        report_paths = comparison.compare_outputs_with_expectations()
        LOGGER.info(f"Comparison reports: {report_paths}")

    await tester.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("interrupted")
