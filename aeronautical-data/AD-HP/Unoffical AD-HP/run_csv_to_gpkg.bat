@echo off
cd /d "%~dp0"
py csv_to_gpkg.py
if %errorlevel% neq 0 (
    python csv_to_gpkg.py
)
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Script failed. Make sure geopandas is installed:
    echo   pip install geopandas
    echo.
)
pause
