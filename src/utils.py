# Utility Functions
import csv
import json
import pandas as pd
from src.exceptions import handle_exceptions


def custom_serializer(obj):
    """
    Attempts to JSON-serialize objects of known non-serializable types.
    """
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    else:
        return str(obj)


@handle_exceptions("Error loading/saving JSON file")
def load_json_file(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


@handle_exceptions("Failed to save JSON file", True)
def save_json_file(data, file_path):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=2, default=custom_serializer)
        return True


def extract_timestamp_from_filename(filename):
    """Extracts the timestamp from the filename."""
    # Assuming filename format is "%m%d%H%M%S%f_messageType.json"
    timestamp_str, _ = filename.split("_", 1)
    return int(timestamp_str)  # Convert to integer for sorting


def check_json_structure(data):
    try:
        # Check the first level
        if not isinstance(data, dict) or "data" not in data:
            return "The top level is not a dictionary or lacks the 'data' key."

        nested_data = data["data"]
        if not isinstance(nested_data, dict) or "data" not in nested_data:
            return "'data' key does not lead to a dictionary or lacks a nested 'data' key."

        csv_data = nested_data["data"]
        if not isinstance(csv_data, list) or not all(isinstance(item, dict) for item in csv_data):
            return "Nested 'data' is not a list of dictionaries as expected."

        return "JSON structure is as expected."
    except ValueError as e:
        return f"Invalid JSON data: {e}"
    except Exception as e:
        return f"An error occurred: {e}"


def contains_csv_data(data):
    try:
        struct = check_json_structure(data)
        if struct == "JSON structure is as expected.":
            # Check if the expected CSV data exists and is a list of dictionaries
            csv_data = data.get("data", {}).get("data", None)
            if csv_data != []:
                return isinstance(csv_data, list) and all(isinstance(item, dict) for item in csv_data)

        # print(struct)
        return False
    except ValueError as e:
        # Handle the case where JSON is invalid
        # print(f"Invalid JSON data: {e}")
        return False
    except Exception as e:
        # Handle any other exceptions
        # print(f"An error occurred: {e}")
        return False


@handle_exceptions("Failed to save csv file", True)
def json_to_csv(csv_data, csv_filename):
    """converts JSON data into a CSV file."""
    with open(csv_filename, "w", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)
        header = csv_data[0].keys()
        csv_writer.writerow(header)

        for row in csv_data:
            csv_writer.writerow(row.values())
