# `navaidSymbology_*` alanları

`navaids` ve `navaidComponents` katmanlarındaki **türetilmiş** sembol
alanları. Üreten kod: [`gpkg/navaid_symbology.py`](gpkg/navaid_symbology.py).

---

## 1. Neden ayrı bir aile

`navaidLabeling_*` etiket **metnini** üretir — ne yazılacağını. Bu aile ise
sembolün **nasıl çizileceğini** besler. İki farklı soru olduğu için önekleri
de ayrıdır ve kodları farklı modüllerde durur.

Ortak yanları: ikisi de AIXM'de karşılığı olmayan türetilmiş alanlardır,
ikisi de katman öneki taşımaz, ikisi de `schema.finalize`'dan önce çalışır
(sütun index'leri orada kuruluyor).

| Adım | Alan ailesi | Katman |
|---|---|---|
| `[5]` | `navaidLabeling_*` | `navaids`, `navaidComponents` |
| `[6]` | **`navaidSymbology_*`** | `declination`: ikisi de; `GPAssociatedLOCTrueBrg`: yalnızca `navaidComponents` |

---

## 2. Sütunlar

| Sütun | Tip | Katman | Geçerli olduğu tür |
|---|---|---|---|
| `navaidSymbology_declination` | REAL | `navaids`, `navaidComponents` | `navaids`: `VOR`/`VOR_DME`/`TACAN`/`VORTAC`; `navaidComponents`: `VOR`/`TACAN` |
| `navaidSymbology_GPAssociatedLOCTrueBrg` | REAL | `navaidComponents` | yalnızca `Glidepath` |

---

## 3. `declination`

### Neden gerekli

Harita sembolünde bir VOR/TACAN istasyonu **pusula gülü** olarak çizilir ve bu
gülün kuzey referansı istasyonun kendi beyan ettiği manyetik sapmaya
(`declination`) göre döndürülmelidir. Değer AIXM'de zaten `VORPropertyGroup`
ve `TACANPropertyGroup`'ta vardır (`ValMagneticVariationType`, -180/+180°);
yeni bir hesap değil, doğrudan bir **devir**dir — ama iki katmana da
taşınması ve navaid düzeyinde hangi bileşenden geleceğinin (`VOR_DME`,
`VORTAC` gibi bileşik tiplerde) belirlenmesi gerekir.

### Nasıl bulunur

* **`navaidComponents`** — birebir kopya: satır `VOR` ise
  `navaidComponents_VOR_declination`, `TACAN` ise
  `navaidComponents_TACAN_declination`. Başka hiçbir alt-türe (`Localizer`
  dahil — AIXM'de onun da `declination`'ı var ama pusula gülü kapsamında
  DEĞİL, kullanıcı kararı) dokunulmaz.
* **`navaids`** — yalnızca `VOR`, `VOR_DME`, `TACAN`, `VORTAC` türlerinde
  doldurulur (kullanıcı kararı); kaynak bileşen türe göre değişir:

  | `navaids_type` | Kaynak bileşen |
  |---|---|
  | `VOR` | `VOR` |
  | `VOR_DME` | `VOR` — `DME`'nin AIXM'de `declination` alanı yok |
  | `TACAN` | `TACAN` |
  | `VORTAC` | `VOR` **varsa** o, yoksa `TACAN` (kullanıcı kararı, 2026-08-31) |

  `VORTAC`, AIXM'de birbirinden bağımsız bir `VOR` bileşeni **ve** bir
  `TACAN` bileşeni ile modellenir (iki ayrı `navaidComponents` satırı).
  İkisinin de kendi `declination`'ı raporlanabildiği için sıra gerekiyordu;
  bugünkü veride TACAN bileşeninin `declination`'ı hiç dolu değil
  (0/13.362), bu yüzden kural şu an fiilen her zaman VOR'a düşüyor — ama
  kural gelecekteki veri için de geçerli kalsın diye VOR öncelikli yazıldı.

### Ölçülen doluluk (son koşu)

| | Adet |
|---|---:|
| `navaidComponents` (`VOR`+`TACAN` satırı) | 3.594 + 877 = 4.471 |
| Kaynakta `declination` dolu → **`navaidComponents` sütunu dolu** | **86** (hepsi `VOR`; `TACAN`'da 0) |
| `navaids` (`VOR`/`VOR_DME`/`TACAN`/`VORTAC`) | 277+2.800+409+518 = 4.004 |
| **sütunu dolu** | **86** |
| Beklenen bileşen navaid'e hiç bağlı değil (`declination_bileseni_yok`) | **1** — `LT_NAV_KAM` (`VOR_DME`), zaten `navaidLabeling_*`'ta da bileşensiz görünüyor |
| Bileşen var ama kaynakta `declination` raporlanmamış (`declination_kaynakta_yok`) | 3.917 |

> **Çoğu ülke bu alanı raporlamıyor; bu bir hata değildir** (`GPAssociatedLOCTrueBrg`
> ile aynı durum). Eksik satırlar `errored-features.csv`'ye yazılmaz, yalnızca
> sayılır.

### İzinsiz fallback kurulmadı

`navaidComponents_VOR_magneticVariation` (istasyonun genel manyetik varyasyonu,
`EQUIPMENT_COMMON_FIELDS`'te ayrı bir alan) `declination`'ın yerine
**kullanılmaz** — ikisi AIXM'de farklı alanlardır ve farklı anlam taşır
(`declination` istasyonun *beyan ettiği* sapma ile gerçek sapma arasındaki
fark; `magneticVariation` konumun genel manyetik varyasyonudur). Yalnızca
`VORTAC`'ta VOR↔TACAN arası sıralama kullanıcı kararıyla kuruldu, başka hiçbir
alt-türe genişletilmedi.

### Doğrulama

Son koşuda ölçüldü:

| Kontrol | Sonuç |
|---|---|
| Değer dolu | 86, hem `navaids` hem `navaidComponents`'te |
| Değer aralığı | -23,0 – 20,0 |
| `VOR`/`VOR_DME`/`TACAN`/`VORTAC` dışında `navaids` değeri | **0** |
| `VOR`/`TACAN` dışında `navaidComponents` değeri | **0** |
| `navaidComponents` değeri kendi alt-tür sütunuyla uyuşmayan satır | **0** |
| Örnek çapraz kontrol (`EAD_NAV_YFB_4699784`, VOR) | AIXM `declination=-22` → sütun `-22.0` ✓ |

---

## 4. `GPAssociatedLOCTrueBrg`

### Neden gerekli

Glidepath sembolü haritada bir **hüzme** olarak çizilir ve bu hüzmenin bir
yönü olmalıdır. Ama `Glidepath`'in AIXM'de yön alanı **yoktur**:

```
GlidepathPropertyGroup = frequency, slope, rdh,
                         signalPerformance, courseQuality, integrityLevel
```

Yön, aynı ILS'in **`Localizer`** bileşenindeki `trueBearing`'dir. Bu sütun o
değeri Glidepath satırına taşır, böylece QGIS sembolü tek alandan
döndürebilir.

### Nasıl bulunur

Kardeş bağı üzerinden: Glidepath → ebeveyn Navaid → aynı navaid'e bağlı
`Localizer` → `trueBearing`.

`associatedNavaid` virgüllü bir **listedir** (bir ekipman birden fazla
navaid'e ait olabiliyor); ebeveynlerden ilk çözüleni kullanılır. Bir
navaid'in birden fazla Localizer'ı olursa **ilki** alınır ve
`navaidde_birden_fazla_localizer` loglanır — veride böyle bir kayıt yok.

### Ölçülen doluluk

| | Adet |
|---|---:|
| `Glidepath` bileşeni | 524 |
| **Kardeş `Localizer` bulunan** | **524** — eşleştirme %100 |
| Kardeş LOC'ta `trueBearing` dolu → **sütun dolu** | **135** |
| Kardeş LOC'ta yalnızca `magneticBearing` dolu | 111 |
| Kardeş LOC'ta ikisi de boş | 272 |

**Eşleştirme darboğaz değil** — 524 Glidepath'in 524'ünde kardeş Localizer
bulunuyor. Sınırlayıcı olan kaynak verisidir: ham EAD `ils-loc.xml`'de 550
Localizer için 145 `valTrueBrg`, 257 `valMagBrg`, 180 `valMagVar` var.

> **Bazı ülkeler bu alanı raporlamıyor; bu bir hata değildir** (kullanıcı
> teyidi). Bu yüzden eksik satırlar `errored-features.csv`'ye **yazılmaz**,
> yalnızca sayılır: `gp_loc_true_bearing_kaynakta_yok` = **389**.

### Manyetik → gerçek çevrimi YAPILMAZ

`magneticBearing` + `magneticVariation` ile 76 satır daha doldurulabilirdi.
Yapılmıyor: istenen alan `trueBearing`'dir ve izinsiz fallback kurulmaz.
Farklı alanlar farklı anlam taşır — manyetik kerteriz gerçek kerteriz değildir
ve çevrim, kaynağın vermediği bir kesinlik iddiası olurdu.

### Doğrulama

Son koşuda ölçüldü:

| Kontrol | Sonuç |
|---|---|
| Değer dolu | 135, **hepsi** `Glidepath` |
| `Glidepath` dışında değer | **0** |
| Değer aralığı | 0 – 359,97 |
| Kardeş LOC'un `trueBearing`'i ile uyuşmayan satır | **0** |

---

## 5. QGIS kullanımı

### Pusula gülü (VOR/TACAN)

`navaids` katmanında bir VOR/TACAN sembolünü döndürmek için, sembol
katmanının **Rotation** alanına:

```sql
"navaidSymbology_declination"
```

`navaidComponents` katmanında aynı şey, bileşen türü filtresiyle:

```sql
"navaidComponents_equipmentType" IN ('VOR', 'TACAN')
  AND "navaidSymbology_declination" IS NOT NULL
```

### Glidepath hüzmesi

Glidepath sembolünü hüzme yönüne döndürmek için, sembol katmanının
**Rotation** alanına:

```sql
"navaidSymbology_GPAssociatedLOCTrueBrg"
```

Yalnızca yönü bilinen Glidepath'leri göstermek için katman filtresi:

```sql
"navaidComponents_equipmentType" = 'Glidepath'
  AND "navaidSymbology_GPAssociatedLOCTrueBrg" IS NOT NULL
```

Yönü olmayan 389 Glidepath için ayrı bir sembol (yönsüz gösterim)
tanımlanabilir:

```sql
"navaidComponents_equipmentType" = 'Glidepath'
  AND "navaidSymbology_GPAssociatedLOCTrueBrg" IS NULL
```

---

## 6. İlgili dokümanlar

* [`Navaid_Labeling_Fields.md`](Navaid_Labeling_Fields.md) — etiket metni
  üreten kardeş aile
* [`AIXM_to_GeoPackage_Schema_Design.md`](AIXM_to_GeoPackage_Schema_Design.md)
  — katman şemalarının tamamı
* [`Common_Builder_Behaviour.md`](Common_Builder_Behaviour.md) — boru hattının
  genel davranışı
