import asyncio
import datetime
import glob
import json
import os
import re
import sys
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
    Args:
        username: Username for login.
        password: Password for login.
    Returns:
        HTTPX response object and cookies after successful login.
    """
    url = server_path + "login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        # Other headers as necessary
    }
    data = {
        "username": username,
        "password": password
    }

    try:
        with httpx.Client() as client:
            response = client.post(url, json=data, headers=headers)
            response.raise_for_status()
            cookies = response.cookies
            return response, cookies
    except Exception as e:
        LOGGER.error(f"Login failed: {e}")
        return None, None


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
        return None, None, None

    cookies_str = f"access_token_cookie={access_token_cookie}; csrf_access_token={csrf_token}"
    return cookies_str, access_token_cookie, csrf_token


def get_most_recent_outputs(outputs_path):
    """
    Finds the most recent output file for each request ID in the specified directory.
    Args:
        outputs_path: Path to the directory containing output files.
    Returns:
        A dictionary mapping each request ID to its most recent output file path.
    """
    pattern = re.compile(r"([a-f0-9\-]+)_at_(\d{8}_\d{6})\.json")
    most_recent_outputs = {}
    LOGGER.info(f"Scanning directories: {outputs_path}")

    for output in os.listdir(outputs_path):
        most_recent_output = {}
        LOGGER.info(f"Scanning directory: {output}")
        for file_path in glob.glob(os.path.join(outputs_path, output, "*.json")):
            match = pattern.match(os.path.basename(file_path))
            if match:
                request_id, timestamp = match.groups()
                timestamp = datetime.datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                if request_id not in most_recent_output or most_recent_output[request_id][1] < timestamp:
                    most_recent_output[request_id] = (file_path, timestamp)

        rec_most_recent_output = {req_id: path for req_id, (path, _) in most_recent_output.items()}
        most_recent_outputs[output] = rec_most_recent_output
    return most_recent_outputs


def save_comparison_report(report_json, path):
    """save comparison report to a json file."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"comparison_{report_json['request_id']}_at_{timestamp}.json"
    output_path = os.path.join(path, file_name)
    with open(output_path, "w") as file:
        json.dump(report_json, file, indent=2)
    return output_path


def compare_outputs_with_expectations(most_recent_outputs, expectations_path, reports_path):
    """
    Compares the most recent outputs with expected outputs stored in a specified directory.
    Args:
        most_recent_outputs: A dictionary mapping request IDs to their most recent output file path.
        expectations_path: Path to the directory containing expected outputs files.
    """
    LOGGER.info(f"comparing {most_recent_outputs} to expectations")
    report_paths = []
    for output in most_recent_outputs:
        path = os.path.join(reports_path, output)
        if not os.path.isdir(path):
            os.mkdir(path)
            LOGGER.info(f'created dir {path}')
        most_recent_output = most_recent_outputs[output]
        LOGGER.info(f'most recent is {most_recent_output}')

        for request_id, output_file in most_recent_output.items():
            expected_file_path = os.path.join(expectations_path, output, f"expected_{request_id}.json")
            LOGGER.info(f'expected_file_path is {most_recent_output}')

            report = {}
            if os.path.exists(expected_file_path):
                with open(output_file, 'r') as file:
                    output_data = json.load(file).get('data')
                with open(expected_file_path, 'r') as file:
                    expected_data = json.load(file).get('data')
                report['request_id'] = request_id
                report['latest_output_file'] = output_file
                report['expected_output_file'] = expected_file_path
                diff = DeepDiff(output_data, expected_data, ignore_order=True)
                report['diff'] = diff.to_json()
                if diff == {}:
                    msg = f"Output for Request ID {request_id} matches the expectation."
                else:
                    msg = f"Output for Request ID {request_id} does not match the expectation. Differences: {diff}"
                report['summary'] = msg
                report_paths.append(save_comparison_report(report, path))
            else:
                msg = f"No expectation file found for Request ID {request_id}."
            LOGGER.info(msg)
    return report_paths


class WiserTester:
    """
    A class to handle automated testing using HTTP requests and SocketIO.
    """

    def __init__(self, input_path, ouputs_path, username, password, host, origin):
        """
        Initializes the WiserTester instance.
        Args:
            input_path: Path to the directory containing inputs for tests.
            ouputs_path: Path to the directory to save test outputs.
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
        self.outputs_path = ouputs_path
        self.current_input_dir = None
        self.current_output_dir = None
        self.cookies = None

        # Event handlers
        @self.socket.event
        async def connect():
            self.logger.info("Socket connected")

        @self.socket.event
        async def disconnect():
            self.logger.info("Socket disconnected")

        @self.socket.event
        async def report_ready(data):
            report_id = data.get('id')
            if report_id:
                async with self.client_lock:
                    report_data = json.loads(data.get('data'))
                    if not (report_data.get('requestId') is None):
                        request_id = report_data['requestId']
                        self.outputs[report_id] = report_data
                        self.logger.info(f"Received data for request ID {request_id}")
                        await self.save_output(request_id, {"data": report_data, "id": report_id})
                    else:
                        self.logger.info(f"Received data without request ID {report_data}")

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

    async def make_output_dir(self):
        input_folder = os.path.basename(self.current_input_dir)
        path = os.path.join(self.outputs_path, input_folder)
        if not os.path.isdir(path):
            os.mkdir(path)
            LOGGER.info(f'created dir {path}')
        return path

    async def save_output(self, request_id, output_data):
        """
        Saves the test output to a JSON file, naming it with the request ID and a timestamp.
        Args:
            request_id (str): The ID of the request associated with the test output.
            output_data (dict): The data to be saved as the test output.
        Returns:
            str: The path to the saved output file.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{request_id}_at_{timestamp}.json"
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
                response = await client.post(f'{self.server_path}report', json=json_request, headers=req_headers)
                response.raise_for_status()
                response_json = response.json()
                request_id = response_json.get('id')  # Assuming the response contains the request ID
                return request_id, response

        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            return None, None

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
        for filename in os.listdir(inp_dir):
            file_path = os.path.join(inp_dir, filename)
            if file_path.endswith(".json"):
                response = await self.send_request_get_response(file_path)
                self.logger.info(f'request sent for file: {file_path}')
                request_id, _ = response
                responses.append(response)
                self.logger.info(f'response: {response}')
                await asyncio.sleep(2)

        self.logger.info(f'all requests completed for {inp_dir}')

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

'''
HOST = "localhost:5000"
SERVER_PATH = f"http://{HOST}/"
ORIGIN = "http://localhost:5050"
'''

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
    host = args.host
    origin = args.origin
    inputs_path = args.input
    outputs_path = args.output
    expectations_path = args.expected_output
    comparison_reports_path = args.comparison_reports
    username = args.username
    password = args.password

    test = WiserTester(inputs_path, outputs_path, username, password, host, origin)

    try:
        if args.mode == 'all':
            await test.start_test()
        elif args.mode == 'specific':
            specific_inputs_str = args.specific_list
            specific_inputs = specific_inputs_str.split(',')
            LOGGER.info(specific_inputs)
            await test.start_test(specific_inputs)
    except Exception as e:
        LOGGER.error(f"An error occurred: {e.with_traceback()}")
    finally:
        await test.close()

    if args.compare == 'yes':
        LOGGER.info('comparing outputs')
        # Read and get most recent outputs
        most_recent_outputs = get_most_recent_outputs(outputs_path)
        # Compare outputs
        report_paths = compare_outputs_with_expectations(most_recent_outputs, expectations_path,
                                                         comparison_reports_path)
        LOGGER.info(f'comparison reports: {report_paths}')


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"interrupted")
