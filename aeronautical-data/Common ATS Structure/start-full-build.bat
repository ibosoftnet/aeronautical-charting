@echo off
REM Tam pipeline: 1) kaynak ureticileri (jeppesen, ead_sdo, lt - config.json
REM sirasiyla; TRNC elle duzenlendigi icin uretici calistirmaz) 2) 2A merge
REM 3) 2B GeoPackage. config.json'daki run_source_generators kapali olsa da
REM --sources bu calistirmayi zorlar.
REM GeoPackage QGIS'te aciksa kilitli olur, once kapatin.
cd /d "%~dp0"
py build_common_ats.py --sources --merge --gpkg
pause
