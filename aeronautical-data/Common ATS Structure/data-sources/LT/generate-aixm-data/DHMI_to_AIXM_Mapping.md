# DHMİ → AIXM 5.2 Eşleme Dokümanı

`generate_aixm.py` tarafından üretilen `../lt-route-data-aixm.xml` dosyasındaki her alanın kaynağı, dönüşümü ve gerekçesi.

**Hedef şema:** AIXM 5.2
`D:\Belgeler\Havacılık Kütüphanesi\Charts, Guides, Regulations\Other Documents\Aeronautical Information Exchange Model (AIXM)\Scheme and Data AIXM 5.2\aixm_5_2_0_xsd\`
Namespace'ler: `message` = `http://www.aixm.aero/schema/5.2/message`, `aixm` = `http://www.aixm.aero/schema/5.2`, `gml` = `http://www.opengis.net/gml/3.2`, `xlink` = `http://www.w3.org/1999/xlink`.

**Doğrulama durumu:** üretilen XML, yukarıdaki şema setine karşı **geçerli** (0 hata).

---

## 1. Kaynak dosya envanteri

| Kaynak dosya | İçerik | Beslediği AIXM feature |
|---|---|---|
| `lats.json`, `lrnav.json`, `uats.json`, `urnav.json` | Point + LineString feature'ları | `DesignatedPoint`, `Navaid` (yalnızca Point'ler) |
| `lats_info.json`, `lrnav_info.json`, `uats_info.json`, `urnav_info.json` | Segment ek bilgileri (kid → alan sözlüğü) | `RouteSegment`, `Route` |
| `VFRPOINT.json` | VFR raporlama noktaları | `DesignatedPoint` (type=VRP), `Navaid` (stub) |
| `VFRSEGMENT.json` | VFR rota segmentleri | `RouteSegment`, `Route` |

ATS noktaları 4 dosyada tekrarlanır; `kid` ile tekilleştirilir. Doğrulandı: aynı `kid` her dosyada aynı isim, tip ve koordinatı taşıyor (0 çakışma).

**Üretilen feature sayıları:** 613 DesignatedPoint (ATS) · 263 DesignatedPoint (VFR) · 65 Navaid · 2 Navaid (stub) · 453 Route (ATS) · 97 Route (VFR) · 2670 RouteSegment (ATS) · 205 RouteSegment (VFR) = **4368**

---

## 2. Ortak yapı

Her feature: `message:hasMember` → `aixm:<Feature>` (`gml:id` okunabilir) → `gml:identifier codeSpace="urn:uuid:"` → tek `aixm:timeSlice`.

TimeSlice zorunlu alanları: `gml:validTime` (TimePeriod, `beginPosition` = `../data.json`'daki `data_effectivity` tarihi, `endPosition indeterminatePosition="unknown"`), `aixm:interpretation` = `BASELINE`, `sequenceNumber` = 1, `correctionNumber` = 0.

| Kimlik | Üretim |
|---|---|
| `gml:id` | **`LT_` kaynak önekiyle** okunabilir: `LT_DP_ODIRA`, `LT_NAV_IST`, `LT_VRP_SAFET`, `LT_RS_0001`, `LT_RS_VFR_0001`, `LT_RTE_UA285`, `LT_RTE_VFR_SOUTH`. Çakışmada sıra eki (`_2`). Türetilmiş id'ler (`_TS`, `_TP`, `_P`, `_EP`, `_NOTE`, `_FIX`, `_MEA`, `_C`, `_AC`, `_DS`) öneki miras alır. Mesaj kökü: `LT_MSG_ROUTE_DATA`. Önek, farklı kaynakların AIXM dosyaları tek bir GeoPackage'da birleşince id'lerin karışmaması içindir. |
| `gml:identifier` | Deterministik UUID5 (sabit namespace + `<tür>:<anahtar>`). DHMİ'nin kendi `kid` uuid'si **kullanılmaz** (kullanıcı kararı). Aynı girdi → aynı UUID. |

**Koordinatlar:** GeoJSON `[lon, lat]` sırasındadır; AIXM/EPSG:4326 `gml:pos` ve `gml:posList` **enlem boylam** sırasındadır — dönüşümde ters çevrilir. `srsName="urn:ogc:def:crs:EPSG::4326"`.

**Element sırası:** AIXM `<sequence>` grupları sıralıdır; tüm yazıcı modülleri alanları XSD sırasında üretir. Sıra dışı yazım şema doğrulamasını kırar.

---

## 3. DesignatedPoint (ATS) — 613 kayıt

| DHMİ | AIXM | Dönüşüm |
|---|---|---|
| `hi` | `designator` | Doğrudan. Doğrulandı: 613/613 tam 5 karakter |
| `pic` → `TYPE` | `type` | Doğrudan. Kaynakta tek değer: `ICAO` (geçerli `CodeDesignatedPointType`) |
| geometry `coordinates` | `location/aixm:Point/gml:pos` | `[lon,lat]` → `lat lon` |

11 ATS noktası ayrıca VFRPOINT'ten devralınan bir `fix`, 15'i ise `annotation` taşır — aynı ad ve konumdaki VFR noktası bu DesignatedPoint'e devredilmiştir (→ §7.3).

---

## 4. Navaid (ATS) — 65 kayıt

| DHMİ | AIXM | Dönüşüm |
|---|---|---|
| `type` (= `pic` → `TYPE`) | `type` | Doğrudan. Kaynak değerleri: `VOR_DME` (59), `NDB` (5), `VORTAC` (1) — üçü de geçerli `CodeNavaidServiceType` |
| `pic` → `DESIGNATOR` | `designator` | Doğrudan. 64 kayıt 3 karakter, 1 kayıt 2 karakter (`LU`) |
| `hi` (= `pic` → `NAME`) | `name` | Doğrudan. Doğrulandı: `hi` ile `pic/NAME` 65/65 birebir aynı |
| geometry `coordinates` | `location/aixm:ElevatedPoint/gml:pos` | Navaid'de `location` **ElevatedPoint** tipindedir (`Point` değil) |

---

## 5. RouteSegment (ATS) — 2670 kayıt

Kaynak: `*_info.json` (kid → alan sözlüğü).

| DHMİ alanı | AIXM hedefi | Dönüşüm / gerekçe |
|---|---|---|
| `LEVEL` | `level` | **Doğrudan.** Kaynak: `UPPER` (1398), `LOWER` (1270), `BOTH` (2) — üçü de geçerli `CodeLevelType` |
| `UPPER_LIMIT` | `upperLimit` (+`uom`) | `999` → **`UNL`** (yorum, kullanıcı onaylı); diğerleri sayı |
| `UPPER_LIMIT_REFERENCE` | `upperLimitReference` | **Doğrudan.** Kaynakta tek değer: `STD` |
| `LOWER_LIMIT` | `lowerLimit` (+`uom`) | Sayı normalize edilir (`055` → `55`) |
| `LOWER_LIMIT_REFERENCE` | `lowerLimitReference` | **Doğrudan.** `STD` (2611), `MSL` (55), `SFC` (4) — üçü de geçerli |
| — | `pathType` | `attribute-override.json` → `GRC` |
| `TRUE_TRACK` | `trueTrack` | Kaynakta 2670/2670 **boş** → element yazılmaz |
| `MAGNETIC_TRACK` | `magneticTrack` | Sayı normalize (`003` → `3`); 608 kayıtta boş → yazılmaz |
| `REVERSE_TRUE_TRACK` | `reverseTrueTrack` | Kaynakta 2670/2670 **boş** → yazılmaz |
| `REVERSE_MAGNETIC_TRACK` | `reverseMagneticTrack` | Sayı normalize |
| `LENGTH` | `length` `uom="NM"` | Doğrudan |
| `WIDTH_LEFT` / `WIDTH_RIGHT` | `widthLeft` / `widthRight` | Kaynakta 2670/2670 **boş** → yazılmaz |
| `LOWER_LIMIT` (ikinci kez) | `minimumEnrouteAltitude/AltitudeIndication/altitude` | Kullanıcı kararı: alt limit aynı zamanda MEA olarak da yazılır, aynı `uom` ile |
| `START_POINT_NAME` | `start/EnRouteSegmentPoint/pointChoice_*` | → §5.1 |
| `START_POINT_REPORTING_ATC` | `start/EnRouteSegmentPoint/reportingATC` | **Doğrudan.** `COMPULSORY` / `ON_REQUEST` — ikisi de geçerli `CodeATCReportingType` |
| `END_POINT_NAME` / `END_POINT_REPORTING_ATC` | `end/…` | Aynı kurallar |
| `START/END_POINT_COORDINATES` | `curveExtent/Curve/segments/GeodesicString/posList` | 2 noktalı geodesic. Kaynak zaten `enlem boylam` sırasında |
| `ROUTE_DESIGNATOR` | `routeFormed` | `xlink:href="urn:uuid:…"` → ilgili Route |
| `NAVIGATION_TYPE` | `aircraftCapability/AircraftCharacteristic/navigationType` | → §5.2 |
| `REQUIRED_NAVIGATION_PERFORMANCE` | aynı AircraftCharacteristic → `navigationSpecification` | → §5.2 |

### 5.1 Uç nokta çözümü

Kaynak uç nokta adı **her zaman noktanın `hi` değeridir**: DP'ler için designator (5 karakter), navaid'ler için NAME (`ISTANBUL`, `CARDAK`, `VAN`…). Navaid `designator`'ları (IST, CRD) uç nokta adı olarak **hiç geçmez**.

Kural: ad önce DP designator indeksinde, bulunamazsa navaid NAME indeksinde aranır.
- Bulunursa DP → `pointChoice_fixDesignatedPoint`, navaid → `pointChoice_navaidSystem` (`xlink:href`).
- Koordinat, indeksteki nokta koordinatıyla çapraz doğrulanır; uyuşmazlık loglanır.

**Ölçüm:** 5340/5340 uç nokta çözüldü, 0 çakışma, 0 koordinat uyuşmazlığı (4290 DP + 1050 navaid).

> **Terk edilen kural:** "5 harfli → DesignatedPoint, 4/3/2/1 harfli → Navaid" kuralı gerçek veriyle çelişiyordu — 13 navaid'in adı 5 harflidir (`SINOP`, `IZMIR`, `ADANA`, `HATAY`, `SIVAS`, `AFYON`, `ZAFER`, `CUBUK`, `IGDIR`, `SIIRT`, `VABEL`, `CORLU`, `TOKAT`) ve bu kural 213 uç noktayı yanlış yönlendiriyordu. Kullanıcı onayıyla isme göre birleşik arama kullanılmaktadır. Hiçbir ad hem DP hem navaid değildir (doğrulandı).

### 5.2 NAVIGATION TYPE ve RNP

AIXM 5.2'de `RouteSegment` üzerinde `navigationType` ve `requiredNavigationPerformance` alanları **yoktur** (5.1.1'de vardı, 5.2'de kaldırıldı). Bu bilgiler yalnızca `aircraftCapability` → `AircraftCharacteristic` üzerinden taşınabilir.

| Kaynak | AIXM | Tür |
|---|---|---|
| `NAVIGATION_TYPE` = `CONV` (932) | `navigationType` = `CONV` | **Doğrudan** (geçerli `CodeNavigationType`) |
| `NAVIGATION_TYPE` = `RNAV` (1738) | `navigationType` = `PBN` | **Yorum** — `RNAV`, `CodeNavigationType` enum'unda yoktur; PBN güncel ICAO karşılığıdır (kullanıcı onaylı) |
| `RNP` = `5` (1644) | `navigationSpecification` = `RNAV_5` | **Yorum** (kullanıcı onaylı) |
| `RNP` = `1` (4) | `navigationSpecification` = `RNAV_1` | **Yorum** (kullanıcı onaylı) |
| `RNP` = boş (1022) | yazılmaz | — |

Doğrulandı: RNP değerleri **yalnızca** `RNAV` satırlarında doludur (`CONV` satırlarında 932/932 boş), dolayısıyla `CONV` + `RNAV_x` çelişkisi oluşmaz.

XSD sırası uyarısı: `navigationSpecification`, `navigationType`'tan **önce** gelir.

---

## 6. Route (ATS) — 453 kayıt

Segmentlerin `ROUTE_DESIGNATOR` değerlerinden türetilir (benzersiz kod başına bir Route).

| Kaynak | AIXM | Dönüşüm |
|---|---|---|
| `ROUTE_DESIGNATOR` (örn. `UA 285`) | `designatorPrefix`, `designatorSecondLetter`, `designatorNumber`, `multipleIdentifier` | Desen: `^([KUST])?\s*([ABGHJLMNPQRTVWYZ])\s*(\d+)\s*([A-Z])?$` → `U`, `A`, `285`, — |
| — | `type` | override → `ATS` |
| — | `flightRule` | override → `IFR` |
| — | `designCriteria/DesignStandard/name` | override → `PANS_OPS` |

**Ölçüm:** 453/453 rota kodu desene uyuyor (0 hata). `ROUTE_DESIGNATOR`, fetcher tarafından sayfadaki `<span class="routeName">` içeriğinden alınır; 2670/2670 segmentte doludur ve geojson'daki `hi` ile 2670/2670 birebir uyuşur (çapraz doğrulandı).

Not: `Route` feature'ının **geometrisi yoktur** — geometri `RouteSegment.curveExtent` üzerindedir. `Route` kendi segmentlerini de listelemez; bağ tek yönlüdür (`RouteSegment.routeFormed` → `Route`).

---

## 7. DesignatedPoint (VFR) — 263 ham kayıt → 242 feature

| Kaynak (`VFRPOINT.json`) | AIXM | Dönüşüm |
|---|---|---|
| `hi` | `name` | ASCII'ye çevrilir (→ §10). **`designator` bilinçli olarak boş bırakılır** |
| — | `type` | override → `VRP` |
| geometry `coordinates` | `location/aixm:Point/gml:pos` | `[lon,lat]` → `lat lon` |
| `pic` → `Description` | `fix/PointReference` | → §7.1 |

263 ham kayıt tekilleştirmeden sonra **242** DesignatedPoint verir: 6 grup kendi içinde birleşir, 15 nokta ATS DesignatedPoint'ine devredilir (→ §7.3).

### 7.1 `fix` yapısı (radyal + mesafe)

Açıklama deseni: `<NAVAID> R<radyal>/D<mesafe>` (örn. `DAL R270/D22.51`).

| Kaynak parçası | AIXM yolu | Değer |
|---|---|---|
| — | `fix/PointReference/role` | **Bir tarif içinde** tek navaid → `RAD_DME`; iki navaid → `INTERSECTION` |
| `D22.51` | `distanceReference/Distance/distance` `uom="NM"` | 22.51 |
| — | `distanceReference/Distance/type` | `DME` |
| `DAL` | `distanceReference/Distance/pointChoice_navaidSystem` | `xlink:href` → Navaid |
| `R270` | `angleReference/AngleUse/theAngle/Angle/angle` | 270 |
| — | `…/Angle/angleType` | `RDL` |
| — | `…/Angle/indicationDirection` | `FROM` |
| `DAL` | `…/Angle/pointChoice_navaidSystem` | `xlink:href` → Navaid |

XSD sırası: `distanceReference`, `angleReference`'tan **önce** gelir.

**Bir açıklama = bir `aixm:fix`.** `fix` XSD'de 0..∞ olduğu için bir nokta birden fazla BAĞIMSIZ konum tarifi taşıyabilir. Bu ayrım önemlidir:

* Tek açıklamada iki navaid geçiyorsa (`BIG R200/D30.43 EDR R010/D16.72`) bu **tek** bir tariftir — iki radyalin KESİŞTİĞİ nokta. Tek `PointReference`, `role=INTERSECTION`, iki `distanceReference` + iki `angleReference`.
* Birleştirilen noktalarda ise her kaynak kaydının kendi açıklaması vardır (BAFA: `BDR R312/D21` ve `MEN R165/D49`). Bunlar aynı noktanın **bağımsız** iki tarifidir; **ayrı** `aixm:fix` alırlar, her biri `role=RAD_DME`. `INTERSECTION` yazmak yanlış olurdu — tarifler kesişerek noktayı belirlemiyor.

gml:id şeması: `<nokta_id>_FIX{n}`, altında `_FIX{n}_DIST{i}`, `_FIX{n}_ANGUSE{i}`, `_FIX{n}_ANG{i}`.

**Ölçüm (242 nokta + 11 ATS DP):** 127 `PointReference` — 125'i `RAD_DME`, 2'si `INTERSECTION` (`BIG…EDR` ve `EDR…CNK`). 2 nokta (BAFA, TURGUT) ikişer `fix` taşır; 128 nokta açıklamasızdır. Tekilleştirme öncesi de toplam 127 `PointReference` vardı: hiçbir tarif kaybolmadı, hiçbiri tekrarlanmadı.

### 7.2 Stub Navaid'ler (2 kayıt)

VFR fix açıklamalarında geçen `MEN` (24 nokta) ve `AYR` (1 nokta) kodları **kaynak dosyaların hiçbirinde tanımlı değildir** — konum, tip ve ad bilgisi yoktur.

Kullanıcı kararı: yalnızca `designator` taşıyan stub `Navaid` feature'ları üretilir. `location` ve `type` **yazılmaz** (uydurma veri girmemek için) ve `annotation` içinde durum açıkça belirtilir. Her ikisi de `errored-features.log`'a kaydedilir.

---

### 7.3 Tekilleştirme: 263 ham kayıt → 242 nokta

DHMİ kaynağında aynı fiziksel nokta birden fazla VFR rota grubunda **ayrı
kayıt** olarak girilmiştir. Ayrıca bazı VFR noktaları ATS tarafında zaten
tanımlı bir DesignatedPoint ile aynıdır. İki aşamalı tekilleştirme uygulanır.

**Eşik: 0,1 NM (~185 m).** Aynı ASCII adlı nokta çiftlerinin mesafeleri iki
kümede toplanır: birleşecek 6 çift 0,000–0,008 NM aralığında, gerçekten farklı
en yakın çift ise **176 NM** uzakta. 0,01–100 NM arasındaki her eşik aynı 6
grubu verir; tam eşitlik ise float sapması yüzünden kırılgandır (TEKIRDAG
çiftinde 0,00002 NM fark var). 0,1–2,0 NM bandındaki aynı adlı çiftler
birleştirilmez ama `vfr_nokta_yakin_ayni_isim` uyarısı yazılır (bugün 0 kayıt;
gelecek AIRAC için erken uyarı).

#### Aşama 1 — VFR noktaları kendi aralarında (6 grup)

Ad karşılaştırması **ASCII'ye katlanmış** ad üzerinden yapılır (§10): kaynakta
hem `BIGA` hem `BİGA` vardır ve AIXM'e ikisi de `BIGA` olarak yazılmaktadır.

| Grup | Birleşen kid | Sonuç |
|---|---|---|
| BAFA | 51 + 132 | 2 `fix` (`BDR R312/D21`, `MEN R165/D49`) |
| TURGUT | 55 + 127 | 2 `fix` (`BDR R062/D19`, `MEN R139/D69`) |
| TEKIRDAG | 28 + 73 | 1 `fix` (`CRL R233/D23.25`) |
| BURSA | 40 + 220 | 1 `fix` (`BRY R279/D28`) |
| BIGA | 30 + 155 (`BİGA`) | 1 `fix`, `annotation` = `BİGA` |
| KUYUMCU | 277 + 5040 | `fix` yok |

**Kimlik:** kazanan kayıt grubun **en küçük `kid`**'idir; `gml:identifier`
`feature_uuid("VfrPoint", <kid>)` ile ondan üretilir. Kullanıcı kararı — bu
sayede birleşmeyen 236 noktanın uuid'i hiç değişmez. Konum da kazanan kaydın
koordinatıdır (ortalama alınmaz, uydurma koordinat üretilmez).

**Veri kaybı yok:** üyelerin tüm konum tarifleri ayrı `fix` olarak korunur
(→ §7.1), ASCII dışı özgün yazımları `annotation` olarak eklenir ve her yutulan
üye `errored-features.log`'a `vfr_nokta_birlestirildi` olarak yazılır.
Birebir aynı tarif iki kez yazılmaz.

**Düzeltilen hata:** eskiden `vfr_index` aynı anahtarı korumasız üzerine
yazıyordu; dosyada sonra gelen kayıt indeksi eziyor, ilk kayıt XML'de kalıp hiç
`xlink:href` almıyordu. Bu yüzden 4 feature erişilemez durumdaydı ve BAFA ile
TURGUT'un birer konum tarifi hiçbir tüketiciye ulaşmıyordu.

#### Aşama 2 — VFR noktası ↔ ATS DesignatedPoint (15 nokta)

VFR noktasının adı bir ATS DesignatedPoint'in `designator`'ı ile aynı **ve**
konumu 0,1 NM içindeyse VFR noktası **yazılmaz**; ona bağlanan VFR segment uç
noktaları doğrudan ATS DesignatedPoint'e bağlanır.

Devredilenler: SOTIV, ALTIN, PETAR, KEKIK, NEXAM, SONUP, SULTA, RIVBU, ERFES,
ATSAL, BIRPU, MANAZ, KEMER, YAPZU, MILBA. Bunların 11'i bir konum tarifi taşır
ve tarif DP'ye `fix` olarak eklenir.

| Konu | Karar |
|---|---|
| DP'nin `type`'ı | **`ICAO` korunur.** Nokta IFR ATS rotalarında kullanılan ICAO noktasıdır; `VRP`'ye çevrilmez |
| VFR kökenli olduğu bilgisi | DP'ye `annotation` eklenir: `It is also a VFR point.` |
| Konum tarifi | DP'ye `fix` olarak taşınır |
| `name` | Eklenmez — eşleşme koşulu gereği zaten `designator` ile aynıdır |

**Sonuç:** bu 15 nokta artık `type=VRP` olmadığı için ortak üründe
(`build_common_ats.py` → `depiction_sig_point`) `VFR_REP` yerine `WPT`/`INT`
sınıfını alır. Bilgi kaybolmaz — annotation'da durur — ama sembolojiyi
etkiler; kullanıcı kararıdır.

**Ad tutup konum tutmayan hâller birleştirilmez:** ASKER (473 NM), SERCE
(391 NM), KEMER (208 NM), ORMAN (202 NM) — `vfr_nokta_dp_adi_ayni_konum_farkli`
uyarısı yazılır. KEMER'in iki VFR noktası vardır: `kid 90` ATS DP ile aynı
konumdadır ve devredilir, `kid 190` (Antalya) ayrı VFR noktası olarak kalır.

#### Uç nokta indeksi

Segment uç noktaları kaynaktaki **ham** ad ve koordinatla arandığı için
`vfr_index` 263 ham kaydın tamamının anahtarını taşır; değeri nihai uuid'dir
(kazanan VFR noktası ya da devralan ATS DesignatedPoint). Böylece
`_normalize_vfr_segment` ve `route_segment.py` hiç değişmeden çalışır.
Doğrulandı: 410/410 uç nokta çözülüyor ve hepsi tekilleştirme öncesiyle **aynı
fiziksel konuma** bağlanıyor.

---

## 8. RouteSegment (VFR) — 205 kayıt

Kaynak `VFRSEGMENT.json`'ın `pic` alanıdır; 9 etiketin tamamı 205/205 kayıtta doludur (ayrı bir clicked-info sorgusu gerekmez).

| `pic` etiketi | AIXM | Dönüşüm |
|---|---|---|
| `Start Point` | `start/…/pointChoice_fixDesignatedPoint` | İsim **+ koordinat** ile VFRPOINT eşlemesi (→ §8.1) |
| `End Point` | `end/…` | Aynı |
| `Distance` | `length` `uom="NM"` | `"10.8 NM"` → `10.8`. Birim envanteri 205/205 `NM` |
| `Calc. Start` | `trueTrack` | `°` temizlenir |
| `Calc End` | `reverseTrueTrack` | `°` temizlenir |
| `Magnetic Start` | `magneticTrack` | 79 kayıtta boş → yazılmaz |
| `Magnetic End` | `reverseMagneticTrack` | 79 kayıtta boş → yazılmaz |
| geometry | `curveExtent` | 2 noktalı geodesic |
| — | `pathType` | override → `GRC` |
| `hi` | ait olduğu Route'un `name` alanı | → §9 |

Doğrulandı: `Calc` ve `Magnetic` değerleri hiçbir kayıtta gerçek anlamda farklı değildir (126 kayıtta birebir aynı, 79 kayıtta magnetic boş).

### 8.1 VFR uç nokta çözümü

VFRPOINT'te aynı isimli farklı konumlu noktalar vardır (`KEMER`, `KILO`, `SANAYI`, `SAHIL`, `YENICE`, `PINARBASI` — en yakını 176 NM uzakta), bu yüzden eşleme **isim + koordinat** anahtarıyla yapılır.

Tekilleştirme (→ §7.3) bu mekanizmayı değiştirmez: indeks yutulan kayıtların anahtarlarını da taşır, yalnızca nihai uuid'e bakar. Uç nokta `pointChoice_fixDesignatedPoint` olarak yazılır — hedef ister VFR noktası ister ATS DesignatedPoint olsun, ikisi de `DesignatedPoint`'tir.

**Ölçüm:** 205/205 segmentin her iki ucu da çözüldü (410 uç nokta, 0 hata); tekilleştirme sonrası da 410/410 ve hepsi öncekiyle aynı fiziksel konumda.

---

## 9. Route (VFR) — 97 kayıt

| Kaynak | AIXM | Dönüşüm |
|---|---|---|
| segment `hi` | `name` | ASCII'ye çevrilir. Designator alanları **yazılmaz** (VFR rotalarının kodu yoktur) |
| — | `type` | override → `OTHER` |
| — | `flightRule` | override → `VFR` |
| — | `designCriteria/DesignStandard/name` | override → `OTHER` |

> **Bilinen sonuç (kullanıcı onaylı):** Rota kimliği olarak `hi` kullanılır, `pic` içindeki tam kod (`LTFE/SOUTH`) kullanılmaz. Bu nedenle 98 kaynak rotası 97 AIXM Route'una iner: `LTFE/NORTH` ile `LTFE/NORTH-SOUTH` ikisi de `hi="NORTH"` taşıdığı için tek Route'ta birleşir; farklı havaalanlarındaki aynı adlı rotalar da birleşir. Kullanıcı bu sonucu görüp onaylamıştır.

`OTHER` değeri geçerlidir: AIXM'de her `Code*Type` bir union'dır — sabit enum listesi **veya** `OTHER(:(\w|_){1,58})?` deseni.

---

## 10. ASCII dönüşümü (92 kayıt)

AIXM `TextNameType` deseni yalnızca ASCII kabul eder:
`([A-Z]|[a-z]|[0-9]|[, !"&#$%'\(\)\*\+\-\./:;<=>\?@\[\\\]\^_\|\{\}])*`

DHMİ VFR nokta ve rota adlarında Türkçe karakter bulunur (ATS tarafında hiç yoktur). Kullanıcı kararı: ad ASCII'ye çevrilir, **orijinal yazım `annotation/Note` içinde korunur** (veri kaybı olmaz).

Çeviri tablosu: `Ç→C, ç→c, Ğ→G, ğ→g, İ→I, ı→i, Ö→O, ö→o, Ş→S, ş→s, Ü→U, ü→u, Â→A, â→a, Î→I, î→i, Û→U, û→u`

Not alanı yalnızca özgün yazımı taşır, açıklama metni içermez.
Örnek: `name` = `HOSKOY`, `annotation/Note/translatedNote/LinguisticNote/note` = `HOŞKÖY`

Her dönüşüm `errored-features.log`'a `ascii_ye_cevrildi` olarak kaydedilir — tekilleştirmede **yutulan üyeler için de** yazılır (92 kayıt korunur), böylece kaynaktaki her Türkçe yazım hem logda hem `annotation`'da görünür.

---

## 11. `attribute-override.json`

Yapı: `<kaynak grubu>.<feature türü>.<attribute> = değer`. Buradaki değerler kaynaktan gelen değerin yerine yazılır; listede olmayan attribute'lar kaynaktan gelir.

| Grup | Feature | Attribute | Değer |
|---|---|---|---|
| `ats` | RouteSegment | `pathType` | `GRC` |
| `ats` | Route | `type` / `flightRule` / `designCriteria` | `ATS` / `IFR` / `PANS_OPS` |
| `vfr` | DesignatedPoint | `type` | `VRP` |
| `vfr` | RouteSegment | `pathType` | `GRC` |
| `vfr` | Route | `type` / `flightRule` / `designCriteria` | `OTHER` / `VFR` / `OTHER` |

---

## 12. Kullanılmayan kaynak alanları

Bunlar DHMİ portalının harita çizim/görsel alanlarıdır; AIXM karşılıkları yoktur ve bilinçli olarak aktarılmamıştır.

| Alan | Neden kullanılmadı |
|---|---|
| `ip`, `cip`, `ipm`, `aip` | İkon dosya yolları (çizim) |
| `strclr`, `fclr` | Çizgi/dolgu rengi (çizim) |
| `t`, `is`, `zi`, `ht`, `rpType` | Katman tipi/kalınlık/zoom/görünürlük (çizim) |
| `cil` | Clicked-info iframe HTML'i (portal iç bağlantısı) |
| `lc` | `hi` + konum + açıklamanın metin birleşimi (zaten ayrı ayrı alınıyor) |
| `kid` | Yalnızca kaynak içi eşleme anahtarı olarak kullanılır; UUID'ler bağımsız üretilir (kullanıcı kararı) |
| `pic` → `POSITION` / `GML POS` (DMS metin) | Geometry alanı daha hassas; DMS saniyeye yuvarlıdır |
| `sa`, `ea`, `dist` (VFRSEGMENT) | `pic` içindeki `Calc. Start` / `Calc End` / `Distance` ile aynı değerler |
| `pic` → `Route` (VFRSEGMENT, örn. `LTFE/SOUTH`) | Kullanıcı kararıyla rota kimliği `hi`'dir (→ §9) |
| `pic` → `Route Segment` (VFRSEGMENT) | `hi` ile aynı değeri taşır |

---

## 13. Bilinen sınırlamalar

1. **Stub navaid'ler (MEN, AYR):** konumsuz ve tipsizdir; kaynakta tanımlı olmadıkları için (→ §7.2).
2. **VFR rota birleşmesi:** 98 kaynak rotası 97 Route'a iner (→ §9).
3. **Kaynakta hep boş alanlar:** ATS segmentlerinde `TRUE_TRACK`, `REVERSE_TRUE_TRACK`, `WIDTH_LEFT`, `WIDTH_RIGHT` 2670/2670 kayıtta boştur; ilgili AIXM elementleri yazılmaz.
4. **Bozuk kaynak değeri:** `RS_VFR_0196` (kid 659, `LTBJ/NORTH2`, GERMENCIK→TORBALI) segmentinde `Calc End` ve `Magnetic End` değerleri `14142°` gelmektedir (kerteriz 0-360 olmalıdır). Kullanıcı kararı: **otomatik düzeltilmez** (her ay tekrar gelebilir) — yalnızca hatalı alan yazılmaz, kayıt XML'de kalır ve `not.txt`'ye tüm kaynak alanlarıyla kaydedilir.
5. **`codeICAOCountry`** hiçbir feature'da yazılmaz — kaynakta ICAO Doc 7910 ülke kodu bulunmamaktadır.
6. **Devredilen VFR noktalarının sembolojisi:** ATS DesignatedPoint'ine devredilen 15 nokta `type=ICAO` kaldığı için ortak üründe `VFR_REP` sınıfını almaz (→ §7.3, Aşama 2). VFR raporlama noktası oldukları bilgisi yalnızca `annotation`'da durur.
7. **Tekilleştirme kimliği `kid`'e bağlıdır:** birleşen grubun uuid'i en küçük `kid`'den üretilir. DHMİ gelecek bir AIRAC'ta o `kid`'i düşürüp diğerini korursa noktanın uuid'i değişir.

---

## 14. Çıktı dosyaları

| Dosya | İçerik |
|---|---|
| `../lt-route-data-aixm.xml` | AIXM 5.2 çıktısı (başında `<!-- Generated by Ibosoft -->`) |
| `errored-features.log` | `SEVERITY \| FEATURE \| ID \| FIELD \| VALUE \| VIOLATION`. Her çalıştırmada sıfırlanır |
| `not.txt` | Hatalı alanı düşürülen kayıtlar, tüm kaynak alanlarıyla — doğru değer elle eklenmelidir. Her çalıştırmada sıfırlanır |
