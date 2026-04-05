@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo AD-HP ARP + usage XML to GeoPackage donusturucu
echo ==============================================
echo.

python build_ad_hp_gpkg.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo HATA: Donusturme basarisiz! Python kurulu mu?
    pause
    exit /b 1
)

echo.
echo Cikti: %~dp0ad-hp.gpkg
echo Katman: ad_hp_airports
echo.
pause
