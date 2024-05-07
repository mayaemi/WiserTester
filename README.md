<div align="center" id="top"> 
  <h1 align="center">WiserTester</h1>
  &#xa0;
  <a href="#about">About</a> •
  <a href="#prerequisites">Prerequisites</a> •
  <a href="#setup-and-execution-instructions">Setup</a> •
  <a href="#cli-options">CLI Options</a> •
  <a href="#config-file">Config File</a> •
  <a href="#generate-recordings">Generate Recordings</a> •
  <a href="#versioning-and-comparisons">Versioning and Comparisons</a> •
  <a href="#post-run-analysis">Analysis</a>
</div>

## About

Wiser Tester is a tool designed to automate the testing of wiser by simulating various inputs and comparing the actual outputs against expected ones. This guide details instructions on how to set up and use WiserTester for building and running tests, building executables, and analyzing results.

## Prerequisites

- Python 3.8 or higher (Verify with `python3 --version`)
- Dependencies from `requirements.txt` file

## Setup and Execution Instructions

### Creating Environment

Set up a virtual environment top isolate requirements (recommended):

```bash
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
```

### Running the Script

Activate the environment, then run:

```bash
wiser_tester.py --username USERNAME --password PASSWORD --config CONFIG_FILE_PATH [options]
```

Example:

``
python wiser_tester.py --username maya --password mayah --config config/config_weizmann.json
``

### Creating A New Executable

Generate a standalone executable:

```bash
python pyinstaller --onefile wiser_tester.py
```

Build using the batch script:

```bash
.\buildNewExe.bat
```

### Building and Packaging New Releases with `buildNewPkg`

This script automates the creation of executables for the `wiser_tester.py` and the `HAR_request_extractor.py` tools, packaging them with necessary configuration and data files, as well as the batch run files. 

```bash
.\buildNewPkg.bat
```

### Using the Standalone Executable

Run at Weizmann:

```bash
wiser_tester.exe --username USERNAME --password PASSWORD --config config/config_weizmann.json
```

or using the batch file:

```bash
.\RunWiserTesterInWeizmann.bat
```

Run at Clalit:

```bash
wiser_tester.exe --username USERNAME --password PASSWORD --config config/config_clalit.json
```

or using the batch file:

```bash
.\RunWiserTesterInClalit.bat
```

## CLI Options

### Required Arguments

- `--username`: Username for login authentication.
- `--password`: Password for login authentication.
- `--config`: Path to the configuration file containing test settings.

### Optional Arguments

- `--mode`: Testing mode, default is `all`.
- `--specific_list`: Comma-separated list of specific input directories to test.
- `--expected_output`: Path for expected output files, defaults to `data/expectations`.
- `--compare`: Comparison to previous outputs, default is `yes`.
- `--comparison_reports`: Path for saving comparison reports, defaults to `data/comparison_reports`.
- `--request_timeout`: Request timeout in seconds, defaults to 60.

## Config File

*make sure the config file fits your environment*
- `host`: Host name of the web application, e.g., `localhost:5000`.
- `origin`: Origin URL to test against, e.g., `http://localhost:5050`.
- `inputs_dir`: Directory for input files, e.g., `data/inputs`.
- `outputs_dir`: Directory for output files, e.g., `data/outputs`.

## Generate Recordings

Process HAR files and save POST request data as JSON:

***To process specific HAR files:***
```bash
python ./HAR_request_extractor.py --har_paths "path/to/your_file1.har" "path/to/your_file2.har" --config path/to/config.json --exclude_request_types type1 type2
```

***Directory of HAR Files***
```bash 
python HAR_request_extractor.py --har_dir "path/to/directory" --config path/to/config.json --exclude_request_types type1 type2
```
Example: ``python tools/HAR_request_extractor.py --config config/config_weizmann.json --exclude_request_types getData userCohortCatalog``

#### Using the Standalone Executable

  **Run the exe in Weizmann**
  - *using only the exe*
    ```bash
        HAR_request_extractor.exe --config config_weizmann.json --har_dir "data/har_files"
    ```
  - *using the batch file*
    ```bash
        .\RunRequestExtractorWeizmann.bat
    ```

  **Run the exe in Clalit**
  - *using only the exe*
    ```bash
        HAR_request_extractor.exe --config config_clalit.json --har_dir "data/har_files"
    ```
  - *using the batch file*
    ```bash
        .\RunRequestExtractorClalit.bat
    ```
**Output**\
Processed files will be saved in the directory specified in the config.json file under inputs_dir, organized by the stem name of each HAR file processed.

## JSON Request Manager
### Overview
The JSON Request Manager is a Python script designed to manage JSON request bundles. The script allows users to add, remove, or modify JSON files within a specified directory based on templates.

### Features
- **Add JSON Files**: Add specific JSON files or all files from a template directory to a target directory.
- **Remove JSON Files**: Remove specified JSON files from a target directory.
- **Modify JSON Files**: Apply modifications to existing JSON files in a target directory.

### Usage
#### Running the Script
Use the following command to run the script with the necessary arguments:

```bash
python path_to_script/request_manager.py --directory path_to_output_directory [options]
```

#### Options
-`--template`: Specifies the path to the folder containing JSON template files.
-`--directory`: Required. Specifies the output directory to manage the requests.
-`--copy_all`: Flag to copy all files from the template directory to the specified directory.
-`--add`: A list of filenames to add from the template to the directory. Specify "all" to add all files.
-`--remove`: A list of filenames to remove from the directory.
-`--modify`: Pairs of filename and value to modify existing requests, e.g., --modify filename key=value.

#### examples
Copy All Templates to Directory
```bash
python tools/request_manager.py --template data/inputs/template --directory data/inputs/new_rec --copy_all
```

Add Specific Files
```bash
python ./request_manager.py --template data/inputs/template --directory data/inputs/new_rec --add report1 report2
```

Modify an existing request:
```bash
python ./request_manager.py --directory data/inputs/new_rec --modify report1.json '{"new_key": "new_value"}'
```

Remove files:
```bash
python ./request_manager.py --directory data/inputs/new_rec --remove outdated_report.json
```

## Versioning and Comparisons

### Versioning
Upon each test run, the WiserTester fetches and saves the version info of the application being tested. This information is stored within each output directory, allowing for version tracking alongside test results.

### Dynamic Comparisons
The Compare class has been enhanced to preprocess output and expected data, normalizing dynamic content such as file names within the figures section. This ensures that comparisons focus on meaningful data changes, disregarding variations in identifiers or timestamps. 
this option can be disabled using --

## Post-Run Analysis and Error Handling
This section will guide you on investigating comparisons, understanding how errors are handled, and interpreting the log files after running the WiserTester script.

### Investigating Comparisons
If the `--compare` option is set to `yes` (as is the default), the script compares the generated outputs against expected results stored in the specified expectations directory. The comparison reports are saved in the directory defined by the `--comparison_reports` argument. Here's how to investigate the comparison results:

1. **Review Comparison Reports**: Navigate to the comparison reports directory. Each report details the differences between the output and the expected result for a specific test case.
   
2. **Understand the Differences**: The reports include a detailed breakdown of discrepancies, including missing or extra data, differences in values, and more. Use this information to pinpoint the cause of any failures or unexpected behavior.

3. **Summary Report**: A summary report is also generated, providing an overview of all tests, including those with discrepancies. Review this summary to quickly assess the overall testing outcome.

### Handling Errors and Unsuccessful Runs

The script is designed to gracefully handle errors without terminating the execution prematurely. Here's how errors are managed:

1. **Error Logging**: Any errors encountered during the script's execution, including login failures, request issues, or comparison errors, are logged in the script's log file.

2. **Continued Execution**: Upon encountering an error, the script logs the issue and continues with the next steps, ensuring that a single error does not halt the entire testing process.

3. **Review Log Files**: To understand why an error occurred, review the log file located in the `logs` directory. The log includes detailed error messages, stack traces, and the context in which the error occurred, aiding in troubleshooting.

### Log File Insights

The log file generated by the script offers comprehensive insights into the execution process, including the following:

1. **Authentication Status**: Logs include information on the success or failure of the login process, including any authentication errors.

2. **Request and Response Details**: Each test case's request and response details are logged, providing visibility into the data sent to and received from the server.

3. **Comparison Outcomes**: For tests with comparisons enabled, the log details the comparison process, including any found differences.

4. **Error Messages**: Detailed error messages and stack traces are included for any exceptions encountered during the script's execution.

5. **Execution Flow**: The log file also outlines the script's execution flow, including the start and end of tests, making it easier to follow the testing process.

To access the log file, navigate to the `logs` directory and open the `testlog.log` file.

<a href="#top">Back to top</a>
