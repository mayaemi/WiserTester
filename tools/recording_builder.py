import json
import os
import sys
from datetime import datetime
import argparse


def setup_directory(path, name):
    """Create a directory for the report type if it doesn't exist."""
    directory = os.path.join(path, name)
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


def load_template(template_path):
    """Load a JSON request folder template."""
    templates = [os.path.join(template_path, f) for f in os.listdir(template_path) if f.endswith(".json")]
    return {os.path.splitext(os.path.basename(f))[0]: json.load(open(f, "r")) for f in templates}


def process_req_data(data, report_type):
    """Process or modify the JSON data based on specific needs."""
    # Example of processing: appending a timestamp or modifying fields based on report_type
    if report_type in data:
        data[report_type]["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return data


def save_request(data, directory, identifier):
    """Save the populated request JSON to a file."""
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{identifier}.json"
    path = os.path.join(directory, filename)
    with open(path, "w") as file:
        json.dump(data, file, indent=4)
    print(f"Saved request to {path}")


def save_requests(templates, generate, directory):
    """Save multiple requests based on the templates and generate list."""
    for report_type in generate:
        if report_type in templates:
            data = process_req_data(templates[report_type], report_type)
            save_request(data, directory, report_type)


def create_recording():
    """Main function to create a request from user input."""
    parser = argparse.ArgumentParser(description="Generate request bundle based on user input.")
    parser.add_argument("--template", help="Path to the full folder of JSON template files", required=True)
    parser.add_argument("--output", help="Output directory to save the requests", required=True)
    parser.add_argument("--name", help="Name of the subdirectory for this batch", required=True)
    parser.add_argument("--generate", nargs="+", help="Types of reports to generate", required=True)

    args = parser.parse_args()

    # Load the template
    template_data = load_template(args.template)

    # Set up the directory based on the report type
    directory = setup_directory(args.output, args.name)

    # Save the processed requests
    save_requests(template_data, args.generate, directory)


if __name__ == "__main__":
    create_recording()
