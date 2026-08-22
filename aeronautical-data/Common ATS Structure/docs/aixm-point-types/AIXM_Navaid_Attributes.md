# AIXM 5.2 — Navaid Feature: Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (`NavaidPropertyGroup`, satır ~9865-9968) +
`AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni. Ayrıca her `Code*`/`Val*`/`Text*Type`, `complexType`
> olarak `gml:NilReasonEnumeration` tipinde bir `nilReason` attribute'u da taşır.
>
> `Navaid`, AIXM'de bir **Feature**'dır (`NavaidType` → `AbstractAIXMFeatureType`), yani
> kendi `gml:id`'si, `timeSlice`/`validTime` geçmişi vardır. `RouteSegment.start`/`end`
> içindeki nokta-seçim choice'ının bir alternatifi olarak, **id referansıyla
> (xlink:href)** bağlanır — bkz. `AIXM_RoutePoint_DataTypes.md` §2.

> *"A service providing guidance information or position data for the efficient and safe
> operation of aircraft supported by one or more radio navigation aids."*

---

## 1. Navaid → NavaidTimeSlice (kendi attribute'ları)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeNavaidServiceType` | `VOR, DME, NDB, TACAN, MKR, ILS, ILS_DME, MLS, MLS_DME, VORTAC, VOR_DME, NDB_DME, TLS, LOC, LOC_DME, NDB_MKR, DF, SDF` (+OTHER) |
| `designator` | `CodeNavaidDesignatorType` | Enum değil — serbest alfanumerik, 1-4 karakter |
| `name` | `TextNameType` | Enum değil — serbest metin, max 60 karakter — bileşik navaid'in uzun adı |
| `flightChecked` | `CodeYesNoType` | `YES/NO` — uçuş kontrolü yapıldı mı |
| `purpose` | `CodeNavaidPurposeType` | `TERMINAL` (terminal alan kullanımı), `ENROUTE` (enroute kullanım), `ALL` (her ikisi) (+OTHER) |
| `signalPerformance` | `CodeSignalPerformanceILSType` | → bkz. **2** |
| `courseQuality` | `CodeCourseQualityILSType` | → bkz. **3** |
| `integrityLevel` | `CodeIntegrityLevelILSType` | → bkz. **4** |
| `touchDownLiftOff` (0..∞) | `TouchDownLiftOffPropertyType` | Navaid belirli bir TLOF'ta kuruluysa association — kapsam dışı (heliport'a özgü feature) |
| `navaidEquipment` (0..∞) | `NavaidComponentPropertyType` | Navaid sisteminin fiziksel bileşeni (örn. bir ILS'in DME'si) → bkz. **5** |
| `location` (0..1) | `ElevatedPointPropertyType` | Navaid bir significant point olarak kullanıldığında konumu → bkz. **6** |
| `runwayDirection` (0..∞) | `RunwayDirectionPropertyType` | Navaid (tipik olarak ILS/MLS) belirli bir pist yönünde kuruluysa association — kapsam dışı (pist yönüne özgü feature) |
| `servedAirport` (0..∞) | `AirportHeliportPropertyType` | Navaid'in homing için kullanıldığı havaalanı/heliport — kapsam dışı (büyük, ayrı feature) |
| `availability` (0..∞) | `NavaidOperationalStatusPropertyType` | → bkz. **7** |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](../AIXM_Annotation_Attributes.md) |
| `codeICAOCountry` | `CodeICAOCountryType` | Enum değil — serbest 1-2 karakter alfanumerik (`AlphanumericType`, maxLength 2), ICAO Doc 7910 ülke/alt-bölge harf kodu |

---

## 2. `signalPerformance` → CodeSignalPerformanceILSType

ICAO Annex 10 Cilt I Bölüm 3'e göre ILS/MLS sinyal hassasiyet kategorisi.

| Değer | Açıklama |
|---|---|
| `I` | Facility Performance category I |
| `II` | Facility Performance category II |
| `III` | Facility Performance category III |
| `IIIA` | ILS Cat III, performans A (DH < 100 ft, RVR ≥ 175 m) |
| `IIIB` | ILS Cat III, performans B (DH < 50 ft, 50 m ≤ RVR < 175 m) |
| `IIIC` | ILS Cat III, performans C (DH = 0, RVR = 0 m) |

(+`OTHER`)

---

## 3. `courseQuality` → CodeCourseQualityILSType

ICAO Annex 10 Cilt I Bölüm 3'e göre, ILS course yapısının hangi mesafeye kadar
kullanılabilir sinyal kalitesinde olduğunu belirtir.

| Değer | Açıklama |
|---|---|
| `A` | Eşikten itibaren yaklaşım yönünde 7.5 km (4 NM) mesafeye kadar kullanılabilir |
| `B` | Eşikten itibaren yaklaşım yönünde 1050 m (3500 ft) mesafeye kadar kullanılabilir |
| `C` | Nominal ILS glide path'in eşiği içeren yatay düzlemin 30 m (100 ft) üzerinden geçtiği noktaya kadar kullanılabilir |
| `D` | Pist merkez hattının 4 m (12 ft) üzerinde ve eşikten localizer yönünde 900 m (3000 ft) mesafeye kadar kullanılabilir |
| `E` | Pist merkez hattının 4 m (12 ft) üzerinde, pistin bitiş ucundan eşik yönünde 600 m (2000 ft) mesafeye kadar kullanılabilir |
| `T` | Pist merkez hattı ile eşiğin kesişiminin üzerinde, belirli bir yükseklikte, glide path'in bu noktadan geçtiği yere kadar kullanılabilir |

(+`OTHER`)

---

## 4. `integrityLevel` → CodeIntegrityLevelILSType

ICAO Annex 10 Cilt I Ek C'ye göre, ILS tesisinin sağladığı bilginin doğruluğuna duyulan
güven düzeyi.

| Değer | Açıklama |
|---|---|
| `1` | Integrity Level 1 |
| `2` | Integrity Level 2 |
| `3` | Integrity Level 3 |
| `4` | Integrity Level 4 |

(+`OTHER`)

---

## 5. `navaidEquipment` → NavaidComponent

> *"Indicates navigation use of a NavaidEquipment as a component of the navigation
> service provided by a Navaid. For example the DME NavaidEquipment is a
> NavaidComponent of an ILS system."*

`NavaidComponentType` → `AbstractAIXMObjectType` (Object, Feature değil — `Navaid`'in
altına gömülü, bileşen ilişkisini tarif eden bir rol nesnesi).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `collocationGroup` | `NoSequenceType` | Sayısal sıra no — aynı numaraya sahip diğer NavaidEquipment'larla ortak konumlandığını belirtir |
| `markerPosition` | `CodePositionInILSType` | → bkz. **5.1** |
| `providesNavigableLocation` | `CodeYesNoType` | `YES/NO` — Navaid, significant point olarak kullanıldığında, bu bileşenin navigasyona uygun konumu belirlediğini gösterir |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](../AIXM_Annotation_Attributes.md) |
| `theNavaidEquipment` | `NavaidEquipmentPropertyType` | Fiziksel navaid ekipmanına (VOR, DME, Localizer, TACAN vb.) association → bkz. [AIXM_NavaidEquipment_Attributes.md](AIXM_NavaidEquipment_Attributes.md) (11 somut alt-tür, tam öznitelik listesi) |

### 5.1 `markerPosition` → CodePositionInILSType

| Değer | Açıklama |
|---|---|
| `OUTER` | Outer marker |
| `MIDDLE` | Middle marker |
| `INNER` | Inner marker |
| `BACKCOURSE` | Backcourse marker |

(+`OTHER`)

---

## 6. `location` → ElevatedPoint

`Point`'in (bkz. `AIXM_Point_Attributes.md`) irtifa bilgisiyle genişletilmiş hâli —
Navaid bir significant point (rota noktası) olarak kullanıldığında konumunu tarif eder.

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `elevation` | `ValDistanceVerticalType` | Noktanın MSL'den (Mean Sea Level) ölçülen dikey mesafesi |
| `geoidUndulation` | `ValDistanceSignedType` | İşaretli mesafe — geoidin, noktanın konumundaki matematiksel referans elipsoidin üstünde (pozitif) veya altında (negatif) olan mesafesi |
| `verticalDatum` | `TextNameType` | Enum değil — serbest metin; dikey konum ölçümlerinin dayandığı referans noktaları/matematiksel model (datum) adı |
| `horizontalAccuracy` | `ValDistanceType` | Sayı (≥0) + `uom`: `NM, KM, M, FT, MI, CM` — kaydedilen yatay koordinatların gerçek konumdan sapması |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](../AIXM_Annotation_Attributes.md) |

---

## 7. `availability` → NavaidOperationalStatus

Navaid'in operasyonel durumu (zaman/programa bağlı olabilir —
`AbstractPropertiesWithScheduleType`'dan miras alır, schedule alanları bu dokümanın
kapsamı dışında).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `operationalStatus` | `CodeStatusNavaidType` | → bkz. **7.1** |
| `signalType` | `CodeRadioSignalType` | → bkz. **7.2** |

### 7.1 `operationalStatus` → CodeStatusNavaidType

| Değer | Açıklama |
|---|---|
| `OPERATIONAL` | Normal çalışıyor |
| `UNSERVICEABLE` | Kullanılamıyor |
| `ONTEST` | Test aşamasında, kullanma |
| `INTERRUPT` | Sinyal kesintisi beklenmeli |
| `PARTIAL` | Sınırlı kapasitede çalışıyor (örn. bir VOR/DME'nin sadece DME kısmı çalışıyorsa) |
| `CONDITIONAL` | Yayınlanmış sınırlama/koşullara tabi olarak çalışıyor |
| `FALSE_INDICATION` | Yanlış gösterge veriyor, kullanma |
| `FALSE_POSSIBLE` | Yanlış gösterge olasılığı var, dikkatli kullan |
| `DISPLACED` | Yeri değiştirilmiş |
| `IN_CONSTRUCTION` | İnşaat/yapım aşamasında |
| `UNRELIABLE` | Hem sinyal kesintisi hem yanlış bilgi verme riski |
| `RAIM_NOT_AVBL` | RAIM (Receiver Autonomous Integrity Monitoring) kullanılamıyor |

(+`OTHER`)

### 7.2 `signalType` → CodeRadioSignalType

| Değer | Açıklama |
|---|---|
| `AZIMUTH` | Yatay açı bilgisi sağlar/hesaplar |
| `DISTANCE` | Doğrusal mesafe bilgisi sağlar/hesaplar |
| `BEAM` | Yatay veya dikey düzlemde yönsel rehberlik sağlar |
| `VOICE` | Sesli bilgi taşıyıcısıdır |
| `DATALINK` | Veri taşıyıcısıdır |

(+`OTHER`)

---

## Ortak (base) attribute'lar

`NavaidType` → `AbstractAIXMFeatureType`, `NavaidTimeSliceType` →
`AbstractAIXMTimeSliceType`'dan miras alır. Bu iki tip `AIXM_AbstractGML_ObjectTypes.xsd`
dosyasında tanımlı — bu dosya elimizde olmadığı için içeriği teyit edilemedi. Standart
AIXM davranışına göre muhtemelen şunları içerir: `gml:identifier`, `validTime`,
`sequenceNumber`, `correctionNumber`, `interpretation`, `featureLifetime`.

## Genişletme noktası

`extension` alanı → soyut `AbstractNavaidExtension` (ulusal AIP'lerin kendi ek alanlarını
eklemesi için extension noktası, boş/soyut tanımlı).

---

## İlgili dokümanlar

- [AIXM_RoutePoint_DataTypes.md](../AIXM_RoutePoint_DataTypes.md) — Navaid'in
  `RouteSegment.start`/`end` içindeki 6 seçenekli nokta-seçim choice'ındaki yeri
- [AIXM_DesignatedPoint_Attributes.md](AIXM_DesignatedPoint_Attributes.md) — alternatif nokta türü
- [AIXM_Point_Attributes.md](AIXM_Point_Attributes.md) — `location`/`ElevatedPoint`'in temel aldığı tip
