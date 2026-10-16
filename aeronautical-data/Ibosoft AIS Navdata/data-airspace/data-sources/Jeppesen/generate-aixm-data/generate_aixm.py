"""Jeppesen (Navigraph) `boundary` tablosu → AIXM 5.2 Airspace.

Girdi : aeronautical-data/Jeppesen Data/jeppesen.sqlite  (`boundary`)
        aeronautical-data/Jeppesen Data/data.json        (provenance)
Çıktı : ../jeppesen-airspace-aixm.xml
Log   : errored-features.log

Eşleme eski `Common Airspaces/sources/jeppesen.py` ile AYNIDIR (kullanıcı
kararı), iki fark dışında:
- FIR/UIR ön elemesi (`_is_fir_uir`) aynen burada; FIR/UIR verisi ayrı ana
  kaynak olan ICAO-FIR-UIR'den gelir.
- Eski "Türk/Macar FIR içindeki sahaları ele" kuralı ARTIK BURADA DEĞİL:
  birleştiricide iki iptal kuralıdır (data-sources/excludes/jeppesen-*.json).
- designator = yalnızca `restrictive_designation` (kullanıcı kararı): eski
  `restrictive_type-restrictive_designation` biçimi 3.240 kayıtta AIXM'in 10
  karakter sınırını aşıyordu; `restrictive_type` zaten `type`'a eşleniyor.

- type            = airspace_type(name, ham_type) yoksa 'OTHER'
- classification  = CA→A … CG→G
- dikey limitler feet; max_altitude_type=UL → upperLimit='UNL'
Ayrıntı: Jeppesen_to_AIXM_Mapping.md
"""
import json
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parents[2]))               # data-airspace
sys.path.insert(0, str(BASE_DIR.parents[3] / "common"))    # data_build_common

from shapely.geometry import Polygon                       # noqa: E402

from airspace_aixm import (AirspaceRecord, ErrorLog, Limit,  # noqa: E402
                           feature_uuid, generate)
from airspace_classify import (airspace_type,              # noqa: E402
                               jeppesen_classification, normalize_vref)
from airspace_geo import antimeridian_safe, decode_polygon_blob  # noqa: E402

SOURCE_DIR = BASE_DIR.parent
# generate-aixm-data → Jeppesen → data-sources → data-airspace →
# Ibosoft AIS Navdata → aeronautical-data
JEPPESEN_DATA = BASE_DIR.parents[4] / "Jeppesen Data"
SQLITE_PATH = JEPPESEN_DATA / "jeppesen.sqlite"
DATA_JSON = JEPPESEN_DATA / "data.json"

BCOLS = ["boundary_id", "type", "name", "restrictive_type",
         "restrictive_designation", "min_altitude", "max_altitude",
         "min_altitude_type", "max_altitude_type"]


def _is_fir_uir(jtype, name):
    """FIR/UIR ön elemesi (eski koddan birebir). Elenecekler:
    - type = FIR veya UIR
    - type = C olup adında fir/uir geçen (ör. 'ANKARA (FIR)', 'ZAGREB (UIR)')
    """
    jt = (jtype or "").strip().upper()
    if jt in ("FIR", "UIR"):
        return True
    if jt == "C":
        nl = (name or "").lower()
        if "fir" in nl or "uir" in nl:
            return True
    return False


def load(meta, log, stats):
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    sel = "SELECT " + ", ".join(BCOLS) + ", geometry FROM boundary"
    for row in conn.execute(sel):
        gml_id = f"JEPP_AS_{row['boundary_id']}"
        if _is_fir_uir(row["type"], row["name"]):
            stats["fir_uir_elendi"] += 1
            continue
        coords = decode_polygon_blob(row["geometry"])
        if coords is None:
            log.error("Airspace", gml_id, "geometry", "-", "gecersiz_blob")
            continue
        geometry = antimeridian_safe(Polygon(coords))
        if geometry is None or geometry.is_empty:
            log.error("Airspace", gml_id, "geometry", "-", "gecersiz_geometri")
            continue

        name = row["name"] or ""
        jtype = row["type"] or ""
        upper = Limit()
        maxt = (row["max_altitude_type"] or "").strip().upper()
        if maxt == "UL":
            upper = Limit("UNL")
        elif row["max_altitude"] is not None:
            upper = Limit(str(row["max_altitude"]), "FT", normalize_vref(maxt))
        lower = Limit()
        if row["min_altitude"] is not None:
            lower = Limit(str(row["min_altitude"]), "FT",
                          normalize_vref(row["min_altitude_type"]))
        yield AirspaceRecord(
            gml_id=gml_id,
            uuid=feature_uuid("JeppesenAirspace", str(row["boundary_id"])),
            geometry=geometry,
            provider=meta.get("data_provider"),
            originator=meta.get("data_originator"),
            effectivity=meta.get("data_effectivity"),
            type=airspace_type(name, jtype) or "OTHER",
            designator=(row["restrictive_designation"] or "").strip() or None,
            name=name or None,
            classification=jeppesen_classification(jtype) or None,
            upper=upper, lower=lower)
    conn.close()


if __name__ == "__main__":
    from collections import Counter
    meta = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    log = ErrorLog(BASE_DIR / "errored-features.log")
    stats = Counter()
    generate(load(meta, log, stats), SOURCE_DIR / "jeppesen-airspace-aixm.xml",
             "JEPP_MSG_AIRSPACE", log, "Jeppesen")
    print(f"  {'fir_uir_on_elemesi':40} {stats['fir_uir_elendi']}")
