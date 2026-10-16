"""LT (DHMİ AIS) hava sahası GeoJSON'ları → AIXM 5.2.

Girdi : ../raw-data/<TİP>.json   (navdata-data-downloaders/lt-dhmi indirir)
        ../data.json             (provenance; indirici data_effectivity'yi yazar)
Çıktı : ../lt-airspace-aixm.xml
Log   : errored-features.log

Eşleme (eski `Common Airspaces/sources/lt.py` ile aynı):
- type          = dosya adı (TMA.json → TMA)
- designator    = property `hi`
- name          = `pic` içindeki 2. NAME (açıklayıcı); tek NAME varsa o
- dikey limitler `pic`'ten; uom referanstan türetilir (STD→FL, MSL/SFC→FT)
- SECTOR.json işlenmez: SECTOR verisi tailored-LT kaynağındadır.

Kimlik: kaynağın kendi `kid` değeri (`uuid.<uuid>`) → gml:identifier. Aynı
`kid` birden fazla GeoJSON feature'ında geçiyorsa (ölçüldü: RAS LTIHAT1, 2
parça) bunlar AYNI hava sahasının parçalarıdır: tek Airspace yazılır, geometri
parçaların MultiPolygon'udur. Parçaların öznitelikleri farklıysa birleştirme
yapılmaz, loglanır ve her parça ayrı (türetilmiş kimlikle) yazılır.
Ayrıntı: LT_to_AIXM_Mapping.md
"""
import glob
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parents[2]))               # data-airspace
sys.path.insert(0, str(BASE_DIR.parents[3] / "common"))    # data_build_common

from shapely.geometry import MultiPolygon                  # noqa: E402

from airspace_aixm import (AirspaceRecord, ErrorLog, Limit,  # noqa: E402
                           feature_uuid, generate, ncname)
from airspace_classify import derive_uom                   # noqa: E402
from airspace_geo import parse_pic, polygon_from_geojson   # noqa: E402

SOURCE_DIR = BASE_DIR.parent
RAW_DIR = SOURCE_DIR / "raw-data"
SKIP_FILES = {"SECTOR"}

#: GeoJSON `properties`'ten OKUNANLAR. Geri kalanlar DHMİ web haritasının
#: görüntüleme alanlarıdır (renk, ikon, iframe, z-index…), AIXM karşılıkları
#: yoktur — eşleme dokümanında tek tek listelenir.
USED_PROPS = ("hi", "kid", "pic")


def _attrs(typ, props):
    pic = parse_pic(props.get("pic", ""))
    names = pic.get("NAME", [])
    name = names[1] if len(names) >= 2 else (names[0] if names else "")
    upr = (pic.get("UPPER LIMIT REF.") or [""])[0]
    lor = (pic.get("LOWER LIMIT REF.") or [""])[0]
    return dict(
        type=typ,
        designator=props.get("hi") or None,
        name=name or None,
        upper=((pic.get("UPPER LIMIT") or [""])[0], derive_uom(upr), upr),
        lower=((pic.get("LOWER LIMIT") or [""])[0], derive_uom(lor), lor),
    )


def load(meta, log):
    groups: dict = {}          # kid → [(typ, attrs, geometry)]
    order = []
    for path in sorted(glob.glob(str(RAW_DIR / "*.json"))):
        typ = os.path.splitext(os.path.basename(path))[0]
        if typ in SKIP_FILES:
            continue
        with open(path, encoding="utf-8") as f:
            fc = json.load(f)
        for feat in fc.get("features", []):
            props = feat.get("properties") or {}
            kid = (props.get("kid") or "").strip()
            geometry = polygon_from_geojson(feat.get("geometry"))
            if geometry is None:
                log.error("Airspace", kid or typ, "geometry", "-",
                          "gecersiz_geometri")
                continue
            if not kid.startswith("uuid."):
                log.error("Airspace", typ, "kid", kid, "kaynak_kimligi_yok")
                continue
            if kid not in groups:
                order.append(kid)
            groups.setdefault(kid, []).append((typ, _attrs(typ, props), geometry))

    for kid in order:
        parts = groups[kid]
        uid = kid[len("uuid."):].upper()
        same = all(p[1] == parts[0][1] for p in parts)
        if len(parts) > 1 and not same:
            log.error("Airspace", kid, "kid", len(parts),
                      "ayni_kid_farkli_oznitelik_parcalar_ayri_yazildi")
        chunks = ([(uid, ncname(f"LT_AS_{uid}"), parts)] if same else
                  [(feature_uuid("LtAirspacePart", f"{uid}:{n}"),
                    ncname(f"LT_AS_{uid}_{n}"), [p])
                   for n, p in enumerate(parts, 1)])
        for chunk_uuid, gml_id, chunk in chunks:
            if len(chunk) > 1:
                log.warning("Airspace", gml_id, "geometry", len(chunk),
                            "ayni_kid_parcalari_tek_airspace_yapildi")
            polys = []
            for _, _, geom in chunk:
                polys.extend(geom.geoms if geom.geom_type == "MultiPolygon"
                             else [geom])
            geometry = polys[0] if len(polys) == 1 else MultiPolygon(polys)
            attrs = chunk[0][1]
            yield AirspaceRecord(
                gml_id=gml_id, uuid=chunk_uuid, geometry=geometry,
                provider=meta.get("data_provider"),
                originator=meta.get("data_originator"),
                effectivity=meta.get("data_effectivity"),
                type=attrs["type"], designator=attrs["designator"],
                name=attrs["name"],
                upper=Limit(*attrs["upper"]), lower=Limit(*attrs["lower"]))


if __name__ == "__main__":
    meta = json.loads((SOURCE_DIR / "data.json").read_text(encoding="utf-8"))
    log = ErrorLog(BASE_DIR / "errored-features.log")
    generate(load(meta, log), SOURCE_DIR / "lt-airspace-aixm.xml",
             "LT_MSG_AIRSPACE", log, "LT")
