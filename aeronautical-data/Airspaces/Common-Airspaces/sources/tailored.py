"""
tailored kaynağı — elle tanımlı GeoJSON (data-sources/tailored/tailored.json).

source = tailored, dataProvider = ibosoft
Her feature.properties ortak şema kolonlarını taşır; geometry GeoJSON
Polygon/MultiPolygon. Dosya yoksa boş taslak yazılır (ilk çalıştırma).
"""
import json
import os

from common import schema
from common.geo import polygon_from_geojson

SOURCE = "tailored"
PROVIDER = "ibosoft"

# source/dataProvider modül tarafından yazılır; taslakta gösterilmez.
_TEMPLATE_PROPS = [n for n in schema.ATTR_NAMES if n not in ("source", "dataProvider")]


def _blank_template():
    return {
        "type": "FeatureCollection",
        "_help": (
            "Elle hava sahası tanımlama. Her feature.properties ortak şema "
            "kolonlarını içerir (source/dataProvider otomatik: tailored/ibosoft). "
            "Aşağıdaki _example'ı 'features' listesine kopyalayıp doldurun."
        ),
        "_example": {
            "type": "Feature",
            "properties": {n: "" for n in _TEMPLATE_PROPS},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[29.0, 41.0], [29.1, 41.0], [29.1, 41.1], [29.0, 41.0]]],
            },
        },
        "features": [],
    }


def load(cfg, base):
    path = os.path.join(base, cfg["tailored"]["file"])
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_blank_template(), f, ensure_ascii=False, indent=2)
        print(f"    [tailored] boş taslak oluşturuldu: {path}")
        return
    with open(path, encoding="utf-8") as f:
        fc = json.load(f)
    if fc.get("type") != "FeatureCollection":
        print("    [tailored] geçersiz FeatureCollection, atlanıyor")
        return
    for feat in fc.get("features", []):
        geom = polygon_from_geojson(feat.get("geometry"))
        if geom is None:
            continue
        props = feat.get("properties") or {}
        rec = schema.blank_record()
        for n in schema.ATTR_NAMES:
            if props.get(n) is not None:
                rec[n] = props[n]
        rec["source"] = SOURCE
        rec["dataProvider"] = PROVIDER
        rec["geometry"] = geom
        yield rec
