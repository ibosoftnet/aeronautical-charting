# EAD-SDO → AIXM 5.2 Eşleme Dokümanı

`generate_aixm.py` tarafından üretilen `../ead-sdo-aixm.xml` dosyasındaki her
alanın kaynağı, dönüşümü ve gerekçesi.

**Hedef şema:** AIXM 5.2
`D:\Belgeler\Havacılık Kütüphanesi\Charts, Guides, Regulations\Other Documents\Aeronautical Information Exchange Model (AIXM)\Scheme and Data AIXM 5.2\aixm_5_2_0_xsd\`

> **Bağlayıcı kural:** Bu dokümandaki hiçbir eşleme varsayıma dayanmaz. Her
> satır ya kaynak değerin AIXM enum'unda birebir bulunmasına, ya XSD'den teyit
> edilmiş bir yapıya, ya da kullanıcı tarafından açıkça onaylanmış bir yoruma
> dayanır. Kaynakta olmayan alanlar "kaynakta yok" olarak işaretlenmiştir;
> hiçbir değer uydurulmamıştır.

---

## 1. Kaynak dosya envanteri

| Kaynak dosya | Kayıt | Beslediği AIXM feature |
|---|---|---|
| `dp-ne.xml`, `dp-nw.xml`, `dp-se.xml` | 49.996 + 91.524 + 10.190 = **151.710** | `DesignatedPoint` |
| `vor.xml` | 3.592 | `VOR` (ekipman) + `Navaid` |
| `dme.xml` | 4.663 | `DME` (ekipman) + `Navaid` (standalone olanlar) |
| `tacan.xml` | 877 | `TACAN` (ekipman) + `Navaid` (standalone olanlar) |
| `ils-loc.xml` | 548 | `Localizer` (ekipman) + `Navaid` |
| `ils-gp.xml` | 522 | `Glidepath` (ekipman) |
| `routes-{upper,non-upper}-{ne,nw,se,sw}.xml` | **93.163** (623'ü tekrar → 92.540 tekil) | `Route` + `RouteSegment` |
| `../../Jeppesen/jeppesen-ndb-index.json` | 3.073 | *(yalnızca referans — bu dosyaya NDB YAZILMAZ)* |

**Üretilen feature sayıları:** 151.710 DesignatedPoint · 6.277 Navaid ·
3.592 VOR · 4.663 DME · 877 TACAN · 548 Localizer · 522 Glidepath ·
14.204 Route · 92.540 RouteSegment = **274.933**

Her ekipman türünün sayısı kaynak dosyasındaki kayıt sayısına **birebir**
eşittir (VOR 3.592, DME 4.663, TACAN 877, Localizer 548, Glidepath 522).

### 1.1 Tekilleştirme — iki durum

AIXM'de her feature tekil bir `gml:identifier` taşımak zorundadır. Kaynakta
aynı gerçek nesnenin birden fazla kez görünebildiği iki durum var:

1. **Bölge sınırını kesen rota segmentleri.** 619 `mid` iki yarımküre raporunda
   birden geçiyor (toplam 623 fazladan kayıt). Doğrulandı: bu kopyalar `level`
   dahil **tüm alanlarda birebir aynı**, yalnızca geldikleri dosya farklı.
   `mid` bazında tekilleştirilir — veri kaybı yok.
2. **Birden fazla Navaid tarafından eşleştirilen ekipman.** Eşleştirme motoru
   (legacy'den birebir port) bir DME/TACAN'ı eşleştirdiğinde başka bir VOR'un
   aynı kaydı eşleştirmesini engellemez; kaynakta aynı `codeId` +
   `OrgCre/txtName` ikilisini taşıyan birden fazla VOR/TACAN kaydı bulunuyor.
   Legacy'de bu düz satırlarda verinin tekrar yazılması demekti (zararsız);
   AIXM'de ekipman **bir kez** yazılır ve onu eşleştiren tüm Navaid'ler aynı
   UUID'ye referans verir. **Eşleştirme kararları değişmez** — yalnızca yazım
   tekilleşir.

---

## 2. Ortak yapı

Her feature: `message:hasMember` → `aixm:<Feature>` (okunabilir `gml:id`) →
`gml:identifier codeSpace="urn:uuid:"` → tek `aixm:timeSlice`.

| Kimlik / alan | Üretim |
|---|---|
| `gml:id` | **`EAD_` kaynak önekiyle** okunabilir: `EAD_DP_<codeId>_<mid>`, `EAD_NAV_<codeId>_<mid>`, `EAD_VOR_…`, `EAD_DME_…`, `EAD_TAC_…`, `EAD_LOC_…`, `EAD_GP_…`, `EAD_RTE_<desig>_<locDesig>`, `EAD_RS_<sıra>`. Çakışmada sıra eki (`_2`). Türetilmiş id'ler (`_TS`, `_TP`, `_EP`, `_P`, `_NC1`, `_C`, `_START`, `_END`, `_AV`, `_TSH`, `_RMK`, `_DSC`) öneki miras alır. Mesaj kökü: `EAD_MSG_SDO` |
| `gml:identifier` | Deterministik UUID5 (sabit namespace + `Ead<Tür>:<mid>`). Aynı girdi → aynı UUID |
| `validTime/beginPosition` | **Kaydın kendi `dtWef` değeri** (`12/06/2025` → `2025-06-12T00:00:00Z`). Kullanıcı kararı: `data.json`'daki `data_effectivity` ÜRETİLEN veri setinin geçerliliğini anlatır, feature'ın yürürlüğüyle ilgisizdir. `dtWef` boşsa `indeterminatePosition="unknown"` yazılır (`gml:validTime` AIXM'de zorunludur) |
| `validTime/endPosition` | Her zaman `indeterminatePosition="unknown"` |
| `interpretation` / `sequenceNumber` / `correctionNumber` | `BASELINE` / `1` / `0` |

**`dtWef` biçimi:** GG/AA/YYYY. Doğrulandı — gün alanında `27`, `30` gibi
değerler geçtiği için sıra AA/GG olamaz.

**Koordinatlar:** EAD `geoLat`/`geoLong` metinleri (`421159.071N`,
`50.2160306N`, `310524N` gibi üç ayrı biçim) legacy `parse_coord` fonksiyonuyla
ondalık dereceye çevrilir; `gml:pos` **enlem boylam** sırasındadır,
`srsName="urn:ogc:def:crs:EPSG::4326"`.

**Element sırası:** AIXM `<sequence>` grupları sıralıdır; tüm yazıcılar alanları
XSD sırasında üretir. Sıra dışı yazım şema doğrulamasını kırar.

**Originator:** AIXM'de provenance/originator alanı **yoktur**. EAD-SDO'da her
kaydın `OrgCre/txtName` değeri farklıdır (tek bir sabit değer kullanılamaz), bu
yüzden `gml:id → originator` eşlemesi ayrı bir yan dosyaya yazılır:
`../ead-sdo-originators.json` (274.933 kayıt).

---

## 3. DesignatedPoint — 151.710 kayıt

XSD sırası: `designator, type, name, location, aimingPoint, airportHeliport,
runwayPoint, annotation, codeICAOCountry, fix`

| EAD | AIXM | Dönüşüm |
|---|---|---|
| `codeId` | `designator` | Doğrudan (büyük harfe normalize) |
| `codeType` | `type` | → §3.1 |
| `txtName` | `name` | Doğrudan |
| `geoLat`, `geoLong` | `location/aixm:Point/gml:pos` | DesignatedPoint'te `Point` (Navaid'deki gibi `ElevatedPoint` değil) |
| `codeDatum` | `annotation` (DESCRIPTION) | → §7 |
| `dtWef` | `timeSlice/validTime/beginPosition` | → §2 |
| `OrgCre/txtName` | → `ead-sdo-originators.json` | AIXM'de alanı yok |
| `mid` | *(kimlik üretiminde)* | UUID5 anahtarı |

### 3.1 `codeType` → AIXM `CodeDesignatedPointType`

AIXM `CodeDesignatedPointType` enum'u: `ICAO`, `COORD`, `CNF`, `TERMINAL`,
`BRG_DIST`, `VRP` (+ `OTHER` deseni). **Kullanıcı onaylı** eşleme:

| EAD | Adet | AIXM | Gerekçe |
|---|---|---|---|
| `ICAO` | 124.566 | `ICAO` | Doğrudan |
| `OTHER` | 16.859 | `OTHER` | EAD'nin kendi catch-all'ı. Kayıtlar yaklaşma/kalkış prosedür noktalarıdır (`001AB` "2.0NM TO RW25", `001DC` "MAPT VOR APCH RWY04 1.0 DME DND"); enum'da karşılığı yok, düz `OTHER` doğru değerdir |
| `ADHP` | 9.367 | `TERMINAL` | Kayıtlar beş alfanümerik karakterli terminal saha noktalarıdır (`15NAT`, `AA408`, `AA415`). XSD'nin `TERMINAL` tanımı birebir budur: "maximum of five alphanumeric characters, unique in the context of the terminal area where it is used" |
| `COORD` | 918 | `COORD` | Doğrudan |

> **Düzeltme geçmişi:** ilk sürümde `ADHP → OTHER:ADHP` ve
> `OTHER → OTHER:EAD_OTHER` yazılmıştı. `ADHP`'nin `TERMINAL` enum tanımına
> birebir uyduğu, `OTHER`'a alt kod eklemenin de bilgi katmadığı görülünce
> düzeltildi. `OTHER:<kod>` sözdizimi geçerlidir (her `Code*Type` bir union'dır:
> sabit enum listesi **veya** `OTHER(:(\w|_){1,58})?` deseni), ama burada
> gereksizdi.

---

## 4. Navaid eşleştirme motoru

Eşleştirme mantığı `Navaids\EAD-SDO\build_navaids_gpkg.py` (1339 satır)
dosyasından **birebir port edilmiştir** (`matching.py`). Karar kuralları AYNEN
korunmuş; değişen tek şey çıktının şekli (düz GeoPackage satırı yerine AIXM
`Navaid` + `NavaidComponent` + `AbstractNavaidEquipment` yapısı).

| Eşleşme | Kural | Legacy satır |
|---|---|---|
| LOC + GP | GP indeksi `(Ahp/codeId, Ase/firCodeId, Ilz/codeId, OrgCre/txtName)` anahtarlı; LOC `(Ahp/codeId, Ase/firCodeId, kendi codeId, OrgCre/txtName)` ile arar, `all([ahp_code_id, originator])` şartı | 369-420, 423-481 |
| LOC + DME | DME'nin `Vor/codeId` alanı **boş** olmalı + `codeId` LOC'unkiyle aynı + `OrgCre/txtName` aynı | 469-481 |
| VOR + TACAN | TACAN'ın `Vor/codeId`'si VOR'un `codeId`'sine eşit + `OrgCre/txtName` aynı. **Ülke (`Org/txtName`) bilerek karşılaştırılmaz** — aynı tesis için VOR ve TACAN farklı ülke etiketi taşıyabiliyor | 622-633 |
| VOR + DME | VOR+TACAN ile aynı şekil; yalnızca **TACAN eşleşmesi yoksa** denenir | 676-686 |
| Öncelik | TACAN, DME'yi yener — bir VOR ya VORTAC ya VOR/DME ya da düz VOR olur | 670-696 |

### 4.1 Ölçülen sonuç

| Grup | Adet | AIXM `Navaid.type` |
|---|---|---|
| LOC + GP + DME | 402 | `ILS_DME` |
| LOC + GP | 120 | `ILS` |
| LOC (eşleşmesiz) | 26 | `LOC` |
| VOR + DME | 2.797 | `VOR_DME` |
| VOR + TACAN | 518 | `VORTAC` |
| VOR (eşleşmesiz) | 277 | `VOR` |
| DME (standalone) | 1.728 | `DME` |
| TACAN (standalone) | 409 | `TACAN` |
| **Toplam Navaid** | **6.277** | |

Hepsi geçerli `CodeNavaidServiceType` değerleridir.

**Port doğrulaması — legacy çıktısıyla karşılaştırma.** Ham XML dosyalarının
legacy dizinindeki (`Navaids\EAD-SDO\`) kopyalarıyla **bayt-bayt aynı** olduğu
teyit edildi. Legacy `navaids.gpkg` katman sayıları ile bu üreticinin grup
sayıları karşılaştırıldığında aradaki tek fark, legacy'nin ek olarak işlediği
**tailored** (elle girilen) kayıtlardır — bu turda kapsam dışı:

| Grup | Legacy gpkg | Tailored payı | XML kaynaklı | Bu üretici |
|---|---|---|---|---|
| `vor_dme` | 2.799 | 2 | 2.797 | **2.797** ✓ |
| `vortac` | 518 | 0 | 518 | **518** ✓ |
| `vor` | 277 | 0 | 277 | **277** ✓ |
| `ils_loc` | 550 | 2 | 548 | **548** ✓ |
| `dme` (standalone) | 1.728 | 0 | 1.728 | **1.728** ✓ |
| `tacan` (standalone) | 409 | 0 | 409 | **409** ✓ |

Yani port edilen motor, legacy ile **birebir aynı gruplama kararlarını**
üretiyor.

> **Eşleşmeyen GP:** son çalıştırmada 522 GP'nin tamamı bir LOC ile eşleşti.
> Eşleşmeyen bir GP çıkarsa kendi `Glidepath` ekipman feature'ı yine yazılır
> (haritalama değeri kaybolmasın diye) ama hiçbir `Navaid`'e bağlanmaz — `GP`
> tek başına geçerli bir `CodeNavaidServiceType` değildir — ve loglanır.

### 4.2 Navaid feature'ı

XSD sırası: `type, designator, name, flightChecked, purpose, signalPerformance,
courseQuality, integrityLevel, touchDownLiftOff, navaidEquipment, location, …`
(**`navaidEquipment`, `location`'dan ÖNCE gelir**)

| EAD (birincil bileşen) | AIXM | Not |
|---|---|---|
| *(eşleştirme sonucu)* | `type` | §4.1 tablosu |
| `codeId` | `designator` | Birincil bileşenin kodu |
| `txtName` | `name` | Birincil bileşenin adı |
| *(her eşleşen bileşen)* | `navaidEquipment/NavaidComponent/theNavaidEquipment` | `xlink:href` → ilgili ekipman feature'ı. Birincil bileşende `providesNavigableLocation=YES` |
| `geoLat`, `geoLong` (birincil) | `location/ElevatedPoint` | VOR grubunda VOR'un, LOC grubunda LOC'un konumu |

`flightChecked`, `purpose`, `signalPerformance`, `courseQuality`,
`integrityLevel`, `codeICAOCountry` — **kaynakta yok**, yazılmaz.

---

## 5. NavaidEquipment alt-türleri

Hepsi ortak `NavaidEquipmentPropertyGroup` sırasını paylaşır: `designator, name,
emissionClass, mobile, magneticVariation, dateMagneticVariation, flightChecked,
location, authority, monitoring, availability, annotation` — ardından alt-türe
özgü alanlar gelir.

### 5.1 Ortak taban

| EAD | AIXM | Dönüşüm |
|---|---|---|
| `codeId` | `designator` | Doğrudan |
| `txtName` | `name` | Doğrudan |
| `codeEm` | `emissionClass` | Doğrudan — kaynak değerleri `A8W`, `A9W` geçerli `CodeRadioEmissionType` üyeleri |
| `valMagVar` | `magneticVariation` | Sayısal normalize (`+15` → `15`) |
| `dateMagVar` | `dateMagneticVariation` | Doğrudan — kaynak zaten 4 haneli yıl (`1965`, `2020`), AIXM `DateYearType` deseniyle (`[1-9][0-9]{3}`) birebir |
| `geoLat`, `geoLong` | `location/ElevatedPoint/gml:pos` | |
| `valElev` + `uomDistVer` | `location/ElevatedPoint/elevation` | `uom` ∈ {FT, M, FL, SM} |
| `valGeoidUndulation` | `location/ElevatedPoint/geoidUndulation` | |
| `txtVerDatum` | `location/ElevatedPoint/verticalDatum` | Serbest metin |
| `valGeoAccuracy` + `uomGeoAccuracy` | `location/ElevatedPoint/horizontalAccuracy` | |
| `codeWorkHr` = `H24` | `availability/NavaidOperationalStatus/timeInterval/Timesheet` | → §5.2 |
| `txtRmk`, `txtRmkWorkHr` | `annotation` (REMARK) | Kaynak notları |
| `codeDatum`, `valElevAccuracy`, `dtCom`, `codeWorkHr` | `annotation` (DESCRIPTION) | → §7 |

`mobile`, `flightChecked`, `authority`, `monitoring` — **kaynakta yok**.

### 5.2 `codeWorkHr` → Timesheet (kullanıcı kararı: annotation + tam yapı)

Kaynak değerleri: `H24` (512), `TIMSH` (7), `HO` (3).

`H24` için tam AIXM çizelge yapısı üretilir:

```xml
<aixm:availability>
  <aixm:NavaidOperationalStatus>
    <aixm:timeInterval>
      <aixm:Timesheet>
        <aixm:timeReference>UTC</aixm:timeReference>
        <aixm:day>ANY</aixm:day>
        <aixm:startTime>00:00</aixm:startTime>
        <aixm:endTime>24:00</aixm:endTime>
      </aixm:Timesheet>
    </aixm:timeInterval>
  </aixm:NavaidOperationalStatus>
</aixm:availability>
```

`operationalStatus` **yazılmaz** — kaynak yalnızca "ne zaman çalıştığını"
söylüyor, "çalışıyor mu"yu söylemiyor; uydurulmaz.

`TIMSH`/`HO` için çizelgeyi üretecek bilgi kaynakta yok — yalnızca annotation'a
yazılır. Tüm değerler (H24 dahil) ayrıca annotation'da da saklanır.

### 5.3 VOR (3.592)

Ortak taban + `type, frequency, zeroBearingDirection, declination`

| EAD | AIXM | Dönüşüm |
|---|---|---|
| `codeType` | `type` | Doğrudan — kaynak `VOR` (2.639), `DVOR` (949), `OTHER` (4); üçü de geçerli `CodeVORType` / union |
| `valFreq` + `uomFreq` | `frequency` | `uomFreq` kaynakta 3.592/3.592 `MHZ` |
| `codeTypeNorth` | `zeroBearingDirection` | Doğrudan — `MAG` (3.555), `TRUE` (35), `OTHER` (2); hepsi geçerli `CodeNorthReferenceType` / union |
| `valDeclination` | `declination` | Sayısal normalize |

### 5.4 DME (4.927)

Ortak taban + `type, channel, displace, tuningFrequencyVHF`

| EAD | AIXM | Dönüşüm |
|---|---|---|
| `codeChannel` | `channel` | Doğrudan (`40X`, `44Y` — `CodeDMEChannelType`) |
| `valGhostFreq` | `tuningFrequencyVHF` `uom="MHZ"` | **Kullanıcı onaylı.** "Ghost frequency", ICAO Annex 10 Tablo A'ya göre DME ile eşleştirilmiş sanal VHF tesisinin frekansıdır — AIXM `tuningFrequencyVHF` tanımıyla birebir aynı |
| *(ghost freq yoksa)* `codeChannel` | `tuningFrequencyVHF` | `frequency-pairing.csv` tablosundan kanal → VHF araması. Legacy `enrich_frequency_fields` (satır 849-1001) ile **aynı yön**; tablo legacy'den birebir kopyalandı |

`type` (NARROW/PRECISION/WIDE), `displace` — **kaynakta yok**.

### 5.5 TACAN (927)

Ortak taban + `channel, declination, tuningFrequencyVHF`

| EAD | AIXM |
|---|---|
| `codeChannel` | `channel` |
| *(kanaldan)* | `tuningFrequencyVHF` — `frequency-pairing.csv` araması (§5.4 ile aynı) |

### 5.6 Localizer (548)

Ortak taban + `frequency, magneticBearing, trueBearing, declination,
widthCourse, backCourseUsable, signalPerformance, courseQuality, integrityLevel`

| EAD | AIXM | Dönüşüm |
|---|---|---|
| `valFreq` + `uomFreq` | `frequency` | |
| `valMagBrg` | `magneticBearing` | 0-360 (`ValBearingType`) |
| `valTrueBrg` | `trueBearing` | 0-360 |
| `valWidCourse` | `widthCourse` | -180…+180 (`ValAngleType`) |
| `codeTypeUseBack` | `backCourseUsable` | `N` → `NO`, `Y` → `YES`, `R` → `RSTR` (AIXM `CodeILSBackCourseType` = YES/NO/RSTR — `R`/`RSTR` birebir "restricted") |

`signalPerformance`, `courseQuality`, `integrityLevel` — **kaynakta yok**.

### 5.7 Glidepath (522)

Ortak taban + `frequency, slope, rdh, signalPerformance, courseQuality,
integrityLevel`

| EAD | AIXM | Dönüşüm |
|---|---|---|
| `valFreq` + `uomFreq` | `frequency` | |
| `valSlope` | `slope` | Sayısal normalize (`003.00` → `3`) |
| `valRdh` + `uomRdh` | `rdh` | `uom` ∈ {FT, M, FL, SM} |

---

## 6. Route ve RouteSegment

### 6.1 Ham kaynakta gerçekten bulunan alanlar

Rota XML'lerinin **tüm külliyatı** (8 dosya, 93.163 kayıt) taranarak doğrulandı
— her `<Record>` yalnızca şu 14 alanı taşıyor:

`mid`, `Rte/txtDesig`, `Rte/txtLocDesig`, `SpnSta/codeId`, `SpnSta/codeType`,
`SpnEnd/codeId`, `SpnEnd/codeType`, `valDistVerUpper`, `uomDistVerUpper`,
`codeDistVerUpper`, `valDistVerLower`, `uomDistVerLower`, `codeDistVerLower`,
`dtWef`, `OrgCre/txtName`

**Kaynakta bulunmayan** AIXM Route/RouteSegment öznitelikleri (yazılmaz,
uydurulmaz): `pathType`, `trueTrack`, `magneticTrack`, `reverseTrueTrack`,
`reverseMagneticTrack`, `length`, `widthLeft`, `widthRight`, `turnDirection`,
`signalGap`, `minimumObstacleClearanceAltitude`, `minimumEnrouteAltitude`,
`minimumCrossingAtEnd(+Reference)`, `maximumCrossingAtEnd(+Reference)`,
`designatorSuffix`, `availability`, `annotation`, `cardinalDirectionLeft/Right`,
`aircraftCapability`, `airspaceClass`, `evaluationArea` — ve Route tarafında
`name`, `type`, `flightRule`, `internationalUse`, `militaryUse`,
`militaryTrainingType`, `userOrganisation`, `designCriteria`.

### 6.2 Route — 14.204 kayıt

Rota kimliği = `txtDesig` + `txtLocDesig` (aynı kod farklı bölgelerde ayrı rota).

XSD sırası: `designatorPrefix, designatorSecondLetter, designatorNumber,
multipleIdentifier, locationDesignator, name, type, flightRule, …`

| EAD | AIXM | Dönüşüm |
|---|---|---|
| `Rte/txtDesig` | `designatorPrefix`, `designatorSecondLetter`, `designatorNumber`, `multipleIdentifier` | Desen `^([KUST])?\s*([ABGHJLMNPQRTVWYZ])\s*(\d+)\s*([A-Z])?$` |
| `Rte/txtLocDesig` | `locationDesignator` | Doğrudan (`EUR`, `NAM`, `LT-LT`…) |
| `Rte/txtDesig` (desene uymayanlar) | `name` | **Kullanıcı kararı** → §6.3 |

### 6.3 Desene uymayan rota kodları

10.249 farklı koddan **244'ü** AIXM designator desenine uymuyor (`AR10`,
`LPC19`, `OTR17`, `ZZ910`, `VFR5`, `ATS18`, `RNPC10`, `BR7`, `NCA24` gibi).

**Kullanıcı kararı:** designator alanları boş bırakılır, **ham kod `name`
alanına yazılır** ve loglanır — kayıt düşürülmez. (LT üreticisi de designator'ı
olmayan VFR rotaları için `name` kullanıyor — tutarlı.)

Son çalıştırmada bu duruma düşen Route feature'ı: **251**
(`desene_uymayan_kod_name_alanina_yazildi`).

### 6.4 RouteSegment — 93.163 kayıt

XSD sırası: `level, upperLimit, upperLimitReference, lowerLimit,
lowerLimitReference, …, start, routeFormed, evaluationArea, curveExtent, end, …`

| EAD | AIXM | Dönüşüm |
|---|---|---|
| *(dosya grubu)* | `level` | `routes-upper-*.xml` → `UPPER`, `routes-non-upper-*.xml` → `LOWER`. **Hesaplanan alan** — kaynakta literal karşılığı yok |
| `valDistVerUpper` + `uomDistVerUpper` | `upperLimit` | `uom` ∈ {FL, FT, M} — hepsi geçerli |
| `codeDistVerUpper` | `upperLimitReference` | → §6.5 |
| `valDistVerLower` + `uomDistVerLower` | `lowerLimit` | |
| `codeDistVerLower` | `lowerLimitReference` | → §6.5 |
| `SpnSta/codeId` + `codeType` | `start/EnRouteSegmentPoint/pointChoice_*` | → §6.6 |
| `SpnEnd/codeId` + `codeType` | `end/…` | Aynı kurallar |
| `Rte/txtDesig` + `txtLocDesig` | `routeFormed` | `xlink:href` → ilgili Route |
| *(çözülen uç nokta koordinatları)* | `curveExtent/Curve/segments/GeodesicString/posList` | **Hesaplanan alan** — kaynakta geometri yok; iki ucu da çözülen segmentlerde 2 noktalı geodesic üretilir |

`start`/`end` içindeki `reportingATC`, `flyOver`, `waypoint`, `radarGuidance`,
`facilityMakeup`, `roleRVSM`, `turnRadius` — **kaynakta yok**.

### 6.5 Dikey referans eşlemesi

Kaynak değerleri AIXM `CodeVerticalReferenceType` (`SFC`, `MSL`, `W84`, `STD`)
ile örtüşmüyor. **Kullanıcı onaylı** eşleme:

| EAD | Adet (upper+lower) | AIXM |
|---|---|---|
| `STD` | 54.110 | `STD` |
| `ALT` | 36.294 | `MSL` |
| `HEI` | 267 | `SFC` |
| `QNH` | 9 | `OTHER:QNH` |
| `OTHER` | 10 | `OTHER` |

### 6.6 Uç nokta çözümlemesi

**Kullanıcı onaylı strateji — segmentin İKİ UCU BİRLİKTE çözülür:**

1. Her uç için ident (+tip) ile **aday listesi** çıkarılır; seçim yapılmaz.
2. İki ucun da adayı varsa, aday çiftleri arasından **segment uzunluğunu en
   küçük yapan** çift seçilir (coğrafi yakınlık).
3. Eşitlik durumunda rotanın originator'ı **ikincil** ölçüt olarak kullanılır.
4. Bir ucun hiç adayı yoksa (dayanak yok), diğer uç yalnızca originator ile
   ayıklanır; ayıklanamazsa çözülmez ve loglanır.
5. Seçilen en iyi çift bile **1000 NM**'yi aşıyorsa eşleşme **kabul edilmez** —
   doğru nokta kaynakta hiç yok demektir, "en az kötü" aday yazmak yanlış
   referans üretir.

> **Neden originator ne zorunlu şart ne de tek başına ayıklama ölçütü:**
> rota kaydının `OrgCre/txtName`'i ROTAYI yayımlayan kurumdur, noktayı
> yayımlayan değil — rotalar sınır aşar. Ölçüldü:
> * originator **zorunlu şart** yapılırsa çözünürlük **%64,6**
> * originator **tek ayıklama ölçütü** olursa **%87,6** — ama coğrafi olarak
>   yanlış adayı seçebiliyordu: 233 segment 2000 NM'den uzun çıkmıştı (en uzunu
>   10.287 NM), örn. `UL210` rotasında Bahamalar'daki `UMIMI`den **Tayvan'daki**
>   `BORDO`ya (kaynakta iki `BORDO` var; rotanın originator'ı
>   `EUROCONTROL NMOC` olduğu için yanlış olanı seçmişti)
> * **coğrafi yakınlık** ile **%91,5** ve 1000 NM üstü segment **sıfır**
>
> Rota segmentleri kısa olduğu için (%98,4'ü < 300 NM) yakınlık çok daha güçlü
> bir sinyaldir.

| Uç nokta `codeType` | Aranan yer | Kural |
|---|---|---|
| `WPT` | Bu dosyadaki `DesignatedPoint`'ler | Önce `type=ICAO` adayları; yoksa diğer DP tipleri |
| `VOR/DME`, `DME/VOR` | `Navaid` (`type=VOR_DME`) | Yazım varyantı normalize edilir |
| `VORTAC`, `TACVOR` | `Navaid` (`type=VORTAC`) | Yazım varyantı normalize edilir |
| `VOR`, `DME`, `TACAN` | `Navaid` (aynı `type`) | |
| `NDB` | **Jeppesen** `jeppesen-ndb-index.json` | Yakınlıktan ÖNCE `txtLocDesig` ICAO bölge kodu (`LT-LT` → `LT`) ile aday daraltılır |

**Ölçülen sonuç (92.540 segment × 2 = 185.080 uç nokta):**

| Sonuç | Adet | Oran |
|---|---|---|
| DesignatedPoint çözüldü | 141.309 | %76,3 |
| Navaid çözüldü | 25.113 | %13,6 |
| NDB çözüldü (Jeppesen) | 2.901 | %1,6 |
| **Toplam çözülen** | **169.323** | **%91,5** |
| Aday bulunamadı (WPT 13.582 · navaid 984 · NDB 56) | 14.622 | %7,9 |
| Belirsiz (yakınlık da ayıramadı) | 577 | %0,3 |
| En iyi çift 1000 NM eşiğini aştı → çözülmedi | 279 | %0,2 |

Bunların **9.936 tanesi yalnızca yakınlık sayesinde** ayıklandı (birden fazla
aday vardı). Önceki stratejide belirsiz kalan 8.356 uç noktanın büyük kısmı
böylece doğru şekilde çözüldü.

Çözülemeyen uç noktalarda `pointChoice_*` referansı yazılmaz (AIXM'de bu alanlar
opsiyoneldir), segment yine üretilir ve durum loglanır.

**Üretilen geometri:** 83.444 segment `curveExtent` aldı; en uzunu **966 NM**,
1000 NM üstü segment **yok**. Antimeridyeni aşan segment sayısı **53** (düzeltme
öncesi 96'ydı; aradaki fark yanlış eşleşmelerden kaynaklanıyordu). Kalanlar
Bering Boğazı, Aleutlar, Pasifik ekvatoru ve bir kutup rotası — 40-587 NM.

---

## 7. Düşürülen / annotation'a taşınan kaynak alanları

**Kullanıcı kararlarına göre:**

| Alan | Karar | Gerekçe |
|---|---|---|
| `valCrc` | **Düşürüldü** | CRC checksum; AIXM'de karşılığı yok, bilgi değeri taşımıyor |
| `codeDatum` (WGE/NAW/U) | `annotation` (DESCRIPTION) | Yatay datum; AIXM'de yalnızca `verticalDatum` alanı var (XSD'de arandı, yatay datum alanı **yok**) — yatay datum `srsName` ile ifade edilir |
| `valElevAccuracy` | `annotation` (DESCRIPTION) | AIXM `ElevatedPoint`'te yalnızca `horizontalAccuracy` var, irtifa doğruluğu alanı yok |
| `dtCom` | `annotation` (DESCRIPTION) | İşletmeye alınma tarihi; AIXM'de karşılığı yok |
| `codeWorkHr` | `annotation` + `Timesheet` | → §5.2 |
| `Org/txtName` (ülke adı) | *(kullanılmıyor)* | Serbest metin ülke **adı** (`ALGERIA`), ICAO Doc 7910 **kodu** değil; `codeICAOCountry`'ye yazmak uydurma olurdu. Ayrıca eşleştirme motorunda bilerek karşılaştırılmıyor (§4) |
| `Ahp/codeId`, `Ahp/codeIcao`, `Rwy/txtDesig`, `Rdn/txtDesig`, `Ase/firCodeId` | *(kullanılmıyor)* | ILS'in bağlı olduğu havaalanı/pist/FIR referansları. AIXM'de karşılıkları `servedAirport` / `runwayDirection` association'larıdır; bu projenin kapsamındaki 5 katman `AirportHeliport`/`RunwayDirection` feature'larını içermediği için hedef feature yok. Eşleştirme motorunda **anahtar olarak kullanılıyor** (§4) |
| `mid` | *(kimlik üretiminde)* | UUID5 anahtarı; ayrı alan olarak aktarılmaz |
| `Vor/codeId` (DME/TACAN) | *(eşleştirmede)* | Motor anahtarı (§4); AIXM'de karşılığı `Navaid` ↔ `NavaidComponent` bağıdır, o da zaten kuruluyor |
| `Vor/geoLat`, `Vor/geoLong` (TACAN) | *(kullanılmıyor)* | Eşleşilen VOR'un konumu; VOR kendi feature'ında zaten yazılıyor |
| `ReportSettings`, `SdoReportResult`, `SdoReportAttributeUid` | *(kullanılmıyor)* | EAD rapor zarfı/meta elemanları; kayıt verisi taşımıyor |

---

## 8. Bilinen sınırlamalar

1. **NDB kaynakta yok.** EAD-SDO'da NDB raporu bulunmuyor; NDB'ler Jeppesen'den
   üretilip ayrı dosyada tutuluyor ve buradan referans veriliyor. 3.040 NDB
   referansının 2.558'i (%84,1) çözülüyor.
2. **`codeICAOCountry` hiçbir feature'da yazılmıyor** — kaynakta ICAO Doc 7910
   ülke kodu yok, yalnızca serbest metin ülke adı var.
3. **Rota segmentlerinin çoğu özniteliği kaynakta yok** (§6.1) — bu segmentler
   yalnızca seviye, dikey limitler ve uç nokta referansları taşıyor.
4. **Uç noktaların %12,5'i çözülemiyor** (§6.6) — bunların bir kısmı ileride
   LT/TRNC gibi ek kaynaklar devreye girdiğinde kapanabilir.
5. **`curveExtent` iki ucu da çözülen segmentlerde üretiliyor**; tek ucu
   çözülemeyen segmentlerde geometri yazılmıyor.

---

## 9. Çıktı dosyaları

| Dosya | İçerik |
|---|---|
| `../ead-sdo-aixm.xml` | AIXM 5.2 çıktısı, 274.933 feature (~461 MB) |
| `../ead-sdo-originators.json` | `gml:id → originator` (274.933 kayıt) — AIXM'de originator alanı olmadığı için |
| `errored-features.log` | `SEVERITY \| FEATURE \| ID \| FIELD \| VALUE \| VIOLATION`. Her çalıştırmada sıfırlanır |

**Son çalıştırma log özeti (15.729 kayıt):**

| İhlal | Adet |
|---|---|
| `uc_nokta_cozulemedi` (aday hiç yok) | 14.622 |
| `birden_fazla_aday_ayiklanamadi` | 577 |
| `en_iyi_cift_esigi_asti_cozulmedi` | 279 |
| `desene_uymayan_kod_name_alanina_yazildi` | 251 |

Tamamı **beklenen** durumlardır (kaynak veri eksikliği/belirsizliği), uygulama
hatası değildir — hiçbiri enum/tip ihlali değildir.

Çalıştırma: `start-generate-aixm.bat` (veya `py generate_aixm.py`).
Doğrulama: `validate.bat` (veya `py validate_aixm.py`) — `lxml` gerektirir;
AIXM şeması GML 3.2.1'i uzaktan import ettiği için ilk derleme internet
gerektirir ve birkaç dakika sürer. Doğrulama akış (streaming) modundadır,
460 MB'lik dosya düşük bellekle işlenir.

**Sıra bağımlılığı:** bu üretici, NDB referansları için
`../../Jeppesen/jeppesen-ndb-index.json` dosyasını okur — önce Jeppesen
üreticisi çalıştırılmalıdır.

---

## 10. Doğrulama sonuçları

| Kontrol | Sonuç |
|---|---|
| AIXM 5.2 XSD (tam dosya, 274.933 feature) | **0 hata** |
| `gml:identifier` tekilliği | 274.933 farklı / 274.933 feature — **0 çakışma** |
| `gml:id` tekilliği | 274.933 farklı — **0 çakışma** |
| `xlink:href` bütünlüğü | 272.379 referansın tamamı çözülüyor — **0 kırık** (2.901'i Jeppesen dosyasına çapraz referans) |
| Ekipman sayıları | Her tür kaynak dosyasındaki kayıt sayısına birebir eşit |
| Eşleştirme motoru | Legacy `navaids.gpkg` ile birebir aynı gruplama (§4.1) |
| Uçtan uca örnek | `EAD_RS_000001` → start `ARA` (VOR/DME Navaid), end `SOTEG` (ICAO DesignatedPoint), `routeFormed` → `UA14/EUR` — kaynak XML ile birebir |
| Segment uzunluğu makullüğü | En uzun segment 966 NM; 1000 NM üstü **yok** (yakınlık ayrıştırması + eşik öncesi 233 segment >2000 NM idi) |
