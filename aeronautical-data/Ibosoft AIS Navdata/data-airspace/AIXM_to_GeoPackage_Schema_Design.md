# AIXM → GeoPackage Şema Tasarımı (data-airspace)

Bu doküman **2B aşamasının tam eşleme tablosudur**:
`navdata/ibosoft-ais-navdata-airspaces-aixm.xml` içindeki her AIXM öğesinin
`navdata/ibosoft-ais-navdata-airspaces.gpkg` → `airspaces` tablosunda hangi sütuna gittiğini
ve kararların gerekçesini listeler.

- Builder davranışı: [`Common_Builder_Behaviour.md`](Common_Builder_Behaviour.md)
- AIXM airspace kılavuzu: [`docs/`](docs/) (özellikle [`docs/AIXM_Airspace_Attributes.md`](docs/AIXM_Airspace_Attributes.md))
- Ortak sütun aileleri ve extension: [`../common/README.md`](../common/README.md), [`../common/docs/Ibosoft_AIS_Extension.md`](../common/docs/Ibosoft_AIS_Extension.md)
- Ham veri → AIXM: `data-sources/*/generate-aixm-data/*_to_AIXM_Mapping.md`
- Kod: `gpkg_airspace.py` (eşleme), `airspace_geometry.py` (geometri), ortak `data_build_common/aixm_fields.py`, `gpkg_writer.py`

## Bağlayıcı kural

> **Hiçbir AIXM özniteliği sessizce atlanamaz.** Her öznitelik ya bir sütuna
> eşlenir, ya "kaynakta yok" olarak işaretlenir. "Kapsam dışı" ilan etmek tek
> başına verilecek bir karar değildir — bulgusu ve gerekçesiyle kullanıcıya
> getirilip onaylanır. **Uydurma eşleme/açıklama yok.**

AIXM 5.2 XSD'deki `Airspace`, `AirspaceLayerClass`, `AirspaceGeometryComponent`,
`AirspaceVolume`, `AirspaceVolumeDependency`, `AirspaceLayer`,
`AirspaceActivation`, `PropertiesWithSchedule`, `Timesheet`, `Note` ve
`AbstractAIXMFeature*`/`AbstractAIXMTimeSlice*` öğelerinin **tamamı** aşağıda
eşlenmiştir; kapsam dışı bırakılan öğe **yoktur** (§7). Bu, XSD'den otomatik
çıkarılan öğe listesiyle karşılaştırılarak doğrulandı.

"Dolu" yüzdeleri son koşudan ölçüldü (`COUNT(NULLIF(sütun,''))`). `%0,0` bir
sütun "kaynakta yok" demektir: eşleme kurulu ve çalışır, bugünkü kaynaklar o
alanı vermiyor. Bu sütunlar kaldırılmaz — yeni bir kaynak geldiğinde şema
değişmeden dolar.

---

## 1. Katman

| Katman | AIXM Feature | Geometri | Sütun | Satır |
|---|---|---|---:|---:|
| `airspaces` | `Airspace` | MULTIPOLYGON (EPSG:4326) | 55 | 36.916 |

Ayrıca `id` (INTEGER PRIMARY KEY AUTOINCREMENT) ve `geom` (BLOB). **Her Airspace
tek satırdır** (kullanıcı kararı: sınıfa ya da bileşene göre bölme yok).

---

## 2. Adlandırma kuralları (ATS ile aynı)

| Kural | Örnek |
|---|---|
| AIXM alanı | `airspaces_<AIXM adı>` → `airspaces_designator` |
| Alt nesne alanı | camelCase birleşik → `airspaces_locationLatitude`, `airspaces_contributorAirspaceUuid` |
| Ölçü birimi / dikey referans | `<alan>Uom`, `<alan>Reference` |
| Başka feature'a referans | `…Uuid` (hedefin `gml:identifier`'ı) |
| Tekrarlanan (0..∞) yapı | **tam JSON** (`element_to_dict`: hiçbir alt alan atılmaz, `xlink:href` → `{"href": uuid}`, `uom` korunur) |
| Ortak aileler | `annotation*`, `data_*`, `aixm_*` — öneksiz, ATS ile aynı |
| Türetilmiş (AIXM'de yok) | kendi aile öneki: `airspaceLabeling_*` |

---

## 3. Tam eşleme tablosu

### 3.1 Airspace (`AirspacePropertyGroup`)

| AIXM öğesi | Sütun | Tip | Dolu |
|---|---|---|---|
| `type` | `airspaces_type` | TEXT | 100,0% (36.914; 2 boş = ICAO `NIL1`/`NIL2`) |
| `designator` | `airspaces_designator` | TEXT | 61,3% |
| `localType` | `airspaces_localType` | TEXT | 0,0% (17) |
| `name` | `airspaces_name` | TEXT | 89,6% |
| `designatorICAO` | `airspaces_designatorICAO` | TEXT | 0,0% (18) |
| `controlType` | `airspaces_controlType` | TEXT | 0,0% (18) |
| `upperLowerSeparation` (+ `uom`) | `airspaces_upperLowerSeparation`, `…Uom` | REAL, TEXT | **0,0%** |
| `class` (0..∞) | `airspaces_class` | TEXT (JSON dizisi: `classification`, `associatedLevels[]`, `timeInterval[]`, `annotation[]`, `specialDateAuthority[]`) | 34,4% |
| `protectedRoute` | `airspaces_protectedRouteUuid` | TEXT | **0,0%** |
| `geometryComponent` (0..∞) | `geom` (hesaplanmış, §4) + `airspaces_geometryComponent` (JSON) + BASE volume sütunları (§3.2) | — | 100,0% |
| `activation` (0..∞) | `airspaces_activation` | TEXT (JSON dizisi: `activity`, `status`, `levels[]`, `user[]`, `aircraft[]`, `timeInterval[]`, `annotation[]`, `specialDateAuthority[]`) | 0,1% (24) |
| `annotation` (0..∞) | `annotationDescription` / `Remark` / `Warning` / `Disclaimer` | TEXT | 0,0% (5) / 0,4% / **0,0%** / 0,0% (18) |

`activation` tekil `activity`/`status` sütunlarına **indirgenmez** (kullanıcı
kararı, ATS'deki `availability` ile aynı desen): bir sahada birden çok
aktivasyon olabilir, tekil sütun hangisini göstereceğini uydurmak zorunda
kalırdı.

### 3.2 AirspaceGeometryComponent / AirspaceVolume

`airspaces_geometryComponent`: TÜM bileşenler JSON dizisi olarak —
`operation`, `operationSequence`, `annotation`, `theAirspaceVolume` (bütün
volume alanları). Tek istisna geometriler: `horizontalProjection` `geom`
sütunundadır, `centreline` `airspaces_centreline`'dadır; JSON'a tekrar
konmaz.

**BASE bileşeninin** volume alanları ayrıca tekil sütunlardadır (diğer
bileşenlerinkiler yalnız JSON'da):

| AIXM öğesi (AirspaceVolume) | Sütun | Tip | Dolu |
|---|---|---|---|
| `upperLimit` (+ `uom`), `upperLimitReference` | `airspaces_upperLimit`, `…Uom`, `…Reference` | TEXT, TEXT, TEXT | 99,1% / 95,3% / 93,4% |
| `maximumLimit` (+ `uom`), `maximumLimitReference` | `airspaces_maximumLimit`, `…Uom`, `…Reference` | TEXT | **0,0%** |
| `lowerLimit` (+ `uom`), `lowerLimitReference` | `airspaces_lowerLimit`, `…Uom`, `…Reference` | TEXT | 99,1% / 98,7% / 97,6% |
| `minimumLimit` (+ `uom`), `minimumLimitReference` | `airspaces_minimumLimit`, `…Uom`, `…Reference` | TEXT | **0,0%** |
| `width` (+ `uom`) | `airspaces_width`, `airspaces_widthUom` | REAL, TEXT | **0,0%** |
| `horizontalProjection` | `geom` | MULTIPOLYGON | 100,0% |
| `centreline` | `airspaces_centreline` | TEXT (WKT LineString, boylam enlem) | **0,0%** |
| `contributorAirspace/…/dependency` | `airspaces_contributorAirspaceDependency` | TEXT | **0,0%** |
| `contributorAirspace/…/theAirspace` | `airspaces_contributorAirspaceUuid` | TEXT | **0,0%** |
| `annotation` | `airspaces_geometryComponent` JSON'unda | — | — |
| `name` | `airspaces_volumeName` | TEXT | **0,0%** |
| `location` | `airspaces_locationLatitude`, `…Longitude` | REAL | **0,0%** |

> **Dikey limitler neden TEXT (ATS'den bilinçli fark).** AIXM değeri sayı
> **ya da** `UNL`/`GND`/`FLOOR`/`CEILING` olabilir ve bu veride gerçekten var:
> Jeppesen'de 1.400 `UNL`, LH'de 141 `GND`. ATS'deki gibi REAL sütun bu
> değerleri NULL'a çevirirdi; referans sütunu `UNL`'ı ayırt edemez — sessiz
> kayıp olurdu. Değer AIXM'de yazıldığı gibi taşınır.

### 3.3 Extension, provenance, kimlik

| AIXM öğesi | Sütun | Dolu |
|---|---|---|
| `extension/ibosoftais:AirspaceExtension/regionIcao` | `airspaces_regionIcao` | 0,9% (yalnız ICAO-FIR-UIR) |
| `extension/ibosoftais:AirspaceExtension/regionSupProc` | `airspaces_regionSupProc` | 0,9% |
| `extension/ibosoftais:AirspaceDataProvenance/dataProvider` | `data_provider` | 100,0% |
| `…/dataOriginator` | `data_originator` | 2,4% (Jeppesen ve ICAO-FIR-UIR'de yok → NULL) |
| `…/dataEffectivity` | `data_effectivity` | 100,0% |
| `gml:id` | `aixm_gml_id` | 100,0% |
| `gml:identifier` | `aixm_uuid` | 100,0% |

### 3.4 TimeSlice / feature tabanı (`aixm_*`, ATS ile ortak)

| AIXM öğesi | Sütun | Dolu |
|---|---|---|
| `gml:validTime` begin / end | `aixm_validTimeBegin`, `aixm_validTimeEnd` | 100,0% (hepsi `unknown`, §5) |
| `interpretation` | `aixm_interpretation` | 100,0% (`BASELINE`) |
| `sequenceNumber`, `correctionNumber` | `aixm_sequenceNumber`, `aixm_correctionNumber` (INTEGER) | 100,0% |
| `featureLifetime` | `aixm_featureLifetimeBegin`, `…End` | **0,0%** |
| `timeSliceMetadata` | `aixm_timeSliceMetadata` (JSON) | **0,0%** |
| `featureMetadata` | `aixm_featureMetadata` (JSON) | **0,0%** |
| `gml:description` | `aixm_description` | **0,0%** |
| `gml:name` (0..∞) | `aixm_name` (JSON dizisi) | **0,0%** |
| `gml:boundedBy` | — (`geom`'dan türetilen zarf; ayrı bilgi taşımaz) | — |

### 3.5 Türetilmiş: `airspaceLabeling_*`

| Sütun | Kural | Dolu |
|---|---|---|
| `airspaceLabeling_classifications` | Sınıf harflerinin `,` ile birleşik listesi (ör. `C,D`), **AIXM'deki yazılış sırasıyla**. Sınıf yoksa NULL. | 34,4% |

Kullanıcı kararı: çok sınıflı saha satırlara **bölünmez**; tam bilgi
`airspaces_class` JSON'undadır, bu sütun QGIS filtre/etiketi içindir. Liste
seviyeye göre **sıralanmaz**: sınıf bantlarının referansları karışık olabilir
(`FT MSL` / `FL`), karşılaştırmak dönüşüm uydurmayı gerektirirdi. Bugünkü
kaynakların hiçbiri çok sınıflı saha üretmiyor; davranış sentetik veriyle
sınandı.

---

## 4. Geometri hesabı

`airspace_geometry.airspace_geometry()` (kullanıcı kararı):

1. Bileşenler `operationSequence` ile sıralanır; tekrar eden sıra numarası →
   hata.
2. İlk bileşen tek `BASE` olmalı → değilse hata.
3. Her bileşenin poligonu `horizontalProjection`'dan okunur (`PolygonPatch`
   dış halka + `interior` delikler). Poligonu olmayan bileşen (yalnız
   `centreline`/`width` ya da `contributorAirspace`) → **hata; poligon
   uydurulmaz**.
4. `BASE`'ten başlanır; `UNION` birleşim, `SUBTR` fark, `INTERS` kesişim.
5. Sonuç antimeridyene karşı güvenli MultiPolygon'a çevrilir (±180'de bölünür).
6. Halka yönü **RFC 7946 §3.1.6**'ya getirilir (dış saat yönünün tersi, delik
   saat yönü). Birleşik AIXM zaten bu yöndedir (birleştirici uygular, bkz.
   `Common_Builder_Behaviour.md` §4.1); burada yeniden uygulanır çünkü
   birleşim/fark/kesişim ve antimeridyen bölmesi yönü değiştirebilir. Sonuç:
   `geom` sütunundaki her poligon RFC 7946 yönündedir.

Hata durumunda satır **yazılmaz** ve `errored-features.csv`'ye
`geometri_hesaplanamadi_satir_yazilmadi` yazılır. Son koşu: **0**.

Bugünkü kaynakların hepsi tek `BASE` bileşeni üretir; çok bileşenli yol
sentetik veriyle sınandı (BASE+SUBTR, BASE+UNION, BASE+INTERS alanları; BASE'siz,
sıra tekrarı ve yalnız-centreline hataları).

---

## 5. Kaynak değerlerinin GeoPackage'taki görünümü

| Konu | Davranış |
|---|---|
| `validTime` | Üreticiler başlangıcı `unknown` yazar: kaynakların `data_effectivity`'si veri setinin geçerliliğidir, feature'ın yürürlüğü değil (uydurma yürürlük iddiası olurdu). Veri seti geçerliliği `data_effectivity`'dedir |
| Türkçe harf | AIXM `TextNameType` ASCII ister; üretici dönüştürür ve loglar (kullanıcı kararı). Son koşu: 1 kayıt (TRNC) |
| LH `GSEC` sınıfı | AIXM listesinde yok → `OTHER:GSEC` (AIXM'in kendi genişletme deseni; değer kaybolmaz). 5 kayıt |
| Jeppesen designator | Yalnız `restrictive_designation` (kullanıcı kararı; eski önekli biçim 10 karakteri aşıyordu) |

---

## 6. Validasyon ve index

Satır doğrulaması AIXM düzeyinde yapılır: her kaynak AIXM'i ve birleşik AIXM
XSD'den (AIXM 5.2 + extension şeması) **0 hata** ile geçer; değer listeleri,
desenler ve uzunluklar şemanın kendisiyle denetlenir. 2B ayrıca kural tablosu
taşımaz.

Index (ortak `gpkg_writer.finalize`): her sütunda B-tree (55/55), RTree
mekânsal index (`rtree_airspaces_geom`, GeoPackage 1.2 Ek F.3 tetikleyicileri),
`gpkg_contents` sınırlayıcı kutusu, `gpkg_ogr_contents` sayacı, `ANALYZE`.

---

## 7. Kapsam dışı bırakılanlar

**Yok.** XSD'deki her Airspace öğesinin bir sütunu ya da JSON içindeki yeri
var; `%0,0` görünen sütunlar kaynakların o alanı vermemesindendir.

## 8. Eski `Common Airspaces` şemasından farklar

| Eski sütun | Yeni karşılık | Neden |
|---|---|---|
| `type`, `designator`, `name`, `localType`, `designatorICAO`, `controlType` | `airspaces_<aynı>` | ATS adlandırma kuralı |
| `classification` (tekil) | `airspaces_class` (JSON) + `airspaceLabeling_classifications` | AIXM'de `class` 0..∞ ve seviyeye bağlı |
| `upperLimit…`, `lowerLimit…` | `airspaces_upperLimit…`, `airspaces_lowerLimit…` (BASE volume) | Gerçek yeri `AirspaceVolume` |
| `activity`, `status` (tekil) | `airspaces_activation` (JSON) | AIXM'de `activation` 0..∞ |
| `annotation*` | aynı (öneksiz) | ATS ile ortak |
| `data_provider`, `data_originator`, `data_effectivity` | aynı; kaynak provenance kutusu | ATS ile ortak |
| `add_date` | **kaldırıldı** | Kullanıcı kararı |
| `horizontalProjection` (geometri sütunu adı) | `geom` | ATS ile aynı |
| — | `aixm_*`, `maximum/minimumLimit`, `width`, `centreline`, `location`, `contributorAirspace…`, `protectedRouteUuid`, `upperLowerSeparation`, `volumeName`, `geometryComponent`, `regionIcao/SupProc` | Önceden eşlenmemiş AIXM öğeleri |

> `ais-map` (`D:\ibosoft\AIS\ais-map`) bugün eski şemanın sütun adlarını
> (`controlType`, `activity`, `status` …) okuyor. Yeni GeoPackage'a geçildiğinde
> oradaki alan adları da güncellenmelidir.
