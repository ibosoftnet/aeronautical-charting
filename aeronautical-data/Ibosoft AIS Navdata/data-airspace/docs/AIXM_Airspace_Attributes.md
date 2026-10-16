# AIXM 5.2 — Airspace Feature: Tam Attribute Listesi

Kaynak: `AIXM_Features.xsd`, `AIXM_DataTypes.xsd`,
`AIXM_AbstractGML_ObjectTypes.xsd` (AIXM 5.2) ve açıklamalı kopyaları
(`../../common/docs/AIXM_*_annotated.xsd`). Eski
`Common Airspaces/AIXM_Airspace_Attributes.md`'nin tamamlanmış hâlidir:
`PropertiesWithSchedule`/`Timesheet`, TimeSlice/feature tabanı ve extension
noktaları eklendi; "taban şema dosyası elimizde yok" notu kaldırıldı
(`AIXM_AbstractGML_ObjectTypes.xsd` artık mevcut ve §8 ondan doğrulandı).

> **Genel not:** Her `Code*Type` `union` yapıdadır: sabit liste **veya**
> `OTHER(:(\w|_){1,58})?` deseni. Her `Code*`/`Val*`/`Text*Type` bir
> `nilReason` niteliği (`gml:NilReasonEnumeration`) taşıyabilir. Tüm alanlar
> `minOccurs="0"` ve `nillable="true"`'dur (aşağıdaki çokluk sütunu 0..1 ya
> da 0..∞'u gösterir).

---

## 1. Airspace → AirspaceTimeSlice (`AirspacePropertyGroup`, XSD sırasıyla)

| # | Attribute | Çokluk | Değer Tipi | Enum / Format |
|---|---|---|---|---|
| 1 | `type` | 0..1 | `CodeAirspaceType` | `NAS, FIR, FIR_P, UIR, UIR_P, CTA, CTA_P, OCA_P, OCA, UTA, UTA_P, TMA, TMA_P, CTR, CTR_P, OTA, SECTOR, SECTOR_C, TSA, CBA, RCA, RAS, AWY, MTR, P, R, D, ADIZ, NO_FIR, PART, CLASS, POLITICAL, D_OTHER, TRA, A, W, PROTECT, ASR, ADV, UADV, ATZ, ATZ_P, NAS_P, NTZ, NOZ, FBZ, FIZ, FRA, MOA, NPZ, RCZ, RMZ, TMZ` |
| 2 | `designator` | 0..1 | `CodeAirspaceDesignatorType` | Serbest kod, `Character3Type` deseni, **1-10** karakter |
| 3 | `localType` | 0..1 | `TextNameType` | Serbest metin, **1-60**, ASCII |
| 4 | `name` | 0..1 | `TextNameType` | Serbest metin, **1-60**, ASCII |
| 5 | `designatorICAO` | 0..1 | `CodeYesNoType` | `YES, NO` — designator ICAO Doc 7910'da kayıtlı mı |
| 6 | `controlType` | 0..1 | `CodeMilitaryOperationsType` | `CIVIL, MIL, JOINT` |
| 7 | `upperLowerSeparation` | 0..1 | `ValFLType` | Sayı (0-999) + `uom`: `FL, SM` — alt/üst hava sahası ayrım seviyesi |
| 8 | `class` | 0..∞ | `AirspaceLayerClassPropertyType` | → §2 |
| 9 | `protectedRoute` | 0..1 | `RoutePropertyType` | **Route** feature'ına `xlink:href` — sahanın koruduğu rota |
| 10 | `geometryComponent` | 0..∞ | `AirspaceGeometryComponentPropertyType` | → §3 |
| 11 | `activation` | 0..∞ | `AirspaceActivationPropertyType` | → §5 |
| 12 | `annotation` | 0..∞ | `NotePropertyType` | → §6 |
| — | `extension` | 0..∞ | `aixm:AbstractAirspaceExtension` ikame grubu | → §7 |

---

## 2. `class` → AirspaceLayerClass (`AbstractPropertiesWithScheduleType`'tan türer)

Eleman sırası: önce `PropertiesWithSchedulePropertyGroup` (§5.1), sonra:

| Attribute | Çokluk | Değer Tipi | Enum / Format |
|---|---|---|---|
| `classification` | 0..1 | `CodeAirspaceClassificationType` | `A, B, C, D, E, F, G` (ICAO Annex 11 Ek 4) |
| `associatedLevels` | 0..∞ | `AirspaceLayerPropertyType` | → §4 |
| `extension` | 0..∞ | `AbstractPropertiesWithScheduleExtension` / `AbstractAirspaceLayerClassExtension` | |

---

## 3. `geometryComponent` → AirspaceGeometryComponent

| Attribute | Çokluk | Değer Tipi | Enum / Format |
|---|---|---|---|
| `operation` | 0..1 | `CodeAirspaceAggregationType` | `BASE, UNION, INTERS, SUBTR` |
| `operationSequence` | 0..1 | `NoSequenceType` | Sayı (`unsignedInt`) |
| `annotation` | 0..∞ | `NotePropertyType` | → §6 |
| `theAirspaceVolume` | 0..1 | `AirspaceVolumePropertyType` | → §3.1 |

### 3.1 `theAirspaceVolume` → AirspaceVolume (XSD sırasıyla)

| Attribute | Çokluk | Değer Tipi | Enum / Format |
|---|---|---|---|
| `upperLimit` | 0..1 | `ValDistanceVerticalType` | Sayı \| `UNL` \| `GND` \| `FLOOR` \| `CEILING`; `uom`: `FT, M, FL, SM` |
| `upperLimitReference` | 0..1 | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `maximumLimit` | 0..1 | `ValDistanceVerticalType` | (yukarıdaki gibi) |
| `maximumLimitReference` | 0..1 | `CodeVerticalReferenceType` | |
| `lowerLimit` | 0..1 | `ValDistanceVerticalType` | |
| `lowerLimitReference` | 0..1 | `CodeVerticalReferenceType` | |
| `minimumLimit` | 0..1 | `ValDistanceVerticalType` | |
| `minimumLimitReference` | 0..1 | `CodeVerticalReferenceType` | |
| `width` | 0..1 | `ValDistanceType` | Sayı + `uom`: `NM, KM, M, FT, MI, CM` |
| `horizontalProjection` | 0..1 | `SurfacePropertyType` | `aixm:Surface` (GML yüzey; `gml:patches/gml:PolygonPatch`) |
| `centreline` | 0..1 | `CurvePropertyType` | `aixm:Curve` (GML eğri) |
| `contributorAirspace` | 0..1 | `AirspaceVolumeDependencyPropertyType` | → §3.1.1 |
| `annotation` | 0..∞ | `NotePropertyType` | → §6 |
| `name` | 0..1 | `TextNameType` | Serbest metin, 1-60 |
| `location` | 0..1 | `PointPropertyType` | `aixm:Point` / `aixm:ElevatedPoint` |

#### 3.1.1 `contributorAirspace` → AirspaceVolumeDependency

| Attribute | Çokluk | Değer Tipi | Enum / Format |
|---|---|---|---|
| `dependency` | 0..1 | `CodeAirspaceDependencyType` | `FULL_GEOMETRY, HORZ_PROJECTION` |
| `annotation` | 0..∞ | `NotePropertyType` | → §6 |
| `theAirspace` | 0..1 | `AirspacePropertyType` | Başka bir **Airspace**'e `xlink:href` |

---

## 4. `associatedLevels` / `levels` → AirspaceLayer

| Attribute | Çokluk | Değer Tipi | Enum / Format |
|---|---|---|---|
| `upperLimit` | 0..1 | `ValDistanceVerticalType` | Sayı \| `UNL` \| `GND` \| `FLOOR` \| `CEILING`; `uom`: `FT, M, FL, SM` |
| `upperLimitReference` | 0..1 | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `lowerLimit` | 0..1 | `ValDistanceVerticalType` | |
| `lowerLimitReference` | 0..1 | `CodeVerticalReferenceType` | |
| `altitudeInterpretation` | 0..1 | `CodeAltitudeUseType` | `AT_OR_ABOVE, AT_OR_BELOW, AT, BETWEEN, RECOMMENDED, EXPECTED, BY_ATC` |
| `discreteLevelSeries` | 0..1 | `StandardLevelColumnPropertyType` | **StandardLevelColumn** feature'ına `xlink:href` (standart IFR/VFR seviye kümesi) |
| `annotation` | 0..∞ | `NotePropertyType` | → §6 |

---

## 5. `activation` → AirspaceActivation (`AbstractPropertiesWithScheduleType`'tan türer)

Eleman sırası: önce `PropertiesWithSchedulePropertyGroup` (§5.1), sonra:

| Attribute | Çokluk | Değer Tipi | Enum / Format |
|---|---|---|---|
| `activity` | 0..1 | `CodeAirspaceActivityType` | `AD_TFC, HELI_TFC, TRAINING, AEROBATICS, AIRSHOW, SPORT, ULM, GLIDING, PARAGLIDER, HANGGLIDING, PARACHUTE, AIR_DROP, BALLOON, RADIOSONDE, SPACE_FLIGHT, AERIAL_WORK, CROP_DUSTING, FIRE_FIGHTING, MILOPS, REFUEL, JET_CLIMBING, EXERCISE, TOWING, NAVAL_EXER, MISSILES, AIR_GUN, ARTILLERY, SHOOTING, BLASTING, WATER_BLASTING, ANTI_HAIL, BIRD, BIRD_MIGRATION, FIREWORK, HI_RADIO, HI_LIGHT, LASER, NATURE, FAUNA, NO_NOISE, ACCIDENT, POPULATION, VIP, VIP_PRES, VIP_VICE, OIL, GAS, REFINERY, CHEMICAL, NUCLEAR, TECHNICAL, ATS, PROCEDURE, UAS, ACFT_MASS_MOVEMENT, CAPTIVE_BALLOON_KITE, DEMOLITION, DISASTER_RELIEF, FORMATION_FLIGHT, MODEL_FLYING, NIGHT_VISION_OPS, SAR, SKY_LANTERN, SMOKE, VOLCANO` |
| `status` | 0..1 | `CodeStatusAirspaceType` | `AVBL_FOR_ACTIVATION, ACTIVE, IN_USE, INACTIVE, INTERMITTENT` |
| `levels` | 0..∞ | `AirspaceLayerPropertyType` | → §4 |
| `user` | 0..∞ | `OrganisationAuthorityPropertyType` | **OrganisationAuthority** feature'ına `xlink:href` |
| `aircraft` | 0..∞ | `AircraftCharacteristicPropertyType` | `AircraftCharacteristic` nesnesi (tip, motor, ağırlık …) |

### 5.1 PropertiesWithSchedulePropertyGroup (`class` ve `activation`'da ortak)

| Attribute | Çokluk | Değer Tipi | Enum / Format |
|---|---|---|---|
| `timeInterval` | 0..∞ | `TimesheetPropertyType` | → `Timesheet` nesnesi (alanları: [`AIXM_Airspace_Activation_Schedule.md`](AIXM_Airspace_Activation_Schedule.md) §2) |
| `annotation` | 0..∞ | `NotePropertyType` | → §6 |
| `specialDateAuthority` | 0..∞ | `OrganisationAuthorityPropertyType` | O kuruluşun özel günleri (bayram vb.) çizelgeye uygulanır |

---

## 6. `annotation` → Note

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `propertyName` | `TextPropertyNameType` | Notun ilgili olduğu alan adı (lowerCamelCase) |
| `purpose` | `CodeNotePurposeType` | `DESCRIPTION, REMARK, WARNING, DISCLAIMER` |
| `translatedNote` (0..∞) | `LinguisticNotePropertyType` | → `LinguisticNote/note` (`TextNoteType`, dil etiketli serbest metin) |

Ayrıntı: [`../../common/docs/AIXM_Annotation_Attributes.md`](../../common/docs/AIXM_Annotation_Attributes.md).

---

## 7. Extension noktaları

Her yapının kendi soyut extension başlığı vardır:
`AbstractAirspaceExtension`, `AbstractAirspaceLayerClassExtension`,
`AbstractAirspaceGeometryComponentExtension`, `AbstractAirspaceVolumeExtension`,
`AbstractAirspaceVolumeDependencyExtension`, `AbstractAirspaceLayerExtension`,
`AbstractAirspaceActivationExtension`, `AbstractPropertiesWithScheduleExtension`.

Bu projenin `AbstractAirspaceExtension`'a bağladığı iki eleman
(`AirspaceDataProvenance`, `AirspaceExtension`):
[`../../common/docs/Ibosoft_AIS_Extension.md`](../../common/docs/Ibosoft_AIS_Extension.md).

---

## 8. Ortak (base) alanlar — `AIXM_AbstractGML_ObjectTypes.xsd`

**Feature** (`AbstractAIXMFeatureType` ← `AbstractAIXMFeatureBaseType` ← `gml:DynamicFeatureType`):

| Alan | Çokluk | Not |
|---|---|---|
| `gml:description` | 0..1 | |
| `gml:identifier` | 0..1 | `codeSpace="urn:uuid:"` — kalıcı kimlik (UUID); diğer feature'lar `xlink:href="urn:uuid:…"` ile buna bakar |
| `gml:name` | 0..∞ | |
| `gml:boundedBy` | 0..1 | Zarf |
| `featureMetadata` | 0..1 | ISO 19115 tabanlı feature metadata'sı |
| `gml:id` (nitelik) | zorunlu | Belge içi kimlik |

**TimeSlice** (`AbstractAIXMTimeSliceType` ← `AbstractAIXMTimeSliceBaseType` ← `gml:AbstractTimeSliceType`):

| Alan | Çokluk | Not |
|---|---|---|
| `gml:validTime` | **1** | `gml:TimePeriod` (begin/end) ya da `gml:TimeInstant`; bilinmeyen zaman `indeterminatePosition="unknown"` ile yazılır |
| `interpretation` | **1** | `BASELINE, TEMPDELTA, PERMDELTA, SNAPSHOT` |
| `sequenceNumber` | 0..1 | |
| `correctionNumber` | 0..1 | |
| `timeSliceMetadata` | 0..1 | |
| `featureLifetime` | 0..1 | `gml:TimePeriod` — feature'ın varlık süresi |

**Nesne** (`AbstractAIXMObjectType` ← `gml:AbstractGMLType`): `gml:id`
(nitelik), `gml:identifier` 0..1.
