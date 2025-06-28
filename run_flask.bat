@echo off
REM Change directory to the folder where this script is located
cd /d "%~dp0"

echo ========================================
echo Starting Anime Planner
echo ========================================
echo.

REM Git pull on startup
echo [1/3] Pulling latest changes...
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

echo [2/3] Starting Flask application...
echo.
echo ========================================
echo Flask is running on http://localhost:5000
echo ========================================
echo.
echo To stop Flask gracefully (recommended):
echo 1. Open a new terminal/command prompt
echo 2. Navigate to this folder
echo 3. Run: taskkill /f /im python.exe
echo.
echo Or press Ctrl+C (will kill entire batch)
echo.

REM Run Flask in background
start /b python -m flask run

echo [3/3] Flask started in background
echo.
echo ========================================
echo IMPORTANT: Use taskkill to stop Flask
echo Then run 'commit_changes.bat' to save
echo ========================================
echo.

REM Wait for user to stop Flask
echo Press any key when you want to stop Flask and commit changes...
pause >nul

REM Stop Flask gracefully
echo Stopping Flask...
taskkill /f /im python.exe >nul 2>&1
echo ✓ Flask stopped

REM Run git operations
echo.
echo ========================================
echo Committing and Pushing Changes
echo ========================================
echo.

REM Check if we're in a git repository
git status >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Error: This is not a git repository!
    pause
    exit /b 1
)

REM Add all changes
echo [1/3] Adding all changes...
git add .
if %errorlevel% neq 0 (
    echo ✗ Failed to add changes
    pause
    exit /b 1
)

REM Check if there are changes to commit
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo ✓ No changes to commit
    goto :push_only
)

REM Get timestamp for commit message
echo [2/3] Committing changes...
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "datestamp=%dt:~0,4%-%dt:~4,2%-%dt:~6,2% %dt:~8,2%:%dt:~10,2%:%dt:~12,2%"

git commit -m "%datestamp%"
if %errorlevel% neq 0 (
    echo ✗ Failed to commit changes
    pause
    exit /b 1
)
echo ✓ Changes committed with message: %datestamp%

:push_only
REM Push changes
echo [3/3] Pushing changes...
git push origin main
if %errorlevel% neq 0 (
    echo ✗ Failed to push changes
    pause
    exit /b 1
)
echo ✓ Successfully pushed changes!

echo.
echo ========================================
echo ✓ All operations completed successfully!
echo ========================================
echo.
pause