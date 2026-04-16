@echo off
REM Run the ATS route info fetcher from the current folder.
cd /d "%~dp0"
python "%~dp0fetch_ats_route_info.py"
pause
