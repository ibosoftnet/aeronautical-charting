"""AŞAMA 2B — Airspace feature → `airspaces` GeoPackage satırı.

Saf eşlemedir: kaynak bilgisi ya da override kuralı içermez (hepsi 2A'da
bitti). Tam eşleme tablosu: AIXM_to_GeoPackage_Schema_Design.md.

Adlandırma ATS ile aynıdır: tablo önekli sütun (`airspaces_<alan>`), alt
nesne alanı camelCase birleşik, ortak aileler (`annotation*`, `data_*`,
`aixm_*`) öneksiz, tekrarlanan (0..∞) yapılar TAM JSON. AIXM'de karşılığı
olmayan TÜRETİLMİŞ alanlar kendi aile önekini taşır (`airspaceLabeling_*`).
"""

import copy
import json

from data_build_common.aixm_fields import (ANNOTATION_COLUMNS, BASE_COLUMNS, IDENTITY_COLUMNS,
                                           INTEGER_BASE_COLUMNS,
                                           PROVENANCE_COLUMNS, annotations,
                                           base_columns, element_to_dict,
                                           json_list, number, provenance,
                                           text, value_uom)
from data_build_common.aixm_reader import A, G, I, href_of

LIST_SEPARATOR = ","

#: Volume'un tekil dikey alanları (BASE bileşeninden).
_LIMITS = ("upperLimit", "maximumLimit", "lowerLimit", "minimumLimit")

AIRSPACES = (
    ["airspaces_type", "airspaces_designator", "airspaces_localType",
     "airspaces_name", "airspaces_designatorICAO", "airspaces_controlType",
     "airspaces_upperLowerSeparation", "airspaces_upperLowerSeparationUom",
     "airspaces_class",                          # JSON: AirspaceLayerClass[]
     "airspaces_protectedRouteUuid",
     "airspaces_geometryComponent"]              # JSON: tüm bileşenler (geometri hariç)
    + [f"airspaces_{n}{s}" for n in _LIMITS for s in ("", "Uom", "Reference")]
    + ["airspaces_width", "airspaces_widthUom",
       "airspaces_volumeName",
       "airspaces_locationLatitude", "airspaces_locationLongitude",
       "airspaces_contributorAirspaceDependency",
       "airspaces_contributorAirspaceUuid",
       "airspaces_centreline",                   # WKT LineString
       "airspaces_activation",                   # JSON: AirspaceActivation[]
       # ibosoftais:AirspaceExtension
       "airspaces_regionIcao", "airspaces_regionSupProc",
       # türetilmiş (AIXM'de karşılığı yok)
       "airspaceLabeling_classifications"]
    + ANNOTATION_COLUMNS
    + PROVENANCE_COLUMNS
    + IDENTITY_COLUMNS + BASE_COLUMNS
)

LAYERS = {"airspaces": {"columns": AIRSPACES, "geometry": "MULTIPOLYGON"}}

_REAL = {"airspaces_upperLowerSeparation", "airspaces_width",
         "airspaces_locationLatitude", "airspaces_locationLongitude"}


def column_type(name: str) -> str:
    """Sütun tipi.

    Dikey limitler (`upperLimit` vb.) bilinçli olarak TEXT: AIXM değeri sayı
    YA DA `UNL`/`GND`/`FLOOR`/`CEILING` olabilir ve bu kaynaklarda gerçekten
    var (Jeppesen 1.400 UNL, LH 141 GND). REAL sütun bu değerleri NULL'a
    çevirip sessizce kaybederdi; referans sütunu onları ayırt edemez.
    """
    if name in INTEGER_BASE_COLUMNS:
        return "INTEGER"
    if name in _REAL:
        return "REAL"
    return "TEXT"


def _strip_geometry(component):
    """Bileşen kopyası; poligon/çizgi geometrileri çıkarılmış (onlar `geom`
    ve `airspaces_centreline` sütunlarındadır)."""
    clone = copy.deepcopy(component)
    for el in list(clone.iter(A + "horizontalProjection")) + \
            list(clone.iter(A + "centreline")):
        el.getparent().remove(el)
    return clone


def _wkt_linestring(curve_holder):
    pos_list = curve_holder.find(".//" + G + "posList")
    if pos_list is None or not pos_list.text:
        return None
    values = [float(v) for v in pos_list.text.split()]
    pairs = [f"{lon!r} {lat!r}" for lat, lon in zip(values[0::2], values[1::2])]
    return f"LINESTRING ({', '.join(pairs)})" if pairs else None


def _volume_columns(row, volume):
    for name in _LIMITS:
        value, uom = value_uom(volume, name)
        row[f"airspaces_{name}"] = value
        row[f"airspaces_{name}Uom"] = uom
        row[f"airspaces_{name}Reference"] = text(volume, name + "Reference")
    value, uom = value_uom(volume, "width")
    row["airspaces_width"] = number(value)
    row["airspaces_widthUom"] = uom
    row["airspaces_volumeName"] = text(volume, "name")
    pos = volume.find(f"{A}location//{G}pos")
    if pos is not None and pos.text:
        lat, lon = (float(v) for v in pos.text.split()[:2])
        row["airspaces_locationLatitude"], row["airspaces_locationLongitude"] = lat, lon
    dependency = volume.find(f"{A}contributorAirspace/{A}AirspaceVolumeDependency")
    if dependency is not None:
        row["airspaces_contributorAirspaceDependency"] = text(dependency, "dependency")
        row["airspaces_contributorAirspaceUuid"] = href_of(
            dependency.find(A + "theAirspace"))
    centreline = volume.find(A + "centreline")
    if centreline is not None:
        row["airspaces_centreline"] = _wkt_linestring(centreline)


def map_airspace(feature, ts, gml_id, aixm_uuid, prov_entry, base_volume):
    row = {"aixm_gml_id": gml_id, "aixm_uuid": aixm_uuid}
    for name in ("type", "designator", "localType", "name", "designatorICAO",
                 "controlType"):
        row[f"airspaces_{name}"] = text(ts, name)
    value, uom = value_uom(ts, "upperLowerSeparation")
    row["airspaces_upperLowerSeparation"] = number(value)
    row["airspaces_upperLowerSeparationUom"] = uom

    row["airspaces_class"] = json_list(ts, "class")
    classes = [c.findtext(A + "classification") for c in
               ts.findall(f"{A}class/{A}AirspaceLayerClass")]
    classes = [c.strip() for c in classes if c and c.strip()]
    # Türetilmiş: sınıf harflerinin AIXM'deki YAZILIŞ SIRASIYLA listesi.
    row["airspaceLabeling_classifications"] = (
        LIST_SEPARATOR.join(classes) if classes else None)

    row["airspaces_protectedRouteUuid"] = href_of(ts.find(A + "protectedRoute"))

    comps = []
    for holder in ts.findall(A + "geometryComponent"):
        comp = holder.find(A + "AirspaceGeometryComponent")
        if comp is not None:
            value = element_to_dict(_strip_geometry(comp))
            if value is not None:
                comps.append(value)
    row["airspaces_geometryComponent"] = (
        json.dumps(comps, ensure_ascii=False) if comps else None)
    if base_volume is not None:
        _volume_columns(row, base_volume)

    row["airspaces_activation"] = json_list(ts, "activation")

    ext = ts.find(f"{A}extension/{I}AirspaceExtension")
    if ext is not None:
        for name in ("regionIcao", "regionSupProc"):
            el = ext.find(I + name)
            row[f"airspaces_{name}"] = el.text.strip() if el is not None and el.text else None

    annotations(ts, row)
    provenance(row, prov_entry)
    base_columns(row, feature, ts)
    return row
