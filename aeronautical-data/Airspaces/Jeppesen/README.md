# Jeppesen Airspaces

Bu klasör, Jeppesen sqlite veritabanındaki `boundary` tablosundan üretilmiş hava sahası poligonlarını içerir.

- **Kaynak**: [../../Jeppesen Data/jeppesen.sqlite](../../Jeppesen%20Data/jeppesen.sqlite), tablo `boundary` (36,622 kayıt)
- **Çıktı**: `jeppesen_airspaces.gpkg` — GeoPackage, tek tablo `airspaces`, EPSG:4326 POLYGON, RTree spatial index dahil. QGIS'e drag-and-drop yeterli.
- **Üreten**: [export_airspaces.py](export_airspaces.py)
- **Geometry kodlaması**: blob = `[BE uint32 N]` + `N × (BE float32 lon, BE float32 lat)`. Ring kapatılmamış, decoder kapatır.

## Çıktı şeması (`airspaces` tablosu)

| sütun | tip | açıklama |
|---|---|---|
| `fid` | INTEGER PK | GeoPackage feature id |
| `geom` | POLYGON (4326) | hava sahası sınırı |
| `source` | TEXT | `jeppesen` / `jeppesen+override` / `tailored` |
| `boundary_id`, `file_id` | INTEGER | Jeppesen kaynak PK + dosya referansı |
| `type`, `name`, `description` | TEXT | hava sahası tipi/adı/açıklama |
| `restrictive_designation`, `restrictive_type`, `multiple_code`, `time_code` | TEXT | kısıtlama / kod alanları |
| `com_type`, `com_frequency`, `com_name` | TEXT/INT | telsiz bilgisi (çoğu NULL) |
| `min_altitude_type`, `max_altitude_type` | TEXT | `MSL`/`AGL` vs. |
| `min_altitude`, `max_altitude` | INTEGER | feet |
| `min_lonx`, `min_laty`, `max_lonx`, `max_laty` | REAL | bbox |

---

## Sütunlardaki distinct değerler

### `type` — 23 farklı değer

| değer | adet |
|---|---|
| `R`    | 8432 |
| `CD`   | 4586 |
| `DA`   | 4368 |
| `CC`   | 3964 |
| `W`    | 3507 |
| `P`    | 2448 |
| `CE`   | 2151 |
| `TR`   | 1676 |
| `M`    | 1302 |
| `C`    | 917 |
| `GCA`  | 793 |
| `CA`   | 740 |
| `CB`   | 680 |
| `FIR`  | 271 |
| `T`    | 210 |
| `CG`   | 146 |
| `CN`   | 125 |
| `TRSA` | 107 |
| `UIR`  | 104 |
| `AL`   | 49 |
| `RD`   | 29 |
| `MCTR` | 12 |
| `CF`   | 5 |

### `restrictive_type` — 9 farklı değer

| değer | adet |
|---|---|
| `NULL` | 14715 |
| `R`    | 8432 |
| `D`    | 4368 |
| `W`    | 3507 |
| `P`    | 2448 |
| `T`    | 1676 |
| `M`    | 1302 |
| `C`    | 125 |
| `A`    | 49 |

### `multiple_code` — 28 farklı değer

| değer | adet |
|---|---|
| `NULL` | 23387 |
| `A` | 2679 |
| `B` | 2644 |
| `Z` | 1603 |
| `C` | 1220 |
| `D` | 766 |
| `''` (boş string) | 750 |
| `E` | 586 |
| `F` | 476 |
| `G` | 362 |
| `H` | 305 |
| `I` | 251 |
| `J` | 207 |
| `K` | 189 |
| `L` | 166 |
| `M` | 145 |
| `N` | 124 |
| `O` | 109 |
| `P` | 99 |
| `R` | 82 |
| `Q` | 79 |
| `S` | 77 |
| `T` | 66 |
| `U` | 62 |
| `X` | 50 |
| `W` | 50 |
| `V` | 50 |
| `Y` | 38 |

### `time_code` — 5 farklı değer

| değer | adet |
|---|---|
| `U`    | 22657 |
| `C`    | 6685 |
| `N`    | 4908 |
| `NULL` | 1810 |
| `H`    | 562 |

---

## Tailored veri (opsiyonel `tailored.geojson`)

Bu klasörde `tailored.geojson` adlı bir GeoJSON dosyası bulunursa, [export_airspaces.py](export_airspaces.py) onu Jeppesen verisinin üzerine merge eder.

İki kullanım:
- **override** — mevcut bir Jeppesen kaydının attribute'larını ve/veya geometrisini değiştir
- **new**     — Jeppesen'de hiç olmayan yeni bir hava sahası ekle

`source` kolonu sayesinde QGIS'te `jeppesen` / `jeppesen+override` / `tailored` ayrımı filter/sembol olarak kullanılabilir.

### Örnek `tailored.geojson`

```json
{
  "type": "FeatureCollection",
  "name": "tailored_airspaces",
  "crs": { "type": "name", "properties": { "name": "EPSG:4326" } },
  "features": [
    {
      "type": "Feature",
      "properties": {
        "action": "override",
        "boundary_id": 270,
        "name": "ISTANBUL FIR (LTAA) - local edit",
        "max_altitude": 66000
      },
      "geometry": null
    },
    {
      "type": "Feature",
      "properties": {
        "action": "new",
        "type": "R",
        "name": "ORNEK YASAK BOLGE",
        "restrictive_designation": "LTR99",
        "restrictive_type": "R",
        "min_altitude_type": "MSL",
        "max_altitude_type": "MSL",
        "min_altitude": 0,
        "max_altitude": 10000
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [32.50, 39.90], [32.60, 39.90],
          [32.60, 40.00], [32.50, 40.00],
          [32.50, 39.90]
        ]]
      }
    }
  ]
}
```

**Kurallar:**
- `action` verilmezse `"new"` varsayılır.
- `override` için `boundary_id` zorunlu; eşleşme yoksa uyarı basılır ve atlanır.
- `override` geometrisi `null` ise orijinal geometri korunur, sadece verilen attribute'lar güncellenir.
- `new` için `geometry` zorunlu (Polygon). `boundary_id` yok sayılır (NULL kalır).
- Geometri her zaman EPSG:4326 (`lon, lat`) sırasında.

QGIS'te tailored dosyasını üretmenin pratik yolu: yeni bir geçici layer yarat (POLYGON, 4326), poligonu çiz, attribute'ları doldur, sağ-tık → Export → Save Features As → GeoJSON → `tailored.geojson` olarak bu klasöre kaydet. Sonra `python export_airspaces.py` çalıştır.

## Yeniden üretim

```powershell
python "aeronautical-data/Airspaces/Jeppesen/export_airspaces.py"
```

Beklenen çıktı: `Jeppesen: inserted=~36622 skipped=…`, ardından (varsa) `Tailored: overrides=…  new=…`.
