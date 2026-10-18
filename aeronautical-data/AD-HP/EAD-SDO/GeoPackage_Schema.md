# Aerodrome Data AIXM Mapping

> **Base endpoint:** none\
> **Reference documents:** AIXM 4.5 · AIXM 5.1 / 5.2 schema set (aixm.aero)\
> **Attribution:** show `{{BRAND_AIS}}` wherever this data is displayed\
> **Data sources:** none\
> **Last updated:** 18 OCT 2026

> **Work in progress.** The aerodrome data is still being developed; its structure and fields will change in the future.

The aerodrome GeoPackage holds aerodromes and heliports with their usage restrictions, and their runway directions. Most columns come from the AIXM 4.5 based EAD SDO reports and keep their field names; the elevation and transition columns follow AIXM 5.1. Records added or corrected by Ibosoft AIS use the same columns.

---

## Layers

| Layer | Type | Geometry | One row is |
|---|---|---|---|
| `ad_hp_airports` | features | POINT (aerodrome reference point, WGS 84 / EPSG:4326) | one aerodrome or heliport |
| `ad_hp_runways` | attributes only | — (the source has no runway coordinates) | one runway **direction** |

The two layers are linked by `match_id` (see [Linking airports and runways](#linking-airports-and-runways)). Every layer also has `fid` (INTEGER primary key); `ad_hp_airports` has `geom`.

---

## `ad_hp_airports`

### Aerodrome reference point

| Column | Type | Source field | Meaning |
|---|---|---|---|
| `join_key` | TEXT | — | `code_icao` if present, else `code_id`; key used to join the usage data |
| `mid` | TEXT | `mid` | EAD SDO record id |
| `code_id` | TEXT | `codeId` | Aerodrome/heliport identification (AIXM identifier, **not** necessarily the ICAO code) |
| `code_icao` | TEXT | `codeIcao` | ICAO location indicator, if any |
| `code_iata` | TEXT | `codeIata` | IATA code, if any |
| `code_type` | TEXT | `codeType` | `AD` aerodrome, `HP` heliport, `AH` aerodrome with heliport |
| `name` | TEXT | `txtName` | Name |
| `city` | TEXT | `txtNameCitySer` | City or area served |
| `country` | TEXT | `Org/txtName` | Country (organisation) |
| `datum` | TEXT | `codeDatum` | Coordinate datum (`WGE` = WGS 84) |
| `lat_text`, `lon_text` | TEXT | `geoLat`, `geoLong` | Coordinates as written in the source (DMS, DDM or DD) |
| `lat_dd`, `lon_dd` | REAL | — | Decimal degrees, WGS 84 |
| `dt_wef` | TEXT | `dtWef` | Effective date of the record |
| `arp_work_hr` | TEXT | `codeWorkHr` | Working hours |
| `sys_rmk` | TEXT | `sysRmk` | Remark |
| `data_provider` | TEXT | — | Provider of the data: `EUROCONTROL EAD SDO`, or `Ibosoft AIS` for records added or corrected by Ibosoft AIS |
| `data_originator` | TEXT | `OrgCre/txtName` | Original publisher (for Ibosoft AIS records entered per record) |
| `data_effectivity` | TEXT | — | Effectivity of the source data set |

Provenance coding: [Data Coding Policies › Provenance](data-coding-policies.md#provenance). Identifier coding: [Data Coding Policies › Aerodrome AIXM Identifier and ICAO Location Indicator](data-coding-policies.md#aerodrome-aixm-identifier-and-icao-location-indicator).

### Elevation and transition (AIXM 5.1)

Not in the EAD SDO reports; filled only in records entered by Ibosoft AIS.

| Column | Type | AIXM 5.1 | Meaning |
|---|---|---|---|
| `field_elevation`, `field_elevation_uom` | REAL, TEXT | `fieldElevation` | Aerodrome elevation, `FT` or `M` |
| `field_elevation_accuracy`, `field_elevation_accuracy_uom` | REAL, TEXT | `fieldElevationAccuracy` | Accuracy of the elevation, `FT` or `M` |
| `vertical_datum` | TEXT | `verticalDatum` | Vertical datum, e.g. `EGM96` |
| `transition_altitude`, `transition_altitude_uom`, `transition_altitude_nil_reason` | REAL, TEXT, TEXT | `transitionAltitude` | Transition altitude, `FT` or `M`, and the reason when there is no value |
| `transition_level`, `transition_level_uom`, `transition_level_nil_reason` | REAL, TEXT, TEXT | `transitionLevel` | Transition level (FL 0–999), `FL` or `SM`, and the reason when there is no value. Often variable (set by ATC), so usually empty with a nil reason |

### Usage restrictions

From the EAD SDO AD/HP usage report, joined by `join_key`. One usage record per aerodrome.

| Column | Source field | Meaning |
|---|---|---|
| `usage_mid` | `mid` | Usage record id |
| `usage_dt_wef` | `dtWef` | Effective date |
| `usage_dt_com` | `dtCom` | Commissioning / publication date |
| `usage_limit` | `codeUsageLimitation` | Kind of limitation (permitted, forbidden, permission required …) |
| `usage_work_hr` | `codeWorkHr` | Working hours code |
| `usage_work_hr_rmk` | `txtRmkWorkHr` | Working hours remark |
| `usage_time_ref` | `codeTimeRef` | Time reference |
| `usage_valid_wef`, `usage_valid_til` | `dateValidWef`, `dateValidTil` | Validity period |
| `usage_day`, `usage_day_til` | `codeDay`, `codeDayTil` | Day (from / until) |
| `usage_time_wef`, `usage_time_til` | `timeWef`, `timeTil` | Time (from / until) |
| `usage_event_wef`, `usage_event_til` | `codeEventWef`, `codeEventTil` | Event (from / until), e.g. sunrise / sunset |
| `usage_comb_til` | `codeCombTil` | Combination of time and event |
| `usage_type` | flight class `codeType` | Type of flight |
| `usage_rule` | flight class `codeRule` | Flight rules |
| `usage_mil` | flight class `codeMil` | Civil / military |
| `usage_origin` | flight class `codeOrigin` | Origin (national, international …) |
| `usage_purpose` | flight class `codePurpose` | Purpose of flight |
| `usage_status` | flight class `codeStatus` | Status of flight |
| `usage_capability` | flight class `codeCapability` | Required capability |
| `usage_aircraft_type` | aircraft class `codeIcaoAcftType` | ICAO aircraft type |
| `usage_engine_no` | aircraft class `codeEngineNo` | Number of engines |
| `usage_engine_type` | aircraft class `codeTypeEngine` | Engine type |
| `usage_org_name` | organisation `txtName` | Organisation |
| `usage_joined` | — | `1` if a usage record was found, else `0` (INTEGER) |

All `usage_*` columns are TEXT except `usage_joined`.

### Link

| Column | Type | Meaning |
|---|---|---|
| `match_id` | INTEGER | Link to `ad_hp_runways` (below) |

---

## `ad_hp_runways`

One row per runway direction (e.g. `11` and `29` of runway `11/29` are two rows). The direction comes from the EAD SDO runway direction report (RWY-DIR); the runway data (dimensions, surface, strength) from the runway report (RWY-INFO), copied to both directions of the runway.

### Direction

| Column | Type | Source field | Meaning |
|---|---|---|---|
| `match_id` | INTEGER | — | Link to `ad_hp_airports` |
| `ahp_code_id` | TEXT | RWY-DIR `Ahp/codeId` | Aerodrome identification (not necessarily ICAO) |
| `ahp_code_icao` | TEXT | RWY-DIR `Ahp/codeIcao` | ICAO location indicator, if any |
| `rwy_designator` | TEXT | RWY-DIR `Rwy/txtDesig` | Runway designator, e.g. `RWY 11/29` |
| `direction_designator` | TEXT | RWY-DIR `txtDesig` | Direction of this row, e.g. `11` |
| `true_bearing` | REAL | RWY-DIR `valTrueBrg` | True bearing, degrees |
| `mag_bearing` | REAL | RWY-DIR `valMagBrg` | Magnetic bearing, degrees |
| `dir_dt_wef` | TEXT | RWY-DIR `dtWef` | Effective date of the direction record |
| `dir_mid` | TEXT | RWY-DIR `mid` | Direction record id |
| `data_provider` | TEXT | — | `EUROCONTROL EAD SDO`, or `Ibosoft AIS` |
| `data_originator` | TEXT | RWY-DIR + RWY-INFO `OrgCre/txtName` | Original publisher |
| `data_effectivity` | TEXT | — | Effectivity of the source data set |

### Runway

| Column | Type | Source field | Meaning |
|---|---|---|---|
| `info_joined` | INTEGER | — | `1` if runway data was found, else `0` |
| `info_designator` | TEXT | `txtDesig` | Runway designator as written in the runway report |
| `info_length`, `info_width` | REAL | `valLen`, `valWid` | Runway length and width |
| `info_dim_unit` | TEXT | `uomDimRwy` | Unit of length and width (`FT` / `M`) |
| `info_dt_wef` | TEXT | `dtWef` | Effective date of the runway record |
| `info_dt_com` | TEXT | `dtCom` | Publication date of the runway record |
| `info_surface_composition` | TEXT | `codeComposition` | Surface material, e.g. `ASPH`, `CONC` |
| `info_surface_condition` | TEXT | `codeCondSfc` | Surface condition, e.g. `GOOD` |
| `info_surface_preparation` | TEXT | `codePreparation` | Surface preparation, e.g. `GROOVED` |
| `info_status` | TEXT | `codeSts` | Runway status |
| `info_marking_rmk` | TEXT | `txtMarking` | Marking remark |
| `info_profile_rmk` | TEXT | `txtProfile` | Profile / slope remark, e.g. `Rwy 35 up 0.56%` |
| `info_rmk` | TEXT | `txtRmk` | Remark |
| `info_pcn_class` | TEXT | `valPcnClass` | PCN (Pavement Classification Number) value |
| `info_pcn_pavement_type` | TEXT | `codePcnPavementType` | Pavement type: `F` flexible, `R` rigid |
| `info_pcn_pavement_subgrade` | TEXT | `codePcnPavementSubgrade` | Subgrade category: `A` – `D` |
| `info_pcn_max_tire_pressure_code` | TEXT | `codePcnMaxTirePressure` | Maximum tyre pressure category: `W` – `Z` |
| `info_pcn_eval_method` | TEXT | `codePcnEvalMethod` | Evaluation method: `T` technical, `U` using aircraft experience |
| `info_pcn_note` | TEXT | `txtPcnNote` | Note when the PCN is not in the standard format |
| `info_lcn_class` | REAL | `valLcnClass` | LCN (Load Classification Number) value |
| `info_length_offset` | REAL | `valLenOffset` | Length offset; the meaning is not confirmed in the EAD SDO documentation (probably displaced threshold) — use with care |
| `info_strip_length`, `info_strip_width` | REAL | `valLenStrip`, `valWidStrip` | Runway strip length and width |
| `info_strip_dim_unit` | TEXT | `uomDimStrip` | Unit of the strip dimensions |
| `info_auw_weight`, `info_auw_weight_unit` | REAL, TEXT | `valAuwWeight`, `uomAuwWeight` | All-up-weight limit and unit |
| `info_siwl_weight`, `info_siwl_weight_unit` | REAL, TEXT | `valSiwlWeight`, `uomsiwlweight` | Single isolated wheel load and unit |
| `info_siwl_tire_pressure`, `info_siwl_tire_pressure_unit` | REAL, TEXT | `valSiwlTirePressure`, `uomSiwlTirePressure` | SIWL tyre pressure and unit |
| `info_ahp_code_id`, `info_ahp_code_icao` | TEXT | `Ahp/codeId`, `Ahp/codeIcao` | Aerodrome codes as written in the runway report |
| `info_mid` | TEXT | `mid` | Runway record id |

Even with `info_joined = 1`, many `info_*` columns can be empty: the source does not give them for every runway.

---

## Linking airports and runways

- `match_id` is shared by an aerodrome row and all its runway rows (grouped by `code_id` / `ahp_code_id`, not by the ICAO code).
- `match_id` is **not permanent**: it is created again every time the GeoPackage is produced. Use it only to join the two layers of the **same** file; for a stable reference use `code_id` / `ahp_code_id`.
- In QGIS: layer properties → Joins → `ad_hp_runways.match_id` = `ad_hp_airports.match_id`.
- Direction and runway data are matched by aerodrome `codeId` and the runway designator with `RWY`, `-`, `/` and spaces removed (`RWY 11/29` and `RWY-11/29` → `1129`). The order of the numbers is kept, so `04/22` and `22/04` do not match.
- Not every aerodrome has runway rows: the runway reports cover fewer aerodromes than the reference point report (e.g. many small heliports).

---

## Column types

| Type | Columns |
|---|---|
| REAL | coordinates, bearings, dimensions, LCN, weight and pressure limits, elevation and transition values |
| INTEGER | `match_id`, `usage_joined`, `info_joined` |
| TEXT | codes, designators, names, units, remarks, dates (as written in the source, `DD/MM/YYYY`), record ids |

---

## Indexes

| Index | Applies to |
|---|---|
| R-Tree (`rtree_ad_hp_airports_geom`, GeoPackage RTree extension) | `geom` of `ad_hp_airports` |
| B-Tree | every attribute column of both layers |
