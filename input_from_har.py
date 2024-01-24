import json
import logging
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

HAR_PATH = 'examplehar.har'

har_parser = HarParser.from_file(HAR_PATH)

LOGGER.info(har_parser.hostname)

pages = []
for page in har_parser.pages:
    page_id = page.page_id
    LOGGER.info(page_id)
    har_page = HarPage(page_id, har_parser=har_parser)
    entries = har_page.filter_entries(request_type='POST', status_code='2.*')
    request_messages = []
    for entry in entries:
        req_txt = entry.request.text
        json_req = json.loads(req_txt)
        request_messages.append(json_req)



