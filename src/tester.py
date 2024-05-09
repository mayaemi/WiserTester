import asyncio
from datetime import datetime
import json
import os
import shutil
from pathlib import Path
import socketio
import httpx
from src.exceptions import handle_exceptions
from src.configure import LOGGER
from src.auth import handle_cookies, login
from src.utils import contains_csv_data, json_to_csv, load_json_file, save_json_file, extract_timestamp_from_filename


class WiserTester:
    def __init__(self, username, password, request_timeout, config, exclude_inputs, input_dir=None, output_dir=None):
        """
        Initializes the WiserTester instance.
        Args:
            username (str): Username for login.
            password (str): Password for login.
            request_timeout (int): Timeout for waiting on reports.
            config (dict): Config file dictionary
            exclude_inputs (lst): List of input files to exclude
        """
        self.socket = socketio.AsyncClient(reconnection_attempts=10)
        self.http_client = httpx.AsyncClient()
        self.username = username
        self.password = password
        self.host = config["host"]
        self.origin = config["origin"]
        self.input_dir = input_dir or config["input_dir"]
        self.output_dirs = output_dir or config["output_dir"]
        self.exclude_inputs = exclude_inputs
        self.server_path = f"http://{self.host}/"
        self.request_timeout = request_timeout  # seconds
        self.config = config
        self.s_id, self.cookies = None, None
        self.current_input_dir, self.current_output_dir = None, None
        self.is_connected = False
        self.request_to_input_map = {}  # dictionary to map request IDs to input file names
        self.request_to_input_dir_map = {}  # Map request IDs to input directories
        self.request_mapping_event = asyncio.Event()
        self.report_event = asyncio.Event()
        self.request_id_lock = asyncio.Lock()  # Lock for synchronizing request ID mapping
        self.client_lock = asyncio.Lock()
        self.pending_requests = set()
        self.version_info = None
        self.is_csv = []

        # Define event handlers for the socket events
        self._define_event_handlers()

    async def start_test(self, specific_inputs=None):
        """
        Starts the testing process. Tests either all inputs or a specific list of input directories.
        Args:
            specific_inputs (list, optional): A list of specific inputs to be tested. If None, all inputs will be tested.
        """
        # Perform login and store cookies
        _, self.cookies = await login(self.username, self.password, self.server_path)
        LOGGER.info(f"Logged in and obtained cookies {self.cookies}")

        await self.connect_to_server()

        await self.get_version_info()
        await self.save_version_info()

        await self.test_inputs(specific_inputs)

        # await self.socket.wait()

    def _define_event_handlers(self):
        """Define event handlers for socket events."""

        @self.socket.event
        async def connect():
            LOGGER.info("Socket connected")
            self.s_id = self.socket.get_sid()
            LOGGER.info(f"sid: {self.s_id}")
            self.is_connected = True

        @self.socket.event
        async def disconnect():
            LOGGER.info("Socket disconnected")
            self.is_connected = False

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
        await asyncio.sleep(0.3)
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
        await self.socket.connect(self.server_path, wait_timeout=10, transports=["websocket", "polling"])

    async def get_version_info(self):
        """retrieve the wiser version information from server"""
        request_id, _ = await self.send_request_get_response("get_version")
        if request_id:
            self.pending_requests.add(request_id)
            await self.wait_for_report(request_id)
        return request_id

    # Request handling methods

    def prepare_request_data(self, json_request):
        """prepares the requests data, returns json request and headers."""
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

    async def send_request(self, json_request, headers, input_file_name):
        """sends request using http post, returns request_id, response object."""
        response = await self.http_client.post(f"{self.server_path}report", json=json_request, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        request_id = response_json.get("id")
        if request_id:
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
        Sends a request to the server and waits for the response.
        Args:
            json_request_path (str): Path to the JSON file with request data.
        Returns:
            tuple: (request_id, response) if successful, None otherwise.
        """
        self.report_event.clear()  # Reset the event for the next report

        # Wait for the socket to be connected before proceeding
        while not self.is_connected:
            LOGGER.info("Waiting for socket to reconnect...")
            await asyncio.sleep(1)  # Check connection status every second

        if json_request_path == "get_version":
            json_request = self.config["version_request"]
            input_file_name = json_request_path
        else:
            json_request = load_json_file(json_request_path)
            input_file_name = Path(json_request_path).stem

        json_request, headers = self.prepare_request_data(json_request)

        request_id, response = await self.send_request(json_request, headers, input_file_name)
        return request_id, response

    # Report handling methods

    async def process_report(self, data):
        """
        Processes an incoming report by updating internal states and handling data accordingly.
        Args:
            report_data (dict): The report data received from the server.
        """
        report_id = data.get("id")
        if not report_id:
            LOGGER.error("Report ID missing in data")
            return
        report_data = json.loads(data.get("data"))
        LOGGER.info(f"Report received for ID {report_id}")

        if report_id in self.pending_requests:
            self.pending_requests.remove(report_id)

        if report_data.get("messageType") == "retData":
            if report_data.get("dataType") == "appVersion":
                self.version_info = report_data.get("data")
                LOGGER.info(f"got version info {self.version_info}")
                self.report_event.set()
                return

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
        """
        Handles specific late report data based on the id received.
        Args:
            report_id (str): The unique identifier for the report.
            report_data (dict): The report data.
        """
        inp_dir = self.request_to_input_dir_map.get(report_id)
        input_folder = os.path.basename(inp_dir)
        path = os.path.join(self.output_dirs, input_folder)
        LOGGER.warning(f"Late report received for ID {report_id} which should be in {inp_dir}")
        await self.save_output({"data": data, "id": report_id}, path)

    async def wait_for_report(self, request_id):
        """wait for specific report from server, if timeout occurs, issue warning"""
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
            directories = [os.path.join(self.input_dir, f) for f in os.listdir(self.input_dir) if f != ".gitkeep"]
        else:  # If inputs_list is provided, test only those inputs
            LOGGER.info(f"Started testing inputs {inputs_list}")
            directories = [os.path.join(self.input_dir, rec) for rec in inputs_list]

        for rec_dir in directories:
            await self.test_input(rec_dir)
            await asyncio.sleep(1)  # pause between inputs

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
        files_sorted = sorted(lst, key=lambda x: extract_timestamp_from_filename(x))
        LOGGER.info(files_sorted)
        for filename in files_sorted:
            if filename not in self.exclude_inputs:
                file_path = os.path.join(inp_dir, filename)
                if file_path.endswith(".json"):
                    await self.process_request_file(file_path)
            else:
                LOGGER.info(f"ignoring {filename}")
        LOGGER.info(f"all requests completed for {inp_dir}")

    async def process_request_file(self, file_path):
        LOGGER.info(f"sending request for file: {file_path}")
        request_id, _ = await self.send_request_get_response(file_path)
        if request_id:
            self.pending_requests.add(request_id)
            await self.wait_for_report(request_id)

    # Utilities

    async def make_output_dir(self):
        """
        creates a new directory in the `outputs_dir` based on the current input directory and copies a version info file into it.
        :return: The `make_output_dir` method returns the path of the newly created output directory.
        """

        input_folder = os.path.basename(self.current_input_dir)
        path = os.path.join(self.output_dirs, input_folder)
        if not os.path.isdir(path):
            os.mkdir(path)
            LOGGER.info(f"created dir {path}")
            version_info_src = os.path.join(self.output_dirs, "version_info.json")
            version_info_dest = os.path.join(path, "version_info.json")
            shutil.copy(version_info_src, version_info_dest)
            LOGGER.info(f"Copied version info to {path}")
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
            self.handle_csv(output_data, output_dir, input_file_name)
            return output_path
        except Exception as e:
            LOGGER.error(f"Failed to save output for request ID {output_data['id']}: {e}")

    @handle_exceptions("An error occurred during csv checks", False)
    def handle_csv(self, output_data, output_dir, input_file_name):
        """This function handles CSV data by converting JSON data to a CSV file.
        Args:
            output_data: Output data containing information to be processed
            output_dir: The directory where the CSV file will be saved after the conversion from JSON to CSV is completed
            input_file_name: The name of the input file being processed.
        """
        if contains_csv_data(output_data):
            csv_data = output_data.get("data", {}).get("data", None)
            csv_path = os.path.join(output_dir, f"{input_file_name}.csv")
            json_to_csv(csv_data, csv_path)

    async def save_version_info(self):
        """
        Saves the version information to a JSON file in a designated location.
        """
        if self.version_info:
            version_info_path = os.path.join(self.output_dirs, "version_info.json")
            with open(version_info_path, "w") as file:
                json.dump(self.version_info, file)
            LOGGER.info("Version information saved.")
        else:
            LOGGER.error("Version information is not available to save.")

    # Cleanup methods

    async def close(self):
        """Closes the WebSocket connection and HTTP client they are open."""
        if self.socket:
            await self.socket.disconnect()

        if self.http_client:
            await self.http_client.aclose()
            LOGGER.info("HTTP client closed.")
