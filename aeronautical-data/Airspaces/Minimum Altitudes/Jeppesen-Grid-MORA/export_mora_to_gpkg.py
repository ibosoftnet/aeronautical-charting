"""
Jeppesen `mora_grid` BLOB -> GeoPackage (1-degree polygon grid)

Input : aeronautical-data/Jeppesen Data/jeppesen.sqlite  (mora_grid table)
Output: temporary-files/mora-grid-export/mora_grid.gpkg
        Layer 'grid_mora': 63,600 polygon features (no-data hücreler atlanmis)
            Attributes:
                fid           INTEGER PK
                mora_ft       INTEGER MORA in feet  (= raw uint16 * 100)
"""
import os, sqlite3, struct
from shapely.geometry import Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"d:/ibosoft/aeronautical-charting/aeronautical-data/Jeppesen Data/jeppesen.sqlite"
DST = os.path.join(HERE, "grid_mora.gpkg")

# ------------ 1) Read & decode the BLOB ------------
sc = sqlite3.connect(SRC)
cols, rows, blob = sc.execute(
    "SELECT lonx_columns, laty_rows, geometry FROM mora_grid"
).fetchone()
sc.close()

magic, version = struct.unpack(">II", blob[:8])
assert magic == 0xA5B44CDB, f"Unexpected magic {magic:#x}"
assert version == 1, f"Unexpected version {version}"

payload = blob[8:]
vals = struct.unpack(f">{cols*rows}H", payload)
assert cols == 360 and rows == 180

# ------------ 2) Helper: GeoPackage binary geometry ------------
def gpkg_geom(wkb: bytes, srs_id: int = 4326) -> bytes:
    """Wrap standard WKB in a GeoPackage Binary header.
    Minimal header: magic 'GP', version=0, flags=0x01 (LE, no envelope), srs_id.
    """
    header = b"GP" + bytes([0, 0x01]) + struct.pack("<i", srs_id)
    return header + wkb

# ------------ 3) Create empty GeoPackage ------------
if os.path.exists(DST):
    os.remove(DST)

gpkg = sqlite3.connect(DST)
gpkg.executescript("""
PRAGMA application_id = 1196444487;   -- 'GPKG' = 0x47504B47
PRAGMA user_version   = 10300;        -- GeoPackage 1.3

CREATE TABLE gpkg_spatial_ref_sys (
    srs_name                 TEXT    NOT NULL,
    srs_id                   INTEGER NOT NULL PRIMARY KEY,
    organization             TEXT    NOT NULL,
    organization_coordsys_id INTEGER NOT NULL,
    definition               TEXT    NOT NULL,
    description              TEXT
);

CREATE TABLE gpkg_contents (
    table_name  TEXT    NOT NULL PRIMARY KEY,
    data_type   TEXT    NOT NULL,
    identifier  TEXT    UNIQUE,
    description TEXT    DEFAULT '',
    last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    min_x       DOUBLE,
    min_y       DOUBLE,
    max_x       DOUBLE,
    max_y       DOUBLE,
    srs_id      INTEGER,
    CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
);

CREATE TABLE gpkg_geometry_columns (
    table_name         TEXT    NOT NULL,
    column_name        TEXT    NOT NULL,
    geometry_type_name TEXT    NOT NULL,
    srs_id             INTEGER NOT NULL,
    z                  TINYINT NOT NULL,
    m                  TINYINT NOT NULL,
    CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),
    CONSTRAINT uk_gc_table_name UNIQUE (table_name),
    CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
    CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id)
);
""")

# Mandatory SRS rows + EPSG:4326
gpkg.executemany(
    "INSERT INTO gpkg_spatial_ref_sys VALUES (?,?,?,?,?,?)",
    [
        ("Undefined cartesian SRS",  -1, "NONE", -1, "undefined", "undefined cartesian coordinate reference system"),
        ("Undefined geographic SRS",  0, "NONE",  0, "undefined", "undefined geographic coordinate reference system"),
        ("WGS 84",                4326, "EPSG", 4326,
         'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],'
         'AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
         'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]',
         "WGS 84"),
    ],
)

# ------------ 4) Feature table ------------
gpkg.executescript("""
CREATE TABLE grid_mora (
    fid     INTEGER PRIMARY KEY AUTOINCREMENT,
    geom    BLOB,
    mora_ft INTEGER
);
CREATE VIRTUAL TABLE rtree_grid_mora_geom USING rtree(id, minx, maxx, miny, maxy);
""")

gpkg.execute(
    "INSERT INTO gpkg_contents (table_name, data_type, identifier, description, "
    "min_x, min_y, max_x, max_y, srs_id) VALUES (?,?,?,?,?,?,?,?,?)",
    ("grid_mora", "features", "grid_mora",
     "Jeppesen Grid MORA, 1deg x 1deg polygons, value in feet",
     -180.0, -90.0, 180.0, 90.0, 4326),
)
gpkg.execute(
    "INSERT INTO gpkg_geometry_columns VALUES (?,?,?,?,?,?)",
    ("grid_mora", "geom", "POLYGON", 4326, 0, 0),
)

# ------------ 5) Insert features ------------
NODATA = 0xFFFF
skipped = 0
inserted = 0

gpkg.commit()
cur = gpkg.cursor()
for r in range(rows):
    lat_max = 90 - r
    lat_min = lat_max - 1
    for c in range(cols):
        raw = vals[r * cols + c]
        if raw == NODATA:
            skipped += 1
            continue
        lon_min = -180 + c
        lon_max = lon_min + 1
        poly = Polygon([
            (lon_min, lat_min),
            (lon_max, lat_min),
            (lon_max, lat_max),
            (lon_min, lat_max),
            (lon_min, lat_min),
        ])
        geom = gpkg_geom(poly.wkb, srs_id=4326)
        ft = raw * 100
        cur.execute(
            "INSERT INTO grid_mora (geom, mora_ft) VALUES (?, ?)",
            (geom, ft),
        )
        fid = cur.lastrowid
        cur.execute(
            "INSERT INTO rtree_grid_mora_geom(id, minx, maxx, miny, maxy) VALUES (?,?,?,?,?)",
            (fid, lon_min, lon_max, lat_min, lat_max),
        )
        inserted += 1
gpkg.commit()
gpkg.close()

print(f"Wrote {DST}")
print(f"  inserted: {inserted}  skipped (no-data): {skipped}")
print(f"  size: {os.path.getsize(DST):,} bytes")
