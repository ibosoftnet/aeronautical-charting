"""DesignatedPoint yazıcı.

XSD sırası (DesignatedPointPropertyGroup):
  designator, type, name, location, aimingPoint, airportHeliport,
  runwayPoint, annotation, codeICAOCountry, fix
"""

import xml.etree.ElementTree as ET

import mapping
from .writer import NS_GML, aixm, note, opt, pos, q, sub, xlink_ref, SRS_NAME


def write(builder, log, gml_id, feature_uuid, record, *, designator=None,
          point_type=None, name=None, fix_groups=None, annotation=None):
    """Tek bir DesignatedPoint feature'ı yazar.

    fix_groups: [[{'navaid_uuid': …, 'radial': …, 'distance': …}, …], …]
    Her iç liste KAYNAKTAKİ BİR konum tarifidir ve kendi `aixm:fix`/
    `PointReference` nesnesini alır. Tarif içinde tek navaid varsa
    role=RAD_DME, birden fazla navaid varsa (gerçek kesişim noktası)
    role=INTERSECTION. Birleştirilmiş noktalarda birden fazla BAĞIMSIZ
    tarif bulunabildiği için `fix` XSD'de 0..∞'dur (kullanıcı kararı).

    annotation: str veya str listesi. Birden fazla not verilirse her biri
    ayrı `aixm:annotation` olur (XSD'de 0..∞).
    """
    ts = builder.add_feature("DesignatedPoint", gml_id, feature_uuid)

    opt(ts, aixm("designator"), designator)

    if point_type:
        log.check_enum("DesignatedPoint", gml_id, "type", point_type,
                       mapping.CODE_DESIGNATED_POINT)
        sub(ts, aixm("type"), point_type)

    opt(ts, aixm("name"), name)

    # location → aixm:Point (Navaid'den farklı olarak ElevatedPoint değil)
    loc = ET.SubElement(ts, aixm("location"))
    point = ET.SubElement(loc, aixm("Point"))
    point.set(q(NS_GML, "id"), gml_id + "_P")
    point.set("srsName", SRS_NAME)
    pos(point, record["lat"], record["lon"])

    _write_notes(ts, gml_id, annotation)

    # Kaynağın tamamı DHMİ Türkiye verisidir; ICAO Doc 7910'a göre Türkiye'nin
    # lokasyon göstergesi öneki "LT"dir (LTBA, LTFJ, LTAC …) — kullanıcı kararı.
    sub(ts, aixm("codeICAOCountry"), "LT")

    for n, fixes in enumerate(fix_groups or [], 1):
        if fixes:
            _write_fix(ts, f"{gml_id}_FIX{n}", fixes)


def _write_notes(ts, gml_id, annotation):
    """annotation str ya da liste olabilir; boş girdiler atlanır.

    Tek not eski `_NOTE` id'sini korur; birden fazlası `_NOTE1`, `_NOTE2` …
    olur (gml:id belge içinde benzersiz olmak zorundadır).
    """
    if not annotation:
        return
    texts = [annotation] if isinstance(annotation, str) else list(annotation)
    texts = [t for t in texts if t]
    if not texts:
        return
    if len(texts) == 1:
        note(ts, gml_id + "_NOTE", texts[0])
        return
    for n, text in enumerate(texts, 1):
        note(ts, f"{gml_id}_NOTE{n}", text)


def _write_fix(ts, fix_id, fixes):
    """Bir konum tarifi → tek `aixm:fix`/PointReference.

    XSD sırası (PointReferencePropertyGroup): role, priorFixTolerance,
    postFixTolerance, fixToleranceArea, annotation, minimumReceptionLimit,
    minimumReceptionLimitReference, maximumAuthorisedLimit,
    maximumAuthorisedLimitReference, distanceReference, angleReference
    """
    fix_el = ET.SubElement(ts, aixm("fix"))
    ref = ET.SubElement(fix_el, aixm("PointReference"))
    ref.set(q(NS_GML, "id"), fix_id)

    # Tek navaid → RAD_DME, birden fazla navaid → INTERSECTION
    role = "RAD_DME" if len(fixes) == 1 else "INTERSECTION"
    sub(ref, aixm("role"), role)

    # distanceReference'lar angleReference'lardan ÖNCE gelir (XSD sırası).
    for i, fix in enumerate(fixes, 1):
        dist_el = ET.SubElement(ref, aixm("distanceReference"))
        dist = ET.SubElement(dist_el, aixm("Distance"))
        dist.set(q(NS_GML, "id"), f"{fix_id}_DIST{i}")
        sub(dist, aixm("distance"), fix["distance"], uom="NM")
        sub(dist, aixm("type"), "DME")
        xlink_ref(dist, aixm("pointChoice_navaidSystem"), fix["navaid_uuid"])

    for i, fix in enumerate(fixes, 1):
        ang_el = ET.SubElement(ref, aixm("angleReference"))
        use = ET.SubElement(ang_el, aixm("AngleUse"))
        use.set(q(NS_GML, "id"), f"{fix_id}_ANGUSE{i}")
        angle_el = ET.SubElement(use, aixm("theAngle"))
        angle = ET.SubElement(angle_el, aixm("Angle"))
        angle.set(q(NS_GML, "id"), f"{fix_id}_ANG{i}")
        sub(angle, aixm("angle"), fix["radial"])
        sub(angle, aixm("angleType"), "RDL")
        sub(angle, aixm("indicationDirection"), "FROM")
        xlink_ref(angle, aixm("pointChoice_navaidSystem"), fix["navaid_uuid"])
