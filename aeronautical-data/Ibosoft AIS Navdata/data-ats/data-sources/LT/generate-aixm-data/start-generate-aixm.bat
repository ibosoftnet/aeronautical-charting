@echo off
REM Generate the LT AIXM 5.2 XML from the fetched raw data.
cd /d "%~dp0"
python "%~dp0generate_aixm.py"
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
