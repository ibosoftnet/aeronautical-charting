@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo AIXM Obstacle (VerticalStructure) -^> GeoPackage donusturucu
echo =============================================================
echo.

py build_obstacles_gpkg.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo HATA: Donusturme basarisiz! Python kurulu mu?
    pause
    exit /b 1
)

echo.
echo Cikti: %~dp0obstacles.gpkg
echo Katman: obstacles
echo.
pause
