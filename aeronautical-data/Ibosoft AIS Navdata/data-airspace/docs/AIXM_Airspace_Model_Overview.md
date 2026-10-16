# AIXM 5.2 — Hava Sahası Modeli (Genel Bakış)

Kaynak: AIXM 5.2 XSD (`AirspacePropertyGroup`, `AirspaceGeometryComponent`,
`AirspaceVolume`, `AirspaceVolumeDependency`, `AirspaceLayerClass`,
`AirspaceLayer`, `AirspaceActivation`) ve açıklamalı XSD'deki tanımlar.

## 1. Üç katmanlı yapı

```
Airspace (feature)                       kimlik: type, designator, name, …
 └─ timeSlice / AirspaceTimeSlice
     ├─ class                0..∞  ──▶ AirspaceLayerClass (nesne)
     │                                  classification + associatedLevels
     ├─ geometryComponent    0..∞  ──▶ AirspaceGeometryComponent (nesne)
     │                                  operation + operationSequence
     │                                  └─ theAirspaceVolume ──▶ AirspaceVolume (nesne)
     │                                       horizontalProjection (poligon)
     │                                       upper/lower/maximum/minimumLimit
     │                                       centreline + width (koridor)
     │                                       contributorAirspace (başka saha)
     ├─ activation           0..∞  ──▶ AirspaceActivation (nesne)
     └─ annotation           0..∞  ──▶ Note
```

| Yapı | AIXM tanımı |
|---|---|
| `Airspace` | Hava trafiği için anlamlı, tanımlı üç boyutlu bir bölge |
| `AirspaceGeometryComponent` | Bileşenin saha geometrisindeki rolü. Geometri **tek** hacimden oluşuyorsa bu sınıfın alanları boş bırakılabilir |
| `AirspaceVolume` | Havada tanımlı bir hacim: yatay izdüşüm + dikey limitler |
| `AirspaceLayerClass` | İki dikey seviye arasındaki bir saha parçasının sınıfı |
| `AirspaceLayer` | İki dikey seviye arasındaki saha parçası |
| `AirspaceActivation` | Sahanın operasyonel durumu hakkında bilgi |

## 2. Geometri: bileşenler ve işlemler

Sahanın şekli doğrudan feature'da değil, bileşenlerdedir. Her bileşen:

| Alan | Anlamı (AIXM) |
|---|---|
| `operation` | Bileşenin birleşime nasıl katıldığı (ekleme, çıkarma, kesişim) |
| `operationSequence` | Bileşenin birleşimdeki sırası |
| `theAirspaceVolume` | Bileşenin hacmi |

`CodeAirspaceAggregationType` değerleri:

| Değer | AIXM tanımı | Anlamı |
|---|---|---|
| `BASE` | 'Parent' airspace is the basis for subsequent operations | Başlangıç geometrisi |
| `UNION` | … second operand in a union operation | Birleşim (ekle) |
| `INTERS` | … second operand in intersection operation | Kesişim |
| `SUBTR` | … second operand in subtraction operation | Fark (çıkar) |

Sonuç geometri: `BASE` ile başlanır, diğer bileşenler `operationSequence`
sırasıyla uygulanır. Örnek: "TMA, CTR hariç" = `BASE`(TMA poligonu) +
`SUBTR`(CTR poligonu).

> Bu projede (data-airspace) üreticiler her sahayı **tek** `BASE` bileşeniyle
> yazar (kaynaklar tek parça poligon veriyor). Birleştirici/GeoPackage tarafı
> çok bileşenli geometriyi de hesaplar — bkz.
> [`../AIXM_to_GeoPackage_Schema_Design.md`](../AIXM_to_GeoPackage_Schema_Design.md).

## 3. Hacim (AirspaceVolume)

### 3.1 Yatay şekil

| Alan | Anlamı (AIXM) |
|---|---|
| `horizontalProjection` | Hacmin yatay şeklini tanımlayan yüzey (`aixm:Surface` → `gml:PolygonPatch`'ler; delikler `gml:interior`) |
| `centreline` | Koridor biçimli hacmin ortasından geçen çizgi |
| `width` | Hacim baştan koridor olarak tanımlandıysa koridorun genişliği |
| `location` | Hacmin coğrafi referansı olarak tek bir konum; özellikle kesin bir `horizontalProjection` verilmediğinde |
| `name` | Hacmin serbest metin adı |

**Koridor.** Bazı sahalar (ör. rota koridoru, `AWY`/`MTR`) poligon yerine bir
merkez çizgisi + genişlikle tanımlanır. AIXM her ikisini birden taşıyabilir;
yalnız `centreline` + `width` varsa poligon, çizginin genişlik kadar
tamponlanmasıyla elde edilir — bu bir **hesaplama** kararıdır, şema bunun
yöntemini tanımlamaz.

### 3.2 Dikey limitler

| Alan | Anlamı (AIXM) |
|---|---|
| `upperLimit` | Hacmin üst sınırının (tavan) dikey mesafesi; referansı `upperLimitReference` |
| `lowerLimit` | Hacmin alt sınırının (taban) dikey mesafesi; referansı `lowerLimitReference` |
| `maximumLimit` | Azami sınır. Üst sınırın azami sınırın **altında** kaldığı yerlerde azami sınır üst sınırı **geçersiz kılar** |
| `minimumLimit` | Asgari sınır. Alt sınırın asgari sınırın **altında** kaldığı yerlerde asgari sınır alt sınırı **geçersiz kılar** |

`maximum`/`minimumLimit`, tavanı/tabanı arazi gibi değişken bir yüzeye bağlı
sahalarda anlamlıdır (ör. "1000 FT SFC, ama en az 2500 FT MSL").

**Değer** (`ValDistanceVerticalType`): sayı ya da şu özel değerler —

| Değer | AIXM tanımı |
|---|---|
| `GND` | Yeryüzü |
| `UNL` | Sınırsız |
| `FLOOR` | Sahanın tabanı — tabanı sabit olmayan sahalarda kullanım ifade etmek için |
| `CEILING` | Sahanın tavanı — tavanı sabit olmayan sahalarda kullanım ifade etmek için |

**Birim** (`uom` niteliği): `FT`, `M`, `FL`, `SM`. **Referans**
(`CodeVerticalReferenceType`):

| Değer | AIXM tanımı |
|---|---|
| `SFC` | Yeryüzünden ölçülen mesafe (AGL ile eşdeğer) |
| `MSL` | Ortalama deniz seviyesinden (irtifa) |
| `W84` | WGS84 elipsoidinden |
| `STD` | Standart atmosfere ayarlı altimetreyle (uçuş seviyesi) |

### 3.3 Başka sahadan geometri alma

`contributorAirspace` → `AirspaceVolumeDependency`: hacmin geometrisini
etkileyen (üst) bir Airspace'e referans (`theAirspace`, `xlink:href`).

| `dependency` | AIXM tanımı |
|---|---|
| `FULL_GEOMETRY` | Sahanın tüm geometrisi kullanılır |
| `HORZ_PROJECTION` | Sahanın yatay izdüşümü devralınır |

Bu, iki sahanın feature düzeyinde bağlandığı tek yerdir; referans verilen
saha birleşik veride bulunmalıdır.

## 4. Sınıf katmanları

`class` 0..∞ `AirspaceLayerClass` taşır:

| Alan | Anlamı (AIXM) |
|---|---|
| `classification` | ICAO Annex 11 Ek 4'e göre işletme kuralları, uçuş gereklilikleri ve verilen hizmetleri belirleyen sınıf (`A`–`G`) |
| `associatedLevels` | Sınıfın geçerli olduğu `AirspaceLayer`(lar) — üst/alt limit + referans + `altitudeInterpretation` |

Tek sınıflı sahada `associatedLevels` genellikle yazılmaz (sınıf tüm hacim için
geçerlidir). **Çok sınıflı** sahada (ör. TMA: FL95 üstü C, altı D) her sınıf
kendi seviye bandını taşır. `AirspaceLayerClass` aynı zamanda bir
`PropertiesWithSchedule`'dır: sınıf **saate bağlı** da değişebilir
(bkz. [`AIXM_Airspace_Activation_Schedule.md`](AIXM_Airspace_Activation_Schedule.md)).

## 5. Aktivasyon

`activation` 0..∞ `AirspaceActivation`: `activity` (sahanın kullanım
nedeni), `status` (aktivasyon durumu), `levels` (aktivasyonun geçerli olduğu
seviyeler), `user` (kullanan kuruluş), `aircraft` (kullanan uçak tipi) ve
`PropertiesWithSchedule`'dan gelen `timeInterval` (saatler). Ayrıntı:
[`AIXM_Airspace_Activation_Schedule.md`](AIXM_Airspace_Activation_Schedule.md).

## 6. Uçtan uca örnek akış

Yapıyı göstermek için **kurgusal** bir örnek (değerler gerçek AIP verisi
değildir): "ÖRNEK TMA: FL95–FL195 C sınıfı, 4500 FT MSL–FL95 D sınıfı, ÖRNEK
CTR hariç; hafta içi 06:00–22:00 UTC aktif" sahası:

1. `Airspace` feature'ı: `type=TMA`, `designator`, `name`.
2. `geometryComponent` 1: `operation=BASE`, `operationSequence=1`,
   hacim = TMA poligonu, `upperLimit=195 FL STD`, `lowerLimit=4500 FT MSL`.
3. `geometryComponent` 2: `operation=SUBTR`, `operationSequence=2`, hacim =
   CTR poligonu (ya da `contributorAirspace` ile CTR feature'ına referans).
4. `class` 1: `C`, `associatedLevels` = FL95–FL195; `class` 2: `D`,
   `associatedLevels` = 4500 FT MSL–FL95.
5. `activation`: `status=ACTIVE`, `timeInterval` → `Timesheet`
   (`day=MON_FRI`, `startTime=06:00`, `endTime=22:00`, `timeReference=UTC`).

XML iskeleti: [`AIXM_Airspace_How_To_Add.md`](AIXM_Airspace_How_To_Add.md) §3.

## İlgili dokümanlar

- [`AIXM_Airspace_Attributes.md`](AIXM_Airspace_Attributes.md) — tam öznitelik listesi
- [`../../common/docs/AIXM_Annotation_Attributes.md`](../../common/docs/AIXM_Annotation_Attributes.md) — `annotation`/`Note`
- [`../../common/docs/Ibosoft_AIS_Extension.md`](../../common/docs/Ibosoft_AIS_Extension.md) — projenin extension elemanları
