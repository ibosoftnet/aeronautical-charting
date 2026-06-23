"""
Export fir-2021-ibosoft-tailored.json -> GeoPackage of FIR polygons.

Source : aeronautical-data/Airspaces/ICAO/FIR/fir-2021-ibosoft-tailored.json
Output : aeronautical-data/Airspaces/ICAO/FIR/fir-2021-ibosoft-tailored.gpkg
         Layer `fir` (GEOMETRY, EPSG:4326), RTree spatial index.
         Most features are POLYGON; some (antimeridian-crossing FIRs) are MULTIPOLYGON.
"""
import json
import os
import sqlite3
import struct

from shapely.geometry import shape

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "fir-2021-ibosoft-tailored.json")
DST = os.path.join(HERE, "fir-2021-ibosoft-tailored.gpkg")

# Properties columns to copy verbatim (geometry handled separately).
ATTR_COLS = [
    ("OBJECTID", "INTEGER"),
    ("OBJECTID_1", "INTEGER"),
    ("Id", "INTEGER"),
    ("FIRname", "TEXT"),
    ("REGION", "TEXT"),
    ("KIND", "TEXT"),
    ("UPPER", "TEXT"),
    ("LOWER", "TEXT"),
    ("ULC", "TEXT"),
    ("ICAOCODE", "TEXT"),
    ("RESP", "TEXT"),
    ("NOM_COMP", "TEXT"),
    ("HISTORIC", "TEXT"),
    ("REMARKS", "TEXT"),
    ("REMARKS2", "TEXT"),
    ("REMARKS3", "TEXT"),
    ("centlong", "REAL"),
    ("centlat", "REAL"),
    ("AREAsqkm", "REAL"),
    ("PERIMEkm", "REAL"),
    ("SUPP_REGIO", "TEXT"),
    ("PURE", "TEXT"),
    ("ET_ID", "INTEGER"),
    ("Shape_Leng", "REAL"),
    ("Shape__Area", "REAL"),
    ("Shape__Length", "REAL"),
]
ATTR_NAMES = [c[0] for c in ATTR_COLS]

WGS84_WKT = (
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,'
    'AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],'
    'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
    'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],'
    'AUTHORITY["EPSG","4326"]]'
)


def gpkg_geom(wkb: bytes, srs_id: int = 4326) -> bytes:
    """Wrap standard WKB in a minimal GeoPackage Binary header."""
    return b"GP" + bytes([0, 0x01]) + struct.pack("<i", srs_id) + wkb


def create_gpkg(path: str) -> sqlite3.Connection:
    if os.path.exists(path):
        os.remove(path)
    g = sqlite3.connect(path)
    g.executescript("""
        PRAGMA application_id = 1196444487;   -- 'GPKG'
        PRAGMA user_version   = 10300;        -- GeoPackage 1.3

        CREATE TABLE gpkg_spatial_ref_sys (
            srs_name TEXT NOT NULL,
            srs_id INTEGER NOT NULL PRIMARY KEY,
            organization TEXT NOT NULL,
            organization_coordsys_id INTEGER NOT NULL,
            definition TEXT NOT NULL,
            description TEXT
        );
        CREATE TABLE gpkg_contents (
            table_name TEXT NOT NULL PRIMARY KEY,
            data_type TEXT NOT NULL,
            identifier TEXT UNIQUE,
            description TEXT DEFAULT '',
            last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE,
            srs_id INTEGER,
            CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
        );
        CREATE TABLE gpkg_geometry_columns (
            table_name TEXT NOT NULL,
            column_name TEXT NOT NULL,
            geometry_type_name TEXT NOT NULL,
            srs_id INTEGER NOT NULL,
            z TINYINT NOT NULL,
            m TINYINT NOT NULL,
            CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),
            CONSTRAINT uk_gc_table_name UNIQUE (table_name),
            CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
            CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id)
        );
    """)
    g.executemany("INSERT INTO gpkg_spatial_ref_sys VALUES (?,?,?,?,?,?)", [
        ("Undefined cartesian SRS",  -1, "NONE", -1, "undefined", "undefined cartesian"),
        ("Undefined geographic SRS",  0, "NONE",  0, "undefined", "undefined geographic"),
        ("WGS 84", 4326, "EPSG", 4326, WGS84_WKT, "WGS 84"),
    ])
    attr_ddl = ",\n    ".join(f"{n} {t}" for n, t in ATTR_COLS)
    g.execute(f"""
        CREATE TABLE fir (
            fid INTEGER PRIMARY KEY AUTOINCREMENT,
            geom BLOB,
            {attr_ddl}
        )
    """)
    g.execute("CREATE VIRTUAL TABLE rtree_fir_geom USING rtree(id, minx, maxx, miny, maxy)")
    g.execute(
        "INSERT INTO gpkg_contents (table_name, data_type, identifier, description, "
        "min_x, min_y, max_x, max_y, srs_id) VALUES (?,?,?,?,?,?,?,?,?)",
        ("fir", "features", "fir",
         "ICAO World FIR boundaries, ibosoft-tailored (Turkey AIXM geometry + Tel Aviv ICAO code fix)",
         -180.0, -90.0, 180.0, 90.0, 4326),
    )
    g.execute("INSERT INTO gpkg_geometry_columns VALUES (?,?,?,?,?,?)",
              ("fir", "geom", "GEOMETRY", 4326, 0, 0))
    return g


def main():
    print(f"Source : {SRC}")
    print(f"Output : {DST}")
    with open(SRC, encoding="utf-8") as f:
        fc = json.load(f)

    gpkg = create_gpkg(DST)
    cur = gpkg.cursor()
    cols_sql = "geom, " + ", ".join(ATTR_NAMES)
    placeholders = ",".join("?" * (len(ATTR_NAMES) + 1))
    insert_sql = f"INSERT INTO fir ({cols_sql}) VALUES ({placeholders})"

    inserted = skipped = multipolygon_count = 0
    for feat in fc["features"]:
        geom_obj = shape(feat["geometry"])
        if not geom_obj.is_valid:
            geom_obj = geom_obj.buffer(0)
        if geom_obj.is_empty:
            skipped += 1
            continue
        if geom_obj.geom_type == "MultiPolygon":
            multipolygon_count += 1
        geom = gpkg_geom(geom_obj.wkb, 4326)
        props = feat["properties"]
        attrs = tuple(props.get(c) for c in ATTR_NAMES)
        cur.execute(insert_sql, (geom,) + attrs)
        fid = cur.lastrowid
        minx, miny, maxx, maxy = geom_obj.bounds
        cur.execute(
            "INSERT INTO rtree_fir_geom(id, minx, maxx, miny, maxy) VALUES (?,?,?,?,?)",
            (fid, minx, maxx, miny, maxy),
        )
        inserted += 1
    gpkg.commit()
    gpkg.close()
    print(f"  inserted={inserted}  skipped={skipped}  multipolygon={multipolygon_count}")
    print(f"Done. {DST}  ({os.path.getsize(DST):,} bytes)")


if __name__ == "__main__":
    main()
