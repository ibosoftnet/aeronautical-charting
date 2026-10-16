@echo off
REM Tam pipeline: 1) kaynak ureticileri (config.json sirasiyla) 2) 2A merge
REM 3) 2B GeoPackage. GeoPackage QGIS'te aciksa kilitli olur, once kapatin.
cd /d "%~dp0"
py build_common_airspaces.py --sources --merge --gpkg
if errorlevel 1 (
    echo.
    echo ==============================================================
    echo   HATA: islem BASARISIZ oldu ^(cikis kodu %ERRORLEVEL%^)
    echo ==============================================================
) else (
    echo.
    echo ==============================================================
    echo   TAMAM: islem BASARIYLA tamamlandi
    echo ==============================================================
)
pause
