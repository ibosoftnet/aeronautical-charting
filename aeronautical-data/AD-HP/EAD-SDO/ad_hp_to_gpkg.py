"""
ad_hp_to_gpkg.py
EAD-SDO AD-HP XML dosyasını GeoPackage (non-spatial attributes tablosu) olarak dönüştürür.
"""

import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

INPUT_XML = Path(__file__).parent / "ad-hp.xml"
OUTPUT_GPKG = Path(__file__).parent / "ad-hp.gpkg"
TABLE_NAME = "ad_hp"
GPKG_DATA_TYPE = "aspatial"  # Eski QGIS/GDAL sürümleriyle daha uyumlu
GPKG_ASPATIAL_EXTENSION = "http://gdal.org/geopackage_aspatial.html"

# Her Record altındaki section -> field prefix eşlemesi
SECTION_PREFIXES = {
    "Ahp": "ahp",
    "Aul": "aul",
    "Aut": "aut",
    "Fcs": "fcs",
    "Acs": "acs",
    "OrgCre": "org",
}

# Root-level alanlar (section içinde değil)
ROOT_FIELDS = {"dtWef", "dtCom", "mid"}


def flatten_record(record: ET.Element) -> dict:
    row = {}
    for child in record:
        if child.tag in SECTION_PREFIXES:
            prefix = SECTION_PREFIXES[child.tag]
            for field in child:
                col = f"{prefix}_{field.tag}"
                val = (field.text or "").strip() or None
                # Aynı section'dan birden fazla değer varsa birleştir (nadiren olur)
                if col in row and row[col] and val:
                    row[col] = row[col] + "; " + val
                else:
                    row[col] = val
        elif child.tag in ROOT_FIELDS:
            row[child.tag] = (child.text or "").strip() or None
    return row


def collect_columns(xml_path: Path) -> list[str]:
    """Tüm kayıtları tarayarak kolon setini belirle."""
    print("Kolon şeması taranıyor...")
    cols_ordered = []
    cols_seen = set()
    # Önce sabit sıralamayı ekle
    priority = [
        "ahp_codeId", "ahp_codeIcao",
        "mid",
        "aul_codeUsageLimitation", "aul_codeWorkHr", "aul_txtRmkWorkHr",
        "aut_codeTimeRef", "aut_dateValidWef", "aut_dateValidTil",
        "aut_codeDay", "aut_codeDayTil", "aut_timeWef", "aut_timeTil",
        "aut_codeEventWef", "aut_timeRelEventWef",
        "aut_codeEventTil", "aut_timeRelEventTil", "aut_codeCombTil",
        "fcs_codeType", "fcs_codeRule", "fcs_codeMil",
        "fcs_codeOrigin", "fcs_codePurpose", "fcs_codeStatus",
        "fcs_codeCapability",
        "acs_codeIcaoAcftType", "acs_codeEngineNo", "acs_codeTypeEngine",
        "org_txtName",
        "dtWef", "dtCom",
    ]
    for col in priority:
        cols_ordered.append(col)
        cols_seen.add(col)

    # Dosyayı tararken görülen diğer kolonları ekle
    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag == "Record":
            row = flatten_record(elem)
            for k in row:
                if k not in cols_seen:
                    cols_ordered.append(k)
                    cols_seen.add(k)
            elem.clear()

    return cols_ordered


def create_gpkg(gpkg_path: Path, table: str, columns: list[str]):
    con = sqlite3.connect(gpkg_path)
    cur = con.cursor()

    # GeoPackage metadata tabloları + eski QGIS/GDAL için aspatial uyumluluk kaydı
    cur.executescript("""
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
    """)

    # Data tablosunu oluştur
    col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
    cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" (fid INTEGER PRIMARY KEY AUTOINCREMENT, {col_defs})')

    # QGIS/GDAL'ın aspatial tabloyu listeleyebilmesi için içerik kaydı
    cur.execute("""
        INSERT OR REPLACE INTO gpkg_contents (table_name, data_type, identifier, description, last_change, srs_id)
        VALUES (?, ?, ?, 'EAD-SDO AD-HP Usage Limitations', strftime('%Y-%m-%dT%H:%M:%fZ','now'), NULL)
    """, (table, GPKG_DATA_TYPE, table))

    cur.execute("""
        INSERT OR IGNORE INTO gpkg_extensions (table_name, column_name, extension_name, definition, scope)
        VALUES (NULL, NULL, 'gdal_aspatial', ?, 'read-write')
    """, (GPKG_ASPATIAL_EXTENSION,))

    cur.execute("""
        INSERT OR REPLACE INTO gpkg_ogr_contents (table_name, feature_count)
        VALUES (?, 0)
    """, (table,))

    con.commit()
    return con


def insert_records(con: sqlite3.Connection, xml_path: Path, table: str, columns: list[str]):
    cur = con.cursor()
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(f'"{c}"' for c in columns)
    sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'

    batch = []
    BATCH_SIZE = 500
    total = 0

    print("Veriler aktarılıyor...")
    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag == "Record":
            row = flatten_record(elem)
            values = tuple(row.get(c) for c in columns)
            batch.append(values)
            elem.clear()
            if len(batch) >= BATCH_SIZE:
                cur.executemany(sql, batch)
                con.commit()
                total += len(batch)
                batch.clear()
                print(f"  {total} kayıt aktarıldı...", end="\r")

    if batch:
        cur.executemany(sql, batch)
        con.commit()
        total += len(batch)

    print(f"\nToplam {total} kayıt yazıldı.")
    return total


def finalize_gpkg(con: sqlite3.Connection, table: str, total: int):
    cur = con.cursor()
    cur.execute(
        """
        UPDATE gpkg_contents
        SET last_change = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE table_name = ?
        """,
        (table,),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO gpkg_ogr_contents (table_name, feature_count)
        VALUES (?, ?)
        """,
        (table, total),
    )
    con.commit()


def validate_gpkg(gpkg_path: Path):
    with sqlite3.connect(gpkg_path) as con:
        cur = con.cursor()
        tables = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required_tables = {
            'gpkg_spatial_ref_sys',
            'gpkg_contents',
            'gpkg_geometry_columns',
            'gpkg_extensions',
            TABLE_NAME,
        }
        missing = required_tables - tables
        if missing:
            raise RuntimeError(f"GeoPackage eksik sistem tabloları içeriyor: {sorted(missing)}")

        contents = cur.execute(
            "SELECT table_name, data_type FROM gpkg_contents WHERE table_name = ?",
            (TABLE_NAME,),
        ).fetchone()
        if not contents:
            raise RuntimeError(f"{TABLE_NAME} gpkg_contents içinde kayıtlı değil")

        print(f"GeoPackage doğrulandı: {contents[0]} ({contents[1]})")


def main():
    if not INPUT_XML.exists():
        print(f"HATA: Girdi dosyası bulunamadı: {INPUT_XML}")
        sys.exit(1)

    if OUTPUT_GPKG.exists():
        OUTPUT_GPKG.unlink()
        print(f"Mevcut dosya silindi: {OUTPUT_GPKG.name}")

    columns = collect_columns(INPUT_XML)
    print(f"  {len(columns)} kolon bulundu.")

    con = create_gpkg(OUTPUT_GPKG, TABLE_NAME, columns)
    total = insert_records(con, INPUT_XML, TABLE_NAME, columns)
    finalize_gpkg(con, TABLE_NAME, total)
    con.close()
    validate_gpkg(OUTPUT_GPKG)

    size_mb = OUTPUT_GPKG.stat().st_size / 1024 / 1024
    print(f"\nTamamlandi: {OUTPUT_GPKG.name} ({size_mb:.1f} MB)")
    print(f"Tablo: {TABLE_NAME}, Kayıt: {total}, Kolon: {len(columns)}")
    print("Not: Bu çıktı geometrisiz (aspatial) bir tablodur; QGIS'te Browser/DB Manager altında tablo olarak görünür, doğrudan harita üzerine çizilmez.")


if __name__ == "__main__":
    main()
