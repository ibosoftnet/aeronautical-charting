"""
LH kaynağı — Macaristan TNP formatı (data-sources/LH/data.txt).

source = tailored, dataProvider = soaringweb
Kayıtlar INCLUDE=YES ile başlar; alanlar CLASS/TYPE/TITLE/TOPS/BASE/POINT.
- name           = TITLE
- classification = CLASS
- type           = TYPE (PROHIBITED/RESTRICTED/DANGER) else başlıktan (airspace_type)
- dikey limitler = TOPS/BASE (ft + STD/MSL/AGL; GND özel değer)
- geometri       = POINT=Nddmmss Edddmmss (DMS -> ondalık), poligon
"""
import os

from shapely.geometry import Polygon

from common import schema
from common.classify import LH_TYPE_MAP, lh_type_from_title, parse_lh_altitude
from common.geo import parse_dms

SOURCE = "tailored"
PROVIDER = "soaringweb"


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


def load(cfg, base):
    path = os.path.join(base, cfg["lh"]["file"])
    add_date = schema.file_mtime_str(path)
    for r in _iter_records(path):
        coords = _coords(r.get("points", []))
        if len(coords) < 3:
            continue
        # Ham poligon; antimeridyen koruması merkezde (insert_record) uygulanır.
        try:
            geom = Polygon(coords)
        except (ValueError, TypeError):
            continue
        if geom.is_empty:
            continue

        title = r.get("TITLE", "")
        lhtype = (r.get("TYPE") or "").strip().upper()
        # Açık TYPE (P/R/D) > başlıktan (TMA/CTR/CTA/RMZ/TMZ...) > fallback RAS.
        typ = LH_TYPE_MAP.get(lhtype) or lh_type_from_title(title) or "RAS"

        up_v, up_u, up_r = parse_lh_altitude(r.get("TOPS", ""))
        lo_v, lo_u, lo_r = parse_lh_altitude(r.get("BASE", ""))

        rec = schema.blank_record()
        rec.update(
            type=typ,
            name=title,
            classification=r.get("CLASS", ""),
            upperLimit=up_v, upperLimitUom=up_u, upperLimitReference=up_r,
            lowerLimit=lo_v, lowerLimitUom=lo_u, lowerLimitReference=lo_r,
            source=SOURCE,
            dataProvider=PROVIDER,
            add_date=add_date,
            geometry=geom,
        )
        yield rec
