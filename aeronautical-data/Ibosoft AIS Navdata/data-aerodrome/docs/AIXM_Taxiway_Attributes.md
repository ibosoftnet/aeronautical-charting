# AIXM 5.2 — Taksi Yolu Ailesi: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (satır ~6980-7483 taksi feature'ları; ~3190-3783
ışık; ~4046-4500 işaret; ~1071 hotspot) + `AIXM_DataTypes_annotated.xsd`
(17 January 2025, AIXM 5.2)

> Taksi modeli, pist modeliyle aynı mantıktadır:
>
> | Katman | Feature | Geometri |
> |---|---|---|
> | Mantıksal taksi yolu (`A`, `B`, `K1`...) | `Taxiway` | **yok** |
> | Yüzey parçaları | `TaxiwayElement` | alan |
> | Taksi merkez hattı / lead-in / lead-out | `GuidanceLine` | çizgi |
> | Bekleme noktaları | `TaxiHoldingPosition` | nokta |
>
> `GuidanceLine`, taksi yolları, apronlar, park yerleri, pist eşik noktaları ve TLOF'lar
> arasında **ağ (graph)** oluşturur — ground movement / taxi routing için kullanılan
> katman budur.
> Ekleme adımları ve XML örneği: `AIXM_Surfaces_How_To_Add.md` §3.

---

## 1. Taxiway

Meydanın bir bölümünü diğerine bağlamak için kurulmuş tanımlı taksi yolu (stand taxilane,
apron taxiway, hızlı çıkış, hava taksi yolu dahil).

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `designator` | `TextDesignatorType` | 1-16 karakter | Taksi yolu adı (ör. `A`, `B2`) |
| `type` | `CodeTaxiwayType` | → aşağıdaki tablo | |
| `width` | `ValDistanceType` | ≥0 + `uom` | Fiziksel genişlik (AD 2.8) |
| `widthShoulder` | `ValDistanceType` | 〃 | Omuz genişliği |
| `length` | `ValDistanceType` | 〃 | Uzunluk |
| `abandoned` | `CodeYesNoType` | `YES, NO` | Kullanım dışı ama mevcut |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | → `AIXM_Surface_Common_Objects.md` §1 | Kaplama, PCN/PCR (AD 2.8 "TWY surface and strength") |
| `associatedAirportHeliport` | `AirportHeliportPropertyType` | xlink | **Bağlı meydan** |
| `contaminant` (0..∞) | `TaxiwayContaminationPropertyType` | → §4 ortak | Ek alan: `clearedWidth` |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `availability` (0..∞) | `ManoeuvringAreaAvailabilityPropertyType` | → §3 ortak | Açık/kapalı, kullanım kuralları (ör. "Code F yasak") |
| `diameter` | `ValDistanceType` | ≥0 + `uom` | Yalnız su dönüş havzası (`TURNING_BASIN`) çapı |
| `depth` | `ValDistanceType` | ≥0 + `uom` | Yalnız su taksi yolu derinliği |

### `type` → CodeTaxiwayType

| Değer | Açıklama |
|---|---|
| `AIR` | Hava taksi yolu (helikopter) |
| `GND` | Yer taksi yolu |
| `EXIT` | Çıkış/dönüş taksi yolu |
| `FASTEXIT` | Hızlı çıkış taksi yolu (RET) |
| `STUB` | Kısa bağlantı taksi yolu |
| `TURN_AROUND` | Dönüş cebi |
| `PARALLEL` | Paralel taksi yolu |
| `BYPASS` | Bypass / bekleme cebi |
| `CHANNEL` | Su meydanında deniz uçağı taksi kanalı |
| `TURNING_BASIN` | Su dönüş havzası |

(+`OTHER`)

---

## 2. TaxiwayElement

Taksi yolunun parçası. Çizilebilir taksi yolu yüzeyi bu elemanlardan oluşur.

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `type` | `CodeTaxiwayElementType` | `NORMAL`, `INTERSECTION` (pist/taksi kesişimi), `SHOULDER` (omuz), `HOLDING_BAY` (taksi yolu yanında bekleme/bypass alanı) | |
| `length` | `ValDistanceType` | ≥0 + `uom` | |
| `width` | `ValDistanceType` | ≥0 + `uom` | |
| `gradeSeparation` | `CodeGradeSeparationType` | `UNDERPASS, OVERPASS` | Köprü/tünel |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | | Parça bazında kaplama/PCN |
| `associatedTaxiway` (0..∞) | `TaxiwayPropertyType` | xlink | **Bağlı Taxiway(ler)** — kesişim elemanı birden fazla taksi yoluna ait olabilir (DO-272 Rule 9) |
| `extent` | `ElevatedSurfacePropertyType` | poligon | **Geometri** |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `availability` (0..∞) | `ManoeuvringAreaAvailabilityPropertyType` | | Parça bazında kapalılık (NOTAM: "TWY B between B1 and B2 CLSD") |

---

## 3. GuidanceLine

Uçağı hareket alanları üzerinde ve arasında yönlendiren çizgi. **Havalimanına doğrudan bağı
yoktur**; bağlandığı elemanlar üzerinden ilişkilenir.

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `designator` | `TextNameType` | 1-60 karakter | Çizgi tanımlayıcısı (**not:** `TextNameType`, `TextDesignatorType` değil) |
| `type` | `CodeGuidanceLineType` | → aşağıdaki tablo | |
| `connectedTouchDownLiftOff` (0..∞) | `TouchDownLiftOffPropertyType` | xlink | Bağlandığı TLOF |
| `connectedRunwayCentrelinePoint` (0..∞) | `RunwayCentrelinePointPropertyType` | xlink | Bağlandığı pist eksen noktası (DO-272 Rule 21: RunwayExitLine ↔ threshold) |
| `connectedApron` (0..∞) | `ApronPropertyType` | xlink | Bağlandığı apron |
| `connectedStand` (0..∞) | `AircraftStandPropertyType` | xlink | Bağlandığı park yeri (DO-272 Rule 22: StandGuidanceLine) |
| `extent` | `ElevatedCurvePropertyType` | çizgi | **Geometri** |
| `connectedTaxiway` (0..∞) | `TaxiwayPropertyType` | xlink | Bağlandığı taksi yolu |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `availability` (0..∞) | `GuidanceLineDirectionPropertyType` | → §3.1 | **Yön bazlı** kullanılabilirlik (tek yönlü taksi vb.) |

### `type` → CodeGuidanceLineType

| Değer | Açıklama |
|---|---|
| `RWY` | Pist yüzeyinde, pist ile diğer yüzeyler arasında taksi hattı |
| `TWY` | Taksi yolu yüzeyinde taksi hattı |
| `APRON` | Apron üzerinde taksi hattı |
| `GATE_TLANE` | Apronda park yerine giden hat |
| `LI_TLANE` | Lead-in (park yerine giriş) |
| `LO_TLANE` | Lead-out (park yerinden çıkış) |
| `AIR_TLANE` | Helikopterler için sanal hava taksi hattı |

(+`OTHER`)

### 3.1 `availability` → GuidanceLineDirection (O)

Diğer yüzeylerden farklı olarak GuidanceLine'ın availability'si doğrudan
`ManoeuvringAreaAvailability` değil, arada **yön** bilgisi taşıyan bir sarmalayıcıdır.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `direction` | `CodeDirectionType` | `FORWARD, BACKWARD, BOTH` — `extent` eğrisinin başlangıç→bitiş yönüne göre |
| `cardinalDirection` | `CodeCardinalDirectionType` | 16 pusula yönü (`N, NNE, NE...`) |
| `theManoeuvringAreaAvailability` | `ManoeuvringAreaAvailabilityPropertyType` | → `AIXM_Surface_Common_Objects.md` §3 |
| `annotation` (0..∞) | `NotePropertyType` | |

> **Önemli:** `direction` eğrinin **çizim yönüne** bağlıdır; `extent`'in koordinat sırası
> değişirse yön anlamı tersine döner.

---

## 4. TaxiHoldingPosition

Taksi yapan uçak ve araçların kule izniyle devam edene kadar durup bekleyeceği tanımlı yer.

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `landingCategory` | `CodeHoldingCategoryType` | `NON_PRECISION, CAT_I, CAT_II_III` | İlgili olduğu iniş operasyon kategorisi (CAT I / CAT II-III bekleme noktaları) |
| `status` | `CodeStatusOperationsType` | `NORMAL, DOWNGRADED, UNSERVICEABLE, WORK_IN_PROGRESS` | |
| `associatedGuidanceLine` | `GuidanceLinePropertyType` | xlink | Üzerinde bulunduğu guidance line (DO-272 Rule 12) |
| `protectedRunway` (0..∞) | `RunwayPropertyType` | xlink | Koruduğu pist(ler) (DO-272 Rule 6, 20) |
| `location` | `ElevatedPointPropertyType` | nokta | **Geometri** |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `type` | `CodeTaxiHoldingPositionType` | `RUNWAY_HOLDING_POSITION` (pist giriş bekleme), `TAXI_HOLD_POSITION` (ara bekleme / hold spot), `ILS_HOLDING_POSITION` (ILS kritik alan beklemesi) | |

> Bekleme noktasının kendine ait bir `designator` alanı **yoktur**; adı (ör. "A1 CAT II")
> gerekiyorsa `annotation` ile verilir veya ilişkili `AirportSign`/`TaxiHoldingPositionMarking`
> üzerinden okunur.

---

## 5. Taksi ışık sistemleri

Üçü de `AbstractGroundLightSystem`'dan türer → miras alanlar: `emergencyLighting`,
`intensityLevel`, `colour`, `element` (LightElement), `availability`
(GroundLightingAvailability), `annotation` (bkz. `AIXM_Surface_Common_Objects.md` §5).

### 5.1 TaxiwayLightSystem

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `position` | `CodeTaxiwaySectionType` | `CL` (eksen), `EDGE` (kenar), `END`, `RWY_INT`, `TWY_INT`, `SHOULDER` |
| `lightedTaxiway` | `TaxiwayPropertyType` | **Bağlı Taxiway** |

### 5.2 GuidanceLineLightSystem

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `lightedGuidanceLine` | `GuidanceLinePropertyType` | **Bağlı GuidanceLine** (eksen ışıkları) |

### 5.3 TaxiHoldingPositionLightSystem

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeLightHoldingPositionType` | `STOP_BAR` (yüzeyde stop bar), `SIGN` (ışıklı tabela), `RUNWAY_ENTRANCE_LIGHT` (REL), `RUNWAY_GUARD_LIGHT` (RGL — "wig-wag") |
| `taxiHolding` | `TaxiHoldingPositionPropertyType` | **Bağlı TaxiHoldingPosition** |

---

## 6. Taksi işaretleri

Üçü de `AbstractMarking`'den türer → miras alanlar: `markingICAOStandard`, `condition`
(`GOOD, FAIR, POOR, EXCELLENT`), `element` (MarkingElement), `annotation`.

### 6.1 TaxiwayMarking

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `markingLocation` | `CodeTaxiwaySectionType` | `CL, EDGE, END, RWY_INT, TWY_INT, SHOULDER` |
| `markedTaxiway` | `TaxiwayPropertyType` | Bağlı Taxiway (DO-272 Rule 10-11) |
| `markedElement` | `TaxiwayElementPropertyType` | Bağlı TaxiwayElement (daha ince taneli) |
| `type` | `CodeTaxiwayMarkingType` | `DIRECTION` (kavşakta yön), `LOCATION` (bulunulan taksi yolu), `VOR_CHECKPOINT`, `MANDATORY_INSTRUCTION` (izinsiz geçilmez) |

### 6.2 GuidanceLineMarking

| Attribute | Değer Tipi |
|---|---|
| `markedGuidanceLine` | `GuidanceLinePropertyType` |

### 6.3 TaxiHoldingPositionMarking

| Attribute | Değer Tipi |
|---|---|
| `markedTaxiHold` | `TaxiHoldingPositionPropertyType` |

---

## 7. AirportHotSpot

Taksi ağıyla doğrudan bağlantılı değildir ama ground chart'larda taksi yollarıyla birlikte
gösterilir. Tam attribute listesi: `AIXM_Aerodrome_Components.md` §3.1
(`designator`, `instruction`, `area`, `affectedAirport`, `annotation`).

---

## 8. Kullanılabilirlik örnekleri (şemaya göre kurgu)

| Durum | Kodlama |
|---|---|
| TWY B tamamen kapalı | `Taxiway(B).availability{operationalStatus=CLOSED}` |
| TWY B'nin bir kısmı kapalı | İlgili `TaxiwayElement.availability{operationalStatus=CLOSED}` |
| TWY K'de Code F uçak yasak | `Taxiway(K).availability{operationalStatus=LIMITED, usage{type=FORBID, operation=TAXIING, selection{aircraft{wingspan…}}}}` |
| TWY A yalnızca batı yönlü | `GuidanceLine.availability{direction=FORWARD, theManoeuvringAreaAvailability{…NORMAL}}` + `{direction=BACKWARD, …CLOSED}` |
| Pist geçişi yasak | `usage{type=FORBID, operation=CROSSING}` |

(`operation` değerleri — `CodeOperationManoeuvringAreaType`: `LANDING, TAKEOFF, TOUCHGO,
TRAIN_APPROACH, TAXIING, CROSSING, AIRSHOW, ALL`.)
