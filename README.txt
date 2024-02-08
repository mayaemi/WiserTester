
Using python
    creating environment
        python -m venv env
        myenv\Scripts\activate
        pip install -r allrequirements.txt
    creating new exe
        pyinstaller --onefile wiser_tester.py
    running script
        usage: wiser_tester.py --host HOST --origin ORIGIN --username USERNAME --password PASSWORD --config CONFIG_FILE_PATH
                       [--mode {all,specific}] [--specific_list LIST_OF_INPUTS (example1,example2,...)] [--input INPUT]
                       [--output OUTPUT] [--expected_output EXPECTED_OUTPUT]
                       [--compare {yes,no}] [--comparison_reports COMPARISON_REPORTS]
                       [--comparison_ignore LIST_OF_PATHS (path1,path2,..)][--request_timeout REQUEST_TIMEOUT]
        example:
        python wiser_tester.py --host 'localhost:5000' --origin 'http://localhost:5050' --username maya --password mayah --config config.json

Using the Standalone Executable:
    command line arguments:
        wiser_tester.exe --host HOST --origin ORIGIN --username USERNAME --password PASSWORD --config CONFIG_FILE_PATH
                       [--mode {all,specific}] [--specific_list LIST_OF_INPUTS (example1,example2,...)] [--input INPUT]
                       [--output OUTPUT] [--expected_output EXPECTED_OUTPUT]
                       [--compare {yes,no}] [--comparison_reports COMPARISON_REPORTS]
                       [--comparison_ignore LIST_OF_PATHS (path1,path2,..)][--request_timeout REQUEST_TIMEOUT]

Using the buildNewExe script to build new exe
       .\buildNewExe.bat