@echo off
REM Ortak dogrulayici: Ibosoft AIS Navdata\common\data_build_common\validate_aixm.py
cd /d "%~dp0"
py "..\..\..\..\common\data_build_common\validate_aixm.py" "..\ead-sdo-aixm.xml"
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
