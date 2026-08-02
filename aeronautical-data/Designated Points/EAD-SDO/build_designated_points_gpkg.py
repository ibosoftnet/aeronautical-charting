"""
EAD-SDO Designated Point (DP) veri dosyalarını (3 regional) birleştirir,
QGIS uyumlu spatial GeoPackage üretir. Tailored (manuel) veri desteği dahil.
Tüm sütunlarda index oluşturur (dp_coord hariç) - query performansı için optimize edilmiş.

Provenance: her kayıtta data_provider/data_originator/data_effectivity sütunları bulunur
(eski created_by/source sütunlarının yerine geçer).
  - XML (EAD-SDO) kayıtları: data_provider/data_effectivity data.json'dan, data_originator
    ham kayıttaki OrgCre/txtName'den okunur.
  - Tailored kayıtlar: data_provider her zaman "Ibosoft AIS"; data_originator ve
    data_effectivity kayıt bazında tailored-designated-points.jsonc'de girilir.
    data_effectivity, dosyanın kök objesindeki _effectivity_keys sözlüğü üzerinden bir
    anahtar (örn. "eff_trnc") olarak da girilebilir, bu durumda gerçek değere çözümlenir.
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
OUTPUT_GPKG = BASE_DIR / "designated_points.gpkg"

# XML kaynakları (3 regional file)
DP_NE_XML = BASE_DIR / "dp-ne.xml"
DP_NW_XML = BASE_DIR / "dp-nw.xml"
DP_SE_XML = BASE_DIR / "dp-se.xml"
TAILORED_JSON = BASE_DIR / "tailored-designated-points.jsonc"
DATA_JSON = BASE_DIR / "data.json"
META_KEYS = ("data_provider", "data_effectivity")

# GeoPackage katmanları — code_type'a göre ayrı
LAYER_TYPES: list[str] = [
    "ICAO", "ADHP", "COORD", "CNF", "DESIGNED",
    "MTR", "TERMINAL", "BRG_DIST", "OTHER",
]

def table_name_for(code_type: str) -> str:
    """code_type → GeoPackage tablo adı (örn. 'ICAO' → 'dp_icao')"""
    ct = (code_type or "OTHER").strip().upper()
    # Bilinen tipler dışındaki her şey OTHER'a gider
    if ct not in LAYER_TYPES:
        ct = "OTHER"
    return f"dp_{ct.lower()}"


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


def load_source_meta(path: Path) -> dict[str, str]:
    """data.json'dan data_provider/data_effectivity oku (data_originator ham
    kayıttaki OrgCre/txtName'den ayrı ayrı türetilir, burada değil)."""
    meta = {k: "" for k in META_KEYS}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for k in META_KEYS:
            meta[k] = data.get(k, "") or ""
    return meta


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


def load_dp_records(xml_path: Path, meta: dict[str, str]) -> list[dict[str, Any]]:
    """DP XML'i oku"""
    records: list[dict[str, Any]] = []
    valid, reason = looks_like_xml(xml_path)
    if not valid:
        print(f"  DP atlandı: {reason}")
        return records

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "Record":
            continue

        code_id = normalize_code(elem.findtext("codeId"))
        code_type = normalize_code(elem.findtext("codeType"))
        name = (elem.findtext("txtName") or "").strip() or None
        originator = (elem.findtext("OrgCre/txtName") or "").strip() or None

        lat_text = (elem.findtext("geoLat") or "").strip()
        lon_text = (elem.findtext("geoLong") or "").strip()
        lat_dd = parse_coord(lat_text, is_lat=True)
        lon_dd = parse_coord(lon_text, is_lat=False)

        if not code_id or lat_dd is None or lon_dd is None:
            elem.clear()
            continue

        records.append({
            "mid": (elem.findtext("mid") or "").strip() or None,
            "code_id": code_id,
            "code_type": code_type,
            "name": name,
            "datum": (elem.findtext("codeDatum") or "").strip() or None,
            "lat_text": lat_text,
            "lon_text": lon_text,
            "lat_dd": lat_dd,
            "lon_dd": lon_dd,
            "dt_wef": (elem.findtext("dtWef") or "").strip() or None,
            "data_provider": meta["data_provider"],
            "data_originator": originator,
            "data_effectivity": meta["data_effectivity"],
        })

        elem.clear()

    return records


def load_tailored_data(json_path: Path) -> tuple[list[dict[str, Any]], set[tuple[str, str]]]:
    """Tailored veri yükle ve suppress set oluştur.

    Kök yapı hem eski (bare list) hem yeni ({"_effectivity_keys": {...}, "points": [...]})
    formatını destekler.
    """
    tailored: list[dict[str, Any]] = []
    suppress_set: set[tuple[str, str]] = set()

    if not json_path.exists():
        return tailored, suppress_set

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            text = f.read()
        text_clean = strip_jsonc_comments(text)
        data = json.loads(text_clean)

        if isinstance(data, dict):
            eff_keys = data.get("_effectivity_keys", {}) or {}
            entries = data.get("points", [])
        elif isinstance(data, list):
            eff_keys = {}
            entries = data
        else:
            return tailored, suppress_set

        if not isinstance(entries, list):
            return tailored, suppress_set

        for item in entries:
            if not isinstance(item, dict):
                continue

            # Suppress kaydını işle
            suppress = item.get("suppress", {})
            if isinstance(suppress, dict) and suppress.get("code_id") and suppress.get("data_originator"):
                code_id = normalize_code(suppress.get("code_id"))
                data_originator = suppress.get("data_originator")
                if code_id and data_originator:
                    suppress_set.add((code_id, data_originator))

            # Tailored kaydını ekle (suppress boş değilse override, boşsa sadece ekle)
            if all(k in item for k in ["code_id"]):
                data_effectivity = item.get("data_effectivity")
                if data_effectivity in eff_keys:
                    data_effectivity = eff_keys[data_effectivity]

                tailored_row = {
                    "mid": item.get("mid"),
                    "code_id": normalize_code(item.get("code_id")),
                    "code_type": item.get("code_type"),
                    "name": item.get("name"),
                    "datum": item.get("datum"),
                    "lat_dd": item.get("lat_dd"),
                    "lon_dd": item.get("lon_dd"),
                    "dt_wef": item.get("dt_wef"),
                    "data_provider": "Ibosoft AIS",
                    "data_originator": item.get("data_originator"),
                    "data_effectivity": data_effectivity,
                }
                tailored.append(tailored_row)

        print(
            f"  Tailored okunan: {len(tailored)}, suppress set size: {len(suppress_set)}"
        )
        return tailored, suppress_set

    except Exception as e:
        print(f"  Tailored veri parse hatası: {e}")
        return tailored, suppress_set


def apply_suppress(
    rows: list[dict[str, Any]],
    suppress_set: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Suppress'e eşleşen kayıtları çıkar"""
    if not suppress_set:
        return rows

    filtered = []
    for row in rows:
        code_id = normalize_code(row.get("code_id"))
        data_originator = row.get("data_originator")
        if (code_id, data_originator) not in suppress_set:
            filtered.append(row)

    return filtered


def get_column_type(col_name: str) -> str:
    """Field adına göre SQL tipi belirle"""
    # REAL: koordinatlar, yükseklikler vb.
    real_patterns = [
        "lat_dd", "lon_dd", "lat_text", "lon_text",
    ]
    for pattern in real_patterns:
        if pattern in col_name:
            return "REAL"

    return "TEXT"


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
    print("EAD-SDO Designated Points GeoPackage Oluşturucu")
    print("=" * 60)

    meta = load_source_meta(DATA_JSON)

    # Kayıtları oku (3 regional file)
    print("\n[1] XML dosyaları okunuyor...")
    dp_ne = load_dp_records(DP_NE_XML, meta)
    dp_nw = load_dp_records(DP_NW_XML, meta)
    dp_se = load_dp_records(DP_SE_XML, meta)

    total_loaded = len(dp_ne) + len(dp_nw) + len(dp_se)
    print(f"  NE: {len(dp_ne)}, NW: {len(dp_nw)}, SE: {len(dp_se)} (Toplam: {total_loaded})")

    # Tüm DP'leri birleştir
    dp_rows = dp_ne + dp_nw + dp_se

    # Tailored verisi yükle
    print("\n[2] Tailored veri yükleniyor...")
    tailored_data, suppress_set = load_tailored_data(TAILORED_JSON)

    # Suppress uygula
    print("\n[3] Suppress uygulanıyor...")
    dp_rows = apply_suppress(dp_rows, suppress_set)

    # Tailored verisi ekle
    print("\n[4] Tailored kayıtlar ekleniyor...")
    dp_rows.extend(tailored_data)

    # Tipe göre grupla
    print("\n[5] Kayıtlar tipe göre gruplanıyor...")
    by_type: dict[str, list[dict[str, Any]]] = {ct: [] for ct in LAYER_TYPES}
    for row in dp_rows:
        ct = (row.get("code_type") or "OTHER").strip().upper()
        if ct not in by_type:
            ct = "OTHER"
        by_type[ct].append(row)
    for ct in LAYER_TYPES:
        print(f"  {ct:<12}: {len(by_type[ct])} kayit")

    # GeoPackage yazma
    print("\n[6] GeoPackage yazılıyor...")
    if OUTPUT_GPKG.exists():
        try:
            OUTPUT_GPKG.unlink()
        except PermissionError:
            pass  # Dosya başka bir işlem tarafından kullanılıyorsa, üzerine yaz

    with sqlite3.connect(OUTPUT_GPKG) as con:
        create_base_gpkg(con)
        for ct in LAYER_TYPES:
            rows = by_type[ct]
            if not rows:
                continue
            write_layer(con, table_name_for(ct), rows, lat_field="lat_dd", lon_field="lon_dd")

    # Create indexes on all columns (except dp_coord)
    print("\n[7] Indexler oluşturuluyor (dp_coord hariç)...")
    with sqlite3.connect(OUTPUT_GPKG) as con:
        cur = con.cursor()
        total_indexes = 0

        for ct in LAYER_TYPES:
            table_name = table_name_for(ct)

            # dp_coord tablosunu atla
            if table_name == "dp_coord":
                print(f"  {table_name}: SKIPPED")
                continue

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
                        print(f"    [warn] {col_name}: {e}")

            if index_count > 0:
                print(f"  {table_name}: {index_count} index oluşturuldu")
                total_indexes += index_count

        con.commit()
        print(f"  Toplam: {total_indexes} index oluşturuldu")

    size_mb = OUTPUT_GPKG.stat().st_size / 1024 / 1024
    print("\n" + "=" * 60)
    print(f"Tamamlandi: {OUTPUT_GPKG.name} ({size_mb:.1f} MB)")
    print(f"  Toplam: {len(dp_rows)} kayit, {sum(1 for ct in LAYER_TYPES if by_type[ct])} katman")
    print("QGIS'te dogrudan acilabilir.")
    print("=" * 60)


if __name__ == "__main__":
    main()
