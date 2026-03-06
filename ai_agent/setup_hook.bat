@echo off
REM AI Test Agent - One-time Windows setup
REM Run this once from the project root: ai_agent\setup_hook.bat

setlocal EnableDelayedExpansion

echo.
echo [AI Test Agent Setup]
echo =====================

REM ── Locate project root (parent of this script's directory) ──────────────
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Resolve to absolute path
pushd "%PROJECT_ROOT%"
set "PROJECT_ROOT=%CD%"
popd

echo Project root: %PROJECT_ROOT%

REM ── Verify we are in a git repo ──────────────────────────────────────────
if not exist "%PROJECT_ROOT%\.git\" (
    echo [ERROR] Not a git repository: %PROJECT_ROOT%
    exit /b 1
)

REM ── Install the hook ─────────────────────────────────────────────────────
set "HOOK_SRC=%SCRIPT_DIR%hooks\pre-push"
set "HOOK_DST=%PROJECT_ROOT%\.git\hooks\pre-push"

if not exist "%SCRIPT_DIR%hooks\pre-push" (
    echo [ERROR] Hook source not found: %HOOK_SRC%
    exit /b 1
)

copy /Y "%HOOK_SRC%" "%HOOK_DST%" >nul
echo [OK] Hook installed: .git\hooks\pre-push

REM ── Install Python dependencies ───────────────────────────────────────────
echo.
echo [Setup] Installing Python dependencies...

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARN] Python not found in PATH. Install Python 3.8+ and re-run this script.
    goto :setup_env
)

python -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet
if %ERRORLEVEL% equ 0 (
    echo [OK] Python dependencies installed.
) else (
    echo [WARN] pip install had issues. Check manually: pip install -r ai_agent\requirements.txt
)

:setup_env
REM ── Create .env if it doesn't exist ──────────────────────────────────────
echo.
if not exist "%SCRIPT_DIR%.env" (
    copy /Y "%SCRIPT_DIR%.env.example" "%SCRIPT_DIR%.env" >nul
    echo [OK] Created ai_agent\.env from template.
    echo.
    echo ^>^>^> ACTION REQUIRED: Edit ai_agent\.env and set your ANTHROPIC_API_KEY ^<^<^<
) else (
    echo [OK] ai_agent\.env already exists.
)

REM ── Done ──────────────────────────────────────────────────────────────────
echo.
echo =====================
echo Setup complete!
echo.
echo Next steps:
echo   1. Edit ai_agent\.env and set ANTHROPIC_API_KEY=sk-ant-...
echo   2. Make changes on a branch and run: git push
echo   3. The agent will run automatically and save reports to ai_agent\reports\
echo.
