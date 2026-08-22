# LT Route Data → AIXM 5.2 XML üretici

> Arşiv notu: Bu, `generate-aixm-data/` altındaki script'i üretmek için kullanılan orijinal uygulama planıdır. İş tamamlandı (çıktı `../lt-route-data-aixm.xml`, AIXM 5.2 XSD setine karşı 0 hatayla doğrulandı, bkz. `DHMI_to_AIXM_Mapping.md`). Bu dosya, planın kaydını korumak amacıyla buraya arşivlenmiştir.

## Context

Önceki adımda `LT Route Data Fetcher` yeniden yazıldı ve DHMİ AIS portalından 6 ham GeoJSON (`urnav`, `lrnav`, `uats`, `lats`, `VFRSEGMENT`, `VFRPOINT`) + ATS segmentleri için 4 ek-bilgi dosyası (`*_info.json`) `raw-data/` altına indiriliyor. Şimdi bu ham veriyi AIXM 5.2 şemasına uygun tek bir XML dosyasına dönüştüren ana işleme scripti yazılacak.

**Bağlayıcı kural:** Yalnızca AIXM 5.2 XSD ve `Common ATS Structure\docs\` altındaki öznitelik sözlüklerinde tanımlı alanlar kullanılacak. Hiçbir alan uydurulmayacak, bilinmeyen/belirsiz her durum kullanıcıya sorulacak (bu plan boyunca yapıldığı gibi), sessizce varsayım yapılmayacak.

### Doğrulanmış kaynak bulguları (hepsi gerçek veri üzerinde ölçüldü, varsayım değil)

| Bulgu | Ölçüm |
|---|---|
| ATS noktaları 4 dosyada tekrarlanıyor ama `kid` (uuid) ve koordinat **birebir tutarlı** | 678 farklı nokta (613 DP + 65 navaid), 0 kid çakışması, 0 koordinat çakışması |
| DP `hi` değerleri **hep 5 karakter**, `pic` TYPE değeri **hep ICAO** | 613/613 |
| Navaid `hi` == `pic` NAME **her zaman**; designator 3 karakter (64), 2 karakter (1: `LU`) | 65/65 |
| Navaid tipleri | VOR_DME (59), NDB (5), VORTAC (1) — hepsi geçerli `CodeNavaidServiceType` |
| ATS segmentleri | 2670, hepsi benzersiz `kid`, dosyalar arası tekrar yok |
| Segment uç noktaları isimle **%100 çözülüyor** (koordinatlar da birebir tutuyor) | 5340/5340, 0 çakışma, 0 kayıp |
| "5 harfli → DP" kuralı **213 uç noktada yanlış** (5 harfli navaid adları: SINOP, IZMIR, ADANA, HATAY, SIVAS…) | kullanıcı onayıyla terk edildi |
| Rota kodları (`hi`) AIXM designator desenine **%100 uyuyor** | 453/453 |
| VFR segment uç noktaları VFRPOINT'te **isim+koordinatla %100 çözülüyor** | 205/205 |
| VFRPOINT'te aynı isimli farklı konumlu noktalar var (KEMER, KILO) | isim tek başına yetersiz → isim+koordinat kullanılacak |
| VFR `Calc` ve `Magnetic` track'ler **hiç farklı değil** (126 aynı, 79'unda magnetic boş) | 205/205, gerçek fark 0 |
| VFR fix referanslarındaki `MEN` (24) ve `AYR` (1) kaynakta **hiç tanımlı değil** | 6 dosyanın hiçbirinde konum/tip yok |

### Kullanıcı onaylı kararlar

- **Uç nokta eşleme:** uzunluk kuralı yok — isim önce DP designator'larında, bulunamazsa navaid NAME'lerinde aranır (çakışma yok, %100 çözülüyor).
- **NAVIGATION TYPE:** `aircraftCapability/AircraftCharacteristic/navigationType`; `CONV→CONV`, `RNAV→PBN`.
- **RNP:** aynı `AircraftCharacteristic` altında `navigationSpecification`; `5→RNAV_5`, `1→RNAV_1`. (Doğrulandı: RNP değerleri yalnızca RNAV satırlarında var, CONV'da hep boş — çakışma yok.)
- **UPPER LIMIT `999` → `UNL`**.
- **Rota kodu:** fetcher güncellenip sayfadan yakalanacak (kullanıcı HTML örneği verdi: `<span class="routeName">UT 54</span>`).
- **VFR rota kimliği:** `Route.name = hi` (kullanıcı, LTFE/NORTH + LTFE/NORTH-SOUTH birleşmesi uyarısını görüp bu seçeneği onayladı) → 97 Route.
- **MEN/AYR:** konumsuz, tipsiz stub Navaid; yalnızca `designator` + açıklayıcı `annotation`.
- **UUID:** hepsi yeniden üretilir — `gml:identifier` = deterministik UUID5 (kaynak türü + anahtar), DHMİ `kid` uuid'si kullanılmaz.
- **gml:id:** okunabilir şema — `DP_ODIRA`, `NAV_IST`, `RS_0001`, `RTE_UA285`, `VRP_SAFET`; aynı adlı VFR noktalarında sıra eki (`VRP_KEMER_2`).
- **MEA:** `minimumEnrouteAltitude/AltitudeIndication/altitude` = lowerLimit değeri + aynı uom; diğer alt alanlar boş.
- **AIXM sürümü:** tam 5.2. Eksik sanılan şema seti bulundu: `D:\Belgeler\Havacılık Kütüphanesi\Charts, Guides, Regulations\Other Documents\Aeronautical Information Exchange Model (AIXM)\Scheme and Data AIXM 5.2\aixm_5_2_0_xsd\` (`AIXM_Features.xsd`, `AIXM_DataTypes.xsd`, `AIXM_AbstractGML_ObjectTypes.xsd`, `message/AIXM_BasicMessage.xsd`, namespace `http://www.aixm.aero/schema/5.2/message`). Yerel XSD doğrulaması yapılabilir.

---

## Adım 1 — `fetch_ats_route_info.py` güncellemesi (küçük)

Kullanıcının verdiği gerçek HTML yapısı:
```html
<span id="labelRouteSegmentInfo">
  <span class="routeName">UT 54</span><br>
  <table><tbody>
    <tr><td class="tooltipHeader">LEVEL :</td><td class="tooltipValue">UPPER</td></tr>
```

- `parse_segment_page()`'e **rota kodu yakalama** eklenir: `soup.find("span", class_="routeName")` → `ROUTE_DESIGNATOR` anahtarıyla info sözlüğüne yazılır (mevcut alan normalizasyonuyla uyumlu).
- Strategy 1'in sınıf regex'i `tooltipHeader`/`tooltipValue` çiftini de kapsayacak şekilde genişletilir (şu an `label` aradığı için eşleşmiyor, Strategy 2'ye düşerek çalışıyor — doğru sonuç veriyor ama kırılgan).
- Rota kodu bulunamazsa `errored-features.log`'a değil, fetcher'ın kendi konsol özetine ve info dosyasındaki eksik alan olarak yansır; XML üretiminde eksikse loglanır.
- Kullanıcı fetcher'ı yeniden çalıştırıp `_info.json` dosyalarını üretmeli (login + CAPTCHA/SMS manuel).

---

## Adım 2 — `LT\generate-aixm-data\` modülü (yeni)

Tek giriş noktası, modüler iç yapı (fetcher ile aynı felsefe).

```
data-sources/LT/
├── lt-route-data-aixm.xml            # ÇIKTI (her çalıştırmada yeniden üretilir)
└── generate-aixm-data/
    ├── generate_aixm.py              # ana script (tek giriş noktası)
    ├── start-generate-aixm.bat
    ├── attribute-override.json       # ayar dosyası
    ├── errored-features.log          # her çalıştırmada sıfırlanır
    ├── DHMI_to_AIXM_Mapping.md       # dokümantasyon çıktısı
    ├── mapping.py                    # tüm DHMİ→AIXM değer/enum eşleme tabloları
    ├── ids.py                        # gml:id + UUID5 üretimi
    ├── logger.py                     # errored-features.log yazıcı
    ├── sources/
    │   ├── ats.py                    # 4 geojson + *_info.json okuma, nokta tekilleştirme
    │   └── vfr.py                    # VFRPOINT/VFRSEGMENT okuma, pic parse
    └── aixm/
        ├── writer.py                 # XSD sırasına uyan element yazıcı yardımcıları
        ├── designated_point.py
        ├── navaid.py
        ├── route_segment.py
        └── route.py
```

Çıktı dosyasının başına yorum satırı: `<!-- Generated by Ibosoft -->`

### XML zarfı (AIXM 5.2)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- Generated by Ibosoft -->
<message:AIXMBasicMessage
    xmlns:message="http://www.aixm.aero/schema/5.2/message"
    xmlns:aixm="http://www.aixm.aero/schema/5.2"
    xmlns:gml="http://www.opengis.net/gml/3.2"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    gml:id="MSG_LT_ROUTE_DATA">
  <message:hasMember> … </message:hasMember>
</message:AIXMBasicMessage>
```

Her feature: `gml:identifier codeSpace="urn:uuid:"` + tek `aixm:timeSlice` → `<X>TimeSlice` içinde `gml:validTime` (TimePeriod, beginPosition = `data.json`'daki AIRAC yürürlük tarihi, endPosition `indeterminatePosition="unknown"`), `aixm:interpretation=BASELINE`, `sequenceNumber=1`, `correctionNumber=0`.

Geometri: `srsName="urn:ogc:def:crs:EPSG::4326"`, `gml:pos` **enlem boylam** sırasında (GeoJSON'daki `[lon, lat]` ters çevrilir).

**Element sırası XSD sequence'ine birebir uyacak** — `writer.py` her feature için sabit sıra listesi tutar; sıra dışı yazım XSD doğrulamasını kırar.

### 2a) ATS noktaları

4 dosyadan Point feature'ları toplanır, `kid` ile tekilleştirilir (678 nokta).

**DesignatedPoint** (`type=DP`, 613 adet) — XSD sırası: `designator, type, name, location, …, annotation, codeICAOCountry, fix`

| DHMİ | AIXM | Not |
|---|---|---|
| `hi` | `designator` | 5 karakter |
| `pic` → `TYPE` | `type` | hep `ICAO` (geçerli enum) |
| geometry coords | `location/aixm:Point/gml:pos` | GeoJSON `[lon,lat]` → `lat lon` |

**Navaid** (65 adet) — XSD sırası: `type, designator, name, …, location, …, annotation, codeICAOCountry`

| DHMİ | AIXM | Not |
|---|---|---|
| `type` (= `pic` TYPE) | `type` | VOR_DME / VORTAC / NDB |
| `pic` → `DESIGNATOR` | `designator` | |
| `hi` (= `pic` NAME) | `name` | ikisi birebir aynı, doğrulandı |
| geometry coords | `location/aixm:ElevatedPoint/gml:pos` | Navaid'de ElevatedPoint kullanılır (Point değil) |

`pic` içindeki `POSITION`/`GML POS` (DMS metin) kullanılmaz — geometry daha hassas. Bu, mapping dokümanında "kullanılmayan kaynak alan" olarak listelenir.

### 2b) ATS rota segmentleri (2670)

`_info.json` dosyalarından okunur (kid → alan sözlüğü). XSD sırasına göre yazılır.

| DHMİ alanı | AIXM hedefi | Dönüşüm |
|---|---|---|
| `LEVEL` | `level` | UPPER/LOWER/BOTH — doğrudan (geçerli enum) |
| `UPPER_LIMIT` | `upperLimit` | `999→UNL`, aksi halde sayı; `uom="FL"` |
| `UPPER_LIMIT_REFERENCE` | `upperLimitReference` | STD — doğrudan |
| `LOWER_LIMIT` | `lowerLimit` | `uom`: referans STD ise `FL`, MSL/SFC ise `FT` |
| `LOWER_LIMIT_REFERENCE` | `lowerLimitReference` | STD/MSL/SFC — doğrudan |
| — | `pathType` | override config → `GRC` |
| `TRUE_TRACK` | `trueTrack` | kaynakta hep boş → yazılmaz |
| `MAGNETIC_TRACK` | `magneticTrack` | 608 kayıtta boş → yazılmaz |
| `REVERSE_TRUE_TRACK` | `reverseTrueTrack` | kaynakta hep boş → yazılmaz |
| `REVERSE_MAGNETIC_TRACK` | `reverseMagneticTrack` | |
| `LENGTH` | `length` | `uom="NM"` |
| `WIDTH_LEFT` / `WIDTH_RIGHT` | `widthLeft` / `widthRight` | kaynakta hep boş → yazılmaz |
| `LOWER_LIMIT` (ikinci kez) | `minimumEnrouteAltitude/AltitudeIndication/altitude` | aynı değer + aynı uom |
| `START_POINT_NAME` | `start/EnRouteSegmentPoint/pointChoice_fixDesignatedPoint` \| `pointChoice_navaidSystem` | `xlink:href="urn:uuid:<UUID>"` |
| `START_POINT_REPORTING_ATC` | `start/EnRouteSegmentPoint/reportingATC` | COMPULSORY/ON_REQUEST — doğrudan |
| `END_POINT_NAME` / `END_POINT_REPORTING_ATC` | `end/…` aynısı | |
| `ROUTE_DESIGNATOR` (yeni) | `routeFormed` | `xlink:href` → ilgili Route |
| `START/END_POINT_COORDINATES` | `curveExtent/aixm:Curve/gml:segments/gml:GeodesicString/gml:posList` | 2 noktalı geodesic |
| `NAVIGATION_TYPE` | `aircraftCapability/AircraftCharacteristic/navigationType` | CONV→CONV, RNAV→PBN |
| `REQUIRED_NAVIGATION_PERFORMANCE` | aynı AircraftCharacteristic → `navigationSpecification` | 5→RNAV_5, 1→RNAV_1, boş→yazılmaz |

Uç nokta çözümü: isim → önce DP indeksi, sonra navaid indeksi. Koordinat, indeksteki nokta koordinatıyla çapraz doğrulanır; uyuşmazlık/çözümsüzlük `errored-features.log`'a yazılır ve segment yine üretilir (uç nokta referansı olmadan).

### 2c) ATS rotaları (453)

Segmentlerin `ROUTE_DESIGNATOR` değerlerinden türetilir. Desen: `^([KUST])?\s*([ABGHJLMNPQRTVWYZ])\s*(\d+)\s*([A-Z])?$` → `designatorPrefix`, `designatorSecondLetter`, `designatorNumber`, `multipleIdentifier`. Desene uymayan varsa loglanır ve dört alan boş bırakılır (ölçümde 453/453 uyuyor).
Override config'den: `type=ATS`, `flightRule=IFR`, `designCriteria=PANS_OPS`.

### 2d) VFR noktaları (263 → DesignatedPoint)

| DHMİ | AIXM |
|---|---|
| `hi` | `name` (designator **boş bırakılır**) |
| — | `type` = override config → `VRP` |
| geometry coords | `location/aixm:Point/gml:pos` |
| `pic` → `Description` | `fix` → `PointReference` |

`Description` çözümü (ölçüm: 125 tek referans, 2 çift referans, 136 açıklamasız):
- Desen `<NAV> R<radyal>/D<mesafe>` (örn. `DAL R270/D22.51`).
- Tek referans → `PointReference` `role=RAD_DME`:
  - `angleReference/AngleUse/theAngle/Angle`: `angle=270`, `angleType=RDL`, `indicationDirection=FROM`, `pointChoice_navaidSystem xlink:href=<navaid>`
  - `distanceReference/Distance`: `distance=22.51 uom="NM"`, `type=DME`, `pointChoice_navaidSystem xlink:href=<navaid>`
- Çift referans (2 nokta: `BIG R200/D30.43 EDR R010/D16.72`, `EDR R291/D33.43 CNK R185/D21.21`) → tek `PointReference`, `role=INTERSECTION`, iki `angleReference` + iki `distanceReference`.
- Açıklaması olmayan 136 nokta → `fix` yazılmaz (0..∞ olduğu için geçerli).
- `MEN`/`AYR` için konumsuz stub Navaid üretilir: yalnızca `designator` + `annotation` ("kaynakta tanımlı değil; VFR fix referansından türetildi"). Ayrıca loglanır.

### 2e) VFR segmentleri (205 → RouteSegment) ve rotaları (97 → Route)

`pic` alanı 9 etiketin tamamını 205/205 taşıyor:

| `pic` etiketi | AIXM |
|---|---|
| `Start Point` | `start/…/pointChoice_fixDesignatedPoint` (isim **+ koordinat** ile VFRPOINT eşleme) |
| `End Point` | `end/…` aynısı |
| `Distance` | `length` `uom="NM"` |
| `Calc. Start` | `trueTrack` (° işareti temizlenir) |
| `Calc End` | `reverseTrueTrack` |
| `Magnetic Start` | `magneticTrack` (79 kayıtta boş → yazılmaz) |
| `Magnetic End` | `reverseMagneticTrack` |
| geometry | `curveExtent` (2 noktalı geodesic) |
| — | `pathType` = override → `GRC` |
| `hi` | ait olduğu Route'un `name` alanı |
| `Route` (`LTFE/SOUTH`) | **kullanılmaz** — kullanıcı `hi` kullanımını onayladı; mapping dokümanında "kullanılmayan alan + sonucu (97 rota, LTFE/NORTH ile LTFE/NORTH-SOUTH birleşiyor)" olarak açıkça belgelenir |
| `Route Segment` | kullanılmaz (belgelenir) |

VFR Route: `name=hi`, override'dan `type=OTHER`, `flightRule=VFR`, `designCriteria=OTHER`. Designator alanları (prefix/letter/number) **yazılmaz** — VFR rotalarının kodu yok.

Aynı isimli farklı konumlu VFRPOINT'ler (KEMER, KILO) için eşleme **isim + koordinat** ile yapılır; yalnızca isimle eşleşme belirsizse loglanır.

### 2f) `attribute-override.json`

```json
{
  "ats": {
    "RouteSegment": { "pathType": "GRC" },
    "Route": { "type": "ATS", "flightRule": "IFR", "designCriteria": "PANS_OPS" }
  },
  "vfr": {
    "DesignatedPoint": { "type": "VRP" },
    "RouteSegment": { "pathType": "GRC" },
    "Route": { "type": "OTHER", "flightRule": "VFR", "designCriteria": "OTHER" }
  }
}
```
Genel mekanizma: `<kaynak grubu>.<feature türü>.<attribute> = değer`. Override edilen değer kaynaktan gelen değerin **yerine** yazılır; ayarda olmayan attribute'lar kaynaktan gelir. Bilinmeyen feature/attribute adı → loglanır, yok sayılır.

### 2g) `errored-features.log`

Her çalıştırmada sıfırlanır (`w` modu). Satır formatı: `SEVERITY | feature türü | kimlik | alan | değer | ihlal`. Loglanan durumlar: çözülemeyen uç nokta, koordinat uyuşmazlığı, desene uymayan rota kodu, tanımsız navaid referansı (MEN/AYR), enum dışı değer, eksik `ROUTE_DESIGNATOR`, geçersiz override anahtarı.

---

## Adım 3 — `DHMI_to_AIXM_Mapping.md` (dokümantasyon çıktısı)

`generate-aixm-data/` içinde. İçerik:
1. Kaynak dosya envanteri ve her birinin hangi AIXM feature'ına beslendiği.
2. Alan bazında tam eşleme tablosu (yukarıdaki tabloların tamamı, kaynak alan → AIXM yolu → dönüşüm).
3. Enum eşleme tabloları ve her birinin gerekçesi (`RNAV→PBN`, `999→UNL`, `5→RNAV_5` vb. — hangisi doğrudan, hangisi yorum içeriyor açıkça işaretlenir).
4. **Kullanılmayan kaynak alanları** listesi ve neden kullanılmadıkları (`ip`, `cip`, `strclr`, `zi`, `t`, `kid`, `cil`, `pic` POSITION, VFR `Route`/`Route Segment`, `sa`/`ea`/`dist` — AIXM karşılığı olmayan çizim/görsel alanlar).
5. Ölçülen kapsam istatistikleri (kaç feature, kaç çözülen/çözülemeyen).
6. Bilinen sınırlamalar: MEN/AYR stub'ları, VFR rota birleşmesi, kaynakta hep boş olan alanlar (trueTrack, widthLeft/Right).

---

## Doğrulama

1. `python generate_aixm.py` çalıştırılır; istisna atmadan tamamlanmalı.
2. Çıktı sayıları beklenenle karşılaştırılır: **613** DesignatedPoint (ATS) + **263** DesignatedPoint (VFR) + **65** Navaid + **2** stub Navaid + **2670** RouteSegment (ATS) + **205** RouteSegment (VFR) + **453** Route (ATS) + **97** Route (VFR).
3. XML, tam 5.2 XSD setine karşı doğrulanır:
   `python -c "from lxml import etree; etree.XMLSchema(etree.parse(r'D:\Belgeler\...\aixm_5_2_0_xsd\message\AIXM_BasicMessage.xsd')).assertValid(etree.parse('lt-route-data-aixm.xml'))"`
   (GML 3.2.1 uzak import'u için internet gerekirse yerel kopya kullanılır.)
4. Tüm `xlink:href` değerlerinin dosya içinde karşılık gelen bir `gml:identifier`'a çözüldüğü programatik olarak kontrol edilir (kırık referans = 0 olmalı, MEN/AYR stub'ları dahil).
5. Bilinen bir örnek uçtan uca elle doğrulanır: `UA 285` segmenti → `ERHAN` (DP) ve `TIRMA` (DP) uç noktaları, `LEVEL=UPPER`, `lowerLimit=285 FL`, `upperLimit=660 FL`; ve `ISTANBUL` uç noktalı bir segmentin VORTAC Navaid'ine bağlandığı görülür.
6. Bir VFR noktası (`SAFET`, `DAL R270/D22.51`) açılıp `fix/PointReference` yapısının doğru navaid'e (`DAL`) `RDL`/`FROM` + `22.51 NM`/`DME` ile bağlandığı doğrulanır.
7. `errored-features.log` incelenir: beklenen tek kalem MEN/AYR stub kaydı olmalı; çözülemeyen uç nokta **0** beklenir (ölçümde 5340/5340 ve 205/205 çözülüyordu).
