from datetime import datetime
import os
import re
import shutil
from src.configure import LOGGER
from src.exceptions import handle_exceptions
from src.utils import contains_csv_data, json_to_csv, load_json_file, save_json_file
from deepdiff import DeepDiff, Delta


class Compare:
    def __init__(self, config, expectations_path, reports_path, specific_list=None):
        self.outputs_path = config["outputs_dir"]
        self.inputs_path = config["inputs_dir"]
        self.expectations_path = expectations_path
        self.reports_path = reports_path
        self.report_paths = []
        self.ignore_paths = config["ignore_paths"] if config["ignore_paths"] is not None else []
        self.no_preprocessing = False
        self.specific_list = specific_list
        LOGGER.info(f"Excluding paths: {self.ignore_paths}")

    @handle_exceptions("Comparison error", False)
    def compare_outputs_with_expectations(self, no_preprocessing):
        """Compare the output files with expected outputs stored in a specified directory."""
        LOGGER.info("Comparing outputs to expectations")
        self.no_preprocessing = no_preprocessing
        if self.specific_list:
            for output_folder in self.specific_list:
                expectation_folder_path = os.path.join(self.expectations_path, output_folder)
                if os.path.isdir(expectation_folder_path):
                    output_folder_path = os.path.join(self.outputs_path, output_folder)
                    self.compare_folder_outputs(output_folder_path, expectation_folder_path)
        else:
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
                self.compare_and_save_report(
                    input_file_name, output_file_path, expected_file_path, new_report_path, os.path.basename(output_folder_path)
                )
            else:
                LOGGER.warning(f"No expectation file found for {input_file_name}")

    @handle_exceptions("Unexpected error reading files", True)
    def compare_and_save_report(self, input_file_name, output_file_path, expected_file_path, report_path, folder):
        """Compare an output file with its expected counterpart and save the report."""
        if not (output_file_path.endswith(".json") and expected_file_path.endswith(".json")):
            return
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
                delta = Delta(diff, bidirectional=True)
                flat_dicts = delta.to_flat_dicts()
                report["diff"] = flat_dicts

                # If differences are found, prepare a dedicated folder for this comparison
                dedicated_folder_path = os.path.join(report_path, f"{input_file_name}_comparison")
                os.makedirs(dedicated_folder_path, exist_ok=True)

                # Save the comparison report in the dedicated folder
                file_name = f"{input_file_name}_comparison.json"
                report_path = os.path.join(dedicated_folder_path, file_name)
                save_json_file(report, report_path)

                # Copy the input, expected and output files to the dedicated folder
                input_name = f"input_{input_file_name}.json"
                input_path = os.path.join(dedicated_folder_path, input_name)
                shutil.copy(os.path.join(self.inputs_path, folder, f"{input_file_name}.json"), input_path)
                expected_name = f"expected_{input_file_name}.json"
                expected_path = os.path.join(dedicated_folder_path, expected_name)
                shutil.copy(expected_file_path, expected_path)
                output_name = f"output_{input_file_name}.json"
                output_path = os.path.join(dedicated_folder_path, output_name)
                shutil.copy(output_file_path, output_path)

                self.process_csv(input_file_name, expected_file_path, output_file_path, dedicated_folder_path)
                self.report_paths.append(report_path)
                LOGGER.info(f"Comparison report generated for {input_file_name}")
            else:
                LOGGER.info(f"No difference found in output for {input_file_name}")

    def process_csv(self, input_file_name, expected_file_path, output_file_path, dedicated_folder_path):

        self.copy_csv("expected_", input_file_name, expected_file_path, dedicated_folder_path)
        self.copy_csv("output_", input_file_name, output_file_path, dedicated_folder_path)

    def copy_csv(self, arg0, input_file_name, file_path, dedicated_folder_path):
        # Copy the expected and output csv files to the dedicated folder
        csv_name = f"{arg0}{input_file_name}.csv"
        csv_path = os.path.join(dedicated_folder_path, csv_name)
        expected_csv = file_path.replace(".json", ".csv")
        if os.path.exists(expected_csv):
            shutil.copy(expected_csv, csv_path)
        else:
            data = load_json_file(file_path)
            if contains_csv_data(data):
                csv_path = os.path.join(dedicated_folder_path, csv_name)
                json_to_csv(data.get("data", {}).get("data", None), csv_path)

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
