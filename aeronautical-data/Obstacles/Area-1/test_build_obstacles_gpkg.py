"""build_obstacles_gpkg.py icin birim testleri (stdlib unittest, harici bagimlilik yok)."""

import struct
import tempfile
import unittest
from pathlib import Path

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


class ToNumTests(unittest.TestCase):
    def test_integer_text_returns_int(self):
        self.assertEqual(mod.to_num("827"), 827)
        self.assertIsInstance(mod.to_num("827"), int)

    def test_decimal_text_is_preserved(self):
        # LH verisi metre cinsinden ondalikli: int() zorlanirsa deger kaybolur
        self.assertEqual(mod.to_num("309.6"), 309.6)

    def test_trailing_zero_decimal_returns_int(self):
        self.assertEqual(mod.to_num("100.0"), 100)
        self.assertIsInstance(mod.to_num("100.0"), int)

    def test_negative_decimal(self):
        self.assertEqual(mod.to_num("-12.5"), -12.5)

    def test_none(self):
        self.assertIsNone(mod.to_num(None))

    def test_invalid(self):
        self.assertIsNone(mod.to_num("not-a-number"))

    def test_non_numeric_aixm_vertical_codes_are_ignored(self):
        # ValDistanceVerticalType UNL/GND/FLOOR/CEILING de kabul ediyor
        self.assertIsNone(mod.to_num("UNL"))


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
              <aixm:verticalExtent uom="M">55.5</aixm:verticalExtent>
              <aixm:type>CATENARY</aixm:type>
              <aixm:designator>P2</aixm:designator>
              <aixm:horizontalProjection_location>
                <aixm:ElevatedPoint gml:id="gml.id27" srsName="urn:ogc:def:crs:EPSG::4326">
                  <gml:pos>41.001 30.001</gml:pos>
                  <aixm:elevation uom="M">11.4</aixm:elevation>
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
        # Ondalikli metre degerleri (LH verisi gibi) yuvarlanmadan korunmali
        self.assertEqual(rows[1]["verticalExtent"], 55.5)
        self.assertEqual(rows[1]["verticalExtent_uom"], "M")
        self.assertEqual(rows[1]["elevation"], 11.4)
        self.assertEqual(rows[1]["elevation_uom"], "M")


if __name__ == "__main__":
    unittest.main()
