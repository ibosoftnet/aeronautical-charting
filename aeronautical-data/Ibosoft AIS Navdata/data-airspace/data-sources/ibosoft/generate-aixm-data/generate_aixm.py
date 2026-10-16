"""ibosoft (originator Ibosoft AIS, elle tutulan) hava sahaları → AIXM 5.2.

Girdi : ../ibosoft-airspace.json     (biçim: data-airspace/tailored_geojson.py)
Çıktı : ../ibosoft-airspace-aixm.xml
Log   : errored-features.log
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parents[2]))               # data-airspace
sys.path.insert(0, str(BASE_DIR.parents[3] / "common"))    # data_build_common

from airspace_aixm import ErrorLog, generate               # noqa: E402
import tailored_geojson                                    # noqa: E402

SOURCE_DIR = BASE_DIR.parent

if __name__ == "__main__":
    log = ErrorLog(BASE_DIR / "errored-features.log")
    generate(tailored_geojson.load(SOURCE_DIR / "ibosoft-airspace.json",
                                   "IBO", log),
             SOURCE_DIR / "ibosoft-airspace-aixm.xml",
             "IBO_MSG_AIRSPACE", log, "ibosoft")
