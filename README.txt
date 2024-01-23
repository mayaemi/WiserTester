
Using python
    creating environment
        python -m venv myenv
        myenv\Scripts\activate
        pip install -r requirements.txt
    creating new exe
        pyinstaller --onefile wiser_tester.py
    running script
        usage: wiser_tester.py [-h] --username USERNAME --password PASSWORD
                       [--mode {all,specific}] [--input INPUT]
                       [--output OUTPUT] [--expected_output EXPECTED_OUTPUT]
                       [--compare {yes,no}]


Using the Standalone Executable:
    basic execution:
        .\dist\wiser_tester.exe

    command line arguments:
        .\dist\wiser_tester --username USERNAME --password PASSWORD
                       [--mode {all,specific}] [--input INPUT]
                       [--output OUTPUT] [--expected_output EXPECTED_OUTPUT]
                       [--compare {yes,no}]

Using the buildNewExe script
       .\buildNewExe.bat