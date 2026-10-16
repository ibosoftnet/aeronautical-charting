# Jeppesen `boundary` → AIXM 5.2 Airspace

Üretici: `generate_aixm.py` · Çıktı: `../jeppesen-airspace-aixm.xml` ·
Log: `errored-features.log` · Rol: **ana kaynak**

| Girdi | İçerik |
|---|---|
| `aeronautical-data/Jeppesen Data/jeppesen.sqlite` → `boundary` | 37.104 satır (Navigraph) |
| `aeronautical-data/Jeppesen Data/data.json` | `data_provider` = `Jeppesen`, `data_effectivity`; `data_originator` boş |

Eşleme eski `Common Airspaces/sources/jeppesen.py` + `common/classify.py` ile
**aynıdır** (kullanıcı kararı); sınıflandırıcı `data-airspace/airspace_classify.py`'ye
birebir taşındı. İki fark: FIR içi eleme artık birleştiricideki iptal kuralıdır
(`../../excludes/`), designator yalnız `restrictive_designation`'dır.

## 1. Ön eleme (kayıt yazılmaz)

| Koşul | Gerekçe | Son koşu |
|---|---|---:|
| `type` = `FIR` / `UIR`, ya da `type` = `C` ve adında `fir`/`uir` geçiyor (`_is_fir_uir`, eski koddan birebir) | FIR/UIR sınırları ayrı ana kaynak ICAO-FIR-UIR'den gelir | 750 |
| Geometri blob'u çözülemiyor / geçersiz | Poligon uydurulmaz, loglanır | 0 |

## 2. Alan eşlemesi

| Jeppesen sütunu | AIXM | Kural |
|---|---|---|
| `boundary_id` | `gml:id` = `JEPP_AS_<id>`, `gml:identifier` = uuid5(`JeppesenAirspace:<id>`) | Kalıcı kimlik |
| `name` + `type` | `type` | `airspace_type(name, type)` öncelik sıralı ilk eşleşme; eşleşme yoksa `OTHER` (eski davranış) |
| `type` (`CA`…`CG`) | `class/AirspaceLayerClass/classification` | `CA→A … CG→G`; diğer tiplerde sınıf yazılmaz |
| `restrictive_designation` | `designator` | Yalnız bu alan (≤ 10 karakter). Eski `restrictive_type-restrictive_designation` biçimi 3.240 kayıtta AIXM'in 10 karakter sınırını aşıyordu (kullanıcı kararı) |
| `restrictive_type` | — (designator'a girmez) | Bilgisi `type`'a eşleniyor (`P`, `R`, `DA→D`, `W`, `AL→A` …) |
| `name` | `name` | Türkçe harf varsa ASCII'ye çevrilir ve loglanır |
| `max_altitude_type` = `UL` | `upperLimit` = `UNL` (uom/referans yok) | |
| `max_altitude` + `max_altitude_type` | `upperLimit` (uom `FT`) + `upperLimitReference` | `normalize_vref`: `AGL→SFC`, diğerleri aynen (`MSL`) |
| `min_altitude` + `min_altitude_type` | `lowerLimit` (uom `FT`) + `lowerLimitReference` | aynı |
| `geometry` (BE uint32 N + N×(float32 lon, lat)) | `horizontalProjection` | `decode_polygon_blob` → antimeridyen güvenli MultiPolygon |
| `data.json` | provenance kutusu | originator boş → yazılmaz |

`airspace_type` tablosu (öncelik sırası, `airspace_classify.py`): ad
anahtar kelimeleri `ctr/mctr→CTR`, `tma/mtma→TMA`, `cta/mcta→CTA`, `uta→UTA`,
`adiz→ADIZ`, `atz/matz→ATZ`, `rmz→RMZ`, `tmz→TMZ`; ham tip `P`, `R`,
`DA→D`, `AL→A`, `W`, `TR/M/CN` veya `sua→RAS`; ad `moa→MOA`, `oca`/"oceanic
control"→OCA, `ota`/"oceanic transition"→OTA, `ada/adv`/"advisory"→ADV,
"free rt"→FRA, "sector"→SECTOR.

## 3. Aktarılmayan kaynak alanları

| Sütun | Ölçülen içerik | Durum |
|---|---|---|
| `file_id` | 37.104 satırın hepsinde `1` | Veritabanı iç alanı |
| `description` | **0** satır dolu | Kaynakta yok |
| `max_lonx`, `max_laty`, `min_lonx`, `min_laty` | Sınırlayıcı kutu | Geometriden türetilir, ayrı bilgi değil |
| `multiple_code` | 12.630 satır (`A`, `B`, `Z`, `C` …) | **Eski kodda da aktarılmıyordu.** AIXM'de doğrudan karşılığı yok; anlamı (aynı adlı sahaları ayırt eden harf) kaynağın belgesiyle doğrulanmadı — karar bekliyor |
| `time_code` | 35.265 satır (`U`, `C`, `N`, `H`) | **Eski kodda da aktarılmıyordu.** Aktivasyon zamanına ilişkin olabilir; kodların anlamı doğrulanmadan `activation`'a eşlenmez — karar bekliyor |
| `com_type`, `com_frequency`, `com_name` | 646 satır (`CTR` + frekans + ad) | **Eski kodda da aktarılmıyordu.** Frekans AIXM'de `Airspace`'in değil `Unit`/`Service` feature'larının alanıdır; bu projede o feature'lar üretilmiyor |

## 4. Kimlik ve geçerlilik

`gml:validTime` başlangıcı `unknown`: Jeppesen'de feature başına yürürlük
tarihi yok; `data_effectivity` veri setinin geçerliliğidir (ATS Jeppesen
üreticisindeki kullanıcı kararıyla aynı).

Çalıştırma: `start-generate-aixm.bat` (veya `py generate_aixm.py`).
Doğrulama: `py ../../../../common/data_build_common/validate_aixm.py ../jeppesen-airspace-aixm.xml`.
