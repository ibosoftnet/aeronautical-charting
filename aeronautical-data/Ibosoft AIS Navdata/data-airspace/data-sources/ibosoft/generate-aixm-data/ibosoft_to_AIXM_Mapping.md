# ibosoft (originator Ibosoft AIS, elle tutulan) → AIXM 5.2 Airspace

Üretici: `generate_aixm.py` · Girdi: `../ibosoft-airspace.json` (1 kayıt, ATZ) ·
Çıktı: `../ibosoft-airspace-aixm.xml` · Rol: **ek kaynak (ekleme modu)**

Verinin yayımcısı (originator) bir otorite değil Ibosoft AIS'in kendisi olan
kayıtlar için ayrı kaynak (kullanıcı kararı). Eski
`Common Airspaces/data-sources/tailored/tailored.json`'dan ayrıldı.

Kod: `data-airspace/tailored_geojson.py`. `gml:id` öneki: `IBO_AS_<sıra>`.

## Kayıt biçimi (GeoJSON `properties`)

| Özellik | AIXM | Not |
|---|---|---|
| `aixm_uuid` | `gml:identifier` | **Zorunlu, kalıcı.** Yeni kayıtta yeni UUID üretilip yazılır; mevcut kayıtta değiştirilmez. `gml:id` = `IBO_AS_<sıra>` |
| `type` | `type` | `CodeAirspaceType` değeri |
| `designator`, `name`, `localType` | aynı adlı alanlar | `name`/`localType` Türkçe harf içerirse ASCII'ye çevrilir ve loglanır |
| `designatorICAO`, `controlType` | aynı adlı alanlar | |
| `classification` | `class/AirspaceLayerClass/classification` | |
| `upperLimit`, `upperLimitUom`, `upperLimitReference` | `upperLimit` (+ `uom`), `upperLimitReference` | |
| `lowerLimit`, `lowerLimitUom`, `lowerLimitReference` | aynı | |
| `activity`, `status` | `activation/AirspaceActivation` | biri varsa yazılır |
| `annotationDescription` / `Remark` / `Warning` / `Disclaimer` | `annotation` (purpose: DESCRIPTION / REMARK / WARNING / DISCLAIMER) | |
| `data_provider`, `data_originator`, `data_effectivity` | provenance kutusu | Kayıt başına. `data_effectivity`'ye dosya kökündeki `_effectivity_keys` sözlüğünün bir anahtarı yazılırsa değeri oradan çözülür — AIRAC güncellemesi tek yerden |
| geometri | `horizontalProjection` | Polygon / MultiPolygon |

Tanımsız bir özellik anahtarı dolu gelirse sessizce atlanmaz:
`tanimsiz_ozellik_eslenmedi` olarak loglanır.

AIRAC değişince: `_effectivity_keys` içindeki değer güncellenir.
