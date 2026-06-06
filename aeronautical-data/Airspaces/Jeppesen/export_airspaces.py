"""
Export Jeppesen `boundary` table -> GeoPackage of airspace polygons.

Source : aeronautical-data/Jeppesen Data/jeppesen.sqlite  (table `boundary`)
Output : aeronautical-data/Airspaces/Jeppesen/jeppesen_airspaces.gpkg
         Layer `airspaces` (GEOMETRY, EPSG:4326), RTree spatial index.
         Most features are POLYGON; antimeridian-crossing features become MULTIPOLYGON.

Optional input: tailored.geojson (in this same folder).
    FeatureCollection where each Feature has:
        properties.action       = "override" | "new"        (default: "new")
        properties.boundary_id  = INT   (required for override)
        properties.<col>        = any boundary column to set
        geometry                = Polygon  (required for new; optional for override)
    Behaviour:
        - "override" updates given attributes (and geometry if provided) on the
          matching boundary_id, sets source='jeppesen+override'.
        - "new" inserts a fresh polygon with source='tailored', boundary_id=NULL.

Boundary blob format (verified):
    [4 bytes BE uint32 N] [N * (BE float32 lon, BE float32 lat)]
    First point != last point; ring is closed in code.

Antimeridian handling:
    Polygons whose consecutive vertices jump >180° in longitude are detected and
    split at ±180° via coordinate unrolling + shapely clipping. The result is
    stored as MULTIPOLYGON (two or more pieces, each normalized to [-180, 180]).
"""
import math, os, sqlite3, struct, json
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry import box as _box

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "..", "Jeppesen Data", "jeppesen.sqlite"))
DST = os.path.join(HERE, "jeppesen_airspaces.gpkg")
TAILORED = os.path.join(HERE, "tailored.geojson")

# Boundary table columns to copy verbatim (geometry handled separately).
ATTR_COLS = [
    ("boundary_id", "INTEGER"),
    ("file_id", "INTEGER"),
    ("type", "TEXT"),
    ("name", "TEXT"),
    ("description", "TEXT"),
    ("restrictive_designation", "TEXT"),
    ("restrictive_type", "TEXT"),
    ("multiple_code", "TEXT"),
    ("time_code", "TEXT"),
    ("com_type", "TEXT"),
    ("com_frequency", "INTEGER"),
    ("com_name", "TEXT"),
    ("min_altitude_type", "TEXT"),
    ("max_altitude_type", "TEXT"),
    ("min_altitude", "INTEGER"),
    ("max_altitude", "INTEGER"),
    ("max_lonx", "REAL"),
    ("max_laty", "REAL"),
    ("min_lonx", "REAL"),
    ("min_laty", "REAL"),
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


# ---------------------------------------------------------------------------
# Antimeridian handling
# ---------------------------------------------------------------------------

def _unroll_coords(coords):
    """Make lon sequence continuous — eliminate jumps > 180°."""
    result = [coords[0]]
    for lon, lat in coords[1:]:
        prev = result[-1][0]
        while lon - prev > 180:
            lon -= 360
        while prev - lon > 180:
            lon += 360
        result.append((lon, lat))
    return result


def _to_standard(ring_coords, east_piece=False):
    """Convert unrolled [0,360] coords back to [-180, 180].

    east_piece=True  : coords are on the east side of the antimeridian
                       (lon >= 180 in unrolled space), so subtract 360.
    east_piece=False : coords are on the west side (lon <= 180), keep as-is
                       except lon==180 stays at 180.
    """
    if east_piece:
        return [(x - 360, y) for x, y in ring_coords]
    return [(x, y) for x, y in ring_coords]


def make_geometry(coords):
    """
    Build a Polygon or MultiPolygon from a closed ring, correctly handling
    antimeridian crossings.

    Algorithm:
      1. Normalize all raw lons to [0, 360) — eliminates the ±180 sign ambiguity
         that occurs when source data clamps vertices to exactly ±180.
      2. Unroll the ring to be continuous (no jumps > 180° in the 0-360 space).
      3. If the unrolled extent crosses the 180° line → split into west and east
         pieces, convert each back to [-180, 180], return as MultiPolygon.
      4. Otherwise convert directly and return as Polygon.

    Returns None for degenerate input.
    """
    # Step 1: map all lons to [0, 360)
    coords_360 = [(lon % 360, lat) for lon, lat in coords]

    # Step 2: make continuous in [0, 360] space
    unrolled = _unroll_coords(coords_360)
    lons = [x for x, _ in unrolled]
    min_lon, max_lon = min(lons), max(lons)

    if max_lon - min_lon > 360:
        return None  # degenerate: spans more than a full circle

    # Step 3: build polygon in unrolled space
    p = Polygon(unrolled)
    if not p.is_valid:
        p = p.buffer(0)
    if p.is_empty:
        return None

    # No antimeridian crossing (180° line not inside the longitude extent)
    if max_lon <= 180:
        # Entirely in [0, 180] — some lons may be > 180 only if == 180 exactly
        return Polygon(_to_standard(unrolled, east_piece=False))
    if min_lon >= 180:
        # Entirely in [180, 360] — shift all to [-180, 0]
        return Polygon(_to_standard(unrolled, east_piece=True))

    # Step 4: split at the antimeridian (lon=180 in unrolled space)
    west_clip = _box(min_lon - 1, -90, 180, 90)
    east_clip = _box(180, -90, max_lon + 1, 90)

    parts = []
    for clip, is_east in [(west_clip, False), (east_clip, True)]:
        piece = p.intersection(clip)
        if piece.is_empty:
            continue
        geoms = list(piece.geoms) if piece.geom_type == "MultiPolygon" else [piece]
        for sub in geoms:
            if sub.geom_type != "Polygon" or sub.is_empty:
                continue
            ext = _to_standard(sub.exterior.coords, is_east)
            holes = [_to_standard(ring.coords, is_east) for ring in sub.interiors]
            parts.append(Polygon(ext, holes))

    if not parts:
        return None
    return parts[0] if len(parts) == 1 else MultiPolygon(parts)


# ---------------------------------------------------------------------------

def decode_polygon_blob(blob: bytes):
    """Return closed coordinate list, or None if degenerate."""
    if not blob or len(blob) < 4:
        return None
    n = struct.unpack(">I", blob[:4])[0]
    if n < 3 or len(blob) < 4 + n * 8:
        return None
    pts = struct.unpack(f">{n*2}f", blob[4:4 + n * 8])
    coords = list(zip(pts[0::2], pts[1::2]))
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    if len(set(coords)) < 3:
        return None
    return coords


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
        CREATE TABLE airspaces (
            fid INTEGER PRIMARY KEY AUTOINCREMENT,
            geom BLOB,
            source TEXT NOT NULL DEFAULT 'jeppesen',
            {attr_ddl}
        )
    """)
    g.execute("CREATE VIRTUAL TABLE rtree_airspaces_geom USING rtree(id, minx, maxx, miny, maxy)")
    g.execute(
        "INSERT INTO gpkg_contents (table_name, data_type, identifier, description, "
        "min_x, min_y, max_x, max_y, srs_id) VALUES (?,?,?,?,?,?,?,?,?)",
        ("airspaces", "features", "airspaces",
         "Jeppesen boundary airspaces (+ tailored overrides/new)",
         -180.0, -90.0, 180.0, 90.0, 4326),
    )
    g.execute("INSERT INTO gpkg_geometry_columns VALUES (?,?,?,?,?,?)",
              ("airspaces", "geom", "GEOMETRY", 4326, 0, 0))
    return g


def _make_polygon_from_geojson(geom_gj):
    if not geom_gj or geom_gj.get("type") != "Polygon":
        return None
    rings = geom_gj.get("coordinates") or []
    if not rings:
        return None
    outer = rings[0]
    holes = rings[1:] if len(rings) > 1 else None
    poly = Polygon(outer, holes)
    if not poly.is_valid:
        poly = poly.buffer(0)
        if poly.is_empty or poly.geom_type != "Polygon":
            return None
    return poly


def merge_tailored(gpkg: sqlite3.Connection):
    if not os.path.exists(TAILORED):
        print(f"  no tailored file at {TAILORED} (skipping)")
        return 0, 0, 0
    with open(TAILORED, encoding="utf-8") as f:
        fc = json.load(f)
    if fc.get("type") != "FeatureCollection":
        print("  [warn] tailored.geojson is not a FeatureCollection, skipping")
        return 0, 0, 0
    cur = gpkg.cursor()
    n_over = n_new = n_warn = 0
    for feat in fc.get("features", []):
        props = dict(feat.get("properties") or {})
        action = (props.pop("action", None) or "new").lower()
        bid = props.pop("boundary_id", None)
        poly = _make_polygon_from_geojson(feat.get("geometry"))

        if action == "override":
            if bid is None:
                print(f"  [warn] override without boundary_id: {props}")
                n_warn += 1
                continue
            set_clauses, values = [], []
            for k, v in props.items():
                if k in ATTR_NAMES:
                    set_clauses.append(f"{k}=?")
                    values.append(v)
            minx = miny = maxx = maxy = None
            if poly is not None:
                minx, miny, maxx, maxy = poly.bounds
                set_clauses.append("geom=?"); values.append(gpkg_geom(poly.wkb, 4326))
                set_clauses += ["min_lonx=?", "max_lonx=?", "min_laty=?", "max_laty=?"]
                values += [minx, maxx, miny, maxy]
            set_clauses.append("source='jeppesen+override'")
            values.append(bid)
            cur.execute(
                f"UPDATE airspaces SET {', '.join(set_clauses)} WHERE boundary_id=?",
                values,
            )
            if cur.rowcount == 0:
                print(f"  [warn] no boundary_id={bid} match for override")
                n_warn += 1
                continue
            if poly is not None:
                for (fid,) in cur.execute(
                    "SELECT fid FROM airspaces WHERE boundary_id=?", (bid,)
                ).fetchall():
                    cur.execute(
                        "UPDATE rtree_airspaces_geom "
                        "SET minx=?, maxx=?, miny=?, maxy=? WHERE id=?",
                        (minx, maxx, miny, maxy, fid),
                    )
            n_over += 1

        else:  # new
            if poly is None:
                print(f"  [warn] new without polygon geometry: {props}")
                n_warn += 1
                continue
            minx, miny, maxx, maxy = poly.bounds
            row = {c: props.get(c) for c in ATTR_NAMES}
            row["min_lonx"], row["max_lonx"] = minx, maxx
            row["min_laty"], row["max_laty"] = miny, maxy
            values = tuple(row[c] for c in ATTR_NAMES)
            cur.execute(
                f"INSERT INTO airspaces (geom, source, {', '.join(ATTR_NAMES)}) "
                f"VALUES (?, 'tailored', {', '.join('?' for _ in ATTR_NAMES)})",
                (gpkg_geom(poly.wkb, 4326),) + values,
            )
            fid = cur.lastrowid
            cur.execute(
                "INSERT INTO rtree_airspaces_geom(id, minx, maxx, miny, maxy) VALUES (?,?,?,?,?)",
                (fid, minx, maxx, miny, maxy),
            )
            n_new += 1
    gpkg.commit()
    return n_over, n_new, n_warn


def main():
    print(f"Source : {SRC}")
    print(f"Output : {DST}")
    src = sqlite3.connect(SRC)
    src.row_factory = sqlite3.Row
    gpkg = create_gpkg(DST)
    gpkg.commit()

    cur = gpkg.cursor()
    cols_sql = "geom, " + ", ".join(ATTR_NAMES)
    placeholders = ",".join("?" * (len(ATTR_NAMES) + 1))
    insert_sql = f"INSERT INTO airspaces ({cols_sql}) VALUES ({placeholders})"

    inserted = skipped = antimeridian_count = 0
    select_sql = "SELECT " + ", ".join(ATTR_NAMES) + ", geometry FROM boundary"
    for row in src.execute(select_sql):
        coords = decode_polygon_blob(row["geometry"])
        if coords is None:
            skipped += 1
            continue
        geom_obj = make_geometry(coords)
        if geom_obj is None or geom_obj.is_empty:
            skipped += 1
            continue
        if geom_obj.geom_type == "MultiPolygon":
            antimeridian_count += 1
        geom = gpkg_geom(geom_obj.wkb, 4326)
        attrs = tuple(row[c] for c in ATTR_NAMES)
        cur.execute(insert_sql, (geom,) + attrs)
        fid = cur.lastrowid
        minx, miny, maxx, maxy = geom_obj.bounds
        cur.execute(
            "INSERT INTO rtree_airspaces_geom(id, minx, maxx, miny, maxy) VALUES (?,?,?,?,?)",
            (fid, minx, maxx, miny, maxy),
        )
        inserted += 1
    gpkg.commit()
    src.close()
    print(f"  Jeppesen: inserted={inserted}  skipped={skipped}  antimeridian_split={antimeridian_count}")

    print("Merging tailored.geojson (if present)…")
    n_over, n_new, n_warn = merge_tailored(gpkg)
    print(f"  Tailored: overrides={n_over}  new={n_new}  warnings={n_warn}")

    print(f"Done. {DST}  ({os.path.getsize(DST):,} bytes)")
    gpkg.close()


if __name__ == "__main__":
    main()
