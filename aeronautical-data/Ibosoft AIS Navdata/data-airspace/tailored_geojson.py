"""Elle tutulan hava sahası GeoJSON'u → AirspaceRecord.

Bugün yalnız `ibosoft` kaynağı kullanır (TRNC ve tailored-LT'nin AIXM'i elle
düzenlenir, JSON/üreticileri yoktur). Okuma mantığı eski
`Common Airspaces/sources/tailored.py` ile aynıdır:

* Her `feature.properties` aşağıdaki anahtarları taşıyabilir:
  `aixm_uuid` (ZORUNLU, kalıcı kimlik), `type`, `designator`, `name`,
  `localType`, `designatorICAO`, `controlType`, `classification`,
  `upperLimit`/`upperLimitUom`/`upperLimitReference`, `lowerLimit…`,
  `activity`, `status`, `annotationDescription/Remark/Warning/Disclaimer`,
  `data_provider`, `data_originator`, `data_effectivity`.
* Provenance KAYIT BAŞINADIR (data.json yok). `data_effectivity` alanında
  dosya kökündeki `_effectivity_keys` sözlüğünün bir anahtarı yazılıysa
  değeri oradan çözülür (AIRAC güncellemesini tek yerden yapmak için).
"""

import json

from airspace_aixm import AirspaceRecord, Limit
from airspace_geo import polygon_from_geojson

_NOTE_PROPS = (("annotationDescription", "DESCRIPTION"),
               ("annotationRemark", "REMARK"),
               ("annotationWarning", "WARNING"),
               ("annotationDisclaimer", "DISCLAIMER"))

#: Okunan özellik anahtarları; bunların dışındaki bir anahtar loglanır
#: (sessizce atlanmasın diye).
KNOWN_PROPS = {
    "aixm_uuid", "type", "designator", "name", "localType", "designatorICAO",
    "controlType", "classification",
    "upperLimit", "upperLimitUom", "upperLimitReference",
    "lowerLimit", "lowerLimitUom", "lowerLimitReference",
    "activity", "status",
    "data_provider", "data_originator", "data_effectivity",
} | {p for p, _ in _NOTE_PROPS}


def _v(props, key):
    value = props.get(key)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def load(path, gml_prefix, log):
    """GeoJSON dosyası → AirspaceRecord üreteci."""
    fc = json.loads(path.read_text(encoding="utf-8"))
    eff_keys = fc.get("_effectivity_keys") or {}
    for n, feat in enumerate(fc.get("features", []), 1):
        props = feat.get("properties") or {}
        uid = _v(props, "aixm_uuid")
        gml_id = f"{gml_prefix}_AS_{n:03d}"
        if not uid:
            log.error("Airspace", gml_id, "aixm_uuid", "-", "kalici_kimlik_yok")
            continue
        for key in sorted(set(props) - KNOWN_PROPS):
            if props.get(key) not in (None, ""):
                log.error("Airspace", gml_id, key, props[key],
                          "tanimsiz_ozellik_eslenmedi")
        geometry = polygon_from_geojson(feat.get("geometry"))
        if geometry is None:
            log.error("Airspace", gml_id, "geometry", "-", "gecersiz_geometri")
            continue
        effectivity = _v(props, "data_effectivity")
        effectivity = eff_keys.get(effectivity, effectivity)
        yield AirspaceRecord(
            gml_id=gml_id,
            uuid=uid.upper(),
            geometry=geometry,
            provider=_v(props, "data_provider"),
            originator=_v(props, "data_originator"),
            effectivity=effectivity,
            type=_v(props, "type"),
            designator=_v(props, "designator"),
            name=_v(props, "name"),
            local_type=_v(props, "localType"),
            designator_icao=_v(props, "designatorICAO"),
            control_type=_v(props, "controlType"),
            classification=_v(props, "classification"),
            upper=Limit(_v(props, "upperLimit"), _v(props, "upperLimitUom"),
                        _v(props, "upperLimitReference")),
            lower=Limit(_v(props, "lowerLimit"), _v(props, "lowerLimitUom"),
                        _v(props, "lowerLimitReference")),
            activity=_v(props, "activity"),
            status=_v(props, "status"),
            notes=[(purpose, _v(props, key)) for key, purpose in _NOTE_PROPS
                   if _v(props, key)],
        )
