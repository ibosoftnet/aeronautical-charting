# `navaidSymbology_*` alanları

`navaidComponents` katmanındaki **türetilmiş** sembol alanları.
Üreten kod: [`gpkg/navaid_symbology.py`](gpkg/navaid_symbology.py).

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
| `[6]` | **`navaidSymbology_*`** | yalnızca `navaidComponents` |

---

## 2. Sütunlar

| Sütun | Tip | Geçerli olduğu ekipman |
|---|---|---|
| `navaidSymbology_GPAssociatedLOCTrueBrg` | REAL | yalnızca `Glidepath` |

---

## 3. `GPAssociatedLOCTrueBrg`

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

## 4. QGIS kullanımı

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

## 5. İlgili dokümanlar

* [`Navaid_Labeling_Fields.md`](Navaid_Labeling_Fields.md) — etiket metni
  üreten kardeş aile
* [`AIXM_to_GeoPackage_Schema_Design.md`](AIXM_to_GeoPackage_Schema_Design.md)
  — katman şemalarının tamamı
* [`Common_Builder_Behaviour.md`](Common_Builder_Behaviour.md) — boru hattının
  genel davranışı
