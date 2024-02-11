import argparse
import json
import logging
import os
import sys
from pathlib import Path
from haralyzer import HarParser, HarPage


class HarFileProcessor:
    """
    A class to process HTTP Archive (HAR) files, extracting and saving POST request data as json files.

    Attributes:
        har_path (str): The path to the HAR file to be processed.
        inputs_dir (str): Directory where processed input files will be stored.
        initial_requests_path (str, optional): Path for initial requests, not used in this version.
        page_title (str): The title of the page to filter HAR entries by.
        remove_initial_data (bool): Flag to determine whether to remove initial data requests.
        logger (logging.Logger): Logger object for logging messages.
    """

    def __init__(
        self,
        har_path,
        inputs_dir="data/inputs",
        initial_requests_path=None,
        page_title="http://localhost:5050/",
        remove_initial_data=True,
    ):
        self.har_path = har_path
        self.inputs_dir = inputs_dir
        self.initial_requests_path = initial_requests_path
        self.page_title = page_title
        self.remove_initial_data = remove_initial_data
        self.logger = self.setup_logger()

    def setup_logger(self):
        """Sets up a logger for logging information and debug messages."""
        if not os.path.isdir("logs"):
            os.mkdir("logs")
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(formatter)

        file_handler = logging.FileHandler("logs/inputBuilderlog.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stdout_handler)
        return logger

    def make_dir(self):
        """Creates a directory for storing processed files, if it does not already exist."""
        path = os.path.join(self.inputs_dir, Path(self.har_path).stem)
        if not os.path.isdir(path):
            os.mkdir(path)
            self.logger.info(f"Created dir {path}")
        return path

    def save_request_file(self, dir, json_data, file_name):
        """Saves processed request data to a JSON file."""
        new_req_path = os.path.join(dir, file_name)
        with open(new_req_path, "w") as file:
            json.dump(json_data, file, indent=2)
        self.logger.info(f"Saved file {new_req_path}")
        return new_req_path

    def process_har_file(self):
        """Processes the HAR file, extracting and saving POST request data."""
        har_parser = HarParser.from_file(self.har_path)

        self.logger.info(har_parser.hostname)

        new_rec_dir = self.make_dir()
        pages = {}
        for page in har_parser.pages:
            page_id = page.page_id
            pages[page.title] = page_id
            self.logger.info(f"id: {page_id}, title: {page.title}")

        har_page = HarPage(pages[self.page_title], har_parser=har_parser)
        entries = har_page.filter_entries(request_type="POST", status_code="2.*")
        for entry in entries:
            req_txt = entry.request.text
            json_req = json.loads(req_txt)
            if self.remove_initial_data:
                if json_req.get("messageType") not in ["getData", "userCohortCatalog"]:
                    name = f'{entry.startTime.strftime("%Y%m%d%H%M%S%f")[:-3]}.json'
                    self.save_request_file(new_rec_dir, json_req, name)
            else:
                name = f'{entry.startTime.strftime("%Y%m%d%H%M%S%f")[:-3]}.json'
                self.save_request_file(new_rec_dir, json_req, name)


def main():
    """Entry point of the script. Parses command-line arguments and processes the HAR file."""
    parser = argparse.ArgumentParser(description="Process HAR files and extract POST requests.")
    parser.add_argument("--har_path", help="Path to the HAR file")
    parser.add_argument("--inputs_dir", default="data/inputs", help="Directory to store inputs")
    parser.add_argument("--page_title", default="http://localhost:5050/", help="Title of the page to filter entries by")
    parser.add_argument("--remove_initial_data", action="store_true", help="Remove initial data requests")

    args = parser.parse_args()

    processor = HarFileProcessor(
        har_path=args.har_path,
        inputs_dir=args.inputs_dir,
        page_title=args.page_title,
        remove_initial_data=args.remove_initial_data,
    )
    processor.process_har_file()


if __name__ == "__main__":
    main()
