"""AIXM 5.2 feature yazıcıları (EAD-SDO).

Her yazıcı alanları XSD `<sequence>` sırasında yazar; sıra dışı yazım şema
doğrulamasını kırar. Sıralar `AIXM_Features.xsd`ten teyit edilmiştir.
"""

import xml.etree.ElementTree as ET

import mapping
from aixm_writer import (
    NS_GML, aixm, gml, note, opt, point, q, sub, xlink_ref, SRS_NAME,
)

# ── Ortak yardımcılar ───────────────────────────────────────────────────────

def _residue_note(rec) -> str:
    """AIXM karşılığı olmayan teknik alanları tek bir nota toplar.

    Kullanıcı kararı: yatay datum (AIXM'de yalnızca `verticalDatum` var),
    irtifa doğruluğu (ElevatedPoint'te yalnızca `horizontalAccuracy` var) ve
    işletmeye alınma tarihi annotation'a yazılır; `valCrc` düşürülür.
    """
    parts = []
    if rec.get("datum"):
        parts.append(f"Horizontal datum: {rec['datum']}")
    if rec.get("elev_accuracy"):
        parts.append(f"Elevation accuracy: {rec['elev_accuracy']}")
    if rec.get("dt_com"):
        parts.append(f"Commissioning date: {rec['dt_com']}")
    if rec.get("work_hr"):
        parts.append(f"Working hours: {rec['work_hr']}")
    return "; ".join(parts)


def _remark_text(rec) -> str:
    parts = [rec.get("rmk"), rec.get("work_hr_rmk")]
    return " | ".join(p for p in parts if p)


def _availability(ts, gml_id, rec):
    """codeWorkHr=H24 için tam AIXM Timesheet yapısı (kullanıcı kararı).

    NavaidOperationalStatusType sırası: PropertiesWithSchedulePropertyGroup
    (timeInterval, annotation, specialDateAuthority) → operationalStatus,
    signalType. Kaynak yalnızca "ne zaman çalıştığını" söylüyor, "çalışıyor
    mu"yu söylemiyor; bu yüzden operationalStatus YAZILMAZ (uydurulmaz).

    TIMSH/HO gibi çizelgesi kaynakta bulunmayan değerler yalnızca annotation'a
    yazılır — Timesheet üretmek için yeterli bilgi yok.
    """
    if (rec.get("work_hr") or "").strip().upper() != "H24":
        return
    av = ET.SubElement(ts, aixm("availability"))
    status = ET.SubElement(av, aixm("NavaidOperationalStatus"))
    status.set(q(NS_GML, "id"), gml_id + "_AV")
    interval = ET.SubElement(status, aixm("timeInterval"))
    sheet = ET.SubElement(interval, aixm("Timesheet"))
    sheet.set(q(NS_GML, "id"), gml_id + "_TSH")
    sub(sheet, aixm("timeReference"), "UTC")
    sub(sheet, aixm("day"), "ANY")
    sub(sheet, aixm("startTime"), "00:00")
    sub(sheet, aixm("endTime"), "24:00")


def _annotations(ts, gml_id, rec, extra=None):
    """REMARK (kaynak notları) + DESCRIPTION (teknik artık alanlar)."""
    remark = _remark_text(rec)
    if remark:
        note(ts, gml_id + "_RMK", remark, purpose="REMARK")
    residue = _residue_note(rec)
    if extra:
        residue = f"{residue}; {extra}" if residue else extra
    if residue:
        note(ts, gml_id + "_DSC", residue, purpose="DESCRIPTION")


def _elevated_location(ts, gml_id, rec):
    """Navaid/NavaidEquipment.location → ElevatedPoint.

    ElevatedPointPropertyGroup sırası: elevation, geoidUndulation,
    verticalDatum, horizontalAccuracy, annotation.
    """
    el = point(ts, aixm("location"), gml_id + "_EP",
               rec["lat_dd"], rec["lon_dd"], elevated=True)
    uom = (rec.get("uom_dist_ver") or "").strip().upper()
    if rec.get("elev") and uom in mapping.UOM_DISTANCE_VERTICAL:
        sub(el, aixm("elevation"), mapping.number(rec["elev"]), uom=uom)
    opt(el, aixm("geoidUndulation"), mapping.number(rec.get("geoid_undulation")))
    opt(el, aixm("verticalDatum"), rec.get("vert_datum"))
    if rec.get("geo_accuracy") and rec.get("uom_geo_accuracy"):
        sub(el, aixm("horizontalAccuracy"), mapping.number(rec["geo_accuracy"]),
            uom=rec["uom_geo_accuracy"].strip().upper())
    return el


def _equipment_base(ts, gml_id, log, feature, rec):
    """NavaidEquipmentPropertyGroup — tüm ekipman alt-türlerinde ortak.

    Sıra: designator, name, emissionClass, mobile, magneticVariation,
    dateMagneticVariation, flightChecked, location, authority, monitoring,
    availability, annotation
    """
    opt(ts, aixm("designator"), rec.get("code_id"))
    opt(ts, aixm("name"), rec.get("name"))

    emission = (rec.get("emission") or "").strip().upper()
    if emission:
        if emission not in mapping.CODE_RADIO_EMISSION:
            log.error(feature, gml_id, "emissionClass", emission, "enum_disi_deger")
        else:
            sub(ts, aixm("emissionClass"), emission)

    opt(ts, aixm("magneticVariation"), mapping.number(rec.get("mag_var")))
    opt(ts, aixm("dateMagneticVariation"), mapping.year_only(rec.get("mag_var_date")))

    _elevated_location(ts, gml_id, rec)
    _availability(ts, gml_id, rec)
    _annotations(ts, gml_id, rec)


# ── NavaidEquipment somut alt-türleri ───────────────────────────────────────

def write_vor_equipment(builder, log, gml_id, uuid_value, rec, valid_time):
    """<aixm:VOR> — common base + type, frequency, zeroBearingDirection,
    declination."""
    ts = builder.add_feature("VOR", gml_id, uuid_value, valid_time)
    _equipment_base(ts, gml_id, log, "VOR", rec)

    vor_type = (rec.get("code_type") or "").strip().upper()
    if vor_type:
        if vor_type in mapping.CODE_VOR or vor_type.startswith("OTHER"):
            sub(ts, aixm("type"), vor_type)
        else:
            log.error("VOR", gml_id, "type", vor_type, "enum_disi_deger")

    if rec.get("freq"):
        sub(ts, aixm("frequency"), mapping.number(rec["freq"]),
            uom=(rec.get("uom_freq") or "MHZ").strip().upper())

    north = (rec.get("north_ref") or "").strip().upper()
    if north:
        if north in mapping.CODE_NORTH_REFERENCE or north.startswith("OTHER"):
            sub(ts, aixm("zeroBearingDirection"), north)
        else:
            log.error("VOR", gml_id, "zeroBearingDirection", north, "enum_disi_deger")

    opt(ts, aixm("declination"), mapping.number(rec.get("declination")))


def write_dme_equipment(builder, log, gml_id, uuid_value, rec, valid_time,
                        tuning_vhf=None):
    """<aixm:DME> — common base + type, channel, displace, tuningFrequencyVHF."""
    ts = builder.add_feature("DME", gml_id, uuid_value, valid_time)
    _equipment_base(ts, gml_id, log, "DME", rec)

    opt(ts, aixm("channel"), rec.get("channel"))
    if tuning_vhf:
        sub(ts, aixm("tuningFrequencyVHF"), tuning_vhf, uom="MHZ")


def write_tacan_equipment(builder, log, gml_id, uuid_value, rec, valid_time,
                          tuning_vhf=None):
    """<aixm:TACAN> — common base + channel, declination, tuningFrequencyVHF."""
    ts = builder.add_feature("TACAN", gml_id, uuid_value, valid_time)
    _equipment_base(ts, gml_id, log, "TACAN", rec)

    opt(ts, aixm("channel"), rec.get("channel"))
    if tuning_vhf:
        sub(ts, aixm("tuningFrequencyVHF"), tuning_vhf, uom="MHZ")


def write_localizer_equipment(builder, log, gml_id, uuid_value, rec, valid_time):
    """<aixm:Localizer> — common base + frequency, magneticBearing, trueBearing,
    declination, widthCourse, backCourseUsable, signalPerformance,
    courseQuality, integrityLevel."""
    ts = builder.add_feature("Localizer", gml_id, uuid_value, valid_time)
    _equipment_base(ts, gml_id, log, "Localizer", rec)

    if rec.get("freq"):
        sub(ts, aixm("frequency"), mapping.number(rec["freq"]),
            uom=(rec.get("uom_freq") or "MHZ").strip().upper())
    opt(ts, aixm("magneticBearing"), mapping.number(rec.get("mag_brg")))
    opt(ts, aixm("trueBearing"), mapping.number(rec.get("true_brg")))
    opt(ts, aixm("widthCourse"), mapping.number(rec.get("course_width")))

    back = (rec.get("back_course") or "").strip().upper()
    if back:
        mapped = mapping.BACK_COURSE.get(back)
        if mapped:
            sub(ts, aixm("backCourseUsable"), mapped)
        else:
            log.error("Localizer", gml_id, "backCourseUsable", back,
                      "bilinmeyen_back_course_kodu")


def write_glidepath_equipment(builder, log, gml_id, uuid_value, rec, valid_time):
    """<aixm:Glidepath> — common base + frequency, slope, rdh, …"""
    ts = builder.add_feature("Glidepath", gml_id, uuid_value, valid_time)
    _equipment_base(ts, gml_id, log, "Glidepath", rec)

    if rec.get("freq"):
        sub(ts, aixm("frequency"), mapping.number(rec["freq"]),
            uom=(rec.get("uom_freq") or "MHZ").strip().upper())
    opt(ts, aixm("slope"), mapping.number(rec.get("slope")))
    uom_rdh = (rec.get("uom_rdh") or "").strip().upper()
    if rec.get("rdh") and uom_rdh in mapping.UOM_DISTANCE_VERTICAL:
        sub(ts, aixm("rdh"), mapping.number(rec["rdh"]), uom=uom_rdh)


# ── Navaid (bileşik servis) ─────────────────────────────────────────────────

def write_navaid(builder, log, gml_id, uuid_value, primary, aixm_type,
                 components, valid_time):
    """<aixm:Navaid>.

    XSD sırası: type, designator, name, flightChecked, purpose,
    signalPerformance, courseQuality, integrityLevel, touchDownLiftOff,
    navaidEquipment, location, runwayDirection, servedAirport, availability,
    annotation, codeICAOCountry

    components: [(equipment_uuid, is_primary), …]
    """
    ts = builder.add_feature("Navaid", gml_id, uuid_value, valid_time)

    if aixm_type not in mapping.CODE_NAVAID_SERVICE:
        log.error("Navaid", gml_id, "type", aixm_type, "enum_disi_deger")
    sub(ts, aixm("type"), aixm_type)
    opt(ts, aixm("designator"), primary.get("code_id"))
    opt(ts, aixm("name"), primary.get("name"))

    # navaidEquipment, location'dan ÖNCE gelir (XSD sırası).
    for n, (equipment_uuid, is_primary) in enumerate(components, 1):
        eq = ET.SubElement(ts, aixm("navaidEquipment"))
        comp = ET.SubElement(eq, aixm("NavaidComponent"))
        comp.set(q(NS_GML, "id"), f"{gml_id}_NC{n}")
        if is_primary:
            # Navaid significant point olarak kullanıldığında navigasyona esas
            # konumu bu bileşen belirler.
            sub(comp, aixm("providesNavigableLocation"), "YES")
        xlink_ref(comp, aixm("theNavaidEquipment"), equipment_uuid)

    point(ts, aixm("location"), gml_id + "_EP",
          primary["lat_dd"], primary["lon_dd"], elevated=True)


# ── DesignatedPoint ────────────────────────────────────────────────────────

def write_designated_point(builder, log, gml_id, uuid_value, rec, valid_time):
    """<aixm:DesignatedPoint>.

    XSD sırası: designator, type, name, location, aimingPoint,
    airportHeliport, runwayPoint, annotation, codeICAOCountry, fix
    """
    ts = builder.add_feature("DesignatedPoint", gml_id, uuid_value, valid_time)

    opt(ts, aixm("designator"), rec["code_id"])

    raw_type = (rec.get("code_type") or "").strip().upper()
    if raw_type:
        mapped = mapping.DP_TYPE.get(raw_type)
        if mapped is None:
            log.error("DesignatedPoint", gml_id, "type", raw_type,
                      "bilinmeyen_dp_code_type")
        else:
            sub(ts, aixm("type"), mapped)

    opt(ts, aixm("name"), rec.get("name"))
    # DesignatedPoint.location = Point (Navaid'deki gibi ElevatedPoint değil).
    point(ts, aixm("location"), gml_id + "_P", rec["lat_dd"], rec["lon_dd"])

    if rec.get("datum"):
        note(ts, gml_id + "_DSC", f"Horizontal datum: {rec['datum']}",
             purpose="DESCRIPTION")


# ── Route ve RouteSegment ──────────────────────────────────────────────────

def write_route(builder, log, gml_id, uuid_value, designator, loc_designator,
                valid_time):
    """<aixm:Route>.

    XSD sırası: designatorPrefix, designatorSecondLetter, designatorNumber,
    multipleIdentifier, locationDesignator, name, type, flightRule, …

    Kullanıcı kararı: AIXM designator desenine uymayan kodlar (AR10, LPC19,
    VFR5 gibi ~%2.4) designator alanlarına yazılamaz; ham kod `name` alanına
    yazılır ve loglanır — kayıt düşürülmez.
    """
    ts = builder.add_feature("Route", gml_id, uuid_value, valid_time)

    parts = mapping.decompose_route_designator(designator)
    if parts:
        prefix, letter, number, multiple = parts
        opt(ts, aixm("designatorPrefix"), prefix)
        sub(ts, aixm("designatorSecondLetter"), letter)
        sub(ts, aixm("designatorNumber"), number)
        opt(ts, aixm("multipleIdentifier"), multiple)

    opt(ts, aixm("locationDesignator"), loc_designator)

    if not parts:
        log.warning("Route", gml_id, "designator", designator,
                    "desene_uymayan_kod_name_alanina_yazildi")
        opt(ts, aixm("name"), designator)

    # EAD-SDO'nun rota raporları (routes-upper-*/routes-non-upper-*) tanımı
    # gereği ATS rotalarıdır (ICAO Annex 11) — ham veride ayrı bir sınıflama
    # alanı yok (Record'da yalnızca mid/Rte/SpnSta/SpnEnd/dtWef/OrgCre/
    # valDistVer*/uomDistVer*/codeDistVer* var), bu yüzden sabit değer
    # kullanıcı kararıyla yazılır. AIXM CodeRouteType enum'unda `ATS`
    # "ATS Route as described in ICAO Annex 11" olarak tanımlı.
    sub(ts, aixm("type"), "ATS")


def write_route_segment(builder, log, gml_id, uuid_value, seg, valid_time):
    """<aixm:RouteSegment>.

    XSD sırası: level, upperLimit, upperLimitReference, lowerLimit,
    lowerLimitReference, minimumObstacleClearanceAltitude, pathType, trueTrack,
    magneticTrack, reverseTrueTrack, reverseMagneticTrack, length, widthLeft,
    widthRight, turnDirection, signalGap, minimumEnrouteAltitude,
    minimumCrossingAtEnd(+Reference), maximumCrossingAtEnd(+Reference),
    designatorSuffix, start, routeFormed, evaluationArea, curveExtent, end, …
    """
    ts = builder.add_feature("RouteSegment", gml_id, uuid_value, valid_time)

    opt(ts, aixm("level"), seg.get("level"))
    _limit(ts, log, gml_id, "upper", seg)
    _limit(ts, log, gml_id, "lower", seg)

    _endpoint(ts, gml_id, "start", seg)

    if seg.get("route_uuid"):
        xlink_ref(ts, aixm("routeFormed"), seg["route_uuid"])

    _curve(ts, gml_id, seg)

    _endpoint(ts, gml_id, "end", seg)


def _limit(ts, log, gml_id, which, seg):
    value = seg.get(f"{which}_limit")
    uom = (seg.get(f"{which}_uom") or "").strip().upper()
    raw_ref = (seg.get(f"{which}_ref") or "").strip().upper()

    if value and uom in mapping.UOM_DISTANCE_VERTICAL:
        sub(ts, aixm(f"{which}Limit"), mapping.number(value), uom=uom)
    elif value:
        log.error("RouteSegment", gml_id, f"{which}Limit uom", uom,
                  "bilinmeyen_dikey_birim")

    if raw_ref:
        mapped = mapping.VERTICAL_REFERENCE.get(raw_ref)
        if mapped is None:
            log.error("RouteSegment", gml_id, f"{which}LimitReference", raw_ref,
                      "bilinmeyen_dikey_referans")
        else:
            sub(ts, aixm(f"{which}LimitReference"), mapped)


def _endpoint(ts, gml_id, side, seg):
    """start/end → EnRouteSegmentPoint → pointChoice_*.

    SegmentPointPropertyGroup sırası: reportingATC, flyOver, waypoint,
    radarGuidance, facilityMakeup, <pointChoice_*>, … — EAD kaynağında bu
    alanlardan yalnızca nokta referansı bulunuyor.
    """
    target = seg.get(f"{side}_uuid")
    if not target:
        return
    el = ET.SubElement(ts, aixm(side))
    pt = ET.SubElement(el, aixm("EnRouteSegmentPoint"))
    pt.set(q(NS_GML, "id"), f"{gml_id}_{side.upper()}")
    tag = ("pointChoice_navaidSystem" if seg.get(f"{side}_kind") == "NAVAID"
           else "pointChoice_fixDesignatedPoint")
    xlink_ref(pt, aixm(tag), target)


def _curve(ts, gml_id, seg):
    """curveExtent → aixm:Curve → gml:segments → GeodesicString → posList.

    Kaynak XML'de geometri yok; iki ucu da çözülen segmentlerde uç nokta
    koordinatlarından 2 noktalı geodesic üretilir.
    """
    start, end = seg.get("start_coord"), seg.get("end_coord")
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
