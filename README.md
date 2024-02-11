<div align="center" id="top"> 
  <h1 align="center">WiserTester</h1>
  &#xa0;

</div>

<p align="center">
  <a href="#dart-about">About</a> &#xa0; | &#xa0; 
  <a href="#checkered_flag-starting">Setup and Execution Instructions</a> &#xa0; | &#xa0;
</p>

<br>

## :dart: About ##

Wiser Tester is a tool designed to automate the testing of wiser by simulating various inputs and comparing the actual outputs against expected ones. This document provides detailed instructions on how to set up and use Wiser Tester for building and running tests, building executables, and analyzing results.

## :checkered_flag: Setup and Execution Instructions ##

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
    wiser_tester.py --host HOST --origin ORIGIN --username USERNAME --password PASSWORD --config CONFIG_FILE_PATH [options]
  ```
  Example Command:
  ```bash
    python wiser_tester.py --host 'localhost:5000' --origin 'http://localhost:5050' --username maya --password mayah --config config.json\
  ```

### Creating New Executable
  **Generate Standalone Executable** \
    - Set Up a Virtual Environment and Install the requirements.txt  (see above)\
    - run command: pyinstaller --onefile wiser_tester.py\
  **Building a New Executable using the batch script**\
    .\buildNewExe.bat\

### Using the Standalone Executable
  Command Line Arguments: Similar to the Python version, with the .exe extension.\
  **Run the exe at Weizmann**\

  **Run the exe at Clalit**\


### Generate recordings of Queries


<a href="#top">Back to top</a>
