"""
EAD-SDO Navaid (VOR, DME, TACAN, ILS) veri dosyalarını birleştirir,
ilgili alt elemanları (DME→VOR, GP→ILS, vb.) eşleştirir ve QGIS uyumlu
spatial GeoPackage üretir. Tailored (manuel) veri desteği dahil.
Tüm sütunlarda index oluşturur - query performansı için optimize edilmiş.
"""

from __future__ import annotations

import json
import sqlite3
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_GPKG = BASE_DIR / "navaids.gpkg"

# XML kaynakları
VOR_XML = BASE_DIR / "vor.xml"
DME_XML = BASE_DIR / "dme.xml"
TACAN_XML = BASE_DIR / "tacan.xml"
ILS_LOC_XML = BASE_DIR / "ils-loc.xml"
ILS_GP_XML = BASE_DIR / "ils-gp.xml"
TAILORED_JSON = BASE_DIR / "tailored-navaids.jsonc"
FREQUENCY_PAIRING_CSV = BASE_DIR / "frequency-pairing.csv"

# GeoPackage katmanları
ILS_LOC_TABLE = "ils_loc"
ILS_GP_TABLE = "ils_gp"
ILS_DME_TABLE = "ils_dme"
VOR_TABLE = "vor"
VOR_DME_TABLE = "vor_dme"
VORTAC_TABLE = "vortac"
DME_TABLE = "dme"
TACAN_TABLE = "tacan"


def read_head_text(path: Path, size: int = 256) -> str:
    try:
        return path.read_bytes()[:size].decode("utf-8", errors="ignore").strip()
    except OSError:
        return ""


def looks_like_xml(path: Path) -> tuple[bool, str | None]:
    if not path.exists():
        return False, "dosya bulunamadı"
    head = read_head_text(path).lstrip("\ufeff")
    if not head:
        return False, "dosya boş"
    if not head.startswith("<"):
        return False, head[:80]
    return True, None


def normalize_code(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().upper()
    return text or None


def prefix_row(d: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Dict alanlarına prefix ekle (tüm alanlar, boş value'ları da dahil)"""
    return {f"{prefix}{k}": v for k, v in d.items()}


def parse_coord(coord: str | None, is_lat: bool) -> float | None:
    if not coord:
        return None

    text = coord.strip().upper().replace(" ", "")
    if not text:
        return None

    sign = 1
    if text[0] in "+-":
        if text[0] == "-":
            sign = -1
        text = text[1:]

    if text and text[-1] in "NSEW":
        if text[-1] in "SW":
            sign *= -1
        text = text[:-1]

    if not text:
        return None

    deg_len = 2 if is_lat else 3
    before, dot, after = text.partition(".")

    # Decimal degrees
    if len(before) <= deg_len:
        try:
            return sign * float(text)
        except ValueError:
            return None

    # Degrees + decimal minutes
    if len(before) <= deg_len + 2:
        try:
            degrees = int(before[:deg_len])
            minutes = float(before[deg_len:] + (dot + after if dot else ""))
            return sign * (degrees + minutes / 60.0)
        except ValueError:
            return None

    # Degrees + minutes + decimal seconds
    try:
        degrees = int(before[:deg_len])
        minutes = int(before[deg_len : deg_len + 2])
        seconds = float(before[deg_len + 2 :] + (dot + after if dot else ""))
        return sign * (degrees + minutes / 60.0 + seconds / 3600.0)
    except ValueError:
        return None


def strip_jsonc_comments(text: str) -> str:
    result: list[str] = []
    in_string = False
    escape = False
    i = 0

    while i < len(text):
        ch = text[i]

        if in_string:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == "/":
                i += 2
                while i < len(text) and text[i] not in "\r\n":
                    i += 1
                continue
            if nxt == "*":
                i += 2
                while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2
                continue

        result.append(ch)
        i += 1

    return "".join(result)


def gpkg_point_blob(lon: float, lat: float, srs_id: int = 4326) -> bytes:
    header = b"GP" + bytes([0, 1]) + struct.pack("<i", srs_id)
    wkb = struct.pack("<BI2d", 1, 1, lon, lat)
    return header + wkb


def create_base_gpkg(con: sqlite3.Connection):
    cur = con.cursor()
    cur.executescript(
        """
        PRAGMA application_id = 0x47504B47;
        PRAGMA user_version = 10300;
        PRAGMA encoding = 'UTF-8';

        CREATE TABLE IF NOT EXISTS gpkg_spatial_ref_sys (
            srs_name TEXT NOT NULL,
            srs_id INTEGER NOT NULL PRIMARY KEY,
            organization TEXT NOT NULL,
            organization_coordsys_id INTEGER NOT NULL,
            definition TEXT NOT NULL,
            description TEXT
        );

        INSERT OR IGNORE INTO gpkg_spatial_ref_sys VALUES
            ('Undefined Cartesian', -1, 'NONE', -1, 'undefined', 'undefined cartesian'),
            ('Undefined Geographic', 0, 'NONE', 0, 'undefined', 'undefined geographic'),
            ('WGS84', 4326, 'EPSG', 4326,
             'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]',
             'WGS 84 geographic 2D');

        CREATE TABLE IF NOT EXISTS gpkg_contents (
            table_name TEXT NOT NULL PRIMARY KEY,
            data_type TEXT NOT NULL,
            identifier TEXT UNIQUE,
            description TEXT DEFAULT '',
            last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            min_x REAL, min_y REAL, max_x REAL, max_y REAL,
            srs_id INTEGER,
            CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
        );

        CREATE TABLE IF NOT EXISTS gpkg_geometry_columns (
            table_name TEXT NOT NULL,
            column_name TEXT NOT NULL,
            geometry_type_name TEXT NOT NULL,
            srs_id INTEGER NOT NULL,
            z TINYINT NOT NULL,
            m TINYINT NOT NULL,
            PRIMARY KEY (table_name, column_name),
            CONSTRAINT fk_ggc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
            CONSTRAINT fk_ggc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
        );

        CREATE TABLE IF NOT EXISTS gpkg_extensions (
            table_name TEXT,
            column_name TEXT,
            extension_name TEXT NOT NULL,
            definition TEXT NOT NULL,
            scope TEXT NOT NULL,
            CONSTRAINT ge_tce UNIQUE (table_name, column_name, extension_name)
        );

        CREATE TABLE IF NOT EXISTS gpkg_ogr_contents (
            table_name TEXT NOT NULL PRIMARY KEY,
            feature_count INTEGER DEFAULT 0
        );
        """
    )
    con.commit()


def load_dme_records(xml_path: Path) -> dict[str, dict[str, Any]]:
    """DME XML'i oku, mid → record dict'e """
    records: dict[str, dict[str, Any]] = {}
    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  DME atlandı: {reason}")
        return records

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue

        mid = (elem.findtext("mid") or "").strip() or None
        code_id = normalize_code(elem.findtext("codeId"))
        if not mid or not code_id:
            elem.clear()
            continue

        lat_text = (elem.findtext("geoLat") or "").strip()
        lon_text = (elem.findtext("geoLong") or "").strip()
        lat_dd = parse_coord(lat_text, is_lat=True)
        lon_dd = parse_coord(lon_text, is_lat=False)

        if lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        vor_code_id = normalize_code(elem.findtext("Vor/codeId"))

        records[mid] = {
            "mid": mid,
            "code_id": code_id,
            "name": (elem.findtext("txtName") or "").strip() or None,
            "country": (elem.findtext("Org/txtName") or "").strip() or None,
            "channel": (elem.findtext("codeChannel") or "").strip() or None,
            "ghost_freq": (elem.findtext("valGhostFreq") or "").strip() or None,
            "uom_ghost_freq": (elem.findtext("uomGhostFreq") or "").strip() or None,
            "datum": (elem.findtext("codeDatum") or "").strip() or None,
            "work_hr": (elem.findtext("codeWorkHr") or "").strip() or None,
            "dt_wef": (elem.findtext("dtWef") or "").strip() or None,
            "created_by": (elem.findtext("OrgCre/txtName") or "").strip() or None,
            "vor_code_id": vor_code_id,
            "lat_text": lat_text,
            "lon_text": lon_text,
            "lat_dd": lat_dd,
            "lon_dd": lon_dd,
            "source": "xml",
        }
        elem.clear()

    print(f"  DME okunan: {len(records)}")
    return records


def load_tacan_records(xml_path: Path) -> dict[str, dict[str, Any]]:
    """TACAN XML'i oku"""
    records: dict[str, dict[str, Any]] = {}
    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  TACAN atlandı: {reason}")
        return records

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue

        mid = (elem.findtext("mid") or "").strip() or None
        code_id = normalize_code(elem.findtext("codeId"))
        if not mid or not code_id:
            elem.clear()
            continue

        lat_text = (elem.findtext("geoLat") or "").strip()
        lon_text = (elem.findtext("geoLong") or "").strip()
        lat_dd = parse_coord(lat_text, is_lat=True)
        lon_dd = parse_coord(lon_text, is_lat=False)

        if lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        vor_code_id = normalize_code(elem.findtext("Vor/codeId"))

        records[mid] = {
            "mid": mid,
            "code_id": code_id,
            "name": (elem.findtext("txtName") or "").strip() or None,
            "country": (elem.findtext("Org/txtName") or "").strip() or None,
            "channel": (elem.findtext("codeChannel") or "").strip() or None,
            "datum": (elem.findtext("codeDatum") or "").strip() or None,
            "vor_code_id": vor_code_id,
            "vor_lat_text": (elem.findtext("Vor/geoLat") or "").strip() or None,
            "vor_lon_text": (elem.findtext("Vor/geoLong") or "").strip() or None,
            "work_hr": (elem.findtext("codeWorkHr") or "").strip() or None,
            "dt_wef": (elem.findtext("dtWef") or "").strip() or None,
            "created_by": (elem.findtext("OrgCre/txtName") or "").strip() or None,
            "lat_text": lat_text,
            "lon_text": lon_text,
            "lat_dd": lat_dd,
            "lon_dd": lon_dd,
            "source": "xml",
        }
        elem.clear()

    print(f"  TACAN okunan: {len(records)}")
    return records


def load_gp_records(xml_path: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    """GP XML'i oku, lookup index: (ahp_code_id, fir_code_id, ilz_code_id, originator) → record"""
    records: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  ILS-GP atlandı: {reason}")
        return records

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue

        ahp_code_id = normalize_code(elem.findtext("Ahp/codeId"))
        fir_code_id = normalize_code(elem.findtext("Ase/firCodeId"))
        ilz_code_id = normalize_code(elem.findtext("Ilz/codeId"))
        originator = (elem.findtext("OrgCre/txtName") or "").strip() or None

        if not all([ahp_code_id, ilz_code_id, originator]):
            elem.clear()
            continue

        lat_text = (elem.findtext("geoLat") or "").strip()
        lon_text = (elem.findtext("geoLong") or "").strip()
        lat_dd = parse_coord(lat_text, is_lat=True)
        lon_dd = parse_coord(lon_text, is_lat=False)

        if lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        key = (ahp_code_id or "", fir_code_id or "", ilz_code_id or "", originator or "")

        records[key] = {
            "mid": (elem.findtext("mid") or "").strip() or None,
            "lat_text": lat_text,
            "lon_text": lon_text,
            "lat_dd": lat_dd,
            "lon_dd": lon_dd,
            "freq": (elem.findtext("valFreq") or "").strip() or None,
            "slope": (elem.findtext("valSlope") or "").strip() or None,
            "elev": (elem.findtext("valElev") or "").strip() or None,
            "rdh": (elem.findtext("valRdh") or "").strip() or None,
            "uom_rdh": (elem.findtext("uomRdh") or "").strip() or None,
            "datum": (elem.findtext("codeDatum") or "").strip() or None,
            "emission": (elem.findtext("codeEm") or "").strip() or None,
            "crc": (elem.findtext("valCrc") or "").strip() or None,
            "dt_wef": (elem.findtext("dtWef") or "").strip() or None,
            "source": "xml",
        }
        elem.clear()

    print(f"  ILS-GP okunan: {len(records)}")
    return records


def load_loc_records(
    xml_path: Path,
    gp_index: dict[tuple[str, str, str, str], dict[str, Any]],
    dme_records: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    """LOC XML'i oku, GP ve DME ile eşleştir.
    Returns: (loc_rows, gp_rows, ils_dme_rows, dme_consumed_by_ils)
    - loc_rows: LOC kayıtları (GP+DME sub-elementler flattened)
    - gp_rows: Eşleşen GP'ler (ils_gp katmanı için, kendi konumlarıyla)
    - ils_dme_rows: Eşleşen DME'ler (ils_dme katmanı için, kendi konumlarıyla)
    """
    loc_rows: list[dict[str, Any]] = []
    gp_rows: list[dict[str, Any]] = []
    ils_dme_rows: list[dict[str, Any]] = []
    dme_consumed_by_ils: set[str] = set()

    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  ILS-LOC atlandı: {reason}")
        return loc_rows, gp_rows, ils_dme_rows, dme_consumed_by_ils

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue

        code_id = normalize_code(elem.findtext("codeId"))
        ahp_code_id = normalize_code(elem.findtext("Ahp/codeId"))
        ahp_code_icao = normalize_code(elem.findtext("Ahp/codeIcao"))
        fir_code_id = normalize_code(elem.findtext("Ase/firCodeId"))
        originator = (elem.findtext("OrgCre/txtName") or "").strip() or None
        rwy_desig = (elem.findtext("Rwy/txtDesig") or "").strip() or None
        rdn_desig = (elem.findtext("Rdn/txtDesig") or "").strip() or None

        lat_text = (elem.findtext("geoLat") or "").strip()
        lon_text = (elem.findtext("geoLong") or "").strip()
        lat_dd = parse_coord(lat_text, is_lat=True)
        lon_dd = parse_coord(lon_text, is_lat=False)

        if not code_id or lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        # GP'yi eşleştir
        gp_key = (ahp_code_id or "", fir_code_id or "", code_id, originator or "")
        gp = gp_index.get(gp_key, {}) if all([ahp_code_id, originator]) else {}

        # DME'yi eşleştir: vor_code_id boş + codeId eşleşme + originator eşleşme
        dme = {}
        dme_mid_matched = None
        for dme_mid, dme_rec in dme_records.items():
            if (
                not dme_rec.get("vor_code_id")
                and dme_rec.get("code_id") == code_id
                and dme_rec.get("created_by") == originator
            ):
                dme = dme_rec
                dme_mid_matched = dme_mid
                dme_consumed_by_ils.add(dme_mid)
                break

        # LOC base fields (prefix'li)
        loc_base = {
            "mid": (elem.findtext("mid") or "").strip() or None,
            "code_id": code_id,
            "ahp_code_id": ahp_code_id,
            "ahp_code_icao": ahp_code_icao,
            "rwy_desig": rwy_desig,
            "rdn_desig": rdn_desig,
            "freq": (elem.findtext("valFreq") or "").strip() or None,
            "uom_freq": (elem.findtext("uomFreq") or "").strip() or None,
            "mag_brg": (elem.findtext("valMagBrg") or "").strip() or None,
            "true_brg": (elem.findtext("valTrueBrg") or "").strip() or None,
            "course_width": (elem.findtext("valWidCourse") or "").strip() or None,
            "back_course": (elem.findtext("codeTypeUseBack") or "").strip() or None,
            "mag_var": (elem.findtext("valMagVar") or "").strip() or None,
            "mag_var_date": (elem.findtext("dateMagVar") or "").strip() or None,
            "elev": (elem.findtext("valElev") or "").strip() or None,
            "uom_dist_ver": (elem.findtext("uomDistVer") or "").strip() or None,
            "datum": (elem.findtext("codeDatum") or "").strip() or None,
            "crc": (elem.findtext("valCrc") or "").strip() or None,
            "work_hr": (elem.findtext("codeWorkHr") or "").strip() or None,
            "emission": (elem.findtext("codeEm") or "").strip() or None,
            "fir_code_id": fir_code_id,
            "geo_accuracy": (elem.findtext("valGeoAccuracy") or "").strip() or None,
            "uom_geo_accuracy": (elem.findtext("uomGeoAccuracy") or "").strip() or None,
            "geoid_undulation": (elem.findtext("valGeoidUndulation") or "").strip() or None,
            "vert_datum": (elem.findtext("txtVerDatum") or "").strip() or None,
            "dt_wef": (elem.findtext("dtWef") or "").strip() or None,
            "dt_com": (elem.findtext("dtCom") or "").strip() or None,
            "created_by": originator,
            "rmk": (elem.findtext("txtRmk") or "").strip() or None,
            "work_hr_rmk": (elem.findtext("txtRmkWorkHr") or "").strip() or None,
            "lat_text": lat_text,
            "lon_text": lon_text,
            "lat_dd": lat_dd,
            "lon_dd": lon_dd,
            "source": "xml",
        }
        loc_row = prefix_row(loc_base, "loc_")

        # GP alt alanları (loc_row'a flattened)
        for prefix, gp_field in [
            ("gp_mid", "mid"),
            ("gp_lat_text", "lat_text"),
            ("gp_lon_text", "lon_text"),
            ("gp_lat_dd", "lat_dd"),
            ("gp_lon_dd", "lon_dd"),
            ("gp_freq", "freq"),
            ("gp_slope", "slope"),
            ("gp_elev", "elev"),
            ("gp_rdh", "rdh"),
            ("gp_uom_rdh", "uom_rdh"),
            ("gp_datum", "datum"),
            ("gp_emission", "emission"),
            ("gp_crc", "crc"),
            ("gp_dt_wef", "dt_wef"),
        ]:
            loc_row[prefix] = gp.get(gp_field) if gp else None
        loc_row["gp_joined"] = 1 if gp else 0

        # DME alt alanları (loc_row'a flattened)
        for prefix, dme_field in [
            ("dme_mid", "mid"),
            ("dme_code_id", "code_id"),
            ("dme_lat_text", "lat_text"),
            ("dme_lon_text", "lon_text"),
            ("dme_lat_dd", "lat_dd"),
            ("dme_lon_dd", "lon_dd"),
            ("dme_channel", "channel"),
            ("dme_ghost_freq", "ghost_freq"),
            ("dme_uom_ghost_freq", "uom_ghost_freq"),
            ("dme_datum", "datum"),
            ("dme_work_hr", "work_hr"),
            ("dme_dt_wef", "dt_wef"),
        ]:
            loc_row[prefix] = dme.get(dme_field) if dme else None
        loc_row["dme_joined"] = 1 if dme else 0

        loc_rows.append(loc_row)

        # GP ayrı katman kaydı (kendi konumuyla + LOC referansı)
        if gp:
            gp_row = prefix_row(gp, "gp_")
            gp_row.update(prefix_row(loc_base, "loc_"))
            gp_rows.append(gp_row)

        # DME ayrı katman kaydı (kendi konumuyla + LOC referansı)
        if dme:
            dme_row = prefix_row(dme, "dme_")
            dme_row.update(prefix_row(loc_base, "loc_"))
            ils_dme_rows.append(dme_row)

        elem.clear()

    print(
        f"  ILS-LOC okunan: {len(loc_rows)}, "
        f"GP eşleşmesi: {len(gp_rows)}, DME eşleşmesi: {len(ils_dme_rows)}"
    )
    return loc_rows, gp_rows, ils_dme_rows, dme_consumed_by_ils


def load_vor_records(
    xml_path: Path,
    dme_records: dict[str, dict[str, Any]],
    tacan_records: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], set[str], set[str]]:
    """VOR XML'i oku.
    - Önce TACAN eşleştir: TACAN'ı olan VOR → vortac_rows (DME eşleştirmesi yapılmaz)
    - TACAN'sız VOR → DME eşleştir:
        - DME'li VOR → vor_dme_rows
        - DME'siz VOR → vor_rows
    Returns: (vor_rows, vor_dme_rows, vortac_rows, dme_consumed, tacan_consumed)
    """
    vor_rows: list[dict[str, Any]] = []
    vor_dme_rows: list[dict[str, Any]] = []
    vortac_rows: list[dict[str, Any]] = []
    dme_consumed_by_vor: set[str] = set()
    tacan_consumed_by_vor: set[str] = set()

    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  VOR atlandı: {reason}")
        return vor_rows, vor_dme_rows, vortac_rows, dme_consumed_by_vor, tacan_consumed_by_vor

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue

        code_id = normalize_code(elem.findtext("codeId"))
        lat_text = (elem.findtext("geoLat") or "").strip()
        lon_text = (elem.findtext("geoLong") or "").strip()
        lat_dd = parse_coord(lat_text, is_lat=True)
        lon_dd = parse_coord(lon_text, is_lat=False)
        created_by = (elem.findtext("OrgCre/txtName") or "").strip() or None
        country = (elem.findtext("Org/txtName") or "").strip() or None

        if not code_id or lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        # Önce TACAN eşleştir
        # Not: country karşılaştırması yapılmıyor — VOR ve TACAN farklı org adları kullanabilir
        # (örn. VOR country="TURKIYE", TACAN country="DHMI TURKIYE")
        tacan = {}
        for tacan_mid, tacan_rec in tacan_records.items():
            if (
                tacan_rec.get("vor_code_id") == code_id
                and tacan_rec.get("created_by") == created_by
            ):
                tacan = tacan_rec
                tacan_consumed_by_vor.add(tacan_mid)
                break

        # VOR temel alanları (her iki layer için ortak)
        base = {
            "mid": (elem.findtext("mid") or "").strip() or None,
            "code_id": code_id,
            "name": (elem.findtext("txtName") or "").strip() or None,
            "code_type": (elem.findtext("codeType") or "").strip() or None,
            "freq": (elem.findtext("valFreq") or "").strip() or None,
            "uom_freq": (elem.findtext("uomFreq") or "").strip() or None,
            "north_ref": (elem.findtext("codeTypeNorth") or "").strip() or None,
            "declination": (elem.findtext("valDeclination") or "").strip() or None,
            "mag_var": (elem.findtext("valMagVar") or "").strip() or None,
            "mag_var_date": (elem.findtext("dateMagVar") or "").strip() or None,
            "emission": (elem.findtext("codeEm") or "").strip() or None,
            "datum": (elem.findtext("codeDatum") or "").strip() or None,
            "geo_accuracy": (elem.findtext("valGeoAccuracy") or "").strip() or None,
            "uom_geo_accuracy": (elem.findtext("uomGeoAccuracy") or "").strip() or None,
            "elev": (elem.findtext("valElev") or "").strip() or None,
            "uom_dist_ver": (elem.findtext("uomDistVer") or "").strip() or None,
            "elev_accuracy": (elem.findtext("valElevAccuracy") or "").strip() or None,
            "geoid_undulation": (elem.findtext("valGeoidUndulation") or "").strip() or None,
            "vert_datum": (elem.findtext("txtVerDatum") or "").strip() or None,
            "crc": (elem.findtext("valCrc") or "").strip() or None,
            "work_hr": (elem.findtext("codeWorkHr") or "").strip() or None,
            "work_hr_rmk": (elem.findtext("txtRmkWorkHr") or "").strip() or None,
            "country": country,
            "created_by": created_by,
            "dt_wef": (elem.findtext("dtWef") or "").strip() or None,
            "dt_com": (elem.findtext("dtCom") or "").strip() or None,
            "rmk": (elem.findtext("txtRmk") or "").strip() or None,
            "lat_text": lat_text,
            "lon_text": lon_text,
            "lat_dd": lat_dd,
            "lon_dd": lon_dd,
            "source": "xml",
        }

        if tacan:
            # VORTAC: VOR + TACAN alt alanları eklenir, DME eşleştirmesi yapılmaz
            row = prefix_row(base, "vor_")
            row.update(prefix_row(tacan, "tacan_"))
            vortac_rows.append(row)
        else:
            # TACAN yok → DME eşleştir
            # Not: country karşılaştırması yapılmıyor — VOR ve DME farklı org adları kullanabilir
            dme = {}
            for dme_mid, dme_rec in dme_records.items():
                if (
                    dme_rec.get("vor_code_id") == code_id
                    and dme_rec.get("created_by") == created_by
                ):
                    dme = dme_rec
                    dme_consumed_by_vor.add(dme_mid)
                    break

            if dme:
                # VOR/DME: VOR + DME alt alanları eklenir
                row = prefix_row(base, "vor_")
                row.update(prefix_row(dme, "dme_"))
                vor_dme_rows.append(row)
            else:
                # Saf VOR: sadece VOR alanları
                row = prefix_row(base, "vor_")
                vor_rows.append(row)

        elem.clear()

    total = len(vor_rows) + len(vor_dme_rows) + len(vortac_rows)
    print(
        f"  VOR okunan: {total} → "
        f"VOR={len(vor_rows)}, "
        f"VOR/DME={len(vor_dme_rows)} (DME eşleşmesi: {len(dme_consumed_by_vor)}), "
        f"VORTAC={len(vortac_rows)} (TACAN eşleşmesi: {len(tacan_consumed_by_vor)})"
    )
    return vor_rows, vor_dme_rows, vortac_rows, dme_consumed_by_vor, tacan_consumed_by_vor


def load_tailored_data(json_path: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, set[tuple[str, str]]]]:
    """Tailored JSON yükle: {"ils": [...], "vor": [...], "dme": [...], "tacan": [...]}
    Suppress bilgileri: {type: {(ident, originator), ...}}"""
    tailored_by_type: dict[str, list[dict[str, Any]]] = {
        "loc": [],
        "gp": [],
        "vor": [],
        "dme": [],
        "tacan": [],
    }
    suppress_by_type: dict[str, set[tuple[str, str]]] = {
        "loc": set(),
        "gp": set(),
        "vor": set(),
        "dme": set(),
        "tacan": set(),
    }

    if not json_path.exists():
        print(f"  Tailored veri dosyası bulunamadı: {json_path.name}")
        return tailored_by_type, suppress_by_type

    try:
        text = json_path.read_text(encoding="utf-8").strip()
        if not text:
            return tailored_by_type, suppress_by_type

        payload = json.loads(strip_jsonc_comments(text))
        if not isinstance(payload, list):
            print("  Tailored veri kökü dizi olmalıdır")
            return tailored_by_type, suppress_by_type

        for idx, entry in enumerate(payload, start=1):
            if not isinstance(entry, dict):
                print(f"  Tailored kayıt atlandı (#{idx}): dict değil")
                continue

            nav_type = entry.get("type", "").lower()
            if nav_type not in tailored_by_type:
                print(f"  Tailored kayıt atlandı (#{idx}): type={nav_type} geçersiz")
                continue

            suppress = entry.get("suppress", {})
            suppress_ident = suppress.get("ident")
            suppress_originator = suppress.get("originator")

            # Suppress işaretle
            if suppress_ident and suppress_originator:
                suppress_by_type[nav_type].add((suppress_ident.upper(), suppress_originator))

            # Giriş verisi ekle (meta anahtarları çıkar)
            record = {k: v for k, v in entry.items() if k not in ("suppress", "type")}
            record["source"] = "tailored"
            tailored_by_type[nav_type].append(record)

        print(
            f"  Tailored okunan: LOC={len(tailored_by_type['loc'])}, "
            f"GP={len(tailored_by_type['gp'])}, VOR={len(tailored_by_type['vor'])}, "
            f"DME={len(tailored_by_type['dme'])}, TACAN={len(tailored_by_type['tacan'])}"
        )
        return tailored_by_type, suppress_by_type

    except Exception as e:
        print(f"  Tailored veri parse hatası: {e}")
        return tailored_by_type, suppress_by_type


def apply_suppress(
    rows: list[dict[str, Any]],
    suppress_set: set[tuple[str, str]],
    code_id_field: str = "code_id",
    created_by_field: str = "created_by",
) -> list[dict[str, Any]]:
    """Suppress'e eşleşen kayıtları çıkar"""
    if not suppress_set:
        return rows

    filtered = []
    for row in rows:
        code_id = normalize_code(row.get(code_id_field))
        created_by = row.get(created_by_field)
        if (code_id, created_by) not in suppress_set:
            filtered.append(row)

    return filtered


def get_column_type(col_name: str) -> str:
    """Field adına göre SQL tipi belirle"""
    # REAL: koordinatlar, frekanslar, yükseklikler, açılar vb.
    real_patterns = [
        "lat_dd", "lon_dd", "lat_text", "lon_text",
        "_freq", "_elev", "_slope", "_rdh", "_declination",
        "_mag_var", "_geoid_undulation", "_crc", "_channel",
        "_ghost_freq", "_accuracy", "_height", "_distance",
        "_brg", "_bearing", "_width", "_angle",
    ]
    for pattern in real_patterns:
        if pattern in col_name:
            return "REAL"

    # INTEGER: joined flags
    if "_joined" in col_name:
        return "INTEGER"

    return "TEXT"


def load_frequency_pairing(csv_path: Path) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    """
    frequency-pairing.csv'den bidirectional lookup dicts oluştur.
    Döner: (channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel)

    CSV columns:
      0: DME channel number
      1: VHF frequency MHz
      11: GP Frequency MHz (sadece bazı channels için)
    """
    channel_to_vhf: dict[str, str] = {}
    vhf_to_channel: dict[str, str] = {}
    channel_to_gp: dict[str, str] = {}
    gp_to_channel: dict[str, str] = {}

    if not csv_path.exists():
        return channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            # Header satırını atla
            next(f, None)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) < 2:
                    continue
                channel = parts[0].strip().upper()
                vhf_raw = parts[1].strip()
                gp_raw = parts[11].strip() if len(parts) > 11 else ""

                # Normalize: "112.50" → "112.5", "108.00" → "108.0" (trailing zero strip)
                def norm_freq(s: str) -> str:
                    try:
                        return str(float(s))
                    except ValueError:
                        return s

                if channel and vhf_raw:
                    vhf_norm = norm_freq(vhf_raw)
                    channel_to_vhf[channel] = vhf_norm
                    vhf_to_channel[vhf_norm] = channel

                if channel and gp_raw:
                    gp_norm = norm_freq(gp_raw)
                    channel_to_gp[channel] = gp_norm
                    gp_to_channel[gp_norm] = channel
    except Exception as e:
        print(f"  Frequency pairing yükleme hatası: {e}")

    return channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel


def add_common_ident(
    rows: list[dict[str, Any]],
    ident_field: str,
    name_field: str | None = None,
    ident_fallback_field: str | None = None,
    name_fallback_field: str | None = None,
) -> list[dict[str, Any]]:
    """Her row'a 'ident' ve 'name' ortak alanlarını ekle."""
    for row in rows:
        ident = row.get(ident_field)
        if not ident and ident_fallback_field:
            ident = row.get(ident_fallback_field)
        row["ident"] = ident

        name = row.get(name_field) if name_field else None
        if not name and name_fallback_field:
            name = row.get(name_fallback_field)
        row["name"] = name
    return rows


def enrich_frequency_fields(
    rows: list[dict[str, Any]],
    channel_to_vhf: dict[str, str],
    vhf_to_channel: dict[str, str],
    channel_to_gp: dict[str, str],
    gp_to_channel: dict[str, str],
    primary_freq_field: str | None = None,
    primary_channel_field: str | None = None,
    is_gp: bool = False,
) -> list[dict[str, Any]]:
    """
    Rows'a standardize channelNo ve frequency alanları ekle.

    Parametreler:
    - primary_freq_field: frequency'nin primary kaynağı (örn. "loc_freq", "dme_freq", "gp_freq", "vor_freq")
    - primary_channel_field: channel'ın primary kaynağı (örn. "dme_channel", "tacan_channel")
    - is_gp: True ise GP lookup'larını (gp_to_channel) kullan, aksi takdirde VHF lookup'larını kullan

    Mantık:
    1. Primary freq varsa → frequency = primary_freq
    2. Primary channel varsa → channelNo = primary_channel
    3. Freq varsa ama channel yoksa → channel'ı lookup'tan doldur (is_gp ise gp_to_channel, aksi vhf_to_channel)
    4. Channel varsa ama freq yoksa → freq'i lookup'tan doldur (is_gp ise channel_to_gp, aksi channel_to_vhf)
    """
    enriched = []
    for row in rows:
        enriched_row = row.copy()

        freq_value: str | None = None
        channel_value: str | None = None

        if primary_freq_field:
            fr = enriched_row.get(primary_freq_field)
            if fr:
                raw = str(fr).strip()
                # Lookup dict'teki key'lerle eşleşmesi için normalize et
                try:
                    freq_value = str(float(raw))
                except ValueError:
                    freq_value = raw

        if primary_channel_field:
            ch = enriched_row.get(primary_channel_field)
            if ch:
                channel_value = str(ch).strip().upper()

        # Bidirectional lookup: eksik olanı doldur
        if is_gp:
            # GP katmanı: gp_to_channel lookup'u kullan
            if freq_value and not channel_value:
                looked_up_channel = gp_to_channel.get(freq_value)
                if looked_up_channel:
                    channel_value = looked_up_channel

            if channel_value and not freq_value:
                looked_up_freq = channel_to_gp.get(channel_value)
                if looked_up_freq:
                    freq_value = looked_up_freq
        else:
            # Diğer katmanlar: vhf_to_channel lookup'u kullan
            if freq_value and not channel_value:
                looked_up_channel = vhf_to_channel.get(freq_value)
                if looked_up_channel:
                    channel_value = looked_up_channel

            if channel_value and not freq_value:
                looked_up_freq = channel_to_vhf.get(channel_value)
                if looked_up_freq:
                    freq_value = looked_up_freq

        # Ortak alanları ekle
        enriched_row["channelNo"] = channel_value
        enriched_row["frequency"] = freq_value

        enriched.append(enriched_row)

    return enriched


def write_layer(
    con: sqlite3.Connection,
    table_name: str,
    rows: list[dict[str, Any]],
    lat_field: str = "lat_dd",
    lon_field: str = "lon_dd",
):
    """Katman yazma"""
    if not rows:
        return

    cur = con.cursor()

    # Sütunları belirle
    all_keys: set[str] = set()
    for row in rows:
        all_keys.update(row.keys())
    all_keys.discard("geom")

    columns = sorted(all_keys)
    col_defs = ", ".join(f'"{col}" {get_column_type(col)}' for col in columns)
    cur.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    cur.execute(f'CREATE TABLE "{table_name}" (fid INTEGER PRIMARY KEY AUTOINCREMENT, geom BLOB NOT NULL, {col_defs})')

    # Insert
    batch: list[tuple[object, ...]] = []
    xs: list[float] = []
    ys: list[float] = []

    for row in rows:
        lon_value = row.get(lon_field)
        lat_value = row.get(lat_field)
        if not isinstance(lon_value, (int, float, str)) or not isinstance(lat_value, (int, float, str)):
            continue

        try:
            lon = float(lon_value)
            lat = float(lat_value)
        except (ValueError, TypeError):
            continue

        xs.append(lon)
        ys.append(lat)

        values = [row.get(col) for col in columns]
        batch.append((gpkg_point_blob(lon, lat), *values))

    if not batch:
        print(f"  UYARI: {table_name} için geçerli geometri yok")
        return

    col_names = ", ".join(f'"{col}"' for col in columns)
    placeholders = ", ".join("?" for _ in range(len(columns) + 1))
    sql = f'INSERT INTO "{table_name}" (geom, {col_names}) VALUES ({placeholders})'
    cur.executemany(sql, batch)

    # GeoPackage metadata
    cur.execute(
        """
        INSERT OR REPLACE INTO gpkg_contents (
            table_name, data_type, identifier, description, last_change,
            min_x, min_y, max_x, max_y, srs_id
        ) VALUES (?, 'features', ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), ?, ?, ?, ?, 4326)
        """,
        (table_name, table_name, f"EAD-SDO {table_name}", min(xs), min(ys), max(xs), max(ys)),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO gpkg_geometry_columns (
            table_name, column_name, geometry_type_name, srs_id, z, m
        ) VALUES (?, 'geom', 'POINT', 4326, 0, 0)
        """,
        (table_name,),
    )
    cur.execute(
        "INSERT OR REPLACE INTO gpkg_ogr_contents (table_name, feature_count) VALUES (?, ?)",
        (table_name, len(batch)),
    )
    con.commit()
    print(f"  {table_name}: {len(batch)} kayıt yazıldı")


def main():
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")

    print("=" * 60)
    print("EAD-SDO Navaid GeoPackage Oluşturucu")
    print("=" * 60)

    # Kayıtları oku
    print("\n[1] XML dosyaları okunuyor...")
    dme_records = load_dme_records(DME_XML)
    tacan_records = load_tacan_records(TACAN_XML)
    gp_index = load_gp_records(ILS_GP_XML)
    loc_rows, gp_rows, ils_dme_rows, dme_consumed_ils = load_loc_records(ILS_LOC_XML, gp_index, dme_records)
    vor_rows, vor_dme_rows, vortac_rows, dme_consumed_vor, tacan_consumed_vor = load_vor_records(VOR_XML, dme_records, tacan_records)

    # Tailored verisi yükle
    print("\n[2] Tailored veri yükleniyor...")
    tailored_by_type, suppress_by_type = load_tailored_data(TAILORED_JSON)

    # Suppress uygula
    print("\n[3] Suppress uygulanıyor...")
    loc_rows = apply_suppress(loc_rows, suppress_by_type["loc"], "loc_code_id", "loc_created_by")
    vor_rows = apply_suppress(vor_rows, suppress_by_type["vor"], "vor_code_id", "vor_created_by")
    vor_dme_rows = apply_suppress(vor_dme_rows, suppress_by_type.get("vor_dme", set()), "vor_code_id", "vor_created_by")
    vortac_rows = apply_suppress(vortac_rows, suppress_by_type.get("vortac", set()), "vor_code_id", "vor_created_by")

    # Kalan DME / TACAN ekle
    print("\n[4] Kalan kayıtlar (standalone) toplanıyor...")
    dme_standalone = [
        prefix_row(dme_records[mid], "dme_")
        for mid in dme_records
        if mid not in dme_consumed_ils and mid not in dme_consumed_vor
    ]
    dme_standalone = apply_suppress(dme_standalone, suppress_by_type["dme"], "dme_code_id", "dme_created_by")

    tacan_standalone = [
        prefix_row(tacan_records[mid], "tacan_")
        for mid in tacan_records if mid not in tacan_consumed_vor
    ]
    tacan_standalone = apply_suppress(tacan_standalone, suppress_by_type["tacan"], "tacan_code_id", "tacan_created_by")

    # Tailored verisi ekle (eşleştirme motoru)
    print("\n[5] Tailored kayıtlar ekleniyor...")

    # Tailored LOC kayıtlarını loc_code_id'ye göre index'le (GP/DME join için)
    tailored_loc_index: dict[str, dict[str, Any]] = {
        r["loc_code_id"]: r
        for r in tailored_by_type["loc"]
        if r.get("loc_code_id")
    }

    # Build aşamasında tailored GP/DME ile eşleşmeleri tespit et
    tailored_gp_loc_ids: set[str] = {
        gp.get("loc_code_id")
        for gp in tailored_by_type["gp"]
        if gp.get("loc_code_id")
    }
    tailored_dme_loc_ids: set[str] = {
        dme.get("loc_code_id")
        for dme in tailored_by_type["dme"]
        if dme.get("loc_code_id")
    }

    # LOC → loc_rows (doğrudan) + joined bayraklarını set et
    for loc_rec in tailored_by_type["loc"]:
        loc_id = loc_rec.get("loc_code_id")
        loc_rec["gp_joined"] = 1 if loc_id in tailored_gp_loc_ids else 0
        loc_rec["dme_joined"] = 1 if loc_id in tailored_dme_loc_ids else 0
    loc_rows.extend(tailored_by_type["loc"])

    # GP → karşılık gelen tailored LOC alanlarını merge et, sonra gp_rows'a ekle
    for gp_rec in tailored_by_type["gp"]:
        loc_id = gp_rec.get("loc_code_id")
        if loc_id and loc_id in tailored_loc_index:
            merged = {**tailored_loc_index[loc_id], **gp_rec}  # GP alanları öncelikli
        else:
            merged = gp_rec
        merged["gp_joined"] = 1  # ✅ Tailored GP için joined bayrağını set et
        gp_rows.append(merged)

    tacan_standalone.extend(tailored_by_type["tacan"])

    # VOR + DME eşleştirme: vor_code_id üzerinden join, yoksa ayrı katmanlara
    t_dme_by_vor: dict[str, dict[str, Any]] = {}   # vor_code_id → dme record
    t_dme_to_ils: list[dict[str, Any]] = []         # dme with loc_code_id → ils_dme
    t_dme_standalone: list[dict[str, Any]] = []     # bağımsız dme

    for dme_rec in tailored_by_type["dme"]:
        vor_id = dme_rec.get("vor_code_id") or dme_rec.get("dme_vor_code_id")
        loc_id = dme_rec.get("loc_code_id")
        if vor_id:
            t_dme_by_vor[vor_id] = dme_rec
        elif loc_id:
            dme_rec["dme_joined"] = 1  # ✅ Tailored DME/ILS için joined bayrağını set et
            if loc_id in tailored_loc_index:
                t_dme_to_ils.append({**tailored_loc_index[loc_id], **dme_rec})
            else:
                t_dme_to_ils.append(dme_rec)
        else:
            t_dme_standalone.append(dme_rec)

    for vor_rec in tailored_by_type["vor"]:
        code_id = vor_rec.get("vor_code_id")
        if code_id and code_id in t_dme_by_vor:
            row = {**vor_rec, **t_dme_by_vor.pop(code_id)}
            vor_dme_rows.append(row)
        else:
            vor_rows.append(vor_rec)

    # vor_code_id'si olan ama eşleşmeyen tailored DME'ler → standalone
    t_dme_standalone.extend(t_dme_by_vor.values())

    ils_dme_rows.extend(t_dme_to_ils)
    dme_standalone.extend(t_dme_standalone)

    # Frequency pairing yükle
    print("\n[5.5] Frequency pairing yükleniyor...")
    channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel = load_frequency_pairing(FREQUENCY_PAIRING_CSV)

    # Frequency alanları ekle (enrich) — her katman için standardize
    print("\n[5.6] Frequency alanları ekleniyor...")
    # ILS-LOC: frequency = loc_freq, channelNo = loc_freq'ten hesaplanan
    loc_rows = enrich_frequency_fields(loc_rows, channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel, primary_freq_field="loc_freq", primary_channel_field=None, is_gp=False)
    # ILS-GP: frequency = gp_freq, channelNo = gp_freq'ten hesaplanan (GP lookup)
    gp_rows = enrich_frequency_fields(gp_rows, channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel, primary_freq_field="gp_freq", primary_channel_field=None, is_gp=True)
    # ILS-DME: kendi dme_channel ve dme_ghost_freq'i, eksik olanı lookup'tan
    ils_dme_rows = enrich_frequency_fields(ils_dme_rows, channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel, primary_freq_field="dme_ghost_freq", primary_channel_field="dme_channel", is_gp=False)
    # VOR: frequency = vor_freq, channelNo = vor_freq'ten hesaplanan
    vor_rows = enrich_frequency_fields(vor_rows, channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel, primary_freq_field="vor_freq", primary_channel_field=None, is_gp=False)
    # VOR-DME: frequency = vor_freq, channelNo = vor_freq'ten hesaplanan
    vor_dme_rows = enrich_frequency_fields(vor_dme_rows, channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel, primary_freq_field="vor_freq", primary_channel_field=None, is_gp=False)
    # VORTAC: kendi tacan_channel'ı, frequency = tacan_channel'dan hesaplanan
    vortac_rows = enrich_frequency_fields(vortac_rows, channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel, primary_freq_field=None, primary_channel_field="tacan_channel", is_gp=False)
    # DME (standalone): kendi dme_channel ve dme_ghost_freq'i, eksik olanı lookup'tan
    dme_standalone = enrich_frequency_fields(dme_standalone, channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel, primary_freq_field="dme_ghost_freq", primary_channel_field="dme_channel", is_gp=False)
    # TACAN (standalone): kendi tacan_channel'ı, frequency = tacan_channel'dan hesaplanan
    tacan_standalone = enrich_frequency_fields(tacan_standalone, channel_to_vhf, vhf_to_channel, channel_to_gp, gp_to_channel, primary_freq_field=None, primary_channel_field="tacan_channel", is_gp=False)

    print("\n[5.7] Ortak ident/name alanları ekleniyor...")
    loc_rows        = add_common_ident(loc_rows,        "loc_code_id",   name_field=None)
    gp_rows         = add_common_ident(gp_rows,         "loc_code_id",   name_field=None)
    ils_dme_rows    = add_common_ident(ils_dme_rows,    "dme_code_id",   name_field=None)
    vor_rows        = add_common_ident(vor_rows,        "vor_code_id",   name_field="vor_name")
    vor_dme_rows    = add_common_ident(vor_dme_rows,    "vor_code_id",   name_field="vor_name")
    vortac_rows     = add_common_ident(vortac_rows,     "vor_code_id",   name_field="vor_name",
                                       ident_fallback_field="tacan_code_id",
                                       name_fallback_field="tacan_name")
    dme_standalone  = add_common_ident(dme_standalone,  "dme_code_id",   name_field="dme_name")
    tacan_standalone = add_common_ident(tacan_standalone, "tacan_code_id", name_field="tacan_name")

    print("\n[5.8] Ortak type alanı ekleniyor...")
    for row in loc_rows:        row["type"] = "LOC"
    for row in gp_rows:         row["type"] = "GP"
    for row in ils_dme_rows:    row["type"] = "DME"
    for row in vor_rows:        row["type"] = "VOR"
    for row in vor_dme_rows:    row["type"] = "VOR DME"
    for row in vortac_rows:     row["type"] = "VORTAC"
    for row in dme_standalone:  row["type"] = "DME"
    for row in tacan_standalone: row["type"] = "TACAN"

    # GeoPackage yazma
    print("\n[6] GeoPackage yazılıyor...")
    if OUTPUT_GPKG.exists():
        try:
            OUTPUT_GPKG.unlink()
        except PermissionError:
            pass  # Dosya başka bir işlem tarafından kullanılıyorsa, üzerine yaz

    with sqlite3.connect(OUTPUT_GPKG) as con:
        create_base_gpkg(con)
        write_layer(con, ILS_LOC_TABLE, loc_rows, lat_field="loc_lat_dd", lon_field="loc_lon_dd")
        write_layer(con, ILS_GP_TABLE, gp_rows, lat_field="gp_lat_dd", lon_field="gp_lon_dd")
        write_layer(con, ILS_DME_TABLE, ils_dme_rows, lat_field="dme_lat_dd", lon_field="dme_lon_dd")
        write_layer(con, VOR_TABLE, vor_rows, lat_field="vor_lat_dd", lon_field="vor_lon_dd")
        write_layer(con, VOR_DME_TABLE, vor_dme_rows, lat_field="vor_lat_dd", lon_field="vor_lon_dd")
        write_layer(con, VORTAC_TABLE, vortac_rows, lat_field="vor_lat_dd", lon_field="vor_lon_dd")
        write_layer(con, DME_TABLE, dme_standalone, lat_field="dme_lat_dd", lon_field="dme_lon_dd")
        write_layer(con, TACAN_TABLE, tacan_standalone, lat_field="tacan_lat_dd", lon_field="tacan_lon_dd")

    # Create indexes on all columns for all tables
    print("[8] Indexler oluşturuluyor…")
    all_tables = [
        ILS_LOC_TABLE, ILS_GP_TABLE, ILS_DME_TABLE,
        VOR_TABLE, VOR_DME_TABLE, VORTAC_TABLE,
        DME_TABLE, TACAN_TABLE
    ]

    with sqlite3.connect(OUTPUT_GPKG) as con:
        cur = con.cursor()
        total_indexes = 0

        for table_name in all_tables:
            # Sütunları oku
            cur.execute(f"PRAGMA table_info({table_name})")
            columns = cur.fetchall()

            if not columns:
                continue

            index_count = 0
            for col in columns:
                col_name = col[1]
                # geom ve fid sütunlarını atla (zaten index var)
                if col_name in ("geom", "fid"):
                    continue

                idx_name = f"idx_{table_name}_{col_name}"
                try:
                    cur.execute(f"CREATE INDEX {idx_name} ON {table_name}({col_name})")
                    index_count += 1
                except sqlite3.OperationalError as e:
                    if "already exists" not in str(e):
                        pass  # Hataları sessizce yoksay

            if index_count > 0:
                print(f"  {table_name:<15}: {index_count} index")
                total_indexes += index_count

        con.commit()
        print(f"  Toplam: {total_indexes} index oluşturuldu")

    size_mb = OUTPUT_GPKG.stat().st_size / 1024 / 1024
    print("\n" + "=" * 60)
    print(f"Tamamlandi: {OUTPUT_GPKG.name} ({size_mb:.1f} MB)")
    print(f"  ILS-LOC: {len(loc_rows)} kayit")
    print(f"  ILS-GP:  {len(gp_rows)} kayit")
    print(f"  ILS-DME: {len(ils_dme_rows)} kayit")
    print(f"  VOR:     {len(vor_rows)} kayit")
    print(f"  VOR/DME: {len(vor_dme_rows)} kayit")
    print(f"  VORTAC:  {len(vortac_rows)} kayit")
    print(f"  DME (standalone): {len(dme_standalone)} kayit")
    print(f"  TACAN (standalone): {len(tacan_standalone)} kayit")
    print("QGIS'te dogrudan acilabilir.")
    print("=" * 60)


if __name__ == "__main__":
    main()
