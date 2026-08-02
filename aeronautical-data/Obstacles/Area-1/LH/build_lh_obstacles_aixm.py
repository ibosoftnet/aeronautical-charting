"""
LH (Macaristan) engel verisini Excel'den AIXM 5.1 VerticalStructure XML'ine cevirir.

Girdi : LHCC_Database_2024_all_100.xlsx  (Obstacle_Data sayfasi)
Cikti : LH_ENR_5_4_Obstacles_AIXM_5_1.xml

Bir 'Obstacle Identifier' = bir aixm:VerticalStructure,
her Excel satiri  = bir aixm:VerticalStructurePart.

Bu script ust klasordeki build_obstacles_gpkg.py'den bagimsizdir; sadece bu
klasordeki Excel'i okur ve bu klasore XML yazar.
"""

from __future__ import annotations

import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import openpyxl

BASE_DIR = Path(__file__).resolve().parent
INPUT_XLSX = BASE_DIR / "LHCC_Database_2024_all_100.xlsx"
OUTPUT_XML = BASE_DIR / "LH_ENR_5_4_Obstacles_AIXM_5_1.xml"
SHEET_NAME = "Obstacle_Data"

MSG_NS = "http://www.aixm.aero/schema/5.1/message"
AIXM_NS = "http://www.aixm.aero/schema/5.1"
GML_NS = "http://www.opengis.net/gml/3.2"
XLINK_NS = "http://www.w3.org/1999/xlink"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

MSG = f"{{{MSG_NS}}}"
AIXM = f"{{{AIXM_NS}}}"
GML = f"{{{GML_NS}}}"

# gml:identifier UUIDv5 uretimi icin sabit namespace - degistirilirse tum
# identifier'lar degisir, bu yuzden sabit tutulmalidir.
UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "obstacles.lh.aixm.ibosoft")

SRS_NAME = "urn:ogc:def:crs:EPSG::4326"

# Excel'de "veri yok" anlamina gelen degerler. Bunlar AIXM kod listelerinde
# karsiligi olmadigi icin ilgili eleman hic yazilmaz.
EMPTY_VALUES = {"", "unknown", "UNKNOWN", "None", "N/A", "NA", "-"}

COL = {
    "lat_gml": "Latitude (WGS-84, GML)",
    "lon_gml": "Longitude (WGS-84, GML)",
    "obstacle_id": "Obstacle Identifier",
    "part_id": "Obstacle Part Identifier",
    "type": "Type",
    "material": "Material",
    "lighted": "Lighted",
    "lighting_colour": "Lighting colour",
    "marking_icao": "Marking ICAO Standard",
    "marking_pattern": "Marking pattern",
    "marking_colour1": "Marking First Colour",
    "marking_colour2": "Marking Second Colour",
    "horiz_accuracy": "Horizontal accuracy",
    "horiz_accuracy_uom": "Horizontal accuracy Uom",
    "elevation": "Elevation (at top)",
    "elevation_uom": "Elevation Uom",
    "height": "Height",
    "height_uom": "Height Uom",
    "vert_accuracy": "Vertical Accuracy",
    "vert_accuracy_uom": "Vertical Accuracy Uom",
    "vert_datum": "Vertical Datum",
    "mobile": "Mobile",
    "timestamp": "Timestamp",
}


class GmlIdCounter:
    """LT dosyasindaki 'gml.idN' desenini uretir."""

    def __init__(self) -> None:
        self._n = 0

    def next(self) -> str:
        self._n += 1
        return f"gml.id{self._n}"


def clean(value: Any) -> str | None:
    """Hucre degerini metne cevir; bos/bilinmeyen ise None don."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text in EMPTY_VALUES else text


def sub(parent: ET.Element, tag: str, text: str | None = None, **attrs: str) -> ET.Element:
    elem = ET.SubElement(parent, tag, {k: v for k, v in attrs.items() if v is not None})
    if text is not None:
        elem.text = text
    return elem


def add_optional(parent: ET.Element, tag: str, value: Any, **attrs: str) -> None:
    """Deger doluysa elemani ekle, degilse hic yazma."""
    text = clean(value)
    if text is not None:
        sub(parent, tag, text, **attrs)


def read_rows() -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(INPUT_XLSX, read_only=True, data_only=True)
    ws = wb[SHEET_NAME]
    rows_iter = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows_iter)]

    missing = [name for name in COL.values() if name not in header]
    if missing:
        raise SystemExit(f"HATA: Excel'de beklenen sutunlar yok: {missing}")

    index = {key: header.index(name) for key, name in COL.items()}

    rows: list[dict[str, Any]] = []
    for raw in rows_iter:
        if raw is None or not any(cell is not None for cell in raw):
            continue
        row = {key: raw[i] if i < len(raw) else None for key, i in index.items()}
        if clean(row["obstacle_id"]) is None:
            continue
        rows.append(row)
    wb.close()
    return rows


def group_by_obstacle(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Excel sirasini koruyarak Obstacle Identifier'a gore grupla."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row["obstacle_id"]).strip(), []).append(row)
    return groups


def make_identifier(obstacle_id: str) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE, obstacle_id)).upper()


def add_time_period(parent: ET.Element, tag: str, begin: str, ids: GmlIdCounter) -> None:
    wrapper = sub(parent, tag)
    period = sub(wrapper, f"{GML}TimePeriod", **{f"{GML}id": ids.next()})
    sub(period, f"{GML}beginPosition", begin)
    sub(period, f"{GML}endPosition", indeterminatePosition="unknown")


def build_part(parent: ET.Element, row: dict[str, Any], ids: GmlIdCounter) -> bool:
    """VerticalStructurePart ekler. Koordinat yoksa False doner."""
    lat = clean(row["lat_gml"])
    lon = clean(row["lon_gml"])
    if lat is None or lon is None:
        return False

    wrapper = sub(parent, f"{AIXM}part")
    part = sub(wrapper, f"{AIXM}VerticalStructurePart", **{f"{GML}id": ids.next()})

    # XSD VerticalStructurePartPropertyGroup sequence sirasi
    add_optional(part, f"{AIXM}verticalExtent", row["height"], uom=clean(row["height_uom"]))
    add_optional(part, f"{AIXM}type", row["type"])
    add_optional(part, f"{AIXM}markingPattern", row["marking_pattern"])
    add_optional(part, f"{AIXM}markingFirstColour", row["marking_colour1"])
    add_optional(part, f"{AIXM}markingSecondColour", row["marking_colour2"])
    add_optional(part, f"{AIXM}mobile", row["mobile"])
    add_optional(part, f"{AIXM}visibleMaterial", row["material"])
    add_optional(part, f"{AIXM}designator", row["part_id"])

    location = sub(part, f"{AIXM}horizontalProjection_location")
    point = sub(
        location,
        f"{AIXM}ElevatedPoint",
        **{f"{GML}id": ids.next(), "srsName": SRS_NAME},
    )
    sub(point, f"{GML}pos", f"{lat} {lon}")
    # PointPropertyGroup (horizontalAccuracy) ElevatedPointPropertyGroup'tan once gelir
    add_optional(
        point, f"{AIXM}horizontalAccuracy", row["horiz_accuracy"], uom=clean(row["horiz_accuracy_uom"])
    )
    add_optional(point, f"{AIXM}elevation", row["elevation"], uom=clean(row["elevation_uom"]))
    add_optional(point, f"{AIXM}verticalDatum", row["vert_datum"])
    add_optional(
        point, f"{AIXM}verticalAccuracy", row["vert_accuracy"], uom=clean(row["vert_accuracy_uom"])
    )

    colour = clean(row["lighting_colour"])
    if colour is not None:
        lighting = sub(part, f"{AIXM}lighting")
        light = sub(lighting, f"{AIXM}LightElement", **{f"{GML}id": ids.next()})
        sub(light, f"{AIXM}colour", colour)

    return True


def build_structure(
    root: ET.Element, obstacle_id: str, rows: list[dict[str, Any]], ids: GmlIdCounter
) -> int:
    """VerticalStructure ekler; yazilan part sayisini doner."""
    first = rows[0]
    begin = clean(first["timestamp"]) or ""

    member = sub(root, f"{MSG}hasMember")
    structure = sub(member, f"{AIXM}VerticalStructure", **{f"{GML}id": ids.next()})
    sub(structure, f"{GML}identifier", make_identifier(obstacle_id), codeSpace="urn:uuid:")

    time_slice_wrapper = sub(structure, f"{AIXM}timeSlice")
    ts = sub(
        time_slice_wrapper, f"{AIXM}VerticalStructureTimeSlice", **{f"{GML}id": ids.next()}
    )

    # XSD sirasi: validTime, interpretation, sequenceNumber, correctionNumber,
    # featureLifetime, ardindan VerticalStructurePropertyGroup
    add_time_period(ts, f"{GML}validTime", begin, ids)
    sub(ts, f"{AIXM}interpretation", "BASELINE")
    sub(ts, f"{AIXM}sequenceNumber", "1")
    sub(ts, f"{AIXM}correctionNumber", "0")
    add_time_period(ts, f"{AIXM}featureLifetime", begin, ids)

    sub(ts, f"{AIXM}name", obstacle_id)
    add_optional(ts, f"{AIXM}type", first["type"])
    add_optional(ts, f"{AIXM}lighted", first["lighted"])
    add_optional(ts, f"{AIXM}markingICAOStandard", first["marking_icao"])
    sub(ts, f"{AIXM}group", "NO")

    written = 0
    for row in rows:
        if build_part(ts, row, ids):
            written += 1

    if written == 0:
        root.remove(member)
    return written


def build_document(groups: dict[str, list[dict[str, Any]]]) -> tuple[ET.ElementTree, int, int]:
    for prefix, ns in (
        ("", MSG_NS),
        ("aixm", AIXM_NS),
        ("gml", GML_NS),
        ("xlink", XLINK_NS),
        ("xsi", XSI_NS),
    ):
        ET.register_namespace(prefix, ns)

    ids = GmlIdCounter()
    root = ET.Element(
        f"{MSG}AIXMBasicMessage",
        {
            f"{GML}id": ids.next(),
            f"{{{XSI_NS}}}schemaLocation": (
                "http://www.aixm.aero/schema/5.1/message "
                "https://www.aixm.aero/schema/5.1/message/AIXM_BasicMessage.xsd"
            ),
        },
    )

    structures = 0
    parts = 0
    for obstacle_id, rows in groups.items():
        written = build_structure(root, obstacle_id, rows, ids)
        if written:
            structures += 1
            parts += written

    ET.indent(root, space="\t")
    return ET.ElementTree(root), structures, parts


def main() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")

    print("=" * 60)
    print("LH Engel Verisi (Excel) -> AIXM 5.1 XML")
    print("=" * 60)

    if not INPUT_XLSX.exists():
        print(f"HATA: Girdi bulunamadi: {INPUT_XLSX.name}")
        sys.exit(1)

    print(f"[1] Okunuyor: {INPUT_XLSX.name} / {SHEET_NAME}")
    rows = read_rows()
    print(f"    {len(rows)} veri satiri okundu")

    groups = group_by_obstacle(rows)
    print(f"    {len(groups)} farkli Obstacle Identifier")

    print("[2] AIXM agaci olusturuluyor…")
    tree, structures, parts = build_document(groups)
    skipped = len(rows) - parts

    print("[3] Yaziliyor…")
    tree.write(OUTPUT_XML, encoding="UTF-8", xml_declaration=True)

    size_kb = OUTPUT_XML.stat().st_size / 1024
    print("\n" + "=" * 60)
    print(f"Tamamlandi: {OUTPUT_XML.name} ({size_kb:.0f} KB)")
    print(f"  {structures} VerticalStructure, {parts} VerticalStructurePart")
    if skipped:
        print(f"  {skipped} satir atlandi (koordinat yok)")
    print("Ust klasordeki convert_obstacles.bat artik LH verisini de gpkg'ye alir.")
    print("=" * 60)


if __name__ == "__main__":
    main()
