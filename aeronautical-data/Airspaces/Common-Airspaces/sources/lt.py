"""
LT kaynağı — DHMI GeoJSON (data-sources/LT/*.json).

source = tailored, dataProvider = dhmi
- type          = dosya adı (TMA.json -> TMA)
- designator    = property `hi`
- name          = pic içindeki 2. NAME (açıklayıcı)
- dikey limitler + referanslar pic'ten; uom referanstan türetilir.
"""
import glob
import json
import os

from common import schema
from common.classify import derive_uom
from common.geo import parse_pic, polygon_from_geojson

SOURCE = "tailored"
PROVIDER = "dhmi"

# SECTOR verisi tailored.json'a elle taşındı; LT modülü artık işlemez.
SKIP_FILES = {"SECTOR"}


def load(cfg, base):
    lt_dir = os.path.join(base, cfg["lt"]["dir"])
    for path in sorted(glob.glob(os.path.join(lt_dir, "*.json"))):
        typ = os.path.splitext(os.path.basename(path))[0]
        if typ in SKIP_FILES:
            continue
        add_date = schema.file_mtime_str(path)
        with open(path, encoding="utf-8") as f:
            fc = json.load(f)
        for feat in fc.get("features", []):
            props = feat.get("properties") or {}
            geom = polygon_from_geojson(feat.get("geometry"))
            if geom is None:
                continue
            pic = parse_pic(props.get("pic", ""))
            names = pic.get("NAME", [])
            name = names[1] if len(names) >= 2 else (names[0] if names else "")
            upr = (pic.get("UPPER LIMIT REF.") or [""])[0]
            lor = (pic.get("LOWER LIMIT REF.") or [""])[0]

            rec = schema.blank_record()
            rec.update(
                type=typ,
                designator=props.get("hi") or "",
                name=name,
                upperLimit=(pic.get("UPPER LIMIT") or [""])[0],
                upperLimitUom=derive_uom(upr),
                upperLimitReference=upr,
                lowerLimit=(pic.get("LOWER LIMIT") or [""])[0],
                lowerLimitUom=derive_uom(lor),
                lowerLimitReference=lor,
                source=SOURCE,
                dataProvider=PROVIDER,
                add_date=add_date,
                geometry=geom,
            )
            yield rec
