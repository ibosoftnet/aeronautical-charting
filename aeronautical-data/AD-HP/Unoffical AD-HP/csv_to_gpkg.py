import sys
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

# Replace empty strings with None for coordinate columns
df["latitude_deg"] = pd.to_numeric(df["latitude_deg"], errors="coerce")
df["longitude_deg"] = pd.to_numeric(df["longitude_deg"], errors="coerce")

missing = df["latitude_deg"].isna() | df["longitude_deg"].isna()
if missing.any():
    print(f"  Skipping {missing.sum()} row(s) with missing/invalid coordinates.")
    df = df[~missing].copy()

geometry = [Point(lon, lat) for lon, lat in zip(df["longitude_deg"], df["latitude_deg"])]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

print(f"Writing: {GPKG_PATH}  ({len(gdf):,} features)")
gdf.to_file(GPKG_PATH, layer=LAYER_NAME, driver="GPKG")

INDEXED_COLUMNS = ["ident", "icao_code", "gps_code"]
with sqlite3.connect(GPKG_PATH) as con:
    for col in INDEXED_COLUMNS:
        con.execute(f'CREATE INDEX idx_{LAYER_NAME}_{col} ON "{LAYER_NAME}" ({col})')
    con.commit()
print(f"Indexed: {', '.join(INDEXED_COLUMNS)}")

print("Done.")
