<div align="center" id="top"> 
  <h1 align="center">WiserTester</h1>
  &#xa0;

</div>

<p align="center">
  <a>About</a> &#xa0; | &#xa0; 
  <a>Setup and Execution Instructions</a> &#xa0;
</p>

<br>

##  About ##

Wiser Tester is a tool designed to automate the testing of wiser by simulating various inputs and comparing the actual outputs against expected ones. This document provides detailed instructions on how to set up and use Wiser Tester for building and running tests, building executables, and analyzing results.

## Setup and Execution Instructions ##

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
  ``wiser_tester.py --host HOST --origin ORIGIN --username USERNAME --password PASSWORD --config CONFIG_FILE_PATH [options]``
  Example Command:
  ```bash
    python wiser_tester.py --host 'localhost:5000' --origin 'http://localhost:5050' --username maya --password mayah --config config.json
  ```

### Creating New Executable
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

  **Run the exe at Weizmann**\

  **Run the exe at Clalit**\


### CLI Options for wiser tester
#### Required Arguments

- **`--host`**: Specifies the host name where the web application is running. This argument is required.
  - Example: `--host localhost:5000`
- **`--origin`**: Defines the origin URL to test against. This argument is required.
  - Example: `--origin http://localhost:5050`
- **`--username`**: Username for login authentication. This argument is required.
- **`--password`**: Password for login authentication. This argument is required.
- **`--config`**: Path to the configuration file containing test settings. This argument is required.

### Optional Arguments

- **`--mode`**: Determines the testing mode. Options are `all` or `specific`, with `all` being the default.
- **`--specific_list`**: If `--mode` is `specific`, this specifies a comma-separated list of specific input directories to test.
- **`--input`**: Path to the directory containing input files for testing. Defaults to `data/inputs`.
- **`--output`**: Path where output files will be saved. Defaults to `data/outputs`.
- **`--expected_output`**: Path to the directory containing expected output files for comparison. Defaults to `data/expectations`.
- **`--compare`**: Enables or disables comparison to previous outputs. Options are `yes` or `no`, with `yes` being the default.
- **`--comparison_reports`**: Path where comparison reports will be saved. Defaults to `data/comparison_reports`.
- **`--request_timeout`**: Sets the request timeout in seconds. Defaults to 60 seconds.


### Generate recordings of Queries


<a href="#top">Back to top</a>
