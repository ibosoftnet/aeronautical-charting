"""Route yazıcı.

XSD sırası (RoutePropertyGroup):
  designatorPrefix, designatorSecondLetter, designatorNumber,
  multipleIdentifier, locationDesignator, name, type, flightRule,
  internationalUse, militaryUse, militaryTrainingType, userOrganisation,
  annotation, designCriteria, availability, aircraftCapability

Not: Route'un geometrisi YOKTUR — geometri RouteSegment.curveExtent üzerindedir.
"""

import xml.etree.ElementTree as ET

import mapping
from .writer import NS_GML, aixm, note, opt, q, sub


def write(builder, log, gml_id, feature_uuid, *, designator=None, name=None,
          overrides=None, annotation=None):
    """Tek bir Route feature'ı yazar.

    designator verilirse AIXM designator alanlarına ayrıştırılır (ATS rotaları).
    VFR rotalarının kodu olmadığı için yalnızca `name` yazılır.
    """
    overrides = overrides or {}
    ts = builder.add_feature("Route", gml_id, feature_uuid)

    if designator:
        parts = mapping.decompose_route_designator(designator)
        if parts is None:
            log.error("Route", gml_id, "designator", designator,
                      "rota_kodu_desene_uymuyor")
        else:
            prefix, letter, number, multiple = parts
            opt(ts, aixm("designatorPrefix"), prefix)
            sub(ts, aixm("designatorSecondLetter"), letter)
            sub(ts, aixm("designatorNumber"), number)
            opt(ts, aixm("multipleIdentifier"), multiple)

    opt(ts, aixm("name"), name)

    route_type = overrides.get("type")
    if route_type:
        log.check_enum("Route", gml_id, "type", route_type, mapping.CODE_ROUTE)
        sub(ts, aixm("type"), route_type)

    flight_rule = overrides.get("flightRule")
    if flight_rule:
        log.check_enum("Route", gml_id, "flightRule", flight_rule,
                       mapping.CODE_FLIGHT_RULE)
        sub(ts, aixm("flightRule"), flight_rule)

    # annotation, XSD sırasında designCriteria'dan ÖNCE gelir.
    if annotation:
        note(ts, gml_id + "_NOTE", annotation)

    # designCriteria → DesignStandard nesnesi (annotation'dan SONRA gelir).
    # DesignStandardPropertyGroup: name, version, annotation — enum değeri
    # `name` alanına yazılır (XSD'den teyit edildi).
    design = overrides.get("designCriteria")
    if design:
        log.check_enum("Route", gml_id, "designCriteria", design,
                       mapping.CODE_DESIGN_STANDARD)
        el = ET.SubElement(ts, aixm("designCriteria"))
        std = ET.SubElement(el, aixm("DesignStandard"))
        std.set(q(NS_GML, "id"), gml_id + "_DS")
        sub(std, aixm("name"), design)
