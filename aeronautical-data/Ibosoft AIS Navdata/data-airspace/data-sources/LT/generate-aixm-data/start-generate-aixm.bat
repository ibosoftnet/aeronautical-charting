@echo off
cd /d "%~dp0"
py generate_aixm.py
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
