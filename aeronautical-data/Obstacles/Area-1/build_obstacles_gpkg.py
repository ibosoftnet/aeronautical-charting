"""
AIXM 5.1 VerticalStructure (engel) verilerini Area-1 altindaki tum
ulke/alan klasorlerinden toplayip tek bir spatial GeoPackage'a yazar.
"""

from __future__ import annotations

import struct
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_GPKG = BASE_DIR / "obstacles.gpkg"
TABLE_NAME = "obstacles"

GML = "{http://www.opengis.net/gml/3.2}"
AIXM = "{http://www.aixm.aero/schema/5.1}"
VERTICAL_STRUCTURE_TAG = f"{AIXM}VerticalStructure"

COLUMNS: list[tuple[str, str]] = [
    ("identifier", "TEXT"),
    ("interpretation", "TEXT"),
    ("sequenceNumber", "INTEGER"),
    ("correctionNumber", "INTEGER"),
    ("beginPosition", "TEXT"),
    ("featureLifetime_beginPosition", "TEXT"),
    ("name", "TEXT"),
    ("type", "TEXT"),
    ("lighted", "TEXT"),
    ("group", "TEXT"),
    ("verticalExtent", "INTEGER"),
    ("verticalExtent_uom", "TEXT"),
    ("part_type", "TEXT"),
    ("designator", "TEXT"),
    ("elevation", "INTEGER"),
    ("elevation_uom", "TEXT"),
    ("colour", "TEXT"),
    ("country", "TEXT"),
    ("source_file", "TEXT"),
]


def parse_pos(text: str | None) -> tuple[float, float] | None:
    """gml:pos 'lat lon' (WGS84) -> (lon, lat) for WKB x/y order."""
    if not text:
        return None
    parts = text.split()
    if len(parts) != 2:
        return None
    try:
        lat, lon = float(parts[0]), float(parts[1])
    except ValueError:
        return None
    return lon, lat


def to_int(text: str | None) -> int | None:
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def child_text(elem: ET.Element | None, path: str) -> str | None:
    if elem is None:
        return None
    found = elem.find(path)
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def gpkg_point_blob(lon: float, lat: float, srs_id: int = 4326) -> bytes:
    header = b"GP" + bytes([0, 1]) + struct.pack("<i", srs_id)
    wkb = struct.pack("<BI2d", 1, 1, lon, lat)
    return header + wkb


def find_country_dirs(area_dir: Path) -> list[Path]:
    return sorted(p for p in area_dir.iterdir() if p.is_dir())


def find_xml_files(country_dir: Path) -> list[Path]:
    return sorted(country_dir.glob("*.xml"))


def looks_like_aixm(path: Path) -> bool:
    try:
        head = path.read_bytes()[:1000].decode("utf-8", errors="ignore")
    except OSError:
        return False
    return "AIXMBasicMessage" in head or "aixm.aero/schema" in head


def iter_structures(xml_path: Path):
    # Caller must extract data INSIDE the loop body before requesting the
    # next item: elem.clear() runs on resume, after the yielded element is
    # already in the caller's hands but before it asks for the next one.
    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag == VERTICAL_STRUCTURE_TAG:
            yield elem
            elem.clear()


def extract_part_rows(
    structure: ET.Element, country: str, source_file: str
) -> tuple[list[dict[str, Any]], int]:
    identifier = child_text(structure, f"{GML}identifier")
    time_slice = structure.find(f"{AIXM}timeSlice/{AIXM}VerticalStructureTimeSlice")
    if identifier is None or time_slice is None:
        return [], 0

    common = {
        "identifier": identifier,
        "interpretation": child_text(time_slice, f"{AIXM}interpretation"),
        "sequenceNumber": to_int(child_text(time_slice, f"{AIXM}sequenceNumber")),
        "correctionNumber": to_int(child_text(time_slice, f"{AIXM}correctionNumber")),
        "beginPosition": child_text(
            time_slice, f"{GML}validTime/{GML}TimePeriod/{GML}beginPosition"
        ),
        "featureLifetime_beginPosition": child_text(
            time_slice, f"{AIXM}featureLifetime/{GML}TimePeriod/{GML}beginPosition"
        ),
        "name": child_text(time_slice, f"{AIXM}name"),
        "type": child_text(time_slice, f"{AIXM}type"),
        "lighted": child_text(time_slice, f"{AIXM}lighted"),
        "group": child_text(time_slice, f"{AIXM}group"),
        "country": country,
        "source_file": source_file,
    }

    rows: list[dict[str, Any]] = []
    skipped = 0

    for part_wrapper in time_slice.findall(f"{AIXM}part"):
        part = part_wrapper.find(f"{AIXM}VerticalStructurePart")
        if part is None:
            skipped += 1
            continue

        point = part.find(f"{AIXM}horizontalProjection_location/{AIXM}ElevatedPoint")
        coords = parse_pos(child_text(point, f"{GML}pos")) if point is not None else None
        if coords is None:
            skipped += 1
            continue
        lon, lat = coords

        vertical_extent_elem = part.find(f"{AIXM}verticalExtent")
        elevation_elem = point.find(f"{AIXM}elevation")

        colours: list[str] = []
        for light_wrapper in part.findall(f"{AIXM}lighting"):
            colour = child_text(light_wrapper.find(f"{AIXM}LightElement"), f"{AIXM}colour")
            if colour:
                colours.append(colour)

        row = dict(common)
        row.update(
            {
                "verticalExtent": to_int(
                    vertical_extent_elem.text if vertical_extent_elem is not None else None
                ),
                "verticalExtent_uom": (
                    vertical_extent_elem.get("uom") if vertical_extent_elem is not None else None
                ),
                "part_type": child_text(part, f"{AIXM}type"),
                "designator": child_text(part, f"{AIXM}designator"),
                "elevation": to_int(
                    elevation_elem.text if elevation_elem is not None else None
                ),
                "elevation_uom": (
                    elevation_elem.get("uom") if elevation_elem is not None else None
                ),
                "colour": ",".join(colours) if colours else None,
                "lon": lon,
                "lat": lat,
            }
        )
        rows.append(row)

    return rows, skipped


def create_base_gpkg(con: sqlite3.Connection) -> None:
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


def create_rtree_index(
    con: sqlite3.Connection, table: str, geom_col: str = "geom", id_col: str = "fid"
) -> None:
    """GeoPackage spec Annex L RTree extension: virtual table + 6 maintenance
    triggers + gpkg_extensions registration. The ST_* functions referenced by
    the triggers are provided by the reader's own engine (QGIS/GDAL/mod_spatialite)
    when this file is opened later - not by this script, which populates the
    rtree table directly during the initial bulk load instead of relying on
    the triggers to fire under plain stdlib sqlite3."""
    cur = con.cursor()
    cur.execute(
        f'CREATE VIRTUAL TABLE "rtree_{table}_{geom_col}" USING rtree(id, minx, maxx, miny, maxy)'
    )
    cur.execute(
        """
        INSERT INTO gpkg_extensions (table_name, column_name, extension_name, definition, scope)
        VALUES (?, ?, 'gpkg_rtree_index', 'http://www.geopackage.org/spec/#extension_rtree', 'write-only')
        """,
        (table, geom_col),
    )
    cur.executescript(
        f"""
        CREATE TRIGGER "rtree_{table}_{geom_col}_insert" AFTER INSERT ON "{table}"
          WHEN (new."{geom_col}" NOT NULL AND NOT ST_IsEmpty(NEW."{geom_col}"))
        BEGIN
          INSERT OR REPLACE INTO "rtree_{table}_{geom_col}" VALUES (
            NEW."{id_col}",
            ST_MinX(NEW."{geom_col}"), ST_MaxX(NEW."{geom_col}"),
            ST_MinY(NEW."{geom_col}"), ST_MaxY(NEW."{geom_col}")
          );
        END;

        CREATE TRIGGER "rtree_{table}_{geom_col}_update1" AFTER UPDATE OF "{geom_col}" ON "{table}"
          WHEN OLD."{id_col}" = NEW."{id_col}" AND
               (NEW."{geom_col}" NOTNULL AND NOT ST_IsEmpty(NEW."{geom_col}"))
        BEGIN
          INSERT OR REPLACE INTO "rtree_{table}_{geom_col}" VALUES (
            NEW."{id_col}",
            ST_MinX(NEW."{geom_col}"), ST_MaxX(NEW."{geom_col}"),
            ST_MinY(NEW."{geom_col}"), ST_MaxY(NEW."{geom_col}")
          );
        END;

        CREATE TRIGGER "rtree_{table}_{geom_col}_update2" AFTER UPDATE OF "{geom_col}" ON "{table}"
          WHEN OLD."{id_col}" = NEW."{id_col}" AND
               (NEW."{geom_col}" ISNULL OR ST_IsEmpty(NEW."{geom_col}"))
        BEGIN
          DELETE FROM "rtree_{table}_{geom_col}" WHERE id = OLD."{id_col}";
        END;

        CREATE TRIGGER "rtree_{table}_{geom_col}_update3" AFTER UPDATE ON "{table}"
          WHEN OLD."{id_col}" != NEW."{id_col}" AND
               (NEW."{geom_col}" NOTNULL AND NOT ST_IsEmpty(NEW."{geom_col}"))
        BEGIN
          DELETE FROM "rtree_{table}_{geom_col}" WHERE id = OLD."{id_col}";
          INSERT OR REPLACE INTO "rtree_{table}_{geom_col}" VALUES (
            NEW."{id_col}",
            ST_MinX(NEW."{geom_col}"), ST_MaxX(NEW."{geom_col}"),
            ST_MinY(NEW."{geom_col}"), ST_MaxY(NEW."{geom_col}")
          );
        END;

        CREATE TRIGGER "rtree_{table}_{geom_col}_update4" AFTER UPDATE ON "{table}"
          WHEN OLD."{id_col}" != NEW."{id_col}" AND
               (NEW."{geom_col}" ISNULL OR ST_IsEmpty(NEW."{geom_col}"))
        BEGIN
          DELETE FROM "rtree_{table}_{geom_col}" WHERE id = OLD."{id_col}";
        END;

        CREATE TRIGGER "rtree_{table}_{geom_col}_delete" AFTER DELETE ON "{table}"
          WHEN old."{geom_col}" NOT NULL
        BEGIN
          DELETE FROM "rtree_{table}_{geom_col}" WHERE id = OLD."{id_col}";
        END;
        """
    )
    con.commit()


def populate_rtree_index(
    con: sqlite3.Connection,
    table: str,
    rows_with_coords: list[tuple[int, float, float]],
    geom_col: str = "geom",
) -> None:
    cur = con.cursor()
    cur.executemany(
        f'INSERT INTO "rtree_{table}_{geom_col}" (id, minx, maxx, miny, maxy) VALUES (?, ?, ?, ?, ?)',
        [(fid, lon, lon, lat, lat) for fid, lon, lat in rows_with_coords],
    )
    con.commit()


def write_layer(con: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    cur = con.cursor()
    col_defs = ", ".join(f'"{name}" {sql_type}' for name, sql_type in COLUMNS)
    cur.execute(f'DROP TABLE IF EXISTS "{table}"')
    cur.execute(
        f'CREATE TABLE "{table}" (fid INTEGER PRIMARY KEY AUTOINCREMENT, geom BLOB NOT NULL, {col_defs})'
    )

    col_names = ", ".join(f'"{name}"' for name, _ in COLUMNS)
    placeholders = ", ".join("?" for _ in COLUMNS)
    insert_sql = f'INSERT INTO "{table}" (geom, {col_names}) VALUES (?, {placeholders})'

    xs: list[float] = []
    ys: list[float] = []
    rtree_rows: list[tuple[int, float, float]] = []

    for row in rows:
        lon, lat = row["lon"], row["lat"]
        xs.append(lon)
        ys.append(lat)
        values = [row.get(name) for name, _ in COLUMNS]
        cur.execute(insert_sql, (gpkg_point_blob(lon, lat), *values))
        rtree_rows.append((cur.lastrowid, lon, lat))

    con.commit()

    create_rtree_index(con, table)
    populate_rtree_index(con, table, rtree_rows)

    cur.execute(
        """
        INSERT OR REPLACE INTO gpkg_contents (
            table_name, data_type, identifier, description, last_change,
            min_x, min_y, max_x, max_y, srs_id
        ) VALUES (?, 'features', ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), ?, ?, ?, ?, 4326)
        """,
        (table, table, "AIXM 5.1 VerticalStructure obstacles", min(xs), min(ys), max(xs), max(ys)),
    )
    cur.execute(
        """
        INSERT OR REPLACE INTO gpkg_geometry_columns (
            table_name, column_name, geometry_type_name, srs_id, z, m
        ) VALUES (?, 'geom', 'POINT', 4326, 0, 0)
        """,
        (table,),
    )
    cur.execute(
        "INSERT OR REPLACE INTO gpkg_ogr_contents (table_name, feature_count) VALUES (?, ?)",
        (table, len(rows)),
    )
    con.commit()


def main() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")

    print("=" * 60)
    print("AIXM Obstacle (VerticalStructure) GeoPackage Olusturucu")
    print("=" * 60)

    country_dirs = find_country_dirs(BASE_DIR)
    if not country_dirs:
        print(f"HATA: {BASE_DIR} altinda ulke/alan klasoru bulunamadi.")
        sys.exit(1)

    all_rows: list[dict[str, Any]] = []
    total_structures = 0
    total_skipped = 0

    for country_dir in country_dirs:
        country = country_dir.name
        for xml_path in find_xml_files(country_dir):
            if not looks_like_aixm(xml_path):
                print(f"  Atlandi (AIXM degil): {xml_path.relative_to(BASE_DIR)}")
                continue

            file_structures = 0
            file_rows = 0
            file_skipped = 0
            for structure in iter_structures(xml_path):
                file_structures += 1
                rows, skipped = extract_part_rows(structure, country, xml_path.name)
                all_rows.extend(rows)
                file_rows += len(rows)
                file_skipped += skipped

            print(
                f"  {xml_path.relative_to(BASE_DIR)}: "
                f"{file_structures} structure, {file_rows} satir, {file_skipped} atlandi"
            )
            total_structures += file_structures
            total_skipped += file_skipped

    print(
        f"\nToplam: {total_structures} structure, {len(all_rows)} satir, "
        f"{total_skipped} atlandi (geometri yok)"
    )

    if not all_rows:
        print("HATA: yazilacak satir yok.")
        sys.exit(1)

    if OUTPUT_GPKG.exists():
        try:
            OUTPUT_GPKG.unlink()
        except PermissionError:
            print(f"UYARI: {OUTPUT_GPKG.name} baska bir islem tarafindan kullaniliyor, uzerine yazilacak.")

    with sqlite3.connect(OUTPUT_GPKG) as con:
        create_base_gpkg(con)
        write_layer(con, TABLE_NAME, all_rows)

    size_mb = OUTPUT_GPKG.stat().st_size / 1024 / 1024
    print("\n" + "=" * 60)
    print(f"Tamamlandi: {OUTPUT_GPKG.name} ({size_mb:.1f} MB)")
    print(f"  Katman: {TABLE_NAME} ({len(all_rows)} kayit, spatial index ile)")
    print("QGIS'te dogrudan acilabilir.")
    print("=" * 60)


if __name__ == "__main__":
    main()
