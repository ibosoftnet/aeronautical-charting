"""LH (Macaristan) TNP hava sahası dosyası → AIXM 5.2.

Girdi : ../data.txt   (TNP biçimi; INCLUDE=YES ile başlayan kayıtlar)
        ../data.json  (provenance)
Çıktı : ../lh-airspace-aixm.xml
Log   : errored-features.log

Eşleme (eski `Common Airspaces/sources/lh.py` ile aynı):
- name           = TITLE
- classification = CLASS. AIXM listesinde olmayan değer (ölçüldü: `GSEC`)
                   AIXM'in kendi genişletme deseniyle `OTHER:<değer>` yazılır
                   (CodeAirspaceClassificationType union'ı); değer kaybolmaz.
- type           = TYPE (PROHIBITED/RESTRICTED/DANGER) yoksa başlıktan,
                   o da yoksa RAS (eski davranış)
- dikey limitler = TOPS/BASE (`parse_lh_altitude`; GND özel değer)
- geometri       = POINT=Nddmmss Edddmmss → poligon

Kimlik: dosyada kalıcı kimlik yok; uuid5(sıra numarası + başlık). Dosya
değişirse sıra kayabilir — kaynağın kendisi kimlik sağlamıyor.
Ayrıntı: LH_to_AIXM_Mapping.md
"""
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parents[2]))               # data-airspace
sys.path.insert(0, str(BASE_DIR.parents[3] / "common"))    # data_build_common

from shapely.geometry import Polygon                       # noqa: E402

from airspace_aixm import (AirspaceRecord, ErrorLog, Limit,  # noqa: E402
                           feature_uuid, generate)
from airspace_classify import (LH_TYPE_MAP, lh_type_from_title,  # noqa: E402
                               parse_lh_altitude)
from airspace_geo import parse_dms                          # noqa: E402

SOURCE_DIR = BASE_DIR.parent

#: AIXM CodeAirspaceClassificationType sabit listesi + evrensel OTHER deseni.
_AIXM_CLASSES = {"A", "B", "C", "D", "E", "F", "G"}
_OTHER_RE = re.compile(r"OTHER(:(\w|_){1,58})?")

#: Kayıtta OKUNAN anahtarlar; diğerleri loglanır.
KNOWN_KEYS = {"points", "CLASS", "TYPE", "TITLE", "TOPS", "BASE"}


def _iter_records(path):
    rec = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip().upper(), val.strip()
            if key == "INCLUDE":
                if rec is not None:
                    yield rec
                rec = {"points": []}
                continue
            if rec is None:
                continue
            if key == "POINT":
                rec["points"].append(val)
            else:
                rec[key] = val
    if rec is not None:
        yield rec


def _coords(points):
    coords = []
    for p in points:
        lat = lon = None
        for tok in p.split():
            if not tok:
                continue
            if tok[0].upper() in "NS":
                lat = parse_dms(tok)
            elif tok[0].upper() in "EW":
                lon = parse_dms(tok)
        if lat is not None and lon is not None:
            coords.append((lon, lat))
    return coords


def _classification(value, gml_id, log):
    value = (value or "").strip()
    if not value or value in _AIXM_CLASSES or _OTHER_RE.fullmatch(value):
        return value or None
    coded = f"OTHER:{value}"
    log.warning("Airspace", gml_id, "classification", value,
                f"aixm_listesinde_yok_other_ile_yazildi -> {coded}")
    return coded


def load(meta, log):
    for n, r in enumerate(_iter_records(SOURCE_DIR / "data.txt"), 1):
        title = r.get("TITLE", "")
        gml_id = f"LH_AS_{n:04d}"
        for key in sorted(set(r) - KNOWN_KEYS):
            log.error("Airspace", gml_id, key, r[key], "tanimsiz_alan_eslenmedi")
        coords = _coords(r.get("points", []))
        if len(coords) < 3:
            log.error("Airspace", gml_id, "POINT", len(coords), "uc_noktadan_az")
            continue
        try:
            geometry = Polygon(coords)
        except (ValueError, TypeError):
            log.error("Airspace", gml_id, "POINT", "-", "gecersiz_geometri")
            continue
        if geometry.is_empty:
            log.error("Airspace", gml_id, "POINT", "-", "bos_geometri")
            continue

        lhtype = (r.get("TYPE") or "").strip().upper()
        # Açık TYPE (P/R/D) > başlıktan (TMA/CTR/CTA/RMZ/TMZ…) > RAS (eski davranış).
        typ = LH_TYPE_MAP.get(lhtype) or lh_type_from_title(title) or "RAS"
        yield AirspaceRecord(
            gml_id=gml_id,
            uuid=feature_uuid("LhAirspace", f"{n}:{title}"),
            geometry=geometry,
            provider=meta.get("data_provider"),
            originator=meta.get("data_originator"),
            effectivity=meta.get("data_effectivity"),
            type=typ, name=title or None,
            classification=_classification(r.get("CLASS"), gml_id, log),
            upper=Limit(*parse_lh_altitude(r.get("TOPS", ""))),
            lower=Limit(*parse_lh_altitude(r.get("BASE", ""))))


if __name__ == "__main__":
    meta = json.loads((SOURCE_DIR / "data.json").read_text(encoding="utf-8"))
    log = ErrorLog(BASE_DIR / "errored-features.log")
    generate(load(meta, log), SOURCE_DIR / "lh-airspace-aixm.xml",
             "LH_MSG_AIRSPACE", log, "LH")
