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

# configurations
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)
file_handler = logging.FileHandler('testlog.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
LOGGER.addHandler(file_handler)
LOGGER.addHandler(stdout_handler)


# login using httpx

async def login(username, password, server_path):
    """
    Logs into the application using provided credentials.
    Returns:
        HTTPX response object and cookies after successful login.
    """
    url = server_path + "login"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    data = {"username": username, "password": password}

    try:
        with httpx.Client() as client:
            response = client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response, response.cookies
    except Exception as e:
        LOGGER.error(f"Login failed: {e}")
        raise


# helpers

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


def save_comparison_report(report_json, path, input_file_name):
    """save comparison report to a json file."""
    file_name = f"{input_file_name}_comparison.json"
    output_path = os.path.join(path, file_name)
    report_path = output_path
    with open(output_path, "w") as file:
        json.dump(report_json, file, indent=2)
    return report_path


def compare_outputs_with_expectations(outputs_path, expectations_path, reports_path):
    """
    Compare the output files with expected outputs stored in a specified directory.
    """
    LOGGER.info(f"Comparing outputs to expectations")
    report_paths = []
    for output_folder in os.listdir(outputs_path):
        if os.path.isdir(os.path.join(expectations_path, output_folder)):
            output_folder_path = os.path.join(outputs_path, output_folder)
            LOGGER.info(f"Comparing results for {output_folder}")
            for output_file in os.listdir(output_folder_path):
                input_file_name, _ = os.path.splitext(output_file)
                expected_file_name = f"{input_file_name}.json"
                expected_file_path = os.path.join(expectations_path, output_folder, expected_file_name)
                output_file_path = os.path.join(output_folder_path, output_file)
                report_path = os.path.join(reports_path, output_folder)

                if not os.path.isdir(report_path):
                    os.mkdir(report_path)
                    LOGGER.info(f'Created directory {report_path}')

                report = {}
                if os.path.exists(expected_file_path):
                    with open(output_file_path, 'r') as file:
                        output_data = json.load(file).get('data')
                    with open(expected_file_path, 'r') as file:
                        expected_data = json.load(file).get('data')
                    report['request_id'] = output_data.get('requestId')
                    report['output_file'] = output_file_path
                    report['expected_output_file'] = expected_file_path
                    report['diff'] = DeepDiff(output_data, expected_data, ignore_order=True).to_json()
                    report_paths.append(save_comparison_report(report, report_path, input_file_name))
                    LOGGER.info(f"Comparison report generated for {input_file_name}")
                else:
                    LOGGER.warning(f"No expectation file found for {input_file_name}")
    return report_paths


class WiserTester:
    """
    A class to handle automated testing using HTTP requests and SocketIO.
    """

    def __init__(self, input_path, outputs_path, username, password, host, origin):
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
        self.outputs = {}
        self.host = host
        self.server_path = f"http://{host}/"
        self.origin = origin
        self.client_lock = asyncio.Lock()
        self.s_id = None
        self.input_path = input_path
        self.outputs_path = outputs_path
        self.current_input_dir = None
        self.current_output_dir = None
        self.cookies = None
        self.request_to_input_map = {}  # dictionary to map request IDs to input file names
        self.request_id_lock = asyncio.Lock()  # Lock for synchronizing request ID mapping
        self.report_queue = asyncio.Queue()  # Initialize a queue for reports

        # Event handlers
        @self.socket.event
        async def connect(): self.logger.info("Socket connected")

        @self.socket.event
        async def disconnect(): self.logger.info("Socket disconnected")

        @self.socket.event
        async def report_ready(data):
            await self.report_queue.put(data)  # Enqueue the report data
            self.logger.info(f"Report queued with ID {data.get('id')}")

        @self.socket.event
        async def error(data):
            error_msg = data.get('error')
            report_id = data.get('id')
            if report_id:
                async with self.client_lock:
                    self.outputs[report_id] = {'error': error_msg}
                    self.logger.error(f"Error for ID {report_id}: {error_msg}")

    async def connect_to_server(self):
        """Establishes connection to the server."""
        try:
            await self.socket.connect(self.server_path)
            self.s_id = self.socket.get_sid()
            self.logger.info(f'sid: {self.s_id}')
        except socketio.exceptions.ConnectionError as e:
            self.logger.error(f"Socket connection failed: {e}")
            raise

    async def process_report_queue(self):
        while not self.report_queue.empty():
            try:
                data = await asyncio.wait_for(self.report_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            report_id = data.get('id')
            if report_id:
                async with self.client_lock:
                    async with self.request_id_lock:
                        if report_id in self.request_to_input_map:
                            report_data = json.loads(data.get('data'))
                            self.outputs[report_id] = report_data
                            self.logger.info(f"Processing report with ID {report_id}")
                            await self.save_output({"data": report_data, "id": report_id})
                        else:
                            self.logger.error(f"Report ID {report_id} not found in request mapping")
            self.report_queue.task_done()

    async def check_for_reports(self, req_lst):
        not_ready = []
        for req in req_lst:
            file_path = os.path.join(self.current_output_dir, req)
            if not os.path.isfile(file_path):
                not_ready.append(file_path)
        return not_ready

    async def make_output_dir(self):
        input_folder = os.path.basename(self.current_input_dir)
        path = os.path.join(self.outputs_path, input_folder)
        if not os.path.isdir(path):
            os.mkdir(path)
            LOGGER.info(f'created dir {path}')
        return path

    async def save_output(self, output_data):
        """
        Saves the test output to a JSON file, naming it with the request ID and a timestamp.
        Args:
            output_data (dict): The data to be saved as the test output.
        Returns:
            str: The path to the saved output file.
        """
        input_file_name = self.request_to_input_map.get(output_data['id'], "unknown")
        file_name = f"{input_file_name}.json"
        output_path = os.path.join(self.current_output_dir, file_name)
        with open(output_path, "w") as file:
            json.dump(output_data, file, indent=2)
        return output_path

    async def get_output(self, req_id):
        """ Retrieves the test output associated with the given request ID. """
        return self.outputs.get(req_id)

    async def send_request_get_response(self, json_request_path):
        """
        Sends a request to the server using the data in the specified JSON file.
        Args:
            json_request_path (str): The file path of the JSON file containing the request data.
        Returns:
            tuple: A tuple containing the request ID and the server's response object.
        """
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

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f'{self.server_path}report', json=json_request,
                                             headers=req_headers)
                response.raise_for_status()
                response_json = response.json()
                request_id = response_json.get('id')  # Assuming the response contains the request ID

                if request_id:
                    # Lock the section where the request ID is mapped to the input file name
                    async with self.request_id_lock:
                        input_file_name = Path(json_request_path).stem
                        self.request_to_input_map[request_id] = input_file_name
                        self.logger.info(f"request: {request_id}, input file name {input_file_name}")
                    return request_id, response
                else:
                    self.logger.error("No request ID found in response")
                    return None, None

        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            return None, None

    async def test_input(self, inp_dir):
        """
        Tests an input directory.
        Args:
            inp_dir (str): The directory containing an input to be tested.
        """
        self.logger.info(f'testing {inp_dir}')
        self.current_input_dir = inp_dir
        self.current_output_dir = await self.make_output_dir()
        self.logger.info(f'made directory {self.current_output_dir}')
        responses = []
        lst = os.listdir(inp_dir)
        lst.sort()
        self.logger.info(lst)
        for filename in lst:
            file_path = os.path.join(inp_dir, filename)
            if file_path.endswith(".json"):
                self.logger.info(f'sending request for file: {file_path}')
                response = await self.send_request_get_response(file_path)
                request_id, _ = response
                responses.append(response)
                self.logger.info(f'response: {response}')
                await asyncio.sleep(2)
        self.logger.info(f'all requests completed for {inp_dir}')
        await self.process_report_queue()  # Process the queued reports for this input folder
        not_ready = await self.check_for_reports(lst)
        while not_ready:
            self.logger.info(f"reports: {not_ready} are not ready")
            await self.process_report_queue()  # Process the queued reports for this input folder
            not_ready = await self.check_for_reports(lst)

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
        if self.socket:
            await self.socket.disconnect()


def parse_args():
    parser = argparse.ArgumentParser(description="Run Wiser Tester")
    parser.add_argument("--host", type=str, required=True, help="host name (ex. localhost:5000")
    parser.add_argument("--origin", type=str, required=True, help="origin  (ex. http://localhost:5050")
    parser.add_argument("--username", type=str, required=True, help="Username for login")
    parser.add_argument("--password", type=str, required=True, help="Password for login")
    parser.add_argument("--mode", type=str, choices=['all', 'specific'], default='all',
                        help="Testing mode: 'all' or 'specific'")
    parser.add_argument("--specific_list", type=str,
                        help="specific list of input directories")
    parser.add_argument("--input", type=str, default="data/inputs",
                        help="Path to the inputs directory")
    parser.add_argument("--output", type=str, default="data/outputs",
                        help="Path to save outputs")
    parser.add_argument("--expected_output", type=str, default='data/expectations',
                        help="path to expectations")
    parser.add_argument("--compare", type=str, choices=['yes', 'no'], default='yes',
                        help="Compare to previous outputs: 'yes' or 'no'")
    parser.add_argument("--comparison_reports", type=str, default='data/comparison_reports',
                        help="path to comparison reports")

    return parser.parse_args()


async def main():
    args = parse_args()

    tester = WiserTester(args.input, args.output, args.username, args.password, args.host, args.origin)

    try:
        await tester.start_test(args.specific_list.split(',') if args.mode == 'specific' else None)
        if args.compare == 'yes':
            LOGGER.info('Comparing outputs')
            report_paths = compare_outputs_with_expectations(args.output, args.expected_output, args.comparison_reports)
            LOGGER.info(f'Comparison reports: {report_paths}')
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")
    finally:
        await tester.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"interrupted")