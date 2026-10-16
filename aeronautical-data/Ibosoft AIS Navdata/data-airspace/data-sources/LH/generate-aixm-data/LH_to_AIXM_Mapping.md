# LH (Macaristan) TNP dosyası → AIXM 5.2 Airspace

Üretici: `generate_aixm.py` · Çıktı: `../lh-airspace-aixm.xml` ·
Log: `errored-features.log` · Rol: **ek kaynak (ekleme modu)**

| Girdi | İçerik |
|---|---|
| `../data.txt` | TNP biçimi (soaringweb.org, HungaroControl verisinden; "UNOFFICIAL"). Kayıtlar `INCLUDE=YES` ile başlar; anahtarlar `CLASS`, `TYPE`, `TITLE`, `TOPS`, `BASE`, `POINT` |
| `../data.json` | `soaringweb.org` / `HungaroControl` / `23 JUN 2026 (Non-AIRAC)` |

Eşleme eski `Common Airspaces/sources/lh.py` ile aynıdır. Dosyadaki tüm
anahtarlar (ölçüldü: `INCLUDE`, `CLASS`, `TITLE`, `TOPS`, `BASE`, `TYPE`,
`POINT`) okunur; bilinmeyen bir anahtar gelirse loglanır.

## 1. Alan eşlemesi

| Kaynak | AIXM | Kural |
|---|---|---|
| sıra no + `TITLE` | `gml:id` = `LH_AS_<sıra>`, `gml:identifier` = uuid5(`LhAirspace:<sıra>:<başlık>`) | Kaynakta kalıcı kimlik yok; dosya değişirse sıra kayabilir |
| `TITLE` | `name` | |
| `TYPE` (`PROHIBITED`/`RESTRICTED`/`DANGER`) | `type` = `P`/`R`/`D` | yoksa başlıktan (`lh_type_from_title`: `CTR`, `TMA`, `CTA`, `UTA`, `OCA`, `ADIZ`, `ATZ`, `RMZ`, `TMZ`, `MOA`, `FRA`, `SECTOR`), o da yoksa `RAS` (eski davranış) |
| `CLASS` | `class/AirspaceLayerClass/classification` | `A`–`G` ve `OTHER` aynen. Listede olmayan değer AIXM'in genişletme deseniyle `OTHER:<değer>` yazılır ve loglanır (ölçüldü: `GSEC`, 5 kayıt) |
| `TOPS` | `upperLimit` (+ uom) + `upperLimitReference` | `parse_lh_altitude`: `GND`/`UNL` özel değer (uom/referans yok); `STD` referansında feet en yakın FL'e yuvarlanır (`19501ft` → `FL195`), diğerleri `FT` |
| `BASE` | `lowerLimit` (+ uom) + `lowerLimitReference` | aynı (ölçüldü: 141 kayıt `GND`) |
| `POINT=Nddmmss Edddmmss` | `horizontalProjection` | DMS → ondalık, poligon (< 3 nokta → loglanır, yazılmaz) |
| `data.json` | provenance kutusu | |

## 2. Geçerlilik

`gml:validTime` başlangıcı `unknown`; dosya tarihi provenance kutusundadır.
