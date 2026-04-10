# EAD-SDO Designated Points GeoPackage

## Açıklama

Bu araç, EAD-SDO (European AIS Data Service - Standardized Data Only) kaynaklarından Designated Point (DP) verilerini XML formatından OGC-compliant GeoPackage formatına dönüştürür. 3 regional dosya (NE, NW, SE) birleştirilerek tek bir katman oluşturur.

## Kaynak Dosyalar

| Dosya | Bölge | Kayıt Sayısı |
|-------|-------|-------------|
| `dp-ne.xml` | North-East (Kuzey-Doğu) | - |
| `dp-nw.xml` | North-West (Kuzey-Batı) | - |
| `dp-se.xml` | South-East (Güney-Doğu) | ~10,190 |

## Katman

| Katman | Kayıt Sayısı |
|--------|-------------|
| `designated_points` | ~10,190 |

## Field Tanımları

### Koordinat Alanları
- **`lat_dd`**: Latitude (WGS84, decimal degrees)
- **`lon_dd`**: Longitude (WGS84, decimal degrees)
- **`lat_text`**: Latitude (original DMS format)
- **`lon_text`**: Longitude (original DMS format)

### Identification Alanları
- **`code_id`**: Designated Point Code (örn. "ABMEL", "ALVOR", "AA012")
- **`code_type`**: Type (örn. "ADHP" = Aerodrome Designated Point, "RNAV" = RNAVigation)
- **`name`**: Descriptive name

### Metadata Alanları
- **`datum`**: Coordinate datum (örn. "WGE" = WGS84)
- **`created_by`**: Creator organization (örn. "AIRWAYS CORPORATION OF NEW ZEALAND LTD")
- **`dt_wef`**: Date with effect (örn. "27/03/2019")
- **`mid`**: Unique internal identifier
- **`source`**: Veri kaynağı ("xml" = EAD-SDO, "tailored" = manuel)

## Suppress/Override Mekanizması

Dosya: `tailored-designated-points.jsonc`

Manuel olarak DP verilerini:
1. **Suppress** etmek (EAD-SDO'daki kaydı sil, yerine yenisini ekle)
2. **Ek kayıt** olarak eklemek

Suppress mantığı:
- **code_id** ve **created_by** IKISI DA girilirse → EAD-SDO'daki matching kaydı siler, yerine tailored giriş eklenir
- **code_id** veya **created_by** boşsa → Ek kayıt olarak layer'a eklenir, XML verisi dokunulmaz

Örnek:
```jsonc
{
  "suppress": {
    "code_id": "ABMEL",
    "created_by": "EUROCONTROL"
  },
  "code_id": "ABMEL",
  "code_type": "ADHP",
  "name": "ABMEL (Updated)",
  "datum": "WGE",
  "lat_dd": 40.1234,
  "lon_dd": 28.5678,
  "created_by": "EUROCONTROL",
  "dt_wef": "01/04/2026"
}
```

## Script Kullanımı

### Windows Batch Launcher
```bash
convert_designated_points.bat
```

Otomatik olarak `build_designated_points_gpkg.py` çalıştırır ve designated_points.gpkg oluşturur.

### Doğrudan Python
```bash
python build_designated_points_gpkg.py
```

### Çıktı
- **designated_points.gpkg**: OGC-compliant GeoPackage (QGIS tarafından doğrudan açılabilir)

## QGIS'te Kullanımı

1. QGIS'te `designated_points.gpkg` dosyasını açın
2. `designated_points` katmanı otomatik yüklenir
3. Point geometrisi (WGS84 EPSG:4326) ile tüm veriye erişilebilir
4. Attribute sorguları (code_id, code_type, name, vb.) doğrudan yapılabilir

Örnek sorgular:
```sql
-- Belirli bir code_type'ın tüm DP'leri
SELECT * FROM designated_points WHERE code_type = 'ADHP'

-- Belirli bir organizasyonun DP'leri
SELECT * FROM designated_points WHERE created_by = 'AIRWAYS CORPORATION OF NEW ZEALAND LTD'

-- Belirli bir tarihten sonra eklenen DP'ler
SELECT * FROM designated_points WHERE dt_wef >= '01/01/2020'
```

## Teknik Detaylar

### Koordinat Dönüşümü
- Input: DMS (Degrees, Minutes, Seconds) + Decimal Degrees
- Output: WGS84 (EPSG:4326) Decimal Degrees
- Geometry: WKB Point blobs (GeoPackage standard)

### Field Type Otomasyonu
- **REAL**: Koordinatlar (lat_dd, lon_dd)
- **TEXT**: Tüm diğer alanlar

### Data Integration
- **3 Regional Files**: NE, NW, SE dosyaları otomatik birleştirilir
- **No Deduplication**: Aynı code_id farklı bölgelerde bulunabilir (ihtiyaç varsa suppress kullanılır)

## Veri Kaynakları

- `dp-ne.xml`: North-East regional DP data (EAD-SDO)
- `dp-nw.xml`: North-West regional DP data (EAD-SDO)
- `dp-se.xml`: South-East regional DP data (EAD-SDO)
- `tailored-designated-points.jsonc`: Manuel veri override'ları

## Notlar

- Tüm kayıtlar WGS84 (EPSG:4326) referans sisteminde depolanır
- NULL değerler standart SQL NULL olarak tutulur (veritabanında, QGIS'te gri gösterilir)
- Regional dosyalar boş olabilir (dp-ne.xml, dp-nw.xml örneğinde boş, tüm veri dp-se.xml'de)
- GeoPackage bir standar spatial database formatı olduğu için, SQL sorguları direkt veritabanına yazılabilir

## File Size

- **designated_points.gpkg**: ~1.6 MB (10,190 DP kaydı)

## Format Specifications

- **Format**: OGC GeoPackage (SQLite-based)
- **CRS**: WGS84 (EPSG:4326)
- **Geometry Type**: Point
- **Table Engine**: SQLite3
