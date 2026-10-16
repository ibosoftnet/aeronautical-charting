# AIXM 5.2 — AirportHeliport Feature: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (`AirportHeliportPropertyGroup`, satır ~541-770;
alt objeler satır ~773-1336) + `AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> **Tanım (şema):** Karada veya suda, uçak/helikopterlerin iniş, kalkış ve yer hareketleri
> için tamamen veya kısmen kullanılması amaçlanan tanımlı alan (binalar, tesisler ve
> ekipman dahil).
>
> `AirportHeliport` bir **Feature**'dır (`AirportHeliportType` → `AbstractAIXMFeatureType`).
> Tek geometrileri `ARP` (nokta) ve `aviationBoundary` (alan)'dır. Pist/taksi yolu/apron
> **listesi tutmaz** — bunlar kendi `associatedAirportHeliport` alanlarıyla bu feature'a
> işaret eder (bkz. `AIXM_Aerodrome_Model_Overview.md` §2).
>
> Genel `Code*` / `nilReason` notu için bkz. `README.md`.

---

## 1. AirportHeliport → AirportHeliportTimeSlice (kendi attribute'ları)

Şemadaki sırayla (XML'de de bu sıra zorunludur — `sequence`):

### 1.1 Kimlik

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `designator` | `CodeAirportHeliportDesignatorType` | 3-6 karakter, `([A-Z]\|\d)*` | Meydanın tanımlayıcısı. ICAO kodu olan meydanlarda genellikle ICAO kodunun aynısı; ICAO kodu olmayanlarda ulusal kod (ör. FAA LID `3N6`). |
| `name` | `TextNameType` | Serbest metin, 1-60 karakter | Yetkili otoritece belirlenmiş birincil resmi ad |
| `locationIndicatorICAO` | `CodeICAOType` | **Tam 4 harf**, `[A-Z]*` | ICAO Doc 7910 konum göstergesi (ör. `LTFM`) |
| `designatorIATA` | `CodeIATAType` | **Tam 3 harf**, `[A-Z]*` | IATA kodu (ör. `IST`) |
| `type` | `CodeAirportHeliportType` | → bkz. **§5.1** | Meydan tipi (AD, AH, HP, LS...) |

> **Fallback uyarısı:** `designator` ile `locationIndicatorICAO` farklı alanlardır ve
> farklı anlam taşır. Biri boşsa diğeriyle doldurulmamalıdır (kullanıcı genel kuralı).

### 1.2 Statü / sertifikasyon

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `certifiedICAO` | `CodeYesNoType` | `YES, NO` | ICAO emniyet gerekliliklerine uygunluk |
| `privateUse` | `CodeYesNoType` | `YES, NO` | Halka kapalı, yalnızca sahiplerinin kullanımında |
| `controlType` | `CodeMilitaryOperationsType` | `CIVIL, MIL, JOINT` | Meydanı kontrol eden birincil organizasyon tipi |
| `abandoned` | `CodeYesNoType` | `YES, NO` | Operasyonel olarak kullanılmıyor ama altyapısı havadan görünür durumda |
| `certificationDate` | `DateType` | Tarih | Sertifikanın verildiği tarih |
| `certificationExpirationDate` | `DateType` | Tarih | Sertifikanın geçersiz olacağı tarih |

### 1.3 Konum, yükseklik ve manyetik veriler

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `fieldElevation` | `ValDistanceVerticalType` | decimal + `uom` (`FT, M, FL, SM`) | İniş alanının en yüksek noktasının MSL'den yüksekliği (AD elevation) |
| `verticalDatum` | `TextNameType` | Serbest metin, max 60 | Yüksekliklerin referans yüzeyi (ör. `EGM96`, `MSL`) |
| `magneticVariation` | `ValMagneticVariationType` | decimal, `-180..180` | Manyetik sapma (derece; işaret konvansiyonu şemada tanımlı değil — pratikte doğu `+`) |
| `dateMagneticVariation` | `DateYearType` | 4 haneli yıl `[1-9][0-9]{3}` | Sapmanın ölçüldüğü yıl |
| `magneticVariationChange` | `ValMagneticVariationChangeType` | decimal, `-180..180` | Yıllık değişim oranı |
| `ARP` | `ElevatedPointPropertyType` | → `ElevatedPoint` (bkz. `AIXM_Surface_Common_Objects.md`) | **Aerodrome Reference Point** — meydanın temsil noktası |
| `aviationBoundary` | `ElevatedSurfacePropertyType` | → `ElevatedSurface` | Meydan sınırları (poligon) |
| `timeZone` | `CodeTimeReferenceType` | `UTC`, `UTC-12`...`UTC+14`, yarım/çeyrek saat dilimleri (`UTC+5:30`, `UTC+5:45`...) | Meydanın bulunduğu zaman dilimi |

### 1.4 Meteorolojik referans / irtifa

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `referenceTemperature` | `ValTemperatureType` | decimal + `uom` (`C, F, K`) | En sıcak ayın günlük maksimumlarının aylık ortalaması (AD reference temperature) |
| `lowestTemperature` | `ValTemperatureType` | decimal + `uom` | En soğuk ayın günlük minimumlarının aylık ortalaması |
| `transitionAltitude` | `ValDistanceVerticalType` | decimal + `uom` | Geçiş irtifası |
| `transitionLevel` | `ValFLType` | `unsignedInt`, max 999, `uom` (`FL, SM`) | Geçiş seviyesi |
| `altimeterCheckLocation` | `CodeYesNoType` | `YES, NO` | Altimetre kontrol yeri mevcut mu |
| `altimeterSource` (0..∞) | `AltimeterSourcePropertyType` | → bkz. **§2.6** | Altimetre ayarı kaynağı |

### 1.5 Tesis bilgileri

| Attribute | Değer Tipi | Enum / Format | Açıklama |
|---|---|---|---|
| `secondaryPowerSupply` | `CodeYesNoType` | `YES, NO` | Yedek (acil) güç kaynağı |
| `windDirectionIndicator` | `CodeYesNoType` | `YES, NO` | Rüzgâr yön göstergesi (windsock) |
| `landingDirectionIndicator` | `CodeYesNoType` | `YES, NO` | İniş yönü göstergesi (T/tetrahedron) |
| `segmentedCircleMarker` | `CodeSegmentedCircleType` | `NO, YES, YES_LIGHTED` | Segmentli daire işaret sistemi |

### 1.6 İlişkiler ve gömülü objeler

| Attribute | Değer Tipi | Hedef | Açıklama |
|---|---|---|---|
| `contaminant` (0..∞) | `AirportHeliportContaminationPropertyType` | Object (gömülü) | Meydanın genel kirliliği → bkz. `AIXM_Surface_Common_Objects.md` §4 |
| `servedCity` (0..∞) | `CityPropertyType` | Object (gömülü) | Hizmet verdiği şehir(ler) → **§2.5** |
| `responsibleOrganisation` (0..∞) | `AirportHeliportResponsibilityOrganisationPropertyType` | Object (gömülü) | Meydandan sorumlu kuruluş(lar) ve rolü → **§2.4** |
| `contact` (0..∞) | `ContactInformationPropertyType` | Object (gömülü) | İletişim bilgisi (adres, telefon, e-posta...) — ortak AIXM tipi, kapsam dışı |
| `availability` (0..∞) | `AirportHeliportAvailabilityPropertyType` | Object (gömülü) | Operasyonel durum + kullanım kuralları + zaman çizelgesi → **§2.1** |
| `annotation` (0..∞) | `NotePropertyType` | Object (gömülü) | Serbest notlar → bkz. `../AIXM_Annotation_Attributes.md` |

---

## 2. Gömülü objeler

### 2.1 `availability` → AirportHeliportAvailability

`AbstractPropertiesWithScheduleType`'tan türer; yani `timeInterval` (Timesheet),
`specialDateAuthority` ve `annotation` alanlarını da taşır (bkz.
`AIXM_Surface_Common_Objects.md` §3). **Timesheet verilmezse durum sürekli geçerli kabul
edilir** (AIXM kodlama konvansiyonu; şema metninde yazmaz).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `operationalStatus` | `CodeStatusAirportType` | `NORMAL` (nominal), `LIMITED` (nominal altında, ek kısıtlamalı), `CLOSED` (operasyonel değil), `EXTENDED` (genişletilmiş parametreler, ör. uzatılmış çalışma saatleri) |
| `warning` | `CodeAirportWarningType` | `WIP, EQUIP, BIRD, ANIMAL, RUBBER_REMOVAL, PARKED_ACFT, RESURFACING, PAVING, PAINTING, INSPECTION, GRASS_CUTTING, CALIBRATION` |
| `usage` (0..∞) | `AirportHeliportUsagePropertyType` | → **§2.2** |

> **AIP AD 2.3 "operational hours"** bu yapıyla ifade edilir: `operationalStatus=NORMAL`
> + çalışma saatlerini veren `timeInterval`; saat dışı için ayrı bir availability
> `CLOSED` ile verilebilir.

### 2.2 `usage` → AirportHeliportUsage

`AbstractUsageConditionType`'tan türer: `type`, `priorPermission`, `contact`, `selection`,
`annotation` alanlarını da taşır (bkz. **§2.3**).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| *(miras)* `type` | `CodeUsageLimitationType` | `PERMIT` (izin), `CONDITIONAL` (ek talimatlı izin), `FORBID` (yasak), `RESERV` (özel/rezerve kullanım) |
| *(miras)* `priorPermission` | `ValDurationType` | Süre + `uom` (`HR, MIN, SEC`) — yalnızca `CONDITIONAL` için: kullanımdan ne kadar önce izin alınmalı (PPR) |
| *(miras)* `contact` (0..∞) | `ContactInformationPropertyType` | İzin için iletişim |
| *(miras)* `selection` | `ConditionCombinationPropertyType` | Kuralın **hangi uçuşlara/koşullara** uygulanacağı → **§2.3** |
| `operation` | `CodeOperationAirportHeliportType` | `LANDING, TAKEOFF, TOUCHGO, TRAIN_APPROACH` (alçak geçiş eğitimi), `ALTN_LANDING` (yedek meydan inişi), `AIRSHOW, ALL` |

### 2.3 `selection` → ConditionCombination

Kullanım kuralının hangi uçuş/uçak/hava koşulu kombinasyonuna uygulandığını tanımlayan
filtre ağacı. `AbstractPropertiesWithScheduleType`'tan türediği için kendi zaman
çizelgesi (`timeInterval`) de olabilir.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `logicalOperator` | `CodeLogicalOperatorType` | `AND, OR, NOT` (tek operand), `NONE` (tek koşul) |
| `weather` (0..∞) | `MeteorologyPropertyType` | Hava koşulu (IMC/VMC, görüş, tavan...) — ortak tip |
| `aircraft` (0..∞) | `AircraftCharacteristicPropertyType` | Uçak özelliği (tip, motor, ağırlık, wingspan...) — `../AIXM_RouteSegment_Attributes.md` §6 ile aynı tip |
| `flight` (0..∞) | `FlightCharacteristicPropertyType` | Uçuş özelliği (kural, askeri/sivil, amaç, GAT/OAT...) — ortak tip |
| `subCondition` (0..∞) | `ConditionCombinationPropertyType` | İç içe alt kombinasyon (özyinelemeli) |

Örnek mantık: *"Tüm operasyonlar için 24 saat önceden izin (PPR)"* →
`usage{type=CONDITIONAL, priorPermission=24 HR, operation=ALL}` — `selection` verilmezse
kuralın tüm uçuşlara uygulandığı kabul edilir (yorum; şema bunu açıkça yazmaz). Belirli bir uçuş grubuyla sınırlamak için `selection`
içinde `flight`/`aircraft`/`weather` kullanılır; bu ortak tiplerin (`FlightCharacteristic`,
`AircraftCharacteristic`, `Meteorology`) attribute'ları bu dokümanın kapsamı dışındadır.

### 2.4 `responsibleOrganisation` → AirportHeliportResponsibilityOrganisation

`AbstractPropertiesWithScheduleType`'tan türer (sorumluluk zamana bağlı olabilir).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `role` | `CodeAuthorityRoleType` | `OWN` (sahibi), `OPERATE` (işleticisi), `SUPERVISE` (düzenleyici otorite) |
| `theOrganisationAuthority` | `OrganisationAuthorityPropertyType` | → `OrganisationAuthority` feature'ına `xlink:href` (ör. DHMİ, İGA) |

### 2.5 `servedCity` → City

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `name` | `TextNameType` | Serbest metin, max 60 — hizmet verilen şehir/kasaba adı |
| `annotation` (0..∞) | `NotePropertyType` | |

### 2.6 `altimeterSource` → AltimeterSource

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `rank` | `CodeFacilityRankingType` | `PRIMARY, ALTERNATE, EMERG, GUARD` |
| `relativeLocation` | `CodeRelativeLocationType` | `LOCAL` (meydanda), `REMOTE` (uzak) |
| `distance` | `ValDistanceType` | decimal ≥ 0 + `uom` (`NM, KM, M, FT, MI, CM`) — uzak kaynak ise mesafe |
| `altimeterData` | `WeatherSourcePropertyType` | → `WeatherSource` feature'ı (`sensorType=ALTIMETER`) |
| `annotation` (0..∞) | `NotePropertyType` | |

---

## 3. İlgili bağımsız feature: WeatherSource

Havalimanına doğrudan bağı **yoktur**; `AltimeterSource.altimeterData` üzerinden ulaşılır.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `designator` | `TextDesignatorType` | 1-16 karakter |
| `sensorType` | `CodeWeatherSourceType` | `ALTIMETER, WIND, TEMPERATURE, CAMERA` |
| `position` | `ElevatedPointPropertyType` | Konum |
| `availability` (0..∞) | `WeatherSourceAvailabilityPropertyType` | Operasyonel durum (`CodeStatusServiceType`: `NORMAL, LIMITED, ONTEST, UNSERVICEABLE, UPGRADED`) |
| `annotation` (0..∞) | `NotePropertyType` | |

---

## 4. İlgili bağımsız feature: AirportHeliportCollocation

İki meydanın yer tesislerinin bir kısmını veya tamamını paylaşması (ör. aynı pisti kullanan
sivil havalimanı + askeri üs). **Ayrı bir Feature'dır**; iki `AirportHeliport`'u birbirine
bağlar.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeAirportHeliportCollocationType` | `FULL` (tam; aslında tek meydan), `RWY` (tüm RWY ve TWY'ler paylaşılıyor, apronlar değil), `PARTIAL` (şema dokümantasyonu `RWY` ile **birebir aynı** metni içeriyor — şema kaynaklı belirsizlik), `UNILATERAL` (1. meydanın RWY/TWY/apronları 2. meydan trafiğine açık, tersi değil), `SEPARATED` (fiziksel olarak taksi mümkün olsa da manevra alanları ayrı kabul ediliyor) |
| `hostAirport` | `AirportHeliportPropertyType` | Ana meydan |
| `dependentAirport` | `AirportHeliportPropertyType` | Ana meydanın tesislerini kullanan bağımlı meydan |
| `annotation` (0..∞) | `NotePropertyType` | |

---

## 5. Enum detayları

### 5.1 `type` → CodeAirportHeliportType

| Değer | Açıklama |
|---|---|
| `AD` | Yalnızca havalimanı (Airport only) |
| `AH` | Heliport iniş alanı olan havalimanı |
| `HP` | Yalnızca heliport |
| `LS` | İniş sahası (landing site) |
| `BP` | Balon meydanı |
| `SPB` | Deniz uçağı üssü (Seaplane Base) |
| `UL` | Ultralight uçuş parkı |
| `GP` | Planör meydanı |
| `SPACE` | Uzay limanı |

(+`OTHER`)

### 5.2 Birim (uom) listeleri

| Tip | `uom` değerleri |
|---|---|
| `ValDistanceType` / `ValDistanceSignedType` | `NM, KM, M, FT, MI, CM` |
| `ValDistanceVerticalType` | `FT, M, FL, SM` — değer ayrıca `UNL, GND, FLOOR, CEILING` olabilir |
| `ValTemperatureType` | `C, F, K` |
| `ValFLType` | `FL, SM` |
| `ValDurationType` | `HR, MIN, SEC` |

---

## Genişletme noktası

`extension` alanı → soyut `AbstractAirportHeliportExtension` (ulusal ek alanlar için boş
genişletme noktası).
