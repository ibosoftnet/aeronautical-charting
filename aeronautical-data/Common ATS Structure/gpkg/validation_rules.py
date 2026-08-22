"""AŞAMA 2B — katman/alan doğrulama kuralları.

Kurallar `docs/*.md` öznitelik sözlüklerinden bire bir aktarılmıştır (o
dokümanlar AIXM 5.2 XSD'ye karşı doğrulanarak hazırlanmıştı).

AIXM'de her `Code*Type` bir union'dır: sabit enum listesi **veya**
`OTHER(:(\\w|_){1,58})?` deseni — bu yüzden `allow_other` varsayılan olarak
açıktır.
"""

import re
from dataclasses import dataclass, field

OTHER_RE = re.compile(r"^OTHER(:(\w|_){1,58})?$")


@dataclass(frozen=True)
class FieldRule:
    kind: str = "text"                 # text | enum | number
    max_length: int | None = None
    enum: frozenset = field(default_factory=frozenset)
    allow_other: bool = True
    minimum: float | None = None
    maximum: float | None = None


def enum_rule(*values, allow_other=True):
    return FieldRule(kind="enum", enum=frozenset(values), allow_other=allow_other)


def number_rule(minimum=None, maximum=None):
    return FieldRule(kind="number", minimum=minimum, maximum=maximum)


# ── AIXM enum listeleri (XSD'den) ───────────────────────────────────────────
CODE_DESIGNATED_POINT = ("ICAO", "COORD", "CNF", "TERMINAL", "BRG_DIST", "VRP")
CODE_NAVAID_SERVICE = ("VOR", "DME", "NDB", "TACAN", "MKR", "ILS", "ILS_DME",
                       "MLS", "MLS_DME", "VORTAC", "VOR_DME", "NDB_DME", "TLS",
                       "LOC", "LOC_DME", "NDB_MKR", "DF", "SDF")
CODE_NAVAID_PURPOSE = ("TERMINAL", "ENROUTE", "ALL")
CODE_SIGNAL_PERFORMANCE = ("I", "II", "III", "IIIA", "IIIB", "IIIC")
CODE_COURSE_QUALITY = ("A", "B", "C", "D", "E", "T")
CODE_INTEGRITY_LEVEL = ("1", "2", "3", "4")
CODE_YES_NO = ("YES", "NO")
CODE_LEVEL = ("UPPER", "LOWER", "BOTH")
CODE_VERTICAL_REFERENCE = ("SFC", "MSL", "W84", "STD")
CODE_ROUTE_SEGMENT_PATH = ("GRC", "RHL", "GDS")
CODE_DIRECTION_TURN = ("LEFT", "RIGHT", "EITHER")
CODE_ATC_REPORTING = ("COMPULSORY", "ON_REQUEST", "NO_REPORT")
CODE_ROUTE = ("ATS", "NAT")
CODE_FLIGHT_RULE = ("IFR", "VFR", "ALL")
CODE_ROUTE_ORIGIN = ("INTL", "DOM", "BOTH")
CODE_MILITARY_STATUS = ("MIL", "CIVIL", "ALL")
CODE_MILITARY_TRAINING = ("IR", "VR", "SR")
CODE_ROUTE_DESIGNATOR_SUFFIX = ("F", "G")
CODE_CARDINAL_DIRECTION = ("N", "NE", "E", "SE", "S", "SW", "W", "NW", "NNE",
                           "ENE", "ESE", "SSE", "SSW", "WSW", "WNW", "NNW")
CODE_FREE_FLIGHT = ("PITCH", "CATCH")
CODE_RVSM_POINT_ROLE = ("IN", "OUT", "IN_OUT")
CODE_MILITARY_ROUTE_POINT = ("S", "T", "X", "AS", "AX", "ASX")
CODE_RADIO_EMISSION = ("A2", "A3A", "A3B", "A3E", "A3H", "A3J", "A3L", "A3U",
                       "J3E", "NONA1A", "NONA2A", "PON", "A8W", "A9W", "NOX", "G1D")
CODE_NORTH_REFERENCE = ("TRUE", "MAG", "GRID")
CODE_ILS_BACK_COURSE = ("YES", "NO", "RSTR")
CODE_POSITION_IN_ILS = ("OUTER", "MIDDLE", "INNER", "BACKCOURSE")
UOM_DISTANCE = ("NM", "KM", "M", "FT", "MI", "CM")
UOM_DISTANCE_VERTICAL = ("FT", "M", "FL", "SM")
UOM_FREQUENCY = ("HZ", "KHZ", "MHZ", "GHZ")

# `navaidComponents_type` / `_class` sütunlarının izinli değerleri
# `equipmentType`'a göre DEĞİŞİR (aynı sütun farklı alt-türlerce paylaşılır).
EQUIPMENT_TYPE_ENUM = {
    "VOR": ("VOR", "DVOR", "VOT"),
    "DME": ("NARROW", "PRECISION", "WIDE"),
    "Azimuth": ("FWD", "BWD"),
}
EQUIPMENT_CLASS_ENUM = {
    "MarkerBeacon": ("FAN", "LOW_PWR_FAN", "Z", "BONES"),
    "NDB": ("ENR", "L", "MAR"),
}
EQUIPMENT_TYPES = ("VOR", "DME", "TACAN", "Localizer", "Glidepath",
                   "MarkerBeacon", "NDB", "SDF", "Azimuth", "Elevation",
                   "DirectionFinder")

_BEARING = number_rule(0, 360)
_ANGLE = number_rule(-180, 180)

# `atsStatus_*` enum'lari — AIXM'den DEGIL, kendi turetme kurallarimizdan
# gelir (bkz. ATS_Status_Fields.md). Bu listeler gpkg/schema.py'deki
# DEPICTION_* sabitleriyle ayni olmak zorundadir.
CODE_DEPICTION_NAV = ("CONV", "RNAVFlyBy", "RNAVFlyOver", "OTHER")
CODE_DEPICTION_SIG_POINT = ("NAVAID", "VFR_REP", "WPT", "INT", "OTHER")

#: Alanlar arasi tutarlilik kurali: `depictionNav=CONV` ile
#: `depictionSIGPointBasicFunc=WPT` BIRLIKTE OLAMAZ. Denetim
#: `build_common_ats.compute_ats_status` icinde uygulanir — o alanlar satir
#: yazildiktan SONRA UPDATE ile dolduruldugu icin `validate_row` gormez.
ATS_STATUS_CONFLICTS = (
    ("atsStatus_depictionNav", "CONV",
     "atsStatus_depictionSIGPointBasicFunc", "WPT",
     "depictionNav_CONV_ile_WPT_birlikte_olamaz"),
)

RULES: dict[str, dict[str, FieldRule]] = {
    "designatedPoints": {
        "atsStatus_depictionNav": enum_rule(*CODE_DEPICTION_NAV),
        "atsStatus_depictionSIGPointBasicFunc":
            enum_rule(*CODE_DEPICTION_SIG_POINT),
        "designatedPoints_designator": FieldRule(max_length=5),
        "designatedPoints_type": enum_rule(*CODE_DESIGNATED_POINT),
        "designatedPoints_name": FieldRule(max_length=60),
        "designatedPoints_codeICAOCountry": FieldRule(max_length=2),
    },
    "navaids": {
        "atsStatus_depictionNav": enum_rule(*CODE_DEPICTION_NAV),
        "atsStatus_depictionSIGPointBasicFunc":
            enum_rule(*CODE_DEPICTION_SIG_POINT),
        "navaids_type": enum_rule(*CODE_NAVAID_SERVICE),
        "navaids_designator": FieldRule(max_length=4),
        "navaids_name": FieldRule(max_length=60),
        "navaids_flightChecked": enum_rule(*CODE_YES_NO),
        "navaids_purpose": enum_rule(*CODE_NAVAID_PURPOSE),
        "navaids_signalPerformance": enum_rule(*CODE_SIGNAL_PERFORMANCE),
        "navaids_courseQuality": enum_rule(*CODE_COURSE_QUALITY),
        "navaids_integrityLevel": enum_rule(*CODE_INTEGRITY_LEVEL),
        "navaids_codeICAOCountry": FieldRule(max_length=2),
        "navaids_locationElevationUom": enum_rule(*UOM_DISTANCE_VERTICAL),
        "navaids_locationHorizontalAccuracyUom": enum_rule(*UOM_DISTANCE),
    },
    "navaidComponents": {
        "navaidComponents_equipmentType": enum_rule(*EQUIPMENT_TYPES,
                                                    allow_other=False),
        "navaidComponents_markerPosition": enum_rule(*CODE_POSITION_IN_ILS),
        "navaidComponents_providesNavigableLocation": enum_rule(*CODE_YES_NO),
        "navaidComponents_designator": FieldRule(max_length=4),
        "navaidComponents_name": FieldRule(max_length=60),
        "navaidComponents_emissionClass": enum_rule(*CODE_RADIO_EMISSION),
        "navaidComponents_mobile": enum_rule(*CODE_YES_NO),
        "navaidComponents_flightChecked": enum_rule(*CODE_YES_NO),
        "navaidComponents_magneticVariation": number_rule(-180, 180),
        "navaidComponents_zeroBearingDirection": enum_rule(*CODE_NORTH_REFERENCE),
        "navaidComponents_backCourseUsable": enum_rule(*CODE_ILS_BACK_COURSE),
        "navaidComponents_signalPerformance": enum_rule(*CODE_SIGNAL_PERFORMANCE),
        "navaidComponents_courseQuality": enum_rule(*CODE_COURSE_QUALITY),
        "navaidComponents_integrityLevel": enum_rule(*CODE_INTEGRITY_LEVEL),
        "navaidComponents_frequencyUom": enum_rule(*UOM_FREQUENCY),
        "navaidComponents_tuningFrequencyVHFUom": enum_rule(*UOM_FREQUENCY),
        "navaidComponents_magneticBearing": _BEARING,
        "navaidComponents_trueBearing": _BEARING,
        "navaidComponents_axisBearing": _BEARING,
        "navaidComponents_declination": number_rule(-180, 180),
        "navaidComponents_widthCourse": _ANGLE,
        "navaidComponents_slope": _ANGLE,
        "navaidComponents_angleNominal": _ANGLE,
        "navaidComponents_angleMinimum": _ANGLE,
        "navaidComponents_angleSpan": _ANGLE,
        "navaidComponents_doppler": enum_rule(*CODE_YES_NO),
        "navaidComponents_locationElevationUom": enum_rule(*UOM_DISTANCE_VERTICAL),
        "navaidComponents_rdhUom": enum_rule(*UOM_DISTANCE_VERTICAL),
    },
    "routeSegments": {
        "routeSegments_level": enum_rule(*CODE_LEVEL),
        "routeSegments_upperLimitUom": enum_rule(*UOM_DISTANCE_VERTICAL),
        "routeSegments_lowerLimitUom": enum_rule(*UOM_DISTANCE_VERTICAL),
        "routeSegments_upperLimitReference": enum_rule(*CODE_VERTICAL_REFERENCE),
        "routeSegments_lowerLimitReference": enum_rule(*CODE_VERTICAL_REFERENCE),
        "routeSegments_minimumCrossingAtEndReference": enum_rule(*CODE_VERTICAL_REFERENCE),
        "routeSegments_maximumCrossingAtEndReference": enum_rule(*CODE_VERTICAL_REFERENCE),
        "routeSegments_pathType": enum_rule(*CODE_ROUTE_SEGMENT_PATH),
        "routeSegments_turnDirection": enum_rule(*CODE_DIRECTION_TURN),
        "routeSegments_signalGap": enum_rule(*CODE_YES_NO),
        "routeSegments_designatorSuffix": enum_rule(*CODE_ROUTE_DESIGNATOR_SUFFIX),
        "routeSegments_trueTrack": _BEARING,
        "routeSegments_magneticTrack": _BEARING,
        "routeSegments_reverseTrueTrack": _BEARING,
        "routeSegments_reverseMagneticTrack": _BEARING,
        "routeSegments_lengthUom": enum_rule(*UOM_DISTANCE),
        "routeSegments_widthLeftUom": enum_rule(*UOM_DISTANCE),
        "routeSegments_widthRightUom": enum_rule(*UOM_DISTANCE),
        "routeSegments_cardinalDirectionLeft": enum_rule(*CODE_CARDINAL_DIRECTION),
        "routeSegments_cardinalDirectionRight": enum_rule(*CODE_CARDINAL_DIRECTION),
        # `route_*` — RouteSegment'in değil, bağlı Route feature'ının alanları
        # (bkz. gpkg/mapper.py, gpkg/schema.py — bilinçli olarak farklı önek).
        "route_type": enum_rule(*CODE_ROUTE),
        "route_flightRule": enum_rule(*CODE_FLIGHT_RULE),
        "route_internationalUse": enum_rule(*CODE_ROUTE_ORIGIN),
        "route_militaryUse": enum_rule(*CODE_MILITARY_STATUS),
        "route_militaryTrainingType": enum_rule(*CODE_MILITARY_TRAINING),
        "route_name": FieldRule(max_length=60),
    },
}

# start/end uçlarının simetrik kuralları
for _side in ("start", "end"):
    RULES["routeSegments"].update({
        f"routeSegments_{_side}ReportingATC": enum_rule(*CODE_ATC_REPORTING),
        f"routeSegments_{_side}FlyOver": enum_rule(*CODE_YES_NO),
        f"routeSegments_{_side}Waypoint": enum_rule(*CODE_YES_NO),
        f"routeSegments_{_side}RadarGuidance": enum_rule(*CODE_YES_NO),
        f"routeSegments_{_side}RoleFreeFlight": enum_rule(*CODE_FREE_FLIGHT),
        f"routeSegments_{_side}RoleRVSM": enum_rule(*CODE_RVSM_POINT_ROLE),
        f"routeSegments_{_side}RoleMilitaryTraining": enum_rule(*CODE_MILITARY_ROUTE_POINT),
        f"routeSegments_{_side}TurnRadiusUom": enum_rule(*UOM_DISTANCE),
    })
