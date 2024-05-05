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

<h2 id="about">About</h2>

Wiser Tester is a tool designed to automate the testing of wiser by simulating various inputs and comparing the actual outputs against expected ones. This document provides detailed instructions on how to set up and use Wiser Tester for building and running tests, building executables, and analyzing results.

<h2 id="prerequisites">Prerequisites</h2>

* Python 3.8 - check with ```python3 --version```
* packages listed in requirements.txt file

<h2 id="setup-and-execution-instructions">Setup and Execution Instructions</h2>

### Running the Python Version at Weizmann 

#### Creating Environment
 **Set Up a Virtual Environment** (recommended for isolating dependencies)
   ```bash
   python -m venv env
   env\Scripts\activate
   pip install -r requirements.txt
  ```
#### Running the Script
  Activation: If using a virtual environment, activate it before running the script.\
  Usage:
  ```bash
    wiser_tester.py --username USERNAME --password PASSWORD --config CONFIG_FILE_PATH [options]
  ```
  Example Command:
  ```bash
    python wiser_tester.py --username maya --password mayah --config config/config.json
  ```

### Creating A New Executable
  **Generate Standalone Executable** \
    - Set Up a Virtual Environment and Install the requirements.txt  (see above)\
    - run command:
  ```bash
      python pyinstaller --onefile wiser_tester.py
  ```
  **Building a New Executable using the batch script**
  ```bash
      .\buildNewExe.bat
  ```


### Using the Standalone Executable
  Command Line Arguments: Similar to the Python version, with the .exe extension.\
  Make sure config file is set correctly for the environment

  **Run the exe at Weizmann**
  - ***using only the exe***
    ```bash
        wiser_tester.exe --username USERNAME --password PASSWORD --config config/config_weizmann.json
    ```
  - ***using the batch file***
    ```bash
        .\RunWiserTesterInWeizmann.bat
    ```

  **Run the exe at Clalit**
  - ***using only the exe***
    ```bash
        wiser_tester.exe --username USERNAME --password PASSWORD --config config/config_clalit.json
    ```
  - ***using the batch file***
    ```bash
        .\RunWiserTesterInClalit.bat
    ```


<h2 id="cli-options">CLI Options for wiser tester</h2>

### Required Arguments

- **`--username`**: Username for login authentication. This argument is required.
- **`--password`**: Password for login authentication. This argument is required.
- **`--config`**: Path to the configuration file containing test settings. This argument is required. 

### Optional Arguments

- **`--mode`**: Determines the testing mode. Options are `all` or `specific`, with `all` being the default.
- **`--specific_list`**: If `--mode` is `specific`, this specifies a comma-separated list of specific input directories to test.
- **`--expected_output`**: Path to the directory containing expected output files for comparison. Defaults to `data/expectations`.
- **`--compare`**: Enables or disables comparison to previous outputs. Options are `yes` or `no`, with `yes` being the default.
- **`--comparison_reports`**: Path where comparison reports will be saved. Defaults to `data/comparison_reports`.
- **`--request_timeout`**: Sets the request timeout in seconds. Defaults to 60 seconds.


<h2 id="config-file">Config File</h2>

- **`host`**: Specifies the host name where the web application is running.
  - Example: `localhost:5000`
- **`origin`**: Defines the origin URL to test against.
  - Example: `http://localhost:5050`
- **`inputs_dir`**: Path to the directory containing input files for testing. 
  - Example: `data/inputs`
- **`outputs_dir`**: Path to the directory containing output files for testing. 
  - Example: `data/outputs`

<h2 id="generate-recordings">Generate Recordings of Queries</h2>

## process HAR files
The `HAR_request_extractor.py` script is designed to process HAR files, extracting POST request data and saving it as JSON files. This can be useful for analyzing and replaying wiser interactions.

#### Single HAR File

***To process specific HAR files:***
```bash
python HAR_request_extractor.py --har_paths "path/to/your_file1.har" "path/to/your_file2.har" --config path/to/config.json --exclude_request_types type1 type2
```
  - Example: `python HAR_request_extractor.py --har_path "data\har_files\cohort_builder_example.har" --config config.json --exclude_request_types getData userCohortCatalog`

#### Directory of HAR Files
***To process all HAR files within a directory:***
```bash 
python HAR_request_extractor.py --har_dir "path/to/directory" --config path/to/config.json --exclude_request_types type1 type2
```
  - Example: `python tools/HAR_request_extractor.py --config config/config_weizmann.json --exclude_request_types getData userCohortCatalog`

#### Using the Standalone Executable
  Command Line Arguments: Similar to the Python version, with the .exe extension.\
  Make sure config file is set correctly for the environment

  **Run the exe at Weizmann**
  - ***using only the exe***
    ```bash
        HAR_request_extractor.exe --config config_weizmann.json --har_dir "data/har_files"
    ```
  - ***using the batch file***
    ```bash
        .\RunRequestExtractorWeizmann.bat
    ```

  **Run the exe at Clalit**
  - ***using only the exe***
    ```bash
        HAR_request_extractor.exe --config config_clalit.json --har_dir "data/har_files"
    ```
  - ***using the batch file***
    ```bash
        .\RunRequestExtractorClalit.bat
    ```
**Output**
Processed files will be saved in the directory specified in the config.json file under inputs_dir, organized by the stem name of each HAR file processed.

## JSON Request Manager
### Overview
The JSON Request Manager is a Python script designed to manage JSON request bundles. It supports creating, modifying, and managing JSON files based on templates. The script allows users to add, remove, or modify JSON files within a specified directory.

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
-**`--template`**: Specifies the path to the folder containing JSON template files.
-**`--directory`**: Required. Specifies the output directory to manage the requests.
-**`--copy_all`**: Flag to copy all files from the template directory to the specified directory.
-**`--add`**: A list of filenames to add from the template to the directory. Specify "all" to add all files.
-**`--remove`**: A list of filenames to remove from the directory.
-**`--modify`**: Pairs of filename and value to modify existing requests, e.g., --modify filename key=value.

#### examples
Copy All Templates to Directory
```bash
python tools/request_manager.py --template data/inputs/template --directory data/inputs/new_rec --copy_all
```

Add Specific Files
```bash
python ./request_manager.py --template data/inputs/template --directory ./requests --add report1.json report2.json
```

Modify an existing request:
```bash
python ./request_manager.py --directory ./requests --modify report1.json '{"new_key": "new_value"}'
```

Remove files:
```bash
python ./request_manager.py --directory ./requests --remove outdated_report.json
```

<h2 id="versioning-and-comparisons">Versioning and Comparisons</h2>


### Versioning
Upon each test run, the WiserTester fetches and saves the version info of the application being tested. This information is stored within each output directory, allowing for version tracking alongside test results.

### Dynamic Comparisons
The Compare class has been enhanced to preprocess output and expected data, normalizing dynamic content such as file names within the figures section. This ensures that comparisons focus on meaningful data changes, disregarding variations in identifiers or timestamps. 
this option can be disabled using --

<h2 id="post-run-analysis">Post-Run Analysis and Error Handling</h2>
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
