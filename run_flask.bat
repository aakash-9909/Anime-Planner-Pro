@echo off
REM Change directory to the folder where this script is located
cd /d "%~dp0"

REM Auto pull functionality on startup
echo Starting git operations...

REM Check if this is a git repository
git status >nul 2>&1
if %errorlevel% neq 0 (
    echo This is not a git repository. Skipping git operations.
    goto :start_flask
)

REM Pull latest changes if available (ONLY on startup)
echo Checking for updates...
git pull origin main 2>nul
if %errorlevel% equ 0 (
    echo Successfully pulled latest changes.
) else (
    git pull origin master 2>nul
    if %errorlevel% equ 0 (
        echo Successfully pulled latest changes.
    ) else (
        echo No remote repository found or no updates available.
    )
)

:start_flask
REM Set Flask environment variables
set FLASK_APP=app.py
set FLASK_ENV=development

echo Starting Flask application...
REM Run Flask
python -m flask run

REM Auto commit functionality on exit
echo.
echo Flask application stopped. Committing changes...
echo.

REM Check if this is a git repository
git status >nul 2>&1
if %errorlevel% neq 0 (
    echo This is not a git repository. Skipping commit.
    goto :end
)

REM Add all changes
echo Adding all changes...
git add .

REM Check if there are changes to commit
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo No changes to commit.
) else (
    REM Commit changes with timestamp
    echo Committing changes...
    for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
    set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
    set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
    set "datestamp=%YYYY%-%MM%-%DD% %HH%:%Min%:%Sec%"
    git commit -m "Auto commit: %datestamp%"
    echo Changes committed successfully!
)

:end
REM Keep the window open after Flask stops
pause