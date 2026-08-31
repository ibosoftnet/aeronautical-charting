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
| `designatedPoints` | `DesignatedPoint` | POINT | 28 | 152.040 |
| `navaids` | `Navaid` | POINT | 60 | 9.357 |
| `navaidComponents` | `NavaidComponent` + `AbstractNavaidEquipment` | POINT | 100 | 13.362 |
| `routeSegments` | `RouteSegment` (+ `Route`) | LINESTRING | 83 | 92.976 |

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
| Ekipman alt-türüne özgü | `navaidComponents_<AltTür>_<alan>` → `navaidComponents_Glidepath_slope` — ortak taban önek almaz (§6.1) |
| Rota kökenli (Route feature'ından) | `route_<Attr>` → `route_designatorNumber` — **`routeSegments_` DEĞİL**, RouteSegment'in kendi alanlarından ayırt edilsin diye |
| Uç nokta | `routeSegments_<start\|end><Attr>` → `routeSegments_startFlyOver` |

**İstisna — katman önekisiz sütunlar.** `annotation`, provenance ve kimlik
alanları her katmanda birebir aynı yapıyı taşır; tabloya özgü bir anlamları
olmadığı için **önek almazlar** (kullanıcı kararı):

| Alan | Sütun |
|---|---|
| `annotation` (4 purpose) | `annotationDescription`, `annotationRemark`, `annotationWarning`, `annotationDisclaimer` |
| Provenance | `data_provider`, `data_originator`, `data_effectivity`, `add_date` |
| Kimlik | `aixm_gml_id`, `aixm_uuid` — her katmanın son iki sütunu (aşağıda) |
| ATS rota durumu (türetilmiş) | `atsStatus_*` — yalnızca `designatedPoints` ve `navaids`'te |
| Navaid ↔ Component bağı | `associatedComponent_<AltTür>` (navaids), `associatedNavaid` / `associatedNavaidType` (navaidComponents) — virgüllü liste (§6.3) |
| Harita etiketi (türetilmiş) | `navaidLabeling_*` — yalnızca `navaids` ve `navaidComponents`'te |
| Sembol geometrisi (türetilmiş) | `navaidSymbology_*` — `declination` hem `navaids` hem `navaidComponents`'te, `GPAssociatedLOCTrueBrg` yalnızca `navaidComponents`'te |

Bu istisna dışındaki tüm sütunlar yukarıdaki genel kurala göre katman önekli
kalır (`designatedPoints_designator`, `navaids_type` gibi).

### Kimlik sütunları

Her katman kaynak AIXM feature'ının **iki** kimliğini de taşır (kullanıcı
kararı). İkisi farklı şeydir ve biri diğerinin yerini tutmaz:

| Sütun | AIXM karşılığı | Kapsam |
|---|---|---|
| `aixm_gml_id` | `gml:id` | **Belge içi.** Birleşik AIXM dosyasında benzersizdir, kaynak önekini taşır (`EAD_DP_…`, `LT_VRP_BAFA`, `JEPP_NAV_…`) ve hangi kaynaktan geldiğini okunur biçimde gösterir. Belge yeniden üretildiğinde değişebilir |
| `aixm_uuid` | `gml:identifier` (`codeSpace="urn:uuid:"`) | **Belgeden bağımsız, kalıcı kimlik.** AIXM içindeki tüm çapraz referanslar (`xlink:href="urn:uuid:…"`) buna bakar; kaynak üreticileri onu girdi anahtarından deterministik olarak üretir, yani aynı nokta her AIRAC'ta aynı uuid'i alır |

Değerler `merge/aixm_reader.py`'deki `gml_id_of()` ve `uuid_of()` ile okunur;
`uuid_of()` değeri BÜYÜK HARFE çevirir.

İki tabloda kimlik, satırı oluşturan **iki** AIXM nesnesinden yalnızca birine
aittir:

* **`navaidComponents`** — kimlik, bağlı `AbstractNavaidEquipment`
  **feature**'ınındır. Satıra alanlarını veren `NavaidComponent` AIXM'de bir
  *Object*'tir, Feature değildir: yalnızca `gml:id` taşır, `gml:identifier`'ı
  yoktur (doğrulandı). Bir ekipman birden fazla Navaid tarafından
  paylaşılabildiği için ebeveyn bağı ayrıca `associatedNavaid` sütunundadır.
* **`routeSegments`** — kimlik, `RouteSegment` feature'ınındır. `route_*`
  sütunlarını besleyen `Route` feature'ının kendi `gml:id`/`gml:identifier`
  değeri **taşınmaz**; Route ayrı bir katman olmadığı için (§1.2) bağlantı
  `route_designator*` alanları üzerinden kurulur.

`atsStatus_*` alanları AIXM'den okunmaz; `routeSegments` yazıldıktan sonra
ondan türetilir. Tam tanımları, kuralları ve ölçülen dağılımları ayrı
dokümandadır: [`ATS_Status_Fields.md`](ATS_Status_Fields.md).

`navaidLabeling_*` alanları da AIXM'den okunmaz. Bunlar harita etiketinin
hangi öğeleri göstereceğini navaid **tipine** göre belirler ve eksik
frekans/kanal bilgisini ICAO eşleştirme tablosundan türetir — AIXM'de frekans
ve kanal Navaid feature'ında değil bağlı ekipmanda durduğu için `navaids`
satırları bileşenlerden beslenir. Ayrıntı:
[`Navaid_Labeling_Fields.md`](Navaid_Labeling_Fields.md).

`navaidSymbology_*` ise etiket metnini değil sembolün **çizimini** besler. İki
alanı var: `GPAssociatedLOCTrueBrg` (yalnızca `navaidComponents`) — Glidepath
hüzmesinin yönü AIXM'de `Glidepath`'te değil kardeş `Localizer`'da durur, bu
sütun onu taşır; `declination` (`navaids` ve `navaidComponents`) — pusula gülü
sembolünün döndürme açısı, VOR/TACAN bileşeninin kendi AIXM `declination`
alanından, yalnızca VOR/VOR_DME/TACAN/VORTAC navaid türlerinde. Ayrıntı:
[`Navaid_Symbology_Fields.md`](Navaid_Symbology_Fields.md).

**Sütun tipi** `gpkg/schema.py:column_type()` ile belirlenir: `*Uom` ve
`*Reference` her zaman TEXT; `*PointId` INTEGER; bilinen sayısal
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
| `navaidEquipment` | — | Ayrı `navaidComponents` katmanı + **çift yönlü** bağ (§6.3) | Kullanıcı kararı |

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

## 4. `designatedPoints` (27 sütun)

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
| `aixm_gml_id` | `gml:id` | TEXT | 100,0% |
| `aixm_uuid` | `gml:identifier` | TEXT | 100,0% |

`type` %100 doludur çünkü AIXM'de zorunludur; EAD `WPT` kayıtlarında
`ICAO`/`COORD`/`OTHER` gibi değerler taşır, antimeridyen noktalarında `OTHER`.

---

## 5. `navaids` (58 sütun)

Kaynak: `NavaidTimeSlice`. Geometri: `location/ElevatedPoint` (yoksa `Point`) →
POINT. Rota uç noktaları **bu katmana** çözülür.

| Sütun | AIXM kaynağı | Tip | Dolu |
|---|---|---|---:|
| `navaids_type` | `type` | TEXT | 100,0% |
| `navaids_designator` | `designator` | TEXT | 100,0% |
| `navaids_name` | `name` | TEXT | 98,9% |
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
| `aixm_gml_id` | `gml:id` | TEXT | 100,0% |
| `aixm_uuid` | `gml:identifier` | TEXT | 100,0% |

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

> **GEÇİCİ — ILS ailesinde `name` pist bilgisi taşır.** `ILS`, `ILS_DME`,
> `LOC`, `LOC_DME` navaid'lerinde ve `Localizer`/`Glidepath` bileşenlerinde
> kaynakta `name` **hiç yok**; yerine `RWY 04R` biçiminde pist yönü yazılıyor.
> ILS bileşeni DME'lerde mevcut adın **sonuna** ekleniyor
> (`BRUSSELS NATIONAL RWY 25R`), ad ezilmiyor.
>
> Sebep: AIXM'de bunun doğru yeri `Navaid/runwayDirection` association'ıdır ama
> `AirportHeliport` ve `RunwayDirection` feature'ları bu projede **henüz
> implemente edilmedi**, yani association'ın hedefi yok. O feature'lar
> eklendiğinde bu çözüm **kaldırılmalıdır**. Ayrıntı:
> [`EAD-SDO_Field_Mapping.md` §4.3](data-sources/EAD-SDO/generate-aixm-data/EAD-SDO_Field_Mapping.md).

---

## 6. `navaidComponents` (98 sütun)

`NavaidComponent` tek başına anlamı olmayan ince bir Object olduğu için kendi
alanları ile bağlı `AbstractNavaidEquipment`'ın alanları **tek satırda**
düzleştirilir. Zincir:

```
Navaid.navaidEquipment (0..∞) → NavaidComponent → theNavaidEquipment (xlink)
                                                → AbstractNavaidEquipment (Feature)
```

Her satırın **kendi gerçek konumu** vardır (bir ILS'in LOC/GP/DME'si üç ayrı
noktadadır). Rota uç noktası çözümlemesinde **kullanılmaz**.

Alt-tür dağılımı (son koşu): DME 4.667 · VOR 3.594 · NDB 3.073 · TACAN 877 ·
Localizer 550 · Glidepath 524 · MarkerBeacon 77. Alt-türlerin tam öznitelik
listeleri:
[`docs/aixm-point-types/AIXM_NavaidEquipment_Attributes.md`](docs/aixm-point-types/AIXM_NavaidEquipment_Attributes.md) §2.1-2.11.

### 6.1 Sütun adlandırması — ortak vs alt-türe özgü

| Alan sınıfı | Sütun adı | Örnek |
|---|---|---|
| `NavaidComponent`'in kendi alanları | `navaidComponents_<alan>` | `navaidComponents_markerPosition` |
| Ekipman **ortak tabanı** (`NavaidEquipmentPropertyGroup`) | `navaidComponents_<alan>` | `navaidComponents_designator` |
| **Alt-türe özgü** her alan | `navaidComponents_<AltTür>_<alan>` | `navaidComponents_Glidepath_slope` |

Ortak taban 11 alt-türde de **birebir aynıdır**, o yüzden önek almaz:
`designator`, `name`, `emissionClass`, `mobile`, `magneticVariation`,
`dateMagneticVariation`, `flightChecked`, `location*` (6 sütun), `monitoring`,
`availability`.

**Aynı alan adı birden çok alt-türde geçebilir** — `frequency` altı alt-türde
(VOR, Localizer, Glidepath, MarkerBeacon, NDB, SDF), `channel` üçünde
(DME, TACAN, Azimuth), `type` üçünde (VOR, DME, Azimuth). Bunlar AIXM'de ayrı
elemanlardır ve bir kısmı **farklı enum taşır**. Bu yüzden her alt-tür kendi
sütununu alır (kullanıcı kararı):

```
navaidComponents_VOR_frequency        navaidComponents_DME_channel
navaidComponents_NDB_frequency        navaidComponents_TACAN_channel
navaidComponents_Localizer_frequency  navaidComponents_Azimuth_channel
…
```

Tablo bilinçli olarak **seyrektir**: her satırda yalnızca kendi alt-türünün
sütunları dolar. Karşılığında iki kazanç var:

- Hangi alanın hangi alt-türe ait olduğu **sütun adından** okunur.
- Çakışan enum'lar ayrışır. `type` (CodeVORType / CodeDMEType /
  CodeMLSAzimuthType), `class` (CodeMarkerBeaconSignalType / CodeNDBUsageType)
  ve `channel` (CodeDMEChannelType / CodeTACANChannelType / CodeMLSChannelType)
  eskiden tek sütunu paylaşıyordu; doğrulama `equipmentType`'a bakıp doğru
  enum'u seçmek zorundaydı, `channel` ise hiç doğrulanamıyordu. Artık her sütun
  kendi kuralını alır (§8).

Sütun listesi **elle yazılmaz**: `gpkg/schema.EQUIPMENT_SUBTYPE_FIELDS`
sözlüğünden türetilir. Alt-tür → alan eşlemesinin tamamı XSD'den doğrulanmıştır
(`<group name="<AltTür>PropertyGroup">`).

### 6.2 Alt-türe özgü alanlar

```
VOR             : type, frequency(+Uom), zeroBearingDirection, declination
DME             : type, channel, displace(+Uom), tuningFrequencyVHF(+Uom)
TACAN           : channel, declination, tuningFrequencyVHF(+Uom)
Localizer       : frequency(+Uom), magneticBearing, trueBearing, declination,
                  widthCourse, backCourseUsable, signalPerformance,
                  courseQuality, integrityLevel
Glidepath       : frequency(+Uom), slope, rdh(+Uom), signalPerformance,
                  courseQuality, integrityLevel
MarkerBeacon    : class, frequency(+Uom), axisBearing, auralMorseCode
NDB             : frequency(+Uom), class, emissionBand
SDF             : frequency(+Uom), magneticBearing, trueBearing
Azimuth         : type, channel, trueBearing, magneticBearing,
                  angleProportionalLeft/Right, angleCoverLeft/Right
Elevation       : angleNominal, angleMinimum, angleSpan
DirectionFinder : doppler
```

`SDF`, `Azimuth`, `Elevation`, `DirectionFinder` sütunları şu an **boştur** —
kaynaklarda bu alt-türlerden feature yok. Sütunlar kaldırılmaz: veri gelirse
şema değişmeden dolar.

> **Giderilen sessiz atlama:** `merge/aixm_reader.EQUIPMENT_FEATURES` daha önce
> yalnızca 7 alt-tür sayıyordu; bu dördü listede olmadığı için
> `run_gpkg` onları **sessizce atıyordu** — ne bileşen satırı olurdu, ne de
> birleştirmedeki "düşen navaid'in ekipmanı" mantığı görürdü. Liste 11'e
> tamamlandı.

### 6.3 Navaid ↔ Component çift yönlü bağ

AIXM'de ilişki `Navaid.navaidEquipment → NavaidComponent → theNavaidEquipment`
xlink zinciriyle kurulur ve **çok-çoka**dır. GeoPackage'da iki yönden birden
temsil edilir:

| Katman | Sütun | İçerik |
|---|---|---|
| `navaids` | `associatedComponent_<AltTür>` × 11 | O navaid'in ilgili tipteki bileşenlerinin `navaidComponents.id` listesi |
| `navaidComponents` | `associatedNavaid` | Ebeveyn `navaids.id` listesi |
| `navaidComponents` | `associatedNavaidType` | Karşılık gelen `navaids_type` listesi, **aynı sırada** |

Üçü de virgülle ayrılmış **liste** tutar ve katman öneki taşımaz.

**Neden liste:**

- Bir navaid aynı tipten birden fazla bileşen taşıyabilir — ölçüldü, **31
  ILS'te ikişer `MarkerBeacon`** var (OUTER + MIDDLE; veride MIDDLE 43,
  OUTER 31, INNER 3).
- Bir ekipman birden fazla navaid tarafından **paylaşılabilir** — ölçüldü,
  **275 ekipman 2–7 navaid'e ait** (230 DME, 45 TACAN; biri 7 navaid'e).

> **Giderilen veri kaybı:** önceki `navaidComponents_navaidId` tek bir FK'ydı ve
> paylaşımlı ekipmanın **yalnızca son görülen ebeveynini** kaydediyordu.
> `EAD_DME_AS_4720672` hem `EAD_NAV_AS_4699536` hem `EAD_NAV_AS_4720669`
> tarafından kullanılırken tabloda yalnızca ikincisi görünüyordu. Artık
> `associatedNavaid = "550,2181"`, `associatedNavaidType = "VOR_DME,VOR_DME"`.

Örnek — `IBR` (ILS_DME, navaid id 12):

```
navaids  id=12  associatedComponent_Localizer    = "24"
                associatedComponent_Glidepath    = "25"
                associatedComponent_DME          = "26"
                associatedComponent_MarkerBeacon = "13290,13291"

navaidComponents id=13290 MarkerBeacon MIDDLE  associatedNavaid="12" Type="ILS_DME"
                 id=13291 MarkerBeacon OUTER   associatedNavaid="12" Type="ILS_DME"
```

İki yönün tutarlılığı build sırasında ölçülür: her iki yönde de ihlal **0**,
`associatedNavaid` ile `associatedNavaidType` uzunluk uyuşmazlığı **0**.

### 6.4 Not ve provenance

`annotationDescription/Remark/Warning/Disclaimer` — hem `AbstractNavaidEquipment`'ın
hem `NavaidComponent`'in notları aynı 4 sütunda, aralarında boş satır bırakılarak
birleşir (§3). `data_provider` / `data_originator` / `data_effectivity` /
`add_date`, `aixm_gml_id` ve `aixm_uuid` katman öneksizdir (kimlik ekipman feature'ınındır, bkz. §2). `navaidLabeling_*` sütunları için
ayrıca bkz. `gpkg/navaid_labeling.py`.

`authority` (`AbstractNavaidEquipment` → Organisation/Authority) **kapsam
dışıdır** — büyük bir ayrı Feature ağacıdır ve bu projede Organisation
feature'ları üretilmiyor. Kullanıcı onayıyla dışarıda bırakıldı.

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
`_data_effectivity` (hepsi 100,0%), `_add_date`, ayrica katman öneksiz `aixm_gml_id` ve `aixm_uuid` (RouteSegment feature'ının kimliği; Route'unki taşınmaz, bkz. §2).

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

1. **Her sütunda B-tree index** — dört katmanda 271 sütun.
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

Yok. Şemadaki 271 sütunun tamamının AIXM karşılığı kurulu ve çalışır durumda;
`%0,0` görünen sütunlar kaynakların o alanı sağlamamasındandır (§ girişteki
açıklama), eşleme eksikliği değildir.
