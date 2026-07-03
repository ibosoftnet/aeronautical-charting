"""
Ortak GeoPackage şeması — tablo/rtree kurulumu, kayıt insert, index'ler.

Şema `AIXM_to_GeoPackage_Schema_Design.md`'ye göre. Kolon adları AIXM 5.2
attribute isimleriyle birebir (AIXM dışı: id, source, dataProvider, add_date).
"""
import os
import sqlite3
from datetime import datetime

from .geo import antimeridian_safe, gpkg_geom

TABLE = "airspaces"
GEOM_COL = "horizontalProjection"
RTREE = f"rtree_{TABLE}_{GEOM_COL}"

# AIXM dışı kolonlar hariç, kolon adları AIXM attribute isimleriyle birebir.
ATTR_COLS = [
    ("type", "TEXT"),
    ("designator", "TEXT"),
    ("name", "TEXT"),
    ("localType", "TEXT"),
    ("designatorICAO", "TEXT"),
    ("controlType", "TEXT"),
    ("classification", "TEXT"),
    ("upperLimit", "TEXT"),
    ("upperLimitUom", "TEXT"),
    ("upperLimitReference", "TEXT"),
    ("lowerLimit", "TEXT"),
    ("lowerLimitUom", "TEXT"),
    ("lowerLimitReference", "TEXT"),
    ("activity", "TEXT"),
    ("status", "TEXT"),
    ("purpose", "TEXT"),
    ("annotation", "TEXT"),
    ("source", "TEXT"),
    ("dataProvider", "TEXT"),
    ("add_date", "TEXT"),
]
ATTR_NAMES = [c[0] for c in ATTR_COLS]


def file_mtime_str(path: str) -> str:
    """Kaynak dosyanın son değişiklik tarih-saati ('YYYY-MM-DD HH:MM:SS')."""
    try:
        return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return ""

WGS84_WKT = (
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,'
    'AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],'
    'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
    'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],'
    'AUTHORITY["EPSG","4326"]]'
)


def blank_record() -> dict:
    """Tüm ortak kolonları boş + geometry=None içeren kayıt iskeleti."""
    rec = {n: "" for n in ATTR_NAMES}
    rec["geometry"] = None
    return rec


def create_gpkg(path: str) -> sqlite3.Connection:
    """Boş GeoPackage + airspaces tablosu + RTree sanal tablosu kur."""
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
    attr_ddl = ",\n            ".join(f"{n} {t}" for n, t in ATTR_COLS)
    g.execute(f"""
        CREATE TABLE {TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {GEOM_COL} BLOB,
            {attr_ddl}
        )
    """)
    g.execute(f"CREATE VIRTUAL TABLE {RTREE} USING rtree(id, minx, maxx, miny, maxy)")
    g.execute(
        "INSERT INTO gpkg_contents (table_name, data_type, identifier, description, "
        "min_x, min_y, max_x, max_y, srs_id) VALUES (?,?,?,?,?,?,?,?,?)",
        (TABLE, "features", TABLE, "Common airspaces (multi-source)",
         -180.0, -90.0, 180.0, 90.0, 4326),
    )
    g.execute("INSERT INTO gpkg_geometry_columns VALUES (?,?,?,?,?,?)",
              (TABLE, GEOM_COL, "MULTIPOLYGON", 4326, 0, 0))
    return g


_INSERT_SQL = (
    f"INSERT INTO {TABLE} ({GEOM_COL}, {', '.join(ATTR_NAMES)}) "
    f"VALUES (?, {', '.join('?' for _ in ATTR_NAMES)})"
)


def insert_record(cur, rec: dict) -> bool:
    """
    Kaydı airspaces tablosuna ve RTree'ye ekle. Geometri, kaynaktan bağımsız
    olarak merkezi antimeridyen koruması ile güvenli MultiPolygon'a çevrilir.
    Geometri geçersiz/boşsa eklenmez, False döner.
    """
    mp = antimeridian_safe(rec.get("geometry"))
    if mp is None:
        return False
    values = tuple(rec.get(n) or None for n in ATTR_NAMES)
    cur.execute(_INSERT_SQL, (gpkg_geom(mp.wkb, 4326),) + values)
    fid = cur.lastrowid
    minx, miny, maxx, maxy = mp.bounds
    cur.execute(
        f"INSERT INTO {RTREE}(id, minx, maxx, miny, maxy) VALUES (?,?,?,?,?)",
        (fid, minx, maxx, miny, maxy),
    )
    return True


def build_indexes(conn):
    """Geometri dışındaki tüm sütunlar için index oluştur."""
    cur = conn.cursor()
    for name in ATTR_NAMES:
        cur.execute(f"CREATE INDEX idx_{TABLE}_{name} ON {TABLE}({name})")
    conn.commit()
    return len(ATTR_NAMES)
