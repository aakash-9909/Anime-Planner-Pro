@echo off
REM Change directory to the folder where this script is located
cd /d "%~dp0"

echo ========================================
echo Starting Anime Planner
echo ========================================
echo.

REM Git pull on startup
echo [1/2] Pulling latest changes...
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

echo [2/2] Starting Flask application...
echo.
echo ========================================
echo IMPORTANT: After stopping Flask (Ctrl+C)
echo Run 'commit_changes.bat' to save changes
echo ========================================
echo.

REM Run Flask
python -m flask run

echo.
echo Flask stopped. Remember to run commit_changes.bat to save your changes!
echo.
pause