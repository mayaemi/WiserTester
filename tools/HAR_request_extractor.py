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
        har_paths (list): The HAR file list to be processed.
        config_path (str): The path to the config file.
        excluded_request_types (list): list of request types to ignore
    """

    def __init__(self, har_paths, config_path="config.json", excluded_request_types=None):
        with open(config_path, "r") as config_file:
            self.config = json.load(config_file)
        self.har_paths = har_paths
        self.inputs_dir = self.config.get("inputs_dir", "./outputs")
        self.page_title = f'{self.config.get("origin")}/'
        self.excluded_request_types = excluded_request_types or []
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

        file_handler = logging.FileHandler("logs/HAR_request_extractor_log.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stdout_handler)
        return logger

    def make_dir(self, file_path):
        """Creates a directory for storing processed files, if it does not already exist."""
        path = os.path.join(self.inputs_dir, Path(file_path).stem)
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

    def process_har_file(self, file_path):
        """Processes the HAR file, extracting and saving POST request data."""
        har_parser = HarParser.from_file(file_path)

        self.logger.info(har_parser.hostname)
        new_rec_dir = self.make_dir(file_path)
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
            msg_type = json_req.get("messageType").replace("chronicDiseaseCohorts.", "")
            if "genReport" in msg_type:
                report_type = json_req.get("report").get("type")
                name = f'{entry.startTime.strftime("%H%M%S%f")[:-3]}_{msg_type}_{report_type}.json'
            else:
                name = f'{entry.startTime.strftime("%H%M%S%f")[:-3]}_{msg_type}.json'
            if msg_type not in self.excluded_request_types:
                self.save_request_file(new_rec_dir, json_req, name)

    def process_files(self):
        for har_path in self.har_paths:
            self.process_har_file(har_path)


def find_har_files(dir):
    return [os.path.join(dir, f) for f in os.listdir(dir) if f.endswith(".har")]


def main():
    """Entry point of the script. Parses command-line arguments and processes the HAR file."""
    parser = argparse.ArgumentParser(description="Process HAR files and extract POST requests.")
    parser.add_argument("--har_paths", nargs="*", help="Paths to the HAR files")
    parser.add_argument("--har_dir", help="Path to a dir containing HAR files", default="data/temps/har_files")
    parser.add_argument("--config", required=True, help="Path to the configuration file")
    parser.add_argument("--exclude_request_types", nargs="*", help="List of request types to exclude from saving", default=[])

    args = parser.parse_args()
    paths = []
    if args.har_dir:
        paths += find_har_files(args.har_dir)
    if args.har_paths:
        paths += args.har_paths
    processor = HarFileProcessor(
        har_paths=paths,
        config_path=args.config,
        excluded_request_types=args.exclude_request_types,
    )
    processor.process_files()


if __name__ == "__main__":
    main()
