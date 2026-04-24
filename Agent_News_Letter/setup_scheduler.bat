@echo off
REM ================================================================
REM  AI Atlas — Windows Task Scheduler Setup
REM  Run this script as Administrator to register a daily task.
REM ================================================================

set TASK_NAME=AIAtlas_DailyDigest
set PYTHON_PATH=python
set SCRIPT_PATH=%~dp0main.py
set RUN_TIME=07:00

echo.
echo  AI Atlas — Task Scheduler Setup
echo  ================================
echo.
echo  Task name : %TASK_NAME%
echo  Script    : %SCRIPT_PATH%
echo  Time      : %RUN_TIME% daily
echo.

schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" ^
    /sc daily ^
    /st %RUN_TIME% ^
    /f

if %errorlevel% equ 0 (
    echo.
    echo  Task created successfully!
    echo  AI Atlas will run daily at %RUN_TIME%.
    echo.
    echo  To run now:      python main.py
    echo  To do a dry run: python main.py --dry
    echo  To remove task:  schtasks /delete /tn "%TASK_NAME%" /f
) else (
    echo.
    echo  Failed to create task. Try running this script as Administrator.
)

pause
