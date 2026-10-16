# `navaidLabeling_*` alanları

`navaids` ve `navaidComponents` katmanlarındaki **türetilmiş** etiketleme
alanları. Üreten kod: [`gpkg/navaid_labeling.py`](gpkg/navaid_labeling.py).
Eşleştirme tablosu: [`gpkg/frequency-pairing.csv`](gpkg/frequency-pairing.csv).

---

## 1. Neden var

Harita üzerinde bir navaid kutusu çizilirken hangi öğelerin gösterileceği
navaid **tipine** göre değişir: NDB'de kanal yoktur, DME yüksekliği yalnızca
mesafe ekipmanı taşıyan tiplerde anlamlıdır, MLS'te kanal etiketlenir ama
frekans etiketlenmez.

Bu bilgi **AIXM'de yoktur**. AIXM neyin var olduğunu söyler, neyin
etiketleneceğini söylemez. Üstelik iki yapısal engel daha var:

1. **Frekans ve kanal Navaid feature'ında değil, bağlı ekipmanda durur.**
   `NavaidPropertyGroup` = type, designator, name, flightChecked, purpose,
   signalPerformance, courseQuality, integrityLevel, touchDownLiftOff,
   navaidEquipment, location, runwayDirection, servedAirport, availability,
   annotation, codeICAOCountry — **`frequency` de `channel` de yok**. Oysa
   harita etiketi navaid düzeyinde çizilir.
2. **Bir ekipman ya frekans ya kanal taşır, ikisini birden değil.** VOR
   frekans taşır, DME kanal; oysa etiket ikisini yan yana gösterir. Eksik olan
   ICAO eşleştirme tablosundan türetilmelidir.

Bu yüzden modül iki geçişli çalışır: önce `navaidComponents`, sonra `navaids`
(bileşenlerin çözülmüş değerlerini devralır).

Modül ayrıca etiket **metnini** de üretir: ham AIXM enum'unun kartografik
kısaltması (`navaidLabeling_type`, §3b) ve ident'in ITU mors karşılığı
(`navaidLabeling_morseCode`, §5b). İkisi de QGIS ifade dilinde pratik olarak
yazılamayacak işlerdi — biri 20 dallı bir `CASE`, diğeri harf harf alfabe
çevirisi.

`atsStatus_*` ile aynı desen: tablolar yazıldıktan **sonra**,
`schema.finalize`'dan **önce** çalışır (yeni sütunların B-tree index'i orada
kuruluyor). Boru hattındaki adım: `[5] navaidLabeling_* alanlari turetiliyor`.

---

## 2. Sütunlar

Her iki katmanda da aynı 9 sütun. **Katman öneki taşımazlar** —
`annotation*`, `data_*`, `gmlId` ve `atsStatus_*` ile aynı kural.

| Sütun | Tip | Açıklama |
|---|---|---|
| `navaidLabeling_name` | TEXT | Etiket adı |
| `navaidLabeling_ident` | TEXT | Etiket ident'i |
| `navaidLabeling_freq` | REAL | **NDB kHz, diğer her tip MHz** |
| `navaidLabeling_freqUom` | TEXT | `KHZ` \| `MHZ` |
| `navaidLabeling_channel` | TEXT | `40X`, `18Y`, MLS için `500` |
| `navaidLabeling_dmeElev` | REAL | DME bileşeninin konum yüksekliği |
| `navaidLabeling_dmeElevUom` | TEXT | `FT` \| `M` — **çevrilmez**, kaynaktaki birim |
| `navaidLabeling_type` | TEXT | Kartografik tip kısaltması — `VOR DME`, `GP`, `OM`, `L` (bkz. §3b) |
| `navaidLabeling_morseCode` | TEXT | Ident'in ITU mors karşılığı — `IST` → `· ·   · · ·   −` (bkz. §5b) |

### `name` ve `ident` neden bayraksız

`designator` ve `name`, `NavaidPropertyGroup` ve
`NavaidEquipmentPropertyGroup`'ta **ortaktır** — her navaid tipinde ve her
ekipman tipinde tanımlıdır. Geçerlilik bayrağı hep `1` olacağı için anlamsız
olurdu; yalnızca değer sütunları tutulur (kullanıcı kararı).

### Geçerlilik kapıları sütun DEĞİL

Bir alanın hangi tipler için anlamlı olduğu **koda gömülü kapılarla**
belirlenir (`NAVAID_LABELS`, `EQUIPMENT_LABELS`): alan o tip için geçerli
değilse değer hesaplanmaz, sütun NULL kalır.

Bu kapılar bir dönem `navaidLabeling_haveFreq` / `haveChannel` / `haveDmeElev`
adlı üç BOOLEAN sütun olarak da yazılıyordu. **Kaldırıldılar** (kullanıcı
kararı): alan geçerli değilse değer zaten NULL oluyor, ayrı bir bayrak
etiketleme için bilgi katmıyordu.

Kaybedilen tek ayrım "bu tipte etiketlenmez" ile "etiketlenir ama veri yok"
arasındaydı. O bilgi kaybolmadı, yerini değiştirdi: veri eksikliği zaten
`errored-features.csv`'ye ve koşu sayaçlarına yazılıyor (§8). En büyük vaka
DME yüksekliği — 9.189 satır, EAD'nin DME raporunda yükseklik alanı hiç yok.

> Kapılar **kaldırılamaz**, yalnızca sütunları kaldırıldı. Kapılar olmadan
> MLS Azimuth'a kanaldan frekans, NDB'ye eşleştirmeden kanal gibi anlamsız
> değerler sızardı.

---

## 3. Geçerlilik kapıları

**Elle küratörlüdür — XSD'den türetilemez.** Bu bir harita etiketleme
kararıdır, şema kararı değil; ikisi iki yönde de ayrışır:

* `MarkerBeacon` frekans taşır (ICAO sabiti **75 MHz**, üreticide atanır) ama
  kanalı yoktur — frekansı etiketlenir, kanalı etiketlenmez.
* `AzimuthPropertyGroup` **frekans tanımlamaz** (yalnızca `channel` taşır),
  `ElevationPropertyGroup` ikisini de tanımlamaz — buna rağmen her ikisinde de
  frekans **etiketlenir**, çünkü değer MLS kanalından türetilebiliyor (§4b).

### `navaids_type` → hangi alanlar hesaplanır

| Tip | freq | channel | dmeElev |
|---|:---:|:---:|:---:|
| VOR, TACAN, ILS, ILS_DME, VORTAC, LOC, LOC_DME, SDF | 1 | 1 | 0 |
| **DME**, **VOR_DME** | 1 | 1 | **1** |
| **MLS** | **0** | 1 | 0 |
| **MLS_DME** | 1 | 1 | 0 |
| **NDB**, **NDB_DME**, **NDB_MKR** | 1 | **0** | 0 |
| **MKR** | 1 | 0 | 0 |
| **TLS**, **DF** | 0 | 0 | 0 |
| `type` NULL (2 kayıt) | 0 | 0 | 0 |

**Tablo eksiksizdir:** `CodeNavaidServiceType`'ın 18 değerinin **18'i de**
açıkça yazılmıştır. Varsayılana düşen tip yoktur — bu bilinçli: `NDB_DME` ve
`NDB_MKR` bir dönem tabloda hiç yoktu ve sessizce `(0,0,0)`'a düşüyorlardı,
yani `navaidLabeling_type` onları `NDB` diye etiketlerken NDB frekanslarını
gizliyorlardı.

* **`NDB_DME` / `NDB_MKR` birer NDB sayılır** (kullanıcı kararı): NDB frekansı
  etiketlenir, bağlı DME'nin kanalı ve frekansı önemsizdir.
* **`TLS` ve `DF`'te frekans yoktur — şema gereği.** `DirectionFinderPropertyGroup`
  yalnızca `doppler` ve `informationProvision` tanımlar; `TLS` için AIXM'de
  karşılık gelen bir ekipman alt-türü yoktur.
* **MLS'in bütün türlerinde frekans NULL'dur.** `AzimuthPropertyGroup` frekans
  tanımlamaz, `ElevationPropertyGroup` ne frekans ne kanal tanımlar.

### `navaidComponents_equipmentType` → hangi alanlar hesaplanır

| Ekipman | freq | channel | dmeElev | Not |
|---|:---:|:---:|:---:|---|
| VOR, TACAN, Localizer, Glidepath, SDF | 1 | 1 | 0 | |
| **DME** | 1 | 1 | **1** | |
| **NDB** | 1 | **0** | 0 | Kanalı yok, eşleştirme tablosunda da yer almaz |
| **Azimuth** | 1 | 1 | 0 | AIXM'de frekans yok — MLS kanalından türetilir (§4b) |
| **Elevation** | 1 | 1 | 0 | AIXM'de ne kanal ne frekans — kardeş Azimuth'tan (§4b) |
| **MarkerBeacon** | **1** | 0 | 0 | 75 MHz sabiti; kanalı yok |
| DirectionFinder | 0 | 0 | 0 | `DirectionFinderPropertyGroup`: doppler, informationProvision |

---

## 3b. Tip etiketleri (`navaidLabeling_type`)

Ham AIXM enum'u haritada okunmaz: `VOR_DME`, `ILS_DME`, `Glidepath`. Bu sütun
kartografik karşılığı taşır, böylece QGIS tarafında 20 dallı bir `CASE`
ifadesine gerek kalmaz.

Tablolar **elle küratörlüdür** — şema kararı değil, harita kararıdır.

### `navaids_type` → etiket

| AIXM | Etiket | | AIXM | Etiket |
|---|---|---|---|---|
| VOR | `VOR` | | VORTAC | `VORTAC` |
| DME | `DME` | | VOR_DME | `VOR DME` |
| NDB | `NDB` \* | | NDB_DME | `NDB` \* |
| TACAN | `TACAN` | | NDB_MKR | `NDB` \* |
| ILS | `ILS` | | TLS | `TLS` |
| ILS_DME | `ILS DME` | | LOC | `LOC` |
| MLS | `MLS` | | LOC_DME | `LOC DME` |
| MLS_DME | `MLS DME` | | DF | `DF` |
| MKR | konuma göre † | | SDF | `SDF` |

### `navaidComponents_equipmentType` → etiket

Ortak tipler (VOR, DME, NDB, TACAN, SDF) navaid tarafıyla aynı karşılığı alır.
Yalnızca ekipman düzeyinde bulunanlar:

| AIXM | Etiket | | AIXM | Etiket |
|---|---|---|---|---|
| Glidepath | `GP` | | Azimuth | `MLS AZM` |
| Localizer | `LOC` | | Elevation | `MLS ELEV` |
| DirectionFinder | `DF` | | MarkerBeacon | konuma göre † |

### \* Locator kuralı — bütün NDB tiplerinde

NDB'nin `class` alanı `CodeNDBUsageType`'tır: `ENR` / **`L`** / `MAR`.
`class = "L"` ise etiket **`L`** olur (locator), aksi halde `NDB`.

Kural `NDB`, `NDB_DME` ve `NDB_MKR` tiplerinin **hepsinde** geçerlidir.
Ölçüm bunu gerektirdi: `class='L'` olan **673** NDB bileşeninin **673'ü de**
düz `NDB` navaid'ine bağlı ve veride **hiç `NDB_DME` yok** — kuralı yalnızca
`NDB_DME`'ye bağlamak onu hiç çalıştırmazdı.

> **`class` COALESCE edilemez.** `schema.EQUIPMENT_SUBTYPE_FIELDS` içinde iki
> ayrı `class` vardır: `NDB.class` (`ENR`/`L`/`MAR`) ve `MarkerBeacon.class`
> (`FAN`/`LOW_PWR_FAN`/`Z`/`BONES`). Modüldeki `_coalesce()` yardımcısı
> bunları tek değere indirir ve bir marker'ın `class`'ı locator sanılabilirdi;
> bu yüzden locator tespiti `schema.equipment_column("NDB", "class")` ile
> **doğrudan** okunur.

### † Marker konumu

| `markerPosition` | Etiket |
|---|---|
| `INNER` | `IM` |
| `MIDDLE` | `MM` |
| `OUTER` | `OM` |
| `BACKCOURSE` | `BC MKR` |
| boş / `OTHER` / tanınmayan | `MKR` |

Konum `NavaidComponent`'in alanıdır, `MarkerBeacon`'ın değil: aynı fiziksel
marker başka bir ILS'e bağlansa farklı bir konum adı alırdı. Bu yüzden
`navaids` tarafında yalnızca `MKR` tipli navaid bu yolu kullanır — etiketi
bağlı MarkerBeacon bileşeninden gelir.

### `OTHER` ve `OTHER:<x>`

Her `Code*Type` bir birleşimdir: sabit enum **veya** `OTHER(:(\w|_){1,58})?`.

* `OTHER` → `OTHER`
* `OTHER:<x>` → **`<x>` aynen** (kısaltılmaz; sonek kaynağın kendi serbest
  metnidir)
* Tabloda olmayan başka bir değer → alan **NULL** kalır ve
  `tip_eslemesi_yok` olarak loglanır. Uydurma karşılık üretilmez.

---

## 4. Eşleştirme tablosu

`frequency-pairing.csv` — ICAO VHF/UHF frekans-kanal eşleştirmesi, 352 veri
satırı. **Tablodaki tüm frekanslar MHz'dir**; arama yapmadan önce değer MHz'e
çevrilir.

Sütun indeksleri (başlık satırından doğrulandı):

```
0 = DME channel number        1 = VHF frequency MHz
2 = MLS angle frequency MHz   3 = MLS channel number
4 = Interrogation Frequency   5 = DME/N
6 = Initial approach          7 = Final approach
8 = Reply Frequency MHz       9 = Pulse codes
10 = GP Frequency MHz         11 = LOC Sequence Number
```

Modül üç sözlük kurar:

| Sözlük | Sütunlar | Kullanan | Kayıt |
|---|---|---|---:|
| `vhf ↔ dmeChannel` | 1 ↔ 0 | VOR, Localizer, SDF (frekans→kanal); DME, TACAN (kanal→frekans) | 200 |
| `gpFreq → dmeChannel` | **10** → 0 | Glidepath | 40 |
| `mls_to_dme` | **3** → 0 | MLS birleşik kanalı | 200 |
| `mls_to_freq` | **3** → **2** | MLS açı frekansı | 200 |
| `dmeChannel → mlsChannel` | 0 → 3 | Azimuth bileşeni eksik olan MLS_DME | 200 |

MLS sütunları **ters yönde** okunur: yetkili kaynak MLS kanalıdır (`col3`),
DME kanalı (`col0`) ve açı frekansı (`col2`) ondan türetilir.

> Bir dönem `dme_to_mls` (`col0 → col3`) vardı: Azimuth bileşeni eksikken MLS
> kanalını DME'den **uyduruyordu**. İzinsiz bir fallback olduğu için
> kaldırıldı ve **geri gelmedi**. Buradaki yön tersidir ve türetmedir.

### Legacy'deki off-by-one

`data-sources/EAD-SDO/generate-aixm-data/mapping.py:151` içindeki
`load_frequency_pairing`, GP frekansını `parts[11]`'den okuyor ve yorumda
"11 = GP frekansı" diyor. Başlığa göre orası **"LOC Sequence Number"** (1–20
arası sıra numaraları); GP frekansı **index 10**'dadır.

Ölçülen etki: `[11]` ile Glidepath eşleşmesi **0/524**, `[10]` ile **521/524**.

> Hata `generate_aixm.py`'de **etkisizdir**: GP sözlükleri
> `channel_to_vhf, vhf_to_channel, _, _` ile atılıyor. Bu modül düzeltilmiş
> indeksle yazılmıştır; legacy dosyaya dokunulmamıştır.

### `tuningFrequencyVHF` neden kullanılmıyor

DME/TACAN'ın AIXM'de `frequency` alanı yoktur; eşleştirilmiş VHF frekansı
`tuningFrequencyVHF`'te durur ve eşleştirme tablosuyla **5.520 vakanın
5.520'sinde aynı** çıkar. Ancak eşleştirilmemiş kanallarda (60X–69X grubu) EAD
oraya **sorgulama frekansını** yazmış: kanal `63X` → 1087.0, `67X` → 1091.0
MHz. Bunlar VHF seyrüsefer bandı değildir.

Bu yüzden etiket frekansı **yalnızca eşleştirme tablosundan** gelir. Kanalın
eşi yoksa değer NULL kalır — o kanalın gerçekten eşleştirilmiş bir VHF
frekansı yoktur. `tuningFrequencyVHF` kendi sütununda dokunulmadan durur.

---

## 4b. MLS etiketlemesi

MLS üç noktada diğer tiplerden ayrışır: kanalı **birleşik** yazılır, frekansı
AIXM'de **hiç yoktur** (kanaldan türetilir), ve `Elevation` değerlerini
**kardeş bileşenden** alır.

### Birleşik kanal: `18X 500`

MLS kanalı (`CodeMLSChannelType`, `500`–`699`) tek başına yazılmaz; yanına
eşleştirilmiş DME kanalı da konur — **DME kanalı, tek boşluk, MLS kanalı**.

| Kaynak satır | MLS kanalı nereden gelir |
|---|---|
| `Azimuth` | kendi `channel` alanı |
| `MLS` / `MLS_DME` navaid | `Azimuth` bileşeninden |
| `Elevation` | kardeş `Azimuth`'tan (§4b üçüncü geçiş) |

Tabloda eşi bulunamazsa değer **NULL** kalır ve loglanır. Yalnız MLS kanalını
yazmak bir fallback olurdu, yapılmaz. `CodeMLSChannelType`'ın 200 değerinin
200'ü de tabloda eşli olduğu için bu ancak `OTHER:*` gibi enum dışı bir
değerde tetiklenir.

### İki ayrı frekans

Aynı MLS istasyonunun satırlarında **iki farklı frekans** bulunur; ikisi de
doğrudur:

| Satır | Zincir | MLS `500` için |
|---|---|---|
| `Azimuth` | `mls_to_freq[500]` | **5031.0 MHZ** — açı-kılavuz frekansı |
| `Elevation` | kardeş Azimuth'un kanalı → `mls_to_freq` | **5031.0 MHZ** — aynı değer |
| `MLS_DME` navaid | `mls_to_dme[500]` → `channel_to_vhf["18X"]` | **108.10 MHZ** — DME eşinin VHF'i |
| `MLS` navaid | — | NULL (DME'si yok) |

`Azimuth` ve `Elevation` **birebir aynı** değeri alır: MLS'te ikisi aynı RF
kanalında zaman bölmeli yayın yapar, bu yüzden tabloda da tek bir "angle
frequency" sütunu vardır. `MLS_DME`'deki ise pilotun çevirdiği VHF'tir.

`MLS_DME` yolu iki adımlıdır ama **fallback değildir** — her iki adım da aynı
ICAO tablosunda birebir eşleşmedir. VHF eşi yoksa değer NULL kalır ve
`dme_esinin_vhf_frekansi_yok` loglanır; başka bir frekans ikame edilmez.

> **200 MLS kanalının 100'ünde VHF eşi yoktur.** VHF'i olanların DME eşi
> `X`/`Y`, olmayanların `W`/`Z` soneklidir. `W`/`Z` kanalları MLS'e özgü
> genişletmelerdir ve VOR/ILS karşılıkları yoktur — yani `MLS_DME` frekansı
> **tasarım gereği** yaklaşık yarı yarıya dolar.

### Üçüncü geçiş: `Elevation`

`ElevationPropertyGroup` = `angleNominal`, `angleMinimum`, `angleSpan` —
kanal da frekans da yok. İkisi de kardeş `Azimuth`'un kanalından gelir, ama bu
bağ ancak bütün bileşenler okunduktan sonra bilinir.

Bu yüzden `Elevation`, A geçişinde **ertelenir** (`_DEFERRED`) ve
`_resolve_mls_elevation()` adlı ayrı bir geçişte doldurulur. Kardeş `Azimuth`
yoksa kanal ve frekans NULL kalır, `mls_azimuth_bileseni_yok` loglanır.

---

## 5. Birim çevrimi

`UomFrequencyType` enum'unun tamamı desteklenir: **HZ, KHZ, MHZ, GHZ**.
Eşleştirme tablosundan gelen değerler (VHF, GP, MLS açı frekansı) her zaman
**MHz**'dir — MLS açı frekansı 5031.0–5090.7 MHz aralığında, ICAO C-bandı.
Listede olmayan/eksik birim **tahmin edilmez**: loglanır, alan NULL kalır.

Çevrim iki yerde uygulanır:

1. **Eşleştirme öncesi** — aranacak değer MHz'e çevrilir (tablo MHz'dir).
2. **Çıktıda** — `navaidLabeling_freq` hedef birime çevrilir:
   **NDB → kHz, diğer her tip → MHz**. `freqUom` buna göre yazılır.

Çevrim **doğrudan** yapılır, MHz üzerinden gidilmez: NDB'nin `KHZ → KHZ` yolu
böylece birebir kimliktir ve `356 → 0.356 → 355.99999999999994` yuvarlama
zinciri hiç oluşmaz. Arama anahtarları sabit basamaklı dizeye indirgenir
(`_key`), böylece çevrimden gelen kayan nokta gürültüsü eşleşmeyi bozmaz.

`dmeElev` **çevrilmez** — kaynaktaki FT/M korunur ve `dmeElevUom` ile taşınır.

---

## 5b. Mors kodu (`navaidLabeling_morseCode`)

Ident'in mors karşılığı etiketin altında çizilir. QGIS ifade dilinde harf harf
mors çevirisi pratikte yazılamaz, bu yüzden değer burada üretilir.

### Alfabe koda gömülü değildir

Tablo [`gpkg/morse-itu.json`](gpkg/morse-itu.json) veri dosyasındadır —
`frequency-pairing.csv` ile aynı desen. Kaynak **ITU-R M.1677-1**: 26 harf +
`É`, 10 rakam, 14 noktalama işareti, 6 prosign.

Kodlar dosyada ASCII `.` / `-` ile tutulur; görüntü sembollerine çevrim
yükleme sırasında dosyanın `symbols` alanına göre yapılır — böylece sembol
tercihi değişirse tablo değişmez.

| Sembol | Karakter | Kod noktası |
|---|---|---|
| Nokta | `·` | U+00B7 MIDDLE DOT |
| Çizgi | `−` | U+2212 MINUS SIGN |

### Boşluklar standarttan gelir

ITU-R M.1677-1 madde 2.1–2.4, birim = nokta uzunluğu:

| Kural | Birim | Uygulaması |
|---|---:|---|
| Çizgi uzunluğu | 3 | (görsel gösterimde kullanılmaz) |
| Aynı harfin sinyalleri arası | **1** | tek boşluk |
| İki harf arası | **3** | üç boşluk |
| İki kelime arası | **7** | yedi boşluk |

Kelime arası ident'lerde tetiklenmez — ölçüldü, ident'lerin tamamı boşluksuz
A–Z 0–9.

```
IST  →  · ·   · · ·   −
ANK  →  · −   − ·   − · −
X    →  − · · −
```

### Marker beacon istisnası

`MarkerBeacon.auralMorseCode` doluysa ident yerine **o** kullanılır ve
**harf ayrımı konmaz**. Gerekçe: ILS marker'ları ident yayınlamaz, sabit bir
bipleme deseni yayınlar (OM sürekli çizgi, MM nokta-çizgi, IM sürekli nokta).
AIXM deseni de bunu doğruluyor — `([\-\.]*)`, harf ayracı içermiyor.

> **Aural desen kullanıldığında `navaidLabeling_ident` NULL'a çekilir**,
> kaynakta `designator` dolu olsa bile. Harf yayınlamayan bir marker'ın yanına
> ident yazmak yanıltıcı olur (kullanıcı kararı). Bu, `have*` bayrakları
> dışında bir değerin bilinçli olarak bastırıldığı **tek** yerdir; sayacı
> koşu özetinde raporlanır.
>
> **Artık her marker'da geçerli.** Jeppesen üreticisi 77 marker'ın 77'sine de
> konuma özgü `auralMorseCode` yazıyor ve `designator` hiç yazmıyor; ident
> zaten kaynakta da yok. Ölçülen sonuç: MM 43 → `· − · · − ·`, OM 31 → `− −`,
> IM 3 → `· · · · · ·`; hiçbirinde harf ayracı (üç boşluk) yok.

### Çevrilemeyen karakter

Ident'te tabloda bulunmayan bir karakter varsa alan **kısmen yazılmaz**: değer
NULL kalır ve `mors_cevrilemeyen_karakter` olarak loglanır. Yarım mors kodu
yanıltıcı olurdu. (Mevcut veride hiç yok.)

---

## 6. Değer kaynakları

### A geçişi — `navaidComponents` (kendi satırından)

| Alan | Kaynak |
|---|---|
| `ident` | `navaidComponents_designator` |
| `name` | `navaidComponents_name` — **fallback yok** |
| `freq` | VOR/Localizer/Glidepath/NDB/SDF/MarkerBeacon: kendi `frequency`'si. DME/TACAN: `dmeChannel→vhf[channel]`. Azimuth: `mls_to_freq[channel]` |
| `channel` | DME/TACAN: kendi `channel`'ı. **Azimuth: birleşik `18X 500`** (§4b). VOR/Localizer/SDF: `vhf→dmeChannel[freq]`. Glidepath: `gpFreq→dmeChannel[freq]` |
| `dmeElev` | DME'de `locationElevation` + `locationElevationUom` |

> **`name` için ebeveyne fallback yoktur.** Bir bileşenin `name`'i boşsa
> `navaidLabeling_name` NULL kalır; bağlı ILS'in adı devralınmaz. Farklı alanlar
> farklı anlam taşır; izinsiz fallback kurulmaz. Bugün bu yalnızca
> **MarkerBeacon**'ı (77 kayıt) etkiliyor.
>
> **GEÇİCİ — Localizer ve Glidepath artık `name` taşıyor.** Eskiden bu iki tipin
> hiçbirinde `name` yoktu (kaynakta `txtName` geçmiyor). EAD üreteci artık pist
> yönünü `RWY 04R` biçiminde `name` alanına yazıyor, bu yüzden
> `navaidLabeling_name` **550/550 Localizer** ve **524/524 Glidepath** satırında
> dolu. Bu geçici bir çözümdür: `AirportHeliport` / `RunwayDirection`
> feature'ları implemente edilmediği için `runwayDirection` association'ı
> kurulamıyor. O feature'lar eklendiğinde kaldırılacak — ayrıntı
> [`EAD-SDO_Field_Mapping.md` §4.3](data-sources/EAD-SDO/generate-aixm-data/EAD-SDO_Field_Mapping.md).
> Etiket şablonu `name`'e güveniyorsa ILS bileşenlerinde artık pist numarası
> görünecektir.

### B geçişi — `navaids` (bileşenlerin çözülmüş değerlerini devralır)

| Navaid tipi | Frekans bileşeni | Kanal bileşeni |
|---|---|---|
| VOR | VOR | — (VOR frekansından eşleştirme) |
| VOR_DME | VOR | DME |
| VORTAC | VOR | TACAN |
| DME | DME | DME |
| TACAN | TACAN | TACAN |
| ILS / ILS_DME | Localizer | DME; yoksa LOC frekansından eşleştirme |
| LOC / LOC_DME | Localizer | DME; yoksa eşleştirme |
| SDF | SDF | — (eşleştirme) |
| MLS | — (kapı kapalı: DME'si yok) | Azimuth'un MLS kanalından **birleşik** (§4b) |
| MLS_DME | Azimuth'un MLS kanalı → DME eşi → **VHF** (§4b) | aynı, **birleşik** |
| NDB | NDB | — (kapı kapalı: NDB'nin kanalı yok) |

### C geçişi — `Elevation` (kardeş `Azimuth`'tan)

`Elevation`'ın AIXM'de kanalı da frekansı da yoktur; ikisi de kardeş
`Azimuth`'un MLS kanalından türetilir. Kardeş bağı ancak A geçişi bittikten
sonra bilindiği için ayrı bir geçiş gerekir — ayrıntı §4b.

---

`ident` / `name`: `navaids_designator` / `navaids_name` — bileşenden
devralınmaz. `dmeElev` (DME, VOR_DME): bağlı **DME** bileşeninin
`locationElevation`'ı.

Belirlenen bileşen yoksa (ör. 50 VORTAC'ın TACAN'ı yok) frekanstan
eşleştirmeye düşülür; o da olmazsa değer NULL kalır ama **bayrak `1` kalır**.

---

## 7. Ölçülen sonuçlar

### `navaids` (9.357 satır)

| Tip | n | freq dolu | channel dolu | dmeElev dolu |
|---|--:|--:|--:|--:|
| NDB | 3.073 | 3.073 | — | — |
| VOR_DME | 2.800 | 2.799 | 2.799 | 2 |
| DME | 1.728 | 1.725 | 1.728 | — |
| VORTAC | 518 | 518 | 518 | — |
| TACAN | 409 | 395 | 409 | — |
| ILS_DME | 387 | 387 | 387 | — |
| VOR | 277 | 277 | 277 | — |
| ILS | 137 | 137 | 137 | — |
| LOC_DME | 17 | 17 | 17 | — |
| LOC | 9 | 9 | 9 | — |
| (`type` NULL) | 2 | — | — | — |
| **Toplam** | **9.357** | **9.337** | **6.281** | **2** |

### `navaidComponents` (13.362 satır)

| Ekipman | n | freq dolu | channel dolu | dmeElev dolu |
|---|--:|--:|--:|--:|
| DME | 4.667 | 4.657 | 4.662 | 4 |
| VOR | 3.594 | 3.594 | 3.594 | — |
| NDB | 3.073 | 3.073 | — | — |
| TACAN | 877 | 863 | 877 | — |
| Localizer | 550 | 550 | 550 | — |
| Glidepath | 524 | 524 | 520 | — |
| MarkerBeacon | 77 | **77** | — | — |
| **Toplam** | **13.362** | **13.338** | **10.203** | **4** |

`—` işareti kapının kapalı olduğunu gösterir: o alan o tip için hiç
hesaplanmaz. Sayı yazan ama toplamı tutmayan hücreler kapı açık olduğu halde
kaynakta veri bulunmayan satırlardır (§8'de loglanır).

### `navaidLabeling_type` dağılımı

| `navaids` (9.357) | | `navaidComponents` (13.362) | |
|---|--:|---|--:|
| `VOR DME` | 2.800 | `DME` | 4.667 |
| `NDB` | 2.400 | `VOR` | 3.594 |
| `DME` | 1.728 | `NDB` | 2.400 |
| **`L`** (locator) | **673** | `TACAN` | 877 |
| `VORTAC` | 518 | **`L`** (locator) | **673** |
| `TACAN` | 409 | `LOC` | 550 |
| `ILS DME` | 387 | `GP` | 524 |
| `VOR` | 277 | `MM` | 43 |
| `ILS` | 137 | `OM` | 31 |
| `LOC DME` | 17 | `IM` | 3 |
| `LOC` | 9 | | |
| NULL (`type` yok) | 2 | | |

`tip_eslemesi_yok` log kaydı **0** — veride geçen her enum değerinin tablo
karşılığı var. `OTHER` / `OTHER:*` şu an hiç geçmiyor.

### `navaidLabeling_morseCode` dağılımı

Her iki katmanda da **%100 dolu** (9.357 / 9.357 ve 13.362 / 13.362):
ident'lerin tamamı A–Z 0–9, çevrilemeyen karakter yok
(`mors_cevrilemeyen_karakter` = **0**).

Biçim denetimi 13.362 değer üzerinde: `·`, `−` ve boşluk dışında karakter
**yok**; ardışık boşluk uzunlukları yalnızca **1 ve 3** (harf içi / harf
arası). Harf ayracı sayısı her satırda `len(ident) − 1`'e eşit — **sıfır**
uyumsuzluk.

`ident_bastirildi` sayacı **0**: `auralMorseCode` henüz hiçbir marker'da
dolu değil.

### Birim dağılımı

`freqUom` yalnızca iki değer alır ve `KHZ` **tam olarak** NDB satırlarıdır:
`navaids` 3.073 KHZ + 6.264 MHZ, `navaidComponents` 3.073 KHZ + 10.188 MHZ.
NDB olup MHZ yazılmış satır **yoktur**.

Band denetimi (MHZ yazılanlar): VOR 108–117.9, Localizer 108.1–111.95,
DME 108–117.95, TACAN 108–117.9. NDB (KHZ) 198–1730.

Glidepath aralığı **kirlidir**: 109.7–335.0 (523 kayıt) artı yanlış birimden
gelen tek bir 0.3323. Alt uç 109.7, bir GP kaydına yazılmış LOC frekansıdır —
kaynak sorunu, bkz. §9. Sağlıklı GP bandı 328.6–335.4'tür.

---

## 8. Loglama

`haveX=1` olup değeri türetilemeyen **her** satır kaydedilir. `dmeElev`
istisnası: ~9.200 satırı ilgilendirdiği için `errored-features.csv`'yi
şişirmemek adına yalnızca **sayılır** (`log.info_count`), satır yazılmaz.

| İhlal kodu | Adet | Anlamı |
|---|--:|---|
| `dme_yuksekligi_kaynakta_yok` | 9.189 | Yalnızca sayaç — EAD'nin DME raporunda yükseklik alanı hiç yok |
| `frekans_eslestirmesi_bulunamadi` | 19 | Kanal var ama tabloda eşi yok (5 DME + 14 TACAN, 60X–69X grubu) |
| `frekans_icin_kanal_yok` | 5 | DME'nin kanalı da yok, eşleştirmeye girecek girdi hiç yok |
| `kanal_kaynakta_yok` | 5 | Aynı 5 DME — kendi kanal alanı boş |
| `kanal_eslestirmesi_bulunamadi` | 4 | Glidepath frekansının tabloda eşi yok (bkz. §9) |
| `frekans_bileseni_yok` | 1 | VOR_DME'nin VOR bileşeni hiç bağlı değil |
| `mls_kanal_eslestirmesi_bulunamadi` | 0 | MLS kanalının tabloda DME eşi yok (enum dışı değer) |
| `mls_frekans_eslestirmesi_bulunamadi` | 0 | MLS kanalının tabloda açı frekansı yok |
| `mls_azimuth_bileseni_yok` | 0 | `Elevation`'ın kardeş `Azimuth`'u yok — kanal/frekans türetilemez |
| `dme_esinin_vhf_frekansi_yok` | 0 | `MLS_DME`: DME eşi `W`/`Z` sonekli, VHF karşılığı yok |
| `kanal_kaynagi_yok` | 1 | Aynı kayıt — kanal türetecek girdi de yok |

Navaid düzeyinde yalnızca **kaynak bileşenin kendisi eksikse** loglanır;
bileşenden devralınan boşluk (17 DME/TACAN) zaten bileşen düzeyinde
kaydedilmiştir, tekrarlanmaz.

---

## 9. Bilinen kaynak veri sorunları

Aşağıdakiler eşleme hatası **değil**, kaynak verinin kendi sorunlarıdır.
Hepsi loglanır, hiçbiri sessizce düzeltilmez.

| Sorun | Etki |
|---|---|
| EAD'nin ham `dme.xml` raporunda **yükseklik alanı hiç yok** (yalnızca `valGhostFreq`). `valElev` sadece `ils-loc.xml` ve `ils-gp.xml`'de var | `dmeElev` yalnızca 4 DME bileşeninde dolu — dördü de Ibosoft AIS kaynaklı |
| Bir Glidepath kaydı `332.3` değerini **`KHZ`** birimiyle veriyor; değer GP bandında (MHz), birim yanlış yazılmış | Birebir çevrildiği için `0.0003323 MHZ` yazılır, kanal eşleşmesi başarısız olur ve loglanır |
| Üç Glidepath frekansı GP bandı dışında: 109.7 (LOC frekansı), 322.0, 333.1 | Kanal eşleşmesi başarısız, loglanır |
| 5 DME kaydının kanalı yok | Ne frekans ne kanal türetilebilir |
| Bir VOR_DME'ye hiç VOR bileşeni bağlı değil | Frekans ve kanal boş |

---

## 10. QGIS kullanımı

**Etiket ifadesi** — her satır yalnızca değeri varsa çizilir. Bayrak kontrolü
gerekmiyor: alan o tip için geçerli değilse zaten NULL.

```sql
"navaidLabeling_type"
|| if("navaidLabeling_ident"    IS NOT NULL, '\n' || "navaidLabeling_ident", '')
|| if("navaidLabeling_freq"     IS NOT NULL,
      '\n' || format_number("navaidLabeling_freq",
                            if("navaidLabeling_freqUom" = 'KHZ', 0, 2))
           || ' ' || lower("navaidLabeling_freqUom"), '')
|| if("navaidLabeling_channel"  IS NOT NULL, '\n' || "navaidLabeling_channel", '')
|| if("navaidLabeling_dmeElev"  IS NOT NULL,
      '\n' || "navaidLabeling_dmeElev" || ' ' || "navaidLabeling_dmeElevUom", '')
|| if("navaidLabeling_morseCode" IS NOT NULL, '\n' || "navaidLabeling_morseCode", '')
```

> `navaidLabeling_ident` de koşulludur: aural desenli bir marker'da bu alan
> NULL'dur (bkz. §5b) ve etikette yer almamalıdır.

**Sembolleştirme** — `navaidLabeling_type` doğrudan *kategorize* alanı olarak
kullanılabilir; `VOR DME`, `GP`, `OM`, `L` gibi değerler ayrı sembollere
bağlanır.

**Filtreler** (hepsi indekslidir, sanal katman gerekmez):

```sql
-- kanalı etiketlenen navaid'ler
"navaidLabeling_channel" IS NOT NULL

-- frekansı etiketlenmeyenler (kapı kapalı VEYA veri eksik)
"navaidLabeling_freq" IS NULL

-- yalnızca NDB'ler (kHz etiketli)
"navaidLabeling_freqUom" = 'KHZ'

-- locator'lar
"navaidLabeling_type" = 'L'

-- ILS marker'ları (dış / orta / iç)
"navaidLabeling_type" IN ('OM', 'MM', 'IM')
```

---

## 11. İlgili dokümanlar

* [`Common_Builder_Behaviour.md`](Common_Builder_Behaviour.md) — boru hattının
  genel davranışı, 2B adım listesi
* [`AIXM_to_GeoPackage_Schema_Design.md`](AIXM_to_GeoPackage_Schema_Design.md)
  — katman şemalarının tamamı
* [`ATS_Status_Fields.md`](ATS_Status_Fields.md) — aynı desenle türetilen
  `atsStatus_*` alanları
