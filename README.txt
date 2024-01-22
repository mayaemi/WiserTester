
Using python
    creating environment
        python -m venv myenv
        myenv\Scripts\activate
        pip install -r requirements.txt
    running script
        python wiser_tester.py --username [USERNAME] --password [PASSWORD] --mode [all|specific] --input [INPUT_PATH] --output [OUTPUT_PATH] --expected_output [EXPECTED_OUTPUT_PATH] --compare [yes|no]


Using the Standalone Executable:
    basic execution:
        .\dist\wiser_tester.exe

    command line arguments:
        .\dist\wiser_tester --username [USERNAME] --password [PASSWORD] --mode [all|specific] --input [INPUT_PATH] --output [OUTPUT_PATH] --expected_output [EXPECTED_OUTPUT_PATH] --compare [yes|no]

