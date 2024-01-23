@echo off
SETLOCAL

REM Define directories
SET "PROJECT_DIR=C:\Users\mayah\PycharmProjects\WiserTester"
SET "VENV_DIR=%PROJECT_DIR%\cleanVenv"
SET "DIST_DIR=%PROJECT_DIR%\dist"
SET "BUILD_DIR=%PROJECT_DIR%\build"
SET "ENTRY_SCRIPT=wiser_tester.py"

REM Create a virtual environment
ECHO Creating virtual environment...
python -m venv "%VENV_DIR%"

REM Activate the virtual environment
CALL "%VENV_DIR%\Scripts\activate.bat"

REM Install dependencies
ECHO Installing dependencies...
pip install -r "%PROJECT_DIR%\requirements.txt"

REM Remove previous builds
ECHO Removing old builds...
IF EXIST "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
IF EXIST "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"

REM Create the executable
ECHO Creating executable...
pyinstaller --clean --onefile --distpath "%DIST_DIR%" "%PROJECT_DIR%\%ENTRY_SCRIPT%"

REM Deactivate and delete the virtual environment
CALL "%VENV_DIR%\Scripts\deactivate.bat"
rmdir /s /q "%VENV_DIR%"

ECHO Build completed.

ENDLOCAL
