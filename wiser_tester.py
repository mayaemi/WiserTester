import asyncio
import json
import os
import sys
from pathlib import Path

import socketio
import httpx
import logging
import argparse
from deepdiff import DeepDiff

# Constants and configurations
LOGIN_URL = "/login"
LOGIN_JSON_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
LOG_FORMAT = '%(asctime)s | %(levelname)s | %(message)s'

# logger setup
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
formatter = logging.Formatter(LOG_FORMAT)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)
file_handler = logging.FileHandler('testlog.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
LOGGER.addHandler(file_handler)
LOGGER.addHandler(stdout_handler)


# Login related functions
async def login(username, password, server_path):
    """
    Logs into the application using provided credentials.
    Returns: HTTPX response object and cookies after successful login.
    """
    url = f"{server_path}{LOGIN_URL}"
    data = {"username": username, "password": password}
    try:
        with httpx.Client() as client:
            response = client.post(url, json=data, headers=LOGIN_JSON_HEADERS)
            response.raise_for_status()
            return response, response.cookies
    except Exception as e:
        LOGGER.error(f"Login failed: {e}")
        raise


def handle_cookies(response_cookies):
    """
        Extracts and formats required cookies from the HTTPX response.
        Returns:
            Formatted cookies string.
    """
    access_token_cookie = response_cookies.get('access_token_cookie')
    csrf_token = response_cookies.get('csrf_access_token')

    if not all([access_token_cookie, csrf_token]):
        LOGGER.error('Error: Missing required cookies')
        raise ValueError("Missing required cookies")

    cookies_str = f"access_token_cookie={access_token_cookie}; csrf_access_token={csrf_token}"
    return cookies_str, access_token_cookie, csrf_token


class Compare:
    def __init__(self, outputs_path, expectations_path, reports_path):
        self.outputs_path = outputs_path
        self.expectations_path = expectations_path
        self.reports_path = reports_path
        self.report_paths = []

    def compare_outputs_with_expectations(self):
        """ Compare the output files with expected outputs stored in a specified directory. """
        LOGGER.info(f"Comparing outputs to expectations")
        for output_folder in os.listdir(self.outputs_path):
            expectation_folder_path = os.path.join(self.expectations_path, output_folder)
            if os.path.isdir(expectation_folder_path):
                output_folder_path = os.path.join(self.outputs_path, output_folder)
                LOGGER.info(f"Comparing results for {output_folder}")
                self.compare_folder_outputs(output_folder_path, expectation_folder_path)
        return self.report_paths

    def compare_folder_outputs(self, output_folder_path, expectation_folder_path):
        """ Compare outputs in a specific folder with their expected counterparts. """
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
                LOGGER.info(f'Created directory {new_report_path}')

            # Compare the output file with the expected file
            if os.path.exists(expected_file_path):
                self.compare_and_save_report(input_file_name, output_file_path, expected_file_path, new_report_path)
            else:
                LOGGER.warning(f"No expectation file found for {input_file_name}")

    def save_comparison_report(self, report_json, path, input_file_name):
        """save comparison report to a json file."""
        file_name = f"{input_file_name}_comparison.json"
        output_path = os.path.join(path, file_name)
        report_path = output_path
        with open(output_path, "w") as file:
            json.dump(report_json, file, indent=2)
        return report_path

    def compare_and_save_report(self, input_file_name, output_file_path, expected_file_path, report_path):
        """ Compare an output file with its expected counterpart and save the report. """
        report = {}
        with open(output_file_path, 'r') as file:
            output_data = json.load(file).get('data')
        with open(expected_file_path, 'r') as file:
            expected_data = json.load(file).get('data')
        report['request_id'] = output_data.get('requestId')
        report['output_file'] = output_file_path
        report['expected_output_file'] = expected_file_path
        report['diff'] = DeepDiff(output_data, expected_data, ignore_order=True).to_json()
        self.report_paths.append(self.save_comparison_report(report, report_path, input_file_name))
        LOGGER.info(f"Comparison report generated for {input_file_name}")


class WiserTester:
    """ A class to handle automated testing using HTTP requests and SocketIO. """

    def __init__(self, input_path, outputs_path, username, password, host, origin, request_timeout):
        """
        Initializes the WiserTester instance.
        Args:
            input_path: Path to the directory containing inputs for tests.
            outputs_path: Path to the directory to save test outputs.
        """
        self.logger = LOGGER
        # self.socket = socketio.AsyncClient(logger=True, engineio_logger=True)
        self.socket = socketio.AsyncClient()
        self.username = username
        self.password = password
        self.host = host
        self.server_path = f"http://{host}/"
        self.origin = origin
        self.client_lock = asyncio.Lock()
        self.s_id = None
        self.input_path = input_path
        self.outputs_path = outputs_path
        self.current_input_dir = None
        self.current_output_dir = None
        self.request_id_lock = asyncio.Lock()  # Lock for synchronizing request ID mapping
        self.cookies = None
        self.request_to_input_map = {}  # dictionary to map request IDs to input file names
        self.request_to_input_dir_map = {}  # Map request IDs to input directories
        self.request_mapping_event = asyncio.Event()
        self.report_event = asyncio.Event()
        self.http_client = httpx.AsyncClient()
        self.request_timeout = request_timeout  # seconds
        self.pending_requests = set()

        # Event handlers
        @self.socket.event
        async def connect():
            self.logger.info("Socket connected")

        @self.socket.event
        async def disconnect():
            self.logger.info("Socket disconnected")

        @self.socket.event
        async def report_ready(data):
            await self.request_mapping_event.wait()  # Wait for the mapping event
            self.request_mapping_event.clear()  # Clear the event for the next report

            report_id = data.get('id')
            if report_id and report_id in self.request_to_input_map:
                input_dir = self.request_to_input_dir_map.get(report_id)
                report_data = json.loads(data.get('data'))

                if input_dir == self.current_input_dir:
                    # Normal handling of the report
                    self.logger.info(f"Report received for ID {report_id}")
                    await self.save_output({"data": report_data, "id": report_id}, self.current_output_dir)
                else:
                    # Late report handling
                    await self.handle_late_report(report_id, report_data)
            else:
                self.logger.error(f"Report ID {report_id} not found in request mapping")
            # Set the event to signal that the report has been processed
            self.report_event.set()

        @self.socket.event
        async def error(data):
            error_msg = data.get('error')
            report_id = data.get('id')
            if report_id:
                async with self.client_lock:
                    self.logger.error(f"Error for ID {report_id}: {error_msg}")

    async def connect_to_server(self):
        """Establishes connection to the server."""
        try:
            await self.socket.connect(self.server_path)
            self.s_id = self.socket.get_sid()
            self.logger.info(f'sid: {self.s_id}')
        except socketio.exceptions.ConnectionError as e:
            self.logger.error(f"Socket connection failed: {e}")
            raise e

    async def make_output_dir(self):
        input_folder = os.path.basename(self.current_input_dir)
        path = os.path.join(self.outputs_path, input_folder)
        if not os.path.isdir(path):
            os.mkdir(path)
            LOGGER.info(f'created dir {path}')
        return path

    async def save_output(self, output_data, output_dir):
        """
        Saves the test output to a JSON file, naming it with the request ID and a timestamp.
        Args:
            output_data (dict): The data to be saved as the test output.
        Returns:
            str: The path to the saved output file.
        """
        input_file_name = self.request_to_input_map.get(output_data['id'], "unknown")
        file_name = f"{input_file_name}.json"
        output_path = os.path.join(output_dir, file_name)
        with open(output_path, "w") as file:
            json.dump(output_data, file, indent=2)
        return output_path

    def prepare_request_data(self, json_request_path):
        with open(json_request_path, "r") as file:
            json_request_str = file.read()

        json_request = json.loads(json_request_str)
        cookies_str, access_token_cookie_value, csrf_access_token_value = handle_cookies(self.cookies)
        req_headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Cookie': f'{cookies_str}',
            'Host': f'{self.host}',
            'Origin': f"{self.origin}",
            'Referer': f'{self.origin}/',
            'S_ID': f'{self.s_id}',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'X-CSRF-TOKEN': csrf_access_token_value,
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        return json_request, req_headers

    async def send_request(self, json_request, headers, json_request_path):
        response = await self.http_client.post(f'{self.server_path}report', json=json_request, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        request_id = response_json.get('id')  # Assuming the response contains the request ID
        if request_id:
            input_file_name = Path(json_request_path).stem
            async with self.request_id_lock:
                self.request_to_input_map[request_id] = input_file_name
                self.request_to_input_dir_map[request_id] = self.current_input_dir
                self.request_mapping_event.set()  # Signal that mapping is complete
            self.logger.info(f"request: {request_id}, input file name {input_file_name}")
            return request_id, response
        else:
            self.logger.error("No request ID found in response")
            return None, None

    async def send_request_get_response(self, json_request_path):
        """
        Sends a request to the server using the data in the specified JSON file.
        Args:
            json_request_path (str): The file path of the JSON file containing the request data.
        Returns:
            tuple: A tuple containing the request ID and the server's response object.
        """
        self.report_event.clear()  # Reset the event for the next report
        json_request, headers = self.prepare_request_data(json_request_path)

        try:
            request_id, response = await self.send_request(json_request, headers, json_request_path)
            return request_id, response

        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            return None, None

    async def process_file(self, file_path):
        self.logger.info(f'sending request for file: {file_path}')
        request_id, _ = await self.send_request_get_response(file_path)
        if request_id:
            self.pending_requests.add(request_id)
            await self.handle_response(request_id)

    async def handle_late_report(self, report_id, data):
        inp_dir = self.request_to_input_dir_map.get(report_id)
        input_folder = os.path.basename(inp_dir)
        path = os.path.join(self.outputs_path, input_folder)
        self.logger.warning(f"Late report received for ID {report_id} which should be in {inp_dir}")
        await self.save_output({"data": data, "id": report_id}, path)

    async def log_skipped_report(self, request_id):
        input_file_name = self.request_to_input_map.get(request_id, "unknown")
        self.logger.error(f"Skipped report for request ID {request_id}, input file: {input_file_name} due to timeout")

    async def handle_response(self, request_id):
        try:
            await asyncio.wait_for(self.report_event.wait(), timeout=self.request_timeout)
            self.logger.info(f"Report processed for request ID {request_id}")
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout occurred for request ID {request_id}")
            await self.log_skipped_report(request_id)
        finally:
            self.pending_requests.discard(request_id)

    async def test_input(self, inp_dir):
        """
        Tests an input directory.
        Args:
            inp_dir (str): The directory containing an input to be tested.
        """
        try:
            self.logger.info(f'testing {inp_dir}')
            self.current_input_dir = inp_dir
            self.current_output_dir = await self.make_output_dir()
            self.logger.info(f'made directory {self.current_output_dir}')
            lst = os.listdir(inp_dir)
            lst.sort()
            self.logger.info(lst)
            for filename in lst:
                file_path = os.path.join(inp_dir, filename)
                if file_path.endswith(".json"):
                    await self.process_file(file_path)
            self.logger.info(f'all requests completed for {inp_dir}')
            await self.wait_for_all_reports()
        except Exception as e:
            self.logger.error(f"An error occurred during testing {inp_dir}: {e}")

    async def wait_for_all_reports(self):
        while self.pending_requests:
            await asyncio.sleep(1)  # Sleep briefly to avoid busy waiting
        self.logger.info("All reports processed or skipped for the current input folder.")

    async def test_all(self):
        """ Tests all inputs in the input directory. """
        self.logger.info(f'started testing all inputs')
        for rec in os.listdir(self.input_path):
            rec_dir = os.path.join(self.input_path, rec)
            await self.test_input(rec_dir)
            await asyncio.sleep(1)
        await self.close()

    async def test_specific(self, inputs_list):
        """
        Tests a specific list of inputs.
        Args:
            inputs_list (list): A list of specific inputs to be tested.
        """
        self.logger.info(f'started testing inputs {inputs_list}')
        for rec in inputs_list:
            rec_dir = os.path.join(self.input_path, rec)
            await self.test_input(rec_dir)
            await asyncio.sleep(1)
        await self.close()

    async def start_test(self, specific_inputs=None):
        """
            Starts the testing process. Tests either all inputs or a specific list of inputs.
            Args:
                specific_inputs (list, optional): A list of specific inputs to be tested. If None, all inputs will be tested.
        """
        # Perform login and store cookies
        _, self.cookies = await login(self.username, self.password, self.server_path)
        self.logger.info(f'Logged in and obtained cookies {self.cookies}')

        await self.connect_to_server()

        if specific_inputs:
            await self.test_specific(specific_inputs)
        else:
            await self.test_all()
        await self.socket.wait()

    async def close(self):
        """ Closes the WebSocket connection if it is open. """
        # Close the WebSocket connection if it is open
        if self.socket:
            await self.socket.disconnect()

        # Close the HTTP client
        if self.http_client:
            await self.http_client.aclose()
            self.logger.info("HTTP client closed.")


def parse_args():
    parser = argparse.ArgumentParser(description="Run Wiser Tester")
    parser.add_argument("--host", type=str, required=True, help="host name (ex. localhost:5000")
    parser.add_argument("--origin", type=str, required=True, help="origin  (ex. http://localhost:5050")
    parser.add_argument("--username", type=str, required=True, help="Username for login")
    parser.add_argument("--password", type=str, required=True, help="Password for login")
    parser.add_argument("--mode", type=str, choices=['all', 'specific'], default='all',
                        help="Testing mode: 'all' or 'specific'")
    parser.add_argument("--specific_list", type=str, help="specific list of input directories")
    parser.add_argument("--input", type=str, default="data/inputs", help="Path to the inputs directory")
    parser.add_argument("--output", type=str, default="data/outputs", help="Path to save outputs")
    parser.add_argument("--expected_output", type=str, default='data/expectations', help="path to expectations")
    parser.add_argument("--compare", type=str, choices=['yes', 'no'], default='yes',
                        help="Compare to previous outputs: 'yes' or 'no'")
    parser.add_argument("--comparison_reports", type=str, default='data/comparison_reports',
                        help="path to comparison reports")
    parser.add_argument("--request_timeout", type=int, default=60, help="request timeout in seconds")

    return parser.parse_args()


async def main():
    args = parse_args()

    tester = WiserTester(args.input, args.output, args.username, args.password, args.host, args.origin,
                         args.request_timeout)

    try:
        await tester.start_test(args.specific_list.split(',') if args.mode == 'specific' else None)
        if args.compare == 'yes':
            LOGGER.info('Comparing outputs')
            comparison = Compare(args.output, args.expected_output, args.comparison_reports)
            report_paths = comparison.compare_outputs_with_expectations()
            LOGGER.info(f'Comparison reports: {report_paths}')
    except httpx.HTTPError as e:
        LOGGER.error(f"HTTP error occurred: {e}")
    except socketio.exceptions.ConnectionError as e:
        LOGGER.error(f"WebSocket connection error: {e}")
    except Exception as e:
        LOGGER.error(f"An unexpected error occurred: {e}")
    finally:
        await tester.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"interrupted")
