@echo off
REM Change directory to the folder where this script is located
cd /d "%~dp0"

REM Set Flask environment variables
set FLASK_APP=app.py
set FLASK_ENV=development

REM Run Flask
python -m flask run

REM Keep the window open after Flask stops
pause