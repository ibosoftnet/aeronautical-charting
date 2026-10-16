# AIXM 5.2 — Havalimanı Yüzeylerinin Ortak Objeleri

Kaynak: `AIXM_Features_annotated.xsd` (`SurfaceCharacteristics` ~1400; Availability/Usage
~773, ~1634, ~2213, ~4706; Contamination ~6393-6980; ışık üst sınıfı ~3130; işaret üst
sınıfı ~4100; `ElevatedPoint/Curve/Surface` ~8205-8517; `PropertiesWithSchedule` ~21842;
`LightElement` ~21489) + `AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

Bu doküman pist, taksi yolu, apron, park yeri ve TLOF'un **ortak** kullandığı yapı
taşlarını anlatır. Hepsi **Object**'tir (kendi UUID'leri yoktur, ilgili feature'ın
içine gömülü yazılır) — ışık ve işaret üst sınıfları hariç (onlar Feature'dır).

---

## 1. SurfaceCharacteristics (`surfaceProperties`)

Bir hareket alanı yüzeyinin dayanım, malzeme vb. özellikleri. Kullanan feature'lar:
`Runway`, `RunwayElement`, `RunwayBlastPad`, `RunwayProtectArea`, `ArrestingGear`,
`Taxiway`, `TaxiwayElement`, `Apron`, `ApronElement`, `AircraftStand`, `DeicingArea`,
`Road`, `TouchDownLiftOff`, `TouchDownLiftOffSafeArea`.

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `composition` | `CodeSurfaceCompositionType` | → §1.1 | Ana kaplama malzemesi |
| `preparation` | `CodeSurfacePreparationType` | → §1.2 | Yüzey işlemi |
| `surfaceCondition` | `CodeSurfaceConditionType` | `EXCELLENT, GOOD, FAIR, POOR, FAILED, DEFORMED, UNSAFE` | Kaplama kalitesi (çatlak yoğunluğuna göre tanımlı) |
| **PCN (eski ACN-PCN)** | | | |
| `classPCN` | `ValPavementStrengthType` | `[0-9]{1,4}(\.[0-9])?` | PCN sayısal değeri |
| `pavementTypePCN` | `CodePavementBehaviourType` | `RIGID` [R], `FLEXIBLE` [F] | |
| `pavementSubgradePCN` | `CodePavementSubgradeType` | `A` (yüksek), `B` (orta), `C` (düşük), `D` (çok düşük) | Zemin dayanımı |
| `maxTyrePressurePCN` | `CodeTyrePressureType` | `W` (sınırsız), `X` (yüksek), `Y` (orta), `Z` (düşük) | |
| `evaluationMethodPCN` | `CodePavementStrengthMethodType` | `TECH` [T], `ACFT` [U] | Değerlendirme yöntemi |
| **Diğer dayanım yöntemleri** | | | |
| `classLCN` | `ValLCNType` | decimal | Load Classification Number |
| `weightSIWL` | `ValWeightType` | ≥0 + `uom` (`KG, T, LB, TON`) | Single Isolated Wheel Load |
| `tyrePressureSIWL` | `ValPressureType` | + `uom` (`PA, MPA, PSI, BAR, TORR, ATM, HPA`) | SIWL lastik basıncı |
| `weightAUW` | `ValWeightType` | + `uom` | All Up Weight — iniş takımından bağımsız max ağırlık |
| `annotation` (0..∞) | `NotePropertyType` | | |
| **PCR (yeni ACR-PCR, 2024+)** | | | |
| `classPCR` | `ValPavementStrengthType` | `[0-9]{1,4}(\.[0-9])?` | PCR sayısal değeri |
| `pavementTypePCR` | `CodePavementBehaviourType` | `RIGID, FLEXIBLE` | |
| `pavementSubgradePCR` | `CodePavementSubgradeType` | `A, B, C, D` | |
| `maxTyrePressurePCR` | `CodeTyrePressureType` | `W, X, Y, Z` | |
| `evaluationMethodPCR` | `CodePavementStrengthMethodType` | `TECH, ACFT` | |

> **Okuma örneği:** AIP'deki `PCN 80/F/B/W/T` →
> `classPCN=80, pavementTypePCN=FLEXIBLE, pavementSubgradePCN=B, maxTyrePressurePCN=W, evaluationMethodPCN=TECH`.
> `PCR 1030/R/A/W/T` → `classPCR=1030, pavementTypePCR=RIGID, ...PCR` alanları.
> PCN ve PCR alanları aynı objede yan yana bulunabilir (geçiş dönemi).
>
> **Sıra:** PCR alanları şemada `annotation`'dan **sonra** gelir; XML'de de bu sırayla
> yazılmalıdır.

### 1.1 CodeSurfaceCompositionType

`ASPH` (asfalt), `ASPH_GRASS`, `CONC` (beton), `CONC_ASPH`, `CONC_GRS`, `GRASS` (çim/toprak
karışık), `SAND`, `WATER`, `BITUM` (bitümlü karışım), `BRICK`, `MACADAM`, `STONE`, `CORAL`,
`CLAY`, `LATERITE`, `GRAVEL`, `EARTH`, `ICE`, `SNOW`, `MEMBRANE`, `METAL`, `MATS` (portatif
iniş matı), `PIERCED_STEEL`, `WOOD`, `NON_BITUM_MIX`, `ASPH_EARTH`, `ASPH_GRAVEL`,
`CONC_EARTH`, `CONC_GRAVEL`, `GRASS_EARTH`, `GRASS_GRAVEL` (+`OTHER`)

### 1.2 CodeSurfacePreparationType

`NATURAL`, `ROLLED`, `COMPACTED`, `GRADED`, `GROOVED`, `OILED`, `PAVED`, `PFC` (porous
friction coat), `AFSC` (aggregate friction seal coat), `RFSC` (rubberised friction seal
coat), `NON_GROOVED`, `WIRE_COMB` (+`OTHER`)

---

## 2. Geometri tipleri

Tümü GML tiplerini genişletir ve dikey konum bilgisi ekler. Yazım sırası: önce GML
geometrisi, sonra AIXM alanları.

| Tip | GML tabanı | Ek alanlar |
|---|---|---|
| `ElevatedPoint` | `gml:PointType` (`gml:pos`) | `elevation`, `geoidUndulation`, `verticalDatum`, `horizontalAccuracy`, `annotation` |
| `ElevatedCurve` | `gml:CurveType` (`gml:segments`) | aynı 5 alan |
| `ElevatedSurface` | `gml:SurfaceType` (`gml:patches`) | aynı 5 alan |
| `Surface` (yalnız `WaterBody.extent`) | `gml:SurfaceType` | `horizontalAccuracy`, `annotation` — **yükseklik yok** |

| Alan | Değer Tipi | Açıklama |
|---|---|---|
| `elevation` | `ValDistanceVerticalType` | MSL'den yükseklik (+`uom`) |
| `geoidUndulation` | `ValDistanceSignedType` | Geoidin elipsoide göre yüksekliği (+ yukarı / − aşağı) — AD 2.12 "geoid undulation at THR" |
| `verticalDatum` | `TextNameType` | Dikey datum adı |
| `horizontalAccuracy` | `ValDistanceType` | Yatay doğruluk (PANS-AIM güven seviyesinde dairesel hata) |

**Poligon örneği** (`ElevatedSurface`, EPSG:4326 lat-lon sırası, halka kapalı):

```xml
<aixm:extent>
  <aixm:ElevatedSurface gml:id="RWE_0523_1_ES" srsName="urn:ogc:def:crs:EPSG::4326">
    <gml:patches>
      <gml:PolygonPatch>
        <gml:exterior>
          <gml:LinearRing>
            <gml:posList>40.1 29.6 40.1 29.62 40.1005 29.62 40.1005 29.6 40.1 29.6</gml:posList>
          </gml:LinearRing>
        </gml:exterior>
      </gml:PolygonPatch>
    </gml:patches>
    <aixm:elevation uom="FT">320</aixm:elevation>
  </aixm:ElevatedSurface>
</aixm:extent>
```

**Çizgi örneği** (`ElevatedCurve`):

```xml
<aixm:extent>
  <aixm:ElevatedCurve gml:id="GL_A_1_EC" srsName="urn:ogc:def:crs:EPSG::4326">
    <gml:segments>
      <gml:LineStringSegment>
        <gml:posList>40.1010 29.6000 40.1010 29.6100 40.1015 29.6150</gml:posList>
      </gml:LineStringSegment>
    </gml:segments>
  </aixm:ElevatedCurve>
</aixm:extent>
```

---

## 3. Availability / Usage (operasyonel durum)

Tüm Availability objeleri `AbstractPropertiesWithScheduleType`'tan türer:

| Miras alan | Değer Tipi | Açıklama |
|---|---|---|
| `timeInterval` (0..∞) | `TimesheetPropertyType` | Zaman çizelgesi; **yoksa durum sürekli geçerli** kabul edilir (AIXM kodlama konvansiyonu — şema metninde yazmaz) |
| `annotation` (0..∞) | `NotePropertyType` | |
| `specialDateAuthority` (0..∞) | `OrganisationAuthorityPropertyType` | Timesheet'teki `HOL` vb. özel günlerin hangi otoritenin `SpecialDate` listesinden alınacağı |

### 3.1 Hangi feature hangi Availability tipini kullanır?

| Availability tipi | `operationalStatus` tipi | Usage tipi | Kullanan feature'lar |
|---|---|---|---|
| `AirportHeliportAvailability` | `CodeStatusAirportType` | `AirportHeliportUsage` (+`operation`: `CodeOperationAirportHeliportType`) | `AirportHeliport` |
| `ManoeuvringAreaAvailability` | `CodeStatusAirportType` | `ManoeuvringAreaUsage` (+`operation`: `CodeOperationManoeuvringAreaType`) | `RunwayDirection`, `RunwayElement`, `Taxiway`, `TaxiwayElement`, `TouchDownLiftOff`, `SeaplaneLandingArea`, `GuidanceLine` (GuidanceLineDirection üzerinden) |
| `ApronAreaAvailability` | `CodeStatusAirportType` | `ApronAreaUsage` (**`operation` yok**) | `Apron`, `ApronElement`, `AircraftStand`, `DeicingArea` |
| `GroundLightingAvailability` | `CodeStatusOperationsType` | — | Tüm `*LightSystem`'ler |
| (tek alan `status`) | `CodeStatusOperationsType` | — | `RunwayProtectArea`, `RunwayBlastPad`, `ArrestingGear`, `TaxiHoldingPosition`, `Road` (Timesheet'siz, düz alan) |

Ortak alanlar (`AirportHeliport`/`Manoeuvring`/`Apron` availability):

| Attribute | Değer Tipi | Enum |
|---|---|---|
| `operationalStatus` | `CodeStatusAirportType` | `NORMAL, LIMITED, CLOSED, EXTENDED` |
| `warning` | `CodeAirportWarningType` | `WIP, EQUIP, BIRD, ANIMAL, RUBBER_REMOVAL, PARKED_ACFT, RESURFACING, PAVING, PAINTING, INSPECTION, GRASS_CUTTING, CALIBRATION` |
| `usage` (0..∞) | ilgili Usage tipi | |

`CodeStatusOperationsType`: `NORMAL, DOWNGRADED, UNSERVICEABLE, WORK_IN_PROGRESS`.

### 3.2 Usage (AbstractUsageCondition)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeUsageLimitationType` | `PERMIT, CONDITIONAL, FORBID, RESERV` |
| `priorPermission` | `ValDurationType` | Yalnız `CONDITIONAL` için, PPR süresi (`HR, MIN, SEC`) |
| `contact` (0..∞) | `ContactInformationPropertyType` | |
| `selection` | `ConditionCombinationPropertyType` | Filtre: `logicalOperator` + `weather` / `aircraft` / `flight` / `subCondition` (bkz. `AIXM_AirportHeliport_Attributes.md` §2.3) |
| `annotation` (0..∞) | `NotePropertyType` | |
| `operation` | (yalnız AirportHeliport/Manoeuvring usage) | `ManoeuvringArea`: `LANDING, TAKEOFF, TOUCHGO, TRAIN_APPROACH, TAXIING, CROSSING, AIRSHOW, ALL` |

---

## 4. Contamination (kar/buz/su — SNOWTAM / GRF)

Tümü `AbstractSurfaceContaminationType`'tan türeyen **Object**'lerdir.

### 4.1 Ortak alanlar (AbstractSurfaceContamination)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `observationTime` | `DateTimeType` | Ölçüm tamamlanma zamanı |
| `depth` | `ValDepthType` | Derinlik + `uom` (`MM, CM, IN, FT`) |
| `frictionCoefficient` | `ValFrictionType` | `0.NN` biçiminde (ör. `0.35`) |
| `frictionEstimation` | `CodeFrictionEstimateType` | `GOOD, MEDIUM_GOOD, MEDIUM, MEDIUM_POOR, POOR, UNRELIABLE`, **`RWYCC_0` … `RWYCC_6`** (GRF pist durum kodu) |
| `frictionDevice` | `CodeFrictionDeviceType` | `BRD, GRT, MUM, RFT, SFH, SFL, SKH, SKL, TAP` |
| `obscuredLights` | `CodeYesNoType` | Işıklar kirlilikle örtülü mü |
| `furtherClearanceTime` | `TimeType` | Ek temizliğin beklenen bitiş saati |
| `furtherTotalClearance` | `CodeYesNoType` | Tam temizlik bekleniyor mu |
| `nextObservationTime` | `DateTimeType` | Sonraki ölçüm |
| `proportion` | `ValPercentType` | Kirli alan yüzdesi (0-100) |
| `criticalRidge` (0..∞) | `RidgePropertyType` | → **Ridge** (O): `side` (`LEFT, RIGHT, BOTH, CENTRE`), `distance` (kenardan), `depth` (yükseklik), `annotation` — kar setleri |
| `layer` (0..∞) | `SurfaceContaminationLayerPropertyType` | → **SurfaceContaminationLayer** (O): `layerOrder` (üstten alta), `type` (`CodeContaminationType`), `extent` (0..∞ ElevatedSurface), `annotation` |
| `annotation` (0..∞) | `NotePropertyType` | |

`CodeContaminationType`: `NONE, DRY, WET, WATER, STANDING_WATER, SLIPPERY_WET, FROST,
DRY_SNOW, WET_SNOW, SLUSH, ICE, WET_ICE, COMPACT_SNOW, PREPARED_WINTER_RWY, DRIFTING_SNOW,
RUT, ASH, SAND, LOOSE_SAND, OIL, RUBBER, GRAS, CHEMICAL_TREATMENT` (+`OTHER`)

### 4.2 Alt tipler

| Obje | Kullanan feature.attribute | Ek alanlar |
|---|---|---|
| `AirportHeliportContamination` | `AirportHeliport.contaminant` | — |
| `RunwayContamination` | `Runway.overallContaminant` | `clearedLength`, `clearedWidth`, `clearedSide` (`CodeSideType`), `furtherClearanceLength`, `furtherClearanceWidth`, `obscuredLightsSide`, `clearedLengthBegin` (düşük numaralı eşikten), `taxiwayAvailable`, `apronAvailable` |
| `RunwaySectionContamination` | `Runway.areaContaminant` | `section` (`CodeRunwaySectionType` — tipik `1_THIRD`, `2_THIRD`, `3_THIRD`) |
| `TaxiwayContamination` | `Taxiway.contaminant` | `clearedWidth` |
| `ApronContamination` | `Apron.contaminant` | — |
| `AircraftStandContamination` | `AircraftStand.contaminant` | — |
| `TouchDownLiftOffContamination` | `TouchDownLiftOff.contaminant` | — |

> **GRF/SNOWTAM eşlemesi (yorum):** pist üçte birleri için üç `RunwaySectionContamination`
> (`section=1_THIRD/2_THIRD/3_THIRD`) — her birinde `frictionEstimation=RWYCC_n`,
> `proportion`, `depth` ve `layer{type}`. "Üçte bir"ler **düşük numaralı eşikten** sayılır
> (şema tanımı).

---

## 5. Işık sistemleri üst sınıfı (AbstractGroundLightSystem) — Feature

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `emergencyLighting` | `CodeYesNoType` | Yedek ışık sistemi |
| `intensityLevel` | `CodeLightIntensityType` | `LIL` (düşük), `LIM` (orta), `LIH` (yüksek), `LIL_LIH` (gece düşük/gündüz yüksek, fotosel), `PREDETERMINED` |
| `colour` | `CodeColourType` | `YELLOW, RED, WHITE, BLUE, GREEN, PURPLE, ORANGE, AMBER, BLACK, BROWN, GREY, LIGHT_GREY, MAGENTA, PINK, VIOLET, RED_WHITE` |
| `element` (0..∞) | `LightElementPropertyType` | → §5.1 |
| `availability` (0..∞) | `GroundLightingAvailabilityPropertyType` | `operationalStatus`: `NORMAL, DOWNGRADED, UNSERVICEABLE, WORK_IN_PROGRESS` (+ Timesheet) |
| `annotation` (0..∞) | `NotePropertyType` | |

Alt sınıflar ve bağ alanları:

| Alt sınıf | Kendi alanları (bağ **kalın**) |
|---|---|
| `ApproachLightingSystem` | `classICAO`, `type`, `length`, `sequencedFlashing`, `alignmentIndicator`, **`servedRunwayDirection`** |
| `RunwayDirectionLightSystem` | `position`, **`associatedRunwayDirection`**, `type`, `length`, `spacing`, `group` |
| `RunwayProtectAreaLightSystem` | `position`, **`lightedArea`**, `length` |
| `VisualGlideSlopeIndicator` | `type`, `position`, `numberBox`, ... **`runwayDirection`** ... |
| `TaxiwayLightSystem` | `position`, **`lightedTaxiway`** |
| `GuidanceLineLightSystem` | **`lightedGuidanceLine`** |
| `TaxiHoldingPositionLightSystem` | `type`, **`taxiHolding`** |
| `ApronLightSystem` | `position`, **`lightedApron`** |
| `TouchDownLiftOffLightSystem` | `position`, **`lightedTouchDownLiftOff`** |

### 5.1 LightElement (O)

Işık sistemini oluşturan tekil ışık kaynağı (ör. tek bir kenar ışığı).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `colour` | `CodeColourType` | |
| `intensityLevel` | `CodeLightIntensityType` | |
| `intensity` | `ValLightIntensityType` | Kesin yoğunluk + `uom` |
| `type` | `CodeLightSourceType` | `FLOOD, STROBE` |
| `location` | `ElevatedPointPropertyType` | **Işığın konumu** |
| `annotation` (0..∞) | `NotePropertyType` | |
| `availability` (0..∞) | `LightElementStatusPropertyType` | Tekil ışık durumu (+ Timesheet) |
| `direction` | `CodeLightDirectionType` | `UNIDIRECTIONAL, BIDIRECTIONAL, OMNIDIRECTIONAL` |
| `lightingTechnology` | `CodeLightingTechnologyType` | `FLUORESCENT, HALOGEN, INCANDESCENT, LED` |

---

## 6. İşaret üst sınıfı (AbstractMarking) — Feature

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `markingICAOStandard` | `CodeYesNoType` | Annex 14'e uygun mu |
| `condition` | `CodeMarkingConditionType` | `GOOD, FAIR, POOR, EXCELLENT` |
| `element` (0..∞) | `MarkingElementPropertyType` | → §6.1 |
| `annotation` (0..∞) | `NotePropertyType` | |

Alt sınıflar: `RunwayMarking` (→ Runway), `TaxiwayMarking` (→ Taxiway / TaxiwayElement),
`TaxiHoldingPositionMarking`, `GuidanceLineMarking`, `ApronMarking`, `StandMarking`,
`DeicingAreaMarking`, `TouchDownLiftOffMarking`, `AirportProtectionAreaMarking`
(`markingLocation`: `EDGE, END, CL`; `markedProtectionArea` → RunwayProtectArea veya
TouchDownLiftOffSafeArea).

### 6.1 MarkingElement (O)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `colour` | `CodeColourType` | |
| `style` | `CodeMarkingStyleType` | `SOLID, DASHED, DOTTED` |
| `extent_curveExtent` \| `extent_surfaceExtent` \| `extent_location` | `ElevatedCurve` \| `ElevatedSurface` \| `ElevatedPoint` | **choice** — yalnızca biri |
| `annotation` (0..∞) | `NotePropertyType` | |
