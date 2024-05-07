from datetime import datetime
import os
import re
import shutil
from src.configure import LOGGER
from src.exceptions import handle_exceptions
from src.utils import contains_csv_data, json_to_csv, load_json_file, save_json_file
from deepdiff import DeepDiff, Delta


class Compare:
    """A class for comparing output files with expected files and generating reports."""

    def __init__(self, config, expectations_path, reports_path, specific_list=None):
        self.outputs_path = config["outputs_dir"]
        self.inputs_path = config["inputs_dir"]
        self.expectations_path = expectations_path
        self.reports_path = reports_path
        self.report_paths = []
        self.ignore_paths = self.ignore_paths = config.get("ignore_paths", [])
        self.no_preprocessing = False
        self.specific_list = specific_list
        LOGGER.info(f"Excluding paths: {self.ignore_paths}")
        self._handle_existing_reports()

    def _handle_existing_reports(self):
        """Rename existing report directories to include a timestamp before generating new ones."""
        if not os.path.exists(self.reports_path):
            return
        already_renamed_pattern = re.compile(r"^z_.*_\d{8}_\d{6}$")  # Regex to check if already renamed
        for folder in os.listdir(self.reports_path):
            if already_renamed_pattern.match(folder):
                continue  # Skip this folder if it matches the renamed pattern
            folder_path = os.path.join(self.reports_path, folder)
            if os.path.isdir(folder_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_name = f"z_{folder}_{timestamp}"
                new_path = os.path.join(self.reports_path, new_name)
                shutil.move(folder_path, new_path)

    @handle_exceptions("Comparison error", False)
    def compare_outputs_with_expectations(self, no_preprocessing):
        """
        Compare output files with expected outputs and generate reports.
        Args: no_preprocessing (bool): Whether to skip data preprocessing.
        Returns: str: Path to the summary report generated.
        """
        LOGGER.info("Comparing outputs to expectations")
        self.no_preprocessing = no_preprocessing
        target_folders = self.specific_list if self.specific_list is not None else os.listdir(self.outputs_path)
        LOGGER.info(f"target folders: {target_folders}")
        for folder in target_folders:
            expectation_folder_path = os.path.join(self.expectations_path, folder)
            if os.path.isdir(expectation_folder_path):
                output_folder_path = os.path.join(self.outputs_path, folder)
                self._compare_folder(folder, output_folder_path, expectation_folder_path)
        return self.generate_summary_report()

    @handle_exceptions("Failed to compare folder", False)
    def _compare_folder(self, folder, expectation_folder_path, output_folder_path):
        """Compares contents of a single folder."""

        LOGGER.info(f"Comparing results for {folder}")
        new_report_folder = os.path.join(self.reports_path, folder)

        if not os.path.isdir(new_report_folder):
            os.mkdir(new_report_folder)
            LOGGER.info(f"Created directory {new_report_folder}")

        if os.path.isdir(output_folder_path):
            for output_file in os.listdir(output_folder_path):
                self._compare_file(output_folder_path, expectation_folder_path, output_file, new_report_folder, folder)
        else:
            LOGGER.error(f"Output directory does not exist: {output_folder_path}")

    def _compare_file(self, output_folder_path, expectation_folder_path, output_file, new_report_folder, folder_name):
        """Compares a single output file against the expected file."""
        input_file_name, _ = os.path.splitext(output_file)
        expected_file_path = os.path.join(expectation_folder_path, f"{input_file_name}.json")
        output_file_path = os.path.join(output_folder_path, output_file)
        if os.path.exists(expected_file_path):
            self._compare_and_generate_report(
                input_file_name, output_file_path, expected_file_path, new_report_folder, folder_name
            )

    def _compare_and_generate_report(self, input_file_name, output_file_path, expected_file_path, new_report_folder, folder_name):
        """Compares an output file with its expected counterpart and generates detailed report if differences are found."""
        report_dir = os.path.join(new_report_folder, f"{input_file_name}_comparison")
        if not (output_file_path.endswith(".json") and expected_file_path.endswith(".json")):
            return
        output_data = load_json_file(output_file_path).get("data")
        expected_data = load_json_file(expected_file_path).get("data")

        if not self.no_preprocessing:
            output_data = self._preprocess_data(output_data)
            expected_data = self._preprocess_data(expected_data)

        if output_data and expected_data:
            diff = self._calculate_diff(output_data, expected_data)
            if diff:
                # If differences are found, prepare a dedicated folder for this comparison
                os.makedirs(report_dir, exist_ok=True)
                request_id = output_data.get("requestId", "N/A")
                self._handle_differences(diff, input_file_name, output_file_path, expected_file_path, report_dir, request_id)
                self._copy_files_for_review(input_file_name, output_file_path, expected_file_path, report_dir, folder_name)

            else:
                LOGGER.info(f"No difference found in output for {input_file_name}")
        else:
            LOGGER.warning(f"Missing data for comparison in {input_file_name}")

    def _calculate_diff(self, expected_data, output_data):
        """Calculate differences between expected and actual data."""
        exclude_regex = [re.compile(path) for path in self.ignore_paths]
        return DeepDiff(
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

    def _handle_differences(self, diff, input_file_name, output_file_path, expected_file_path, report_dir, request_id):
        """Handles the found differences by creating detailed reports and copying relevant files."""
        delta = Delta(diff, bidirectional=True)
        flat_dicts = delta.to_flat_dicts()
        report = {
            "timestamp": datetime.now().strftime("dd/MM/yyyy HH:mm:ss"),
            "request_id": request_id,
            "output_file": output_file_path,
            "expected_output_file": expected_file_path,
            "diff": flat_dicts,
        }

        # Save the comparison report in the dedicated folder
        file_name = f"{input_file_name}_comparison.json"
        report_path = os.path.join(report_dir, file_name)
        save_json_file(report, report_path)
        self._process_csv(input_file_name, expected_file_path, output_file_path, report_dir)

        self.report_paths.append(report_path)
        LOGGER.info(f"Comparison report generated for {input_file_name}")

    def _copy_files_for_review(self, input_file_name, output_file_path, expected_file_path, report_dir, folder_name):
        """Copy input, expected, and output files to the report directory for further review."""
        input_name = f"input_{input_file_name}.json"
        input_path = os.path.join(report_dir, input_name)
        shutil.copy(os.path.join(self.inputs_path, folder_name, f"{input_file_name}.json"), input_path)
        expected_name = f"expected_{input_file_name}.json"
        expected_path = os.path.join(report_dir, expected_name)
        shutil.copy(expected_file_path, expected_path)
        output_name = f"output_{input_file_name}.json"
        output_path = os.path.join(report_dir, output_name)
        shutil.copy(output_file_path, output_path)

    def _process_csv(self, input_file_name, expected_file_path, output_file_path, dedicated_folder_path):
        """process the expected and output csv files"""
        self._copy_csv("expected_", input_file_name, expected_file_path, dedicated_folder_path)
        self._copy_csv("output_", input_file_name, output_file_path, dedicated_folder_path)

    def _copy_csv(self, arg0, input_file_name, file_path, dedicated_folder_path):
        """Copy the expected and output csv files to the dedicated folder."""
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

    def _preprocess_data(self, data):
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
        if not os.path.exists(self.reports_path):
            os.makedirs(self.reports_path)
        summary_report_path = os.path.join(self.reports_path, "comparison_summary.json")
        save_json_file(summary, summary_report_path)
        LOGGER.info(f"Summary report generated at {summary_report_path}")
        return summary_report_path
