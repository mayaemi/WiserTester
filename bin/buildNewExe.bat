@echo off
SETLOCAL

REM Define directories
SET "PROJECT_DIR=%CD%"
SET "VENV_DIR=%PROJECT_DIR%\cleanVenv"
SET "DIST_DIR=%PROJECT_DIR%\dist"
SET "BUILD_DIR=%PROJECT_DIR%\build"
SET "ENTRY_SCRIPT=main.py"
SET "PYTHON_EXE=python" 
REM Specify the full path if python is not in PATH, e.g., SET "PYTHON_EXE=C:\Path\To\Python\python.exe"

REM Ensure Python is available
%PYTHON_EXE% --version || (
    ECHO Python is not available. Make sure Python is installed and in PATH.
    GOTO END
)

REM Create a virtual environment
ECHO Creating virtual environment...
%PYTHON_EXE% -m venv "%VENV_DIR%"
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip

REM Activate the virtual environment
CALL "%VENV_DIR%\Scripts\activate.bat"

REM Install dependencies
ECHO Installing dependencies...
"%VENV_DIR%\Scripts\pip.exe" install -r "%PROJECT_DIR%\requirements.txt"

REM Remove previous builds
ECHO Removing old builds...
IF EXIST "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
IF EXIST "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"

REM Create the executable
ECHO Creating executable...
"%VENV_DIR%\Scripts\pyinstaller.exe" --clean --onefile --distpath "%DIST_DIR%" "%PROJECT_DIR%\%ENTRY_SCRIPT%"

REM Check for errors after PyInstaller
IF %ERRORLEVEL% NEQ 0 (
    ECHO Failed to create executable.
    GOTO CLEANUP
)

REM Deactivate and delete the virtual environment
:CLEANUP
ECHO deactivating environment
CALL "%VENV_DIR%\Scripts\deactivate.bat"
rmdir /s /q "%VENV_DIR%"

ECHO Build completed.

:END
ENDLOCAL
