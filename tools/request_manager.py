import json
import os
import sys
from datetime import datetime
import argparse
import sys

sys.path.insert(1, "/".join(os.path.realpath(__file__).split("/")[:-2]))

from src.utils import load_json_file, save_json_file


def setup_directory(directory):
    """Create a directory for the report type if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


def load_template(template_path):
    """Load a JSON request folder template."""
    templates = [os.path.join(template_path, f) for f in os.listdir(template_path) if f.endswith(".json")]
    return {os.path.splitext(os.path.basename(f))[0]: json.load(open(f, "r")) for f in templates}


def modify_request(data, modifications):
    """Modify the JSON data based on user inputs."""
    for file, value in modifications.items():
        if file in data:
            data[file] = value
    return data


def load_and_modify_request(file_path, modifications):
    """Load existing requests, modify them, and save back."""
    data = load_json_file(file_path)
    modified_data = modify_request(data, modifications)
    save_json_file(modified_data, file_path)
    print(f"Modified and saved {file_path} with updates.")


def save_request(data, directory, identifier):
    """Save the populated request JSON to a file."""
    filename = f"{identifier}.json"
    path = os.path.join(directory, filename)
    save_json_file(data, path)
    print(f"Saved request to {path}")


def add_files_to_directory(templates, add, directory):
    """Save multiple requests based on the templates and add list."""
    if add == "all":
        for file in templates:
            save_request(templates[file], directory, file)
    else:
        for report_type in add:
            for file in templates:
                if report_type in file:
                    save_request(templates[file], directory, file)


def remove_files_from_directory(files, directory):
    """Remove specified files from the directory."""
    for file in files:
        file_path = os.path.join(directory, file)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Removed {file} from {directory}")
        else:
            print(f"File {file} not found in {directory}")


def main():
    """Main function to handle user input for creating, modifying, or managing requests."""
    parser = argparse.ArgumentParser(description="Manage JSON request bundles based on user inputs.")
    parser.add_argument("--template", help="Path to the folder of JSON template files", required=False)
    parser.add_argument("--directory", help="Output directory to manage the requests", required=True)
    parser.add_argument("--copy_all", help="Flag to copy all files from the template directory", action="store_true")
    parser.add_argument("--add", nargs="+", help="List of file names to add from the template", default=[])
    parser.add_argument("--remove", nargs="+", help="List of file names to remove from the directory", default=[])
    parser.add_argument(
        "--modify",
        nargs=2,
        metavar=("file", "VALUE"),
        help="file and new value to modify existing requests",
        action="append",
        default=[],
    )

    args = parser.parse_args()

    directory = setup_directory(args.directory)

    if args.template:
        templates = load_template(args.template)

    if args.copy_all:
        add_files_to_directory(templates, "all", directory)

    if args.add:
        add_files_to_directory(templates, args.add, directory)

    if args.remove:
        remove_files_from_directory(args.remove, directory)

    if args.modify:
        modifications = dict(args.modify)
        for filename in os.listdir(directory):
            if filename.endswith(".json"):
                filepath = os.path.join(directory, filename)
                with open(filepath, "r") as file:
                    data = json.load(file)
                modified_data = modify_request(data, modifications)
                save_request(modified_data, directory, filename)


if __name__ == "__main__":
    main()
