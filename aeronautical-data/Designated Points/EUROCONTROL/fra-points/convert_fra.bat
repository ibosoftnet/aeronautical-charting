@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set SCRIPT_DIR=%~dp0
set SCRIPT=%SCRIPT_DIR%build_fra_gpkg.py

if not exist "%SCRIPT%" (
    echo.
    echo HATA: Script bulunamadi: %SCRIPT%
    echo.
    pause
    exit /b 1
)

echo.
echo FRA Points GeoPackage olusturuluyor...
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
echo Basarili! fra-points.gpkg olusturuldu.
echo.
pause
exit /b 0
