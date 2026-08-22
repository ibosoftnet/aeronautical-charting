"""RouteSegment yazıcı.

XSD sırası (RouteSegmentPropertyGroup):
  level, upperLimit, upperLimitReference, lowerLimit, lowerLimitReference,
  minimumObstacleClearanceAltitude, pathType, trueTrack, magneticTrack,
  reverseTrueTrack, reverseMagneticTrack, length, widthLeft, widthRight,
  turnDirection, signalGap, minimumEnrouteAltitude, minimumCrossingAtEnd,
  minimumCrossingAtEndReference, maximumCrossingAtEnd,
  maximumCrossingAtEndReference, designatorSuffix, start, routeFormed,
  evaluationArea, curveExtent, end, availability, annotation,
  cardinalDirectionLeft, cardinalDirectionRight, aircraftCapability,
  airspaceClass
"""

import xml.etree.ElementTree as ET

import mapping
from .writer import NS_GML, aixm, gml, opt, q, sub, xlink_ref, SRS_NAME


def write(builder, log, gml_id, feature_uuid, seg, *, overrides=None):
    """seg: normalize edilmiş segment sözlüğü (generate_aixm.py hazırlar)."""
    overrides = overrides or {}
    ts = builder.add_feature("RouteSegment", gml_id, feature_uuid)

    level = seg.get("level")
    if level:
        log.check_enum("RouteSegment", gml_id, "level", level, mapping.CODE_LEVEL)
        sub(ts, aixm("level"), level)

    _limit(ts, log, gml_id, "upper", seg)
    _limit(ts, log, gml_id, "lower", seg)

    path_type = overrides.get("pathType")
    if path_type:
        log.check_enum("RouteSegment", gml_id, "pathType", path_type,
                       mapping.CODE_ROUTE_SEGMENT_PATH)
        sub(ts, aixm("pathType"), path_type)

    opt(ts, aixm("trueTrack"), seg.get("trueTrack"))
    opt(ts, aixm("magneticTrack"), seg.get("magneticTrack"))
    opt(ts, aixm("reverseTrueTrack"), seg.get("reverseTrueTrack"))
    opt(ts, aixm("reverseMagneticTrack"), seg.get("reverseMagneticTrack"))

    opt(ts, aixm("length"), seg.get("length"), uom="NM")
    opt(ts, aixm("widthLeft"), seg.get("widthLeft"), uom="NM")
    opt(ts, aixm("widthRight"), seg.get("widthRight"), uom="NM")

    # MEA: kullanıcı kararı — lowerLimit değeri aynı uom ile MEA'ya da yazılır.
    if seg.get("lowerLimit"):
        mea = ET.SubElement(ts, aixm("minimumEnrouteAltitude"))
        ind = ET.SubElement(mea, aixm("AltitudeIndication"))
        ind.set(q(NS_GML, "id"), gml_id + "_MEA")
        sub(ind, aixm("altitude"), seg["lowerLimit"], uom=seg["lowerLimitUom"])

    _endpoint(ts, log, gml_id, "start", seg)

    if seg.get("routeUuid"):
        xlink_ref(ts, aixm("routeFormed"), seg["routeUuid"])

    _curve(ts, gml_id, seg)

    _endpoint(ts, log, gml_id, "end", seg)

    _aircraft_capability(ts, log, gml_id, seg)


def _limit(ts, log, gml_id, which, seg):
    """upperLimit/lowerLimit + Reference çiftini XSD sırasında yazar."""
    value = seg.get(f"{which}Limit")
    reference = seg.get(f"{which}LimitReference")
    if value:
        sub(ts, aixm(f"{which}Limit"), value, uom=seg[f"{which}LimitUom"])
    if reference:
        log.check_enum("RouteSegment", gml_id, f"{which}LimitReference",
                       reference, mapping.CODE_VERTICAL_REFERENCE)
        sub(ts, aixm(f"{which}LimitReference"), reference)


def _endpoint(ts, log, gml_id, side, seg):
    """start/end → EnRouteSegmentPoint.

    SegmentPointPropertyGroup sırası: reportingATC, flyOver, waypoint,
    radarGuidance, facilityMakeup, <pointChoice_*>, extendedServiceVolume,
    annotation — ardından EnRouteSegmentPointPropertyGroup gelir.
    """
    target_uuid = seg.get(f"{side}PointUuid")
    target_kind = seg.get(f"{side}PointKind")
    reporting = seg.get(f"{side}ReportingATC")

    if not target_uuid and not reporting:
        return

    el = ET.SubElement(ts, aixm(side))
    point = ET.SubElement(el, aixm("EnRouteSegmentPoint"))
    point.set(q(NS_GML, "id"), f"{gml_id}_{side.upper()}")

    if reporting:
        log.check_enum("RouteSegment", gml_id, f"{side}/reportingATC",
                       reporting, mapping.CODE_ATC_REPORTING)
        sub(point, aixm("reportingATC"), reporting)

    if target_uuid:
        tag = ("pointChoice_navaidSystem" if target_kind == "NAVAID"
               else "pointChoice_fixDesignatedPoint")
        xlink_ref(point, aixm(tag), target_uuid)


def _curve(ts, gml_id, seg):
    """curveExtent → aixm:Curve → gml:segments → GeodesicString → posList."""
    start = seg.get("startCoord")
    end = seg.get("endCoord")
    if not start or not end:
        return
    el = ET.SubElement(ts, aixm("curveExtent"))
    curve = ET.SubElement(el, aixm("Curve"))
    curve.set(q(NS_GML, "id"), gml_id + "_C")
    curve.set("srsName", SRS_NAME)
    segments = ET.SubElement(curve, gml("segments"))
    geodesic = ET.SubElement(segments, gml("GeodesicString"))
    geodesic.set("interpolation", "geodesic")
    # posList de gml:pos gibi ENLEM BOYLAM sırasındadır.
    sub(geodesic, gml("posList"),
        f"{start[0]} {start[1]} {end[0]} {end[1]}")


def _aircraft_capability(ts, log, gml_id, seg):
    """NAVIGATION TYPE ve RNP → aircraftCapability/AircraftCharacteristic.

    AIXM 5.2'de RouteSegment üzerinde navigationType ve
    requiredNavigationPerformance alanları YOKTUR; bu bilgiler yalnızca
    AircraftCharacteristic üzerinden taşınabilir.

    AircraftCharacteristicPropertyGroup sırası: … navigationSpecification …
    annotation, category, navigationType, navigationAccuracy …
    (navigationSpecification, navigationType'tan ÖNCE gelir.)
    """
    nav_type = seg.get("navigationType")
    nav_spec = seg.get("navigationSpecification")
    if not nav_type and not nav_spec:
        return

    el = ET.SubElement(ts, aixm("aircraftCapability"))
    char = ET.SubElement(el, aixm("AircraftCharacteristic"))
    char.set(q(NS_GML, "id"), gml_id + "_AC")

    if nav_spec:
        log.check_enum("RouteSegment", gml_id, "navigationSpecification",
                       nav_spec, mapping.CODE_NAVIGATION_SPECIFICATION)
        sub(char, aixm("navigationSpecification"), nav_spec)

    if nav_type:
        log.check_enum("RouteSegment", gml_id, "navigationType", nav_type,
                       mapping.CODE_NAVIGATION_TYPE)
        sub(char, aixm("navigationType"), nav_type)
