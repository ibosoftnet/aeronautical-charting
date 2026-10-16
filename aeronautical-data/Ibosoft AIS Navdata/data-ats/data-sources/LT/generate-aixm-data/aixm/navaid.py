"""Navaid yazıcı.

XSD sırası (NavaidPropertyGroup):
  type, designator, name, flightChecked, purpose, signalPerformance,
  courseQuality, integrityLevel, touchDownLiftOff, navaidEquipment,
  location, runwayDirection, servedAirport, availability, annotation,
  codeICAOCountry
"""

import xml.etree.ElementTree as ET

import mapping
from .writer import NS_GML, aixm, note, opt, pos, q, sub, SRS_NAME


def write(builder, log, gml_id, feature_uuid, *, navaid_type=None,
          designator=None, name=None, lat=None, lon=None, annotation=None):
    """Tek bir Navaid feature'ı yazar.

    Konum verilmezse (kaynakta tanımlı olmayan stub navaid'ler) `location`
    hiç yazılmaz — uydurma koordinat üretilmez.
    """
    ts = builder.add_feature("Navaid", gml_id, feature_uuid)

    if navaid_type:
        log.check_enum("Navaid", gml_id, "type", navaid_type,
                       mapping.CODE_NAVAID_SERVICE)
        sub(ts, aixm("type"), navaid_type)

    opt(ts, aixm("designator"), designator)
    opt(ts, aixm("name"), name)

    if lat is not None and lon is not None:
        # Navaid.location ElevatedPoint tipindedir (Point değil).
        loc = ET.SubElement(ts, aixm("location"))
        point = ET.SubElement(loc, aixm("ElevatedPoint"))
        point.set(q(NS_GML, "id"), gml_id + "_EP")
        point.set("srsName", SRS_NAME)
        pos(point, lat, lon)

    if annotation:
        note(ts, gml_id + "_NOTE", annotation)

    # Kaynağın tamamı DHMİ Türkiye verisidir; ICAO Doc 7910'a göre Türkiye'nin
    # lokasyon göstergesi öneki "LT"dir (LTBA, LTFJ, LTAC …) — kullanıcı kararı.
    sub(ts, aixm("codeICAOCountry"), "LT")
