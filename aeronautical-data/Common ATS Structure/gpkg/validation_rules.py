"""AŞAMA 2B — katman/alan doğrulama kuralları.

Kurallar `docs/*.md` öznitelik sözlüklerinden bire bir aktarılmıştır (o
dokümanlar AIXM 5.2 XSD'ye karşı doğrulanarak hazırlanmıştı).

AIXM'de her `Code*Type` bir union'dır: sabit enum listesi **veya**
`OTHER(:(\\w|_){1,58})?` deseni — bu yüzden `allow_other` varsayılan olarak
açıktır.
"""

import re
from dataclasses import dataclass, field
from gpkg import schema

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
CODE_DEPICTION_NAV_AND_REP = tuple(
    f"{nav}_{suffix}" for suffix in ("Comp", "NonComp")
    for nav in CODE_DEPICTION_NAV)

#: Alanlar arasi tutarlilik kurali: `depictionNav=CONV` ile
#: `depictionSIGPointBasicFunc=WPT` BIRLIKTE OLAMAZ. Denetim
#: `build_common_ats.compute_ats_status` icinde uygulanir — o alanlar satir
#: yazildiktan SONRA UPDATE ile dolduruldugu icin `validate_row` gormez.
#: Bileske alan denetimi: `depictionNavAndREP`, iki bileseniyle UC SUTUNLU
#: bir tutarlilik iliskisi tasir —
#:     depictionNavAndREP == depictionNav + ("_Comp" | "_NonComp")
#: sonek `depictionCompulsory` 1 ise `_Comp`, 0 ise `_NonComp` olmalidir.
#: (bileske_sutun, nav_sutun, bayrak_sutun, (dogru_sonek, yanlis_sonek), kod)
ATS_STATUS_COMPOSITES = (
    ("atsStatus_depictionNavAndREP",
     "atsStatus_depictionNav",
     "atsStatus_depictionCompulsory",
     ("Comp", "NonComp"),
     "depictionNavAndREP_bilesenleriyle_uyusmuyor"),
)

ATS_STATUS_CONFLICTS = (
    ("atsStatus_depictionNav", "CONV",
     "atsStatus_depictionSIGPointBasicFunc", "WPT",
     "depictionNav_CONV_ile_WPT_birlikte_olamaz"),
)

#: Alt-türe özgü sütunların (`navaidComponents_<AltTür>_<alan>`) kuralları.
#: Alan adı → kural. `type`, `class` ve `channel` artık AYRI SÜTUNLARDA olduğu
#: için her alt-tür KENDİ enum'unu alabiliyor — eskiden tek sütunda çakışan üç
#: enum, çalışma zamanında `equipmentType`'a bakılarak ayrıştırılmak zorundaydı
#: (`validate.py`), `channel` ise hiç doğrulanamıyordu.
_EQUIPMENT_FIELD_RULES = {
    ("VOR", "type"): lambda: enum_rule("VOR", "DVOR", "VOT"),
    ("DME", "type"): lambda: enum_rule("NARROW", "PRECISION", "WIDE"),
    ("Azimuth", "type"): lambda: enum_rule("FWD", "BWD"),
    ("MarkerBeacon", "class"): lambda: enum_rule("FAN", "LOW_PWR_FAN", "Z",
                                                 "BONES"),
    ("NDB", "class"): lambda: enum_rule("ENR", "L", "MAR"),
}

#: Alt-türden bağımsız, alan adına göre geçerli kurallar.
_EQUIPMENT_COMMON_RULES = {
    "zeroBearingDirection": lambda: enum_rule(*CODE_NORTH_REFERENCE),
    "backCourseUsable": lambda: enum_rule(*CODE_ILS_BACK_COURSE),
    "signalPerformance": lambda: enum_rule(*CODE_SIGNAL_PERFORMANCE),
    "courseQuality": lambda: enum_rule(*CODE_COURSE_QUALITY),
    "integrityLevel": lambda: enum_rule(*CODE_INTEGRITY_LEVEL),
    "doppler": lambda: enum_rule(*CODE_YES_NO),
    "frequencyUom": lambda: enum_rule(*UOM_FREQUENCY),
    "tuningFrequencyVHFUom": lambda: enum_rule(*UOM_FREQUENCY),
    "rdhUom": lambda: enum_rule(*UOM_DISTANCE_VERTICAL),
    "displaceUom": lambda: enum_rule(*UOM_DISTANCE_VERTICAL),
    "magneticBearing": lambda: _BEARING,
    "trueBearing": lambda: _BEARING,
    "axisBearing": lambda: _BEARING,
    "declination": lambda: number_rule(-180, 180),
    "widthCourse": lambda: _ANGLE,
    "slope": lambda: _ANGLE,
    "angleNominal": lambda: _ANGLE,
    "angleMinimum": lambda: _ANGLE,
    "angleSpan": lambda: _ANGLE,
    "angleProportionalLeft": lambda: _ANGLE,
    "angleProportionalRight": lambda: _ANGLE,
    "angleCoverLeft": lambda: _ANGLE,
    "angleCoverRight": lambda: _ANGLE,
}


def _navaid_component_rules():
    """`navaidComponents` kural sözlüğünü ÜRETİR — elle yazılmaz.

    Ortak taban sütunları sabit; alt-tür sütunları
    `schema.EQUIPMENT_SUBTYPE_FIELDS`'ten türetilir, böylece şema değişince
    kurallar da kendiliğinden takip eder.
    """
    rules = {
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
        "navaidComponents_locationElevationUom":
            enum_rule(*UOM_DISTANCE_VERTICAL),
    }
    for subtype, fields in schema.EQUIPMENT_SUBTYPE_FIELDS.items():
        for field in fields:
            names = [field]
            if field in schema.EQUIPMENT_VALUE_UOM:
                names.append(field + "Uom")
            for name in names:
                factory = (_EQUIPMENT_FIELD_RULES.get((subtype, name))
                           or _EQUIPMENT_COMMON_RULES.get(name))
                if factory:
                    rules[schema.equipment_column(subtype, name)] = factory()
    return rules


RULES: dict[str, dict[str, FieldRule]] = {
    "designatedPoints": {
        "atsStatus_depictionNav": enum_rule(*CODE_DEPICTION_NAV),
        "atsStatus_depictionSIGPointBasicFunc":
            enum_rule(*CODE_DEPICTION_SIG_POINT),
        "atsStatus_depictionNavAndREP":
            enum_rule(*CODE_DEPICTION_NAV_AND_REP),
        "atsStatus_depictionNavAndREP":
            enum_rule(*CODE_DEPICTION_NAV_AND_REP),
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
    "navaidComponents": _navaid_component_rules(),
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
