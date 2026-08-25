"""
tailored kaynağı — elle tanımlı GeoJSON (data-sources/tailored/tailored.json).

data_provider/data_originator/data_effectivity her feature.properties içinde
elle girilir (kaynak dizinindeki data.json mekanizması burada yok). Dosyanın
kökündeki "_effectivity_keys" sözlüğü, properties.data_effectivity alanında
anahtar adı geçen kayıtlar için değeri çözer (AIRAC güncellemesini tek yerden
yapabilmek için, ör. "eff_lt" -> "09 JUL 2026 (AIRAC 2607)").
Dosya yoksa boş taslak yazılır (ilk çalıştırma).
"""
import json
import os

from common import schema
from common.geo import polygon_from_geojson

_TEMPLATE_PROPS = list(schema.ATTR_NAMES)


def _blank_template():
    return {
        "type": "FeatureCollection",
        "_effectivity_keys": {},
        "_help": (
            "Elle hava sahası tanımlama. Her feature.properties ortak şema "
            "kolonlarını (data_provider/data_originator/data_effectivity dahil) "
            "içerir. data_effectivity alanına '_effectivity_keys' altındaki bir "
            "anahtarın adı yazılırsa değeri oradan çözülür. Aşağıdaki _example'ı "
            "'features' listesine kopyalayıp doldurun."
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
    eff_keys = fc.get("_effectivity_keys", {}) or {}
    for feat in fc.get("features", []):
        geom = polygon_from_geojson(feat.get("geometry"))
        if geom is None:
            continue
        props = feat.get("properties") or {}
        rec = schema.blank_record()
        for n in schema.ATTR_NAMES:
            if props.get(n) is not None:
                rec[n] = props[n]
        if rec["data_effectivity"] in eff_keys:
            rec["data_effectivity"] = eff_keys[rec["data_effectivity"]]
        rec["geometry"] = geom
        yield rec
