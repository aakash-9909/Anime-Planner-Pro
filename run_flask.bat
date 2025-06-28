@echo off
REM Change directory to the folder where this script is located
cd /d "%~dp0"

echo ========================================
echo Starting Anime Planner with Git Sync
echo ========================================
echo.

REM Git pull on startup
echo [1/4] Pulling latest changes...
git pull origin main
if %errorlevel% equ 0 (
    echo ✓ Successfully pulled latest changes
) else (
    echo ✗ Failed to pull changes (continuing anyway)
)
echo.

REM Set Flask environment variables
set FLASK_APP=app.py
set FLASK_ENV=development

echo [2/4] Starting Flask application...
echo Press Ctrl+C to stop Flask and save changes
echo.

REM Run Flask
python -m flask run

echo.
echo ========================================
echo Flask stopped. Saving changes...
echo ========================================
echo.

REM Git operations on exit
echo [3/4] Adding all changes...
git add .

echo [4/4] Committing and pushing...
REM Get timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "datestamp=%dt:~0,4%-%dt:~4,2%-%dt:~6,2% %dt:~8,2%:%dt:~10,2%:%dt:~12,2%"

git commit -m "%datestamp%"
git push origin main

echo.
echo ✓ Git operations completed!
echo.
pause