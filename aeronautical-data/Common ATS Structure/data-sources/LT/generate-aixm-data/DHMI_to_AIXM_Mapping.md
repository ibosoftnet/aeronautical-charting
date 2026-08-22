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

## 7. DesignatedPoint (VFR) — 263 kayıt

| Kaynak (`VFRPOINT.json`) | AIXM | Dönüşüm |
|---|---|---|
| `hi` | `name` | ASCII'ye çevrilir (→ §10). **`designator` bilinçli olarak boş bırakılır** |
| — | `type` | override → `VRP` |
| geometry `coordinates` | `location/aixm:Point/gml:pos` | `[lon,lat]` → `lat lon` |
| `pic` → `Description` | `fix/PointReference` | → §7.1 |

### 7.1 `fix` yapısı (radyal + mesafe)

Açıklama deseni: `<NAVAID> R<radyal>/D<mesafe>` (örn. `DAL R270/D22.51`).

| Kaynak parçası | AIXM yolu | Değer |
|---|---|---|
| — | `fix/PointReference/role` | Tek navaid → `RAD_DME`; iki navaid → `INTERSECTION` |
| `D22.51` | `distanceReference/Distance/distance` `uom="NM"` | 22.51 |
| — | `distanceReference/Distance/type` | `DME` |
| `DAL` | `distanceReference/Distance/pointChoice_navaidSystem` | `xlink:href` → Navaid |
| `R270` | `angleReference/AngleUse/theAngle/Angle/angle` | 270 |
| — | `…/Angle/angleType` | `RDL` |
| — | `…/Angle/indicationDirection` | `FROM` |
| `DAL` | `…/Angle/pointChoice_navaidSystem` | `xlink:href` → Navaid |

XSD sırası: `distanceReference`, `angleReference`'tan **önce** gelir.

**Ölçüm:** 125 nokta tek referanslı, 2 nokta çift referanslı (`BIG R200/D30.43 EDR R010/D16.72` ve `EDR R291/D33.43 CNK R185/D21.21`), 136 nokta açıklamasız (`fix` yazılmaz — alan 0..∞ olduğu için geçerli).

### 7.2 Stub Navaid'ler (2 kayıt)

VFR fix açıklamalarında geçen `MEN` (24 nokta) ve `AYR` (1 nokta) kodları **kaynak dosyaların hiçbirinde tanımlı değildir** — konum, tip ve ad bilgisi yoktur.

Kullanıcı kararı: yalnızca `designator` taşıyan stub `Navaid` feature'ları üretilir. `location` ve `type` **yazılmaz** (uydurma veri girmemek için) ve `annotation` içinde durum açıkça belirtilir. Her ikisi de `errored-features.log`'a kaydedilir.

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

VFRPOINT'te aynı isimli farklı konumlu noktalar vardır (`KEMER` iki farklı konumda, `KILO` iki farklı konumda), bu yüzden eşleme **isim + koordinat** anahtarıyla yapılır.

**Ölçüm:** 205/205 segmentin her iki ucu da çözüldü (410 uç nokta, 0 hata).

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

Her dönüşüm `errored-features.log`'a `ascii_ye_cevrildi` olarak kaydedilir.

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

---

## 14. Çıktı dosyaları

| Dosya | İçerik |
|---|---|
| `../lt-route-data-aixm.xml` | AIXM 5.2 çıktısı (başında `<!-- Generated by Ibosoft -->`) |
| `errored-features.log` | `SEVERITY \| FEATURE \| ID \| FIELD \| VALUE \| VIOLATION`. Her çalıştırmada sıfırlanır |
| `not.txt` | Hatalı alanı düşürülen kayıtlar, tüm kaynak alanlarıyla — doğru değer elle eklenmelidir. Her çalıştırmada sıfırlanır |
