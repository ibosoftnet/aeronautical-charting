import os
import sqlite3
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "ourairports-aerodromes.csv")
GPKG_PATH = os.path.join(HERE, "ourairports-aerodromes.gpkg")
LAYER_NAME = "aerodromes"

print(f"Reading: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)
csv_columns = list(df.columns)
print(f"  CSV columns ({len(csv_columns)}): {', '.join(csv_columns)}")

df["latitude_deg"] = pd.to_numeric(df["latitude_deg"], errors="coerce")
df["longitude_deg"] = pd.to_numeric(df["longitude_deg"], errors="coerce")

missing = df["latitude_deg"].isna() | df["longitude_deg"].isna()
if missing.any():
    print(f"  Skipping {missing.sum()} row(s) with missing/invalid coordinates.")
    df = df[~missing].reset_index(drop=True)

geometry = [Point(lon, lat) for lon, lat in zip(df["longitude_deg"], df["latitude_deg"])]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

print(f"Writing: {GPKG_PATH}  ({len(gdf):,} features)")
gdf.to_file(GPKG_PATH, layer=LAYER_NAME, driver="GPKG")

with sqlite3.connect(GPKG_PATH) as con:
    gpkg_cols = {r[1] for r in con.execute(f'PRAGMA table_info("{LAYER_NAME}")').fetchall()}
    missing_cols = [c for c in csv_columns if c not in gpkg_cols]
    if missing_cols:
        print(f"  Restoring {len(missing_cols)} missing column(s): {', '.join(missing_cols)}")
        for col in missing_cols:
            con.execute(f'ALTER TABLE "{LAYER_NAME}" ADD COLUMN "{col}" TEXT')
        # geopandas assigns fid starting at 1, df index is 0-based after reset
        for col in missing_cols:
            values = [(str(v) if v != "" else None, i + 1) for i, v in enumerate(df[col])]
            con.executemany(f'UPDATE "{LAYER_NAME}" SET "{col}" = ? WHERE fid = ?', values)

    all_cols = [r[1] for r in con.execute(f'PRAGMA table_info("{LAYER_NAME}")').fetchall()
                if r[1] not in {"fid", "geom"}]
    for col in all_cols:
        con.execute(
            f'CREATE INDEX IF NOT EXISTS idx_{LAYER_NAME}_{col} ON "{LAYER_NAME}" ("{col}")'
        )
    con.commit()

print(f"Indexed: {', '.join(all_cols)}")
print("Done.")
