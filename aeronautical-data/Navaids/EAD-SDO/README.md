# EAD-SDO Navaid GeoPackage

## Açıklama

Bu araç, EAD-SDO (European AIS Data Service - Standardized Data Only) kaynaklarından navaid verilerini GeoJSON/XML formatından OGC-compliant GeoPackage formatına dönüştürür. 8 katman içinde VOR, DME, TACAN, ILS ve ilgili alt-elementleri içerir.

## Katmanlar (Layers)

| Katman | Geometri Kaynağı | İçerik | Kayıt Sayısı |
|--------|------------------|--------|-------------|
| `ils_loc` | LOC kaydı | ILS LOC + sub-element GP/DME alanları | ~548 |
| `ils_gp` | GP kaydı | ILS GP (sub-element olarak bulunmuş) | ~522 |
| `ils_dme` | DME kaydı | ILS DME (sub-element olarak bulunmuş) | ~402 |
| `vor` | VOR kaydı | Standalone VOR navigasyonu | ~328 |
| `vor_dme` | VOR kaydı | VOR+DME joined | ~2797 |
| `vortac` | VOR kaydı | VOR+TACAN joined | ~467 |
| `dme` | DME kaydı | Standalone DME navigasyonu | ~1467 |
| `tacan` | TACAN kaydı | Standalone TACAN navigasyonu | ~410 |

## Standardize Frequency Fields

Her katman aşağıdaki ortak alanları içerir:

- **`frequency`**: Primary frequency kaynağı
- **`channelNo`**: DME/TACAN channel numarası (varsa)

### Katman-Spesifik Konfigürasyon

#### ILS-LOC
- `frequency` = `loc_freq` (LOC'un VHF frequency'si)
- `channelNo` = `loc_freq`'ten reverse lookup (eğer match varsa)

#### ILS-GP
- `frequency` = `gp_freq` (GPS approach frequency)
- `channelNo` = NULL (GP frequency VHF olmadığı için lookup yapılmaz)

#### ILS-DME
- `channelNo` = `dme_channel` (DME'nin kendi channel'ı)
- `frequency` = `dme_channel`'dan lookup (eğer eksikse)

#### VOR
- `frequency` = `vor_freq` (VOR'un VHF frequency'si)
- `channelNo` = NULL (VOR frequency'si fixed aralık olduğu için DME channel'a map'lanmaz)

#### VOR-DME
- `frequency` = `vor_freq` (VOR component frequency'si)
- `channelNo` = NULL (VOR frequency'si map'lanmaz)

#### VORTAC
- `channelNo` = `tacan_channel` (TACAN'ın kendi channel'ı)
- `frequency` = `tacan_channel`'dan lookup

#### DME (Standalone)
- `channelNo` = `dme_channel` (DME'nin kendi channel'ı)
- `frequency` = `dme_channel`'dan lookup (eğer eksikse)

#### TACAN (Standalone)
- `channelNo` = `tacan_channel` (TACAN'ın kendi channel'ı)
- `frequency` = `tacan_channel`'dan lookup

## Frequency Lookup Tablosu

Dosya: `frequency-pairing.csv`

DME channel ↔ VHF frequency bidirectional mapping:
- **DME Channel** (Col 0): `1X`, `1Y`, `2X`, ... `126Y`
- **VHF Frequency MHz** (Col 1): `108.00`, `108.05`, ... `117.95`
- **GP Frequency MHz** (Col 11): Sadece bazı channels için (optional)

Örnek:
```
Channel 44X → VHF 110.70 MHz
Channel 26X → VHF 108.90 MHz
Channel 56Y → VHF 111.95 MHz
```

## Field Naming Convention

Prefix-based field naming:
- `loc_*`: ILS-LOC element fields
- `gp_*`: GPS Approach element fields
- `dme_*`: DME element fields
- `vor_*`: VOR element fields
- `tacan_*`: TACAN element fields

Ortak alanlar (prefix yok):
- `channelNo`: Channel numarası (standardize)
- `frequency`: Frequency değeri (standardize)

## Suppress/Override Mekanizması

Dosya: `tailored-navaids.jsonc`

Manuel olarak navaid verilerini:
1. **Suppress** etmek (EAD-SDO'daki kaydı sil, yerine yenisini ekle)
2. **Ek kayıt** olarak eklemek

Örnek:
```jsonc
{
  "suppress": {
    "ident": "IJKI",
    "originator": "EUROCONTROL"
  },
  "type": "ils",
  "code_id": "IJKI",
  "ahp_code_id": "LTAC",
  "freq": "110.50",
  "lat_dd": 41.1234,
  "lon_dd": 28.9876,
  "created_by": "EUROCONTROL",
  "dt_wef": "26/03/2026"
}
```

## Script Kullanımı

### Windows Batch Launcher
```bash
convert_navaids.bat
```

Otomatik olarak `build_navaids_gpkg.py` çalıştırır ve navaids.gpkg oluşturur.

### Doğrudan Python
```bash
python build_navaids_gpkg.py
```

### Çıktı
- **navaids.gpkg**: OGC-compliant GeoPackage (QGIS tarafından doğrudan açılabilir)

## QGIS'te Kullanım

1. QGIS'te `navaids.gpkg` dosyasını açın
2. Tüm katmanlar otomatik yüklenir
3. Her katman kendi geometri türüne (Point) ve spatial reference (WGS84 EPSG:4326) sahiptir
4. Attribute sorguları (frequency, channelNo, vb.) doğrudan yapılabilir

## Teknik Detaylar

### Koordinat Dönüşümü
- Input: DMS (Degrees, Minutes, Seconds) + Decimal Degrees
- Output: WGS84 (EPSG:4326) Decimal Degrees
- Geometry: WKB Point blobs (GeoPackage standard)

### Field Type Otomasyonu
- **REAL**: Koordinatlar, frekanslar, yükseklikler, açılar, bearing vb.
- **INTEGER**: Joined flags
- **TEXT**: Identifiers, codes, descriptions vb.

### Join Logic
- **LOC + GP**: ahp_code_id + fir_code_id + code_id + originator match
- **LOC + DME**: code_id + originator match (vor_code_id = NULL)
- **VOR + DME**: code_id + originator match (vor_code_id match)
- **VOR + TACAN**: code_id + originator match (vor_code_id match)

## Veri Kaynakları

- `vor.xml`: VOR navigasyonu
- `dme.xml`: DME navigasyonu
- `tacan.xml`: TACAN navigasyonu
- `ils-loc.xml`: ILS LOC component
- `ils-gp.xml`: ILS GP (Glide Path) component
- `frequency-pairing.csv`: DME channel ↔ VHF frequency lookup
- `tailored-navaids.jsonc`: Manuel veri override'ları

## Notlar

- Tüm kayıtlar WGS84 (EPSG:4326) referans sisteminde depolanır
- Geometry otomatik olarak primary element konumundan türetilir
- Sub-element alanları flattened format'ta katmanda saklanır
- NULL değerler standart SQL NULL olarak tutulur (veritabanında, QGIS'te gri gösterilir)
