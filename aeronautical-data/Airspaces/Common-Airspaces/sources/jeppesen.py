"""
Jeppesen kaynağı — jeppesen.sqlite `boundary` tablosu.

source = jeppesen, dataProvider = (boş)
- type            = airspace_type(name, ham_type) or 'OTHER'  (öncelik sıralı)
- classification  = CA->A ... CG->G
- designator      = restrictive_type-restrictive_designation
- dikey limitler feet; max_altitude_type=UL -> upperLimit='UNL'
- fir-exclude: Türk FIR içindeki (centroid) sahalar elenir ('FREE RT' korunur)
"""
import json
import os
import sqlite3

from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

from common import schema
from common.classify import airspace_type, jeppesen_classification, normalize_vref
from common.geo import antimeridian_safe, decode_polygon_blob, polygon_from_geojson

SOURCE = "jeppesen"
PROVIDER = ""

BCOLS = [
    "type", "name", "restrictive_type", "restrictive_designation",
    "min_altitude", "max_altitude", "min_altitude_type", "max_altitude_type",
]


def _designator(rt, rd):
    parts = [p for p in [(rt or "").strip(), (rd or "").strip()] if p]
    return "-".join(parts)


def _is_fir_uir(jtype, name):
    """
    FIR/UIR ön-elemesi (tip filtrelerinden önce). Elenecekler:
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


def _load_fir(path):
    if not path or not os.path.exists(path):
        print(f"    [jeppesen] fir-exclude yok: {path} (atlanıyor)")
        return None
    with open(path, encoding="utf-8") as f:
        fc = json.load(f)
    polys = [p for feat in fc.get("features", [])
             if (p := polygon_from_geojson(feat.get("geometry"))) is not None]
    return prep(unary_union(polys)) if polys else None


def load(cfg, base):
    jc = cfg["jeppesen"]
    fir = None
    if jc.get("fir_exclude_enabled", True):
        fir = _load_fir(os.path.join(base, jc["fir_exclude"]))

    add_date = schema.file_mtime_str(jc["sqlite"])
    conn = sqlite3.connect(jc["sqlite"])
    conn.row_factory = sqlite3.Row
    sel = "SELECT " + ", ".join(BCOLS) + ", geometry FROM boundary"
    for row in conn.execute(sel):
        # Ön-eleme: FIR/UIR sahaları tip filtrelerinden önce atılır.
        if _is_fir_uir(row["type"], row["name"]):
            continue
        coords = decode_polygon_blob(row["geometry"])
        if coords is None:
            continue
        # Ham koordinatlar ±180 sıçraması içerebilir; merkezi fonksiyonla
        # güvenli geometriye çevir (fir-exclude centroid testi doğru olsun).
        geom = antimeridian_safe(Polygon(coords))
        if geom is None or geom.is_empty:
            continue
        name = row["name"] or ""
        if fir is not None and "FREE RT" not in name.upper() and fir.contains(geom.centroid):
            continue

        jtype = row["type"] or ""
        rec = schema.blank_record()
        rec.update(
            type=airspace_type(name, jtype) or "OTHER",
            designator=_designator(row["restrictive_type"], row["restrictive_designation"]),
            name=name,
            classification=jeppesen_classification(jtype),
            source=SOURCE,
            dataProvider=PROVIDER,
            add_date=add_date,
            geometry=geom,
        )
        maxt = (row["max_altitude_type"] or "").strip().upper()
        if maxt == "UL":
            rec["upperLimit"] = "UNL"
        elif row["max_altitude"] is not None:
            rec["upperLimit"] = str(row["max_altitude"])
            rec["upperLimitUom"] = "FT"
            rec["upperLimitReference"] = normalize_vref(maxt)
        if row["min_altitude"] is not None:
            rec["lowerLimit"] = str(row["min_altitude"])
            rec["lowerLimitUom"] = "FT"
            rec["lowerLimitReference"] = normalize_vref(row["min_altitude_type"])
        yield rec
    conn.close()
