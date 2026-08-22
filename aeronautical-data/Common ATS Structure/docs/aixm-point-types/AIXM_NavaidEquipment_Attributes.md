# AIXM 5.2 — NavaidEquipment (Fiziksel Navigasyon Ekipmanı): Tam Attribute Listesi

Kaynak: `AIXM_Features_annotated.xsd` (`AbstractNavaidEquipmentType`, satır ~10047-10126; 11
somut alt-tür, satır ~9089-10858) + `AIXM_DataTypes_annotated.xsd` (17 January 2025, AIXM 5.2)

> **Genel not:** Her `Code*Type` aslında `union` yapıdadır: sabit enum listesi **veya**
> `OTHER(:(\w|_){1,58})?` deseni (yani `OTHER:MY_CODE` gibi serbest bir uzatma). Ayrıca
> her `Code*`/`Val*`/`Text*Type`, `complexType` olarak `gml:NilReasonEnumeration` tipinde
> bir `nilReason` attribute'u da taşır.

## Bu doküman neden ayrı

`Navaid.navaidEquipment` (→ `NavaidComponent.theNavaidEquipment`, bkz.
[AIXM_Navaid_Attributes.md §5](AIXM_Navaid_Attributes.md)) önceden "kapsam dışı (büyük,
ayrı feature hiyerarşisi)" olarak bırakılmıştı. Bu doğru bir tespitti ama gerekçesi
yetersiz açıklanmıştı — gerçek durum şu:

`AbstractNavaidEquipment`, `NavaidComponent`'in içine gömülü bir alt-yapı **değildir** —
kendi başına bağımsız bir **Feature**'dır (`AbstractNavaidEquipmentType` →
`AbstractAIXMFeatureType`, kendi `gml:id`/`timeSlice` geçmişi var).
`NavaidComponent.theNavaidEquipment` sadece ona bir association'dır (xlink:href).

Bu soyut tipin **11 somut alt-türü** vardır (substitutionGroup üyeleri):

| Element | Tip | Ne olduğu |
|---|---|---|
| `VOR` | `VORType` | → bkz. **2.1** |
| `DME` | `DMEType` | → bkz. **2.2** |
| `TACAN` | `TACANType` | → bkz. **2.3** |
| `Localizer` | `LocalizerType` | ILS'in VHF bileşeni → bkz. **2.4** |
| `Glidepath` | `GlidepathType` | ILS'in UHF (glide slope) bileşeni → bkz. **2.5** |
| `MarkerBeacon` | `MarkerBeaconType` | → bkz. **2.6** |
| `NDB` | `NDBType` | → bkz. **2.7** |
| `SDF` | `SDFType` | Simplified Directional Facility → bkz. **2.8** |
| `Azimuth` | `AzimuthType` | MLS'in azimuth bileşeni → bkz. **2.9** |
| `Elevation` | `ElevationType` | MLS'in elevation bileşeni → bkz. **2.10** |
| `DirectionFinder` | `DirectionFinderType` | → bkz. **2.11** |

Hepsi ortak bir taban özellik grubunu (§1) paylaşır, üzerine kendi özel alanlarını ekler (§2).

---

## 1. Ortak taban — NavaidEquipmentPropertyGroup (tüm 11 alt-türde ortak)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `designator` | `CodeNavaidDesignatorType` | Enum değil — serbest alfanumerik, 1-4 karakter (bkz. `AIXM_Navaid_Attributes.md`) |
| `name` | `TextNameType` | Enum değil — serbest metin, max 60 karakter |
| `emissionClass` | `CodeRadioEmissionType` | → bkz. **1.1** |
| `mobile` | `CodeYesNoType` | `YES/NO` — ekipman mobil mi (örn. taşınabilir DME/TACAN) |
| `magneticVariation` | `ValMagneticVariationType` | -180 ile +180 arası ondalık derece (işaretli) — Manyetik Kuzey'in Coğrafi Kuzey'e göre sapması (pozitif = doğuya) |
| `dateMagneticVariation` | `DateYearType` | Enum değil — 4 haneli yıl (desen `[1-9][0-9][0-9][0-9]`), manyetik sapmanın ölçüldüğü yıl |
| `flightChecked` | `CodeYesNoType` | `YES/NO` — uçuş kontrolü yapıldı mı |
| `location` (0..1) | `ElevatedPointPropertyType` | Ekipmanın bulunduğu konum → bkz. `AIXM_Navaid_Attributes.md` §6 (ElevatedPoint ile aynı yapı) |
| `authority` (0..∞) | `AuthorityForNavaidEquipmentPropertyType` | Ekipmandan sorumlu kuruluş → bkz. **1.2** |
| `monitoring` (0..∞) | `NavaidEquipmentMonitoringPropertyType` | Ekipmanın izlenme (monitoring) bilgisi → bkz. **1.3** |
| `availability` (0..∞) | `NavaidOperationalStatusPropertyType` | Ekipmanın operasyonel durumu → bkz. `AIXM_Navaid_Attributes.md` §7 (NavaidOperationalStatus ile aynı yapı) |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](../AIXM_Annotation_Attributes.md) |

---

### 1.1 `emissionClass` → CodeRadioEmissionType

ITU 1979 Dünya İdari Radyo Konferansı'na göre yayın (emisyon) tipi kodu.

| Değer | Açıklama |
|---|---|
| `A2` | Telgraf, sesli değil |
| `A3A` | Tek yan bant, azaltılmış taşıyıcı |
| `A3B` | İki bağımsız yan bant |
| `A3E` | AM çift yan bant telefoni |
| `A3H` | Tek yan bant, tam taşıyıcı |
| `A3J` | Tek yan bant, bastırılmış taşıyıcı |
| `A3L` | Alt tek yan bant, taşıyıcı bilinmiyor |
| `A3U` | Üst tek yan bant, taşıyıcı bilinmiyor |
| `J3E` | AM çift yan bant bastırılmış taşıyıcı telefoni |
| `NONA1A` | Modülasyonsuz iletim, morse tanımlayıcı, taşıyıcı kesintili |
| `NONA2A` | Modülasyonsuz iletim, morse tanımlayıcı, taşıyıcı sürekli |
| `PON` | Darbeli (pulse) |
| `A8W` | AM (anahtarsız) + tanımlayıcı tonun ON/OFF anahtarlaması |
| `A9W` | Bileşik AM/FM (anahtarsız) + tanımlayıcı tonun ON/OFF anahtarlaması |
| `NOX` | Modülasyonsuz taşıyıcı |
| `G1D` | DPSK veri iletimi |

(+`OTHER`)

---

### 1.2 `authority` → AuthorityForNavaidEquipment

> *"Provides details about the level of responsibility of an OrganisationAuthority for a
> Navaid Equipment."*

`AuthorityForNavaidEquipmentType` → `AbstractAIXMObjectType` (Object, Feature değil).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeAuthorityRoleType` | `OWN` (sahip), `OPERATE` (işletici), `SUPERVISE` (düzenleyici/denetleyici rol) (+OTHER) |
| `annotation` (0..∞) | `NotePropertyType` | → bkz. [AIXM_Annotation_Attributes.md](../AIXM_Annotation_Attributes.md) |
| `theOrganisationAuthority` | `OrganisationAuthorityPropertyType` | Sorumlu kuruluşa association — kapsam dışı (büyük, ayrı Organisation/Authority feature'ı; `Route.userOrganisation` ile aynı tip, bkz. `AIXM_Route_Attributes.md`) |

---

### 1.3 `monitoring` → NavaidEquipmentMonitoring

> *"Navaid equipment monitoring information."*

`NavaidEquipmentMonitoringType` → `AbstractPropertiesWithScheduleType`'ı genişletir (yani
zaman/programa bağlı olabilir — schedule alanları `AIXM_Navaid_Attributes.md` §7'deki
`NavaidOperationalStatus` ile aynı gerekçeyle kapsam dışı bırakılmıştır).

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `monitored` | `CodeYesNoType` | `YES/NO` — ekipman izleniyor (monitor ediliyor) mu |

---

## 2. 11 somut alt-tür (her biri §1'in ortak alanlarına ek olarak)

### 2.1 VOR

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeVORType` | `VOR` (konvansiyonel VOR), `DVOR` (Doppler VOR), `VOT` (VOR test tesisi) (+OTHER) |
| `frequency` | `ValFrequencyType` | Sayı (>0) + `uom`: `HZ, KHZ, MHZ, GHZ` |
| `zeroBearingDirection` | `CodeNorthReferenceType` | `TRUE` (gerçek kuzey), `MAG` (manyetik kuzey), `GRID` (UTM grid kuzeyi) (+OTHER) — "sıfır kerteriz"in referans aldığı kuzey türü |
| `declination` | `ValMagneticVariationType` | -180/+180 derece (işaretli) — istasyonun beyan ettiği manyetik sapma ile gerçek manyetik sapma arasındaki fark |

---

### 2.2 DME

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeDMEType` | `NARROW` (DME/N, dar spektrum), `PRECISION` (DME/P, DME/N'e göre gelişmiş doğruluk), `WIDE` (DME/W, geniş spektrum) (+OTHER) |
| `channel` | `CodeDMEChannelType` | → bkz. **2.2.1** |
| `displace` | `ValDistanceType` | Sayı (≥0) + `uom`: `NM, KM, M, FT, MI, CM` — DME anteninden, DME alıcısında sıfır mesafe göstergesinin oluştuğu konuma olan mesafe |
| `tuningFrequencyVHF` | `ValFrequencyType` | Sayı (>0) + `uom`: `HZ, KHZ, MHZ, GHZ` — ICAO Annex 10 Tablo A'ya göre DME ile eşleştirilmiş sanal VHF tesisinin frekansı |

#### 2.2.1 `channel` → CodeDMEChannelType

Sabit, kapalı bir enumerasyon — **352 değer** (ICAO Annex 10 Tablo A DME kanal tablosuna
göre): kanal numarası `1`-`126` + alt-kanal harfi. Her kanal numarasının en az `X` ve `Y`
alt-kanalı var; MLS ile eşleştirilmiş 100 kanalda ayrıca `W`/`Z` alt-kanalları da mevcut
(örn. `1X, 1Y, ..., 17X, 17Y, 17Z, 18X, 18Y, 18W, 18Z, ..., 126X, 126Y`). Bu 352 değeri
tek tek tablo halinde listelemek yerine formatı ve kaynağı belirtiyoruz — tam liste,
klasördeki `AIXM_DataTypes_annotated.xsd` dosyasında (`CodeDMEChannelBaseType`) birebir
mevcut. (+`OTHER`)

---

### 2.3 TACAN

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `channel` | `CodeTACANChannelType` | DME ile birebir aynı 352 değerlik enumerasyon (bkz. **2.2.1**) — TACAN kanalları DME kanal numaralandırmasıyla ortak |
| `declination` | `ValMagneticVariationType` | -180/+180 derece (işaretli) — istasyonun gösterdiği "sıfır kerteriz" yönü ile Gerçek Kuzey arasındaki açısal fark |
| `tuningFrequencyVHF` | `ValFrequencyType` | Sayı (>0) + `uom`: `HZ, KHZ, MHZ, GHZ` — ICAO Annex 10 Tablo A'ya göre TACAN'ın mesafe ölçüm bileşeniyle eşleştirilmiş VHF tesisinin frekansı |

---

### 2.4 Localizer (ILS'in VHF bileşeni)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `frequency` | `ValFrequencyType` | Sayı (>0) + `uom`: `HZ, KHZ, MHZ, GHZ` |
| `magneticBearing` | `ValBearingType` | 0-360 derece — localizer inbound kursu ile anten konumundaki Manyetik Kuzey arasındaki açı |
| `trueBearing` | `ValBearingType` | 0-360 derece — localizer inbound kursu ile anten konumundaki Gerçek Kuzey arasındaki açı |
| `declination` | `ValMagneticVariationType` | -180/+180 derece (işaretli) — Gerçek Kuzey ile istasyon deklinasyonu (istasyonun gösterdiği Manyetik Kuzey) arasındaki açısal fark |
| `widthCourse` | `ValAngleType` | -180/+180 derece — localizer kurs genişliği |
| `backCourseUsable` | `CodeILSBackCourseType` | `YES`, `NO`, `RSTR` (kısıtlı kullanılabilir) (+OTHER) — arka kurs (back course) sektöründe sinyalin kullanılabilirliği |
| `signalPerformance` | `CodeSignalPerformanceILSType` | → bkz. `AIXM_Navaid_Attributes.md` §2 (aynı tip) |
| `courseQuality` | `CodeCourseQualityILSType` | → bkz. `AIXM_Navaid_Attributes.md` §3 (aynı tip) |
| `integrityLevel` | `CodeIntegrityLevelILSType` | → bkz. `AIXM_Navaid_Attributes.md` §4 (aynı tip) |

---

### 2.5 Glidepath (ILS'in UHF/glide slope bileşeni)

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `frequency` | `ValFrequencyType` | Sayı (>0) + `uom`: `HZ, KHZ, MHZ, GHZ` — glide path göstergesinin frekans değeri |
| `slope` | `ValAngleType` | -180/+180 derece — glide path açısı |
| `rdh` | `ValDistanceVerticalType` | ILS Referans Datum Yüksekliği (ILS RDH) — Sayı + `uom`: `FT, M, FL, SM` |
| `signalPerformance` | `CodeSignalPerformanceILSType` | → bkz. `AIXM_Navaid_Attributes.md` §2 (aynı tip) |
| `courseQuality` | `CodeCourseQualityILSType` | → bkz. `AIXM_Navaid_Attributes.md` §3 (aynı tip) |
| `integrityLevel` | `CodeIntegrityLevelILSType` | → bkz. `AIXM_Navaid_Attributes.md` §4 (aynı tip) |

---

### 2.6 MarkerBeacon

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `class` | `CodeMarkerBeaconSignalType` | `FAN` (fan marker), `LOW_PWR_FAN` (düşük güçlü fan marker), `Z` (Z marker), `BONES` (kemik şeklinde fan marker) (+OTHER) |
| `frequency` | `ValFrequencyType` | Sayı (>0) + `uom`: `HZ, KHZ, MHZ, GHZ` — radyo yayın frekansı değeri |
| `axisBearing` | `ValBearingType` | 0-360 derece — marker beacon'ın minör ekseninin gerçek kerterizi (kaynak: ARINC 424) |
| `auralMorseCode` | `CodeAuralMorseType` | Enum değil — nokta/tire karakter dizisi, desen `([\-\.]*)` (örn. `-.-.`) — beacon'ın yaydığı Morse kodu |

---

### 2.7 NDB

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `frequency` | `ValFrequencyType` | Sayı (>0) + `uom`: `HZ, KHZ, MHZ, GHZ` — NDB yayınının frekansı |
| `class` | `CodeNDBUsageType` | `ENR` (enroute NDB), `L` (Locator — final yaklaşma için düşük güçlü NDB, "compass locator" olarak da bilinir), `MAR` (deniz feneri/marine beacon) (+OTHER) |
| `emissionBand` | `CodeEmissionBandType` | `U` (UHF), `H` (HF), `M` (MF — orta frekans, NDB'ler için tipik bant) (+OTHER) |

---

### 2.8 SDF (Simplified Directional Facility)

> *"Localizer'a benzer bir final yaklaşma kursu sağlar ama Localizer kadar hassas
> değildir; glide slope bilgisi vermez. 108.10-111.95 MHz aralığında yayın yapar."*

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `frequency` | `ValFrequencyType` | Sayı (>0) + `uom`: `HZ, KHZ, MHZ, GHZ` |
| `magneticBearing` | `ValBearingType` | 0-360 derece — localizer huzmesi ile anten konumundaki Manyetik Kuzey arasındaki ölçülen açı |
| `trueBearing` | `ValBearingType` | 0-360 derece — localizer huzmesi ile anten konumundaki Gerçek Kuzey arasındaki ölçülen açı |

---

### 2.9 Azimuth (MLS'in azimuth bileşeni)

> *"MLS'in bir bileşeni; SHF vericisi ve ilgili ekipmandan oluşur, pist yaklaşımı yapan
> uçaklara azimuth bilgisi (veya pist ayrılışı/pas geçme yapan uçaklara ters azimuth
> bilgisi) sağlar."*

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `type` | `CodeMLSAzimuthType` | `FWD` (normal/ileri azimuth), `BWD` (ters/geri azimuth) (+OTHER) |
| `trueBearing` | `ValBearingType` | 0-360 derece — azimuth huzmesi ile anten konumundaki Gerçek Kuzey arasındaki ölçülen açı |
| `magneticBearing` | `ValBearingType` | 0-360 derece — azimuth huzmesi yönü ile anten konumundaki Manyetik Kuzey arasındaki ölçülen açı |
| `angleProportionalLeft` | `ValAngleType` | -180/+180 derece — azimuth göstergesinin, sıfır gösterge yönünden sapmayla orantılı olduğu açı, anten konumundan sola doğru |
| `angleProportionalRight` | `ValAngleType` | -180/+180 derece — aynısı, sağa doğru |
| `angleCoverLeft` | `ValAngleType` | -180/+180 derece — sıfır gösterge yönünden itibaren azimuth göstergesinin kullanılabilir olduğu açı, sola doğru |
| `angleCoverRight` | `ValAngleType` | -180/+180 derece — aynısı, sağa doğru |
| `channel` | `CodeMLSChannelType` | → bkz. **2.9.1** |

#### 2.9.1 `channel` → CodeMLSChannelType

Sabit, kapalı bir enumerasyon — **200 değer**, `500`-`699` arası ardışık tam sayı (ICAO
Annex 10 MLS kanal tablosuna göre). Tek tek listelemek yerine aralığı belirtiyoruz — tam
liste `AIXM_DataTypes_annotated.xsd` dosyasında (`CodeMLSChannelBaseType`) mevcut. (+`OTHER`)

---

### 2.10 Elevation (MLS'in elevation bileşeni)

> *"MLS'in bir bileşeni; SHF vericisi ve ilgili ekipmandan oluşur, pist yaklaşımı yapan
> uçaklara açısal değer olarak elevation (iniş açısı) bilgisi sağlar."*

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `angleNominal` | `ValAngleType` | -180/+180 derece — MLS kurulumu için normal glide path açısı |
| `angleMinimum` | `ValAngleType` | -180/+180 derece — bir MLS prosedürü için izin verilen en düşük elevation açısı |
| `angleSpan` | `ValAngleType` | -180/+180 derece — elevation verici sinyalinin alt ve üst limitleri arasındaki açı aralığının değeri |

---

### 2.11 DirectionFinder

> *"Yönlü antenler aracılığıyla bir radyo kaynağının konumunu belirlemek için kullanılan
> elektronik cihaz; vericiye tam olarak yöneldiğinde en güçlü radyo sinyalini alır."*

| Attribute | Değer Tipi | Enum / Format |
|---|---|---|
| `doppler` | `CodeYesNoType` | `YES/NO` — ekipman daha yüksek hassasiyet için Doppler etkisini kullanıyor mu |
| `informationProvision` (0..∞) | `InformationServicePropertyType` | Direction Finder ile ilişkili bilgi servisi (TWEB, ASOS, AWOS vb.) — kapsam dışı (büyük, ayrı `InformationService` feature hiyerarşisi, `AbstractService` substitution group) |

---

## Ortak (base) attribute'lar

Her 11 alt-tür → `AbstractAIXMFeatureType`'dan miras alır (kendi `gml:id`, `timeSlice`,
`validTime` vb.) — bkz. `AIXM_Route_Attributes.md`'deki genel not.

## Genişletme noktası

Her alt-tür kendi `AbstractXxxExtension` noktasına sahiptir (örn. `AbstractVORExtension`,
`AbstractDMEExtension` vb.) — ulusal AIP'lerin ek alan eklemesi için, boş/soyut tanımlı.

---

## İlgili dokümanlar

- [AIXM_Navaid_Attributes.md](AIXM_Navaid_Attributes.md) — `Navaid.navaidEquipment` (→
  `NavaidComponent.theNavaidEquipment`) bu dokümana yönlendiriyor
- [AIXM_Annotation_Attributes.md](../AIXM_Annotation_Attributes.md) — `annotation` alanının ortak yapısı
