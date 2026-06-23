# AIXM Obstacle Data → Spatial GeoPackage Converter

## Amaç

`aeronautical-data/Obstacles/Area-1/<ülke-kodu>/*.xml` altındaki AIXM 5.1
`VerticalStructure` (engel) verilerini, tüm alt klasörleri tarayıp birleştiren,
spatial index'li, tek bir GeoPackage'a dönüştüren bir script + başlatma
batch dosyası.

## Kapsam

- Girdi: `Obstacles/Area-1/*/*.xml` (her alt klasör bir ülke/alan kodu, örn. `LT`).
- Çıktı: `Obstacles/Area-1/obstacles.gpkg`, tek katman `obstacles`.
- Repodaki diğer dönüştürücülerle aynı yaklaşım: saf Python stdlib
  (`sqlite3`, `xml.etree.ElementTree`, `struct`), harici bağımlılık yok
  (GDAL bu makinede kurulu değil).

## Şema Doğrulaması

Alan adları, repo içinde bulunan resmi AIXM 5.1 XSD'lerine karşı doğrulandı
(`AIS/ais-pib-api/docs/notams/aixm-5-1-schema/AIXM_Features.xsd` ve
`aeronautical-data/ATS Routes/ibodata/docs/AIXM_Features_annotated.xsd`).

- `VerticalStructurePropertyGroup` → `name`, `type`, `lighted`, `group`,
  `designator` (+ ~15 kullanılmayan opsiyonel alan: length, width, radius,
  markingICAOStandard, marker, placeName, dataAssessmentStatus, marked,
  arrestingDevice, vb.)
- `AbstractAIXMTimeSliceType` (tüm AIXM feature'larında ortak) →
  `interpretation`, `sequenceNumber`, `correctionNumber`, `featureLifetime`,
  `gml:validTime/TimePeriod/beginPosition`.
- `VerticalStructurePartPropertyGroup` → `verticalExtent`, `type`,
  `designator`, `horizontalProjection_location` (point/line/polygon
  seçeneklerinden biri — bu veri setinde her zaman point), `lighting`
  (unbounded).
- `LightElementPropertyGroup` → `colour` (+ kullanılmayan: intensityLevel,
  intensity, type, location, direction, lightingTechnology).
- `ElevatedPointPropertyGroup` → `elevation` (+ kullanılmayan:
  geoidUndulation, verticalDatum).

`LT_ENR_5_4_Obstacles_AIXM_5_1.xml` (7121 kayıt) tüm dosya genelinde
`grep -c` ile tarandı: yukarıdaki "kullanılmayan" alanların hiçbiri mevcut
veride yok (hepsi 0 sonuç). Bu yüzden kolon şemasına eklenmiyor —
GeoPackage'da boş kolon biriktirmek yerine, gerçekte var olan alanlarla
sınırlı tutuluyor (GDAL'ın bu dosya için ürettiği `.gfs` önbelleğiyle de
örtüşüyor).

Şema, bir `VerticalStructure`'ın birden fazla `part` ve her `part`'ın
birden fazla `lighting` içerebileceğine izin veriyor (`maxOccurs="unbounded"`).
Mevcut LT verisinde bu sayılar her zaman 1:1:1 (7121 structure = 7121 part =
7121 light = 7121 point), ama script genel/sağlam yazılacak: her `part`
üzerinde döngü (satır birimi = part), bir part'ta birden fazla `lighting`
varsa `colour` değerleri virgülle birleştirilecek. `horizontalProjection_location`
dışındaki geometri seçenekleri (`_surfaceExtent`, `_linearExtent`) bu veri
setinde hiç kullanılmıyor; böyle bir part'a rastlanırsa atlanıp sayılacak
(point geometri yoksa satır yazılmaz).

## Kolon Şeması

`identifier`, `interpretation`, `sequenceNumber` (INT), `correctionNumber`
(INT), `beginPosition`, `featureLifetime_beginPosition`, `name`, `type`,
`lighted`, `group`, `verticalExtent` (INT), `verticalExtent_uom`,
`part_type`, `designator`, `elevation` (INT), `elevation_uom`, `colour`,
`country`, `source_file`.

- `type` (structure seviyesi) / `part_type` (part seviyesi) ve
  `beginPosition` (validTime) / `featureLifetime_beginPosition` —
  AIXM'de aynı isimle iki kez geçtiği için parent-prefix ile ayrıştırıldı
  (mevcut `_uom` ekleme kuralıyla aynı desen).
- `country`: dosyanın bulunduğu alt klasör adı (örn. `LT`).
- `source_file`: kaynak XML dosya adı (izlenebilirlik için).

## Geometri

`gml:pos` "lat lon" (boşlukla ayrılmış) → GeoPackage WKB Point `(lon, lat)`,
EPSG:4326.

## Spatial Index

GeoPackage spesifikasyonuna tam uyumlu RTree extension: `rtree_obstacles_geom`
virtual table + 6 standart trigger (insert/update/delete kendiliğinden
güncellenir) + `gpkg_extensions` kaydı (`gpkg_rtree_index`). Mevcut
`export_mora_to_gpkg.py`'deki gibi sadece statik bir rtree tablosu değil,
trigger'larla kendini koruyan tam spesifikasyon.

## Dosyalar

- `Obstacles/Area-1/build_obstacles_gpkg.py`
- `Obstacles/Area-1/convert_obstacles.bat` (mevcut `convert_navaids.bat`
  pattern'i: `chcp 65001`, `py build_obstacles_gpkg.py`, errorlevel kontrolü,
  `pause`)

## Hata Toleransı

- Alt klasördeki dosya AIXM mesajı gibi görünmüyorsa (kök etiket kontrolü)
  atlanır.
- `identifier` veya geçerli point geometrisi olmayan part'lar sayılıp
  atlanır.
- Var olan `obstacles.gpkg` silinip yeniden yazılır (QGIS'te açıksa
  `PermissionError` toleranslı).
