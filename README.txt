
Using python
    creating environment
        python -m venv myenv
        myenv\Scripts\activate
        pip install -r requirements.txt
    creating new exe
        pyinstaller --onefile wiser_tester.py
    running script
        usage: wiser_tester.py [-h] --username USERNAME --password PASSWORD
                       [--mode {all,specific}] [--specific_list LIST_OF_INPUTS (example1,example2,...)] [--input INPUT]
                       [--output OUTPUT] [--expected_output EXPECTED_OUTPUT]
                       [--compare {yes,no}] [--comparison_reports COMPARISON_REPORTS]


Using the Standalone Executable:
    basic execution:
        wiser_tester.exe

    command line arguments:
        wiser_tester --username USERNAME --password PASSWORD
                       [--mode {all,specific}] [--specific_list LIST_OF_INPUTS (example1,example2,...)] [--input INPUT]
                       [--output OUTPUT] [--expected_output EXPECTED_OUTPUT]
                       [--compare {yes,no}] [--comparison_reports COMPARISON_REPORTS]

Using the buildNewExe script
       .\buildNewExe.bat