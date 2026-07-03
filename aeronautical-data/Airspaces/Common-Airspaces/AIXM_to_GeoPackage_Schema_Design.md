# Common-Airspaces GeoPackage Şema Tasarımı (AIXM 5.2 → GeoPackage)

Bu doküman, `AIXM_Airspace_Attributes.md`'de listelenen tam AIXM 5.2 Airspace
attribute setinin, merkezi hava sahası GeoPackage veritabanına nasıl
işleneceğini ve bu işlemde AIXM'in tam modelinden nerelerde ve neden
**bilinçli olarak sapıldığını** tanımlar.

Durum: **Taslak — kullanıcı onayı bekliyor** (brainstorming aşaması, henüz
implementasyona geçilmedi).

---

## 1. Genel Mimari Kararları

- **Tek düz tablo** (`airspaces`) — GeoPackage'ın flat-table doğasına uygun.
  AIXM'in iç içe geçmiş (nested/repeating) yapısı çözülüp (flatten) tek
  satıra indirgenir.
- **Geometri**: `MULTIPOLYGON`, `EPSG:4326` (WGS84).
- **Temporal model yok**: AIXM'in `timeSlice`/`validTime` geçmişi tutulmaz.
  Her satır sadece güncel/aktif durumu temsil eder. Yeni veri geldiğinde
  tablo yeniden oluşturulur (upsert/history mekanizması yok).
- **Kimlik**: Basit `INTEGER PRIMARY KEY AUTOINCREMENT`. AIXM `gml:id` veya
  kaynak sistem ID'si saklanmaz; yeniden içe aktarmada eşleştirme/update
  senaryosu şimdilik yok.
- **Karmaşık/ayrık geometriler**: AIXM'de bir Airspace, `geometryComponent`
  altında birden fazla `AirspaceVolume`'u `UNION`/`SUBTR`/`INTERS` ile
  birleştirebilir (computed/aggregate geometri). Bu veritabanında böyle bir
  aggregation modellenmez — **ayrık veya bileşik hava sahalarının farklı
  bölümleri, import aşamasında ayrı satırlar (ayrı "airspace" kayıtları)
  olarak işlenir.** Her satırın geometrisi tek, kendi başına anlamlı bir
  MultiPolygon'dur.

---

## 2. Tablo Şeması: `airspaces`

Kolon adları, AIXM dışı olan birkaç alan (`id`, `source`, `dataProvider`,
`add_date`) hariç, **AIXM 5.2 attribute isimleriyle birebir aynı** (camelCase)
kullanılır. Bu, veri sözlüğü ile şema arasında doğrudan izlenebilirlik
sağlar ve import/export script'lerinde eşlemeyi (mapping) basitleştirir.

| Kolon | Tip (SQLite/GPKG) | AIXM Karşılığı | Not |
|---|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | — | AIXM dışı, yapay anahtar |
| `horizontalProjection` | MULTIPOLYGON (EPSG:4326) | `theAirspaceVolume.horizontalProjection` | GeoPackage geometri kolonu |
| `type` | TEXT | `type` (CodeAirspaceType) | FIR, TMA, CTR, R, D, P, ATZ... |
| `designator` | TEXT | `designator` | |
| `name` | TEXT | `name` | |
| `localType` | TEXT | `localType` | |
| `designatorICAO` | TEXT | `designatorICAO` | YES/NO |
| `controlType` | TEXT | `controlType` | CIVIL/MIL/JOINT |
| `classification` | TEXT | `class.classification` | A-G, tekleştirilmiş |
| `upperLimit` | TEXT | `theAirspaceVolume.upperLimit` | sayı veya UNL/GND/FLOOR/CEILING olabildiği için TEXT |
| `upperLimitUom` | TEXT | `upperLimit/@uom` | AIXM'de ayrı eleman değil, XML attribute — FT/M/FL/SM |
| `upperLimitReference` | TEXT | `upperLimitReference` | SFC/MSL/W84/STD |
| `lowerLimit` | TEXT | `theAirspaceVolume.lowerLimit` | aynı format |
| `lowerLimitUom` | TEXT | `lowerLimit/@uom` | AIXM'de ayrı eleman değil, XML attribute |
| `lowerLimitReference` | TEXT | `lowerLimitReference` | |
| `activity` | TEXT | `activation.activity` | tekleştirilmiş |
| `status` | TEXT | `activation.status` | tekleştirilmiş |
| `annotationDescription` | TEXT | `annotation.translatedNote`/`note` (purpose=DESCRIPTION) | serbest metin |
| `annotationRemark` | TEXT | `annotation.translatedNote`/`note` (purpose=REMARK) | serbest metin |
| `annotationWarning` | TEXT | `annotation.translatedNote`/`note` (purpose=WARNING) | serbest metin |
| `annotationDisclaimer` | TEXT | `annotation.translatedNote`/`note` (purpose=DISCLAIMER) | serbest metin |
| `source` | TEXT | — (AIXM dışı) | jeppesen / tailored / aixm-icao vb. |
| `dataProvider` | TEXT | — (AIXM dışı) | dhmi vb., opsiyonel |

---

## 3. AIXM'den Sapılan Noktalar (Deviations) ve Gerekçeleri

Bu bölüm, `AIXM_Airspace_Attributes.md`'deki tam attribute listesine göre
**neyin, neden çıkarıldığını veya basitleştirildiğini** açıkça belgeler.
Amaç: ileride biri "bu alan neden yok?" diye sorduğunda gerekçeyi burada
bulabilmek.

| AIXM Attribute/Yapısı | Karar | Gerekçe |
|---|---|---|
| `timeSlice` / `validTime` / `sequenceNumber` / `correctionNumber` (temporal model) | **Tutulmuyor** | Sadece güncel durum yeterli görüldü; versiyon geçmişi ihtiyacı yok (şimdilik). |
| `geometryComponent` (çoklu `AirspaceVolume`, `operation`: UNION/SUBTR/INTERS, `operationSequence`) | **Tutulmuyor** — yerine ayrık satırlar | Aggregation mantığı GeoPackage'da modellenmiyor; ayrık/bileşik sahaların parçaları import'ta ayrı airspace kaydına bölünüyor. |
| `class` (çoklu, yükseklik bantlı `AirspaceLayerClass` + `associatedLevels`) | **Tekleştirildi** → tek `classification` alanı | Çok katmanlı sınıf gereken durumlar da ayrı satırlara bölünecek (aggregation kararıyla aynı mantık). |
| `activation` (çoklu kayıt: `activity`, `status`, `levels`, `user`, `aircraft`, schedule) | **Tekleştirildi** → tek `activity` + `status` alanı | Zamanlama (schedule), kullanıcı/organizasyon ve uçak detayı bu aşamada gereksiz görüldü; gerekirse ayrı bir Activation/NOTAM modülüyle sonra eklenebilir. |
| `annotation` (çoklu `Note`) + `annotation.purpose` (`CodeNotePurposeType`) | **purpose'a göre 4 serbest metin kolonu**: `annotationDescription`, `annotationRemark`, `annotationWarning`, `annotationDisclaimer` | `purpose` enum'u ayrı bir kolon yerine kolon **adına** gömüldü; böylece aynı saha farklı purpose'lu notları (WARNING + DISCLAIMER + REMARK) aynı anda taşıyabilir. Hâlâ tekleştirilen: aynı purpose'tan birden fazla `Note` (metinler birleştirilir), `propertyName` ve çok dillilik (`translatedNote` çokluğu) tutulmuyor. |
| `protectedRoute` (Route feature'ına association) | **Tutulmuyor** | Nadir kullanılan, karşılıklı bağımlılık gerektiren bir özellik. |
| `contributorAirspace` / `dependency` (`AirspaceVolumeDependency`, başka bir Airspace'e geometri bağımlılığı) | **Tutulmuyor** | Aynı gerekçe — nadir, karmaşık ilişkisel bağ. |
| `centreline`, `width` (koridor şekli — MTR gibi) | **Tutulmuyor** | `horizontalProjection` zaten nihai poligonu içerdiği için koridor iskelet bilgisi (centreline/width) ayrıca gerekmiyor. |
| `upperLowerSeparation` | **Tutulmuyor** | Nadir kullanılan, alt/üst hava sahası ayrım bilgisi; ihtiyaç doğarsa eklenir. |
| `location` (AirspaceVolume için tekil nokta referansı) | **Tutulmuyor** | `geom` zaten tam poligonu sağladığı için ayrı bir nokta referansına gerek yok. |
| `discreteLevelSeries` (StandardLevelColumn association) | **Tutulmuyor** | Ayrı bir feature'a association; kapsam dışı. |
| Kaynak/izlenebilirlik (`source`, `dataProvider`) | **AIXM'de karşılığı yok, eklendi** | Merkezi veritabanı birden fazla kaynaktan (Jeppesen, tailored, AIXM-ICAO, DHMI vb.) veri birleştireceği için provenance takibi gerekli görüldü. |
| `gml:id` / kaynak sistem ID'si (`sourceId`) | **Tutulmuyor** | Yeniden içe aktarmada eşleştirme/update senaryosu şimdilik planlanmıyor; basit autoincrement `id` yeterli görüldü. |

---

## 4. Sonraki Adım

Bu tasarım kullanıcı tarafından onaylandıktan sonra:
1. Tasarım dokümanı kesinleştirilecek.
2. Import/dönüştürme script'i için ayrı bir implementasyon planı çıkarılacak
   (AIXM-ICAO JSON / Jeppesen / ICAO FIR kaynaklarının bu şemaya nasıl
   eşleneceği dahil).
