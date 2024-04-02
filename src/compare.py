from datetime import datetime
import os
import re
import shutil
from config import LOGGER
from exceptions import handle_exceptions
from utils import load_json_file, save_json_file
from deepdiff import DeepDiff, Delta


class Compare:
    def __init__(self, outputs_path, expectations_path, reports_path, ignore_paths=None):
        self.outputs_path = outputs_path
        self.expectations_path = expectations_path
        self.reports_path = reports_path
        self.report_paths = []
        self.ignore_paths = ignore_paths if ignore_paths is not None else []
        self.no_preprocessing = False

        LOGGER.info(f"Excluding paths: {self.ignore_paths}")

    @handle_exceptions("Comparison error", False)
    def compare_outputs_with_expectations(self, no_preprocessing):
        """Compare the output files with expected outputs stored in a specified directory."""
        LOGGER.info("Comparing outputs to expectations")
        self.no_preprocessing = no_preprocessing
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
        for output_file in os.listdir(output_folder_path):
            input_file_name, _ = os.path.splitext(output_file)
            expected_file_name = f"{input_file_name}.json"
            expected_file_path = os.path.join(expectation_folder_path, expected_file_name)
            output_file_path = os.path.join(output_folder_path, output_file)
            new_report_path = os.path.join(self.reports_path, os.path.basename(output_folder_path))

            if not os.path.isdir(new_report_path):
                os.mkdir(new_report_path)
                LOGGER.info(f"Created directory {new_report_path}")

            if os.path.exists(expected_file_path):
                self.compare_and_save_report(input_file_name, output_file_path, expected_file_path, new_report_path)
            else:
                LOGGER.warning(f"No expectation file found for {input_file_name}")

    @handle_exceptions("Unexpected error reading files", True)
    def compare_and_save_report(self, input_file_name, output_file_path, expected_file_path, report_path, timeout=60):
        """Compare an output file with its expected counterpart and save the report."""

        output_data = load_json_file(output_file_path).get("data")
        expected_data = load_json_file(expected_file_path).get("data")
        if not self.no_preprocessing:
            # Preprocess the data to normalize dynamic file names
            output_data = self.preprocess_data(output_data)
            expected_data = self.preprocess_data(expected_data)
        if output_data and expected_data:
            report = {
                "timestamp": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                "request_id": output_data.get("requestId", "N/A"),
                "output_file": output_file_path,
                "expected_output_file": expected_file_path,
            }
            exclude_regex = [re.compile(path) for path in self.ignore_paths]

            diff = DeepDiff(
                expected_data,
                output_data,
                ignore_order=True,
                report_repetition=True,
                exclude_regex_paths=exclude_regex,
                cutoff_intersection_for_pairs=1,
                get_deep_distance=True,
                max_passes=3,
                cache_size=5000,
                log_frequency_in_sec=10,
                progress_logger=LOGGER.warning,
            )
            if diff:
                # If differences are found, prepare a dedicated folder for this comparison
                dedicated_folder_path = os.path.join(report_path, f"{input_file_name}_comparison")
                os.makedirs(dedicated_folder_path, exist_ok=True)

                # Save the comparison report in the dedicated folder
                file_name = f"{input_file_name}_comparison.json"
                output_path = os.path.join(dedicated_folder_path, file_name)
                save_json_file(report, output_path)

                # Copy the expected and output files to the dedicated folder
                shutil.copy(expected_file_path, dedicated_folder_path)
                shutil.copy(output_file_path, dedicated_folder_path)

                self.report_paths.append(output_path)
                LOGGER.info(f"Comparison report generated for {input_file_name}")
            else:
                LOGGER.info(f"No difference found in output for {input_file_name}")

    def preprocess_data(self, data):
        """Preprocess data to normalize dynamic content like file names within the `figures` section."""
        if "figures" in data:
            data["figures"] = self.traverse_and_normalize_figures(data["figures"])
        return data

    def traverse_and_normalize_figures(self, figures):
        """Recursively traverse and normalize file names within the figures structure."""
        if isinstance(figures, dict):
            return {k: self.traverse_and_normalize_figures(v) for k, v in figures.items()}
        elif isinstance(figures, list):
            return [self.traverse_and_normalize_figures(elem) for elem in figures]
        elif isinstance(figures, str):
            # Replace UUIDs within file names with 'PLACEHOLDER'
            return re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "PLACEHOLDER", figures)
        else:
            return figures

    @handle_exceptions("Failed to generate summary report", False)
    def generate_summary_report(self):
        """Generate a summary report of all comparisons."""
        version_info = load_json_file(os.path.join(self.outputs_path, "version_info.json"))
        summary = {"output_version_info": version_info, "total_comparisons": len(self.report_paths), "differences": []}

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
