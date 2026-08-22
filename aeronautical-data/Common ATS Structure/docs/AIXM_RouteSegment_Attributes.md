# AIXM 5.2 — RouteSegment Feature: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (`RouteSegmentPropertyGroup`, satır ~18097-18313) +
`AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni. Her `Code*`/`Val*`/`Text*Type`, `complexType` olarak
> `gml:NilReasonEnumeration` tipinde bir `nilReason` attribute'u da taşır.
>
> `RouteSegment`, AIXM'de bir **Feature**'dır (`RouteSegmentType` → `AbstractAIXMFeatureType`).
> Tanımı: *"A portion of a route to be flown usually without an intermediate stop, as
> defined by two consecutive significant points."*

---

## 1. RouteSegment → RouteSegmentTimeSlice (kendi attribute'ları)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `level` | `CodeLevelType` | `UPPER, LOWER, BOTH` (+OTHER) — segment üst hava sahasında mı, alt hava sahasında mı, ikisinde de mi |
| `upperLimit` | `ValDistanceVerticalType` | Sayı \| `UNL` \| `GND` \| `FLOOR` \| `CEILING` + `uom`: `FT, M, FL, SM` |
| `upperLimitReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `lowerLimit` | `ValDistanceVerticalType` | (yukarıdaki gibi) |
| `lowerLimitReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `minimumObstacleClearanceAltitude` | `ValDistanceVerticalType` | MOCA — engel sınırlaması sağlayan minimum irtifa |
| `pathType` | `CodeRouteSegmentPathType` | `GRC` (great circle), `RHL` (rhumb line), `GDS` (geodesic) (+OTHER) |
| `trueTrack` | `ValBearingType` | 0-360 derece (ondalık), ilk gerçek rota |
| `magneticTrack` | `ValBearingType` | 0-360 derece, ilk manyetik rota |
| `reverseTrueTrack` | `ValBearingType` | 0-360 derece, ters yön gerçek rota |
| `reverseMagneticTrack` | `ValBearingType` | 0-360 derece, ters yön manyetik rota |
| `length` | `ValDistanceType` | Sayı (≥0) + `uom`: `NM, KM, M, FT, MI, CM` — yolun uzunluğu |
| `widthLeft` | `ValDistanceType` | (yukarıdaki gibi) — start→end yönüne göre merkez çizgisinden sol genişlik |
| `widthRight` | `ValDistanceType` | (yukarıdaki gibi) — start→end yönüne göre merkez çizgisinden sağ genişlik |
| `turnDirection` | `CodeDirectionTurnType` | `LEFT, RIGHT, EITHER` (+OTHER) — bir sonraki segmente geçişte dönüş yönü |
| `signalGap` | `CodeYesNoType` | `YES, NO` — segmentte sinyal boşluğu var mı |
| `minimumEnrouteAltitude` (0..∞) | `AltitudeIndicationPropertyType` | MEA — nav sinyal alımı, ATS haberleşmesi ve engel sınırlaması sağlayan en düşük yayınlanmış irtifa — kendi alt-yapısı var, kapsam dışı |
| `minimumCrossingAtEnd` | `ValDistanceVerticalType` | End noktasında en düşük geçiş dikey konumu |
| `minimumCrossingAtEndReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `maximumCrossingAtEnd` | `ValDistanceVerticalType` | End noktasında en yüksek geçiş dikey konumu |
| `maximumCrossingAtEndReference` | `CodeVerticalReferenceType` | `SFC, MSL, W84, STD` |
| `designatorSuffix` | `CodeRouteDesignatorSuffixType` | `F` (yalnızca danışma servisi sağlanır), `G` (yalnızca uçuş bilgi servisi sağlanır) (+OTHER) — ICAO Annex 11'e göre rota eki |
| `start` (0..1) | `EnRouteSegmentPointPropertyType` | Segmentin başlangıç noktası → bkz. `AIXM_RoutePoint_DataTypes.md` |
| `routeFormed` (0..1) | `RoutePropertyType` | Segmentin ait olduğu **Route**'a association |
| `evaluationArea` | `ObstacleAssessmentSurfacePropertyType` | Segment için engel değerlendirme alanı — kapsam dışı |
| `curveExtent` | `CurvePropertyType` | GML geometrisi (`gml:Curve`/`LineString`) — segmentin fiziksel uzanımı, kapsam dışı |
| `end` (0..1) | `EnRouteSegmentPointPropertyType` | Segmentin bitiş noktası → bkz. `AIXM_RoutePoint_DataTypes.md` |
| `availability` (0..∞) | `RouteAvailabilityPropertyType` | → bkz. **2** |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |
| `cardinalDirectionLeft` | `CodeCardinalDirectionType` | 16 yön (`N, NE, E, SE, S, SW, W, NW, NNE, ENE, ESE, SSE, SSW, WSW, WNW, NNW` +OTHER) — start→end yönüne göre sol taraf |
| `cardinalDirectionRight` | `CodeCardinalDirectionType` | (aynı 16 yön) — start→end yönüne göre sağ taraf |
| `aircraftCapability` (0..∞) | `AircraftCharacteristicPropertyType` | Segmentte gereken uçak özellik/ekipman/kapasite kombinasyonu → bkz. **5** |
| `airspaceClass` (0..∞) | `AirspaceLayerClassPropertyType` | Segment üzerindeki hava sahası sınıfı bilgisi → bkz. **3** |

---

## 2. `availability` → RouteAvailability

`Route.availability` ile birebir aynı yapı (bkz. `AIXM_Route_Attributes.md`).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `direction` | `CodeRouteDirectionType` | `FORWARD, BACKWARD` (+OTHER) — **not:** genel `CodeDirectionType`'ın aksine `BOTH` değeri yok |
| `cardinalDirection` | `CodeCardinalDirectionType` | 16 yön (yukarıdaki gibi) |
| `status` | `CodeRouteAvailabilityType` | `OPEN, COND, CLSD` (+OTHER) |
| `levels` (0..∞) | `AirspaceLayerPropertyType` | Kullanılabilirliğin geçerli olduğu seviye/zaman bloğu → bkz. **4** |

---

## 3. `airspaceClass` → AirspaceLayerClass

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `classification` | `CodeAirspaceClassificationType` | `A, B, C, D, E, F, G` (ICAO Annex 11, Appendix 4) |
| `associatedLevels` (0..∞) | `AirspaceLayerPropertyType` | → bkz. **4** (AirspaceLayer ile birebir aynı yapı) |

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
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |

---

## 5. `aircraftCapability` → AircraftCharacteristic

> *"Classification, properties, and equipment capabilities of aircraft, such as
> airplane, balloon, helicopter, etc."* — `Route.aircraftCapability` ile birebir aynı
> tip (bkz. `AIXM_Route_Attributes.md`).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `engine` | `CodeAircraftEngineType` | `JET, PISTON, TURBOPROP, ELECTRIC, ALL` (+OTHER) |
| `numberEngine` | `CodeAircraftEngineNumberType` | `1, 2, 3, 4, 6, 8, 2C` (2C = iki bağlı motor, tek pervane) (+OTHER) |
| `typeAircraftICAO` | `CodeAircraftICAOType` | Enum değil — serbest alfanumerik, 1-4 karakter (örn. `A320`, `B738`) |
| `aircraftLandingCategory` | `CodeAircraftLandingCategoryType` | `A, B, C, D, E, H` (Helikopter), `DL` (D Large), `HPMA` (High Performance Military Aircraft), `A_B, C_D, A_B_C, A_B_C_D, A_B_C_D_DL` (+OTHER) |
| `wingSpan` | `ValDistanceType` | Sayı (≥0) + `uom`: `NM, KM, M, FT, MI, CM` |
| `wingSpanInterpretation` | `CodeValueInterpretationType` | `ABOVE, AT_OR_ABOVE, AT_OR_BELOW, BELOW` (+OTHER) — `wingSpan` değerinin üstü/altı mı |
| `classWingSpan` | `CodeAircraftWingspanClassType` | `A` (<15m), `B` (15-24m), `C` (24-36m), `D` (36-52m), `E` (52-65m), `F` (65-80m) (+OTHER) |
| `weight` | `ValWeightType` | Sayı (≥0) + `uom`: `KG, T, LB, TON` (+OTHER) — maksimum kalkış ağırlığı |
| `weightInterpretation` | `CodeValueInterpretationType` | `ABOVE, AT_OR_ABOVE, AT_OR_BELOW, BELOW` (+OTHER) |
| `passengers` | `NoNumberType` | Sayısal (`unsignedInt`) — maksimum yolcu sayısı |
| `passengersInterpretation` | `CodeValueInterpretationType` | `ABOVE, AT_OR_ABOVE, AT_OR_BELOW, BELOW` (+OTHER) |
| `speed` | `ValSpeedType` | Sayı + `uom`: `KM_H, KT, MACH, M_MIN, FT_MIN, M_SEC, FT_SEC, MPH` — sürdürülebilen IAS |
| `speedInterpretation` | `CodeValueInterpretationType` | `ABOVE, AT_OR_ABOVE, AT_OR_BELOW, BELOW` (+OTHER) — max mı min mi dayatılan değer |
| `wakeTurbulence` | `CodeWakeTurbulenceType` | `LIGHT` (≤7000kg), `MEDIUM` (7000-136000kg), `HEAVY` (≥136000kg), `SUPER`, `GROUP_A`...`GROUP_G` (kanat açıklığı bantlı, RECAT-EU) (+OTHER) |
| `navigationSpecification` | `CodeNavigationSpecificationType` | `RNAV_10, RNAV_5, RNAV_2, RNAV_1, RNP_4, RNP_2, RNP_APCH, RNP_AR_APCH, RNAV, RNP, RNP_1, A_RNP, RNP_0_3` (+OTHER) |
| `verticalSeparationCapability` | `CodeRVSMType` | `RVSM, NON_RVSM` (+OTHER) |
| `antiCollisionAndSeparationEquipment` | `CodeEquipmentAntiCollisionType` | `ACAS_I, ACAS_II, GPWS` (+OTHER) |
| `communicationEquipment` | `CodeCommunicationModeType` | `HF, VHF, VDL1, VDL2, VDL4, AMSS, ADS_B, ADS_B_VDL, HFDL, VHF_833, UHF` (+OTHER) |
| `surveillanceEquipment` | `CodeTransponderType` | `MODE_1, MODE_2, MODE_3A, MODE_4, MODE_5, MODE_C, MODE_S` (+OTHER) |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |
| `category` | `CodeAircraftCategoryType` | `LANDPLANE, SEAPLANE, AMPHIBIAN, HELICOPTER, GYROCOPTER, TILT_WING, STOL, GLIDER, HANGGLIDER, PARAGLIDER, ULTRA_LIGHT, BALLOON, ALL, UA` (İnsansız hava aracı) (+OTHER) |
| `navigationType` | `CodeNavigationType` | `CONV` (konvansiyonel), `TACAN`, `PBN` (Performance Based Navigation) (+OTHER) |
| `navigationAccuracy` | `ValNavigationAccuracyType` | Ondalık sayı, desen `[0-9]{1,2}(\.[0-9]{12})?` — RNP değeri (NM), `uom` yok |
| `dualFrequency` | `CodeYesNoType` | `YES, NO` — iki farklı frekansta (örn. dual VHF) eş zamanlı haberleşme kapasitesi |
| `helicopterPerformanceClass` | `CodeHelicopterPerformanceClassType` | `1, 2, 3, 2WE` (Class 2 with exposure) (+OTHER) |
| `radioNavigationEquipment` (0..∞) | `AircraftNavigationEquipmentPropertyType` | → bkz. **6** |

---

## 6. `radioNavigationEquipment` → AircraftNavigationEquipment

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `navigationEquipment` | `CodeNavigationEquipmentType` | `DME, VOR_DME, DME_DME, TACAN, ILS, MLS, GNSS, WAAS, LORAN, INS, FMS, VOR, DUAL_VOR, ADF, DUAL_ADF, DME_DME_IRU, FMS_RF` (+OTHER) |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](AIXM_Annotation_Attributes.md) |

> Not: Aynı `AircraftCharacteristic` için birden fazla `radioNavigationEquipment` tekrarı
> **"ve" (and)** operatörüyle yorumlanır (örn. hem `GNSS` hem `DME_DME` gerektiği anlamına
> gelir) — XSD annotation'ına göre.

---

## Talep edilen tipik AIXM RouteSegment öznitelikleriyle eşleşme

| Beklenen kavram | Şemadaki karşılığı |
|---|---|
| `pathType` | `pathType` (`GRC/RHL/GDS`) |
| `type`/`kind` | RouteSegment'te yok — sınıflandırma **Route.type** seviyesinde (`ATS/NAT`) |
| `level` (upper/lower) | `level`, `upperLimit(Reference)`, `lowerLimit(Reference)` |
| `direction` (uçuş yönü) | RouteSegment'te değil — `RouteAvailability.direction` (`FORWARD/BACKWARD`) ve `turnDirection` üzerinden |
| `reversible` | Bu isimde alan yok — en yakını `reverseTrueTrack`/`reverseMagneticTrack` ve `RouteAvailability.direction` |
| `class` | `airspaceClass` → `AirspaceLayerClass.classification` (`A`-`G`, bkz. **3**) |
| `width` | Tek alan değil — `widthLeft` / `widthRight` ayrı ayrı |
| `nature` | Bu isimde alan yok — en yakını `designatorSuffix` (F/G) |
| `multipleTrackSeparation` | Bu şemada (AIXM 5.2) bulunamadı |

---

## Ortak (base) attribute'lar

`RouteSegmentType` → `AbstractAIXMFeatureType`, `RouteSegmentTimeSliceType` →
`AbstractAIXMTimeSliceType`'dan miras alır (bkz. `AIXM_Route_Attributes.md`'deki not).

## Genişletme noktası

`extension` alanı → soyut `AbstractRouteSegmentExtension` (ulusal AIP'lerin kendi ek
alanlarını eklemesi için extension noktası, boş/soyut tanımlı).
