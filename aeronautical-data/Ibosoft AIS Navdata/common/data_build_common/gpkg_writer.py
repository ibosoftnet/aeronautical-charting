"""GeoPackage 1.3 yazıcısı — katman tanımından bağımsız ortak altyapı.

Projeler kendi katman sözlüğünü (`{ad: {"columns": [...], "geometry": "POINT"}}`)
ve sütun tipi fonksiyonunu verir; tablo kurulumu, satır yazımı, RTree mekânsal
index'i, her sütunda B-tree index ve `gpkg_contents` sınırları burada yapılır.
SpatiaLite gerekmez.
"""

import sqlite3
import struct

from shapely import wkb as shapely_wkb

SRS_ID = 4326


# ── Geometri blob'ları ─────────────────────────────────────────────────────

def _header() -> bytes:
    """GeoPackage geometri başlığı: magic, sürüm 0, bayrak 1 (LE, zarf yok)."""
    return b"GP" + bytes([0, 1]) + struct.pack("<i", SRS_ID)


def point_blob(lon: float, lat: float) -> bytes:
    return _header() + struct.pack("<BI2d", 1, 1, lon, lat)


def linestring_blob(points) -> bytes:
    """points: [(lat, lon), …] — GeoPackage WKB'de sıra (lon, lat)."""
    wkb = struct.pack("<BII", 1, 2, len(points))
    for lat, lon in points:
        wkb += struct.pack("<2d", lon, lat)
    return _header() + wkb


def shapely_blob(geometry) -> bytes:
    """Herhangi bir shapely geometrisi (lon, lat) → GeoPackage blob'u."""
    return _header() + shapely_wkb.dumps(geometry, byte_order=1)


def geometry_envelope(blob: bytes):
    """GeoPackage geometri blob'unun sınırlayıcı kutusu → (minx, maxx, miny, maxy)."""
    if not blob or len(blob) < 8 or blob[:2] != b"GP":
        return None
    flags = blob[3]
    # bit 1-3: envelope göstergesi (0 = yok, 1 = XY, 2 = XYZ, 3 = XYM, 4 = XYZM)
    envelope_doubles = (0, 4, 6, 6, 8)[(flags >> 1) & 0x07]
    offset = 8 + envelope_doubles * 8
    if len(blob) < offset + 5:
        return None
    endian = "<" if blob[offset] == 1 else ">"
    wkb_type = struct.unpack(endian + "I", blob[offset + 1:offset + 5])[0]
    body = offset + 5

    if wkb_type == 1:                                     # Point (hızlı yol)
        if len(blob) < body + 16:
            return None
        x, y = struct.unpack(endian + "2d", blob[body:body + 16])
        return x, x, y, y

    if wkb_type == 2:                                     # LineString (hızlı yol)
        if len(blob) < body + 4:
            return None
        count = struct.unpack(endian + "I", blob[body:body + 4])[0]
        start = body + 4
        if count == 0 or len(blob) < start + count * 16:
            return None
        coords = struct.unpack(endian + f"{count * 2}d",
                               blob[start:start + count * 16])
        xs, ys = coords[0::2], coords[1::2]
        return min(xs), max(xs), min(ys), max(ys)

    # Diğer tipler (Polygon, MultiPolygon, …) genel yol.
    try:
        geom = shapely_wkb.loads(bytes(blob[offset:]))
    except Exception:                                     # noqa: BLE001
        return None
    if geom.is_empty:
        return None
    minx, miny, maxx, maxy = geom.bounds
    return minx, maxx, miny, maxy


# ── Tablo kurulumu ─────────────────────────────────────────────────────────

def create_gpkg(path, layers: dict, column_type):
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.executescript(
        """
        PRAGMA application_id = 0x47504B47;
        PRAGMA user_version = 10300;
        CREATE TABLE gpkg_spatial_ref_sys (
            srs_name TEXT NOT NULL, srs_id INTEGER NOT NULL PRIMARY KEY,
            organization TEXT NOT NULL, organization_coordsys_id INTEGER NOT NULL,
            definition TEXT NOT NULL, description TEXT);
        INSERT INTO gpkg_spatial_ref_sys VALUES
            ('Undefined Cartesian', -1, 'NONE', -1, 'undefined', 'undefined cartesian'),
            ('Undefined Geographic', 0, 'NONE', 0, 'undefined', 'undefined geographic'),
            ('WGS84', 4326, 'EPSG', 4326, 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]', 'WGS 84 geographic 2D');
        CREATE TABLE gpkg_contents (
            table_name TEXT NOT NULL PRIMARY KEY, data_type TEXT NOT NULL,
            identifier TEXT UNIQUE, description TEXT DEFAULT '',
            last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            min_x REAL, min_y REAL, max_x REAL, max_y REAL, srs_id INTEGER);
        CREATE TABLE gpkg_geometry_columns (
            table_name TEXT NOT NULL, column_name TEXT NOT NULL,
            geometry_type_name TEXT NOT NULL, srs_id INTEGER NOT NULL,
            z TINYINT NOT NULL, m TINYINT NOT NULL,
            PRIMARY KEY (table_name, column_name));
        CREATE TABLE gpkg_ogr_contents (
            table_name TEXT NOT NULL PRIMARY KEY, feature_count INTEGER DEFAULT 0);
        CREATE TABLE gpkg_extensions (
            table_name TEXT, column_name TEXT, extension_name TEXT NOT NULL,
            definition TEXT NOT NULL, scope TEXT NOT NULL,
            CONSTRAINT ge_tce UNIQUE (table_name, column_name, extension_name));
        """
    )

    for name, spec in layers.items():
        cols = ",\n  ".join(
            f'"{c}" {column_type(c)}' for c in spec["columns"])
        cur.execute(
            f'CREATE TABLE "{name}" (\n'
            f'  id INTEGER PRIMARY KEY AUTOINCREMENT,\n'
            f'  geom BLOB,\n  {cols}\n)')
        cur.execute(
            "INSERT INTO gpkg_contents "
            "(table_name, data_type, identifier, srs_id) VALUES (?,?,?,?)",
            (name, "features", name, SRS_ID))
        cur.execute(
            "INSERT INTO gpkg_geometry_columns VALUES (?,?,?,?,0,0)",
            (name, "geom", spec["geometry"], SRS_ID))
        cur.execute("INSERT INTO gpkg_ogr_contents VALUES (?, 0)", (name,))

    con.commit()
    return con


def insert_row(cur, layers: dict, layer: str, row: dict,
               geom: bytes | None) -> int:
    columns = layers[layer]["columns"]
    placeholders = ",".join("?" * (len(columns) + 1))
    names = ",".join(['geom'] + [f'"{c}"' for c in columns])
    values = [geom] + [row.get(c) for c in columns]
    cur.execute(f'INSERT INTO "{layer}" ({names}) VALUES ({placeholders})', values)
    return cur.lastrowid


# ── Index'ler ──────────────────────────────────────────────────────────────

# GeoPackage 1.2 Ek F.3 — RTree index tetikleyicileri. `ST_*` fonksiyonları
# QGIS/GDAL tarafından sağlanır; düz SQLite'ta tanımsız olmaları sorun değildir
# çünkü tetikleyici gövdesi yalnızca çalıştırıldığında çözülür.
_RTREE_TRIGGERS = """
CREATE TRIGGER "rtree_{t}_geom_insert" AFTER INSERT ON "{t}"
  WHEN (NEW."geom" NOT NULL AND NOT ST_IsEmpty(NEW."geom"))
BEGIN
  INSERT OR REPLACE INTO "rtree_{t}_geom" VALUES (NEW."id",
    ST_MinX(NEW."geom"), ST_MaxX(NEW."geom"),
    ST_MinY(NEW."geom"), ST_MaxY(NEW."geom"));
END;
CREATE TRIGGER "rtree_{t}_geom_update1" AFTER UPDATE OF "geom" ON "{t}"
  WHEN OLD."id" = NEW."id"
   AND (NEW."geom" NOTNULL AND NOT ST_IsEmpty(NEW."geom"))
BEGIN
  INSERT OR REPLACE INTO "rtree_{t}_geom" VALUES (NEW."id",
    ST_MinX(NEW."geom"), ST_MaxX(NEW."geom"),
    ST_MinY(NEW."geom"), ST_MaxY(NEW."geom"));
END;
CREATE TRIGGER "rtree_{t}_geom_update2" AFTER UPDATE OF "geom" ON "{t}"
  WHEN OLD."id" = NEW."id"
   AND (NEW."geom" ISNULL OR ST_IsEmpty(NEW."geom"))
BEGIN
  DELETE FROM "rtree_{t}_geom" WHERE id = OLD."id";
END;
CREATE TRIGGER "rtree_{t}_geom_update3" AFTER UPDATE ON "{t}"
  WHEN OLD."id" != NEW."id"
   AND (NEW."geom" NOTNULL AND NOT ST_IsEmpty(NEW."geom"))
BEGIN
  DELETE FROM "rtree_{t}_geom" WHERE id = OLD."id";
  INSERT OR REPLACE INTO "rtree_{t}_geom" VALUES (NEW."id",
    ST_MinX(NEW."geom"), ST_MaxX(NEW."geom"),
    ST_MinY(NEW."geom"), ST_MaxY(NEW."geom"));
END;
CREATE TRIGGER "rtree_{t}_geom_update4" AFTER UPDATE ON "{t}"
  WHEN OLD."id" != NEW."id"
   AND (NEW."geom" ISNULL OR ST_IsEmpty(NEW."geom"))
BEGIN
  DELETE FROM "rtree_{t}_geom" WHERE id IN (OLD."id", NEW."id");
END;
CREATE TRIGGER "rtree_{t}_geom_delete" AFTER DELETE ON "{t}"
  WHEN OLD."geom" NOT NULL
BEGIN
  DELETE FROM "rtree_{t}_geom" WHERE id = OLD."id";
END;
"""


def _build_spatial_index(cur, name: str) -> tuple[int, tuple | None]:
    """Katman için RTree sanal tablosunu kurar, doldurur, tetikleyicileri ekler."""
    cur.execute(f'CREATE VIRTUAL TABLE "rtree_{name}_geom" '
                f'USING rtree(id, minx, maxx, miny, maxy)')

    rows, bounds = [], None
    read = cur.connection.cursor()
    read.execute(f'SELECT id, geom FROM "{name}" WHERE geom IS NOT NULL')
    for row_id, blob in read:
        envelope = geometry_envelope(blob)
        if envelope is None:
            continue
        rows.append((row_id, *envelope))
        bounds = envelope if bounds is None else (
            min(bounds[0], envelope[0]), max(bounds[1], envelope[1]),
            min(bounds[2], envelope[2]), max(bounds[3], envelope[3]))
    read.close()

    cur.executemany(f'INSERT INTO "rtree_{name}_geom" VALUES (?,?,?,?,?)', rows)
    cur.executescript(_RTREE_TRIGGERS.format(t=name))
    cur.execute(
        "INSERT INTO gpkg_extensions VALUES (?,'geom','gpkg_rtree_index',"
        "'http://www.geopackage.org/spec120/#extension_rtree','write-only')",
        (name,))
    return len(rows), bounds


def _build_column_indexes(cur, name: str, columns) -> list[tuple[str, str]]:
    """Her sütunda B-tree index kurar; kurulamayanların listesini döndürür.

    Hata yutulmaz: başarısızlık raporda görünür olmalı.
    """
    failed = []
    for column in columns:
        try:
            cur.execute(f'CREATE INDEX "idx_{name}_{column}" '
                        f'ON "{name}"("{column}")')
        except sqlite3.OperationalError as exc:
            failed.append((column, str(exc)))
    return failed


def _indexed_columns(cur, name: str) -> set[str]:
    """Katmanda GERÇEKTEN index'lenmiş sütunlar (diskteki durumdan)."""
    covered = set()
    for row in cur.execute(f'PRAGMA index_list("{name}")').fetchall():
        index = row[1]
        for info in cur.execute(f'PRAGMA index_info("{index}")').fetchall():
            if info[2] is not None:
                covered.add(info[2])
    return covered


def finalize(con, layers: dict, log=None, stage="2B"):
    """Satır sayaçları, tüm sütun index'leri ve mekânsal (RTree) index."""
    cur = con.cursor()
    eksik_toplam = 0
    for name in layers:
        cur.execute(f'SELECT COUNT(*) FROM "{name}"')
        cur.execute("UPDATE gpkg_ogr_contents SET feature_count=? WHERE table_name=?",
                    (cur.fetchone()[0], name))
        failed = _build_column_indexes(cur, name, layers[name]["columns"])

        indexed, bounds = _build_spatial_index(cur, name)
        if bounds:
            cur.execute(
                "UPDATE gpkg_contents SET min_x=?, max_x=?, min_y=?, max_y=? "
                "WHERE table_name=?", (*bounds, name))

        beklenen = layers[name]["columns"]
        covered = _indexed_columns(cur, name)
        indexsiz = [c for c in beklenen if c not in covered]
        eksik_toplam += len(indexsiz)
        uyari = "" if not indexsiz else f"  !! {len(indexsiz)} EKSIK"
        print(f"    {name:18} sutun_index={len(beklenen) - len(indexsiz):>3}"
              f"/{len(beklenen)}{uyari} mekansal_index={indexed}")
        for column in indexsiz:
            print(f"        INDEXSIZ SUTUN: {column}")
            if log is not None:
                log.error(stage, name, column, "index", "-", "sutun_indexsiz")
        for column, hata in failed:
            print(f"        index kurulamadi: {column} -> {hata}")
            if log is not None:
                log.error(stage, name, column, "index", hata,
                          "sutun_indexi_kurulamadi")

    if eksik_toplam:
        print(f"    UYARI: toplam {eksik_toplam} sutun indexsiz kaldi")
    con.commit()
    cur.execute("ANALYZE")
    con.commit()
