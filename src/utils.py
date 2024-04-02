# Utility Functions
import json
import pandas as pd
from exceptions import handle_exceptions


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
