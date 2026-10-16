"""ICAO FIR/UIR sınırları (ibosoft-tailored, 2021) → AIXM 5.2 Airspace.

Girdi : ../fir-2021-ibosoft-tailored.json
        (kopya: aeronautical-data/Airspaces/ICAO/FIR/fir-2021-ibosoft-tailored.json)
        ../data.json  (provenance: ICAO GIS / 2021 (Non-AIRAC); originator yok)
Çıktı : ../icao-fir-uir-airspace-aixm.xml
Log   : errored-features.log

Eşleme (kullanıcı kararları):
- type            = KIND (FIR / UIR); başka değer (ölçüldü: NIL1/NIL2'de boş) → yazılmaz
- designator      = ICAOCODE
- name            = FIRname
- annotation      = REMARKS, REMARKS2, REMARKS3 (her biri ayrı REMARK notu)
- dikey limitler  = YOK (kaynakta sayısal seviye yok; eksik bilgi boş kalır)
- ibosoftais:AirspaceExtension
    regionIcao    = REGION
    regionSupProc = SUPP_REGIO
Aktarılmayan alanlar ve gerekçeleri: ICAO-FIR-UIR_to_AIXM_Mapping.md
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parents[2]))               # data-airspace
sys.path.insert(0, str(BASE_DIR.parents[3] / "common"))    # data_build_common

from airspace_aixm import (AirspaceRecord, ErrorLog,       # noqa: E402
                           feature_uuid, generate)
from airspace_geo import polygon_from_geojson              # noqa: E402

SOURCE_DIR = BASE_DIR.parent
TYPES = {"FIR", "UIR"}


def _v(props, key):
    value = props.get(key)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def load(meta, log):
    fc = json.loads((SOURCE_DIR / "fir-2021-ibosoft-tailored.json")
                    .read_text(encoding="utf-8"))
    for feat in fc["features"]:
        props = feat.get("properties") or {}
        object_id = props.get("OBJECTID")
        gml_id = f"FIR_AS_{object_id}"
        geometry = polygon_from_geojson(feat.get("geometry"))
        if geometry is None:
            log.error("Airspace", gml_id, "geometry", "-", "gecersiz_geometri")
            continue
        kind = _v(props, "KIND")
        if kind and kind not in TYPES:
            log.error("Airspace", gml_id, "KIND", kind, "beklenmeyen_tur")
        yield AirspaceRecord(
            gml_id=gml_id,
            uuid=feature_uuid("IcaoFirAirspace", str(object_id)),
            geometry=geometry,
            provider=meta.get("data_provider"),
            originator=meta.get("data_originator"),
            effectivity=meta.get("data_effectivity"),
            type=kind if kind in TYPES else None,
            designator=_v(props, "ICAOCODE"),
            name=_v(props, "FIRname"),
            notes=[("REMARK", _v(props, k))
                   for k in ("REMARKS", "REMARKS2", "REMARKS3") if _v(props, k)],
            region_icao=_v(props, "REGION"),
            region_sup_proc=_v(props, "SUPP_REGIO"))


if __name__ == "__main__":
    meta = json.loads((SOURCE_DIR / "data.json").read_text(encoding="utf-8"))
    log = ErrorLog(BASE_DIR / "errored-features.log")
    generate(load(meta, log), SOURCE_DIR / "icao-fir-uir-airspace-aixm.xml",
             "FIR_MSG_AIRSPACE", log, "ICAO-FIR-UIR")
