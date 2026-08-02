@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo LH Engel Verisi (Excel) -^> AIXM 5.1 XML donusturucu
echo =============================================================
echo.

py build_lh_obstacles_aixm.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo HATA: Donusturme basarisiz! Python ve openpyxl kurulu mu?
    pause
    exit /b 1
)

echo.
echo Cikti: %~dp0LH_ENR_5_4_Obstacles_AIXM_5_1.xml
echo.
pause
