"""AŞAMA 2B — AIXM feature → GeoPackage katman satırı.

Bu modül **saf eşlemedir**: kaynak bilgisi, override kuralı veya geometri
hesabı içermez (hepsi 2A'da bitti). Girdi yalnızca birleşik AIXM dosyasıdır;
provenance her feature'ın kendi extension kutusundan okunur.

Tekrarlanan (0..∞) yapılar TEXT sütunda JSON dizisi olarak saklanır — plan
kararı. Yapı, AIXM element adlarını birebir koruyan sade sözlüklerdir; hiçbir
alt alan atılmaz.
"""

import json

from data_build_common.aixm_fields import (  # noqa: F401
    FEATURE_SEPARATOR, NOTE_SEPARATOR, annotations, base_columns,
    element_to_dict, json_list, number, provenance, text, value_uom)
from merge.aixm_reader import A, G, X, local
from gpkg import schema

# Ortak sütun aileleri (`annotation*`, `data_*`, `aixm_*`) ve tekrarlanan
# yapıların JSON dönüşümü `data_build_common.aixm_fields`'tadır (tüm alt ağaç
# sözlüğe dönüştürülür, veri kaybı olmaz). NOTE_SEPARATOR / FEATURE_SEPARATOR
# oradan yeniden dışa verilir.


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
    base_columns(row, feature, ts)
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
    base_columns(row, feature, ts)
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
    # Kimlik ve taban alanlar ekipman FEATURE'ınındır (NavaidComponent bir
    # Object'tir, TimeSlice'ı yoktur).
    base_columns(row, equipment_ts.getparent().getparent(), equipment_ts)
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
                        # `resolved` 5 alan taşır (ad/tip `changeOverPoints`
                        # için eklendi); segment ilk üçünü kullanır.
                        layer, row_id, designator = hit[:3]
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
    base_columns(row, feature, ts)

    positions = None
    pl = ts.find(".//" + G + "posList")
    if pl is not None and pl.text:
        nums = [float(x) for x in pl.text.split()]
        if len(nums) >= 4 and len(nums) % 2 == 0:
            positions = list(zip(nums[0::2], nums[1::2]))
    return row, positions


# ── changeOverPoints ────────────────────────────────────────────────────────

#: `route_*` sütunlarını besleyen Route alanları: rota kimliği + `name`
#: (kullanıcı kararı). `routeSegments`'in devraldığı `type`/`flightRule`/
#: `locationDesignator` gibi alanlar COP'a taşınmaz. Adlandırma
#: `routeSegments`'teki `route_*` ailesiyle aynıdır; ilişkinin kendisi ayrı
#: durur (`associatedRoute_uuid`).
#:
#: `designatorSuffix` BU LİSTEDE YOKTUR ve COP'a hiç taşınmaz. Sebep yapısaldır,
#: veriyle ilgili değil: AIXM'de `designatorSuffix` `Route`'un değil
#: **`RouteSegment`'in** özniteliğidir. COP ise tek bir segmente değil bir
#: `RoutePortion`'a — yani bir segment ARALIĞINA — bağlıdır ve aralıktaki
#: segmentler birbirinden farklı suffix değerleri taşıyabilir. Tek bir sütuna
#: indirgemek bu farkı gizler, hangi segmentin hangi suffix'i taşıdığı
#: kaybolurdu; bu yüzden bilerek atlandı (kullanıcı kararı).
_COP_ROUTE_FIELDS = ("designatorPrefix", "designatorSecondLetter",
                     "designatorNumber", "multipleIdentifier", "name")


def _reference(row, prefix, holder, resolve, with_details):
    """`RoutePortion`'daki bir choice referansını sütunlara çözer.

    `holder`: içinde `xlink:href` taşıyan eleman (`start_navaidSystem` gibi).
    `with_details`: ad/tip sütunları da doldurulsun mu (uç noktalarda evet).

    Hedef bulunamazsa sütunlar boş kalır — uydurma yapılmaz.
    """
    if holder is None:
        return
    href = holder.get(X + "href")
    if not href or not href.startswith("urn:uuid:"):
        return
    uuid_value = href[len("urn:uuid:"):].strip().upper()
    # Uuid HER ZAMAN yazılır: hedef bu GeoPackage'da bir satıra çözülemese
    # bile (örneğin pist noktası gibi katmanı olmayan bir tip) referansın
    # kendisi kaybolmamalı.
    row[f"{prefix}Uuid"] = uuid_value

    hit = resolve(uuid_value)
    if not hit:
        return
    layer, row_id, designator, name, type_ = hit
    row[f"{prefix}Layer"] = layer
    row[f"{prefix}Id"] = row_id
    row[f"{prefix}Designator"] = designator
    if with_details:
        row[f"{prefix}Name"] = name
        row[f"{prefix}Type"] = type_


def map_change_over_point(feature, ts, gml_id, aixm_uuid, prov_entry, route_ts,
                          resolve, portion):
    """ChangeOverPoint → satır + geometri koordinatları.

    `resolve(uuid)` → `(layer, row_id, designator, name, type)`
    `portion`       : `gpkg.route_portion.Portion` ya da None

    Geometri COP'un kendi konumu DEĞİL, geçerli olduğu rota aralığının
    çizgisidir (bkz. modül `gpkg/route_portion.py`). `portion` None ise satır
    yine yazılır, geometri boş kalır — çağıran taraf loglar.
    """
    row = {"aixm_gml_id": gml_id, "aixm_uuid": aixm_uuid}

    value, uom = value_uom(ts, "distance")
    row["changeOverPoints_distance"] = number(value)
    row["changeOverPoints_distanceUom"] = uom

    # İkinci mesafe çekirdek AIXM'de yoktur; bu projenin extension'ından gelir
    # (bkz. common/schemas/ibosoftais-extension.xsd).
    for ext in ts.findall(A + "extension"):
        for child in ext.iter():
            if local(child.tag) == "distanceFromEnd":
                row["changeOverPoints_distanceFromEnd"] = number(
                    child.text.strip() if child.text else None)
                row["changeOverPoints_distanceFromEndUom"] = child.get("uom")
                break

    # COP'un KENDİ konumu (opsiyonel, bu kaynakta hiç yok). İki yüzü ayrı
    # taşınır: ham koordinat ve çözülmüş referans. Koordinat referanstan
    # TÜRETİLMEZ — yalnızca AIXM'de gerçekten yazılmışsa dolar.
    for child in ts:
        name = local(child.tag)
        if not name.startswith("location_"):
            continue
        if name == "location_position":
            pos = child.find(".//" + G + "pos")
            if pos is not None and pos.text:
                parts = pos.text.split()
                if len(parts) >= 2:
                    row["changeOverPoints_locationLatitude"] = number(parts[0])
                    row["changeOverPoints_locationLongitude"] = number(parts[1])
        else:
            _reference(row, "changeOverPoints_location", child, resolve, False)
        break

    portion_el = ts.find(A + "applicableRoutePortion")
    portion_el = (portion_el.find(A + "RoutePortion")
                  if portion_el is not None else None)
    if portion_el is not None:
        for child in portion_el:
            name = local(child.tag)
            if name.startswith("start_"):
                _reference(row, "changeOverPoints_startPoint", child,
                           resolve, True)
            elif name.startswith("end_"):
                _reference(row, "changeOverPoints_endPoint", child,
                           resolve, True)
            elif name.startswith("intermediatePoint_"):
                _reference(row, "changeOverPoints_intermediatePoint", child,
                           resolve, False)
            elif name == "referencedRoute":
                href = child.get(X + "href")
                if href and href.startswith("urn:uuid:"):
                    row["associatedRoute_uuid"] = \
                        href[len("urn:uuid:"):].strip().upper()

    for name in _COP_ROUTE_FIELDS:
        row[f"route_{name}"] = text(route_ts, name)

    if portion is not None:
        row["associatedRouteSegment_id"] = schema.LIST_SEPARATOR.join(
            str(i) for i in portion.row_ids)
        row["associatedRouteSegment_uuid"] = schema.LIST_SEPARATOR.join(
            portion.uuids)
        # QGIS sembolü ÇİZGİ BOYUNCA yüzdeyle kaydırır; payda bu yüzden
        # çizginin kendi uzunluğudur, yayımlanan mesafelerin toplamı değil.
        distance = row["changeOverPoints_distance"]
        if distance is not None and portion.length_nm > 0:
            row["copSymbology_offsetPercent"] = round(
                float(distance) / portion.length_nm * 100.0, 6)

    # COP'un kendi notları, ardından bağlı Route'un notları (routeSegments ile
    # aynı desen — ikisi de aynı 4 purpose sütununda birleşir).
    annotations(ts, row)
    annotations(route_ts, row)
    provenance(row, prov_entry)
    base_columns(row, feature, ts)

    return row, (portion.coords if portion is not None else None)
