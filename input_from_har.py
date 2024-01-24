import json
import logging
import os
import sys

from haralyzer import HarParser, HarPage

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

INPUTS_DIR = 'data/inputs'
HAR_PATH = 'diabetes_complication_comparison.har'
PAGE_TITLE = 'http://localhost:5050/'
FILE_NAME_FORMAT = '%Y%m%d%H%M%S%f'


def make_dir():
    path = os.path.join(INPUTS_DIR, HAR_PATH.strip('.har'))
    if not os.path.isdir(path):
        os.mkdir(path)
        LOGGER.info(f'created dir {path}')
    return path


def save_request_file(dir, json_data, file_name):
    new_req_path = os.path.join(dir, file_name)
    with open(new_req_path, "w") as file:
        json.dump(json_data, file, indent=2)
    return new_req_path


har_parser = HarParser.from_file(HAR_PATH)

LOGGER.info(har_parser.hostname)

new_rec_dir = make_dir()
pages = {}
for page in har_parser.pages:
    page_id = page.page_id
    pages[page.title] = page_id
    LOGGER.info(f"id: {page_id}, title: {page.title}")

har_page = HarPage(pages[PAGE_TITLE], har_parser=har_parser)
entries = har_page.filter_entries(request_type='POST', status_code='2.*')
for entry in entries:
    req_txt = entry.request.text
    json_req = json.loads(req_txt)
    name = entry.startTime.strftime(FILE_NAME_FORMAT)[:-3]+'.json'
    saved = save_request_file(new_rec_dir, json_req, name)
    LOGGER.info(saved)
