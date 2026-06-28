"""
EAD-SDO AD/HP ARP bölge dosyalarını birleştirir, varsa usage verisiyle
kod bazında eşleştirir ve QGIS uyumlu spatial GeoPackage üretir.
Tüm sütunlarda index oluşturur - query performansı için optimize edilmiş.
"""

from __future__ import annotations

import json
import sqlite3
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_GPKG = BASE_DIR / "ad-hp.gpkg"
AIRPORTS_TABLE = "ad_hp_airports"
USAGE_TABLE = "ad_hp_usage"
USAGE_XML = BASE_DIR / "ad-hp-usage.xml"
TAILORED_DATA_FILE = BASE_DIR / "tailored-data.jsonc"
EXPORT_RAW_USAGE_TABLE = False  # False => QGIS'te yalnızca birleşik airport katmanı görünsün

ARP_SOURCES = [
    ("afr", BASE_DIR / "arp-afr.xml"),
    ("am-pac", BASE_DIR / "arp-am-pac.xml"),
    ("asi-aus", BASE_DIR / "arp-asi-aus.xml"),
    ("eur", BASE_DIR / "arp-eur.xml"),
]

SECTION_PREFIXES = {
    "Ahp": "ahp",
    "Aul": "aul",
    "Aut": "aut",
    "Fcs": "fcs",
    "Acs": "acs",
    "OrgCre": "org",
}
ROOT_FIELDS = {"dtWef", "dtCom", "mid"}

AIRPORT_FIELD_NAMES = [
    "source_region", "source_file", "join_key", "mid",
    "code_id", "code_icao", "code_iata", "code_type", "name", "city", "country",
    "datum", "lat_text", "lon_text", "lat_dd", "lon_dd", "dt_wef", "arp_work_hr",
    "sys_rmk", "created_by", "usage_mid", "usage_dt_wef", "usage_dt_com",
    "usage_limit", "usage_work_hr", "usage_work_hr_rmk", "usage_time_ref",
    "usage_valid_wef", "usage_valid_til", "usage_day", "usage_day_til",
    "usage_time_wef", "usage_time_til", "usage_event_wef", "usage_event_til",
    "usage_comb_til", "usage_type", "usage_rule", "usage_mil", "usage_origin",
    "usage_purpose", "usage_status", "usage_capability", "usage_aircraft_type",
    "usage_engine_no", "usage_engine_type", "usage_org_name", "usage_joined",
]
USAGE_VALUE_FIELDS = [name for name in AIRPORT_FIELD_NAMES if name.startswith("usage_") and name != "usage_joined"]


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

    # Decimal degrees (örn: 68.7218472N)
    if len(before) <= deg_len:
        try:
            return sign * float(text)
        except ValueError:
            return None

    # Degrees + decimal minutes (örn: 0951.2S / 16158.5E)
    if len(before) <= deg_len + 2:
        try:
            degrees = int(before[:deg_len])
            minutes = float(before[deg_len:] + (dot + after if dot else ""))
            return sign * (degrees + minutes / 60.0)
        except ValueError:
            return None

    # Degrees + minutes + decimal seconds (örn: 242116.635S)
    try:
        degrees = int(before[:deg_len])
        minutes = int(before[deg_len:deg_len + 2])
        seconds = float(before[deg_len + 2:] + (dot + after if dot else ""))
        return sign * (degrees + minutes / 60.0 + seconds / 3600.0)
    except ValueError:
        return None


def merge_value(existing: str | None, new_value: str | None) -> str | None:
    existing = (existing or "").strip()
    new_value = (new_value or "").strip()
    if not existing:
        return new_value or None
    if not new_value or new_value == existing:
        return existing

    existing_parts = [part.strip() for part in existing.split(" | ") if part.strip()]
    if new_value in existing_parts:
        return existing
    return existing + " | " + new_value


def flatten_usage_record(record: ET.Element) -> dict[str, str | None]:
    row: dict[str, str | None] = {}
    for child in record:
        if child.tag in SECTION_PREFIXES:
            prefix = SECTION_PREFIXES[child.tag]
            for field in child:
                col = f"{prefix}_{field.tag}"
                val = (field.text or "").strip() or None
                row[col] = merge_value(row.get(col), val)
        elif child.tag in ROOT_FIELDS:
            row[child.tag] = (child.text or "").strip() or None
    return row


def merge_rows(existing: dict[str, str | None], new_row: dict[str, str | None]) -> dict[str, str | None]:
    merged = dict(existing)
    for key, value in new_row.items():
        merged[key] = merge_value(merged.get(key), value)
    return merged


def load_usage_index(xml_path: Path) -> tuple[dict[str, dict[str, str | None]], list[dict[str, str | None]]]:
    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"Usage dosyası atlandı: {xml_path.name} ({reason})")
        return {}, []

    usage_by_code: dict[str, dict[str, str | None]] = {}
    raw_rows: list[dict[str, str | None]] = []

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue

        row = flatten_usage_record(elem)
        code = normalize_code(row.get("ahp_codeIcao") or row.get("ahp_codeId"))
        if code:
            raw_rows.append(row)
            if code in usage_by_code:
                usage_by_code[code] = merge_rows(usage_by_code[code], row)
            else:
                usage_by_code[code] = row
        elem.clear()

    print(f"Usage kaydı: {len(raw_rows)}")
    return usage_by_code, raw_rows


def build_usage_fields(usage: dict[str, str | None]) -> dict[str, str | int | None]:
    return {
        "usage_mid": usage.get("mid"),
        "usage_dt_wef": usage.get("dtWef"),
        "usage_dt_com": usage.get("dtCom"),
        "usage_limit": usage.get("aul_codeUsageLimitation"),
        "usage_work_hr": usage.get("aul_codeWorkHr"),
        "usage_work_hr_rmk": usage.get("aul_txtRmkWorkHr"),
        "usage_time_ref": usage.get("aut_codeTimeRef"),
        "usage_valid_wef": usage.get("aut_dateValidWef"),
        "usage_valid_til": usage.get("aut_dateValidTil"),
        "usage_day": usage.get("aut_codeDay"),
        "usage_day_til": usage.get("aut_codeDayTil"),
        "usage_time_wef": usage.get("aut_timeWef"),
        "usage_time_til": usage.get("aut_timeTil"),
        "usage_event_wef": usage.get("aut_codeEventWef"),
        "usage_event_til": usage.get("aut_codeEventTil"),
        "usage_comb_til": usage.get("aut_codeCombTil"),
        "usage_type": usage.get("fcs_codeType"),
        "usage_rule": usage.get("fcs_codeRule"),
        "usage_mil": usage.get("fcs_codeMil"),
        "usage_origin": usage.get("fcs_codeOrigin"),
        "usage_purpose": usage.get("fcs_codePurpose"),
        "usage_status": usage.get("fcs_codeStatus"),
        "usage_capability": usage.get("fcs_codeCapability"),
        "usage_aircraft_type": usage.get("acs_codeIcaoAcftType"),
        "usage_engine_no": usage.get("acs_codeEngineNo"),
        "usage_engine_type": usage.get("acs_codeTypeEngine"),
        "usage_org_name": usage.get("org_txtName"),
        "usage_joined": 1 if usage else 0,
    }


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


def apply_tailored_data(
    airport_rows: list[dict[str, str | float | int | None]],
    usage_by_code: dict[str, dict[str, str | None]],
    tailored_path: Path,
) -> list[dict[str, str | float | int | None]]:
    if not tailored_path.exists():
        return airport_rows

    raw_text = tailored_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        print(f"Tailored data dosyası boş: {tailored_path.name}")
        return airport_rows

    try:
        payload = json.loads(strip_jsonc_comments(raw_text))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Tailored data parse hatası ({tailored_path.name}): {exc}") from exc

    if isinstance(payload, list):
        entries = payload
    elif isinstance(payload, dict):
        entries = payload.get("airports", [])
    else:
        raise RuntimeError("Tailored data kökü liste veya {'airports': [...]} olmalıdır")

    if not isinstance(entries, list):
        raise RuntimeError("Tailored data içindeki 'airports' alanı liste olmalıdır")

    rows_by_key: dict[str, dict[str, str | float | int | None]] = {}
    ordered_keys: list[str] = []

    for row in airport_rows:
        key = normalize_code(str(row.get("join_key") or row.get("code_icao") or row.get("code_id") or ""))
        if not key:
            continue
        rows_by_key[key] = dict(row)
        ordered_keys.append(key)

    added = 0
    overridden = 0

    for idx, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            print(f"Tailored kayıt atlandı (#{idx}): nesne/dict değil")
            continue
        if entry.get("enabled", True) is False:
            continue

        join_key = normalize_code(
            str(entry.get("join_key") or entry.get("code_icao") or entry.get("code_id") or "")
        )
        if not join_key:
            print(f"Tailored kayıt atlandı (#{idx}): join_key/code_icao/code_id zorunlu")
            continue

        existing_row = rows_by_key.get(join_key)
        is_override = existing_row is not None

        # Tailored kayıtlar tam override gibi davranır:
        # mevcut kayıttan yalnızca geometriyi korumak için koordinatlar ödünç alınır.
        base: dict[str, str | float | int | None] = {field: None for field in AIRPORT_FIELD_NAMES}
        base["source_region"] = "tailored"
        base["source_file"] = tailored_path.name
        base["join_key"] = join_key
        base["code_id"] = join_key
        base["code_icao"] = join_key if len(join_key) == 4 else None

        if existing_row is not None:
            for coord_field in ("lat_dd", "lon_dd", "lat_text", "lon_text"):
                base[coord_field] = existing_row.get(coord_field)

        for key, value in entry.items():
            if key in {"enabled"} or key.startswith("_"):
                continue
            if key in AIRPORT_FIELD_NAMES or key == "join_key":
                base[key] = value

        for code_field in ("join_key", "code_id", "code_icao", "code_iata", "code_type"):
            value = base.get(code_field)
            if value is not None:
                base[code_field] = normalize_code(str(value))

        resolved_key = normalize_code(
            str(base.get("join_key") or base.get("code_icao") or base.get("code_id") or "")
        )
        if not resolved_key:
            raise RuntimeError(f"Tailored kayıt için geçerli join key üretilemedi: #{idx}")
        base["join_key"] = resolved_key

        lat_value = base.get("lat_dd")
        lon_value = base.get("lon_dd")
        lat_text_value = base.get("lat_text")
        lon_text_value = base.get("lon_text")
        lat_text = lat_text_value if isinstance(lat_text_value, str) else None
        lon_text = lon_text_value if isinstance(lon_text_value, str) else None
        try:
            lat_dd = float(lat_value) if lat_value not in (None, "") else parse_coord(lat_text, True)
            lon_dd = float(lon_value) if lon_value not in (None, "") else parse_coord(lon_text, False)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Tailored koordinat hatası ({resolved_key}): {exc}") from exc

        if lat_dd is None or lon_dd is None:
            raise RuntimeError(f"Tailored kayıt için lat_dd/lon_dd veya lat_text/lon_text gerekli: {resolved_key}")
        base["lat_dd"] = lat_dd
        base["lon_dd"] = lon_dd

        has_usage = any(base.get(field) not in (None, "") for field in USAGE_VALUE_FIELDS)
        base["usage_joined"] = 1 if has_usage else int(base.get("usage_joined") or 0)
        if not base.get("mid"):
            base["mid"] = f"TAILORED:{resolved_key}"
        if not base.get("source_region"):
            base["source_region"] = "tailored"
        if not base.get("source_file"):
            base["source_file"] = tailored_path.name

        rows_by_key[resolved_key] = base
        if resolved_key not in ordered_keys:
            ordered_keys.append(resolved_key)
            added += 1
        elif is_override:
            overridden += 1

    if added or overridden:
        print(f"Tailored kayıt işlendi: override={overridden}, yeni={added}")

    return [rows_by_key[key] for key in ordered_keys]


def iter_airport_rows(usage_by_code: dict[str, dict[str, str | None]]):
    skipped_sources: list[tuple[str, str]] = []

    for region, path in ARP_SOURCES:
        valid, reason = looks_like_xml(path)
        if not valid:
            skipped_sources.append((path.name, reason or "geçersiz içerik"))
            continue

        print(f"Kaynak işleniyor: {path.name}")
        for _, elem in ET.iterparse(path, events=("end",)):
            if elem.tag != "Record":
                continue

            code_icao = normalize_code(elem.findtext("codeIcao"))
            code_id = normalize_code(elem.findtext("codeId"))
            join_key = code_icao or code_id

            lat_text = (elem.findtext("geoLat") or "").strip()
            lon_text = (elem.findtext("geoLong") or "").strip()
            lat_dd = parse_coord(lat_text, is_lat=True)
            lon_dd = parse_coord(lon_text, is_lat=False)

            if not join_key or lat_dd is None or lon_dd is None:
                elem.clear()
                continue

            usage = usage_by_code.get(join_key, {})

            yield {
                "source_region": region,
                "source_file": path.name,
                "join_key": join_key,
                "mid": (elem.findtext("mid") or "").strip() or None,
                "code_id": code_id,
                "code_icao": code_icao,
                "code_iata": normalize_code(elem.findtext("codeIata")),
                "code_type": (elem.findtext("codeType") or "").strip() or None,
                "name": (elem.findtext("txtName") or "").strip() or None,
                "city": (elem.findtext("txtNameCitySer") or "").strip() or None,
                "country": (elem.findtext("Org/txtName") or "").strip() or None,
                "datum": (elem.findtext("codeDatum") or "").strip() or None,
                "lat_text": lat_text,
                "lon_text": lon_text,
                "lat_dd": lat_dd,
                "lon_dd": lon_dd,
                "dt_wef": (elem.findtext("dtWef") or "").strip() or None,
                "arp_work_hr": (elem.findtext("codeWorkHr") or "").strip() or None,
                "sys_rmk": (elem.findtext("sysRmk") or "").strip() or None,
                "created_by": (elem.findtext("OrgCre/txtName") or "").strip() or None,
                "usage_mid": usage.get("mid"),
                "usage_dt_wef": usage.get("dtWef"),
                "usage_dt_com": usage.get("dtCom"),
                "usage_limit": usage.get("aul_codeUsageLimitation"),
                "usage_work_hr": usage.get("aul_codeWorkHr"),
                "usage_work_hr_rmk": usage.get("aul_txtRmkWorkHr"),
                "usage_time_ref": usage.get("aut_codeTimeRef"),
                "usage_valid_wef": usage.get("aut_dateValidWef"),
                "usage_valid_til": usage.get("aut_dateValidTil"),
                "usage_day": usage.get("aut_codeDay"),
                "usage_day_til": usage.get("aut_codeDayTil"),
                "usage_time_wef": usage.get("aut_timeWef"),
                "usage_time_til": usage.get("aut_timeTil"),
                "usage_event_wef": usage.get("aut_codeEventWef"),
                "usage_event_til": usage.get("aut_codeEventTil"),
                "usage_comb_til": usage.get("aut_codeCombTil"),
                "usage_type": usage.get("fcs_codeType"),
                "usage_rule": usage.get("fcs_codeRule"),
                "usage_mil": usage.get("fcs_codeMil"),
                "usage_origin": usage.get("fcs_codeOrigin"),
                "usage_purpose": usage.get("fcs_codePurpose"),
                "usage_status": usage.get("fcs_codeStatus"),
                "usage_capability": usage.get("fcs_codeCapability"),
                "usage_aircraft_type": usage.get("acs_codeIcaoAcftType"),
                "usage_engine_no": usage.get("acs_codeEngineNo"),
                "usage_engine_type": usage.get("acs_codeTypeEngine"),
                "usage_org_name": usage.get("org_txtName"),
                "usage_joined": 1 if usage else 0,
            }
            elem.clear()

    if skipped_sources:
        print("Atlanan kaynaklar:")
        for name, reason in skipped_sources:
            print(f"  - {name}: {reason}")


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


def write_airports_layer(
    con: sqlite3.Connection,
    rows: list[dict[str, str | float | int | None]],
):
    cur = con.cursor()
    cur.execute(
        f'''
        CREATE TABLE "{AIRPORTS_TABLE}" (
            fid INTEGER PRIMARY KEY AUTOINCREMENT,
            geom BLOB NOT NULL,
            source_region TEXT,
            source_file TEXT,
            join_key TEXT,
            mid TEXT,
            code_id TEXT,
            code_icao TEXT,
            code_iata TEXT,
            code_type TEXT,
            name TEXT,
            city TEXT,
            country TEXT,
            datum TEXT,
            lat_text TEXT,
            lon_text TEXT,
            lat_dd REAL,
            lon_dd REAL,
            dt_wef TEXT,
            arp_work_hr TEXT,
            sys_rmk TEXT,
            created_by TEXT,
            usage_mid TEXT,
            usage_dt_wef TEXT,
            usage_dt_com TEXT,
            usage_limit TEXT,
            usage_work_hr TEXT,
            usage_work_hr_rmk TEXT,
            usage_time_ref TEXT,
            usage_valid_wef TEXT,
            usage_valid_til TEXT,
            usage_day TEXT,
            usage_day_til TEXT,
            usage_time_wef TEXT,
            usage_time_til TEXT,
            usage_event_wef TEXT,
            usage_event_til TEXT,
            usage_comb_til TEXT,
            usage_type TEXT,
            usage_rule TEXT,
            usage_mil TEXT,
            usage_origin TEXT,
            usage_purpose TEXT,
            usage_status TEXT,
            usage_capability TEXT,
            usage_aircraft_type TEXT,
            usage_engine_no TEXT,
            usage_engine_type TEXT,
            usage_org_name TEXT,
            usage_joined INTEGER DEFAULT 0
        )
        '''
    )

    field_names = AIRPORT_FIELD_NAMES
    column_sql = ", ".join(field_names)
    placeholder_sql = ", ".join("?" for _ in range(len(field_names) + 1))
    sql = f'INSERT INTO "{AIRPORTS_TABLE}" (geom, {column_sql}) VALUES ({placeholder_sql})'

    batch: list[tuple[object, ...]] = []
    xs: list[float] = []
    ys: list[float] = []

    for row in rows:
        lon_value = row.get("lon_dd")
        lat_value = row.get("lat_dd")
        if not isinstance(lon_value, (int, float, str)) or not isinstance(lat_value, (int, float, str)):
            continue

        lon = float(lon_value)
        lat = float(lat_value)
        xs.append(lon)
        ys.append(lat)
        values = [row.get(field) for field in field_names]
        batch.append((gpkg_point_blob(lon, lat), *values))

    if not batch:
        raise RuntimeError("GeoPackage için yazılacak geçerli geometri bulunamadı")

    cur.executemany(sql, batch)
    cur.execute(f'CREATE INDEX idx_{AIRPORTS_TABLE}_icao ON "{AIRPORTS_TABLE}" (code_icao)')

    cur.execute(
        """
        INSERT OR REPLACE INTO gpkg_contents (
            table_name, data_type, identifier, description, last_change,
            min_x, min_y, max_x, max_y, srs_id
        ) VALUES (?, 'features', ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), ?, ?, ?, ?, 4326)
        """,
        (
            AIRPORTS_TABLE,
            AIRPORTS_TABLE,
            'EAD-SDO merged airport positions enriched with usage data',
            min(xs), min(ys), max(xs), max(ys),
        ),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO gpkg_geometry_columns (
            table_name, column_name, geometry_type_name, srs_id, z, m
        ) VALUES (?, 'geom', 'POINT', 4326, 0, 0)
        """,
        (AIRPORTS_TABLE,),
    )
    cur.execute(
        "INSERT OR REPLACE INTO gpkg_ogr_contents (table_name, feature_count) VALUES (?, ?)",
        (AIRPORTS_TABLE, len(batch)),
    )
    con.commit()


def write_usage_table(con: sqlite3.Connection, usage_rows: list[dict[str, str | None]]):
    if not usage_rows:
        return

    cur = con.cursor()
    columns: list[str] = []
    seen: set[str] = set()
    for row in usage_rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(key)

    col_defs = ", ".join(f'"{col}" TEXT' for col in columns)
    cur.execute(f'CREATE TABLE "{USAGE_TABLE}" (fid INTEGER PRIMARY KEY AUTOINCREMENT, {col_defs})')

    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(f'"{col}"' for col in columns)
    sql = f'INSERT INTO "{USAGE_TABLE}" ({col_names}) VALUES ({placeholders})'
    batch = [tuple(row.get(col) for col in columns) for row in usage_rows]
    cur.executemany(sql, batch)

    cur.execute(
        """
        INSERT OR REPLACE INTO gpkg_contents (
            table_name, data_type, identifier, description, last_change, srs_id
        ) VALUES (?, 'aspatial', ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), NULL)
        """,
        (USAGE_TABLE, USAGE_TABLE, 'Raw usage records matched by ICAO/code where possible'),
    )
    cur.execute(
        """
        INSERT OR IGNORE INTO gpkg_extensions (table_name, column_name, extension_name, definition, scope)
        VALUES (NULL, NULL, 'gdal_aspatial', 'http://gdal.org/geopackage_aspatial.html', 'read-write')
        """
    )
    cur.execute(
        "INSERT OR REPLACE INTO gpkg_ogr_contents (table_name, feature_count) VALUES (?, ?)",
        (USAGE_TABLE, len(usage_rows)),
    )
    con.commit()


def validate_gpkg(path: Path):
    with sqlite3.connect(path) as con:
        cur = con.cursor()
        contents = cur.execute(
            "SELECT table_name, data_type FROM gpkg_contents ORDER BY table_name"
        ).fetchall()
        airport_count = cur.execute(f'SELECT COUNT(*) FROM "{AIRPORTS_TABLE}"').fetchone()[0]
        joined_count = cur.execute(
            f'SELECT COUNT(*) FROM "{AIRPORTS_TABLE}" WHERE usage_joined = 1'
        ).fetchone()[0]
        print("GeoPackage doğrulandı:")
        for table_name, data_type in contents:
            print(f"  - {table_name} ({data_type})")
        print(f"  - {AIRPORTS_TABLE} kayıt sayısı: {airport_count}")
        print(f"  - usage eşleşen kayıt sayısı: {joined_count}")


def main():
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")

    usage_by_code, usage_rows = load_usage_index(USAGE_XML)
    airport_rows = list(iter_airport_rows(usage_by_code))
    airport_rows = apply_tailored_data(airport_rows, usage_by_code, TAILORED_DATA_FILE)

    if not airport_rows:
        print("HATA: Geçerli havalimanı konum kaydı bulunamadı.")
        sys.exit(1)

    if OUTPUT_GPKG.exists():
        OUTPUT_GPKG.unlink()
        print(f"Mevcut dosya silindi: {OUTPUT_GPKG.name}")

    with sqlite3.connect(OUTPUT_GPKG) as con:
        create_base_gpkg(con)
        write_airports_layer(con, airport_rows)
        if EXPORT_RAW_USAGE_TABLE:
            write_usage_table(con, usage_rows)

    validate_gpkg(OUTPUT_GPKG)

    # Create indexes on all columns for query performance
    print("\nTüm sütunlara indexler oluşturuluyor…")
    with sqlite3.connect(OUTPUT_GPKG) as con:
        cur = con.cursor()
        index_count = 0
        for col_name in AIRPORT_FIELD_NAMES:
            idx_name = f"idx_ad_hp_{col_name}"
            try:
                cur.execute(f"CREATE INDEX {idx_name} ON {AIRPORTS_TABLE}({col_name})")
                index_count += 1
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    print(f"  [warn] {col_name}: {e}")
        con.commit()
        print(f"  ✓ {index_count} index oluşturuldu")

    size_mb = OUTPUT_GPKG.stat().st_size / 1024 / 1024
    print(f"\nTamamlandı: {OUTPUT_GPKG.name} ({size_mb:.1f} MB)")
    print(f"Toplam havalimanı/heliport: {len(airport_rows)}")
    print("QGIS'te `ad_hp_airports` katmanını doğrudan haritaya ekleyebilirsiniz.")


if __name__ == "__main__":
    main()
