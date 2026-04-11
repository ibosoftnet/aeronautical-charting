# EUROCONTROL FRA Points

## Veri Kaynağı

EUROCONTROL tarafından yayımlanan Free Route Airspace (FRA) nokta verisi.

## Dosyalar

| Dosya | Açıklama |
|---|---|
| `fra-points.xlsx` | Ham veri (EUROCONTROL kaynaklı) |
| `fra-points.gpkg` | Üretilen GeoPackage (QGIS'te açılabilir) |
| `build_fra_gpkg.py` | Dönüştürme scripti |
| `convert_fra.bat` | Çalıştırma batch dosyası |

## Çalıştırma

```
convert_fra.bat
```

veya doğrudan:

```
py build_fra_gpkg.py
```

**Gereksinimler:** `openpyxl`, `geopandas`, `shapely`

## Ayarlar (`build_fra_gpkg.py` üstü)

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `EXCLUDE_DELETED` | `True` | `True` ise `Change Record = DEL` olan kayıtlar GeoPackage'a dahil edilmez |

## Koordinat Formatı

Koordinatlar DDMMSS formatındadır:

| Örnek | Tip | Dönüşüm |
|---|---|---|
| `N404519` | Enlem | N 40°45'19" → +40.755278° |
| `S404519` | Enlem | S 40°45'19" → −40.755278° |
| `E0183830` | Boylam | E 018°38'30" → +18.641667° |
| `W0183830` | Boylam | W 018°38'30" → −18.641667° |

## GeoPackage Katmanı: `fra_points`

| Alan | Tip | Açıklama |
|---|---|---|
| `change_record` | TEXT | Değişiklik türü (bkz. aşağıda) |
| `point_type` | TEXT | Navaid tipi; boşsa koordinat noktası |
| `ident` | TEXT | FRA nokta tanımlayıcısı |
| `fra_name` | TEXT | FRA bölge adı |
| `relevance_enroute` | TEXT | En-route kullanım (I / X / EX / -) |
| `relevance_arr_dep` | TEXT | Varış/kalkış kullanımı (A / D / AD / -) |
| `arrival_airport` | TEXT | İlişkili varış havalimanı ICAO kodu |
| `departure_airport` | TEXT | İlişkili kalkış havalimanı ICAO kodu |
| `flos` | TEXT | Flight Level Odd/Even kısıtı |
| `level_availability` | TEXT | Kullanılabilir uçuş seviyeleri (ör: FL195 / FL660) |
| `time_availability` | TEXT | Kullanılabilirlik zamanı (ör: H24) |
| `loc_indicators` | TEXT | FIR/UIR ICAO göstergesi(leri) |
| `remarks` | TEXT | Açıklamalar |
| `geometry` | Point | WGS84 (EPSG:4326) |

## Change Record Değerleri

| Değer | Açıklama |
|---|---|
| *(boş)* | Değişiklik yok |
| `NEW` | Yeni eklenen nokta |
| `AMD` | Değiştirilmiş nokta |
| `DEL` | Silinmiş nokta (`EXCLUDE_DELETED=True` ise dahil edilmez) |

## Point Type Değerleri

| Değer | Açıklama |
|---|---|
| *(boş)* | Koordinat tanımlı FRA noktası |
| `VOR` | VOR navaidi |
| `VORDME` | VOR/DME navaidi |
| `VORTAC` | VORTAC navaidi |
| `DME` | DME navaidi |
| `NDB` | NDB navaidi |
| `NDBDME` | NDB/DME navaidi |
| `TACAN` | TACAN navaidi |
