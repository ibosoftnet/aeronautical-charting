@echo off
REM Generate the LT AIXM 5.2 XML from the fetched raw data.
cd /d "%~dp0"
python "%~dp0generate_aixm.py"
pause
