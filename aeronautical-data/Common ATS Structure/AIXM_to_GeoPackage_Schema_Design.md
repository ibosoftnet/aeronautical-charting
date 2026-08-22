# AIXM → GeoPackage Şema Tasarımı

Bu doküman **2B aşamasının tam eşleme tablosudur**: `common-ats-structure-aixm.xml`
içindeki hangi AIXM öğesinin hangi GeoPackage sütununa gittiğini, hangi
özniteliğin kaynakta bulunmadığını ve hangi kararların gerekçesini listeler.

- Builder'ın davranışı (aşamalar, çakışma çözümü, antimeridyen, provenance):
  [`Common_Builder_Behaviour.md`](Common_Builder_Behaviour.md)
- AIXM öznitelik referansları: [`docs/`](docs/) — özellikle
  [`AIXM_Annotation_Attributes.md`](docs/AIXM_Annotation_Attributes.md) ve
  [`docs/aixm-point-types/`](docs/aixm-point-types/)
- Ham veri → AIXM eşlemeleri: `data-sources/*/generate-aixm-data/*_Mapping.md`

## Bağlayıcı kural

> **Hiçbir AIXM özniteliği sessizce atlanamaz.** Her öznitelik ya bir sütuna
> eşlenir, ya "kaynakta yok" olarak (ham veriye bakılarak doğrulanmış şekilde)
> işaretlenir. Bir şeyi "kapsam dışı" ilan etmek tek başına verilecek bir karar
> değildir — bulgusu ve gerekçesiyle kullanıcıya getirilip onaylanır.
> **Uydurma eşleme/açıklama yok.** Bilinmeyen her şey sorulur.

Bu dokümandaki **"dolu"** yüzdeleri son koşudan ölçülmüştür
(`COUNT(NULLIF(sütun,''))` — boş dize dolu sayılmaz). `%0,0` bir sütun
"kaynakta yok" demektir: eşleme kurulmuştur ve çalışır, kaynaklar o alanı
sağlamıyor. Bu sütunlar **kaldırılmaz** — görünür boşluk bırakmak, sessizce
atlamaktan yeğdir ve yeni bir kaynak geldiğinde şema değişmeden dolar.

---

## 1. Katmanlar

| Katman | AIXM Feature | Geometri | Sütun | Satır |
|---|---|---|---:|---:|
| `designatedPoints` | `DesignatedPoint` | POINT | 23 | 152.055 |
| `navaids` | `Navaid` | POINT | 34 | 9.357 |
| `navaidComponents` | `NavaidComponent` + `AbstractNavaidEquipment` | POINT | 61 | 13.285 |
| `routeSegments` | `RouteSegment` (+ `Route`) | LINESTRING | 82 | 92.976 |

Her katmanda ayrıca `id` (INTEGER PRIMARY KEY AUTOINCREMENT) ve `geom` (BLOB)
bulunur; yukarıdaki sütun sayıları bu ikisini içermez.

### 1.1 `points` katmanı neden yok

`aixm:Point`, `gml:Point` ikame grubundadır — `AbstractAIXMFeature` **değildir**,
dolayısıyla `message:hasMember` olamaz ve kendi `gml:id`/`timeSlice`'ı yoktur.
`PointPropertyType`, `aixm:Point`'i **değer olarak gömer** (`DesignatedPoint` ve
`Navaid`'in aksine — onlar boş xlink association type'larıdır). Ayrı bir feature
olmadığı için ayrı bir katman da kurulamaz; kullanıcı kararıyla `points` katmanı
iptal edildi. Antimeridyen kesişim noktaları bu yüzden `Point` değil
`DesignatedPoint` (`type = OTHER`) olarak üretilir.

### 1.2 `Route` neden ayrı katman değil

`Route` feature'ı birleşik AIXM'de vardır (14.754 kayıt) ama ayrı katmana
yazılmaz: rota düzeyindeki öznitelikler `routeSegments` katmanına
`route_*` önekiyle devredilir (RouteSegment'in kendi alanlarından bilinçli
olarak farklı bir önek — ikisi ayrı feature'dır), böylece QGIS'te tek tabloda
hem segment hem rota bilgisi görünür.

---

## 2. Adlandırma kuralları

| Kural | Örnek |
|---|---|
| Sütun adı | `<katman>_<AIXM öznitelik adı, camelCase>` → `navaids_type` |
| Ölçü birimi | `<alan>Uom` → `routeSegments_lengthUom` |
| Dikey referans | `<alan>Reference` → `routeSegments_upperLimitReference` |
| `location` alt alanları | `<katman>_location<Alan>` → `navaids_locationElevation` |
| Rota kökenli (Route feature'ından) | `route_<Attr>` → `route_designatorNumber` — **`routeSegments_` DEĞİL**, RouteSegment'in kendi alanlarından ayırt edilsin diye |
| Uç nokta | `routeSegments_<start\|end><Attr>` → `routeSegments_startFlyOver` |

**İstisna — katman önekisiz sütunlar.** `annotation`, provenance ve kimlik
alanları her katmanda birebir aynı yapıyı taşır; tabloya özgü bir anlamları
olmadığı için **önek almazlar** (kullanıcı kararı):

| Alan | Sütun |
|---|---|
| `annotation` (4 purpose) | `annotationDescription`, `annotationRemark`, `annotationWarning`, `annotationDisclaimer` |
| Provenance | `data_provider`, `data_originator`, `data_effectivity`, `add_date` |
| Kimlik | `gmlId` — birleşik AIXM'deki `gml:id` (kaynak önekli, örn. `EAD_DP_…`) |
| ATS rota durumu (türetilmiş) | `atsStatus_*` — yalnızca `designatedPoints` ve `navaids`'te |

Bu istisna dışındaki tüm sütunlar yukarıdaki genel kurala göre katman önekli
kalır (`designatedPoints_designator`, `navaids_type` gibi).

`atsStatus_*` alanları AIXM'den okunmaz; `routeSegments` yazıldıktan sonra
ondan türetilir. Tam tanımları, kuralları ve ölçülen dağılımları ayrı
dokümandadır: [`ATS_Status_Fields.md`](ATS_Status_Fields.md).

**Sütun tipi** `gpkg/schema.py:column_type()` ile belirlenir: `*Uom` ve
`*Reference` her zaman TEXT; `*PointId`/`*navaidId` INTEGER; bilinen sayısal
son ekler (`frequency`, `slope`, `angle*`, `length`, `upperLimit` …) REAL; geri
kalan TEXT.

> **Neden dikey limitler REAL:** `upperLimit`/`lowerLimit` gibi alanlar AIXM'de
> `UNL`, `GND` gibi metin değerler de alabilir. Sütun REAL olduğu için bu özel
> değerler sayıya çevrilemez ve `NULL` kalır; ayrımı `*Reference` sütunu taşır.
> Ölçüldü: `upperLimit` %50,6, `lowerLimit` %46,9 dolu.

---

## 3. Tekrarlanan (0..∞) yapılar

Kullanıcı kararıyla, tekrarlanan yapılar TEXT sütunda **JSON** olarak saklanır.
`element_to_dict()` alt ağacın **tamamını** sözlüğe çevirir — hiçbir alt alan
atılmaz; yalnızca `gml:id` gibi teknik nitelikler dışarıda kalır. `xlink:href`
taşıyan eleman `{"href": "<uuid>"}` olur, `uom` niteliği `{"uom": …}` olarak
korunur.

| AIXM alanı | Katman | Sütun | Karar |
|---|---|---|---|
| `designCriteria` | routeSegments | `_designCriteria` | Virgülle ayrılmış metin |
| `availability` | routeSegments, navaids, navaidComponents | `_availability` | JSON dizisi (iç içe `levels[]` dahil) |
| `aircraftCapability` | routeSegments | `_aircraftCapability` | JSON dizisi (25 alt-alan + `radioNavigationEquipment[]`). **Segment boşsa Route'unki alınır** — aşağıya bakın |
| `airspaceClass` | routeSegments | `_airspaceClass` | JSON dizisi (`associatedLevels[]` dahil) |
| `minimumEnrouteAltitude` | routeSegments | `_minimumEnrouteAltitude` | JSON dizisi |
| `facilityMakeup` | routeSegments start/end | `_startFacilityMakeup`, `_endFacilityMakeup` | Tek JSON, tam iç içe yapıyla (`distanceReference[]`/`angleReference[]` dahil) |
| `fix` | designatedPoints | `_fix` | Tek JSON, tam iç içe `PointReference` yapısı |
| `monitoring` | navaidComponents | `_monitoring` | JSON dizisi |
| `navaidEquipment` | — | Ayrı `navaidComponents` katmanı + FK | Kullanıcı kararı |

### Hem `Route`'ta hem `RouteSegment`'te tanımlı alanlar

AIXM'de dört alan **her iki** property group'ta da bulunur:
`aircraftCapability`, `availability`, `annotation`, `extension`. `routeSegments`
katmanı ikisini birden temsil ettiği için her biri ayrı ele alınır:

| Alan | Davranış | Gerekçe |
|---|---|---|
| `aircraftCapability` | Segmentin kendi değeri varsa **o**; yoksa bağlı `Route`'unki alınır | Kullanıcı kararı. Önceden yalnızca segmente bakılıyordu; Route düzeyinde tanımlı 11 kayıt sessizce düşüyordu |
| `annotation` | **İkisi de** alınır, araya boş satır konarak birleşir | Notlar birbirini dışlamaz; aşağıdaki bölüm |
| `availability` | Yalnızca segmentinki | Ölçüldü: `Route.availability` hiçbir kayıtta yok (0), `RouteSegment` 7. Fallback eklenmedi — gereksiz |
| `extension` | Eşlenmez | Soyut uzatma noktası, somut içeriği yok |

`designCriteria` de aynı desende çalışır (segment → Route), ancak o alan
yalnızca `Route`'ta 0..∞'dur; segmentteki karşılığı ayrı bir yapıdır.

### `annotation` → 4 sütun

`annotation/Note/purpose` değeri (`DESCRIPTION`, `REMARK`, `WARNING`,
`DISCLAIMER`) hangi sütuna yazılacağını belirler; `purpose` yoksa `REMARK`
varsayılır. Hiçbir not atılmaz; iki ayrı ayırıcı vardır:

| Durum | Ayırıcı |
|---|---|
| **Aynı** feature içinde, aynı `purpose`'a düşen birden çok not | `" | "` (`NOTE_SEPARATOR`) |
| **Farklı** feature'lardan gelen notlar, aynı `purpose` sütununda | bir **boş satır** (`"\n\n"`, `FEATURE_SEPARATOR`) |

Bir satır iki farklı feature'ın notlarını taşıyabilir:

| Katman | Notların geldiği feature'lar |
|---|---|
| `routeSegments` | önce `RouteSegment`'in kendi notları, sonra bağlı `Route`'unkiler |
| `navaidComponents` | önce `AbstractNavaidEquipment`'ınkiler, sonra `NavaidComponent`'inkiler |

`annotations()` aynı satır için birden çok kez çağrılabilir; sonraki çağrılar
mevcut değerin **üzerine yazmaz**, boş satır bırakarak ekler.

`Route.annotation`, AIXM'de `RouteSegment.annotation`'dan bağımsız bir alandır
(`RoutePropertyGroup` ve `RouteSegmentPropertyGroup` gruplarının her ikisinde de
`annotation` 0..∞ olarak tanımlıdır). Ölçüldü: 20 `Route` ve 106 `RouteSegment`
not taşıyor; `annotationRemark` 128 satırda dolu.

Yapının tam tanımı:
[`docs/AIXM_Annotation_Attributes.md`](docs/AIXM_Annotation_Attributes.md).

---

## 4. `designatedPoints` (23 sütun)

Kaynak: `DesignatedPointTimeSlice`. Geometri: `location/Point/gml:pos` → POINT.

| Sütun | AIXM kaynağı | Tip | Dolu |
|---|---|---|---:|
| `designatedPoints_designator` | `designator` | TEXT | 99,8% |
| `designatedPoints_type` | `type` | TEXT | 100,0% |
| `designatedPoints_name` | `name` | TEXT | 98,2% |
| `designatedPoints_codeICAOCountry` | `codeICAOCountry` | TEXT | **0,0%** |
| `designatedPoints_fix` | `fix` (JSON) | TEXT | 0,1% |
| `annotationDescription` | `annotation` purpose=DESCRIPTION | TEXT | 99,4% |
| `annotationRemark` | purpose=REMARK | TEXT | 0,1% |
| `annotationWarning` | purpose=WARNING | TEXT | **0,0%** |
| `annotationDisclaimer` | purpose=DISCLAIMER | TEXT | **0,0%** |
| `data_provider` | provenance yan dosyası | TEXT | 100,0% |
| `data_originator` | provenance yan dosyası | TEXT | 100,0% |
| `data_effectivity` | provenance yan dosyası | TEXT | 100,0% |
| `add_date` | builder çalışma zamanı (UTC ISO-8601) | TEXT | 100,0% |
| `gmlId` | `gml:id` | TEXT | 100,0% |

`type` %100 doludur çünkü AIXM'de zorunludur; EAD `WPT` kayıtlarında
`ICAO`/`COORD`/`OTHER` gibi değerler taşır, antimeridyen noktalarında `OTHER`.

---

## 5. `navaids` (34 sütun)

Kaynak: `NavaidTimeSlice`. Geometri: `location/ElevatedPoint` (yoksa `Point`) →
POINT. Rota uç noktaları **bu katmana** çözülür.

| Sütun | AIXM kaynağı | Tip | Dolu |
|---|---|---|---:|
| `navaids_type` | `type` | TEXT | 100,0% |
| `navaids_designator` | `designator` | TEXT | 100,0% |
| `navaids_name` | `name` | TEXT | 93,1% |
| `navaids_flightChecked` | `flightChecked` | TEXT | **0,0%** |
| `navaids_purpose` | `purpose` | TEXT | **0,0%** |
| `navaids_signalPerformance` | `signalPerformance` | TEXT | **0,0%** |
| `navaids_courseQuality` | `courseQuality` | TEXT | **0,0%** |
| `navaids_integrityLevel` | `integrityLevel` | TEXT | **0,0%** |
| `navaids_codeICAOCountry` | `codeICAOCountry` | TEXT | **0,0%** |
| `navaids_locationElevation` | `location/ElevatedPoint/elevation` | REAL | **0,0%** |
| `navaids_locationElevationUom` | aynı elemanın `uom` niteliği | TEXT | **0,0%** |
| `navaids_locationGeoidUndulation` | `…/geoidUndulation` | REAL | **0,0%** |
| `navaids_locationVerticalDatum` | `…/verticalDatum` | TEXT | **0,0%** |
| `navaids_locationHorizontalAccuracy` | `…/horizontalAccuracy` | REAL | **0,0%** |
| `navaids_locationHorizontalAccuracyUom` | aynı elemanın `uom` | TEXT | **0,0%** |
| `navaids_availability` | `availability` (JSON) | TEXT | **0,0%** |
| `navaids_annotation*` (4) | `annotation` | TEXT | Remark 0,0% (2 kayıt), diğerleri 0,0% |
| `data_provider` | provenance | TEXT | 100,0% |
| `data_originator` | provenance | TEXT | 67,2% |
| `data_effectivity` | provenance | TEXT | 100,0% |
| `add_date` | builder çalışma zamanı | TEXT | 100,0% |
| `gmlId` | `gml:id` | TEXT | 100,0% |

**`data_originator` neden %67,2:** boş kalan 3.073 satır Jeppesen NDB
navaid'leridir. Jeppesen'in `data.json`'ında originator alanı yok — doğrulanmış
yokluk, sessiz düşürme değil. 9.359 − 6.286 = 3.073.

**`navaids_type` neden 9.357 (2 eksik):** LT'nin `MEN` ve `AYR` stub kayıtları.
Bunlar LT'nin VFR `fix`/`PointReference` yapılarından türetilmiştir; ham LT
verisinde tip ve konum tanımlı değildir, bu yüzden `type` ve `geom` NULL'dur.
Katmandaki geometrisiz iki satır bunlardır.

- **`MEN`**: EAD'de aynı designator ve `DHMI TURKIYE` originator'ıyla **iki**
  kayıt var (`VOR_DME` "IZMIR" ve `TACAN` "ADNAN MENDERES"). Tipsiz stub bu
  ikisi arasında ayırt edilemediği için **eşleştirilmemiştir**; kullanıcı kararı
  "stub kalsın". Belirsizlik `errored-features.csv`'de
  `tipsiz_navaid_birden_fazla_ana_kaynak_adayi` olarak durur.
- **`AYR`**: EAD'de bu designator'la hiç navaid yok, devredilecek bir ana kaynak
  kaydı yok. Kullanıcı kararı: NULL geometriyle katmanda kalsın.

---

## 6. `navaidComponents` (61 sütun)

`NavaidComponent` tek başına anlamı olmayan ince bir Object olduğu için kendi
alanları ile bağlı `AbstractNavaidEquipment`'ın alanları **tek satırda**
düzleştirilir. Zincir:

```
Navaid.navaidEquipment (0..∞) → NavaidComponent → theNavaidEquipment (xlink)
                                                → AbstractNavaidEquipment (Feature)
```

Her satırın **kendi gerçek konumu** vardır (bir ILS'in LOC/GP/DME'si üç ayrı
noktadadır). Rota uç noktası çözümlemesinde **kullanılmaz**.

Alt-tür dağılımı (son koşu): DME 4.663 · VOR 3.592 · NDB 3.073 · TACAN 877 ·
Localizer 548 · Glidepath 522. Alt-türlerin tam öznitelik listeleri:
[`docs/aixm-point-types/AIXM_NavaidEquipment_Attributes.md`](docs/aixm-point-types/AIXM_NavaidEquipment_Attributes.md) §2.1-2.11.

### 6.1 Bağ ve tür

| Sütun | Kaynak | Tip | Dolu |
|---|---|---|---:|
| `navaidComponents_navaidId` | üst `navaids.id` (FK) | INTEGER | 100,0% |
| `navaidComponents_equipmentType` | ekipman feature'ının eleman adı | TEXT | 100,0% |

`equipmentType`, 11 somut alt-türden hangisi olduğunu söyler ve `type`/`class`
sütunlarının izinli enum'unu belirler.

### 6.2 `NavaidComponent`'in kendi alanları

| Sütun | AIXM kaynağı | Tip | Dolu |
|---|---|---|---:|
| `navaidComponents_collocationGroup` | `collocationGroup` | TEXT | **0,0%** |
| `navaidComponents_markerPosition` | `markerPosition` | TEXT | **0,0%** |
| `navaidComponents_providesNavigableLocation` | `providesNavigableLocation` | TEXT | 70,4% |

### 6.3 Ekipman ortak tabanı

| Sütun | AIXM kaynağı | Tip | Dolu |
|---|---|---|---:|
| `navaidComponents_designator` | `designator` | TEXT | 100,0% |
| `navaidComponents_name` | `name` | TEXT | 91,1% |
| `navaidComponents_emissionClass` | `emissionClass` | TEXT | 0,2% |
| `navaidComponents_mobile` | `mobile` | TEXT | **0,0%** |
| `navaidComponents_magneticVariation` | `magneticVariation` | REAL | 32,7% |
| `navaidComponents_dateMagneticVariation` | `dateMagneticVariation` | TEXT | 9,5% |
| `navaidComponents_flightChecked` | `flightChecked` | TEXT | **0,0%** |
| `navaidComponents_locationElevation` (+`Uom`) | `location/ElevatedPoint/elevation` | REAL/TEXT | 10,4% |
| `navaidComponents_locationGeoidUndulation` | `…/geoidUndulation` | REAL | 1,7% |
| `navaidComponents_locationVerticalDatum` | `…/verticalDatum` | TEXT | 1,2% |
| `navaidComponents_locationHorizontalAccuracy` (+`Uom`) | `…/horizontalAccuracy` | REAL/TEXT | 0,2% |
| `navaidComponents_monitoring` | `monitoring` (JSON) | TEXT | **0,0%** |
| `navaidComponents_availability` | `availability` (JSON) | TEXT | 19,6% |

`authority` (`AbstractNavaidEquipment` → Organisation/Authority) **kapsam
dışıdır** — büyük bir ayrı Feature ağacıdır ve bu projede Organisation
feature'ları üretilmiyor. Kullanıcı onayıyla dışarıda bırakıldı.

### 6.4 Alt-türe özgü alanlar

Yalnızca eşleşen `equipmentType` için dolar; diğerlerinde NULL kalır.

| Sütun | AIXM kaynağı | Tip | Dolu |
|---|---|---|---:|
| `navaidComponents_type` | `type` | TEXT | 27,1% |
| `navaidComponents_class` | `class` | TEXT | 5,1% |
| `navaidComponents_frequency` (+`Uom`) | `frequency` | REAL/TEXT | 58,3% |
| `navaidComponents_channel` | `channel` | TEXT | 41,7% |
| `navaidComponents_declination` | `declination` | REAL | 0,6% |
| `navaidComponents_zeroBearingDirection` | `zeroBearingDirection` | TEXT | 27,1% |
| `navaidComponents_displace` (+`Uom`) | `displace` | REAL/TEXT | **0,0%** |
| `navaidComponents_tuningFrequencyVHF` (+`Uom`) | `tuningFrequencyVHF` | REAL/TEXT | 41,6% |
| `navaidComponents_magneticBearing` | `magneticBearing` | REAL | 1,9% |
| `navaidComponents_trueBearing` | `trueBearing` | REAL | 1,1% |
| `navaidComponents_widthCourse` | `widthCourse` | REAL | 1,2% |
| `navaidComponents_backCourseUsable` | `backCourseUsable` | TEXT | 1,1% |
| `navaidComponents_signalPerformance` | `signalPerformance` | TEXT | **0,0%** |
| `navaidComponents_courseQuality` | `courseQuality` | TEXT | **0,0%** |
| `navaidComponents_integrityLevel` | `integrityLevel` | TEXT | **0,0%** |
| `navaidComponents_slope` | `slope` | REAL | 3,4% |
| `navaidComponents_rdh` (+`Uom`) | `rdh` | REAL/TEXT | 2,6% |
| `navaidComponents_axisBearing` | `axisBearing` | REAL | **0,0%** |
| `navaidComponents_auralMorseCode` | `auralMorseCode` | TEXT | **0,0%** |
| `navaidComponents_emissionBand` | `emissionBand` | TEXT | **0,0%** |
| `navaidComponents_angleProportionalLeft/Right` | aynı adlı elemanlar | REAL | **0,0%** |
| `navaidComponents_angleCoverLeft/Right` | aynı adlı elemanlar | REAL | **0,0%** |
| `navaidComponents_angleNominal/Minimum/Span` | aynı adlı elemanlar | REAL | **0,0%** |
| `navaidComponents_doppler` | `doppler` | TEXT | **0,0%** |

`CodeDMEChannelType` (352 değer) ve `CodeMLSChannelType` (200 değer) kapalı
enum'ları **elle kopyalanmaz**; `channel` sütunu biçim kuralına göre doğrulanır
(§2.2.1 / §2.9.1).

### 6.5 Not ve provenance

| Sütun | Kaynak | Dolu |
|---|---|---:|
| `annotationDescription` | ekipman + bileşen notları (§3) | 76,9% |
| `annotationRemark` | aynı | 16,7% |
| `annotationWarning` / `Disclaimer` | aynı | **0,0%** |
| `data_provider` | provenance | 100,0% |
| `data_originator` | provenance | 76,9% |
| `data_effectivity` | provenance | 100,0% |
| `add_date` | builder çalışma zamanı | 100,0% |
| `gmlId` | `gml:id` | 100,0% |

`data_originator` %76,9: boş kalan 3.073 satır Jeppesen NDB ekipmanlarıdır
(§5'teki aynı doğrulanmış yokluk).

---

## 7. `routeSegments` (82 sütun)

Kaynak: `RouteSegmentTimeSlice` + `routeFormed` ile bağlı `RouteTimeSlice`.
Geometri: `curveExtent`'in `gml:posList`'i → LINESTRING.

### 7.1 Segmentin kendi alanları

| Sütun | AIXM kaynağı | Tip | Dolu |
|---|---|---|---:|
| `routeSegments_level` | `level` | TEXT | 99,8% |
| `routeSegments_upperLimit` (+`Uom`, +`Reference`) | `upperLimit` | REAL/TEXT | 50,6% |
| `routeSegments_lowerLimit` (+`Uom`, +`Reference`) | `lowerLimit` | REAL/TEXT | 46,9% |
| `routeSegments_minimumObstacleClearanceAltitude` (+`Uom`) | aynı ad | REAL/TEXT | **0,0%** |
| `routeSegments_pathType` | `pathType` | TEXT | 3,1% |
| `routeSegments_trueTrack` | `trueTrack` | REAL | 0,2% |
| `routeSegments_magneticTrack` | `magneticTrack` | REAL | 2,4% |
| `routeSegments_reverseTrueTrack` | `reverseTrueTrack` | REAL | 0,2% |
| `routeSegments_reverseMagneticTrack` | `reverseMagneticTrack` | REAL | 2,6% |
| `routeSegments_length` (+`Uom`) | `length` | REAL/TEXT | 3,1% |
| `routeSegments_widthLeft` / `widthRight` (+`Uom`) | aynı adlar | REAL/TEXT | **0,0%** |
| `routeSegments_turnDirection` | `turnDirection` | TEXT | **0,0%** |
| `routeSegments_signalGap` | `signalGap` | TEXT | **0,0%** |
| `routeSegments_minimumEnrouteAltitude` | `minimumEnrouteAltitude` (JSON) | TEXT | 2,9% |
| `routeSegments_minimumCrossingAtEnd` (+`Uom`, +`Reference`) | aynı ad | REAL/TEXT | **0,0%** |
| `routeSegments_maximumCrossingAtEnd` (+`Uom`, +`Reference`) | aynı ad | REAL/TEXT | **0,0%** |
| `routeSegments_designatorSuffix` | `designatorSuffix` | TEXT | **0,0%** |
| `routeSegments_availability` | `availability` (JSON) | TEXT | **0,0%** |
| `routeSegments_cardinalDirectionLeft` / `Right` | aynı adlar | TEXT | **0,0%** |
| `routeSegments_aircraftCapability` | `aircraftCapability` (JSON) | TEXT | 2,9% |
| `routeSegments_airspaceClass` | `airspaceClass` (JSON) | TEXT | **0,0%** |
| `routeSegments_designCriteria` | `designCriteria/name` (virgüllü) | TEXT | 3,1% |

`designCriteria` segmentte yoksa bağlı `Route`'un `designCriteria`'sına düşülür —
bu **bilinçli bir devralmadır**, fallback zinciri değil: AIXM'de tasarım ölçütü
rota düzeyinde de tanımlanabilir.

### 7.2 Uç noktalar (`start` / `end`)

Kaynak: `start|end/EnRouteSegmentPoint`. Aşağıdaki tablo `start` içindir; `end`
için birebir aynı sütunlar `routeSegments_end…` önekiyle vardır.

| Sütun | AIXM kaynağı | Tip | Dolu (start / end) |
|---|---|---|---|
| `routeSegments_startPointLayer` | çözülen katman adı | TEXT | 91,6% / 91,5% |
| `routeSegments_startPointId` | çözülen satır `id` (FK) | INTEGER | 91,6% / 91,5% |
| `routeSegments_startPointDesignator` | çözülen satırın designator'ı | TEXT | 91,3% / 91,2% |
| `routeSegments_startReportingATC` | `reportingATC` | TEXT | 2,9% |
| `routeSegments_startFlyOver` | `flyOver` | TEXT | **0,0%** |
| `routeSegments_startWaypoint` | `waypoint` | TEXT | **0,0%** |
| `routeSegments_startRadarGuidance` | `radarGuidance` | TEXT | **0,0%** |
| `routeSegments_startFacilityMakeup` | `facilityMakeup` (JSON) | TEXT | **0,0%** |
| `routeSegments_startRoleFreeFlight` | `roleFreeFlight` | TEXT | **0,0%** |
| `routeSegments_startRoleRVSM` | `roleRVSM` | TEXT | **0,0%** |
| `routeSegments_startTurnRadius` (+`Uom`) | `turnRadius` | REAL/TEXT | **0,0%** |
| `routeSegments_startRoleMilitaryTraining` | `roleMilitaryTraining` | TEXT | **0,0%** |

**Çözümleme:** birleşik dosyada her `xlink:href` aynı dosyadaki bir
`gml:identifier`'a işaret ettiği için çözümleme doğrudan sözlük aramasıdır
(`uuid → (katman, satır id, designator)`). `pointChoice_fixDesignatedPoint`
`designatedPoints`'e, `pointChoice_navaidSystem` `navaids`'e çözülür.

**Kaynaklarda koordinatla verilmiş uç yok.** Ham EAD kaydı uçları yalnızca
`codeId` + `codeType` olarak taşır (`WPT` → DesignatedPoint; `VOR/DME`,
`VORTAC`, `NDB`, `VOR`, `DME`, `DME/VOR`, `TACAN`, `TACVOR` → Navaid). Birleşik
AIXM'de inline `Point` uçlu segment sayısı **0**'dır (tarandı). Bunun sonucu:
segment geometrisi uç noktalar çözülerek üretilir; iki ucu da çözülemeyen
segment `NULL` geometriyle yazılır — **kayıt düşürülmez**.

> **Bilinen boşluk:** ileride bir kaynak segment ucunu koordinatla verirse
> mevcut kod bunu işlemez (ne geometri ne uç kimliği üretir). Şu an hiçbir
> kaynakta böyle bir kayıt olmadığı için tetiklenmiyor.

### 7.3 `Route`'tan devralınan alanlar

> **Önek bilinçli olarak farklıdır.** Bu tablo `route_<Attr>` sütunlarını listeler — `routeSegments_<Attr>` DEĞİL. Aynı öneki kullanmak, RouteSegment'in kendi alanlarıyla bağlı Route'un alanlarını ayırt edilemez kılardı (kullanıcı düzeltmesi).

| Sütun | AIXM kaynağı (`RouteTimeSlice`) | Dolu |
|---|---|---:|
| `route_designatorPrefix` | `designatorPrefix` | 20,5% |
| `route_designatorSecondLetter` | `designatorSecondLetter` | 98,9% |
| `route_designatorNumber` | `designatorNumber` | 98,9% |
| `route_multipleIdentifier` | `multipleIdentifier` | 1,4% |
| `route_locationDesignator` | `locationDesignator` | 96,9% |
| `route_name` | `name` | 1,1% |
| `route_type` | `type` | 3,1% |
| `route_flightRule` | `flightRule` | 3,1% |
| `route_internationalUse` | `internationalUse` | **0,0%** |
| `route_militaryUse` | `militaryUse` | **0,0%** |
| `route_militaryTrainingType` | `militaryTrainingType` | **0,0%** |

Rota kodu AIXM'de parçalıdır (`prefix` + `secondLetter` + `number` +
`multipleIdentifier`); tam kod kullanıcı kararıyla `Route.name` alanına da
yazılır.

### 7.4 Not ve provenance

`annotationDescription/Remark/Warning/Disclaimer` — `Remark` 128
satırda dolu (106 antimeridyen segmenti + 22 LT VFR segmenti, notu bağlı
`Route`'tan gelir), diğer üçü 0. `_data_provider` / `_data_originator` /
`_data_effectivity` (hepsi 100,0%), `_add_date`, `_gmlId`.

Antimeridyen bölmesinden gelen 106 segmentin `annotationRemark`'ı tam olarak şu
metni taşır (segmentin kendi notlarıyla `" | "`, `Route`'unkilerle boş satır
bırakılarak birleşmiş olarak):

```
Route segment automatically split by the AIS system at the antimeridian for display on web maps.
```

---

## 8. Validasyon politikası

`gpkg/validation_rules.py`: katman başına `alan → FieldRule(type, max_length,
enum, allow_other, pattern)`; `docs/*.md` tablolarından bire bir aktarılmıştır.
`allow_other`, AIXM'in her `Code*Type`'ında bulunan evrensel
`OTHER(:(\w|_){1,58})?` union desenini karşılar.

| İhlal | Severity | Davranış |
|---|---|---|
| Enum dışı değer | `error` | Alan null'lanır, **kayıt yine yazılır** |
| Sayısal olmayan / aralık dışı değer | `error` | Alan null'lanır, kayıt yazılır |
| Serbest metin `max_length` aşımı | `warning` | Kırpılır, tam değer logda |
| Kaynağın hiç sağlamadığı alan | — | Loglanmaz (boş değer ihlal değildir) |

`navaidComponents_type` ve `_class` sütunları `equipmentType`'a göre farklı enum
taşıdığı için alt-türe göre ayrıca doğrulanır (`EQUIPMENT_TYPE_ENUM`,
`EQUIPMENT_CLASS_ENUM`).

`errored-features.csv` sütunları: `stage, layer, record_identifier, field,
value, violation, severity`.

---

## 9. Index'ler

`gpkg/schema.py:finalize()`:

1. **Her sütunda B-tree index** — dört katmanda 182 sütun.
2. **Mekânsal index (RTree)** — katman başına `rtree_<katman>_geom` sanal
   tablosu, GeoPackage 1.2 Ek F.3'teki altı tetikleyici (insert, update1-4,
   delete) ve `gpkg_extensions` kaydı (`gpkg_rtree_index`, scope `write-only`).
3. `gpkg_contents` sınırlayıcı kutuları + `gpkg_ogr_contents` sayaçları,
   ardından `ANALYZE`.

Sınırlayıcı kutular geometri blob'undan Python tarafında hesaplanır
(`geometry_envelope()`), SpatiaLite gerekmez. Tetikleyiciler `ST_MinX` gibi
fonksiyonlara başvurur; düz SQLite'ta tanımsız olmaları sorun değildir çünkü
tetikleyici gövdesi yalnızca çalıştırıldığında çözülür — bu fonksiyonları
QGIS/GDAL sağlar.

---

## 10. Kullanıcı onayıyla kapsam dışı bırakılanlar

| Öğe | Nerede | Gerekçe |
|---|---|---|
| `navaidEquipment` iç yapısı | `navaids` | Ayrı `navaidComponents` katmanı + FK olarak modellendi |
| `authority` | `navaidComponents` | Organisation/Authority ayrı bir büyük Feature ağacı; bu projede üretilmiyor |
| CRC / veri kalitesi alanları | Jeppesen kaynağı | Düşürüldü, mapping doc'ta belirtildi |
| `points` katmanı | — | `aixm:Point` Feature değil; katman iptal edildi |

## 11. Kaynaklar arası çakışmanın katmana etkisi

Bir katmandaki satırın hangi kaynaktan geldiği, o kaynağın çakışma ayarına
bağlıdır ([`Common_Builder_Behaviour.md`](Common_Builder_Behaviour.md) §4.3):

| Katman | LT | TRNC |
|---|---|---|
| `designatedPoints` | LT kazanır (override) | LT'de varsa LT kazanır; yoksa EAD-Cyprus DCA kaydını TRNC override eder |
| `navaids` / `navaidComponents` | Ana kaynak kazanır | Aynı iki yönlü kural |
| `routeSegments` | LT kazanır (override) | TRNC kazanır (override) |

TRNC'de override ve devretme yönleri **farklı sağlayıcıları** hedefler
(`override_base_originator` = Cyprus DCA, `prefer_base_originator` = DHMI
TURKIYE); ikisi aynı kayıtta birlikte işleyebilir ve `remap` zinciri yazımdan
önce çözülür.

Kaybeden kaynağın kaydı **hiç yazılmaz** ve ona referans veren her şey kazanan
kaydın UUID'sine yönlendirilir; katmanda tek satır kalır, `xlink` bütünlüğü
korunur. Alan bazında birleştirme yapılmaz.

## 12. Karar bekleyen konu

Yok. Şemadaki 182 sütunun tamamının AIXM karşılığı kurulu ve çalışır durumda;
`%0,0` görünen sütunlar kaynakların o alanı sağlamamasındandır (§ girişteki
açıklama), eşleme eksikliği değildir.
