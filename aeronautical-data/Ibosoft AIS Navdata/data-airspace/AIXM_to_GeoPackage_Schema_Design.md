# Airspace Data AIXM Mapping

> **Base endpoint:** none\
> **Reference documents:** AIXM 5.2 schema set (aixm.aero) · RFC 7946 The GeoJSON Format\
> **Attribution:** show `{{BRAND_AIS}}` wherever this data is displayed\
> **Data sources:** none\
> **Last updated:** 18 OCT 2026

How the airspace data in AIXM maps to the columns of the Airspace GeoPackage. Every AIXM property of `Airspace` has a column or a place in a JSON column; a column can be empty when no source provides that property.

For the extension elements (`ibosoftais:*`) see [AIXM Schema Extension](aixm-schema-annex.md); for coding rules (provenance, geometry) see [Data Coding Policies](data-coding-policies.md). The naming rules and the common column families are the same as in the [ATS Data AIXM Mapping](ats-data-aixm-mapping.md).

---

## Layer

| Layer | AIXM feature | Geometry |
|---|---|---|
| `airspaces` | `Airspace` | MULTIPOLYGON (EPSG:4326) |

The layer also has `id` (INTEGER primary key) and `geom`. **Each airspace is one row**: an airspace with several classes or several geometry components is not split into rows.

---

## Naming rules

| Rule | Pattern | Example |
|---|---|---|
| AIXM property | `airspaces_<AIXM name>` | `airspaces_designator` |
| Field of a sub-object | camelCase joined | `airspaces_locationLatitude`, `airspaces_contributorAirspaceUuid` |
| Unit / vertical reference | `<field>Uom`, `<field>Reference` | `airspaces_upperLimitUom` |
| Reference to another feature | `…Uuid` (the target's `gml:identifier`) | `airspaces_protectedRouteUuid` |
| Repeated (0..∞) structure | full JSON | `airspaces_class` |
| Common families (no prefix) | `annotation*`, `data_*`, `aixm_*` | `annotationRemark` |
| Derived (no AIXM counterpart) | own family prefix | `airspaceLabeling_classifications` |

JSON keeps the whole AIXM subtree: an element with `xlink:href` becomes `{"href": "<uuid>"}`, a value with a unit becomes `{"value": …, "uom": …}`; only technical attributes such as `gml:id` are left out.

---

## Columns

### Airspace

| AIXM | Column | Type |
|---|---|---|
| `type` | `airspaces_type` | TEXT |
| `designator` | `airspaces_designator` | TEXT |
| `localType` | `airspaces_localType` | TEXT |
| `name` | `airspaces_name` | TEXT |
| `designatorICAO` | `airspaces_designatorICAO` | TEXT |
| `controlType` | `airspaces_controlType` | TEXT |
| `upperLowerSeparation` (+`uom`) | `airspaces_upperLowerSeparation`, `airspaces_upperLowerSeparationUom` | REAL, TEXT |
| `class` (0..∞) | `airspaces_class` | TEXT (JSON array: `classification`, `associatedLevels`, `timeInterval`, `annotation`, `specialDateAuthority`) |
| `protectedRoute` | `airspaces_protectedRouteUuid` | TEXT |
| `geometryComponent` (0..∞) | `geom` (calculated, see [Geometry](#geometry)), `airspaces_geometryComponent` (JSON) and the BASE volume columns | — |
| `activation` (0..∞) | `airspaces_activation` | TEXT (JSON array: `activity`, `status`, `levels`, `user`, `aircraft`, `timeInterval`, `annotation`, `specialDateAuthority`) |
| `annotation` (0..∞) | `annotationDescription`, `annotationRemark`, `annotationWarning`, `annotationDisclaimer` | TEXT |

`class` and `activation` are kept as full JSON arrays and are not reduced to single columns: an airspace can have several classes (each for its own levels) and several activations.

Example `airspaces_class` of an FIR with a class C layer:

```json
[{"classification": "C",
  "associatedLevels": {"AirspaceLayer": {
      "upperLimit": {"uom": "FL", "value": "660"}, "upperLimitReference": "STD",
      "lowerLimit": {"uom": "FL", "value": "305"}, "lowerLimitReference": "STD"}}}]
```

Annotation columns and separators work as in the [ATS Data AIXM Mapping › Annotation](ats-data-aixm-mapping.md#annotation).

### Geometry component and volume

`airspaces_geometryComponent` holds **all** components as a JSON array: `operation`, `operationSequence`, `annotation` and `theAirspaceVolume` with all its fields. The geometries are not repeated in the JSON: `horizontalProjection` is in `geom`, `centreline` in `airspaces_centreline`.

The volume fields of the **BASE** component are also in single columns (the fields of the other components are only in the JSON):

| AIXM (`AirspaceVolume`) | Column | Type |
|---|---|---|
| `upperLimit` (+`uom`), `upperLimitReference` | `airspaces_upperLimit`, `airspaces_upperLimitUom`, `airspaces_upperLimitReference` | TEXT |
| `maximumLimit` (+`uom`), `maximumLimitReference` | `airspaces_maximumLimit`, `airspaces_maximumLimitUom`, `airspaces_maximumLimitReference` | TEXT |
| `lowerLimit` (+`uom`), `lowerLimitReference` | `airspaces_lowerLimit`, `airspaces_lowerLimitUom`, `airspaces_lowerLimitReference` | TEXT |
| `minimumLimit` (+`uom`), `minimumLimitReference` | `airspaces_minimumLimit`, `airspaces_minimumLimitUom`, `airspaces_minimumLimitReference` | TEXT |
| `width` (+`uom`) | `airspaces_width`, `airspaces_widthUom` | REAL, TEXT |
| `horizontalProjection` | `geom` | MULTIPOLYGON |
| `centreline` | `airspaces_centreline` | TEXT (WKT LineString, longitude latitude) |
| `contributorAirspace/AirspaceVolumeDependency/dependency` | `airspaces_contributorAirspaceDependency` | TEXT |
| `contributorAirspace/AirspaceVolumeDependency/theAirspace` | `airspaces_contributorAirspaceUuid` | TEXT |
| `name` | `airspaces_volumeName` | TEXT |
| `location` | `airspaces_locationLatitude`, `airspaces_locationLongitude` | REAL |
| `annotation` | in `airspaces_geometryComponent` | — |

> **Vertical limits are TEXT.** An AIXM limit is a number **or** a text value such as `UNL`, `GND`, `FLOOR` or `CEILING`, and both occur in the data. A numeric column would turn the text values into NULL, and the reference column cannot tell `UNL` apart. The value is carried as written in AIXM.

### Extension, provenance, identity

| AIXM | Column |
|---|---|
| `extension/ibosoftais:AirspaceExtension/regionIcao` | `airspaces_regionIcao` (FIR/UIR) |
| `extension/ibosoftais:AirspaceExtension/regionSupProc` | `airspaces_regionSupProc` (FIR/UIR) |
| `extension/ibosoftais:AirspaceDataProvenance/dataProvider` | `data_provider` |
| `extension/ibosoftais:AirspaceDataProvenance/dataOriginator` | `data_originator` (NULL when the source does not state it) |
| `extension/ibosoftais:AirspaceDataProvenance/dataEffectivity` | `data_effectivity` |
| `gml:id` | `aixm_gml_id` |
| `gml:identifier` | `aixm_uuid` |

Region values are as published by the source; see [AIXM Schema Extension › Airspace](aixm-schema-annex.md#airspace). Provenance coding: [Data Coding Policies › Provenance](data-coding-policies.md#provenance).

### TimeSlice and feature base

| AIXM | Column |
|---|---|
| `gml:validTime` begin / end | `aixm_validTimeBegin`, `aixm_validTimeEnd` |
| `interpretation` | `aixm_interpretation` |
| `sequenceNumber`, `correctionNumber` | `aixm_sequenceNumber`, `aixm_correctionNumber` (INTEGER) |
| `featureLifetime` | `aixm_featureLifetimeBegin`, `aixm_featureLifetimeEnd` |
| `timeSliceMetadata` | `aixm_timeSliceMetadata` (JSON) |
| `featureMetadata` | `aixm_featureMetadata` (JSON) |
| `gml:description` | `aixm_description` |
| `gml:name` (0..∞) | `aixm_name` (JSON array) |
| `gml:boundedBy` | — (envelope of `geom`) |

The begin of `gml:validTime` is `unknown`: the sources give the effectivity of the data set, not of each airspace. The data set effectivity is in `data_effectivity`.

### Derived: `airspaceLabeling_*`

| Column | Rule |
|---|---|
| `airspaceLabeling_classifications` | The class letters, comma-separated (e.g. `C,D`), **in the order written in AIXM**. NULL when the airspace has no class |

For filters and labels. The full class information with levels is in `airspaces_class`. The list is not sorted by level: the level references of class bands can be mixed (`FT MSL` / `FL`) and cannot be compared without conversion.

---

## Geometry

`geom` is calculated from the geometry components:

1. Components are ordered by `operationSequence`.
2. The first component must be the only `BASE`.
3. The polygon of each component is read from `horizontalProjection` (`PolygonPatch` exterior ring and `interior` holes).
4. Starting from `BASE`, the operations are applied: `UNION` union, `SUBTR` difference, `INTERS` intersection.
5. The result is a MultiPolygon split at ±180° (antimeridian).
6. Ring orientation follows RFC 7946 §3.1.6: exterior counter-clockwise, holes clockwise (see [Data Coding Policies › Area Geometry Coding](data-coding-policies.md#area-geometry-coding)).

A component without a polygon (only `centreline`/`width`, or `contributorAirspace`) cannot be calculated; no polygon is invented for it, and such an airspace is not in the layer.

---

## Values in the data

| Topic | Value |
|---|---|
| Names | AIXM `TextNameType` allows ASCII only; national characters are transliterated (e.g. `İ` → `I`) |
| Class not in the AIXM code list | Written with the AIXM extension pattern, e.g. `OTHER:GSEC` |

---

## Indexes

| Index | Applies to |
|---|---|
| R-Tree (`rtree_airspaces_geom`, GeoPackage RTree extension) | `geom` |
| B-Tree | every attribute column |

---

## Changes from the previous airspace schema

| Previous column | New column | Reason |
|---|---|---|
| `type`, `designator`, `name`, `localType`, `designatorICAO`, `controlType` | `airspaces_<same>` | Same naming rule as ATS |
| `classification` (single) | `airspaces_class` (JSON) and `airspaceLabeling_classifications` | In AIXM `class` is 0..∞ and tied to levels |
| `upperLimit…`, `lowerLimit…` | `airspaces_upperLimit…`, `airspaces_lowerLimit…` (BASE volume) | Their AIXM place is `AirspaceVolume` |
| `activity`, `status` (single) | `airspaces_activation` (JSON) | In AIXM `activation` is 0..∞ |
| `annotation*` | same (no prefix) | Same as ATS |
| `data_provider`, `data_originator`, `data_effectivity` | same | Same as ATS |
| `add_date` | removed | It was the production time of the file, not data |
| `horizontalProjection` (geometry column) | `geom` | Same as ATS |
| — | `aixm_*`, `maximum/minimumLimit`, `width`, `centreline`, `location`, `contributorAirspace…`, `protectedRouteUuid`, `upperLowerSeparation`, `volumeName`, `geometryComponent`, `regionIcao`, `regionSupProc` | AIXM properties that were not mapped before |
