# AIXM 5.2 — Apron Ailesi: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (satır ~2011-2722 apron feature'ları; ~3018 apron
ışığı; ~3918, ~3986, ~4296 işaretler) + `AIXM_DataTypes_annotated.xsd`
(17 January 2025, AIXM 5.2)

> | Katman | Feature | Geometri |
> |---|---|---|
> | Mantıksal apron (`APRON 1`, `KARGO APRONU`...) | `Apron` | **yok** |
> | Yüzey parçaları (fonksiyonel tipli) | `ApronElement` | alan |
> | Park yeri / gate | `AircraftStand` | nokta + alan |
> | Buz çözme alanı | `DeicingArea` | alan |
> | Yolcu köprüsü, servis yolu | `PassengerLoadingBridge`, `Road` | alan |
>
> Apron alanı elemanları, manevra alanı elemanlarından farklı bir availability tipi
> kullanır: **`ApronAreaAvailability`** (manevra alanı: `ManoeuvringAreaAvailability`).
> Ekleme adımları ve XML örneği: `AIXM_Surfaces_How_To_Add.md` §4.

---

## 1. Apron

Kara meydanında yolcu/kargo/posta yükleme-boşaltma, yakıt ikmali, park veya bakım için
tanımlı alan.

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `name` | `TextNameType` | 1-60 karakter | Apron adı (birden fazla apron varsa) |
| `abandoned` | `CodeYesNoType` | `YES, NO` | Kullanım dışı ama mevcut |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | → `AIXM_Surface_Common_Objects.md` §1 | AD 2.8 "Apron surface and strength" |
| `associatedAirportHeliport` | `AirportHeliportPropertyType` | xlink | **Bağlı meydan** |
| `contaminant` (0..∞) | `ApronContaminationPropertyType` | → §4 ortak | |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `availability` (0..∞) | `ApronAreaAvailabilityPropertyType` | → §1.1 | |

> Apron'un `designator` alanı yoktur; adı `name` ile verilir. **Geometri alanı yoktur.**

### 1.1 ApronAreaAvailability (O) — Apron, ApronElement, AircraftStand, DeicingArea için ortak

`AbstractPropertiesWithScheduleType`'tan türer (Timesheet destekli).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `operationalStatus` | `CodeStatusAirportType` | `NORMAL, LIMITED, CLOSED, EXTENDED` |
| `warning` | `CodeAirportWarningType` | `WIP, EQUIP, BIRD, ANIMAL, RUBBER_REMOVAL, PARKED_ACFT, RESURFACING, PAVING, PAINTING, INSPECTION, GRASS_CUTTING, CALIBRATION` |
| `usage` (0..∞) | `ApronAreaUsagePropertyType` | → `ApronAreaUsage` |

**ApronAreaUsage** yalnızca `AbstractUsageCondition`'dan miras alanları taşır (`type`,
`priorPermission`, `contact`, `selection`, `annotation`) — **kendine özgü `operation`
alanı yoktur** (Airport/Manoeuvring usage'dan farkı).

---

## 2. ApronElement

Apronun parçaları; fonksiyonel tip ve servis bilgisi (jetway, yakıt, çekme, docking, GPU)
taşıyabilir.

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `type` | `CodeApronElementType` | → aşağıdaki tablo | |
| `jetwayAvailability` | `CodeYesNoType` | | Körük var mı |
| `towingAvailability` | `CodeYesNoType` | | Çekme servisi |
| `dockingAvailability` | `CodeYesNoType` | | Docking sistemi |
| `groundPowerAvailability` | `CodeYesNoType` | | GPU |
| `length` | `ValDistanceType` | ≥0 + `uom` | |
| `width` | `ValDistanceType` | ≥0 + `uom` | |
| `associatedApron` | `ApronPropertyType` | xlink | **Bağlı Apron** (DO-272 Rule 23, 26) |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | | |
| `extent` | `ElevatedSurfacePropertyType` | poligon | **Geometri** |
| `supplyService` (0..∞) | `AirportSuppliesServicePropertyType` | → `AirportSuppliesService` feature'ı | Yakıt/yağ/oksijen/nitrojen ikmali (`fuelSupply`, `oilSupply`, `oxygenSupply`, `nitrogenSupply`) |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `availability` (0..∞) | `ApronAreaAvailabilityPropertyType` | → §1.1 | |

### `type` → CodeApronElementType

| Değer | Açıklama |
|---|---|
| `NORMAL` | Varsayılan |
| `PARKING` | Park yeri alanı (AMDB Parking Stand Area) |
| `RAMP` | Hangar kapısı ile apron kenarı arası erişim yüzeyi |
| `CARGO` | Kargo yükleme alanı |
| `FUEL` | Yakıt ikmal alanı |
| `HARDSTAND` | Tek uçak için geçici park yüzeyi |
| `MAINT` | Bakım alanı |
| `MILITARY` | Askeri apron |
| `LOADING` | Yolcu biniş/iniş alanı |
| `TAXILANE` | Kule değil terminal kontrolündeki taksi şeridi |
| `TURNAROUND` | Dönüş alanı |
| `TEMPORARY` | Geçici |
| `STAIRS` | Merdiven |
| `AGRICULTURE` | Zirai faaliyet yükleme alanı |
| `PARACHUTE_AREA` | Paraşüt faaliyet alanı |
| `SNOW_COLLECTION` | Kar toplama alanı |

(+`OTHER`)

---

## 3. AircraftStand

Apronda uçak park etmek için belirlenmiş alan (park yeri / gate).

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `designator` | `TextDesignatorType` | 1-16 karakter | Park yeri adı (ör. `13`, `84A`) |
| `type` | `CodeAircraftStandType` | `NI` (nose-in), `ANG_NI` (açılı nose-in), `ANG_NO` (açılı nose-out), `PARL` (binaya paralel), `RMT` (uzak), `ISOL` (izole park yeri) | |
| `visualDockingSystem` | `CodeVisualDockingGuidanceType` | `AGNIS, PAPA, SAFE_GATE, SAFE_DOC, APIS, A_VDGS, AGNIS_STOP, AGNIS_PAPA` | Görsel yanaşma sistemi |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | | |
| `location` | `ElevatedPointPropertyType` | nokta | **Referans konum** (AD 2.24 park yeri koordinat tablosu) |
| `apronLocation` | `ApronElementPropertyType` | xlink | **Bağlı ApronElement** (Apron değil!) |
| `extent` | `ElevatedSurfacePropertyType` | poligon | Park yeri alanı |
| `contaminant` (0..∞) | `AircraftStandContaminationPropertyType` | → §4 ortak | |
| `annotation` (0..∞) | `NotePropertyType` | | |
| `availability` (0..∞) | `ApronAreaAvailabilityPropertyType` | → §1.1 | Kısıtlama (ör. max wingspan) buradan `usage.selection.aircraft` ile |

> **Zincir:** `AircraftStand.apronLocation → ApronElement.associatedApron → Apron.associatedAirportHeliport`.
> Park yerinin Apron'a veya meydana doğrudan bağı yoktur.

---

## 4. DeicingArea

Buz çözme işlemi gören uçağın park edildiği iç alan ve iki veya daha fazla mobil buz
çözme aracının manevra yaptığı dış alandan oluşan alan.

| Attribute | Değer Tipi | Açıklama |
|---|---|---|
| `associatedApron` | `ApronPropertyType` | Apron üzerindeyse |
| `taxiwayLocation` | `TaxiwayPropertyType` | Taksi yolu üzerindeyse |
| `standLocation` | `AircraftStandPropertyType` | Park yerindeyse |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | |
| `extent` | `ElevatedSurfacePropertyType` | **Geometri** |
| `annotation` (0..∞) | `NotePropertyType` | |
| `availability` (0..∞) | `ApronAreaAvailabilityPropertyType` | |
| `designator` | `TextDesignatorType` | Alan adı (şemada listenin **sonunda**) |

> Üç konum alanından hangisinin doldurulacağı alanın fiziksel yerine bağlıdır; şema birini
> zorunlu kılmaz. Birinin boş olması durumunda diğerinin "yedek" olarak doldurulması
> anlamlı değildir — farklı konumları ifade ederler.

---

## 5. PassengerLoadingBridge

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeLoadingBridgeType` | `ARM, MOVABLE_ARM, PORTABLE_RAMP, PORTABLE_STAIRS` |
| `extent` | `ElevatedSurfacePropertyType` | **Geometri** |
| `associatedStand` (0..∞) | `AircraftStandPropertyType` | Hizmet verdiği park yeri(leri) |
| `annotation` (0..∞) | `NotePropertyType` | |

---

## 6. Road

Meydanda yalnızca yetkili araç ve personelin kullanımına ayrılmış yol.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `designator` | `TextNameType` | 1-60 karakter |
| `status` | `CodeStatusOperationsType` | `NORMAL, DOWNGRADED, UNSERVICEABLE, WORK_IN_PROGRESS` |
| `type` | `CodeRoadType` | `SERVICE, PUBLIC` |
| `abandoned` | `CodeYesNoType` | |
| `associatedAirport` | `AirportHeliportPropertyType` | **Bağlı meydan** (alan adı `associatedAirport` — diğerlerinden farklı) |
| `surfaceProperties` | `SurfaceCharacteristicsPropertyType` | |
| `accessibleStand` (0..∞) | `AircraftStandPropertyType` | Erişim sağladığı park yerleri |
| `surfaceExtent` | `ElevatedSurfacePropertyType` | **Geometri** (alan adı `surfaceExtent` — diğerlerinde `extent`) |
| `annotation` (0..∞) | `NotePropertyType` | |

---

## 7. Apron ışık ve işaretleri

### 7.1 ApronLightSystem

`AbstractGroundLightSystem`'dan türer (miras: `emergencyLighting`, `intensityLevel`,
`colour`, `element`, `availability`, `annotation`).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `position` | `CodeApronSectionType` | `EDGE` (tek değer) |
| `lightedApron` | `ApronPropertyType` | **Bağlı Apron** |

### 7.2 İşaretler

Hepsi `AbstractMarking`'den türer (miras: `markingICAOStandard`, `condition`, `element`,
`annotation`).

| Feature | Kendi attribute'ları |
|---|---|
| `ApronMarking` | `markingLocation` (`CodeApronSectionType`: `EDGE`), `markedApron` (→ Apron) |
| `StandMarking` | `markedStand` (→ AircraftStand) |
| `DeicingAreaMarking` | `markedDeicingArea` (→ DeicingArea) |
