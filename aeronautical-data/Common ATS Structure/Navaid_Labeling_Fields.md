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

`atsStatus_*` ile aynı desen: tablolar yazıldıktan **sonra**,
`schema.finalize`'dan **önce** çalışır (yeni sütunların B-tree index'i orada
kuruluyor). Boru hattındaki adım: `[5] navaidLabeling_* alanlari turetiliyor`.

---

## 2. Sütunlar

Her iki katmanda da aynı 10 sütun. **Katman öneki taşımazlar** —
`annotation*`, `data_*`, `gmlId` ve `atsStatus_*` ile aynı kural.

| Sütun | Tip | Açıklama |
|---|---|---|
| `navaidLabeling_haveFreq` | BOOLEAN | Frekans bu tip için etiketlenir mi |
| `navaidLabeling_haveChannel` | BOOLEAN | Kanal bu tip için etiketlenir mi |
| `navaidLabeling_haveDmeElev` | BOOLEAN | DME yüksekliği bu tip için etiketlenir mi |
| `navaidLabeling_name` | TEXT | Etiket adı |
| `navaidLabeling_ident` | TEXT | Etiket ident'i |
| `navaidLabeling_freq` | REAL | **NDB kHz, diğer her tip MHz** |
| `navaidLabeling_freqUom` | TEXT | `KHZ` \| `MHZ` |
| `navaidLabeling_channel` | TEXT | `40X`, `18Y`, MLS için `500` |
| `navaidLabeling_dmeElev` | REAL | DME bileşeninin konum yüksekliği |
| `navaidLabeling_dmeElevUom` | TEXT | `FT` \| `M` — **çevrilmez**, kaynaktaki birim |

### `name` ve `ident` neden bayraksız

`designator` ve `name`, `NavaidPropertyGroup` ve
`NavaidEquipmentPropertyGroup`'ta **ortaktır** — her navaid tipinde ve her
ekipman tipinde tanımlıdır. Geçerlilik bayrağı hep `1` olacağı için anlamsız
olurdu; yalnızca değer sütunları tutulur (kullanıcı kararı).

### Bayrakların anlamı: TİP bazlı, kayıt bazlı değil

`have*` sorusu **"bu alan bu TİP için etiketlenir mi"**dir, "bu kayıtta dolu
mu" değil. Alan o tip için geçerliyse **değer boş olsa bile bayrak `1` kalır**
("tanımlı fakat boşsa true" — kullanıcı kararı). Böylece "etiketlenmez" ile
"etiketlenir ama veri yok" ayrımı korunur; QGIS'te ikisi farklı sembolle
gösterilebilir.

En belirgin örnek `haveDmeElev`: 4.528 navaid ve 4.667 DME bileşeni bayrağı
`1` taşır, ama değer yalnızca 2 + 4 satırda doludur (bkz. §7).

---

## 3. Geçerlilik tabloları

**Elle küratörlüdür — XSD'den türetilemez.** Bu bir harita etiketleme
kararıdır, şema kararı değil; ikisi iki yönde de ayrışır:

* `MarkerBeaconPropertyGroup` **frekans tanımlar** (class, frequency,
  axisBearing, auralMorseCode) ve 77 marker'ın **hepsinde doludur**
  (ICAO sabiti 75 MHz) — buna rağmen MKR'de frekans **etiketlenmez**. 75 MHz
  bütün marker'lar için aynı olduğundan haritada bilgi taşımaz.
* `AzimuthPropertyGroup` **frekans tanımlamaz** (channel taşır); MLS'te
  yalnızca kanal etiketlenir.

### `navaids_type` → bayraklar

| Tip | haveFreq | haveChannel | haveDmeElev |
|---|:---:|:---:|:---:|
| VOR, TACAN, ILS, ILS_DME, VORTAC, LOC, LOC_DME, SDF | 1 | 1 | 0 |
| **DME**, **VOR_DME** | 1 | 1 | **1** |
| **MLS**, **MLS_DME** | **0** | 1 | 0 |
| **NDB** | 1 | **0** | 0 |
| MKR, NDB_DME, NDB_MKR, TLS, DF | 0 | 0 | 0 |
| `type` NULL (2 kayıt) | 0 | 0 | 0 |

### `navaidComponents_equipmentType` → bayraklar

| Ekipman | haveFreq | haveChannel | haveDmeElev | Not |
|---|:---:|:---:|:---:|---|
| VOR, TACAN, Localizer, Glidepath, SDF | 1 | 1 | 0 | |
| **DME** | 1 | 1 | **1** | |
| **NDB** | 1 | **0** | 0 | Kanalı yok, eşleştirme tablosunda da yer almaz |
| **Azimuth** | **0** | 1 | 0 | AIXM'de frekans alanı yok |
| **Elevation** | 0 | 0 | 0 | AIXM'de ne kanal ne frekans |
| **MarkerBeacon** | 0 | 0 | 0 | Frekansı dolu (75 MHz sabiti) ama etiketlenmez — bkz. §3 girişi |
| DirectionFinder | 0 | 0 | 0 | `DirectionFinderPropertyGroup`: doppler, informationProvision |

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
| `dmeChannel → mlsChannel` | 0 → 3 | Azimuth bileşeni eksik olan MLS_DME | 200 |

`col2` (MLS angle frequency) **okunmaz** — MLS'te frekans etiketlenmiyor.

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

## 5. Birim çevrimi

`UomFrequencyType` enum'unun tamamı desteklenir: **HZ, KHZ, MHZ, GHZ**.
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

## 6. Değer kaynakları

### A geçişi — `navaidComponents` (kendi satırından)

| Alan | Kaynak |
|---|---|
| `ident` | `navaidComponents_designator` |
| `name` | `navaidComponents_name` — **fallback yok** |
| `freq` | VOR/Localizer/Glidepath/NDB/SDF: kendi `frequency`'si. DME/TACAN: `dmeChannel→vhf[channel]` |
| `channel` | DME/TACAN/Azimuth: kendi `channel`'ı. VOR/Localizer/SDF: `vhf→dmeChannel[freq]`. Glidepath: `gpFreq→dmeChannel[freq]` |
| `dmeElev` | DME'de `locationElevation` + `locationElevationUom` |

> **`name` için ebeveyne fallback yoktur.** Localizer (550), Glidepath (524) ve
> MarkerBeacon (77) kayıtlarının hiçbirinde `name` yoktur; bu satırlarda
> `navaidLabeling_name` NULL kalır, bağlı ILS'in adı devralınmaz. Farklı
> alanlar farklı anlam taşır; izinsiz fallback kurulmaz.

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
| MLS / MLS_DME | — (`haveFreq=0`) | Azimuth; yoksa DME kanalından `col0→col3` |
| NDB | NDB | — (`haveChannel=0`) |

`ident` / `name`: `navaids_designator` / `navaids_name` — bileşenden
devralınmaz. `dmeElev` (DME, VOR_DME): bağlı **DME** bileşeninin
`locationElevation`'ı.

Belirlenen bileşen yoksa (ör. 50 VORTAC'ın TACAN'ı yok) frekanstan
eşleştirmeye düşülür; o da olmazsa değer NULL kalır ama **bayrak `1` kalır**.

---

## 7. Ölçülen sonuçlar

### `navaids` (9.357 satır)

| Tip | n | haveFreq | haveChannel | haveDmeElev | freq dolu | channel dolu | dmeElev dolu |
|---|--:|--:|--:|--:|--:|--:|--:|
| NDB | 3.073 | 3.073 | 0 | 0 | 3.073 | 0 | 0 |
| VOR_DME | 2.800 | 2.800 | 2.800 | 2.800 | 2.799 | 2.799 | 2 |
| DME | 1.728 | 1.728 | 1.728 | 1.728 | 1.725 | 1.728 | 0 |
| VORTAC | 518 | 518 | 518 | 0 | 518 | 518 | 0 |
| TACAN | 409 | 409 | 409 | 0 | 395 | 409 | 0 |
| ILS_DME | 387 | 387 | 387 | 0 | 387 | 387 | 0 |
| VOR | 277 | 277 | 277 | 0 | 277 | 277 | 0 |
| ILS | 137 | 137 | 137 | 0 | 137 | 137 | 0 |
| LOC_DME | 17 | 17 | 17 | 0 | 17 | 17 | 0 |
| LOC | 9 | 9 | 9 | 0 | 9 | 9 | 0 |
| (NULL) | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Toplam** | **9.357** | **9.355** | **6.282** | **4.528** | **9.337** | **6.281** | **2** |

### `navaidComponents` (13.362 satır)

| Ekipman | n | haveFreq | haveChannel | haveDmeElev | freq dolu | channel dolu | dmeElev dolu |
|---|--:|--:|--:|--:|--:|--:|--:|
| DME | 4.667 | 4.667 | 4.667 | 4.667 | 4.657 | 4.662 | 4 |
| VOR | 3.594 | 3.594 | 3.594 | 0 | 3.594 | 3.594 | 0 |
| NDB | 3.073 | 3.073 | 0 | 0 | 3.073 | 0 | 0 |
| TACAN | 877 | 877 | 877 | 0 | 863 | 877 | 0 |
| Localizer | 550 | 550 | 550 | 0 | 550 | 550 | 0 |
| Glidepath | 524 | 524 | 524 | 0 | 524 | 520 | 0 |
| MarkerBeacon | 77 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Toplam** | **13.362** | **13.285** | **10.212** | **4.667** | **13.261** | **10.203** | **4** |

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

**Etiket ifadesi** — tipe göre değişen kutu:

```sql
"navaidLabeling_ident"
|| if("navaidLabeling_haveFreq" AND "navaidLabeling_freq" IS NOT NULL,
      '\n' || format_number("navaidLabeling_freq",
                            if("navaidLabeling_freqUom" = 'KHZ', 0, 2))
           || ' ' || lower("navaidLabeling_freqUom"), '')
|| if("navaidLabeling_haveChannel" AND "navaidLabeling_channel" IS NOT NULL,
      '\n' || "navaidLabeling_channel", '')
|| if("navaidLabeling_haveDmeElev" AND "navaidLabeling_dmeElev" IS NOT NULL,
      '\n' || "navaidLabeling_dmeElev" || ' ' || "navaidLabeling_dmeElevUom", '')
```

**Filtreler** (hepsi indekslidir, sanal katman gerekmez):

```sql
-- kanal etiketlenen navaid'ler
"navaidLabeling_haveChannel" = 1

-- etiketlenmesi gerekip verisi eksik olanlar (veri kalitesi taraması)
"navaidLabeling_haveFreq" = 1 AND "navaidLabeling_freq" IS NULL

-- yalnızca NDB'ler (kHz etiketli)
"navaidLabeling_freqUom" = 'KHZ'
```

---

## 11. İlgili dokümanlar

* [`Common_Builder_Behaviour.md`](Common_Builder_Behaviour.md) — boru hattının
  genel davranışı, 2B adım listesi
* [`AIXM_to_GeoPackage_Schema_Design.md`](AIXM_to_GeoPackage_Schema_Design.md)
  — katman şemalarının tamamı
* [`ATS_Status_Fields.md`](ATS_Status_Fields.md) — aynı desenle türetilen
  `atsStatus_*` alanları
