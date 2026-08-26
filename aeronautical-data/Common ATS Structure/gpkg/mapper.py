"""AŞAMA 2B — AIXM feature → GeoPackage katman satırı.

Bu modül **saf eşlemedir**: kaynak bilgisi, override kuralı veya geometri
hesabı içermez (hepsi 2A'da bitti). Girdi yalnızca birleşik AIXM dosyası +
provenance yan dosyasıdır.

Tekrarlanan (0..∞) yapılar TEXT sütunda JSON dizisi olarak saklanır — plan
kararı. Yapı, AIXM element adlarını birebir koruyan sade sözlüklerdir; hiçbir
alt alan atılmaz.
"""

import json
from datetime import datetime, timezone

from merge.aixm_reader import A, G, X, local
from gpkg import schema

# Tekrarlanan yapıların JSON'a çevrilirken atlanacak alt elemanları yoktur —
# tüm alt ağaç sözlüğe dönüştürülür (veri kaybı olmaması için).

ADD_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def text(parent, name):
    if parent is None:
        return None
    el = parent.find(A + name)
    return el.text.strip() if el is not None and el.text else None


def value_uom(parent, name):
    """`<aixm:x uom="NM">12</aixm:x>` → (değer, uom)."""
    if parent is None:
        return None, None
    el = parent.find(A + name)
    if el is None:
        return None, None
    return (el.text.strip() if el.text else None), el.get("uom")


def number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def element_to_dict(el):
    """Bir AIXM alt ağacını sade bir sözlüğe çevirir (JSON sütunları için).

    * Metin taşıyan yaprak → `{"value": …, "uom": …}` veya düz metin
    * `xlink:href` taşıyan eleman → `{"href": "<uuid>"}`
    * Tekrarlanan kardeşler listeye toplanır
    Hiçbir alt alan atılmaz; `gml:id` gibi teknik nitelikler dışarıda bırakılır.
    """
    node = {}
    href = el.get(X + "href")
    if href:
        node["href"] = href[len("urn:uuid:"):] if href.startswith("urn:uuid:") else href
    uom = el.get("uom")
    if uom:
        node["uom"] = uom

    children = [c for c in el if isinstance(c.tag, str)]
    if not children:
        txt = (el.text or "").strip()
        if txt and not node:
            return txt
        if txt:
            node["value"] = txt
        return node or None

    for child in children:
        name = local(child.tag)
        if name == "id":
            continue
        value = element_to_dict(child)
        if value is None:
            continue
        if name in node:
            if not isinstance(node[name], list):
                node[name] = [node[name]]
            node[name].append(value)
        else:
            node[name] = value
    return node or None


def json_list(ts, name):
    """0..∞ alanı → JSON dizisi metni (boşsa None)."""
    if ts is None:
        return None
    items = []
    for el in ts.findall(A + name):
        # Sarmalayıcının tek çocuğu asıl nesnedir (örn. availability → Navaid…).
        inner = [c for c in el if isinstance(c.tag, str)]
        value = element_to_dict(inner[0]) if len(inner) == 1 else element_to_dict(el)
        if value is not None:
            items.append(value)
    return json.dumps(items, ensure_ascii=False) if items else None


#: Aynı feature içindeki, aynı purpose'a düşen notların ayırıcısı.
NOTE_SEPARATOR = " | "
#: Farklı feature'lardan (örn. RouteSegment ile Route) gelen notların ayırıcısı:
#: aralarında bir boş satır bırakılır.
FEATURE_SEPARATOR = "\n\n"


def annotations(ts, row):
    """`annotation` → 4 sabit sütun (Description/Remark/Warning/Disclaimer).

    Sütun adları katman önekisiz — annotation yapısı her katmanda aynı 4
    purpose'a indirgendiği için tabloya özgü bir anlamı yoktur (kullanıcı
    kararı, bkz. AIXM_to_GeoPackage_Schema_Design.md §2).

    Aynı feature içindeki aynı purpose'lu notlar `NOTE_SEPARATOR` ile birleşir.
    Fonksiyon aynı satır için birden fazla kez çağrılabilir (RouteSegment + Route,
    ekipman + NavaidComponent gibi): sonraki çağrılar mevcut değerin **üzerine
    yazmaz**, `FEATURE_SEPARATOR` ile ekler. Hiçbir not kaybolmaz.
    """
    if ts is None:
        return
    buckets = {}
    for ann in ts.findall(A + "annotation"):
        note = ann.find(A + "Note")
        if note is None:
            continue
        purpose = (text(note, "purpose") or "REMARK").capitalize()
        texts = [n.text.strip() for n in note.iter(A + "note")
                 if n.text and n.text.strip()]
        if not texts:
            continue
        buckets.setdefault(purpose, []).extend(texts)
    for purpose, values in buckets.items():
        column = f"annotation{purpose}"
        yeni = NOTE_SEPARATOR.join(values)
        mevcut = row.get(column)
        row[column] = f"{mevcut}{FEATURE_SEPARATOR}{yeni}" if mevcut else yeni


def elevated_point(ts, prefix, row):
    """`location` → ElevatedPoint alt alanları + (lat, lon)."""
    location = ts.find(A + "location") if ts is not None else None
    if location is None:
        return None
    inner = location.find(A + "ElevatedPoint")
    if inner is None:
        inner = location.find(A + "Point")
    if inner is None:
        return None

    value, uom = value_uom(inner, "elevation")
    row[f"{prefix}_locationElevation"] = number(value)
    row[f"{prefix}_locationElevationUom"] = uom
    row[f"{prefix}_locationGeoidUndulation"] = number(text(inner, "geoidUndulation"))
    row[f"{prefix}_locationVerticalDatum"] = text(inner, "verticalDatum")
    value, uom = value_uom(inner, "horizontalAccuracy")
    row[f"{prefix}_locationHorizontalAccuracy"] = number(value)
    row[f"{prefix}_locationHorizontalAccuracyUom"] = uom

    pos = inner.find(G + "pos")
    if pos is None or not pos.text:
        return None
    parts = pos.text.split()
    return (float(parts[0]), float(parts[1])) if len(parts) >= 2 else None


def plain_point(ts):
    """`location/Point/gml:pos` → (lat, lon)."""
    pos = ts.find(".//" + G + "pos") if ts is not None else None
    if pos is None or not pos.text:
        return None
    parts = pos.text.split()
    return (float(parts[0]), float(parts[1])) if len(parts) >= 2 else None


def provenance(row, entry):
    """Provenance + `add_date` → 4 sabit sütun, katman önekisiz (kullanıcı
    kararı — bkz. AIXM_to_GeoPackage_Schema_Design.md §2)."""
    row["data_provider"] = (entry or {}).get("data_provider")
    row["data_originator"] = (entry or {}).get("data_originator")
    row["data_effectivity"] = (entry or {}).get("data_effectivity")
    row["add_date"] = ADD_DATE


# ── Katman eşleyicileri ─────────────────────────────────────────────────────

def map_designated_point(feature, ts, gml_id, aixm_uuid, prov_entry):
    row = {"aixm_gml_id": gml_id, "aixm_uuid": aixm_uuid}
    row["designatedPoints_designator"] = text(ts, "designator")
    row["designatedPoints_type"] = text(ts, "type")
    row["designatedPoints_name"] = text(ts, "name")
    row["designatedPoints_codeICAOCountry"] = text(ts, "codeICAOCountry")
    row["designatedPoints_fix"] = json_list(ts, "fix")
    annotations(ts, row)
    provenance(row, prov_entry)
    return row, plain_point(ts)


def map_navaid(feature, ts, gml_id, aixm_uuid, prov_entry):
    row = {"aixm_gml_id": gml_id, "aixm_uuid": aixm_uuid}
    for name in ("type", "designator", "name", "flightChecked", "purpose",
                 "signalPerformance", "courseQuality", "integrityLevel",
                 "codeICAOCountry"):
        row[f"navaids_{name}"] = text(ts, name)
    row["navaids_availability"] = json_list(ts, "availability")
    position = elevated_point(ts, "navaids", row)
    annotations(ts, row)
    provenance(row, prov_entry)
    return row, position


def map_navaid_component(component, equipment_ts, equipment_type,
                         parents, gml_id, aixm_uuid, prov_entry):
    """`NavaidComponent` + bağlı `AbstractNavaidEquipment` → tek satır.

    Alt-türe özgü alanlar `navaidComponents_<AltTür>_<alan>` sütunlarına
    yazılır; hangi alanların yazılacağı `schema.EQUIPMENT_SUBTYPE_FIELDS`'ten
    gelir. Bir satırda YALNIZCA kendi alt-türünün sütunları dolar — bilinmeyen
    bir alt-tür gelirse hiçbir alt-tür sütunu yazılmaz (uydurma eşleme yok).

    `parents`: `[(navaid_row_id, navaid_type), …]` — bir ekipman birden fazla
    Navaid tarafından paylaşılabildiği için LİSTE. Ölçüldü: 275 ekipman 2-7
    navaid'e ait. İki sütun aynı sırada hizalı yazılır.
    """
    # Kimlik, bağlı `AbstractNavaidEquipment` FEATURE'ının kimliğidir.
    # `NavaidComponent` nesnesinin kendi `gml:identifier`'ı yoktur
    # (yalnızca `gml:id` taşır) — AIXM'de Object'tir, Feature değil.
    row = {"aixm_gml_id": gml_id, "aixm_uuid": aixm_uuid,
           "navaidComponents_equipmentType": equipment_type}

    # Ebeveyn bağı — sıralı ve hizalı iki liste.
    row["associatedNavaid"] = schema.LIST_SEPARATOR.join(
        str(row_id) for row_id, _ in parents) if parents else None
    row["associatedNavaidType"] = schema.LIST_SEPARATOR.join(
        (navaid_type or "") for _, navaid_type in parents) if parents else None

    # NavaidComponent'in kendi alanları
    for name in schema.NAVAID_COMPONENT_OWN_FIELDS:
        row[f"navaidComponents_{name}"] = text(component, name)

    # Ortak taban (11 alt-türde de aynı) — önek almaz.
    for name in ("designator", "name", "emissionClass", "mobile",
                 "dateMagneticVariation", "flightChecked"):
        row[f"navaidComponents_{name}"] = text(equipment_ts, name)
    row["navaidComponents_magneticVariation"] = number(
        text(equipment_ts, "magneticVariation"))
    row["navaidComponents_monitoring"] = json_list(equipment_ts, "monitoring")
    row["navaidComponents_availability"] = json_list(equipment_ts, "availability")
    position = elevated_point(equipment_ts, "navaidComponents", row)

    # Alt-türe özgü — yalnızca bu alt-türün sütunları.
    for field in schema.EQUIPMENT_SUBTYPE_FIELDS.get(equipment_type, ()):
        column = schema.equipment_column(equipment_type, field)
        if field in schema.EQUIPMENT_VALUE_UOM:
            value, uom = value_uom(equipment_ts, field)
            row[column] = number(value)
            row[column + "Uom"] = uom
        else:
            value = text(equipment_ts, field)
            row[column] = (number(value) if field in schema.EQUIPMENT_NUMERIC
                           else value)

    # Hem bileşenin hem ekipmanın notları aynı 4 sütunda birleşir.
    annotations(equipment_ts, row)
    annotations(component, row)
    provenance(row, prov_entry)
    return row, position


_SEGMENT_SIMPLE = ("level", "pathType", "turnDirection", "signalGap",
                   "designatorSuffix", "cardinalDirectionLeft",
                   "cardinalDirectionRight")
_SEGMENT_NUMERIC = ("trueTrack", "magneticTrack", "reverseTrueTrack",
                    "reverseMagneticTrack")
_SEGMENT_VALUE_UOM = ("length", "widthLeft", "widthRight",
                      "minimumObstacleClearanceAltitude")
_SEGMENT_LIMITS = ("upperLimit", "lowerLimit",
                   "minimumCrossingAtEnd", "maximumCrossingAtEnd")
_ROUTE_FIELDS = ("designatorPrefix", "designatorSecondLetter",
                 "designatorNumber", "multipleIdentifier", "locationDesignator",
                 "name", "type", "flightRule", "internationalUse",
                 "militaryUse", "militaryTrainingType")


def map_route_segment(feature, ts, gml_id, aixm_uuid, prov_entry, route_ts,
                      resolve):
    """RouteSegment → satır. `resolve(uuid)` → (layer, row_id, designator).

    Kimlik sütunları RouteSegment feature'ınındır; `route_*` sütunlarını
    besleyen Route feature'ının kendi kimliği ayrıca taşınmaz.
    """
    row = {"aixm_gml_id": gml_id, "aixm_uuid": aixm_uuid}

    for name in _SEGMENT_SIMPLE:
        row[f"routeSegments_{name}"] = text(ts, name)
    for name in _SEGMENT_NUMERIC:
        row[f"routeSegments_{name}"] = number(text(ts, name))
    for name in _SEGMENT_VALUE_UOM:
        value, uom = value_uom(ts, name)
        row[f"routeSegments_{name}"] = number(value)
        row[f"routeSegments_{name}Uom"] = uom
    for name in _SEGMENT_LIMITS:
        value, uom = value_uom(ts, name)
        # `UNL`/`GND` gibi özel değerler sayıya çevrilemez; metin olarak kalır.
        row[f"routeSegments_{name}"] = number(value)
        row[f"routeSegments_{name}Uom"] = uom
        row[f"routeSegments_{name}Reference"] = text(ts, name + "Reference")

    row["routeSegments_minimumEnrouteAltitude"] = json_list(
        ts, "minimumEnrouteAltitude")
    row["routeSegments_availability"] = json_list(ts, "availability")
    # `aircraftCapability` AIXM'de HEM Route'ta HEM RouteSegment'te tanımlıdır
    # (RoutePropertyGroup ve RouteSegmentPropertyGroup'un ikisinde de 0..∞).
    # Segmentin kendi değeri varsa o geçerlidir; yoksa bağlı Route'unki alınır
    # (kullanıcı kararı). Önceden yalnızca segmente bakılıyordu ve Route
    # düzeyinde tanımlı kayıtlar sessizce düşüyordu.
    row["routeSegments_aircraftCapability"] = (
        json_list(ts, "aircraftCapability")
        or json_list(route_ts, "aircraftCapability"))
    row["routeSegments_airspaceClass"] = json_list(ts, "airspaceClass")

    designs = [text(el, "name") for el in ts.findall(A + "designCriteria")]
    designs = [d for d in designs if d]
    if not designs and route_ts is not None:
        designs = [text(el.find(A + "DesignStandard") if el.find(A + "DesignStandard")
                        is not None else el, "name")
                   for el in route_ts.findall(A + "designCriteria")]
        designs = [d for d in designs if d]
    row["routeSegments_designCriteria"] = ",".join(designs) if designs else None

    # Uç noktalar
    for side in ("start", "end"):
        holder = ts.find(A + side)
        prefix = f"routeSegments_{side}"
        if holder is None:
            continue
        point = holder.find(A + "EnRouteSegmentPoint")
        if point is None:
            continue
        for name, column in (("reportingATC", "ReportingATC"),
                             ("flyOver", "FlyOver"), ("waypoint", "Waypoint"),
                             ("radarGuidance", "RadarGuidance"),
                             ("roleFreeFlight", "RoleFreeFlight"),
                             ("roleRVSM", "RoleRVSM"),
                             ("roleMilitaryTraining", "RoleMilitaryTraining")):
            row[f"{prefix}{column}"] = text(point, name)
        value, uom = value_uom(point, "turnRadius")
        row[f"{prefix}TurnRadius"] = number(value)
        row[f"{prefix}TurnRadiusUom"] = uom
        row[f"{prefix}FacilityMakeup"] = json_list(point, "facilityMakeup")

        for child in point:
            if local(child.tag).startswith("pointChoice_"):
                href = child.get(X + "href")
                if href and href.startswith("urn:uuid:"):
                    hit = resolve(href[len("urn:uuid:"):].upper())
                    if hit:
                        layer, row_id, designator = hit
                        row[f"{prefix}PointLayer"] = layer
                        row[f"{prefix}PointId"] = row_id
                        row[f"{prefix}PointDesignator"] = designator
                break

    # Route'tan devralınan alanlar. `route_` öneki bilinçli olarak
    # `routeSegments_`'ten FARKLIDIR: bu alanlar RouteSegment'in kendi
    # zaman-dilimine değil, bağlı `Route` feature'ına aittir; aynı önek
    # kullanmak iki farklı kaynağı ayırt edilemez hale getirirdi (kullanıcı
    # düzeltmesi).
    for name in _ROUTE_FIELDS:
        row[f"route_{name}"] = text(route_ts, name)

    # Önce segmentin kendi notları, sonra bağlı Route'un notları — ikisi de aynı
    # 4 purpose sütununda, aralarında bir boş satırla birleşir. Route'un
    # annotation'ı AIXM'de segmentinkinden bağımsız bir alandır.
    annotations(ts, row)
    annotations(route_ts, row)
    provenance(row, prov_entry)

    positions = None
    pl = ts.find(".//" + G + "posList")
    if pl is not None and pl.text:
        nums = [float(x) for x in pl.text.split()]
        if len(nums) >= 4 and len(nums) % 2 == 0:
            positions = list(zip(nums[0::2], nums[1::2]))
    return row, positions
