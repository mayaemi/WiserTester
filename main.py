import asyncio
import datetime
import json
import os
import sys
import socketio
import httpx
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import logging
import argparse

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

SERVER_PATH = "http://localhost:5000/"
ORIGIN = "http://localhost:5050/"


# selenium

def driver_setup():
    chrome_options = Options()
    chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    return driver


def login():
    driver = driver_setup()
    driver.get(ORIGIN)

    # print(self.driver.current_url)
    driver.maximize_window()

    WebDriverWait(driver, timeout=100).until(lambda d: d.find_element(By.NAME, "username"))
    driver.find_element(By.NAME, "username").click()
    driver.find_element(By.NAME, "username").send_keys("maya")

    driver.find_element(By.NAME, "password").click()
    driver.find_element(By.NAME, "password").send_keys("mayah")
    driver.find_element(By.XPATH, "//button[contains(.,'Login')]").click()

    # print(driver.current_url)
    # Wait for the authentication to complete
    WebDriverWait(driver, timeout=10).until(
        lambda d: d.find_element(By.XPATH, "//a[contains(text(),'Cohort Builder')]"))

    print(driver.title)

    return driver


# helpers

def handle_cookies(cookies):
    # Extract cookie values
    access_token_cookie_value = next(
        (cookie['value'] for cookie in cookies if cookie['name'] == 'access_token_cookie'), None)
    csrf_access_token_value = next(
        (cookie['value'] for cookie in cookies if cookie['name'] == 'csrf_access_token'), None)

    # Check if both cookies are present
    if access_token_cookie_value is None or csrf_access_token_value is None:
        print('Error: Missing required cookies')
        return

    cookies_str = f"access_token_cookie={access_token_cookie_value}; csrf_access_token={csrf_access_token_value}"
    return cookies_str, access_token_cookie_value, csrf_access_token_value


class WiserTester:
    def __init__(self, recordings_path, results_path):
        self.logger = LOGGER
        # self.socket = socketio.AsyncClient(logger=True, engineio_logger=True)
        self.socket = socketio.AsyncClient()
        self.results = {}
        self.server_path = SERVER_PATH
        self.client_lock = asyncio.Lock()
        self.s_id = None
        self.driver = login()
        self.recordings_path = recordings_path
        self.results_path = results_path

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
                    request_id = report_data['requestId']
                    self.results[report_id] = data
                    self.logger.info(f"Received data for request ID {request_id}: {report_data}")
                    await self.save_result(request_id, data)

        @self.socket.event
        async def error(data):
            error_msg = data.get('error')
            report_id = data.get('id')
            if report_id:
                async with self.client_lock:
                    self.results[report_id] = {'error': error_msg}
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

    async def save_result(self, request_id, result_data):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{request_id}_at_{timestamp}.json"
        result_path = os.path.join(self.results_path, file_name)
        with open(result_path, "w") as file:
            json.dump(result_data, file, indent=2)
        return result_path

    async def get_result(self, req_id):
        return self.results.get(req_id)

    async def send_request_get_response(self, json_request_path, cookies):
        with open(json_request_path, "r") as file:
            json_request_str = file.read()

        json_request = json.loads(json_request_str)
        cookies_str, access_token_cookie_value, csrf_access_token_value = handle_cookies(cookies)
        req_headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Cookie': f'{cookies_str}',
            'Host': 'localhost:5000',
            'Origin': 'http://localhost:5050',
            'Referer': 'http://localhost:5050/',
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
                response = await client.post('http://localhost:5000/report', json=json_request, headers=req_headers)
                response.raise_for_status()
                response_json = response.json()
                request_id = response_json.get('id')  # Assuming the response contains the request ID
                return request_id, response

        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            return None, None

    async def test_all(self):
        self.logger.info(f'started testing all recordings')
        for rec in os.listdir(self.recordings_path):
            rec_dir = os.path.join(self.recordings_path, rec)
            await self.test_recording(rec_dir)
            await asyncio.sleep(1)

        await self.close()

    async def test_specific(self, recordings_list):
        self.logger.info(f'started testing recordings {recordings_list}')
        for rec in recordings_list:
            rec_dir = os.path.join(self.recordings_path, rec)
            await self.test_recording(rec_dir)
            await asyncio.sleep(1)
        await self.close()

    async def test_recording(self, rec_dir):
        cookies = self.driver.get_cookies()
        self.logger.info(f'Cookies obtained')
        responses = []
        for filename in os.listdir(rec_dir):
            file_path = os.path.join(rec_dir, filename)
            if file_path.endswith(".json"):
                response = await self.send_request_get_response(file_path, cookies)
                self.logger.info(f'request sent for file: {file_path}')
                request_id, _ = response
                responses.append(response)
                self.logger.info(f'response: {response}')
                await asyncio.sleep(1)

        self.logger.info(f'all requests completed for {rec_dir}')

    async def start_test(self, specific_recordings=None):
        await self.connect_to_server()
        if specific_recordings:
            await self.test_specific(specific_recordings)
        else:
            await self.test_all()
        await self.socket.wait()

    async def close(self):
        if self.socket:
            await self.socket.disconnect()


def parse_args():
    parser = argparse.ArgumentParser(description="Run Wiser Tester")
    parser.add_argument("--mode", type=str, choices=['all', 'specific'], default='all',
                        help="Testing mode: 'all' or 'specific'")
    parser.add_argument("--recordings_path", type=str, default="data/recordings",
                        help="Path to the recordings directory")
    parser.add_argument("--results_path", type=str, default="data/results",
                        help="Path to save results")
    return parser.parse_args()


async def main():
    args = parse_args()
    recordings_path = args.recordings_path
    results_path = args.results_path
    test = WiserTester(recordings_path, results_path)

    try:
        if args.mode == 'all':
            await test.start_test()
        elif args.mode == 'specific':
            # need to define how to handle specific recordings
            specific_recordings = []
            await test.start_test(specific_recordings)
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")
    finally:
        await test.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"interrupted")
