# Jeppesen (Navigraph) NDB + Marker Beacon → AIXM 5.2 Eşleme Dokümanı

`generate_aixm.py` tarafından üretilen `../jeppesen-ndb-aixm.xml` dosyasındaki
her alanın kaynağı, dönüşümü ve gerekçesi.

**Hedef şema:** AIXM 5.2
`D:\Belgeler\Havacılık Kütüphanesi\Charts, Guides, Regulations\Other Documents\Aeronautical Information Exchange Model (AIXM)\Scheme and Data AIXM 5.2\aixm_5_2_0_xsd\`

**Doğrulama durumu:** üretilen XML (6.146 feature) bu şema setine karşı
**geçerli — 0 hata**. `errored-features.log` boş (0 kayıt).

---

## 1. Bu kaynak neden var

EAD-SDO SDO raporları arasında **NDB raporu bulunmuyor** — `raw-data/` altında
`ndb.xml` yok. Buna karşılık EAD rota kayıtları **3.040 kez** NDB'ye referans
veriyor (500 farklı ident). Bu boşluğu kapatmak için NDB'ler ayrı bir kaynaktan
(Jeppesen/Navigraph veritabanı) üretilir.

**Kullanıcı kararı:** EAD-SDO üreticisi kendi AIXM dosyasına NDB **yazmaz**,
yalnızca buradaki NDB'lere `xlink:href` ile referans verir.

| Girdi | İçerik |
|---|---|
| `..\..\..\..\Jeppesen Data\jeppesen.sqlite` → `ndb` tablosu | 3.073 kayıt, 1.648 farklı ident |
| `..\..\..\..\Jeppesen Data\data.json` | Provenance (`data_provider`, `data_originator`, `data_effectivity`) |

Veritabanı meta bilgisi: `data_source = NAVIGRAPH`, `airac_cycle = 2608`.

> **Provenance tek yerde yönetilir.** `../data.json` **elle tutulan bir dosya
> değildir** — her çalıştırmada kaynağın yanındaki `Jeppesen Data\data.json`'dan
> birebir kopyalanır. Sağlayıcı/geçerlilik bilgisini değiştirmek için kaynak
> dosyayı düzenleyip script'i yeniden çalıştırmak yeterlidir.

---

## 2. Üretilen feature yapısı

AIXM'de `Navaid` (servis) ile onun fiziksel bileşeni (`AbstractNavaidEquipment`)
ayrı feature'lardır ve aralarında `navaidEquipment` → `NavaidComponent` →
`theNavaidEquipment` zinciriyle bağ kurulur. Her NDB kaydı için **iki** feature
üretilir:

```
Navaid (type=NDB, kendi location'ı)          ← rota uç noktaları BUNA referans verir
  └─ navaidEquipment → NavaidComponent
        ├─ providesNavigableLocation = YES
        └─ theNavaidEquipment ──xlink──► NDB (kendi location'ı + frekansı)
```

**Üretilen feature sayısı:** 3.073 `Navaid` + 3.073 `NDB` = **6.146**

---

## 3. Ortak yapı

Her feature: `message:hasMember` → `aixm:<Feature>` (okunabilir `gml:id`) →
`gml:identifier codeSpace="urn:uuid:"` → tek `aixm:timeSlice`.

| Kimlik | Üretim |
|---|---|
| `gml:id` | **`JEPP_` kaynak önekiyle**: `JEPP_NAV_NDB_<ident>_<region>` ve `JEPP_NDBEQ_<ident>_<region>`; çakışmada sıra eki (`_2`). Türetilmiş id'ler (`_TS`, `_TP`, `_EP`, `_NC`, `_NOTE`) öneki miras alır. Mesaj kökü: `JEPP_MSG_NDB` |
| `gml:identifier` | Deterministik UUID5 (sabit namespace + `JeppesenNdbNavaid:<ident>:<region>:<ndb_id>`). Aynı girdi → aynı UUID |
| `validTime/beginPosition` | **Boş** — `indeterminatePosition="unknown"`. Jeppesen kayıtlarında feature başına yürürlük tarihi **yoktur**; `data.json`'daki AIRAC effectivity **veri setinin** geçerliliğidir, feature'ın kendi yürürlüğü değil (EAD'de her kaydın kendi `dtWef`'i var, burada karşılığı yok). O tarihi buraya yazmak uydurma bir yürürlük iddiası olurdu — kullanıcı kararı. `endPosition` de aynı şekilde belirsizdir |
| `interpretation` / `sequenceNumber` / `correctionNumber` | `BASELINE` / `1` / `0` |

**Koordinatlar:** sqlite `laty`/`lonx` → `gml:pos` **enlem boylam** sırasında,
`srsName="urn:ogc:def:crs:EPSG::4326"`.

---

## 4. Navaid (3.073 kayıt)

XSD sırası: `type, designator, name, flightChecked, purpose, signalPerformance,
courseQuality, integrityLevel, touchDownLiftOff, navaidEquipment, location, …`

| Jeppesen | AIXM | Dönüşüm |
|---|---|---|
| — | `type` | Sabit `NDB` (geçerli `CodeNavaidServiceType`) |
| `ident` | `designator` | Doğrudan |
| `name` | `name` | Doğrudan |
| — | `navaidEquipment/NavaidComponent/theNavaidEquipment` | `xlink:href` → aynı kaydın NDB ekipman feature'ı; `providesNavigableLocation=YES` |
| `laty`, `lonx` | `location/ElevatedPoint/gml:pos` | `[lat lon]` sırası |

---

## 5. NDB (ekipman, 3.073 kayıt)

XSD sırası: `NavaidEquipmentPropertyGroup` (designator, name, emissionClass,
mobile, magneticVariation, dateMagneticVariation, flightChecked, location,
authority, monitoring, availability, annotation) → `frequency, class, emissionBand`

| Jeppesen | AIXM | Dönüşüm / gerekçe |
|---|---|---|
| `ident` | `designator` | Doğrudan |
| `name` | `name` | Doğrudan |
| `mag_var` | `magneticVariation` | **Doğrudan, dönüşüm yok.** İşaret konvansiyonu gerçek deklinasyon değerleriyle doğrulandı: Ottawa `-12.5` (gerçek 12.5°W), Moskova `+11.5` (gerçek 11.5°E), Alaska `+15.2` (gerçek ~15°E) → kaynak **pozitif = Doğu** kullanıyor, AIXM `ValMagneticVariationType` (-180…+180, pozitif = Doğu) ile birebir aynı |
| `laty`, `lonx` | `location/ElevatedPoint/gml:pos` | `[lat lon]` sırası |
| `frequency` | `frequency` `uom="KHZ"` | Kaynak 100 Hz biriminde saklıyor: `32000 → 320 kHz`. Doğrulandı: değer aralığı 19800–173000 → 198–1730 kHz, ICAO NDB bandıyla (190–1750 kHz) birebir örtüşüyor |
| `type` = `CP` | `class` = `L` | **Kullanıcı onaylı.** CP (Compass Locator) ile AIXM `L` (Locator) birebir aynı kavram |
| `type` = `H` / `MH` | *(yazılmaz)* | **Kullanıcı kararı.** Bunlar ARINC **güç** sınıflarıdır; AIXM `CodeNDBUsageType` (`ENR`/`L`/`MAR`) ise **kullanım** sınıfıdır — farklı kavramlar, uydurma eşleme yapılmaz. Ham değer `annotation/Note` içinde saklanır (veri kaybı yok) |
| `type` = boş (1.149 kayıt) | *(yazılmaz)* | Kaynakta yok |

### Kaynak `type` dağılımı

| Değer | Adet | AIXM `class` |
|---|---|---|
| boş | 1.149 | — |
| `MH` | 1.098 | — (annotation'a) |
| `CP` | 673 | `L` |
| `H` | 153 | — (annotation'a) |

---

## 6. Marker Beacon (`marker` tablosu, 913 kayıt)

### 6.1 Neden AIXM dosyasına yazılmaz

Bir marker beacon **tek başına anlamlı değildir**; ilişkili olduğu LOC/ILS
navaid'inin `navaidComponent`'i olarak yer almalıdır. Hangi LOC/ILS'e
bağlanacağı ancak **birleşik** veride bilinebilir — marker Jeppesen'den, hedef
navaid EAD-SDO'dan gelir.

Bu yüzden bu üretici marker'ı `jeppesen-ndb-aixm.xml`'e **yazmaz**; yalnızca
kimlikleriyle birlikte `../jeppesen-marker.json` yan dosyasına döker.
Eşleştirme ve AIXM üretimi common builder'daki `merge/marker_beacon.py`
modülünde yapılır (config: `special_sources` → `marker_beacon_matching: true`).

Kimlikler (`JEPP_MKR_<ident>_<region>_<position>` ve sabit namespace'li UUID5)
**burada** atanır — `JEPP_` ad alanı bu üreticinin sorumluluğudur, NDB ile aynı
desen.

### 6.2 Alan eşlemeleri

| Jeppesen `marker` | AIXM | Gerekçe |
|---|---|---|
| `type` | **`NavaidComponent.markerPosition`** | `CodePositionInILSType` enum'u tam olarak `OUTER`/`MIDDLE`/`INNER`/`BACKCOURSE` — kaynak değerleriyle **birebir**. Eşlemeye gerek yok, doğrulama yeterli. **`MarkerBeacon.class` DEĞİL**: o enum `FAN`/`LOW_PWR_FAN`/`Z`/`BONES`, yani enroute marker sinyal biçimleri |
| `heading` | **`MarkerBeacon.axisBearing`** | XSD: *"The true bearing of the minor axis of the marker beacon"*. Değerin **true** olduğu veriden doğrulandı: `\|mag_var\|>8` olan 3.000 ILS'te pist adına göre true sapması 3,73°, manyetik sapması 13,46° |
| `altitude` | `location/ElevatedPoint/elevation` uom=`FT` | Birim doğrulandı: Antalya 159–174 (saha 177 ft), Denizli Çardak 2774 (2795 ft), Diyarbakır 2176 (2251 ft). 913 kaydın hiçbirinde boş yok |
| `laty` / `lonx` | `location/ElevatedPoint/gml:pos` | AIXM/EPSG:4326 sırası: enlem boylam |
| `ident` | `MarkerBeacon.designator` + eşleştirme anahtarı | EAD'de Localizer/Glidepath ekipmanları da ILS ident'ini taşıyor — tutarlı |
| `region` | **yazılmaz** | Hedef LOC/ILS'te karşılığı yok (`codeICAOCountry` 550 kaydın 548'inde boş). Ebeveyn ILS zaten konumu/devleti belirliyor |
| `marker_id`, `file_id` | yazılmaz | UUID türetme anahtarı (`ndb_id` ile aynı desen) |
| **(kaynakta yok)** | **`MarkerBeacon.frequency` = `75` uom=`MHZ`** | ICAO Annex 10 Cilt I: **bütün** marker beacon'lar 75 MHz'de çalışır. Kaynaktan gelmez, üreticide sabit atanır (`MARKER_FREQUENCY_MHZ`) — kullanıcı kararı |

> **Bu alan önce boş bırakılmıştı.** İlk uygulamada "ICAO standardını yazmak
> varsayım olur" gerekçesiyle atlanmıştı; kullanıcı kararıyla sabit olarak
> yazılıyor. Standartla sabitlenmiş tek değer budur — `class` ve
> `auralMorseCode` hâlâ boş, çünkü onların standart bir karşılığı yok.

**Kaynakta bulunmayan AIXM alanları** (uydurulmaz):

| Alan | Neden boş |
|---|---|
| `MarkerBeacon.class` | Kaynakta karşılığı yok. `type` bu alana ait değil (yukarıya bakın) |
| `auralMorseCode` | Kaynakta yok (nokta/çizgi deseni) |

### 6.3 Eşleştirme sonucu

913 marker'ın **77'si** birleşik veride bir LOC/ILS ile eşleşiyor; kalan 836
yazılmaz ve `errored-features.csv`'ye `marker_ebeveyn_loc_ils_bulunamadi`
olarak loglanır (kullanıcı kararı — ayrı `MKR` navaid üretilmez).

Düşük oranın nedeni **coğrafi kapsam**: EAD-SDO'nun ILS raporunda ABD hiç yok
(FAA kaynaklı LOC/ILS = 0), Jeppesen marker verisi ise ağırlıklı ABD
(eşleşemeyenlerin 380'i K3–K7 bölgeleri). Türkiye'nin 7 marker'ının **7'si de**
eşleşiyor. Eşik kısıt değil: 15/25/40 NM → sonuç hep 77.

Ayrıntı: `merge/marker_beacon.py` ve `Common_Builder_Behaviour.md`.

## 7. Kullanılmayan / düşürülen kaynak alanları

| Alan | Neden |
|---|---|
| `range` (1.924 kayıtta dolu) | **Kullanıcı kararı: düşürülür.** AIXM 5.2'de `NDB` ve `NavaidEquipment` şemalarında kapsama mesafesi alanı **yok** (XSD'den teyit edildi: NDB'de yalnızca `frequency`, `class`, `emissionBand` var) |
| `region` | ICAO Doc 7910 ülke kodu **değil**, Navigraph'ın kendi bölge kodudur (`K3`, `K5`, `K7` gibi ABD alt-bölgeleri içerir). Bu yüzden `codeICAOCountry`'ye yazılmaz — uydurma eşleme yapılmaz. Bunun yerine `jeppesen-ndb-index.json` yan dosyasına aktarılır ve EAD-SDO üreticisinin belirsizlik ayıklamasında kullanılır |
| `altitude` | Kaynakta **tümüyle boş** (3.073 kaydın hiçbirinde değer yok) |
| `airport_ident`, `airport_id` | Kaynakta **tümüyle boş** |
| `ndb_id`, `file_id` | Kaynak içi anahtarlar; UUID'ler bunlardan deterministik üretilir ama alan olarak aktarılmaz |
| `emissionBand` (AIXM alanı) | Kaynakta karşılığı yok — yazılmaz |
| `codeICAOCountry` (AIXM alanı) | Kaynakta ICAO Doc 7910 kodu yok (yukarıdaki `region` notu) |

---

## 8. Çıktı dosyaları

| Dosya | İçerik |
|---|---|
| `../jeppesen-ndb-aixm.xml` | AIXM 5.2 çıktısı — **yalnızca NDB** (marker buraya girmez) |
| `../jeppesen-ndb-index.json` | `designator`, `region`, `navaid_uuid`, `equipment_uuid`, `lat`, `lon` — EAD-SDO üreticisinin NDB referans çözümlemesi için |
| `../jeppesen-marker.json` | Marker beacon yan dosyası (913 kayıt) — `ident`, `region`, `markerPosition`, `axisBearing`, `elevation`, `elevationUom`, `lat`, `lon`, `equipment_gml_id`, `equipment_uuid`. **AIXM dosyasından bağımsızdır**; common builder'ın marker modülü okur (§6) |
| `../data.json` | `Jeppesen Data\data.json`'ın birebir kopyası — **çıktıdır, elle düzenlenmez** |
| `errored-features.log` | `SEVERITY \| FEATURE \| ID \| FIELD \| VALUE \| VIOLATION`. Her çalıştırmada sıfırlanır |

Çalıştırma: `start-generate-aixm.bat` (veya `py generate_aixm.py`).
Doğrulama: `validate.bat` (veya `py validate_aixm.py`) — `lxml` gerektirir;
AIXM şeması GML 3.2.1'i uzaktan import ettiği için ilk derleme internet
gerektirir ve birkaç dakika sürer.

**Son çalıştırma:** `ndb` 3.073 kayıt okundu, 0 atlandı → 6.146 feature; `marker` 913 kayıt okundu, 0 atlandı → yan dosya. `errored-features.log` **0 kayıt**.

---

## 9. EAD-SDO tarafındaki referans çözümlemesi

EAD rota kayıtlarındaki `SpnSta`/`SpnEnd` `codeType=NDB` uç noktaları buradaki
`Navaid` feature'larına `xlink:href="urn:uuid:…"` ile bağlanır.

**Kullanıcı onaylı strateji:** ident ile ara → tek aday varsa al → birden fazla
aday varsa rotanın `txtLocDesig` alanındaki ICAO bölge kodu (`LT-LT` → `LT`) ile
ayıkla → hâlâ belirsizse **çözme ve logla** (yanlış eşleşme üretme).

Ölçülen sonuç (3.040 NDB referansı):

| Sonuç | Adet | Oran |
|---|---|---|
| Çözüldü | 2.546 | %84,1 |
| Belirsiz (birden fazla aday, bölge ayıklaması yetmedi) | 420 | %13,9 |
| Jeppesen'de hiç yok | 56 | %1,9 |

*(Ölçüm, EAD tarafında tekilleştirilmiş 92.540 segment üzerinden; tekilleştirme
öncesi ham 93.163 segmentte sırasıyla 2.558 / 423 / 59.)*
