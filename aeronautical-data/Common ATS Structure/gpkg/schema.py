"""AŞAMA 2B — GeoPackage şeması: 4 katmanın sütun listeleri ve DDL.

Sütun adlandırma (plan kararı):
  * `<katman>_<AIXM öznitelik adı, camelCase>`
  * ölçü birimi → `<alan>Uom`, dikey referans → `<alan>Reference`
  * `annotation` → 4 sabit sütun (purpose değerlerine göre), katman ÖNEKİSİZ
  * provenance (`data_provider`/`data_originator`/`data_effectivity`/`add_date`)
    ve `gmlId` de katman ÖNEKİSİZ — bu alanlar her katmanda birebir aynı yapıyı
    taşır, tabloya özgü bir anlamları yoktur (kullanıcı kararı)

`points` katmanı YOKTUR: AIXM `Point` bağımsız bir feature değildir
(`gml:Point` substitution group'unda, `AbstractAIXMFeature` değil), bu yüzden
bağımsız satırları olan bir katman kurulamaz — kullanıcı kararıyla iptal edildi.
"""

import sqlite3
import struct

SRS_ID = 4326

ANNOTATION_PURPOSES = ("Description", "Remark", "Warning", "Disclaimer")


#: `annotation` ve provenance sütunları katman önekisiz — bu yapılar her
#: katmanda birebir aynı 4 alana indirgenir, tabloya özgü bir anlamı yoktur
#: (kullanıcı kararı). `_annotation_columns`/`_provenance_columns` artık
#: parametresiz: tüm katmanlar aynı sabit listeyi kullanır.
ANNOTATION_COLUMNS = [f"annotation{p}" for p in ANNOTATION_PURPOSES]
PROVENANCE_COLUMNS = ["data_provider", "data_originator",
                      "data_effectivity", "add_date"]

#: `atsStatus_*` — noktanın ATS rota ağındaki rolünün TÜRETİLMİŞ özeti.
#: Yalnızca nokta katmanlarında (`designatedPoints`, `navaids`) bulunur;
#: `navaidComponents` rota uç noktası olarak çözümlenmez, orada anlamsızdır.
#: AIXM'de karşılığı YOKTUR — `routeSegments` tablosu yazıldıktan SONRA ondan
#: türetilir (bkz. build_common_ats.py `compute_ats_status`). Amaç: QGIS'te
#: "yalnızca rota noktaları" gibi filtreleri sanal katman kurmadan, mevcut
#: RTree/B-tree indekslerini bozmadan yapabilmek.
#: Katman öneki taşımazlar (annotation/provenance ile aynı kural).
ATS_STATUS_COLUMNS = [
    "atsStatus_isElementOfRouteSegment",   # BOOLEAN — kapı alanı
    # CodeLevelType degerleri, dort BAGIMSIZ bayrak olarak: her biri
    # "iliskili segmentlerden EN AZ BIRI bu seviyede mi". Birbirlerini
    # dislamazlar. `Other` yalnizca gercek `OTHER`/`OTHER:xxx` degeri varsa
    # 1 olur — level tasimayan segmentler icin fallback DEGILDIR.
    "atsStatus_associatedLevelUpper",      # BOOLEAN
    "atsStatus_associatedLevelLower",      # BOOLEAN
    "atsStatus_associatedLevelBoth",       # BOOLEAN
    "atsStatus_associatedLevelOther",      # BOOLEAN — gercek OTHER/OTHER:xxx
    "atsStatus_reportingAssociation",      # JSON: [{segmentId, role, reportingATC}]
    "atsStatus_depictionCompulsory",       # BOOLEAN — reportingATC = COMPULSORY
    # Harita gosterimi icin TURETILMIS siniflandirmalar. Diger alanlar gibi
    # KAPIYA BAGLIDIRLAR: nokta rota elemani degilse NULL kalirlar — bir
    # noktanin rota gosterim sinifi ancak bir ATS rotasinin parcasiysa
    # anlamlidir (kullanici karari, bkz. compute_ats_status).
    "atsStatus_depictionNav",              # CONV / RNAVFlyBy / RNAVFlyOver / OTHER
    "atsStatus_depictionSIGPointBasicFunc",  # NAVAID / VFR_REP / WPT / INT / OTHER
    # `depictionNav` + `depictionCompulsory` bileskesi. Tek sutunda hem
    # seyrusefer sinifini hem raporlama zorunlulugunu tasir; QGIS'te tek
    # kategorize alanindan sembol uretmek icin (kullanici karari).
    "atsStatus_depictionNavAndREP",        # <depictionNav>_<Comp|NonComp>
]

#: `atsStatus_depictionNav` enum'u — seyrusefer gosterim sinifi.
DEPICTION_NAV = ("CONV", "RNAVFlyBy", "RNAVFlyOver", "OTHER")

#: `atsStatus_depictionSIGPointBasicFunc` enum'u — onemli nokta temel islevi.
DEPICTION_SIG_POINT = ("NAVAID", "VFR_REP", "WPT", "INT", "OTHER")

#: `atsStatus_depictionNavAndREP` enum'u — `DEPICTION_NAV` degerlerinin
#: `_Comp` / `_NonComp` sonekiyle carpimi. Elle yazilmaz, turetilir ki
#: `DEPICTION_NAV` degisince burasi da otomatik guncellensin.
DEPICTION_NAV_AND_REP = tuple(
    f"{nav}_{suffix}" for suffix in ("Comp", "NonComp") for nav in DEPICTION_NAV)

#: GeoPackage'da BOOLEAN yoktur; 0/1 INTEGER olarak saklanır (GDAL bunu
#: mantıksal alan olarak tanır). Sütun adıyla açıkça listelenir — son ek
#: tahminine bırakmak kırılgan olurdu.
BOOLEAN_COLUMNS = frozenset([
    "atsStatus_isElementOfRouteSegment",
    "atsStatus_associatedLevelUpper",
    "atsStatus_associatedLevelLower",
    "atsStatus_associatedLevelBoth",
    "atsStatus_associatedLevelOther",
    "atsStatus_depictionCompulsory",
])


# ── designatedPoints ────────────────────────────────────────────────────────
DESIGNATED_POINTS = (
    ["designatedPoints_designator", "designatedPoints_type",
     "designatedPoints_name", "designatedPoints_codeICAOCountry",
     "designatedPoints_fix"]                      # JSON: PointReference[]
    + ANNOTATION_COLUMNS
    + PROVENANCE_COLUMNS
    + ATS_STATUS_COLUMNS
    + ["gmlId"]
)

# ── navaids ─────────────────────────────────────────────────────────────────
NAVAIDS = (
    ["navaids_type", "navaids_designator", "navaids_name",
     "navaids_flightChecked", "navaids_purpose", "navaids_signalPerformance",
     "navaids_courseQuality", "navaids_integrityLevel",
     "navaids_codeICAOCountry",
     # location → ElevatedPoint alt alanları (geometri ayrı sütunda)
     "navaids_locationElevation", "navaids_locationElevationUom",
     "navaids_locationGeoidUndulation", "navaids_locationVerticalDatum",
     "navaids_locationHorizontalAccuracy", "navaids_locationHorizontalAccuracyUom",
     "navaids_availability"]                      # JSON: NavaidOperationalStatus[]
    + ANNOTATION_COLUMNS
    + PROVENANCE_COLUMNS
    + ATS_STATUS_COLUMNS
    + ["gmlId"]
)

# ── navaidComponents ────────────────────────────────────────────────────────
# NavaidComponent (ince Object) + bağlı AbstractNavaidEquipment tek satırda.
# Alt-türe özgü alanlar ortak sütun adlarını paylaşır; hangi alt-türün alanı
# olduğu `equipmentType` sütunundan bilinir. `type` ve `class` sütunlarının
# izinli değerleri alt-türe göre DEĞİŞİR (validasyon equipmentType'a duyarlıdır).
NAVAID_COMPONENTS = (
    ["navaidComponents_navaidId",                 # FK → navaids.id
     "navaidComponents_equipmentType",            # 11 somut alt-türden hangisi
     # NavaidComponent'in kendi alanları
     "navaidComponents_collocationGroup", "navaidComponents_markerPosition",
     "navaidComponents_providesNavigableLocation",
     # NavaidEquipmentPropertyGroup (tüm alt-türlerde ortak)
     "navaidComponents_designator", "navaidComponents_name",
     "navaidComponents_emissionClass", "navaidComponents_mobile",
     "navaidComponents_magneticVariation", "navaidComponents_dateMagneticVariation",
     "navaidComponents_flightChecked",
     "navaidComponents_locationElevation", "navaidComponents_locationElevationUom",
     "navaidComponents_locationGeoidUndulation",
     "navaidComponents_locationVerticalDatum",
     "navaidComponents_locationHorizontalAccuracy",
     "navaidComponents_locationHorizontalAccuracyUom",
     "navaidComponents_monitoring", "navaidComponents_availability",
     # Alt-türe özgü (paylaşılan adlar)
     "navaidComponents_type",                     # VOR / DME / Azimuth
     "navaidComponents_class",                    # MarkerBeacon / NDB
     "navaidComponents_frequency", "navaidComponents_frequencyUom",
     "navaidComponents_channel",
     "navaidComponents_declination",
     "navaidComponents_zeroBearingDirection",     # VOR
     "navaidComponents_displace", "navaidComponents_displaceUom",   # DME
     "navaidComponents_tuningFrequencyVHF", "navaidComponents_tuningFrequencyVHFUom",
     "navaidComponents_magneticBearing", "navaidComponents_trueBearing",
     "navaidComponents_widthCourse", "navaidComponents_backCourseUsable",
     "navaidComponents_signalPerformance", "navaidComponents_courseQuality",
     "navaidComponents_integrityLevel",
     "navaidComponents_slope",                    # Glidepath
     "navaidComponents_rdh", "navaidComponents_rdhUom",
     "navaidComponents_axisBearing", "navaidComponents_auralMorseCode",  # MarkerBeacon
     "navaidComponents_emissionBand",             # NDB
     "navaidComponents_angleProportionalLeft", "navaidComponents_angleProportionalRight",
     "navaidComponents_angleCoverLeft", "navaidComponents_angleCoverRight",  # Azimuth
     "navaidComponents_angleNominal", "navaidComponents_angleMinimum",
     "navaidComponents_angleSpan",                # Elevation
     "navaidComponents_doppler"]                  # DirectionFinder
    + ANNOTATION_COLUMNS
    + PROVENANCE_COLUMNS
    + ["gmlId"]
)

# ── routeSegments ───────────────────────────────────────────────────────────
_SEGMENT_POINT_FIELDS = [
    "PointLayer", "PointId", "PointDesignator",   # çözülen referans
    "ReportingATC", "FlyOver", "Waypoint", "RadarGuidance",
    "FacilityMakeup",                             # JSON: PointReference[]
    "RoleFreeFlight", "RoleRVSM",
    "TurnRadius", "TurnRadiusUom", "RoleMilitaryTraining",
]

ROUTE_SEGMENTS = (
    ["routeSegments_level",
     "routeSegments_upperLimit", "routeSegments_upperLimitUom",
     "routeSegments_upperLimitReference",
     "routeSegments_lowerLimit", "routeSegments_lowerLimitUom",
     "routeSegments_lowerLimitReference",
     "routeSegments_minimumObstacleClearanceAltitude",
     "routeSegments_minimumObstacleClearanceAltitudeUom",
     "routeSegments_pathType",
     "routeSegments_trueTrack", "routeSegments_magneticTrack",
     "routeSegments_reverseTrueTrack", "routeSegments_reverseMagneticTrack",
     "routeSegments_length", "routeSegments_lengthUom",
     "routeSegments_widthLeft", "routeSegments_widthLeftUom",
     "routeSegments_widthRight", "routeSegments_widthRightUom",
     "routeSegments_turnDirection", "routeSegments_signalGap",
     "routeSegments_minimumEnrouteAltitude",      # JSON: AltitudeIndication[]
     "routeSegments_minimumCrossingAtEnd", "routeSegments_minimumCrossingAtEndUom",
     "routeSegments_minimumCrossingAtEndReference",
     "routeSegments_maximumCrossingAtEnd", "routeSegments_maximumCrossingAtEndUom",
     "routeSegments_maximumCrossingAtEndReference",
     "routeSegments_designatorSuffix"]
    + [f"routeSegments_start{f}" for f in _SEGMENT_POINT_FIELDS]
    + [f"routeSegments_end{f}" for f in _SEGMENT_POINT_FIELDS]
    + ["routeSegments_availability",              # JSON
       "routeSegments_cardinalDirectionLeft", "routeSegments_cardinalDirectionRight",
       "routeSegments_aircraftCapability",        # JSON
       "routeSegments_airspaceClass",             # JSON
       "routeSegments_designCriteria",            # virgülle ayrılmış
       # Route'tan devralınan alanlar (Route'un geometrisi yok, ayrı katman
       # değil). `route_` öneki BİLİNÇLİ OLARAK `routeSegments_`'ten farklıdır:
       # bu alanlar RouteSegment'in değil, bağlı Route feature'ının alanlarıdır
       # (kullanıcı düzeltmesi — aynı önek iki farklı kaynağı ayırt edilemez
       # kılıyordu).
       "route_designatorPrefix", "route_designatorSecondLetter",
       "route_designatorNumber", "route_multipleIdentifier",
       "route_locationDesignator", "route_name",
       "route_type", "route_flightRule",
       "route_internationalUse", "route_militaryUse",
       "route_militaryTrainingType"]
    + ANNOTATION_COLUMNS
    + PROVENANCE_COLUMNS
    + ["gmlId"]
)

LAYERS = {
    "designatedPoints": {"columns": DESIGNATED_POINTS, "geometry": "POINT"},
    "navaids": {"columns": NAVAIDS, "geometry": "POINT"},
    "navaidComponents": {"columns": NAVAID_COMPONENTS, "geometry": "POINT"},
    "routeSegments": {"columns": ROUTE_SEGMENTS, "geometry": "LINESTRING"},
}

# Sayısal olarak saklanacak sütunlar (diğerleri TEXT).
_REAL_SUFFIXES = (
    "Elevation", "GeoidUndulation", "HorizontalAccuracy", "magneticVariation",
    "frequency", "tuningFrequencyVHF", "declination", "magneticBearing",
    "trueBearing", "widthCourse", "slope", "rdh", "axisBearing", "displace",
    "angleProportionalLeft", "angleProportionalRight", "angleCoverLeft",
    "angleCoverRight", "angleNominal", "angleMinimum", "angleSpan",
    "trueTrack", "magneticTrack", "reverseTrueTrack", "reverseMagneticTrack",
    "length", "widthLeft", "widthRight", "TurnRadius", "upperLimit",
    "lowerLimit", "minimumObstacleClearanceAltitude", "minimumCrossingAtEnd",
    "maximumCrossingAtEnd",
)


def column_type(name: str) -> str:
    if name in BOOLEAN_COLUMNS:
        return "BOOLEAN"                  # SQLite'ta 0/1 INTEGER olarak saklanır
    if name.endswith("Uom") or name.endswith("Reference"):
        return "TEXT"
    if name.endswith("PointId") or name.endswith("navaidId"):
        return "INTEGER"
    short = name.split("_", 1)[-1]
    for suffix in _REAL_SUFFIXES:
        if short == suffix or short.endswith(suffix):
            return "REAL"
    return "TEXT"


# ── GeoPackage yazımı ───────────────────────────────────────────────────────

def point_blob(lon: float, lat: float) -> bytes:
    header = b"GP" + bytes([0, 1]) + struct.pack("<i", SRS_ID)
    return header + struct.pack("<BI2d", 1, 1, lon, lat)


def linestring_blob(points) -> bytes:
    """points: [(lat, lon), …] — GeoPackage WKB'de sıra (lon, lat)."""
    header = b"GP" + bytes([0, 1]) + struct.pack("<i", SRS_ID)
    wkb = struct.pack("<BII", 1, 2, len(points))
    for lat, lon in points:
        wkb += struct.pack("<2d", lon, lat)
    return header + wkb


def create_gpkg(path):
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

    for name, spec in LAYERS.items():
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


def insert_row(cur, layer: str, row: dict, geom: bytes | None) -> int:
    columns = LAYERS[layer]["columns"]
    placeholders = ",".join("?" * (len(columns) + 1))
    names = ",".join(['geom'] + [f'"{c}"' for c in columns])
    values = [geom] + [row.get(c) for c in columns]
    cur.execute(f'INSERT INTO "{layer}" ({names}) VALUES ({placeholders})', values)
    return cur.lastrowid


def geometry_envelope(blob: bytes):
    """GeoPackage geometri blob'unun sınırlayıcı kutusu → (minx, maxx, miny, maxy).

    Yalnızca bu modülün ürettiği iki tipi çözer (Point, LineString); başka bir
    tip gelirse None döner ve satır mekânsal index'e girmez.
    """
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

    if wkb_type == 1:                                     # Point
        if len(blob) < body + 16:
            return None
        x, y = struct.unpack(endian + "2d", blob[body:body + 16])
        return x, x, y, y

    if wkb_type == 2:                                     # LineString
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

    return None


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
    """Katman için RTree sanal tablosunu kurar, doldurur, tetikleyicileri ekler.

    Dönen: (indekslenen satır sayısı, katmanın toplam sınırlayıcı kutusu).
    """
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


def finalize(con):
    """Satır sayaçları, tüm sütun index'leri ve mekânsal (RTree) index."""
    cur = con.cursor()
    for name in LAYERS:
        cur.execute(f'SELECT COUNT(*) FROM "{name}"')
        cur.execute("UPDATE gpkg_ogr_contents SET feature_count=? WHERE table_name=?",
                    (cur.fetchone()[0], name))
        for column in LAYERS[name]["columns"]:
            try:
                cur.execute(f'CREATE INDEX "idx_{name}_{column}" '
                            f'ON "{name}"("{column}")')
            except sqlite3.OperationalError:
                pass

        indexed, bounds = _build_spatial_index(cur, name)
        if bounds:
            cur.execute(
                "UPDATE gpkg_contents SET min_x=?, max_x=?, min_y=?, max_y=? "
                "WHERE table_name=?", (*bounds, name))
        print(f"    {name:18} sutun_index={len(LAYERS[name]['columns']):>3} "
              f"mekansal_index={indexed}")
    con.commit()
    cur.execute("ANALYZE")
    con.commit()
