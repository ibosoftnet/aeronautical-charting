# ICAO FIR/UIR (2021, ibosoft-tailored) → AIXM 5.2 Airspace

Üretici: `generate_aixm.py` · Çıktı: `../icao-fir-uir-airspace-aixm.xml` ·
Log: `errored-features.log` · Rol: **ana kaynak**

| Girdi | İçerik |
|---|---|
| `../fir-2021-ibosoft-tailored.json` | 344 feature (325 Polygon, 19 MultiPolygon). Kopyası alındığı yer: `aeronautical-data/Airspaces/ICAO/FIR/fir-2021-ibosoft-tailored.json` (Türkiye geometrisi AIXM'den, Tel Aviv ICAO kodu düzeltmeli) |
| `../data.json` | `data_provider` = `ICAO GIS`, `data_effectivity` = `2021 (Non-AIRAC)`; originator **yok** (kullanıcı kararı) |

## 1. Alan eşlemesi (kullanıcı kararları)

| Özellik | AIXM | Kural |
|---|---|---|
| `OBJECTID` | `gml:id` = `FIR_AS_<OBJECTID>`, `gml:identifier` = uuid5(`IcaoFirAirspace:<OBJECTID>`) | 344 tekil |
| `KIND` | `type` | `FIR` / `UIR`. Başka değer yazılmaz (ölçüldü: `NIL1`, `NIL2` kayıtlarında boş) |
| `ICAOCODE` | `designator` | Boşsa yazılmaz |
| `FIRname` | `name` | |
| `REMARKS`, `REMARKS2`, `REMARKS3` | `annotation` | Her biri ayrı `REMARK` notu |
| `REGION` | `ibosoftais:AirspaceExtension/regionIcao` | ICAO bölgesi |
| `SUPP_REGIO` | `ibosoftais:AirspaceExtension/regionSupProc` | Doc 7030 bölgesi |
| geometri | `horizontalProjection` | antimeridyen güvenli MultiPolygon |
| — | `upperLimit`, `lowerLimit` | **Yazılmaz**: kaynakta sayısal seviye yok; eksik bilgi boş kalır (kullanıcı kararı) |
| `data.json` | provenance kutusu | originator yok → yazılmaz |

## 2. Aktarılmayan kaynak alanları

| Özellik | Durum |
|---|---|
| `ULC`, `UPPER`, `LOWER` | Kodlu katman göstergeleri (`LC`, `UC`, `U`, `L`); sayısal seviye taşımıyor ve anlamları doğrulanmadı — kullanıcı kararı: eksik bilgi boş |
| `RESP` | ICAO bölge ofisi (ör. `PARIS`) — AIXM Airspace'te karşılığı yok |
| `NOM_COMP`, `HISTORIC`, `PURE`, `ET_ID`, `Id`, `OBJECTID_1` | Kaynak veri setinin iç alanları |
| `centlong`, `centlat`, `AREAsqkm`, `PERIMEkm`, `Shape_Leng`, `Shape__Area`, `Shape__Length` | Geometriden türetilmiş ölçüler |
| `data_provider` (özellik) | Her kayıtta `ICAO GIS` — provenance `data.json`'dan aynı değerle yazılır |

## 3. Birleşik veride çıkarılanlar

LTAA ve LTBB bu kaynaktan üretilir ama birleştiricide `../../excludes/icao-fir-lt.json` ile düşer; ikisi `tailored-LT` kaynağında AIP bilgileriyle tutulur.

## 4. Geçerlilik

`gml:validTime` başlangıcı `unknown`; veri setinin yılı provenance
kutusundadır.

Çalıştırma: `start-generate-aixm.bat`. Doğrulama:
`py ../../../../common/data_build_common/validate_aixm.py ../icao-fir-uir-airspace-aixm.xml`.
