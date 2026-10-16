# AIXM 5.2 — Airspace Feature: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` + `AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni (yani `OTHER:MY_CODE` gibi serbest bir uzatma).
> Ayrıca her `Code*`/`Val*`/`Text*Type`, `complexType` olarak `gml:NilReasonEnumeration`
> tipinde bir `nilReason` attribute'u da taşır (nedeni bilinmeyen/uygulanmayan değerler için).

---

## 1. Airspace → AirspaceTimeSlice (kendi attribute'ları)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeAirspaceType` | `NAS, FIR, FIR_P, UIR, UIR_P, CTA, CTA_P, OCA_P, OCA, UTA, UTA_P, TMA, TMA_P, CTR, CTR_P, OTA, SECTOR, SECTOR_C, TSA, CBA, RCA, RAS, AWY, MTR, P, R, D, ADIZ, NO_FIR, PART, CLASS, POLITICAL, D_OTHER, TRA, A, W, PROTECT, ASR, ADV, UADV, ATZ, ATZ_P, NAS_P, NTZ, NOZ, FBZ, FIZ, FRA, MOA, NPZ, RCZ, RMZ, TMZ` |
| `designator` | `CodeAirspaceDesignatorType` | Enum değil — serbest metin, `Character3Type`, 1-10 karakter |
| `localType` | `TextNameType` | Enum değil — serbest metin, max 60 karakter |
| `name` | `TextNameType` | Enum değil — serbest metin, max 60 karakter |
| `designatorICAO` | `CodeYesNoType` | `YES, NO` |
| `controlType` | `CodeMilitaryOperationsType` | `CIVIL, MIL, JOINT` |
| `upperLowerSeparation` | `ValFLType` | Sayısal (0-999, `unsignedInt`) + `uom`: `FL, SM` |
| `class` (0..∞) | `AirspaceLayerClassPropertyType` | → bkz. **2** |
| `protectedRoute` (0..1) | `RoutePropertyType` | Ayrı bir **Route** feature'ına association — kapsam dışı |
| `geometryComponent` (0..∞) | `AirspaceGeometryComponentPropertyType` | → bkz. **3** |
| `activation` (0..∞) | `AirspaceActivationPropertyType` | → bkz. **5** |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. **6** |

---

## 2. `class` → AirspaceLayerClass

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `classification` | `CodeAirspaceClassificationType` | `A, B, C, D, E, F, G` |
| `associatedLevels` (0..∞) | `AirspaceLayerPropertyType` | → bkz. **4** (AirspaceLayer ile birebir aynı yapı) |

---

## 3. `geometryComponent` → AirspaceGeometryComponent

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `operation` | `CodeAirspaceAggregationType` | `BASE, UNION, INTERS, SUBTR` |
| `operationSequence` | `NoSequenceType` | Sayısal (`unsignedInt`, sınırsız) |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. **6** |
| `theAirspaceVolume` | `AirspaceVolumePropertyType` | → **AirspaceVolume**, bkz. **3.1** |

### 3.1 `theAirspaceVolume` → AirspaceVolume

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `upperLimit` | `ValDistanceVerticalType` | Sayı \| `UNL` \| `GND` \| `FLOOR` \| `CEILING` + `uom`: `FT, M, FL, SM` |
| `upperLimitReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `maximumLimit` | `ValDistanceVerticalType` | (yukarıdaki gibi) |
| `maximumLimitReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `lowerLimit` | `ValDistanceVerticalType` | (yukarıdaki gibi) |
| `lowerLimitReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `minimumLimit` | `ValDistanceVerticalType` | (yukarıdaki gibi) |
| `minimumLimitReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `width` | `ValDistanceType` | Sayı + `uom`: `NM, KM, M, FT, MI, CM` |
| `horizontalProjection` | `SurfacePropertyType` | GML geometrisi (`gml:Surface`/`Polygon`) — kapsam dışı |
| `centreline` | `CurvePropertyType` | GML geometrisi (`gml:Curve`/`LineString`) — kapsam dışı |
| `contributorAirspace` | `AirspaceVolumeDependencyPropertyType` | → bkz. **3.1.1** |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. **6** |
| `name` | `TextNameType` | Serbest metin, max 60 karakter |
| `location` | `PointPropertyType` | GML geometrisi (`gml:Point`) — kapsam dışı |

#### 3.1.1 `contributorAirspace` → AirspaceVolumeDependency

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `dependency` | `CodeAirspaceDependencyType` | `FULL_GEOMETRY, HORZ_PROJECTION` |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. **6** |
| `theAirspace` | `AirspacePropertyType` | Başka bir **Airspace** feature'ına (kendi kendine) association |

---

## 4. `levels` / `associatedLevels` → AirspaceLayer

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `upperLimit` | `ValDistanceVerticalType` | Sayı \| `UNL` \| `GND` \| `FLOOR` \| `CEILING` + `uom`: `FT, M, FL, SM` |
| `upperLimitReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `lowerLimit` | `ValDistanceVerticalType` | (yukarıdaki gibi) |
| `lowerLimitReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `altitudeInterpretation` | `CodeAltitudeUseType` | `AT_OR_ABOVE, AT_OR_BELOW, AT, BETWEEN, RECOMMENDED, EXPECTED, BY_ATC` |
| `discreteLevelSeries` | `StandardLevelColumnPropertyType` | Ayrı bir **StandardLevelColumn** feature'ına association — kapsam dışı |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. **6** |

---

## 5. `activation` → AirspaceActivation

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `activity` | `CodeAirspaceActivityType` | `AD_TFC, HELI_TFC, TRAINING, AEROBATICS, AIRSHOW, SPORT, ULM, GLIDING, PARAGLIDER, HANGGLIDING, PARACHUTE, AIR_DROP, BALLOON, RADIOSONDE, SPACE_FLIGHT, AERIAL_WORK, CROP_DUSTING, FIRE_FIGHTING, MILOPS, REFUEL, JET_CLIMBING, EXERCISE, TOWING, NAVAL_EXER, MISSILES, AIR_GUN, ARTILLERY, SHOOTING, BLASTING, WATER_BLASTING, ANTI_HAIL, BIRD, BIRD_MIGRATION, FIREWORK, HI_RADIO, HI_LIGHT, LASER, NATURE, FAUNA, NO_NOISE, ACCIDENT, POPULATION, VIP, VIP_PRES, VIP_VICE, OIL, GAS, REFINERY, CHEMICAL, NUCLEAR, TECHNICAL, ATS, PROCEDURE, UAS, ACFT_MASS_MOVEMENT, CAPTIVE_BALLOON_KITE, DEMOLITION, DISASTER_RELIEF, FORMATION_FLIGHT, MODEL_FLYING, NIGHT_VISION_OPS, SAR, SKY_LANTERN, SMOKE, VOLCANO` |
| `status` | `CodeStatusAirspaceType` | `AVBL_FOR_ACTIVATION, ACTIVE, IN_USE, INACTIVE, INTERMITTENT` |
| `levels` (0..∞) | `AirspaceLayerPropertyType` | → **4**'teki AirspaceLayer ile aynı yapı |
| `user` (0..∞) | `OrganisationAuthorityPropertyType` | **Organisation/Authority** feature'ına association — kapsam dışı |
| `aircraft` (0..∞) | `AircraftCharacteristicPropertyType` | Uçak karakteristiği tipi (kendi alt-yapısı var: `type`, `engine`, `weight`... ) — kapsam dışı |

---

## 6. `annotation` → Note

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `propertyName` | `TextPropertyNameType` | Serbest metin, lowerCamelCase, max 60 karakter, desen: `[A-Za-z\-_]*` |
| `purpose` | `CodeNotePurposeType` | `DESCRIPTION, REMARK, WARNING, DISCLAIMER` |
| `translatedNote` (0..∞) | `LinguisticNotePropertyType` | → **LinguisticNote**: `note` (`TextNoteType`, dil etiketli serbest metin) |

---

## Ortak (base) attribute'lar

`AirspaceType` → `AbstractAIXMFeatureType`, `AirspaceTimeSliceType` → `AbstractAIXMTimeSliceType`'dan miras alır.
Bu iki tip `AIXM_AbstractGML_ObjectTypes.xsd` dosyasında tanımlı — bu dosya elimizde olmadığı için içeriği
teyit edilemedi. Standart AIXM davranışına göre muhtemelen şunları içerir: `gml:identifier`, `validTime`,
`sequenceNumber`, `correctionNumber`, `interpretation`, `featureLifetime`.
