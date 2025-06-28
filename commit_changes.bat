@echo off
REM Change directory to the folder where this script is located
cd /d "%~dp0"

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