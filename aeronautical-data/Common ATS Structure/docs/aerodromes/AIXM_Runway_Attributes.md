# AIXM 5.2 — Pist Ailesi: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (satır ~2926-3650 ışık, ~4227 işaret, ~4568-5850
pist feature'ları) + `AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> Pist modeli 4 katmandır:
>
> | Katman | Feature | Geometri |
> |---|---|---|
> | Fiziksel pist (iki yönü birlikte) | `Runway` | **yok** |
> | Yön (05 / 23) | `RunwayDirection` ×2 | **yok** |
> | Eksen üzerindeki noktalar (THR, END, TDZ...) | `RunwayCentrelinePoint` | nokta |
> | Yüzey parçaları | `RunwayElement` | alan |
>
> Buna yöne bağlı koruma alanları (`RunwayProtectArea`: stopway, clearway, RESA...),
> blast pad, arresting gear, RVR, VGSI/PAPI ve ışık sistemleri eklenir.
> Ekleme adımları ve XML örneği: `AIXM_Surfaces_How_To_Add.md` §2.

---

## 1. Runway

Kara veya su meydanında uçakların iniş/kalkışı için hazırlanmış tanımlı dikdörtgen alan.
Helikopter **FATO** da bu feature ile modellenir (`type=FATO`).

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `designator` | `TextDesignatorType` | 1-16 karakter, büyük harf/rakam/işaret | Meydanda pisti benzersiz tanımlayan ad, ör. `05/23`, `16L/34R` |
| `type` | `CodeRunwayType` | `RWY` (uçak pisti), `FATO` (helikopter final yaklaşma ve kalkış alanı), `WATER_RWY` (su pisti) | |
| `nominalLength` | `ValDistanceType` | ≥0 + `uom` | Performans hesabı için beyan edilen uzunluk (AD 2.12 "Dimensions") |
| `nominalWidth` | `ValDistanceType` | 〃 | Beyan edilen genişlik |
| `widthShoulder` | `ValDistanceType` | 〃 | Omuz genişliği |
| `lengthStrip` | `ValDistanceType` | 〃 | Strip uzunluğu (pist + varsa stopway'i içeren alan) |
| `widthStrip` | `ValDistanceType` | 〃 | Strip genişliği |
| `lengthOffset` | `ValDistanceSignedType` | işaretli + `uom` | Strip, iki uçta simetrik değilse boyuna kayma |
| `widthOffset` | `ValDistanceSignedType` | işaretli + `uom` | Strip, iki kenarda simetrik değilse yanal kayma |
| `abandoned` | `CodeYesNoType` | `YES, NO` | Kullanım dışı ama fiziksel olarak mevcut |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | → `AIXM_Surface_Common_Objects.md` §1 | Kaplama, PCN/PCR |
| `associatedAirportHeliport` | `AirportHeliportPropertyType` | xlink | **Bağlı meydan** |
| `overallContaminant` (0..∞) | `RunwayContaminationPropertyType` | → `AIXM_Surface_Common_Objects.md` §4 | Pistin genel kirliliği |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `areaContaminant` (0..∞) | `RunwaySectionContaminationPropertyType` | → §4 | Pist bölümü (1/3'ler) kirliliği |
| `referenceCodeFieldLength` | `CodeAircraftFieldLengthType` | `1` (<800 m), `2` (800-1200), `3` (1200-1800), `4` (≥1800) | Aerodrome reference code — rakam kısmı |
| `referenceCodeWingspan` | `CodeAircraftWingspanClassType` | `A` (<15 m), `B` (15-24), `C` (24-36), `D` (36-52), `E` (52-65), `F` (65-80) | Aerodrome reference code — harf kısmı |
| `depth` | `ValDistanceType` | ≥0 + `uom` | Yalnızca su pisti: düşük su seviyesinde derinlik |

> **Runway'de `availability` yoktur.** Operasyonel durum (açık/kapalı/kısıtlı) yön bazında
> `RunwayDirection.availability` ve yüzey bazında `RunwayElement.availability` üzerinden
> verilir. Runway'de ayrıca **geometri alanı yoktur**.

---

## 2. RunwayDirection

Bir pistin veya FATO'nun iki iniş/kalkış yönünden biri. Her `Runway` için normalde **iki**
`RunwayDirection` kaydı olur (ör. `05` ve `23`).

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `designator` | `TextDesignatorType` | 1-16 karakter | Yön tanımlayıcısı, ör. `05`, `34R` |
| `trueBearing` | `ValBearingType` | 0-360 | Gerçek kuzeye göre yön (AD 2.12 "TRUE BRG") |
| `magneticBearing` | `ValBearingType` | 0-360 | Manyetik kuzeye göre yön |
| `patternVFR` | `CodeDirectionTurnType` | `LEFT, RIGHT, EITHER` | VFR trafik paterni dönüş yönü |
| `slopeTDZ` | `ValSlopeType` | `-100..100` | TDZ boyuna eğimi (pist uzunluğunun ilk 1/3'ü) |
| `elevationTDZ` | `ValDistanceVerticalType` | + `uom` | TDZ'nin en yüksek noktası (AD 2.12 "THR/TDZ ELEV") |
| `approachMarkingType` | `CodeRunwayMarkingType` | → §11.2 | Yaklaşma işaretleme sınıfı |
| `approachMarkingCondition` | `CodeMarkingConditionType` | `GOOD, FAIR, POOR, EXCELLENT` | İşaret kalitesi |
| `classLightingJAR` | `CodeLightingJARType` | `FALS` (≥720 m ALS), `IALS` (420-720 m), `BALS` (<420 m), `NALS` (yok/yetersiz) | JAR-OPS 1 yaklaşma ışığı sınıfı (minima hesabı için) |
| `usedRunway` | `RunwayPropertyType` | xlink | **Bağlı Runway** |
| `startingElement` | `RunwayElementPropertyType` | xlink | Yönün başladığı `RunwayElement` — tipik olarak kaydırılmış eşik alanı (`DISPLACED`) |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `availability` (0..∞) | `ManoeuvringAreaAvailabilityPropertyType` | → `AIXM_Surface_Common_Objects.md` §3 | Yönün operasyonel durumu / kullanım kuralları (ör. "yalnızca iniş") |
| `slope` | `ValSlopeType` | `-100..100` | Yaklaşma ucundan kalkış ucuna ortalama eğim |
| `approachGuidance` | `CodeRunwayApproachGuidanceType` | `NON_INSTRUMENT, NON_PRECISION, PRECISION_CAT_I, PRECISION_CAT_II, PRECISION_CAT_III, PRECISION_CAT_IIIA, PRECISION_CAT_IIIB, PRECISION_CAT_IIIC` | Annex 14 pist sınıfı (görsel/görsel olmayan yardımlara göre) |

> RunwayDirection'ın da **geometrisi yoktur**. Yön doğrusu, bu yönün `THR` (veya `START`)
> ve `END` rolündeki `RunwayCentrelinePoint`'lerinden türetilir.

---

## 3. RunwayCentrelinePoint

Bir pist yönünün ekseni üzerindeki operasyonel olarak önemli konum (tipik örnek: eşik).

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `role` | `CodeRunwayPointRoleType` | → aşağıdaki tablo | Noktanın rolü |
| `designator` | `TextDesignatorType` | 1-16 karakter | Meydanda benzersiz nokta adı |
| `location` | `ElevatedPointPropertyType` | → `ElevatedPoint` | **Konum + yükseklik + geoid undulation** (AD 2.12 THR koordinatları) |
| `associatedDeclaredDistance` (0..∞) | `RunwayDeclaredDistancePropertyType` | → **§4** | Bu noktada başlayan beyan mesafeleri |
| `navaidEquipment` (0..∞) | `NavaidEquipmentDistancePropertyType` | → **§5** | Noktaya göre konumu verilen navaid ekipmanı |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `relativeDistance` | `ValDistanceType` | ≥0 + `uom` | Yönün **fiziksel başlangıcından** bu noktaya mesafe (ör. kaydırılmış eşik mesafesi) |
| `onRunwayDirection` | `RunwayDirectionPropertyType` | xlink | **Bağlı RunwayDirection** |

### `role` → CodeRunwayPointRoleType

| Değer | Açıklama |
|---|---|
| `START` | Yönün fiziksel başlangıcı |
| `THR` | Eşik |
| `DISTHR` | Kaydırılmış eşik |
| `TDZ` | Teker koyma bölgesi |
| `MID` | Pistin orta noktası |
| `END` | Yönün fiziksel sonu |
| `START_RUN` | Kalkış koşusunun başlangıcı (ör. kesişimden kalkış) |
| `LAHSO` | Land And Hold Short noktası |
| `ABEAM_GLIDESLOPE` | GP antenine dik eksen noktası (aiming point) |
| `ABEAM_PAR` | PAR antenine dik eksen noktası |
| `ABEAM_ELEVATION` | Elevation antenine dik eksen noktası |
| `ABEAM_TDR` | Touchdown Reflector'a dik eksen noktası |
| `ABEAM_RER` | Runway End Reflector'a dik eksen noktası |
| `HEL_AIMING_PT` | Helikopter nişan noktası |
| `DER` | Departure End of Runway (kalkış prosedürlerinde) |

(+`OTHER`)

> **Tipik set:** Her yön için `THR` (eşik; kaydırılmışsa `DISTHR` + ayrıca `START`), `END`,
> gerekirse `TDZ`, `MID`, `ABEAM_GLIDESLOPE`, `DER`. `RunwayCentrelinePoint` aynı zamanda
> rota/prosedür dünyasında **significant point** olarak kullanılabilir
> (`pointChoice_runwayPoint`, `DesignatedPoint.runwayPoint`, `FinalLeg.finalPathAlignmentPoint_runwayPoint`...).

---

## 4. Declared distances: RunwayDeclaredDistance → RunwayDeclaredDistanceValue

Beyan mesafeleri ayrı bir feature değil, **`RunwayCentrelinePoint` içine gömülü** objedir.

```
RunwayCentrelinePoint (F)
 └─ associatedDeclaredDistance (0..∞)
     └─ RunwayDeclaredDistance (O)        type = TORA | TODA | ASDA | LDA | ...
         └─ declaredValue (0..∞)
             └─ RunwayDeclaredDistanceValue (O, PropertiesWithSchedule)
                  distance = 3000 M   (+ opsiyonel timeInterval)
```

### 4.1 RunwayDeclaredDistance

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeDeclaredDistanceType` | `TORA` (take-off run available), `TODA` (take-off distance available), `ASDA` (accelerate-stop distance available), `LDA` (landing distance available), `TODAH` / `RTODAH` / `LDAH` (helikopter karşılıkları) |
| `declaredValue` (0..∞) | `RunwayDeclaredDistanceValuePropertyType` | → §4.2 — birden fazla değer = zamana bağlı farklı değerler |
| `annotation` (0..∞) | `NotePropertyType` | |

### 4.2 RunwayDeclaredDistanceValue

`AbstractPropertiesWithScheduleType`'tan türer → `timeInterval` (Timesheet),
`specialDateAuthority`, `annotation` da vardır.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `distance` | `ValDistanceType` | ≥0 + `uom` |

> **Hangi noktaya asılır?** Şema dokümantasyonu yalnızca "centreline point'in sağladığı
> declared distance" der. Mantıksal karşılık (yorum): mesafenin **başladığı** nokta —
> TORA/TODA/ASDA kalkış koşusunun başladığı `START` (veya kesişim kalkışı için
> `START_RUN`) noktasına, LDA iniş eşiği olan `THR`/`DISTHR` noktasına. Aynı pist yönü
> için kesişimden kalkış mesafeleri, ilgili `START_RUN` noktasına ikinci bir TORA/TODA/ASDA
> seti olarak eklenir.

---

## 5. NavaidEquipmentDistance (O)

Pist eksen noktası ile bir navaid ekipmanı arasındaki mesafe (ör. GP anteni ↔ THR,
LOC ↔ END).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `distance` | `ValDistanceType` | ≥0 + `uom` |
| `annotation` (0..∞) | `NotePropertyType` | |
| `theNavaidEquipment` | `NavaidEquipmentPropertyType` | → `Localizer`, `Glidepath`, `DME`, `MarkerBeacon`... (bkz. `../aixm-point-types/AIXM_NavaidEquipment_Attributes.md`) |

---

## 6. RunwayElement

Pistin başka sınıflarla tanımlanmamış poligon parçaları. Pistin çizilebilir yüzeyi bu
elemanlardan oluşur.

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `type` | `CodeRunwayElementType` | `NORMAL` (varsayılan), `INTERSECTION` (pist/taksi kesişimi), `DISPLACED` (başlangıç ile kaydırılmış eşik arası), `SHOULDER` (omuz) | |
| `length` | `ValDistanceType` | ≥0 + `uom` | |
| `width` | `ValDistanceType` | ≥0 + `uom` | |
| `gradeSeparation` | `CodeGradeSeparationType` | `UNDERPASS` (tünelde), `OVERPASS` (köprüde) | Başka bir elemandan farklı seviyede |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | → §1 ortak obje | Parça bazında kaplama/PCN (pist genelinden farklıysa) |
| `associatedRunway` (0..∞) | `RunwayPropertyType` | xlink | **Bağlı Runway(ler)** — `INTERSECTION` elemanı iki piste birden ait olabilir |
| `extent` | `ElevatedSurfacePropertyType` | poligon | **Geometri** |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `availability` (0..∞) | `ManoeuvringAreaAvailabilityPropertyType` | | Parça bazında kapalılık (ör. kesişim kapalı) |

> AMDB (DO-272/ED-99) karşılıkları şema notlarında geçer: `RunwayElement` ↔ AMDB
> RunwayElement / RunwayIntersection / RunwayShoulder (Rule 1-3). Taksi yolu ile kesişim
> parçası hem `RunwayElement(type=INTERSECTION)` hem `TaxiwayElement(type=INTERSECTION)`
> olarak modellenebilir; hangisinin kullanılacağı veri sağlayıcının kuralıdır.

---

## 7. RunwayProtectArea

Pist yakınında, manevra/kalkış/iniş sırasında uçağı korumak için tanımlı alan.
`AbstractAirportHeliportProtectionArea`'dan türer.

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| *(miras)* `width` | `ValDistanceType` | + `uom` | |
| *(miras)* `length` | `ValDistanceType` | + `uom` | |
| *(miras)* `lighting` | `CodeYesNoType` | | Düşük görüşte alanı gösteren ışık var mı |
| *(miras)* `obstacleFree` | `CodeYesNoType` | | Mâniasız mı |
| *(miras)* `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | | |
| *(miras)* `extent` | `ElevatedSurfacePropertyType` | | **Geometri** |
| *(miras)* `annotation` (0..∞) | `NotePropertyType` | | |
| `type` | `CodeRunwayProtectionAreaType` | → aşağıdaki tablo | |
| `status` | `CodeStatusOperationsType` | `NORMAL, DOWNGRADED, UNSERVICEABLE, WORK_IN_PROGRESS` | |
| `protectedRunwayDirection` | `RunwayDirectionPropertyType` | xlink | **Bağlı RunwayDirection** (DO-272 Rule 7-8: displaced area / stopway ↔ threshold) |

### `type` → CodeRunwayProtectionAreaType

| Değer | Açıklama | AIP karşılığı |
|---|---|---|
| `CWY` | Clearway | AD 2.13 CWY |
| `STOPWAY` | Stopway — TORA sonunda, iptal edilen kalkışta durmaya uygun hazırlanmış alan | AD 2.12 SWY |
| `RESA` | Runway End Safety Area | AD 2.12 RESA |
| `OFZ` | Obstacle Free Zone | AD 2.12 OFZ |
| `IOFZ` | Inner Obstacle Free Zone | |
| `POFZ` | Precision Obstacle Free Zone | |
| `ILS` | ILS koruma alanı (sinyal bozulmasına karşı büyük nesne yasağı) | |
| `VGSI` | VGSI koruma alanı | |

(+`OTHER`)

> **Stopway ve clearway `RunwayElement` değil, `RunwayProtectArea`'dır.** TODA = TORA +
> CWY, ASDA = TORA + SWY ilişkisi şemada hesaplanmaz; beyan mesafeleri ayrıca §4'te girilir.

---

## 8. RunwayBlastPad

Pist ucunda jet üfleme erozyonunu önleyen özel yüzey.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `length` | `ValDistanceType` | + `uom` |
| `status` | `CodeStatusOperationsType` | `NORMAL, DOWNGRADED, UNSERVICEABLE, WORK_IN_PROGRESS` |
| `usedRunwayDirection` | `RunwayDirectionPropertyType` | **Bağlı RunwayDirection** |
| `extent` | `ElevatedSurfacePropertyType` | **Geometri** |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | |
| `annotation` (0..∞) | `NotePropertyType` | |

---

## 9. ArrestingGear

Uçağı momentumunu emerek durduran sistem (kablo, ağ, EMAS).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `status` | `CodeStatusOperationsType` | `NORMAL, DOWNGRADED, UNSERVICEABLE, WORK_IN_PROGRESS` |
| `length` | `ValDistanceType` | Sistemin toplam uzunluğu |
| `width` | `ValDistanceType` | Fiziksel genişlik |
| `engageDevice` | `CodeArrestingGearEngageDeviceType` | Yakalama cihazı: `BAK_12`, `BAK_14_HOOK`, `BAK_15_HOOK`, `BAK_15_STANCHION_NET`, `BAK_11_STRUT`, `HOOK_CABLE`, `HOOK_H`, `NET`, `NET_A30`, `NET_A40`, `HP_NET`, `MA_1_NET`, `MA_1A_HOOK_CABLE`, `61QSII`, `62NI`, `63PI`, `J_BAR`, `JET_BARRIER`, **`EMAS`** (Engineered Materials Arresting System) |
| `absorbType` | `CodeArrestingGearEnergyAbsorbType` | Enerji emici tipi — 73 değer (`ROTARY_BAK_12A`, `ROTARY_BAK_13`, `LINEAR_BAK_6`, `DISK_BEFAB_*`, `CHAIN_E5*`, `MOBILROTARY_MAG_*`, `TEXTILE_MB_100`...; tam liste şemada `CodeArrestingGearEnergyAbsorbBaseType`) |
| `bidirectional` | `CodeYesNoType` | İki yönde de kullanılıyor mu |
| `location` | `ValDistanceType` | **Eşikten sisteme mesafe** (koordinat değil!) |
| `runwayDirection` (0..∞) | `RunwayDirectionPropertyType` | **Bağlı RunwayDirection(lar)** |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | |
| `extent_surfaceExtent` / `extent_curveExtent` / `extent_pointExtent` | `ElevatedSurface` / `ElevatedCurve` / `ElevatedPoint` | **choice** — üçünden yalnızca biri (EMAS → alan, kablo → çizgi, konum → nokta) |
| `annotation` (0..∞) | `NotePropertyType` | |

---

## 10. Pist yönüne bağlı ekipman

### 10.1 RunwayVisualRangeEquipment

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `readingPosition` | `CodeRVRReadingType` | `TDZ` (teker koyma), `MID` (orta), `TO` (kalkış/rollout) |
| `location` | `ElevatedPointPropertyType` | Sensör konumu |
| `associatedRunwayDirection` (0..∞) | `RunwayDirectionPropertyType` | Hizmet verdiği yön(ler) — bir sensör 05'in TDZ'si ve 23'ün rollout'u olabilir |
| `annotation` (0..∞) | `NotePropertyType` | |

### 10.2 VisualGlideSlopeIndicator (PAPI / VASIS)

`AbstractGroundLightSystem`'dan türer (→ `emergencyLighting`, `intensityLevel`, `colour`,
`element` (LightElement), `availability`, `annotation` miras alanları; bkz.
`AIXM_Surface_Common_Objects.md` §5).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeVASISType` | `PAPI, APAPI, HAPI, VASIS, AVASIS, TVASIS, ATVASIS, 3B_VASIS, 3B_AVASIS, 3B_ATVASIS, PVASI, TRCV, PNI, ILU, OLS, LCVASI` |
| `position` | `CodeSideType` | `LEFT, RIGHT, BOTH, CENTRE` — eksene göre konum |
| `numberBox` | `NoNumberType` | Ünite sayısı (PAPI → 4, APAPI → 2) |
| `portable` | `CodeYesNoType` | Taşınabilir mi |
| `slopeAngle` | `ValAngleType` | `-180..180` — yaklaşma açısı (ör. `3.0`) |
| `minimumEyeHeightOverThreshold` | `ValDistanceVerticalType` | MEHT + `uom` (AD 2.14) |
| `runwayDirection` | `RunwayDirectionPropertyType` | **Bağlı RunwayDirection** |
| `thresholdDistance` | `ValDistanceType` | Referans noktasından eşiğe mesafe |
| `displacementAngle` | `ValAngleType` | VGSI ekseninin pist eksenine göre açısal kayması |
| `finalApproachRunwayOccupancySignal` | `CodeYesNoType` | FAROS mevcut mu |

### 10.3 ApproachLightingSystem

`AbstractGroundLightSystem`'dan türer.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `classICAO` | `CodeApproachLightingICAOType` | `SIMPLE, CAT1, CAT23, CIRCLING, LEADIN, NONE` (Annex 14 sınıfı) |
| `type` | `CodeApproachLightingType` | `ALSAF, MALS, MALSR, SALS, SSALS, SSALR, LDIN, ODALS, AFOVRN, MILOVRN, CALVERT, RTIL, WBAR` (bölgesel/FAA sınıfı) |
| `length` | `ValDistanceType` | ALS toplam uzunluğu (AD 2.14 "APCH LGT LEN") |
| `sequencedFlashing` | `CodeYesNoType` | Sıralı flaşör var mı |
| `alignmentIndicator` | `CodeYesNoType` | Pist hizalama göstergesi (RAIL) var mı |
| `servedRunwayDirection` | `RunwayDirectionPropertyType` | **Bağlı RunwayDirection** |

### 10.4 RunwayDirectionLightSystem

Bir iniş/kalkış yönünün ışık sistemi (stopway ışıkları dahil). `AbstractGroundLightSystem`'dan
türer. Kenar, eşik, TDZ, eksen, son ışıkları **ayrı kayıtlar** olarak, `position` ile
ayrılarak kodlanır.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `position` | `CodeRunwaySectionType` | → §11.1 (ör. `EDGE` kenar, `THR` eşik, `TDZ`, `CL` eksen, `END` son) |
| `associatedRunwayDirection` | `RunwayDirectionPropertyType` | **Bağlı RunwayDirection** |
| `type` | `CodeRunwayLightType` | `LAHSO_LIGHT, POSITION_LIGHT, RUNWAY_INTERSECTION_LIGHT, TAKEOFF_HOLD_LIGHT, TWY_CL_LEAD_ON_LIGHT, TWY_CL_LEAD_OFF_LIGHT` (özel ışık tipleri; standart kenar/eşik ışıkları için genelde boş bırakılır) |
| `length` | `ValDistanceType` | Sistem uzunluğu (AD 2.14 "RWY EDGE LGT LEN") |
| `spacing` | `ValDistanceType` | Işık aralığı |
| `group` (0..∞) | `LightGroupPropertyType` | → **LightGroup** (O): `fromDistance`, `toDistance` (başlangıçtan mesafe), `colour`, `direction` (`UNIDIRECTIONAL, BIDIRECTIONAL, OMNIDIRECTIONAL`), `element` (LightElement), `annotation` — ör. pist sonuna son 600 m kırmızı/beyaz |

### 10.5 RunwayProtectAreaLightSystem

`AbstractGroundLightSystem`'dan türer.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `position` | `CodeProtectAreaSectionType` | `EDGE, END, CL` |
| `lightedArea` | `RunwayProtectAreaPropertyType` | → RunwayProtectArea (ör. stopway) |
| `length` | `ValDistanceType` | |

---

## 11. RunwayMarking

`AbstractMarking`'den türer (→ `markingICAOStandard`, `condition`, `element`
(MarkingElement: renk, stil, nokta/çizgi/alan geometri), `annotation`).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `markingLocation` | `CodeRunwaySectionType` | → §11.1 |
| `markedRunway` | `RunwayPropertyType` | **Bağlı Runway** (RunwayDirection değil!) |

### 11.1 CodeRunwaySectionType

`TDZ`, `AIM` (nişan noktası), `CL` (eksen), `EDGE`, `THR`, `DESIG` (pist numarası),
`AFT_THR` (eşik sonrası sabit mesafe işaretleri), `DTHR` (kaydırılmış eşik), `END`,
`TWY_INT`, `RPD_TWY_INT`, `1_THIRD` / `2_THIRD` / `3_THIRD` (düşük numaralı eşikten
itibaren üçte birler), `LAHSO`.

### 11.2 CodeRunwayMarkingType (`RunwayDirection.approachMarkingType`)

| Değer | Açıklama |
|---|---|
| `PRECISION` | Hassas yaklaşma pisti işaretleri |
| `NONPRECISION` | Hassas olmayan yaklaşma pisti işaretleri |
| `BASIC` | Temel (görsel) pist işaretleri |
| `NONE` | İşaret yok |
| `RUNWAY_NUMBERS` | Yalnızca pist numarası |
| `NON_STANDARD` | Standart dışı |
| `HELIPORT` | Heliport işaretleri |
| `BUOY` | Şamandıra (su alanları) |

---

## 12. Pistle ilgili dış referanslar (özet)

| Dış feature.attribute | Hedef |
|---|---|
| `Navaid.runwayDirection` (0..*) | RunwayDirection — ILS/LOC/GP'nin hizmet verdiği yön |
| `GBASService.servedApproach` | RunwayDirection |
| `LandingTakeoffAreaCollection.runwayDirection` | RunwayDirection — prosedürün uygulandığı pist yönleri |
| `ObstacleArea.reference_ownerRunway` / `_ownerRunwayDirection` | Runway / RunwayDirection |
| `RadarSystem.PARRunway` | Runway |
| `TaxiHoldingPosition.protectedRunway` | Runway |
| `*.pointChoice_runwayPoint`, `DesignatedPoint.runwayPoint`, `AltimeterCheckpoint.locationOnRunway` | RunwayCentrelinePoint |
