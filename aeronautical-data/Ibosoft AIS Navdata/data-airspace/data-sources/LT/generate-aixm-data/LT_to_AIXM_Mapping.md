# LT (DHMİ AIS) hava sahası GeoJSON → AIXM 5.2 Airspace

Üretici: `generate_aixm.py` · Çıktı: `../lt-airspace-aixm.xml` ·
Log: `errored-features.log` · Rol: **ek kaynak (ekleme modu)**

| Girdi | İçerik |
|---|---|
| `../raw-data/<TİP>.json` | DHMİ web haritası GeoJSON'ları: `CTR`, `D`, `D_OTHER`, `P`, `R`, `RAS`, `TMA` (+ `SECTOR`, işlenmez). İndirici: `navdata-data-downloaders/lt-dhmi` |
| `../data.json` | `Ibosoft AIS` / `DHMİ Türkiye` / effectivity (indirici günceller) |

Eşleme eski `Common Airspaces/sources/lt.py` ile aynıdır.

## 1. Alan eşlemesi

| Kaynak | AIXM | Kural |
|---|---|---|
| dosya adı (`TMA.json` → `TMA`) | `type` | Hepsi AIXM `CodeAirspaceType` listesinde |
| `kid` (`uuid.<uuid>`) | `gml:identifier` (UUID kısmı, büyük harf); `gml:id` = `LT_AS_<uuid>` | DHMİ'nin kendi kalıcı kimliği |
| `hi` | `designator` | |
| `pic` → 2. `NAME` (tek `NAME` varsa o) | `name` | `pic` HTML tablosu `parse_pic` ile ayrıştırılır |
| `pic` → `UPPER LIMIT` / `UPPER LIMIT REF.` | `upperLimit` + `upperLimitReference` | uom referanstan: `STD→FL`, `MSL`/`SFC→FT` (`derive_uom`) |
| `pic` → `LOWER LIMIT` / `LOWER LIMIT REF.` | `lowerLimit` + `lowerLimitReference` | aynı |
| geometri | `horizontalProjection` | `polygon_from_geojson` (geçersizse `buffer(0)`) → antimeridyen güvenli |
| `data.json` | provenance kutusu | |

**Aynı `kid`'li parçalar.** Ölçüldü: `RAS.json`'da `LTIHAT1` iki feature
olarak geliyor, ikisi de aynı `kid`'i ve aynı öznitelikleri taşıyor, poligonları
farklı. Aynı kaynak kimliği aynı hava sahası demektir: **tek Airspace**
yazılır, geometri iki parçanın MultiPolygon'udur (log:
`ayni_kid_parcalari_tek_airspace_yapildi`). Parçaların öznitelikleri farklı
olsaydı birleştirilmez, her parça türetilmiş kimlikle ayrı yazılır ve
loglanırdı. Bu yüzden 483 GeoJSON feature'ı 482 Airspace olur.

## 2. Aktarılmayan kaynak alanları

| Özellik | Durum |
|---|---|
| `t`, `strclr`, `cil`, `ht`, `gt`, `cip`, `zi` | DHMİ web haritasının görüntüleme alanları (tür kodu, renk, iframe bağlantısı, görünürlük, ikon, z-index) — AIXM karşılığı yok |
| `na`, `type` (özellik), `pic` → `TYPE` | Tür bilgisi; `type` dosya adından alınır (eski davranış). Özellikteki değer `TMA-MTMA` gibi birleşik olabilir |
| `pic` → 1. `NAME` | Ölçüldü: 483 kaydın **hepsinde** `hi` ile aynı (designator'ın tekrarı); açıklayıcı ad 2. `NAME`'dedir |
| `SECTOR.json` | İşlenmez: SECTOR verisi `tailored-LT` kaynağında elle tutulur |

## 3. Geçerlilik

`gml:validTime` başlangıcı `unknown`; `data_effectivity` veri setinin
geçerliliğidir, provenance kutusundadır.
