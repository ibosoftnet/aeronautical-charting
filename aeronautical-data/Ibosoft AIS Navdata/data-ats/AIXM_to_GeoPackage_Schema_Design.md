# ATS Data AIXM Mapping

> **Base endpoint:** none\
> **Reference documents:** AIXM 5.2 schema set (aixm.aero) · ICAO Doc 10066 PANS-AIM, Ed. 1, Amend. 3 (28/11/24) · ITU-R M.1677-1 International Morse code\
> **Attribution:** show `{{BRAND_AIS}}` wherever this data is displayed\
> **Data sources:** none\
> **Last updated:** 18 OCT 2026

How the ATS data in AIXM maps to the columns of the ATS GeoPackage. Every AIXM property of the mapped features has a column; a column can be empty when no source provides that property. Derived columns (map labelling, symbology, route network status) have no AIXM counterpart and are described in their own sections.

For the extension elements (`ibosoftais:*`) see [AIXM Schema Extension](aixm-schema-annex.md); for coding rules (provenance, antimeridian, geometry) see [Data Coding Policies](data-coding-policies.md).

---

## Layers

| Layer | AIXM feature | Geometry |
|---|---|---|
| `designatedPoints` | `DesignatedPoint` | POINT |
| `navaids` | `Navaid` | POINT |
| `navaidComponents` | `NavaidComponent` + the linked navaid equipment (`VOR`, `DME`, `TACAN`, `NDB`, `Localizer`, `Glidepath`, `MarkerBeacon`, `SDF`, `Azimuth`, `Elevation`, `DirectionFinder`) | POINT |
| `routeSegments` | `RouteSegment` (+ its `Route`) | LINESTRING |
| `changeOverPoints` | `ChangeOverPoint` (+ its `RoutePortion`) | LINESTRING |

Every layer also has `id` (INTEGER primary key) and `geom`. Coordinates are WGS 84 (EPSG:4326).

**Why there is no `Route` layer.** The attributes of a `Route` are carried on each of its segments in the `route_*` columns of `routeSegments` (and partly of `changeOverPoints`), so one table shows both segment and route information.

**Why there is no `points` layer.** `aixm:Point` is not an AIXM feature (it has no identifier or TimeSlice of its own); it is embedded in the feature that uses it. Points that must exist on their own, such as the antimeridian crossing points, are coded as `DesignatedPoint` (`type = OTHER`).

**Why `changeOverPoints` is a line.** A change-over point is a point, but AIP ENR 3 publishes only its distances from the navaids at the two ends, not its coordinates. Calculating coordinates would add data the source does not give. The layer therefore carries the **route portion** the COP applies to as a line that **starts at the start point** of the portion; `copSymbology_offsetPercent` places the COP symbol along that line.

---

## Naming rules

| Rule | Pattern | Example |
|---|---|---|
| Column | `<layer>_<AIXM property, camelCase>` | `navaids_type` |
| Unit of measurement | `<field>Uom` | `routeSegments_lengthUom` |
| Vertical reference | `<field>Reference` | `routeSegments_upperLimitReference` |
| Sub-fields of `location` | `<layer>_location<Field>` | `navaids_locationElevation` |
| Equipment-specific field | `navaidComponents_<Equipment>_<field>` | `navaidComponents_Glidepath_slope` |
| Field inherited from `Route` | `route_<field>` | `route_designatorNumber` |
| Segment end point | `routeSegments_<start\|end><Field>` | `routeSegments_startFlyOver` |

**Columns without layer prefix.** Families that have the same structure in every layer carry no layer prefix:

| Family | Columns | Layers |
|---|---|---|
| Annotation | `annotationDescription`, `annotationRemark`, `annotationWarning`, `annotationDisclaimer` | all |
| Provenance | `data_provider`, `data_originator`, `data_effectivity` | all |
| AIXM identity and base | `aixm_gml_id`, `aixm_uuid` and 11 TimeSlice/feature base columns | all |
| Route network status (derived) | `atsStatus_*` | `designatedPoints`, `navaids`; 7 of them also in `changeOverPoints` |
| Navaid ↔ component link | `associatedComponent_<Equipment>`, `associatedNavaid`, `associatedNavaidType` | `navaids`, `navaidComponents` |
| Map label (derived) | `navaidLabeling_*` | `navaids`, `navaidComponents` |
| Symbol geometry (derived) | `navaidSymbology_*` | `navaids`, `navaidComponents` |
| Route of a COP | `associatedRoute_uuid`, `associatedRouteSegment_*` | `changeOverPoints` |
| COP symbol (derived) | `copSymbology_*` | `changeOverPoints` |

**Column types.**

| Type | Columns |
|---|---|
| TEXT | `*Uom`, `*Reference`, codes, names, JSON, comma-separated lists |
| INTEGER | resolved row ids (`…Id`), `aixm_sequenceNumber`, `aixm_correctionNumber` |
| REAL | numeric values (frequency, slope, angles, length, limits, elevation …) |
| BOOLEAN | `atsStatus_*` flags (stored as 0/1) |

Vertical limits of route segments are REAL: text values such as `UNL` or `GND` cannot be stored as numbers and stay NULL; use the `*Reference` column to tell them apart.

---

## Common columns

### Relation columns

| Form | Holds | Example |
|---|---|---|
| `…Id` | **GeoPackage row id** of the target | `routeSegments_startPointId` |
| `…Uuid` | **AIXM `gml:identifier`** of the target | `changeOverPoints_startPointUuid` |
| `…Layer` | Layer of the target (`navaids` or `designatedPoints`) | `routeSegments_startPointLayer` |
| `associated…` | A link to something that is not a layer, or that has no AIXM counterpart | `associatedNavaid`, `associatedRoute_uuid` |

Lists (`associated…`) are comma-separated and their order is meaningful where stated.

### Identity

| Column | AIXM | Meaning |
|---|---|---|
| `aixm_gml_id` | `gml:id` | Identifier inside the AIXM file. It shows the source in readable form but may change when the file is produced again |
| `aixm_uuid` | `gml:identifier` (`codeSpace="urn:uuid:"`) | Permanent identifier, upper case. All AIXM cross-references (`xlink:href="urn:uuid:…"`) point to it; the same point keeps the same uuid from cycle to cycle |

In two layers a row is built from two AIXM objects and the identity is that of one of them:

- `navaidComponents`: the identity of the **navaid equipment feature**. `NavaidComponent` is an AIXM object with no identifier of its own. One piece of equipment can belong to several navaids; the links are in `associatedNavaid`.
- `routeSegments`: the identity of the **RouteSegment**. The identity of the `Route` is not carried; the route is identified by its `route_designator*` fields.

### AIXM base

From `AbstractAIXMFeature` / `AbstractAIXMTimeSlice`. When a time has no value, the GML `indeterminatePosition` (`unknown` …) is written to the same column.

| Column | AIXM |
|---|---|
| `aixm_validTimeBegin` / `aixm_validTimeEnd` | `gml:validTime` (TimePeriod begin/end; for a TimeInstant only begin) |
| `aixm_interpretation` | `interpretation` |
| `aixm_sequenceNumber` / `aixm_correctionNumber` | same names (INTEGER) |
| `aixm_featureLifetimeBegin` / `aixm_featureLifetimeEnd` | `featureLifetime` |
| `aixm_timeSliceMetadata` | `timeSliceMetadata` (JSON) |
| `aixm_featureMetadata` | `featureMetadata` (JSON) |
| `aixm_description` | `gml:description` |
| `aixm_name` | `gml:name` 0..∞ (JSON array) |

`gml:boundedBy` has no column; it is the envelope of `geom`.

### Provenance

From the `ibosoftais:<Feature>DataProvenance` extension element ([AIXM Schema Extension](aixm-schema-annex.md)). Coding: [Data Coding Policies › Provenance](data-coding-policies.md#provenance).

| Column | Extension element |
|---|---|
| `data_provider` | `dataProvider` |
| `data_originator` | `dataOriginator` — NULL when the source does not state it |
| `data_effectivity` | `dataEffectivity` — effectivity of the source data set; the validity of the feature is in `aixm_validTime*` |

### Annotation

`annotation/Note/purpose` decides the column; a note without `purpose` goes to `annotationRemark`. No note is dropped.

| Column | `purpose` |
|---|---|
| `annotationDescription` | `DESCRIPTION` |
| `annotationRemark` | `REMARK` |
| `annotationWarning` | `WARNING` |
| `annotationDisclaimer` | `DISCLAIMER` |

| Case | Separator |
|---|---|
| Several notes of the **same** feature in one column | new line |
| Notes of **different** features in one column | an empty line |

A row can hold the notes of two features:

| Layer | Order of the notes |
|---|---|
| `routeSegments` | the `RouteSegment`'s notes, then its `Route`'s notes |
| `navaidComponents` | the equipment's notes, then the `NavaidComponent`'s notes |
| `changeOverPoints` | the `ChangeOverPoint`'s notes, then its `Route`'s notes |

---

## Repeated (0..∞) structures

Repeated AIXM structures are stored as **JSON** in a TEXT column. The whole subtree is kept; only technical attributes such as `gml:id` are left out. An element with `xlink:href` becomes `{"href": "<uuid>"}`; a value with a unit becomes `{"value": …, "uom": …}`.

| AIXM property | Layer | Column | Form |
|---|---|---|---|
| `designCriteria` | routeSegments | `routeSegments_designCriteria` | comma-separated text |
| `availability` | routeSegments, navaids, navaidComponents | `…_availability` | JSON array (incl. `levels`) |
| `aircraftCapability` | routeSegments | `routeSegments_aircraftCapability` | JSON array |
| `airspaceClass` | routeSegments | `routeSegments_airspaceClass` | JSON array (incl. `associatedLevels`) |
| `minimumEnrouteAltitude` | routeSegments | `routeSegments_minimumEnrouteAltitude` | JSON array |
| `facilityMakeup` | routeSegments start/end | `routeSegments_startFacilityMakeup`, `routeSegments_endFacilityMakeup` | JSON (incl. distance and angle references) |
| `fix` | designatedPoints | `designatedPoints_fix` | JSON (`PointReference`) |
| `monitoring` | navaidComponents | `navaidComponents_monitoring` | JSON array |
| `navaidEquipment` | navaids | — | the `navaidComponents` layer and the navaid ↔ component link |

**Properties defined on both `Route` and `RouteSegment`:**

| Property | In `routeSegments` |
|---|---|
| `aircraftCapability` | The segment's own value; if the segment has none, the route's |
| `designCriteria` | The segment's own value; if the segment has none, the route's (AIXM allows it on the route) |
| `annotation` | Both, segment notes first |
| `availability` | The segment's only |

---

## `designatedPoints`

Source: `DesignatedPointTimeSlice`. Geometry: `location/Point/gml:pos`.

| Column | AIXM | Type |
|---|---|---|
| `designatedPoints_designator` | `designator` | TEXT |
| `designatedPoints_type` | `type` | TEXT |
| `designatedPoints_name` | `name` | TEXT |
| `designatedPoints_codeICAOCountry` | `codeICAOCountry` | TEXT |
| `designatedPoints_fix` | `fix` | TEXT (JSON) |
| `annotation*` (4) | `annotation` | TEXT |
| `data_*` (3) | provenance | TEXT |
| `atsStatus_*` (13) | derived | see [Route network status](#route-network-status-atsstatus) |
| `aixm_*` (13) | identity and base | see [Common columns](#common-columns) |

---

## `navaids`

Source: `NavaidTimeSlice`. Geometry: `location/ElevatedPoint` (or `Point`). Route segment end points resolve to this layer.

| Column | AIXM | Type |
|---|---|---|
| `navaids_type` | `type` | TEXT |
| `navaids_designator` | `designator` | TEXT |
| `navaids_name` | `name` | TEXT |
| `navaids_flightChecked` | `flightChecked` | TEXT |
| `navaids_purpose` | `purpose` | TEXT |
| `navaids_signalPerformance` | `signalPerformance` | TEXT |
| `navaids_courseQuality` | `courseQuality` | TEXT |
| `navaids_integrityLevel` | `integrityLevel` | TEXT |
| `navaids_codeICAOCountry` | `codeICAOCountry` | TEXT |
| `navaids_locationElevation` (+`Uom`) | `location/ElevatedPoint/elevation` | REAL / TEXT |
| `navaids_locationGeoidUndulation` | `location/ElevatedPoint/geoidUndulation` | REAL |
| `navaids_locationVerticalDatum` | `location/ElevatedPoint/verticalDatum` | TEXT |
| `navaids_locationHorizontalAccuracy` (+`Uom`) | `location/ElevatedPoint/horizontalAccuracy` | REAL / TEXT |
| `navaids_availability` | `availability` | TEXT (JSON) |
| `associatedComponent_<Equipment>` (11) | navaid ↔ component link | TEXT (list) |
| `annotation*` (4) | `annotation` | TEXT |
| `data_*` (3) | provenance | TEXT |
| `atsStatus_*` (13) | derived | see [Route network status](#route-network-status-atsstatus) |
| `navaidLabeling_*` (9) | derived | see [Map labels](#map-labels-navaidlabeling) |
| `navaidSymbology_declination` | derived | see [Symbol geometry](#symbol-geometry-navaidsymbology) |
| `aixm_*` (13) | identity and base | see [Common columns](#common-columns) |

> **ILS family name (temporary).** For `ILS`, `ILS_DME`, `LOC` and `LOC_DME` navaids and their Localizer / Glidepath components the sources give no `name`; the runway direction is written there instead (`RWY 04R`). For ILS DME components it is added after the existing name (`BRUSSELS NATIONAL RWY 25R`). The correct AIXM place is the `runwayDirection` association; this will change when aerodrome and runway features are added.

---

## `navaidComponents`

One row per navaid equipment. The fields of the `NavaidComponent` and of the linked equipment feature are flattened into one row:

```
Navaid.navaidEquipment (0..∞) → NavaidComponent → theNavaidEquipment → equipment feature (VOR, DME …)
```

Each row has its **own position** (the localizer, glide path and DME of an ILS are three points).

### Common columns

| Column | AIXM | Type |
|---|---|---|
| `navaidComponents_equipmentType` | equipment feature type (`VOR`, `DME`, `TACAN`, `NDB`, `Localizer`, `Glidepath`, `MarkerBeacon`, `SDF`, `Azimuth`, `Elevation`, `DirectionFinder`) | TEXT |
| `associatedNavaid` | parent `navaids.id` list | TEXT (list) |
| `associatedNavaidType` | `navaids_type` of each parent, same order | TEXT (list) |
| `navaidComponents_collocationGroup` | `NavaidComponent/collocationGroup` | TEXT |
| `navaidComponents_markerPosition` | `NavaidComponent/markerPosition` | TEXT |
| `navaidComponents_providesNavigableLocation` | `NavaidComponent/providesNavigableLocation` | TEXT |
| `navaidComponents_designator` | `designator` | TEXT |
| `navaidComponents_name` | `name` | TEXT |
| `navaidComponents_emissionClass` | `emissionClass` | TEXT |
| `navaidComponents_mobile` | `mobile` | TEXT |
| `navaidComponents_magneticVariation` | `magneticVariation` | REAL |
| `navaidComponents_dateMagneticVariation` | `dateMagneticVariation` | TEXT |
| `navaidComponents_flightChecked` | `flightChecked` | TEXT |
| `navaidComponents_locationElevation` (+`Uom`) | `location/ElevatedPoint/elevation` | REAL / TEXT |
| `navaidComponents_locationGeoidUndulation` | `location/ElevatedPoint/geoidUndulation` | REAL |
| `navaidComponents_locationVerticalDatum` | `location/ElevatedPoint/verticalDatum` | TEXT |
| `navaidComponents_locationHorizontalAccuracy` (+`Uom`) | `location/ElevatedPoint/horizontalAccuracy` | REAL / TEXT |
| `navaidComponents_monitoring` | `monitoring` | TEXT (JSON) |
| `navaidComponents_availability` | `availability` | TEXT (JSON) |
| `annotation*` (4) | `annotation` (equipment, then component) | TEXT |
| `data_*` (3) | provenance | TEXT |
| `navaidLabeling_*` (9) | derived | see [Map labels](#map-labels-navaidlabeling) |
| `navaidSymbology_*` (2) | derived | see [Symbol geometry](#symbol-geometry-navaidsymbology) |
| `aixm_*` (13) | identity and base of the equipment feature | see [Common columns](#common-columns) |

### Equipment-specific columns

A field that belongs to one equipment type is named `navaidComponents_<Equipment>_<field>`. The same AIXM name can exist in several equipment types with **different code lists** (`type`, `class`, `channel`), so each type has its own column. The table is sparse: only the columns of the row's own equipment type have values.

| Equipment | Fields |
|---|---|
| `VOR` | `type`, `frequency` (+`Uom`), `zeroBearingDirection`, `declination` |
| `DME` | `type`, `channel`, `displace` (+`Uom`), `tuningFrequencyVHF` (+`Uom`) |
| `TACAN` | `channel`, `declination`, `tuningFrequencyVHF` (+`Uom`) |
| `Localizer` | `frequency` (+`Uom`), `magneticBearing`, `trueBearing`, `declination`, `widthCourse`, `backCourseUsable`, `signalPerformance`, `courseQuality`, `integrityLevel` |
| `Glidepath` | `frequency` (+`Uom`), `slope`, `rdh` (+`Uom`), `signalPerformance`, `courseQuality`, `integrityLevel` |
| `MarkerBeacon` | `class`, `frequency` (+`Uom`), `axisBearing`, `auralMorseCode` |
| `NDB` | `frequency` (+`Uom`), `class`, `emissionBand` |
| `SDF` | `frequency` (+`Uom`), `magneticBearing`, `trueBearing` |
| `Azimuth` | `type`, `channel`, `trueBearing`, `magneticBearing`, `angleProportionalLeft`, `angleProportionalRight`, `angleCoverLeft`, `angleCoverRight` |
| `Elevation` | `angleNominal`, `angleMinimum`, `angleSpan` |
| `DirectionFinder` | `doppler` |

Example: `navaidComponents_VOR_frequency`, `navaidComponents_DME_channel`, `navaidComponents_NDB_class`.

### Navaid ↔ component link

The AIXM relation is many-to-many and is shown from both sides:

| Layer | Column | Content |
|---|---|---|
| `navaids` | `associatedComponent_<Equipment>` (11) | `navaidComponents.id` list of that equipment type |
| `navaidComponents` | `associatedNavaid` | parent `navaids.id` list |
| `navaidComponents` | `associatedNavaidType` | parent `navaids_type` list, in the same order |

Lists are used because a navaid can have several components of one type (e.g. outer and middle marker of an ILS) and one piece of equipment can be shared by several navaids (e.g. a DME used by two navaids).

```
navaids          id=12     associatedComponent_Localizer    = "24"
                           associatedComponent_Glidepath    = "25"
                           associatedComponent_DME          = "26"
                           associatedComponent_MarkerBeacon = "13290,13291"

navaidComponents id=13290  MarkerBeacon MIDDLE  associatedNavaid = "12"  associatedNavaidType = "ILS_DME"
                 id=13291  MarkerBeacon OUTER   associatedNavaid = "12"  associatedNavaidType = "ILS_DME"
```

---

## `routeSegments`

Source: `RouteSegmentTimeSlice` and the `Route` it belongs to (`routeFormed`). Geometry: `curveExtent` (`gml:posList`). Route segments crossing the antimeridian are split (see [Data Coding Policies](data-coding-policies.md#line-geometry-coding)).

### Segment

| Column | AIXM | Type |
|---|---|---|
| `routeSegments_level` | `level` | TEXT |
| `routeSegments_upperLimit` (+`Uom`, +`Reference`) | `upperLimit` | REAL / TEXT |
| `routeSegments_lowerLimit` (+`Uom`, +`Reference`) | `lowerLimit` | REAL / TEXT |
| `routeSegments_minimumObstacleClearanceAltitude` (+`Uom`) | `minimumObstacleClearanceAltitude` | REAL / TEXT |
| `routeSegments_pathType` | `pathType` | TEXT |
| `routeSegments_trueTrack` | `trueTrack` | REAL |
| `routeSegments_magneticTrack` | `magneticTrack` | REAL |
| `routeSegments_reverseTrueTrack` | `reverseTrueTrack` | REAL |
| `routeSegments_reverseMagneticTrack` | `reverseMagneticTrack` | REAL |
| `routeSegments_length` (+`Uom`) | `length` | REAL / TEXT |
| `routeSegments_widthLeft` (+`Uom`) | `widthLeft` | REAL / TEXT |
| `routeSegments_widthRight` (+`Uom`) | `widthRight` | REAL / TEXT |
| `routeSegments_turnDirection` | `turnDirection` | TEXT |
| `routeSegments_signalGap` | `signalGap` | TEXT |
| `routeSegments_minimumEnrouteAltitude` | `minimumEnrouteAltitude` | TEXT (JSON) |
| `routeSegments_minimumCrossingAtEnd` (+`Uom`, +`Reference`) | `minimumCrossingAtEnd` | REAL / TEXT |
| `routeSegments_maximumCrossingAtEnd` (+`Uom`, +`Reference`) | `maximumCrossingAtEnd` | REAL / TEXT |
| `routeSegments_designatorSuffix` | `designatorSuffix` | TEXT |
| `routeSegments_availability` | `availability` | TEXT (JSON) |
| `routeSegments_cardinalDirectionLeft` / `…Right` | `cardinalDirectionLeft` / `cardinalDirectionRight` | TEXT |
| `routeSegments_aircraftCapability` | `aircraftCapability` (segment, else route) | TEXT (JSON) |
| `routeSegments_airspaceClass` | `airspaceClass` | TEXT (JSON) |
| `routeSegments_designCriteria` | `designCriteria/name` (segment, else route) | TEXT (list) |

### End points

From `start/EnRouteSegmentPoint` and `end/EnRouteSegmentPoint`. The table shows `start`; the same columns exist with `routeSegments_end…`.

| Column | AIXM | Type |
|---|---|---|
| `routeSegments_startPointLayer` | layer of the resolved point (`navaids` / `designatedPoints`) | TEXT |
| `routeSegments_startPointId` | row id of the resolved point | INTEGER |
| `routeSegments_startPointDesignator` | designator of the resolved point | TEXT |
| `routeSegments_startReportingATC` | `reportingATC` | TEXT |
| `routeSegments_startFlyOver` | `flyOver` | TEXT |
| `routeSegments_startWaypoint` | `waypoint` | TEXT |
| `routeSegments_startRadarGuidance` | `radarGuidance` | TEXT |
| `routeSegments_startFacilityMakeup` | `facilityMakeup` | TEXT (JSON) |
| `routeSegments_startRoleFreeFlight` | `roleFreeFlight` | TEXT |
| `routeSegments_startRoleRVSM` | `roleRVSM` | TEXT |
| `routeSegments_startTurnRadius` (+`Uom`) | `turnRadius` | REAL / TEXT |
| `routeSegments_startRoleMilitaryTraining` | `roleMilitaryTraining` | TEXT |

`pointChoice_fixDesignatedPoint` resolves to `designatedPoints`, `pointChoice_navaidSystem` to `navaids`. If a point cannot be resolved, its `Layer`/`Id`/`Designator` columns stay empty; the segment is still written.

### Inherited from `Route`

The `route_` prefix (not `routeSegments_`) shows that these are properties of the `Route` feature.

| Column | AIXM (`RouteTimeSlice`) |
|---|---|
| `route_designatorPrefix` | `designatorPrefix` |
| `route_designatorSecondLetter` | `designatorSecondLetter` |
| `route_designatorNumber` | `designatorNumber` |
| `route_multipleIdentifier` | `multipleIdentifier` |
| `route_locationDesignator` | `locationDesignator` |
| `route_name` | `name` |
| `route_type` | `type` |
| `route_flightRule` | `flightRule` |
| `route_internationalUse` | `internationalUse` |
| `route_militaryUse` | `militaryUse` |
| `route_militaryTrainingType` | `militaryTrainingType` |

The route code is split in AIXM (`designatorPrefix` + `designatorSecondLetter` + `designatorNumber` + `multipleIdentifier`); the full code is also written to `route_name`.

Plus `annotation*` (segment, then route), `data_*` and `aixm_*` of the RouteSegment.

---

## `changeOverPoints`

Source: `ChangeOverPointTimeSlice` and its `applicableRoutePortion/RoutePortion`. Geometry: the route portion as a line, from its start point to its end point, built from the route segments of the portion in order (through `intermediatePoint` where given). If the portion cannot be built, the geometry is empty and the row is still written.

| Column | AIXM | Type |
|---|---|---|
| `changeOverPoints_distance` (+`Uom`) | `distance` — from the **start** of the route portion | REAL / TEXT |
| `changeOverPoints_distanceFromEnd` (+`Uom`) | `ibosoftais:ChangeOverPointExtension/distanceFromEnd` — from the **end** | REAL / TEXT |
| `changeOverPoints_startPointLayer` / `…Id` / `…Uuid` / `…Designator` / `…Name` / `…Type` | `RoutePortion/start_*`, resolved | TEXT / INTEGER |
| `changeOverPoints_endPointLayer` / `…Id` / `…Uuid` / `…Designator` / `…Name` / `…Type` | `RoutePortion/end_*`, resolved | TEXT / INTEGER |
| `changeOverPoints_intermediatePointLayer` / `…Id` / `…Uuid` / `…Designator` | `RoutePortion/intermediatePoint_*`, resolved | TEXT / INTEGER |
| `changeOverPoints_locationLatitude` / `…Longitude` | `location_position` (`gml:pos`) | REAL |
| `changeOverPoints_locationLayer` / `…Id` / `…Uuid` / `…Designator` | `location_fixDesignatedPoint` / `location_navaidSystem`, resolved | TEXT / INTEGER |
| `associatedRoute_uuid` | `RoutePortion/referencedRoute` | TEXT |
| `route_designatorPrefix`, `route_designatorSecondLetter`, `route_designatorNumber`, `route_multipleIdentifier`, `route_name` | the referenced `Route` (same names as in `routeSegments`) | TEXT |
| `associatedRouteSegment_id` | `routeSegments.id` list of the portion, start → end | TEXT (list) |
| `associatedRouteSegment_uuid` | `aixm_uuid` list of the same segments, same order | TEXT (list) |
| `copSymbology_offsetPercent` | derived | REAL |
| `annotation*` (4) | `annotation` (COP, then route) | TEXT |
| `data_*` (3) | provenance | TEXT |
| `atsStatus_associatedLevel*` / `atsStatus_associatedType*` (7) | derived from the segments of the portion | BOOLEAN |
| `aixm_*` (13) | identity and base | see [Common columns](#common-columns) |

`…Uuid` is always written when the reference exists, even if the target is not in this GeoPackage; `…Layer`/`…Id`/`…Designator` are written only when it resolves.

**`copSymbology_offsetPercent`** = `distance` / geodesic length of the line × 100. It places the COP symbol along the line from its start. `distanceFromEnd` is not used for it.

**No `designatorSuffix` for COPs.** In AIXM the suffix belongs to `RouteSegment`, not `Route`, and the segments of one portion can have different suffixes, so no single value exists.

---

## Derived columns

These columns have no AIXM counterpart. They are calculated from the other columns so that maps and queries can use them directly with the indexes of the layer.

### Route network status (`atsStatus_*`)

The role of a point in the ATS route network, derived from the route segments that use the point as start or end point. The columns form two groups:

- **`atsStatus_associated*`** — for grouping: they tell which kinds of route segments (level, route type) a point or change-over point is related to, so that points can be grouped and filtered, e.g. "points of upper routes".
- **`atsStatus_depiction*`** — for chart depiction. This information is **not in AIXM**, and it is **not among the data required by PANS-AIM**. Its definitions exist in several manuals, above all **ICAO Doc 8697** (Aeronautical Chart Manual), and **ICAO Annex 4** gives different symbols according to these definitions. Because the data requirements, the definitions and the symbology do not match each other exactly, these values are **produced by logic: from the other parameters in the existing data, following those definitions**. The rules are given below.

| Column | Type | Layers | Meaning |
|---|---|---|---|
| `atsStatus_isElementOfRouteSegment` | BOOLEAN | DP, NAV | The point is the start or end point of at least one route segment. Always 0 or 1 |
| `atsStatus_associatedLevelUpper` | BOOLEAN | DP, NAV, COP | At least one related segment has `level = UPPER` |
| `atsStatus_associatedLevelLower` | BOOLEAN | DP, NAV, COP | … `level = LOWER` |
| `atsStatus_associatedLevelBoth` | BOOLEAN | DP, NAV, COP | … `level = BOTH` (not derived from UPPER + LOWER) |
| `atsStatus_associatedLevelOther` | BOOLEAN | DP, NAV, COP | … `level = OTHER` or `OTHER:<x>` |
| `atsStatus_associatedTypeAts` | BOOLEAN | DP, NAV, COP | At least one related segment has `route_type = ATS` |
| `atsStatus_associatedTypeNat` | BOOLEAN | DP, NAV, COP | … `route_type = NAT` |
| `atsStatus_associatedTypeOther` | BOOLEAN | DP, NAV, COP | … `route_type = OTHER` or `OTHER:<x>` |
| `atsStatus_reportingAssociation` | TEXT (JSON) | DP, NAV | Reporting type per segment end: `[{"segmentId": …, "role": "START"\|"END", "reportingATC": …}]`; only ends with a reporting type |
| `atsStatus_depictionCompulsory` | BOOLEAN | DP, NAV | At least one related segment end has `reportingATC = COMPULSORY` |
| `atsStatus_depictionNav` | TEXT | DP, NAV | Navigation depiction class (below) |
| `atsStatus_depictionSIGPointBasicFunc` | TEXT | DP, NAV | Basic function of the significant point (below) |
| `atsStatus_depictionNavAndREP` | TEXT | DP, NAV | `depictionNav` + `_Comp` or `_NonComp` (from `depictionCompulsory`), e.g. `CONV_Comp`, `RNAVFlyBy_NonComp` |

DP = `designatedPoints`, NAV = `navaids`, COP = `changeOverPoints`.

- **Gate:** when `atsStatus_isElementOfRouteSegment = 0`, all other `atsStatus_*` columns are NULL (not 0). This separates "not in the route network" from "in the network but no such information".
- The level and type flags are independent; a point on both UPPER and LOWER segments has both flags set. A segment without `level` / `route_type` adds to no flag.
- For `changeOverPoints` the flags come from the segments of the COP's route portion (`associatedRouteSegment_id`); if the portion cannot be built, the seven columns are NULL.

**`atsStatus_depictionNav`** — first matching rule wins:

| Order | Value | Condition |
|---|---|---|
| 1 | `RNAVFlyOver` | Reserved; no source gives the fly-over / fly-by distinction yet, so it is not produced |
| 2 | `RNAVFlyBy` | DesignatedPoint `type = COORD`; or one of the related routes is `PBN` |
| 3 | `CONV` | One of the related ATS routes is `CONV` or `TACAN` |
| 4 | `OTHER` | Otherwise |

The navigation type comes from `navigationType` in `routeSegments_aircraftCapability`.

**`atsStatus_depictionSIGPointBasicFunc`** — first matching rule wins:

| Order | Value | Condition |
|---|---|---|
| 1 | `NAVAID` | Every navaid in the route network (never a DesignatedPoint) |
| 2 | `VFR_REP` | DesignatedPoint `type = VRP` |
| 3 | `WPT` | `depictionNav` is not `CONV`, and (`type = COORD` or all related segments are `PBN`) |
| 4 | `INT` | One of the related routes is `CONV` or `TACAN` |
| 5 | `OTHER` | Otherwise (DesignatedPoint) |

### Map labels (`navaidLabeling_*`)

Values for drawing a navaid label. In AIXM the frequency and channel are on the equipment, not on the navaid, and one piece of equipment has either a frequency or a channel; the missing value is taken from the ICAO VHF/UHF frequency–channel pairing table. `navaids` rows take the resolved values of their components.

| Column | Type | Meaning |
|---|---|---|
| `navaidLabeling_name` | TEXT | Label name (`name` of the row; not taken from a parent) |
| `navaidLabeling_ident` | TEXT | Label ident (`designator`); NULL for marker beacons that use an aural Morse pattern |
| `navaidLabeling_freq` | REAL | Frequency: **kHz for NDB, MHz for all other types** |
| `navaidLabeling_freqUom` | TEXT | `KHZ` or `MHZ` |
| `navaidLabeling_channel` | TEXT | Channel, e.g. `40X`; MLS: `<DME channel> <MLS channel>`, e.g. `18X 500` |
| `navaidLabeling_dmeElev` | REAL | Elevation of the DME component |
| `navaidLabeling_dmeElevUom` | TEXT | `FT` or `M`, as in the source (not converted) |
| `navaidLabeling_type` | TEXT | Chart abbreviation of the type (below) |
| `navaidLabeling_morseCode` | TEXT | Morse code of the ident (ITU-R M.1677-1), e.g. `IST` → `· ·   · · ·   −` |

A value is calculated only where it is meaningful for the type; otherwise it is NULL:

| `navaids_type` | freq | channel | dmeElev |
|---|:---:|:---:|:---:|
| VOR, TACAN, ILS, ILS_DME, VORTAC, LOC, LOC_DME, SDF | ✔ | ✔ | — |
| DME, VOR_DME | ✔ | ✔ | ✔ |
| MLS | — | ✔ | — |
| MLS_DME | ✔ | ✔ | — |
| NDB, NDB_DME, NDB_MKR | ✔ | — | — |
| MKR | ✔ | — | — |
| TLS, DF | — | — | — |

| `navaidComponents_equipmentType` | freq | channel | dmeElev |
|---|:---:|:---:|:---:|
| VOR, TACAN, Localizer, Glidepath, SDF | ✔ | ✔ | — |
| DME | ✔ | ✔ | ✔ |
| NDB | ✔ | — | — |
| Azimuth, Elevation (MLS) | ✔ | ✔ | — |
| MarkerBeacon | ✔ (75 MHz) | — | — |
| DirectionFinder | — | — | — |

**`navaidLabeling_type`:**

| AIXM | Label | AIXM | Label |
|---|---|---|---|
| VOR | `VOR` | VORTAC | `VORTAC` |
| DME | `DME` | VOR_DME | `VOR DME` |
| NDB, NDB_DME, NDB_MKR | `NDB`, or `L` when the NDB `class = L` (locator) | TACAN | `TACAN` |
| ILS | `ILS` | ILS_DME | `ILS DME` |
| LOC | `LOC` | LOC_DME | `LOC DME` |
| MLS | `MLS` | MLS_DME | `MLS DME` |
| TLS | `TLS` | DF / DirectionFinder | `DF` |
| SDF | `SDF` | Glidepath | `GP` |
| Localizer | `LOC` | Azimuth | `MLS AZM` |
| Elevation | `MLS ELEV` | MKR / MarkerBeacon | by `markerPosition`: `IM`, `MM`, `OM`, `BC MKR`, otherwise `MKR` |

`OTHER` → `OTHER`; `OTHER:<x>` → `<x>`; a value not in the table → NULL.

**Morse code.** Dot `·` (U+00B7), dash `−` (U+2212); one space between the signals of a letter, three between letters, seven between words. For a marker beacon with `auralMorseCode` that pattern is used, without letter spacing. If the ident has a character with no Morse code, the value is NULL.

**MLS.** The MLS frequency is not in AIXM; it is taken from the MLS channel. Azimuth and Elevation rows get the angle guidance frequency (5031.0–5090.7 MHz); an `MLS_DME` navaid gets the VHF frequency paired with its DME channel (about half of the MLS channels have no VHF pair, so this value is often NULL). Elevation takes its channel and frequency from the Azimuth of the same navaid.

### Symbol geometry (`navaidSymbology_*`)

The main purpose of these columns is to help place symbols in mapping: a symbol that belongs to one element but depends on a parameter of another element. The parameter is copied onto the element's own row, so the symbol can be placed from that row alone — e.g. the glide path beam drawn in the direction of the localizer of the same ILS.

| Column | Type | Layers | Meaning |
|---|---|---|---|
| `navaidSymbology_declination` | REAL | `navaids`, `navaidComponents` | Station declination for rotating the compass rose. Components: `VOR_declination` or `TACAN_declination` of the row. Navaids (only `VOR`, `VOR_DME`, `TACAN`, `VORTAC`): from the VOR component, for TACAN from the TACAN component, for VORTAC from the VOR if present, else the TACAN |
| `navaidSymbology_GPAssociatedLOCTrueBrg` | REAL | `navaidComponents` (Glidepath only) | Direction of the glide path beam: `trueBearing` of the Localizer of the same navaid. Not calculated from the magnetic bearing |

If the source has no declination, the value is empty (see [Data Coding Policies](data-coding-policies.md#vortacan-declination)).

---

## Indexes

| Index | Applies to |
|---|---|
| R-Tree (`rtree_<layer>_geom`, GeoPackage RTree extension) | `geom` of every layer |
| B-Tree | every attribute column of every layer |

The spatial index is kept up to date by the standard GeoPackage triggers, which use the `ST_*` functions of GIS software such as QGIS or GDAL. The derived columns are stored, not calculated in queries, so filters such as "route points only" use the same table, spatial index and column indexes.
