"""
EUROCONTROL FRA Points — Excel → GeoPackage
Koordinatlar DDMMSS formatından ondalık dereceye çevrilir.
Tüm sütunlara index oluşturur (lat/lon hariç), spatial index korunur.

Provenance: data_provider/data_originator data.json'dan okunur (ikisi de "EUROCONTROL").
data_effectivity, Excel'in COVER sayfasındaki A4 hücresinden ("Effective Date - " öneki
atılarak) okunur — her build'de kaynak dosyadaki güncel AIRAC tarihini yansıtır.
"""

import os
import sys
import json
import sqlite3
from collections import Counter

import openpyxl
import geopandas as gpd
from shapely.geometry import Point

# ---------------------------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------------------------
EXCLUDE_DELETED = True   # True ise Change Record == 'DEL' kayıtlar dahil edilmez
# ---------------------------------------------------------------------------

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE  = os.path.join(SCRIPT_DIR, 'fra-points.xlsx')
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'fra-points.gpkg')
DATA_JSON   = os.path.join(SCRIPT_DIR, 'data.json')
LAYER_NAME  = 'fra_points'
EFFECTIVITY_PREFIX = 'Effective Date - '


def load_source_meta(path):
    """data.json'dan data_provider/data_originator oku."""
    meta = {'data_provider': '', 'data_originator': ''}
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        for k in meta:
            meta[k] = data.get(k, '') or ''
    return meta


def read_effectivity(wb):
    """COVER sayfası A4 hücresinden ('Effective Date - ' öneki atılarak) tarihi oku."""
    cover = wb['COVER']
    raw = clean(cover['A4'].value)
    if raw.startswith(EFFECTIVITY_PREFIX):
        raw = raw[len(EFFECTIVITY_PREFIX):]
    return raw.strip()


def parse_ddmmss(val):
    """HDDMMSS / HDDDMMSS → ondalık derece."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    hemi   = s[0].upper()
    digits = s[1:]
    try:
        if hemi in ('N', 'S'):
            dd, mm, ss = int(digits[0:2]), int(digits[2:4]), int(digits[4:6])
        else:
            dd, mm, ss = int(digits[0:3]), int(digits[3:5]), int(digits[5:7])
    except (ValueError, IndexError):
        return None
    dec = dd + mm / 60.0 + ss / 3600.0
    if hemi in ('S', 'W'):
        dec = -dec
    return dec


def clean(val):
    """None → '', diğerleri → str().strip()"""
    if val is None:
        return ''
    return str(val).strip()


def main():
    print('=' * 60)
    print('FRA Points GeoPackage Oluşturucu')
    print('=' * 60)
    print()

    meta = load_source_meta(DATA_JSON)

    print('[1] Excel okunuyor...')
    wb = openpyxl.load_workbook(INPUT_FILE, read_only=True, data_only=True)
    ws = wb.active
    data_effectivity = read_effectivity(wb)
    print(f'  data_effectivity: {data_effectivity!r}')

    rows_total   = 0
    rows_deleted = 0
    rows_no_coord = 0
    records      = []
    cr_counter   = Counter()
    pt_counter   = Counter()

    for row in ws.iter_rows(min_row=2, values_only=True):
        rows_total += 1

        change_record   = clean(row[0])
        point_type      = clean(row[1])
        ident           = clean(row[2])
        lat_raw         = row[3]
        lon_raw         = row[4]
        fra_name        = clean(row[5])
        rel_enroute     = clean(row[6])
        rel_arr_dep     = clean(row[7])
        arrival_airport = clean(row[8])
        dep_airport     = clean(row[9])
        flos            = clean(row[10])
        level_avail     = clean(row[11])
        time_avail      = clean(row[12])
        loc_indicators  = clean(row[13])
        remarks         = clean(row[14])

        # DEL filtresi
        if EXCLUDE_DELETED and change_record == 'DEL':
            rows_deleted += 1
            continue

        # Koordinat parse
        lat = parse_ddmmss(lat_raw)
        lon = parse_ddmmss(lon_raw)
        if lat is None or lon is None:
            rows_no_coord += 1
            continue

        cr_counter[change_record or '(boş)'] += 1
        pt_counter[point_type   or '(koordinat noktası)'] += 1

        records.append({
            'change_record':   change_record,
            'point_type':      point_type,
            'ident':           ident,
            'fra_name':        fra_name,
            'relevance_enroute': rel_enroute,
            'relevance_arr_dep': rel_arr_dep,
            'arrival_airport': arrival_airport,
            'departure_airport': dep_airport,
            'flos':            flos,
            'level_availability': level_avail,
            'time_availability':  time_avail,
            'loc_indicators':  loc_indicators,
            'remarks':         remarks,
            'data_provider':   meta['data_provider'],
            'data_originator': meta['data_originator'],
            'data_effectivity': data_effectivity,
            'geometry':        Point(lon, lat),
        })

    wb.close()
    print(f'  Toplam satır   : {rows_total}')
    print(f'  DEL atlanan    : {rows_deleted}')
    print(f'  Koordinatsız   : {rows_no_coord}')
    print(f'  Yazılacak kayıt: {len(records)}')
    print()

    print('[2] GeoDataFrame oluşturuluyor...')
    gdf = gpd.GeoDataFrame(records, crs='EPSG:4326')

    print('[3] GeoPackage yazılıyor...')
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    gdf.to_file(OUTPUT_FILE, layer=LAYER_NAME, driver='GPKG')

    # Create indexes on all columns except lat/lon (geometry already has spatial index)
    print('[4] Indexler oluşturuluyor (lat/lon hariç)...')
    conn = sqlite3.connect(OUTPUT_FILE)
    cur = conn.cursor()

    # Sütunları oku
    cur.execute(f"PRAGMA table_info({LAYER_NAME})")
    columns = cur.fetchall()

    index_count = 0
    skip_columns = {'geometry', 'fid', 'lat_dd', 'lon_dd', 'lat_text', 'lon_text'}

    for col in columns:
        col_name = col[1]

        # lat/lon ve geom sütunlarını atla
        if col_name in skip_columns:
            continue

        idx_name = f"idx_fra_points_{col_name}"
        try:
            cur.execute(f"CREATE INDEX {idx_name} ON {LAYER_NAME}({col_name})")
            index_count += 1
        except sqlite3.OperationalError as e:
            if "already exists" not in str(e):
                print(f"  [warn] {col_name}: {e}")

    conn.commit()
    conn.close()
    print(f"  ✓ {index_count} index oluşturuldu")

    # Spatial index durumunu kontrol et
    conn = sqlite3.connect(OUTPUT_FILE)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'rtree%'")
    rtree_tables = cur.fetchall()
    conn.close()
    print(f"  ✓ Spatial index: rtree (mevcut, {len(rtree_tables)} tablo)")

    size_mb = os.path.getsize(OUTPUT_FILE) / 1024 / 1024
    print()
    print('=' * 60)
    print(f'Tamamlandı: fra-points.gpkg ({size_mb:.1f} MB)')
    print(f'  Katman: {LAYER_NAME} — {len(records)} kayıt')
    print()
    print('Change Record dağılımı:')
    for k, v in sorted(cr_counter.items()):
        print(f'  {k:<12} : {v}')
    print()
    print('Point Type dağılımı:')
    for k, v in sorted(pt_counter.items()):
        print(f'  {k:<25} : {v}')
    print('=' * 60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'\nHATA: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
