@echo off
REM Convert EAD-SDO Designated Points XML files to GeoPackage (UTF-8 support)
REM

setlocal enabledelayedexpansion

REM Set UTF-8 output encoding
chcp 65001 >nul 2>&1

REM Get script directory
set SCRIPT_DIR=%~dp0
set SCRIPT=%SCRIPT_DIR%build_designated_points_gpkg.py

REM Check if script exists
if not exist "%SCRIPT%" (
    echo.
    echo HATA: Script bulunamadi: %SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Run with py launcher (default Python installation)
echo.
echo GeoPackage olusturuluyor...
echo.

py "%SCRIPT%"

if errorlevel 1 (
    echo.
    echo HATA: GeoPackage olusturulurken hata olustu.
    echo.
    pause
    exit /b 1
)

echo.
echo Basarili! designated_points.gpkg olusturuldu.
echo.
pause
exit /b 0
