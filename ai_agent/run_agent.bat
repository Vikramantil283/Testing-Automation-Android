@echo off
REM AI Test Agent - Manual trigger
REM Run this when your task is done and you want tests generated.
REM Usage: ai_agent\run_agent.bat [base-branch]
REM   base-branch defaults to "main"

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
pushd "%PROJECT_ROOT%"
set "PROJECT_ROOT=%CD%"
popd

set "BASE=%~1"
if "%BASE%"=="" set "BASE=main"

REM Detect current branch
for /f "tokens=*" %%i in ('git -C "%PROJECT_ROOT%" rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%i"
if "%BRANCH%"=="" (
    echo [ERROR] Could not detect current branch. Are you in a git repo?
    exit /b 1
)

echo.
echo [AI Test Agent] Manual trigger
echo   Branch : %BRANCH%
echo   Base   : %BASE%
echo   Root   : %PROJECT_ROOT%
echo.

REM Locate Python
set "PYTHON="
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
) do (
    if exist %%P (
        set "PYTHON=%%~P"
        goto :found_python
    )
)
where python >nul 2>&1 && set "PYTHON=python" && goto :found_python
echo [ERROR] Python not found. Install Python 3.8+ and re-run.
exit /b 1

:found_python
echo [OK] Using Python: %PYTHON%
echo.

"%PYTHON%" "%SCRIPT_DIR%ai_test_agent.py" ^
    --branch "%BRANCH%" ^
    --base "%BASE%" ^
    --project-root "%PROJECT_ROOT%"
