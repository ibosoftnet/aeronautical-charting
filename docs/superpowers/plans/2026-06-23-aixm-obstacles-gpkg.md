# AIXM Obstacle → Spatial GeoPackage Converter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `build_obstacles_gpkg.py` + `convert_obstacles.bat` in
`aeronautical-data/Obstacles/Area-1/` that scan every country/area subfolder
for AIXM 5.1 `VerticalStructure` XML files and merge them into one
spec-compliant, spatial-indexed `obstacles.gpkg`.

**Architecture:** Pure Python 3 stdlib (`xml.etree.ElementTree`, `sqlite3`,
`struct`) — no GDAL/external dependency, matching every other converter in
this repo. One module, four responsibilities: discovery (filesystem),
extraction (AIXM → row dicts, one row per `VerticalStructurePart`), writing
(hand-rolled GeoPackage with a spec-compliant RTree spatial index), and
orchestration (`main()`).

**Tech Stack:** Python 3.14 (`py` launcher), stdlib only, `unittest` for
tests (no pytest installed on this machine).

**Spec:** `docs/superpowers/specs/2026-06-23-aixm-obstacles-gpkg-design.md`

---

## Task 1: Module skeleton + pure parsing helpers

**Files:**
- Create: `aeronautical-data/Obstacles/Area-1/build_obstacles_gpkg.py`
- Create: `aeronautical-data/Obstacles/Area-1/test_build_obstacles_gpkg.py`

- [ ] **Step 1: Write the failing tests**

```python
"""build_obstacles_gpkg.py icin birim testleri (stdlib unittest, harici bagimlilik yok)."""

import struct
import unittest

import build_obstacles_gpkg as mod


class ParsePosTests(unittest.TestCase):
    def test_valid_lat_lon_swapped_to_lon_lat(self):
        self.assertEqual(
            mod.parse_pos("40.7479944444 29.5148305556"),
            (29.5148305556, 40.7479944444),
        )

    def test_none_input(self):
        self.assertIsNone(mod.parse_pos(None))

    def test_wrong_token_count(self):
        self.assertIsNone(mod.parse_pos("40.0"))

    def test_non_numeric(self):
        self.assertIsNone(mod.parse_pos("abc def"))


class ToIntTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(mod.to_int("827"), 827)

    def test_none(self):
        self.assertIsNone(mod.to_int(None))

    def test_invalid(self):
        self.assertIsNone(mod.to_int("not-a-number"))


class GpkgPointBlobTests(unittest.TestCase):
    def test_header_and_coordinates_roundtrip(self):
        blob = mod.gpkg_point_blob(29.51, 40.74)
        self.assertEqual(blob[:2], b"GP")
        srs_id = struct.unpack("<i", blob[4:8])[0]
        self.assertEqual(srs_id, 4326)
        geom_type, x, y = struct.unpack("<I2d", blob[9:])
        self.assertEqual(geom_type, 1)
        self.assertAlmostEqual(x, 29.51)
        self.assertAlmostEqual(y, 40.74)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `aeronautical-data/Obstacles/Area-1/`):
```
py -m unittest test_build_obstacles_gpkg -v
```
Expected: `ModuleNotFoundError: No module named 'build_obstacles_gpkg'` (file doesn't exist yet).

- [ ] **Step 3: Write the module skeleton + pure helpers**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
py -m unittest test_build_obstacles_gpkg -v
```
Expected: `OK` (7 tests passed: 4 ParsePosTests, 3 ToIntTests, 1 GpkgPointBlobTests... actually 4+3+1=8, verify count in output).

- [ ] **Step 5: Commit**

```bash
git add "aeronautical-data/Obstacles/Area-1/build_obstacles_gpkg.py" "aeronautical-data/Obstacles/Area-1/test_build_obstacles_gpkg.py"
git commit -m "Add AIXM obstacle converter skeleton with pure parsing helpers"
```

---

## Task 2: Filesystem discovery helpers

**Files:**
- Modify: `aeronautical-data/Obstacles/Area-1/build_obstacles_gpkg.py` (append)
- Modify: `aeronautical-data/Obstacles/Area-1/test_build_obstacles_gpkg.py` (append)

- [ ] **Step 1: Write the failing tests**

Add to `test_build_obstacles_gpkg.py` (above the `if __name__ == "__main__":` line):

```python
import tempfile
from pathlib import Path


class DiscoveryTests(unittest.TestCase):
    def test_find_country_dirs_only_lists_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "LT").mkdir()
            (base / "XX").mkdir()
            (base / "notes.txt").write_text("not a dir")
            self.assertEqual(
                [p.name for p in mod.find_country_dirs(base)], ["LT", "XX"]
            )

    def test_find_xml_files_only_matches_xml_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "a.xml").write_text("<a/>")
            (base / "a.gfs").write_text("<a/>")
            self.assertEqual([p.name for p in mod.find_xml_files(base)], ["a.xml"])

    def test_looks_like_aixm_true_for_aixm_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.xml"
            path.write_text(
                '<?xml version="1.0"?>'
                '<AIXMBasicMessage xmlns:aixm="http://www.aixm.aero/schema/5.1">'
                "</AIXMBasicMessage>"
            )
            self.assertTrue(mod.looks_like_aixm(path))

    def test_looks_like_aixm_false_for_unrelated_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.xml"
            path.write_text('<?xml version="1.0"?><Unrelated></Unrelated>')
            self.assertFalse(mod.looks_like_aixm(path))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -m unittest test_build_obstacles_gpkg -v`
Expected: `AttributeError: module 'build_obstacles_gpkg' has no attribute 'find_country_dirs'`

- [ ] **Step 3: Implement discovery helpers**

Append to `build_obstacles_gpkg.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -m unittest test_build_obstacles_gpkg -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add "aeronautical-data/Obstacles/Area-1/build_obstacles_gpkg.py" "aeronautical-data/Obstacles/Area-1/test_build_obstacles_gpkg.py"
git commit -m "Add filesystem discovery helpers for obstacle converter"
```

---

## Task 3: AIXM record extraction (iter_structures + extract_part_rows)

This is the core mapping logic: one `VerticalStructure` → one row per
`VerticalStructurePart` that has valid point geometry, fields named exactly
like the verified AIXM 5.1 schema (see spec doc).

**Files:**
- Modify: `aeronautical-data/Obstacles/Area-1/build_obstacles_gpkg.py` (append)
- Modify: `aeronautical-data/Obstacles/Area-1/test_build_obstacles_gpkg.py` (append)

- [ ] **Step 1: Write the failing tests**

Add to `test_build_obstacles_gpkg.py`:

```python
SAMPLE_SINGLE_PART = """<?xml version="1.0" encoding="UTF-8"?>
<AIXMBasicMessage xmlns:aixm="http://www.aixm.aero/schema/5.1" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns="http://www.aixm.aero/schema/5.1/message">
  <hasMember>
    <aixm:VerticalStructure gml:id="gml.id2">
      <gml:identifier codeSpace="urn:uuid:">TEST-UUID-1</gml:identifier>
      <aixm:timeSlice>
        <aixm:VerticalStructureTimeSlice gml:id="gml.id3">
          <gml:validTime>
            <gml:TimePeriod gml:id="gml.id4">
              <gml:beginPosition>2026-06-11T00:00:00</gml:beginPosition>
              <gml:endPosition indeterminatePosition="unknown"/>
            </gml:TimePeriod>
          </gml:validTime>
          <aixm:interpretation>BASELINE</aixm:interpretation>
          <aixm:sequenceNumber>1</aixm:sequenceNumber>
          <aixm:correctionNumber>0</aixm:correctionNumber>
          <aixm:featureLifetime>
            <gml:TimePeriod gml:id="gml.id5">
              <gml:beginPosition>2026-06-11T00:00:00</gml:beginPosition>
              <gml:endPosition indeterminatePosition="unknown"/>
            </gml:TimePeriod>
          </aixm:featureLifetime>
          <aixm:name>TEST_TOWER</aixm:name>
          <aixm:type>TOWER</aixm:type>
          <aixm:lighted>YES</aixm:lighted>
          <aixm:group>NO</aixm:group>
          <aixm:part>
            <aixm:VerticalStructurePart gml:id="gml.id6">
              <aixm:verticalExtent uom="FT">100</aixm:verticalExtent>
              <aixm:type>TOWER</aixm:type>
              <aixm:designator>T1</aixm:designator>
              <aixm:horizontalProjection_location>
                <aixm:ElevatedPoint gml:id="gml.id7" srsName="urn:ogc:def:crs:EPSG::4326">
                  <gml:pos>40.0 29.0</gml:pos>
                  <aixm:elevation uom="FT">200</aixm:elevation>
                </aixm:ElevatedPoint>
              </aixm:horizontalProjection_location>
              <aixm:lighting>
                <aixm:LightElement gml:id="gml.id8">
                  <aixm:colour>RED</aixm:colour>
                </aixm:LightElement>
              </aixm:lighting>
            </aixm:VerticalStructurePart>
          </aixm:part>
        </aixm:VerticalStructureTimeSlice>
      </aixm:timeSlice>
    </aixm:VerticalStructure>
  </hasMember>
</AIXMBasicMessage>
"""

SAMPLE_MULTI_PART = """<?xml version="1.0" encoding="UTF-8"?>
<AIXMBasicMessage xmlns:aixm="http://www.aixm.aero/schema/5.1" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns="http://www.aixm.aero/schema/5.1/message">
  <hasMember>
    <aixm:VerticalStructure gml:id="gml.id20">
      <gml:identifier codeSpace="urn:uuid:">TEST-UUID-2</gml:identifier>
      <aixm:timeSlice>
        <aixm:VerticalStructureTimeSlice gml:id="gml.id21">
          <aixm:interpretation>BASELINE</aixm:interpretation>
          <aixm:name>TEST_MULTI</aixm:name>
          <aixm:type>CATENARY</aixm:type>
          <aixm:group>NO</aixm:group>
          <aixm:part>
            <aixm:VerticalStructurePart gml:id="gml.id22">
              <aixm:verticalExtent uom="FT">50</aixm:verticalExtent>
              <aixm:type>CATENARY</aixm:type>
              <aixm:designator>P1</aixm:designator>
              <aixm:horizontalProjection_location>
                <aixm:ElevatedPoint gml:id="gml.id23" srsName="urn:ogc:def:crs:EPSG::4326">
                  <gml:pos>41.0 30.0</gml:pos>
                  <aixm:elevation uom="FT">10</aixm:elevation>
                </aixm:ElevatedPoint>
              </aixm:horizontalProjection_location>
              <aixm:lighting>
                <aixm:LightElement gml:id="gml.id24">
                  <aixm:colour>RED</aixm:colour>
                </aixm:LightElement>
              </aixm:lighting>
              <aixm:lighting>
                <aixm:LightElement gml:id="gml.id25">
                  <aixm:colour>WHITE</aixm:colour>
                </aixm:LightElement>
              </aixm:lighting>
            </aixm:VerticalStructurePart>
          </aixm:part>
          <aixm:part>
            <aixm:VerticalStructurePart gml:id="gml.id26">
              <aixm:verticalExtent uom="FT">55</aixm:verticalExtent>
              <aixm:type>CATENARY</aixm:type>
              <aixm:designator>P2</aixm:designator>
              <aixm:horizontalProjection_location>
                <aixm:ElevatedPoint gml:id="gml.id27" srsName="urn:ogc:def:crs:EPSG::4326">
                  <gml:pos>41.001 30.001</gml:pos>
                  <aixm:elevation uom="FT">11</aixm:elevation>
                </aixm:ElevatedPoint>
              </aixm:horizontalProjection_location>
            </aixm:VerticalStructurePart>
          </aixm:part>
          <aixm:part>
            <aixm:VerticalStructurePart gml:id="gml.id28">
              <aixm:verticalExtent uom="FT">60</aixm:verticalExtent>
              <aixm:type>CATENARY</aixm:type>
              <aixm:designator>P3-no-geom</aixm:designator>
            </aixm:VerticalStructurePart>
          </aixm:part>
        </aixm:VerticalStructureTimeSlice>
      </aixm:timeSlice>
    </aixm:VerticalStructure>
  </hasMember>
</AIXMBasicMessage>
"""


def _first_structure(xml_text: str):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_text)
    return root.find(f".//{mod.VERTICAL_STRUCTURE_TAG}")


class IterStructuresTests(unittest.TestCase):
    def test_yields_vertical_structure_elements(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.xml"
            path.write_text(SAMPLE_SINGLE_PART, encoding="utf-8")
            identifiers = []
            count = 0
            for structure in mod.iter_structures(path):
                count += 1
                identifier = structure.find(f"{{http://www.opengis.net/gml/3.2}}identifier")
                identifiers.append(identifier.text)
            self.assertEqual(count, 1)
            self.assertEqual(identifiers, ["TEST-UUID-1"])


class ExtractPartRowsTests(unittest.TestCase):
    def test_single_part_extracts_expected_fields(self):
        structure = _first_structure(SAMPLE_SINGLE_PART)
        rows, skipped = mod.extract_part_rows(structure, "LT", "test.xml")
        self.assertEqual(skipped, 0)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["identifier"], "TEST-UUID-1")
        self.assertEqual(row["interpretation"], "BASELINE")
        self.assertEqual(row["sequenceNumber"], 1)
        self.assertEqual(row["correctionNumber"], 0)
        self.assertEqual(row["beginPosition"], "2026-06-11T00:00:00")
        self.assertEqual(row["featureLifetime_beginPosition"], "2026-06-11T00:00:00")
        self.assertEqual(row["name"], "TEST_TOWER")
        self.assertEqual(row["type"], "TOWER")
        self.assertEqual(row["lighted"], "YES")
        self.assertEqual(row["group"], "NO")
        self.assertEqual(row["part_type"], "TOWER")
        self.assertEqual(row["designator"], "T1")
        self.assertEqual(row["verticalExtent"], 100)
        self.assertEqual(row["verticalExtent_uom"], "FT")
        self.assertEqual(row["elevation"], 200)
        self.assertEqual(row["elevation_uom"], "FT")
        self.assertEqual(row["colour"], "RED")
        self.assertEqual(row["country"], "LT")
        self.assertEqual(row["source_file"], "test.xml")
        self.assertEqual((row["lon"], row["lat"]), (29.0, 40.0))

    def test_multiple_parts_fan_out_join_colours_and_skip_missing_geometry(self):
        structure = _first_structure(SAMPLE_MULTI_PART)
        rows, skipped = mod.extract_part_rows(structure, "LT", "test.xml")
        self.assertEqual(skipped, 1)  # P3-no-geom has no horizontalProjection_location
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["designator"], "P1")
        self.assertEqual(rows[0]["colour"], "RED,WHITE")
        self.assertIsNone(rows[0]["lighted"])
        self.assertEqual(rows[1]["designator"], "P2")
        self.assertIsNone(rows[1]["colour"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -m unittest test_build_obstacles_gpkg -v`
Expected: `AttributeError: module 'build_obstacles_gpkg' has no attribute 'iter_structures'`

- [ ] **Step 3: Implement iter_structures and extract_part_rows**

Append to `build_obstacles_gpkg.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -m unittest test_build_obstacles_gpkg -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add "aeronautical-data/Obstacles/Area-1/build_obstacles_gpkg.py" "aeronautical-data/Obstacles/Area-1/test_build_obstacles_gpkg.py"
git commit -m "Add AIXM VerticalStructure extraction with multi-part fan-out"
```

---

## Task 4: GeoPackage writer with spec-compliant RTree spatial index

No unit tests here — this writes real SQLite/GeoPackage structures and is
verified by running it and inspecting the resulting file directly (Step 4),
the same way every other converter script in this repo is checked.

**Files:**
- Modify: `aeronautical-data/Obstacles/Area-1/build_obstacles_gpkg.py` (append)

- [ ] **Step 1: Implement create_base_gpkg**

Append to `build_obstacles_gpkg.py`:

```python
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
```

- [ ] **Step 2: Implement the RTree spatial index (spec-compliant, 6 triggers)**

Append to `build_obstacles_gpkg.py`:

```python
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
```

- [ ] **Step 3: Implement write_layer**

Append to `build_obstacles_gpkg.py`:

```python
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
```

- [ ] **Step 4: Verify by writing a throwaway GeoPackage and inspecting it**

Run from `aeronautical-data/Obstacles/Area-1/`:
```
py -c "
import sqlite3, build_obstacles_gpkg as mod
con = sqlite3.connect('_verify.gpkg')
mod.create_base_gpkg(con)
mod.write_layer(con, 'obstacles', [
    {'identifier': 'X1', 'lon': 29.0, 'lat': 40.0, 'name': 'T'},
    {'identifier': 'X2', 'lon': 29.1, 'lat': 40.1, 'name': 'U'},
])
print('rows:', con.execute('SELECT count(*) FROM obstacles').fetchone()[0])
print('rtree rows:', con.execute('SELECT count(*) FROM rtree_obstacles_geom').fetchone()[0])
print('triggers:', con.execute(\"SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'rtree_obstacles_geom_%'\").fetchone()[0])
print('extensions:', con.execute('SELECT extension_name FROM gpkg_extensions').fetchone()[0])
con.close()
"
del _verify.gpkg
```
Expected output: `rows: 2`, `rtree rows: 2`, `triggers: 6`, `extensions: gpkg_rtree_index`.

- [ ] **Step 5: Commit**

```bash
git add "aeronautical-data/Obstacles/Area-1/build_obstacles_gpkg.py"
git commit -m "Add spec-compliant GeoPackage writer with RTree spatial index"
```

---

## Task 5: Orchestration (main) + real end-to-end run

**Files:**
- Modify: `aeronautical-data/Obstacles/Area-1/build_obstacles_gpkg.py` (append)

- [ ] **Step 1: Implement main()**

Append to `build_obstacles_gpkg.py`:

```python
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
```

- [ ] **Step 2: Run against the real data**

Run from `aeronautical-data/Obstacles/Area-1/`:
```
py build_obstacles_gpkg.py
```
Expected: prints `LT\LT_ENR_5_4_Obstacles_AIXM_5_1.xml: 7121 structure, 7121 satir, 0 atlandi`,
then `Toplam: 7121 structure, 7121 satir, 0 atlandi (geometri yok)`, then
`Tamamlandi: obstacles.gpkg (...)`.

- [ ] **Step 3: Verify the real output file**

Run:
```
py -c "
import sqlite3
con = sqlite3.connect('obstacles.gpkg')
print('rows:', con.execute('SELECT count(*) FROM obstacles').fetchone()[0])
print('rtree rows:', con.execute('SELECT count(*) FROM rtree_obstacles_geom').fetchone()[0])
print('distinct countries:', con.execute('SELECT DISTINCT country FROM obstacles').fetchall())
print('sample:', con.execute('SELECT identifier, name, type, part_type, designator, elevation, verticalExtent, colour FROM obstacles LIMIT 1').fetchone())
"
```
Expected: `rows: 7121`, `rtree rows: 7121`, `distinct countries: [('LT',)]`, and a
sample row with non-null `identifier`/`name`/`type`/`designator`/`elevation`.

- [ ] **Step 4: Commit**

```bash
git add "aeronautical-data/Obstacles/Area-1/build_obstacles_gpkg.py"
git commit -m "Add main() orchestration for AIXM obstacle GeoPackage converter"
```

(Do not commit `obstacles.gpkg` itself unless the repo already tracks
generated `.gpkg` outputs alongside their source XML — check
`aeronautical-data/Navaids/EAD-SDO/.gitignore` or `git status` for
precedent before adding it.)

---

## Task 6: Launcher batch file

**Files:**
- Create: `aeronautical-data/Obstacles/Area-1/convert_obstacles.bat`

- [ ] **Step 1: Write the batch file**

```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo AIXM Obstacle (VerticalStructure) -> GeoPackage donusturucu
echo =============================================================
echo.

py build_obstacles_gpkg.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo HATA: Donusturme basarisiz! Python kurulu mu?
    pause
    exit /b 1
)

echo.
echo Cikti: %~dp0obstacles.gpkg
echo Katman: obstacles
echo.
pause
```

- [ ] **Step 2: Run it and confirm it matches the Task 5 output**

Run (from `aeronautical-data/Obstacles/Area-1/`):
```
cmd /c convert_obstacles.bat
```
Expected: same summary as Task 5 Step 2, ending in `Cikti: ...\obstacles.gpkg` and `Katman: obstacles`, then waits for a key press.

- [ ] **Step 3: Commit**

```bash
git add "aeronautical-data/Obstacles/Area-1/convert_obstacles.bat"
git commit -m "Add convert_obstacles.bat launcher"
```

---

## Spec Coverage Check

- Discovery of all `Area-1/*/​*.xml` ✅ Task 2 + Task 5
- AIXM field names verified against XSD ✅ Task 3 (matches spec doc table)
- `type`/`part_type`, `beginPosition`/`featureLifetime_beginPosition` collision handling ✅ Task 3
- Multi-part / multi-lighting robustness ✅ Task 3 (`SAMPLE_MULTI_PART` test)
- Point-only geometry, non-point parts skipped and counted ✅ Task 3 (`P3-no-geom` test) + Task 5 (`atlandi` counter)
- `country` / `source_file` provenance columns ✅ Task 3
- GeoPackage spec-compliant RTree spatial index (not just a static table) ✅ Task 4
- Output at `Area-1/obstacles.gpkg`, single `obstacles` layer ✅ Task 5
- `convert_obstacles.bat` launcher matching repo convention ✅ Task 6
- Error tolerance (non-AIXM file skip, existing file PermissionError) ✅ Task 2 (`looks_like_aixm`) + Task 5 (`main`)
